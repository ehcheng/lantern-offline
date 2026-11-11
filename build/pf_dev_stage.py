#!/usr/bin/env python3
"""Staging step for _app/pagefind_dev: under <stage>/docs/cd3wd/2012 an English document (wrapper lang="en") keeps one
wrapper holding the summary plus the first DEV_CHARS of page text, and its .c2+ chunks are dropped. A document in any
other language keeps every page chunk, so its deep pages are findable by their words in its own language bucket.
The real wrappers in library/_app/text stay page-chunked for mcp.db and embeddings.
FIXES #116 (2026-10-06), measured on scratch builds (dev, 80-load s2 set + 50 Spanish v3 questions, cold per query):
  3,000 chars for all (old)  245 MB; EN page p95 510 ms / 3.9 MB; ES page p95 116 ms / 0.5 MB
  full text for all          786 MB; EN page p95 3,033 ms / 10.9 MB (max 7.9 s); gold v2 +1, v3 +-0, v1 -1
  full text for non-English  319 MB; EN page p95 478 ms / 3.9 MB; ES page p95 247 ms / 1.4 MB; gold v2 +1 (K235), v3 +-0
English deep pages stay with /semantic (English embedding model); Spanish deep pages had no path at all."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from gen_index import DEV_DOC_LEVEL
DEV_CHARS = 3000
root = os.path.join(sys.argv[1], DEV_DOC_LEVEL)
PAGE = re.compile(r'<h2 id="p(\d+)">Page \d+</h2>\n<p>(.*?)</p>', re.S)
LANG = re.compile(r'<html lang="([^"]+)"')
lang = {}   # document -> wrapper language, read from its .c1 wrapper
for d, _, files in os.walk(root):
    for fn in files:
        if fn.endswith(".c1.html"):
            m = LANG.search(open(os.path.join(d, fn)).read(300))
            lang[os.path.join(d, fn[:-len(".c1.html")])] = m.group(1) if m else "en"
kept = dropped = whole = 0
for d, _, files in os.walk(root):
    for fn in files:
        p = os.path.join(d, fn)
        if lang.get(re.sub(r"\.c\d+\.html$", "", p), "en") != "en":
            whole += 1; continue
        if not fn.endswith(".c1.html"):
            os.remove(p); dropped += 1; continue
        s = open(p).read()
        head, body = s.split("\n<h2 ", 1) if "\n<h2 " in s else (s, "")
        out, n = [], 0
        for pn, text in PAGE.findall("<h2 " + body):
            out.append(f'<h2 id="p{pn}">Page {pn}</h2>\n<p>{text[:DEV_CHARS - n]}</p>')
            n += len(text)
            if n >= DEV_CHARS: break
        open(p, "w").write(head + "\n" + "\n".join(out) + "\n</body></html>")
        kept += 1
print(f"pf_dev_stage: {kept} English records ({dropped} chunk files dropped), {whole} non-English chunk records kept whole")
