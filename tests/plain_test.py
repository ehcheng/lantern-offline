#!/usr/bin/env python3
"""No-server test for the plain pages (index_v1.html, triage_v1.html, triage_es_v1.html).

They must work opened straight from a drive (file://) in any browser, and on
the box. Checks, per page:
  - every relative link target exists (file mode) or answers 200 (http mode)
  - Chromium loads the page with no console errors and no request that leaves
    the page's own origin (file mode: nothing but file://)
  - a sample of directory and PDF links opens without a browser error page
Usage: plain_test.py                 # file:// over the local library
       plain_test.py http://10.10.10.10/   # against a served copy
Exit 1 on any failure. Run outside the sandbox for the http mode.
"""
import os, re, sys, urllib.parse, urllib.request

LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/library"
PAGES = ["index_v1.html", "triage_v1.html", "triage_es_v1.html"]   # FIXES #206: the Spanish plain triage page too
base = sys.argv[1] if len(sys.argv) > 1 else "file://" + LIB + "/"
http = base.startswith("http")
fails = []

def hrefs(page):
    html = open(f"{LIB}/{page}").read()
    return sorted({h for h in re.findall(r'href="([^"#]+)"', html) if not h.startswith(("http", "mailto"))})

def ok(path):
    if http:
        # #188 (RT3 b5 N1): unquote first, so an href that is already percent-encoded (%C3%B3) is not encoded twice (%25C3%25B3)
        req = urllib.request.Request(base + urllib.parse.quote(urllib.parse.unquote(path.split("?")[0])), method="HEAD", headers={"Host": "library.lan"})  # ?q= is not part of the file
        try:
            return urllib.request.urlopen(req, timeout=20).status == 200
        except Exception as e:
            return False
    return os.path.exists(f"{LIB}/{urllib.parse.unquote(path.split('?')[0])}")  # search.html?q=... is one file

for page in PAGES:
    links = hrefs(page)
    bad = [h for h in links if not ok(h)]
    print(f"{page}: {len(links)} links, {len(bad)} broken")
    fails += [f"{page} -> {h}" for h in bad]

if http:
    # Chrome on this Mac is blocked from LAN addresses by macOS local-network
    # privacy; the link checks above are the served-mode test. Browser
    # behaviour is covered by the file:// run.
    print(f"\n{len(fails)} FAIL"); [print("FAIL", f) for f in fails]
    sys.exit(1 if fails else 0)

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")   # bundled headless shell lacks ICU under the sandbox; acceptance_run uses chrome too
    errors, foreign = [], []
    for page in PAGES:
        # fresh tab per page (r29): Chrome's PDF viewer loads chrome-extension:// files lazily after the previous page's
        # PDF sample opens, and on a shared tab those late requests were counted against the next page
        pg = b.new_page()
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("request", lambda r: foreign.append(r.url) if not r.url.startswith(base.split("/", 3)[0] + "//" + ("" if not http else base.split("/")[2])) else None)
        errors.clear(); foreign.clear()
        pg.goto(base + page); pg.wait_for_timeout(1500)
        title = pg.title()
        if errors: fails.append(f"{page} console errors: {errors[:3]}")
        if foreign: fails.append(f"{page} left its origin: {foreign[:3]}")
        print(f"{page}: title '{title}', {len(errors)} console errors, {len(foreign)} foreign requests")
        # open a sample: first 3 directory links + first 2 PDFs
        links = hrefs(page)
        sample = [h for h in links if h.endswith("/")][:3] + [h for h in links if h.endswith(".pdf")][:2]
        for h in sample:
            try:
                r = pg.goto(base + urllib.parse.quote(h), wait_until="commit", timeout=20000)
                bad = (r is not None and r.status >= 400) or pg.url.startswith("chrome-error")
            except Exception as e:
                bad = "net::ERR_ABORTED" not in str(e)   # PDF download aborts navigation: fine
            if bad: fails.append(f"{page} open {h}")
            print(f"  open {h}: {'FAIL' if bad else 'ok'}")
        pg.close()
    b.close()

print(f"\n{len(fails)} FAIL"); [print("FAIL", f) for f in fails]
sys.exit(1 if fails else 0)
