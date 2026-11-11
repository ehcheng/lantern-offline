#!/usr/bin/env python3
"""T7 inputs: deterministic dumps for the judgment agents (they read files only).
a) 200 random docs/ PDFs: page 1-3 text via read_document (:8090)   -> t7_input/text_sample.md
b) 30 random shelf groups: description + first 25 file names          -> t7_input/groups_sample.md
c) 30 queries from RUNBOOK/SKILLS topics: top-3 search_library hits   -> t7_input/queries_sample.md"""
import os, re, json, random, glob, urllib.request, html
EX = os.path.dirname(os.path.abspath(__file__)); os.chdir(f"{EX}/.."); random.seed(7)
def mcp(name, args):
    req = urllib.request.Request("http://127.0.0.1:8090/mcp", data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}}).encode(),
                                 headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    return json.loads(json.load(urllib.request.urlopen(req, timeout=120))["result"]["content"][0]["text"])
paths = [l[74:].rstrip("\n") for l in open("library/MANIFEST.sha256")]
docs = [p for p in paths if p.startswith("docs/") and p.endswith(".pdf")]
with open(f"{EX}/t7_input/text_sample.md", "w") as f:
    f.write("# T7a: page 1-3 text of 200 random docs/ PDFs (read_document)\n\n")
    for p in random.sample(docs, 200):
        try: d = mcp("read_document", {"path": p, "page": 1, "pages": 3}); txt = (d.get("text") or d.get("error") or json.dumps(d))[:1200].replace("`", "'")
        except Exception as e: txt = "ERROR " + str(e)
        f.write(f"## {p}\n\n```\n{txt}\n```\n\n")
S = json.load(open("data/summaries.json"))
groups = [k for k in S if k.startswith("group:")]
with open(f"{EX}/t7_input/groups_sample.md", "w") as f:
    f.write("# T7b: 30 random shelf groups — description vs folder contents\n\n")
    for k in random.sample(groups, 30):
        shelf, g = k[6:].rsplit("/", 1)
        files = [p for p in paths if p.startswith(shelf + "/" + g + "/") or p.startswith(shelf + "/") and f"/{g}/" in p][:25]
        f.write(f"## {k}\n\nDescription: {S[k]}\n\nFiles ({len(files)} shown):\n\n" + "\n".join("- " + x for x in files) + "\n\n")
topics = set()
for src in ("library/RUNBOOK.md", "library/SKILLS_CHECKLIST.md"):
    for m in re.findall(r"^#+\s+(.+)$|^- (?:\[.\] )?(.+)$", open(src).read(), re.M):
        t = re.sub(r"[`*_#\[\]()]", "", (m[0] or m[1])).split(":")[0].split(" — ")[0].strip()
        if 6 < len(t) < 50 and not t.startswith(("Part", "Step", "http")): topics.add(t)
qs = random.sample(sorted(topics), min(30, len(topics)))
with open(f"{EX}/t7_input/queries_sample.md", "w") as f:
    f.write("# T7c: 30 queries from RUNBOOK/SKILLS topics — top-3 search_library hits\n\n")
    for q in qs:
        try: hits = mcp("search_library", {"query": q, "limit": 3}).get("hits", [])
        except Exception as e: hits = [{"title": "ERROR " + str(e)}]
        f.write(f"## {q}\n\n" + "\n".join(f"{i+1}. {h.get('title','')} — `{h.get('path','')}` p{h.get('page','')}" for i, h in enumerate(hits)) + "\n\n")
print("t7 inputs written", len(qs), "queries")
