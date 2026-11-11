#!/usr/bin/env python3
"""Lantern build: generate _app/index/*.json from MANIFEST.sha256 + curated files.
Outputs: titles.json, shelves.json, plants.json. Rerunnable. Spec §7 step 2."""
import json, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = f"{BASE}/library"
CUR = f"{BASE}/data"
OUT = os.environ.get("GEN_INDEX_OUT", f"{LIB}/_app/index")  # scratch override for tests

SHELVES = {
    "docs/medical": ("Medical", "TCCC 2024, MSF, WHO, Hesperian, war surgery"),
    "docs/plant_id": ("Plants, mushrooms & the coast", "62 species, edible and deadly, 1 to 6 photos each"),  # RT9 M5 hand-off: duplicate plates removed, counts vary
    "docs/foraging_coastal": ("Coastal foraging", "CA ocean sport fishing regs 2025, CDPH marine biotoxins, WA shellfish ID"),
    "docs/homesteading_extension": ("Homestead & garden", "Canning, dehydrating, seeds, soils, livestock"),
    "docs/food_preservation": ("Food preservation", "USDA Complete Guide to Home Canning 2015"),
    "docs/water": ("Water", "Treatment, storage, quality"),
    "docs/sanitation": ("Sanitation", "Waste, hygiene, disease prevention"),
    "docs/shelter": ("Shelter", "Building, insulation, repair"),
    "docs/fire_safety": ("Fire safety", "Wildfire prep, defensible space"),
    "docs/energy": ("Energy & power", "NEETS electronics course, wood gas, solar"),
    "docs/comms": ("Communications", "Radio, mesh, antennas"),
    "docs/military_manuals": ("Military field manuals", "FM 21-76 survival, Ranger handbook, welding, vehicles, survivability"),
    "docs/death_care": ("Death care", "Body handling, burial, bereavement in disaster"),
    "docs/grain_processing": ("Grain & bread", "Milling, storage, sourdough bread from scratch"),
    "docs/navigation": ("Navigation", "Land nav, celestial"),
    "docs/emergency_mgmt": ("Emergency management", "Planning, response"),
    "docs/nuclear": ("Nuclear", "Fallout, sheltering"),
    "docs/security": ("Community security", "De-escalation, neighborhood watch, mutual aid, personal safety"),
    "docs/textiles": ("Clothing & textiles", "Fabric repair, hand sewing, spinning basics"),
    "docs/mit_ocw": ("MIT OpenCourseWare", "23 college and grad courses"),
    "docs/survivor_library": ("Survivor Library", "7,448 pre-industrial technology scans", True),
    "docs/HISTORICAL": ("Historical medical", "Pre-2010 — background only", True),
    "docs/cd3wd": ("Development handbooks (CD3WD)", "About 6,100 aid-agency how-to manuals, 1970–2012"),
    "docs/school_textbooks": ("School textbooks", "Siyavula grades 4–12 and Connexions open textbooks, about 1,100"),
    "audio/librivox": ("Audiobooks", "52 classics in five age shelves"),
    "video/prelinger": ("Video", "Prelinger archive picks"),
    # RT9 a4 W4 W5 (#255): the number is the count the shelf lists, set at build time (live_desc); letters and counting
    "video/khan_academy": ("Khan Academy lessons", "1,484 maths and science lessons, arithmetic to calculus"),  # live_desc() restates it from the files listed
    "video/preschool": ("Preschool videos", "430 clips: letters, words, counting, telling time, story chapters"),   # RT10 b5 F-M2-6: live_desc
    "maps": ("Maps & charts", "Topo, satellite, nautical, world vectors"),
    "mirrors": ("Site mirrors", "Hesperian, NCHFP, Ready.gov, Sheldon Brown…"),
    "tools": ("Tools", "Sun calculator, converters, offline AI"),
    "datasets": ("Datasets", "Climate normals, ephemeris, FCC callsigns, DailyMed drug labels"),
    "zim": ("Encyclopedias", "Wikipedia, Wiktionary, iFixit, Gutenberg and 30 more reference sets, served by Kiwix"),
}
# E4 (2026-10-04): health shelves show the document year; over MEDICAL_MAX_AGE years old = "background, see newer"
HEALTH_SHELVES = ("docs/medical", "docs/nuclear", "docs/HISTORICAL")
MEDICAL_MAX_AGE = 10
LANG_NAME = {"en": "English", "es": "Spanish", "fr": "French", "pt": "Portuguese", "de": "German", "sw": "Swahili",
             "ar": "Arabic", "ru": "Russian", "zh": "Chinese", "it": "Italian",
             "ko": "Korean", "ja": "Japanese", "vi": "Vietnamese", "nl": "Dutch", "bn": "Bengali", "hi": "Hindi",
             "fa": "Persian", "tl": "Tagalog", "ht": "Haitian Creole", "so": "Somali",
             "da": "Danish", "nb": "Norwegian", "sv": "Swedish", "ne": "Nepali"}  # #75: every label gen_doc_answers emits; #184 (RT3 H3): da/nb/sv/ne rows had no shelf badge
SKIP_EXT = {".sha256", ".part", ".tmp", ".json", ".log", ".css", ".js", ".woff2"}
TITLE_EXT = {".pdf", ".mp3", ".mp4", ".epub", ".zim", ".mbtiles", ".kap", ".zip"}
# single source of truth for HISTORICAL routing (safety invariant 3):
# the True flag on SHELVES entries. gen_shelves + h:1 flags both derive here.
HIST_SHELVES = tuple(k for k, m in SHELVES.items() if len(m) > 2 and m[2])
# per-path gate inside an open shelf (2026-09-30: only the CD3WD health
# category stays behind the interstitial); every gate check uses HIST_PATHS
HIST_PATHS = HIST_SHELVES + ("docs/cd3wd/2012/health/",)
# round 9 a7a W8: the CD3WD health folder also holds engineering and manufacturing papers with no patient care in them
# (power sizing, a refrigerator, a ramp, a wheelchair, an ambulance trailer, sanitary-pad making, an incinerator); they
# open without the patient-care warning. Hand-listed from the folder's 339 titles; a clinical or device-for-treatment
# paper (ECG pad, stents, phototherapy, glasses, first aid) stays gated. Every gate check calls is_hist(p).
HIST_EXEMPT = frozenset("docs/cd3wd/2012/health/" + f for f in (
    "_mc_405_HEALTH_2_jf_en_136310_.pdf", "_mc_437_How_to_Look_After_a_Refrigerator27_717_jf_en_136560_.pdf",
    "_mc_Portable_Wheelchair_Ramp_Design_ap_en_lp_138160_.pdf", "_mc_S00017_bicycle_ambulance_e4c_en_138440_.pdf",
    "_mc_S00063_MIT_Public_Service_Center_presentation_6_10_10_e4c_en_138490_.pdf",
    "_mc_S00063_TIE_SE_Presentation_8_2_10_e4c_en_138520_.pdf", "_mc_S00063_The_Alpha_Prototype_Brochure_e4c_en_138500_.pdf",
    "_mc_S00063_The_Alpha_Prototype_Presentation_e4c_en_138510_.pdf",
    "_mc_S00063_USAID_Komera_Project_Factsheet_e4c_en_138530_.pdf",
    "_mc_S00064_Amos_Winter_LFC_2009_ASME_IDETC_e4c_en_138540_.pdf", "_mc_S00064_USAID_lfc_project_factsheet_e4c_en_138550_.pdf",
    "_mc_ms_medical_waste_incinerator_pa_en_137940_.pdf"))


def is_hist(p):
    """the historical / patient-care gate for one library path"""
    return p.startswith(HIST_PATHS) and p not in HIST_EXEMPT
DEV_PREFIX = ("docs/cd3wd/2012/", "docs/school_textbooks/")  # third Pagefind index: own ranking, never crowds the modern shelves
DEV_DOC_LEVEL = "docs/cd3wd/2012/"  # one record per handbook; textbooks keep page chunks

def load_paths():
    """library-relative paths from the sealed MANIFEST (shared parser)."""
    paths = []
    with open(f"{LIB}/MANIFEST.sha256") as f:
        for line in f:
            if "  " in line:
                p = line.split("  ", 1)[1].strip()
                if p.startswith("library/"):
                    paths.append(p[len("library/"):])
    # rendered .md siblings (gen_shelves.gen_md_siblings) are views, not items
    md = {p[:-3] for p in paths if p.endswith(".md")}
    return [p for p in paths if not (p.endswith(".html") and p[:-5] in md)]

def shelf_of(p):
    top2 = "/".join(p.split("/")[:2])
    top1 = p.split("/")[0]
    return top2 if top2 in SHELVES else (top1 if top1 in SHELVES else None)

_OSMAND = re.compile(r"^([a-z]{2})_(.+?)_(?:northamerica|southamerica|centralamerica|europe|asia|africa|australia-oceania)_\d+\.obf\.zip$", re.I)

# RT9 a3 N1 (#255): the maps shelf's folder headings and its raw-stem rows, named for a reader (gen_shelves.group_title and the
# bulk folder rows fall back to humanize(); these names occur only under maps/). ponytail: a name table, one row per new map folder
MAP_NAMES = {"geofabrik": "OpenStreetMap source data (Geofabrik)", "noaa_charts": "NOAA nautical charts",
             "organicmaps": "Organic Maps region files", "osmand": "OsmAnd region files", "pmtiles": "Built-in map tiles",
             "satellite_ca": "California satellite photos, source file", "topo_ca": "California topographic maps (USGS quads)",
             "us-latest.osm.pbf": "US OpenStreetMap extract (Geofabrik)",
             "us-latest.osm.pbf.md5": "Checksum for the US OpenStreetMap extract", "filelist.txt": "OsmAnd file list",
             "planet.pmtiles": "World vector map (Protomaps)", "satellite_ca.pmtiles": "California satellite tiles for the map page",
             "satellite_ca_naip.mbtiles": "California satellite photos (NAIP, MBTiles)"}

def live_desc(key, desc, counts):
    """RT9 a4 W4 (#255): a shelf line that opens with a file count states the count the shelf lists (hidden title cards and
    second copies left out), so titles.json and shelves.json cannot drift from the shelf page."""
    return re.sub(r"^\d[\d,]*(?= )", f"{counts.get(key, 0):,}", desc) if key in FILE_COUNT_DESC and counts.get(key) else desc

FILE_COUNT_DESC = {"video/khan_academy", "video/preschool"}   # shelf lines whose number counts files (the audiobook "52" counts albums)

def humanize(name):
    if name in MAP_NAMES:
        return MAP_NAMES[name]
    m = _OSMAND.match(name)
    if m:   # RT8 a3 W3 (#243): "Us_new-york_albany_northamerica_2.obf.zip" -> "US New York Albany (OsmAnd)", as the Organic Maps rows
        words = [w if w in ("of", "and") else w.capitalize() for w in re.split(r"[_\-]+", m.group(2).lower())]
        return f"{m.group(1).upper()} {' '.join(words)} (OsmAnd)"
    stem = re.sub(r"\.[a-z0-9]+$", "", name, flags=re.I)
    stem = re.sub(r"[_\-]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem[:1].upper() + stem[1:] if stem else name

_YEAR = re.compile(r"(?<!\d)(1[5-9]\d\d|20[0-2]\d)(?!\d)")

def doc_meta():
    """docs.curated.json: {path: {t, s, a?, y?, l?, src}} (gen_doc_meta + gen_doc_answers). {} when absent."""
    ct_path = os.environ.get("CURATED") or f"{CUR}/docs.curated.json"   # CURATED: a copy (r22 trials)
    return json.load(open(ct_path)) if os.path.exists(ct_path) else {}

def doc_year(path, meta):
    """Year a document was written: gen_doc_answers "y" (read off the copyright page), else the year in the curated
    title, else the last 4-digit year in the file name. "" = unknown."""
    e = meta.get(path, {})
    y = e.get("y", "")
    # #79: a year that is not a publication year. Pre-1800 is genuine only when the file name carries it (the
    # text check was satisfied by VITA's "1600 Wilson Boulevard"); WFS/Gutenberg CD3WD compilations are dated
    # by the compile run (2008), not by the text.
    if y and (("_wfs_gtb_" in path) or (y < "1800" and y not in os.path.basename(path))):
        y = ""
    if y:
        return y
    m = _YEAR.findall(e.get("t", "")) or _YEAR.findall(os.path.basename(path))
    return m[-1] if m else ""

# RT4 #195 (J1/J2 hand-off): library-written notes are not in docs.curated.json (a PDF catalog). Their title and language
# live here so titles.json finds them and the shelf row (gen_shelves: TITLES + doc_lang) shows the accented title and badge.
NOTES = {"docs/energy/charging_a_phone_from_a_car_battery.md": ("Charging a phone from a car battery", "en"),
         "docs/energy/cargar_el_telefono_con_la_bateria_del_carro.md": ("Cargar el teléfono con la batería del carro (Spanish)", "es"),
         # RT5 E4 (K8 notes, K5 #206): Spanish-only notes, linked from the Spanish landing page (K4); titles.json rows carry l="es"
         "docs/military_manuals/encender_fuego_con_lena_mojada.md": ("Encender fuego con leña mojada (Spanish)", "es"),
         "docs/homesteading_extension/cultivos_de_cosecha_rapida.md": ("Cultivos de cosecha rápida (Spanish)", "es"),
         "docs/food_preservation/conservar_carne_con_sal.md": ("Conservar carne con sal (Spanish)", "es")}

def doc_lang(path, meta):
    if path in NOTES:
        return NOTES[path][1]
    e = meta.get(path, {})
    if re.search(r"_po_", os.path.basename(path)) and "cd3wd" in path:
        return "pt"  # #79: VITA "_po_" files are Portuguese; curated l said es
    if e.get("l"):
        return e["l"]
    # RT6 L5 (a4 F1): the file-name language token is a CD3WD naming rule; in a video name "_pt_1" is "part 1" (127 English
    # Khan lessons were badged Portuguese)
    m = re.search(r"_(en|es|fr|pt|sw)_", os.path.basename(path)) if not path.startswith(("video/", "audio/")) else None
    return m.group(1) if m else "en"


OVR_PATH = f"{CUR}/title_overrides.json"
# CD3WD file-name tokens that say nothing about the document (language, series, source codes)
_NOISE = {"en", "lp", "pdf", "jf", "bv", "pa", "sp", "fp", "pc", "trp", "vth", "ss", "gret", "unfao", "siya",
          "cnx", "fr", "es", "po", "ag", "at", "co", "sa", "wa", "me", "ms", "mh", "mc", "ind", "engy", "eg",
          "em", "ed", "wo", "it", "wi", "ma", "bg", "ap", "tech", "inpho", "weir", "skat", "gtb", "wfs", "lstock", "proc", "kno", "dwg", "fo", "mfkh", "sl", "st", "ec", "au", "ac", "cm", "tr", "elct", "sc", "mng"}
_WORDS = {"grd": "grade", "gr": "grade", "vol": "vol.", "pt": "part", "no": "no.", "ch": "chapter"}
_BOLT = re.compile(r"mauser|k11|k31|k98|m96|m41|mosin|enfield|springfield_?1903|bolt", re.I)

def _toks(path):
    stem = re.sub(r"\.[a-z0-9]+$", "", os.path.basename(path), flags=re.I)
    stem = re.sub(r"_\d{5,6}_?$", "", stem)
    return [t for t in re.split(r"[_\-\s.+]+", stem) if t]

def _fname_noise(t, path):
    """CD3WD titles that are the file name ("Ag Pests 5 BV En Lp 114130", "Cattle Marketing (mis 2 weir en lp
    104940)"): drop the parenthesised file-name tail and the series/language/id tokens."""
    if not os.path.basename(path).startswith("_"):  # CD3WD-style names (also under school_textbooks/)
        return t
    ws, ftk = t.split(" "), [x.lower() for x in _toks(path)]
    while len(ws) > 1 and ftk and ws[0].lower() == ftk[0] and ftk[0] in _NOISE:  # "Ag Farm Reaching Poor", "Mc Herb ..."
        ws, ftk = ws[1:], ftk[1:]
    t = " ".join(ws)
    ft = {x.lower() for x in _toks(path)} | {x.lower() for x in re.split(r"[_\s]+", os.path.basename(path))}
    m = re.match(r"^(.*?)\s*\(([^()]*)\)\s*$", t)
    if m and m.group(1) and all(w.lower() in ft or w.isdigit() for w in m.group(2).split()) \
            and any(w.lower() in _NOISE or re.fullmatch(r"\d{5,}", w) for w in m.group(2).split()):
        return m.group(1)  # "(PA SP EN 105390)", "(Ag crops 9 bv en lp 105780)": file-name tail
    m = re.match(r"^(.*?)\s*\(([^()]*)\)$", t)
    body = re.sub(r"\s*\([^()]*\)$", "", t)
    if body and all(w.lower() in ft or w.isdigit() for w in body.split()):  # whole title is the file name
        tail = t[len(body):]
        words = [w for w in body.split() if not (w.lower() in _NOISE or re.fullmatch(r"\d{5,}", w))]
        if len(words) > 1 and re.fullmatch(r"\d{3}", words[0]):
            words = words[1:]  # CD3WD catalogue prefix ("405 Regulator for ...")
        if words:
            return " ".join(words) + tail
    return t

def _labels(path, group, noise=_NOISE):
    """What tells this file from the others sharing its title: the file-name tokens the others do not all have
    ("part 2", "grade 4", "gtz060ae", "PICS"), else the folder."""
    tk = {p: _toks(p) for p in group}
    common = set.intersection(*[{x.lower() for x in v} for v in tk.values()])
    mine = tk[path]
    pick = []
    for i, x in enumerate(mine):
        xl = x.lower()
        # catalogue numbers and page counts ("407", "Plan30", "12pps") are not what tells two files apart
        if xl in common or xl in noise or re.fullmatch(r"\d{3,}|\d+pps|[a-z]+\d{2}", xl):
            continue
        if re.fullmatch(r"\d+", x) or re.fullmatch(r"[a-z]\d+", xl):
            n = x.lstrip("0") or "0" if x.isdigit() else x[1:].lstrip("0") or "0"
            prev = mine[i - 1].lower() if i else ""
            if re.fullmatch(r"[a-z]\d{4,}", xl):
                pick.append("id " + x[1:])
            elif re.fullmatch(r"m\d+", xl):
                pick.append("module " + n)
            elif prev in _WORDS or prev in ("volume", "part", "book", "issue", "module", "chapter"):
                pick.append(f"{_WORDS.get(prev, prev)} {n}")
            else:
                pick.append(f"part {n}")
        else:
            pick.append(x)
    if noise is not _NOISE:  # loose pass: series codes alone are no label
        pick = [x for x in pick if x.lower() not in ("lp", "jf", "bv")]
    tok = " ".join(pick)
    dirs = [p.split("/")[:-1] for p in group]
    odd = [d for d in path.split("/")[:-1] if not all(d in o for o in dirs)]
    dated = [d for d in odd if re.fullmatch(r"20\d\d-\d\d", d)]  # ready.gov upload folders
    odd = [d for d in odd if re.search(r"[A-Za-z]{3}", d) and not re.fullmatch(r"[\d\-]+", d)]
    d = ("in " + humanize(odd[-1])) if odd else (f"posted {dated[-1]}" if dated else "")
    if noise is _NOISE:  # (strict tokens, loose tokens, folder)
        return tok, _labels(path, group, {"en", "pdf"})[0], d
    return tok, d

_SMALL = {"a", "an", "and", "of", "the", "in", "with", "for", "to", "on", "or", "at", "de", "la", "le", "y", "en"}

def _polish(t, path):
    """File-name-derived titles ("Tm 1 205 air navigation 1943", "Child growth chart nwtnd"): Title Case, military
    publication numbers as numbers (TM 1-205). Only when the title carries no capitals of its own."""
    if t[1:] != t[1:].lower():
        return t
    t = re.sub(r"\s\d{6,8}$", "", t)  # trailing file-date (ready.gov "... 01292026")
    t = re.sub(r"^(Tm|Fm|Tc|Atp|Gta|Ar|Dd) (\d+) (\d+)\b", lambda m: f"{m[1].upper()} {m[2]}-{m[3]}", t)
    ws = t.split(" ")
    return " ".join(w if (i and w in _SMALL) or re.search(r"\d", w) else w[:1].upper() + w[1:] for i, w in enumerate(ws))

def _key(t):
    """collision key: search folds case, quotes and dashes, so "Long-Hole" and "Long-hole" are one title"""
    return re.sub(r"[\W_]+", " ", t.casefold()).strip()

_MON = r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(?:\d{1,2},?\s+)?)?"
_Y4 = r"(?:1[5-9]\d\d|20[0-2]\d)"
_DATE_PART = re.compile(rf"(?:(?:Revised|Rev\.|Updated|Reprinted|Printed)\s+)?(?:\d{{1,2}}/(?:\d{{1,2}}/)?)?{_MON}{_Y4}")
# "1979", "April 2018", "Revised 3/5/2018"; a range ("1900-1950") is a period, a name
_TAIL = re.compile(r"^(.*?,\s*)([^,()]*?)(\s*(?:\([^()]*\)\s*)*)$")  # "Survey, 1874 (Spanish)": the part after the last comma

def _date_parts(t):
    """#129: the comma parts of every parenthetical, plus the part after the title's last comma. A part that is only
    a date (_DATE_PART) is where a title prints a year. Years in the wording ("Act of 1887",
    "Winchester Model 1892", "(1900-1950)", "(1996 Japan Patent Method)") and collision labels ("posted 2019-06",
    "in Medical Medicine 1900 1922") are names, not dates."""
    out = [re.split(r"\s*,\s*", c) for c in re.findall(r"\(([^()]*)\)", t)]
    m = _TAIL.match(t)
    return out + ([[m[2].strip()]] if m else [])

def date_years(t):
    return [y for parts in _date_parts(t) for x in parts if _DATE_PART.fullmatch(x) for y in _YEAR.findall(x)]

EDITION = re.compile(r"\b(?:edition|edici[oó]n|[ée]dition|edi[çc][ãa]o|ausgabe|printing|impression)\b", re.I)

def year_is_y(t, y):
    """#129 (2026-10-07): a reader sees the year field only, so a date in the title that is not y becomes y
    (dropped when y is unknown). "(FAO, 1979)" -> "(FAO, 1988)", "(SKAT, 1993, 1997)" -> "(SKAT, 1993)"."""
    def fix(parts):
        out = []
        ed = any(EDITION.search(x) for x in parts)   # #139: "(New Edition, 2019)" names a printing: y never replaces its
        for x in parts:                               # date (that paired "New Edition" with a chapter's 2023); dropped
            if _DATE_PART.fullmatch(x) and set(_YEAR.findall(x)) != {y}:
                x = "" if ed else y
            if x and not (x == y and y in out):
                out.append(x)
        return ", ".join(out)
    def paren(m):
        s = fix(re.split(r"\s*,\s*", m[1]))
        return f" ({s})" if s else ""
    t = re.sub(r"\s*\(([^()]*)\)", paren, t).strip()
    m = _TAIL.match(t)
    if m and _DATE_PART.fullmatch(m[2].strip()) and set(_YEAR.findall(m[2])) != {y}:
        t = (m[1] + y if y else m[1].rstrip(", ")) + m[3]
    return t

# #139: a language suffix is always the English name from LANG_NAME ("(Português)", "(বাংলা)", "(Bangla)" -> "(Portuguese)",
# "(Bengali)"), and a compilation's series name is in the document's language (VITA's own headers: "EL BOLETÍN TÉCNICO",
# "BULLETIN TECHNIQUE", "BOLETIM TÉCNICO"), never the English "VITA Technical Papers:" on an es/fr/pt volume
NATIVE = {"português": "pt", "portugues": "pt", "portugués": "pt", "español": "es", "espanol": "es", "castellano": "es",
          "français": "fr", "francais": "fr", "deutsch": "de", "বাংলা": "bn", "bangla": "bn", "tiếng việt": "vi",
          "kiswahili": "sw", "nederlands": "nl", "italiano": "it", "русский": "ru", "中文": "zh", "简体中文": "zh",
          "한국어": "ko", "日本語": "ja", "العربية": "ar", "فارسی": "fa", "دری": "fa", "हिन्दी": "hi", "kreyòl ayisyen": "ht",
          "af-soomaali": "so", "soomaali": "so", "polski": "pl"}
COMP_PREFIX = {"en": "VITA Technical Papers", "es": "Boletines técnicos VITA", "fr": "Bulletins techniques VITA",
               "pt": "Boletins técnicos VITA"}
_EN_SERIES = re.compile(r"^\s*VITA?\s+Technical\s+(?:Papers?|Bulletins?)\s*:\s*", re.I)

def title_lang(t, l):
    """#139, a pure dictionary step (gen_index and r22_regen.sh's curated `t` sync): native language names -> the
    English name, English VITA series prefix -> the document language's"""
    def nat(m):
        parts = [LANG_NAME.get(NATIVE[x.casefold()], x) if x.casefold() in NATIVE else x for x in re.split(r"\s*,\s*", m[1])]
        return "(" + ", ".join(parts) + ")"
    t = re.sub(r"\(([^()]*)\)", nat, t)
    if l in COMP_PREFIX and l != "en":
        t = _EN_SERIES.sub(COMP_PREFIX[l] + ": ", t)
    return t

def lang_from_l(t, l):
    """#126: a "(Language)" in a title comes only from `l`. A parenthetical naming one language that is not
    LANG_NAME[l] ("(German)" from an "Original title:" line on the English GTZ text) loses that name; it is never
    swapped. Bilingual lists ("(English, Spanish)" on a glossary) are left alone."""
    names = {v.lower() for v in LANG_NAME.values()} | {"english"}
    mine = LANG_NAME.get(l, "English").lower()
    def fix(m):
        parts = re.split(r"\s*,\s*", m[2])
        if sum(x.lower() in names for x in parts) != 1:
            return m[0]
        parts = [x for x in parts if not (x.lower() in names and x.lower() != mine)]
        return f"{m[1]}({', '.join(parts)})" if parts else ""
    return re.sub(r"(\s*)\(([^()]*)\)", fix, t).strip()

NONCANON = {l.strip() for l in open(f"{CUR}/noncanonical_paths.txt") if l.strip() and not l.startswith("#")} \
    if os.path.exists(f"{CUR}/noncanonical_paths.txt") else set()

def resolve_titles(meta):
    """E3: path -> display title. Titles that collide get what tells them apart: Wood Magazine issues their issue
    number, everything else "(year, Language)" with only the parts the title does not already carry.
    "Compost (Swahili, 2002)" rather than two rows called "Compost"."""
    base = {p: (e.get("t") or humanize(os.path.basename(p))) for p, e in meta.items()}
    base.update({p: t for p, (t, _) in NOTES.items() if p not in base})
    for p in base:  # #79 rules
        # #184 (RT3 H3): a curated title in a sentence-case language ("Los planes de preparación de emergencia") is not a
        # file name; Title Case is for file-name-derived and English titles only
        keep = p in NOTES or (meta.get(p, {}).get("t") and doc_lang(p, meta) != "en")   # a note title is hand-written
        base[p] = _fname_noise(base[p], p) if keep else _polish(_fname_noise(base[p], p), p)
        if _BOLT.search(os.path.basename(p)):  # "semi_automatic_rifle" is the source folder's naming, not a fact
            base[p] = re.sub(r"Semi-?\s?Automatic (Rifle|Carbine)", r"\1", base[p], flags=re.I)
        base[p] = lang_from_l(title_lang(base[p], doc_lang(p, meta)), doc_lang(p, meta))
    ovr = json.load(open(OVR_PATH)) if os.path.exists(OVR_PATH) else {}
    base.update({p: t for p, t in ovr.items() if p in base})  # genuine one-offs: path -> corrected title (wins over every rule)
    for p in base:  # every Wood Magazine issue, collision or not (the owner E3): "Wood Magazine issue 4 (1985)"
        m = re.search(r"wood_magazine_(\d+)_(\d{4})", os.path.basename(p))
        if m:
            base[p] = f"Wood Magazine issue {int(m.group(1))} ({m.group(2)})"
        # Hesperian chapter files (en_nwtnd_2014_03g.pdf = New Where There Is No Doctor chapter 3) share one book title
        m = re.search(r"^en_(nwtnd|dent|cgeh|dvc)_(\d{4})_(\d{1,2})[a-z]?(?:_.*)?\.pdf$", os.path.basename(p))
        if m and not re.search(r"\bch(apter|\.)", base[p].lower()):
            t = re.sub(r"\s*\((?:Hesperian, )?\d{4}\)$", "", base[p])
            y = doc_year(p, meta)  # #129: the page-footer year, not the folder year
            base[p] = f"{t}, chapter {int(m.group(3))}" + ("" if not y or y in t else f" ({y})")
        if p not in ovr:  # #129: hand-checked titles keep their year; check_titles reports a mismatch
            base[p] = year_is_y(base[p], doc_year(p, meta))
    seen = {}
    for p, t in base.items():
        seen.setdefault(_key(t), []).append(p)
    out = dict(base)
    for ps in seen.values():
        if len(ps) < 2:
            continue
        for p in ps:
            t = base[p]
            if p in ovr:  # hand-checked title: no curated year/language tacked on
                continue
            y, l = doc_year(p, meta), doc_lang(p, meta)
            parts = []
            if l != "en" and LANG_NAME.get(l, "").lower() not in t.lower():
                parts.append(LANG_NAME.get(l, l))
            if y and y not in t:
                parts.append(y)
            out[p] = f"{t} ({', '.join(parts)})" if parts else t
    # still identical (same year, same language, or a suffix landed on another title): number the printings
    for _ in range(2):  # #79: part/volume/grade/folder from the file name before numbering copies
        still = {}
        for p, t in out.items():
            still.setdefault(_key(t), []).append(p)
        for ps2 in still.values():
            if len(ps2) > 1:
                # drop label words the title already has (", dryer" on "Solar Crop Dryer"); a run of more than
                # four file-name words is not a label
                def tidy(p, l):
                    have = set(_key(out[p]).split())
                    w = [x for x in l.split() if not (x.isalpha() and x.lower() in have)]
                    return " ".join(w) if len(w) <= 4 else ""
                pairs = {p: (tidy(p, v[0]), tidy(p, v[1]), v[2]) for p in ps2 for v in [_labels(p, ps2)]}
                for pick in (lambda v: v[0], lambda v: v[1], lambda v: v[2], lambda v: ", ".join(x for x in v[1:] if x)):
                    labs = {p: pick(v) for p, v in pairs.items()}
                    if len(set(labs.values())) == len(ps2):  # one member may stay bare ("" is a label too)
                        for p in ps2:
                            if labs[p]:
                                out[p] = f"{out[p]}, {labs[p]}"
                        break
    still = {}
    for p, t in out.items():
        still.setdefault(_key(t), []).append(p)
    for ps2 in still.values():
        if len(ps2) > 1:
            ids = {p: re.search(r"_(\d{5,6})_?\.", os.path.basename(p)) for p in ps2}  # CD3WD catalogue number
            if all(ids.values()) and len({i[1] for i in ids.values()}) == len(ps2):
                for p in ps2:
                    out[p] = f"{out[p]}, no. {ids[p][1]}"
                continue
            for i, p in enumerate(sorted(ps2), 1):
                out[p] = f"{out[p]}, copy {i}"
    # FIXES #161: audio/video labels (LibriVox section titles, Prelinger film titles, preschool clips) from
    # gen_media_titles.py; these paths have no docs.curated.json entry, so they fell through to humanize()
    if os.path.exists(f"{CUR}/media_titles.json"):
        out.update(json.load(open(f"{CUR}/media_titles.json")))
    return out

def gen_species(curated_path, dir_prefix, out_name, default_cat):
    """plants.json / coastal.json: curated entries + photo paths per species."""
    cur = json.load(open(curated_path))
    out = []
    for slug, meta in sorted(cur.items()):
        if slug.startswith("_"):
            continue
        if not os.path.isdir(f"{LIB}/{dir_prefix}"):   # photos not fetched (download_plant_images.py / ..._coastal_...)
            break
        d = f"{LIB}/{dir_prefix}/{slug}"
        names = set(os.listdir(d))
        photos = sorted(x for x in names
                        if x.lower().endswith((".jpg", ".jpeg", ".png")) and ".640." not in x)
        # prefer the 640px derivative when make_640.sh has produced one
        photos = [x if f"{x.rsplit('.', 1)[0]}.640.{x.rsplit('.', 1)[1]}" not in names
                  else f"{x.rsplit('.', 1)[0]}.640.{x.rsplit('.', 1)[1]}" for x in photos]
        if not photos:
            print(f"WARN no photos: {slug}", file=sys.stderr)
            continue
        out.append({"slug": slug, "name": humanize(slug), "kind": meta["kind"],
                    "cat": meta.get("category", default_cat),
                    "label": meta["label"], "note": meta["note"],
                    "lookalike": meta["lookalike"], "es": meta.get("es", []),   # #177: Spanish common names
                    "photos": [f"{dir_prefix}/{slug}/{x}" for x in photos]})
    json.dump(out, open(f"{OUT}/{out_name}.json", "w"), separators=(",", ":"))
    return out

def kiwix_books():
    """E6: [{file, title, summary, lang, size, date, articles, stem}] from data/kiwix_catalog.xml (OPDS,
    saved by fetch_kiwix_catalog.sh from kiwix-serve /catalog/v2/entries?count=-1). Only books whose .zim is on disk."""
    import xml.etree.ElementTree as ET
    xml = f"{CUR}/kiwix_catalog.xml"
    if not os.path.exists(xml):
        return []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    on_disk = {f for f in os.listdir(f"{LIB}/zim") if f.endswith(".zim")} if os.path.isdir(f"{LIB}/zim") else set()
    out = []
    for e in ET.parse(xml).getroot().findall("a:entry", ns):
        g = lambda tag: (e.find(f"a:{tag}", ns).text or "").strip() if e.find(f"a:{tag}", ns) is not None else ""
        link = e.find("a:link[@type='text/html']", ns)
        stem = (link.get("href", "") if link is not None else "").rsplit("/", 1)[-1]
        if not stem or f"{stem}.zim" not in on_disk:
            continue
        size = next((int(l.get("length", 0)) for l in e.findall("a:link", ns) if l.get("length")), 0) \
            or os.path.getsize(f"{LIB}/zim/{stem}.zim")
        out.append({"file": f"{stem}.zim", "stem": stem, "title": g("title"), "summary": g("summary"),
                    "lang": g("language").split(",")[0], "size": size, "date": g("issued")[:10] or g("updated")[:10],
                    "articles": int(g("articleCount") or 0)})
    return sorted(out, key=lambda z: z["title"].lower())

def main():
    os.makedirs(OUT, exist_ok=True)
    paths = load_paths()

    # titles.json — searchable docs only, not every mirror asset/tile
    meta = doc_meta()
    curated_titles = resolve_titles(meta)  # E3: collisions carry year/language
    # E6: encyclopedia titles from the kiwix catalog (fetch_kiwix_catalog.sh), not the file name
    zlang = {}   # RT5 #206: row language for titles.json (kiwix gives ISO 639-3: eng, spa)
    for z in kiwix_books():
        curated_titles[f"zim/{z['file']}"] = z["title"]
        zlang[f"zim/{z['file']}"] = {"eng": "en", "spa": "es", "fra": "fr", "por": "pt"}.get(z["lang"], z["lang"][:2] or "en")
    titles, counts = [], {}
    # RT9 a4 W4 (#255): count what the shelf page lists (gen_shelves n_files): no hidden title cards (media_titles "hide:"),
    # no .md views on the audio and video shelves
    hidden = ({k[5:] for k in json.load(open(f"{CUR}/media_titles.json")) if k.startswith("hide:")}
              if os.path.exists(f"{CUR}/media_titles.json") else set())
    for p in paths:
        ext = os.path.splitext(p)[1].lower()
        shelf = shelf_of(p)
        if shelf and p not in hidden and not (shelf.startswith(("audio/", "video/")) and ext == ".md"):
            counts[shelf] = counts.get(shelf, 0) + 1
        if ext not in TITLE_EXT:
            continue
        if p in hidden:
            continue  # RT10 a4 F4 (#256): a hidden second copy or silent title card leaves the front-page title search too
        if p.startswith(("mirrors/", "maps/noaa_charts/rnc", "maps/topo_ca",
                         "datasets/dailymed", "kolibri_data/")):
            continue  # bulk sets, raw drug labels (dosing gate), kolibri blobs stay out
        if p in NONCANON:
            continue  # FIXES #111: a duplicate copy; its canonical twin carries the title
        t = curated_titles.get(p) or humanize(os.path.basename(p))
        e = {"t": t, "p": p, "l": zlang.get(p) or doc_lang(p, meta)}
        if is_hist(p):
            e["h"] = 1  # HISTORICAL: UI must route via _app/historical.html
        titles.append(e)
    # library-written notes: listed from the .md source (RT5 follow-up 3: gen_index runs before gen_shelves renders the
    # .html, so waiting for the .html left new notes out); the row opens the rendered page gen_shelves writes next.
    # E6 (#206): a Spanish note carries l="es", so English mode drops it and Spanish mode finds it (search.html, K2)
    for p in NOTES:
        if os.path.exists(f"{LIB}/{p}"):
            titles.append({"t": curated_titles[p], "p": p[:-3] + ".html", "l": NOTES[p][1]})
    # shelf pseudo-entries (search_design.md: +3/50 hit@3 — shelf names carry
    # vocabulary no doc title has). p="shelf:<key>"; UI links _app/shelf/<slug>.html
    for key, meta in SHELVES.items():
        if not counts.get(key):
            continue  # empty shelf (no content yet) — don't advertise in search
        e = {"t": f"{meta[0]} — {live_desc(key, meta[1], counts)}", "p": f"shelf:{key}"}
        if len(meta) > 2 and meta[2]:
            e["h"] = 1
        titles.append(e)
    # species rows (H26): the 86 plants/coastal species live only in
    # plants.json/coastal.json, so title search missed "chanterelle" etc.
    # Deep-link scheme plants.html#(plants|coastal)/<slug> opens the card.
    plants = gen_species(f"{CUR}/plants.curated.json", "docs/plant_id", "plants", "plant")
    coastal = gen_species(f"{CUR}/coastal.curated.json", "docs/coastal_id", "coastal", "coastal")
    # E6 (#206, K7 hand-off): the English row carries English only; the Spanish names (#177: "mejillones" finds the card)
    # go on a separate Spanish-only row that opens K7's Spanish view. search.html drops "?lang=es" rows in English mode (K2).
    for tab, rows in (("plants", plants), ("coastal", coastal)):
        for x in rows:
            titles.append({"t": f"{x['name']} ({x['cat']}, {x['label'].lower()})", "p": f"plants.html#{tab}/{x['slug']}"})
            if x.get("es"):
                titles.append({"t": ", ".join(x["es"]) + (" (ficha de planta)" if tab == "plants" else " (ficha de la costa)"),
                               "p": f"plants.html?lang=es#{tab}/{x['slug']}", "l": "es"})
    assert not any(x["p"].startswith("datasets/dailymed") for x in titles), \
        "dosing-leak gate: dailymed in titles.json"
    # dir-prefix packing (A7 <1.2MB budget): {"d":[dirnames],"i":[[di,base,t(,h)(,l)]]}
    # app.js decodeTitles() expands back to [{t,p,h?}] at load. RT5 #206 (E6): element 4 is the row language (ISO 639-1),
    # present only when it is not "en" (then element 3 is h as 1/0); absent = "en". Shelves and English species rows: "en"
    dirs, didx, packed = [], {}, []
    for e in titles:
        p = e["p"]
        k = p.rfind("/") + 1
        d, b = p[:k], p[k:]
        if d not in didx:
            didx[d] = len(dirs)
            dirs.append(d)
        it = [didx[d], b, e["t"]]
        lang = e.get("l") or "en"
        if lang != "en":
            it += [1 if e.get("h") else 0, lang]
        elif e.get("h"):
            it.append(1)
        packed.append(it)
    json.dump({"d": dirs, "i": packed}, open(f"{OUT}/titles.json", "w"),
              separators=(",", ":"))

    # triage synonym map ships beside the indexes (search pin layer)
    syn = json.load(open(f"{CUR}/triage_synonyms.json"))
    syn = {k: v for k, v in syn.items() if not k.startswith("_")}
    json.dump(syn, open(f"{OUT}/triage_synonyms.json", "w"), separators=(",", ":"))

    # .js wrappers: Chrome blocks XHR/fetch on file:// — direct mode loads
    # these via <script> instead (T6/T7 direct-mode search requirement)
    def js_wrap(name, obj):
        with open(f"{OUT}/{name}.js", "w") as f:
            f.write(f"window.LANTERN_{name.upper()}=")
            json.dump(obj, f, separators=(",", ":"))
    js_wrap("titles", {"d": dirs, "i": packed})
    js_wrap("synonyms", syn)
    # E1a: survival synonym table (en + es), applied by search.html before pagefind
    ssyn = {k: v for k, v in json.load(open(f"{CUR}/search_synonyms.json")).items() if not k.startswith("_")}
    json.dump(ssyn, open(f"{OUT}/search_synonyms.json", "w"), separators=(",", ":"), ensure_ascii=False)
    js_wrap("search_synonyms", ssyn)

    # shelves.json — ORDER CONVENTION (09-19): survival-priority
    # shelves first in curated order, everything else alphabetical.
    # Landing grid, sidebar, and the search filter rail all inherit this.
    PRIORITY = ["docs/medical", "docs/plant_id", "docs/food_preservation",
                "docs/water", "docs/sanitation"]
    shelves = []
    for key, meta in SHELVES.items():
        if not counts.get(key):
            continue  # empty shelf — sidebar/landing skip it until content lands
        hist = len(meta) > 2 and meta[2]
        shelves.append({"path": key, "title": meta[0], "desc": live_desc(key, meta[1], counts),
                        "count": counts.get(key, 0), "historical": bool(hist)})
    shelves.sort(key=lambda s: (PRIORITY.index(s["path"]), "")
                 if s["path"] in PRIORITY else (len(PRIORITY), s["title"].lower()))
    json.dump(shelves, open(f"{OUT}/shelves.json", "w"), indent=1)
    js_wrap("shelves", shelves)

    js_wrap("plants", plants)
    js_wrap("coastal", coastal)
    print(f"titles={len(titles)} shelves={len(shelves)} plants={len(plants)} coastal={len(coastal)}")
    sz = os.path.getsize(f"{OUT}/titles.json")
    print(f"titles.json {sz/1024:.0f} KB {'OK' if sz < 2_000_000 else 'OVER 2MB BUDGET'}")
    assert sz < 2_000_000, "titles.json over 2MB budget"  # raised from 1.2MB for the 6,400 CD3WD titles (2026-09-30)

if __name__ == "__main__":
    main()
