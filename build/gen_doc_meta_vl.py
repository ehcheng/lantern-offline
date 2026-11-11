#!/usr/bin/env python3
"""Title + one-line summary for IMAGE-ONLY PDFs (no OCR text) via a Qwen VL
model on local Ollama: first 3 pages -> PNG -> /api/chat with images.
Same JSON contract as gen_doc_meta.PROMPT. r21: fills only MISSING keys ("t" absent, "s" empty), never rewrites an
entry (a/y/l survive), and writes "s" in the entry's language "l" (#132). Review table: <LISTFILE>_review.md.
Usage: python3 gen_doc_meta_vl.py LISTFILE [--limit N] [model]
"""
import base64, glob, json, os, re, subprocess, sys, tempfile, time, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from gen_text import LIB, extract
from gen_index import humanize
from gen_doc_meta import OUT, PROMPT

URL = "http://127.0.0.1:11434"
LIST = sys.argv[1]
LIMIT = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
MODEL = next((a for a in sys.argv[2:] if not a.startswith("--") and not a.isdigit()), "qwen3-vl:32b-instruct")
REVIEW = os.path.splitext(LIST)[0] + "_review.md"
PAGES = 3


def pages_png(pdf, tmp, first=1):
    subprocess.run(["pdftoppm", "-r", "80", "-png", "-f", str(first), "-l", str(first + PAGES - 1), pdf, os.path.join(tmp, "p")],
                   check=True, capture_output=True, timeout=300)
    return [base64.b64encode(open(f, "rb").read()).decode() for f in sorted(glob.glob(os.path.join(tmp, "p*.png")))]


def ask(stem, shelf, imgs, langname="English", note=""):
    prompt = (PROMPT.format(stem=stem, shelf=shelf, head="(attached: scans of the first pages)", tail="")
              + "\nThe images are the FIRST pages of a longer document. Describe the DOCUMENT as a whole "
                "(what it teaches or documents, for whom), not the pictures on these pages. If the cover shows "
                "a title, use it; if these pages are only a photo, map or drawing, name the subject the "
                "document is about."
              + f"\nWrite the summary in {langname}." + ("" if langname == "English" else f" End the title with ({langname}).") + note)
    # r21: num_predict 200 cut 5 Bengali answers mid-string ("Unterminated string"); Bengali costs ~4x the tokens.
    # More room, one retry, then salvage the fields from the raw text.
    for temp, n in ((0.1, 700), (0.3, 1200)):
        req = urllib.request.Request(f"{URL}/api/chat", data=json.dumps({
            "model": MODEL, "stream": False, "format": "json",
            "messages": [{"role": "user", "content": prompt, "images": imgs}],
            "options": {"temperature": temp, "num_predict": n}}).encode(),
            headers={"Content-Type": "application/json"})
        r = json.load(urllib.request.urlopen(req, timeout=900))["message"]["content"]
        try:
            j = json.loads(r)
            return str(j.get("title", "")).strip().strip('"'), str(j.get("summary", "")).strip().split("\n")[0]
        except ValueError:
            pass
    field = lambda k: (re.search(r'"%s"\s*:\s*"((?:[^"\\]|\\.)+)' % k, r) or [None, ""])[1]
    if not field("summary"):
        raise ValueError("no summary in VL reply: " + r[:80])
    return field("title").strip(), field("summary").strip()


def main():
    import gen_doc_answers as A
    from gen_doc_answers import LANG_NAME, skip_google
    have = json.load(open(OUT))
    todo = [l.strip() for l in open(LIST) if l.strip()]
    todo = [r for r in todo if "t" not in have.get(r, {}) or not have.get(r, {}).get("s")]   # per key: only what is missing
    if LIMIT:
        todo = todo[:LIMIT]
    rows, t0 = [], time.time()
    print(f"model={MODEL} todo={len(todo)}", flush=True)
    for i, rel in enumerate(todo, 1):
        pdf = os.path.join(LIB, rel)
        stem = humanize(os.path.basename(rel))
        shelf = rel.split("/")[1] if rel.startswith("docs/") else rel.split("/")[0]
        e = have.setdefault(rel, {"src": "vl"})
        try:
            text = extract(pdf, rel) or ""
        except Exception:
            text = ""
        first = 1 + len(text.split("\f")) - len(skip_google(text).split("\f")) if text else 1   # r21: skip Google's notice pages
        try:
            with tempfile.TemporaryDirectory() as tmp:
                imgs, ln = pages_png(pdf, tmp, first), LANG_NAME.get(e.get("l"), "English")
                t, s = ask(stem, shelf, imgs, ln)
                s = A.fit_s(s, lambda note: ask(stem, shelf, imgs, ln, note)[1], e.get("l", ""))   # #135: no "…" cut
        except Exception as ex:
            print(f"FAIL {rel}: {ex}", file=sys.stderr, flush=True)
            continue
        if "t" not in e:
            e["t"] = t or stem
        if rel.startswith(A.OLD_SHELVES) and A.audience_bad(rel, e.get("t", t), s):   # #125, as in gen_doc_meta
            s = A.aud_cut(s)
        if not e.get("s"):
            e["s"] = s; e["src"] = "vl"
        rows.append((rel, stem, e["t"], e["s"]))
        json.dump(have, open(OUT + ".tmp", "w"), indent=1, ensure_ascii=False, sort_keys=True)
        os.replace(OUT + ".tmp", OUT)
        print(f"{i}/{len(todo)} {time.time()-t0:.0f}s {rel} -> {e.get('l')} {e['s'][:70]!r}", flush=True)
    with open(REVIEW, "w") as f:
        f.write(f"# Image-only PDFs: Qwen VL titles/summaries ({MODEL}, {time.strftime('%Y-%m-%d')})\n\n"
                f"{len(rows)} of {len(todo)} done. Old title = tidied filename.\n\n"
                "| file | old title | title | summary |\n|---|---|---|---|\n")
        for rel, old, t, s in rows:
            f.write(f"| `{rel.split('/')[-1]}` | {old} | {t} | {s} |\n")
    print(f"DONE {len(rows)}/{len(todo)} {time.time()-t0:.0f}s -> {REVIEW}")


if __name__ == "__main__":
    main()
