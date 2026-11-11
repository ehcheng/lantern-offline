#!/usr/bin/env python3
"""R12 subset validation: does an embedding sidecar fix the vocab-miss queries,
and is a pure-stdlib cosine scan fast enough to serve?

Embeds a subset of mcp.db pages (all pages of shelves relevant to the eval
queries, capped) via llamafile /embedding (:8091, nomic-embed-text-v1.5),
then runs the retrieval.md vocab-miss queries + control queries, reporting
semantic top-5 vs the FTS5 verdicts recorded in retrieval.md.

Also times the dot-product scan and extrapolates to the full 34k pages.
Usage: python3 validate_subset.py [--cap 4000]
"""
import argparse, array, json, sqlite3, time, urllib.request

DB = "library/_app/mcp/mcp.db"
EMB_URL = "http://127.0.0.1:8091/embedding"

# vocab-miss queries from the private test record (post-R5:
# apostrophe + synonym fixes landed; these are the residual semantic misses)
# each: (query, substring expected in a top-5 hit path or title, shelf hint)
EVAL = [
    ("chainsaw cut my leg badly", "bleed|wound|laceration|hemorrhage|trauma", "docs/medical"),
    ("green pond water safe to drink", "water|treat|purif|filter", "docs/water"),
    ("make water safe without fuel", "sodis|solar|disinfect|filter|water", "docs/water"),
    ("patch a roof with a tarp", "roof|shelter|repair|emergency", "docs/shelter"),
    ("how deep to dig an outhouse", "latrine|excreta|sanitation|pit", "docs/sanitation"),
    ("bug out bag list", "supply|kit|prepared|evacuat", "docs/emergency_mgmt"),
    # controls (FTS already gets these; semantic must not regress them)
    ("how to preserve meat by canning", "can|preserv|meat", "docs/food_preservation"),
    ("treat a burn", "burn", "docs/medical"),
]
SHELVES = ("docs/medical", "docs/water", "docs/sanitation", "docs/shelter",
           "docs/emergency_mgmt", "docs/food_preservation")


def embed(text, prefix):
    body = json.dumps({"content": prefix + text[:4000]}).encode()
    req = urllib.request.Request(EMB_URL, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    v = d[0]["embedding"][0] if isinstance(d, list) else d["embedding"]
    if isinstance(v[0], list):
        v = v[0]
    return array.array("f", v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=4000)
    args = ap.parse_args()

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    ph = ",".join("?" * len(SHELVES))
    rows = con.execute(
        f"select path, page, title, substr(body,1,2000) from pages where shelf in ({ph})"
        " order by path, page", SHELVES).fetchall()
    step = max(1, len(rows) // args.cap)
    rows = rows[::step]
    print(f"subset: {len(rows)} pages (1/{step} sample of shelves {SHELVES})")

    t0 = time.time()
    vecs = []
    for i, (path, page, title, body) in enumerate(rows):
        vecs.append(embed(f"{title}. {body}", "search_document: "))
        if (i + 1) % 200 == 0:
            el = time.time() - t0
            print(f"  {i+1}/{len(rows)} embedded, {el:.0f}s ({el/(i+1)*1000:.0f} ms/page)", flush=True)
    embed_s = time.time() - t0
    print(f"embedded {len(rows)} pages in {embed_s:.0f}s -> full 34k est {embed_s/len(rows)*34000/3600:.1f} h")

    import re
    hits_ok = 0
    scan_times = []
    for q, pat, shelf in EVAL:
        qv = embed(q, "search_query: ")
        t1 = time.time()
        scored = sorted(
            ((sum(a * b for a, b in zip(qv, dv)), j) for j, dv in enumerate(vecs)),
            reverse=True)[:5]
        scan_times.append(time.time() - t1)
        top = [(round(s, 3), rows[j][0], rows[j][1], rows[j][2]) for s, j in scored]
        rx = re.compile(pat, re.I)
        ok = any(rx.search(p) or rx.search(t or "") for _, p, _, t in top)
        hits_ok += ok
        print(f"\n{'HIT ' if ok else 'MISS'} {q!r}")
        for s, p, pg, t in top[:3]:
            print(f"   {s} {p} p{pg} {t[:60]}")
    n = len(rows)
    st = sum(scan_times) / len(scan_times)
    print(f"\n== {hits_ok}/{len(EVAL)} queries have a plausible top-5 hit")
    print(f"scan {n} vecs: {st*1000:.0f} ms -> 34k est {st*34000/n:.2f} s/query (pure python)")


if __name__ == "__main__":
    main()
