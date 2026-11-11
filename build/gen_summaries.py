#!/usr/bin/env python3
"""H30: one-line "what is this" summary for every shelf and every grouped
option on a shelf page (mirrors, maps, tools, CD3WD, MIT OCW). Local LLM
(Ollama) reads a minimal sample — folder listing + entry-page title/text —
and writes one sentence. Output: data/summaries.json, keys
"shelf:<path>" / "group:<shelf>/<group>". Only MISSING keys are generated,
so hand edits survive reruns; delete a key to regenerate it.
Usage: python3 gen_summaries.py [ollama_url] [model]"""
import json, os, re, sys, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from gen_index import SHELVES, load_paths, shelf_of
from gen_shelves import group_key

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = f"{BASE}/library"
OUT = f"{BASE}/data/summaries.json"
URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:11434"
MODEL = sys.argv[2] if len(sys.argv) > 2 else "qwen3:32b"
GROUPED = ("mirrors", "maps", "tools", "docs/cd3wd", "docs/mit_ocw",
           "audio/librivox", "docs/plant_id", "docs/survivor_library")  # the owner: everything described

def entry_text(folder):
    """title + first visible text of the shallowest index.html, if any"""
    best = None
    for root, dirs, files in os.walk(f"{LIB}/{folder}", followlinks=True):
        if root.count("/") - LIB.count("/") > 4:
            dirs[:] = []
            continue
        if "index.html" in files:
            best = f"{root}/index.html"
            break
    if not best:
        return ""
    s = open(best, errors="ignore").read()[:200_000]
    t = re.search(r"<title>([^<]*)", s)
    body = re.sub(r"(?s)<(script|style|nav|header).*?</\1>", " ", s)
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"\s+", " ", body)[:700]
    return f"Entry page title: {t.group(1).strip() if t else ''}\nEntry page text: {body}"

def ask(prompt):
    req = urllib.request.Request(f"{URL}/api/generate", data=json.dumps({
        "model": MODEL, "prompt": prompt, "stream": False, "think": False,
        "options": {"temperature": 0.2, "num_predict": 80}}).encode(),
        headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=300))["response"]
    r = re.sub(r"(?s)<think>.*?</think>", "", r).strip().split("\n")[0].strip().strip('"')
    return r

RULES = ("Write ONE plain sentence, at most 20 words, telling a non-expert what this "
         "is and when they would use it. Use only facts visible in the material below; "
         "do not invent contents. No marketing words. Do not start with 'This'. "
         "Output only the sentence.")

def plant_summaries():
    """docs/plant_id groups are one species each: built from plants.json, no LLM."""
    out = {}
    for r in json.load(open(f"{LIB}/_app/index/plants.json")):
        line = f"{r.get('label', '').capitalize()}. {r.get('note', '')}".strip()
        la = r.get("lookalike")
        if la and la != "None":
            line += f" Look-alike: {la}."
        out[f"group:docs/plant_id/{r['slug']}"] = line
    return out


def main():
    have = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for k, v in plant_summaries().items():   # data-derived, no LLM; hand edits win
        have.setdefault(k, v)
    json.dump(have, open(OUT, "w"), indent=1, ensure_ascii=False)
    by = {}
    for p in load_paths():
        s = shelf_of(p)
        if s:
            by.setdefault(s, []).append(p)
    todo = []
    for shelf, meta in SHELVES.items():
        files = by.get(shelf)
        if not files:
            continue
        todo.append((f"shelf:{shelf}", f"Library shelf: {meta[0]} (current tagline: {meta[1]}). "
                     f"{len(files)} files. Sample paths:\n" + "\n".join(files[:: max(1, len(files) // 25)][:25])))
        if shelf in GROUPED:
            groups = {}
            for p in files:
                groups.setdefault(group_key(shelf, p) or "top", []).append(p)
            for g, ps in groups.items():
                if g == "top":
                    continue
                todo.append((f"group:{shelf}/{g}",
                             f"Collection '{g}' on the '{meta[0]}' shelf of an offline survival library. "
                             f"{len(ps)} files. Sample paths:\n" + "\n".join(ps[:: max(1, len(ps) // 20)][:20])
                             + "\n" + entry_text(f"{shelf}/{g}")))
    for key, ctx in todo:
        if key in have:
            continue
        try:
            have[key] = ask(f"{RULES}\n\n{ctx}")
        except Exception as e:   # no Ollama reachable: leave the key missing, gen_shelves reports it
            print(f"SKIP {key}: {e}", flush=True)
            continue
        print(f"{key}: {have[key]}", flush=True)
        json.dump(have, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(f"{len(have)} summaries in {OUT}")

if __name__ == "__main__":
    main()
