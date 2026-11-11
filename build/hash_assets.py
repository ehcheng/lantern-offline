#!/usr/bin/env python3
"""A7 final step (spec 7.6): cache-bust app.css/app.js with content-hash copies.

Copies _app/app.css -> _app/app.<sha8>.css (canonical file stays — generators
and file:// bookmarks keep working) and rewrites every shipped page's
href/src, including refs to stale hashes, which are then deleted.
RUN LAST: touches every page. Idempotent.
"""
import hashlib
import os
import re
import sys

LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "library"))
APP = os.path.join(LIB, "_app")


def main():
    hashes = {}
    for ext in ("css", "js"):
        data = open(f"{APP}/app.{ext}", "rb").read()
        h = hashlib.sha256(data).hexdigest()[:8]
        hashes[ext] = h
        with open(f"{APP}/app.{h}.{ext}", "wb") as f:
            f.write(data)
        for old in os.listdir(APP):
            if re.fullmatch(rf"app\.[0-9a-f]{{8}}\.{ext}", old) and old != f"app.{h}.{ext}":
                os.remove(f"{APP}/{old}")

    pat = re.compile(r"(_app/)app(?:\.[0-9a-f]{8})?\.(css|js)")
    changed = 0
    for root, dirs, files in os.walk(LIB):
        if os.path.basename(root) in ("text", "pagefind", "pagefind_hist", "covers", "fonts", "vendor"):
            dirs[:] = []
            continue
        for fn in files:
            if not fn.endswith((".html", ".htm")):
                continue
            p = os.path.join(root, fn)
            src = open(p, encoding="utf-8", errors="replace").read()
            out = pat.sub(lambda m: f"{m.group(1)}app.{hashes[m.group(2)]}.{m.group(2)}", src)
            if out != src:
                open(p, "w", encoding="utf-8").write(out)
                changed += 1
    print(f"app.css -> app.{hashes['css']}.css, app.js -> app.{hashes['js']}.js; "
          f"{changed} pages rewritten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
