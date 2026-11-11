#!/usr/bin/env python3
"""R12: precompute nomic-embed vectors for every mcp.db pages row.

Sidecar DB (library/_app/mcp/embeddings.db) so build_mcp_index.py rebuilds
don't wipe vectors; rows are keyed (path, page) to survive re-index. Embeds
"search_document: {title}. {body[:2000]}" per page via llamafile /embedding
(:8091, nomic-embed-text-v1.5.f16, start with -b 2048 -ub 2048 -c 2048).
Resumable: skips (path,page) rows already present. Stdlib only.
H37c: historical shelves (survivor_library, cd3wd, HISTORICAL) get ONE vector
per document, keyed page=0, from title + the first ~2000 chars of the doc, so
the scan stays ~34k modern pages + ~7.5k historical docs. mcp_server returns
those hits with page 0 (= no page), shelf from the path.
ponytail: still 768 x float32; matryoshka-256 float16 is the upgrade path if
the Pi scan budget forces it.
RT5 E2 (#207, b2 F11; 10-17 E6): the Spanish Hesperian pages (NO_VECTOR, #144) get vectors again, in their own
table vectors_es, which mcp_server scores for Spanish-mode queries only, so they can never take an English slot.
Usage: python3 build_embeddings.py [--limit N] [--src mcp.db] [--dst embeddings.db] [--es-only]
"""
import argparse, array, json, os, sqlite3, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "library", "_app", "mcp", "mcp.db")
DST = os.path.join(ROOT, "library", "_app", "mcp", "embeddings.db")
EMB_URL = "http://127.0.0.1:8091/embedding"
MODEL = "nomic-embed-text-v1.5.f16"
DIMS = 768
HISTORICAL = ("docs/survivor_library", "docs/cd3wd", "docs/HISTORICAL", "docs/school_textbooks")  # one vector per doc: historical shelves + the development/textbook tier (2026-10-01)
DOC_CHARS = 2000
# FIXES #144 (10-09, S1): Spanish Hesperian pages stay fulltext-only. The English-centred model (#117) scores every
# Spanish page 0.63-0.70 against any Spanish question, so 1,684 of them crowded the right CD3WD answers out of the top 8.
NO_VECTOR = ("mirrors/hesperian/es.hesperian.org/",)
# E2/E6: ...so they live in vectors_es, never in vectors (the table English-mode scoring reads)
ES_TABLE_PREFIX = NO_VECTOR


def embed(text):
    body = json.dumps({"content": "search_document: " + text[:4000]}).encode()
    req = urllib.request.Request(EMB_URL, body, {"Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read())
            v = d[0]["embedding"] if isinstance(d, list) else d["embedding"]
            while isinstance(v[0], list):
                v = v[0]
            assert len(v) == DIMS, f"got {len(v)} dims"
            return array.array("f", v)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--src", default=SRC, help="mcp.db to read (default library/_app/mcp/mcp.db)")
    ap.add_argument("--dst", default=DST, help="sidecar to write (default library/_app/mcp/embeddings.db); a $TMPDIR copy for tests")
    ap.add_argument("--es-only", action="store_true", help="only the vectors_es table (the English table is not touched)")
    args = ap.parse_args()

    src = sqlite3.connect(f"file:{args.src}?mode=ro", uri=True)
    dst = sqlite3.connect(args.dst)
    dst.executescript(
        "create table if not exists meta(k text primary key, v text);"
        "create table if not exists vectors("
        " path text, page integer, vec blob, primary key(path, page)) without rowid;"
        "create table if not exists vectors_es("
        " path text, page integer, vec blob, primary key(path, page)) without rowid;")
    dst.execute("insert or replace into meta values('model', ?)", (MODEL,))
    dst.execute("insert or replace into meta values('dims', ?)", (str(DIMS),))
    dst.execute("insert or replace into meta values('prefix_doc', 'search_document: ')")
    dst.execute("insert or replace into meta values('prefix_query', 'search_query: ')")

    es_todo = embed_es(src, dst, args.limit)
    if args.es_only:
        print(f"done (es only): {es_todo} added, {os.path.getsize(args.dst)/1e6:.0f} MB")
        return
    # prune: a resumable sidecar never forgot a path, so vectors for files that left the manifest (cd3wd_disk1and2
    # reorganised) kept surfacing as dead semantic hits (T4 stale_emb, 105 on 2026-10-04)
    valid = {p for (p,) in src.execute("select distinct path from pages") if not p.startswith(NO_VECTOR)}
    stale = [p for (p,) in dst.execute("select distinct path from vectors") if p not in valid]
    for p in stale:
        dst.execute("delete from vectors where path = ?", (p,))
    dst.commit()
    print(f"pruned {len(stale)} paths no longer in mcp.db", flush=True)
    have = {(p, g) for p, g in dst.execute("select path, page from vectors")}
    hist_q = " or ".join("shelf = ?" for _ in HISTORICAL)
    rows = src.execute(
        f"select path, page, title, substr(body,1,{DOC_CHARS}) from pages "
        f"where not ({hist_q}) order by path, page", HISTORICAL).fetchall()
    # historical: one row per doc, page 0, title + first DOC_CHARS chars. Streamed
    # in rowid order (no ORDER BY: sorting ~2M bodies would spill to disk); the
    # first-seen rows of a doc are its .c1 wrapper's pages in ascending order.
    docs, order = {}, []
    for path, page, title, body in src.execute(
            f"select path, cast(page as integer), title, substr(body,1,{DOC_CHARS}) "
            f"from pages where {hist_q}", HISTORICAL):
        d = docs.get(path)
        if d is None:
            d = docs[path] = [title, []]
            order.append(path)
        if sum(len(b) for _, b in d[1]) < DOC_CHARS:
            d[1].append((page, body))
    rows += [(p, 0, docs[p][0], " ".join(b for _, b in sorted(docs[p][1]))[:DOC_CHARS])
             for p in order]
    todo = [r for r in rows if (r[0], r[1]) not in have and r[0] in valid]
    if args.limit:
        todo = todo[: args.limit]
    print(f"rows total {len(rows)} (historical docs {len(order)}), already embedded {len(have)}, todo {len(todo)}", flush=True)

    t0 = time.time()
    for i, (path, page, title, body) in enumerate(todo):
        v = embed(f"{title}. {body}")
        dst.execute("insert or replace into vectors values(?,?,?)",
                    (path, page, v.tobytes()))
        if (i + 1) % 500 == 0:
            dst.commit()
            el = time.time() - t0
            print(f"  {i+1}/{len(todo)} ({el/(i+1)*1000:.0f} ms/page, "
                  f"eta {(len(todo)-i-1)*el/(i+1)/60:.0f} min)", flush=True)
    dst.commit()
    n = dst.execute("select count(*) from vectors").fetchone()[0]
    print(f"done: {n} vectors, {os.path.getsize(args.dst)/1e6:.0f} MB, {time.time()-t0:.0f}s")


def embed_es(src, dst, limit=0):
    """E2: one vector per Spanish Hesperian page into vectors_es (pruned and resumed like vectors)."""
    rows = [r for r in src.execute(
        f"select path, page, title, substr(body,1,{DOC_CHARS}) from pages where rowid in "
        "(select rid from loc where path >= ? and path < ?)", (ES_TABLE_PREFIX[0], ES_TABLE_PREFIX[0][:-1] + "0"))]
    valid = {r[0] for r in rows}
    stale = [p for (p,) in dst.execute("select distinct path from vectors_es") if p not in valid]
    for p in stale:
        dst.execute("delete from vectors_es where path = ?", (p,))
    have = {(p, g) for p, g in dst.execute("select path, page from vectors_es")}
    todo = [r for r in rows if (r[0], int(r[1])) not in have]
    if limit:
        todo = todo[:limit]
    print(f"es: rows {len(rows)}, pruned {len(stale)}, already embedded {len(have)}, todo {len(todo)}", flush=True)
    t0 = time.time()
    for i, (path, page, title, body) in enumerate(todo):
        dst.execute("insert or replace into vectors_es values(?,?,?)", (path, int(page), embed(f"{title}. {body}").tobytes()))
        if (i + 1) % 200 == 0:
            dst.commit()
            print(f"  es {i+1}/{len(todo)} ({(time.time()-t0)/(i+1)*1000:.0f} ms/page)", flush=True)
    dst.commit()
    return len(todo)


if __name__ == "__main__":
    main()
