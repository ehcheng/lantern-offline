#!/usr/bin/env python3
"""H37b gold gate: hit@5 of exact-only Pagefind vs the fused list on
server/gold_queries.json, plus a cosine-floor sweep.

Drives the live search.html (dev server :8765) with Playwright and reads
window.__lanternFT = {q, pf, sem, titles, fused}: pf = Pagefind doc list
(grouped, filtered), sem = /semantic list as the page saw it, titles = the
title-layer dedupe set, fused = what the page rendered. The floor sweep
re-fetches /semantic?floor=0 for scores and re-runs the same RRF in python
(a port of search.html fuse()); at the server floor it must equal `fused`.

Ship criterion: fused hit@5 > exact hit@5 AND no exact-kind query whose
expected doc was in the exact top-3 loses it in the fused top-3.

Usage (sandbox off, servers up: 8765 library, 8090 mcp, 8091 embed):
  python3 server/eval_gold.py [--floor 0.60] > logs/h37_gold.log
"""
import argparse, json, os, re, statistics, sys, time, urllib.parse, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = "http://127.0.0.1:8765/search.html?q="
SEM = "http://127.0.0.1:8090/semantic?limit=20&lang=eng&floor=0&q="
FLOORS = (0.50, 0.55, 0.60, 0.65, 0.70)


def hit(paths, expect, k, titles=()):
    """Expected doc in the top-k body rows, or already shown by the Titles
    layer (search.html dedupes those out of the body list)."""
    pats = [p.lower() for p in expect.split("|")]
    pool = list(titles) + list(paths[:k])
    return any(any(re.search(p, path.lower()) for p in pats) for path in pool)


HIST = ("docs/survivor_library/", "docs/cd3wd/", "docs/HISTORICAL/")


def hist_only(paths):
    """H37c: the rows search.html renders under the historical divider."""
    return [p for p in paths if p.startswith(HIST)]


def rrf(pf, sem, titles):
    """search.html fuse(): 1/(60+rank) per list, rank = 1-based index in the
    source list; titles-layer docs dropped from the semantic side."""
    score = {}
    order = []
    for i, rel in enumerate(pf):
        score[rel] = 1.0 / (61 + i)
        order.append(rel)
    for i, rel in enumerate(sem):
        if rel in titles:
            continue
        if rel in score:
            score[rel] += 1.0 / (61 + i)
        else:
            score[rel] = 1.0 / (61 + i)
            order.append(rel)
    return sorted(order, key=lambda r: -score[r])  # stable, like JS sort in Chrome


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--floor", type=float, default=0.65,
                    help="server SEMANTIC_FLOOR the page is running with")
    a = ap.parse_args()
    gold = json.load(open(os.path.join(HERE, "gold_queries.json")))["queries"]

    rows = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        pg = b.new_page()
        for g in gold:
            q = g["q"]
            pg.goto(PAGE + urllib.parse.quote(q))
            pg.wait_for_function(
                "window.__lanternFT && window.__lanternFT.q === %s" % json.dumps(q),
                timeout=45000)
            ft = pg.evaluate("window.__lanternFT")
            t0 = time.time()
            raw = json.load(urllib.request.urlopen(SEM + urllib.parse.quote(q), timeout=15))
            ms = (time.time() - t0) * 1000
            rows.append((g, ft, raw, ms))
        b.close()

    print("H37b/H37c gold eval  %s  server floor=%.2f  n=%d" % (
        time.strftime("%Y-%m-%d %H:%M"), a.floor, len(rows)))
    print()
    print("per query (E=exact-only top5, F=fused top5, Titles-layer hits count for both;"
          " exact-kind: T3 keep = expected doc stayed in top-3)")
    feel5 = 0
    base5 = fused5 = 0
    body_e = body_f = 0  # same, ignoring the Titles layer (body section alone)
    lost = []
    per_kind = {}
    for g, ft, raw, ms in rows:
        pf, fused, titles = ft["pf"], ft["fused"], set(ft["titles"])
        if g["kind"] == "historical":
            pf, fused = hist_only(pf), hist_only(fused)
        e = hit(pf, g["expect"], 5, titles)
        f = hit(fused, g["expect"], 5, titles)
        base5 += e
        fused5 += f
        body_e += hit(pf, g["expect"], 5)
        body_f += hit(fused, g["expect"], 5)
        sem_l = hist_only(ft["sem"]) if g["kind"] == "historical" else ft["sem"]
        feel5 += hit(sem_l, g["expect"], 5, titles)  # "By feeling" mode = semantic list alone
        k = per_kind.setdefault(g["kind"], [0, 0, 0])
        k[0] += 1; k[1] += e; k[2] += f
        note = ""
        if g["kind"] == "exact":
            had = hit(pf, g["expect"], 3, titles)
            keep = hit(fused, g["expect"], 3, titles)
            note = "T3 keep" if (not had or keep) else "T3 LOST"
            if had and not keep:
                lost.append(g["q"])
        # parity: python RRF over the lists the page saw must reproduce the
        # rendered order (top 12 = 8 modern + 4 historical rows). The floor
        # sweep below uses re-fetched 3-decimal scores instead, which can
        # differ from the page list by a row right at the boundary.
        parity = "ok" if rrf(pf, ft["sem"], titles)[:12] == fused[:12] else "DIFF"
        print("  %-8s E=%d F=%d %-8s parity=%-4s %4.0fms  %s" % (
            g["kind"], e, f, note, parity, ms, g["q"]))
        if not f:
            print("           fused top5:", [x.split("/")[-1][:40] for x in fused[:5]])
            print("           sem  top3 :", [(h["score"], h["path"].split("/")[-1][:40]) for h in raw[:3]])
    n = len(rows)
    print()
    print("hit@5  exact-only %d/%d = %.2f   fused %d/%d = %.2f   feeling-only %d/%d = %.2f" % (
        base5, n, base5 / n, fused5, n, fused5 / n, feel5, n, feel5 / n))
    print("  (modes: Precise = exact-only, Both = fused, By feeling = feeling-only)")
    for kind, (t, e, f) in per_kind.items():
        print("  %-8s exact %d/%d  fused %d/%d" % (kind, e, t, f, t))
    print("  body section alone (no Titles credit): exact-only %d/%d  fused %d/%d" % (
        body_e, n, body_f, n))
    print("exact-kind top-3 lost: %s" % (lost or "none"))
    lat = [r[3] for r in rows]
    print("/semantic latency (warm, embed+scan, M2): median %.0f ms  max %.0f ms" % (
        statistics.median(lat), max(lat)))

    print()
    print("floor sweep (python RRF port on the same pf/sem lists):")
    print("  floor  hit@5  mismatch  exact  T3lost  sem-only rows in top8 (avg)")
    for fl in FLOORS:
        h5 = mm = ex = t3 = 0
        extra = 0
        for g, ft, raw, ms in rows:
            pf, titles = ft["pf"], set(ft["titles"])
            sem_at = [h["path"] for h in raw if h["score"] >= fl]
            fz = rrf(pf, sem_at, titles)
            ok = hit(fz, g["expect"], 5, titles)
            h5 += ok
            if g["kind"] == "mismatch":
                mm += ok
            else:
                ex += ok
                if hit(pf, g["expect"], 3, titles) and not hit(fz, g["expect"], 3, titles):
                    t3 += 1
            extra += sum(1 for r in fz[:8] if r not in pf)
        print("  %.2f   %2d/%d    %2d/%d     %2d/%d    %d       %.1f" % (
            fl, h5, n, mm, per_kind.get("mismatch", [0])[0], ex,
            per_kind.get("exact", [0])[0], t3, extra / n))
    ship = fused5 > base5 and not lost
    print()
    print("SHIP" if ship else "NO-SHIP", "(hit@5 rises and no exact top-3 lost)" if ship else "")
    return 0 if ship else 1


if __name__ == "__main__":
    sys.exit(main())
