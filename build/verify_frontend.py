#!/usr/bin/env python3
"""A7 verify gate (BUILD_PLAN safety invariants). Exit 1 on ANY failure.

Checks, over every shipped HTML page (library/*.html, _app/*.html,
_app/shelf/*.html, _app/text/**):
  1. every href/src resolves on disk (incl. ?f= targets of reader/historical)
  2. no direct href into a historical prefix outside _app/historical.html?f=
  3. no dailymed anywhere in titles.json or the wrapper tree
  4. landing index.html <= 100KB
"""
import html
import json
import os
import re
import sys
import urllib.parse

LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "library"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_index import HIST_PATHS as HIST  # one source for the historical gate (flagged shelves + cd3wd health)
from refs import shelf_fetched, shelf_of   # one rule for "not fetched" vs "broken"
from gen_index import is_hist  # r9 a7a W8: HIST_PATHS minus HIST_EXEMPT, the same rule gen_shelves and search.html use
LINK = re.compile(r"""(?:href|src)=["']([^"']+)["']""")
fails = []
not_fetched = set()   # content folders the hand-written pages link to that this build did not fetch
CONTENT = ("docs", "maps", "tools", "mirrors", "audio", "video", "datasets", "zim", "kolibri_data")
PRE_HASH = "--pre-hash" in sys.argv   # before hash_assets: pages still name the bundles of the last build
HASHED = re.compile(r"_app/app\.[0-9a-f]{8}\.(css|js)$")


def fail(msg):
    fails.append(msg)
    if len(fails) <= 30:
        print(f"FAIL {msg}")


def pages():
    for pat_dir, recurse in ((LIB, False), (os.path.join(LIB, "_app"), True)):
        for root, dirs, files in os.walk(pat_dir):
            if not recurse and root != pat_dir:
                continue
            if not recurse:
                dirs[:] = []
            for fn in files:
                # *_v1.html = pre-Lantern backups, kept but not shipped chrome
                if fn.endswith((".html", ".htm")) and not fn.endswith("_v1.html"):
                    yield os.path.join(root, fn)


def check_page(page):
    rel_page = os.path.relpath(page, LIB)
    src = open(page, encoding="utf-8", errors="replace").read()
    if "/_app/text/" in page:
        # gen_text escapes all page text below the first <h2 id="pN">; the only links are above it
        src = src[:src.find('<h2 id="p')] if '<h2 id="p' in src else src
    for raw in LINK.findall(src):
        u = html.unescape(raw)
        if u.startswith(("http:", "https:", "//", "mailto:", "javascript:", "data:", "#")):
            continue
        if "${" in u:  # JS template literal in inline script, not a real link
            continue
        path, _, query = u.partition("?")
        path = urllib.parse.unquote(path.split("#")[0])
        if path:
            target = (os.path.normpath(LIB + path) if path.startswith("/")
                      else os.path.normpath(os.path.join(os.path.dirname(page), path)))
            if (not os.path.exists(target) and os.path.basename(path) not in ("image-release.txt", "VERSION.json")
                    and "discs/" not in path):
                # image-release.txt is written at first boot; /discs/ is lantern-discs.service's
                # loop mount of the CD3WD .iso files; VERSION.json is written by the seal AFTER this build
                # (and a rejected seal renames it away). None is in the tree at build time.
                rel = os.path.relpath(target, LIB).split(os.sep)
                if PRE_HASH and HASHED.search(path):
                    continue
                if rel[0] in CONTENT and len(rel) > 1 and not shelf_fetched("/".join(rel)):
                    not_fetched.add(shelf_of("/".join(rel)))   # a partial library: the folder is absent
                    continue
                fail(f"{rel_page}: broken link {u[:120]}")
                continue
        # ?f= payloads (reader.html / historical.html) must also resolve
        if "f=" in query:
            f = urllib.parse.parse_qs(query).get("f", [""])[0]
            if f and not os.path.exists(os.path.join(LIB, f)):
                fail(f"{rel_page}: ?f= target missing {f[:120]}")
                f = None
            # invariant 3: historical docs only via the interstitial
            if f and is_hist(f) and not path.endswith("historical.html"):
                fail(f"{rel_page}: historical ?f= outside interstitial {u[:120]}")
        # invariant 3: no direct href into historical prefixes
        rel_target = os.path.relpath(
            os.path.normpath(LIB + path) if path.startswith("/")
            else os.path.normpath(os.path.join(os.path.dirname(page), path)),
            LIB) if path else ""
        if (is_hist(rel_target) and rel_page != "_app/historical.html"
                and not rel_target.endswith("README-WARNING.txt")):  # the warning itself
            fail(f"{rel_page}: direct historical href {u[:120]}")


def main():
    n = 0
    for page in pages():
        n += 1
        check_page(page)
    print(f"scanned {n} pages")
    if not_fetched:
        print(f"NOTE pages link to {len(not_fetched)} content folders this build did not fetch (dead links until fetched): "
              + " ".join(sorted(not_fetched)))

    # invariant 1: dosing-leak gates
    tj = open(f"{LIB}/_app/index/titles.json").read()
    if "dailymed" in tj:
        fail("dailymed in titles.json")
    if os.path.exists(f"{LIB}/_app/text/datasets"):
        fail("dailymed/datasets wrappers present in _app/text")
    # titles budget
    if len(tj) >= 2_000_000:  # raised from 1.2MB for the CD3WD titles (2026-09-30)
        fail(f"titles.json {len(tj)} bytes over 2MB budget")
    # landing weight
    sz = os.path.getsize(f"{LIB}/index.html")
    if sz > 100_000:
        fail(f"landing index.html {sz} bytes > 100KB")

    if fails:
        print(f"VERIFY FAILED: {len(fails)} problems")
        return 1
    print("VERIFY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
