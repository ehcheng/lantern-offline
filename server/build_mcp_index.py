#!/usr/bin/env python3
"""Build library/_app/mcp/mcp.db per MCP_PLAN.md DB CONTRACT. Stdlib only."""
import csv, html, io, json, os, re, sqlite3, sys, time, zipfile
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "library")
DB = os.path.join(LIB, "_app", "mcp", "mcp.db")

SHELVES = [e["path"] for e in json.load(open(os.path.join(LIB, "_app", "index", "shelves.json")))]
SHELVES.sort(key=len, reverse=True)  # longest prefix wins

def shelf_of(path):
    for sp in SHELVES:
        if path == sp or path.startswith(sp + "/"):
            return sp
    return "/".join(path.split("/")[:2])

# ---------- wrapper pages (_app/text/**/*.html) ----------
RE_TITLE = re.compile(r"<title>(.*?)</title>", re.S)
RE_PDF = re.compile(r'data-pdf="([^"]+)"')
RE_H2 = re.compile(r'<h2 id="p(\d+)">.*?</h2>', re.S)
RE_TAG = re.compile(r"<[^>]+>")

# lang by content, not shelf (known-item v2 gate 2026-10-03: Spanish cd3wd/FAO PDFs were tagged en and hidden by
# the hard Spanish filter). Stopword vote over the first pages of the document; one lang per document.
_ES = {"de", "la", "que", "el", "en", "los", "del", "las", "por", "con", "una", "para", "es", "se", "como", "más"}
_EN = {"the", "of", "and", "to", "in", "is", "for", "that", "with", "as", "on", "are", "be", "this", "from", "or"}
def guess_lang(text):
    w = re.findall(r"[a-záéíóúñ]+", text.lower()[:30000])
    es = sum(x in _ES for x in w); en = sum(x in _EN for x in w)
    return "es" if es > 1.5 * en and es > 20 else "en"

# round 8 M4 hand-off (#240, a8 note): the catalogue's `l` field wins over the stopword vote (*Cálculo I* was tagged en).
# Only toward es: 21 documents the vote reads as Spanish text are catalogued en (INPHO postharvest, bilingual glossaries),
# and an es -> en override would put Spanish text in English results (10-17, English first). A pt or fr tag would
# drop those documents from English /semantic rows (a ranking change left for round 9); other languages keep the vote.
def curated():
    """data/docs.curated.json (build/gen_doc_meta.py + gen_doc_answers.py, a local LLM); {} when a build has none"""
    f = os.path.join(ROOT, "data", "docs.curated.json")
    if not os.path.exists(f):
        print("WARN no data/docs.curated.json: no catalog languages, title-only list or health years", file=sys.stderr)
        return {}
    return json.load(open(f, encoding="utf-8"))


CAT_LANG = {p: "es" for p, v in curated().items() if v.get("l") == "es"}


def wrapper_rows():
    tdir = os.path.join(LIB, "_app", "text")
    for dirpath, _, files in os.walk(tdir):
        for fn in sorted(files):
            if not fn.endswith(".html"):
                continue
            raw = open(os.path.join(dirpath, fn), encoding="utf-8", errors="replace").read()
            m = RE_PDF.search(raw)
            if not m:
                continue
            path = html.unescape(m.group(1))
            title = html.unescape(RE_TITLE.search(raw).group(1)).strip() if RE_TITLE.search(raw) else fn
            shelf = shelf_of(path)
            parts = RE_H2.split(raw)  # [pre, p1num, p1body, p2num, ...]
            bodies = [re.sub(r"\s+", " ", html.unescape(RE_TAG.sub(" ", parts[i + 1]))).strip() for i in range(1, len(parts) - 1, 2)]
            lang = CAT_LANG.get(path) or guess_lang(" ".join(bodies[:5]))
            for i, body in zip(range(1, len(parts) - 1, 2), bodies):
                if body:
                    yield body, title, path, shelf, parts[i], lang

# ---------- raw mirror EN HTML (wrappers only cover PDFs) ----------
# RT5 b2 F10 (#207): Spanish Hesperian bodies opened with wiki chrome ("Hesperian Health Guides … En otros idiomas … (not
# mirrored) … Editar los enlaces WikiSalud > …", then the chapter's "En este capítulo:" link list), so MCP snippets and the
# embedding text quoted the chrome instead of the article. These MediaWiki boxes are dropped at index build (Spanish sets).
# Round 9 #207 (b5 W6): English pages drop the language-switch box only ("In other languages English Español 中文 (not
# mirrored) …", 2,105 of 4,640 Hesperian pages opened with it in MCP snippets and Ask passages); the rest of the English
# body is unchanged.
CHROME_IDS = {"p-lang", "bct", "bookinfosidebar", "sidetoc", "catlinks", "mw-js-message"}
CHROME_CLASSES = {"printonly", "noprint", "navlink"}
# round 10 (#271, a7b W7): Ready.gov site chrome (USWDS banner, header, menus, footer: "FIFA World Cup 2026", «Evacuación
# Refugio») was quoted as passages. Dropped in every mode: nav and footer elements, ARIA navigation / banner / contentinfo
# regions, the USWDS banner, header, skip link, side menu, identifier and language list. A plain <header> stays: NCHFP's
# <header class="section__head"> holds the article title and opening paragraph.
SITE_CHROME_TAGS = {"nav", "footer"}
SITE_CHROME_ROLES = {"navigation", "banner", "contentinfo"}
SITE_CHROME_CLASSES = {"usa-banner", "usa-header", "usa-skipnav", "skip-link", "usa-sidenav", "usa-identifier", "usa-footer",
                       "translations-available"}

class Stripper(HTMLParser):
    def __init__(self, chrome=False, ids=()):
        super().__init__(convert_charrefs=True)
        self._ids = CHROME_IDS if chrome else set(ids)
        self.txt, self.title, self.lang = [], "", None
        self._skip, self._in_title = 0, False
        self._chrome, self._cstack = chrome, None  # [tag, depth] while inside a dropped chrome box
    def handle_starttag(self, tag, attrs):
        if self._cstack is not None:
            if tag == self._cstack[0]:
                self._cstack[1] += 1
            return
        if self._ids:
            a = dict(attrs)
            cls = set((a.get("class") or "").split())
            # round 9 #207 (M5): the language switch also carries data-pagefind-ignore on the mirror pages
            if (a.get("id") in self._ids or "data-pagefind-ignore" in a
                    or (self._chrome and CHROME_CLASSES & cls)
                    or tag in SITE_CHROME_TAGS or a.get("role") in SITE_CHROME_ROLES or SITE_CHROME_CLASSES & cls):
                self._cstack = [tag, 1]
                return
        if tag == "html":
            self.lang = dict(attrs).get("lang")
        elif tag in ("script", "style", "noscript"):
            self._skip += 1
        elif tag == "title":
            self._in_title = True
    def handle_endtag(self, tag):
        if self._cstack is not None:
            if tag == self._cstack[0]:
                self._cstack[1] -= 1
                if not self._cstack[1]:
                    self._cstack = None
            return
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False
    def handle_data(self, d):
        if self._cstack is not None:
            return
        if self._in_title:
            self.title += d
        elif not self._skip:
            self.txt.append(d)

READY_LANG_DIRS = {"ar", "de", "es", "fr", "hi", "ht", "ja", "ko", "nl", "pt-br", "ru", "tl", "vi", "zh-hans", "kids"}

def mirror_rows():
    # EN-only mirrors: skip any page whose <html lang> is not en
    en_sets = [
        ("mirrors/hesperian/en.hesperian.org", None),
        ("mirrors/nchfp/nchfp.uga.edu", None),
        ("mirrors/ready_gov/www.ready.gov", READY_LANG_DIRS),
    ]
    for rel, langdirs in en_sets:
        base = os.path.join(LIB, rel)
        for dirpath, dirs, files in os.walk(base):
            if langdirs is not None and dirpath == base:
                dirs[:] = [d for d in dirs if d not in langdirs]
            for fn in sorted(files):
                if not fn.endswith((".html", ".htm")):
                    continue
                fp = os.path.join(dirpath, fn)
                raw = open(fp, encoding="utf-8", errors="replace").read()
                p = Stripper(ids=("p-lang",))
                try:
                    p.feed(raw)
                except Exception:
                    continue
                if p.lang and not p.lang.lower().startswith("en"):
                    continue  # translated page (ready_gov es.html etc.)
                body = re.sub(r"\s+", " ", " ".join(p.txt)).strip()
                if not body:
                    continue
                path = os.path.relpath(fp, LIB)
                title = re.sub(r"\s+", " ", p.title).strip() or fn
                yield body, title, path, shelf_of(path), "0", "en"

    yield from es_rows()

def es_rows():
    # ES mirrors: index Spanish pages
    # ponytail: porter tokenizer used for es rows; switch table tokenizer to unicode61 if es recall measurably suffers
    es_sets = [
        "mirrors/hesperian/es.hesperian.org",
        "mirrors/ready_gov/www.ready.gov/es",
    ]
    for rel in es_sets:
        base = os.path.join(LIB, rel)
        if not os.path.isdir(base):
            continue
        for dirpath, _, files in os.walk(base):
            for fn in sorted(files):
                if not fn.endswith((".html", ".htm")):
                    continue
                fp = os.path.join(dirpath, fn)
                raw = open(fp, encoding="utf-8", errors="replace").read()
                p = Stripper(chrome=True)
                try:
                    p.feed(raw)
                except Exception:
                    continue
                body = re.sub(r"\s+", " ", " ".join(p.txt)).strip()
                if not body:
                    continue
                path = os.path.relpath(fp, LIB)
                title = re.sub(r"\s+", " ", p.title).strip() or fn
                yield body, title, path, shelf_of(path), "0", "es"

# ---------- library-written notes (docs/**/<name>.md, rendered to <name>.html by gen_shelves) ----------
# RT4 class 4 (#193): nothing indexed the D9 car-battery note, so the Ask page never showed it (en41/es41). The body is
# the markdown with link targets and markup removed (the rendered page adds header chrome); the hit opens the .html.
def note_rows():
    for dirpath, _, files in os.walk(os.path.join(LIB, "docs"), followlinks=True):
        for fn in sorted(files):
            if not fn.endswith(".md") or fn.lower().startswith("readme"):
                continue
            md = os.path.join(dirpath, fn)
            page = md[:-3] + ".html"
            if not os.path.isfile(page):
                continue
            text = open(md, encoding="utf-8").read()
            m = re.search(r"^# (.+)$", text, re.M)
            body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
            body = re.sub(r"\s+", " ", re.sub(r"[#*_`>|]+", " ", body)).strip()
            path = os.path.relpath(page, LIB)
            yield body, (m.group(1).strip() if m else fn[:-3]), path, shelf_of(path), "0", guess_lang(body)

# ---------- titles.json ----------
def title_rows():
    d = json.load(open(os.path.join(LIB, "_app", "index", "titles.json")))
    dirs = d["d"]
    for item in d["i"]:
        path = dirs[item[0]] + item[1]
        if not os.path.exists(os.path.join(LIB, path)): continue   # titles.json can lag a removal (r14: 24 removed PDFs)
        yield item[2], path, shelf_of(path)

# ---------- guard drugs from search.html ----------
def guard_names():
    src = open(os.path.join(LIB, "search.html"), encoding="utf-8").read()
    m = re.search(r"var DRUGS = \((.*?)\)\.split\(' '\)", src, re.S)
    if not m:
        sys.exit("FATAL: DRUGS block not found in search.html")
    names = " ".join(re.findall(r"'([^']*)'", m.group(1))).split()
    if len(names) < 100:
        sys.exit(f"FATAL: only {len(names)} drug names parsed (<100)")
    return names

# ---------- climate normals ----------
def climate():
    stations, normals = [], []
    cdir = os.path.join(LIB, "datasets", "climate_normals")
    for fn in sorted(os.listdir(cdir)) if os.path.isdir(cdir) else []:   # not fetched: no climate tool data
        if not fn.endswith(".csv"):
            continue
        temps = {m: [] for m in range(1, 13)}
        winds = {m: [] for m in range(1, 13)}
        sid = name = lat = lon = None
        with open(os.path.join(cdir, fn), newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                if sid is None:
                    sid, name = row["STATION"], row["NAME"].strip()
                    lat, lon = float(row["LATITUDE"]), float(row["LONGITUDE"])
                mo = int(row["month"])
                t = float(row["HLY-TEMP-NORMAL"])
                if t > -9998:
                    temps[mo].append(t)
                w = float(row["HLY-WIND-AVGSPD"])
                if w > -9998:
                    winds[mo].append(w)
        stations.append((sid, name, lat, lon))
        for mo in range(1, 13):
            ts, ws = temps[mo], winds[mo]
            normals.append((sid, mo,
                            min(ts) if ts else None,
                            round(sum(ts) / len(ts), 1) if ts else None,
                            max(ts) if ts else None,
                            round(sum(ws) / len(ws), 1) if ws else None))
    return stations, normals

# ---------- FCC callsigns ----------
def callsign_rows():
    if not os.path.exists(os.path.join(LIB, "datasets", "fcc", "l_amat.zip")):   # not fetched: no callsign lookup
        return []
    z = zipfile.ZipFile(os.path.join(LIB, "datasets", "fcc", "l_amat.zip"))
    with z.open("EN.dat") as f:
        for line in io.TextIOWrapper(f, encoding="latin-1"):
            p = line.rstrip("\r\n").split("|")
            if len(p) < 18 or p[0] != "EN" or not p[4]:
                continue
            yield p[4], p[7], p[16], p[17]

SYNONYMS = [
    # required minimums from R5 spec
    ("chainsaw",        "laceration wound"),
    ("baby",            "infant child"),
    ("outhouse",        "latrine"),
    ("bug out bag",     "emergency kit supplies"),
    ("tarp roof",       "temporary roofing shelter"),
    ("fever 104",       "high fever"),
    ("pond water",      "surface water treatment"),
    ("car battery",     "12 volt battery inverter"),
    ("patch",           "repair"),
    # additional pairs from retrieval.md recommendations + judgment
    ("chainsaw leg",    "laceration amputation"),
    ("tarp",            "emergency roofing temporary shelter"),
    ("go bag",          "emergency supply kit"),
    ("72 hour kit",     "emergency supply kit"),
    ("gut wound",       "abdominal injury"),
    ("deep cut",        "laceration wound"),
    ("won't stop bleeding", "hemorrhage control tourniquet"),
    ("bloody stool",    "gastrointestinal bleeding"),
    ("fever child",     "febrile pediatric"),
    ("sick baby",       "infant illness febrile"),
    ("can't breathe",   "respiratory distress airway"),
    ("pit toilet",      "latrine sanitation"),
    ("latrine dig",     "pit latrine sanitation"),
    ("smoke the meat",  "meat preservation smoking"),
    ("no power",        "power outage emergency preparedness"),
    ("dead battery",    "battery charge power"),
    ("charge phone",    "battery inverter power"),
    ("water filter diy","biosand filter water treatment"),
    ("boil water",      "water purification treatment"),
    ("drinking water",  "water purification potable"),
    ("solar still",     "water collection SODIS"),
    # ES↔EN pairs for Spanish-speaker queries
    ("fiebre",          "fever"),
    ("niño",            "child infant"),
    ("agua",            "water"),
    ("sangrado",        "bleeding"),
    ("quemadura",       "burn"),
    ("parto",           "birth delivery"),
    ("diarrea",         "diarrhea"),
    ("envenenamiento",  "poisoning"),
    ("herida",          "wound"),
    ("hervir",          "boil"),
]

# E22 B (round 8, #238): a document whose catalogue `a` carries the historical line (pre-1945 treatment books, the L5
# wording, the 1940-44 "before modern medicine" form and the eye-care form) is title-only: MCP search_library gives no
# snippet, /semantic no excerpt, and search.html no Pagefind excerpt for it. One list for the server and the page.
HISTORICAL_LINE_RE = re.compile(r"\bit is a historical text\b[^.]*\bnot a guide to (?:examining or )?treating (?:anyone|animals|eyes) today\b")
TITLE_ONLY = os.path.join(LIB, "_app", "index", "title_only.json")


def write_title_only():
    cat = curated()
    paths = sorted(p for p, v in cat.items() if HISTORICAL_LINE_RE.search(v.get("a") or ""))
    with open(TITLE_ONLY, "w", encoding="utf-8") as f:
        json.dump(paths, f, ensure_ascii=False, indent=0)
        f.write("\n")
    print(f"title_only: {len(paths)} documents -> {TITLE_ONLY}", flush=True)


# E27 age weight (round 9, #246): {path: year} for health documents with a catalogue year; mcp_server.py weights their
# ranking (fix plan "Age weight"; field names in redteam_20261026_scripts/index_files.txt). Same prefix list as
# mcp_server.HEALTH_PREFIXES. ponytail: a path-prefix list; a catalogue topic field is the upgrade.
HEALTH_PREFIXES = ("docs/medical/", "docs/HISTORICAL/", "docs/cd3wd/2012/health/", "mirrors/hesperian/",
                   "docs/survivor_library/SurvivalLibrary/library/Medical-") + tuple(
    "docs/survivor_library/SurvivalLibrary/library/%s/" % s for s in ("First Aid", "Dentistry", "Herbalism", "Veterinary"))
HEALTH_YEARS = os.path.join(LIB, "_app", "index", "health_years.json")
OUTDATED_PAGES = os.path.join(LIB, "_app", "index", "outdated_pages.json")


def cat_year(y):
    m = re.search(r"(?<!\d)(1[5-9]\d\d|20[0-2]\d)(?!\d)", y or "")
    return int(m.group(1)) if m and int(m.group(1)) <= 2026 else None


def write_health_years():
    cat = curated()
    years = {p: cat_year(v.get("y")) for p, v in sorted(cat.items()) if p.startswith(HEALTH_PREFIXES)}
    years = {p: y for p, y in years.items() if y}
    with open(HEALTH_YEARS, "w", encoding="utf-8") as f:
        json.dump(years, f, ensure_ascii=False, indent=0, sort_keys=True)
        f.write("\n")
    print(f"health_years: {len(years)} documents -> {HEALTH_YEARS}", flush=True)


# a8 F3 (round 9, #229 #252): every (path, page) whose body the server flags outdated_aid(), so the Search page withholds
# the Pagefind excerpt on that page even when /semantic returned a sibling page. FTS pre-filter on the words every
# outdated_aid rule needs (a bite or sting word, dengue, ipecac, dilution, the old resuscitation methods), then the
# server's own function on the full body.
OUTDATED_FTS = ("snake* OR venom* OR bite* OR bitten OR fang* OR sting* OR stung OR serpient* OR vibora* OR víbora* OR "
                "culebra* OR mordedura* OR veneno* OR picadura* OR dengue OR ipecac* OR dilution OR neck OR breaths OR "
                "schafer OR schaefer OR shafer OR schaffer OR prone OR nielsen OR silvester")


def _dose_shard(args):
    """One worker of the dose pass: every (path, page) of rowid shard k whose body is a server dose_page()."""
    db, k, n = args
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import types
    import mcp_server
    con = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    mcp_server.STATE = types.SimpleNamespace(guard_drugs={r[0].lower() for r in con.execute("SELECT name FROM guard_drugs")})
    out = [(path, int(page)) for path, page, body in
           con.execute("SELECT path, page, body FROM pages WHERE rowid % ? = ?", (n, k)) if body and mcp_server.dose_page(body)]
    con.close()
    return out


def write_outdated_pages(db=DB, out_path=OUTDATED_PAGES, procs=None):
    """outdated_aid() pages (round 9) plus, round 10 (#272 a8 F3), every dose_page() page: the Search page withholds the
    Pagefind excerpt on a listed (path, page) although /semantic never returned it. Documents on title_only.json are already
    title-only on the page and are not listed again. The dose pass reads every page body (no FTS pre-filter: porter unicode61
    keeps "500mg" and "5gr" as one token), in parallel rowid shards."""
    import multiprocessing
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import mcp_server  # main() is __main__-guarded; outdated_aid() needs no STATE
    t0 = time.time()
    con = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    out = {}
    q = "SELECT path, page, body FROM pages WHERE pages MATCH ?"
    for path, page, body in con.execute(q, (OUTDATED_FTS,)):
        if mcp_server.outdated_aid(body or ""):
            out.setdefault(path, set()).add(int(page))
    con.close()
    n_out = sum(map(len, out.values()))
    tonly = set(json.load(open(TITLE_ONLY, encoding="utf-8"))) if os.path.exists(TITLE_ONLY) else set()
    n = procs or max(1, min(16, (os.cpu_count() or 2) - 2))
    with multiprocessing.Pool(n) as pool:
        shards = pool.map(_dose_shard, [(db, k, n) for k in range(n)])
    n_dose = 0
    for path, page in (x for sh in shards for x in sh):
        if path not in tonly:
            n_dose += page not in out.get(path, ())
            out.setdefault(path, set()).add(page)
    out = {p: sorted(v) for p, v in sorted(out.items())}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0, sort_keys=True)
        f.write("\n")
    print(f"outdated_pages: {sum(map(len, out.values()))} pages on {len(out)} documents ({n_out} outdated_aid, {n_dose} more "
          f"dose_page, {time.time()-t0:.0f}s, {n} procs) -> {out_path}", flush=True)


def main():
    if "--title-only" in sys.argv:  # just the lists (no mcp.db rebuild)
        write_title_only()
        write_health_years()
        return
    if "--outdated-to" in sys.argv:  # dry run: outdated_pages from the existing mcp.db into the named file only
        write_outdated_pages(out_path=sys.argv[sys.argv.index("--outdated-to") + 1])
        return
    if "--index-files" in sys.argv:  # title_only, health_years and outdated_pages from the existing mcp.db
        write_title_only()
        write_health_years()
        write_outdated_pages()
        return
    write_title_only()
    write_health_years()
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.executescript("""
    CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
    CREATE VIRTUAL TABLE pages USING fts5(
      body, title, path UNINDEXED, shelf UNINDEXED, page UNINDEXED, lang UNINDEXED,
      tokenize='porter unicode61');
    CREATE VIRTUAL TABLE titles USING fts5(
      title, path UNINDEXED, shelf UNINDEXED, tokenize='porter unicode61');
    CREATE TABLE guard_drugs(name TEXT PRIMARY KEY);
    CREATE TABLE synonyms(term TEXT PRIMARY KEY, expansion TEXT);
    CREATE TABLE stations(id TEXT PRIMARY KEY, name TEXT, lat REAL, lon REAL);
    CREATE TABLE normals(station TEXT, month INT, tmin REAL, tmean REAL,
      tmax REAL, wind_avg REAL, PRIMARY KEY(station, month));
    CREATE TABLE callsigns(callsign TEXT PRIMARY KEY, name TEXT, city TEXT,
      state TEXT);
    """)
    t0 = time.time()
    n = con.executemany("INSERT INTO pages VALUES(?,?,?,?,?,?)", wrapper_rows()).rowcount
    print(f"wrapper pages: {n} ({time.time()-t0:.0f}s)", flush=True)
    n2 = con.executemany("INSERT INTO pages VALUES(?,?,?,?,?,?)", mirror_rows()).rowcount
    n2 += con.executemany("INSERT INTO pages VALUES(?,?,?,?,?,?)", note_rows()).rowcount
    n2_es = con.execute("SELECT count(*) FROM pages WHERE lang='es'").fetchone()[0]
    print(f"mirror pages: {n2} (es: {n2_es}) ({time.time()-t0:.0f}s)", flush=True)
    tn = con.executemany("INSERT INTO titles VALUES(?,?,?)", title_rows()).rowcount
    print(f"titles: {tn}", flush=True)
    drugs = guard_names()
    con.executemany("INSERT OR IGNORE INTO guard_drugs VALUES(?)", [(d,) for d in drugs])
    gc = con.execute("SELECT count(*) FROM guard_drugs").fetchone()[0]
    print(f"guard_drugs: {gc}", flush=True)
    con.executemany("INSERT OR REPLACE INTO synonyms VALUES(?,?)", SYNONYMS)
    sc = con.execute("SELECT count(*) FROM synonyms").fetchone()[0]
    print(f"synonyms: {sc}", flush=True)
    stations, normals = climate()
    con.executemany("INSERT INTO stations VALUES(?,?,?,?)", stations)
    con.executemany("INSERT INTO normals VALUES(?,?,?,?,?,?)", normals)
    print(f"stations: {len(stations)}, normals: {len(normals)}", flush=True)
    cs = con.executemany("INSERT OR REPLACE INTO callsigns VALUES(?,?,?,?)", callsign_rows()).rowcount
    csn = con.execute("SELECT count(*) FROM callsigns").fetchone()[0]
    print(f"callsigns: {csn} (from {cs} EN records, {time.time()-t0:.0f}s)", flush=True)
    pc = con.execute("SELECT count(*) FROM pages").fetchone()[0]
    con.executemany("INSERT INTO meta VALUES(?,?)", [
        ("built_at", time.strftime("%Y-%m-%dT%H:%M:%S")),
        ("pages_count", str(pc)), ("titles_count", str(tn)),
        ("guard_count", str(gc)), ("schema_version", "3")])
    con.commit()
    # (path, page) -> rowid side table: pages' path/page are UNINDEXED in
    # FTS5, so a direct lookup is a full scan (1.6 s on 7.8 GB); /semantic
    # excerpts need it per hit.
    con.execute("CREATE TABLE loc(path TEXT, page INT, rid INT)")
    con.execute("INSERT INTO loc SELECT path, CAST(page AS INT), rowid FROM pages")
    con.execute("CREATE INDEX loc_pp ON loc(path, page)")
    con.execute("INSERT INTO pages(pages) VALUES('optimize')")
    con.execute("INSERT INTO titles(titles) VALUES('optimize')")
    con.commit()
    con.close()
    print(f"done: {DB} {os.path.getsize(DB)} bytes, {time.time()-t0:.0f}s")
    write_outdated_pages()

if __name__ == "__main__":
    main()
