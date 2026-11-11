#!/usr/bin/env python3
"""Fold results/*.csv into REPORT.md. Rows: tier,check,path,status,detail.
Known failures (known_failures.txt, one path prefix per line) are netted out."""
import csv, glob, os, collections, datetime, json
here = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(here, "..", "library")
manifest = {l[66:].rstrip("\n") for l in open(f"{LIB}/MANIFEST.sha256")}
sealed = json.load(open(f"{LIB}/VERSION.json")).get("library", "")   # "2026.10.02" -> results older than the seal are stale
seal_day = datetime.datetime.strptime(sealed[:10], "%Y.%m.%d") if sealed[:4].isdigit() else None
PER_FILE = ("t1", "t2")   # tiers that owe one row per manifest path
known = [l.strip() for l in open(f"{here}/known_failures.txt") if l.strip()]
def is_known(p, check=""):
    if check == "zero_byte" and os.path.basename(p).startswith("."): return True  # .done markers
    return any(p.startswith(k) or f"{check}:{p}".startswith(k) for k in known)   # "check:path" form for summary rows
out = [f"# Exhaustive test report — {datetime.datetime.now():%Y-%m-%d %H:%M} (seal {sealed})\n",
       "| tier | PASS | FAIL | known | miss | SKIP | unchecked | as of |", "|---|---|---|---|---|---|---|---|"]
stale = []
SAMPLED = ("known_gold_v1", "known_gold_v2", "known_gold_v3", "known_phrase", "title_rank1")
fails = collections.defaultdict(list)
for f in sorted(glob.glob(f"{here}/results/*.csv")):
    tier = os.path.basename(f)[:-4]
    n = collections.Counter(); last = {}
    for row in csv.reader(open(f, newline="")):
        if len(row) < 4 or row[0] == "tier": continue
        last[(row[1], row[2])] = row   # resumable runs append; the last verdict per path wins
    seen = set()
    for row in last.values():
        st = row[3]
        if tier.split("_")[0] in PER_FILE:
            # #179: a library/ path that left the manifest earns nothing; service rows (discs /discs/..., kiwix catalog,
            # kolibri channels, mcp tools/list) have no manifest path and must still count, so a /discs/ 404 turns a seal red.
            if row[2] not in manifest:
                if row[2].startswith("library/"): continue
            else:
                seen.add(row[2])
        if st == "FAIL" and is_known(row[2], row[1]): st = "known"
        # sampled checks (known-item gold, phrase, title rank) are judged by their summary row; a per-item miss under a
        # passing summary is a "miss", not an unexplained FAIL. If the summary fails, every item stays FAIL.
        if st == "FAIL" and row[1] in SAMPLED and row[2] != "summary" and (last.get((row[1], "summary"), [None]*4)[3] == "PASS" or is_known("summary", row[1])): st = "miss"   # a known summary (bar missed, recorded) demotes its items too
        n[st] += 1
        if st == "FAIL": fails[tier].append(row)
    unchecked = len(manifest - seen) if tier.split("_")[0] in PER_FILE else ""
    asof = datetime.datetime.fromtimestamp(os.path.getmtime(f))
    flag = " STALE" if seal_day and asof < seal_day else ""
    if flag or unchecked: stale.append(f"{tier}: {unchecked or 0} manifest paths unchecked{flag}")
    if fails[tier]: stale.append(f"{tier}: {len(fails[tier])} unexplained FAIL")   # #179: VERDICT's bar is 0 FAIL too
    out.append(f"| {tier} | {n['PASS']} | {n['FAIL']} | {n['known']} | {n['miss']} | {n['SKIP']} | {unchecked} | {asof:%m-%d %H:%M}{flag} |")
if stale: out += ["", "**Not green:** " + "; ".join(stale) + ". A tier older than the seal, or with unchecked paths, proves nothing about this seal."]
for tier, rows in fails.items():
    out += [f"\n## {tier}: {len(rows)} unexplained FAIL\n"]
    for r in rows[:500]:
        out.append(f"- `{r[2]}` {r[1]}: {r[4] if len(r) > 4 else ''}")
    if len(rows) > 500: out.append(f"- ... {len(rows)-500} more, see results/{tier}.csv")
verdict = open(f"{here}/VERDICT.md").read() if os.path.exists(f"{here}/VERDICT.md") else ""
open(f"{here}/REPORT.md", "w").write(verdict + "\n" + "\n".join(out) + "\n")
print("\n".join(out[:20]))
