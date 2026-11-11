#!/usr/bin/env python3
"""T2 serving check against the Pi. HEAD every manifest path (16 keep-alive threads),
MIME/Range rules, /discs/, kiwix, kolibri, MCP. Resumable on the HEAD crawl.
Usage: python3 t2_serve.py [ip] [threads]   (needs the dev tree for sizes)"""
import sys, os, csv, json, random, re, time, threading, http.client, urllib.parse
from concurrent.futures import ThreadPoolExecutor
IP = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LANTERN_IP", "10.10.10.10")
NT = int(sys.argv[2]) if len(sys.argv) > 2 else 16
HOST = {"Host": "library.lan"}
EX = os.path.dirname(os.path.abspath(__file__)); OUT = f"{EX}/results/t2.csv"
os.chdir(f"{EX}/..")
random.seed(2)
tl = threading.local()
lock = threading.Lock()
out = open(OUT, "a", newline=""); w = csv.writer(out, lineterminator="\n")
def row(check, path, st, det=""):
    with lock: w.writerow(["t2", check, path, st, det]); out.flush()

def conn(port=80):
    c = getattr(tl, "c%d" % port, None)
    if c is None: c = http.client.HTTPConnection(IP, port, timeout=30); setattr(tl, "c%d" % port, c)
    return c
def req(method, path, port=80, headers=None, body=None, retry=2):
    h = dict(HOST if port == 80 else {}); h.update(headers or {})
    url = path  # callers pass URL-encoded paths
    for i in range(retry + 1):
        try:
            c = conn(port); c.request(method, url, body=body, headers=h); r = c.getresponse()
            data = r.read() if method != "HEAD" else b""
            return r.status, dict(r.getheaders()), data
        except Exception as e:
            setattr(tl, "c%d" % port, None); err = e
            if i == retry: return 0, {}, str(err).encode()

# 1. HEAD every manifest path, Content-Length == dev size
done = set()
# a PASS carries over only while the manifest line (sha + path) is unchanged: results/t2.manifest = manifest of the last run
same = set(open(f"{EX}/results/t2.manifest")) & set(open("library/MANIFEST.sha256")) if os.path.exists(f"{EX}/results/t2.manifest") else set()
same = {l[66:].rstrip("\n") for l in same}
if os.path.exists(OUT):
    for r in csv.reader(open(OUT, newline="")):
        if len(r) > 3 and r[1] == "head" and r[2] in same:  # last row wins: an old PASS must not hide a later FAIL
            (done.add if r[3] == "PASS" else done.discard)(r[2])
paths = [l[66:].rstrip("\n") for l in open("library/MANIFEST.sha256")]
todo = [p for p in paths if p not in done]
print(f"{time.strftime('%T')} t2 head todo={len(todo)} done={len(done)} threads={NT}", flush=True)
MIME = {".apk": "application/vnd.android.package-archive", ".md": "text/plain", ".pdf": "application/pdf",
        ".html": "text/html", ".mp4": "video/mp4", ".mp3": "audio/mpeg", ".json": "application/json", ".css": "text/css"}
def head(p):
    url = urllib.parse.quote("/" + p[len("library/"):], safe="/")  # literal ? and % in mirror filenames must be %3F / %25
    try: size = os.path.getsize(p)
    except OSError: size = -1
    st, h, _ = req("HEAD", url)
    cl = int(h.get("Content-Length", -2))
    # FIXES #151 (F8): nginx returns 404 for the raw MCP databases and the Kolibri data folder on purpose (doses, sessions)
    if p.startswith(("library/_app/mcp/", "library/kolibri_data/")):
        row("head", p, "PASS" if st == 404 else "FAIL", f"denied path status {st}"); return
    if st != 200: row("head", p, "FAIL", f"status {st}"); return
    if cl != size: row("head", p, "FAIL", f"len {cl} != {size}"); return
    ext = os.path.splitext(url.split("?")[0])[1].lower()
    ct = h.get("Content-Type", "").split(";")[0]
    if ext in MIME and ct != MIME[ext]: row("mime", p, "FAIL", f"{ext} -> {ct}"); return
    if ext in (".mp4", ".pmtiles", ".mp3"):
        st2, h2, _ = req("GET", url, headers={"Range": "bytes=0-1023"})
        if st2 != 206: row("range", p, "FAIL", f"range status {st2}"); return
    row("head", p, "PASS", str(size))
n = 0
with ThreadPoolExecutor(NT) as ex:
    for _ in ex.map(head, todo):
        n += 1
        if n % 20000 == 0: print(f"{time.strftime('%T')} head {n}/{len(todo)}", flush=True)
print(f"{time.strftime('%T')} head done", flush=True)

# 2. /discs/: every disc lists, 20 random files per disc fetch 200
HREF = re.compile(r'href="([^"]+)"')
def listing(path):
    st, h, b = req("GET", path)
    return [x for x in HREF.findall(b.decode("utf-8", "replace")) if x != "../"] if st == 200 else None
def walk(path, depth=0, acc=None):
    acc = [] if acc is None else acc
    for x in listing(path) or []:
        if x.endswith("/"):
            if depth < 4: walk(path + x, depth + 1, acc)
        else: acc.append(path + x)
        if len(acc) > 400: break
    return acc
discs = listing("/discs/") or []
isos = [p for p in paths if p.endswith(".iso")]
if len(discs) != len(isos): row("discs", "/discs/", "FAIL", f"{len(discs)} mounted vs {len(isos)} iso in manifest")
else: row("discs", "/discs/", "PASS", f"{len(discs)} discs")
for d in discs:
    files = walk("/discs/" + d)
    if not files: row("discs", "/discs/" + d, "FAIL", "no files listed"); continue
    bad = [f for f in random.sample(files, min(20, len(files))) if req("HEAD", f)[0] != 200]
    row("discs", "/discs/" + d, "FAIL" if bad else "PASS", f"{len(bad)} bad of 20; e.g. {bad[0]}" if bad else f"{len(files)} files seen")

# 3. kiwix: catalog lists all zims, 25 random per book
st, h, b = req("GET", "/catalog/v2/entries?count=-1", 8080)
cat = b.decode("utf-8", "replace")
books = re.findall(r'href="/content/([^"]+)"', cat)
zims = [os.path.basename(p)[:-4] for p in paths if p.endswith(".zim")]
for z in zims:
    b1 = z if z in books else z.rsplit("_", 1)[0]
    if b1 not in books: row("kiwix", "library/zim/" + z + ".zim", "FAIL", "not in catalog"); continue
    ok = 0
    for _ in range(25):
        s, hh, _ = req("GET", "/random?content=" + b1, 8080)
        if s == 302:
            loc = hh.get("Location", "")
            s = req("GET", urllib.parse.urlparse(loc).path, 8080)[0]
        ok += s == 200
    row("kiwix", "library/zim/" + z + ".zim", "PASS" if ok >= 23 else "FAIL", f"random {ok}/25")
row("kiwix", "catalog", "PASS" if len(books) == len(zims) else "FAIL", f"catalog {len(books)} vs {len(zims)} zim files")

# 4. kolibri: channels + 50 random nodes fetch
st, h, b = req("GET", "/api/public/v1/channels", 8081)
chans = json.loads(b) if st == 200 else []
dbs = [p for p in paths if "/content/databases/" in p]
row("kolibri", "channels", "PASS" if chans and len(chans) == len(dbs) else "FAIL", f"{len(chans)} channels vs {len(dbs)} dbs")
nodes = []
for c in chans:
    s, _, bb = req("GET", f"/api/content/contentnode/?channel_id={c['id']}&max_results=50", 8081)
    if s == 200: nodes += json.loads(bb).get("results", [])
sample = random.sample(nodes, min(50, len(nodes)))
bad = [x["id"] for x in sample if req("GET", f"/api/content/contentnode/{x['id']}/", 8081)[0] != 200]
row("kolibri", "nodes", "FAIL" if bad else "PASS", f"{len(bad)} bad of {len(sample)}")

# 5. MCP: tools/list, read_document on 200 random docs paths < 2 s each
def mcp(payload):
    t = time.time()
    s, _, bb = req("POST", "/mcp", body=json.dumps(payload),
                   headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    return s, bb.decode("utf-8", "replace"), time.time() - t
s, bb, _ = mcp({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
row("mcp", "tools/list", "PASS" if s == 200 and "read_document" in bb else "FAIL", f"status {s}")
docs = [p for p in paths if p.startswith("library/docs/") and p.endswith(".pdf")]
slow = bad = 0
for p in random.sample(docs, min(200, len(docs))):
    s, bb, dt = mcp({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "read_document", "arguments": {"path": p[8:], "page": 1, "pages": 1}}})
    okk = s == 200 and '"error"' not in bb[:300] and len(bb) > 200
    if not okk: bad += 1; row("mcp", p, "FAIL", f"read_document status {s} len {len(bb)} {dt:.1f}s")
    elif dt > 2: slow += 1; row("mcp", p, "FAIL", f"read_document {dt:.1f}s > 2s")
    else: row("mcp", p, "PASS", f"{dt:.2f}s")
print(f"{time.strftime('%T')} t2 done: mcp bad={bad} slow={slow}", flush=True)
out.close()
os.system(f"python3 {EX}/report.py > /dev/null")
import shutil; shutil.copy("library/MANIFEST.sha256", f"{EX}/results/t2.manifest")   # resume key for the next run
