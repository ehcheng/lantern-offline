#!/usr/bin/env python3
"""Validate every OCR'd PDF against its pre-OCR backup. Stdlib + poppler only.

For each path in cache/ocr/needs_ocr.txt:
  structure  pdfinfo parses the file (exit 0) and reports a page count
  pages      page count equals the backup's page count
  size       new size >= backup size (OCR only adds a text layer)
  text       pdftotext yields > 200 chars
  quality    share of alphabetic tokens (3+ letters) that are ASCII words with
             at least one vowel, on a 3-page sample; < 0.55 flagged as garbage-ish
Writes cache/ocr/validation.tsv (path, status, pages, bak_pages, size, bak_size,
chars, quality) and prints a summary. Exit 1 if any structure/pages/text check fails.
"""
import os
import random
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.realpath(os.path.join(ROOT, "library", "docs"))
BAK = os.path.join(os.path.dirname(DOCS), "docs_ocr_bak_20260925")
LIST = os.path.join(ROOT, "cache", "ocr", "needs_ocr.txt")
OUT = os.path.join(ROOT, "cache", "ocr", "validation.tsv")
WORD = re.compile(r"[A-Za-z]{3,}")
VOWEL = re.compile(r"[aeiouyAEIOUY]")


def run(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=300)
    except subprocess.TimeoutExpired:
        return None


def pages(f):
    r = run("pdfinfo", f)
    if not r or r.returncode:
        return None
    m = re.search(r"^Pages:\s+(\d+)", r.stdout, re.M)
    return int(m.group(1)) if m else None


def quality(f, n):
    """Fraction of 3+ letter tokens that look like words, on 3 sampled pages."""
    toks = []
    for p in sorted(random.Random(f).sample(range(1, n + 1), min(3, n))):
        r = run("pdftotext", "-f", str(p), "-l", str(p), "-enc", "UTF-8", f, "-")
        if r and r.returncode == 0:
            toks += WORD.findall(r.stdout)
    if len(toks) < 20:
        return None
    good = sum(1 for t in toks if VOWEL.search(t) and t.isascii())
    return round(good / len(toks), 3)


def check(rel):
    f, b = os.path.join(DOCS, rel), os.path.join(BAK, rel)
    n = pages(f)
    if n is None:
        return (rel, "FAIL-structure", "", "", "", "", "", "")
    nb = pages(b) if os.path.exists(b) else None
    sz, szb = os.path.getsize(f), (os.path.getsize(b) if os.path.exists(b) else "")
    r = run("pdftotext", "-enc", "UTF-8", f, "-")
    chars = len(r.stdout.replace("\f", "").strip()) if r and r.returncode == 0 else 0
    q = quality(f, n) if chars > 200 else None
    if nb is not None and n != nb:
        st = "FAIL-pages"
    elif chars <= 200:
        st = "FAIL-text"
    elif szb != "" and sz < szb:
        st = "WARN-size"
    elif q is not None and q < 0.55:
        st = "WARN-quality"
    else:
        st = "ok"
    return (rel, st, n, nb if nb is not None else "", sz, szb, chars, q if q is not None else "")


def main():
    rels = [l.strip() for l in open(LIST) if l.strip()]
    with ThreadPoolExecutor(16) as ex:
        rows = list(ex.map(check, rels))
    with open(OUT, "w") as o:
        o.write("path\tstatus\tpages\tbak_pages\tsize\tbak_size\tchars\tquality\n")
        for r in rows:
            o.write("\t".join(str(x) for x in r) + "\n")
    counts = {}
    for r in rows:
        counts[r[1]] = counts.get(r[1], 0) + 1
    print("validated", len(rows), "files:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print("report:", OUT)
    sys.exit(1 if any(r[1].startswith("FAIL") for r in rows) else 0)


if __name__ == "__main__":
    main()
