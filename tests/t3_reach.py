#!/usr/bin/env python3
"""T3 reachability: every content path (docs, audio, video, maps, tools, mirrors entry, datasets)
is linked from a generated page, or sits under a folder that is linked. Plus md<->html siblings
and verify_frontend.py / gen_shelves description warnings."""
import os, re, csv, html, glob, sqlite3, subprocess, urllib.parse, collections
EX = os.path.dirname(os.path.abspath(__file__)); os.chdir(f"{EX}/..")
out = open(f"{EX}/results/t3.csv", "w", newline=""); w = csv.writer(out, lineterminator="\n")
def row(c, p, st, d=""): w.writerow(["t3", c, p, st, d])
paths = [l[66:].rstrip("\n") for l in open("library/MANIFEST.sha256")]
pset = set(paths)
LINK = re.compile(r"""(?:href|src|data-f|data-src|data-path)=["']([^"']+)["']""")
QF = re.compile(r"[?&](?:f|path|p|src)=([^&\x22\x27#]+)")
# *_v1.html are the plain pages (T8); their shelf-root folder links would make every file "reachable" via autoindex
# T3 is the dev-tree tier: generated pages are read from disk, not the sealed manifest, so a shelf added
# between seals is checked before the reseal (the manifest still decides which content paths must be reached)
gen = [p for p in glob.glob("library/*.html") if not p.endswith("_v1.html")]
gen += [p for p in glob.glob("library/_app/**/*.html", recursive=True) if "/_app/text/" not in p]
gen += glob.glob("library/_app/index/*.json")
linked, folders, targets = set(), set(), set()  # targets: every href as written, manifest or not (VERSION.json is sealed after)
def add(target):
    t = os.path.normpath(target); targets.add(t)
    if t.endswith("/"): folders.add(t.rstrip("/"))
    elif t in pset: linked.add(t)
    elif os.path.isdir(t): folders.add(t)
for g in gen:
    body = open(g, encoding="utf-8", errors="replace").read()
    base = os.path.dirname(g)
    refs = LINK.findall(body) + QF.findall(body)
    if g.endswith(".json"):  # index json: any "path"-like string
        refs += re.findall(r'"(?:path|file|url|href|src|pdf|f)"\s*:\s*"([^"]+)"', body)
        refs += re.findall(r'"((?:docs|audio|video|maps|tools|mirrors|datasets|zim)/[^"]+)"', body)
    for r in refs:
        r = html.unescape(r).strip()
        if r.startswith(("http:", "https:", "//", "mailto:", "javascript:", "data:", "#")) or "${" in r: continue
        p = urllib.parse.unquote(r.split("#")[0].split("?")[0])
        if not p: continue
        add(os.path.join("library", p.lstrip("/")) if p.startswith("/") else os.path.join(base, p))
        if r.startswith(("docs/", "audio/", "video/", "maps/", "tools/", "mirrors/", "datasets/", "zim/")): add("library/" + p)
        for f in QF.findall("?" + r.partition("?")[2]): add("library/" + urllib.parse.unquote(f).lstrip("/"))
def direct(p):  # a .md row opens its rendered .html sibling (gen_shelves.doc_row)
    return p in linked or (p.endswith(".md") and p[:-3] + ".html" in linked)
def reachable(p):
    if direct(p): return True
    d = os.path.dirname(p)
    while d.startswith("library/") and d != "library":
        if d in folders: return True
        d = os.path.dirname(d)
    return False
n_ok = 0; ndirect = collections.Counter(); byfolder = collections.Counter(); folder_only = collections.defaultdict(list)
# uniformity rule (2026-10-03, EXHAUSTIVE_TEST_PLAN T3): a shelf page must list every docs/ PDF, every datasets/
# file and every tools/*/README.md itself; maps/mirrors inner files and bulk sets stay folder-reach
MUST_DIRECT = ("docs/pdf", "datasets", "tools/readme")
for p in paths:
    top = p.split("/")[1]
    if top not in ("docs", "audio", "video", "maps", "tools", "mirrors", "datasets", "zim"): continue
    if top == "mirrors" and not p.endswith(("index.html", "index.htm")): continue  # entry pages only
    if top == "maps" and re.search(r"\.(kap|bsb|00\d|0\d\d|mwm)$", p): continue  # chart cells reachable by folder only
    if top == "datasets" and re.search(r"climate_normals/[A-Z0-9]+\.csv$", p): continue  # 467 station CSVs: one described folder row
    if reachable(p):
        n_ok += 1
        k = top + ("/pdf" if p.endswith(".pdf") else "/readme" if re.fullmatch(r"library/tools/[^/]+/README\.md", p) else "")
        (ndirect if direct(p) else byfolder)[k] += 1
        if not direct(p) and k in MUST_DIRECT: folder_only[k].append(p)
    else: row("reach", p, "FAIL", "no generated page links it or its folder")
row("reach", "library", "PASS", f"linked={n_ok} pages={len(gen)} folders={len(folders)}")
# folder-only reach means "nginx autoindex would show it", not "a shelf page shows it" — report it per area, and
# MUST_DIRECT classes must be shelf rows, so folder-only there is a FAIL
for k in sorted(set(ndirect) | set(byfolder)):
    d, f = ndirect[k], byfolder[k]
    st = "FAIL" if k in MUST_DIRECT and f else "PASS"
    row("reach_direct", k, st, f"{d} linked from a page, {f} only via a folder link" + (": " + " ".join(folder_only[k][:5]) if st == "FAIL" else ""))
# uniformity: everything the plain page (index_v1) or the MCP index (mcp.db) reaches, a Lantern page reaches too
# root .md files that gen_shelves renders into a Lantern page (gen_md_page): their plain .html sibling is the same text
MD_RENDER = {f"library/{a[:-3]}.html": f"library/_app/{b}" for a, b in
             re.findall(r'gen_md_page\(f"\{LIB\}/([^"/]+\.md)", "([^"]+)"', open("build/gen_shelves.py").read())}
def reached_any(t):  # file linked, or folder linked, or something inside the folder linked
    if t in MD_RENDER and reachable(MD_RENDER[t]): return True  # FIXES #121: plain sibling of a Lantern-rendered .md
    return reachable(t) or t in targets or t in folders or any(l.startswith(t + "/") for l in linked | folders)
v1 = open("library/index_v1.html", encoding="utf-8").read()
bad = 0
for r in sorted(set(LINK.findall(v1))):
    r = html.unescape(r).strip()
    if r.startswith(("http:", "https:", "#", "mailto:")) or r.split("#")[0].endswith("_v1.html"): continue  # triage_v1.html#es
    t = os.path.normpath("library/" + urllib.parse.unquote(r.split("#")[0]))
    if t.startswith("library/zim"): continue  # kiwix-serve, never an href (known_failures)
    if not reached_any(t): bad += 1; row("v1_parity", t, "FAIL", "index_v1 links it, no Lantern page does")
row("v1_parity", "library/index_v1.html", "PASS" if not bad else "FAIL", f"{bad} targets only the plain page reaches")
db = "library/_app/mcp/mcp.db"
if os.path.exists(db) and os.path.getsize(db):
    bad = 0; n = 0
    for (mp,) in sqlite3.connect(f"file:{db}?mode=ro", uri=True).execute("select distinct path from titles"):
        if mp.startswith(("shelf:", "plants.html", "zim/")): continue
        n += 1; t = "library/" + mp
        ok = direct(t) if (t.startswith("library/docs/") and t.endswith(".pdf")) or t.startswith("library/datasets/") else reachable(t)
        if not ok: bad += 1; row("mcp_parity", t, "FAIL", "mcp.db titles row, no Lantern page row")
    row("mcp_parity", db, "PASS" if not bad else "FAIL", f"{n} mcp.db paths, {bad} without a Lantern row")
else:
    row("mcp_parity", db, "FAIL", "mcp.db missing or empty")
# md <-> html siblings at root
for p in paths:
    if re.fullmatch(r"library/[^/]+\.md", p):
        row("md_html", p, "PASS" if p[:-3] + ".html" in pset else "FAIL", "html sibling")
# verify_frontend.py
r = subprocess.run(["python3", "build/verify_frontend.py"], capture_output=True, text=True)
row("verify_frontend", "library", "PASS" if r.returncode == 0 else "FAIL", (r.stdout + r.stderr).strip().splitlines()[-1][:200] if (r.stdout + r.stderr).strip() else "")
# every shelf group described: every <details><summary> on a shelf page carries an l-sum span
bare = 0
for f in glob.glob("library/_app/shelf/*.html"):
    for m in re.finditer(r"<summary[^>]*>(.*?)</summary>", open(f, encoding="utf-8").read(), re.S):
        label = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if label.startswith(("More", "Más")): continue   # the show-more disclosure (English or Spanish tab bar) is not a content group
        if 'class="l-sum"' not in m.group(1): bare += 1; row("shelf_desc", f, "FAIL", label[:80])
row("shelf_desc", "library/_app/shelf", "PASS" if not bare else "FAIL", f"{bare} bare groups")
out.close(); os.system(f"python3 {EX}/report.py > /dev/null")
