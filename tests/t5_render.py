#!/usr/bin/env python3
"""T5 rendering with Playwright against the dev server (:8765, sandbox off).
Every root/_app/shelf page in light+dark x 390/1200: 0 console errors (LAN LLM probes excluded),
breadcrumb, header search, mobile tab bar, no horizontal overflow. reader.html on 3 PDFs per shelf,
plants photos, audio/video playback, map tile, search queries both modes, chat e2e.
Usage: python3 t5_render.py [workers] [base_url]
  base_url defaults to the dev server http://127.0.0.1:8765/; the seal chain also runs it against the Pi,
  http://10.10.10.10/ (nginx default_server answers any Host; /semantic and /mcp are proxied there)."""
import os, re, csv, json, glob, random, subprocess, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
EX = os.path.dirname(os.path.abspath(__file__)); os.chdir(f"{EX}/..")
NW = int(sys.argv[1]) if len(sys.argv) > 1 else 8
B = (sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8765/").rstrip("/") + "/"
TAG = "" if "127.0.0.1" in B else "_" + re.sub(r"\W+", "_", B.split("//", 1)[1]).strip("_")   # results/t5_10_10_10_10.csv for the Pi run
random.seed(5)
rows = []
def row(c, p, st, d=""): rows.append(["t5", c, p, st, d]); print(f"{c} {p} {st} {d[:80]}", flush=True)
NOISE = re.compile(r"image-release\.txt|10\.10\.10\.20|11434|fakellm|llmEndpoints|ERR_CONNECTION|ERR_NAME_NOT_RESOLVED|Failed to load resource: net::ERR|/v1/models|/api/tags")

def page_check(pw_page, url, mobile):
    errs = []
    pw_page.on("console", lambda m: errs.append(m.text) if m.type == "error" and not NOISE.search(m.text) and "Failed to load resource" not in m.text else None)  # 4xx/5xx come from the response hook with the URL
    pw_page.on("pageerror", lambda e: errs.append(str(e)))
    pw_page.on("response", lambda r: errs.append(f"HTTP {r.status} {r.url[-90:]}") if r.status >= 400 and not NOISE.search(r.url) else None)
    if url == "_app/historical.html": url += "?f=" + urllib.parse.quote(HIST_PDF)  # interstitial needs a target
    pw_page.goto(B + url, wait_until="load", timeout=60000); pw_page.wait_for_timeout(800)
    r = pw_page.evaluate("""() => ({
        crumb: !!document.querySelector('.l-caption a[href$="index.html"], .l-caption a[href$="es.html"], nav.l-nav, .crumb'),
        search: !!document.querySelector('.l-search, input[type=search], #q, a[href$="search.html"]'),
        tabbar: !!document.querySelector('.l-tabbar'),
        tabvis: (function(t){ if(!t) return false; var s=getComputedStyle(t); return s.display!=='none' && s.visibility!=='hidden'; })(document.querySelector('.l-tabbar')),
        overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
        text: document.body.innerText.length,
        ticks: document.body.innerText.indexOf('```') !== -1 })""")
    bad = []
    if errs: bad.append("console: " + errs[0][:100])
    # interstitial warning page, and the nginx 404 page (#188: served at any depth, so hand-written with absolute
    # links to triage/front page/search instead of the relative chrome; FIXES #190): no chrome by design
    chromeless = url.startswith(("_app/historical.html", "_app/404.html"))
    if not r["crumb"] and url not in ("index.html", "index_v1.html", "triage_v1.html", "triage_es_v1.html") and not chromeless: bad.append("no breadcrumb/nav")
    if not r["search"] and not url.endswith(("_v1.html", "LICENSES.html")) and not chromeless: bad.append("no header search")
    if mobile and not r["tabvis"] and not url.endswith(("_v1.html",)) and not chromeless: bad.append("tab bar hidden on mobile")
    if r["overflow"]: bad.append("horizontal overflow")
    if r["text"] < 50: bad.append("near-empty body")
    if r["ticks"]: bad.append("three backticks in the page text (a code fence leaked; FIXES #201)")
    return bad, errs

def shoot(pg, name):
    try: pg.screenshot(path=f"{EX}/shots/{name}.png", full_page=False)
    except Exception: pass

def worker(job):
    kind, args = job
    with sync_playwright() as p:
        # T5_PROXY=127.0.0.1:8766 routes the browser through an ssh tunnel to the Pi (macOS Local Network privacy blocks
        # a Playwright-launched Chrome from 10.10.10.10; curl is fine). Requests keep Host 10.10.10.10, so nginx is happy.
        br = p.chromium.launch(args=["--proxy-server=" + os.environ["T5_PROXY"]] if os.environ.get("T5_PROXY") else [])
        try:
            if kind == "page":
                url, scheme, width = args
                ctx = br.new_context(viewport={"width": width, "height": 844 if width < 600 else 900}, color_scheme=scheme)
                pg = ctx.new_page()
                try:
                    bad, errs = page_check(pg, url, width < 600)
                    name = f"{url.replace('/', '_')}_{scheme}_{width}"
                    if bad: shoot(pg, name)
                    row("page", f"library/{url}", "FAIL" if bad else "PASS", f"{scheme}/{width}: " + ("; ".join(bad) if bad else "ok"))
                except Exception as e:
                    row("page", f"library/{url}", "FAIL", f"{scheme}/{width}: {str(e)[:120]}")
            elif kind == "reader":
                path = args
                ctx = br.new_context(viewport={"width": 1200, "height": 900}); pg = ctx.new_page()
                errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
                try:
                    pg.goto(B + "reader.html?f=" + urllib.parse.quote(path) + "&p=2", timeout=60000)
                    pg.wait_for_function("() => { var c=document.getElementById('r-canvas'); return c && !c.hidden && c.width > 0 }", timeout=45000)
                    pg.wait_for_timeout(1500)
                    r = pg.evaluate("() => ({w: document.getElementById('r-canvas').width, p: (document.getElementById('r-page')||{}).value || (document.getElementById('r-page')||{}).textContent, spans: document.querySelectorAll('.textLayer span, .r-text span, [class*=text] span').length, msg: (document.getElementById('r-msg')||{}).textContent||''})")
                    bad = []
                    if r["w"] <= 0: bad.append("canvas empty")
                    total = int((re.findall(r"\d+", str(pg.evaluate("() => (document.getElementById('r-total')||{}).textContent || '0'"))) or ["0"])[0])
                    if total >= 2 and str(r["p"]).strip() != "2": bad.append(f"page jump landed on {r['p']!r} of {total}")
                    # reader.html draws highlights on the canvas; there is no DOM text layer by design
                    if errs: bad.append("pageerror " + errs[0][:80])
                    if bad: shoot(pg, "reader_" + os.path.basename(path)[:40])
                    row("reader", "library/" + path, "FAIL" if bad else "PASS", "; ".join(bad) or f"canvas {r['w']}px spans {r['spans']}")
                except Exception as e:
                    row("reader", "library/" + path, "FAIL", str(e)[:150])
            elif kind == "plants":
                ctx = br.new_context(viewport={"width": 1200, "height": 900}); pg = ctx.new_page()
                pg.goto(B + "plants.html", timeout=60000); pg.wait_for_timeout(1500)
                pg.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
                pg.wait_for_timeout(2000)
                r = pg.evaluate("""() => { var cards=[...document.querySelectorAll('.l-plant-card')]; var out=[];
                    cards.forEach(c => { var imgs=[...c.querySelectorAll('img')]; out.push({n:(c.querySelector('b,h3,.name')||{}).textContent||'?', imgs: imgs.length, loaded: imgs.filter(i=>i.complete && i.naturalWidth>0).length}); });
                    return out; }""")
                for c in r:
                    row("plants", "library/plants.html#" + c["n"][:40], "PASS" if c["imgs"] >= 1 and c["loaded"] == c["imgs"] else "FAIL", f"imgs {c['loaded']}/{c['imgs']}")
                row("plants", "library/plants.html", "PASS" if len(r) >= 62 else "FAIL", f"{len(r)} cards (expect >= 62)")
            elif kind == "media":
                url, sel, media = args
                ctx = br.new_context(viewport={"width": 1200, "height": 900}); pg = ctx.new_page()
                pg.goto(B + url, timeout=60000); pg.wait_for_timeout(1500)
                albums = pg.query_selector_all(".a-albums a, .a-album, a[data-album], a[href^='#']") if url == "audio.html" else []
                if albums: albums[0].click(); pg.wait_for_timeout(1500)
                groups = pg.evaluate("() => document.querySelectorAll('.l-group, .a-group, details, h2, h3').length")
                items = pg.query_selector_all(sel)
                row("media", "library/" + url, "PASS" if len(items) > 0 else "FAIL", f"{len(items)} items, {groups} groups")
                tried = set()
                for it in items:
                    key = it.evaluate("e => (e.closest('details, .l-group, section') || {}).id || e.closest('details, .l-group, section')?.querySelector('summary,h2,h3')?.textContent || 'x'")
                    if key in tried: continue
                    tried.add(key)
                    try:
                        it.evaluate("e => { for (var d = e.closest('details'); d; d = d.parentElement.closest('details')) d.open = true }")  # a user opens the group first (khan groups are closed by default)
                        it.scroll_into_view_if_needed(); it.click(timeout=5000)
                        pg.wait_for_function(f"() => {{ var m=document.getElementById('{media}'); return m && m.readyState >= 2 }}", timeout=30000)
                        row("media", "library/" + url + "#" + key[:40], "PASS", "readyState>=2")
                    except Exception as e:
                        row("media", "library/" + url + "#" + key[:40], "FAIL", str(e)[:120])
                    if len(tried) >= 12: break
            elif kind == "map":
                ctx = br.new_context(viewport={"width": 1200, "height": 900}); pg = ctx.new_page()
                errs = []; pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and not NOISE.search(m.text) else None)
                tiles = []; pg.on("response", lambda r: tiles.append(r.status) if "pmtiles" in r.url else None)
                pg.goto(B + "map.html", timeout=60000); pg.wait_for_timeout(8000)
                r = pg.evaluate("""() => { var c=document.querySelector('#map canvas'); if(!c) return {canvas:false};
                    var g=c.getContext('webgl')||c.getContext('webgl2'); var px=new Uint8Array(4*400);
                    try { g.readPixels(c.width/2-10, c.height/2-10, 20, 20, g.RGBA, g.UNSIGNED_BYTE, px); } catch(e) { return {canvas:true, err:String(e)} }
                    var nonblank=0; for (var i=0;i<px.length;i+=4){ if(px[i]+px[i+1]+px[i+2] > 0 && px[i+3] > 0) nonblank++; }
                    return {canvas:true, nonblank:nonblank, links:[...document.querySelectorAll('a[href*="noaa"], a[href*="maps/"]')].map(a=>a.getAttribute('href'))}; }""")
                bad = []
                if not r.get("canvas"): bad.append("no map canvas")
                elif not any(t in (200, 206) for t in tiles): bad.append(f"no pmtiles range responses ({len(tiles)} requests)")
                for l in r.get("links", []):
                    t = os.path.join("library", urllib.parse.unquote(l.split("#")[0].split("?")[0]))
                    if not os.path.exists(t): bad.append("missing " + l)
                if errs: bad.append("console " + errs[0][:80])
                if bad: shoot(pg, "map")
                row("map", "library/map.html", "FAIL" if bad else "PASS", "; ".join(bad) or f"tile ok, {len(r.get('links', []))} links")
            elif kind == "search":
                q, mode = args
                ctx = br.new_context(viewport={"width": 1200, "height": 900}); pg = ctx.new_page()
                pg.goto(B + "search.html?mode=" + mode, timeout=60000)
                pg.fill("#q", q); pg.keyboard.press("Enter")
                try:
                    pg.wait_for_function("() => document.querySelectorAll('#r-titles a, #r-fulltext a, #r-enc a').length > 0", timeout=60000)
                    n = pg.evaluate("() => ({t: document.querySelectorAll('#r-titles a').length, f: document.querySelectorAll('#r-fulltext a').length, e: document.querySelectorAll('#r-enc a').length, hist: !!document.querySelector('.s-histdiv, .l-src--hist')})")
                    row("search", f"search.html?mode={mode}&q={q}", "PASS", f"titles {n['t']} full {n['f']} enc {n['e']} hist {n['hist']}")
                except Exception as e:
                    shoot(pg, "search_" + re.sub(r"\W", "_", q)[:30] + "_" + mode)
                    row("search", f"search.html?mode={mode}&q={q}", "FAIL", "no rows in 60s")
        finally:
            br.close()

pages = sorted(os.path.basename(p) for p in glob.glob("library/*.html")) + \
        sorted("_app/" + os.path.basename(p) for p in glob.glob("library/_app/*.html")) + \
        sorted("_app/shelf/" + os.path.basename(p) for p in glob.glob("library/_app/shelf/*.html"))
pages = [p for p in pages if p not in ("reader.html", "chat.html")]
HIST_PDF = next(l[74:].rstrip("\n") for l in open("library/MANIFEST.sha256") if "/docs/survivor_library/" in l and l.rstrip().endswith(".pdf"))  # reader/chat need params; covered below
jobs = [("page", (u, s, w)) for u in pages for s in ("light", "dark") for w in (390, 1200)]
pdf_by_shelf = {}
for l in open("library/MANIFEST.sha256"):
    p = l[66:].rstrip("\n")
    if p.startswith("library/docs/") and p.endswith(".pdf"): pdf_by_shelf.setdefault(p.split("/")[2], []).append(p[8:])
for sh, ps in pdf_by_shelf.items():
    jobs += [("reader", x) for x in random.sample(ps, min(3, len(ps)))]
jobs += [("plants", None), ("media", ("audio.html", "#view a[data-i]", "audio")), ("media", ("video.html", "a[data-i]", "video")), ("map", None)]
QUERIES = ["water purification", "how to treat a burn", "solar panel wiring", "canning tomatoes", "splint a broken arm", "ham radio antenna",
           "chlorine dose for drinking water", "rabbit hutch", "bread without yeast", "compost toilet", "hypothermia", "tourniquet",
           "diesel generator maintenance", "wound infection antibiotics", "beekeeping", "wood stove chimney", "well pump", "snake bite",
           "radiation fallout shelter", "childbirth emergency"]
jobs += [("search", (q, m)) for q in QUERIES for m in ("both", "precise")]
# chat e2e (mocked LLM) — existing script; runs alone first, it is timing-sensitive under 8 parallel browsers
d = f"{EX}/shots/chat_e2e"; os.makedirs(d, exist_ok=True)
r = subprocess.run(["python3", "tests/pw_chat_e2e.py", d, B], capture_output=True, text=True)
row("chat", "library/chat.html", "PASS" if r.returncode == 0 else "FAIL", ((r.stdout + r.stderr).strip().splitlines() or [""])[-1][:150])
print(f"{time.strftime('%T')} t5 jobs={len(jobs)} workers={NW} base={B}", flush=True)
with ThreadPoolExecutor(NW) as ex: list(ex.map(worker, jobs))
with open(f"{EX}/results/t5{TAG}.csv", "w", newline="") as f: csv.writer(f, lineterminator="\n").writerows(rows)
print(f"{time.strftime('%T')} t5 done: {sum(r[3]=='FAIL' for r in rows)} FAIL / {len(rows)}", flush=True)
os.system(f"python3 {EX}/report.py > /dev/null")
