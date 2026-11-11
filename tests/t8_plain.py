#!/usr/bin/env python3
"""T8 plain version (index_v1.html, triage_v1.html, triage_es_v1.html): the no-script pages that must work
from a bare drive in any browser. One check per invocation so simple agents can run
them in parallel; every check appends CSV rows (tier,check,path,status,detail) to
results/t8_<check>[_<shard>].csv. Every row is re-checked every run: an old PASS is never carried
over (FIXES #160; the same resume bug as #32/#124 left the 10-09 t8 rows stale). report.py takes the last row per path.

  t8_plain.py static                     no <script>, no external src/link, charset+viewport,
                                         size budget, every #anchor resolves, ids unique
  t8_plain.py links [--base http://IP/]  EVERY relative href exists on disk (file mode) or
                                         answers HEAD 200 with Host: library.lan (http mode);
                                         one historical.html?f= link per HIST_PATHS prefix passes
                                         historical.html's ALLOWED (redteam 2026-10-05 F1);
                                         search/chat/reader/viewer links on the plain pages carry a
                                         "needs the server" marking (title, data-server, or wording)
  t8_plain.py coverage                   every shelf in gen_index.SHELVES and every top-level
                                         content folder in the manifest is linked (or an ancestor is)
  t8_plain.py parity                     triage_v1 text and links survive into triage.html;
                                         index_v1 links runbook, triage, VERSION.json, zim/;
                                         index_v1's Survivor Library count = PDFs in MANIFEST
  t8_plain.py browser [--shard i/N]      Chrome, file://, JS disabled: every link opens (no
                                         chrome-error, no console error, no request leaving
                                         file://), pages have no horizontal overflow at 390 px

Run browser outside the sandbox (real Chrome). Logs: redirect to logs/t8_<check>.log.
"""
import csv, html, os, re, sys, urllib.parse, urllib.request
EX = os.path.dirname(os.path.abspath(__file__)); os.chdir(f"{EX}/..")
sys.path.insert(0, "build")
LIB = "library"
PAGES = ["index_v1.html", "triage_v1.html", "triage_es_v1.html"]   # FIXES #206: the Spanish plain triage page too
# md-rendered pages that also serve as plain pages (gen_shelves shell(server=True)); the Lantern tab bar on them is the
# only place a drive reader meets search/chat links without prose around them (redteam 2026-10-05 s0 W3)
PLAIN_MD = ["RUNBOOK.html", "SKILLS_CHECKLIST.html", "PURCHASE_LIST.html", "LICENSES.html", "MAINTENANCE_PROMPT.html", "REFRESH.html"]
SERVER_ONLY = re.compile(r"(?:^|/)(?:search|chat|reader)\.html(?:[?#]|$)|/viewer#")
SIZE_BUDGET = 150_000  # bytes per page; index_v1 is ~25 KB, triage_v1 ~40 KB

check = sys.argv[1] if len(sys.argv) > 1 else "static"
args = dict(zip(sys.argv[2::2], sys.argv[3::2]))
shard, nshard = (int(x) for x in args.get("--shard", "1/1").split("/"))
base = args.get("--base")  # http mode for links
out_name = f"t8_{check}" + (f"_{shard}of{nshard}" if nshard > 1 else "")
out_path = f"{EX}/results/{out_name}.csv"
out = open(out_path, "a", newline=""); w = csv.writer(out, lineterminator="\n")
def row(c, p, st, d=""):
    w.writerow(["t8", c, p, st, d]); out.flush(); print(c, p, st, d, flush=True)

def read(page): return open(f"{LIB}/{page}", encoding="utf-8").read()
def hrefs(page):
    """relative hrefs (no anchors, no http/mailto), html-unescaped, in document order, deduped"""
    seen, res = set(), []
    for h in re.findall(r'href="([^"]+)"', read(page)):
        h = html.unescape(h).split("#", 1)[0].split("?", 1)[0]   # search.html?q=... (wikimed refs) is the page, not a path
        if not h or h.startswith(("http:", "https:", "mailto:")) or h in seen: continue
        seen.add(h); res.append(h)
    return res
def exists(h): return os.path.exists(f"{LIB}/{urllib.parse.unquote(h)}")

if check == "static":
    for page in PAGES:
        t = read(page); p = page
        row("no_script", p, "FAIL" if re.search(r"<script\b", t, re.I) else "PASS")
        ext = [m for m in re.findall(r'(?:src|href)="([^"]+)"', t) if m.startswith(("http", "//"))
               and not re.search(r'<a [^>]*href="%s"' % re.escape(m), t)]
        row("no_external_assets", p, "FAIL" if ext else "PASS", ";".join(ext[:3]))
        row("charset_viewport", p, "PASS" if 'charset="utf-8"' in t and 'name="viewport"' in t else "FAIL")
        n = os.path.getsize(f"{LIB}/{page}")
        row("size_budget", p, "PASS" if n <= SIZE_BUDGET else "FAIL", str(n))
        ids = re.findall(r'\bid="([^"]+)"', t)
        row("ids_unique", p, "PASS" if len(ids) == len(set(ids)) else "FAIL",
            ";".join(sorted({i for i in ids if ids.count(i) > 1})[:5]))
        for a in sorted(set(re.findall(r'href="#([^"]+)"', t))):
            row("anchor", f"{p}#{a}", "PASS" if a in ids else "FAIL")
        row("has_h1", p, "PASS" if re.search(r"<h1\b", t) else "FAIL")
        inert = [m for m in re.findall(r"<a\b[^>]*>", t) if "href=" not in m]   # data-ref anchors never resolved = dead link in plain mode
        row("no_inert_anchor", p, "PASS" if not inert else "FAIL", f"{len(inert)} <a> without href: " + ";".join(inert[:2]))

elif check == "links":
    def ok_http(h):
        req = urllib.request.Request(base + urllib.parse.quote(urllib.parse.unquote(h)), method="HEAD",
                                     headers={"Host": "library.lan"})
        try: return urllib.request.urlopen(req, timeout=20).status == 200
        except Exception: return False
    for page in PAGES:
        for h in hrefs(page):
            if base: row("link_http", f"{page} -> {h}", "PASS" if ok_http(h) else "FAIL")
            else:
                st = "PASS" if exists(h) else "FAIL"
                if st == "PASS" and h.endswith("/") and not os.path.isdir(f"{LIB}/{urllib.parse.unquote(h)}"): st = "FAIL"
                row("link_file", f"{page} -> {h}", st, "" if st == "PASS" else "missing")
    # (a) interstitial: one real historical.html?f= link per gate prefix must pass historical.html's ALLOWED
    import glob
    from gen_index import HIST_PATHS
    allowed = re.findall(r"'([^']+)'", re.search(r"var ALLOWED = \[(.*?)\];", read("_app/historical.html")).group(1))
    links = {urllib.parse.unquote(html.unescape(m)) for f in glob.glob(f"{LIB}/_app/shelf/*.html")
             for m in re.findall(r'historical\.html\?f=([^"&]+)', open(f, encoding="utf-8").read())}
    for pre in HIST_PATHS:
        sample = next((l for l in sorted(links) if l.startswith(pre)), None)
        if sample is None: row("hist_allowed", pre, "FAIL", "no shelf page links historical.html?f= under this prefix"); continue
        ok = any(sample.startswith(a) for a in allowed)
        row("hist_allowed", pre, "PASS" if ok else "FAIL", sample if ok else f"{sample} not in ALLOWED {allowed}")
    # (b) server-only links on plain pages need a "needs the server" marking: title/data-server on the <a>, or the word
    # "server" in the anchor's sentence or the one before (R2's triage wording). ponytail: regex sentence split, no DOM.
    def plain(s): return html.unescape(re.sub(r"<[^>]+>", " ", s))
    for page in PAGES + PLAIN_MD:
        if not os.path.exists(f"{LIB}/{page}"): continue
        t = read(page)
        for n, m in enumerate(re.finditer(r"<a\b[^>]*>.*?</a>", t, flags=re.S)):
            href = re.search(r'href="([^"]*)"', m.group(0))
            if not href or not SERVER_ONLY.search(html.unescape(href.group(1))): continue
            tag = m.group(0)
            marked = "server" in tag.split(">", 1)[0].lower() or "server" in plain(tag).lower()
            if not marked:
                sents = re.split(r"(?<=[.!?:])\s+", re.sub(r"\s+", " ", plain(t[max(0, m.start() - 400):m.end()])))
                marked = "server" in " ".join(sents[-2:]).lower()
            row("server_marked", f"{page}#{n} -> {html.unescape(href.group(1))[:60]}", "PASS" if marked else "FAIL",
                "" if marked else "no 'needs the server' title/data-server/wording")

elif check == "coverage":
    from gen_index import SHELVES
    import posixpath
    linked = {urllib.parse.unquote(h).rstrip("/") for h in hrefs("index_v1.html")}
    # one hop: a static shelf page index_v1 links (e.g. _app/shelf/mirrors.html, #114 moved the firmware folders there) counts
    for pg in [l for l in linked if l.startswith("_app/shelf/") and l.endswith(".html") and os.path.exists(f"{LIB}/{l}")]:
        linked |= {posixpath.normpath(posixpath.join(posixpath.dirname(pg), urllib.parse.unquote(h))).rstrip("/") for h in hrefs(pg)}
    def covered(path):
        parts = path.split("/")
        return any("/".join(parts[:i]) in linked for i in range(1, len(parts) + 1)) \
            or any(l.startswith(path + "/") for l in linked)   # a shelf whose subfolders are linked one by one
    for shelf in SHELVES:
        row("shelf_linked", shelf, "PASS" if covered(shelf) else "FAIL", SHELVES[shelf][0])
    # every second-level content folder in the manifest (docs/x, mirrors/x, maps/x, datasets/x, tools/x, video/x, audio/x)
    tops = set()
    for l in open(f"{LIB}/MANIFEST.sha256"):
        p = l[74:].rstrip("\n").split("/")
        if len(p) > 2 and p[0] in ("docs", "mirrors", "maps", "datasets", "tools", "video", "audio", "zim", "kolibri_data"):
            tops.add("/".join(p[:2]) if p[0] != "zim" else "zim")
    for t in sorted(tops):
        if t.startswith("kolibri_data"): row("folder_linked", t, "SKIP", "server-only, not browsable from a drive"); continue
        if t == "datasets/dailymed": row("folder_linked", t, "SKIP", "policy: the full site hides DailyMed (dose rule); linking it from the plain page is the owner's call"); continue
        row("folder_linked", t, "PASS" if covered(t) else "FAIL")
    for must in ("triage_v1.html", "RUNBOOK.html", "VERSION.json", "zim", "index.html"):
        row("must_link", must, "PASS" if must in linked else "FAIL")

elif check == "parity":
    def text(s):
        s = re.sub(r"<(script|style)\b.*?</\1>", " ", s, flags=re.S | re.I)
        return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()
    def norm(s): return re.sub(r"[^a-z0-9]+", " ", re.sub(r"\(\s*PDF\s*\)", " ", s).lower()).strip()   # build_triage turns "NOW:" into a badge, refs add (PDF) links
    for v1page, fullpage in (("triage_v1.html", "triage.html"), ("triage_es_v1.html", "triage_es.html")):   # FIXES #206: ES pair too
        v1, full = read(v1page), read(fullpage)
        # every section body in v1 (between h2s) must appear verbatim as text in triage.html
        secs = re.split(r'<h2 id="[^"]+">', v1.split("</nav>", 1)[1].rsplit("<hr>", 1)[0])[1:]
        ids = re.findall(r'<h2 id="([^"]+)">', v1)
        ft = norm(text(full))
        for i, s in zip(ids, secs):
            body = text(s.split("</h2>", 1)[1])
            # build_triage inserts a dosing notice at the end of each section; compare the longest sentence chunks
            chunks = [c.strip() for c in re.split(r"(?<=[.!?])\s", body) if len(c.strip()) > 40][:8]
            miss = [c for c in chunks if norm(c) not in ft]
            row("triage_text", f"{v1page}#{i}", "PASS" if not miss else "FAIL", miss[0][:80] if miss else f"{len(chunks)} chunks")
            row("triage_anchor", f"{fullpage}#{i}", "PASS" if f'id="{i}"' in full else "FAIL")
        v1links = set(hrefs(v1page)); fl = set(hrefs(fullpage))
        for h in sorted(v1links):
            # the plain page's language switch targets the other plain page; the full page links that page's full twin
            ok = h in fl or (h.endswith("_v1.html") and h.replace("_v1.html", ".html") in fl)
            row("triage_link", f"{v1page} -> {h}", "PASS" if ok else "FAIL", "" if ok else "dropped by build_triage")
    v = read("index_v1.html")
    for pat, name in ((r"About [\d.,]+ TB", "size line"), (r'href="triage_v1\.html"', "plain triage link"),
                      (r'href="VERSION\.json"', "version link"), (r'href="RUNBOOK\.html"', "runbook link")):
        row("index_v1_has", name, "PASS" if re.search(pat, v) else "FAIL")
    # (c) the Survivor Library figure on index_v1 equals the PDFs on disk per MANIFEST (7,344 claimed vs 7,322 on 2026-10-05)
    li = re.search(r"<li>[^\n]*Survivor Library[^\n]*</li>", v)
    num = li and re.search(r"\d{1,3}(?:,\d{3})+|\d+", re.sub(r"<[^>]+>", "", li.group(0)).split("Survivor Library", 1)[1])
    claimed = int(num.group(0).replace(",", "")) if num else None
    ondisk = sum(1 for l in open(f"{LIB}/MANIFEST.sha256") if re.search(r"library/docs/survivor_library/.*\.pdf$", l.rstrip("\n")))
    row("survivor_count", "index_v1.html", "PASS" if claimed == ondisk else "FAIL", f"page {claimed} manifest {ondisk}")

elif check == "browser":
    from playwright.sync_api import sync_playwright
    root = "file://" + os.path.abspath(LIB) + "/"
    jobs = [(pg, None) for pg in PAGES] + [(pg, h) for pg in PAGES for h in hrefs(pg)]
    jobs = [j for i, j in enumerate(jobs) if i % nshard == shard - 1]
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        ctx = b.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
        for page, h in jobs:
            pg = ctx.new_page()   # one page per job: late sub-resource requests of the previous page must not bleed into this row
            errors, foreign, failed = [], [], []
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "Failed to load resource" not in m.text else None)
            pg.on("requestfailed", lambda r: failed.append(r.url))   # a missing sub-resource (mirror css/img) is noted, a missing target is a FAIL
            pg.on("request", lambda r: foreign.append(r.url) if not r.url.startswith(("file://", "chrome-extension://")) else None)   # Chrome PDF viewer is an extension
            target = page if h is None else h
            key = page if h is None else f"{page} -> {h}"
            url = root + urllib.parse.quote(urllib.parse.unquote(target))
            try:
                r = pg.goto(url, wait_until="commit", timeout=30000)
                try: pg.wait_for_load_state("load", timeout=15000)   # sub-resources (external css, images) only show up after load
                except Exception: pass
                bad = (r is not None and r.status >= 400) or pg.url.startswith("chrome-error")
                detail = f"status {r.status}" if r else ""
            except Exception as e:
                bad = "net::ERR_ABORTED" not in str(e)   # PDF/binary download aborts navigation: fine
                detail = str(e).split("\n")[0][:80]
            if h is None and not bad:
                pg.wait_for_timeout(500)
                ov = pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 1")
                row("no_overflow_390", page, "FAIL" if ov else "PASS")
                row("h1_nojs", page, "PASS" if pg.locator("h1").count() else "FAIL")
            if foreign: bad, detail = True, "left file://: " + foreign[0][:60]
            if errors: bad, detail = True, "console: " + errors[0][:60]
            if any(urllib.parse.unquote(u) == urllib.parse.unquote(url) for u in failed): bad, detail = True, "target failed to load"
            elif failed: detail = (detail + " " if detail else "") + f"{len(failed)} sub-resource(s) missing e.g. " + failed[0].rsplit("/", 1)[-1][:40]
            row("open_nojs", key, "FAIL" if bad else "PASS", detail)
            pg.close()
        b.close()
else:
    sys.exit(f"unknown check {check}")
out.close()
print("done", out_name)
