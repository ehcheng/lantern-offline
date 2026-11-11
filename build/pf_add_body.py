#!/usr/bin/env python3
"""Prepare the pagefind STAGE copy of the mirrors (never the mirror itself).
1. Give body-less staged HTML a <body> so pagefind indexes it. nchfp paper pages are SSI fragments: the
   header include never ran, so there is no </head> or <body>; browsers synthesize one, pagefind does not.
2. Hesperian (red team 10-09 b2): every result was titled "Hesperian Health Guides" because pagefind takes the first
   <h1>, the hidden print heading. The page heading (#firstHeading) becomes the explicit title; the print heading,
   the nav/language menus (class navigation-not-searchable, .languageSelectorContainer) and the footer are ignored
   so snippets stop opening with "فارسی Bahasa Indonesia ... PARTNERS APPS".
Usage: pf_add_body.py <staged dir>"""
import os, re, sys


TAG = re.compile(r"<(?:div|ul|header|footer)\b[^>]*>", re.I)
SKIP = re.compile(r'class="[^"]*(?:navigation-not-searchable|languageSelectorContainer)|id="footer"')


def hesperian(s):
    s = re.sub(r'<h1 class="printonly"(?![^>]*data-pagefind)', '<h1 class="printonly" data-pagefind-ignore', s, count=1)
    s = re.sub(r'<h1 id="firstHeading"(?![^>]*data-pagefind)', '<h1 id="firstHeading" data-pagefind-meta="title"', s, count=1)
    def tag(m):
        t = m.group(0)
        if "data-pagefind" in t or not SKIP.search(t): return t
        i = t.index(" ") if " " in t else len(t) - 1
        return t[:i] + " data-pagefind-ignore" + t[i:]
    return TAG.sub(tag, s)


if __name__ == "__main__":
    n = h = 0
    for root, _, files in os.walk(sys.argv[1]):
        for fn in files:
            if not fn.lower().endswith((".html", ".htm")): continue
            p = os.path.join(root, fn)
            with open(p, "rb") as fh: head = fh.read(8)
            if head.startswith(b"%PDF"): continue   # a PDF saved under .html
            s = open(p, encoding="utf-8", errors="replace").read()
            s2 = s
            if "/hesperian/" in p.replace(os.sep, "/"):
                s2 = hesperian(s)
                if s2 != s: h += 1
            if not re.search(r"<body[\s>]", s2, re.I):
                s3 = re.sub(r'<!--#include virtual="[^"]*header[^"]*"\s*-->', "</head><body>", s2, count=1)
                if s3 == s2: s3 = re.sub(r"</head>", "</head><body>", s2, count=1, flags=re.I)
                if s3 == s2: s3 = re.sub(r"</title>", "</title></head><body>", s2, count=1, flags=re.I)
                if s3 != s2:
                    if not re.search(r"</body>", s3, re.I): s3 += "</body>"
                    s2 = s3; n += 1
            if s2 != s:
                open(p, "w", encoding="utf-8").write(s2)
    print(f"pf_add_body: {n} pages given a <body>, {h} hesperian pages tagged for pagefind title/ignore")
