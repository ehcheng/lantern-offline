#!/usr/bin/env python3
"""A6: pdftotext tree -> per-doc HTML wrappers for Pagefind.

Walks the Pagefind whitelist dirs (BUILD_PLAN A6), extracts text per PDF,
writes library/_app/text/<relpath>.<chunk>.html — CHUNK_PAGES PDF pages per
wrapper (one giant wrapper per book made Pagefind data() take 5-15s; small
fragments keep search snappy) with one <h2 id="pN"> per PDF page (Pagefind
sub-results anchor there; search.html maps to reader.html?p=N).
Skips zero-text PDFs (scanned). Idempotent: skips up-to-date wrappers.
"""
import glob, hashlib
import html
import json
import os
import re
import subprocess
import sys
from urllib.parse import quote

LIB = os.path.join(os.path.dirname(__file__), "..", "library")
LIB = os.path.abspath(LIB)
OUT = os.path.join(LIB, "_app", "text")

WHITELIST = [
    "docs/medical", "docs/water", "docs/sanitation", "docs/energy",
    "docs/food_preservation", "docs/homesteading_extension",
    "docs/foraging_coastal", "docs/fire_safety", "docs/shelter",
    "docs/comms", "docs/navigation", "docs/emergency_mgmt", "docs/nuclear",
    "docs/grain_processing", "docs/textiles", "docs/security", "docs/death_care",
    "docs/military_manuals",  # ponytail: second copy of gen_index.SHELVES; keep in sync
    "mirrors/hesperian", "mirrors/nchfp", "mirrors/ready_gov",
    "docs/survivor_library", "docs/cd3wd", "docs/HISTORICAL",  # H37c, historical-gated
    "docs/school_textbooks",
]
# same prefixes as search.html HIST_PREFIX / shelves.json historical flags
from gen_index import HIST_PATHS as HISTORICAL, DEV_PREFIX  # one source for the historical gate
DEV_CHARS = 3000  # unused here; pf_dev_stage.py owns the dev-index cut (English CD3WD: one 3,000-char record; other languages: every page, #116)
CURATED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "docs.curated.json")

# FIXES #111: duplicate copies kept on their shelves but indexed once (canonical copy only)
NONCANON = {l.strip() for l in open(os.path.join(os.path.dirname(CURATED), "noncanonical_paths.txt"))
            if l.strip() and not l.startswith("#")} if os.path.exists(os.path.join(os.path.dirname(CURATED), "noncanonical_paths.txt")) else set()
MIN_TEXT = 200  # chars across whole doc; below = no text layer, skip
FORCE = "--force" in sys.argv  # rewrite every wrapper (wrap() changed: lang, summary meta) even when the PDF is older
CHUNK_PAGES = 25
HIST_CHUNK_PAGES = 100  # ~2.3M historical pages: 4x fewer wrapper files (bytes are text-bound either way)
# H37c: pdftotext cache so a rebuild only re-extracts changed PDFs.
# ponytail: key = sha1(relpath+size+mtime), not content — 114 GB is too big to hash.
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache", "pdftext")


def titles_map():
    with open(os.path.join(LIB, "_app", "index", "titles.json")) as f:
        v = json.load(f)
    if isinstance(v, dict):  # dir-prefix packed (gen_index A7)
        return {v["d"][it[0]] + it[1]: it[2] for it in v["i"]}
    return {it["p"]: it["t"] for it in v}


# round 10 (#273, b5 F-D4 F-D8): markup that pdftotext copies out of a PDF text layer (Webster's "<ets>", "<def>",
# "<Xpage=1088>") and control characters (a U+0007 in NWTND ch.3 p.39; C1 controls in font-garbled pages), each control a
# space so words stay apart. The form feed \x0c is the page break and stays. Applied on the way out, so the cache keeps
# pdftotext's own output. Same two patterns as PDF_TAG_RE / CTRL_RE in server/mcp_server.py page_excerpt().
# r39 acceptance: an open fragment needs 2+ letters and a tag right after "<" stays, so "0.1<x<16 MPa", "(0<r<1)" and the MSF
# survey's "<<t>>" keep their variables (Webster's output unchanged but for 4 chars). The pagefind_dev word count fell
# 1,707,585 -> 1,175,382 at r39 from this cleaning, ~385k of it Webster's markup tokens: intended.
# ponytail: tag-shaped text is still dropped ("pulsar la tecla <Enter>", HTML/XML samples in computing textbooks, ~1k rows);
# a per-document markup flag is the upgrade if a reviewer needs those words.
PDF_TAG_RE = re.compile(r"(?<!<)</?[A-Za-z][A-Za-z0-9]*(?:=[^<>\s]{0,12})?>|<\?/|</[a-z]{1,8}(?=\n|<|$)|<[a-z]{2,8}(?=<)")  # + cut fragments
CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0e-\x1f\x7f-\x9f]")


def clean(text):
    return CTRL_RE.sub(" ", PDF_TAG_RE.sub("", text))


def extract(pdf, rel):
    st = os.stat(pdf)
    key = hashlib.sha1(f"{rel}|{st.st_size}|{int(st.st_mtime)}".encode()).hexdigest()
    cpath = os.path.join(CACHE, key + ".txt")
    if os.path.exists(cpath):
        with open(cpath, encoding="utf-8") as f:
            return clean(f.read())
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", pdf, "-"],
                       capture_output=True, timeout=300)
    if r.returncode != 0:
        return None
    text = r.stdout.decode("utf-8", "replace")
    os.makedirs(CACHE, exist_ok=True)
    with open(cpath + ".tmp", "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(cpath + ".tmp", cpath)
    return clean(text)


def wrap(rel, title, pages, summary="", lang="en", answers=""):
    e = html.escape
    # relative link back to the PDF so the wrapper also works over file://
    depth = rel.count("/") + 2  # wrapper lives at _app/text/<rel dirs>/
    up = "../" * depth
    hist = rel.startswith(HISTORICAL)
    # historical shelves: same badge + historical.html routing as gen_shelves doc_row
    href = f"{up}_app/historical.html?f={quote(rel, safe='')}" if hist else f"{up}{quote(rel)}"  # quote: a '#' in a CD3WD filename broke the link (r8)
    badge = ' <span class="l-badge l-badge--hist" data-pagefind-ignore>HISTORICAL</span>' if hist else ""
    parts = [
        f"<!doctype html><html lang=\"{e(lang)}\"><head><meta charset=\"utf-8\">",  # E9: Spanish PDFs land in pagefind's es bucket
        f"<title>{e(title)}</title></head><body>",
        f"<h1>{e(title)}{badge}</h1>",
        f"<span data-pagefind-meta=\"pdf[data-pdf]\" data-pdf=\"{e(rel)}\" hidden></span>",
        # era filter: search.html queries modern and historical separately so
        # 1.9M historical pages cannot crowd modern hits out of the top-N
        f"<span data-pagefind-filter=\"era\" hidden>{'historical' if hist else 'development' if rel.startswith(DEV_PREFIX) else 'modern'}</span>",
        f"<p><a href=\"{href}\">Open the PDF</a></p>",
    ]
    if answers:
        # E1c: "what this answers" shown on the result row (meta) and searchable at low weight so plain words in the
        # summary find the document without lifting c1 over the page chunk that holds an exact phrase (r8c)
        parts.append(f"<span data-pagefind-meta=\"summary[data-summary]\" data-summary=\"{e(answers)}\" hidden></span>")
        parts.append(f"<p data-pagefind-weight=\"0.3\">{e(answers)}</p>")
    if summary:
        parts.append(f"<p>{e(summary)}</p>")
    for n, text in pages:
        parts.append(f"<h2 id=\"p{n}\">Page {n}</h2>")
        parts.append(f"<p>{e(text)}</p>")
    parts.append("</body></html>")
    return "\n".join(parts)


def main():
    titles = titles_map()
    curated = {}   # optional: data/docs.curated.json (build/gen_doc_meta.py, a local LLM) adds summaries to the wrappers
    if os.path.exists(CURATED):
        with open(CURATED) as f:
            curated = json.load(f)
    else:
        print(f"WARN no {CURATED}: text wrappers carry no summaries (BUILDING.md, step 6)", file=sys.stderr)
    summaries = {k: v.get("s") or v.get("a", "") for k, v in curated.items()}   # C1 (#285) blanked some s: fall back to a
    answers = {k: v.get("a", "") for k, v in curated.items()}
    langs = {k: v.get("l", "en") or "en" for k, v in curated.items()}
    done = skipped_notext = failed = uptodate = 0
    for wdir in WHITELIST:
        base = os.path.join(LIB, wdir)
        if not os.path.isdir(base):
            continue
        for root, _, files in os.walk(base, followlinks=True):
            for fn in sorted(files):
                if fn.startswith(".") or not fn.lower().endswith(".pdf"):
                    continue
                pdf = os.path.join(root, fn)
                rel = wdir + pdf[len(base):]
                probe = os.path.join(OUT, rel + ".c1.html")
                if rel in NONCANON:
                    for w in glob.glob(glob.escape(os.path.join(OUT, rel)) + ".c*.html"):
                        os.remove(w)
                    continue
                if not FORCE and os.path.exists(probe) and os.path.getmtime(probe) >= os.path.getmtime(pdf):
                    uptodate += 1
                    continue
                try:
                    text = extract(pdf, rel)
                except subprocess.TimeoutExpired:
                    text = None
                if text is None:
                    print(f"FAIL extract: {rel}", file=sys.stderr)
                    failed += 1
                    continue
                if len(text.replace("\f", "").strip()) < MIN_TEXT:
                    # figure-only scans (drawings, posters): OCR finds nothing, but the vision-model description in
                    # docs.curated.json (2026-10-04) is text enough for search, chat and MCP to find the file by
                    if not summaries.get(rel):
                        skipped_notext += 1
                        continue
                    text = "Figure-only document, no text layer. Description: " + summaries[rel]
                pages = [(i + 1, t.strip()) for i, t in enumerate(text.split("\f")) if t.strip()]
                title = titles.get(rel) or os.path.splitext(fn)[0].replace("_", " ").replace("-", " ").strip().capitalize()
                os.makedirs(os.path.dirname(probe), exist_ok=True)
                # cd3wd handbooks keep full page chunks here (mcp.db + embeddings read these
                # wrappers); pf_dev_stage.py cuts them to one DEV_CHARS record for pagefind_dev
                per = HIST_CHUNK_PAGES if rel.startswith(HISTORICAL) else CHUNK_PAGES
                for c in range(0, len(pages), per):
                    chunk = pages[c:c + per]
                    out = os.path.join(OUT, f"{rel}.c{c // per + 1}.html")
                    with open(out, "w") as f:
                        f.write(wrap(rel, title, chunk, summaries.get(rel, "") if c == 0 and rel.startswith(DEV_PREFIX) else "",  # summary only in the dev tier: on modern docs it lifted c1 over the chunk holding the phrase (r8c)
                                     langs.get(rel, "en"), answers.get(rel, "") if c == 0 else ""))
                done += 1
                if done % 50 == 0:
                    print(f"...{done} written", flush=True)
    print(f"DONE written={done} uptodate={uptodate} no_text_layer={skipped_notext} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
