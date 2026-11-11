#!/usr/bin/env python3
"""Per-document human title + one-sentence summary for every text-bearing PDF
on the Pagefind whitelist (gen_text.WHITELIST). Local LLM (Ollama) reads the
filename stem plus the first clean prose of the book (OCR cover noise skipped)
and returns JSON. Output: data/docs.curated.json
  {path: {"t": title, "s": sentence, "src": "llm"|"stem"}}
Only MISSING paths or keys are generated (r21: per key, so deleting "t" or "s" regenerates just that key and keeps
"a"/"y"/"l"); hand edits survive reruns. gen_index.py reads "t", gen_shelves.py reads "s". #132: "s" is written in
the entry's language "l"; reference lists and compilations get gen_doc_answers.prompt_note().
Usage: python3 gen_doc_meta.py [--limit N] [--only PREFIX] [--threads 4] [--sample] [ollama_url] [model]
  --sample   30 docs spread across shelves, written to docs.sample.json (not curated)
"""
import json, os, re, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from gen_text import WHITELIST, LIB, extract
from gen_index import humanize, COMP_PREFIX

OUT = os.environ.get("CURATED") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "docs.curated.json")   # CURATED: a copy (trials)
_skip = {sys.argv[i + 1] for i, a in enumerate(sys.argv) if a in ("--limit", "--only", "--threads", "--paths", "--vl-list") and i + 1 < len(sys.argv)}
THREADS = int(sys.argv[sys.argv.index("--threads") + 1]) if "--threads" in sys.argv else 1
args = [a for a in sys.argv[1:] if not a.startswith("--") and a not in _skip]
URL = next((a for a in args if a.startswith("http")), "http://127.0.0.1:11434")
MODEL = next((a for a in args if not a.startswith("http")), "qwen3:32b")
LIMIT = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
ONLY = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else ""
SAMPLE = "--sample" in sys.argv
if SAMPLE:
    OUT = OUT.replace("docs.curated.json", "docs.sample.json")

HEAD, TAIL, MIN_CLEAN = 2500, 500, 400
WORD = re.compile(r"[A-Za-zÀ-ÿ]{3,}")  # accented Latin too: French/Spanish CD3WD manuals were scored as noise (2026-09-30)
VOWEL = re.compile(r"[aeiouyAEIOUYàáâäèéêëìíîïòóôöùúûüÀÁÂÄÈÉÊËÌÍÎÏÒÓÔÖÙÚÛÜ]")


def clean_ratio(s):
    toks = s.split()
    if len(toks) < 8:
        return 0.0
    good = sum(1 for t in toks if WORD.fullmatch(t.strip(".,;:!?()\"'")) and VOWEL.search(t))
    return good / len(toks)


def prose(text):
    """first HEAD chars of real prose (window-scored so OCR cover garbage is skipped), plus last TAIL."""
    body = re.sub(r"[ \t]+", " ", text.replace("\f", "\n"))
    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    keep, n = [], 0
    for p in paras:
        if clean_ratio(p) >= 0.7:
            keep.append(p)
            n += len(p)
            if n >= HEAD:
                break
    head = "\n".join(keep)[:HEAD]
    tail = "\n".join(p for p in paras[-12:] if clean_ratio(p) >= 0.7)[-TAIL:]
    return head, tail


PROMPT = """You catalog books for a library that ordinary people read on a phone, possibly years from now. From the filename and excerpt below, return JSON only:
{{"title": "...", "summary": "..."}}
title: the book's real title in Title Case, author or year appended only if the excerpt shows them (e.g. "Where There Is No Dentist (Hesperian, 2025)"). Keep acronyms and brand codes uppercase (ATP, FM, HK USP, FEMA, WHO). If the year is known put it last in parentheses: "Steam Engines (1911)". If the text is not English, append the language: "(Russian)". Never invent a title. If the filename is a catalog code or abbreviation (numbers, agency codes like cisa/neets/ncvec/fema, cd3wd "_ag_..._pa_en_NNNN_" codes), ignore it and take the title from the first heading or title page in the excerpt; if unsure, tidy the filename.
summary: ONE plain sentence, at most 20 words, telling a non-expert what this document covers and when they would use it. Only facts visible below; no marketing words; do not start with "This". Do not assume survival, emergency, off-grid or prepper use unless the document is about that.

Filename: {stem}
Shelf: {shelf}
Excerpt (start):
{head}
Excerpt (end):
{tail}
"""


def ask(stem, shelf, head, tail, extra=""):
    req = urllib.request.Request(f"{URL}/api/generate", data=json.dumps({
        "model": MODEL, "prompt": PROMPT.format(stem=stem, shelf=shelf, head=head, tail=tail) + extra,
        "stream": False, "think": False, "format": "json",
        "options": {"temperature": 0.1, "num_predict": 320}}).encode(),   # r22: 160 truncated Bengali/Vietnamese JSON
        headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=600))["response"]
    j = json.loads(r)
    t, s = str(j.get("title", "")).strip().strip('"'), str(j.get("summary", "")).strip().split("\n")[0]
    return t, s


def docs():
    for wdir in WHITELIST:
        base = os.path.join(LIB, wdir)
        if not os.path.isdir(base) or (ONLY and not wdir.startswith(ONLY)):
            continue
        for root, _, files in os.walk(base, followlinks=True):
            for fn in sorted(files):
                if fn.startswith(".") or not fn.lower().endswith(".pdf"):
                    continue
                pdf = os.path.join(root, fn)
                yield wdir + pdf[len(base):], pdf, wdir


def main():
    import threading
    from concurrent.futures import ThreadPoolExecutor
    import gen_doc_answers as A   # lazy: gen_doc_answers imports this module
    have = json.load(open(OUT)) if os.path.exists(OUT) and not SAMPLE else {}
    need = lambda e: e is None or "t" not in e or (not e.get("s") and "s" not in e.get("c1", ""))   # C1 (#285): a blank s marked c1 stays blank
    paths = {l.strip() for l in open(sys.argv[sys.argv.index("--paths") + 1])} if "--paths" in sys.argv else None   # trials
    todo = [d for d in docs() if need(have.get(d[0])) and (paths is None or d[0] in paths)]
    if SAMPLE:  # spread: every k-th doc so all shelves show up
        k = max(1, len(todo) // 30)
        todo = todo[::k][:30]
    if LIMIT:
        todo = todo[:LIMIT]
    print(f"model={MODEL} threads={THREADS} have={len(have)} todo={len(todo)}", flush=True)
    lock, cnt, t0, vl_need = threading.Lock(), {"llm": 0, "stem": 0, "skip": 0}, time.time(), []
    def save():
        tmp = OUT + ".tmp"
        json.dump(have, open(tmp, "w"), indent=1, ensure_ascii=False, sort_keys=True)
        os.replace(tmp, OUT)
    def one(d):
        rel, pdf, wdir = d
        e = have.get(rel)
        stem = humanize(os.path.basename(rel))
        try:
            text = A.clean_text(extract(pdf, rel) or "")
        except Exception:
            text = ""
        lang = (e or {}).get("l") if (e or {}).get("l") in A.LANG_NAME else A.detect_lang(text, os.path.basename(rel))[0]
        if not A.readable(text, rel, lang):
            with lock:
                if e is None:
                    have[rel] = {"t": stem, "s": "", "src": "stem"}  # no readable text: title only, never hallucinate
                    cnt["stem"] += 1
                else:
                    e.setdefault("t", stem); cnt["skip"] += 1   # VL docs keep their description (gen_doc_meta_vl.py)
                    if not e.get("s"):   # r21: any dropped `s` on a file without usable text goes to the vision model
                        vl_need.append(rel)
            return
        head, tail = A.excerpt(text, rel)
        name = A.LANG_NAME[lang]
        extra = (f"\nThe document is in {name}. Write the summary in {name}." + ("" if lang == "en" else
                 f" End the title with ({name}).") + A.prompt_note(text, rel))
        if A.papers(text, rel):   # r21: a compilation's title names the volume and its papers, not the first paper
            # #139: the series name in the document's language ("Boletines técnicos VITA: ..."), never English on es/fr/pt
            extra += (" For the title, name the collection and its main topics (for example \"%s: Adobe, Hydroponics, "
                      "Hydropower\" with the topics in %s); never the first paper alone or the filename." % (COMP_PREFIX.get(lang, COMP_PREFIX["en"]), name))
        if rel.startswith(A.OLD_SHELVES) and not A.aud_ok(rel, e.get("t", "") if e else ""):
            extra += "\n" + A.AUD_NO   # #125: the one-liner gets the same audience rule as the answer
        bad = lambda x: A.mixed_script(x, lang) or A.audience_bad(rel, e.get("t", "") if e else "", x)
        try:
            for _ in range(2):   # r21: retry once when the one-liner comes back in a mixed script or with an invented audience
                t, s = ask(stem, wdir, head, tail, extra)
                if not bad(s):
                    break
            if A.audience_bad(rel, e.get("t", "") if e else "", s):
                s = A.aud_cut(s)
            # #135: never cut mid-sentence: over S_MAX or unfinished -> ask once for a shorter one, else a clause cut
            s = A.fit_s(s, lambda note: ask(stem, wdir, head, tail, extra + note)[1], lang, bad)
        except Exception as ex:
            print(f"FAIL {rel}: {ex}", file=sys.stderr, flush=True)
            return
        with lock:
            if e is None:
                have[rel] = e = {"src": "llm"}
            if "t" not in e or (e.get("src") == "stem" and e["t"] == stem):   # a filename placeholder is not a title
                e["t"] = t or stem
            if not e.get("s"):
                e["s"] = s
            if e.get("src") == "stem":
                e["src"] = "llm"
            cnt["llm"] += 1
            if cnt["llm"] % 20 == 0 or SAMPLE:
                save()
                print(f"...{cnt['llm']}/{len(todo)} {time.time()-t0:.0f}s  {rel} -> {lang} {e['t']!r} {e['s'][:60]!r}", flush=True)
    with ThreadPoolExecutor(THREADS) as ex:
        list(ex.map(one, todo))
    save()
    if "--vl-list" in sys.argv:   # r21_regen.sh runs gen_doc_meta_vl.py on this list
        open(sys.argv[sys.argv.index("--vl-list") + 1], "w").write("".join(p + "\n" for p in sorted(vl_need)))
    print(f"VL_NEEDED={len(vl_need)}")
    print(f"DONE llm={cnt['llm']} stem_only={cnt['stem']} kept_no_text={cnt['skip']} total={len(have)} {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
