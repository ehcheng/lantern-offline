#!/usr/bin/env python3
"""#79 title self-check. Usage:
  check_titles.py                 structural gates on resolve_titles (unique, no noise, #129 title year == y); exit 1 on failure
  check_titles.py --regen-list F  also write the #126 list of paths whose `t` came from the file name (for the `t` regen)
  check_titles.py --sample N SEED [--before titles_before.json] [--out file.tsv]
                                  seeded random N-title sample checked against each PDF's pages 1-2 (pdftotext -l 2):
                                  PASS = >=60% of the title's content words (and any year) appear in the text;
                                  FLAG = needs a human read. Prints per-path rows; --before compares an older dump."""
import sys, os, re, json, random, subprocess, collections
sys.path.insert(0, os.path.dirname(__file__))
import gen_index as g

STOP = set("the of and for to in a an on with by from at as or is are la le les de du des el los las y en un una pour et der die das und".split())
NOISE = {"copy", "part", "vol", "chapter", "grade", "module", "no", "id", "in"}

def norm(s):
    s = s.casefold().replace("’", "'")
    return re.sub(r"[^a-z0-9À-ɏ]+", " ", s)

def words(title):
    t = re.sub(r"\([^()]*\)", " ", title)                 # parenthetical = author/year/lang, checked separately
    t = t.split(", ")[0] if re.search(r", (part|copy|in|vol|grade|module|chapter|id)\b", t) else t
    return [w for w in norm(t).split() if w not in STOP and len(w) > 2 and w not in NOISE and not w.isdigit()]

def first_pages(p):
    f = f"{g.LIB}/{p}"
    if not os.path.exists(f) or not f.lower().endswith(".pdf"):
        return None
    r = subprocess.run(["pdftotext", "-l", "2", "-enc", "UTF-8", f, "-"], capture_output=True, timeout=60)
    return norm(r.stdout.decode("utf-8", "replace"))

def defect(t, path=""):
    """structural title defects: copy numbering, file-name series words, category-code prefix, trailing id,
    "Semi Automatic" on a bolt-action file"""
    cd = os.path.basename(path).startswith("_") if path else True  # series words only mean noise on CD3WD-style names
    return bool(re.search(r", copy \d+$|(?<!no\.) \d{6}$", t) or not re.search(r"[^\W\d_]", t)   # #174: "1" is no title
                or cd and re.search(r"\b(lp|jf|bv|vth)\b|^(Ag|At|Ec|Wa|Co|Me|Ms|Mh|Mc|Sl|Wi|Ed|Engy) [A-Za-z]", t)
                or (path and g._BOLT.search(os.path.basename(path)) and re.search(r"semi.?automatic (rifle|carbine)", t, re.I)))

def verdict(title, text):
    if text is None or len(text.strip()) < 40:
        return "UNVERIFIABLE"
    w = words(title)
    hit = sum(1 for x in w if x in text)
    ok = (not w) or hit / len(w) >= 0.6
    bad = []
    for y in re.findall(r"(?<!\d)(1[5-9]\d\d|20[0-2]\d)(?!\d)", re.sub(r"\([^()]*(?:Hesperian)[^()]*\)", "", title)):
        if y not in text.replace(" ", "") and y not in text:
            bad.append(y)
    if defect(title):
        bad.append("noise")
    return "PASS" if ok and not bad else "FLAG"

COPY = lambda T: sum(1 for t in T.values() if re.search(r', copy \d+$', t))

def structural():
    meta = g.doc_meta()
    T = g.resolve_titles(meta)
    k = collections.Counter(re.sub(r"[\W_]+", " ", t.casefold()).strip() for t in T.values())
    dup = [t for t, n in k.items() if n > 1]
    bolt = [p for p, t in T.items() if g._BOLT.search(os.path.basename(p)) and re.search(r"semi.?automatic (rifle|carbine)", t, re.I)]
    dupf = f"{g.BASE}/data/fix79_duplicate_files.tsv"   # byte/text-identical files awaiting removal by the files owner
    dups = set()
    if os.path.exists(dupf):
        for ln in list(open(dupf))[1:]:
            a, b = ln.rstrip("\n").split("\t")[:2]; dups |= {a, b}
    noise = [p for p, t in T.items() if defect(t, p) and p not in dups]  # copy N allowed only on listed duplicate files
    stray = [p for p, t in T.items() if re.search(r", copy \d+$", t) and p not in dups]
    assert not stray, ("copy N on a distinct document", stray[:5])
    print(f"titles={len(T)} duplicate_titles={len(dup)} bolt_semi_auto={len(bolt)} defects={len(noise)} "
          f"copy_n={COPY(T)}")
    assert not dup, dup[:5]
    assert not bolt, bolt[:5]
    ov = json.load(open(g.OVR_PATH)) if os.path.exists(g.OVR_PATH) else {}
    for p, t in ov.items():
        assert T.get(p) in (t, None) or T[p].startswith(t), (p, T.get(p), t)
    # #129: a title prints no date year other than y (the year the shelves show); override titles included
    # media (audio/, video/) has no catalog entry and no shelf year: the film year in a Prelinger title is its only date
    ymis = [(p, T[p], g.doc_year(p, meta)) for p in T if p in meta and any(x != g.doc_year(p, meta) for x in g.date_years(T[p]))]
    print(f"title_year_mismatch={len(ymis)}")
    assert not ymis, ymis[:5]
    lang_defects(T, meta, ov)
    return T, meta

def lang_defects(T, meta, ov):
    """#139: an English VITA series prefix on an es/fr/pt title, a native language name in a parenthetical ("(Português)"),
    and an edition parenthetical carrying a year its source title does not ("(New Edition, 2023)" built from y)"""
    pre = [(p, T[p]) for p in T if g.doc_lang(p, meta) in ("es", "fr", "pt") and g._EN_SERIES.match(T[p])]
    nat = [(p, T[p]) for p in T for par in re.findall(r"\(([^()]*)\)", T[p])
           if any(x.casefold() in g.NATIVE for x in re.split(r"\s*,\s*", par))]
    src = lambda p: ov.get(p) or meta.get(p, {}).get("t", "")
    edy = [(p, T[p]) for p in T for par in re.findall(r"\(([^()]*)\)", T[p])
           if g.EDITION.search(par) and not set(g._YEAR.findall(par)) <= set(g._YEAR.findall(src(p)))]
    # #142: curated `t` (search, MCP, embeddings read it) names no language other than `l` ("(German)" on an English GTZ
    # text). Override titles too: the 3 that said "(German)" for a German-made rifle or a German cover were reworded 10-08
    cur = [(p, ov.get(p) or e["t"]) for p, e in meta.items() if (ov.get(p) or e.get("t"))
           and g.lang_from_l(ov.get(p) or e["t"], g.doc_lang(p, meta)) != (ov.get(p) or e["t"])]
    print(f"english_series_prefix={len(pre)} native_language_name={len(nat)} edition_year_from_y={len(edy)} "
          f"curated_t_language={len(cur)}")
    assert not pre, pre[:5]
    assert not nat, nat[:5]
    assert not edy, edy[:5]
    assert not cur, cur[:5]

STRICT = {"ag", "bg", "bv", "cm", "cnx", "dwg", "ec", "eg", "elct", "engy", "fp", "gret", "gtb", "inpho", "jf", "kno", "lp",
          "lstock", "mc", "mfkh", "mh", "mng", "pa", "pc", "sl", "sp", "ss", "trp", "unfao", "vth", "weir", "wfs"}

def from_filename(p, t, meta, dictw):
    """#126: `t` is the file name, not a title page line. CD3WD names: every word of t is a file-name token and the
    document is not English ("Grains Drying" on "Cosecha de granos") or t keeps a series/source code or catalogue
    number ("Ag Crops 10 BV EN LP"). Other names outside Survivor Library and the textbooks (whose file names are
    real titles): t is the humanized file name and is either lower case after the first letter ("Ready gov tornado
    info sheet spanish") or carries a Title-cased acronym ("Ncvec", "Cfr47", "Msf")."""
    base = os.path.basename(p)
    body = re.sub(r"\s*\([^()]*\)", " ", t).strip()
    raw = re.findall(r"[^\W_]+", body.casefold())
    if not t:
        return True
    if base.startswith("_"):
        ft = {x.lower() for x in g._toks(p)} | set(re.findall(r"[^\W_]+", base.casefold()))
        w = [x for x in raw if x not in STOP and not x.isdigit()]
        return bool(w) and all(x in ft for x in w) and (g.doc_lang(p, meta) != "en" or any(x in STRICT for x in raw)
                                                       or bool(re.search(r"\b\d{5,6}\b", body)))
    if "survivor_library" in p or "school_textbooks" in p:
        return False
    hb = g.humanize(base)
    if g._key(body) not in (g._key(hb), g._key(re.sub(r"\s\d{4}$", "", hb))):
        return False
    acro = [x for x in re.findall(r"\b[A-Z][a-z0-9]{1,4}\b", body) if x.lower() not in dictw and x.lower().rstrip("s") not in dictw]
    return body[1:] == body[1:].lower() or bool(acro)

def regen_list(meta, out):
    ov = json.load(open(g.OVR_PATH)) if os.path.exists(g.OVR_PATH) else {}
    try:
        dictw = {w.strip().lower() for w in open("/usr/share/dict/words")}
    except OSError:
        dictw = set()
    ps = sorted(p for p, e in meta.items() if p not in ov and from_filename(p, e.get("t") or "", meta, dictw))
    open(out, "w").write("".join(p + "\n" for p in ps))
    print(f"regen_list={len(ps)} -> {out}")

if __name__ == "__main__":
    T, meta = structural()
    if "--regen-list" in sys.argv:
        regen_list(meta, sys.argv[sys.argv.index("--regen-list") + 1])
    if "--sample" in sys.argv:
        i = sys.argv.index("--sample"); n, seed = int(sys.argv[i + 1]), int(sys.argv[i + 2])
        before = json.load(open(sys.argv[sys.argv.index("--before") + 1])) if "--before" in sys.argv else {}
        pool = sorted(p for p in T if p in meta and p.lower().endswith(".pdf") and os.path.exists(f"{g.LIB}/{p}"))
        random.Random(seed).shuffle(pool)
        rows = []
        for p in pool[:n]:
            tx = first_pages(p)
            rows.append((p, before.get(p, ""), verdict(before[p], tx) if p in before else "", T[p], verdict(T[p], tx)))
        out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
        lines = ["\t".join(r) for r in rows]
        if out: open(out, "w").write("path\tbefore\tbefore_v\tafter\tafter_v\n" + "\n".join(lines) + "\n")
        print("before", collections.Counter(r[2] for r in rows), "after", collections.Counter(r[4] for r in rows))
