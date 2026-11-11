#!/usr/bin/env python3
"""T4 search coverage on the dev DBs: every docs/ PDF and docs+mirrors HTML page in mcp.db loc
and in pagefind; every docs/ path has an embedding; known-item retrieval (gold jsonl + 500
deterministic phrase queries); every shelf title at rank 1. Needs :8090 (mcp_server) up, sandbox off.
Usage: python3 t4_coverage.py [base_url]   base_url defaults to the dev server http://127.0.0.1:8765/ (which proxies
/mcp and /semantic to :8090); the seal chain also runs it against the Pi, http://10.10.10.10/ (same routes via nginx)."""
import os, re, csv, json, gzip, glob, random, sqlite3, sys, time, urllib.request, urllib.parse
EX = os.path.dirname(os.path.abspath(__file__)); os.chdir(f"{EX}/..")
B = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/").rstrip("/") + "/"
TAG = "" if "127.0.0.1" in B else "_" + re.sub(r"\W+", "_", B.split("//", 1)[1]).strip("_")
out = open(f"{EX}/results/t4{TAG}.csv", "w", newline=""); w = csv.writer(out, lineterminator="\n")
def row(c, p, st, d=""): w.writerow(["t4", c, p, st, d])
random.seed(4)
paths = [l[66:].rstrip("\n")[8:] for l in open("library/MANIFEST.sha256")]  # without library/
db = sqlite3.connect("file:library/_app/mcp/mcp.db?mode=ro", uri=True)
loc = {r[0] for r in db.execute("select distinct path from loc")}
titles = {r[0]: r[1] for r in db.execute("select path, title from titles")}
emb = {r[0] for r in sqlite3.connect("file:library/_app/mcp/embeddings.db?mode=ro", uri=True).execute("select distinct path from vectors")}
pf, pf_raw, rawof = set(), set(), {}
for f in glob.glob("library/_app/pagefind*/fragment/*.pf_fragment"):
    raw = gzip.open(f).read()
    m = re.search(rb'"url":"((?:[^"\\]|\\.)*)"', raw)   # the url may hold \" (hesperian titles with quotes)
    if m:
        raw = json.loads('"' + m.group(1).decode() + '"').lstrip("/")
        u = urllib.parse.unquote(raw)
        if u.endswith("/"): u += "index.html"
        pf.add(u); pf_raw.add(raw); rawof[u] = raw   # a few mirror file names hold a literal %2F
pf_norm = {re.sub(r"^_app/text/", "", p).split(".c1.html")[0].split(".html")[0] if p.startswith("_app/text/") else p for p in pf}
def in_pf(p):
    return p in pf or p in pf_raw or p in pf_norm or p.rsplit(".", 1)[0] in pf_norm or ("_app/text/" + p + ".c1.html") in pf
docs_pdf = [p for p in paths if p.startswith("docs/") and p.endswith(".pdf")]
PF_MIRRORS = ("mirrors/hesperian/", "mirrors/nchfp/", "mirrors/ready_gov/")  # build_pagefind.sh indexes only these three
docs_html = [p for p in paths if (p.startswith("docs/") or p.startswith(PF_MIRRORS)) and p.endswith((".html", ".htm")) and "/feed/" not in p and not p.endswith("feed/index.html")
             and "/wp-content/uploads/" not in p   # WordPress attachment pages (one image, no text) are not content
             and "/wp-json/" not in p and "store.hesperian.org/collections/" not in p]   # REST dump and shop listings are not pages
def thin(p):   # a page with less visible text than gen_text's MIN_TEXT (200 chars) is below the index floor, like a PDF without a text layer
    try:
        t = re.sub(r"<script.*?</script>|<style.*?</style>", "", open("library/" + p, encoding="utf-8", errors="replace").read(), flags=re.S)
        return len(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))) < 200
    except OSError:
        return False
import subprocess
def no_text_layer(p):   # gen_text's floor: under MIN_TEXT (200) chars of extractable text = nothing to index (drawings, blank scans)
    try:
        t = subprocess.run(["pdftotext", "-enc", "UTF-8", "library/" + p, "-"], capture_output=True, text=True, timeout=120).stdout
        return len("".join(t.split())) < 200
    except Exception:
        return False
# FIXES #111 (r19): byte-identical copies in data/noncanonical_paths.txt stay on disk but are indexed once,
# through their canonical twin (keep_path in data/fix79_duplicate_files.tsv). A non-canonical path PASSes a
# per-document check when its twin does, and FAILs when the copy itself shows up in an index (the skip broke).
NONCANON = {l.strip() for l in open("data/noncanonical_paths.txt") if l.strip() and not l.startswith("#")}
GROUP = {}   # tsv pairs joined into duplicate groups (some groups span 3+ copies; keep/remove columns were flipped for some)
for r in csv.reader(open("data/fix79_duplicate_files.tsv"), delimiter="\t"):
    if len(r) < 2 or r[0] == "keep_path": continue
    g = GROUP.get(r[0], {r[0]}) | GROUP.get(r[1], {r[1]})
    for x in g: GROUP[x] = g
TWIN = {p: sorted(x for x in GROUP.get(p, ()) if x not in NONCANON)[:1] for p in NONCANON}
TWIN = {p: t[0] for p, t in TWIN.items() if t}   # the canonical copy of each non-canonical path
def noncanon_rows(p, kind):
    t = TWIN.get(p)
    hits = [c for c, ok in (("loc", p in loc), ("pagefind", in_pf(p)), ("embedding", p in emb), ("titles", p in titles)) if ok]
    for c in ("loc", "pagefind", "embedding") if kind == "pdf" else ("pagefind",):
        twin_ok = bool(t) and {"loc": t in loc, "pagefind": in_pf(t), "embedding": t in emb}[c]
        if hits: row(c, p, "FAIL", "non-canonical copy is indexed (%s); only its twin should be" % ",".join(hits))
        else: row(c, p, "PASS" if twin_ok else "FAIL", "non-canonical; twin %s %s" % (t or "(none in fix79_duplicate_files.tsv)", "indexed" if twin_ok else "NOT indexed"))
for p in docs_pdf:
    if p in NONCANON: noncanon_rows(p, "pdf"); continue
    if not (p in loc and in_pf(p) and p in emb) and no_text_layer(p) and not os.path.exists(f"library/_app/text/{p}.c1.html"):   # E2: a vision-description wrapper makes a drawing indexable
        for c in ("loc", "pagefind", "embedding"): row(c, p, "SKIP", "no text layer (OCR found none); below the index floor")
        continue
    row("loc", p, "PASS" if p in loc else "FAIL", "mcp.db loc")
    row("pagefind", p, "PASS" if in_pf(p) else "FAIL", "pagefind url")
    row("embedding", p, "PASS" if p in emb else "FAIL", "embeddings.db")
for p in docs_html:
    if p in NONCANON: noncanon_rows(p, "html"); continue
    if not os.path.exists("library/" + p):
        row("pagefind", p, "FAIL", "in MANIFEST, not on disk (reseal)"); continue
    if open("library/" + p, "rb").read(5) == b"%PDF-":
        row("pagefind", p, "SKIP", "a PDF saved under .html"); continue
    ok = in_pf(p)
    row("pagefind", p, "PASS" if ok else "SKIP" if thin(p) else "FAIL", "pagefind url" if ok else "under 200 chars of text" if thin(p) else "pagefind url")
# stale entries: index lists paths not on disk (Refrigeration_ until reseal)
pset = set(paths)
for p in sorted(loc - pset): row("stale_loc", p, "FAIL", "in mcp.db, not in manifest")
for p in sorted(emb - pset): row("stale_emb", p, "FAIL", "in embeddings.db, not in manifest")
for p in sorted(x for x in pf if x.startswith(("docs/", "mirrors/")) and x not in pset and x.split("#")[0] not in pset and x.split("?")[0] not in pset and rawof.get(x) not in pset):
    row("stale_pagefind", p, "FAIL", "in pagefind, not in manifest")
print(f"{time.strftime('%T')} coverage: loc={len(loc)} emb={len(emb)} pf={len(pf)} pdf={len(docs_pdf)} html={len(docs_html)}", flush=True)
# search helpers via :8090
def mcp(name, args):
    req = urllib.request.Request(B + "mcp", data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}}).encode(),
                                 headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    return json.loads(d["result"]["content"][0]["text"])
# known-item gold
def sem(q, lang="eng"):
    try: return [h["path"] for h in json.load(urllib.request.urlopen(B + "semantic?limit=8&lang=%s&q=%s" % (lang, urllib.parse.quote(q)), timeout=120))]
    except Exception: return []
def fts(q, n=8, table="pages", phrase=False):
    toks = re.findall(r"\w+", q)
    if not toks: return []
    q = '"%s"' % " ".join(toks) if phrase else " ".join('"%s"' % t for t in toks)
    try: return [r[0] for r in db.execute(f"select path from {table} where {table} match ? order by rank limit ?", (q, n))]
    except sqlite3.OperationalError: return []
# known-item gold: v2 (2026-10-03, 40 questions written FROM the pages, 6 Spanish incl. 2 encyclopedia) is the gate at 80%;
# v1 (H37, 39 questions) stays as a regression row at its 2026-09 baseline 26/39
# v3 (E1d 2026-10-04, 100 plain-words questions, 50 Spanish on Spanish pages, written blind) is measured beside v2 with a 65% floor; it becomes the
# gate once it beats v2's hit rate (PROGRESS E1d)
GOLD = (("v2", "data/known_items_v2.jsonl", 0.80, "gate"), ("v3", "data/known_items_v3.jsonl", 0.65, "regression floor 65 (2026-10-06, fix87: dev 67/100); becomes the gate when it beats v2 (PROGRESS item 5)"),
        ("v1", "data/known_items.jsonl", 0.64, "regression, baseline 26/39; 36 items since 2026-10-06 (K26 K28 K29 struck per the owner's veto in known_items_review.md)"))
from playwright.sync_api import sync_playwright
import os
# T5_PROXY=127.0.0.1:8766: same forwarding proxy as t5_render (macOS Local Network privacy blocks Chrome from the Pi)
pw = sync_playwright().start(); br = pw.chromium.launch(args=["--disable-features=LocalNetworkAccessChecks,BlockInsecurePrivateNetworkRequests"] + (["--proxy-server=" + os.environ["T5_PROXY"]] if os.environ.get("T5_PROXY") else [])); pg = br.new_page(viewport={"width": 390, "height": 844})  # Chromium 147 blocks the dev page's cross-port kiwix/mcp calls (round-10 M7)
def page_hits(q, lang):
    pg.goto(B + "search.html?mode=both" + ("&lang=" + lang if lang != "eng" else ""), timeout=60000)
    pg.fill("#q", q); pg.keyboard.press("Enter")
    try: pg.wait_for_function("window.__lanternFT && window.__lanternFT.q === %s" % json.dumps(q), timeout=120000)   # set once all three Pagefind indexes answered (#90)
    except Exception: return []
    pg.wait_for_timeout(500)
    try: pg.wait_for_function("() => document.querySelectorAll('#r-enc a.l-doc-row').length > 0", timeout=8000)   # kiwix answers after fulltext
    except Exception: pass
    def rel(h):
        h = h or ""
        if "/viewer#" in h: return "zim/" + urllib.parse.unquote(h.split("/viewer#", 1)[1]).split("?")[0]   # encyclopedia row -> zim/<book>/<article>
        m = re.search(r"[?&]f=([^&]+)", h)
        return urllib.parse.unquote(m.group(1)) if m else urllib.parse.unquote(h).split("#")[0].split("?")[0].lstrip("./")
    body = pg.evaluate("() => [...document.querySelectorAll('#r-fulltext .l-result a.title')].map(a => a.getAttribute('href'))")
    titles = pg.evaluate("() => [...document.querySelectorAll('#r-pin a.l-doc-row, #r-titles a.l-doc-row')].filter(a => !a.closest('nav.l-emerg') && (!a.closest('details.s-cards') || a.querySelector('b'))).map(a => a.getAttribute('href'))")   # r40 R1 (#283): the open card list after a match is cards, not document hits (the bold matched row still counts)
    enc = pg.evaluate("() => [...document.querySelectorAll('#r-enc a.l-doc-row')].map(a => a.getAttribute('href'))")
    return [rel(h) for h in body] + [rel(h) for h in titles][:3] + [rel(h) for h in enc][:8]   # every rendered fulltext row, a title hit, or an encyclopedia row
hit = 0
for tag, path, bar, role in GOLD:
    if not os.path.exists(path): row(f"known_gold_{tag}", "summary", "FAIL", f"{path} missing"); continue
    gold = [json.loads(l) for l in open(path) if l.strip()]; hit = 0
    for g in gold:
        hits = page_hits(g["q"], "spa" if g.get("lang") == "spa" else "eng")
        ok = g["expect_path"] in hits
        hit += ok; row(f"known_gold_{tag}", g["expect_path"], "PASS" if ok else "FAIL", f"{g['id']} top8 for: {g['q'][:60]}")
    row(f"known_gold_{tag}", "summary", "PASS" if hit >= bar * len(gold) else "FAIL", f"{hit}/{len(gold)} in top 8 on search.html (Both); {role}, bar {bar:.0%}")
    print(f"{time.strftime('%T')} known_gold_{tag}: {hit}/{len(gold)}", flush=True)
br.close(); pw.stop()
BOILER = re.compile(r"project gutenberg|buy this book|all rights reserved|course materials and make them|creative commons|table of contents|www\.|copyright|isbn", re.I)
# deterministic known-item: a distinctive 6-word phrase from 500 random indexed pages must return its doc top-3
# #89 (2026-10-06): the sample came from sqlite random() (unseeded, a new 500 every run) and all 12 misses of the r18 run
# were phrases that other documents also print ("have been described under the name", two STI pistol manuals, five
# Collaborative Statistics editions): FTS found every one, just not top-3 among identical text. Rows are now picked with
# the seeded Python RNG, and a phrase found on 3+ pages of OTHER documents is not distinctive and is re-drawn. A phrase
# found nowhere is kept: that is a real index defect and fails.
maxrow = db.execute("select max(rowid) from pages").fetchone()[0]
rowids = random.sample(range(1, maxrow + 1), 1600)
sample = [r for rid in rowids for r in db.execute("select path, page, body from pages where rowid = ?", (rid,))]
def others(q, path):
    return db.execute("select count(*) from (select 1 from pages where pages match ? and path != ? limit 3)", ('"%s"' % q, path)).fetchone()[0]
n = ok = 0
for path, page, body in sample:
    toks = (body or "").split()
    if len(toks) < 60: continue
    lo, hi = int(len(toks) * 0.3), int(len(toks) * 0.7)   # E8: middle of the body only (no front matter, no license tail)
    for _ in range(20):  # a run of 6 consecutive plain words (FTS5 phrase must match the body verbatim)
        i = random.randrange(lo, hi - 6); run = toks[i:i + 6]
        if not all(re.fullmatch(r"[A-Za-z]{3,}", t) for t in run): continue
        ctx = " ".join(toks[max(0, i - 16):i + 22])[:200]   # the surrounding ~200 chars must not read as boilerplate
        if not BOILER.search(ctx) and others(" ".join(run), path) < 3: break
    else: continue
    q = " ".join(run)
    good = path in fts(q, 3, phrase=True)
    n += 1; ok += good
    row("known_phrase", path, "PASS" if good else "FAIL", f"p{page} q={q[:60]}")
    if n >= 500: break
row("known_phrase", "summary", "PASS" if n and ok >= 0.9 * n else "FAIL", f"{ok}/{n} top3")
print(f"{time.strftime('%T')} known_phrase {ok}/{n}", flush=True)
# title search: shelf titles return themselves at rank 1 (sample 500 of the titles table)
random.seed(4); tl = list(titles.items()); random.shuffle(tl)   # own seed: the phrase sampler's draws don't move the title sample
ok = n = 0
for path, title in tl[:500]:
    hits = fts(title, 1, "titles")
    good = bool(hits) and (hits[0] == path or titles.get(hits[0]) == title)   # duplicate titles (two printings) tie at rank 1
    n += 1; ok += good
    row("title_rank1", path, "PASS" if good else "FAIL", f"title={title[:60]}" + ("" if good else f" got={hits[0][:60] if hits else 'none'}"))
row("title_rank1", "summary", "PASS" if ok >= 0.9 * n else "FAIL", f"{ok}/{n} rank1")
print(f"{time.strftime('%T')} t4 done: title rank1 {ok}/{n}", flush=True)
out.close(); os.system(f"python3 {EX}/report.py > /dev/null")
