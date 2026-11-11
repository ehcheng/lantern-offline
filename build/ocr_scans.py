#!/usr/bin/env python3
"""H37(a): give scanned PDFs a text layer (ocrmypdf --skip-text), in place.

Detection rule is gen_text.py's: `pdftotext -enc UTF-8 f -` yields < MIN_TEXT
chars after stripping form feeds and whitespace. Originals are copied to BAK
before being overwritten. Resumable via cache/ocr/done/<sha1(relpath)>.

  ocr_scans.py --enum          enumerate only, print counts by shelf/category
  ocr_scans.py --run [--limit N] [--workers W] [--list FILE] [--force] [--redo] [--mixed] [--lang L] [--bak DIR]

CropBox (FIXES #112): a page whose CropBox is smaller than its MediaBox shows only the crop, but ocrmypdf
rasterises the whole MediaBox. On scans placed inside a larger white page (e.g. a 4x5 in scan on a Letter
MediaBox) tesseract's threshold then treats the whole tinted scan as background and finds no text. Before OCR,
such pages are normalised: content shifted so the crop starts at 0,0, MediaBox = crop, other boxes dropped,
annotation rects shifted. Lossless (no re-encoding). Only pages with no extractable text are touched (the pages
ocrmypdf will OCR): pages with text keep their geometry, because some hold real text in the hidden strip (plate
captions under a Google/Microsoft crop) that clipping would drop from pdftotext.

--mixed (FIXES #112, for files that already have text): OCR only the text-less pages (--pages), then retry the
pages still empty with --redo-ocr --oversample 300 (auto, then adaptive-otsu thresholding). Never --force-ocr:
output page images stay as they were. In every --mixed pass, a page whose new text is not plausibly words is left
without text rather than indexed as noise (photos and upside-down tables make tesseract invent letters). Word lists:
/usr/share/dict/words for eng, tesseract's own dictionary for fra, deu, spa, ... (#112b).
--selftest checks the box normaliser and the noise gate.
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))
from gen_text import MIN_TEXT, WHITELIST  # noqa: E402  (the detection rule lives there)

DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "library", "docs")
BAK = os.path.join(os.path.dirname(os.path.realpath(DOCS)), "docs_ocr_bak_20260925")   # beside the bulk docs/ (library/docs is a symlink)
RES = os.path.join(os.path.dirname(__file__), "..", "cache", "ocr")
DONE = os.path.join(RES, "done")
SHELVES = ["survivor_library", "cd3wd", "HISTORICAL"] + [
    w[len("docs/"):] for w in WHITELIST if w.startswith("docs/")]
OCR = ["ocrmypdf", "--skip-text", "--optimize", "0", "--output-type", "pdf",
       "-l", "eng+spa", "--jobs", "2", "--tesseract-timeout", "600"]
OCRPY = open(shutil.which("ocrmypdf") or "/dev/null").readline()[2:].strip()  # ocrmypdf's own python has pikepdf
NORMALIZE = r"""
import sys, pikepdf
pdf = pikepdf.open(sys.argv[1]); n = 0
only = {int(x) for x in sys.argv[3].split(",") if x}
for i, pg in enumerate(pdf.pages):
    if i + 1 not in only:
        continue
    m = [float(v) for v in pg.mediabox]; c = [float(v) for v in pg.cropbox]
    m = [min(m[0], m[2]), min(m[1], m[3]), max(m[0], m[2]), max(m[1], m[3])]
    c = [max(min(c[0], c[2]), m[0]), max(min(c[1], c[3]), m[1]), min(max(c[0], c[2]), m[2]), min(max(c[1], c[3]), m[3])]
    if max(abs(a - b) for a, b in zip(m, c)) < 1 or c[2] - c[0] < 10 or c[3] - c[1] < 10:
        continue
    x, y = c[0], c[1]
    pg.contents_add(pikepdf.Stream(pdf, b"q 1 0 0 1 %.4f %.4f cm\n" % (-x, -y)), prepend=True)
    pg.contents_add(pikepdf.Stream(pdf, b"\nQ"))
    pg.MediaBox = pikepdf.Array([0, 0, c[2] - x, c[3] - y])
    for k in ("/CropBox", "/TrimBox", "/BleedBox", "/ArtBox"):
        if k in pg.obj: del pg.obj[k]
    for a in pg.get("/Annots", []):
        if "/Rect" in a:
            r = [float(v) for v in a.Rect]; a.Rect = pikepdf.Array([r[0] - x, r[1] - y, r[2] - x, r[3] - y])
    n += 1
if n: pdf.save(sys.argv[2])
print(n)
"""


def empty_pages(pdf):
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", pdf, "-"], capture_output=True, timeout=900)
    return [i + 1 for i, t in enumerate(r.stdout.decode("utf-8", "replace").split("\f")[:-1]) if not t.split()]


def page_text(pdf, p):
    return subprocess.run(["pdftotext", "-enc", "UTF-8", "-f", str(p), "-l", str(p), pdf, "-"],
                          capture_output=True, timeout=300).stdout.decode("utf-8", "replace")


_WORDS = {}


def wordlist(lang):
    """English: /usr/share/dict/words (tesseract's eng list holds too many short fragments: MATA, ONY). Other languages:
    tesseract's own dictionary for `lang` (fra, deu, spa, ...), unpacked once into cache/ocr/wordlists."""
    if lang == "eng" and lang not in _WORDS:
        _WORDS[lang] = {w.strip().lower() for w in open("/usr/share/dict/words")}
    if lang not in _WORDS:
        out = os.path.join(RES, "wordlists", lang + ".words")
        if not os.path.exists(out):
            import tempfile
            os.makedirs(os.path.dirname(out), exist_ok=True)
            td = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout.split('"')[1]
            with tempfile.TemporaryDirectory() as t:
                subprocess.run(["combine_tessdata", "-u", os.path.join(td, lang + ".traineddata"), os.path.join(t, lang + ".")],
                               capture_output=True, check=True)
                subprocess.run(["dawg2wordlist", os.path.join(t, lang + ".lstm-unicharset"),
                                os.path.join(t, lang + ".lstm-word-dawg"), out + ".part"], capture_output=True, check=True)
            os.rename(out + ".part", out)
        _WORDS[lang] = {w.strip().lower() for w in open(out, encoding="utf-8")}
    return _WORDS[lang]


def plausible(text):
    """>= 2 dictionary words (plain English suffixes also stripped) making up >= 30% of the tokens that contain a
    letter. Dictionary = union of the word lists for the run's languages (-l eng+spa -> eng and spa)."""
    words = set().union(*(wordlist(l) for l in OCR_REDO[OCR_REDO.index("-l") + 1].split("+")))
    # dot leaders come out as "cece eee reece esse": drop such tokens (mostly c/e, >= 3 letters) from both counts
    text = " ".join(t for t in text.split() if not (len(re.sub(r"[.,:;']", "", t)) >= 3 and re.fullmatch(r"[ceonrsta.,:;']+", t)
                                                   and sum(ch in "ce" for ch in t) * 2 >= len(re.sub(r"[.,:;']", "", t))))
    toks = [t for t in text.split() if re.search(r"[^\W\d_]", t)]
    hits = longest = 0
    for t in re.findall(r"[^\W\d_]{3,}", text):
        w = t.lower()
        vs = [w] + [w[:-len(x)] + y for x, y in (("s", ""), ("es", ""), ("ed", ""), ("ed", "e"), ("ing", ""),
                                                    ("ing", "e"), ("ly", "")) if w.endswith(x)]
        if any(len(v) >= 3 and v in words for v in vs):
            hits += 1; longest = max(longest, len(w))
    # one real word of 5+ letters: short dictionary hits ("mgr oar aero") come up by chance in photo noise
    return hits >= 2 and hits >= 0.3 * len(toks) and longest >= 5


def normalize_boxes(src, dst):
    """Write dst with the text-less pages crop-normalised; return the number of pages changed (0: dst not written)."""
    empty = empty_pages(src)
    if not empty:
        return 0
    r = subprocess.run([OCRPY, "-I", "-c", NORMALIZE, src, dst, ",".join(map(str, empty))],
                       capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError("normalize: " + (r.stderr.strip().splitlines() or ["?"])[-1])
    return int(r.stdout.strip() or 0)


def selftest():
    """Offset CropBox on a text-less page -> MediaBox [0 0 w h], CropBox gone, content shifted; idempotent."""
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        src, dst, chk = (os.path.join(t, n) for n in ("a.pdf", "b.pdf", "c.pdf"))
        subprocess.run([OCRPY, "-I", "-c", "import pikepdf,sys; p=pikepdf.new(); p.add_blank_page(page_size=(612,792)); "
                        "p.pages[0].CropBox=pikepdf.Array([100,150,300,450]); p.save(sys.argv[1])", src], check=True)
        assert normalize_boxes(src, dst) == 1
        out = subprocess.run(["pdfinfo", "-box", dst], capture_output=True, text=True).stdout
        boxes = {l.split(":")[0]: l.split(":")[1].split() for l in out.splitlines() if "Box:" in l}
        assert boxes["MediaBox"] == boxes["CropBox"] == ["0.00", "0.00", "200.00", "300.00"], boxes
        assert normalize_boxes(dst, chk) == 0
    OCR_REDO[OCR_REDO.index("-l") + 1] = "eng"
    assert plausible("| Framing Pictures") and plausible("G & GUIDE*BOLT*OPERATING ROD")
    assert not plausible("be it ioe siteangy ek, a it i al) =e ol ey i a Wi)! Brabe MRE ThA ROO a civ ri Barey e")
    assert not plausible("MATA WOLLOG ONY MJIA dOL—3NIZVOYN—ILS DLV Id") and not plausible("mgr 2 oar aero")
    assert plausible("INDEX Aesthetic values... 0.2... 02 ec eee eee cee eect eee ete n cence resenees 2.5 "
                     "Burning, prescribed ............ esse cere eee e reece Lecce ceeeees 4.3")
    OCR_REDO[OCR_REDO.index("-l") + 1] = "fra"
    assert plausible("Le réseau de distribution d'eau potable") and not plausible("© ES, ON ES, EN SES, EN EL ENS, EN, ES LOS")
    OCR_REDO[OCR_REDO.index("-l") + 1] = "deu"
    assert plausible("Magazin K 43 an Stelle der linken Patrone") and not plausible(
        "ulhenrpe tohc Hl für Entternangstrilueg hi ERBENanSeilenwarsteldung Körebinerrigmen Aasthabus öigtanı")
    print("selftest ok")


# --mixed: a second pass with --redo-ocr limited to pages still without text. redo-ocr keeps visible text and
# OCRs the image areas around it; unlike --force-ocr it never rasterises the output page.
MIXED = False
OCR_REDO = ["ocrmypdf", "--redo-ocr", "--optimize", "0", "--output-type", "pdf", "-l", "eng+spa", "--jobs", "2",
            "--tesseract-timeout", "600"]
# ponytail: no confidence floor. ocrmypdf has no per-page confidence gate;
# upgrade path is --pdf-renderer hocr + filtering hOCR by x_wconf before render.


def text_chars(pdf):
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", pdf, "-"],
                       capture_output=True, timeout=600)
    if r.returncode != 0:
        return None
    return len(r.stdout.decode("utf-8", "replace").replace("\f", "").strip())


def pages(pdf):
    r = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True, timeout=120)
    for line in r.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    return -1


def enumerate_pdfs():
    for shelf in SHELVES:
        base = os.path.join(DOCS, shelf)
        for root, _, files in os.walk(base):
            for fn in sorted(files):
                if fn.lower().endswith(".pdf") and not fn.startswith("."):
                    yield os.path.relpath(os.path.join(root, fn), DOCS)


def check(rel):
    try:
        n = text_chars(os.path.join(DOCS, rel))
    except subprocess.TimeoutExpired:
        n = None
    return rel, n


def enum(workers):
    need, bad = [], []
    with ThreadPoolExecutor(workers) as ex:
        for rel, n in ex.map(check, enumerate_pdfs()):
            if n is None:
                bad.append(rel)
            elif n < MIN_TEXT:
                need.append(rel)
    os.makedirs(RES, exist_ok=True)
    with open(os.path.join(RES, "needs_ocr.txt"), "w") as f:
        f.write("".join(r + "\n" for r in need))
    counts = {}
    for r in need:
        p = r.split("/")
        key = p[0] if p[0] != "survivor_library" else "/".join(p[:3])  # shelf/SurvivalLibrary/<cat>
        counts[key] = counts.get(key, 0) + 1
    print(f"needs_ocr={len(need)} pdftotext_failed={len(bad)}")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"{v:6d}  {k}")
    for r in bad:
        print(f"BAD  {r}")
    return need


def key(rel):
    return os.path.join(DONE, hashlib.sha1(rel.encode()).hexdigest())


def gated_pass(cmd, inp, out, todo, gate=True):
    """cmd + --pages todo, inp -> out; keep it only if pages and qpdf hold. With an English-only run, pages whose
    new text is noise (oversampled photos) are dropped from --pages and the pass is redone. Returns (ok, why)."""
    def once(pg):
        if os.path.exists(out):
            os.remove(out)
        r = subprocess.run(cmd + ["--pages", ",".join(map(str, pg)), inp, out], capture_output=True, text=True,
                           timeout=6 * 3600)
        return r.returncode == 0 and os.path.exists(out) and pages(out) == pages(inp) and \
            subprocess.run(["qpdf", "--check", out], capture_output=True, timeout=600).returncode in (0, 3)
    if not once(todo):
        return False, "ocrmypdf or gate failed"
    bad = [p for p in todo if gate and page_text(out, p).strip() and not plausible(page_text(out, p))]
    good = [p for p in todo if p not in bad]
    if bad and not (good and once(good)):
        if os.path.exists(out):
            os.remove(out)
        return False, "only noise"
    return True, ""


def ocr_one(rel):
    src = os.path.join(DOCS, rel)
    bak = os.path.join(BAK, rel)
    tmp = src + ".ocr.tmp"
    norm = src + ".norm.tmp"
    t0 = time.time()
    try:
        if not os.path.exists(bak):
            os.makedirs(os.path.dirname(bak), exist_ok=True)
            shutil.copy2(src, bak + ".part")
            os.rename(bak + ".part", bak)
        inp = norm if normalize_boxes(src, norm) else src
        if MIXED:  # page-limited, gated passes: only text-less pages are OCR'd and noise is not kept
            todo = empty_pages(inp)
            # gated too (#112b): upside-down tables and photos give mirrored noise at native resolution as well;
            # tables and Latin indexes pass because only letter-bearing tokens are counted. Costs a few one-line
            # captions with Latin names ("Biscuit-Root (Peucedanum ambiguum)").
            ok, err = (gated_pass(OCR, inp, tmp, todo) if todo else (False, "no text-less pages"))
            if not ok:
                shutil.copy2(inp, tmp)
            for thr in ("auto", "adaptive-otsu"):
                # pages still without text: a stray text object over a scan (--skip-text skipped them), a 96 ppi
                # image (too coarse for tesseract), or a tinted page (global Otsu blanks it). Upsample the OCR
                # raster to 300 dpi (output images untouched) and retry with adaptive thresholding.
                left = empty_pages(tmp)
                if left and gated_pass(OCR_REDO + ["--oversample", "300", "--tesseract-thresholding", thr],
                                       tmp, tmp + "2", left)[0]:
                    os.replace(tmp + "2", tmp)
            r = subprocess.CompletedProcess([], 0, "", "")
        else:
            r = subprocess.run(OCR + [inp, tmp], capture_output=True, text=True, timeout=6 * 3600)
        if os.path.exists(norm):
            os.remove(norm)
        q = subprocess.run(["qpdf", "--check", tmp], capture_output=True, timeout=600).returncode if os.path.exists(tmp) else -1
        if r.returncode != 0 or not os.path.exists(tmp) or pages(tmp) != pages(src) or q not in (0, 3):
            err = (r.stderr.strip().splitlines() or [f"rc={r.returncode}"])[-1] if r.returncode else f"gate: pages {pages(src)}->{pages(tmp) if os.path.exists(tmp) else '-'} qpdf {q}"
            if os.path.exists(tmp):
                os.remove(tmp)
            return rel, "fail", time.time() - t0, pages(src), 0, err
        os.rename(tmp, src)  # atomic; backup already holds the original
        n = text_chars(src) or 0
        status = "ok" if n > MIN_TEXT else "fail-empty"
        return rel, status, time.time() - t0, pages(src), n, "" if status == "ok" else "chars<=200 after OCR"
    except Exception as e:  # never crash the batch
        for t in (tmp, norm):
            if os.path.exists(t):
                os.remove(t)
        return rel, "fail", time.time() - t0, -1, 0, repr(e).splitlines()[-1]


def run(workers, limit, listfile=None, force=False, redo=False):
    os.makedirs(DONE, exist_ok=True)
    if force:  # rerun for fail-empty files: rasterize + OCR every page, ignore done markers
        # --force-ocr re-encodes every page as a 300 dpi raster: 10-28x bloat at r14 (743 MB magazine).
        # Run shrink_ocr.sh over anything that grew >4x afterwards (gs /ebook, text layer kept).
        OCR[1:2] = ["--force-ocr", "--oversample", "300"]
    todo = [r for r in open(listfile or os.path.join(RES, "needs_ocr.txt")).read().splitlines()
            if r and (force or redo or not os.path.exists(key(r)))]
    if limit:
        todo = todo[:limit]
    print(f"todo={len(todo)} workers={workers}", flush=True)
    res = open(os.path.join(RES, "results.tsv"), "a")
    fails = open(os.path.join(RES, "failures.tsv"), "a")
    n = 0
    with ThreadPoolExecutor(workers) as ex:
        for fut in as_completed([ex.submit(ocr_one, r) for r in todo]):
            rel, status, secs, pg, chars, err = fut.result()
            res.write(f"{rel}\t{status}\t{secs:.1f}\t{pg}\t{chars}\n"); res.flush()
            if status != "ok":
                fails.write(f"{rel}\t{status}\t{err}\n"); fails.flush()
            if status in ("ok", "fail-empty"):  # file was rewritten; don't redo
                open(key(rel), "w").close()
            n += 1
            print(f"{n}/{len(todo)} {status} {secs:.0f}s {pg}p {rel}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--enum", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--list", help="path list instead of needs_ocr.txt")
    ap.add_argument("--force", action="store_true", help="--force-ocr --oversample 300, ignore done markers")
    ap.add_argument("--redo", action="store_true", help="ignore done markers, keep --skip-text")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--mixed", action="store_true", help="then --redo-ocr the pages still without text")
    ap.add_argument("--lang", help="tesseract languages (default eng+spa)")
    ap.add_argument("--bak", help="backup root for originals (default docs_ocr_bak_20260925)")
    a = ap.parse_args()
    if a.lang:
        OCR[OCR.index("-l") + 1] = OCR_REDO[OCR_REDO.index("-l") + 1] = a.lang
    MIXED = a.mixed
    if a.bak:
        BAK = a.bak
    if a.selftest:
        selftest()
    if a.enum:
        enum(a.workers)
    if a.run:
        run(a.workers, a.limit, a.list, a.force, a.redo)
