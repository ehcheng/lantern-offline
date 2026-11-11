#!/usr/bin/env python3
"""T1 per-file format checker. stdin: paths (library/...), one per line.
stdout: t1,<ext>,<path>,PASS|FAIL|SKIP,<detail>. One process handles a batch."""
import sys, os, re, io, json, csv, zipfile, sqlite3, subprocess, urllib.request, urllib.parse, struct, hashlib, gzip, glob
from xml.etree import ElementTree
from html.parser import HTMLParser

LIB = "library"
KIWIX = os.environ.get("KIWIX", "http://127.0.0.1:8080")
TMP = os.environ.get("TMPDIR", "/tmp")

def run(*cmd, timeout=120):
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=timeout)
    return p.returncode, p.stdout, p.stderr

def ext_of(p):
    base = os.path.basename(p).split("?")[0]
    e = base.rsplit(".", 1)[-1].lower() if "." in base else ""
    if re.fullmatch(r"\d{3}", e): return "enc"
    return e

def head(p, n=64):
    with open(p, "rb") as f: return f.read(n)
def tail(p, n=2048):
    with open(p, "rb") as f:
        f.seek(max(0, os.path.getsize(p) - n)); return f.read()
def nonempty_not_html(p, what):
    h = head(p, 512)
    if not h: raise Exception("0 bytes")
    # anchored: an error page starts with the tag; app.js names <html lang="es"> in a comment (r31 false FAIL)
    if re.match(rb"(?:\xef\xbb\xbf)?\s*(?:<!--.*?-->\s*)*(?:<!doctype html|<html)", h, re.I | re.S): raise Exception("HTML where %s expected (saved error page?)" % what)
    return h

IMAGE_ONLY_TSV = os.path.join("logs", "audit", "fix81_imageonly_pages.tsv")
IMAGE_ONLY_1_10 = set()
if os.path.exists(IMAGE_ONLY_TSV):
    for _r in csv.DictReader((l for l in open(IMAGE_ONLY_TSV) if not l.startswith("#")), delimiter="\t"):
        if _r.get("all_1_10_image_only") == "yes": IMAGE_ONLY_1_10.add(_r["path"])

# ---- checkers: return detail on PASS, raise on FAIL, return ("SKIP", why) to skip
def c_pdf(p):
    # a truncated PDF must FAIL: %%EOF trailer present, pdfinfo page count, qpdf structure, and the LAST
    # pages readable (text PDFs: pdftotext of the last 3 pages non-empty; image PDFs: pdftoppm renders the last page)
    if b"%%EOF" not in tail(p, 2048): raise Exception("no %%EOF in last 2 KB (truncated?)")
    rc, out, err = run("pdfinfo", p)
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    if rc or not m or int(m.group(1)) < 1: raise Exception("pdfinfo: " + (err.strip().splitlines() or ["no pages"])[0][:120])
    pages = int(m.group(1))
    rc, out, err = run("qpdf", "--check", p, timeout=600)   # 0 clean, 3 warnings (old scans), 2 errors
    if rc not in (0, 3): raise Exception("qpdf rc=%d %s" % (rc, (err.strip().splitlines() or [""])[-1][:120]))
    qw = " qpdf=warn" if rc == 3 else ""
    try:
        rc, first, err = run("pdftotext", "-l", "10", p, "-")
        rc, last, err = run("pdftotext", "-f", str(max(1, pages - 2)), "-l", str(pages), p, "-")
    except subprocess.TimeoutExpired:   # USGS GeoPDF topo quads: pdftotext grinds for minutes on the vector layers; the render check below still runs
        first = last = ""
    wrapper = os.path.join(LIB, "_app", "text", os.path.relpath(p, LIB) + ".c1.html")   # E2: drawings carry a vision description
    figure_only = not first.strip() and os.path.exists(wrapper) and b"Figure-only document" in open(wrapper, "rb").read(4096)
    if not first.strip() and p.startswith(LIB + "/docs/") and not figure_only:
        # FIXES #81: books whose pages 1-10 were checked by eye and hold no printed text (covers, plates, drawings)
        # pass when the text layer starts later; any other textless opening still FAILs
        if p not in IMAGE_ONLY_1_10: raise Exception("no text on pages 1-10")
        rc, later, err = run("pdftotext", "-f", "11", "-l", str(min(pages, 60)), p, "-")
        if not later.strip(): raise Exception("no text on pages 1-10 (listed image-only) nor on 11-60")
        first = later
    kind = "text" if first.strip() else "image, figure-only (vision description indexed)" if figure_only else "image"
    if first.strip() and last.strip(): return "pages=%d text%s" % (pages, qw)
    # no text on the last pages (image PDF, or a scan whose back cover has no OCR layer): the last page must still render
    out_prefix = os.path.join(TMP, "fmt_%d_%d" % (os.getpid(), pages))
    rc, out, err = run("pdftoppm", "-f", str(pages), "-l", str(pages), "-r", "10", "-png", p, out_prefix, timeout=300)
    pngs = glob.glob(out_prefix + "*.png"); ok = any(os.path.getsize(x) > 0 for x in pngs)
    for x in pngs: os.unlink(x)
    if rc or not ok: raise Exception("last page does not render (truncated?): " + (err.strip().splitlines() or ["no output"])[0][:120])
    return "pages=%d %s, last page rendered%s" % (pages, kind, qw)

def c_img(p):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(p) as im: im.verify()
    with Image.open(p) as im: im.load(); return "%dx%d" % im.size

def c_media(p):
    rc, out, err = run("ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", p)
    if rc: raise Exception("ffprobe: " + (err.strip().splitlines() or [""])[0][:120])
    d = json.loads(out)
    dur = float(d.get("format", {}).get("duration", 0) or 0)
    if dur <= 0: raise Exception("duration 0")
    codecs = [s.get("codec_name") for s in d["streams"]]
    v = [s for s in d["streams"] if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")]  # mp3 cover art is a 1-packet "video"
    a = [s for s in d["streams"] if s["codec_type"] == "audio"]
    if p.endswith(".mp4"):
        if not v or v[0]["codec_name"] != "h264": raise Exception("video codec %s" % (v[0]["codec_name"] if v else None))
        if a and a[0]["codec_name"] != "aac": raise Exception("audio codec %s" % a[0]["codec_name"])
    note = ""
    for s in v + a:   # every audio/video stream's own duration within 2% of the container's (subtitle/data streams end early by design)
        sd = float(s.get("duration") or 0)
        if sd > 0 and abs(sd - dur) > 0.02 * dur + 0.5:
            if s["codec_type"] == "audio": note = " audio ends at %.0fs of %.0fs" % (sd, dur); continue   # 13 kolibri lessons: silent tail, plays fine; truncation is the packet demux below
            raise Exception("%s stream dur %.1f vs container %.1f" % (s["codec_type"], sd, dur))
    # demux every packet of the primary stream (no decode): a truncated file stops early
    prim = v[0] if v else (a[0] if a else None)
    if prim is None: raise Exception("no audio/video stream")
    sel = "v:0" if v else "a:0"
    rc, out, err = run("ffprobe", "-v", "error", "-select_streams", sel, "-show_entries", "packet=pts_time", "-of", "csv=p=0", p, timeout=900)
    if rc or err.strip(): raise Exception("packets: " + (err.strip().splitlines() or ["rc=%d" % rc])[0][:120])
    pts = [float(x.strip(", ")) for x in out.split() if x.strip(", ") not in ("", "N/A")]
    if not pts: raise Exception("0 packets")
    last = max(pts)
    if last < 0.98 * dur - 0.5: raise Exception("last packet at %.1fs of %.1fs (truncated?)" % (last, dur))
    nb = int(prim.get("nb_frames") or 0) if v else 0   # audio nb_frames counts samples, not packets
    if nb and len(pts) < 0.98 * nb: raise Exception("packets %d/%d (truncated?)" % (len(pts), nb))
    return "dur=%.0f pkts=%d %s" % (dur, len(pts), "+".join(map(str, codecs))) + note

TS = re.compile(r"(\d+):(\d\d):(\d\d)\.(\d{3})|(\d\d):(\d\d)\.(\d{3})")
def c_vtt(p):
    txt = open(p, encoding="utf-8-sig", errors="strict").read()
    if not txt.startswith("WEBVTT"): raise Exception("no WEBVTT header")
    cues, last, unordered = 0, -1.0, 0   # out-of-order cues (137 kolibri captions) play fine; count them, do not fail
    for line in txt.splitlines():
        if "-->" not in line: continue
        a, b = line.split("-->")[:2]
        def sec(s):
            m = TS.search(s)
            if not m: raise Exception("bad timestamp " + s.strip()[:20])
            g = m.groups()
            return (int(g[0])*3600+int(g[1])*60+int(g[2])+int(g[3])/1000) if g[0] else (int(g[4])*60+int(g[5])+int(g[6])/1000)
        s, e = sec(a), sec(b)
        if s < last - 0.001: unordered += 1
        last = max(last, s); cues += 1
    if cues == 0: raise Exception("0 cues")
    return "cues=%d" % cues + (", %d out of order" % unordered if unordered else "")

class HP(HTMLParser):
    def __init__(s): super().__init__(); s.refs = []; s.text = 0; s.body = False
    def handle_starttag(s, tag, attrs):
        if tag == "body": s.body = True
        for k, v in attrs:
            if k in ("href", "src") and v: s.refs.append(v)
    def handle_data(s, d): s.text += len(d.strip())
def c_html(p):
    txt = open(p, encoding="utf-8", errors="replace").read()
    h = HP(); h.feed(txt)
    if h.text == 0 and "<body" in txt.lower():
        if re.search(r'http-equiv="refresh"', txt, re.I): return ("SKIP", "meta-refresh stub (offline dead-end)")
        raise Exception("empty body")
    import urllib.parse
    missing, n = [], 0
    for r in h.refs:
        r = r.strip()
        if r.startswith(("http:", "https:", "//", "mailto:", "javascript:", "data:", "#", "tel:")) or "${" in r or "{{" in r: continue
        path = urllib.parse.unquote(r.split("#")[0].split("?")[0])
        if not path or re.search(r"(^|/)(discs/|image-release\.txt$|mcp$|semantic$|stt$)", path): continue  # box-only routes (nginx alias/proxy)
        tgt = os.path.normpath(os.path.join(LIB, path.lstrip("/")) if path.startswith("/") else os.path.join(os.path.dirname(p), path))
        n += 1
        if not os.path.exists(tgt): missing.append(path)
    pages = [m for m in missing if re.search(r"\.(html?|pdf)$", m.split("?")[0], re.I) or m.endswith("/")]
    if p.startswith((LIB + "/mirrors/", LIB + "/kolibri_data/")) and missing:
        return "refs=%d, %d refs missing (%d page links; upstream dead links, not mirrored)" % (n, len(missing), len(pages))
    if missing: raise Exception("%d/%d missing refs (%d page links) e.g. %s" % (len(missing), n, len(pages), (pages or missing)[0][:80]))
    return "refs=%d" % n

def c_text(p):
    if p.startswith(LIB + "/maps/noaa_charts/enc/"):
        open(p, encoding="latin-1").read(); return ("SKIP", "ENC catalog txt, latin-1 by spec")
    open(p, encoding="utf-8", errors="strict").read(); return "utf8"
def c_csv(p):
    rows = list(csv.reader(open(p, encoding="utf-8", errors="strict", newline="")))
    widths = {len(r) for r in rows if r}
    if len(widths) > 1: raise Exception("ragged columns %s" % sorted(widths)[:5])
    return "rows=%d cols=%s" % (len(rows), widths.pop() if widths else 0)
def c_zip(p):
    with zipfile.ZipFile(p) as z:
        bad = z.testzip()
        if bad: raise Exception("corrupt member " + bad)
        return "members=%d" % len(z.namelist())
def c_sqlite(p):
    r = sqlite3.connect("file:%s?mode=ro" % p, uri=True).execute("PRAGMA integrity_check").fetchone()[0]
    if r != "ok": raise Exception(r[:120])
    return "ok"
def c_zim(p):
    h = head(p, 80)
    if h[:4] != b"\x5a\x49\x4d\x04": raise Exception("bad magic")
    size = os.path.getsize(p); cpos = struct.unpack("<Q", h[72:80])[0]
    if cpos != size - 16: raise Exception("checksumPos %d != size-16 %d (truncated?)" % (cpos, size - 16))
    m = hashlib.md5(); left = cpos
    with open(p, "rb") as f:
        while left > 0:
            b = f.read(min(1 << 24, left)); m.update(b); left -= len(b)
        if m.digest() != f.read(16): raise Exception("embedded MD5 mismatch")
    name = os.path.basename(p)[:-4]
    try:
        cat = urllib.request.urlopen(KIWIX + "/catalog/v2/entries?count=-1", timeout=10).read().decode()
    except Exception as e:
        raise Exception("kiwix %s unreachable (%s); start it, a ZIM is not verified until it serves" % (KIWIX, str(e)[:60]))
    book = name if name in cat else name.rsplit("_", 1)[0]
    if book not in cat: raise Exception("not in kiwix catalog")
    ok = 0
    for _ in range(25):
        try:
            u = KIWIX + "/random?content=" + urllib.parse.quote(book)
            r = urllib.request.urlopen(u, timeout=30)
            if r.status == 200 and len(r.read()) > 0: ok += 1
        except Exception: pass
    if ok < 20: raise Exception("random articles ok=%d/25" % ok)
    return "md5 ok catalog ok random=%d/25" % ok
def c_iso(p):
    rc, out, err = run("hdiutil", "attach", "-readonly", "-nobrowse", "-noverify", "-mountrandom", os.environ.get("TMPDIR", "/tmp"), p, timeout=300)
    if rc: raise Exception("hdiutil: " + err.strip()[:120])
    mp = out.strip().splitlines()[-1].split("\t")[-1].strip()
    try:
        n = sum(len(f) for _, _, f in os.walk(mp))
    finally:
        run("hdiutil", "detach", mp, "-force")
    if n == 0: raise Exception("0 files")
    return "files=%d" % n
def c_enc(p):
    h = head(p, 12)
    if not (h[:5].isdigit() and h[5:9] == b"3LE1"): raise Exception("no ISO 8211 leader: %r" % h[:9])
    return "iso8211"
def c_bsb(p):
    h = head(p, 4096)
    if not (h.startswith(b"!") or h.startswith(b"VER/")): raise Exception("bad header")
    if b"BSB/NA=" not in h and b"NA=" not in h: raise Exception("no BSB/NA")
    return "bsb"
def c_mwm(p):
    if b"MWM" not in head(p, 16): raise Exception("no MWM magic")
    if os.path.getsize(p) < 1_000_000: raise Exception("size < 1 MB")
    return "mwm"
def c_pmtiles(p):
    h = head(p, 8)
    if h[:7] != b"PMTiles" or h[7] != 3: raise Exception("bad magic/version")
    return "pmtiles v3"
def c_pbf(p):
    h = head(p, 2)
    if h[:2] == b"\x1f\x8b":
        import gzip; gzip.open(p).read(1); return "gzip"
    if h and h[0] & 7 in (0, 2): return "protobuf"
    raise Exception("not protobuf/gzip")
def c_json(p): json.load(open(p, encoding="utf-8")); return "json"
def c_xml(p): ElementTree.parse(p); return "xml"
MAGIC = {"gguf": b"GGUF", "apk": b"PK\x03\x04", "dmg": None, "exe": b"MZ", "pkg": b"xar!", "appimage": b"\x7fELF", "so": b"\x7fELF", "ort": None}
def c_bin(p):
    e = ext_of(p); m = MAGIC.get(e)
    h = head(p, 8)
    if m and h[:len(m)] != m: raise Exception("bad magic %r" % h[:4])
    if e == "dmg":
        with open(p, "rb") as f: f.seek(-512, 2); k = f.read(4)
        if k != b"koly": raise Exception("no koly trailer")
    if e == "ort" and h[4:8] != b"ORTM": raise Exception("no ORTM magic")
    sums = os.path.join(os.path.dirname(p), "SHA256SUMS")
    if os.path.exists(sums):
        want = {l.split()[1].lstrip("*"): l.split()[0] for l in open(sums) if l.strip() and not l.startswith("#")}
        if os.path.basename(p) in want:
            rc, out, _ = run("shasum", "-a", "256", p, timeout=1800)
            if out.split()[0] != want[os.path.basename(p)]: raise Exception("sha256 != SHA256SUMS")
            return "magic+sha ok"
    return "magic ok"

GGUF_T = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<B", 10: "<Q", 11: "<q", 12: "<d"}
def gguf_meta(p):
    """Parse the GGUF header + every metadata kv (spec: magic, version, tensor count, kv count, kv pairs)."""
    with open(p, "rb") as f:
        def rd(fmt): return struct.unpack(fmt, f.read(struct.calcsize(fmt)))[0]
        def rstr():
            n = rd("<Q")
            if n > 1 << 24: raise Exception("gguf string len %d" % n)
            return f.read(n).decode("utf-8", "replace")
        def rval(t):
            if t == 8: return rstr()
            if t == 9:
                et, n = rd("<I"), rd("<Q")
                if n > 1 << 28: raise Exception("gguf array len %d" % n)
                for _ in range(n): rval(et)
                return "array[%d]" % n
            if t not in GGUF_T: raise Exception("gguf kv type %d" % t)
            return rd(GGUF_T[t])
        if f.read(4) != b"GGUF": raise Exception("bad magic")
        ver = rd("<I")
        if ver not in (2, 3): raise Exception("gguf version %d" % ver)
        n_t, n_kv = rd("<Q"), rd("<Q")
        if n_t == 0 or n_t > 1 << 20 or n_kv > 1 << 16: raise Exception("gguf counts tensors=%d kv=%d" % (n_t, n_kv))
        meta = {}
        for _ in range(n_kv):
            k = rstr(); meta[k] = rval(rd("<I"))
        far = 0   # tensor infos: name, n_dims, dims, type, offset (relative to the aligned data start)
        for _ in range(n_t):
            rstr(); nd = rd("<I")
            if nd > 8: raise Exception("gguf tensor n_dims %d" % nd)
            for _ in range(nd): rd("<Q")
            rd("<I"); far = max(far, rd("<Q"))
        align = meta.get("general.alignment", 32); start = -(-f.tell() // align) * align
    if "general.architecture" not in meta: raise Exception("gguf: no general.architecture")
    if os.path.getsize(p) <= start + far: raise Exception("gguf file ends before the last tensor (truncated?)")
    return ver, n_t, meta
def c_gguf(p):
    ver, n_t, meta = gguf_meta(p)
    arch = meta["general.architecture"]
    d = "gguf v%d tensors=%d arch=%s" % (ver, n_t, arch)
    if "/tools/models/" in p and arch == "llama":   # the llamafile chat models: load once, one prompt
        bins = sorted(glob.glob(LIB + "/tools/llamafile/llamafile-*"))
        if not bins: raise Exception(d + "; no llamafile binary to load it with")
        rc, out, err = run("/bin/sh", bins[-1], "-m", p, "--cli", "-p", "Reply with the single word OK.", "-n", "8", "--temp", "0", "--no-display-prompt", timeout=1800)
        if rc or not out.strip(): raise Exception(d + "; llamafile rc=%d %s" % (rc, (err.strip().splitlines() or [""])[-1][:100]))
        d += "; llamafile reply=%r" % out.strip()[:40]
    return d
def c_onnx(p):
    h = head(p, 16)
    if h[:1] != b"\x08": raise Exception("not an ONNX ModelProto (first field must be ir_version)")
    cfg = p + ".json"
    if os.path.exists(cfg): json.load(open(cfg, encoding="utf-8")); return "onnx + voice config json"
    return "onnx"
def c_gz(p):
    with gzip.open(p) as g:
        n = 0
        while True:
            b = g.read(1 << 20)
            if not b: break
            n += len(b)
    if n == 0: raise Exception("empty after gunzip")
    return "gzip ok %d bytes" % n
def c_pf_fragment(p):
    d = gzip.open(p).read()
    j = json.loads(d[d.index(b"{"):])
    if not j.get("url") or not j.get("content"): raise Exception("fragment without url/content")
    return "pagefind fragment %s" % j["url"][:60]
FONT_MAGIC = {"woff2": (b"wOF2",), "woff": (b"wOFF", b"wOF2"), "ttf": (b"\x00\x01\x00\x00", b"true", b"ttcf"), "otf": (b"OTTO", b"\x00\x01\x00\x00")}
def c_font(p):
    e = ext_of(p); h = head(p, 40)
    if e == "eot":
        if h[34:36] != b"LP": raise Exception("no EOT magic at 34")
    elif not h.startswith(FONT_MAGIC[e]): raise Exception("bad %s magic %r" % (e, h[:4]))
    return e
def c_code(p):
    nonempty_not_html(p, ext_of(p))
    open(p, encoding="utf-8", errors="strict").read(); return "utf8 " + ext_of(p)
def c_md5(p):
    t = open(p, encoding="ascii").read()
    if not re.match(r"^[0-9a-fA-F]{32}\b", t): raise Exception("no md5 hex")
    return "md5 text"
def c_ole(p):
    if head(p, 8) != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": raise Exception("not OLE2")
    return "ole2"
def c_sniff(p):
    """No extension-specific validator: identify by magic and run that check; opaque data must be non-empty and not HTML."""
    if p.startswith(LIB + "/mirrors/") and re.search(rb"<!doctype html|<html", head(p, 512), re.I):
        return "sniff " + c_html(p)   # wget saves php / extensionless pages as HTML
    h = nonempty_not_html(p, "data")
    if h[:2] == b"\x1f\x8b": return "sniff " + c_gz(p)
    if h[:4] == b"PK\x03\x04": return "sniff " + c_zip(p)
    if h[:4] == b"%PDF": return "sniff " + c_pdf(p)
    if h[:15] == b"SQLite format 3": return "sniff sqlite " + c_sqlite(p)
    if h[:4] == b"\x7fELF" or h[:2] == b"MZ": return "sniff elf/pe/ape nonempty"
    if h[:5] == b"<?xml": return "sniff " + c_xml(p)
    if h[:7] == b"StuffIt": return "sniff stuffit"
    if h[:7] == b"DAF/SPK": return "sniff naif spk"
    if h[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": return "sniff ole2"
    if h[:1] in (b"{", b"["):
        json.load(open(p, encoding="utf-8")); return "sniff json"
    try:
        open(p, encoding="utf-8", errors="strict").read(); return "sniff utf8 text"
    except UnicodeDecodeError:
        return "sniff opaque binary, nonempty, not html"

CHECK = {"pdf": c_pdf, "jpg": c_img, "jpeg": c_img, "jfif": c_img, "png": c_img, "gif": c_img, "webp": c_img, "tif": c_img, "tiff": c_img, "ico": c_img,
         "mp4": c_media, "mp3": c_media, "mov": c_media, "mpg": c_media, "vtt": c_vtt, "html": c_html, "htm": c_html,
         "txt": c_text, "md": c_text, "sh": c_text, "ini": c_text, "data_version": c_text, "csv": c_csv,
         "zip": c_zip, "h5p": c_zip, "perseus": c_zip, "whl": c_zip, "docx": c_zip, "argosmodel": c_zip, "xls": c_ole,
         "sqlite3": c_sqlite, "db": c_sqlite, "zim": c_zim, "iso": c_iso, "enc": c_enc, "kap": c_bsb, "bsb": c_bsb,
         "mwm": c_mwm, "pmtiles": c_pmtiles, "pbf": c_pbf, "json": c_json, "oembed": c_json, "svg": c_xml, "xml": c_xml,
         "gguf": c_gguf, "onnx": c_onnx, "ort": c_bin, "so": c_bin, "apk": c_bin, "dmg": c_bin, "exe": c_bin, "pkg": c_bin, "appimage": c_bin,
         "gz": c_gz, "pf_index": c_gz, "pf_meta": c_gz, "pf_filter": c_gz, "pagefind": c_gz, "pf_fragment": c_pf_fragment,
         "css": c_code, "js": c_code, "mjs": c_code, "woff2": c_font, "woff": c_font, "ttf": c_font, "otf": c_font, "eot": c_font,
         "md5": c_md5}

def main():
    w = csv.writer(sys.stdout, lineterminator="\n")
    for p in sys.stdin:
        p = p.rstrip("\n")
        if not p: continue
        e = ext_of(p); fn = CHECK.get(e, c_sniff)
        try:
            if not os.path.exists(p): raise Exception("missing on disk")
            if os.path.basename(p).startswith("."): w.writerow(["t1", e or "noext", p, "SKIP", "dot marker"]); continue
            if os.path.getsize(p) == 0: raise Exception("0 bytes")
            d = fn(p)
            if isinstance(d, tuple): w.writerow(["t1", e or "noext", p, d[0], d[1]]); continue
            w.writerow(["t1", e or "noext", p, "PASS", d])
        except Exception as ex:
            w.writerow(["t1", e or "noext", p, "FAIL", str(ex).replace("\n", " ")[:200]])
        sys.stdout.flush()

if __name__ == "__main__":
    if len(sys.argv) > 1:  # self-check: python3 fmt.py <path...>
        sys.stdin = io.StringIO("\n".join(sys.argv[1:]) + "\n")
    main()
