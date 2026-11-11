#!/usr/bin/env python3
"""T8 mirror entry (FIXES #107, the owner's rule): X1 lets links INSIDE a mirror dead-end, but these must not.

  landing  every library/mirrors/<m>/ has a landing page (the page _app/shelf/mirrors.html links for it, else
           <host>/index.html; a mirror with no HTML, like meshtastic_aredn, is its folder listing) that exists,
           is non-empty and renders a body with text.
  linked   every target in library/mirrors/ that Lantern (library/*.html, library/_app/**/*.html incl. the
           _app/text/mirrors wrappers, _app/index/*.json|js), index_v1, triage, refs.json or mcp.db (loc paths) / embeddings.db
           points at exists and is not a stub: HTML renders text and is no meta-refresh; PDF/zip have their magic;
           a folder holds at least one file. Lantern search counts as a link: every HTML page pagefind indexes
           (PF_MIRRORS, feeds excluded) is a target.
  hollow   a linked HTML page whose own page links mostly dead-end is a table of contents that opens nothing
           (redteam 2026-10-05 B1): FAIL at >= HOLLOW_MIN page links and < HOLLOW_OK resolving (MediaWiki red links
           not counted: dead on the origin). Dead links on a passing page are X1 and only counted.

Rows (tier,check,path,status,detail) -> results/t8_mirror_entry.csv (folded into REPORT.md);
FAILs also -> logs/audit/t8_mirror_entry_fails.tsv (path, check, detail, linked_from).
Usage: python3 t8_mirror_entry.py [--selftest]   (read-only; mcp.db opened ?mode=ro)
"""
import csv, glob, html, json, os, re, sqlite3, sys, tempfile, urllib.parse
from collections import defaultdict
from html.parser import HTMLParser

HOLLOW_MIN, HOLLOW_OK = 10, 0.25   # B1 covers open 0-10%; a portal where 1 link in 4 opens is navigation with X1 dead ends
PF_MIRRORS = ("hesperian", "nchfp", "ready_gov")   # build_pagefind.sh indexes only these three (t4_coverage.PF_MIRRORS)
LINK = re.compile(r"""(?:href|src|data-f|data-src|data-path)\s*=\s*["']([^"']+)["']""", re.I)
QF = re.compile(r"[?&](?:f|path|p|src)=([^&\x22\x27#]+)")
SKIP = ("http:", "https:", "//", "mailto:", "javascript:", "data:", "#", "tel:")


class HP(HTMLParser):
    def __init__(s):
        super().__init__(); s.text = 0; s.body = False; s.refresh = False; s.hrefs = []; s._skip = 0
    def handle_starttag(s, tag, attrs):
        a = dict(attrs)
        if tag == "body": s.body = True
        if tag in ("script", "style"): s._skip += 1
        if tag == "meta" and (a.get("http-equiv") or "").lower() == "refresh": s.refresh = True
        if tag == "a" and a.get("href"): s.hrefs.append(a["href"])
    def handle_endtag(s, tag):
        if tag in ("script", "style") and s._skip: s._skip -= 1
    def handle_data(s, d):
        if not s._skip: s.text += len(d.strip())


def on_disk(base, ref):
    """resolve a relative/root-absolute href inside a mirror page; True if a file or non-empty dir is there"""
    raw = html.unescape(ref).split("#", 1)[0]
    for p in dict.fromkeys((raw, raw.split("?", 1)[0])):
        p = urllib.parse.unquote(p)
        if not p: return True
        t = os.path.normpath(os.path.join(base, p))
        if os.path.isfile(t) or (os.path.isdir(t) and os.listdir(t)): return True
    return False


def check_target(t, hollow=False):
    """(status, detail) for one library path"""
    if os.path.isdir(t):
        n = sum(1 for _ in os.scandir(t))
        return ("PASS", f"folder, {n} entries") if n else ("FAIL", "empty folder")
    if not os.path.isfile(t): return ("FAIL", "missing")
    size = os.path.getsize(t)
    if size == 0: return ("FAIL", "zero bytes")
    head = open(t, "rb").read(8)
    low = t.lower()
    if low.endswith(".pdf"): return ("PASS", f"PDF {size} B") if head.startswith(b"%PDF") else ("FAIL", "no %PDF header")
    if low.endswith(".zip"): return ("PASS", f"zip {size} B") if head.startswith(b"PK") else ("FAIL", "no zip header")
    if not low.endswith((".html", ".htm")) and ".htm" not in os.path.basename(low): return ("PASS", f"{size} B")
    if head.startswith(b"%PDF"): return ("FAIL", "a PDF saved under .html (renders as garbage)")
    h = HP(); h.feed(open(t, encoding="utf-8", errors="replace").read())
    if h.refresh and h.text < 50: return ("FAIL", "meta-refresh stub")
    if h.text == 0: return ("FAIL", "no visible text")
    det = f"text={h.text}"
    if not hollow: return ("PASS", det)
    base, mroot = os.path.dirname(t), mirror_root(t)
    # MediaWiki red links (action=edit&redlink=1) were dead on the origin too: X1 by definition, not counted
    pages = [r for r in h.hrefs if not r.startswith(SKIP) and not re.search(r"\.(css|js|png|jpe?g|gif|svg|ico|webp)(\?|$)", r, re.I)
             and not re.search(r"[?&](?:amp;)?(?:redlink=1|action=edit)", r)]
    # absolute links to the page's own host are dead offline too (wget left them for never-fetched pages)
    host = os.path.relpath(t, mroot).split(os.sep)[0] if mroot else ""
    own = [r for r in h.hrefs if host and re.match(rf"https?://{re.escape(host)}/", r)]
    dead = sum(1 for r in pages if not (on_disk(base, r) if not r.startswith("/") else on_disk(os.path.join(mroot, host), r.lstrip("/"))))
    total = len(pages) + len(own); ok = len(pages) - dead
    det += f", page links {ok}/{total} resolve"
    if total >= HOLLOW_MIN and ok / total < HOLLOW_OK: return ("FAIL", "hollow: " + det)
    return ("PASS", det + (f" ({total - ok} dead, X1)" if total - ok else ""))


def mirror_root(t):
    parts = os.path.normpath(t).split(os.sep)
    return os.sep.join(parts[:parts.index("mirrors") + 2]) if "mirrors" in parts and len(parts) > parts.index("mirrors") + 2 else None


def collect(lib, refs_json, mcp_db):
    """{target library path: set(sources)}; source prefixed 'mcp:' for mcp.db rows"""
    tg = defaultdict(set)
    def add(src, base, r):
        r = html.unescape(r).strip()
        if r.startswith(SKIP) or "${" in r: return
        # the link itself (relative to its page), plus viewer params like historical.html?f=mirrors/... (library-relative)
        cands = [(base, r)] + [(lib, urllib.parse.unquote(f)) for f in QF.findall("?" + r.partition("?")[2])]
        for b, c in cands:
            # index JSON, refs.json and db rows hold literal library paths ("…Unsafe?.html" is a file name); only an HTML href has a query
            p = c if not src.endswith(".html") and os.path.isfile(os.path.join(b, c)) else urllib.parse.unquote(c.split("#")[0].split("?")[0])
            if not p: continue
            t = os.path.normpath(os.path.join(lib, p.lstrip("/")) if p.startswith("/") else os.path.join(b, p))
            if t.startswith(os.path.join(lib, "mirrors") + os.sep):
                tg[t + ("/" if p.endswith("/") else "")].add(src)
    pages = glob.glob(f"{lib}/*.html") + [p for p in glob.glob(f"{lib}/_app/**/*.html", recursive=True)
                                         if "/_app/text/" not in p or "/_app/text/mirrors/" in p]
    for g in pages:
        s = open(g, encoding="utf-8", errors="replace").read()
        if "mirrors/" not in s: continue
        for r in LINK.findall(s): add(os.path.relpath(g, lib), os.path.dirname(g), r)
    for g in glob.glob(f"{lib}/_app/index/*.js*"):
        s = open(g, encoding="utf-8", errors="replace").read()
        for r in re.findall(r'"(mirrors/[^"]+)"', s): add(os.path.relpath(g, lib), lib, r)
    if refs_json and os.path.exists(refs_json):
        def walk(o):
            if isinstance(o, dict): [walk(v) for v in o.values()]
            elif isinstance(o, list): [walk(v) for v in o]
            elif isinstance(o, str) and o.startswith("mirrors/"): add("refs.json", lib, o)
        walk(json.load(open(refs_json)))
    # Lantern search (pagefind) links every HTML page of the mirrors build_pagefind.sh stages (feeds are not pages)
    for m in PF_MIRRORS:
        for d, _, fs in os.walk(os.path.join(lib, "mirrors", m)):
            if os.path.basename(d) == "feed": continue
            for fn in fs:
                if fn.lower().endswith((".html", ".htm")): tg[os.path.join(d, fn)].add("pagefind")
    if mcp_db and os.path.exists(mcp_db) and os.path.getsize(mcp_db):
        db = sqlite3.connect(f"file:{mcp_db}?mode=ro", uri=True)
        for (p,) in db.execute("select distinct path from loc where path like 'mirrors/%'"):
            tg[os.path.normpath(os.path.join(lib, p))].add("mcp:loc")
    emb = mcp_db and os.path.join(os.path.dirname(mcp_db), "embeddings.db")   # semantic search hits link these
    if emb and os.path.exists(emb) and os.path.getsize(emb):
        for (p,) in sqlite3.connect(f"file:{emb}?mode=ro", uri=True).execute("select distinct path from vectors where path like 'mirrors/%'"):
            tg[os.path.normpath(os.path.join(lib, p))].add("mcp:emb")
    return tg


def landings(lib):
    shelf = os.path.join(lib, "_app/shelf/mirrors.html")
    s = open(shelf, encoding="utf-8").read() if os.path.exists(shelf) else ""
    links = [os.path.normpath(os.path.join(os.path.dirname(shelf), html.unescape(r))) for r in LINK.findall(s)]
    out = {}
    for m in sorted(e.name for e in os.scandir(os.path.join(lib, "mirrors")) if e.is_dir()):
        root = os.path.join(lib, "mirrors", m)
        pick = next((l for l in links if l.startswith(root + os.sep) and l.endswith((".html", ".htm"))), None)
        if not pick:
            pick = next(iter(sorted(glob.glob(f"{root}/*/index.html"))), None)
        if not pick and not glob.glob(f"{root}/**/*.htm*", recursive=True): pick = root   # non-HTML mirror: the folder
        out[m] = (pick, "shelf" if pick and (pick in links or pick == root and any(l.startswith(root + os.sep) for l in links)) else "fallback")
    return out


def run(lib, refs_json, mcp_db, out_csv, out_tsv):
    rows, fails = [], []
    for m, (pick, how) in landings(lib).items():
        st, det = ("FAIL", "no landing page found") if not pick else check_target(pick, hollow=os.path.isfile(pick))
        if how == "fallback" and st == "PASS": det += ", not linked from _app/shelf/mirrors.html"
        rows.append(("landing", pick or os.path.join(lib, "mirrors", m), st, f"{m}: {det}"))
    for t, srcs in sorted(collect(lib, refs_json, mcp_db).items()):
        st, det = check_target(t.rstrip("/"), hollow=True)
        rows.append(("linked", t, st, f"{det}; from {len(srcs)}: {', '.join(sorted(srcs)[:3])}"))
    for c, p, st, d in rows:
        if st == "FAIL": fails.append((p, c, d))
    if out_csv:
        with open(out_csv, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            for c, p, st, d in rows: w.writerow(["t8", "mirror_" + c, p, st, d])
    if out_tsv:
        with open(out_tsv, "w") as f:
            f.write("path\tcheck\tdetail\n"); f.writelines(f"{p}\t{c}\t{d}\n" for p, c, d in fails)
    return rows, fails


def selftest():
    d = tempfile.mkdtemp(); lib = os.path.join(d, "library")
    def w(p, s):
        p = os.path.join(lib, p); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(s)
    good = "<html><body><p>Real content here.</p>" + "".join(f'<a href="p{i}.html">x</a>' for i in range(12)) + "</body></html>"
    w("mirrors/a/a.org/index.html", good)
    for i in range(12): w(f"mirrors/a/a.org/p{i}.html", "<body>page</body>")
    w("mirrors/b/b.org/index.html", "<html><body><p>toc</p>" + "".join(f'<a href="gone{i}.html">x</a>' for i in range(12)) + "</body></html>")
    w("mirrors/c/c.org/index.html", '<HTML><HEAD><META HTTP-EQUIV="Refresh" CONTENT="0; URL=https://c.org/x"></HEAD><BODY></BODY></HTML>')
    w("mirrors/c/c.org/real.html", "<body>ok text</body>")
    w("mirrors/d/files/fw.zip", "PK\x03\x04zip")
    w("mirrors/hesperian/x.org/hhg/Red.html", "<body><p>chapter text</p><a href='p.html'>p</a>" + "".join(
        f'<a href="/w/index.php?title=T{i}&amp;action=edit&amp;redlink=1">r</a>' for i in range(12)) + "</body>")
    w("mirrors/hesperian/x.org/hhg/p.html", "<body>ok</body>")
    w("mirrors/hesperian/x.org/hhg/Cover.html", "<body><p>cover</p>" + "".join(f'<a href="Ch{i}.html">c</a>' for i in range(12)) + "</body>")
    w("mirrors/a/a.org/fake.pdf", "<html>not a pdf</html>")
    w("_app/shelf/mirrors.html", '<a href="../../mirrors/a/a.org/index.html">a</a><a href="../../mirrors/c/c.org/real.html">c</a>')
    w("triage.html", '<a href="mirrors/b/b.org/index.html">b</a><a href="mirrors/a/a.org/missing.html">m</a>'
      '<a href="mirrors/c/c.org/index.html">stub</a><a href="mirrors/a/a.org/fake.pdf">f</a><a href="mirrors/d/">d</a>'
      '<a href="mirrors/a/a.org/p3.html#sec">ok</a>')
    open(os.path.join(d, "refs.json"), "w").write('{"docs":{"k":{"href":"mirrors/a/a.org/p4.html"}}}')
    rows, fails = run(lib, os.path.join(d, "refs.json"), None, None, None)
    got = {(c, os.path.relpath(p.rstrip("/"), lib)): st for c, p, st, _ in rows}
    want = {("landing", "mirrors/a/a.org/index.html"): "PASS", ("landing", "mirrors/b/b.org/index.html"): "FAIL",
            ("landing", "mirrors/c/c.org/real.html"): "PASS", ("landing", "mirrors/d"): "PASS",
            ("linked", "mirrors/b/b.org/index.html"): "FAIL", ("linked", "mirrors/a/a.org/missing.html"): "FAIL",
            ("linked", "mirrors/c/c.org/index.html"): "FAIL", ("linked", "mirrors/a/a.org/fake.pdf"): "FAIL",
            ("linked", "mirrors/d"): "PASS", ("linked", "mirrors/a/a.org/p3.html"): "PASS",
            ("linked", "mirrors/a/a.org/p4.html"): "PASS", ("linked", "mirrors/hesperian/x.org/hhg/Red.html"): "PASS",
            ("linked", "mirrors/hesperian/x.org/hhg/Cover.html"): "FAIL"}
    bad = {k: (got.get(k), v) for k, v in want.items() if got.get(k) != v}
    assert not bad, f"selftest mismatches (got, want): {bad}\nall: {got}"
    print(f"t8_mirror_entry selftest: OK ({len(want)} cases)")


if __name__ == "__main__":
    if "--selftest" in sys.argv: selftest(); sys.exit(0)
    EX = os.path.dirname(os.path.abspath(__file__)); os.chdir(f"{EX}/..")
    rows, fails = run("library", "data/refs.json", "library/_app/mcp/mcp.db",
                      f"{EX}/results/t8_mirror_entry.csv", "logs/audit/t8_mirror_entry_fails.tsv")
    n = defaultdict(int)
    for c, _, st, _ in rows: n[(c, st)] += 1
    print("t8_mirror_entry:", dict(sorted(n.items())), f"FAIL={len(fails)}")
    for p, c, d in fails[:40]: print(f"  FAIL {c} {p} :: {d[:160]}")
