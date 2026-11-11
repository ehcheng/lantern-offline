#!/usr/bin/env python3
"""E1c: per-document "what this answers" (two sentences, in the document's own language), year and language
for every entry in docs.curated.json. Adds keys  a (answers), y (year or ""), l (ISO 639-1 lang)  to each entry;
only entries missing "a" are generated, so reruns resume. Text comes from gen_text's pdftotext cache (same prose()
cleaner as gen_doc_meta); figure-only docs use their vision description as the excerpt.
Usage: python3 gen_doc_answers.py [--limit N] [--only PREFIX] [--threads 4] [--model qwen3:32b]
       python3 gen_doc_answers.py --verify [--dups]   (no model; marks entries for regen, sets y and l by rule)
       python3 gen_doc_answers.py --selftest          (year rule on the judge's examples, echo regex, language detector)
"""
import difflib, json, os, re, sys, threading, time, unicodedata, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from gen_text import LIB, extract
from gen_doc_meta import OUT, prose, MIN_CLEAN, HEAD, TAIL
from gen_index import humanize

def opt(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
URL = "http://127.0.0.1:11434"
MODEL = opt("--model", "qwen3:32b")
PATHS = {l.strip() for l in open(opt("--paths", ""))} if "--paths" in sys.argv else None   # trials: only these entries
MARK = "--mark" in sys.argv   # r21 one-time: also queue reference lists (#127) and compilations (#128)
LIMIT = int(opt("--limit", 0)); ONLY = opt("--only", ""); SKIP = opt("--skip", "\0"); THREADS = int(opt("--threads", 4))

# Language (#75). The model is TOLD the language instead of guessing it (told "Spanish excerpt = Spanish sentences" it
# answered 24 English docs in Spanish). One detector for generation and --verify: script share first (ready.gov
# ko/zh/ja/ar/ru/hi sheets, Practical Action Bangladesh "_ms_..._pa_" manuals in Bengali, Hesperian Dari/Russian),
# then a stopword vote over Latin-script languages where only words unique to one language carry a vote.
LANG_NAME = {"en": "English", "es": "Spanish", "fr": "French", "pt": "Portuguese", "de": "German", "nl": "Dutch", "el": "Greek",
             "it": "Italian", "vi": "Vietnamese", "ht": "Haitian Creole", "so": "Somali", "sw": "Swahili", "tl": "Tagalog",
             "id": "Indonesian", "pl": "Polish", "ko": "Korean", "zh": "Chinese", "ja": "Japanese", "ar": "Arabic",
             "fa": "Persian", "ur": "Urdu", "ru": "Russian", "hi": "Hindi", "bn": "Bengali", "da": "Danish",   # da: G3 2026-10-10 #174
             "nb": "Norwegian", "sv": "Swedish", "ne": "Nepali"}   # RT3 H3 #184
_STOP = {"en": "the and of to in is for that with are this be on which you can not have from their",
         "es": "que los las una por para con del como pero más sus está esta este cuando también entre sobre hasta",
         "fr": "les des une pour dans sur avec pas cette qui est sont aux leur elle nous vous dont",
         "pt": "não uma dos das com para que mais como ou seu também pelo são pela ainda muito foi quando",
         "de": "und nicht eine mit den dem von für auch werden wird sind oder bei nach durch über zwischen",
         "nl": "het een van zijn voor niet worden ook bij aan wordt deze naar zoals kunnen wat",
         "it": "della delle degli sono anche nel nella alla dei gli questo questa essere più perché",
         "vi": "và của là có những các được trong không một người này với để khi cho",
         "ht": "nan pou yo ki li gen fè tout moun kapab sou lè ak",
         "so": "iyo waxaa ayaa waa oo ee kale loo haddii sida ama",
         "sw": "katika kwa ya wa za hii kuwa ni au cha vya",
         "tl": "ang mga ng sa ay ito kung hindi isang nang",
         "id": "dan yang ini itu dengan untuk dari tidak dalam akan pada",
         "pl": "się jest że dla oraz przez jak może być które",
         "da": "og det til er af på med som ikke kan skal eller når ved"}   # G3 2026-10-10 #174: two Danish CD3WD manuals
_cnt = {}
for _ws in _STOP.values():
    for _w in _ws.split():
        _cnt[_w] = _cnt.get(_w, 0) + 1
_STOP = {l: {w for w in ws.split() if _cnt[w] == 1} for l, ws in _STOP.items()}
def vote(text, counts=None):
    """(lang, share, total) over the first 200k chars; share = winner's stopwords / all stopwords. counts: a dict to fill"""
    c, seen = {l: 0 for l in _STOP}, {l: set() for l in _STOP}
    text = re.sub(r"(?:https?://|www\.)\S+|\S+\.(?:com|org|net|gov|edu)\b\S*", " ", text[:200000])   # ".com" voted Portuguese
    for w in re.findall(r"[^\W\d_]+", text.lower()):
        for l, s in _STOP.items():
            if w in s:
                c[l] += 1; seen[l].add(w)
    c = {l: n if len(seen[l]) >= 3 else 0 for l, n in c.items()}   # one repeated word is not a language
    if counts is not None:
        counts.update(c)
    tot = sum(c.values())
    if not tot:
        return "", 0.0, 0
    l = max(c, key=c.get)
    return l, c[l] / tot, tot

# only scripts the corpus holds (10-06 scan: Han, Bengali, Hangul, Arabic, Cyrillic, kana, Devanagari); Greek left out:
# the one Greek-heavy doc is an English course on Greek. CJK weighs 2 (one character carries about a word).
_SCRIPT = [(l, re.compile("[%s]" % r), w) for l, r, w in (
    ("ko", "가-힣ᄀ-ᇿ㄰-㆏", 2), ("ja", "぀-ヿ", 2), ("zh", "一-鿿㐀-䶿", 2),
    ("ar", "؀-ۿݐ-ݿ", 1), ("ru", "Ѐ-ӿ", 1), ("hi", "ऀ-ॿ", 1), ("bn", "ঀ-৿", 1))]
_LATIN = re.compile(r"[A-Za-zÀ-ɏḀ-ỿ]")
_ARABIC_NAME = re.compile(r"(?<![a-z])(?:prs|fa|farsi|persian|dari)(?![a-z])|(?<![a-z])(ur|urdu)(?![a-z])", re.I)
def script_lang(text, name=""):
    """non-Latin script code when that script is >= 30% of the weighted letters (and >= 50 chars), else ""."""
    t = text[:200000]
    n = {l: len(r.findall(t)) * w for l, r, w in _SCRIPT}
    if n["ja"] > 0.1 * n["zh"]:
        n["ja"] += n["zh"]; n["zh"] = 0   # kana present: Japanese text carries Han too
    l = max(n, key=n.get)
    if n[l] < 100 or n[l] < 0.3 * (n[l] + len(_LATIN.findall(t))):
        return ""
    if l == "ar":
        m = _ARABIC_NAME.search(name.replace("_", " "))
        return ("ur" if m.group(1) else "fa") if m else "ar"
    return l

# #131: a language named in the filename. Words beat codes; two different codes ("_en_es_" glossary) say nothing.
# cd3wd category prefixes (_it_ = IT, _ed_, _sp_ ...) are not language codes, so only po/pt/es/fr count as codes.
_NAME_WORD = {"portuguese": "pt", "portugues": "pt", "spanish": "es", "espanol": "es", "french": "fr", "francais": "fr",
              "vietnamese": "vi", "german": "de", "deutsch": "de", "dutch": "nl", "swahili": "sw", "indonesian": "id",
              "tagalog": "tl", "haitian": "ht", "somali": "so"}
_NAME_CODE = {"po": "pt", "pt": "pt", "es": "es", "fr": "fr"}
def name_lang(name):
    toks = re.split(r"[^a-z]+", name.lower().replace("ñ", "n").replace("ç", "c").replace("ê", "e"))
    words = {_NAME_WORD[t] for t in toks if t in _NAME_WORD}
    codes = {_NAME_CODE[t] for t in toks if t in _NAME_CODE} | ({"en"} if "en" in toks else set())
    if len(words) == 1:
        return words.pop()
    return codes.pop() if len(codes) == 1 and not words else ""

# Vietnamese typed in the VNI font and extracted as Latin-1 ("Chöông trình Giaûng daïy", "vaø", "cuûa"): no stopword
# matches and no Vietnamese script, so the vote saw 0-11 words
_VNI = re.compile(r"(?<!\w)(?:vaø|cuûa|laø|ñeå|caùc|nhöõng|ñöôïc|moät|naøy|ngöôøi|khoâng|chöông|giaûng|daïy|baøi|ñoà|thò|söû|duïng|trình)(?!\w)")
# a vision description that names the language ("A guide in Bengali on ...") is the only evidence for an image-only file
def vl_lang(s):
    names = {v: k for k, v in LANG_NAME.items() if k != "en"} | {"Bangla": "bn", "Farsi": "fa", "Dari": "fa"}
    m = re.search(r"\b(?i:in|written in) (%s)\b|\b(?i:an?) (%s)-language\b|\b(?i:an?) (Bangla|Bengali)\b"
                  % ("|".join(names), "|".join(names)), s or "")
    m = m and (m.group(1) or m.group(2) or m.group(3))   # "in Bengali", "A Bangla-language guide", "A Bangla guide";
    # not "A German textbook": GTZ courses are English with a German original title, so that adjective is not evidence
    return names[m] if m else ""

LANG_FIX = {  # read by hand (r21 titles list): Spanish course whose English CNX licence boilerplate ties the vote (es 72, en 65)
    "Curso_de_elaboraci_artesanal_de_vino_arts_arts_cnx_x10660_.pdf": "es",
    "schweizerische_armee_model1878_revolver.pdf": "de",   # German/French Swiss Army manual (de 151, fr 165, en 37), title German
    # #158 (red team 10-09 b1mech lang, text windows read by hand): the vote's English share of a bilingual or
    # licence-padded text kept these at en; the body is another language
    "_ag_sorghum_millets_human_nutrition_27_2_es_unfao_lp_116900_.pdf": "es",   # es 2606 / en 1181
    "_wa_Drinking_Water_skat_en_150750_.pdf": "de",   # SKAT/AGUASAN workshop papers, de 2400 / en 698
    "_wa_Vocational_Training_German_skat_en_153190_.pdf": "de",   # de 681 / en 414
    "_wa_Water_who_pays_skat_en_153630_.pdf": "de",   # "Wasser ist kein freies Gut (mehr) - Wer bezahlt?", de 3355 / en 1235
    "Claude_Oscar_Monet_impressionist_artist_painter_arts_cnx_x10657_.pdf": "es",   # 'Impresión, sol naciente', es 175 / en 66
    "Programmazione_di_Artefatti_Interattivi_cmptr_cnx_x10417_.pdf": "it",   # it 1615 / es 509 / en 446
    "Python_programming_es_cmptr_cnx_x10564_.pdf": "pt",   # 'É preciso cavar uma ou mais crateras', pt 165 / en 90
    "greek_language_stuff_lang_cnx_x11138_.pdf": "el",   # RT2 #174: Greek-language Connexions module (TOC "Βασικά Πρότυπα Διάθεσης Ηλεκτρονικών Βιβλίων"), not an English course on Greek
    "_me_gtz_Basics_for_Metalworking_photos_en_139660_.pdf": "de",
    # #174 (G3 2026-10-10, read by hand): Danish texts; "_en_" in the file name is the CD3WD catalogue token, not the body
    "_st_405_Solar_cooker_Systime_jf_en_148260_.pdf": "da",
    "_wi_Danish_version_ITDG_pmg_konstruktions_manual_jf_pa_en_155290_.pdf": "da"}   # "Bildreihen für die Grundstufe Metall", Holland & Josenhans Verlag; picture sheets, OCR junk voted en
LANG_FIX.update({  # RT3 H3 (#184, 2026-10-12): read by hand, see the private test record;
    # a full --verify reverted these to the rule values (and popped `s` on the two INPHO rice files)
    "_ag_postharvest_1025_inpho_en_lp_114710_.pdf": "fr",
    "_ag_postharvest_1025_inpho_sp_en_114720_.pdf": "fr",
    "_co_ms_405_Mud_straw_plaster_Alice_Reite_Norway_1998_jf_en_125490_.pdf": "nb",
    "_ms_405_Wood_chemistry_jf_en_144950_.pdf": "sv",
    "_tr_bicycle_ambulance_manual_nepali_pa_en_148930_.pdf": "ne",
    "_tr_bicycle_trailor_manual_nepali_pa_en_148940_.pdf": "ne",
})
LANG_FIX.update({  # RT5 K5 follow-up 3 (#206): CNX courses whose English licence boilerplate outvotes a short body
    "Calculo_I_es_maths_cnx_x11176_.pdf": "es",
    "Geogebra_y_Descartes_en_Moodle_es_lang_cnx_x11149_.pdf": "es",
    "management_of_technological_innovation_es_mgt_cnx_x10675_.pdf": "pt",   # "Gestão da Inovação Tecnológica"
})
LANG_FIX.update({  # RT4 J3 (#195, 2026-10-13): read by hand, see the private test record;
    # the CNX Spanish course votes en on its English licence boilerplate
    "GestiON_desarrollo_del_conocimiento_es_mgt_cnx_x10648_.pdf": "es",
})

_PT_ORTH = re.compile(r"ção|ções|ões\b|\bnão\b|\bvocê|\bpelo\b|\bpela\b")   # Portuguese-only spellings
_ES_ORTH = re.compile(r"ción|ciones|ñ|\bel\b|\blos\b|\busted\b")
def detect_lang(text, name=""):
    """(lang, strong). strong = script share, a vote of >= 20 stopwords with >= 70% share, or (#131) a weak vote that
    the filename's language token or Portuguese/Spanish spelling confirms; weak results say "en"."""
    if name in LANG_FIX:
        return LANG_FIX[name], True
    s = script_lang(text, name)
    if s:
        return s, True
    if len(_VNI.findall(text[:200000])) >= max(10, len(text[:200000].split()) / 200):   # r21 titles list: 12 FETP "_vietnamese_en_" files in the VNI font encoding
        return "vi", True
    c = {}
    l, share, tot = vote(text, c)
    if l and (tot >= 20 and share >= 0.7 or tot >= 200 and share >= 0.6 or tot >= 8 and share >= 0.95):
        return l, True   # VITA "_po_" manuals: pt 0.64-0.69 over 800-2,000 words; 145-word German sheets: de 1.00 of 9
    if l in ("pt", "es") and tot >= 20 and c["pt"] + c["es"] >= 0.8 * tot:   # a pt-vs-es call, not an en/es bundle (VITA _em_441)   # CTA mycotoxin leaflet: pt 0.65 of 175, filename says _es_, 229 "ção/ões" vs 0
        pt, es = len(_PT_ORTH.findall(text[:200000])), len(_ES_ORTH.findall(text[:200000]))
        if max(pt, es) >= 20 and max(pt, es) >= 5 * min(pt, es):
            return ("pt" if pt > es else "es"), True
    n = name_lang(name)
    if n and n != "en" and l == n and tot >= 8:   # "_pa_en_" Bengali OCR junk voted en 0.62: "_en_" confirms nothing   # VITA "_po_lp_15_" (pt 0.60 of 127), VNI-encoded "vietnamese" FETP slides (vi 1.0 of 8)
        return n, True
    return (l if l and tot >= 8 and share >= 0.6 else "en"), False

GOOGLE_PAGE = re.compile(r"google", re.I), re.compile(r"public domain|digitiz|domaine public|numéris|dominio p|digitaliz", re.I)
def skip_google(text):
    """drop Google Books front-matter pages (red team 10-05: 93 summaries described the scan notice, not the book)"""
    pages = text.split("\f")
    while pages and GOOGLE_PAGE[0].search(pages[0]) and GOOGLE_PAGE[1].search(pages[0]):
        pages.pop(0)
    return "\f".join(pages)

# #127: publisher-ad pages ("JUST PUBLISHED, IN ONE VOLUME, 8VO." in front of the 1836 steam engine book: its summary
# listed the advertised maths book's Statics and Hydrostatics). Blanked, not removed, so page numbers stay put.
AD = re.compile(r"just published|new books|(?:also|lately|recently|books) published by|lately published|recently published|"
                r"catalogue of (?:books|works|publications)|uniform with this|opinions of the press|press notices|"
                r"price[ ,:.]+(?:\$|£|\d)|\d+ ?c(?:en)?ts\b|\b(?:8|12|16)mo\b|8vo\b|post ?free|sent by mail", re.I)
def skip_ads(text):
    pages = text.split("\f")
    for i in list(range(min(15, len(pages)))) + list(range(max(15, len(pages) - 15), len(pages))):
        if len(AD.findall(pages[i])) >= 2:
            pages[i] = ""
    return "\f".join(pages)

def google_only(text):
    """r21: a scan whose whole text layer is Google's notice (preserving_and_pickling 1917, buttermilk_cheese 1920):
    nothing is left after skip_google, so only the page images (VL) can describe it"""
    return len(text.strip()) > 200 and len(skip_google(text).strip()) < 200

def clean_text(text):
    """the one text cleaner for answers, one-liners, years and --verify: Google scan notice and publisher ads out"""
    return skip_ads(skip_google(text))

# #127: a file that is a reference list (appendix-a "References", the jumbo-rotor "consult the following ... books"
# page): its summary named the cited works' topics and its year was the first citation's.
_BOILER = re.compile(r"^\s*(?:\d{1,2}/\d{1,2}/\d{4}|page \d+ of \d+|pg_\d+|home\W*|.*ar\.cn\.de\.en\.es.*|file:///\S*)\s*$", re.I | re.M)
REFHEAD = re.compile(r"\b(?:references|bibliograph\w*|further reading|reading list|recommended (?:books|reading)|"
                     r"following .{0,60}books|bibliograf[ií]a|r[ée]f[ée]rences|literatur)\b", re.I)
def is_reflist(text):
    """the file opens with a references/reading-list heading and carries >= 2.5 years per 100 words"""
    words = len(text.split())
    head = " | ".join([l for l in _BOILER.sub("", text[:1500]).split("\n") if l.strip()][:3])   # the heading, not a TOC entry
    return bool(words and REFHEAD.search(head) and len(re.findall(YR, text)) * 100 / words >= 2.5)

# #128: compilations. cd3wd HTML-to-PDF files restart the language bar ("home.cd3wd.ar.cn.de.en...") at every paper;
# the 104 VITA "_at_vita_vth_{es,po,fr}_lp_NN_" files hold 1-14 papers ("PAPEL TÉCNICO #24", "PERFIL #6") and were
# summarised from the first one. Returns the papers' first title lines.
_NAV = re.compile(r"(?:home\.cd3wd\.)?ar\.cn\.de\.en\.es\.fr\.id\.it\.ph\.po\.ru\.sw[^\n]*\n((?:[^\n]*\n){1,4})")
_PAPER = re.compile(r"^(?:EL |LA |LE |UN )?(?:(?:PAPEL|PAPIER|TECHNICAL PAPER|DOCUMENT)\b[^\n]{0,20}T[ÉE]CHNI?\w*|(?:LA )?IND[ÚU]STRI\w* (?:DE )?PERFIL|PERFIL|INDUSTRY PROFILE|PROFIL)\s*#\s*\d+[^\n]*(?:\n[^\n]+){0,2}", re.M)
VITA_COMP = re.compile(r"_at_vita_vth_(?:es|po|fr)_lp_\d+_")
def papers(text, rel=""):
    """the language bar also restarts on every HTML page of one ordinary cd3wd doc (the CTA mycotoxin leaflet), so it
    counts as a paper header only in the VITA compilations; "PAPEL TÉCNICO #n" / "PERFIL #n" headers count anywhere"""
    out = paper_titles(text, rel)
    return out[:15] if len(out) >= 2 else []

def paper_titles(text, rel=""):
    """every distinct paper title line (one entry for a single paper; papers() wants 2+)"""
    seen, out = [], []
    for m in (list(_NAV.finditer(text)) if VITA_COMP.search(rel) else []) + list(_PAPER.finditer(text)):
        t = re.sub(r"\s+", " ", re.sub(r"VITA (?:EL )?(?:BOLETÍN TÉCNICO|BULLETIN TECHNIQUE|BOLETIM TÉCNICO)|Prepared|Por\b.*|Page \d+ of \d+", " ",
                                       m.group(1) if m.re is _NAV else m.group(0))).strip(" -:")[:90]
        if len(t) >= 8 and not any(same_paper(t, x) for x in seen):
            seen.append(t); out.append(t)
    return out

def _paper_no(t):
    """("perfil", "6") for "INDÚSTRIA DE PERFIL #6 ...", ("papel", "24") for "PAPEL TÉCNICO #24 ..."; None without a number"""
    m = re.search(r"#\s*(\d+)", t)
    return m and ("perfil" if re.search(r"perfil|profil", t, re.I) else "papel", m.group(1))

def same_paper(a, b):
    """#137 (r21 judge H): one paper's running header in several spellings ("INDÚSTRIA DE PERFIL #6 CALÇAS JEANS AZUIS",
    "INDÚSTRIA PERFIL #6") is one paper. Same kind and number when both carry one; else near-identical normalised text."""
    na, nb = _paper_no(a), _paper_no(b)
    if na and nb:
        return na == nb
    ka, kb = (re.sub(r"[\W\d_]+", "", x.lower())[:40] for x in (a, b))
    short = min(ka, kb, key=len)
    return ka == kb or len(short) >= 12 and (ka.startswith(kb) or kb.startswith(ka)) or \
        difflib.SequenceMatcher(None, ka, kb).ratio() >= 0.85

def prompt_note(text, rel=""):
    """extra prompt lines for the special file kinds; shared by gen_doc_meta (title, one-liner) and work() (answers)"""
    if is_reflist(text):
        return ("\nThis file is a REFERENCE LIST (a bibliography or reading list), not a manual. Say that it is a list of "
                "references or further reading and name its subject; do not describe the cited works as if this file taught them.")
    ps = papers(text, rel)
    if ps:
        return ("\nThis file is a COMPILATION of %d separate papers, in this order: %s. Describe the collection as a whole: "
                "name the papers' topics, not only the first one's." % (len(ps), "; ".join("%d) %s" % (i, p) for i, p in enumerate(ps, 1))))
    one = paper_titles(text, rel)
    if one:   # #137: one paper whose running header looked like several (VITA po_lp_15 came back as "Industrial Planning")
        return ("\nThis file is ONE paper, titled \"%s\": name that paper and its subject in the title and the summary." % one[0]
                + (" Its general text about planning a factory is the series' standard framework, not the subject."
                   if re.search(r"perfil|profil", one[0], re.I) else ""))
    if len(text.split()) < 300:
        return "\nThe excerpt is the WHOLE document (under 300 words): describe only what it shows."
    return ""

# #125: invented survival audiences on old books ("Survivalists in coastal regions" for a 1920 canoe ethnography,
# "survivors ... in 1918" for an encyclopedia). #74 kept them whenever "surviv" appeared anywhere in the text; old
# books say "survived" and "surviving son". On the old-book shelves the words are allowed only when the path or
# title is about survival.
OLD_SHELVES = ("docs/survivor_library", "docs/HISTORICAL", "docs/cd3wd", "docs/school_textbooks", "docs/homesteading_extension")
AUD_BAD = re.compile(r"\bsurvivor|\bsurvivalist|prepper|for survival|in emergenc|long-term (?:food security|sustenance)|self-sufficien|"
                     r"supervivien|sobrevivien|en (?:caso de )?emergencias?\b|autosufici|survivants?\b|autosuffis", re.I)
# #158 (red team 10-09 b1mech, 93 rows): survivalist framing on farm/craft/cookbook entries ("useful in survival situations",
# "long-term survival"). Same regex and shelf list as the t9 checker (b1mech_checks.SURV / SURV_OK_SHELVES): outside the
# survival shelves, and unless the title itself is about survival, these words never describe the readers.
SURV_WORDS = re.compile(r"\b(survivalists?|preppers?|prepping|SHTF|TEOTWAWKI|bug[- ]?out|grid[- ]down|post[- ]collapse|"
                        r"(societal|civili[sz]ation(al)?|society) collapse|collapse of (society|civili[sz]ation)|apocalyp\w*|"
                        r"doomsday|end of the world|survival (situations?|scenarios?|settings?|conditions?)|"
                        r"off[- ]grid survival|wilderness survival|long[- ]term survival|self[- ]reliance after|"
                        r"after (a|the) collapse|when (modern )?(infrastructure|supply chains?) (fail|collapse)\w*)\b", re.I)
SURV_OK_SHELVES = ("docs/emergency_mgmt", "docs/military_manuals", "docs/HISTORICAL", "docs/security", "docs/shelter",
                   "docs/water", "docs/navigation", "docs/nuclear", "docs/fire_safety", "docs/foraging_coastal", "mirrors/ready_gov",
                   "docs/survivor_library/SurvivalLibrary/library/Survival-Individual",
                   "docs/survivor_library/SurvivalLibrary/library/Boy Scout Manuals",
                   "docs/survivor_library/SurvivalLibrary/library/Trapping and Hunting",
                   "docs/survivor_library/SurvivalLibrary/library/NBC")
# RT5 #205 (b5 R1, b1mech s3): the named-reader words (survivalists, preppers, "Für Überlebende", "after collapse") are
# checked on EVERY shelf; only a path or title about survival is exempt (the shelf prefix "SurvivalLibrary" is not)
SURV_AUD = re.compile(r"\b(survivalists?|preppers?|prepping|SHTF|TEOTWAWKI|bug[- ]?out|post[- ]collapse|"
                      r"(?:societal|civili[sz]ation(?:al)?|society) collapse|collapse of (?:society|civili[sz]ation)|apocalyp\w*|"
                      r"doomsday|end of the world|(?:after|for) (?:a |the )?(?:coming )?collapse|Überlebende\w*|Survivalisten|"
                      r"supervivencialistas?|survivalistes?|sobrevivencialistas?)\b", re.I)
# RT6 L5 (#205 regression, b5): "Survivors in remote areas should open it ..." is the same invented reader as "survivalists";
# AUD_OK let it through on woodcraft/wilderness/disaster titles. A survivors-as-reader sentence fails off the survival paths.
SURV_READER = re.compile(r"\bsurvivors?\b(?:\W+\w+){0,10}?\W+(?:should|would|could|can|must|need to|will)\s+(?:open|use|read|consult|find)", re.I)
# RT6 L5 (c9, b1mech): an invented reading time ("should be opened ... in 2025 or later", "open it in 1914", "users in 2025")
# is never a fact (#138 "open it in 1915" was fixed one at a time; 141 entries carried it)
READ_YEAR = re.compile(r"\b(?:should|would|could|can|will)\s+(?:be\s+)?(?:open(?:ed)?|use[ds]?|read)\b[^.]{0,90}?\b(?:in|by|after|before|from)\s+(?:1[6-9]\d\d|20\d\d)\b(?!s)|\b(?:in|by|after|before)\s+(?:19[5-9]\d|20[0-4]\d)\s+or\s+later\b|\b(?:users|readers|enthusiasts|researchers|buyers)\s+in\s+(?:19|20)\d\d\b|\b(?:starting|beginning)\s+\w+\s+in\s+20\d\d\s+or\s+later", re.I)
# RT10 M4 (#205 regressed, b5 W10; b1mech s17, 18 rows): the shelf exemption let "long-term survival trips" (camping and
# woodcraft vol 2), "long-term survival" (Foxfire One) and "survival situations" (a 1920 Boy Scout novel) through, and the
# other s17 framings ("during food shortages", "without modern tools", "survival insights", "during textile shortages") were
# in no pattern. s17's rule, on every shelf: a framing phrase in s/a stands only when the document text holds the phrase
# (its content words in order, a few words apart). The shelf and path exemptions stay only for the named-reader tests.
# (survival phrases: the phrase itself; the other framings: the word or a synonym the round-9 s17 hand check accepted)
_BIO = "".join(f"(?<!{w} )" for w in ("crop", "crops", "calf", "calves", "plant", "plants", "fish", "fry", "tree", "trees", "lamb",
                                         "seedling", "seedlings", "chick", "chicks", "piglet", "cell", "egg", "bee", "colony", "larval"))
_FRAMES = [
    (SURV_WORDS.pattern + r"|\b(?:(?:long[- ]term|outdoor|wilderness|agricultural|practical|basic|emergency)\s+survival|" + _BIO + r"survival)"
     r"(?:\s+(?:situations?|scenarios?|settings?|conditions?|insights?|trips?|skills?|tasks?|techniques|practices|purposes|needs|use))?\b"
     r"|\bwhen\s+(?:supplies|stores|modern\s+\w+|the\s+grid|power)\s+(?:runs?\s+out|are\s+unavailable|fails?|goes\s+down)\b", None),
    (r"\b(?:during|in|amid)\s+(?:times\s+of\s+)?(?:(?!water\b|firewood\b)\w+\s+){0,2}?(?:shortages?|scarcity)\b"
     r"|\b(?:food|resource|textile|fuel|energy|material|supply|petroleum)\s+(?:shortages?|scarcity)\b|\btimes\s+of\s+(?:\w+\s+)?scarcity\b",
     r"\b(?:shortage|scarc|lack of|deficien|famine|rationing|ration card|food conserv|conserv\w* (?:of )?food|wheat[- ]?saving|save wheat|war[- ]?time|war bread|victory bread)"),
    (r"\boff[- ]grid\s+(?:living|life|lifestyle)\b", r"\boff[- ]?grid|no (?:mains|grid)|without (?:mains|grid|electricity)|not connected|"
     r"stand[- ]?alone|autonomous|isolated|remote|rural electrif|no electricity|\bgrid\b|\butilit|power (?:line|company)|independen"),
    (r"\bwithout\s+modern\s+(?:\w+\s+){0,2}?(?:tools|resources|equipment|technology|conveniences|medicine|care|help|methods)\b",
     r"\b(?:without modern|before modern|no modern|primitive (?:conditions|tools|methods)|hand tools|simple tools)"),
    (r"\b(?:during|in)\s+(?:an?\s+|times\s+of\s+)?(?:emergenc(?:y|ies)|crisis|crises|hard\s+times)\b",
     r"\b(?:emergenc|disaster|crisis|crises|relief|refugee|hard times|first aid|accident|rescue)"),
    (r"\bself[- ]relian\w*", r"\b(?:self[- ]?relian|self[- ]?suffic|independen)"),
    (r"\bpreparedness\b", r"\b(?:prepar|mitigat|readiness|civil defen)"),
]
FRAME = re.compile("|".join(f"(?:{a})" for a, _ in _FRAMES), re.I)
_FRAME_RX = [(re.compile(a, re.I), b and re.compile(b, re.I)) for a, b in _FRAMES]
_FRAME_STOP = {"during", "in", "a", "an", "the", "of", "times", "when", "are", "is", "without", "and", "or", "for", "use",
               "skills", "skill", "techniques", "practices", "tasks", "purposes", "needs"}   # "survival skills": the survival word is the claim
def _frame_core(phrase):
    r""""long-term survival trips" -> long\w*\W+(?:\w+\W+){0,2}?term\w*\W+... (6-letter stems, plural endings off)"""
    for rx, syn in _FRAME_RX:
        if syn and rx.fullmatch(phrase):
            return syn
    stems = []
    for w in re.findall(r"[^\W\d_]+", phrase.lower()):
        if w in _FRAME_STOP:
            continue
        w = w[:-3] + "y" if w.endswith("ies") and len(w) > 5 else w[:-1] if w.endswith("s") and len(w) > 3 else w
        stems.append(re.escape(w[:6]))
    return re.compile(r"\b" + r"\w*\W+(?:\w+\W+){0,2}?".join(stems) + r"\w*", re.I) if stems else None
def ftext(text):
    """the text frame_bad reads: None (the shelf rule) when the file has no usable text layer (under 200 words)"""
    return text if len((text or "").split()) >= 200 else None
def frame_bad(v, text):
    """the first framing phrase of v that the document text does not hold, or "" (s17's rule)"""
    for m in FRAME.finditer(v or ""):
        core = _frame_core(m.group(0))
        if core and not core.search(text or ""):
            return m.group(0)
    return ""
def surv_path(rel, title):
    # RT7 M4 (#205 regression, b5 R7): the file name or the title must be about survival; a folder name is not ("Survival-
    # Individual" let "survivalists should open it" through on a 1914 boys' woodcraft book and the Marine Corps Mao reprint)
    return bool(re.search(r"surviv", os.path.basename(rel) + " " + (title or ""), re.I))
def surv_bad(rel, title, v, text=None):
    # RT10 M4: with the document text, the framing test is frame_bad on every shelf; without it (no text at hand), the old
    # shelf rule
    frame = bool(frame_bad(v, text)) if text is not None else \
        not rel.startswith(SURV_OK_SHELVES) and "surviv" not in (title or "").lower() and bool(SURV_WORDS.search(v or ""))
    return (frame or not surv_path(rel, title) and bool(SURV_AUD.search(v or "") or SURV_READER.search(v or ""))
            or bool(READ_YEAR.search(v or "")))
AUD_OK = re.compile(r"surviv|scout|trap|wilderness|camp|woodcraft|emergenc|first.?aid|disaster|refugee|relief|civil.?defen|"
                    r"homestead|self.?relian|self.?suffic|"   # r21: "Homesteader Handbook", "Self-reliant couple ... homestead"
                    r"fallout|famine|_em_|urgenc|desastre|catastroph|primeros.?auxilios|secours", re.I)
# #138 (r21 judge A): the reader sentence restates the plot or the book's situation ("Children and families stranded
# by snow should open it during Christmas" for a 1921 Christmas play, "Farmers and transporters should open it before
# the war", "Blind people ... long-term sustenance" for a cookbook sold for the benefit of the blind). Checked on the
# LAST sentence of a two-sentence `a` only: a one-line `s` may tell the plot.
AUD_PLOT = re.compile(r"\bstranded\b|\b(?:before|during|after) the (?:war|depression|flood|storm|siege)\b|\bsustenance\b|"
                      r"\bblind (?:people|readers)\b|\bsnowbound\b|\bshipwreck", re.I)
def reader_plot(a):
    sents = re.split(r"(?<=[.!?])\s+", (a or "").strip())
    return len(sents) >= 2 and bool(AUD_PLOT.search(sents[-1]))

def audience_bad(rel, title, a, text=None):
    """True when `a` names a survival/emergency audience the old book does not have (#125), or its reader sentence
    restates the plot (#138), or carries survivalist wording off the survival shelves (#158); one rule for verify and ask"""
    return rel.startswith(OLD_SHELVES) and (bool(AUD_BAD.search(a)) and not aud_ok(rel, title) or reader_plot(a)) \
        or surv_bad(rel, title, a, text)

def aud_cut(s):
    """r21: drop the comma clauses that carry the invented audience ("..., useful for survival or self-sufficiency.")"""
    keep = [x for x in re.split(r",\s+|;\s+", s) if not AUD_BAD.search(x) and not SURV_WORDS.search(x)]
    return (", ".join(keep).rstrip(" ,;.") + ".") if keep else ""

def aud_ok(rel, title):
    """folder, filename or title is about survival/emergencies (the shelf prefix "survivor_library/SurvivalLibrary" is not)"""
    return bool(AUD_OK.search(re.sub(r"^docs/survivor_library/SurvivalLibrary/library/|^docs/[^/]+/", "", rel) + " " + title))

DOSE = re.compile(r"(?!(?<=iphone\s)[2-5]\s?g\b)(?!(?<=phone\s)[2-5]\s?g\b)(?![2-5]\s?g\b(?=\s*(?:lte|networks?|phones?|iphones?|modems?|signal|wi-?fi|cellular|data|service|coverage|speeds?|internet|front|back|screen|battery|case|replacement|red|se[nñ]al|celular|m[oó]vil)\b))(?<!\bFM\s)(?<!\bTM\s)(?<!\bTC\s)(?<!\bATP\s)(?<!\bSTP\s)(?<!\d-)(?<!\d\.)(?<!gallon\s)(?<!gallons\s)(?<!quart\s)(?<!quarts\s)(?<!liter\s)(?<!liters\s)(?<!litre\s)(?<!litres\s)(?<!litro\s)(?<!litros\s)(?<!gal[oó]n\s)(?<!galones\s)(?<!barrel\s)(?<!barrels\s)(?<!barril\s)(?<!barriles\s)(?<!drum\s)(?<!drums\s)(?<!tank\s)(?<!tanks\s)(?<!tambo\s)(?<!tambos\s)(?<!tanque\s)(?<!tanques\s)(?<!drops\s\()(?<!gotas\s\()(?<!\d\/)(?<!\d\/)(?<!\d\/)(?!(?<=\bdrops\s)\d+\s*drops\b)(?!(?<=\bgotas\s)\d+\s*gotas\b)(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*(?:(?:parte\s+)?de\s+(?:una?\s+)?)?(?:mg|mcg|µg|ug|g|ml|cc|mililitros?|millilit(?:er|re)s?|m\s?iu|m\s?ui|iu|ui|(?:million|mill[oó]n(?:es)?)\s+(?:de\s+)?(?:(?:international\s+)?(?:units?|unidades)|ui|iu)|units?|unidades|grams?|gramos?|milligrams?|miligramos?|micrograms?|microgramos?|tabs?|tablets?|tabletas?|pills?|pastillas?|comprimidos?|caps?|capsules?|c[aá]psulas?|(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|capfuls?|dropperfuls?|tsp|tbsp|c[àá]c|c[àá]s|c\.[àá]\.[cs](?=\.)|cucharaditas?|cucharadas?|drops?|gotas?|ampoules?|ampules?|ampuls?|ampollas?|ampolletas?|vials?|frascos?[-\s]ampollas?)\b(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))(?:\s*(?:\/|per|por(?:\s+cada)?)\s*(?:kg|kilos?|kilogramos?|kilograms?|d[ií]a|day|dose|dosis|m2)\b(?:\s+(?:of\s+body\s+weight|de\s+peso(?:\s+corporal)?))?)*(?:\s*x\s*\d+(?:\s*(?:[-–]|or|o|to|a)\s*\d+)?\b)?(?:,?\s+(?:daily|a\s+day|per\s+day|each\s+day|al\s+d[ií]a|por\s+d[ií]a|cada\s+d[ií]a|diari[oa]s?))?|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|o|ó|u|a|y|and)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+(?:of\s+)?an?)?|cuarto\s+de(?:\s+una?)?|an?(?=\s+(?:(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|capfuls?|dropperfuls?|ampoules?|ampules?|vials?)\b))\s+(?:tabletas?|pastillas?|comprimidos?|c[aá]psulas?|tablets?|pills?|capsules?|ampoules?|ampules?|vials?|(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|capfuls?|dropperfuls?|cucharaditas?|cucharadas?|goteros?|ampolletas?|frascos?[-\s]ampollas?|drops?|gotas?|ampollas?(?=\s+(?:de\s+(?:\w*ina\b|suero|antiveneno|antiof[ií]dico|antitet[aá]nic)|i\.?[mv]\b|intramuscular|intraven)))\b(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))(?:\s*(?:\/|per|por(?:\s+cada)?)\s*(?:kg|kilos?|kilogramos?|kilograms?|d[ií]a|day|dose|dosis|m2)\b(?:\s+(?:of\s+body\s+weight|de\s+peso(?:\s+corporal)?))?)*(?:\s*x\s*\d+(?:\s*(?:[-–]|or|o|to|a)\s*\d+)?\b)?(?:,?\s+(?:daily|a\s+day|per\s+day|each\s+day|al\s+d[ií]a|por\s+d[ií]a|cada\s+d[ií]a|diari[oa]s?))?|(?:(?=every\s|cada\s)(?<!compost\s)(?<!pile\s)(?<!dough\s)(?<!wake\s)(?<!wake\sthem\s)(?<!wake\shim\s)(?<!wake\sher\s)(?<!wake\sit\s)(?<!wake\sup\s)(?<!wake\sthem\sup\s)(?<!wake\shim\sup\s)(?<!wake\sher\sup\s)(?<!wake\son\sthem\s)(?<!wake\son\shim\s)(?<!wake\son\sher\s)(?<!wake\sthe\sperson\s)(?<!wake\sthe\schild\s)(?<!wake\sthe\sbaby\s)(?<!wake\sthe\spatient\s)(?<!wake\son\sthe\sperson\s)(?<!wake\son\sthe\schild\s)(?<!wake\son\sthe\spatient\s)(?<!waken\s)(?<!waken\sthem\s)(?<!waken\shim\s)(?<!waken\sher\s)(?<!waken\sit\s)(?<!waken\sup\s)(?<!waken\sthem\sup\s)(?<!waken\shim\sup\s)(?<!waken\sher\sup\s)(?<!waken\son\sthem\s)(?<!waken\son\shim\s)(?<!waken\son\sher\s)(?<!waken\sthe\sperson\s)(?<!waken\sthe\schild\s)(?<!waken\sthe\sbaby\s)(?<!waken\sthe\spatient\s)(?<!waken\son\sthe\sperson\s)(?<!waken\son\sthe\schild\s)(?<!waken\son\sthe\spatient\s)(?<!awaken\s)(?<!awaken\sthem\s)(?<!awaken\shim\s)(?<!awaken\sher\s)(?<!awaken\sit\s)(?<!awaken\sup\s)(?<!awaken\sthem\sup\s)(?<!awaken\shim\sup\s)(?<!awaken\sher\sup\s)(?<!awaken\son\sthem\s)(?<!awaken\son\shim\s)(?<!awaken\son\sher\s)(?<!awaken\sthe\sperson\s)(?<!awaken\sthe\schild\s)(?<!awaken\sthe\sbaby\s)(?<!awaken\sthe\spatient\s)(?<!awaken\son\sthe\sperson\s)(?<!awaken\son\sthe\schild\s)(?<!awaken\son\sthe\spatient\s)(?<!waking\s)(?<!waking\sthem\s)(?<!waking\shim\s)(?<!waking\sher\s)(?<!waking\sit\s)(?<!waking\sup\s)(?<!waking\sthem\sup\s)(?<!waking\shim\sup\s)(?<!waking\sher\sup\s)(?<!waking\son\sthem\s)(?<!waking\son\shim\s)(?<!waking\son\sher\s)(?<!waking\sthe\sperson\s)(?<!waking\sthe\schild\s)(?<!waking\sthe\sbaby\s)(?<!waking\sthe\spatient\s)(?<!waking\son\sthe\sperson\s)(?<!waking\son\sthe\schild\s)(?<!waking\son\sthe\spatient\s)(?<!check\s)(?<!check\sthem\s)(?<!check\shim\s)(?<!check\sher\s)(?<!check\sit\s)(?<!check\sup\s)(?<!check\sthem\sup\s)(?<!check\shim\sup\s)(?<!check\sher\sup\s)(?<!check\son\sthem\s)(?<!check\son\shim\s)(?<!check\son\sher\s)(?<!check\sthe\sperson\s)(?<!check\sthe\schild\s)(?<!check\sthe\sbaby\s)(?<!check\sthe\spatient\s)(?<!check\son\sthe\sperson\s)(?<!check\son\sthe\schild\s)(?<!check\son\sthe\spatient\s)(?<!checking\s)(?<!checking\sthem\s)(?<!checking\shim\s)(?<!checking\sher\s)(?<!checking\sit\s)(?<!checking\sup\s)(?<!checking\sthem\sup\s)(?<!checking\shim\sup\s)(?<!checking\sher\sup\s)(?<!checking\son\sthem\s)(?<!checking\son\shim\s)(?<!checking\son\sher\s)(?<!checking\sthe\sperson\s)(?<!checking\sthe\schild\s)(?<!checking\sthe\sbaby\s)(?<!checking\sthe\spatient\s)(?<!checking\son\sthe\sperson\s)(?<!checking\son\sthe\schild\s)(?<!checking\son\sthe\spatient\s)(?<!recheck\s)(?<!recheck\sthem\s)(?<!recheck\shim\s)(?<!recheck\sher\s)(?<!recheck\sit\s)(?<!recheck\sup\s)(?<!recheck\sthem\sup\s)(?<!recheck\shim\sup\s)(?<!recheck\sher\sup\s)(?<!recheck\son\sthem\s)(?<!recheck\son\shim\s)(?<!recheck\son\sher\s)(?<!recheck\sthe\sperson\s)(?<!recheck\sthe\schild\s)(?<!recheck\sthe\sbaby\s)(?<!recheck\sthe\spatient\s)(?<!recheck\son\sthe\sperson\s)(?<!recheck\son\sthe\schild\s)(?<!recheck\son\sthe\spatient\s)(?<!despi[eé]rtela\s)(?<!despi[eé]rtela\sa\sla\spersona\s)(?<!despi[eé]rtela\sal\sni[nñ]o\s)(?<!despi[eé]rtela\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtela\sal\senfermo\s)(?<!despi[eé]rtela\sa\sla\senferma\s)(?<!despi[eé]rtela\sal\sbeb[eé]\s)(?<!despi[eé]rtelo\s)(?<!despi[eé]rtelo\sa\sla\spersona\s)(?<!despi[eé]rtelo\sal\sni[nñ]o\s)(?<!despi[eé]rtelo\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtelo\sal\senfermo\s)(?<!despi[eé]rtelo\sa\sla\senferma\s)(?<!despi[eé]rtelo\sal\sbeb[eé]\s)(?<!despi[eé]rtele\s)(?<!despi[eé]rtele\sa\sla\spersona\s)(?<!despi[eé]rtele\sal\sni[nñ]o\s)(?<!despi[eé]rtele\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtele\sal\senfermo\s)(?<!despi[eé]rtele\sa\sla\senferma\s)(?<!despi[eé]rtele\sal\sbeb[eé]\s)(?<!despi[eé]rtenla\s)(?<!despi[eé]rtenla\sa\sla\spersona\s)(?<!despi[eé]rtenla\sal\sni[nñ]o\s)(?<!despi[eé]rtenla\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtenla\sal\senfermo\s)(?<!despi[eé]rtenla\sa\sla\senferma\s)(?<!despi[eé]rtenla\sal\sbeb[eé]\s)(?<!despi[eé]rtenlo\s)(?<!despi[eé]rtenlo\sa\sla\spersona\s)(?<!despi[eé]rtenlo\sal\sni[nñ]o\s)(?<!despi[eé]rtenlo\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtenlo\sal\senfermo\s)(?<!despi[eé]rtenlo\sa\sla\senferma\s)(?<!despi[eé]rtenlo\sal\sbeb[eé]\s)(?<!despi[eé]rtenle\s)(?<!despi[eé]rtenle\sa\sla\spersona\s)(?<!despi[eé]rtenle\sal\sni[nñ]o\s)(?<!despi[eé]rtenle\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtenle\sal\senfermo\s)(?<!despi[eé]rtenle\sa\sla\senferma\s)(?<!despi[eé]rtenle\sal\sbeb[eé]\s)(?<!despi[eé]rtala\s)(?<!despi[eé]rtala\sa\sla\spersona\s)(?<!despi[eé]rtala\sal\sni[nñ]o\s)(?<!despi[eé]rtala\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtala\sal\senfermo\s)(?<!despi[eé]rtala\sa\sla\senferma\s)(?<!despi[eé]rtala\sal\sbeb[eé]\s)(?<!despi[eé]rtalo\s)(?<!despi[eé]rtalo\sa\sla\spersona\s)(?<!despi[eé]rtalo\sal\sni[nñ]o\s)(?<!despi[eé]rtalo\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtalo\sal\senfermo\s)(?<!despi[eé]rtalo\sa\sla\senferma\s)(?<!despi[eé]rtalo\sal\sbeb[eé]\s)(?<!despertarla\s)(?<!despertarla\sa\sla\spersona\s)(?<!despertarla\sal\sni[nñ]o\s)(?<!despertarla\sa\sla\sni[nñ]a\s)(?<!despertarla\sal\senfermo\s)(?<!despertarla\sa\sla\senferma\s)(?<!despertarla\sal\sbeb[eé]\s)(?<!despertarlo\s)(?<!despertarlo\sa\sla\spersona\s)(?<!despertarlo\sal\sni[nñ]o\s)(?<!despertarlo\sa\sla\sni[nñ]a\s)(?<!despertarlo\sal\senfermo\s)(?<!despertarlo\sa\sla\senferma\s)(?<!despertarlo\sal\sbeb[eé]\s)(?<!despertarle\s)(?<!despertarle\sa\sla\spersona\s)(?<!despertarle\sal\sni[nñ]o\s)(?<!despertarle\sa\sla\sni[nñ]a\s)(?<!despertarle\sal\senfermo\s)(?<!despertarle\sa\sla\senferma\s)(?<!despertarle\sal\sbeb[eé]\s)(?<!despierte\s)(?<!despierte\sa\sla\spersona\s)(?<!despierte\sal\sni[nñ]o\s)(?<!despierte\sa\sla\sni[nñ]a\s)(?<!despierte\sal\senfermo\s)(?<!despierte\sa\sla\senferma\s)(?<!despierte\sal\sbeb[eé]\s)(?<!despertar\s)(?<!despertar\sa\sla\spersona\s)(?<!despertar\sal\sni[nñ]o\s)(?<!despertar\sa\sla\sni[nñ]a\s)(?<!despertar\sal\senfermo\s)(?<!despertar\sa\sla\senferma\s)(?<!despertar\sal\sbeb[eé]\s)(?<!rev[ií]sela\s)(?<!rev[ií]sela\sa\sla\spersona\s)(?<!rev[ií]sela\sal\sni[nñ]o\s)(?<!rev[ií]sela\sa\sla\sni[nñ]a\s)(?<!rev[ií]sela\sal\senfermo\s)(?<!rev[ií]sela\sa\sla\senferma\s)(?<!rev[ií]sela\sal\sbeb[eé]\s)(?<!rev[ií]selo\s)(?<!rev[ií]selo\sa\sla\spersona\s)(?<!rev[ií]selo\sal\sni[nñ]o\s)(?<!rev[ií]selo\sa\sla\sni[nñ]a\s)(?<!rev[ií]selo\sal\senfermo\s)(?<!rev[ií]selo\sa\sla\senferma\s)(?<!rev[ií]selo\sal\sbeb[eé]\s)(?<!rev[ií]sele\s)(?<!rev[ií]sele\sa\sla\spersona\s)(?<!rev[ií]sele\sal\sni[nñ]o\s)(?<!rev[ií]sele\sa\sla\sni[nñ]a\s)(?<!rev[ií]sele\sal\senfermo\s)(?<!rev[ií]sele\sa\sla\senferma\s)(?<!rev[ií]sele\sal\sbeb[eé]\s)(?<!revise\s)(?<!revise\sa\sla\spersona\s)(?<!revise\sal\sni[nñ]o\s)(?<!revise\sa\sla\sni[nñ]a\s)(?<!revise\sal\senfermo\s)(?<!revise\sa\sla\senferma\s)(?<!revise\sal\sbeb[eé]\s)(?<!revisar\s)(?<!revisar\sa\sla\spersona\s)(?<!revisar\sal\sni[nñ]o\s)(?<!revisar\sa\sla\sni[nñ]a\s)(?<!revisar\sal\senfermo\s)(?<!revisar\sa\sla\senferma\s)(?<!revisar\sal\sbeb[eé]\s)(?<!revisarla\s)(?<!revisarla\sa\sla\spersona\s)(?<!revisarla\sal\sni[nñ]o\s)(?<!revisarla\sa\sla\sni[nñ]a\s)(?<!revisarla\sal\senfermo\s)(?<!revisarla\sa\sla\senferma\s)(?<!revisarla\sal\sbeb[eé]\s)(?<!revisarlo\s)(?<!revisarlo\sa\sla\spersona\s)(?<!revisarlo\sal\sni[nñ]o\s)(?<!revisarlo\sa\sla\sni[nñ]a\s)(?<!revisarlo\sal\senfermo\s)(?<!revisarlo\sa\sla\senferma\s)(?<!revisarlo\sal\sbeb[eé]\s)(?<!vig[ií]lela\s)(?<!vig[ií]lela\sa\sla\spersona\s)(?<!vig[ií]lela\sal\sni[nñ]o\s)(?<!vig[ií]lela\sa\sla\sni[nñ]a\s)(?<!vig[ií]lela\sal\senfermo\s)(?<!vig[ií]lela\sa\sla\senferma\s)(?<!vig[ií]lela\sal\sbeb[eé]\s)(?<!vig[ií]lelo\s)(?<!vig[ií]lelo\sa\sla\spersona\s)(?<!vig[ií]lelo\sal\sni[nñ]o\s)(?<!vig[ií]lelo\sa\sla\sni[nñ]a\s)(?<!vig[ií]lelo\sal\senfermo\s)(?<!vig[ií]lelo\sa\sla\senferma\s)(?<!vig[ií]lelo\sal\sbeb[eé]\s)(?<!vig[ií]lele\s)(?<!vig[ií]lele\sa\sla\spersona\s)(?<!vig[ií]lele\sal\sni[nñ]o\s)(?<!vig[ií]lele\sa\sla\sni[nñ]a\s)(?<!vig[ií]lele\sal\senfermo\s)(?<!vig[ií]lele\sa\sla\senferma\s)(?<!vig[ií]lele\sal\sbeb[eé]\s)(?<!vigile\s)(?<!vigile\sa\sla\spersona\s)(?<!vigile\sal\sni[nñ]o\s)(?<!vigile\sa\sla\sni[nñ]a\s)(?<!vigile\sal\senfermo\s)(?<!vigile\sa\sla\senferma\s)(?<!vigile\sal\sbeb[eé]\s)(?<!vigilar\s)(?<!vigilar\sa\sla\spersona\s)(?<!vigilar\sal\sni[nñ]o\s)(?<!vigilar\sa\sla\sni[nñ]a\s)(?<!vigilar\sal\senfermo\s)(?<!vigilar\sa\sla\senferma\s)(?<!vigilar\sal\sbeb[eé]\s)(?<!vigilarla\s)(?<!vigilarla\sa\sla\spersona\s)(?<!vigilarla\sal\sni[nñ]o\s)(?<!vigilarla\sa\sla\sni[nñ]a\s)(?<!vigilarla\sal\senfermo\s)(?<!vigilarla\sa\sla\senferma\s)(?<!vigilarla\sal\sbeb[eé]\s)(?<!vigilarlo\s)(?<!vigilarlo\sa\sla\spersona\s)(?<!vigilarlo\sal\sni[nñ]o\s)(?<!vigilarlo\sa\sla\sni[nñ]a\s)(?<!vigilarlo\sal\senfermo\s)(?<!vigilarlo\sa\sla\senferma\s)(?<!vigilarlo\sal\sbeb[eé]\s)(?:every|cada)\s+(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)|\b(?:two|three|four|five|six|seven|eight|nine|ten|twelve|twenty-four|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|veinticuatro)(?:\s+(?:to|or|and|o|a|y)\s+(?:two|three|four|five|six|seven|eight|nine|ten|twelve|twenty-four|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|veinticuatro))?)\s*(?:h|hrs?|hours?|horas?)\b(?!\s*,?\s*(?:turn|stir|mix|knead|rotate)\b)|(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)|(?:one|two|three|four|five|six|una|dos|tres|cuatro|cinco|seis))\s*(?:times?|x|veces|vez)\s*(?:(?:a|per|al|por|each|cada)\s*(?:day|d[ií]a)|daily|diari[oa]s?)|(?:once|twice|thrice)\s+(?:(?:a|per|each)\s+day|daily)|(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s+(?:doses|dosis)\b)(?:,?\s*(?:for|por|durante)\s+(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*(?:days?|d[ií]as|weeks?|semanas)\b)?|(?:en\s+)?una\s+sola\s+dosis|\b1\s+sola\s+vez|(?:again|repeat(?:ed)?|otra\s+vez|de\s+nuevo|repetir|repita)\s+(?:in|after|en|despu[eé]s\s+de)\s+(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*(?:h|hrs?|hours?|horas?)\b|\b(?:every\s+(?:[\w-]+\s+){0,2}?hours?|hourly|cada\s+(?:\w+\s+){0,2}?horas?|doses?|dosis|dosage|given|give|gives|giving|administer\w*|administr\w*|take|takes|taken|inject\w*|ivermectin|dele|dale|darle|dar|d[eé]selo|d[eé]sele|tome|tomar|toma|tomando|tinctures?|tintura|infusions?|infusi[oó]n|decoctions?|remed(?:y|ies)|remedios?|medicinal(?:ly)?|medicines?|medicinas?|mixtures?|prescrib\w*|recommend\w*|purgatives?|purgantes?|cathartics?|emetics?|vomitivos?|antispasmodic|anodyne|laxatives?|laxantes?|tonics?|t[oó]nicos?|physic|draughts?|drench\w*|bolus|pills?|liniments?|ointments?|salves?|embrocations?|poultices?|gargles?|lotions?|eye-?waters?|collyri\w*|pomadas?|ung[uü]entos?|linimentos?|cataplasmas?|quinine|quinina|opium|opio|laudanum|l[aá]udano|morphi\w*|morfina|calomel|camphor\w*|alcanfor|digitalis|foxglove|strychni\w*|estricnina|bromides?|bromuro|salicin|salicyl\w*|buchu|creosote|creosota|elaterium|ipecac\w*|paregoric|parag[oó]rico|castor\s+oil|ricino|epsom|glauber|iodides?|yoduro|aloes|rhubarb|ruibarbo|senna|jalap|turpentine|trementina|chloral|chloroform|cloroformo|ether|belladonn?a|aconite|ac[oó]nito|ergot\w*|arseni\w*|ars[eé]nico|mercury|mercurio|antitoxins?|antitoxina|serum|suero|antimony|tartar\s+emetic|pine\s+tar|penny\s*royal|carbolic|creolin|sulphur|azufre|magnesia|bismuth|santonin|cocaine|atropine|aspirin\w*|chlorodyne|squills?|antipyrin\w*|acetanilid\w*|phenacetin|cod[\s-]liver\s+oil|vermifuge|nux\s+vomica|nitre|lobelia|asaf\w*tida|valerian|hyoscyam\w*|cannabis|cantharides|croton\s+oil|podophyll\w*|sarsaparilla|guaiac\w*|colchicum|stramonium|hellebore|savin|tansy|wormwood|quassia|gentian|cinchona)\b[^;!?]{0,80}?(?:(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:fluid\s+|fl\.\s*)?(?:(?:grains?|minims?|drachms?|drams?|ounces?|gills?|scruples?|granos?|dracmas?|onzas?|escr[uú]pulos?)\b|(?:grs?|oz)(?:\.|\b)|oz\b|c\.\s?c\.)|\b(?:a\s+few\s+drops|a\s+drop\s+or\s+two|unas\s+(?:cuantas\s+|pocas\s+)?gotas)\b)(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))(?!\s*(?:(?:of|de)\s+)?(?:wheat|corn|oats?|barley|rye|bran|meal|seeds?|feed|hay|yeast|lard|suet|starch|gelatine?|cheese|meat|beef|tea(?!\s+tree)|coffee|cocoa|chocolate|vinegar|gold|silver|sand|clay|wax|beeswax|rosin|resin|gunpowder|trigo|ma[ií]z|cebada|avena|salvado|semillas?|levadura|manteca|almid[oó]n|queso|carne|caf[eé]|cacao|vinagre|oro|plata|arena|cera)\b)|(?:(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:fluid\s+|fl\.\s*)?(?:(?:grains?|minims?|drachms?|drams?|ounces?|gills?|scruples?|granos?|dracmas?|onzas?|escr[uú]pulos?)\b|(?:grs?|oz)(?:\.|\b)|oz\b|c\.\s?c\.)|\b(?:a\s+few\s+drops|a\s+drop\s+or\s+two|unas\s+(?:cuantas\s+|pocas\s+)?gotas)\b)(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))(?!\s*(?:(?:of|de)\s+)?(?:wheat|corn|oats?|barley|rye|bran|meal|seeds?|feed|hay|yeast|lard|suet|starch|gelatine?|cheese|meat|beef|tea(?!\s+tree)|coffee|cocoa|chocolate|vinegar|gold|silver|sand|clay|wax|beeswax|rosin|resin|gunpowder|trigo|ma[ií]z|cebada|avena|salvado|semillas?|levadura|manteca|almid[oó]n|queso|carne|caf[eé]|cacao|vinagre|oro|plata|arena|cera)\b)(?=[^;!?]{0,80}?\b(?:every\s+(?:[\w-]+\s+){0,2}?hours?|hourly|cada\s+(?:\w+\s+){0,2}?horas?|doses?|dosis|dosage|given|give|gives|giving|administer\w*|administr\w*|take|takes|taken|inject\w*|ivermectin|dele|dale|darle|dar|d[eé]selo|d[eé]sele|tome|tomar|toma|tomando|tinctures?|tintura|infusions?|infusi[oó]n|decoctions?|remed(?:y|ies)|remedios?|medicinal(?:ly)?|medicines?|medicinas?|mixtures?|prescrib\w*|recommend\w*|purgatives?|purgantes?|cathartics?|emetics?|vomitivos?|antispasmodic|anodyne|laxatives?|laxantes?|tonics?|t[oó]nicos?|physic|draughts?|drench\w*|bolus|pills?|liniments?|ointments?|salves?|embrocations?|poultices?|gargles?|lotions?|eye-?waters?|collyri\w*|pomadas?|ung[uü]entos?|linimentos?|cataplasmas?|quinine|quinina|opium|opio|laudanum|l[aá]udano|morphi\w*|morfina|calomel|camphor\w*|alcanfor|digitalis|foxglove|strychni\w*|estricnina|bromides?|bromuro|salicin|salicyl\w*|buchu|creosote|creosota|elaterium|ipecac\w*|paregoric|parag[oó]rico|castor\s+oil|ricino|epsom|glauber|iodides?|yoduro|aloes|rhubarb|ruibarbo|senna|jalap|turpentine|trementina|chloral|chloroform|cloroformo|ether|belladonn?a|aconite|ac[oó]nito|ergot\w*|arseni\w*|ars[eé]nico|mercury|mercurio|antitoxins?|antitoxina|serum|suero|antimony|tartar\s+emetic|pine\s+tar|penny\s*royal|carbolic|creolin|sulphur|azufre|magnesia|bismuth|santonin|cocaine|atropine|aspirin\w*|chlorodyne|squills?|antipyrin\w*|acetanilid\w*|phenacetin|cod[\s-]liver\s+oil|vermifuge|nux\s+vomica|nitre|lobelia|asaf\w*tida|valerian|hyoscyam\w*|cannabis|cantharides|croton\s+oil|podophyll\w*|sarsaparilla|guaiac\w*|colchicum|stramonium|hellebore|savin|tansy|wormwood|quassia|gentian|cinchona)\b)|\b(?:emetics?|vomitivos?|laxatives?|laxantes?|purgatives?|purgantes?|purg(?:e|es|ed|ing)|cathartics?|physic)\b[^;!?]{0,80}?(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|cucharaditas?|cucharadas?|cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b(?:[\s,]+(?:(?:or|and|to|o|y)\s+)?(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|cucharaditas?|cucharadas?|cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b)*|(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|cucharaditas?|cucharadas?|cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b(?:[\s,]+(?:(?:or|and|to|o|y)\s+)?(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|cucharaditas?|cucharadas?|cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b)*(?=[^;!?]{0,80}?\b(?:emetics?|vomitivos?|laxatives?|laxantes?|purgatives?|purgantes?|purg(?:e|es|ed|ing)|cathartics?|physic)\b)|(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:fluid\s+|fl\.\s*)?(?:drachms?|minims?|scruples?|dracmas?|escr[uú]pulos?)\b|\b(?:castor\s+oil|ricino|emetics?|vomitivos?|laxatives?|laxantes?|purgatives?|purgantes?|cathartics?|quinine|quinina|opium|opio|laudanum|l[aá]udano|morphi\w*|morfina|calomel|camphor\w*|alcanfor|digitalis|foxglove|strychni\w*|estricnina|bromides?|bromuro|salicin|salicyl\w*|buchu|creosote|creosota|elaterium|ipecac\w*|paregoric|parag[oó]rico|epsom|glauber|iodides?|yoduro|aloes|senna|jalap|turpentine|trementina|chloral|chloroform|cloroformo|belladonn?a|aconite|ac[oó]nito|ergot\w*|arseni\w*|ars[eé]nico|antitoxins?|antitoxina|antimony|tartar\s+emetic|pine\s+tar|penny\s*royal|carbolic|creolin|magnesia|bismuth|santonin|cocaine|atropine|aspirin\w*|chlorodyne|squills?|antipyrin\w*|acetanilid\w*|phenacetin|cod[\s-]liver\s+oil|vermifuge|nux\s+vomica|lobelia|asaf\w*tida|valerian|hyoscyam\w*|cannabis|cantharides|croton\s+oil|podophyll\w*|colchicum|stramonium|hellebore|savin|tansy|wormwood|quassia|gentian|cinchona|ivermectin)\b[^;!?]{0,80}?(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:de\s+(?:una?\s+)?)?(?:cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))|(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:de\s+(?:una?\s+)?)?(?:cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))(?=[^;!?]{0,80}?\b(?:castor\s+oil|ricino|emetics?|vomitivos?|laxatives?|laxantes?|purgatives?|purgantes?|cathartics?|quinine|quinina|opium|opio|laudanum|l[aá]udano|morphi\w*|morfina|calomel|camphor\w*|alcanfor|digitalis|foxglove|strychni\w*|estricnina|bromides?|bromuro|salicin|salicyl\w*|buchu|creosote|creosota|elaterium|ipecac\w*|paregoric|parag[oó]rico|epsom|glauber|iodides?|yoduro|aloes|senna|jalap|turpentine|trementina|chloral|chloroform|cloroformo|belladonn?a|aconite|ac[oó]nito|ergot\w*|arseni\w*|ars[eé]nico|antitoxins?|antitoxina|antimony|tartar\s+emetic|pine\s+tar|penny\s*royal|carbolic|creolin|magnesia|bismuth|santonin|cocaine|atropine|aspirin\w*|chlorodyne|squills?|antipyrin\w*|acetanilid\w*|phenacetin|cod[\s-]liver\s+oil|vermifuge|nux\s+vomica|lobelia|asaf\w*tida|valerian|hyoscyam\w*|cannabis|cantharides|croton\s+oil|podophyll\w*|colchicum|stramonium|hellebore|savin|tansy|wormwood|quassia|gentian|cinchona|ivermectin)\b)", re.I)
DOSE_OK = re.compile(r"/Firearms Manuals/|FM \d-\d+\.\d+")  # 1A: rifle model numbers (A-500G, 700 ML) and FM 4-25.12 are not doses
ADDR_PRE = re.compile(r"^(?:box|p\.?o\.?m?|suite|ste\.?|apt\.?|no\.?|#\d*|tel:?|phone:?|fax:?|isbn:?|nsn:?|(?!(?:1[5-9]|20)\d\d-$|\d{1,2}-\d{1,2}-$)\S*\d-|\(?\d+(?:-\d+)+)$", re.I)  # 1990-1997 is a range and 22-08-2001 a date, not catalogue numbers
ADDR_POST = re.compile(r"^(?:street|st\.?|avenue|ave\.?|boulevard|blvd\.?|road|rd\.?|drive|lane|ln\.?|way|bulevar|avenida|av\.|calle|rua)[,.;]?$|^-(?!\d{1,2}\b|(?:1[5-9]|20)\d\d\b)\d", re.I)  # -13 / -1997 are ranges; no "Dr." (Dr. John Snow)
GOOGLE_TXT = re.compile(r"public domain|google|usage guidelines|digitiz|scanned|copyright (?:term|law|expir|notice)", re.I)  # bare copyright/scanning hit 11 real summaries

PROMPT = """You catalog documents for a library that ordinary people read on a phone, possibly years from now.
From the title, filename and excerpt below, return JSON only: {{"answers": "..."}}
answers: exactly TWO plain sentences, at most 45 words in all, written in {langname}. The first sentence names the concrete practical questions or topics the document covers. The second sentence names the readers who would use it and the situation in which they would: take the readers from the document itself (its title page, preface or stated purpose says whom it is for); if it does not say, name the people who do the work it describes. {audience}Write full sentences, never labels, headings or questions; only facts visible below; no marketing words; never start with "This document".{extra}

Title: {title}
Filename: {stem}
Shelf: {shelf}
Excerpt (start):
{head}
Excerpt (end):
{tail}
"""
# #74: the old "offline survival library" framing invented survivalist readers for a 1920 canoe ethnography
AUDIENCE = "Do not assume survival, emergency or prepper use unless the excerpt is about that. "
# #125: never "survivors", "survivalists", "preppers", "self-sufficiency" or "in emergencies" on an old book (verify drops them)
AUD_NO = ("Never call the readers survivors, survivalists or preppers and never write 'for survival', 'in emergencies', "
          "'self-sufficiency' or 'long-term food security'. ")
AUDIENCE_HIST = ("This is an old book: describe it as what the excerpt shows it to be. For the readers, first name the people "
                 "who still do what it teaches (home canners, blacksmiths, beekeepers, gun owners ...); only when its content is "
                 "obsolete name historians or collectors instead. Never assume survival, emergency or prepper use unless the "
                 "excerpt itself is about survival. ")
# #138: a play's or story's characters and plot are not its readers (name who would stage or read it); a book sold for
# the benefit of a cause is not written for that cause's beneficiaries; a report's subject period is not a reading time
AUD_SOURCE = ("The readers are never the characters or situation of a story or play (name who would stage or read it), never "
              "the beneficiaries of a charity the book was sold for, and never 'before/during the war'. ")
HIST = ("docs/survivor_library", "docs/HISTORICAL")
# #73: every echo variant seen in 15,290 summaries (10-06): template text, "Who should X ..." / "Quién ..." / "Qui ..."
# question fragments, "Who should open it:" style labels, "Practical questions about ..." openers
_S = r"(?:^|[.!?]\s+)"
ECHO = re.compile(r"what practical questions|concrete topics|\bsentence [12]\b|only facts visible|who should open it"
                  + "|" + _S + r"(?:practical questions|questions answered|topics covered|answers?)\b.{0,3}(?:about|on|:)"
                  + "|" + _S + r"(?:who|qui[eé]n|qui|à qui|quem|wer)\s"
                  + "|" + _S + r"(?:who should [a-z ]{0,25}|when|audience|target audience|intended (?:audience|users)|readers?|"
                  r"users?|for whom|use(?:d|ful)? (?:by|for)|open (?:it|when)|para qui[eé]n|p[uú]blico|destinataires?|public cible)\s*:"
                  # #158 (b1mech echo): the prompt's own words ("as described in the excerpt"), numbered-list answers
                  + r"|\b(?:as |the )(?:described|stated|shown|seen|noted|mentioned|provided|given)? ?(?:in )?the (?:excerpt|provided text|given text)\b"
                  + r"|\bthe excerpt\b|^\s*\d+[.)]\s|\bhere are\b|\bresumen en dos frases\b",
                  re.I)
def bad_shape(a):
    """#158 (b1mech echo): an answer that is a list of questions ("What is X? How does Y?"), or does not end a sentence"""
    a = (a or "").strip()
    return bool(a) and (a.count("?") >= 2 or not _END.search(a))

def post(prompt, temp, n):
    req = urllib.request.Request(f"{URL}/api/generate", data=json.dumps({
        "model": MODEL, "prompt": prompt, "stream": False, "think": False, "format": "json",
        "options": {"temperature": temp, "num_predict": n}}).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=900))["response"]

def ask(title, stem, shelf, head, tail, lang, hist=False, dup="", note="", rel="", text=None):
    extra = ("\nOther documents in this library got almost the same summary: \"%s\". Make the first sentence specific to "
             "THIS document: its part, volume, chapter or particular topic as the excerpt shows." % dup) if dup else ""
    old = rel.startswith(OLD_SHELVES) and not aud_ok(rel, title)
    prompt = PROMPT.format(title=title, stem=stem, shelf=shelf, head=head, tail=tail, langname=LANG_NAME[lang],
                           audience=(AUDIENCE_HIST if hist else AUDIENCE) + (AUD_NO if old else "")
                           + (AUD_SOURCE if rel.startswith(OLD_SHELVES) else ""), extra=extra + note)
    a = ""
    for temp, n in ((0.1, 320), (0.5, 600)):   # #77: 4 "Unterminated string" parse fails; retry, then salvage the field
        r = post(prompt, temp, n)
        try:
            a = str(json.loads(r).get("answers", ""))
        except ValueError:
            m = re.search(r'"answers"\s*:\s*"((?:[^"\\]|\\.)+)', r)
            a = m.group(1).replace('\\"', '"') if m else ""
        a = re.sub(r"\s+", " ", a).strip()
        if a and not ECHO.search(a) and not audience_bad(rel, title, a, text) and not mixed_script(a, lang) \
                and not bad_shape(a) and (lang == "en" or s_lang_ok(a, lang)):   # #158: shape and language as --verify checks them
            break
    if audience_bad(rel, title, a, text):   # #125: two tries still invented survivors: keep the sentences that do not
        ss = re.split(r"(?<=[.!?])\s+", a)
        a = " ".join(x for i, x in enumerate(ss) if not AUD_BAD.search(x) and not SURV_WORDS.search(x) and not (i and AUD_PLOT.search(x))
                     and not (text is not None and frame_bad(x, text)))
    if len(a.split()) > 60:   # #135: whole sentences only, never "…"
        out = []
        for x in re.split(r"(?<=[.!?])\s+", a):
            if len(" ".join(out + [x]).split()) > 60:
                break
            out.append(x)
        a = " ".join(out) or trim_s(a, lang, cap=len(" ".join(a.split()[:60])))
    return a

def year_from_name(rel):
    m = re.findall(r"(?<!\d)(1[5-9]\d\d|20[0-2]\d)(?![\ds])", os.path.basename(rel))   # "1890s" is a decade
    return m[-1] if m else ""

def script_prose(text):
    """#76: prose() scores Latin words only and rejected every ko/zh/ar/bn sheet; non-Latin text is used as is."""
    body = re.sub(r"\s+", " ", text).strip()
    return body[:HEAD], (body[-TAIL:] if len(body) > HEAD + TAIL else "")

def excerpt(text, rel):
    """(head, tail) for the prompt: non-Latin scripts and reference lists as is (#76; r21: citation lines fail prose()'s
    word-quality filter, so the Humanure Notes, the NREL bibliography and the jumbo-rotor reading list read as no text)"""
    return script_prose(text) if script_lang(text, os.path.basename(rel)) or is_reflist(text) else prose(text)

def work(rel, e, dup=""):
    stem = humanize(os.path.basename(rel))
    shelf = rel.split("/")[1] if rel.startswith("docs/") else rel.split("/")[0]
    pdf = os.path.join(LIB, rel)
    try:
        text = extract(pdf, rel) or "" if os.path.exists(pdf) else ""
    except Exception:
        text = ""
    text = clean_text(text)
    y = pick_year(text, rel, e.get("t", ""))
    lang = e["l"] if e.get("l") in LANG_NAME else detect_lang(text, os.path.basename(rel))[0]   # --verify's label wins
    head, tail = excerpt(text, rel)
    if not readable(text, rel, lang):
        if not e.get("s"):
            return rel, {"a": "", "y": y, "l": e.get("l", "")}   # nothing readable, nothing to invent; keep the label
            # (r21: returning "" here blanked the VL-detected bn label on 5 Bengali sheets and the en label on 6 more)
        head, tail = "(no text layer; vision description of the pages) " + e["s"], ""
    if dup and len(text) > 3 * HEAD:   # #78: series parts share front matter; the middle says which part this is
        tail = prose(text[len(text) // 2:])[0][:1500] + "\n...\n" + tail
    a = ask(e.get("t", stem), stem, shelf, head, tail, lang, rel.startswith(HIST), dup, prompt_note(text, rel), rel, ftext(text))
    return rel, {"a": a, "y": y, "l": lang}

# #72 years: a copyright/revision/edition/printing cue, a dated title page, or a date repeated in the footers; then the
# filename year; else blank. A bare 4-digit occurrence is no evidence (Emergency War Surgery 1946 vs "Revision 2004").
YR = r"(?<!\d)(1[5-9]\d\d|20[0-2]\d)(?!\d)"
CUE = re.compile(r"(?:©|\(c\)|\[c\]|copyri\w{1,4}|revised|revision|rev\.|edition|printing|printed|reprinted|first published|"
                 r"publication date|date of publication|updated|issued|act of congress|édition|edición|impreso|imprimé|derechos|"
                 r"revisado|révisé|last reviewed)[^\d\f]{0,40}?(?:\d{1,2}(?:st|nd|rd|th)?,?[ ./-][^\d\f]{0,12}|(?:\d{1,2}[./-]){2})?" + YR, re.I)
# ("Revised 3/5/2018" on the SCARES wallet card: a numeric date after the cue)
# "published in 1910" / "published by UNICEF in 1984" are narrative (Humanure ch. 6, SODIS); "First Edition 1 June 2001" carries a day
CUE_AFTER = re.compile(YR + r"(?:[ ,]{0,3}(?:edition|revision|revised|printing|reprint|édition|edición)|, \d+ ?p\.)", re.I)
# ", 1999, 90 p.)": the CD3WD/Greenstone citation line on page 1 ("Water Resources Institute, 1999, 90 p.)")
CUE_BACK = re.compile(r"(?:©|\(c\)|\[c\]|copyri\w{1,4}|printed (?:in|by))[^\d\f]{0,40}?" + YR, re.I)   # tail: no "edition" (bibliographies)
_MON = ("January February March April May June July August September October November December Jan Feb Mar Apr Jun Jul "
        "Aug Sep Sept Oct Nov Dec").split()
_MON_X = ("enero febrero marzo abril mayo junio julio agosto septiembre setiembre octubre noviembre diciembre janvier février "
          "mars avril mai juin juillet août octobre novembre décembre Januar Februar März Juni Juli Oktober Dezember janeiro "
          "fevereiro março maio junho julho setembro outubro novembro dezembro").split()
_MONTHS = sorted({v for w in _MON for v in (w, w.upper())} | {v for w in _MON_X for v in (w, w.capitalize(), w.upper())},
                 key=len, reverse=True)
DATE = re.compile(r"(?<![A-Za-z])(?:%s)\.?(?: +\d{1,2}(?:-\d{1,2})?(?:st|nd|rd|th)?,?)?(?: +de)?,? +%s" % ("|".join(_MONTHS), YR))
IMPRINT = re.compile(r"^[^\d\n]{2,40}[ ,-]+" + YR + r"\.?$", re.M)   # title-page imprint line: "IQUITOS - PERU 1997", "London, 1890"
NOISE = re.compile(r"gutenberg|ebook|e-text|release date|posting date|posted|digiti|scann|internet archive|downloaded|"
                   r"accessed|retrieved|consulted|electronic edition|pdf generated|digital file|microfiche|microfilm|"
                   r"micro-?r[eo]\w*produc|canadian inst|university library|file:///|archive\.org", re.I)
# #130 (fix80 F): digitization years are not publication years: Cornell "Digital file copyright by Cornell University
# Library 1995", Gutenberg "[Posted: July 8, 2003]", CIHM "microreproductions ©1994", cd3wd browser footers
# "file:///C:/... 25/04/2012" (Gray's Anatomy 1918 printed as 2012)
DEFINITIVE = [re.compile(r"\(\d{1,2}\s*[-–]\s*\d{1,2}\s*[-–]\s*(\d\d)\s+Edition\)"),   # CFR "(10–1–24 Edition)" beats the GPO VerDate stamp
              re.compile(r"last (?:updated|reviewed|revised)\s*:?\s*(?:on\s+)?(?:[A-Za-z]+\.?\s+\d{1,2},?\s+|\d{1,2}[./-]\d{1,2}[./-]|[A-Za-z]+\.?\s+)?" + YR, re.I)]
PRINTCODE = re.compile(r"\bP-\d{3,4}[A-Z]?\s*/\s*(?:%s)\.?\s+" % "|".join(_MONTHS) + YR)   # FEMA "P-2354 / April 2024"
OCR_C = re.compile(r"(?m)^[0O@Q][ \t]+[A-Z][^\d\f\n]{2,80}?" + YR)   # "0 Intermediate Technology Development Group, 1983 and 1985" (OCR'd ©)
# #136 (r21 judge F3): glyph, publisher and year on ONE line. "\s+" spanned line breaks, so a chart axis "0" read
# "A. En 1972" two lines down as "© ... 1972" (all 4 STEP floods files), and "0\n\nFuente: Christensen, 1974"
IMPRINT2 = re.compile(r"^[A-Z][^\d\n,]{1,30}, [A-Z][^\d\n,]{1,25}\n" + YR + r"\.?$", re.M)   # "City, Country" ("COUNTRY\n1986" was a table)   # "Santiago, Chile\n1984" (imprint split over two lines)
SOURCE = re.compile(r"\b(?:from|based on|adapted from|of) the\b", re.I)   # "revised and expanded from the 1991 ... publication"
EDN = re.compile(r"edition|revised|enlarged|édition|edición|ausgabe", re.I)
YEAR_FIX = {  # read off the pages by hand (10-06 docs agent, medical_currency "year unknown"): the rule cannot see these
    "docs/medical/headington_trauma_critical_incident.pdf": "2013",   # only reference-list years in the text
    "docs/medical/hesperian_where_there_is_no_doctor/Child_growth_chart_nwtnd.pdf": "2011",   # no text layer
    "docs/medical/hesperian_where_there_is_no_doctor/NWTND_Development_Charts.pdf": "2011",   # no text layer
    "docs/medical/headington_going_the_distance.pdf": "2020",   # "© Headington Institute, 2020" (G3 2026-10-10: the year IS printed)
    "docs/medical/emergency_war_surgery.pdf": "2004",   # Third US Revision 2004; "Copyright © 2012" is the Skyhorse reprint
    # #130 (fix80 F + r21_titles "y moved 30+ years"): read off the pages 2026-10-07; the rules cannot see these
    "docs/cd3wd/2012/small_business/_ms_405_AMAZONIA_jf_en_142710_.pdf": "1997",   # byline "Roger Taylor 12/97"
    "docs/cd3wd/2012/transport/_tr_ms_405_Home_made_bicycle_from_Alabama_jf_en_149210_.pdf": "",   # 1890 = the bicycle; 1973 = the cited book
    "docs/cd3wd/2012/health/_mc_greys_anatomy_medical_chapter_listings_only__171030_.pdf": "1918",   # "Gray, Henry. 1918."; 2012 = print footer
    "docs/school_textbooks/college_open_textbooks/greys_anatomy_medical_chapter_listings_only__171030_.pdf": "1918",
    "docs/survivor_library/SurvivalLibrary/library/Coal and Mining/report_of_the_geological_survey_of_the_state_of_missouri_1974.pdf": "1874",   # title page "1874 Atlas"; filename typo
    "docs/survivor_library/SurvivalLibrary/library/Coal and Mining/a_textbook_on_mining_engineering_vol_5_1900.pdf": "1900",   # "Copyright, 1893, 1994, 1908, 1899" is OCR
    "docs/survivor_library/SurvivalLibrary/library/Medical-Surgery 2/surgical_diagnosis-kiliani_1850.pdf": "1905",   # "COPYRIGHT, 1905, By WILLIAM WOOD"; filename wrong
    "docs/survivor_library/SurvivalLibrary/library/Optometry/hand-book_for_young_and_old_opticians_1888.pdf": "1888",   # 1936 = Surgeon General's library form stamp
    "docs/survivor_library/SurvivalLibrary/library/Steam Engines/modern_steam_engines-an_elementary_treatise_written_in_plain_language_for_use_in_the_workshop_1853.pdf": "1893",   # Rose 1886/1893
    "docs/survivor_library/SurvivalLibrary/library/Teaching-Readers/elson_junior_literature_book_2_1900.pdf": "1936",   # "Copyright 1932, 1936 by Scott, Foresman"; filename wrong
    "docs/survivor_library/SurvivalLibrary/library/Wood-Furniture/wonders_in_wood_1946.pdf": "1946",   # "Originally published 1946 First Linden edition 1997" (reprint)
    "docs/survivor_library/SurvivalLibrary/library/Economics/ae-principles_of_economics-carl_menger_1871.pdf": "1871",   # 1976 translation, 2007 reprint, 1998 = footnote
    "docs/survivor_library/SurvivalLibrary/library/Wood Magazine/wood_magazine_064_1993.pdf": "1993",   # 1999 = an advertiser's ©
    "docs/survivor_library/SurvivalLibrary/library/Wood Magazine/wood_magazine_012_1986.pdf": "1986",   # 1996 = OCR of the 1986 ©
    "docs/survivor_library/SurvivalLibrary/library/Archery/hunting-with-a-bow-and-arrow.pdf": "1923",   # Saxton Pope, 1923; the text carries only Gutenberg dates
    "docs/survivor_library/SurvivalLibrary/library/Survival-Individual/the_journals_of_lewis_and_clark_by_meriwether_lewis.pdf": "",   # 1804-1806 journals; Gutenberg dates only
    # #136 (r22): real imprints split over lines by the OCR. The one-line © rule no longer reads them; read off the
    # title-page verso text (r22_year_diff.log) 2026-10-07
    "docs/cd3wd/2012/agriculture/_ag_416_Soil_Conservation05_285_jf_en_101570_.pdf": "1982",   # "Copyright 0 International Labour Organisation 1982"
    "docs/cd3wd/2012/wind_power/_wi_406_PU350_PU500_windmills_construction_manual_21_501_jf_en_154760_.pdf": "1982",   # "0 C 1982 NIEK ... VAN DE VEN"
    "docs/cd3wd/2012/agriculture/_ag_413_Hydroponics05_189_jf_en_100970_.pdf": "1959",   # "@ Oxford University Press 1959, Printed in India"
    "docs/cd3wd/2012/metalwork/_me_412_Sharpening_Small_Tools04_117_jf_en_139180_.pdf": "1976",   # "0 Argus Books Ltd and Ian Bradley 1976"
    "docs/cd3wd/2012/solar/_sl_431_Evaluation_of_Solar_Cookers23_535_jf_en_147230_.pdf": "1977",   # "0 VITA, Inc. 1977"
    "docs/cd3wd/2012/construction/_co_434_Rural_Building_Construction25_671_jf_en_123330_.pdf": "1986",   # "@ Stichting Kongregatie F.I.C., Maastricht, 1986"
    "docs/cd3wd/2012/energy/_engy_425_The_Kenya_Ceramic_Jiko20_480_jf_en_131010_.pdf": "1991",   # "0 AT international and CARE 1991"
    "docs/cd3wd/2012/manufacturing/_ma_405_PA_dwg_The_StenScreen31_767_jf_en_135140_.pdf": "1983",   # "@ Intermediate Technology Publications Ltd. 1983"
    "docs/cd3wd/2012/agriculture/_ag_418_China_Grain_Storage_Structures07_295_jf_en_102000_.pdf": "1982",   # "0 FAO 1982"
    "docs/cd3wd/2012/agriculture/_ag_414_Tropical_Feeds05_222_jf_en_101220_.pdf": "1981",   # "@ FAO 1981"; 1971 = the first edition
    "docs/cd3wd/2012/appropriate_technology/_at_ed_ms_408_UNESCO_Small_Technical_Libraries31_768_jf_en_119370_.pdf": "1973",   # "Q Unesco 1973"
    "docs/cd3wd/2012/construction/_co_433_Ferrocement_a_Versatile_Construction_Material25_597_jf_en_123060_.pdf": "1976",   # "0 Asian Institute of Technology, Bangkok, Thailand 1976"
    "docs/cd3wd/2012/energy/_engy_19_429_Renewable_Energy_Research_India_jf_en_130140_.pdf": "1981",   # "0 C 1981 Tata Energy Research Institute"
    "docs/cd3wd/2012/communication/_cm_439_Visual_Literacy_in_Communication31_760_jf_en_122640_.pdf": "1978",   # "@ I.I.A.L.M. ISBN 1978"
    "docs/cd3wd/2012/metalwork/_me_412_How_to_Make_Twelve_Woodworking_Tools04_137_jf_en_139140_.pdf": "1986",   # "@ Intermediate Technology Publications 1986"
    "docs/cd3wd/2012/industry/_ind_The_Village_Texturizer33_788_jf_440_en_133730_.pdf": "1977",   # "@ Meals for Millions, September 1977"
    "docs/cd3wd/2012/agriculture/_ag_414_Small_Scale_Irrigation05_217_jf_en_101150_.pdf": "1979",   # "@ Intermediate Technology Publications ... 1979. Published 1979"
    "docs/cd3wd/2012/emergency/_em_441_The_Management_of_Nutritional_Emergencies_in_Large_Populations35_821_jf_en_129760_.pdf": "1978",   # "0 World Health Organization 1978"
    "docs/cd3wd/2012/small_business/_ac_Rural_Credit30_766_jf_438_en_100360_.pdf": "1988",   # "@ Intermediate Technology Publications Ltd. 1988"
    "docs/cd3wd/2012/water/_wa_422_Slow_Sand_Filtration16_376_jf_en_150420_.pdf": "1974",   # "0 World Health Organization 1974"
    "docs/survivor_library/SurvivalLibrary/library/Sanitation/primer_of_hygiene_and_sanitation_1910.pdf": "1913",
    "docs/survivor_library/SurvivalLibrary/library/Teaching-Readers/elson_primary_school_reader_book_4_1913.pdf": "1918",   # OCR'd "Coprriast 1912, 1918"
    "docs/cd3wd/2012/wind_power/_wi_405_The_sunless_windless_waterless_alternative_energy_system_jf_en_154490_.pdf": "",   # "Benjamin Franklin, May 1738" is a quote; 1800 = RPM   # "@ Yonkers-on-Hudson, World Book Company 1913"
    # #158 (red team 10-09 F6, read off the pages 2026-10-10)
    "docs/cd3wd/2012/agriculture/_ag_1855_Starting_bv_en_100580_.pdf": "2000",   # "© IITA 2000"; "1855" in the file name is a catalogue number that late() took for a year
    "docs/homesteading_extension/psu_ipm.pdf": "2026",   # "Georgia Pest Management Handbook—2026–2027 Home and Garden Edition" (no cue word before the year)
    "docs/cd3wd/2012/computing/_it_ocw_CA_L08_Review_en_134220_.pdf": "2005",   # "Năm học 2005 - 2006"; exam "ngày 25 tháng 08 năm 2005"
    "docs/school_textbooks/college_open_textbooks/_it_ocw_CA_L08_Review_en_134220_.pdf": "2005",
    # #174 (G3 2026-10-10, read off the pages by hand; --verify would otherwise revert these every reseal)
    "docs/cd3wd/2012/agriculture/_ag_cattle_condition_scoring_rsa_en_lp_104930_.pdf": "1999",
    "docs/cd3wd/2012/agriculture/_ag_wa_KnO_100441_Treadle_Pump_TB_pa_117930_.pdf": "2010",   # "created in 2010"
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_20_119910_.pdf": "1983",   # "[C] 1983 CODEL"
    "docs/cd3wd/2012/energy/_engy_Babington_stuff_wwyg_en_131120_.pdf": "2005",   # "11/27/05"
    "docs/cd3wd/2012/health/_mc_health_magazine_sanicho_2_es_pc_lp_137300_.pdf": "1997",   # "Noviembre 97 - Marzo 98"
    "docs/cd3wd/2012/health/_mc_primary_health_es_lp_138370_.pdf": "1997",   # "IQUITOS - PERU 1997"
    "docs/cd3wd/2012/sanitation/_sa_ms_pit_emptying_systems_pa_en_146060_.pdf": "2007",   # "written ... November 2007"
    "docs/cd3wd/2012/small_business/_ms_405_DESAL_jf_en_143140_.pdf": "1998",   # "David Corbus 7/98"
    "docs/cd3wd/2012/solar/_sl_431_Technology_for_Solar_Energy_Utilization323_563_jf_en_147330_.pdf": "1978",   # "New York, 1978"
    "docs/cd3wd/2012/transport/_tr_435_Bicycles_A_Case_Study_of_Indian_Experience26_656_jf_en_148620_.pdf": "1969",   # "New York, 1969"
    "docs/cd3wd/2012/water/_wa_405_Hydraulic_Ram_2003_breurram_es_jf_149570_.pdf": "2006",   # "january 2006"; 2003 is the file name
    "docs/cd3wd/2012/water/_wa_ms_treadle_pumps_pa_en_151300_.pdf": "2010",
    "docs/cd3wd/2012/wind_power/_wi_Danish_version_ITDG_pmg_konstruktions_manual_jf_pa_en_155290_.pdf": "2002",   # "Oversat ... 2002"
    "docs/comms/ofsc_frs_gmrs_emergency_communications_guide22.pdf": "2024",   # "Version 1.7 4/9/24"
    "docs/foraging_coastal/shellfish_id_guide_wa_dnr.pdf": "2016",   # "Effective July 1, 2016 - June 30, 2017"
    "docs/grain_processing/ksu_wheat_production_handbook_C529.pdf": "1997",   # "C-529 May 1997" (last page)
    "docs/sanitation/tamu_graywater_safe_use_b6176.pdf": "2008",   # "B-6176 3-08"; 2005 is the regulatory cut-off
    "docs/school_textbooks/college_open_textbooks/_econ_Economics_Master_ed_en_wfs_gtb_lp_128110_.pdf": "",   # 1636 = Dafforne's edition
    "docs/security/cisa_deescalation_action_guide_2025.pdf": "2024",   # "As of December 2024"
    "docs/survivor_library/SurvivalLibrary/library/Cookbooks/boyscout_cookbook_pdf.pdf": "1997",
    "docs/survivor_library/SurvivalLibrary/library/Economics/principles_of_political_economy_vol_1-wilhelm_roscher_1882.pdf": "1878",   # Callaghan 1878
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/encyclopedia_britannica_11_ed_vol_07_1911.pdf": "1910",   # "Copyright ... 1910"
    "docs/survivor_library/SurvivalLibrary/library/Firearms Manuals/sig_gsr1911_semi_automatic_pistol.pdf": "",   # 1911 = model
    "docs/survivor_library/SurvivalLibrary/library/Wagon and Coach Building/the_new_york_coach-makers_magazine_vol_11_1858.pdf": "1870",   # vol. 11 = 1869-70, (c) 1870
    "docs/textiles/asg_hand_stitches_reference.pdf": "2008",   # "6/08"
    "mirrors/ready_gov/www.ready.gov/sites/default/files/2020-04/structural-design-criteria-chapter-2.pdf": "",   # 1998 = cited source
    "mirrors/ready_gov/www.ready.gov/sites/default/files/2022-11/Vietnamese-1802-CardLayout.pdf": "",   # 1802 = FEMA pub number
}
YEAR_FIX.update({  # RT3 H3 (#184, 2026-10-12): read by hand, see the private test record;
    # a full --verify reverted these to the rule values (and popped `s` on the two INPHO rice files)
    "docs/cd3wd/2012/agriculture/_ag_415_Soil_Tillage_in_the_Tropics_and_Subtropics05_255_jf_en_101410_.pdf": "1984",
    "docs/cd3wd/2012/agriculture/_ag_agroindustry_south_america_2_es_unfao_lp_103120_.pdf": "1996",
    "docs/cd3wd/2012/agriculture/_ag_bees_ss_2_pc_en_lp_103870_.pdf": "1978",
    "docs/cd3wd/2012/agriculture/_ag_diarrhoea_sheep_goats_rsa_en_lp_106000_.pdf": "2001",
    "docs/cd3wd/2012/agriculture/_ag_postharvest_1016_inpho_en_lp_114620_.pdf": "1991",
    "docs/cd3wd/2012/agriculture/_ag_postharvest_1025_inpho_en_lp_114710_.pdf": "1994",
    "docs/cd3wd/2012/agriculture/_ag_postharvest_1025_inpho_sp_en_114720_.pdf": "1994",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_19_119900_.pdf": "1990",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_41_120120_.pdf": "1984",
    "docs/cd3wd/2012/economics/_econ_Economics_Master_ed_en_wfs_gtb_lp_128110_.pdf": "",
    "docs/cd3wd/2012/geography/_geog_afr_Africa_Master_ed_en_wfs_gtb_lp_132580_.pdf": "",
    "docs/cd3wd/2012/geography/_geog_as_countries_asia_ed_en_wfs_gtb_lp_132610_.pdf": "",
    "docs/cd3wd/2012/geography/_geog_eu_countries_europe_ed_en_wfs_gtb_lp_132630_.pdf": "",
    "docs/cd3wd/2012/geography/_geog_me_middle_east_ed_en_wfs_gtb_lp_132640_.pdf": "",
    "docs/cd3wd/2012/history/_hist_History_Master_100_2011_ed_en_wfs_gtb_lp_132660_.pdf": "",
    "docs/cd3wd/2012/history/_hist_History_Modern_Master_ed_en_wfs_gtb_lp_132680_.pdf": "",
    "docs/cd3wd/2012/history/_hist_histukmodm_lp_ed_en_wfs_gtb_lp_132690_.pdf": "",
    "docs/cd3wd/2012/recreation/_art_art_best_of_en_wfs_gtb_118100_.pdf": "",
    "docs/cd3wd/2012/reference/_ppl_David_Livingstone_ed_en_wfs_gtb_lp_145400_.pdf": "",
    "docs/cd3wd/2012/reference/_ppl_Henry_Morton_Stanley_ed_en_wfs_gtb_lp_145410_.pdf": "",
    "docs/cd3wd/2012/reference/_ppl_Johannes_Gutenberg_ed_en_wfs_gtb_lp_145420_.pdf": "",
    "docs/cd3wd/2012/reference/_ppl_Leonardo_da_Vinci_ed_en_wfs_gtb_lp_145430_.pdf": "",
    "docs/cd3wd/2012/reference/_ppl_People_Master_ed_en_wfs_gtb_lp_145440_.pdf": "",
    "docs/cd3wd/2012/reference/_sc_tech_Engineering_Master_engg_ed_en_wfs_gtb_lp_146400_.pdf": "",
    "docs/cd3wd/2012/wind_power/_wi_406_The_Gaudgaon_village_sailwing_windmill_21_506_jf_en_154830_.pdf": "1982",
    "docs/school_textbooks/high_school/_art_art_best_of_en_wfs_gtb_118100_.pdf": "",
    "docs/school_textbooks/high_school/_geog_afr_Africa_Master_ed_en_wfs_gtb_lp_132580_.pdf": "",
    "docs/school_textbooks/high_school/_geog_as_countries_asia_ed_en_wfs_gtb_lp_132610_.pdf": "",
    "docs/school_textbooks/high_school/_geog_eu_countries_europe_ed_en_wfs_gtb_lp_132630_.pdf": "",
    "docs/school_textbooks/high_school/_geog_me_middle_east_ed_en_wfs_gtb_lp_132640_.pdf": "",
    "docs/school_textbooks/high_school/_hist_History_Master_100_2011_ed_en_wfs_gtb_lp_132660_.pdf": "",
    "docs/school_textbooks/high_school/_hist_History_Modern_Master_ed_en_wfs_gtb_lp_132680_.pdf": "",
    "docs/school_textbooks/high_school/_hist_histukmodm_lp_ed_en_wfs_gtb_lp_132690_.pdf": "",
    "docs/school_textbooks/high_school/_ppl_People_Master_ed_en_wfs_gtb_lp_145440_.pdf": "",
    "docs/school_textbooks/high_school/_sc_tech_Engineering_Master_engg_ed_en_wfs_gtb_lp_146400_.pdf": "",
    "docs/school_textbooks/siyavula_grades_4_9/_english_1_grd_5_m5_SINKING_FEELING_f_siya_207860_.pdf": "",
    "docs/survivor_library/SurvivalLibrary/library/Firearms Manuals/baikal_drozd_mp661k_bb_submachine_gu.pdf": "2002",
    "docs/survivor_library/SurvivalLibrary/library/Firearms Manuals/histandard_a103.pdf": "1962",
    "docs/survivor_library/SurvivalLibrary/library/Firearms Manuals/safari_1911_models_semi_automatic_pistols.pdf": "",
    "docs/survivor_library/SurvivalLibrary/library/Morality/history_of_european_morals_from_augustus_to_charlemagne_1873_vol_1.pdf": "1890",
    "mirrors/ready_gov/www.ready.gov/sites/default/files/2020-04/ready_business_power-outage-toolkit_spanish.pdf": "",
    "mirrors/ready_gov/www.ready.gov/sites/default/files/2022-11/SimplifiedChinese_1802_cards.pdf": "",
})
YEAR_FIX.update({  # RT4 J3 (#195, 2026-10-13): read by hand, see the private test record;
    # a --verify dry run on J3's catalog reverted these to the rule values
    "docs/cd3wd/2012/agriculture/_ag_donkey_care_rsa_en_lp_106040_.pdf": "1999",
    "docs/cd3wd/2012/agriculture/_ag_mfkh_en_lp_Ag_1_Cargil_Corp_lp_177900_.pdf": "2003",
    "docs/cd3wd/2012/agriculture/_ag_mfkh_es_lp_Best_of_Organic_Como_Cuba_sobrevivio_al_peak_oil_lp_178950_.pdf": "2006",
    "docs/cd3wd/2012/agriculture/_ag_milk_clean_production_india_en_lp_112460_.pdf": "2002",
    "docs/cd3wd/2012/agriculture/_ag_vet_ms_Arthritis_in_cattle_pa_en_117820_.pdf": "1961",
    "docs/cd3wd/2012/appropriate_technology/_at_411_Towards_Village_Industry03_81_jf_en_118620_.pdf": "1978",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_25_119960_.pdf": "1991",
    "docs/cd3wd/2012/construction/_co_ms_clay_tile_manufacture_pa_en_125780_.pdf": "1986",
    "docs/cd3wd/2012/energy/_engy_3_Dollar_Battery_Charger_wwyg_en_130150_.pdf": "2004",
    "docs/cd3wd/2012/energy/_engy_biodiesel_prod_tech_nrel_usa_sp_en_131170_.pdf": "2004",
    "docs/cd3wd/2012/health/_mc_primary_health_15_transmissible_disease_es_lp_138230_.pdf": "1997",
    "docs/cd3wd/2012/industry/_ind_440_Barbs_Prongs_Points_Prickers_and_Stickers33_790_jf_en_132710_.pdf": "1970",
    "docs/cd3wd/2012/solar/_sl_431_Thermische_Solarenergie_jf_en_147390_.pdf": "1997",
    "docs/death_care/cdp_grief_bereavement_toolkit_2022.pdf": "",
    "docs/school_textbooks/high_school/_ref_lit_Roget_Peter_Mark_1779_1869_Roget_s_Thesaurus_en_final_combined_master_gtb_5star_188403_.pdf": "",
    "docs/school_textbooks/siyavula_grades_4_9/_hist_grd_6_m2_THE_ROAD_TO_DEMOCRACY_siya_210110_.pdf": "",
    "docs/survivor_library/SurvivalLibrary/library/Archery/hunting-with-a-bow-and-arrow.pdf": "1925",
    "docs/survivor_library/SurvivalLibrary/library/Coal and Mining/the_deposits_of_the_useful_minerals_and_rocks_vol_2_1914.pdf": "1916",
    "docs/survivor_library/SurvivalLibrary/library/Forestry/hand_book_of_timber_preservation_1904.pdf": "1909",
    "docs/survivor_library/SurvivalLibrary/library/Survival-Individual/combat-survival-guerrila-skills-handbook-of-the-red-chinese.pdf": "1984",
    "docs/survivor_library/SurvivalLibrary/library/Wood Magazine/wood_magazine_155_2004.pdf": "2004",
    "docs/survivor_library/SurvivalLibrary/library/Wood Magazine/wood_magazine_156_2004.pdf": "2004",
    "mirrors/ready_gov/www.ready.gov/sites/default/files/2022-11/TraditionalChinese1802Cards.pdf": "",
})

YEAR_FIX.update({  # RT5 K5 (#208, 2026-10-17): read off the pages by hand (redteam_20261016_scripts/fix_k5_apply.py)
    "docs/cd3wd/2012/agriculture/_ag_413_Jojoba_A_Guide_to_the_Literature05_195_jf_en_101010_.pdf": "1982",
    "docs/cd3wd/2012/agriculture/_ag_417_The_Employment_of_Draught_Animals_in_Agriculture06_241_jf_en_101910_.pdf": "1972",
    "docs/cd3wd/2012/agriculture/_ag_419_Manual_of_Reforestation_and_Erosion_Control_for_the_Philippines08_313_jf_en_102330_.pdf": "1976",   # "Eschborn I976" (OCR)
    "docs/cd3wd/2012/agriculture/_ag_capibara_rodent_es_lp_104820_.pdf": "1995",
    "docs/cd3wd/2012/electricity/_el_radio_electronics_ded_en_lp_127530_.pdf": "1993",
    "docs/cd3wd/2012/energy/_engy_KnO_100175_CA_Toolkit_PAC_SmartFinal_pa_en_131910_.pdf": "2010",
    "docs/cd3wd/2012/health/_mc_437_The_Tooth_Trip27_713_jf_en_136640_.pdf": "1980",   # "Eighth Printing October 1930" (OCR of 1980)
    "docs/cd3wd/2012/small_business/_ac_Training_Village_Entrepreneurs30_764_jf_438_en_100420_.pdf": "1980",
    "docs/cd3wd/2012/small_business/_ms_es_KnO_100250_la_refrigeracon_por_evaporacion_pa_145250_.pdf": "",   # 1994 dateline vs 2000 citation
    "docs/comms/ncvec_extra_pool_2024_2028.pdf": "2024",
    "docs/survivor_library/SurvivalLibrary/library/Botany/botany_for_young_people_and_common_schools_1900.pdf": "1858",
    "docs/survivor_library/SurvivalLibrary/library/Economics/ae-the_ultimate_standard_of_value-bohm-bawerk_1890.pdf": "1894",
})

YEAR_FIX.update({  # RT6 L5 (#220, 2026-10-21): read off the pages by hand (redteam_20261020_scripts/fix_l5_apply.py)
    "docs/cd3wd/2012/agriculture/_ag_1772_Sp_Plant_Extract_bv_en_100570_.pdf": "2006",   # "The Organic Farmer Nr. 17, Sept./Oct. 2006"
    "docs/cd3wd/2012/agriculture/_ag_animal_feed_olive_byproducts_unfao_en_lp_103250_.pdf": "1985",   # "Rome, 1985 (c) FAO"
    "docs/cd3wd/2012/agriculture/_ag_fruit_conserve_2_fr_trp_unilo_lp_107630_.pdf": "1990",   # "(CTA - ILO - WEP, 1990, 244 p.)"
    "docs/cd3wd/2012/agriculture/_ag_fruit_conserve_fr_trp_unilo_lp_107650_.pdf": "1990",
    "docs/cd3wd/2012/agriculture/_ag_zootechie_insectes_2_fr_bedim_lp_118070_.pdf": "2003",   # "Publication 2003 date"
    "docs/cd3wd/2012/agriculture/_ag_vita_EnterpriseWorks_Harlan_HD_Attfield_Raising_chickens_and_ducks_2011_en_117880_.pdf": "1990",   # "Copyright (c) 1990 by Volunteers in Technical Assistance"
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_23_119940_.pdf": "1987",   # latest imprint "[el LENGUAJE C] 1987" (#143)
    "docs/cd3wd/2012/energy/_engy_425_Splitting_Firewood20_477_jf_en_130980_.pdf": "1981",   # "Copyright 1981", "MCMLXXXI"
    "docs/cd3wd/2012/wind_power/_wi_HPINDEX_1_88_jf2_en_155350_.pdf": "2002",   # "through May 2002"
    "docs/medical/hesperian_where_there_is_no_doctor/en_nwtnd_2017_9_eyechart_landscape.pdf": "2018",   # file date 10 Jan 2018 (a5 E-3)
    "docs/survivor_library/SurvivalLibrary/library/Engineering-Electrical/theoretical_and_practical_electrical_engineering_vol_1_1941.pdf": "1922",
    "docs/survivor_library/SurvivalLibrary/library/Engineering-Electrical/theoretical_and_practical_electrical_engineering_vol_2_1941.pdf": "1922",
    "docs/survivor_library/SurvivalLibrary/library/Horses/the_horse-trainers_and_sportsmans_guide_1868.pdf": "1865",   # "LONGMANS ... 1865"
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Whist/fosters_duplicate_whist_1894.pdf": "1891",   # "MCCLURG AND COMPANY. 1891"
})

YEAR_FIX.update({  # RT6 L5 follow-up (rt6_e10_judge.md, 2026-10-21): read off the pages (redteam_20261020_scripts/fix_l5_apply2.py:
    # J2 judge rows, S1 CODEL volumes, S2 empty y beside the document's own dateline, S3 volume years incl. 15 Badminton volumes)
    "docs/cd3wd/2012/agriculture/_ag_440_The_Backyard_Dairy_Book33_773_jf_en_102670_.pdf": "1975",
    "docs/cd3wd/2012/agriculture/_ag_KnO_100488_Food_Livelihood_and_Freshwater_Ecology_Bangladesh_pa_en_109460_.pdf": "1999",
    "docs/cd3wd/2012/agriculture/_ag_LGB_large_grain_borer_en_lp_109540_.pdf": "1996",
    "docs/cd3wd/2012/agriculture/_ag_Plough_construction_manual_ap_en_lp_114390_.pdf": "2002",
    "docs/cd3wd/2012/agriculture/_ag_armyworm_509_skat_dup_en_103650_.pdf": "2000",
    "docs/cd3wd/2012/agriculture/_ag_fp_KnO_100442_Drying_Vegetables_TB_pa_en_107200_.pdf": "2007",
    "docs/cd3wd/2012/agriculture/_ag_fp_ms_dairy_confectionary_pa_en_107450_.pdf": "2008",
    "docs/cd3wd/2012/agriculture/_ag_lgb_01_large_grain_borer_en_lp_109530_.pdf": "1996",
    "docs/cd3wd/2012/agriculture/_ag_mfkh_en_lp_Local_Food_Local_Currrency_Concept_lp_179590_.pdf": "2004",
    "docs/cd3wd/2012/agriculture/_ag_proc_fp_KnO_100186_butter_and_ghee_pa_en_115170_.pdf": "2008",
    "docs/cd3wd/2012/agriculture/_ag_proc_fp_KnO_100193_cheese_making_pa_en_115220_.pdf": "2008",
    "docs/cd3wd/2012/agriculture/_ag_proc_fp_KnO_100209_dairy_processing_pa_en_115350_.pdf": "2008",
    "docs/cd3wd/2012/agriculture/_ag_proc_fp_KnO_100268_oil_extraction_pa_en_115650_.pdf": "2008",
    "docs/cd3wd/2012/agriculture/_ag_proc_fp_KnO_100296_solar_drying_pa_en_115820_.pdf": "2007",
    "docs/cd3wd/2012/appropriate_technology/_at_chng_KnO_100229_food_processing_parcona_peru_pa_en_118810_.pdf": "2009",
    "docs/cd3wd/2012/appropriate_technology/_at_chng_KnO_100416_drip_uganda_pa_en_118860_.pdf": "2009",
    "docs/cd3wd/2012/appropriate_technology/_at_chng_herbal_products_nepal_pa_en_118750_.pdf": "2006",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_21_119920_.pdf": "1986",
    "docs/cd3wd/2012/biogas/_bg_sa_ms_biogas_pit_latrine_waste_pa_en_122470_.pdf": "2010",
    "docs/cd3wd/2012/communication/_cm_storytelling_pa_en_122780_.pdf": "2003",
    "docs/cd3wd/2012/computing/_it_java_prog_unu_3_m_en_134140_.pdf": "2005",
    "docs/cd3wd/2012/construction/_co_KnO_100064_school_buildings_in_developing_countries_pa_en_124910_.pdf": "2009",
    "docs/cd3wd/2012/construction/_co_ms_school_buildings_in_developing_countries_pa_en_125840_.pdf": "2009",
    "docs/cd3wd/2012/economics/_econ_math_stat_viet_Phan_tich_bien_sai_en_128150_.pdf": "2005",
    "docs/cd3wd/2012/energy/_engy_KnO_100161_producer_gas_power_generation_pa_en_131810_.pdf": "2008",
    "docs/cd3wd/2012/energy/_engy_KnO_100163_renewable_energy_climate_change_pa_en_131830_.pdf": "2007",
    "docs/cd3wd/2012/energy/_engy_KnO_100165_solar_pv_energy_pa_en_131850_.pdf": "2007",
    "docs/cd3wd/2012/energy/_engy_KnO_100168_solar_energy_a_reference_guide_pa_en_131870_.pdf": "2002",
    "docs/cd3wd/2012/energy/_engy_KnO_100169_solar_thermal_energy_pa_en_131880_.pdf": "2007",
    "docs/cd3wd/2012/environment/_ec_sa_ms_ecological_sanitation_pa_en_128060_.pdf": "2007",
    "docs/cd3wd/2012/health/_mc_ag_vet_Natural_remedies_chickens_rd_179850_.pdf": "2011",
    "docs/cd3wd/2012/health/_mc_family_planning_jhopkins_ocw_en_lp_137180_.pdf": "2005",
    "docs/cd3wd/2012/industry/_ind_ma_dwg_KnO_100357_soapmaking_pa_en_133000_.pdf": "2008",
    "docs/cd3wd/2012/industry/_ind_ms_evaporative_cooling_in_india_pa_en_133240_.pdf": "2007",
    "docs/cd3wd/2012/sanitation/_sa_ms_managing_organic_municipal_waste_pa_en_146050_.pdf": "2008",
    "docs/cd3wd/2012/sanitation/_sa_ms_reuse_faeces_urine_pa_en_146080_.pdf": "2007",
    "docs/cd3wd/2012/sanitation/_sa_ms_types_of_toilets_pa_en_146100_.pdf": "2008",
    "docs/cd3wd/2012/water/_wa_Aguasan_skat_en_150530_.pdf": "2004",
    "docs/cd3wd/2012/water/_wa_Collaborative_Working_Group_SWM_skat_en_150600_.pdf": "2004",
    "docs/cd3wd/2012/water/_wa_ms_KnO_100410_human_animal_water_lifters_pa_en_151190_.pdf": "2008",
    "docs/cd3wd/2012/water/_wa_ms_KnO_100411_human_powered_handpumps_pa_en_151200_.pdf": "2008",
    "docs/cd3wd/2012/water/_wa_ms_food_livelihood_and_freshwater_ecology_pa_en_151160_.pdf": "1999",
    "docs/cd3wd/2012/water/_wa_ms_water_treatment_systems_pa_en_151320_.pdf": "2010",
    "docs/cd3wd/2012/water/_wa_trolley_pump_weir_en_lp_152170_.pdf": "1979",
    "docs/cd3wd/2012/water/_wa_water_tank_plastic_tube_pumpkin_uww_en_lp_153530_.pdf": "2000",
    "docs/school_textbooks/college_open_textbooks/_mc_family_planning_jhopkins_ocw_en_lp_137180_.pdf": "2005",
    "docs/survivor_library/SurvivalLibrary/library/Canning/canning-principles.pdf": "1995",
    "docs/survivor_library/SurvivalLibrary/library/Canning/drying-fruits-and-vegetables.pdf": "2000",
    "docs/survivor_library/SurvivalLibrary/library/Canning/preparing-and-canning-fermented-food-and-pickled-vegetables-.pdf": "1995",
    "docs/survivor_library/SurvivalLibrary/library/Canning/usda-utah-can-guide-05.pdf": "1995",
    "docs/survivor_library/SurvivalLibrary/library/Cotton/cotton_1900.pdf": "",
    "docs/survivor_library/SurvivalLibrary/library/History-American/the_american_conflict-the_great_rebellion_vol_2-horace_greely_1867.pdf": "1866",
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Games and Sports/the_badminton_magazine_of_sports_and_pastimes_vol_02_1895.pdf": "1896",
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Games and Sports/the_badminton_magazine_of_sports_and_pastimes_vol_03_1895.pdf": "1896",
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Games and Sports/the_badminton_magazine_of_sports_and_pastimes_vol_04_1895.pdf": "1897",
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Games and Sports/the_badminton_magazine_of_sports_and_pastimes_vol_05_1895.pdf": "1897",
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Games and Sports/the_badminton_magazine_of_sports_and_pastimes_vol_06_1895.pdf": "1898",
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Games and Sports/the_badminton_magazine_of_sports_and_pastimes_vol_07_1895.pdf": "1898",
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Games and Sports/the_badminton_magazine_of_sports_and_pastimes_vol_08_1895.pdf": "1899",
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Games and Sports/the_badminton_magazine_of_sports_and_pastimes_vol_09_1895.pdf": "1899",
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Games and Sports/the_badminton_magazine_of_sports_and_pastimes_vol_10_1895.pdf": "1900",
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Games and Sports/the_badminton_magazine_of_sports_and_pastimes_vol_12_1895.pdf": "1901",
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Games and Sports/the_badminton_magazine_of_sports_and_pastimes_vol_13_1895.pdf": "1901",
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Games and Sports/the_badminton_magazine_of_sports_and_pastimes_vol_14_1895.pdf": "1902",
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Games and Sports/the_badminton_magazine_of_sports_and_pastimes_vol_15_1895.pdf": "1902",
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Games and Sports/the_badminton_magazine_of_sports_and_pastimes_vol_22_1895.pdf": "1906",
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Games and Sports/the_badminton_magazine_of_sports_and_pastimes_vol_24_1895.pdf": "1907",
    "docs/survivor_library/SurvivalLibrary/library/Medical-Diagnostics/clinical_diagnosis-a_manual_of_laboratory_methods_1919.pdf": "1914",
    "docs/survivor_library/SurvivalLibrary/library/Medical-Diagnostics/internal_medicine-diagnosis_and_treatment_vol_2_1920.pdf": "1908",
    "docs/survivor_library/SurvivalLibrary/library/Medical-Medicine 1900-1922/hand_book_of_modern_treatment_and_medical_formulary_1917.pdf": "1914",
    "docs/survivor_library/SurvivalLibrary/library/Medical-Microscopy/the_microscope-an_introduction_to_microscopic_methods_and_to_histology_1925.pdf": "1904",
    "docs/survivor_library/SurvivalLibrary/library/Medical-Nursing 1900-1921/the_principles_and_practice_of_bandaging_1911.pdf": "1902",
    "docs/survivor_library/SurvivalLibrary/library/Medical-Obstetrics 1900-1922/the_american_text_book_of_obstetrics_vol_2_1903.pdf": "1902",
    "docs/survivor_library/SurvivalLibrary/library/Medical-Surgery 1900-1922/a_text_book_of_surgery_1909.pdf": "1903",
    "docs/survivor_library/SurvivalLibrary/library/Optometry/refraction_of_the_human_eye_and_methods_of_estimating_the_refraction_1916.pdf": "1902",
    "docs/survivor_library/SurvivalLibrary/library/Smithing/practical_blacksmithing_volume_2_1891.pdf": "1889",
    "docs/survivor_library/SurvivalLibrary/library/Smithing/practical_sheet_metal_work_and_demonstrated_patterns_volume_3_1911.pdf": "1910",
    "docs/survivor_library/SurvivalLibrary/library/Smithing/practical_sheet_metal_work_and_demonstrated_patterns_volume_7_1912.pdf": "1911",
    "docs/survivor_library/SurvivalLibrary/library/Veterinary/notes_on_veterinary_materia_medica_1898.pdf": "1897",
    "docs/survivor_library/SurvivalLibrary/library/Wood-Carpentry/modern_carpentry-a_practical_manual_vol_2_1917.pdf": "1916",
    "docs/survivor_library/SurvivalLibrary/library/Wood-Carpentry/practical_treatise_on_the_steel_square_vol_2_1913.pdf": "1903",
})
YEAR_FIX.update({  # RT7 PF2 (E15 = B, 2026-10-23): read off the pages (redteam_20261023_scripts/pf2_apply.py; the quoted line
    # for each is in redteam_20261023_pf2_rows.json). Without this block a full --verify resets these 118 years to the rule value
    "docs/cd3wd/2012/agriculture/_ag_vita_ew_harlan_attfield_A_Tropical_Guide_to_Year_Round_Vegetable_Gardening_2011_en_117900_.pdf": "2001",
    "docs/cd3wd/2012/agriculture/_ag_vita_ew_harlan_attfield_Raising_Rabbits_and_Cavies_Guinea_Pigs_for_Meat_2011_en_117910_.pdf": "2001",
    "docs/cd3wd/2012/health/_mc_ms_405_First_aid_kit_for_small_workplaces_BTCV_UK_2003_jf_en_137890_.pdf": "2001",
    "docs/cd3wd/2012/industry/_ind_ms_405_Ropes_BTCV_UK_2003_jf_en_133180_.pdf": "2001",
    "docs/cd3wd/2012/health/_mc_minor_surgical_procedures_msf_en_lp_137820_.pdf": "1989",
    "docs/cd3wd/2012/health/_mc_herb_pharma_India_1890_Pharmacographia_indica_Vol_2_rd_180120_.pdf": "1891",
    "docs/sanitation/who_wedc_wash_emergencies_technical_notes_2013.pdf": "2011",
    "mirrors/hesperian/hesperian.org/wp-content/uploads/pdf/en_wwd_2008/en_WWD_2008_fm.pdf": "2007",
    "docs/survivor_library/SurvivalLibrary/library/First Aid/book_for_midwives_2011_full_book.pdf": "2010",
    "docs/survivor_library/SurvivalLibrary/library/Bookbinding/bookbinding_for_beginners_1924.pdf": "1914",
    "docs/survivor_library/SurvivalLibrary/library/Chemistry/colloid_chemistry_1924.pdf": "1919",
    "docs/survivor_library/SurvivalLibrary/library/Cookbooks/the_century_cookbook_1922.pdf": "1895",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/winstons_cumulative_loose_leaf_encyclopedia_vol_05_1918.pdf": "1915",
    "docs/survivor_library/SurvivalLibrary/library/Engineering-Electrical/electrical_energy_1908.pdf": "1907",
    "docs/survivor_library/SurvivalLibrary/library/Engineering-Hydraulics/hydraulic_tables_of_gagings_and_friction_of_water_flowing_in_pipes_1909.pdf": "1908",
    "docs/survivor_library/SurvivalLibrary/library/Forging and Casting/methods_of_chemical_analysis_and_foundry_chemistry_1904.pdf": "1901",
    "docs/survivor_library/SurvivalLibrary/library/Heavy and Industrial Machinery/pumping_machinery-a_treatise_on_history_design_construction_and_operation_1919.pdf": "1911",
    "docs/survivor_library/SurvivalLibrary/library/Livestock-Swine/a_treatise_on_swine-care_management_diseases_and_remedies_1885.pdf": "1884",
    "docs/survivor_library/SurvivalLibrary/library/Meteorology/elements_of_meteorology-brocklesby_1855.pdf": "1848",
    "docs/survivor_library/SurvivalLibrary/library/Primers/a_library_primer_1920.pdf": "1899",
    "docs/survivor_library/SurvivalLibrary/library/Primers/a_primer_of_spanish_literature_1879.pdf": "1878",
    "docs/survivor_library/SurvivalLibrary/library/Sanitation/handbook_on_sanitation_1913.pdf": "1908",
    "docs/survivor_library/SurvivalLibrary/library/Sanitation/practical_sanitation-a_handbook_for_practitioners_of_medicine_1917.pdf": "1915",
    "docs/survivor_library/SurvivalLibrary/library/Sanitation/primer_of_sanitation-disease_germs_and_how_to_fight_them_1915.pdf": "1909",
    "docs/survivor_library/SurvivalLibrary/library/Shorthand/complete_shorthand_manual_for_self-instruction_1902.pdf": "1898",
    "docs/survivor_library/SurvivalLibrary/library/Teaching-Arithmetic/ferrells_elementary_arithmetic_1903.pdf": "1901",
    "docs/survivor_library/SurvivalLibrary/library/Teaching-Readers/mcguffeys_5th_eclectic_reader-alternate_1896.pdf": "1888",
    "docs/survivor_library/SurvivalLibrary/library/Teaching-Readers/mcguffeys_5th_eclectic_reader_1896.pdf": "1879",
    "docs/survivor_library/SurvivalLibrary/library/Teaching/methods_in_education_1911.pdf": "1908",
    "docs/survivor_library/SurvivalLibrary/library/Boy Scout Manuals/camping_out_1872.pdf": "1873",
    "docs/survivor_library/SurvivalLibrary/library/Chemistry/a_textbook_of_chemistry_for_nurses_1923.pdf": "1919",
    "docs/survivor_library/SurvivalLibrary/library/Conduct of Life/christianity_in_the_daily_conduct_of_life_1889.pdf": "1888",
    "docs/survivor_library/SurvivalLibrary/library/Conduct of Life/plain_thoughts_on_the_art_of_living_1871.pdf": "1868",
    "docs/survivor_library/SurvivalLibrary/library/Cookbooks/the_new_buckeye_cook_book-a_careful_compilation_of_tried_and_approved_recipes_for_all_departments_of_the_household-1890.pdf": "1888",
    "docs/survivor_library/SurvivalLibrary/library/Cookbooks/the_boston_cooking-school_cook_book-1913.pdf": "1906",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/the_encyclopedia_americana_vol_04_1918.pdf": "1903",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/the_encyclopedia_americana_vol_11_1918.pdf": "1904",
    "docs/survivor_library/SurvivalLibrary/library/Engineering-General/a_treatise_on_hydraulic_and_water_supply_engineering_1886.pdf": "1877",
    "docs/survivor_library/SurvivalLibrary/library/Farming/the_nursery_book-a_complete_guide_to_the_multiplication_and_pollination_of_plants-1892.pdf": "1891",
    "docs/survivor_library/SurvivalLibrary/library/Forging and Casting/machinery_pattern_making_1892.pdf": "1891",
    "docs/survivor_library/SurvivalLibrary/library/Heavy and Industrial Machinery/cotton_spinning-construction_operation_and_care_of_spinning_machinery_1909.pdf": "1908",
    "docs/survivor_library/SurvivalLibrary/library/Heavy and Industrial Machinery/hydraulic_engineering-a_treatise_on_water_pressure_1909.pdf": "1908",
    "docs/survivor_library/SurvivalLibrary/library/History-American/american_history-perry_1919.pdf": "1914",
    "docs/survivor_library/SurvivalLibrary/library/Home Economics/a_domestic_cyclopedia_of_practical_information_1878.pdf": "1877",
    "docs/survivor_library/SurvivalLibrary/library/Home Economics/confessions_of_a_housekeeper_1852.pdf": "1851",
    "docs/survivor_library/SurvivalLibrary/library/Home Economics/domestic_science_principles_and_application_1921.pdf": "1918",
    "docs/survivor_library/SurvivalLibrary/library/Horses/the_exterior_of_the_horse_1904.pdf": "1892",
    "docs/survivor_library/SurvivalLibrary/library/Leisure-Whist/the_theory_of_the_modern_scientific_game_of_whist_1879.pdf": "1880",
    "docs/survivor_library/SurvivalLibrary/library/Mechanical Drawing/elements_of_mechanical_drawing-jamison_1911.pdf": "1904",
    "docs/survivor_library/SurvivalLibrary/library/Musical Instruments/creative_music_for_children_1922.pdf": "1923",
    "docs/survivor_library/SurvivalLibrary/library/Musical Instruments/musical_instruments_1876.pdf": "1908",
    "docs/survivor_library/SurvivalLibrary/library/Musical Instruments/orchestral_instruments_and_their_use_1903.pdf": "1902",
    "docs/survivor_library/SurvivalLibrary/library/Primers/childs_health_primer_for_primary_classes_1886.pdf": "1885",
    "docs/survivor_library/SurvivalLibrary/library/Printing/gutenberg_and_the_art_of_printing_1871.pdf": "1870",
    "docs/survivor_library/SurvivalLibrary/library/Refrigeration/audels_answers_on_refrigeration_and_ice_making_1914.pdf": "1911",
    "docs/survivor_library/SurvivalLibrary/library/Shipbuilding/pugsleys_new_guide_1915.pdf": "1912",
    "docs/survivor_library/SurvivalLibrary/library/Shoemaking/from_the_forest_to_the_foot_1893.pdf": "1890",
    "docs/survivor_library/SurvivalLibrary/library/Shorthand/the_analogical_phonetic_syllabic_dictionary_1893.pdf": "1891",
    "docs/survivor_library/SurvivalLibrary/library/Smithing/a_practical_workshop_companion_for_tin_1865.pdf": "1864",
    "docs/survivor_library/SurvivalLibrary/library/Smithing/triangulation_applied_to_sheet_metal_pattern_cutting_1924.pdf": "1917",
    "docs/survivor_library/SurvivalLibrary/library/Steam Engines/the_practical_application_of_the_slide_valve_to_portable_locomotive_and_marine_engines_1897.pdf": "1895",
    "docs/survivor_library/SurvivalLibrary/library/Surveying/a_manual_of_underground_surveying_1910.pdf": "1908",
    "docs/survivor_library/SurvivalLibrary/library/Teaching-Civics/society_and_politics_in_ancient_rome1963.pdf": "1909",
    "docs/survivor_library/SurvivalLibrary/library/Teaching/manual_of_object_teaching_1882.pdf": "1881",
    "docs/survivor_library/SurvivalLibrary/library/Teaching/masterpieces_of_american_eloquence_1890.pdf": "1884",
    "docs/survivor_library/SurvivalLibrary/library/Teaching/the_english_language-its_grammar_history_and_literature_1920.pdf": "1906",
    "docs/survivor_library/SurvivalLibrary/library/Teaching/the_teaching_of_latin_and_greek_in_the_secondary_school_1911.pdf": "1899",
    "docs/survivor_library/SurvivalLibrary/library/Telegraph and Telephone/american_telegraphy_and_encyclopedia_of_the_telegraph_1909.pdf": "1908",
    "docs/survivor_library/SurvivalLibrary/library/Telegraph and Telephone/the_age_of_electricity_from_amber_soul_to_telephone_1901.pdf": "1886",
    "docs/survivor_library/SurvivalLibrary/library/Trapping and Hunting/life_in_the_back-woods-a_guide_to_hunting_and_trapping_of_all_kinds_of_animals_1875.pdf": "1874",
    "docs/survivor_library/SurvivalLibrary/library/Wagon and Coach Building/the_new_york_coach-makers_magazine_vol_7_1858.pdf": "1866",
    "docs/survivor_library/SurvivalLibrary/library/Livestock-Rabbits and Cavies/standard_of_perfection_for_cavies_1922.pdf": "1923",
    "docs/survivor_library/SurvivalLibrary/library/Medical-Medicine 1900-1922/the_diagnostics_on_internal_medicine_1922.pdf": "1909",
    "docs/survivor_library/SurvivalLibrary/library/Primers/the_howell_primer_1912.pdf": "1910",
    "docs/survivor_library/SurvivalLibrary/library/Botany/a_textbook_of_botany_for_colleges_1920.pdf": "1917",
    "docs/survivor_library/SurvivalLibrary/library/Coal and Mining/modern_practice_in_mining_vol_3-working_coal_1908.pdf": "1914",
    "docs/survivor_library/SurvivalLibrary/library/Coal and Mining/the_mechanical_engineering_of_collieries_vol_2_1909.pdf": "1910",
    "docs/survivor_library/SurvivalLibrary/library/Economics/an_inquiry_into_the_nature_and_causes_of_the_wealth_of_nations_vol_1-adam_smith_1901.pdf": "1887",
    "docs/survivor_library/SurvivalLibrary/library/Economics/the_relations_of_rents_wages_and_profits_in_agriculture_1906.pdf": "1906",
    "docs/survivor_library/SurvivalLibrary/library/Engineering-Electrical/alternating_current_electricity_and_its_applications_to_industry_vol_2_1914.pdf": "1916",
    "docs/survivor_library/SurvivalLibrary/library/Engineering-Electrical/electricity_as_applied_to_mining_1903.pdf": "1906",
    "docs/survivor_library/SurvivalLibrary/library/Engineering-Electrical/telegraph_engineering-a_manual_for_telegraph_engineers_snd_engineering_students_1915.pdf": "1922",
    "docs/survivor_library/SurvivalLibrary/library/Engineering-General/a_compendium_of_mechanics_1830.pdf": "1828",
    "docs/survivor_library/SurvivalLibrary/library/Herbalism/annual_report_on_essential_oils_aromatic_chemicals_1890.pdf": "1907",
    "docs/survivor_library/SurvivalLibrary/library/Knitting-Lace-Needlepoint/a_treatise_on_lace_making_embroidery_and_needle_work_vol_7_1892.pdf": "1900",
    "docs/survivor_library/SurvivalLibrary/library/Medical-Medicine 1900-1922/a_text_book_bacteriology_1910.pdf": "1918",
    "docs/survivor_library/SurvivalLibrary/library/Medical-Medicine 1900-1922/medicines-their_uses_and_mode_of_administration_1844.pdf": "1864",
    "docs/survivor_library/SurvivalLibrary/library/Steam Engines/treatise_on_valve-gears_of_locomotive_engines_1884.pdf": "1869",
    "docs/survivor_library/SurvivalLibrary/library/Teaching/education_as_a_science_1897.pdf": "1898",
    "docs/survivor_library/SurvivalLibrary/library/Telegraph and Telephone/design_construction_and_operation_of_telephone_exchanges_vol_6_switchboards_1903.pdf": "1905",
    "docs/survivor_library/SurvivalLibrary/library/Teaching-Arithmetic/elementary_arithmetic_for_graded_and_ungraded_schools_1908.pdf": "1909",
    "docs/survivor_library/SurvivalLibrary/library/Coal and Mining/coal_and_coal-mining_1869.pdf": "1913",
    "docs/survivor_library/SurvivalLibrary/library/Medical-Obstetrics 1900-1922/american_association_of_obstetricians_vol_17_1905.pdf": "1896",
    "docs/survivor_library/SurvivalLibrary/library/Economics/the_development_of_economics_1921.pdf": "1921",
    "docs/cd3wd/2012/agriculture/_ag_mfkh_en_notill_organic_hort_purdue_newcrop_squashflowers_172330_.pdf": "2005",
    "docs/cd3wd/2012/agriculture/_ag_417_Appropriate_Industrial_Technology_for_Agricultural_Machinery_and_Implements06_237_jf_en_101690_.pdf": "1979",
    "docs/cd3wd/2012/transport/_tr_435_Appropriate_Industrial_Technology_for_LowCost_Transport_for_Rural_Areas26_650_jf_en_148580_.pdf": "1979",
    "docs/cd3wd/2012/transport/_tr_435_Boats_from_Ferrocement26_658_jf_en_148650_.pdf": "1972",
    "docs/cd3wd/2012/transport/_tr_435_The_Manufacture_of_LowCost_Vehicles_in_Developing_Countries26_665_jf_en_148890_.pdf": "1978",
    "docs/cd3wd/2012/agriculture/_ag_lstock_Basic_Beekeeping_en_109780_.pdf": "1996",
    "docs/cd3wd/2012/agriculture/_ag_lstock_Beef_en_109800_.pdf": "1998",
    "docs/cd3wd/2012/agriculture/_ag_lstock_Congo_fever_en_109920_.pdf": "1998",
    "docs/cd3wd/2012/agriculture/_ag_lstock_JohnesDisease_en_111200_.pdf": "1997",
    "docs/cd3wd/2012/agriculture/_ag_lstock_Muscovy_ducks_en_111360_.pdf": "1996",
    "docs/cd3wd/2012/agriculture/_ag_lstock_collect_rainwater_from_your_roof_en_109910_.pdf": "1997",
    "docs/cd3wd/2012/agriculture/_ag_lstock_export_of_fresh_meat_en_110330_.pdf": "1997",
    "docs/cd3wd/2012/agriculture/_ag_lstock_import_requirements_for_fresh_meat_en_111190_.pdf": "1997",
    "docs/cd3wd/2012/agriculture/_ag_lstock_nitrogen_fertiliser_en_111400_.pdf": "1998",
    "docs/cd3wd/2012/construction/_co_433_SelfHelp_Practices_in_Housing25_633_jf_en_123200_.pdf": "1973",
    "docs/cd3wd/2012/construction/_co_434_Building_with_Earth25_673_jf_en_123260_.pdf": "1986",
    "docs/cd3wd/2012/construction/_co_434_Thatching25_674_jf_en_123430_.pdf": "1988",
    "docs/cd3wd/2012/energy/_engy_425_Modern_Stoves_for_All20_453_jf_en_130950_.pdf": "1985",
    "docs/cd3wd/2012/construction/_co_433_Chawama_SelfHelp_Housing_Project25_589_jf_en_123030_.pdf": "1975",
    "docs/cd3wd/2012/agriculture/_ag_fp_405_VITA_How_to_Salt_Fish07_288_jf_en_107170_.pdf": "1966",
    "docs/cd3wd/2012/agriculture/_ag_407_Drying_Equip_Cereal_Grains_07_265_jf_en_100810_.pdf": "1977",
    "docs/survivor_library/SurvivalLibrary/library/Food/useful-wild-plants-of-the-united-states-and-canada.pdf": "1920",
    "docs/cd3wd/2012/manufacturing/_ma_407_PA_dwg_Cooperative_Organization30_736_jf_en_135340_.pdf": "1975",
    "docs/cd3wd/2012/energy/_engy_energy_misc_stobart_en_lp_131440_.pdf": "2004",
})
YEAR_FIX.update({  # RT7 M4 (#233, 2026-10-24): read off the title and copyright pages (redteam_20261023_scripts/fix_m4_apply.py;
    # the line used for each is in redteam_20261023_fix_m4.md). A reprint keeps its original year; "" = no year printed
    "docs/cd3wd/2012/agriculture/_ag_fo_wood_harvest_hand_tools_unilo_en_lp_106970_.pdf": "1987",
    "docs/cd3wd/2012/agriculture/_ag_improve_tropical_range_bostid_en_lp_108810_.pdf": "1990",
    "docs/cd3wd/2012/electricity/_el_406_Alternator_Secrets_jf_en_126830_.pdf": "1977",
    "docs/cd3wd/2012/health/_mc_437_The_Tooth_Trip27_713_jf_en_136640_.pdf": "1972",
    "docs/cd3wd/2012/health/_mc_primary_health_16_female_health_es_lp_138240_.pdf": "1997",
    "docs/cd3wd/2012/health/_mc_primary_health_9_emergencies_es_lp_138360_.pdf": "1997",
    "docs/cd3wd/2012/solar/_sl_408_Solar_Grain_Drying_Systems07_275_jf_en_147190_.pdf": "1978",
    "docs/cd3wd/2012/solar/_sl_431_The_Solar_Cookery_Book23_550_jf_en_147370_.pdf": "1978",
    "docs/comms/cisa_nifog_v2_02_2024.pdf": "2025",
    "docs/homesteading_extension/uga_goat_production.pdf": "2017",
    "docs/medical/hesperian_where_there_is_no_doctor/Child_growth_chart_nwtnd.pdf": "",
    "docs/medical/hesperian_where_there_is_no_doctor/NWTND_Development_Charts.pdf": "",
    "docs/school_textbooks/college_open_textbooks/Dyslexia_reading_problems_.pdf": "1992",
    "docs/survivor_library/SurvivalLibrary/library/Dentistry/a_childs_book_of_the_teeth_1918_1924.pdf": "1918",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/the_catholic_encyclopedia_vol_04_1913.pdf": "1908",
    "docs/survivor_library/SurvivalLibrary/library/Firearms Manuals/anschutz_1907_1912_1913.pdf": "2002",
    "docs/survivor_library/SurvivalLibrary/library/Firearms Manuals/colt_m1911_m1911a1.pdf": "",
    "docs/survivor_library/SurvivalLibrary/library/Firearms Manuals/izh_94-2_over_and_under_shotgun-rifle.pdf": "2003",
    "docs/survivor_library/SurvivalLibrary/library/Firearms Manuals/liberator_pistol_blueprints.pdf": "1996",
    "docs/survivor_library/SurvivalLibrary/library/Meteorology/meteorology-a_text-book_on_the_weather_1918.pdf": "1912",
    "mirrors/ready_gov/www.ready.gov/sites/default/files/2020-07/wea-for-kids.pdf": "2016",
    "mirrors/ready_gov/www.ready.gov/sites/default/files/2024-08/ready-gov_wildfire_info-sheet_korean.pdf": "2018",
})

YEAR_FIX.update({  # RT8 M4 (#243, 2026-10-25): read off the title and copyright pages (redteam_20261025_scripts/fix_m4_apply.py;
    # the line used for each is in redteam_20261025_fix_m4.md). A reprint keeps its original year; "" = no year of this text printed
    "docs/cd3wd/2012/agriculture/_ag_415_The_Nursery_Manual05_245_jf_en_101420_.pdf": "1919",
    "docs/cd3wd/2012/agriculture/_ag_417_Cereal_Processing06_299_jf_en_101700_.pdf": "1988",
    "docs/cd3wd/2012/agriculture/_ag_chicken_respiratory_disease_rsa_en_lp_105160_.pdf": "2001",
    "docs/cd3wd/2012/agriculture/_ag_frst_ms_406_Forestry_tools_safety_proceedures_ILO_jf_en_107600_.pdf": "1987",
    "docs/cd3wd/2012/agriculture/_ag_mfkh_en_lp_cupidandpsyche_fruits_vegs_171330_.pdf": "",
    "docs/cd3wd/2012/agriculture/_ag_postharvest_inpho_009_en_lp_114890_.pdf": "",
    "docs/cd3wd/2012/appropriate_technology/_at_411_Technologies_for_Basic_Needs03_78_jf_en_118600_.pdf": "1977",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_39_120100_.pdf": "1980",
    "docs/cd3wd/2012/education/_ed_textbook_authoring_h4255e_en_127570_.pdf": "1996",
    "docs/cd3wd/2012/energy/_engy_405_Using_a_producer_gas_generator_to_create_electricity_By_Gen_jf_en_130600_.pdf": "",
    "docs/cd3wd/2012/energy/_engy_ms_405_Is_methane_production_on_your_homestead_practical_By_Jim_Tr_jf_en_132020_.pdf": "",
    "docs/cd3wd/2012/health/_mc_437_Medicine_and_Public_Health_in_the_Peoples_Republic_of_China27_697_jf_en_136570_.pdf": "1973",
    "docs/cd3wd/2012/health/_mc_primary_health_14_environmental_health_es_lp_138220_.pdf": "1997",
    "docs/cd3wd/2012/small_business/_ms_405_Bell_alarms_sack_hoists_Disk_07_06_238_jf_en_142900_.pdf": "1972",
    "docs/cd3wd/2012/small_business/_ms_405_HERRE_jf_en_143640_.pdf": "",
    "docs/cd3wd/2012/small_business/_ms_405_Selecting_the_right_heating_system_By_Martin_S_Haris_jf_en_144490_.pdf": "",
    "docs/cd3wd/2012/solar/_sl_405_Sun_Times_jf_en_146980_.pdf": "",
    "docs/cd3wd/2012/transport/_tr_KnO_100389_pack_transport_donkeys_pa_en_149110_.pdf": "",
    "docs/cd3wd/2012/water/_wa_405_How_to_build_a_safe_effective_wood_fired_hot_water_heater_jf_en_149540_.pdf": "",
    "docs/cd3wd/2012/water/_wa_405_Water_pump_blues_Condider_the_trusty_ram_pump_By_Don_R_Wil_jf_en_149810_.pdf": "",
    "docs/cd3wd/2012/water/_wa_pump_inertia_hand_pump_vita_en_lp_151500_.pdf": "",
    "docs/cd3wd/2012/wind_power/_wi_405_Bell_Alarms_and_Sack_Hoists_in_Windmills06_238_jf_en_153980_.pdf": "1972",
    "docs/cd3wd/2012/wind_power/_wi_405_Kopi_af_Windmills_Millwrighting_Drawings_jf_en_154200_.pdf": "",
    "docs/cd3wd/2012/wind_power/_wi_405_Windmills_Millwrighting_Drawings_jf_en_154670_.pdf": "",
    "docs/school_textbooks/siyavula_grades_4_9/_ac_econ_economic_mgt_science_grd_7_m4_ECONOMIC_POLICY_DIRECTION_siya_205960_.pdf": "",
    "docs/survivor_library/SurvivalLibrary/library/Printing/sketches_of_printers_and_printing_in_colonial_new_york_1969.pdf": "1895",
    "docs/survivor_library/SurvivalLibrary/library/Survival-Individual/american-boys-book-of-camp-lore-and-woodcraft.pdf": "1920",
    "docs/survivor_library/SurvivalLibrary/library/Survival-Individual/canadian-military-fieldcraft.pdf": "2001",
    "docs/survivor_library/SurvivalLibrary/library/Wagon and Coach Building/the_new_york_coach-makers_magazine_vol_10_1858.pdf": "1869",
    "docs/survivor_library/SurvivalLibrary/library/Wagon and Coach Building/the_new_york_coach-makers_magazine_vol_9_1858.pdf": "1867",
    "docs/textiles/purdue_4h_sew_much_fun.pdf": "2001",
    "mirrors/hesperian/hesperian.org/wp-content/uploads/pdf/ru_dvc_2022/ru_dvc_2022_fm.pdf": "2021",
})

YEAR_FIX.update({  # RT9 M4 (#255, 2026-10-26): read off the title and copyright pages (redteam_20261026_scripts/fix_m4_apply.py;
    # the line used for each is in its comments and redteam_20261026_fix_m4.md). "" = no year of this text printed; the two
    # loose NWTND charts print none and carry their 2011 file date (t9_catalog hand rows)
    "docs/cd3wd/2012/agriculture/_ag_animal_importance_rsa_en_lp_103320_.pdf": "2001",
    "docs/cd3wd/2012/agriculture/_ag_lstock_Subtropical_en_112000_.pdf": "2003",
    "docs/cd3wd/2012/auto_mechanics/_au_406_Battery_repair_jf_en_120860_.pdf": "1971",
    "docs/cd3wd/2012/construction/_co_434_The_Use_of_Bamboo_and_Reeds_in_Building_Construction25_645_jf_en_123450_.pdf": "1972",
    "docs/cd3wd/2012/health/_mc_primary_health_16_teenage_health_es_lp_138250_.pdf": "1997",
    "docs/cd3wd/2012/industry/_ind_ms_recycling_rubber_pa_en_133280_.pdf": "",
    "docs/cd3wd/2012/manufacturing/_ma_dwg_KnO_100353_oil_soaked_wood_bearing_pa_en_135960_.pdf": "",
    "docs/cd3wd/2012/micro_hydro/_mh_franjic_mhyg_en_142160_.pdf": "1994",
    "docs/cd3wd/2012/stoves/_st_405_New_Nepali_Cooking_Stoves20_454_jf_en_148240_.pdf": "1982",
    "docs/homesteading_extension/osu_seed_saving.pdf": "2023",
    "docs/medical/hesperian_where_there_is_no_doctor/Child_growth_chart_nwtnd.pdf": "2011",
    "docs/medical/hesperian_where_there_is_no_doctor/NWTND_Development_Charts.pdf": "2011",
    "docs/sanitation/sfpuc_graywater_design_manual.pdf": "2017",
    "docs/survivor_library/SurvivalLibrary/library/Airships/principle_of_the_boerner_airship_1905.pdf": "1922",
    "docs/survivor_library/SurvivalLibrary/library/Chemistry/chemistry_inorganic_with_experiments_1923.pdf": "1870",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/encyclopedia_britannica_11_ed_vol_01_1911.pdf": "1910",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/encyclopedia_britannica_11_ed_vol_02_1911.pdf": "1910",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/encyclopedia_britannica_11_ed_vol_03_1911.pdf": "1910",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/encyclopedia_britannica_11_ed_vol_04_1911.pdf": "1910",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/encyclopedia_britannica_11_ed_vol_05_1911.pdf": "1910",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/encyclopedia_britannica_11_ed_vol_06_1911.pdf": "1910",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/encyclopedia_britannica_11_ed_vol_08_1911.pdf": "1910",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/encyclopedia_britannica_11_ed_vol_09_1911.pdf": "1910",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/encyclopedia_britannica_11_ed_vol_10_1911.pdf": "1910",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/encyclopedia_britannica_11_ed_vol_11_1911.pdf": "1910",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/encyclopedia_britannica_11_ed_vol_12_1911.pdf": "1910",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/encyclopedia_britannica_11_ed_vol_13_1911.pdf": "1910",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/encyclopedia_britannica_11_ed_vol_14_1911.pdf": "1910",
    "docs/survivor_library/SurvivalLibrary/library/Engineering-Drainage/why_tile_drainage_benefits_wet_land_and_increases_farm_income_1946.pdf": "1971",
    "docs/survivor_library/SurvivalLibrary/library/Farming/domestic_animals_1959.pdf": "1859",
    "docs/survivor_library/SurvivalLibrary/library/Firearms Manuals/m1911_blueprints_scans.pdf": "1942",
    "docs/survivor_library/SurvivalLibrary/library/Firearms Manuals/schweizerische_armee_model1878_revolver.pdf": "1879",
    "docs/survivor_library/SurvivalLibrary/library/Medical-Obstetrics 1900-1922/american_association_of_obstetricians_vol_15_1903.pdf": "1903",
    "docs/survivor_library/SurvivalLibrary/library/Teaching-Civics/the_politics_of_aristotle_volume_1_1958.pdf": "1885",
    "mirrors/ready_gov/www.ready.gov/sites/default/files/2024-08/ready-gov_volcano_info-sheet_korean.pdf": "2018",
})

YEAR_FIX.update({  # RT10 M4 (#276, #143, #267, 2026-10-27): read off the title and copyright pages (redteam_20261027_scripts/fix_m4_apply.py;
    # the line used for each is in its comments and fix_m4_evid.tsv). "" = no year of this text printed. The VITA bundles carry
    # their latest imprint (the r39 VITA_C rule; es_lp_39 replaces the RT8 hand year); the Humanure 4th-edition parts carry
    # the 2022 printing (Contents_HH4) and Rumsey the 1788 roman imprint (t9_catalog hand rows)
    "docs/cd3wd/2012/agriculture/_ag_mfkh_en_lp_Ag_2_Free_weed_control_mice_lp_178380_.pdf": "2006",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_10_119810_.pdf": "1989",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_15_119860_.pdf": "1990",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_16_119870_.pdf": "1990",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_29_120000_.pdf": "1985",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_31_120020_.pdf": "1991",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_32_120030_.pdf": "1989",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_33_120040_.pdf": "1977",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_37_120080_.pdf": "1990",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_38_120090_.pdf": "1985",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_39_120100_.pdf": "1990",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_41_120120_.pdf": "1988",   # latest imprint "[el LENGUAJE C] 1988" (RT4 J3 read 1984)
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_43_120140_.pdf": "1990",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_44_120150_.pdf": "1980",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_fr_lp_38_120430_.pdf": "1990",
    "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_po_lp_14_120540_.pdf": "1987",
    "docs/cd3wd/2012/communication/_cm_439_The_Copy_Book31_769_jf_en_122600_.pdf": "1988",
    "docs/cd3wd/2012/construction/_co_ms_405_Economic_Issues_in_Housing_Reconstruction35_814_jf_en_125330_.pdf": "1981",
    "docs/cd3wd/2012/energy/_eg_ag_at_vita_vth_charcoal_charbon_fr_lp_16_120216_.pdf": "1984",
    "docs/cd3wd/2012/environment/_ec_Green_tuning_ap_en_lp_127950_.pdf": "2010",
    "docs/cd3wd/2012/environment/_ec_eco_projects_planning_implementation_gtz_sp_en_127670_.pdf": "1997",
    "docs/cd3wd/2012/health/_mc_Heart_stents_ap_en_lp_137450_.pdf": "2010",
    "docs/cd3wd/2012/health/_mc_ms_KnO_100420_SODIS_pa_en_137930_.pdf": "",
    "docs/cd3wd/2012/health/_mc_nutr_09305_Botulism_rd_180550_.pdf": "2006",
    "docs/cd3wd/2012/health/_mc_primary_health_10_medicinal_plants_es_lp_138180_.pdf": "1997",
    "docs/cd3wd/2012/health/_mc_where_there_is_no_dentist_hesperian_en_lp_138770_.pdf": "1983",
    "docs/cd3wd/2012/micro_hydro/_mh_422_Water_Current_Turbines14_375_jf_en_141690_.pdf": "1986",
    "docs/cd3wd/2012/micro_hydro/_mh_In_the_event_that_the_Vendors_Airtr_mhyg_en_142240_.pdf": "",
    "docs/cd3wd/2012/small_business/_ms_405_RSVP_jf_en_144440_.pdf": "1998",
    "docs/cd3wd/2012/solar/_sl_408_TPI_A_Hand_Operated_Bar_Mill_for_Decorticating_Sunflower_Seed06_282_jf_en_147200_.pdf": "1981",
    "docs/homesteading_extension/psu_home_apple_production.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Ch_01_Close_Encounters.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Ch_02_Invisible_Beings.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Ch_03_Microbes_Friend_or_Foe.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Ch_04_War_on_Microbes.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Ch_05_Thermophiles.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Ch_06_Deep_Shit.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Ch_07_Day_in_Life.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Ch_08_Compost_Misunderstood.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Ch_09_Compost_Nuts_and_Bolts.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Ch_10_Compost_Miracles.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Ch_11_Compost_Myths.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Ch_12_Compost_Toilets.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Ch_13_Worms_and_Disease.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Ch_14_Tao_Compost.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Ch_15_Rear_End.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Glossary.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/HH4_Index.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Loo_Construction_plans.pdf": "2022",
    "docs/sanitation/humanure_4th_ed/Notes.pdf": "2022",
    "docs/school_textbooks/high_school/_ed_sch_chem_chemistry_101_unibots_bw_course_889pps_lp_170900_.pdf": "2008",
    "docs/survivor_library/SurvivalLibrary/library/Encyclopedias/the_encyclopedia_americana_vol_22_1918.pdf": "1919",
    "docs/survivor_library/SurvivalLibrary/library/Engineering-Electrical/direct_and_alternating_current_manual_1911.pdf": "1928",
    "docs/survivor_library/SurvivalLibrary/library/Firearms Manuals/springfield_rifle_m1903_a1_a2_a3_a4_ww.pdf": "",
    "docs/survivor_library/SurvivalLibrary/library/Fish Culture/artificial_propagation_of_the_black_basses_1907.pdf": "1900",
    "docs/survivor_library/SurvivalLibrary/library/Heating/national_stoves_and_ranges-catalogue_number_49_1947.pdf": "1940",
    "docs/survivor_library/SurvivalLibrary/library/Livestock-Swine/scientific_line_breeding_of_big_type_polands_1919.pdf": "",
    "docs/survivor_library/SurvivalLibrary/library/Medical-Microscopy/hand_microtome-a_modification.pdf": "1918",
    "docs/survivor_library/SurvivalLibrary/library/Shipbuilding/a_short_treatise_on_the_application_of_steam_1785-rumsey.pdf": "1788",
    "mirrors/hesperian/hesperian.org/wp-content/uploads/pdf/prs_wwd_2024/prs_wwd_2024_fm.pdf": "2021",
    "mirrors/ready_gov/www.ready.gov/sites/default/files/2020-04/emergency-management-considerations_chapter-4.pdf": "",
    "mirrors/ready_gov/www.ready.gov/sites/default/files/2020-04/step-overview.pdf": "",
    "mirrors/ready_gov/www.ready.gov/sites/default/files/2025-02/fema_cert_ttt-teen-cert-annex-instructor-guide.pdf": "2012",
})

# #138: one-liners the model gets wrong from what the excerpt shows, read by hand (r21 judge C) and set by --verify
S_FIX = {
    # #285 C1: every sentence of this entry held a digit ("pre-1972 MAC 10", "$10,000 fine and 10 years"), so C1 left it
    # (s and a) with no law line (t9 legal, RT4 #195); it gets the US law line its sibling conversion manuals carry (RT4 J3 MG,
    # redteam_20261013 fix_j3_apply.py), verbatim
    "docs/survivor_library/SurvivalLibrary/library/Firearms Manuals/full-auto_conversion-ingram_mac-10_pistol.pdf":
        "In the United States only licensed manufacturers and government agencies may make a machine gun; "
        "for anyone else it is a federal felony.",
    "docs/school_textbooks/college_open_textbooks/chess_english_chess_problems_170910_.pdf":   # "69" = the unsound ones
        "Several hundred English chess problems from the 1876 collection by Pierce, arranged by number of moves, with solutions.",
    "docs/cd3wd/2012/agriculture/_ag_lstock_rabbits_fr_111500_.pdf":   # the excerpt is the contents page; "intensif" = annex 1
        "Guide Agrodok sur l'élevage du lapin en basse-cour sous les tropiques : races, cages, alimentation, reproduction et maladies.",
    # #141 (r22 judge A): a 1921 school Christmas play script (cast, costumes, "Time of Playing", CURTAIN); the model
    # read the plot as the reader's own Christmas
    "docs/survivor_library/SurvivalLibrary/library/Christmas/snowbound_for_christmas_1921.pdf":
        "A two-act Christmas play script from 1921 in which a snowed-in farm family makes its own presents when it cannot get to town.",
    # #158 (red team 10-09 b1judge3 #171): the old one-liner said bodies are handled "to prevent disease", the myth
    # the manual exists to debunk ("Dead bodies in general do not cause epidemics after disasters")
    # RT4 J3 (#195, b1judge3): qualified; the manual has an infectious-disease chapter and an epidemic annex
    "docs/death_care/paho_who_icrc_dead_bodies_field_manual_2016.pdf":
        "Field manual on recovering, identifying and burying the dead after disasters; bodies generally do not cause epidemics, except deaths from Ebola, cholera or similar diseases.",
}
# #141: two-sentence answers read by hand, set by --verify like S_FIX (each must pass every `a` rule: selftest)
A_FIX = {
    "docs/survivor_library/SurvivalLibrary/library/Christmas/snowbound_for_christmas_1921.pdf":
        "The document covers staging a two-act Christmas play about a snowed-in farm family making its own presents, with a "
        "cast of eight, costumes, stage directions and a playing time of about twenty-five minutes. It is for schoolteachers "
        "or community groups staging a short Christmas play.",
    # #158 (F6): three regenerations in a row closed with "as described in the excerpt"; written from the 1903 contents
    "docs/survivor_library/SurvivalLibrary/library/Beekeeping/the_abc_of_bee_culture_1903.pdf":
        "The document covers hive management, bee biology, swarming, queen rearing and honey production as practised in 1903. "
        "Beekeepers keeping bees in movable-frame hives would open it when setting up or working an apiary.",
}
# #143 (r22 judge F4): a VITA compilation's year is its latest paper's imprint ("[C]1988, Volontaires dans Assistance
# Technique," under each paper's ISBN, anywhere in the file), not the first paper's
# RT10 M4 (#143 regressed, b5 W9): the imprint also prints "(C) 1990" and "© 1984"; and the year rule covers every VITA
# bulletin file (b5's 105, `_at_vita_vth_..._lp_N_`, the charcoal and es_lp_39 bundles included), not only the papers()
# compilations: the latest imprint in the file is the file's year
# the Spanish machine translation prints "[C]" as "[el LENGUAJE C] 1986" (28 es bundles)
# ("(C)" upper-case only: a list item "(c) the pump, 1990" is not an imprint)
VITA_C = re.compile(r"(?:\[(?:c|sup\.c)\]|(?-i:\(C\))|©|\[(?:el )?lenguaje c\])[^\d\f\n]{0,40}?" + YR, re.I)
VITA_FILE = re.compile(r"_at_vita_vth_.*_lp_\d+_")

def _line(t, i):
    ends = [j for j in (t.find("\n", i), t.find("\f", i)) if j >= 0]
    return t[max(t.rfind("\n", 0, i), t.rfind("\f", 0, i)) + 1:min(ends, default=len(t))]

def _addr(t, i):
    """True when the 4-digit number at t[i:i+4] sits in address/catalogue context (Box 1692, 1600 Wilson Boulevard)."""
    pre = t[max(0, i - 80):i].rsplit("\n", 1)[-1].split()[-1:]  # same line only; 3 tokens reached past "ISBN 0-8 [c]1984"
    post = t[i + 4:i + 80].split("\n", 1)[0].split()[:3]
    return any(ADDR_PRE.match(x) for x in pre) or any(ADDR_POST.match(x) for x in post)

def title_year(title, text):
    """#158 (b1mech year, 148 rows): the catalogue title names a year ("Cassia (1993)") that the cue rules did not see
    (no copyright or edition word) but the first pages print. The title was read off those pages by gen_doc_meta, so a
    year it names that the front matter carries on a clean line (no address, table, scan-notice line) is the title-page
    date. One year in the title only; a dated reprint ("1993, 1997") is for the cue rules."""
    ys = {y for g in re.findall(r"\(([^()]*)\)", title or "") for y in re.findall(YR, g)}
    if len(ys) != 1:
        return ""
    y = ys.pop()
    front = "\f".join(text.split("\f")[:8])[:20000]
    for m in re.finditer(r"(?<!\d)%s(?!\d)" % y, front):
        line = _line(front, m.start())
        if not _addr(front, m.start()) and not NOISE.search(line) and not table_line(line):
            return y
    return ""

def pick_year(text, rel, title=""):
    if rel in YEAR_FIX:
        return YEAR_FIX[rel]
    ys = VITA_C.findall(text) if VITA_FILE.search(rel) else []
    if ys and (papers(text, rel) or len(set(ys)) >= 2):   # #143: every page, latest [C] (the 8-page front saw paper 1 only);
        # RT10: two or more imprint years mark a bundle too (es_lp_39's bulletins have no paper headers); one paper keeps the
        # first-pages rule
        if ys:
            return max(ys)
    name = year_from_name(rel)
    if is_reflist(text):   # #127: a reference list's years are the cited works'
        return name
    pages = text.split("\f")
    front, back = "\f".join(pages[:8])[:20000], "\f".join(pages[8:])[-4000:]
    if len(DEFINITIVE[1].findall(text)) >= 3:   # #136 (r21 judge F2): per-chapter "Last updated" stamps (MSF exports
        # carry 45-158) date sections, not the edition: the edition is the cover date on its own line ("December 2024")
        cover = "\f".join(pages[:3])[:3000]   # the cover and its verso, not a Gutenberg file's changelog
        ds = [m.group(1) for m in DATE.finditer(cover) if _line(cover, m.start()).strip() == m.group(0).strip()]
        if len(set(ds)) == 1:   # several own-line dates are a changelog (Gutenberg CIA Factbook), not a cover
            return ds[0]
    for rx in DEFINITIVE[:1] if len(DEFINITIVE[1].findall(text)) >= 3 else DEFINITIVE:
        ys = [(("20" if y < "50" else "19") + y if len(y) == 2 else y) for y in rx.findall(front + "\f" + back)]
        if ys:
            return max(ys)
    strong = [y for rx, t in ((CUE, front), (CUE_AFTER, front), (CUE_BACK, back), (PRINTCODE, front + "\f" + back), (OCR_C, front))
              for m in rx.finditer(t)
              if not _addr(t, m.start(1)) and not NOISE.search(t[max(0, m.start() - 20):m.end()] + " " + _line(t, m.start(1)))
              and not table_line(_line(t, m.start(1)))
              and not SOURCE.search(m.group(0))
              for y in [m.group(1)] + re.findall(YR, re.match(r"(?:\s*(?:,|and|&)\s*(?:and\s+)?\d{4}(?!\d))*", t[m.end():]).group(0))
              if not late(name, y, t, m.start(1), rel)]
    # ("Reprinted 1972, 1977, 1984" counts all three; "1983\nand 1985" too)
    seen = {}
    for i, p in enumerate(pages):
        for m in DATE.finditer(p):
            if not NOISE.search(_line(p, m.start())):
                seen.setdefault(m.group(0), set()).add(i)
    # footer/header date (NWTND "June 7, 2021"): on >= 20% of the pages; a date repeated in citations is not a footer
    strong += [k[-4:] for k, v in seen.items() if len(v) >= max(3, len(pages) / 5)]
    # a dated title page (NEETS "September 1998", COPS "July 2007") counts only without a filename year: library
    # stamps and preface dates on 19th-century scans must not override the catalogue year
    # (a date on its own short line; narrative dates sit in long lines: "was granted on Dec. 1, 1914, after nearly")
    weak = [] if name else [m.group(1) for m in DATE.finditer(front)
                            if len(_line(front, m.start()).strip()) <= 45 and not NOISE.search(_line(front, m.start()))] + \
        [m.group(1) for rx in (IMPRINT, IMPRINT2) for m in rx.finditer("\f".join(pages[:2]))
         if not _addr(m.string, m.start(1)) and not NOISE.search(m.group(0)) and not table_line(_line(m.string, m.start(1)))
         and not (re.search(r"\b(?:in|en|em|of|de|since|desde|from|until|by)\s+$", m.string[m.start():m.start(1)], re.I)
                  and not re.search(r"written|produced|prepared|published|issued|printed", m.string[max(0, m.start() - 80):m.end()], re.I))]
    # (#136: "and a half in 1964" on the STEP floods sheet, "SINCE 1526", "Indian Rebellion of 1857" are narrative, not
    # imprint lines; "written by Edward Stevens for Practical Action in 2008" is a credit and stays)
    c = [y for y in (strong or weak) + [name] if y and y <= "2026"]
    return max(c) if c else title_year(title, text)   # #158: last resort, the title-page year the title already names

_CUEW = re.compile(r"©|\(c\)|copyri|revis|edition|print|publish|updated|issued|édition|edición|impreso|imprimé|derechos|"
                   r"\d ?pp?\.", re.I)   # "27, 1998, 141 p.": the CD3WD citation line, not a table
def table_line(line):
    """#136: a chart axis or table row ("1980 1985 1990 1995", "0 10 20 1972") is never a year source: 3+ numbers making
    60%+ of the tokens, and no copyright/edition word on the line ("Reprinted 1972, 1977, 1984" stays)"""
    toks = line.split()
    nums = [x for x in toks if re.fullmatch(r"[\d.,%()\-–/]+", x) and re.search(r"\d", x)]
    return len(nums) >= 3 and len(nums) >= 0.6 * len(toks) and not _CUEW.search(line)

def late(name, y, t, i, rel):
    """#130: on old-book shelves a cue year 30+ years after the filename year is a reprint, microfiche or OCR slip
    (Colliery "Copyright, 1897, 1999", Menger 1871 "Reprinted in 2007") unless an edition word sits within 100 chars"""
    # a year glued to letters is a model number, not a catalogue year (winchester_model1886, colt_m1911)
    return bool(name) and rel.startswith(OLD_SHELVES) and int(y) > int(name) + 30 and \
        bool(re.search(r"(?<![A-Za-z\d])%s(?!\d)" % name, os.path.basename(rel))) and \
        not EDN.search(t[max(0, i - 100):i] + _line(t, i))

def address_year(text, y):
    """True when every occurrence of y sits in address/catalogue context (Box 1692, 1600 Wilson Boulevard, 574-1868), or none."""
    return all(_addr(text, m.start()) for m in re.finditer(r"(?<!\d)%s(?!\d)" % y, text))

TEMPLATE = re.compile(r"what practical questions|who should open it", re.I)   # in "s" (gen_doc_meta's one-liner)
MOJI = re.compile(r"Ã.|â€|Â |�|ï¿½")   # #158: mojibake (b1mech_checks.MOJI)
SURV = re.compile(r"surviv|prepper", re.I)

# #132 (10-07): the one-liner `s` is written in the document's language `l`. English is recognised by function
# words that no other library language uses as words; non-Latin languages by their script.
_EN = set("the and of to for with how from their this that which are is its by on about using what when or can has have".split())   # #158: "or", "can", "has", "have" (the t9 vote counts them)
_EN_NOT = {"nl": {"of", "is", "what"}, "de": {"is"}, "tl": {"is"}, "id": set(), "da": {"for"}}   # da: Danish "for" is not an English hit
def s_lang_ok(s, l):
    """True when the one-liner s reads as language l (or is too short to tell)"""
    words = re.findall(r"[^\W\d_]+", s.lower())
    if len(words) < 5 or not l:
        return True
    if l in ("ko", "ja", "zh", "ar", "fa", "ur", "ru", "hi", "bn", "ne"):
        return bool(script_lang(s * 20, ""))   # repeated: script_lang wants >= 100 weighted letters
    hits = sum(w in _EN - _EN_NOT.get(l, set()) for w in words)
    if l == "en":   # here "in", "a", "an" count too ("Mice eat weed seeds in fields, helping control weeds ...")
        en = sum(w in _EN or w in ("in", "a", "an", "or", "as", "at") for w in words) / len(words)
        return en >= 0.04 and not script_lang(s * 20, "")
    # #158 (b1mech lang): "A practical guide for setting up ... and case studies." passed the old 12% bar with 2 hits in
    # 18 words; two English function words at 6% is already English (the t9 checker's bar: 2 stopword hits)
    return not (hits >= 2 and hits / len(words) >= 0.06)

# #135 (r21 judge I): a 24-word hard cap cut 170 one-liners mid-sentence ("... para uso em países em…"). One rule for
# every writer (gen_doc_meta, gen_doc_meta_vl) and for --verify: `s` is a finished sentence of at most S_MAX characters
# (a character budget: Vietnamese counts every syllable as a word). Over it: ask once for a shorter sentence; last
# resort: cut at a clause boundary and end the sentence there.
S_MAX = 180
_END = re.compile(r"[.!?。！？।৷][\"'”’»)\]]*$")
_DANGLE = set(("a an the and or of to for with in on at by from as but nor its their this that these those such including "
               "like via into about than e y o u de del la las los el en con para por un una sobre et ou le les des du au aux "
               "pour avec dans sur da do dos das em com os um uma của các những cho với và trong để").split())
def s_done(s):
    """True when s ends a sentence: end punctuation, not "…", and not on a dangling word ("... for the.")"""
    s = (s or "").strip()
    if not _END.search(s) or s.endswith(("…", "...")):
        return False
    w = re.findall(r"[^\W_]+", s.lower())
    return not w or w[-1] not in _DANGLE or bool(re.search(r"[\"'”’»]\W*$", s))   # "... 'Drop, Cover, and Hold On'."

_CLAUSE = (re.compile(r"[,;:，、；：]\s*|\s+[-–—]\s+|\s+\("),   # punctuation first, then a relative/participle clause
           re.compile(r"\s+(?=(?:who|which|that|where|while|using|including|especially|such as|que|qui|quien|onde|où|mà)\s)", re.I))
def trim_s(s, l="", cap=S_MAX):
    """#135 last resort: the longest head that ends at a clause boundary within cap, closed with a full stop. A
    finished sentence with no boundary to cut at is kept whole (long, not broken)."""
    s = re.sub(r"\s*(?:…|\.\.\.)$", "", (s or "").strip())
    if len(s) <= cap and s_done(s):
        return s
    stop = "。" if l in ("zh", "ja") else "।" if l in ("bn", "hi") else "."
    for rx in _CLAUSE:
        for i in sorted((m.start() for m in rx.finditer(s) if m.start() <= cap), reverse=True):
            ws = s[:i].split()
            while ws and re.sub(r"[\W_]+", "", ws[-1].lower()) in _DANGLE:
                ws.pop()
            h = " ".join(ws).rstrip(" ,;:-–—，、；：")
            if len(h) >= min(60, len(s) // 3):
                return h + stop
    if s_done(s):
        return s
    ws = s[:cap].split()[:-1] if len(s) > cap else s.split()   # no boundary at all: whole words, no dangling tail
    while ws and re.sub(r"[\W_]+", "", ws[-1].lower()) in _DANGLE:
        ws.pop()
    return " ".join(ws).rstrip(" ,;:-–—") + stop if ws else ""

S_AGAIN = ("\nYour last summary was too long ({n} characters) or unfinished. Write ONE complete sentence of at most 18 words "
           "(under 150 characters) that ends with a full stop.")
def fit_s(s, again, l="", bad=lambda x: False):
    """#135: s if it is a finished sentence within S_MAX; else again(note) once (same prompt plus S_AGAIN); else trim_s"""
    if len(s) <= S_MAX and s_done(s):
        return s
    try:
        s2 = again(S_AGAIN.format(n=len(s)))
    except Exception:
        s2 = ""
    if s2 and len(s2) <= S_MAX and s_done(s2) and not bad(s2):
        return s2
    return trim_s(s2 if s2 and not bad(s2) else s, l)

# r21: a summary in the wrong script for its language (a Chinese "饼" inside a Vietnamese answer; Latin-only text on a
# zh/ko/bn entry). One check for verify and for the generators' retry.
_SCRIPT_RX = {l: r for l, r, w in _SCRIPT}
_SCRIPT_RX.update(fa=_SCRIPT_RX["ar"], ur=_SCRIPT_RX["ar"], ne=_SCRIPT_RX["hi"])   # ne: Nepali is Devanagari (RT3 H3)
_OTHER = re.compile("|".join(r.pattern for r in _SCRIPT_RX.values()))
_OWN = {"ja": re.compile("[぀-ヿ一-鿿]")}
def mixed_script(v, l):
    """True when v carries another script than l's: any CJK/Hangul/Bengali/Arabic/Cyrillic/Devanagari letter in a
    Latin-script language, or no letter of the language's own script in a non-Latin one"""
    if not v or not l:
        return False
    if l in _SCRIPT_RX:
        return len(v) >= 10 and not (_OWN.get(l) or _SCRIPT_RX[l]).search(v)
    return bool(_OTHER.search(v))

BN_GARBLE = re.compile(r"(^|\s)[া-ৌ]|[ঀ-৿][a-z]")   # vowel sign at word start / Latin inside a Bengali word
def garbled(text, lang):
    """#158 (b1mech, all 46 Bengali and 6 Vietnamese entries): a legacy-font text layer (Bijoy Bengali, VNI Vietnamese)
    extracts as letter salad ("পিরফাiটন", "Höôùng daãn"); the model copied it into t/s/a and once invented an antibiotic
    title from it. Such text is not readable: only the page images (gen_doc_meta_vl) can describe the file."""
    t = text[:200000]
    if lang == "bn":
        bw = len(re.findall(r"[ঀ-৿]+", t))
        return bw > 0 and len(BN_GARBLE.findall(t)) >= 0.1 * bw   # clean Bengali measures ~0; Bijoy extractions 0.19-0.42
    if lang == "vi":
        return len(_VNI.findall(t)) >= max(10, len(t.split()) / 200)   # the detect_lang VNI bar
    return False

def readable(text, rel, lang):
    """enough clean text for the model; below it only a vision description can describe the file"""
    if garbled(text, lang):
        return False
    return len(excerpt(text, rel)[0]) >= (100 if lang in ("ko", "zh", "ja") else MIN_CLEAN)

def near_dups(have):
    """#78: groups of entries whose "a" is identical or token-Jaccard > 0.85 (red team s1_mech e, same method)."""
    norm = lambda a: " ".join(re.sub(r"[^\w ]+", " ", a.lower()).split())
    exact = {}
    for p, e in have.items():
        if e.get("a"):
            exact.setdefault(norm(e["a"]), []).append(p)
    toks = {k: set(k.split()) for k in exact}
    df = {}
    for ts in toks.values():
        for w in ts:
            df[w] = df.get(w, 0) + 1
    post, parent = {}, {k: k for k in exact}
    for k, ts in toks.items():
        for w in ts:
            if df[w] <= 300:   # ponytail: rare-token blocking, same bound as the red team script
                post.setdefault(w, []).append(k)
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for ks in post.values():
        for i, k1 in enumerate(ks):
            for k2 in ks[i + 1:]:
                if find(k1) != find(k2) and len(toks[k1] & toks[k2]) / len(toks[k1] | toks[k2]) > 0.85:
                    parent[find(k1)] = find(k2)
    groups = {}
    for k, ps in exact.items():
        groups.setdefault(find(k), []).extend(ps)
    return [sorted(ps) for ps in groups.values() if len(ps) > 1]

# #285 C1 (round 11 class 8, 10-28): no catalogue s or a sentence carries a digit (a date, count, edition or
# figure the document may contradict: the yellow-fever "vaccine available since 1960"). Mechanical: a sentence holding
# any digit is dropped, nothing is rewritten and no model is asked. The historical warning line ("Written in 1890,
# before antibiotics ... it is a historical text ...") stays: its year is y. A field C1 leaves empty is listed in the
# entry's "c1" ("a", "s" or "as") so main() does not regenerate it and --verify does not queue it.
C1_HIST = re.compile(r"Written in \d{4}, .*\bhistorical text\b")
def has_num(x):
    """#288 (r40 v2 B1/B2, 10-29): any number character, not only ASCII digits: ¾, CO₂, Ⅳ go too (no formula exception)"""
    return any(unicodedata.category(ch) in ("Nd", "No", "Nl") for ch in x)
C1_NONLATIN = set(_SCRIPT_RX) | {"el"}   # t9's fragment floor (b1mech NONLATIN) skips these
_C1_ABBR = re.compile(r"\b(?:[A-Za-z]|e\.g|i\.e|etc|vs|approx|ca|vols?|nos?|pp?|eds?|figs?|dept|govt|inc|ltd|co|st|mt|dr|mrs?|ms|"
                      r"jr|sr|gen|col|lt|sgt|capt|ft|al)\.$", re.I)   # "U.S. Army", "Dr. Snow", "J. Smith": not a sentence end
def c1_sentences(v):
    out, start = [], 0
    for m in re.finditer(r"[.!?。！？।৷][\"'”’»)\]]*(?:\s+|$)|[。！？](?=\S)", v):
        ab = _C1_ABBR.search(v[start:m.start() + 1]) if m.group(0)[0] == "." and m.end() < len(v) else None
        if ab and not C1_HIST.match(v[m.end():]) and not (ab.group(0).lower() == "etc." and v[m.end()].isupper()):
            continue
        if m.group(0)[0] == "." and m.end() < len(v) and " " not in v[start:m.start()].strip():
            continue   # one word is not a sentence (".300 Win. Mag. oder .308 Win.")
        out.append(v[start:m.end()].strip()); start = m.end()
    return out + ([v[start:].strip()] if v[start:].strip() else [])

def c1(v):
    """v without its digit-bearing sentences (the historical warning line kept); v itself when none is dropped"""
    ss = c1_sentences(v or "")
    keep = [x for x in ss if C1_HIST.match(x) or not has_num(x)]
    return v if len(keep) == len(ss) else " ".join(keep)

def c1_entry(e):
    """apply c1() to e's s and a; keep e["c1"] = the fields C1 left empty. Returns the fields changed."""
    hit, mark = [], set(e.get("c1", ""))
    for f in ("s", "a"):
        if e.get(f) and c1(e[f]) != e[f]:
            v = c1(e[f])   # a Latin-script remainder under 5 words is a fragment (t9 echo), not a summary: it goes too
            e[f] = "" if len(v.split()) < 5 and e.get("l") not in C1_NONLATIN else v; hit.append(f)
        if e.get(f):
            mark.discard(f)
        elif f in hit:
            mark.add(f)
    if mark:
        e["c1"] = "".join(sorted(mark))
    else:
        e.pop("c1", None)
    return hit

def verify():
    """--verify: no model. Red team 10-05 + FIXES #72-#78: stale entries, prompt echo, Google boilerplate, invented
    survival audiences, dose allow-list, language (script + stopword vote), years (cue rule), empties; --dups also
    queues distinct documents that share a summary. Deletes "a" (key absent) so main() regenerates."""
    have = json.load(open(OUT)); rows = []; n = {}
    def log(rule, rel, *detail):
        rows.append("\t".join([rule, rel, *map(str, detail)])); n[rule] = n.get(rule, 0) + 1
    def drop(rule, rel, e, *detail, keep_s=False):
        # keep_s: a relabel invalidates the two-sentence answer, not the one-line description that the no-text (VL)
        # path needs (10-06: dropping "s" on LANG left 114 image-only docs with nothing to summarise from)
        log(rule, rel, e.get("a", ""), *detail); e.pop("a", None)
        if not keep_s: e.pop("s", None)
    texts = {}
    for rel, e in list(have.items()):
        if PATHS is not None and rel not in PATHS:
            continue
        pdf = os.path.join(LIB, rel)
        if not os.path.exists(pdf):   # #77: file gone from the tree (22 known gaps; 10-06 files pass moved 474 dups/repairs out)
            log("STALE", rel, e.get("t", "")); del have[rel]; continue
        try:
            text = clean_text(extract(pdf, rel) or "")
        except Exception:
            text = ""
        texts[rel] = text
        name, a, s = os.path.basename(rel), e.get("a", ""), e.get("s", "")
        if ECHO.search(a) or TEMPLATE.search(s):
            drop("ECHO", rel, e, keep_s=not TEMPLATE.search(s))
        elif GOOGLE_TXT.search(a + " " + s):
            drop("GOOGLE", rel, e, keep_s=not GOOGLE_TXT.search(s))
        elif audience_bad(rel, e.get("t", ""), a, ftext(text)):   # #125: old-book shelves, path/title rule (RT10: framing vs text)
            drop("AUDIENCE", rel, e, keep_s=True)
        elif not rel.startswith(OLD_SHELVES) and SURV.search(a) and not SURV.search(text):
            drop("SURVIVAL", rel, e, keep_s=True)
        elif bad_shape(a):   # #158: question lists, no sentence end
            drop("SHAPE", rel, e, keep_s=True)
        if e.get("s") and audience_bad(rel, e.get("t", ""), e["s"], ftext(text)):
            log("AUDIENCE_S", rel, e.pop("s"))
        if e.get("s") and "?" in e["s"]:   # #158: a one-liner is never a question
            log("SQ", rel, e.pop("s"))
        if e.get("s") and MOJI.search(e["s"]):   # #158: "ma�s" copied from a broken source encoding
            log("MOJI_S", rel, e.pop("s"))
        if e.get("a") and MOJI.search(e["a"]):
            drop("MOJI", rel, e, keep_s=True)
        if MARK and e.get("a") and (is_reflist(text) or papers(text, rel)):   # #127/#128 one-time: summarised before the rule
            drop("REFLIST" if is_reflist(text) else "COMPILATION", rel, e, len(papers(text, rel)))
        for f in ("a", "s", "t"):
            m = DOSE.search(e.get(f, ""))
            if m and not DOSE_OK.search(rel + " " + e.get("t", "")):
                log("DOSE", rel, f, m.group(0), e[f]); e[f] = ""
        ok = readable(text, rel, e.get("l", ""))
        vl = "" if ok else vl_lang(e.get("s", "")) or (script_lang(e.get("s", "") * 20) if e.get("s") else "")
        if vl and vl != e.get("l") and name not in LANG_FIX:   # RT3 H3: a hand-read label beats the VL guess (ne -> hi); #131: image-only Bengali "_pa_en_" sheets, VL says "in Bengali" (or writes Bengali)
            log("LANG", rel, "", e.get("l"), vl, "vl"); e["l"] = vl
        elif len(text) > 200:
            l, strong = detect_lang(text, name)
            if strong and l != e.get("l") and (ok or e.get("l") not in _SCRIPT_RX):   # r21: OCR junk from a non-Latin
                # scan reads as weak Latin; it never overwrites a script label (bn/zh/...) on a file with no usable text
                if e.get("a"):
                    drop("LANG", rel, e, e.get("l"), l, keep_s=True)
                else:
                    log("LANG", rel, "", e.get("l"), l)
                e["l"] = l
        if e.get("a") and mixed_script(e["a"], e.get("l", "")):   # r21: stray CJK in a Latin answer, Latin-only zh/ko/bn
            drop("SCRIPT", rel, e, e.get("l"), keep_s=True)
        elif e.get("a") and e.get("l") not in ("en", "") and not s_lang_ok(e["a"], e["l"]):   # #158/#132: `a` follows `l` too
            drop("ALANG", rel, e, e.get("l"), keep_s=True)
        if e.get("s") and mixed_script(e["s"], e.get("l", "")):   # no usable text: gen_doc_meta lists it for the VL model
            log("SCRIPT_S", rel, e.get("l"), e.pop("s"))
        if rel in A_FIX and e.get("a") != A_FIX[rel]:
            log("A_FIX", rel, e.get("a", ""), A_FIX[rel]); e["a"] = A_FIX[rel]
        if rel in S_FIX and e.get("s") != S_FIX[rel]:
            log("S_FIX", rel, e.get("s", ""), S_FIX[rel]); e["s"] = S_FIX[rel]
        for f in c1_entry(e):   # #285 C1: after the hand fixes, so a fixed text with a digit is cut too
            log("C1", rel, f, e.get(f, ""))
        if e.get("s") and not s_done(e["s"]):   # #135: cut or unfinished one-liner (no usable text: listed for the VL model)
            log("SCUT", rel, e.get("l"), e.pop("s"))
        if e.get("a", "").endswith("…"):   # #135: the old 60-word cut on `a`
            drop("ACUT", rel, e, keep_s=True)
        if e.get("s") and not s_lang_ok(e["s"], e.get("l", "")):   # #132
            if readable(text, rel, e.get("l", "")):
                log("SLANG", rel, e.get("l"), e.pop("s"))
            else:
                log("SLANG_VL", rel, e.get("l"), e["s"])   # image-only: the VL text is all there is; kept
        elif not e.get("s") and "s" not in e.get("c1", "") and readable(text, rel, e.get("l", "")):
            log("SEMPTY", rel); e.pop("s", None)   # gen_doc_meta fills it
        y = pick_year(text, rel, e.get("t", ""))
        if y != e.get("y", ""):
            log("YEAR", rel, e.get("y", ""), y); e["y"] = y
        if e.get("a") == "" and "a" not in e.get("c1", "") and (len(text.strip()) > 200 or e.get("s")):   # #77: a VL "s" arriving later (fix81) needs a regen too; #285: never a C1 blank
            del e["a"]; log("EMPTY", rel)
    if "--dups" in sys.argv:   # opt-in: a regen pass, not a check to repeat on every seal
        sha = {}
        for l in open(os.path.join(LIB, "MANIFEST.sha256")):
            h, p = l.rstrip("\n").split("  ", 1)
            sha[p[len("library/"):]] = h
        same = []
        for g in near_dups(have):
            kinds = {sha.get(p) or hash(texts.get(p, "")) for p in g}
            if len(kinds) == 1:
                same.append(g); log("DUPFILE", g[0], len(g), *g[1:])   # the same file twice: report to files, keep
                continue
            for p in g:
                have[p]["_dup"] = have[p]["a"]; drop("DUP", p, have[p], len(g), keep_s=True)
        json.dump(same, open(os.path.join(LIB, "..", "logs", "fix78_dupfiles.json"), "w"), indent=1)
    tmp = OUT + ".tmp"
    json.dump(have, open(tmp, "w"), indent=1, ensure_ascii=False, sort_keys=True); os.replace(tmp, OUT)
    open(os.environ.get("VERIFY_TSV") or os.path.join(LIB, "..", "logs", "e1c_verify_" + time.strftime("%Y%m%d") + ".tsv"), "w").write("\n".join(rows) + "\n")
    print("VERIFY " + " ".join(f"{k}={v}" for k, v in sorted(n.items())) + f" regen={sum('a' not in v for v in have.values())} of {len(have)}"
          + f" empty={sum(not v.get('a') for v in have.values())}")

def selftest():
    assert address_year("VITA, 1600 Wilson Boulevard, Suite 500", "1600") and address_year("P.O. Box 1692 Palo Alto", "1692")
    assert address_year("(763) 574-1868", "1868") and address_year("159-200-2020 Integrate", "2020") and address_year("1815 North Lynn St. Suite 200", "1815")
    assert not address_year("Winrock, 1990-1997, 100", "1997") and not address_year("year 1912-13", "1912") and not address_year("sans Frontières 2002 http://x\nAvenue", "2002")
    assert not address_year("Copyright 1984 by the author", "1984") and not address_year("born in 1971 in Sydney", "1971")
    assert not address_year("ISBN: 0-86619-209-3\n[sup.c]1984, VITA", "1984") and not address_year("F. Alferink\n22-08-2001\nS.G.", "2001")
    assert not address_year("In 1849, Dr. John Snow", "1849") and address_year("ANSI/SAAMI Z299.3-1993.", "1993")
    assert skip_google("scanned by Google ... public domain\fReal page") == "Real page"
    assert DOSE.search("Browning A-500G") and DOSE_OK.search("x/Firearms Manuals/a.pdf") and DOSE_OK.search("FM 4-25.12 Unit")
    # #72 year rule on the judge's confirmed wrong years (text shapes copied from the cached pages)
    Y = lambda t, rel="docs/x/doc.pdf": pick_year(t, rel)
    assert Y("Medical Desk Reference\n\nTHIRD UNITED STATES REVISION\n2004\n\nDEPARTMENT OF\fIn 1946 the first") == "2004"
    assert Y("Washington, DC 20002-4201\n202.289.4262\nwww.icma.org\nJuly 2007\n\niii\fsince 1914") == "2007"   # COPS
    assert Y("First published 1970\nReprinted 1972, 1977, 1984\nP-69") == "1984"
    assert Y("Ministry of Water - Tanzania - Rwegarulila Water\nResources Institute, 1999, 90 p.)") == "1999"
    assert Y("Rural Development\nWashington, D.C., October 6-8, 1998\nAmbassador") == "1998"
    assert Y("Beat Grimm\n\nDübendorf, October 2002\fby Aftim\nAcra in a booklet published by UNICEF in 1984.") == "2002"
    assert Y("Collection structure revised: April 1, 2012\nPDF generated: April 6, 2012\fGauss 1824") == "2012"   # Factoring
    assert Y("HEADQUARTERS\nDEPARTMENT OF THE ARMY\nWashington, DC, 18 June 1998\f FM 5-428 1987") == "1998"
    assert Y("Beat Grimm\n\nDübendorf, October 2002\f" + "first trials 1999\f" * 3) == "2002"   # SODIS
    assert Y("SPECIAL PUBLICATION\nSeptember 1998\fNEETS\f6490 SAUFLEY\n\n1998 Edition Prepared by\f1989") == "1998"
    assert Y("VITA\n1600 Wilson Boulevard, Suite 500\nArlington, Virginia 22209 USA") == ""   # address, no cue
    assert Y("Copyright VITA, 1600 Wilson Boulevard") == ""
    assert Y("Release Date: March 12, 2004 [EBook #11546]\fA TREATISE", "docs/survivor_library/a/treatise_1890.pdf") == "1890"
    assert Y("Received Jun 5 1925\fLONDON 1890", "docs/survivor_library/a/x_1890.pdf") == "1890"   # stamp is not a cue
    assert Y("THIS LAST VOLUME XII\nCopyright, 1912, by\f", "docs/survivor_library/a/vol_11_1911.pdf") == "1912"
    assert Y("Where There Is No Doctor\f" + "page June 7, 2021\f" * 3, "docs/medical/hesperian_where_there_is_no_doctor/en_nwtnd_2019_30a.pdf") == "2021"
    assert Y("VITA\nPublished Por\nVOLUNTEERS EM AJUDA\n1600 Bulevar de Wilson") == ""
    assert Y("Chess Problems\n\nAn Electronic Edition\nAnders Thulin · 1999-04-12\fThe Editors\nFebruary 1876.") == "1876"
    assert Y("Joseph Jenkins wrote a book, published in 1910 titled Farmers of Forty Centuries") == ""
    assert Y("Medical Handbook\nFirst Edition 1 June 2001\n") == "2001" and Y("PROYECTO\nIQUITOS - PERU 1997\n") == "1997"
    assert Y("P.O. Box 1692\nPalo Alto") == "" and Y("JUL 3 1919\n\nCopyricHt, 1919\nBY", "docs/e/vol_18_1918.pdf") == "1919"
    assert Y("First published 1970\nReprinted 1972, 1977, 1984\nP-69") == "1984"
    assert Y("Ministry of Water - Tanzania - Rwegarulila Water\nResources Institute, 1999, 90 p.)") == "1999"
    assert Y("Rural Development\nWashington, D.C., October 6-8, 1998\nAmbassador") == "1998"
    assert Y("Beat Grimm\n\nDübendorf, October 2002\fby Aftim\nAcra in a booklet published by UNICEF in 1984.") == "2002"
    assert Y("Collection structure revised: January 23, 2009\nPDF generated: February 5, 2011") == "2009"
    assert Y("Transmitter, was granted on Dec. 1, 1914, after nearly thirteen years") == ""
    assert Y("the year 1912 was hot") == "" and Y("", "docs/medical/headington_trauma_critical_incident.pdf") == "2013"
    # #73 echo variants seen in the 10-06 data; real sentences must pass
    for bad in ("How to weld. Who should open it and when: welders.", "Soil. Who should use these methods and when.",
                "Practical questions about audit topics. For students.", "Ducks. Who should read it: farmers.",
                "Cómo almacenar granos. Quién debe almacenarlos.", "Rongeurs. Qui devrait exporter et comment.",
                "What practical questions this document answers (name the concrete topics).", "Bricks. Target audience: masons."):
        assert ECHO.search(bad), bad
    for ok in ("How to weld steel. Welders in small workshops should open it before a repair.",
               "Cómo cocinar. Quienes viven en zonas rurales lo usan a diario.", "This document answers practical questions about cavities."):
        assert not ECHO.search(ok), ok
    # #75 language
    assert vote("und nicht eine mit den dem von für")[0] == "de" and vote("the and of the is for")[0] == "en"
    assert detect_lang("페드로와 함께 하는 대비연습 재난대비행동요령책자는 " * 20)[0] == "ko"
    assert detect_lang("在警报和警告上签字制定一个计划 Make a Plan " * 20)[0] == "zh"
    assert detect_lang("非常用持ち出し袋のリスト 水と食料 " * 20)[0] == "ja"
    assert detect_lang("لیست لوازم اضطراری برای خانواده " * 20, "prs_wwd_2024_fm.pdf")[0] == "fa"
    assert detect_lang("লেয়ার মুরগি পালন পদ্ধতি " * 30)[0] == "bn"
    assert detect_lang("Đăng ký nhận báo động và cảnh báo của những người trong cộng đồng được cho " * 5)[0] == "vi"
    assert detect_lang("het is een van de beste manieren om water te zuiveren voor de mensen die niet " * 5)[0] == "nl"
    assert detect_lang("see www.hkpro.com or hk.com for parts; com com com com com com com com com com com com com com com com com com com com com com")[0] == "en"
    assert detect_lang("Kalimera alpha beta: the Greek letters αβγ " * 5)[0] == "en"
    # r21 #125 audience on old-book shelves: path/title decides, never a stray "survived" in the body
    SL = "docs/survivor_library/SurvivalLibrary/library/"
    assert audience_bad(SL + "Shipbuilding/the_outriggers_of_indonesian_canoes_1920.pdf", "The Outriggers of Indonesian Canoes",
                        "Survivalists in coastal regions should open it before leaving for remote islands.")
    assert audience_bad(SL + "Horses/domestic_animals-a_pocket_manual_1858.pdf", "Domestic Animals", "Farmers should open it for long-term food security.")
    assert audience_bad(SL + "Survival-Individual/x.pdf", "Journals", "Survivalists use it.")   # RT7 #205: folder is no exemption
    assert audience_bad(SL + "Survival-Individual/shelters-shacks-shanties-daniel-carter-beard.pdf", "Shelters, Shacks and Shanties",
                        "Young adventurers and survivalists should open it when learning basic shelter construction.")
    assert not audience_bad(SL + "Survival-Individual/x.pdf", "Survival Journals", "Survivalists use it.")   # title about survival
    assert not audience_bad(SL + "Survival-Individual/sas_survival_handbook.pdf", "Handbook", "Survivors should open it.")
    assert not audience_bad("docs/cd3wd/2012/health/_mc_em_refugee_health_x.pdf", "Refugee Health", "For aid workers in emergencies.")
    assert not audience_bad("mirrors/ready_gov/x.pdf", "Make a Plan", "Survivors of floods use it in emergencies.")   # modern shelf
    assert not audience_bad(SL + "Cookbooks/x_1909.pdf", "Recipes", "Home cooks planning family meals.")
    # r21 #127 publisher ads and reference lists
    ad = "JUST PUBLISHED, IN ONE VOLUME, 8VO.\nMATHEMATICS FOR PRACTICAL MEN ... Price $2.50"
    assert skip_ads("Title page\f" + ad + "\fCHAPTER I. Steam") == "Title page\f\fCHAPTER I. Steam"
    jumbo = ("Home-built jumbo-rotors USA 1890's - etc.\n\nPlease further consult the following highly recommended and very useful good books:\n"
             "1: A Field Guide to American Windmills. T. Lindsay Baker, University of Oklahoma Press USA 1985\n"
             "2: The Homemade Windmills of Nebraska. Bulletin No. 59 USA 1899 [reprinted by Farallones Institute California USA 1976]\n"
             "4: Horizontal Windmills, Draft Mills. Greville Bathe, Allen, Lane and Scott Philadelphia, Pa. USA 1948\n")
    assert is_reflist(jumbo) and "REFERENCE LIST" in prompt_note(jumbo)
    assert Y(jumbo, "docs/cd3wd/2012/wind_power/_wi_427_Home_built_jumbo_rotors_etc_1890s_jf_en_155040_.pdf") == ""   # "1890s" is a decade
    assert not is_reflist("How to Make Fish Boxes (NRI, 1991, 8 p.)\n(introduction...)\nFish boxes\nThe design of fish boxes\nReferences\n" + "Smith 1990, 1991. " * 20)   # a TOC entry
    # r21 #128 compilations: one title line per paper after the cd3wd language bar or a PAPEL/PERFIL header
    vita = ("PAPEL TÉCNICO #24 Page 1 of 417\nHome\nhome.cd3wd.ar.cn.de.en.es.fr.id.it.ph.po.ru.sw\nPAPEL TÉCNICO #24 UNDERSTANDING ADOBE\nPor BALLA\n"
            "text\fHome\nhome.cd3wd.ar.cn.de.en.es.fr.id.it.ph.po.ru.sw\nINDÚSTRIA DE PERFIL #6 CALÇAS JEANS AZUIS\nPrepared Por Edward\n")
    ps = papers(vita, "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_po_lp_10_120500_.pdf")
    assert len(ps) == 2 and "ADOBE" in ps[0] and "JEANS" in ps[1] and "COMPILATION of 2" in prompt_note(vita, "_at_vita_vth_po_lp_10_"), ps
    leaflet = "Home\nar.cn.de.en.es.fr.id.it.ph.po.ru.sw\nMicotoxinas em grãos - Indice\nx\f" + "Home\nar.cn.de.en.es.fr.id.it.ph.po.ru.sw\nO que são micotoxinas\nx\f"
    assert papers(leaflet, "docs/cd3wd/2012/agriculture/_ag_mycotoxins_grain_es_cta_lp_113250_.pdf") == []   # pages, not papers
    # r21 #130 date cues and rejected years (fix80 F samples, r21_titles 30-year list)
    assert Y("revised and expanded from the 1991 California Sea Grant publication\n\nApril 8, 2014\n") == "2014"   # cdph biotoxins
    assert Y("Medications\nLast updated June 18, 2025\n", "docs/medical/fda_fema_medications_when_supply_runs_out_2026.pdf") == "2025"
    assert Y("© 2018, 2023 por la Agencia Federal\nP-2354 / April 2024\n") == "2024"   # FEMA print code
    assert Y("§ 97.1 (10–1–24 Edition)\nVerDate Sep<11>2014 08:12 Mar 26, 2025 Jkt\f" * 4, "docs/comms/cfr47_part97_amateur_radio_2024.pdf") == "2024"
    assert Y("OFICINA REGIONAL DE LA FAO\nSantiago, Chile\n1984\nSerie: Tecnología") == "1984"
    assert Y("Group.\n\n0 Intermediate Technology Development Group, 1983\nand 1985.\n\nPrinted in England") == "1985"   # OCR'd ©
    assert Y("Frequency Wallet Card Courtesy of South County ARES Revised 3/5/2018 As per", "docs/comms/scares_wallet_card_2017.pdf") == "2018"
    assert Y("Digital file copyright by Cornell University Library 1995.\nMann Library", SL + "Herbalism/the_book_of_herbs_1903.pdf") == "1903"
    assert Y("Author: Lewis\n[Posted: July 8, 2003]\nRelease Date: July, 2005 [EBook #8419]") == ""
    assert Y("Release Date: February, 2006\nFirst Posted: November 1, 2003\n") == ""   # Gutenberg header is not an imprint
    assert Y("Arithmetic: Copyright, 1892, 1893, 1895, 1999, by THE COLLIERY ENGINEER", SL + "Coal and Mining/a_treatise_on_coal_mining_vol_1_1900.pdf") == "1900"
    assert Y("THIRD EDITION\n\nTHE MACMILLAN COMPANY\n1916\nAll rights reserved\nCopyright, 1916", SL + "Farming/fertilizers_1885.pdf") == "1916"   # a real later edition stays
    assert Y("", SL + "Wood Magazine/wood_magazine_064_1993.pdf") == "1993"   # YEAR_FIX
    assert Y("Copyright 1999 Browning", SL + "Firearms Manuals/winchester_model1886_lever_action_rifle.pdf") == "1999"   # model number
    assert Y("tank sizing, several are reviewed by (Gould & Nissen-Petersen, 1999). Fortunately") == ""   # narrative "reviewed"
    assert Y("Table 3\nCOUNTRY\n1986\nKenya") == ""
    assert Y("Bushmaster Bullpup Operation & Safety Instructions\nDownloadable version - July 1999\n\nBUSHMASTER") == "1999"
    # r21 #131 language: Portuguese spelling, filename token confirming a weak vote, script over the "_en_" filename
    pt = "Micotoxinas em grãos. A contaminação dos grãos não é visível; as condições de armazenagem são importantes para a produção. " * 12
    assert detect_lang(pt, "_ag_mycotoxins_grain_es_cta_lp_113250_.pdf") == ("pt", True)
    assert name_lang("_it_Internet_vietnamese_en_134100_.pdf") == "vi" and name_lang("_ag_glossary_agric_terms_en_es_2_pc_lp_108120_.pdf") == ""
    assert name_lang("_at_vita_vth_po_lp_15_120550_.pdf") == "pt" and name_lang("_it_Charts_en_1.pdf") == "en"
    assert detect_lang("Chöông trình Giaûng daïy vaø Internet cuûa caùc ñeå laø gì moät " * 3 + " và của là có những các được trong", "_it_Charts_vietnamese_en_133850_.pdf") == ("vi", True)
    assert detect_lang("বিভিন্ন ধরনের মাছ চাষ পদ্ধতি পুকুরের পানির ব্যবহার " * 10, "_ag_fsh_pond_preparation_pa_en_107960_.pdf") == ("bn", True)
    # r21 #132: the one-liner follows l
    assert not s_lang_ok("Explains what mycotoxins are, their health risks, and how to prevent contamination in stored grains.", "pt")
    assert s_lang_ok("Guia para avaliar custos, demanda e logística antes de iniciar uma fábrica ou projeto industrial.", "pt")
    assert s_lang_ok("Cómo cosechar y secar trigo, maíz, soya y frijol en fincas pequeñas de América Latina.", "es")
    assert not s_lang_ok("A children's guide to preparing for wildfires, using simple language and scenarios.", "es")
    assert s_lang_ok("A guide to the use of the rifle and its parts for target shooting.", "en")
    assert s_lang_ok("Mice eat weed seeds in fields, helping control weeds without herbicides, especially in sustainable farming.", "en")
    assert not s_lang_ok("Cómo preparar la casa para un incendio forestal y qué llevar al evacuar con la familia.", "en")
    assert s_lang_ok("该文档介绍山火防范措施和应急撤离步骤。", "zh") and not s_lang_ok("Explains wildfire safety steps for families at home.", "zh")
    assert s_lang_ok("Het boek legt uit hoe je water zuivert voor de mensen in het dorp en wat je nodig hebt.", "nl")
    assert detect_lang("Chöông trình Giaûng daïy Kinh teá. Veõ ñoà thò baèng Chart Wizard. Caùc ñaëc tính cuûa ñoà thò. " * 4)[0] == "vi"
    assert detect_lang("Bedarfsermittlungsbogen und die Anlage mit den Werten für eine Schule oder über die Kosten nach dem Bau")[0] == "de"
    assert vl_lang("A guide in Bengali on preparing ponds for fish farming") == "bn" and vl_lang("A guide to ponds in English") == ""
    assert vl_lang("A Bangla-language guide on commercial fish farming") == "bn" and vl_lang("A guide in Bangla on compost") == "bn"
    assert vl_lang("A German technical mathematics textbook for metalwork") == "" and vl_lang("A Bangla guide on fertilizer") == "bn"
    # r21 mixed script
    assert mixed_script("Tài liệu hướng dẫn vẽ các loại đồ thị như cột, thanh, đường,饼, phân tán.", "vi")
    assert not mixed_script("Tài liệu hướng dẫn cách vẽ và định dạng đồ thị trong Excel.", "vi")
    assert mixed_script("How to prepare for a wildfire at home with your family.", "zh")
    assert not mixed_script("该文档介绍山火防范措施 (FEMA) 和应急撤离步骤。", "zh") and not mixed_script("避難所の場所を確認する", "ja")
    assert mixed_script("How to raise fish in ponds, by the 마을 group.", "en") and not mixed_script("Cómo almacenar granos.", "es")
    # r21 resume: reference lists are readable; "_en_" never confirms en; a script label survives OCR junk
    notes = "RefeRences\nChapter 2: INVISIBLe BeINGS\n" + "1 Blaser, M. J. (2014). Missing Microbes. Holt: New York. p. 21.\n" * 30
    assert is_reflist(notes) and readable(notes, "docs/sanitation/humanure_4th_ed/Notes.pdf", "en")
    assert readable(jumbo, "docs/cd3wd/2012/wind_power/_wi_427_Home_built_jumbo_rotors_etc_1890s_jf_en_155040_.pdf", "en")
    junk = "ro AAT RES CNB BA AREA the SA RAR and EN A of Fa Piar to fA for AR with ARS this TA that katika AR kwa TAS hii FRA kuwa E ni MU ON"   # en 8 : sw 5
    assert detect_lang(junk, "_co_ms_Liming_pa_en_125800_.pdf") == ("en", False)
    assert google_only("This book was scanned by Google; public domain, digitized. " * 8 + "\f\f\f") and not google_only("scanned by Google public domain\fChapter I. " + "Real text here. " * 30)
    assert aud_cut("Instructions for making soap from wood ashes and fat, useful for survival or self-sufficiency in the wilderness.") == "Instructions for making soap from wood ashes and fat."
    assert not audience_bad("docs/cd3wd/2012/agriculture/_ag_416_The_Homesteader_Handbook_for_Raising_Small_Livestock05_261_jf_en_101590_.pdf", "", "for self-sufficiency")
    # r22 #135: one-liners end a sentence; over the cap: ask again, else a clause cut, never "…"
    assert not s_done("Cinco documentos técnicos sobre produção de carvão, criação de aves, para uso em países em…")
    assert not s_done("Diccionario bilingüe para traducir palabras entre inglés y español") and not s_done("A guide for the.")
    assert s_done("A manual on safety actions like 'Drop, Cover, and Hold On'.") and s_done("Data from 1982 to 1987.")
    cut = trim_s("A comedy drama for boys about a mischievous boy in a coal mining town who learns to become a better person "
                 "through the Boy Scouts and their leaders in the hills of the old county and the long valley below the mine…")
    assert cut == "A comedy drama for boys about a mischievous boy in a coal mining town.", cut
    cut = trim_s("A FEMA postcard outlining 12 actions individuals and families can take to prepare for disasters, including "
                 "making plans, saving money, practicing drills, and assembling…")
    assert s_done(cut) and len(cut) <= S_MAX and not cut.endswith("…") and "assembling" not in cut, cut
    assert fit_s("Short and done.", lambda n: 1 / 0) == "Short and done."
    assert fit_s("x " * 120 + "end.", lambda n: "A shorter finished sentence.") == "A shorter finished sentence."
    assert s_done(fit_s("Guía para cosechar trigo, maíz y soya en fincas pequeñas, con tablas de secado y almacenamiento "
                        "para cooperativas de agricultores en América Latina y el Caribe durante la temporada de lluvias…",
                        lambda n: "", "es"))
    # r22 #136: section stamps are not the edition; the © cue sits on one line; chart axes and tables are no year source
    msf = ("Clinical guidelines\n\u00a9 Médecins Sans Frontières\fMédecins Sans Frontières. Clinical guidelines.\nDecember 2024\n"
           "ISBN 978\f" + "Last updated: October 2024\f" + "Last updated: September 2023\f" * 3)
    assert Y(msf, "docs/medical/msf/msf_clinical_guidelines.pdf") == "2024"
    assert Y("Medications\nLast updated June 18, 2025\n") == "2025"   # one stamp is still the document's date
    axis = "Historic U.S. Floods\n\n40\n35\n30\n25\n20\n15\n10\n5\n0\n\nA. En 1972, Rapid City, en Dakota del Sur"
    assert Y(axis, "mirrors/ready_gov/www.ready.gov/sites/default/files/2025-04/step_floods_activity_spanish.pdf") == ""
    assert Y("Manual\fIndice\f8\n4\n2\n1\n0\n\nFuente: Christensen, 1974.\nCUADRO 2") == ""   # (grain-drying table, page 3)
    assert Y("Group.\n\n0 Intermediate Technology Development Group, 1983\nand 1985.\n") == "1985"   # one line: still read
    assert Y("Understanding Batteries\nISBN: 0-86619-225-5\n[C]1985, Volunteers in Technical Assistance") == "1985"
    assert table_line("1980 1985 1990 1995 2000") and not table_line("Reprinted 1972, 1977, 1984") and not table_line("No. 27, 1998, 141 p.")
    assert Y("Rainfall (mm)\n1984 1985 1986 1987\n") == ""
    assert Y("D. After 8 inches\nof rain fell in a day\nand a half in 1964\non the Blackfeet") == "" and Y("London, 1890\n") == "1890"
    assert Y("This Technical Brief was written by\nEdward Stevens for Practical Action in 2008.") == "2008"
    # r22 #137: one paper's running header in three spellings is one paper, not a compilation
    jeans = ("Home\nhome.cd3wd.ar.cn.de.en.es.fr.id.it.ph.po.ru.sw\nINDÚSTRIA DE PERFIL #6\nCALÇAS JEANS AZUIS\nPrepared Por\nEdward\n"
             "\fINDÚSTRIA PERFIL #6\n\nPage 2 of 21\n\fINDÚSTRIA DE PERFIL #6\nCALÇAS JEANS AZUIS\nPrepared Por\n")
    assert papers(jeans, "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_po_lp_15_120550_.pdf") == []
    assert "ONE paper" in prompt_note(jeans, "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_po_lp_15_120550_.pdf")
    assert all(s_done(v) and len(v) <= S_MAX for v in S_FIX.values())
    assert same_paper("INDÚSTRIA PERFIL #6", "INDÚSTRIA DE PERFIL #6 CALÇAS JEANS AZUIS") and not same_paper("PAPEL TÉCNICO #6 X", "PERFIL #6 Y")
    assert same_paper("ENTENDENDO O ADOBE", "ENTENDENDO 0 ADOBE") and not same_paper("ENERGIA EOLICA", "AQUICULTURA")
    assert len(papers(vita, "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_po_lp_10_120500_.pdf")) == 2   # two real papers stay
    # r22 #138: the reader sentence restating the plot / the charity / the war is an invented audience
    assert audience_bad(SL + "Christmas/snowbound_for_christmas_1921.pdf", "Snowbound for Christmas",
                        "How to stage a Christmas play. Children and families stranded by snow should open it during Christmas.")
    assert audience_bad(SL + "Cotton/raw_cotton_and_cotton_linters_1944.pdf", "Raw Cotton", "Cotton markets. Farmers should open it before the war.")
    assert audience_bad(SL + "Canning/balanced_meals_1917.pdf", "Balanced Meals", "Menus. Blind people should open it for long-term sustenance.")
    assert not audience_bad(SL + "Christmas/x.pdf", "X", "A family stranded by snow makes gifts.")   # one-line `s` may tell the plot
    # r23 #141: hand answers pass every `a` rule verify applies (else verify drops them and sets them again each run)
    snow = SL + "Christmas/snowbound_for_christmas_1921.pdf"
    assert snow in A_FIX and snow in S_FIX and "staging" in A_FIX[snow] and "stranded" not in A_FIX[snow]
    for p, a in A_FIX.items():
        assert not audience_bad(p, "", a) and not ECHO.search(a) and not GOOGLE_TXT.search(a) and not a.endswith("…") \
            and not mixed_script(a, "en") and a.count(". ") == 1 and len(a.split()) <= 60, (p, a)
    assert s_lang_ok(S_FIX[snow], "en") and not audience_bad(snow, "", S_FIX[snow])
    # r23 #143: a VITA compilation takes the latest paper's [C] from any page; one paper keeps the first-pages rule
    comp = "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_fr_lp_25_120300_.pdf"
    late_c = vita.replace("Por BALLA\n", "Por BALLA\nISBN: 0-86619-278-6\n[C]1985, Voluntários em Ajuda Técnica,\n") + \
        "\fx\f" * 10 + "ISBN: 0-86619-320-0\n[C] 1991, Volontaires dans Assistance Technique,\f[C] VITA, Inc. 1977,\n\f" + "y " * 3000
    assert Y(late_c, comp) == "1991" and Y(late_c.split("\fx")[0], comp) == "1985"
    assert Y(jeans + "\fx" * 10 + "\f[C]1991, VITA\f" + "y " * 3000, "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_po_lp_15_120550_.pdf") == ""
    # RT10 M4 (#143 regressed, b5 W9): "(C) 1990" and "© 1984" are imprints too, the Spanish "[el LENGUAJE C] 1986" as well, and two
    # imprint years mark a bundle on any VITA bulletin file (the charcoal bundle's name has no "_at_vita_vth_fr_lp_")
    fr38 = "docs/cd3wd/2012/appropriate_technology/_at_vita_vth_fr_lp_38_120430_.pdf"
    two = "x\f[C]1985, Volontaires dans Assistance Technique,\f" + "y " * 3000 + "\f(C) 1990, Volontaires dans Assistance Technique\f"
    assert VITA_C.findall("(C) 1990, Volontaires") == ["1990"] and VITA_C.findall("© 1984 VITA") == ["1984"]
    assert VITA_C.findall("[el LENGUAJE C] 1986, Voluntarios") == ["1986"] and not VITA_C.findall("(c) the pump, 1990")
    saved = YEAR_FIX.pop(fr38, None)
    assert Y(two, fr38) == "1990"
    if saved is not None:
        YEAR_FIX[fr38] = saved
    assert Y(two.replace("(C) 1990", "[el LENGUAJE C] 1988"), "docs/cd3wd/2012/x/_eg_ag_at_vita_vth_charcoal_charbon_fr_lp_99_1_.pdf") == "1988"
    assert YEAR_FIX[fr38] == "1990" and YEAR_FIX["docs/cd3wd/2012/appropriate_technology/_at_vita_vth_es_lp_39_120100_.pdf"] == "1990"
    # r22 #139: titles
    from gen_index import title_lang, year_is_y, lang_from_l
    assert title_lang("VITA Technical Papers: Bambú, Baterías (Spanish)", "es") == "Boletines técnicos VITA: Bambú, Baterías (Spanish)"
    assert title_lang("Diretrizes de Planejamento Energético (Português)", "pt") == "Diretrizes de Planejamento Energético (Portuguese)"
    assert lang_from_l(title_lang("সার প্রয়োগ (Bangla)", "bn"), "bn") == "সার প্রয়োগ (Bengali)"
    assert title_lang("VITA Technical Papers: Adobe", "en") == "VITA Technical Papers: Adobe"
    assert year_is_y("Where There Is No Doctor (New Edition, 2019), chapter 16 (2023)", "2023") == "Where There Is No Doctor (New Edition), chapter 16 (2023)"
    assert year_is_y("Weather Elements (Fourth Edition, 1957)", "1957") == "Weather Elements (Fourth Edition, 1957)"
    # #158 (red team 10-09 F6): survivalist wording off the survival shelves, answer shape, `a`/`s` language, garbled
    # legacy-font text, the title-page year a title names
    assert surv_bad("docs/cd3wd/2012/agriculture/_ag_lstock_Rabbit_recipes_en_111490_.pdf", "Rabbit Recipes", "Useful in survival situations.")
    assert audience_bad(SL + "Cookbooks/dainties-1912.pdf", "Dainties", "Recipes for cakes. Home cooks in survival settings would open it.")
    assert not surv_bad("mirrors/ready_gov/x.pdf", "", "survival situations") and not surv_bad("docs/x/y.pdf", "Wilderness Survival Guide", "survival situations")
    assert aud_cut("Recipes for rabbit, useful in survival situations.") == "Recipes for rabbit."
    assert bad_shape("What is X? How does Y work? Students should open it.") and bad_shape("how to preserve mills; for people interested")
    assert not bad_shape("How to weld steel. Welders in small workshops should open it before a repair.")
    assert ECHO.search("It is for farmers and apiarists in that region as described in the excerpt.") and ECHO.search("1. Differences between alternator types. 2. Readers needing basics.")
    assert not s_lang_ok("A practical guide for setting up small-scale artisanal cheese-making operations in Africa, covering technology, processes, and case studies.", "fr")
    assert s_lang_ok("Le document traite de la création d'une petite fromagerie, des procédés techniques et d'expériences concrètes en Afrique.", "fr")
    assert s_lang_ok("Guía en español con 12 acciones para prepararse ante desastres, como hacer planes, ahorrar, practicar simulacros y documentar propiedades.", "es")
    assert garbled("পিরফাiটন ব বহার কের মৎস uৎপাদন পদ িত বর্ণনা কের হয়েছ। " * 20, "bn") and not garbled("পেরিফাইটন ব্যবহার করে মাছ চাষ করার সহজ পদ্ধতি এবং এর সফলতা " * 20, "bn")
    assert garbled("Höôùng daãn söû duïng phaàn meàm vaø caùc ñoà thò trong Excel " * 20, "vi") and not garbled("Hướng dẫn sử dụng phần mềm và các đồ thị trong Excel " * 20, "vi")
    assert not readable("পিরফাiটন ব বহার কের মৎস uৎপাদন পদ িত বর্ণনা কের হয়েছ। " * 60, "docs/cd3wd/2012/x_pa_en_1.pdf", "bn")
    Y3 = lambda t, title, rel="docs/cd3wd/2012/agriculture/_ag_Cassia_en_104910_.pdf": pick_year(t, rel, title)
    assert Y3("WINROCK INTERNATIONAL\nCassia siamea\nNFT Highlights\n1993\nA quick guide", "Cassia Siamea (1993)") == "1993"
    assert Y3("Table 2\n1990 1993 1995 2000\nyields", "Cassia Siamea (1993)") == ""   # a table row is no year source
    assert Y3("Copyright 1991 Winrock\nCassia 1993", "Cassia Siamea (1993)") == "1991"   # a cue beats the title's year
    assert Y3("Published 1993 and reprinted\n", "Cassia (1993, 1997)") == "" and Y3("x 1993 y", "Cassia") == ""
    assert "do not cause epidemics" in S_FIX["docs/death_care/paho_who_icrc_dead_bodies_field_manual_2016.pdf"]
    # RT5 #205: invented survivalist readers on every shelf; survival-themed paths/titles exempt
    SLx = "docs/survivor_library/SurvivalLibrary/library/"
    assert audience_bad(SLx + "Trapping and Hunting/x.pdf", "Carolina Sports", "It is for survivalists interested in historical outdoor activities.")
    assert audience_bad("docs/military_manuals/tm_9-237_welding.pdf", "TM 9-237 Welding", "Preppers stockpiling weapons and ammunition for the coming collapse.")
    assert audience_bad(SLx + "Firearms Manuals/x.pdf", "SIG SG 552", "Für Überlebende, die mit dieser Waffe umgehen müssen.")
    assert audience_bad(SLx + "Survival-Individual/foxfire-two.pdf", "Foxfire Two", "It should be opened by survivalists preparing for long-term isolation.")   # RT7 #205: the folder no longer exempts
    # RT6 L5: "Survivors ... should open it" off the survival paths, and invented reading years, fail; disaster survivors as a topic pass
    assert audience_bad(SLx + "Shipbuilding/through_the_wilderness_of_brazil_1910.pdf", "Through the Wilderness of Brazil (1910)",
                        "Survivors in remote areas should open it when planning travel or understanding local cultures.")
    assert audience_bad(SLx + "Boy Scout Manuals/the_book_of_woodcraft_and_indian_lore_1912.pdf", "The Book of Woodcraft",
                        "Survivors in remote areas should open it when traditional knowledge is scarce.")
    assert audience_bad(SLx + "Survival-Individual/traps.pdf", "Traps", "Survivors should open it when setting up traps.")   # RT7 #205
    assert not audience_bad("docs/cd3wd/2012/emergency/_em_x.pdf", "PCR Tool 6", "Guidance on rebuilding income for disaster survivors.")
    assert audience_bad(SLx + "Printing/x.pdf", "Early Venetian Printing", "It should be opened by historians and book lovers in 2025 or later.")
    # RT10 M4 (#205 regressed, b5 W10; b1mech s17): with the document text, a framing phrase stands only when the text holds the
    # phrase, on every shelf (camping, scouting and survival shelves included); the named-reader tests keep their exemptions
    bk = "the camp is pitched by the river and the woodsman cuts poles; the survival of the old ways depended on it " * 30
    assert frame_bad("Outdoor enthusiasts planning long-term survival trips should open it.", bk).startswith("long-term survival")
    assert audience_bad(SLx + "Boy Scout Manuals/camping_and_woodcraft_vol_2.pdf", "Camping and Woodcraft",
                        "Camping in the wilderness. Outdoor enthusiasts planning long-term survival trips should open it before heading into remote areas.", bk)
    assert audience_bad(SLx + "Survival-Individual/foxfire-one.pdf", "Foxfire One",
                        "Mountain crafts. People preparing for long-term survival should open it when learning practical skills.", bk)
    assert surv_bad(SLx + "Boy Scout Manuals/the_boy_scouts_to_the_rescue_1920.pdf", "The Boy Scouts to the Rescue (1920)",
                    "A story about Boy Scouts, useful for learning teamwork and problem-solving in survival situations.", bk)
    assert surv_bad("docs/cd3wd/2012/agriculture/_ag_ms_405_Yeast_Cottage_Economy_x.pdf", "Yeast Cottage Economy",
                    "Home bakers needing a long-term yeast substitute during food shortages.", bk)
    assert surv_bad(SLx + "Shipbuilding/american_practical_navigation_1920-bowditch.pdf", "American Practical Navigation (1920)",
                    "Seafarers needing to navigate without modern tools should open it before departure.", bk)
    assert not surv_bad(SLx + "Survival-Individual/x.pdf", "Survival Handbook", "Long-term survival planning for a cabin.",
                        bk + " plan for long-term survival in the cabin ")   # the text holds the phrase
    assert not surv_bad("docs/cd3wd/2012/agriculture/x.pdf", "Calves", "Weaning to improve calf survival.", bk)   # biology, not framing
    assert not surv_bad("docs/cd3wd/2012/solar/x.pdf", "Solar lanterns", "For NGOs working in off-grid regions.", bk)   # technical term
    assert surv_bad("docs/cd3wd/2012/agriculture/_ag_lstock_Rabbit_recipes_en_111490_.pdf", "Rabbit Recipes", "Useful in survival situations.")   # no text: shelf rule
    assert frame_bad("for use during food shortages", "bread recipes for wartime rationing " * 40) == ""   # a synonym the 1918 books print
    # #285 C1: digit sentences go, the historical line and abbreviations stay whole
    yf = "A viral disease causing fever and bleeding, with a vaccine available since 1960."
    assert c1(yf) == "" and c1("Plain text. No figures.") == "Plain text. No figures."
    assert c1("A U.S. Army manual from 1944. Soldiers in the field should open it.") == "Soldiers in the field should open it."
    w = "Written in 1890, before antibiotics and modern medicine, it is a historical text, not a guide to treating anyone today."
    assert c1("Home remedies for 12 ailments. " + w) == w and c1("Fevers in vitamin C. " + w) == "Fevers in vitamin C. " + w
    assert c1("Rifle in .300 Win. Mag. oder .308 Win.") == ""
    assert c1("Plans for a ¾” ram pump. Simple build.") == "Simple build." and c1("Absorbs CO₂ from air. Trees.") == "Trees."   # #288
    assert c1("Bombas manuales. Guía de 1998.") == "Bombas manuales." and c1("সৌর ৫ ওয়াট। Solar lamps.") == "Solar lamps."
    e = {"a": "Integers, equations, and geometry. Grade 8 students.", "s": "Plain one-liner for the shelf page.", "l": "en"}
    assert c1_entry(e) == ["a"] and e["a"] == "" and e["c1"] == "a"   # the 4-word remainder is a fragment: dropped too
    e = {"s": yf, "a": "How to treat it, step by step. For nurses on the ward."}
    assert c1_entry(e) == ["s"] and e == {"s": "", "a": "How to treat it, step by step. For nurses on the ward.", "c1": "s"}
    assert c1_entry(e) == [] and e["c1"] == "s"   # rerun: the blank stays marked, nothing else moves
    e["s"] = "A new line."; c1_entry(e); assert "c1" not in e
    print("selftest ok")

def main():
    if "--selftest" in sys.argv:
        return selftest()
    if "--verify" in sys.argv:
        return verify()
    have = json.load(open(OUT))
    # r21: an empty "a" counts as missing (a Google-only scan got its VL "s" after work() had written a="")
    todo = [(k, v) for k, v in have.items() if not v.get("a") and "a" not in v.get("c1", "") and (not ONLY or k.startswith(ONLY)) and not k.startswith(SKIP)
            and (PATHS is None or k in PATHS)]
    # modern shelves first (most asked), then development handbooks, then the historical scans
    todo.sort(key=lambda kv: (kv[0].startswith("docs/survivor_library"), kv[0].startswith(("docs/cd3wd", "docs/school_textbooks")), kv[0]))
    if LIMIT:
        todo = todo[:LIMIT]
    print(f"model={MODEL} threads={THREADS} have={sum('a' in v for v in have.values())} todo={len(todo)}", flush=True)
    lock, t0, n = threading.Lock(), time.time(), [0]
    def save():
        tmp = OUT + ".tmp"
        json.dump(have, open(tmp, "w"), indent=1, ensure_ascii=False, sort_keys=True)
        os.replace(tmp, OUT)
    def one(kv):
        rel, e = kv
        try:
            rel, add = work(rel, e, e.get("_dup", ""))
        except Exception as ex:
            print(f"FAIL {rel}: {ex}", file=sys.stderr, flush=True)
            return
        with lock:
            have[rel].update(add); have[rel].pop("_dup", None); c1_entry(have[rel])   # #285 C1 on the model's answer
            n[0] += 1
            if n[0] % 25 == 0:
                save()
                print(f"...{n[0]}/{len(todo)} {time.time()-t0:.0f}s {rel.split('/')[-1][:50]} -> {add['l']} {add['y']} {add['a'][:70]!r}", flush=True)
    with ThreadPoolExecutor(THREADS) as ex:
        list(ex.map(one, todo))
    save()
    print(f"DONE {n[0]}/{len(todo)} in {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
