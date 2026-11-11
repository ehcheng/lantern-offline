#!/usr/bin/env python3
"""Lantern Library MCP server — stdlib only, Python 3.11+.

JSON-RPC 2.0 over MCP Streamable HTTP (POST /mcp, application/json only).
Six read-only tools; Part 5 content-safety rules enforced server-side.
See docs/mcp/MCP_PLAN.md (v2 amendments are binding).

Usage:
  python3 mcp_server.py --library PATH [--port 8090]
      [--kiwix http://127.0.0.1:8080] [--db PATH]
"""
import argparse
import array
import json
import math
import os
import re
import sqlite3
import sys
import threading
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:  # optional: ~50x faster brute-force scan; pure python fallback below
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

# H37b: cosine floor for semantic candidates (vectors unit-normalised).
# Tuned on server/gold_queries.json (logs/h37_gold.log): nomic's
# cosine baseline is high -- random tokens score ~0.62, real gold hits 0.70+,
# and hit@5 is flat from 0.50 to 0.70, so 0.65 drops the off-topic band
# without losing a hit. Starting guess was 0.60 (R12 log).
# 2026-09-26 sweep on the 86-query eval set (cache/eval/REPORT_floor0{55,60,65}.md):
# 0.60 cut By-feeling empties 15% -> 6% and lifted fused doc@8 0.69 -> 0.72
# and regex@8 0.78 -> 0.83 at flat nDCG/junk; 0.55 killed the last empties
# but cost adversarial nDCG 6 points. Floor 0.60.
SEMANTIC_FLOOR = 0.60
# RT5 E2 (#207, b2 F11): the Spanish Hesperian pages have vectors again, in their own sidecar table (vectors_es). E6 (the owner
# 10-17, "Spanish should NEVER compromise this English-first resource"): that table is scored for Spanish-mode queries
# (lang es/spa) only, never for English or unspecified, so it cannot take an English slot. Its own floor: #144 found the
# English-centred model scores every Spanish page 0.63-0.70 against any Spanish question.
ES_SEMANTIC_FLOOR = 0.60
# K2 sweep 2026-10-17 (t4 v3 Spanish rows + the 36 b2 queries, logs redteam_20261016_fix_k2_sweep_*.log): no cap put 1,681
# loose Hesperian pages above the right CD3WD answers again (v3 65 -> 63: K370 K378, as in #144); a 0.70/0.72 floor also
# dropped right answers (b2 q05 0.69, q20 0.71); at most 3 vectors_es documents per list keeps v3 at its baseline and the
# b2 expected page in /semantic 31/36 (was 0/36).
ES_SEMANTIC_MAX = 3
LANG_MAP = {"eng": "en", "spa": "es", "en": "en", "es": "es"}

PROTOCOL_VERSIONS = {"2024-11-05", "2025-03-26", "2025-06-18"}
DEFAULT_PROTOCOL = "2025-03-26"
SERVER_INFO = {"name": "lantern-library", "version": "1.0.0"}
LIBRARY_HOST = "http://library.lan"
KIWIX_TIMEOUT = 2.0
TEXT_PAGE_CHARS = 8000  # pseudo-page size for html/md/txt pagination

# search.html:156 semantics — token match, single source of truth for keywords
DOSE_KEYWORD_RE = re.compile(  # same list as drugQuery() in search.html (acceptance 2026-10-03: drug classes too)
    r"^(dose|doses|dosage|dosages|dosing|mg|milligram|milligrams|medicine|medicines|medication|medications|antibiotic|antibiotics|painkiller|painkillers|drug|drugs|pill|pills|tablet|tablets|injection|injections|inject|injects|injected|injecting|injectable|injectables|ampoule|ampoules|ampule|ampules|ampul|ampuls|antacid|antacids|laxative|laxatives)$")
# RT6 class 4 (#215, a8 F1): "how many injections for tetanus" named no drug, so the /semantic excerpt quoted "serum
# anti-tetanus (SAT) 2 ampoule". English injection and ampoule words trip the guard like Spanish "inyeccion" (above);
# "shot" and "jab" do too, on a query only, unless the words around them name a wound ("got shot", "shot in the leg",
# "gun shot"): a gunshot question keeps its quotes. Same words and pattern as drugQuery() in search.html and chat.html.
# ponytail: a phrase list, not a parser; "shot" phrasings outside it fall to the dose side (titles, no quotes).
SHOT_WORD_RE = re.compile(r"^(shot|shots|jab|jabs|vial|vials|ampolla|ampollas|ampolleta|ampolletas|ampoule|ampoules|ampule|ampules)$")
# round 10 (#269, a8 F5): «ampolla» is an ampoule and a blister; as a query shot word it counts only beside an injection,
# serum or tetanus word (dose_r39.txt AMPOLLA_CTX_RE, same in search.html / chat.html drugQuery())
AMPOLLA_CTX_RE = re.compile(r"\b(?:inyect\w*|inyecci\w*|suero\w*|vacun\w*|tetan\w*|antiven\w*|antiofidic\w*|antialacran\w*|intramuscular\w*|intraven\w*|im|iv|vial\w*|frasco\w*|jeringa\w*|aguja\w*|ampolletas?|penicilin\w*|antibiotic\w*)\b")
SHOT_WOUND_RE = re.compile(r"\b(?:(?:got|get|gets|getting|was|were|been|being|is|are|accidentally|gun|bullet|arrow|pellet|bird|buck)\s+(?:shot|jabbed)|(?:shot|shots|jab|jabbed)\s+(?:in|through|by|with|at|myself|himself|herself|themselves|me|him|her|them|us|you|wounds?|injur\w*|dead|fired)|shotguns?|gun\s*shots?|gunshots?)\b")
# red team 2026-10-09 (#146): Spanish class words and drug names, accent-folded; same lists as DOSE_ES_RE / DRUGS_ES in
# search.html. guard_drugs from mcp.db stays the English drug list.
DOSE_KEYWORD_ES_RE = re.compile(
    r"^(dosis|medicina|medicinas|medicamento|medicamentos|antibiotico|antibioticos|analgesico|analgesicos|farmaco|farmacos|pastilla|pastillas|tableta|tabletas|comprimido|comprimidos|capsula|capsulas|jarabe|jarabes|inyeccion|inyecciones|miligramo|miligramos|antiacido|antiacidos|laxante|laxantes)$")
DRUGS_ES = set((
    "amoxicilina ampicilina penicilina bencilpenicilina benzatinica espectinomicina doxiciclina tetraciclina eritromicina "
    "azitromicina ciprofloxacina cefalexina cefixima ceftriaxona gentamicina cloranfenicol estreptomicina rifampicina "
    "isoniacida metronidazol cotrimoxazol sulfametoxazol trimetoprima nitrofurantoina clindamicina paracetamol "
    "acetaminofen ibuprofeno aspirina naproxeno diclofenaco codeina morfina tramadol albendazol mebendazol piperazina "
    "praziquantel ivermectina permetrina cloroquina primaquina quinina artemeter fluconazol nistatina clotrimazol "
    "aciclovir misoprostol oxitocina ergometrina insulina metformina prednisona prednisolona dexametasona hidrocortisona "
    "epinefrina adrenalina salbutamol difenhidramina loratadina clorfeniramina diazepam fenobarbital fenitoina "
    "carbamazepina omeprazol loperamida sertralina fluoxetina haloperidol melatonina ricino violeta-de-genciana").split())  # #263 ricino; #264 (P1) the gentian fold
# F2 A1 en58: OTC names missing from mcp.db guard_drugs (same words appended to DRUGS in search.html / chat.html)
DRUGS_EN_EXTRA = set("castor-oil gentian-violet melatonin bismuth pepto-bismol simethicone docusate senna bisacodyl lidocaine benzocaine bacitracin neosporin "
                     "polysporin phenylephrine oxymetazoline afrin chlorpheniramine calcium-carbonate tums milk-of-magnesia "
                     "cotrimoxazole co-trimoxazole cotrimoxazol benzylpenicillin benzathine procaine phenoxymethylpenicillin cloxacillin flucloxacillin dicloxacillin cefixime cefotaxime spectinomycin kanamycin amikacin tinidazole praziquantel niclosamide pyrantel artesunate artemether lumefantrine coartem sulfadoxine pyrimethamine fansidar primaquine quinine mefloquine griseofulvin miconazole clotrimazole zidovudine nevirapine lamivudine efavirenz tenofovir ergometrine methylergometrine carbetocin glibenclamide gliclazide chlorphenamine aminophylline theophylline phenobarbital phenobarbitone amitriptyline chlorpromazine risperidone cimetidine hyoscine atropine ketamine nifedipine enalapril hydralazine methyldopa labetalol tranexamic phytomenadione pyrazinamide ethambutol rifampicin dapsone clofazimine diclofenac mefenamic bupivacaine salbutamol".split())  # G2 b2 F2: MSF essential drugs
# a bare tablet word next to water context is purification, not a drug (en20/es20); a drug name still trips the guard
TABLET_RE = re.compile(r"^(pill|pills|tablet|tablets|tab|tabs|pastilla|pastillas|tableta|tabletas|comprimido|comprimidos)$")
WATER_RE = re.compile(r"\b(water|agua|purif\w*|potabiliz\w*|chlorine|cloro|iodine|yodo|bleach|lejia|aquatabs?)\b")
# #171 (round 4): in a water-treatment TEXT (a snippet, not a query) "dose", "dosage" and "mg" name the amount of
# disinfectant (EPA "Bleach to Water Dose Guidance", WHO "Type and typical dosage: household bleach 4 drops per litre");
# a drug name or a medicine word still trips the guard. Same lists as TREAT_RE / TREAT_WORD_RE in search.html and chat.html.
TREAT_RE = re.compile(r"\b(bleach|chlorin\w*|hypochlorite|cloro|clorad\w*|lejia|blanqueador|iodine|yodo|purif\w*|potabiliz\w*|aquatabs?|disinfect\w*|desinfec\w*)\b")
TREAT_WORD_RE = re.compile(r"^(dose|doses|dosage|dosages|dosing|dosis|mg|milligram|milligrams|miligramo|miligramos)$")
WITHOUT_DRUG_RE = re.compile(r"\b(?:without|w/o|no|other than|instead of|besides|sin|en lugar de|en vez de)\s+(?:any\s+|using\s+|taking\s+|usar\s+|tomar\s+)?(?:medicine|medicines|medication|medications|drugs|pills|medicina|medicinas|medicamentos?|pastillas|farmacos)\b")
# ...and only beside an amount per volume of water ("4 drops per litre", "1 quart/liter 2 drops", "mg/l"): old pharmacy
# books name iodine or chlorine beside "Dose, 2 to 10 minims" and stay withheld
WATER_AMOUNT_RE = re.compile(r"\b(?:drops?|gotas?|teaspoons?|tablespoons?|cucharaditas?|cucharadas?|tablets?|tabletas?|pastillas?|mg|ml|ppm)\s*(?:per|por|/|for\s+each|in\s+each|para\s+cada|cada)\s*(?:\d+\s*)?(?:lit(?:re|er)s?|litros?|l|gal(?:lons?)?|galon(?:es)?|quarts?|qt|cuartos?)\b|\b(?:lit(?:re|er)s?|litros?|gallons?|galon(?:es)?|quarts?)(?:/lit(?:re|er))?\s+\d+\s*(?:drops?|gotas?)\b")
TOKEN_SPLIT_RE = re.compile(r"[^a-z-]+")  # matches search.html drugQuery(), run on accent-folded text
# RT5 a7a S3b (#207): "how do I keep insulin cold?" asks how to store a medicine, not how much to take. On a storage
# question a drug name or medicine word no longer trips the query guard; a dose word (dose, mg, dosis) still does, and
# every snippet still goes through safe_snippet and the page-level dose_page withhold. Same pattern as STORAGE_RE in
# library/search.html drugQuery().
STORAGE_RE = re.compile(r"\b(?:keep|keeping|store|storing|storage|guardar|guardo|conservar|conservo|mantener|mantengo)\b[^.?!]{0,40}\b(?:cold|cool|fresh|refrigerat\w*|fridge|cooler|ice|frozen|freez\w*|heat|hot|warm|temperature|fri[oa]|fresc[oa]|refrigera\w*|nevera|heladera|hielo|calor|temperatura)\b|\b(?:without|with no|no|sin)\s+(?:a\s+)?(?:fridge|refrigerator|refrigeration|electricity|power|nevera|refrigerador|electricidad|luz)\b")
STORAGE_DOSE_RE = re.compile(r"^(dose|doses|dosage|dosages|dosing|mg|milligram|milligrams|dosis|miligramo|miligramos)$")

INSTRUCTIONS = """CONTENT SAFETY RULES (server-enforced; do not attempt to bypass):
1. This library's own pages, summaries and search never state drug doses.
   The medical books on the shelf do: point people to the printed drug guide
   (Davis's, Lippincott pocket) for any dose. A wrong dosage is dangerous.
   This server returns no document text: search_library rows carry title,
   path, page, url, shelf, score and age weight (no snippet), and
   read_document returns text only for the library's own guides
   (RUNBOOK.md, llms.txt, the shelf notes); for any other document it
   returns the url to open. Do not infer, reconstruct, or state drug doses from any source.
2. No plant identification by inference. Never identify a plant as edible or
   medicinal from a description or picture; relay lookalike warnings from the
   library verbatim and unabridged.
3. Home canning and food preservation guidance: USDA / NCHFP tested recipes
   only. Do not improvise processing times or methods.
4. AI must verify against primary sources: any factual claim you relay from
   this library must cite the specific document (title + path) so a human can
   open and verify it. Documents flagged HISTORICAL are outdated — the
   prepended warning must be relayed to the user verbatim.
"""

DOSE_NOTICE = ("This library's own pages, summaries and search never state drug doses. "  # D2 (2026-10-09)
               "The medical books on the shelf do: use the printed drug guide (Davis's, "
               "Lippincott pocket) for any dose. Book quotes are hidden for this search; the "
               "links below still open the full books.")


# ---------------------------------------------------------------- state

class State(object):
    """Loaded once at startup; read-only afterwards (thread-safe)."""

    def __init__(self, library, db_path, kiwix,
                 embed_url=None, emb_db=None):
        self.library = os.path.realpath(library)
        self.db_path = db_path
        self.kiwix = kiwix.rstrip("/")
        self.kiwix_port = urllib.parse.urlparse(self.kiwix).port or 8080
        # R12 semantic sidecar: both optional; absent => keyword-only search
        self.embed_url = embed_url or "http://127.0.0.1:8091/embedding"
        if urllib.parse.urlparse(self.embed_url).hostname not in (
                "127.0.0.1", "localhost", "::1"):  # pinned like kiwix (P0)
            raise ValueError("--embed must point at localhost")
        self.emb_db = emb_db or os.path.join(
            self.library, "_app", "mcp", "embeddings.db")
        self.vec_keys = None   # lazy: [(path, page)]
        self.vec_rows = None   # lazy: numpy (n, dims) or [array('f')], unit rows
        self.vec_lang = None   # lazy: [lang] parallel to vec_keys (from mcp.db)
        self.es_keys, self.es_rows = [], None  # lazy: vectors_es (Spanish Hesperian), Spanish mode only
        self.lang_by_path = {}  # lazy with the vectors: path -> lang (mcp.db), for the English-mode title filter
        self.vec_rows_by_path = None  # lazy: {path: [row index]} for /rerank
        self.titles_by_path = None  # lazy from _app/index/titles.json
        self.title_lang = {}  # lazy with titles_by_path: path -> row language when not English

        with open(os.path.join(self.library, "_app", "index", "shelves.json"),
                  encoding="utf-8") as f:
            self.shelves = json.load(f)
        # v2 P0-2: historical gating source of truth = shelves.json flags
        self.historical_prefixes = [
            s["path"].rstrip("/") + "/" for s in self.shelves
            if s.get("historical")]

        with open(os.path.join(self.library, "_app", "config.json"),
                  encoding="utf-8") as f:
            cfg = json.load(f)
        hr = cfg.get("homeRegion", {})
        self.home_lat = hr.get("lat", 0.0)
        self.home_lon = hr.get("lon", 0.0)

        wpath = os.path.join(self.library, "docs", "HISTORICAL",
                             "README-WARNING.txt")
        try:
            with open(wpath, encoding="utf-8") as f:
                self.historical_warning = f.read().strip()
        except OSError:
            self.historical_warning = ("*** HISTORICAL DOCUMENT - OUTDATED - "
                                       "DO NOT USE FOR PATIENT CARE ***")

        # E22 B (round 8, #238): documents whose catalogue `a` carries the historical line are title-only (no snippet, no
        # excerpt); the list is written by build_mcp_index.py. Missing list: every historical-shelf document is title-only
        # (fails closed).
        try:
            with open(os.path.join(self.library, "_app", "index", "title_only.json"), encoding="utf-8") as f:
                self.title_only_docs = set(json.load(f))
        except (OSError, ValueError):
            sys.stderr.write("title_only.json missing: historical shelves are title-only\n")
            self.title_only_docs = None
        # E27 age weight (round 9, #246): {path: year} for health documents with a catalogue year (build_mcp_index.py);
        # missing list: no weight (the weight is a ranking prior, not a safety layer)
        try:
            with open(os.path.join(self.library, "_app", "index", "health_years.json"), encoding="utf-8") as f:
                self.health_years = json.load(f)
        except (OSError, ValueError):
            sys.stderr.write("health_years.json missing: no age weight\n")
            self.health_years = {}

        con = self.db()
        try:
            self.guard_drugs = set(
                r[0].lower() for r in con.execute("SELECT name FROM guard_drugs"))
        finally:
            con.close()

    def db(self):
        con = sqlite3.connect("file:%s?mode=ro" % self.db_path, uri=True,
                              check_same_thread=False)
        return con

    def is_historical(self, path):
        p = path.lstrip("/")
        return any(p.startswith(pre) for pre in self.historical_prefixes)

    def title_only_doc(self, path):
        p = path.lstrip("/")
        return p in self.title_only_docs if self.title_only_docs is not None else self.is_historical(p)

    def shelf_of(self, path):
        p = path.lstrip("/")
        for s in self.shelves:
            if p.startswith(s["path"].rstrip("/") + "/") or p == s["path"]:
                return s["path"]
        return None


STATE = None  # set in main()
SYNONYMS = {}  # loaded once at startup: term -> expansion (both lowercased)


def _load_synonyms():
    """Load synonyms table into module-level dict at startup."""
    global SYNONYMS
    try:
        con = STATE.db()
        try:
            SYNONYMS = {r[0].lower(): r[1].lower()
                        for r in con.execute("SELECT term, expansion FROM synonyms")}
        finally:
            con.close()
    except Exception:
        SYNONYMS = {}  # graceful degrade if table absent (old db)

# #223 (round 7 b5 R4, six reviewers): "what is amoxicillin for", «para qué sirve el paracetamol» ask what a medicine treats,
# not how much. With no amount word or dose figure in the question the query guard does not trip; every quote still goes
# through safe_snippet and dose_page. Byte-identical to PURPOSE_RE and AMOUNT_RE in library/chat.html decide() (run on
# accent-folded lowercase text there and here).
MAGNESIA_RE = re.compile(r"\b(?:milk of|leche de) magnesia\b")  # same as drugQuery() in search.html / chat.html
CASTOR_RE = re.compile(r"\bcastor oil\b")  # #263: the phrase, not bare castor (castor sugar); dose_r39.txt FOLD_PY
GENTIAN_RE = re.compile(r"\b(?:gentian violet|purple of gentian)\b")  # #264 (P1): not bare gentian (the plant)
GENCIANA_RE = re.compile(r"\bvioleta de genciana\b")  # #264 (P1)
PURPOSE_RE = re.compile(r"\bwhat(?:'s|s| is| are)\b[^.?]{0,40}\b(?:for|used for|good for)\b|\bwhat (?:does|do)\b[^.?]{0,40}\b(?:do|treat|cure)\b|\bpara que (?:sirven?|es|son|se usan?|se toman?)\b")
AMOUNT_RE = re.compile(r"\b(?:how much|how many|how often|what amount|what dose|amount|quantity|doses?|dosage|dosis|cuant[oa]s?|cantidad|cada cuanto|mg|milligrams?|ml|vials?|viales?|frascos?|ampollas?|ampolletas?|ampoules?)\b")
# round 10 (#269, a8 F4): a complaint word stands in for the medicine word of the apothecary branches, in a QUESTION only
# ("two grains for a child with croup", "half an ounce at bedtime for the cough"); never in snippets or dose_page
COMPLAINT_RE = re.compile(r"\b(?:cough\w*|croup|fever\w*|colic\w*|pain\w*|ache\w*|teething|worms?|diarrh\w*|vomit\w*|tos|crup|fiebre|calentura|c[oó]licos?|dolor\w*|lombrices|par[aá]sitos|diarrea|v[oó]mito\w*|dentici[oó]n|t[eé]tanos)\b", re.I)
ANTIVENOM_RE = re.compile(r"\b(?:anti-?venoms?|antivenins?|antiveneno\w*|antiofidic\w*|antiviperin\w*|antialacran\w*|antiescorpion\w*|suero\s+(?:anti\w+|contra\s+(?:el\s+)?veneno)|antitetanic\w*|antitoxins?|antitoxina\w*|(?:cough|fever|pain|teething|baby|children'?s|kids'?|medicine)\s+syrups?|syrups?\s+of\s+\w+)\b")

# round 8 M1 hand-off (#239/#240, a1a en42-en44): amount questions with no drug word ("how many spoons of the pink stuff",
# "how much of the leftover bottle can i give him", "how often and how much can i give the baby for teething pain") trip the
# query guard. Byte-identical to AMOUNT_ASK_RE, RECIPE_RE and FOOD_RE in library/_app/app.js askDose() (fix_f1_test.py checks);
# a recipe, food or water question stays answered.
AMOUNT_ASK_RE = re.compile(r"\b(?:how much|how many|how often|what amount|right amount|quantity|cuant[oa]s?|que cantidad|cada cuanto)\b[^.?]{0,60}\b(?:give|giving|take|dar|doy|damos|darle|tomar|tomo|ponerle|pongo|inject|inyect)\w*\b[^.?]{0,40}(?:\bfor (?:the |his |her |my |a |an )?\w*\s?(?:pain|ache|fever|cough|cold|teething|earache|infection|stomach|diarrh\w*|vomit\w*|rash|allerg\w*|sore|headache|heartburn|malaria|pneumonia|syphilis|gonorrh\w*|tetanus|croup|colic\w*)|\bpara (?:el|la|los|las|su) (?:dolor|fiebre|tos|gripe|gripa|diarrea|infeccion|alergia|oido|muela|vomito|calentura|paludismo|malaria|neumonia|pulmonia|sifilis|gonorrea|tetanos|crup|colicos?))|\bhow much\b[^.?]{0,40}\b(?:malaria|pneumonia|syphilis|gonorrh\w*)\b|\bcuanto\b[^.?]{0,40}\b(?:paludismo|malaria|neumonia|pulmonia|sifilis|gonorrea)\b|\b(?:how much|how many|how often|what amount|right amount|quantity|cuant[oa]s?|cada cuanto|que cantidad)\b[^.?]{0,30}\b(?:spoon\w*|teaspoon\w*|tablespoon\w*|capful\w*|cucharad\w*|cucharadit\w*|tapit\w*|drops?|gotas?|gotitas?|syrups?|jarabes?|stuff|bottle|frascos?|botella|(?:cough|fever|pain|baby|medicine|tummy|stomach) mixtures?|tonics?|tonicos?|million units?|millones (?:de unidades|ui)|vials?|ampoules?|ampollas?|ampolletas?|antiven\w*|antiofidic\w*|suero anti\w*|pastillitas?|pildoritas?)\b")
RECIPE_RE = re.compile(r"\b(?:sugar|salt|azucar|sal|suero casero|suero oral|rehydrat\w*|rehidrat\w*|ors|flour|harina|coffee|tea|yeast|levadura|maple|pancakes?|waffles?|recipes?|cakes?|bak\w*|sap|honey|miel|jam|jelly|mermelada|canning|conserv\w*)\b")
FOOD_RE = re.compile(r"\b(?:eat|food|feed|comer|comida|alimento|leche|milk|formula)\b")
# a8 F2 (round 9, #252): the rest of the page's askDose() words, byte-identical to library/_app/app.js (the router, M1;
# fix_f1_test.py checks): "what do i give and how much", "how many drops", "how much injection" (not shotgun shot)
GIVE_RE = re.compile(r"\b(?:que|what|which)\b[^.?]{0,30}\b(?:le doy|le damos|le puedo dar|le tengo que dar|tomo|tomar|give|take)\b[^.?]{0,40}(?:\bcuanto\b|\bcada cuanto\b|\bhow (?:much|often|many)\b|\bbotiquin\b|\bfirst.aid kit\b)|\b(?:cuant[oa]s?|cada cuanto)\b[^.?]{0,20}\ble (?:doy|damos|puedo dar)\b")
DROPS_RE = re.compile(r"\b(?:how many|cuant[oa]s)\b[^.?]{0,25}\b(?:drops?|gotas?|gotitas?)\b")
SHOT_RE = re.compile(r"\b(?:how much|how many|what amount|which amount|what dose|how big)\b[^.?]{0,30}\b(?:injections?|inject\w*|shots?|jabs?|vaccines?|cc)\b|\b(?:injections?|shots?|jabs?)\b[^.?]{0,30}\b(?:how much|how many|how often|what amount)\b|\bcuant[oa]s?\b[^.?]{0,30}\b(?:inyect|inyecci|vacuna|cc\b)|\b(?:inyect|inyecci|vacuna)\w*\b[^.?]{0,30}\bcuant[oa]s?\b")
GUN_RE = re.compile(r"\b(?:gauge|shotgun|shells?|reload\w*|powder|buckshot|birdshot|camera|photos?|espresso|whiske?y|tequila|vodka)\b")
# M2 follow-up 1 (round 9, #252 #246): the keyword amount forms ("drops ear infection how many", "mg for earache",
# «jarabe tos cuánto niño») and the swallowed-amount exemption, byte-identical to library/_app/app.js (fix_f1_test.py checks)
KEYDOSE_RE = re.compile(r"\b(?:how (?:many|much|often)|cuant[oa]s?|cada cuanto)\b[^.?]{0,40}\b(?:drops?|gotas?|gotitas?|pills?|tablets?|pastillas?|pastillitas?|capsul\w*|syrups?|jarabes?|spoon\w*|teaspoon\w*|tablespoon\w*|cucharad\w*|suppositor\w*|supositori\w*|puffs?|inhalers?|ointments?|pomadas?|unguent\w*|colirios?)\b|\b(?:drops?|gotas?|gotitas?|pills?|tablets?|pastillas?|pastillitas?|capsul\w*|syrups?|jarabes?|spoon\w*|teaspoon\w*|tablespoon\w*|cucharad\w*|suppositor\w*|supositori\w*|puffs?|inhalers?|ointments?|pomadas?|unguent\w*|colirios?)\b[^.?]{0,40}\b(?:how (?:many|much|often)|cuant[oa]s?|cada cuanto)\b|\b(?:mg|milligrams?|miligramos?|ml|mililitros?|cc|doses?|dosage|dosis|dosing)\b[^.?]{0,40}\b(?:croup|crup|colic\w*|tetan\w*|fever|fiebre|calentura|ear\w*|infection|infeccion|pain|dolor|aches?|cough|tos|tooth\w*|muelas?|headache|migraine|diarr\w*|vomit\w*|oidos?|eyes?|ojos?|baby|bebes?|toddler|child|kids?|nin[oa]s?|years? old|anos|months? old|meses|kg|kilos?|pounds?|lbs?)\b|\b(?:croup|crup|colic\w*|tetan\w*|fever|fiebre|calentura|earache|ear infection|infection|infeccion|pain|dolor|cough|tos|toothache|muelas?|headache|diarr\w*|oidos?|baby|bebes?|toddler|child|nin[oa]s?)\b[^.?]{0,40}\b(?:mg|milligrams?|miligramos?|ml|mililitros?|doses?|dosage|dosis)\b|\b(?:spoon\w*|teaspoon\w*|tablespoon\w*|cucharad\w*|capful\w*|tapitas?)\b[^.?]{0,20}\b(?:syrups?|jarabes?|medicines?|medicina|medicamentos?|remedios?)\b|\b(?:minims?|grains?|granos?|ounces?|onzas?|drams?|drachms?|dracmas?)\b[^.?]{0,40}\b(?:croup|crup|colic\w*|tetan\w*|fever|fiebre|calentura|cough|tos|pain|dolor|diarr\w*|vomit\w*|teething|baby|bebes?|toddler|child|kids?|nin[oa]s?)\b|\b(?:how much|cuant[oa]s?)\b[^.?]{0,20}\b(?:creams?|cremas?)\b[^.?]{0,30}\b(?:rash\w*|sarpullido|rozadura|eczema|itch\w*|comezon|infection|infeccion|fung\w*|hongos?|burns?|quemadura|wound|herida)\b")
INGEST_RE = re.compile(r"\b(?:swallow\w*|ate|eaten|took|taken|got into|overdos\w*|trag\w*|se (?:tomo|comio|bebio)|sobredosis|ingiri\w*|accidental\w*|on purpose|a proposito)\b")


def ask_dose(folded):
    """The page's askDose() boolean (library/_app/app.js), on accent-folded lower-case text."""
    return bool((GIVE_RE.search(folded) or DROPS_RE.search(folded) or (SHOT_RE.search(folded) and not GUN_RE.search(folded))
                 or (AMOUNT_ASK_RE.search(folded) and not RECIPE_RE.search(folded))
                 or (KEYDOSE_RE.search(folded) and not INGEST_RE.search(folded) and not RECIPE_RE.search(folded)))
                and not WATER_RE.search(folded) and not FOOD_RE.search(folded))

# ---------------------------------------------------------------- guards

def dose_guard(query, text=False):
    """Decision made ONCE per query; applies to ALL result sources (P0-4). text=True: the snippet rule (safe_snippet)."""
    folded = "".join(c for c in unicodedata.normalize("NFD", query.lower()) if not unicodedata.combining(c))
    folded = CASTOR_RE.sub(" castor-oil ", MAGNESIA_RE.sub(" milk-of-magnesia ", folded))  # #228 #263: the phrases
    folded = GENCIANA_RE.sub(" violeta-de-genciana ", GENTIAN_RE.sub(" gentian-violet ", folded))  # #264 (P1)
    if not text and PURPOSE_RE.search(folded) and not AMOUNT_RE.search(folded) and not DOSE_FIGURE.search(query):
        return False  # #223: a purpose question
    if not text and ask_dose(folded):
        return True  # same rule as askDose() in library/_app/app.js (round 9 a8 F2: GIVE_RE, DROPS_RE, SHOT_RE; KEYDOSE_RE too)
    if not text and DOSE_FIGURE.search(COMPLAINT_RE.sub(r"\g<0> dose", query)):
        return True  # a8 F2: an amount in the question («dos ampolletas para el tétanos»), as the page's hasDose(q) refuses; round 10 a8 F4: a complaint word counts as the medicine word
    if not text and ANTIVENOM_RE.search(folded) and (AMOUNT_RE.search(folded) or DOSE_FIGURE.search(query)):
        return True  # round 8 a8 F1: "how many vials of antivenom", «tres ampollas de suero antiofídico»
    water = bool(WATER_RE.search(folded))
    if text:  # #171: "iodine in your medicine cabinet" (EPA) names a cupboard, not a medicine
        folded = re.sub(r"\bmedicine cabinets?\b", " ", folded)
    else:  # #193 (a1a en60): "stress and anxiety without medicine" asks for no drug; a drug name still trips
        folded = SHOT_WOUND_RE.sub(" ", WITHOUT_DRUG_RE.sub(" ", folded))
    treat = text and bool(TREAT_RE.search(folded)) and bool(WATER_AMOUNT_RE.search(folded))
    storage = not text and bool(STORAGE_RE.search(folded))
    for tok in TOKEN_SPLIT_RE.split(folded):
        if not tok or (water and TABLET_RE.match(tok)) or (treat and TREAT_WORD_RE.match(tok)):
            continue
        if storage and not STORAGE_DOSE_RE.match(tok):
            continue
        if (DOSE_KEYWORD_RE.match(tok) or DOSE_KEYWORD_ES_RE.match(tok) or tok in DRUGS_ES or tok in DRUGS_EN_EXTRA
                or tok in STATE.guard_drugs or (not text and SHOT_WORD_RE.match(tok)
                                                and (not tok.startswith("ampolla") or AMPOLLA_CTX_RE.search(folded)))):
            return True
    return False


# read_document guard (red team 2026-10-03 A6): the search guard hides book quotes, but a client that read a page
# of a drug formulary got the table. DOSE_FIGURE must stay identical to DOSE in build/acceptance_run.py,
# DOSE in gen_doc_answers.py and DOSE_RE in library/search.html (redteam_20261009_scripts/fix_f1_test.py checks).
# 2026-10-09 (#146 #149): English + Spanish units, counts and frequencies; a range or compound goes whole ("200 to
# 400 mg", "de 10 a 15 mg por kg de peso", "4 veces al día por 7 días"); ORS and water-treatment amounts ("de sal",
# "of sugar", "per litre", "mg/l") are not doses and stay.
# RT6 class 4 (#215, a8 F1): ampoule / ampolla / ampolleta / vial / frasco-ampolla are units ("serum anti-tetanus (SAT)
# 2 ampoule", "one vial"), and "2,4 millones UI" goes whole. The source line of every copy is in
# the private test record
DOSE_FIGURE = re.compile(r"(?!(?<=iphone\s)[2-5]\s?g\b)(?!(?<=phone\s)[2-5]\s?g\b)(?![2-5]\s?g\b(?=\s*(?:lte|networks?|phones?|iphones?|modems?|signal|wi-?fi|cellular|data|service|coverage|speeds?|internet|front|back|screen|battery|case|replacement|red|se[nñ]al|celular|m[oó]vil)\b))(?<!\bFM\s)(?<!\bTM\s)(?<!\bTC\s)(?<!\bATP\s)(?<!\bSTP\s)(?<!\d-)(?<!\d\.)(?<!gallon\s)(?<!gallons\s)(?<!quart\s)(?<!quarts\s)(?<!liter\s)(?<!liters\s)(?<!litre\s)(?<!litres\s)(?<!litro\s)(?<!litros\s)(?<!gal[oó]n\s)(?<!galones\s)(?<!barrel\s)(?<!barrels\s)(?<!barril\s)(?<!barriles\s)(?<!drum\s)(?<!drums\s)(?<!tank\s)(?<!tanks\s)(?<!tambo\s)(?<!tambos\s)(?<!tanque\s)(?<!tanques\s)(?<!drops\s\()(?<!gotas\s\()(?<!\d\/)(?<!\d\/)(?<!\d\/)(?!(?<=\bdrops\s)\d+\s*drops\b)(?!(?<=\bgotas\s)\d+\s*gotas\b)(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*(?:(?:parte\s+)?de\s+(?:una?\s+)?)?(?:mg|mcg|µg|ug|g|ml|cc|mililitros?|millilit(?:er|re)s?|m\s?iu|m\s?ui|iu|ui|(?:million|mill[oó]n(?:es)?)\s+(?:de\s+)?(?:(?:international\s+)?(?:units?|unidades)|ui|iu)|units?|unidades|grams?|gramos?|milligrams?|miligramos?|micrograms?|microgramos?|tabs?|tablets?|tabletas?|pills?|pastillas?|comprimidos?|caps?|capsules?|c[aá]psulas?|(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|capfuls?|dropperfuls?|tsp|tbsp|c[àá]c|c[àá]s|c\.[àá]\.[cs](?=\.)|cucharaditas?|cucharadas?|drops?|gotas?|ampoules?|ampules?|ampuls?|ampollas?|ampolletas?|vials?|frascos?[-\s]ampollas?)\b(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))(?:\s*(?:\/|per|por(?:\s+cada)?)\s*(?:kg|kilos?|kilogramos?|kilograms?|d[ií]a|day|dose|dosis|m2)\b(?:\s+(?:of\s+body\s+weight|de\s+peso(?:\s+corporal)?))?)*(?:\s*x\s*\d+(?:\s*(?:[-–]|or|o|to|a)\s*\d+)?\b)?(?:,?\s+(?:daily|a\s+day|per\s+day|each\s+day|al\s+d[ií]a|por\s+d[ií]a|cada\s+d[ií]a|diari[oa]s?))?|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|o|ó|u|a|y|and)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+(?:of\s+)?an?)?|cuarto\s+de(?:\s+una?)?|an?(?=\s+(?:(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|capfuls?|dropperfuls?|ampoules?|ampules?|vials?)\b))\s+(?:tabletas?|pastillas?|comprimidos?|c[aá]psulas?|tablets?|pills?|capsules?|ampoules?|ampules?|vials?|(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|capfuls?|dropperfuls?|cucharaditas?|cucharadas?|goteros?|ampolletas?|frascos?[-\s]ampollas?|drops?|gotas?|ampollas?(?=\s+(?:de\s+(?:\w*ina\b|suero|antiveneno|antiof[ií]dico|antitet[aá]nic)|i\.?[mv]\b|intramuscular|intraven)))\b(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))(?:\s*(?:\/|per|por(?:\s+cada)?)\s*(?:kg|kilos?|kilogramos?|kilograms?|d[ií]a|day|dose|dosis|m2)\b(?:\s+(?:of\s+body\s+weight|de\s+peso(?:\s+corporal)?))?)*(?:\s*x\s*\d+(?:\s*(?:[-–]|or|o|to|a)\s*\d+)?\b)?(?:,?\s+(?:daily|a\s+day|per\s+day|each\s+day|al\s+d[ií]a|por\s+d[ií]a|cada\s+d[ií]a|diari[oa]s?))?|(?:(?=every\s|cada\s)(?<!compost\s)(?<!pile\s)(?<!dough\s)(?<!wake\s)(?<!wake\sthem\s)(?<!wake\shim\s)(?<!wake\sher\s)(?<!wake\sit\s)(?<!wake\sup\s)(?<!wake\sthem\sup\s)(?<!wake\shim\sup\s)(?<!wake\sher\sup\s)(?<!wake\son\sthem\s)(?<!wake\son\shim\s)(?<!wake\son\sher\s)(?<!wake\sthe\sperson\s)(?<!wake\sthe\schild\s)(?<!wake\sthe\sbaby\s)(?<!wake\sthe\spatient\s)(?<!wake\son\sthe\sperson\s)(?<!wake\son\sthe\schild\s)(?<!wake\son\sthe\spatient\s)(?<!waken\s)(?<!waken\sthem\s)(?<!waken\shim\s)(?<!waken\sher\s)(?<!waken\sit\s)(?<!waken\sup\s)(?<!waken\sthem\sup\s)(?<!waken\shim\sup\s)(?<!waken\sher\sup\s)(?<!waken\son\sthem\s)(?<!waken\son\shim\s)(?<!waken\son\sher\s)(?<!waken\sthe\sperson\s)(?<!waken\sthe\schild\s)(?<!waken\sthe\sbaby\s)(?<!waken\sthe\spatient\s)(?<!waken\son\sthe\sperson\s)(?<!waken\son\sthe\schild\s)(?<!waken\son\sthe\spatient\s)(?<!awaken\s)(?<!awaken\sthem\s)(?<!awaken\shim\s)(?<!awaken\sher\s)(?<!awaken\sit\s)(?<!awaken\sup\s)(?<!awaken\sthem\sup\s)(?<!awaken\shim\sup\s)(?<!awaken\sher\sup\s)(?<!awaken\son\sthem\s)(?<!awaken\son\shim\s)(?<!awaken\son\sher\s)(?<!awaken\sthe\sperson\s)(?<!awaken\sthe\schild\s)(?<!awaken\sthe\sbaby\s)(?<!awaken\sthe\spatient\s)(?<!awaken\son\sthe\sperson\s)(?<!awaken\son\sthe\schild\s)(?<!awaken\son\sthe\spatient\s)(?<!waking\s)(?<!waking\sthem\s)(?<!waking\shim\s)(?<!waking\sher\s)(?<!waking\sit\s)(?<!waking\sup\s)(?<!waking\sthem\sup\s)(?<!waking\shim\sup\s)(?<!waking\sher\sup\s)(?<!waking\son\sthem\s)(?<!waking\son\shim\s)(?<!waking\son\sher\s)(?<!waking\sthe\sperson\s)(?<!waking\sthe\schild\s)(?<!waking\sthe\sbaby\s)(?<!waking\sthe\spatient\s)(?<!waking\son\sthe\sperson\s)(?<!waking\son\sthe\schild\s)(?<!waking\son\sthe\spatient\s)(?<!check\s)(?<!check\sthem\s)(?<!check\shim\s)(?<!check\sher\s)(?<!check\sit\s)(?<!check\sup\s)(?<!check\sthem\sup\s)(?<!check\shim\sup\s)(?<!check\sher\sup\s)(?<!check\son\sthem\s)(?<!check\son\shim\s)(?<!check\son\sher\s)(?<!check\sthe\sperson\s)(?<!check\sthe\schild\s)(?<!check\sthe\sbaby\s)(?<!check\sthe\spatient\s)(?<!check\son\sthe\sperson\s)(?<!check\son\sthe\schild\s)(?<!check\son\sthe\spatient\s)(?<!checking\s)(?<!checking\sthem\s)(?<!checking\shim\s)(?<!checking\sher\s)(?<!checking\sit\s)(?<!checking\sup\s)(?<!checking\sthem\sup\s)(?<!checking\shim\sup\s)(?<!checking\sher\sup\s)(?<!checking\son\sthem\s)(?<!checking\son\shim\s)(?<!checking\son\sher\s)(?<!checking\sthe\sperson\s)(?<!checking\sthe\schild\s)(?<!checking\sthe\sbaby\s)(?<!checking\sthe\spatient\s)(?<!checking\son\sthe\sperson\s)(?<!checking\son\sthe\schild\s)(?<!checking\son\sthe\spatient\s)(?<!recheck\s)(?<!recheck\sthem\s)(?<!recheck\shim\s)(?<!recheck\sher\s)(?<!recheck\sit\s)(?<!recheck\sup\s)(?<!recheck\sthem\sup\s)(?<!recheck\shim\sup\s)(?<!recheck\sher\sup\s)(?<!recheck\son\sthem\s)(?<!recheck\son\shim\s)(?<!recheck\son\sher\s)(?<!recheck\sthe\sperson\s)(?<!recheck\sthe\schild\s)(?<!recheck\sthe\sbaby\s)(?<!recheck\sthe\spatient\s)(?<!recheck\son\sthe\sperson\s)(?<!recheck\son\sthe\schild\s)(?<!recheck\son\sthe\spatient\s)(?<!despi[eé]rtela\s)(?<!despi[eé]rtela\sa\sla\spersona\s)(?<!despi[eé]rtela\sal\sni[nñ]o\s)(?<!despi[eé]rtela\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtela\sal\senfermo\s)(?<!despi[eé]rtela\sa\sla\senferma\s)(?<!despi[eé]rtela\sal\sbeb[eé]\s)(?<!despi[eé]rtelo\s)(?<!despi[eé]rtelo\sa\sla\spersona\s)(?<!despi[eé]rtelo\sal\sni[nñ]o\s)(?<!despi[eé]rtelo\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtelo\sal\senfermo\s)(?<!despi[eé]rtelo\sa\sla\senferma\s)(?<!despi[eé]rtelo\sal\sbeb[eé]\s)(?<!despi[eé]rtele\s)(?<!despi[eé]rtele\sa\sla\spersona\s)(?<!despi[eé]rtele\sal\sni[nñ]o\s)(?<!despi[eé]rtele\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtele\sal\senfermo\s)(?<!despi[eé]rtele\sa\sla\senferma\s)(?<!despi[eé]rtele\sal\sbeb[eé]\s)(?<!despi[eé]rtenla\s)(?<!despi[eé]rtenla\sa\sla\spersona\s)(?<!despi[eé]rtenla\sal\sni[nñ]o\s)(?<!despi[eé]rtenla\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtenla\sal\senfermo\s)(?<!despi[eé]rtenla\sa\sla\senferma\s)(?<!despi[eé]rtenla\sal\sbeb[eé]\s)(?<!despi[eé]rtenlo\s)(?<!despi[eé]rtenlo\sa\sla\spersona\s)(?<!despi[eé]rtenlo\sal\sni[nñ]o\s)(?<!despi[eé]rtenlo\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtenlo\sal\senfermo\s)(?<!despi[eé]rtenlo\sa\sla\senferma\s)(?<!despi[eé]rtenlo\sal\sbeb[eé]\s)(?<!despi[eé]rtenle\s)(?<!despi[eé]rtenle\sa\sla\spersona\s)(?<!despi[eé]rtenle\sal\sni[nñ]o\s)(?<!despi[eé]rtenle\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtenle\sal\senfermo\s)(?<!despi[eé]rtenle\sa\sla\senferma\s)(?<!despi[eé]rtenle\sal\sbeb[eé]\s)(?<!despi[eé]rtala\s)(?<!despi[eé]rtala\sa\sla\spersona\s)(?<!despi[eé]rtala\sal\sni[nñ]o\s)(?<!despi[eé]rtala\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtala\sal\senfermo\s)(?<!despi[eé]rtala\sa\sla\senferma\s)(?<!despi[eé]rtala\sal\sbeb[eé]\s)(?<!despi[eé]rtalo\s)(?<!despi[eé]rtalo\sa\sla\spersona\s)(?<!despi[eé]rtalo\sal\sni[nñ]o\s)(?<!despi[eé]rtalo\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtalo\sal\senfermo\s)(?<!despi[eé]rtalo\sa\sla\senferma\s)(?<!despi[eé]rtalo\sal\sbeb[eé]\s)(?<!despertarla\s)(?<!despertarla\sa\sla\spersona\s)(?<!despertarla\sal\sni[nñ]o\s)(?<!despertarla\sa\sla\sni[nñ]a\s)(?<!despertarla\sal\senfermo\s)(?<!despertarla\sa\sla\senferma\s)(?<!despertarla\sal\sbeb[eé]\s)(?<!despertarlo\s)(?<!despertarlo\sa\sla\spersona\s)(?<!despertarlo\sal\sni[nñ]o\s)(?<!despertarlo\sa\sla\sni[nñ]a\s)(?<!despertarlo\sal\senfermo\s)(?<!despertarlo\sa\sla\senferma\s)(?<!despertarlo\sal\sbeb[eé]\s)(?<!despertarle\s)(?<!despertarle\sa\sla\spersona\s)(?<!despertarle\sal\sni[nñ]o\s)(?<!despertarle\sa\sla\sni[nñ]a\s)(?<!despertarle\sal\senfermo\s)(?<!despertarle\sa\sla\senferma\s)(?<!despertarle\sal\sbeb[eé]\s)(?<!despierte\s)(?<!despierte\sa\sla\spersona\s)(?<!despierte\sal\sni[nñ]o\s)(?<!despierte\sa\sla\sni[nñ]a\s)(?<!despierte\sal\senfermo\s)(?<!despierte\sa\sla\senferma\s)(?<!despierte\sal\sbeb[eé]\s)(?<!despertar\s)(?<!despertar\sa\sla\spersona\s)(?<!despertar\sal\sni[nñ]o\s)(?<!despertar\sa\sla\sni[nñ]a\s)(?<!despertar\sal\senfermo\s)(?<!despertar\sa\sla\senferma\s)(?<!despertar\sal\sbeb[eé]\s)(?<!rev[ií]sela\s)(?<!rev[ií]sela\sa\sla\spersona\s)(?<!rev[ií]sela\sal\sni[nñ]o\s)(?<!rev[ií]sela\sa\sla\sni[nñ]a\s)(?<!rev[ií]sela\sal\senfermo\s)(?<!rev[ií]sela\sa\sla\senferma\s)(?<!rev[ií]sela\sal\sbeb[eé]\s)(?<!rev[ií]selo\s)(?<!rev[ií]selo\sa\sla\spersona\s)(?<!rev[ií]selo\sal\sni[nñ]o\s)(?<!rev[ií]selo\sa\sla\sni[nñ]a\s)(?<!rev[ií]selo\sal\senfermo\s)(?<!rev[ií]selo\sa\sla\senferma\s)(?<!rev[ií]selo\sal\sbeb[eé]\s)(?<!rev[ií]sele\s)(?<!rev[ií]sele\sa\sla\spersona\s)(?<!rev[ií]sele\sal\sni[nñ]o\s)(?<!rev[ií]sele\sa\sla\sni[nñ]a\s)(?<!rev[ií]sele\sal\senfermo\s)(?<!rev[ií]sele\sa\sla\senferma\s)(?<!rev[ií]sele\sal\sbeb[eé]\s)(?<!revise\s)(?<!revise\sa\sla\spersona\s)(?<!revise\sal\sni[nñ]o\s)(?<!revise\sa\sla\sni[nñ]a\s)(?<!revise\sal\senfermo\s)(?<!revise\sa\sla\senferma\s)(?<!revise\sal\sbeb[eé]\s)(?<!revisar\s)(?<!revisar\sa\sla\spersona\s)(?<!revisar\sal\sni[nñ]o\s)(?<!revisar\sa\sla\sni[nñ]a\s)(?<!revisar\sal\senfermo\s)(?<!revisar\sa\sla\senferma\s)(?<!revisar\sal\sbeb[eé]\s)(?<!revisarla\s)(?<!revisarla\sa\sla\spersona\s)(?<!revisarla\sal\sni[nñ]o\s)(?<!revisarla\sa\sla\sni[nñ]a\s)(?<!revisarla\sal\senfermo\s)(?<!revisarla\sa\sla\senferma\s)(?<!revisarla\sal\sbeb[eé]\s)(?<!revisarlo\s)(?<!revisarlo\sa\sla\spersona\s)(?<!revisarlo\sal\sni[nñ]o\s)(?<!revisarlo\sa\sla\sni[nñ]a\s)(?<!revisarlo\sal\senfermo\s)(?<!revisarlo\sa\sla\senferma\s)(?<!revisarlo\sal\sbeb[eé]\s)(?<!vig[ií]lela\s)(?<!vig[ií]lela\sa\sla\spersona\s)(?<!vig[ií]lela\sal\sni[nñ]o\s)(?<!vig[ií]lela\sa\sla\sni[nñ]a\s)(?<!vig[ií]lela\sal\senfermo\s)(?<!vig[ií]lela\sa\sla\senferma\s)(?<!vig[ií]lela\sal\sbeb[eé]\s)(?<!vig[ií]lelo\s)(?<!vig[ií]lelo\sa\sla\spersona\s)(?<!vig[ií]lelo\sal\sni[nñ]o\s)(?<!vig[ií]lelo\sa\sla\sni[nñ]a\s)(?<!vig[ií]lelo\sal\senfermo\s)(?<!vig[ií]lelo\sa\sla\senferma\s)(?<!vig[ií]lelo\sal\sbeb[eé]\s)(?<!vig[ií]lele\s)(?<!vig[ií]lele\sa\sla\spersona\s)(?<!vig[ií]lele\sal\sni[nñ]o\s)(?<!vig[ií]lele\sa\sla\sni[nñ]a\s)(?<!vig[ií]lele\sal\senfermo\s)(?<!vig[ií]lele\sa\sla\senferma\s)(?<!vig[ií]lele\sal\sbeb[eé]\s)(?<!vigile\s)(?<!vigile\sa\sla\spersona\s)(?<!vigile\sal\sni[nñ]o\s)(?<!vigile\sa\sla\sni[nñ]a\s)(?<!vigile\sal\senfermo\s)(?<!vigile\sa\sla\senferma\s)(?<!vigile\sal\sbeb[eé]\s)(?<!vigilar\s)(?<!vigilar\sa\sla\spersona\s)(?<!vigilar\sal\sni[nñ]o\s)(?<!vigilar\sa\sla\sni[nñ]a\s)(?<!vigilar\sal\senfermo\s)(?<!vigilar\sa\sla\senferma\s)(?<!vigilar\sal\sbeb[eé]\s)(?<!vigilarla\s)(?<!vigilarla\sa\sla\spersona\s)(?<!vigilarla\sal\sni[nñ]o\s)(?<!vigilarla\sa\sla\sni[nñ]a\s)(?<!vigilarla\sal\senfermo\s)(?<!vigilarla\sa\sla\senferma\s)(?<!vigilarla\sal\sbeb[eé]\s)(?<!vigilarlo\s)(?<!vigilarlo\sa\sla\spersona\s)(?<!vigilarlo\sal\sni[nñ]o\s)(?<!vigilarlo\sa\sla\sni[nñ]a\s)(?<!vigilarlo\sal\senfermo\s)(?<!vigilarlo\sa\sla\senferma\s)(?<!vigilarlo\sal\sbeb[eé]\s)(?:every|cada)\s+(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)|\b(?:two|three|four|five|six|seven|eight|nine|ten|twelve|twenty-four|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|veinticuatro)(?:\s+(?:to|or|and|o|a|y)\s+(?:two|three|four|five|six|seven|eight|nine|ten|twelve|twenty-four|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|veinticuatro))?)\s*(?:h|hrs?|hours?|horas?)\b(?!\s*,?\s*(?:turn|stir|mix|knead|rotate)\b)|(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)|(?:one|two|three|four|five|six|una|dos|tres|cuatro|cinco|seis))\s*(?:times?|x|veces|vez)\s*(?:(?:a|per|al|por|each|cada)\s*(?:day|d[ií]a)|daily|diari[oa]s?)|(?:once|twice|thrice)\s+(?:(?:a|per|each)\s+day|daily)|(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s+(?:doses|dosis)\b)(?:,?\s*(?:for|por|durante)\s+(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*(?:days?|d[ií]as|weeks?|semanas)\b)?|(?:en\s+)?una\s+sola\s+dosis|\b1\s+sola\s+vez|(?:again|repeat(?:ed)?|otra\s+vez|de\s+nuevo|repetir|repita)\s+(?:in|after|en|despu[eé]s\s+de)\s+(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*(?:h|hrs?|hours?|horas?)\b|\b(?:every\s+(?:[\w-]+\s+){0,2}?hours?|hourly|cada\s+(?:\w+\s+){0,2}?horas?|doses?|dosis|dosage|given|give|gives|giving|administer\w*|administr\w*|take|takes|taken|inject\w*|ivermectin|dele|dale|darle|dar|d[eé]selo|d[eé]sele|tome|tomar|toma|tomando|tinctures?|tintura|infusions?|infusi[oó]n|decoctions?|remed(?:y|ies)|remedios?|medicinal(?:ly)?|medicines?|medicinas?|mixtures?|prescrib\w*|recommend\w*|purgatives?|purgantes?|cathartics?|emetics?|vomitivos?|antispasmodic|anodyne|laxatives?|laxantes?|tonics?|t[oó]nicos?|physic|draughts?|drench\w*|bolus|pills?|liniments?|ointments?|salves?|embrocations?|poultices?|gargles?|lotions?|eye-?waters?|collyri\w*|pomadas?|ung[uü]entos?|linimentos?|cataplasmas?|quinine|quinina|opium|opio|laudanum|l[aá]udano|morphi\w*|morfina|calomel|camphor\w*|alcanfor|digitalis|foxglove|strychni\w*|estricnina|bromides?|bromuro|salicin|salicyl\w*|buchu|creosote|creosota|elaterium|ipecac\w*|paregoric|parag[oó]rico|castor\s+oil|ricino|epsom|glauber|iodides?|yoduro|aloes|rhubarb|ruibarbo|senna|jalap|turpentine|trementina|chloral|chloroform|cloroformo|ether|belladonn?a|aconite|ac[oó]nito|ergot\w*|arseni\w*|ars[eé]nico|mercury|mercurio|antitoxins?|antitoxina|serum|suero|antimony|tartar\s+emetic|pine\s+tar|penny\s*royal|carbolic|creolin|sulphur|azufre|magnesia|bismuth|santonin|cocaine|atropine|aspirin\w*|chlorodyne|squills?|antipyrin\w*|acetanilid\w*|phenacetin|cod[\s-]liver\s+oil|vermifuge|nux\s+vomica|nitre|lobelia|asaf\w*tida|valerian|hyoscyam\w*|cannabis|cantharides|croton\s+oil|podophyll\w*|sarsaparilla|guaiac\w*|colchicum|stramonium|hellebore|savin|tansy|wormwood|quassia|gentian|cinchona)\b[^;!?]{0,80}?(?:(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:fluid\s+|fl\.\s*)?(?:(?:grains?|minims?|drachms?|drams?|ounces?|gills?|scruples?|granos?|dracmas?|onzas?|escr[uú]pulos?)\b|(?:grs?|oz)(?:\.|\b)|oz\b|c\.\s?c\.)|\b(?:a\s+few\s+drops|a\s+drop\s+or\s+two|unas\s+(?:cuantas\s+|pocas\s+)?gotas)\b)(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))(?!\s*(?:(?:of|de)\s+)?(?:wheat|corn|oats?|barley|rye|bran|meal|seeds?|feed|hay|yeast|lard|suet|starch|gelatine?|cheese|meat|beef|tea(?!\s+tree)|coffee|cocoa|chocolate|vinegar|gold|silver|sand|clay|wax|beeswax|rosin|resin|gunpowder|trigo|ma[ií]z|cebada|avena|salvado|semillas?|levadura|manteca|almid[oó]n|queso|carne|caf[eé]|cacao|vinagre|oro|plata|arena|cera)\b)|(?:(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:fluid\s+|fl\.\s*)?(?:(?:grains?|minims?|drachms?|drams?|ounces?|gills?|scruples?|granos?|dracmas?|onzas?|escr[uú]pulos?)\b|(?:grs?|oz)(?:\.|\b)|oz\b|c\.\s?c\.)|\b(?:a\s+few\s+drops|a\s+drop\s+or\s+two|unas\s+(?:cuantas\s+|pocas\s+)?gotas)\b)(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))(?!\s*(?:(?:of|de)\s+)?(?:wheat|corn|oats?|barley|rye|bran|meal|seeds?|feed|hay|yeast|lard|suet|starch|gelatine?|cheese|meat|beef|tea(?!\s+tree)|coffee|cocoa|chocolate|vinegar|gold|silver|sand|clay|wax|beeswax|rosin|resin|gunpowder|trigo|ma[ií]z|cebada|avena|salvado|semillas?|levadura|manteca|almid[oó]n|queso|carne|caf[eé]|cacao|vinagre|oro|plata|arena|cera)\b)(?=[^;!?]{0,80}?\b(?:every\s+(?:[\w-]+\s+){0,2}?hours?|hourly|cada\s+(?:\w+\s+){0,2}?horas?|doses?|dosis|dosage|given|give|gives|giving|administer\w*|administr\w*|take|takes|taken|inject\w*|ivermectin|dele|dale|darle|dar|d[eé]selo|d[eé]sele|tome|tomar|toma|tomando|tinctures?|tintura|infusions?|infusi[oó]n|decoctions?|remed(?:y|ies)|remedios?|medicinal(?:ly)?|medicines?|medicinas?|mixtures?|prescrib\w*|recommend\w*|purgatives?|purgantes?|cathartics?|emetics?|vomitivos?|antispasmodic|anodyne|laxatives?|laxantes?|tonics?|t[oó]nicos?|physic|draughts?|drench\w*|bolus|pills?|liniments?|ointments?|salves?|embrocations?|poultices?|gargles?|lotions?|eye-?waters?|collyri\w*|pomadas?|ung[uü]entos?|linimentos?|cataplasmas?|quinine|quinina|opium|opio|laudanum|l[aá]udano|morphi\w*|morfina|calomel|camphor\w*|alcanfor|digitalis|foxglove|strychni\w*|estricnina|bromides?|bromuro|salicin|salicyl\w*|buchu|creosote|creosota|elaterium|ipecac\w*|paregoric|parag[oó]rico|castor\s+oil|ricino|epsom|glauber|iodides?|yoduro|aloes|rhubarb|ruibarbo|senna|jalap|turpentine|trementina|chloral|chloroform|cloroformo|ether|belladonn?a|aconite|ac[oó]nito|ergot\w*|arseni\w*|ars[eé]nico|mercury|mercurio|antitoxins?|antitoxina|serum|suero|antimony|tartar\s+emetic|pine\s+tar|penny\s*royal|carbolic|creolin|sulphur|azufre|magnesia|bismuth|santonin|cocaine|atropine|aspirin\w*|chlorodyne|squills?|antipyrin\w*|acetanilid\w*|phenacetin|cod[\s-]liver\s+oil|vermifuge|nux\s+vomica|nitre|lobelia|asaf\w*tida|valerian|hyoscyam\w*|cannabis|cantharides|croton\s+oil|podophyll\w*|sarsaparilla|guaiac\w*|colchicum|stramonium|hellebore|savin|tansy|wormwood|quassia|gentian|cinchona)\b)|\b(?:emetics?|vomitivos?|laxatives?|laxantes?|purgatives?|purgantes?|purg(?:e|es|ed|ing)|cathartics?|physic)\b[^;!?]{0,80}?(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|cucharaditas?|cucharadas?|cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b(?:[\s,]+(?:(?:or|and|to|o|y)\s+)?(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|cucharaditas?|cucharadas?|cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b)*|(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|cucharaditas?|cucharadas?|cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b(?:[\s,]+(?:(?:or|and|to|o|y)\s+)?(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|cucharaditas?|cucharadas?|cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b)*(?=[^;!?]{0,80}?\b(?:emetics?|vomitivos?|laxatives?|laxantes?|purgatives?|purgantes?|purg(?:e|es|ed|ing)|cathartics?|physic)\b)|(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:fluid\s+|fl\.\s*)?(?:drachms?|minims?|scruples?|dracmas?|escr[uú]pulos?)\b|\b(?:castor\s+oil|ricino|emetics?|vomitivos?|laxatives?|laxantes?|purgatives?|purgantes?|cathartics?|quinine|quinina|opium|opio|laudanum|l[aá]udano|morphi\w*|morfina|calomel|camphor\w*|alcanfor|digitalis|foxglove|strychni\w*|estricnina|bromides?|bromuro|salicin|salicyl\w*|buchu|creosote|creosota|elaterium|ipecac\w*|paregoric|parag[oó]rico|epsom|glauber|iodides?|yoduro|aloes|senna|jalap|turpentine|trementina|chloral|chloroform|cloroformo|belladonn?a|aconite|ac[oó]nito|ergot\w*|arseni\w*|ars[eé]nico|antitoxins?|antitoxina|antimony|tartar\s+emetic|pine\s+tar|penny\s*royal|carbolic|creolin|magnesia|bismuth|santonin|cocaine|atropine|aspirin\w*|chlorodyne|squills?|antipyrin\w*|acetanilid\w*|phenacetin|cod[\s-]liver\s+oil|vermifuge|nux\s+vomica|lobelia|asaf\w*tida|valerian|hyoscyam\w*|cannabis|cantharides|croton\s+oil|podophyll\w*|colchicum|stramonium|hellebore|savin|tansy|wormwood|quassia|gentian|cinchona|ivermectin)\b[^;!?]{0,80}?(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:de\s+(?:una?\s+)?)?(?:cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))|(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:de\s+(?:una?\s+)?)?(?:cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))(?=[^;!?]{0,80}?\b(?:castor\s+oil|ricino|emetics?|vomitivos?|laxatives?|laxantes?|purgatives?|purgantes?|cathartics?|quinine|quinina|opium|opio|laudanum|l[aá]udano|morphi\w*|morfina|calomel|camphor\w*|alcanfor|digitalis|foxglove|strychni\w*|estricnina|bromides?|bromuro|salicin|salicyl\w*|buchu|creosote|creosota|elaterium|ipecac\w*|paregoric|parag[oó]rico|epsom|glauber|iodides?|yoduro|aloes|senna|jalap|turpentine|trementina|chloral|chloroform|cloroformo|belladonn?a|aconite|ac[oó]nito|ergot\w*|arseni\w*|ars[eé]nico|antitoxins?|antitoxina|antimony|tartar\s+emetic|pine\s+tar|penny\s*royal|carbolic|creolin|magnesia|bismuth|santonin|cocaine|atropine|aspirin\w*|chlorodyne|squills?|antipyrin\w*|acetanilid\w*|phenacetin|cod[\s-]liver\s+oil|vermifuge|nux\s+vomica|lobelia|asaf\w*tida|valerian|hyoscyam\w*|cannabis|cantharides|croton\s+oil|podophyll\w*|colchicum|stramonium|hellebore|savin|tansy|wormwood|quassia|gentian|cinchona|ivermectin)\b)", re.I)
DOSE_REDACTED = "[dose removed; printed guide]"


def scrub_dose(s):
    """Every snippet or excerpt the server returns loses dose figures, whatever the query asked (acceptance 2026-10-03:
    'fever medicine for a child' quoted '0.15 ml' from a book). The query guard above still hides whole snippets."""
    if not s or not DOSE_FIGURE.search(s):
        return s
    # a snippet can end between a figure and its unit ("Niños: 50…"): on a dose snippet a trailing bare number goes too
    return re.sub(r"\s\d+(?:[.,]\d+)*\s*(?:…|\.\.\.)?\s*$", " …", DOSE_FIGURE.sub(DOSE_REDACTED, s))


# red team 2026-10-11 class 1 (#181): a search snippet or /semantic excerpt is WITHHELD whole, not scrubbed, when its
# text is dose-bearing: the dose pattern matches (a scrub would change it), or a drug or dose word sits beside any
# figure. Scrubbing left "half tablet ([dose removed]) per day for 10-14 days" readable for a question with no drug
# word, and any future gap in DOSE_FIGURE would leak the same way. The hit keeps its title and link. Same rule as
# doseText() in library/search.html and chat.html.
# RT5 class 2 (#199, es25): relative-dose words too ("la dosis desinflamatoria, que es el doble de la dosis normal");
# byte-identical to DOSE_NUM_RE in library/search.html and library/chat.html (fix_f1_test.py checks)
DOSE_NUMERAL = re.compile(r"\d|[½¼¾⅓⅔⅛]|&#\d|&frac|\b(?:half|quarter|media|medio|cuarto|million|millones|double|doble|twice|triple|dos veces)\b", re.I)
# figures that are never an amount of medicine (durations, temperatures, page numbers) do not count: "cool the burn for
# at least 20 minutes. Relieve pain with aspirin" stays visible
NOT_DOSE_FIG = re.compile(r"\d+(?:[.,]\d+)?(?:\s*(?:-|–|to|a)\s*\d+)?\s*(?:min(?:ute)?s?|minutos?|h(?:ou)?rs?|horas?|days?|d[ií]as?|weeks?|semanas?|months?|mes(?:es)?|years?|a[nñ]os?|°\s*[cf]?|degrees?|grados?)(?![a-z])|\b(?:page|pages|p\.|chapter|cap[ií]tulo|p[aá]gina)\s*\d+", re.I)


# RT4 class 2 (#192, a1a en18): a page that gives snakebite first aid the library's own triage card calls harmful
# (an imperative "Apply constricting band(s)" (Ranger Handbook p.313), "suck out venom", cuts over the fang marks,
# "Kill the snake") is flagged "outdated"; the Ask page never shows it as a passage. A negated line ("Do not cut the
# bite") has no imperative at a sentence start and does not match. Same pattern as OUTDATED_RE in library/chat.html.
OUTDATED_AID_RE = re.compile(r"(?:^|[.:;,•)\]—…]\s*|\d\.\s*)(?:then\s+)?(?:\b(?:apply|place|use|put|tie|make|cut|suck|aplique|aplicar|ponga|poner|coloque|colocar|amarre|amarrar|haga|hacer|haz|corte|cortar|chupe|chupar|succione|succionar)\b[^.]{0,40}?\b(?:constrict\w*\s+bands?|bandas?\s+constrictoras?|torniquete|incisions?\b[^.]{0,30}(?:bite|fang)|cuts?\b[^.]{0,30}fang|(?:out\s+)?(?:the\s+)?(?:venom|veneno)\b|(?:peque[nñ]os\s+)?(?:cortes?|incisi[oó]n(?:es)?)\b[^.]{0,40}(?:huellas|mordedura|colmillos|herida))|\bkill\s+(?:the\s+)?snake|\bmate\s+(?:a\s+)?la\s+(?:serpiente|v[ií]bora|culebra))", re.I)
SNAKE_RE = re.compile(r"snake|venom|\bbite|\bbitten|fang|serpient|v[ií]bora|culebra|mordedura|veneno", re.I)
# RT6 class 3 (#214, a1a BT7, a1b 7): electric shock offered as snakebite first aid (ECHO 1996 p.164: "We have been using
# the electric shock as a first aid measure for snake bites in Ecuador since 1980"); the WHO guide p.70 lists it among
# methods "useless or even frankly dangerous". Shapes: use/apply/give the shock ... bite; shock as first aid /
# treatment ... bite; treat(ing) ... bites with electric shock; bite ... apply/use the shock; "the electric shock was
# given" or "shock treatment for scorpion bites". Every shape needs a bite, sting or venom word within 300 characters
# (ECHO pp.160-165). A negation just before ("DO NOT apply electric shock",
# SOF handbook p.414) does not count. Same words as the electric-shock rows of OUTDATED_RE in library/chat.html.
_SHOCK = r"(?:electric(?:al)?\s+shocks?|electro-?shocks?|shocks?\s+el[eé]ctricos?|choques?\s+el[eé]ctricos?|descargas?\s+el[eé]ctricas?)"
_BITE = r"(?:bites?|bitten|snake\w*|stings?|stung|mordeduras?|mordid[oa]s?|picaduras?|serpientes?|v[ií]boras?|culebras?)\b"
ELECTRIC_AID_RE = re.compile(
    r"\b(?:apply|give|use)\s+(?:the\s+|a\s+)?shocks?\b[^.;]{0,40}?\b" + _BITE + r"|"  # ECHO p.166 "Apply the shock directly to the bite"
    r"\b(?:using|use|used|uses|apply|applying|applied|give|giving|given|usar|usando|usamos|use|aplicar|aplique|aplicando|"
    r"aplicamos|dar|d[eé])\s+(?:an?\s+|the\s+|el\s+|la\s+|las\s+|los\s+|un\s+|una\s+|unas\s+)?" + _SHOCK + r"[^.;]{0,60}?\b" + _BITE +
    r"|" + _SHOCK + r"\s+(?:as|como)\s+(?:an?\s+|una?\s+)?(?:first[\s-]aid|primeros\s+auxilios|treatment|tratamiento|remedy|remedio|cure|cura)\b"
    r"[^.;]{0,40}?\b" + _BITE +
    r"|\b(?:treat\w*|trat(?:ar|ando|amos|e|o|amiento))\s+(?:\w+\s+){0,3}?" + _BITE + r"[^.;]{0,30}?\b(?:with|con)\s+[^.;]{0,15}?"
    r"(?:electric\w*|" + _SHOCK + r")"
    r"|\b" + _BITE + r"[^.;]{0,40}?\b(?:apply|give|use|aplique|aplicar|use|usar|d[eé])\s+(?:an?\s+|the\s+|una?\s+|unas\s+|las\s+)?" + _SHOCK +
    r"|" + _SHOCK + r"\s+(?:was|is|were|are|should\s+be|can\s+be)\s+(?:given|used|applied)\b"
    r"|\bshock\s+treatment\s+(?:for|of|on)\s+(?:\w+\s+){0,2}?" + _BITE,
    re.I)
# RT6 (acceptance bite check, round 6): "measures of emergencies - to try to kill the snake for a possible identification"
# (CD3WD Medical Expert System p.2032) had no sentence-start imperative for OUTDATED_AID_RE. Any "kill the snake" counts
# unless its own sentence says not to ("Do not waste time trying to kill the snake").
KILL_SNAKE_RE = re.compile(r"\bkill(?:ing)?\s+(?:the|a)\s+snake\b|\bmat(?:e|ar|en)\s+(?:a\s+)?(?:la|una)\s+(?:serpiente|v[ií]bora|culebra)\b", re.I)
SENT_NEG_RE = re.compile(r"\b(?:not|never|don'?t|avoid|waste|no|nunca|jam[aá]s|evite|evitar)\b", re.I)
# RT6 L1 hand-off (a1a W1 en03, b5): FM 5-34 p.74 CPR ("Lift up neck", "four quick breaths") and overdose advice to give
# ipecac or "dilution with water or milk" are outdated first aid too; not when a negation comes just before ("Do not give
# syrup of ipecac"). Same pattern and 20-character negation rule as OLD_AID_RE in library/chat.html outdated().
# #234 round 7 [final] (a1a en34): the prone Schafer method of resuscitation too. FM 21-76's "Break open the large blisters"
# (b5 N5) is an item of a "Do not" list (p.39 snakebite), so it is not flagged: a snippet cut there is the risk, not the page
OLD_AID_RE = re.compile(r"lift (?:up )?(?:the )?neck|four quick (?:full )?breaths|ipecac\w*|dilution with (?:water|milk)|"
                        r"\bsch?a(?:e|f)?ff?er'?s?\s+(?:prone\s+)?(?:pressure\s+)?method|prone\s+pressure\s+method|"
                        r"back.pressure.arm.lift|holger.nielsen|silvester\s+method", re.I)
# "dilution with water" is everyday chemistry (bleach solutions, fertiliser, vinegar: about 2,300 pages); it counts only beside a
# poisoning word, so the water-treatment pages keep their quotes
POISON_NEAR_RE = re.compile(r"poison\w*|swallow\w*|ingest\w*|overdose\w*|venen\w*|trag\w*", re.I)
BITE_NEAR_RE = re.compile(r"\b(?:venom\w*|venen\w*|" + _BITE + ")", re.I)
NEGATED_RE = re.compile(r"\b(?:not|never|don'?t|avoid|no|nunca|evite|evitar|jam[aá]s)\b", re.I)

# #229 (round 7 class 6, b5 R2): a passage that names dengue and ibuprofen is outdated advice, never quoted as an answer:
# the Community Guide PDF p.163 says "taking ibuprofen or paracetamol (not aspirin)" for dengue; NWTND ch.22 p.10 and MSF
# p.37 say ibuprofen is dangerous there. Same rule as the dengue row of OUTDATED_RE in library/chat.html (fix plan shared
# interface). A mention with a warning within 80 characters is the current advice and stays quotable (NWTND ch.22 p.10
# "can be dangerous", MSF p.37 "contraindicated", WHO Pocket Book p.212 "Do not give ... ibuprofen").
DENGUE_RE = re.compile(r"\bdengu[eé]", re.I)
IBUPROFEN_RE = re.compile(r"\bibuprofen", re.I)  # ibuprofen, ibuprofeno
IBU_WARN_RE = re.compile(r"dangerous|contraindicat|do not give|don'?t give|never|aggravat|safer than|harmful|peligros|nunca|mejor que|no (?:le )?d[eé]\b|da[ñn]in", re.I)


def dengue_ibuprofen(text):
    if not DENGUE_RE.search(text):
        return False
    return any(not IBU_WARN_RE.search(text[max(0, m.start() - 80):m.end() + 80]) for m in IBUPROFEN_RE.finditer(text))


def outdated_aid(text):
    if dengue_ibuprofen(text or ""):
        return True
    for m in OUTDATED_AID_RE.finditer(text or ""):
        if SNAKE_RE.search(text[max(0, m.start() - 200):m.end() + 200]):
            return True
    for m in OLD_AID_RE.finditer(text or ""):
        if NEGATED_RE.search(text[max(0, m.start() - 20):m.start()]):
            continue
        if m.group(0).lower().startswith("dilution") and not POISON_NEAR_RE.search(text[max(0, m.start() - 200):m.end() + 200]):
            continue
        return True
    for m in KILL_SNAKE_RE.finditer(text or ""):
        if not SENT_NEG_RE.search(re.split(r"[.!?;]", text[max(0, m.start() - 200):m.start()])[-1]):
            return True
    for m in ELECTRIC_AID_RE.finditer(text or ""):  # a negation in the match or just before it ("DO NOT apply ...")
        if (not NEGATED_RE.search(text[max(0, m.start() - 12):m.end()])
                and BITE_NEAR_RE.search(text[max(0, m.start() - 300):m.end() + 300])):
            return True
    return False


# en55 (a1a, #234 outdated first aid): FM 21-76 p.118 "use the Universal Edibility Test" quoted for "which wild mushrooms are
# safe to eat", while the manual says "Do not eat mushrooms in a survival situation!": on a mushroom question a passage that
# offers the edibility test is title-only. Same rule as chat.html (M1). The test stays quotable for plant questions.
MUSHROOM_Q_RE = re.compile(r"\b(?:mushrooms?|toadstools?|fung(?:i|us)|hongos?|setas?|champi(?:n|ñ)on(?:es)?)\b", re.I)
EDIBILITY_RE = re.compile(r"edibility\s+test|prueba\s+(?:universal\s+)?de\s+comestibilidad", re.I)


def title_only(h, key, query=""):
    """E22 B (round 8, #238 class 4): a hit is title-only (no snippet in MCP, no excerpt in /semantic) when its document
    carries the catalogue's historical line (title_only.json), the page or the quote is flagged outdated, or the page is a
    dose_page. The hit keeps its title, link and flags, and carries title_only (search.html and chat.html read it)."""
    if (h.get("outdated") or h.get("dose_page") or STATE.title_only_doc(h["path"]) or outdated_aid(h.get(key))
            or (h.get(key) and MUSHROOM_Q_RE.search(query) and EDIBILITY_RE.search(h[key]))):
        h[key] = None
        h["title_only"] = True
    return h


# D4 (round 11, #278-#281, 10-28): no quoted document text leaves this server. /semantic rows and search_library
# hits keep path, title, page, url, shelf, score, age_w and their flags (title_only, dose_page, outdated, historical and
# its warning); the quote fields are DROPPED, not emptied. The quote is still cut inside the server, because the flags
# and the page a per-document vector links are read from it, so flags and ranking are unchanged.
TEXT_FIELDS = ("snippet", "excerpt")


def no_text(rows):
    for r in rows:
        for k in TEXT_FIELDS:
            r.pop(k, None)
    return rows


# b5 N9 (round 9, #252): a window cut between a number and its unit ("Sulphate of copper, 15…") reads as an amount; the
# bare number before the cut goes (a 4-digit year stays: "in 1997…")
CUT_NUMBER_RE = re.compile(r"[\s,;:(]+\d{1,3}(?:[.,]\d+)?\s*(?:…|\.\.\.)\s*$")


# round 10 (#271, a1a en69): font-garbled PDF text ("E\\KLVWRU\\RUIHHOVKRW…", IMCI chart booklet p.8, a shifted font with no
# Unicode map) is never a quote. Signals: a capital letter then a backslash not starting a lower-case word (not a LaTeX
# command or a Windows path), or control characters; tuned on real excerpts (redteam_20261027_fix_m2.md).
GARBLE_RE = re.compile(r"[A-Z]\\(?![a-z])")
CTRL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0e-\x1f\x7f-\x9f]")


def garbled(s):
    return len(GARBLE_RE.findall(s)) >= 2 or len(CTRL_CHAR_RE.findall(s)) >= 3


# r39 acceptance (J1 / #171 #191, 10-27): a tablet count right after a water disinfectant is a water-treatment amount. The WHO
# Drinking-water Quality p.133 table reads "1. Household bleach (5%)—4 drops per litre 2. Sodium dichloroisocyanurate—1 tablet
# (per package directions)"; the #273 control-character strip (U+0007 bullets) moved the 220-character window to include the
# tablet row, which DOSE_FIGURE counts (no per-volume after it), so the drops-per-litre quote was withheld. Only the named
# disinfectants lift the tablet count out of the dose test; every medicine tablet and the dose_page / guard rules stand.
WATER_TAB_RE = re.compile(r"\b(?:dichloroisocyanurate|dicloroisocianurato|isocyanurate|isocianurato|nadcc|hypochlorite|hipoclorito|"
                          r"halazone|halazona|aquatabs?|purification|potabilizador\w*|purificador\w*)\b[^.;\d]{0,6}\d+\s*"
                          r"(?:tablets?|tabletas?|pastillas?|comprimidos?)\b", re.I)


def safe_snippet(s):
    if not s or DOSE_REDACTED in s or DOSE_FIGURE.search(WATER_TAB_RE.sub(" ", s)) or (dose_guard(s, True) and DOSE_NUMERAL.search(NOT_DOSE_FIG.sub(" ", s))):
        return None
    if garbled(s):
        return None
    return CUT_NUMBER_RE.sub(" …", s)


APOTHECARY_RE = re.compile(r"\b(?:grains?|minims?|drachms?|drams?|ounces?|oz\b|gills?|scruples?|c\.\s?c\.|onzas?|dracmas?|granos?|escr[uú]pulos?|few\s+drops|drop\s+or\s+two|unas\s+(?:cuantas\s+|pocas\s+)?gotas|(?:cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b)|(?<![a-z])grs?(?:\.|\b)", re.I)


def dose_page(body):
    """RT5 class 2 (#199, es25): a page whose full body carries a dose (a drug or dose word plus a DOSE_FIGURE amount, the
    read_document rule) gives no excerpt at all, whatever window the excerpt would have shown: a 220-character window cut
    just before the amounts ("la dosis aquí es ... el doble de la dosis normal") still read as dosing advice. Water-treatment
    amounts keep the #171/#191 exemption (dose_guard text mode and DOSE_FIGURE both pass "4 drops per litre", the EPA
    bleach table). The hit keeps its title and link and carries dose_page so the Ask page shows it title-only."""
    if not body:
        return False
    if dose_guard(body, True) and DOSE_FIGURE.search(body):
        return True
    # E27 (round 9, #246): an apothecary amount the v5 pattern matched already sits beside a medicine word (the pattern's own
    # condition), so it makes the page a dose page with no guard word ("give them an ounce of Epsom Salts", swine 1907 p.36)
    return bool(APOTHECARY_RE.search(body)) and any(APOTHECARY_RE.search(m.group(0)) for m in DOSE_FIGURE.finditer(body))


# a sentence ends at . ! ? before a capital, or a list item starts at a bullet (PDF text keeps private-use bullet glyphs)
SENT_END = re.compile(r"[.!?]\s+(?=[A-Z¿¡\"“(])|\s[•·▪■◦‣\uf0a7\uf0b7\uf076\uf0d8]\s*(?=[A-Z¿¡\"“(#])")


def sentence_start(text, at, back=220):
    """F2 A1 en34: a window that opened mid-sentence dropped Ready.gov's NEVER ("use a generator indoors" read as advice).
    Returns the offset of the sentence boundary at most `back` chars (one window) before `at`, or `at` when there is none."""
    if not at:
        return 0
    m = None
    for m in SENT_END.finditer(text, max(0, at - back), at + 1):
        pass
    return m.end() if m else at


# RT6 #214 (acceptance bite check): the WHO snakebite guide p.70 window opened at "These methods include: making local
# incisions ..., attempts to suck the venom out of the wound, ... electric shock" and cut off the sentence before it,
# "most of the traditional ... first-aid methods have proved to be useless or even frankly dangerous". A window that names
# a harmful bite method next to a bite word and holds no warning word starts up to two sentences earlier.
BAD_AID_TXT = re.compile(r"electric(?:al)?\s+shock|electro-?shock|descargas?\s+el[eé]ctric|choques?\s+el[eé]ctric|\b(?:apply|give|use)\s+(?:the\s+|a\s+)?shocks?\b|"
                         r"constrict\w*\s+band|tourniquet|torniquete|suck\w*\s+(?:out\s+)?(?:the\s+)?venom|chup\w*\s+(?:el\s+)?veneno|"
                         r"kill\w*\s+the\s+snake|mate\s+(?:a\s+)?la\s+(?:serpiente|v[ií]bora)|incisions?|cortes?\b", re.I)
WARN_TXT = re.compile(r"\b(?:not|never|don'?t|avoid|useless|dangerous|harmful|no|nunca|evite|in[uú]til\w*|peligros\w*)\b", re.I)


def warned_start(t, at, size):
    for _ in range(2):
        w = t[at:at + size]
        m = BAD_AID_TXT.search(w)
        if not at or not m or not BITE_NEAR_RE.search(w[max(0, m.start() - 60):m.end() + 60]) or WARN_TXT.search(w):
            return at
        ends = [b.end() for b in SENT_END.finditer(t, max(0, at - 400), at) if b.end() < at - 1]
        prev = ends[-1] if ends else (0 if at <= 400 else at)
        if prev >= at:
            return at
        at = prev
    return at


def cut_window(t, at, size):
    """t[at:at+size] with ellipses. #171 (round 4): a cut inside an amount ("1 tablet p…" of "per liter of water",
    "½ teaspoon o…" of "of household bleach") reads as a dose; a window up to 80 chars longer that reads safe wins.
    safe_snippet still judges the whole returned text, so a longer window never shows a dose."""
    for n in (size, size + 40, size + 80):
        s = ("…" if at else "") + t[at:at + n].strip() + ("…" if at + n < len(t) else "")
        if safe_snippet(s):
            break
    return s


def sentence_snippet(body, snip, size=220):
    """Re-anchor an FTS5 token snippet on the page body so it starts at a sentence boundary; the FTS snippet itself
    when its text cannot be found (body None, or FTS normalised the text differently)."""
    if not body or not snip:
        return snip
    head = snip.strip(". ").lstrip("…").strip()[:40]
    body = re.sub(r"\s+", " ", body)
    at = body.find(head) if head else -1
    if at < 0:
        return snip
    return cut_window(body, warned_start(body, sentence_start(body, at), size), size)


def redact_doses(out):
    """A read_document page that carries drug/dose language (same decision as the search guard) loses every
    dose figure and gets DOSE_NOTICE prepended. Pages without drug language (recipes: '500 g flour') pass through."""
    text = out.get("text") or ""
    if dose_guard(text) and DOSE_FIGURE.search(text):
        out["text"] = DOSE_NOTICE + "\n\n" + DOSE_FIGURE.sub(DOSE_REDACTED, text)
        out["dose_guard"] = True
    return out


def safe_library_path(raw):
    """v2 P0-1: canonicalize; return (realpath, normalized_rel) or None."""
    if not isinstance(raw, str) or not raw:
        return None
    p = raw
    for _ in range(3):  # collapse repeated percent-encoding
        p = urllib.parse.unquote(p)
    if p.startswith("/") or p.startswith("\\") or "\x00" in p:
        return None
    segs = [s for s in p.replace("\\", "/").split("/") if s not in ("", ".")]
    if not segs or ".." in segs:
        return None
    # The library's own top-level entries may be symlinks (dev layout);
    # they are trusted curated content. Containment is checked against the
    # RESOLVED top-level entry, so traversal cannot escape it, while the
    # library's own symlinked shelves still resolve.
    root = os.path.realpath(os.path.join(STATE.library, segs[0]))
    real = os.path.realpath(os.path.join(STATE.library, p))
    if real != root and not real.startswith(root + os.sep):
        return None
    # RT6 a8 F2: only what nginx serves. It 404s /kolibri_data/ (logs with LAN client addresses, sessions) and /_app/mcp/
    # (nginx-lantern.conf, FIXES #151); dotfiles and dot-folders (.claude, .well-known) are no library documents either.
    # Checked on the path as given (case-folded: the dev disk is case-insensitive) and on where it resolves.
    low = [x.lower() for x in segs]
    if any(x.startswith(".") for x in low) or low[0] == "kolibri_data" or low[:2] == ["_app", "mcp"]:
        return None
    for private in ("kolibri_data", os.path.join("_app", "mcp")):
        top = os.path.realpath(os.path.join(STATE.library, private))
        if real == top or real.startswith(top + os.sep):
            return None
    return real, "/".join(segs)


# ---------------------------------------------------------------- helpers

TAG_RE = re.compile(r"<script\b.*?</script>|<style\b.*?</style>",
                    re.I | re.S)
HTML_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(html):
    txt = TAG_RE.sub(" ", html)
    txt = HTML_TAG_RE.sub(" ", txt)
    txt = (txt.replace("&amp;", "&").replace("&lt;", "<")
           .replace("&gt;", ">").replace("&quot;", '"')
           .replace("&#39;", "'").replace("&nbsp;", " "))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", txt)).strip()


ASCII_TOK = r"[A-Za-z0-9]+"
# RT5 b2 F10 (#207): a Spanish question keeps its accented words whole ("tétanos", not "t" + "tanos"): the ASCII split
# matched "tanos" in mojibake CD3WD pages ("pl\ufffdtanos"), so "señales de tétanos" returned fruit-processing PDFs.
# unicode61 folds the accents at index time. English queries keep the ASCII split (English ranking unchanged).
UNI_TOK = r"[^\W_]+"


def fts_match_expr(query, tok=ASCII_TOK):
    # apostrophes excluded: unicode61 splits won't -> won+t at index time,
    # so a quoted "won''t" phrase silently matches nothing; single-char
    # fragments (the orphaned t) are dropped as noise
    toks = re.findall(tok, query)
    multi = [t for t in toks if len(t) > 1 or t.isdigit()]
    toks = multi or toks
    if not toks:
        return None
    return " ".join('"%s"' % t for t in toks)


def _expand_query(query):
    """Return list of extra FTS token groups from SYNONYMS.

    Tries longest synonym phrases first, then single tokens.
    Skips any expansion whose terms would trip the dose guard.
    Returns list of strings to OR into the FTS expression.
    """
    if not SYNONYMS:
        return []
    q_lower = query.lower()
    extras = []
    used_spans = []  # track which positions already matched a longer phrase

    # Sort terms longest-first so multi-word phrases shadow single tokens
    for term in sorted(SYNONYMS, key=len, reverse=True):
        if term not in q_lower:
            continue
        # Check it doesn't overlap a span already consumed
        idx = q_lower.find(term)
        overlap = any(s <= idx < e or s < idx + len(term) <= e
                      for s, e in used_spans)
        if overlap:
            continue
        used_spans.append((idx, idx + len(term)))
        expansion = SYNONYMS[term]
        # Never expand INTO guard terms (P0-4 safety constraint)
        if dose_guard(expansion):
            continue
        extras.append(expansion)
    return extras


def fts_match_expr_with_expansion(query, tok=ASCII_TOK):
    """Build FTS match expr with synonym expansion as OR-groups.

    Returns (match_expr, expanded_bool).
    """
    base_toks = re.findall(tok, query)
    base_multi = [t for t in base_toks if len(t) > 1 or t.isdigit()]
    base_toks = base_multi or base_toks
    if not base_toks:
        return None, False

    extras = _expand_query(query)
    if not extras:
        return " ".join('"%s"' % t for t in base_toks), False

    # Build: (base_terms) OR (expansion1_terms) OR ...
    base_group = " ".join('"%s"' % t for t in base_toks)
    parts = [base_group]
    for exp in extras:
        exp_toks = re.findall(tok, exp)
        exp_toks = [t for t in exp_toks if len(t) > 1 or t.isdigit()]
        if exp_toks:
            parts.append(" ".join('"%s"' % t for t in exp_toks))
    if len(parts) == 1:
        return parts[0], False
    return " OR ".join("(%s)" % p for p in parts), True


def doc_url(path):
    return LIBRARY_HOST + "/" + urllib.parse.quote(path.lstrip("/"))


def kiwix_fetch(path_and_query):
    """Pinned proxy: only /search and /content/ paths ever constructed."""
    assert path_and_query.startswith(("/search", "/content/"))
    try:
        with urllib.request.urlopen(STATE.kiwix + path_and_query,
                                    timeout=KIWIX_TIMEOUT) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return None  # silent degrade when kiwix-serve is down


def haversine(lat1, lon1, lat2, lon2):
    rl1, rl2 = math.radians(lat1), math.radians(lat2)
    dlat = rl2 - rl1
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(rl1) * math.cos(rl2) * math.sin(dlon / 2) ** 2)
    return 6371.0 * 2 * math.asin(math.sqrt(a))


# ------------------------------------------------------- semantic (R12)

EMB_LOCK = threading.Lock()


def _unit(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return array.array("f", (x / n for x in v))


def _load_vectors():
    """One-time load of embeddings.db into RAM (~100 MB), rows unit-normalised
    so a dot product is the cosine. [] = unavailable.

    ponytail: 768 x float32 brute force; matryoshka-256 float16 (~21 MB) is
    the upgrade path if the Pi needs it."""
    if STATE.vec_keys is None:
        with EMB_LOCK:
            if STATE.vec_keys is None:
                keys, rows = [], []
                try:
                    con = sqlite3.connect(
                        "file:%s?mode=ro" % STATE.emb_db, uri=True)
                    for path, page, blob in con.execute(
                            "SELECT path, page, vec FROM vectors"):
                        keys.append((path, int(page)))
                        rows.append(blob if np else _unit(array.array("f", blob)))
                    con.close()
                except (sqlite3.Error, OSError):
                    keys, rows = [], []
                ekeys, erows = [], []
                try:  # E2: the Spanish-only table; absent in an older sidecar
                    con = sqlite3.connect("file:%s?mode=ro" % STATE.emb_db, uri=True)
                    for path, page, blob in con.execute("SELECT path, page, vec FROM vectors_es ORDER BY path, page"):
                        ekeys.append((path, int(page)))
                        erows.append(blob if np else _unit(array.array("f", blob)))
                    con.close()
                except (sqlite3.Error, OSError):
                    ekeys, erows = [], []
                if np and rows:
                    m = np.frombuffer(b"".join(rows), dtype=np.float32)
                    m = m.reshape(len(rows), -1).copy()
                    m /= np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-9)
                    rows = m
                if np and erows:
                    m = np.frombuffer(b"".join(erows), dtype=np.float32).reshape(len(erows), -1).copy()
                    m /= np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-9)
                    erows = m
                STATE.es_keys, STATE.es_rows = ekeys, (erows if len(ekeys) else None)
                langs = _doc_langs()
                STATE.vec_lang = [langs.get(k[0], "en") for k in keys]
                by_path = {}
                for i, k in enumerate(keys):
                    by_path.setdefault(k[0], []).append(i)
                STATE.vec_rows_by_path = by_path
                STATE.vec_keys, STATE.vec_rows = keys, rows
    return STATE.vec_keys, STATE.vec_rows


LANG_LOCK = threading.Lock()


def _doc_langs():
    """path -> lang (mcp.db, one row per document via loc), loaded once: the hard language filter for /semantic and the
    English-mode title rows (E6)."""
    if not STATE.lang_by_path:
        with LANG_LOCK:
            if not STATE.lang_by_path:
                langs = {}
                try:  # hard language filter: lang lives in mcp.db, not the sidecar
                    con = STATE.db()
                    try:  # one row per doc via loc (indexed); pages.path is FTS5 UNINDEXED
                        langs = dict(con.execute(
                            "SELECT path, lang FROM pages WHERE rowid IN "
                            "(SELECT min(rid) FROM loc GROUP BY path)"))
                    except sqlite3.OperationalError:  # mcp.db predates loc
                        langs = dict(con.execute("SELECT DISTINCT path, lang FROM pages"))
                    con.close()
                except sqlite3.Error:
                    pass
                STATE.lang_by_path = langs or {"": "en"}
    return STATE.lang_by_path


SPANISH_TITLE_RE = re.compile(r"\((?:Spanish|Español|Espanol)\)", re.I)


def spanish_doc(path, title=""):
    """E6: a Spanish document: titles.json row language (K5 450df4bf, packed element 4), mcp.db lang, or a "(Spanish)"
    title for a file with no text layer."""
    _title_of(path)  # loads titles_by_path and title_lang once
    return (STATE.title_lang.get(path) == "es" or _doc_langs().get(path) == "es"
            or bool(SPANISH_TITLE_RE.search(title or "")))


def third_lang(path):
    """#240 (a7a note 8, b2 N8): a document whose titles.json row is neither English nor Spanish (Portuguese VITA, French
    CD3WD): Spanish-mode results leave it out (the stopword vote can tag a Portuguese text es). English mode is unchanged."""
    _title_of(path)
    return STATE.title_lang.get(path) not in (None, "en", "es")


def _title_of(path):
    """Lazy titles.json lookup (gen_index packed format); basename fallback."""
    if STATE.titles_by_path is None:
        m = {}
        try:
            with open(os.path.join(STATE.library, "_app", "index",
                                   "titles.json"), encoding="utf-8") as f:
                v = json.load(f)
            if isinstance(v, dict):  # dir-prefix packed (gen_index A7)
                m = {v["d"][it[0]] + it[1]: it[2] for it in v["i"]}
                # K5 450df4bf: element 4 = row language (ISO 639-1), absent = en
                STATE.title_lang = {v["d"][it[0]] + it[1]: it[4] for it in v["i"] if len(it) > 4}
            else:
                m = {it["p"]: it["t"] for it in v}
        except (OSError, ValueError, KeyError):
            pass
        STATE.titles_by_path = m
    t = STATE.titles_by_path.get(path)
    if not t and path.startswith("docs/") and path.endswith(".html"):
        # #193: a library-written note is not in titles.json; its title is the first "# " line of the .md beside it
        try:
            with open(os.path.join(STATE.library, path[:-5] + ".md"), encoding="utf-8") as f:
                m = re.match(r"# (.+)", f.readline())
            t = STATE.titles_by_path[path] = m.group(1).strip() if m else None
        except OSError:
            pass
    return t or os.path.splitext(os.path.basename(path))[0].replace("_", " ")


def embed_query(query):
    """Embed via the local llamafile service; None = degrade silently."""
    body = json.dumps({"content": "search_query: " + query[:2000]}).encode()
    req = urllib.request.Request(
        STATE.embed_url, body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read())
        v = d[0]["embedding"] if isinstance(d, list) else d["embedding"]
        while isinstance(v[0], list):
            v = v[0]
        return array.array("f", v)
    except Exception:
        return None


def rerank(query, paths):
    """E1b: max cosine of the query over each path's page rows, input order;
    score None when a path has no vectors; [] when the embed service is down."""
    keys, rows = _load_vectors()
    qv = embed_query(query) if keys else None
    if qv is None or len(qv) != len(rows[0]):
        return []
    qv = _unit(qv)
    out = []
    for p in paths:
        idx = STATE.vec_rows_by_path.get(p)
        if not idx:
            out.append({"path": p, "score": None, "page": None})
            continue
        if np:
            sc = rows[idx] @ np.asarray(qv, dtype=np.float32)
            b = int(np.argmax(sc))
            best = float(sc[b])
        else:
            best, b = max((sum(x * y for x, y in zip(rows[i], qv)), j)
                          for j, i in enumerate(idx))
        out.append({"path": p, "score": round(best, 4), "page": keys[idx[b]][1]})
    return out


# E27 (round 9, #246): a ranking age weight on health and medical documents only (fix plan "Age weight"; the formula and the
# file are in redteam_20261026_scripts/index_files.txt). Same prefix list as build_mcp_index.HEALTH_PREFIXES.
# ponytail: a path-prefix list; a catalogue topic field is the upgrade.
HEALTH_PREFIXES = ("docs/medical/", "docs/HISTORICAL/", "docs/cd3wd/2012/health/", "mirrors/hesperian/",
                   "docs/survivor_library/SurvivalLibrary/library/Medical-") + tuple(
    "docs/survivor_library/SurvivalLibrary/library/%s/" % s for s in ("First Aid", "Dentistry", "Herbalism", "Veterinary"))
AGE_REF_YEAR = 2026  # the r38 seal year, a constant so the Pi, dev and every later day agree


def age_w(path):
    """0 unless a health document with a catalogue year at least 20 years old; then 0.15 * (age - 20) / 80, capped at
    0.15 (age 30: 0.019, 50: 0.056, 80: 0.113, 100+: 0.15), rounded to 3 decimals."""
    if not path.startswith(HEALTH_PREFIXES):
        return 0.0
    y = (getattr(STATE, "health_years", None) or {}).get(path)
    if not y or AGE_REF_YEAR - y < 20:
        return 0.0
    return round(min(0.15, 0.15 * (AGE_REF_YEAR - y - 20) / 80), 3)


def weighted(raw, path):
    """(order score in thousandths, age_w): the sort, the near-tie band and the displayed score (s / 1000) all use it."""
    w = age_w(path)
    return round(raw * (1 - w) * 1000), w


# b5 W15 (round 9, #252): an older edition of a guide the library carries in a current edition ranks right after it, and
# the current edition is listed when only the old one matched. ponytail: a hand table of the editions a reviewer named; a
# catalogue "superseded_by" field is the upgrade.
_MSF_2026 = "docs/medical/msf/msf_essential_drugs.pdf"
SUPERSEDED = {p: _MSF_2026 for p in (
    "docs/school_textbooks/college_open_textbooks/essential_drugs_medical_msf__171000_.pdf",
    "docs/cd3wd/2012/health/_mc_essential_drugs_medical_msf_171000_.pdf",
    "docs/cd3wd/2012/health/_mc_essential_drugs_2_msf_en_lp_137150_.pdf",
    "docs/cd3wd/2012/health/_mc_essential_drugs_msf_en_lp_137160_.pdf")}
# b5 W7, a8 N7 (round 9): a dictionary row ("Eardrop: a pendant for the ear", Webster's "scalding brimstone") never comes
# first; dictionaries go after every other row unless the question asks what a word means
DICTIONARY_RE = re.compile(r"dictionar|webster", re.I)
MEANING_Q_RE = re.compile(r"\b(?:mean|means|meaning|definition|define|defined|synonyms?|significa\w*|definici[oó]n|"
                          r"sin[oó]nimos?)\b", re.I)


# round 10 (#273, b5 F-D6): children's readers and storybooks (Siyavula English readers HEROES and MIDGE above FM 4-25.11
# for a drowning) go after every other row unless the question asks for a story or reading, as dictionaries do.
# ponytail: a path pattern for the readers reviewers named; a catalogue "reader" kind is the upgrade.
READER_RE = re.compile(r"siyavula_grades_4_9/_english_|storybook|pedro|coloring|worksheet|/Teaching-Readers/", re.I)
STORY_Q_RE = re.compile(r"\b(?:story|stories|reading|readers?|cuentos?|lecturas?|historietas?)\b", re.I)
DEV_TIER = ("docs/cd3wd/2012/", "docs/school_textbooks/")  # gen_index.DEV_PREFIX


def _practical(path):
    """A modern-shelf row: neither the historical tier nor the development tier (CD3WD handbooks, school textbooks)."""
    return not path.startswith(DEV_TIER) and not (STATE.is_historical(path) if STATE else path.startswith("docs/survivor_library/"))


def edition_order(hits, query, new_hit):
    """Superseded editions after their current edition (inserted when absent), readers then dictionaries last unless
    asked for."""
    out, have = [], {h["path"] for h in hits}
    for h in hits:
        new = SUPERSEDED.get(h["path"])
        if new and new not in have:
            out.append(new_hit(new))
            have.add(new)
        out.append(h)
    for old, new in SUPERSEDED.items():  # an old edition above its current one moves to just after it
        if old in have and new in have:
            o = next(h for h in out if h["path"] == old)
            if out.index(o) < next(i for i, h in enumerate(out) if h["path"] == new):
                out.remove(o)
                out.insert(next(i for i, h in enumerate(out) if h["path"] == new) + 1, o)
    if not STORY_Q_RE.search(query or ""):
        # r39 acceptance (K348): a reader goes below the rows of the library's modern practical shelves only (FM 4-25.11
        # for a drowning), not below older books and other textbooks it outscores: a question whose answer is in the
        # reader's own text ("who collected ten thousand shoes", 0.77) sank under fourteen 1850-1920 shoe books (0.64-0.69)
        last = max((i for i, h in enumerate(out) if not READER_RE.search(h["path"]) and _practical(h["path"])), default=-1)
        head = out[:last + 1]
        out = [h for h in head if not READER_RE.search(h["path"])] + [h for h in head if READER_RE.search(h["path"])] + out[last + 1:]
    if not MEANING_Q_RE.search(query or ""):
        out = [h for h in out if not DICTIONARY_RE.search(h["path"])] + [h for h in out if DICTIONARY_RE.search(h["path"])]
    return out


def rank_scored(scored):
    """Rows (s, path, page, ...) with s the weighted score in thousandths (an integer), best first: by s, then path, then
    page (E5). #268 (round 10, P2, PENDING the owner, default drop): no near-tie swap. The r37 swap (#240) and its E25 integer
    band fired on one box only, because the Pi and dev score a row 0.001 apart at a rounding edge (b4 F1-F4, a8 F6, b5 W6).
    The order now depends only on the displayed scores; the round-8 pairs the swap served hold through SUPERSEDED /
    edition_order (MSF 2026 above the 2010 copy) and the age weight (WTND Burns above the 2003 WHO surgical manual)."""
    return sorted(scored, key=lambda t: (-t[0], t[1], t[2]))


def semantic_search(query, shelf, limit, lang=None, floor=None):
    """Cosine-nearest documents (one row per path, best page) from the
    precomputed sidecar, above the cosine floor; [] on any absence.
    lang: 'en'/'es' (or eng/spa) hard filter; None = all languages of the main table.
    E2/E6: the vectors_es table joins only when lang is es/spa.
    E5 (#207): rows sort by (-round(score, 3), path, page), so near-ties never swap between runs."""
    keys, rows = _load_vectors()
    if not keys:
        return []
    lang = LANG_MAP.get(lang) if lang else None
    lay = es_lay(query) if lang == "es" else ""  # b2 F7: a Spanish question also asks for the page's own words
    qv = embed_query(query + " " + lay if lay else query)
    if qv is None or len(qv) != len(rows[0]):
        return []
    if floor is None:
        floor = SEMANTIC_FLOOR
    sets = [(keys, rows, floor, True)]
    if lang == "es" and STATE.es_rows is not None:
        sets.append((STATE.es_keys, STATE.es_rows, max(floor, ES_SEMANTIC_FLOOR), False))
    scored = []  # (weighted score in thousandths, path, page, from vectors_es, age_w)
    pins = set(es_lay_pages(query)) if lang == "es" else set()  # b2 F7: the vetted page ES_LAY names comes first
    pinned = []
    for ks, rs, fl, main in sets:
        if np:
            q = np.asarray(qv, dtype=np.float32)
            sc = rs @ (q / (np.linalg.norm(q) or 1.0))
            idx = [int(i) for i in np.nonzero(sc >= fl)[0]]
            got = ((float(sc[i]), i) for i in idx)
        else:  # ~1 s over 34k pages on M2
            uq = _unit(qv)
            got = ((sum(a * b for a, b in zip(uq, dv)), i) for i, dv in enumerate(rs))
        for score, i in got:
            if score < fl or (main and lang and STATE.vec_lang[i] != lang):
                continue
            s1, w1 = weighted(score, ks[i][0])
            scored.append((s1, ks[i][0], ks[i][1], not main, w1))
        for i, k in enumerate(ks):
            if k[0] in pins:
                d = rs[i]
                sc1 = float(d @ (np.asarray(qv, dtype=np.float32) / (np.linalg.norm(qv) or 1.0))) if np else \
                    sum(a * b for a, b in zip(_unit(qv), d))
                pinned.append((round(sc1 * 1000), k[0], k[1], not main, 0.0))  # ES_LAY pinned rows are not weighted
    scored = rank_scored(scored)
    pinned.sort(key=lambda t: (-t[0], t[1], t[2]))
    scored = pinned + scored
    near = {}  # path -> [(score, page)] within PAGE_NEAR of that document's best page
    for score, path, page, es_row, _w in scored:
        best = near.setdefault(path, [(score, page)])[0][0]
        if page != near[path][0][1] and score >= best - PAGE_NEAR:
            near[path].append((score, page))
    hits, seen, n_es = [], set(), 0
    for score, path, page, es_row, w in scored:
        if path in seen or (es_row and n_es >= ES_SEMANTIC_MAX):
            continue
        if shelf and not (path == shelf
                          or path.startswith(shelf.rstrip("/") + "/")):
            continue
        if lang == "es" and third_lang(path):  # #240: no Portuguese or French rows in Spanish mode
            continue
        seen.add(path)
        n_es += es_row
        if len(near.get(path, ())) > 1:
            page = _near_page(query, path, near[path])
        h = _hit(_title_of(path), path, STATE.shelf_of(path), page, None)
        h["semantic"] = True
        h["score"] = score / 1000
        h["age_w"] = w
        hits.append(h)
        if len(hits) >= limit:
            break

    def new_hit(p):  # the current edition, scored for this question when it has vectors
        idx = STATE.vec_rows_by_path.get(p) if STATE.vec_rows_by_path else None
        # #268: the page is picked on the rounded integer, lowest page at a tie, never on raw floats (the summary's flag)
        best = max(((float(rows[i] @ (np.asarray(qv, dtype=np.float32) / (np.linalg.norm(qv) or 1.0))) if np else
                     sum(a * b for a, b in zip(_unit(qv), rows[i])), keys[i][1]) for i in idx),
                   key=lambda t: (round(t[0] * 1000), -int(t[1] or 0)), default=(0.0, None)) if idx else (0.0, None)
        s1, w1 = weighted(best[0], p)
        nh = _hit(_title_of(p), p, STATE.shelf_of(p), best[1], None)
        nh.update(semantic=True, score=s1 / 1000, age_w=w1)
        return nh
    return edition_order(hits, query, new_hit)[:limit]


# RT6 b4 W1 / E7: two pages of one document within 0.001 swap places between the Pi and dev (float differences), and the
# meningitis question ("my child has a fever and a stiff neck and is very sleepy") opened NWTND ch.28 p.21 (rheumatic
# fever, 0.748) before p.13 (meningitis, 0.747). Among a document's pages within PAGE_NEAR of its best page, the row opens
# the page that holds the most of the question's words, but only when it holds at least 2 more than the best-scored page. The document keeps
# its best score, so the order of documents does not change.
PAGE_NEAR = 2  # thousandths (E25: integers): the E7 float band (0.001) plus rounding; a wider band moved the page on half the English rows


def _near_page(query, path, cands):
    # #268 (round 10, a7a F13, a7b W8 N24): the boxes score a document's pages 0.001 apart at a rounding edge (STEP pandemics
    # p.10 on the Pi, p.7 on dev, both 0.649), so the anchor is the lowest page within 1 thousandth of the best, the same on
    # both; a page with clearly more of the question's words still wins, ties to the lower page
    anchor = min((c for c in cands if c[0] >= cands[0][0] - 1), key=lambda c: int(c[1] or 0))[1]
    toks = {w for w in re.findall(r"\w+", _fold_q(query)) if len(w) > 3}
    if not toks:
        return anchor
    con = STATE.db()
    try:
        def n_words(page):
            r = con.execute("SELECT rid FROM loc WHERE path=? AND page=?", (path, page)).fetchone()
            b = con.execute("SELECT body FROM pages WHERE rowid=?", (r[0],)).fetchone() if r else None
            b = _fold_q(b[0] or "") if b else ""
            return sum(1 for w in toks if re.search(r"\b" + re.escape(w), b))
        # only a clear win moves the page: at least 2 more of the question's words than the best-scored page (meningitis
        # p.13 holds 5 of 6, rheumatic fever p.21 holds 3); any smaller difference keeps the best-scored page, so other
        # English rows open the page they opened before (orchestrator follow-up, round 6)
        base = n_words(anchor)
        best = max(cands, key=lambda c: (n_words(c[1]), -int(c[1] or 0)))
        return best[1] if n_words(best[1]) >= base + 2 else anchor
    except sqlite3.OperationalError:
        return anchor
    finally:
        con.close()


PDF_TAG_RE = re.compile(r"(?<!<)</?[A-Za-z][A-Za-z0-9]*(?:=[^<>\s]{0,12})?>|<\?/|</[a-z]{1,8}(?=\n|<|$)|<[a-z]{2,8}(?=<)")  # same as gen_text.py


def page_excerpt(con, path, page, query, size=220, step=80, where=None):
    """Plain-text quote from the page: the window with the most distinct
    query words (mirror pages open with nav chrome, so first-N hid the
    content). None when mcp.db predates the loc table. where (a dict) gets
    the page the quote came from: a per-document vector has page 0 (#193)."""
    toks = {w for w in re.findall(r"\w+", query.lower()) if len(w) > 2}

    def window(t):
        best, at = -1, 0
        for i in range(0, max(1, len(t) - size + 1), step):
            n = sum(1 for w in toks if w in t[i:i + size].lower())
            if n > best:
                best, at = n, i
        return best, at, t

    try:
        r = con.execute("SELECT rid FROM loc WHERE path=? AND page=?",
                        (path, int(page or 0))).fetchone()
        if r:
            rids = [(r[0], int(page or 0))]
        else:  # historical docs embed per document (page 0): densest of the first 40 pages
            rids = [(x[0], x[1]) for x in con.execute(
                "SELECT rid, page FROM loc WHERE path=? ORDER BY page LIMIT 40", (path,))]
    except sqlite3.OperationalError:
        return None
    if not rids:
        return None
    best = None
    for rid, pg in rids:  # #273 (b5 F-D4 F-D8): dictionary markup and control characters, as gen_text.py clean() (interim)
        t = re.sub(r"\s+", " ", CTRL_CHAR_RE.sub(" ", PDF_TAG_RE.sub("", con.execute(
            "SELECT body FROM pages WHERE rowid=?", (rid,)).fetchone()[0] or "")))
        w = window(t) + (pg,)
        if best is None or w[0] > best[0]:
            best = w
    n, at, t, pg = best
    if where is not None:
        where["page"] = pg
        where["outdated"] = outdated_aid(t)
    if dose_page(t):  # #199: no quote from a page that carries a dose
        if where is not None:
            where["dose_page"] = True
        return None
    at = warned_start(t, sentence_start(t, at), size)  # F2 A1 en34; RT6 #214
    return safe_snippet(cut_window(t, at, size))


# ---------------------------------------------------------------- tools

TOOLS = [
    {"name": "search_library",
     "description": "Full-text search of the offline library (extracted PDFs,"
                    " mirrors, titles, and ZIM encyclopedias via kiwix),"
                    " keyword FTS plus semantic nearest-page fill when the"
                    " embedding sidecar is available."
                    " Returns titles, paths, page numbers, shelves, scores,"
                    " age weights and open-URLs; no document text (no"
                    " snippets): open the url to read the page."
                    " Drug/dose queries carry a dose notice.",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "Search terms."},
         "shelf": {"type": "string",
                   "description": "Optional shelf path filter, e.g."
                                  " 'docs/medical'."},
         "limit": {"type": "integer", "default": 10, "minimum": 1,
                   "maximum": 50},
         "language": {"type": "string", "enum": ["eng", "spa"],
                      "default": "eng",
                      "description": "Result language. Default English: no Spanish"
                                     " pages, titles or encyclopedia rows. 'spa': Spanish"
                                     " pages first (English fill), Spanish encyclopedias."}},
         "required": ["query"]}},
    {"name": "read_document",
     "description": "Read the library's own guides (RUNBOOK.md, llms.txt,"
                    " the shelf notes under docs/) as paginated plain text."
                    " Any other document (PDFs, mirrored sites,"
                    " zim/<book>/<path> encyclopedia articles) returns no"
                    " text, only its url to open.",
     "inputSchema": {"type": "object", "properties": {
         "path": {"type": "string",
                  "description": "Library-relative path (from search_library)"
                                 " or zim/<book>/<article-path>."},
         "page": {"type": "integer", "default": 1, "minimum": 1},
         "pages": {"type": "integer", "default": 3, "minimum": 1,
                   "maximum": 20}},
         "required": ["path"]}},
    {"name": "list_shelves",
     "description": "List the library shelves in curated order with counts"
                    " and descriptions.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "sun_times",
     "description": "Sunrise, sunset, solar noon and day length (NOAA solar"
                    " calculation). Defaults to the home region.",
     "inputSchema": {"type": "object", "properties": {
         "lat": {"type": "number"}, "lon": {"type": "number"},
         "date": {"type": "string",
                  "description": "YYYY-MM-DD (default: today)."}}}},
    {"name": "climate_normals",
     "description": "Monthly climate normals (temp min/mean/max degF, avg"
                    " wind mph) from the nearest NOAA normals station.",
     "inputSchema": {"type": "object", "properties": {
         "lat": {"type": "number"}, "lon": {"type": "number"},
         "month": {"type": "integer", "minimum": 1, "maximum": 12},
         "day": {"type": "integer", "minimum": 1, "maximum": 31,
                 "description": "Accepted but normals are monthly."}},
         "required": ["month"]}},
    {"name": "callsign_lookup",
     "description": "Look up a US amateur radio callsign (FCC ULS database):"
                    " licensee name, city, state.",
     "inputSchema": {"type": "object", "properties": {
         "callsign": {"type": "string"}}, "required": ["callsign"]}},
]


def _run_fts_search(con, match, shelf, limit, guarded, fuzzy=False, lang=None, bodies=False, english=False):
    """Execute pages + titles FTS queries; return hit list. lang: pages of that language only, no title rows.
    english (E6, 10-17): no Spanish pages or Spanish document titles at all."""
    hits = []
    sql = ("SELECT title, path, shelf, page,"
           " snippet(pages, 0, '', '', '...', 12), body, rank"
           " FROM pages WHERE pages MATCH ?")
    params = [match]
    if lang:
        sql += " AND lang = ?"
        params.append(lang)
    elif english:
        sql += " AND (lang IS NULL OR lang != 'es')"
    if shelf:
        sql += " AND shelf = ?"
        params.append(shelf)
    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)
    # E5 (#207): bm25 near-ties order by path, then page (rank is bm25, lower = better)
    # E27 (round 9): the age weight on health pages, rank * (1 - age_w) rounded like E25 (bm25 ties stay as before)
    rows = sorted(con.execute(sql, params), key=lambda r: (round(r[6] * (1 - age_w(r[1])), 3), r[1], int(r[3]) if str(r[3]).isdigit() else 0))
    for title, path, shf, page, snip, body, _rank in rows:
        if lang and path.startswith(ES_SKIP):
            continue
        if english and SPANISH_TITLE_RE.search(title or ""):  # E6: a Spanish book the stopword vote tagged en
            continue
        if not english and third_lang(path):  # #240: Spanish mode, no Portuguese or French documents
            continue
        h = _hit(title, path, shf,
                 int(page) if str(page).isdigit() else 0,
                 None if guarded else sentence_snippet(body, snip), body)
        if outdated_aid(body):
            h["outdated"] = True
        if bodies:
            h["_body"] = body
        if fuzzy:
            h["fuzzy"] = True
        hits.append(h)

    if lang:
        return hits
    sql = "SELECT title, path, shelf FROM titles WHERE titles MATCH ?"
    params = [match]
    if shelf:
        sql += " AND shelf = ?"
        params.append(shelf)
    sql += " LIMIT ?"
    params.append(limit)
    seen = set(h["path"] for h in hits)
    for title, path, shf in con.execute(sql, params):
        if english and spanish_doc(path, title):
            continue
        if not english and third_lang(path):
            continue
        if path not in seen:
            seen.add(path)
            h = _hit(title, path, shf, 0, None)
            if fuzzy:
                h["fuzzy"] = True
            hits.append(h)
    return hits


ES_STOP = set("""a al algo alguien algun alguna alguno ante antes aqui asi aun bien cada casa como con contra cual cuales
cualquier cuando cuanta cuantas cuanto cuantos de debe debo del desde despues donde dos el ella ellas ellos en entre era
es esa ese eso esta estaba estan estar este esto estos estoy fue hace hacer hacerlo hago hay hasta la las le les lo los
mas me mejor mi mis mucha mucho muy nada ni no nos o otra otro para pero poco por porque puede pueden puedo que quien se
sea segun ser si sin sobre solo son su sus tan tambien tengo tiene tienen todo todos tu un una uno unos unas usted y ya
yo ahora hoy dia dias vez veces bueno buena manera forma tipo cosa cosas tomo toma tomar sale salio pasa paso dice dijo
quiere pone puso llega llego empieza empezo siento siente saber""".split())
# E1 = B: the Spanish keyword passes never quote the 1990s CD3WD health manuals or the historical shelves (search.html
# lists them under "Older and historical documents"): they still tell readers to cut over a snakebite
ES_SKIP = ("docs/cd3wd/2012/health/", "docs/survivor_library/", "docs/HISTORICAL/")
ES_SAME = {"celular": "telefono", "celulares": "telefonos", "movil": "telefono"}   # the pages say teléfono
ES_SUFFIX = ("aciones", "iciones", "amiento", "imiento", "mente", "ando", "iendo", "ados", "adas", "idos", "idas",
             "cion", "ado", "ada", "ido", "ida", "ar", "er", "ir", "as", "es", "os", "a", "e", "o", "s")


# RT6 b2 F7: the words a frightened person types are not the words on the Spanish Hesperian page ("hueso roto" for
# Fracturas, "se desmayó y no despierta" for Pérdida del conocimiento, "algo en el ojo" for the eye chapter). A matching
# Spanish question (1) puts that vetted page first in search_library (like search.html's PINS, same patterns and pages),
# (2) adds the page's own words to the keyword pass (es_stems) and (3) to the Spanish query embedding (semantic_search).
# Spanish only; English questions never see this table.
# ponytail: a hand list for the b2 misses and their neighbours; a Spanish lay-word table in search_synonyms is the upgrade.
_HES = "mirrors/hesperian/es.hesperian.org/hhg/"
ES_LAY = [(re.compile(a), b, c if c.startswith("mirrors/") else _HES + c) for a, b, c in (
    # #240 round 8 (b2 F4, a7b W2): the core Spanish emergencies whose search reached no relevant page; most urgent first
    (r"\bno\s+(?:quiere|quiero|quieres|queria)\s+(?:seguir\s+)?vivir|quitar(?:se|me|le)\s+la\s+vida|suicid|\bmatar(?:se|me)\b|"
     r"que\s+todo\s+se\s+acabe|\b(?:se|me|te)\s+(?:quiere|quiero|quieres|queria|va|voy|vas|iba)\s+(?:a\s+)?matar\b",
     "emergencias de salud mental suicidio",
     "New_Where_There_Is_No_Doctor:Emergencias_de_salud_mental.html"),
    (r"^(?!.*\b(?:muelas?|dientes?|encias?|dental)\b).*(?:\b(?:hinch|inflam)\w*\b.*\b(?:cara|labios?|lengua|garganta|parpados)\b|\b(?:cara|labios?|lengua|garganta)\b.*\b(?:hinch|inflam)\w*|"
     r"reaccion\s+alergica|anafila)", "reacciones alergicas graves",
     "New_Where_There_Is_No_Doctor:Reacciones_alérgicas:_leves_o_graves.html"),
    (r"atragant|atorad|\bse\s+(?:le\s+|me\s+)?ator(?:o|a)\b|algo\s+en\s+la\s+garganta", "algo atorado en la garganta",
     "New_Where_There_Is_No_Doctor:La_respiración.html"),
    (r"^(?!.*\b(?:celular|telefono|movil|motor|carro|coche|planta|plantas|computadora|bomba)\b).*(?:\bse\s+(?:me\s+|le\s+|nos\s+)?"
     r"ahog(?:o|aron|ando|a)\b|\b(?:esta|estaba)\s+ahogando\b|\bahogad[oa]s?\b|sacamos\s+del\s+(?:rio|agua|mar|lago|pozo)|\bno\s+(?:respira|esta\s+respirando|puede\s+respirar)\b)",
     "persona ahogada respiracion de boca a boca", "New_Where_There_Is_No_Doctor:La_respiración.html"),
    (r"dolor\s+(?:muy\s+)?(?:fuerte\s+)?(?:en\s+el|de|del)\s+pecho|\bpecho\b.*\bbrazo\s+izquierdo|\b(?:aprieta|oprime)\s+el\s+pecho|"
     r"infarto|ataque\s+al\s+corazon|ataque\s+cardiaco", "ataque al corazon infarto",
     "New_Where_There_Is_No_Doctor:Ataque_al_corazón_(Infarto).html"),
    # round 9 (a7a W6 N26): a generator, brazier or charcoal indoors with group symptoms is carbon monoxide, not toothache
    # round 10 (#266 b2 R2, W8): the fuel word alone (brasero, anafre, lit charcoal) or a group headache, as the router's co row
    # (library/_app/app.js); a generator, stove or heater with a symptom in either order; never bare «calefacción» (es59)
    (r"monoxido|\b(?:brasero|bracero|anafre)s?\b|\bcarbon\s+(?:encendido|prendido|dentro|adentro)|\b(?:quem|prend|encend)\w*\s+(?:el\s+)?carbon\b|"
     r"\b(?:asador|parrilla|carbon|fogon)\b.{0,40}\b(?:dentro|adentro|cerrad\w*|cuarto|recamara|cochera|garaje|carpa|la\s+casa)\b|"
     r"^(?=.*\b(?:generador|planta\s+de\s+luz|calentador(?!\s+de\s+agua)|caldera|calefactor|estufa|boiler|propano|kerosen\w*|queroseno|lena|carbon|gas|calefacci\w*)\b)"
     r"(?=.*(?:dolor\w*\s+de\s+cabeza|duele\w*\s+la\s+cabeza|\bmare\w*|confundid\w*|\bsueno\b|somnolien\w*|adormil\w*|atontad\w*|"
     r"no\s+despierta|desmay\w*))|^(?=.*\b(?:todos|toda\s+la\s+familia|amanecimos|nos\s+levantamos|los\s+dos|ambos)\b"
     r"(?!\s+(?:los|las)\s+(?:dias|noches|mananas|tardes|meses|anos|semanas)))(?!.*\b(?:fiebre|calentura|diarrea|gripe|gripa|covid)\b)"
     r".*(?:dolor\w*\s+de\s+cabeza|duele\w*\s+la\s+cabeza|\bmare\w*)",
     "monoxido de carbono contaminacion del aire interior",
     "A_Community_Guide_to_Environmental_Health:Contaminación_del_aire_interior.html"),
    # round 9 (b2 W9 c10, c15): seizures and stroke reached no Hesperian page in the top 10
    (r"convulsi|epilep|\bsacud\w*\s+(?:\w+\s+)?todo|espuma\s+(?:en|por)\s+la\s+boca|\btiembla\s+(?:todo|de\s+todo\s+el\s+cuerpo)|\bataques?\b(?!\s+(?:de\s+(?:panico|ansiedad|nervios|risa|tos|celos)|al\s+corazon|cardiac\w*|en\s+el\s+ajedrez))",
     "ataques convulsiones", "New_Where_There_Is_No_Doctor:Ataques,_convulsiones.html"),
    (r"derrame\s+cerebral|embolia|\bictus\b|accidente\s+cerebro\w*|(?:cara|boca)\s+(?:caida|chueca|torcida|de\s+lado)|"
     r"\b(?:se\s+le\s+)?(?:cae|cayo|torcio)\s+(?:un\s+lado\s+de\s+)?la\s+(?:cara|boca)\b|lado\s+de\s+la\s+cara",
     "derrame cerebral senas un lado de la cara caido", "New_Where_There_Is_No_Doctor:Otros_problemas_del_corazón.html"),
    (r"^(?!.*\b(?:arroz|comida|frijoles|pan|motor|foco|fusible|trabajo|tortillas?|comal|frenos?|carne)\b)"
     r"(?!.*\bquem\w*\s+(?:la|una|mi|su)\s+olla\b).*(?:quemadur|\b(?:se|me|te|le|nos)\s+(?:\w+\s+)?"
     r"quem(?:o|e|aron)\b|\bquemad[oa]s?\b|escald|eskald|(?:aceite|agua|leche|cafe|sopa)\s+hirviendo)", "quemaduras",
     "New_Where_There_Is_No_Doctor:Quemaduras.html"),
    (r"embarazad\w*.*\bsangr|\bsangr\w*.*embarazad", "sangrado embarazo senas de peligro",
     "New_Where_There_Is_No_Doctor:Cuidar_a_la_mujer_embarazada.html"),
    (r"mucha\s+sangre|sangr\w*\s+(?:mucho|demasiado|sin\s+parar)|no\s+(?:para|deja)\s+de\s+sangrar|sangre\s+no\s+(?:para|se\s+(?:para|detiene|quita))|hemorragi|(?:sale|salia|brota)\s+sangre",
     "sangrado detener la sangre", "New_Where_There_Is_No_Doctor:Sangrado.html"),
    (r"\bhuesos?\b.*\b(?:rot[oa]s?|quebrad\w*|partid\w*|chuec\w*|torcid\w*)\b|\b(?:rot[oa]s?|quebr\w*)\b.*\bhuesos?\b|\bfractur|\b(?:quebr|rompi|rompe)\w*\b.*\b(?:brazos?|piernas?|munecas?|tobillos?|pies?|manos?|dedos?|costillas?|claviculas?|caderas?)\b"
     r"|\b(?:brazos?|piernas?|munecas?|tobillos?|pies?|manos?|dedos?|costillas?|claviculas?|caderas?)\b.*\b(?:quebrad\w*|rot[oa]s?|fracturad\w*|partid[oa]s?|chuec\w*)\b",
     "fractura quebrado",
     "New_Where_There_Is_No_Doctor:Fracturas,_dislocaciones_y_esguinces.html"),
    # round 10 (#266 b2 W8 c10): heat before unconscious when a heat word is present; confused, hot and no sweat in the sun
    (r"^(?!.*\b(?:fiebre|calentura|brasero|anafre|carbon|generador|monoxido)\b)(?:.*\b(?:calor|sol|insolacion)\b.*\b(?:mare\w*|desmay\w*|"
     r"calambre\w*|confundid\w*|no\s+suda|caliente|delira\w*)|.*\b(?:mare\w*|calambre\w*|desmay\w*|confundid\w*)\b.*\b(?:calor|sol)\b|"
     r".*golpe\s+de\s+calor|.*insolad\w*)",
     "agotamiento por calor golpe de calor", "New_Where_There_Is_No_Doctor:Calambres_y_agotamiento_por_calor.html"),
    (r"desmay|\bno (?:despierta|reacciona|responde)\b|inconscien|perdio el (?:sentido|conocimiento)", "perdida del conocimiento",
     "New_Where_There_Is_No_Doctor:Pérdida_del_conocimiento.html"),
    (r"\b(?:golpe\w*|pego|cayo|caer\w*|cayendo)\b.*\bcabeza\b|\bcabeza\b.*\b(?:golpe|pego|cayo|caer)", "lesiones de la cabeza",
     "New_Where_There_Is_No_Doctor:Lesiones_de_la_cabeza.html"),
    (r"^(?!.*\b(?:diarrea|dengue|fiebre|deshidrat\w*)\b).*\bojos?\b", "ojos", "New_Where_There_Is_No_Doctor:Capítulo_9:_Los_problemas_de_los_ojos_y_de_la_vista.html"),
    (r"alacran|escorpion|\bpic(?:o|ado|ada|adura|aduras)\b|aguijon|serpiente|vibora|culebra|\bmordi|mordedura",
     "picaduras mordeduras", "New_Where_There_Is_No_Doctor:Picaduras_y_mordeduras.html"),
    # #227 (round 7 class 4, b2 B2-01): a household product with a swallow verb is a poisoning question («mi niño tomó cloro»);
    # pills only with "se tomó" / "tragó" («se tragó unas pastillas»), not "tomo pastillas para la presión"
    (r"gasolina|kerosen|querosen|petroleo|thinner|veneno|envenen|raticida|insecticida|plaguicida|pesticida|"
     r"\b(?:tomo|trago|bebio)\s+(?:(?!agua\b)\S+\s+){0,3}?(?:cloro|lejia|blanqueador|destapacanos)\b|"
     r"\b(?:se\s+(?:tomo|trago|bebio)|trago)\s+(?:(?!agua\b)\S+\s+){0,3}?pastillas?\b", "envenenamiento",
     "New_Where_There_Is_No_Doctor:Envenenamiento.html"),
    (r"\bdiarrea", "deshidratacion", "New_Where_There_Is_No_Doctor:Diarrea.html"),
    (r"\b(?:cloro|lejia|blanqueador|hipoclorito)\b.*\bagua\b|\bagua\b.*\b(?:cloro|lejia|blanqueador|hipoclorito)\b|"
     r"(?:purificar|desinfectar|limpiar|potabilizar)\s+(?:el\s+)?agua|potabiliz", "agua cloro gotas por litro purificar",
     "A_Community_Guide_to_Environmental_Health:Cómo_purificar_el_agua_para_beber.html"),
    # round 9 (a7a W6 N25, N33): a pan fire is a home fire; storing drinking water is the storage page, not breast milk
    (r"\b(?:aceite|sarten|grasa|olla)\b.*\b(?:fuego|llamas?|prendi\w*|incendi\w*)\b|\b(?:fuego|llamas?|prendi\w*)\b.*\b(?:aceite|sarten|grasa)\b",
     "incendios en el hogar", "mirrors/ready_gov/www.ready.gov/es/incendios-en-el-hogar.html"),
    (r"\b(?:guard\w*|almacen\w*|conserv\w*)\b.*\bagua\b|\bagua\b.*\b(?:guard\w*|almacen\w*)\b",
     "almacenar el agua potable", "A_Community_Guide_to_Environmental_Health:Cómo_almacenar_el_agua_potable.html"),
    (r"^(?!.*\b(?:diente|dientes|muela|muelas|dental|encias?|nervio)\b).*(?:\bnervios\b|ansiedad|angustia|ataques?\s+de\s+panico)",
     "problemas de salud mental ansiedad nervios",
     "Where_Women_Have_No_Doctor:Problemas_de_salud_mental_comunes_en_las_mujeres.html"),
    (r"\b(?:letrinas?|excusados?|retretes?|sanitarios?)\b", "sanitarios",
     "A_Community_Guide_to_Environmental_Health:Capítulo_7:_Construcción_de_sanitarios.html"),
)]


def _fold_q(query):
    return "".join(c for c in unicodedata.normalize("NFD", query.lower()) if not unicodedata.combining(c))


def es_lay(query):
    """The Spanish page words ES_LAY adds for this question (accent-folded), or ''."""
    f = _fold_q(query)
    return " ".join(b for a, b, _ in ES_LAY if a.search(f))


def es_lay_pages(query):
    """The vetted Spanish page ES_LAY pins for this question: the first row that matches, like search.html pinFor()."""
    f = _fold_q(query)
    return [c for a, _, c in ES_LAY if a.search(f)][:1]


# round 10 (#273, b2 W14, b5 F-D7): English water questions about a barrel, drum, tank or cistern, muddy or cloudy water, or
# how long to boil water reached no bleach-table page first on MCP. The CGEH page holds the bleach table (1 litre to a
# 200 litre barrel) and the boiling step; it is pinned first in English search_library as ES_LAY pins Spanish.
# ponytail: one row; more English lay rows when a reviewer names them.
_CGEH_EN = "mirrors/hesperian/en.hesperian.org/hhg/"
EN_LAY = [(re.compile(a, re.I), c) for a, c in (
    (r"^(?!.*\b(?:burn\w*|scald\w*|spill\w*|blister\w*|skin|canning|canner|jars?|pasta|eggs?|rice|fish|aquarium|toilet|radiator|"
     r"engine|pool|hot\s+water\s+heater)\b)(?:.*\b(?:barrels?|drums?|tanks?|cisterns?|jerry\s*cans?|buckets?)\b.{0,60}\b(?:water|bleach|"
     r"chlorine|clorox|purif\w*|disinfect\w*|treat\w*|drink\w*)\b|.*\b(?:bleach|chlorine|clorox)\b.{0,60}\b(?:barrels?|drums?|tanks?|"
     r"cisterns?|gallons?)\b|.*\b(?:muddy|cloudy|murky)\s+water\b|.*\bwater\b.{0,40}\b(?:muddy|cloudy|murky)\b|"
     r".*\bboil\w*\b.{0,40}\bwater\b.{0,60}\b(?:safe|drink\w*|minutes?|germs?|purif\w*|disinfect\w*)\b|"
     r".*\bhow\s+long\b.{0,30}\bboil\w*\b.{0,30}\bwater\b)",
     _CGEH_EN + "A_Community_Guide_to_Environmental_Health:Make_Water_Safe_to_Drink.html"),
)]


def en_lay_pages(query):
    """The vetted English page EN_LAY pins for this question, or []."""
    return [c for a, c in EN_LAY if a.search(query or "")][:1]


TITLE_TAIL_RE = re.compile(r"\s+-\s+Hesperian Health Guides\s*$")


def _fold(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)).strip()


def es_stems(query):
    """E1 = B: the content words of a Spanish question (stopwords out, accents folded), cut to a crude stem."""
    folded = "".join(c for c in unicodedata.normalize("NFD", query.lower()) if not unicodedata.combining(c))
    words = []
    for w in re.findall(r"[a-z]+", es_lay(query) + " " + folded):  # b2 F7: the page's own words first
        w = ES_SAME.get(w, w)
        if len(w) < 4 or w in ES_STOP:
            continue
        for suf in ES_SUFFIX:
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[:-len(suf)]
                break
        if w not in words:
            words.append(w)
    return words[:6]


def _es_prior(path):
    """E1 = B ranking prior: vetted Spanish health and preparedness text (Hesperian, Ready.gov, MedlinePlus) before the
    machine-translated CD3WD/VITA bulletins, which share the same words. ponytail: two fixed weights."""
    if path.startswith("docs/") and path.endswith(".html"):  # a library-written note
        return 5.0
    if path.startswith(("mirrors/hesperian/", "mirrors/ready_gov/", "mirrors/medlineplus")) or "medlineplus.gov/spanish" in path:
        return 1.5
    if "_vita_" in path or "/_at_" in path:
        return -1.5
    return 0.0


_ES_DF = {}


def _es_df(con, stem):
    """Spanish pages holding a word that starts with stem (cached; 1-150 ms each)."""
    if stem not in _ES_DF:
        _ES_DF[stem] = con.execute("SELECT count(*) FROM pages WHERE pages MATCH ? AND lang = 'es'", (stem + "*",)).fetchone()[0]
    return _ES_DF[stem]


def es_keyword_match(query):
    """E1 = B: FTS5 expression for a Spanish question: its content words (stopwords out, accents folded) cut to a crude
    stem and prefix-matched, any TWO of them on a page. ponytail: suffix strip, not a Spanish stemmer; a unicode61-only
    Spanish table is the upgrade path if recall is short."""
    words = es_stems(query)
    if len(words) < 2:
        return " OR ".join("%s*" % w for w in words)
    return " OR ".join("(%s* AND %s*)" % (a, b) for i, a in enumerate(words) for b in words[i + 1:])


def tool_search_library(args):
    query = args.get("query", "")
    if not query.strip():
        raise ToolError("query is required")
    shelf = args.get("shelf")
    limit = max(1, min(int(args.get("limit", 10)), 50))
    guarded = dose_guard(query)  # ONE decision on ORIGINAL query, all sources (P0-4)
    # E6 (10-17): English is the default; English mode returns no Spanish pages, titles or semantic rows
    spanish = args.get("language") == "spa"

    match, _expanded = fts_match_expr_with_expansion(query, UNI_TOK if spanish else ASCII_TOK)
    hits, es_weak = [], []
    fuzzy_fallback = False
    con = STATE.db()
    try:
        # E1 = B (2026-10-13, #117): a Spanish question whose every word is not on one page (most typed questions)
        # got only semantic-fill rows, which are English-centred and carry no quote, so the Ask page showed "Ningún
        # pasaje"; and the all-words match pulled English OCR indexes ("litro de agua"). Spanish pages that hold at least two
        # of its content words come first, then the all-words hits. English (language eng) is unchanged.
        # b2 F7: the vetted page ES_LAY names for this question comes first (quote from the page, same withholds);
        # round 10 (#273 b2 W14): EN_LAY does the same for English water questions
        for path in (es_lay_pages(query) if spanish else en_lay_pages(query)):
            if shelf and not path.startswith(shelf.rstrip("/") + "/"):
                continue
            w = {}
            ex = None if guarded else page_excerpt(con, path, 0, (es_lay(query) + " " if spanish else "") + query, where=w)
            if w.get("page") is None and not con.execute("SELECT 1 FROM loc WHERE path=?", (path,)).fetchone():
                continue  # not in this index (an older mcp.db)
            h = _hit(_title_of(path), path, STATE.shelf_of(path), 0, ex)
            for k in ("outdated", "dose_page"):
                if w.get(k):
                    h[k] = True
            h["es_pin" if spanish else "en_pin"] = True
            hits.append(h)
        if spanish:
            exact = fts_match_expr(query, UNI_TOK)  # every word on one Spanish page (no synonym expansion: "agua" -> "water"
            if exact:                       # pulled English glossaries tagged es)
                # b2 F10 (#207): a page whose title IS the question ("Envenenamiento", "La depresión") comes first
                fq = _fold(query).strip(" ¿?¡!.").lower()
                seen_paths = set(h["path"] for h in hits)
                hits += [h for h in _run_fts_search(con, "title : (%s)" % exact, shelf, 20, guarded, lang="es")
                         if _fold(TITLE_TAIL_RE.sub("", h["title"] or "")).lower() == fq
                         and h["path"] not in seen_paths][:limit - len(hits)]
                seen_paths = set(h["path"] for h in hits)
                hits += [h for h in _run_fts_search(con, exact, shelf, limit * 2, guarded, lang="es")
                         if h["path"] not in seen_paths][:limit - len(hits)]
            es_match = es_keyword_match(query)
            if es_match and len(hits) < limit:
                seen_paths = set(h["path"] for h in hits)
                # the 150 best by bm25, re-ranked by the rarity-weighted share of the question's words each page holds
                # (a page with "machete" and "sangre" before one with "corte", "mano" and "sale")
                wt = {w: math.log(1e5 / max(1, _es_df(con, w))) for w in es_stems(query)}
                cand = _run_fts_search(con, es_match, shelf, 150, guarded, lang="es", bodies=True)
                for h in cand:
                    b = "".join(c for c in unicodedata.normalize("NFD", (h.pop("_body", "") or "").lower()) if not unicodedata.combining(c))
                    h["_w"] = sum(v for w, v in wt.items() if re.search(r"\b" + w, b))
                    h["_n"] = round(h["_w"] * (1 - age_w(h["path"])), 3) + _es_prior(h["path"])  # E27 age weight
                cand.sort(key=lambda h: (-h["_n"], h.get("snippet") is None))  # stable: bm25 order within a tie
                # pages holding at least half the question's word weight come before the all-words (synonym-expanded,
                # often English) hits; weaker ones only fill what is left
                half = sum(wt.values()) / 2
                for h in cand:
                    h["es_keyword"] = True
                    h.pop("_n")
                    if h.pop("_w") >= half and h["path"] not in seen_paths and len(hits) < limit:  # words only, no prior
                        hits.append(h)
                        seen_paths.add(h["path"])
                es_weak = [h for h in cand if h["path"] not in seen_paths]

        if match:
            seen_paths = set(h["path"] for h in hits)
            hits += [h for h in _run_fts_search(con, match, shelf, limit, guarded, english=not spanish)
                     if h["path"] not in seen_paths][:limit - len(hits)]
        for h in (es_weak if spanish else []):
            if len(hits) >= limit:
                break
            if h["path"] not in set(x["path"] for x in hits):
                hits.append(h)

        # R12: semantic fill from the embeddings sidecar — dedup by path,
        # after exact FTS but before the OR-junk fallback; degrades silently
        # when embeddings.db or the local embed service is absent.
        semantic_used = False
        if len(hits) < limit:
            seen_paths = set(h["path"] for h in hits)
            # 3x candidates: page-level hits collapse to one per doc below
            for h in semantic_search(query, shelf, limit * 3, lang="es" if spanish else "en"):
                if h["path"] in seen_paths:
                    continue
                # round 10 (#273, b5 F-D5): every fill row reads its page for the outdated and dose_page flags, as
                # /semantic flags the same pages; only a library-written note keeps the quote
                w = {}
                ex = page_excerpt(con, h["path"], h["page"], query, where=w)
                for k in ("outdated", "dose_page"):
                    if w.get(k):
                        h[k] = True
                if guarded:
                    h["snippet"] = None
                elif h["path"].startswith("docs/") and h["path"].endswith(".html"):
                    # #193 (a1a W7, es41): a library-written note (the only .html under docs/) quotes itself, so
                    # the Ask page can show it as a passage in either language; still through safe_snippet
                    h["snippet"] = ex
                hits.append(h)
                seen_paths.add(h["path"])
                semantic_used = True
                if len(hits) >= limit:
                    break

        # OR-fallback: zero hits → retry with OR of all tokens (original + expanded)
        if not hits and match:
            tok = UNI_TOK if spanish else ASCII_TOK
            all_toks = re.findall(tok, query)
            for exp in _expand_query(query):
                all_toks.extend(re.findall(tok, exp))
            multi = [t for t in all_toks if len(t) > 1 or t.isdigit()]
            or_match = " OR ".join('"%s"' % t for t in (multi or all_toks))
            if or_match:
                hits = _run_fts_search(con, or_match, shelf, limit, guarded, fuzzy=True, english=not spanish)
                fuzzy_fallback = bool(hits)
    finally:
        con.close()

    if not shelf:  # kiwix has no shelf concept; skip when filtering
        # Fetch kiwix separately and interleave: reserve up to 25% of limit
        # for zim results so library FTS hits don't crowd them out entirely.
        # ponytail: simple slot reservation, revisit if relevance ranking matters
        lang = args.get("language", "eng")
        kiwix_hits = kiwix_search(query, guarded, limit, lang)
        lay = zim_lay(query, lang)
        if lay:  # b5 W14 (round 9): the encyclopedia article the reader's words do not name comes first
            got = kiwix_search(lay, guarded, 3, lang)
            seen_z = {h["path"] for h in got}
            kiwix_hits = got + [h for h in kiwix_hits if h["path"] not in seen_z]
        if kiwix_hits:
            kiwix_slots = max(1, limit // 4)
            lib_slots = limit - min(len(kiwix_hits), kiwix_slots)
            hits = hits[:lib_slots] + kiwix_hits[:kiwix_slots]
        else:
            hits = hits[:limit]
    else:
        hits = hits[:limit]

    if guarded:
        # titles+links only is not enough when the title IS a dose ("Effects of taking 1800mg of ibuprofen at once",
        # medical sciences Stack Exchange): on a guarded query a hit whose title or path carries a dose figure is dropped
        hits = [h for h in hits if not DOSE_FIGURE.search((h.get("title") or "") + " " + h.get("path", "") + " " + (h.get("url") or ""))]
    hits = edition_order(hits, query, lambda p: _hit(_title_of(p), p, STATE.shelf_of(p), 0, None))[:limit]
    hits = no_text([title_only(h, "snippet", query) for h in hits])  # D4: no snippet field on any hit
    out = {"query": query, "hits": hits}
    if guarded:
        out["dose_guard"] = True
        out["notice"] = DOSE_NOTICE
    if fuzzy_fallback:
        out["fuzzy_fallback"] = True
    if semantic_used:
        out["semantic"] = True
    if any(h.get("historical") for h in hits):
        out["historical_warning"] = STATE.historical_warning
    return out


def es_title(path, title):
    """b2 N6 (round 9, #252): a Spanish Hesperian page title carries the English book namespace ("New Where There Is No
    Doctor:Quemaduras"); the page's own words stay. The prefix is the file name's, so a Spanish "Capítulo 9:" title stays."""
    if title and "/es.hesperian.org/" in path:
        ns = os.path.basename(path).split(":", 1)[0].replace("_", " ")
        if ":" in os.path.basename(path) and title.startswith(ns + ":"):
            return title[len(ns) + 1:].strip()
    return title


def _hit(title, path, shelf, page, snippet, body=None):
    title = es_title(path, title)
    h = {"title": title, "path": path, "page": page or None,
         "snippet": safe_snippet(snippet), "shelf": shelf, "url": doc_url(path), "age_w": age_w(path)}
    if dose_page(body):  # #199: the page carries a dose, so no excerpt from it at all
        h["snippet"] = None
        h["dose_page"] = True
    if STATE.is_historical(path):
        h["historical"] = True
        # warning prepended to the hit itself, verbatim (plan requirement)
        h["warning"] = STATE.historical_warning
    return h


# #207 (round 7 b5 R6): kiwix full-text snippets are often the article's footer: Wikipedia authority control («Control de
# autoridades Proyectos Wikimedia Datos: Q101017 … LCCN: sh85038517»), navboxes (v · t · e, runs of · separators), reference
# lists (Consultado el / Retrieved / Wayback Machine / ISBN) and the MedlinePlus site footer. Such a snippet is dropped (the
# hit keeps its title and link), so it never becomes an Ask passage. Ranking is unchanged.
ZIM_CHROME_RE = re.compile(r"Control de autoridades|Authority control|Proyectos Wikimedia|Wikimedia projects|Identificadores\s+\w+:|"
                           r"\b(?:LCCN|GND|BNF|BNE|VIAF|ISNI|NDL|NKC|NLI)\s*:|\bQ\d{3,}\b|Wayback Machine|\bISBN\b|Consultado el|"
                           r"Retrieved \d|Archived from|Enlaces externos|External links|Acerca de MedlinePlus|About MedlinePlus|"
                           r"Kit para redes sociales|Pol[ií]tica de privacidad|Privacy policy|\bv\s*[·•]\s*t\s*[·•]\s*e\b")


# #240 (a7b W8, the owner's folk-remedy ruling 10-25): third-party folk-remedy books in the Wikibooks ZIMs («El libro Tliliwik/
# Remedios saludables»: boil Vaporub and drink it; Ethnomedicine/Home Remedies, Home Remedies/*) are left out of search
# results, so no medical answer offers them. ponytail: a path list for the books seen; extend it when another turns up.
FOLK_ZIM_RE = re.compile(r"^zim/wikibooks_[a-z]+_[^/]+/(?:El_libro_Tliliwik/Remedios|Ethnomedicine(?:/|$)|Home_Remedies(?:/|$)|"
                         r"Remedios_caseros|Medicina_tradicional|Herbolaria)", re.I)


def zim_snippet(s):
    """#207: None for a footer or navbox kiwix snippet; else the text."""
    if not s or ZIM_CHROME_RE.search(s) or len(re.findall(r"\s[·•|]\s", s)) >= 4:
        return None
    return s


# b5 W14 (round 9, #252): «perro comió chocolate» found no theobromine page; the article title the question means is
# searched first. ponytail: a hand list for the reviewer's misses; a ZIM-title synonym table is the upgrade.
ZIM_LAY = [(re.compile(a), lang, b) for a, lang, b in (
    (r"\b(?:perr\w*|gat[oa]s?|mascota\w*)\b.*\bchocolate|\bchocolate\b.*\b(?:perr\w*|gat[oa]s?|mascota\w*)\b", "spa",
     "intoxicacion teobromina chocolate"),
    (r"\b(?:dogs?|puppy|puppies|cats?|pets?)\b.*\bchocolate|\bchocolate\b.*\b(?:dogs?|puppy|puppies|cats?|pets?)\b", "eng",
     "theobromine poisoning"))]


def zim_lay(query, lang):
    f = _fold_q(query)
    return next((b for a, l, b in ZIM_LAY if l == lang and a.search(f)), "")


def kiwix_search(query, guarded, limit, lang="eng"):
    """kiwix-serve /search, format=xml (opensearch RSS); degrade silently.
    lang filter is mandatory: kiwix-serve returns Invalid request on
    multi-book search across mixed languages. The TED ZIMs are tagged
    eng,ara,zho,... so the lang filter alone still pulls them in; they have
    no full-text index anyway, so exclude the category."""
    q = urllib.parse.urlencode({"pattern": query, "format": "xml",
                                "pageLength": min(limit, 10),
                                "books.filter.lang": lang,
                                "books.filter.notag": "_category:ted"})
    body = kiwix_fetch("/search?" + q)
    if not body:
        return []
    hits = []
    try:
        root = ET.fromstring(body)
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            lp = urllib.parse.urlparse(link).path.lstrip("/")
            if lp.startswith("content/"):
                lp = lp[len("content/"):]
            if not lp or FOLK_ZIM_RE.match("zim/" + lp):
                continue
            hits.append({
                "title": title or lp, "path": "zim/" + lp, "page": None, "age_w": 0.0,
                "snippet": None if guarded else safe_snippet(zim_snippet(strip_html(desc))) or None,
                "shelf": "encyclopedia",
                "url": "%s:%d/content/%s" % (LIBRARY_HOST, STATE.kiwix_port,
                                             lp)})
    except ET.ParseError:
        # HTML fallback: <a href="/content/<book>/...">Title</a>
        for m in re.finditer(
                r'href="(?:[^"]*?/)?content/([^"]+)"[^>]*>(.*?)</a>', body):
            lp, title = m.group(1), strip_html(m.group(2))
            if FOLK_ZIM_RE.match("zim/" + lp):
                continue
            hits.append({
                "title": title or lp, "path": "zim/" + lp, "page": None, "age_w": 0.0,
                "snippet": None, "shelf": "encyclopedia",
                "url": "%s:%d/content/%s" % (LIBRARY_HOST, STATE.kiwix_port,
                                             lp)})
    return hits


def tool_read_document(args):
    return redact_doses(_read_document(args))


NO_TEXT_NOTICE = ("This library returns no document text (D4, 2026-10-28): open the url to read the page itself. "
                  "read_document reads only the library's own guides (RUNBOOK.md, llms.txt, the shelf notes).")


def library_written(rel):
    """D4: the library's own guides: a top-level file (RUNBOOK.md, llms.txt, SKILLS_CHECKLIST.md ...) or a shelf note,
    the only .html under docs/ (#193). Everything else is document text and is never returned."""
    return "/" not in rel or (rel.startswith("docs/") and rel.lower().endswith((".html", ".htm")))


def _read_document(args):
    """D4 (#278-#281): text only for library_written() paths; any other document (PDF, mirror page, zim article) returns
    its path, url and NO_TEXT_NOTICE, plus the historical warning when its shelf carries one."""
    raw = args.get("path", "")
    page = max(1, int(args.get("page", 1)))
    npages = max(1, min(int(args.get("pages", 3)), 20))

    if raw.startswith("zim/"):
        # a8 F4 (round 9, #252): search_library returns kiwix paths percent-encoded ("The%20Raising%20and%20Care..."); quote
        # the decoded path once, so an encoded and a plain path give the same url (and "%2e%2e" is caught as "..")
        rest = urllib.parse.unquote(raw[len("zim/"):])
        if not rest or ".." in rest.split("/") or rest.startswith("/"):
            raise ToolError("invalid zim path")
        return {"path": raw, "url": "%s:%d/content/%s" % (LIBRARY_HOST, STATE.kiwix_port, urllib.parse.quote(rest)),
                "notice": NO_TEXT_NOTICE}

    resolved = safe_library_path(raw)
    if resolved is None:
        raise ToolError("invalid path: must be a relative path inside the "
                        "library (no '..', no absolute paths)")
    real, rel = resolved  # real = fs access; rel = db key / display path

    if not library_written(rel):
        if not os.path.exists(real):
            con = STATE.db()
            try:
                known = con.execute("SELECT 1 FROM loc WHERE path=? LIMIT 1", (rel,)).fetchone()
            except sqlite3.OperationalError:  # mcp.db predates loc: the full scan, as the old PDF read did
                known = con.execute("SELECT 1 FROM pages WHERE path=? LIMIT 1", (rel,)).fetchone()
            finally:
                con.close()
            if not known:
                raise ToolError("file not found: %s" % rel)
        out = {"path": rel, "url": doc_url(rel), "notice": NO_TEXT_NOTICE}
        if STATE.is_historical(rel):
            out["warning"] = STATE.historical_warning
        return out

    ext = os.path.splitext(rel)[1].lower()
    if ext not in (".html", ".htm", ".md", ".txt"):
        raise ToolError("unsupported document type '%s'; open %s"
                        % (ext or "(none)", doc_url(rel)))
    if not os.path.isfile(real):
        raise ToolError("file not found: %s" % rel)
    with open(real, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if ext in (".html", ".htm"):
        text = strip_html(text)
    chunks = [text[i:i + TEXT_PAGE_CHARS]
              for i in range(0, max(len(text), 1), TEXT_PAGE_CHARS)] or [""]
    if page > len(chunks):
        raise ToolError("page %d beyond end (document has %d page(s))"
                        % (page, len(chunks)))
    body = "".join(chunks[page - 1:page - 1 + npages])
    warning = STATE.historical_warning if STATE.is_historical(rel) else None
    return {"path": rel, "page": page, "total_pages": len(chunks),
            "text": (warning + "\n\n" + body) if warning else body}


def tool_list_shelves(args):
    return {"shelves": STATE.shelves}


def tool_sun_times(args):
    lat = float(args.get("lat", STATE.home_lat))
    lon = float(args.get("lon", STATE.home_lon))
    dstr = args.get("date")
    if dstr:
        try:
            d = datetime.strptime(dstr, "%Y-%m-%d").date()
        except ValueError:
            raise ToolError("date must be YYYY-MM-DD")
    else:
        d = datetime.now().date()

    doy = d.timetuple().tm_yday
    # NOAA solar calculation (General Solar Position Calculations, NOAA SRRB)
    gamma = 2 * math.pi / 365.0 * (doy - 1 + 0.5)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma)
                       - 0.032077 * math.sin(gamma)
                       - 0.014615 * math.cos(2 * gamma)
                       - 0.040849 * math.sin(2 * gamma))
    decl = (0.006918 - 0.399912 * math.cos(gamma)
            + 0.070257 * math.sin(gamma) - 0.006758 * math.cos(2 * gamma)
            + 0.000907 * math.sin(2 * gamma) - 0.002697 * math.cos(3 * gamma)
            + 0.00148 * math.sin(3 * gamma))
    latr = math.radians(lat)
    cos_ha = (math.cos(math.radians(90.833))
              / (math.cos(latr) * math.cos(decl))
              - math.tan(latr) * math.tan(decl))
    if cos_ha > 1:
        return {"date": d.isoformat(), "lat": lat, "lon": lon,
                "polar": "night", "daylength_hours": 0.0}
    if cos_ha < -1:
        return {"date": d.isoformat(), "lat": lat, "lon": lon,
                "polar": "day", "daylength_hours": 24.0}
    ha = math.degrees(math.acos(cos_ha))
    sunrise_utc_min = 720 - 4 * (lon + ha) - eqtime
    sunset_utc_min = 720 - 4 * (lon - ha) - eqtime
    noon_utc_min = 720 - 4 * lon - eqtime

    def fmt(mins):
        base = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        t = base + timedelta(minutes=mins)
        local = t.astimezone()  # server-local zone (Pi runs local time)
        return {"utc": t.strftime("%H:%M"), "local": local.strftime("%H:%M"),
                "local_tz": str(local.tzinfo)}

    return {"date": d.isoformat(), "lat": lat, "lon": lon,
            "sunrise": fmt(sunrise_utc_min), "solar_noon": fmt(noon_utc_min),
            "sunset": fmt(sunset_utc_min),
            "daylength_hours": round(2 * ha / 15.0, 2)}


def tool_climate_normals(args):
    lat = float(args.get("lat", STATE.home_lat))
    lon = float(args.get("lon", STATE.home_lon))
    month = int(args.get("month", 0))
    if not 1 <= month <= 12:
        raise ToolError("month must be 1-12")
    con = STATE.db()
    try:
        best = None
        for sid, name, slat, slon in con.execute(
                "SELECT id, name, lat, lon FROM stations"):
            dk = haversine(lat, lon, slat, slon)
            if best is None or dk < best[0]:
                best = (dk, sid, name, slat, slon)
        if best is None:
            raise ToolError("no climate stations in database")
        dk, sid, name, slat, slon = best
        row = con.execute(
            "SELECT tmin, tmean, tmax, wind_avg FROM normals"
            " WHERE station = ? AND month = ?", (sid, month)).fetchone()
    finally:
        con.close()
    if row is None:
        raise ToolError("no normals for station %s month %d" % (sid, month))
    out = {"station": {"id": sid, "name": name, "lat": slat, "lon": slon,
                       "distance_km": round(dk, 1)},
           "month": month, "tmin_f": row[0], "tmean_f": row[1],
           "tmax_f": row[2], "wind_avg_mph": row[3],
           "note": "monthly normals (day-level not precomputed)"}
    if args.get("day"):
        out["day"] = int(args["day"])
    return out


def tool_callsign_lookup(args):
    cs = str(args.get("callsign", "")).strip().upper()
    if not cs:
        raise ToolError("callsign is required")
    con = STATE.db()
    try:
        row = con.execute(
            "SELECT callsign, name, city, state FROM callsigns"
            " WHERE callsign = ?", (cs,)).fetchone()
    finally:
        con.close()
    if row is None:
        raise ToolError("callsign %s not found in FCC database" % cs)
    return {"callsign": row[0], "name": row[1], "city": row[2],
            "state": row[3]}


TOOL_FUNCS = {
    "search_library": tool_search_library,
    "read_document": tool_read_document,
    "list_shelves": tool_list_shelves,
    "sun_times": tool_sun_times,
    "climate_normals": tool_climate_normals,
    "callsign_lookup": tool_callsign_lookup,
}


class ToolError(Exception):
    pass


# ---------------------------------------------------------------- rpc

def rpc_dispatch(msg):
    """Return (response_dict_or_None, http_status)."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" \
            or not isinstance(msg.get("method"), str):
        return ({"jsonrpc": "2.0", "id": msg.get("id") if isinstance(msg, dict)
                 else None,
                 "error": {"code": -32600, "message": "invalid request"}}, 400)
    method = msg["method"]
    mid = msg.get("id")
    params = msg.get("params") or {}

    if mid is None:  # notification (notifications/initialized etc.)
        return (None, 202)

    if method == "initialize":
        pv = params.get("protocolVersion")
        return (_result(mid, {
            "protocolVersion": pv if pv in PROTOCOL_VERSIONS
            else DEFAULT_PROTOCOL,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
            "instructions": INSTRUCTIONS}), 200)
    if method == "ping":
        return (_result(mid, {}), 200)
    if method == "tools/list":
        return (_result(mid, {"tools": TOOLS}), 200)
    if method == "tools/call":
        name = params.get("name")
        fn = TOOL_FUNCS.get(name)
        if fn is None:
            return (_result(mid, _tool_error("unknown tool: %r" % name)), 200)
        try:
            out = fn(params.get("arguments") or {})
        except ToolError as e:
            return (_result(mid, _tool_error(str(e))), 200)
        except Exception as e:  # never crash the connection on a tool bug
            return (_result(mid, _tool_error("internal error: %s" % e)), 200)
        return (_result(mid, {"content": [
            {"type": "text",
             "text": json.dumps(out, ensure_ascii=False, indent=1)}],
            "isError": False}), 200)

    return ({"jsonrpc": "2.0", "id": mid,
             "error": {"code": -32601,
                       "message": "method not found: %s" % method}}, 200)


def _result(mid, result):
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def _tool_error(text):
    return {"content": [{"type": "text", "text": text}], "isError": True}


# ---------------------------------------------------------------- http

LOCAL_ORIGIN_RE = re.compile(r"^https?://(?:localhost|127\.0\.0\.1)(?::\d+)?$")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "lantern-mcp/1.0"

    def log_message(self, fmt, *a):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % a))

    def _send(self, status, obj=None, cors=False):
        body = json.dumps(obj).encode("utf-8") if obj is not None else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Mcp-Session-Id", "lantern-stateless")
        origin = self.headers.get("Origin") or ""
        if cors and LOCAL_ORIGIN_RE.match(origin):  # dev only: search.html on localhost:8765 calling :8090 directly
            self.send_header("Access-Control-Allow-Origin", origin)  # a8 N-cors: no "*" behind nginx on the box
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        path, _, qs = self.path.partition("?")
        if path == "/mcp":
            self._send(405, {"error": "method not allowed; POST JSON-RPC"})
        elif path == "/semantic":
            # H37b: search.html body-hit fusion. D4 (#278-#281): rows carry no
            # excerpt field; the page is still read for its flags and page.
            a = urllib.parse.parse_qs(qs)
            q = (a.get("q") or [""])[0].strip()
            if not q:
                self._send(400, {"error": "q is required"}, cors=True)
                return
            try:
                limit = max(1, min(int((a.get("limit") or ["20"])[0]), 50))
                floor = a.get("floor")  # tuning knob for eval_gold.py
                floor = float(floor[0]) if floor else None
            except ValueError:
                self._send(400, {"error": "bad limit/floor"}, cors=True)
                return
            hits = semantic_search(q, None, limit,
                                   lang=(a.get("lang") or ["eng"])[0], floor=floor)
            # the page read (no excerpt leaves): outdated, dose_page and the
            # page a per-document vector links; skipped on drug queries.
            con = None if dose_guard(q) else STATE.db()
            try:
                out = []
                for h in hits:
                    row = {"path": h["path"], "page": h["page"] or 0,
                           "score": h["score"], "title": h["title"],
                           "shelf": h["shelf"], "age_w": h["age_w"]}
                    if STATE.is_historical(h["path"]):
                        row["historical"] = True   # chat.html routes it via the interstitial
                    if con is not None:
                        w = {}
                        row["excerpt"] = page_excerpt(con, h["path"], h["page"], q, where=w)
                        if not row["page"] and w.get("page"):
                            row["page"] = w["page"]  # #193 (a1a W4): cd3wd quotes linked p.1
                        if w.get("outdated"):
                            row["outdated"] = True
                        if w.get("dose_page"):
                            row["dose_page"] = True  # #199: chat.html shows it title-only
                    title_only(row, "excerpt", q)  # E22 B (#238); on a drug query too, so search.html sees the flag
                    out.append(row)
                no_text(out)  # D4: no excerpt field
            finally:
                if con is not None:
                    con.close()
            self._send(200, out, cors=True)
        elif path == "/rerank":
            # E1b: search.html re-scores its keyword hits by cosine. Paths
            # only, no snippets, so no dose guard. lang accepted, unused:
            # the client already chose the paths.
            a = urllib.parse.parse_qs(qs)
            q = (a.get("q") or [""])[0].strip()
            paths = [p for p in (a.get("paths") or [""])[0].split("|") if p][:50]
            if not q or not paths:
                self._send(400, {"error": "q and paths are required"}, cors=True)
                return
            self._send(200, rerank(q, paths), cors=True)
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path.split("?")[0] != "/mcp":
            self._send(404, {"error": "not found"})
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(n)
        except Exception:
            self._send(400, {"error": "bad request"})
            return
        try:
            msg = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            self._send(400, {"jsonrpc": "2.0", "id": None,
                             "error": {"code": -32700,
                                       "message": "parse error"}})
            return
        resp, status = rpc_dispatch(msg)
        self._send(status, resp)


def main():
    global STATE, SEMANTIC_FLOOR, ES_SEMANTIC_FLOOR, ES_SEMANTIC_MAX
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--library", required=True)
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--host", default="127.0.0.1",  # F8/F1 2026-10-09: nginx proxies /mcp and /semantic; LAN never talks to :8090 directly
                    help="bind address (default loopback; 0.0.0.0 only for a box without the nginx proxy)")
    ap.add_argument("--kiwix", default="http://127.0.0.1:8080")
    ap.add_argument("--db", default=None)
    ap.add_argument("--embed", default=None,
                    help="local embedding endpoint (default"
                         " http://127.0.0.1:8091/embedding)")
    ap.add_argument("--embdb", default=None,
                    help="embeddings sidecar db (default"
                         " <library>/_app/mcp/embeddings.db)")
    ap.add_argument("--floor", type=float, default=None,
                    help="override SEMANTIC_FLOOR (eval sweeps)")
    ap.add_argument("--es-max", type=int, default=None,
                    help="override ES_SEMANTIC_MAX, vectors_es rows per result list (eval sweeps)")
    ap.add_argument("--es-floor", type=float, default=None,
                    help="override ES_SEMANTIC_FLOOR, the vectors_es floor (eval sweeps)")
    a = ap.parse_args()
    if a.floor is not None:
        SEMANTIC_FLOOR = a.floor
    if a.es_floor is not None:
        ES_SEMANTIC_FLOOR = a.es_floor
    if a.es_max is not None:
        ES_SEMANTIC_MAX = a.es_max
    db = a.db or os.path.join(a.library, "_app", "mcp", "mcp.db")
    if not os.path.isfile(db):
        sys.exit("mcp.db not found at %s (run build_mcp_index.py)" % db)
    STATE = State(a.library, db, a.kiwix, embed_url=a.embed, emb_db=a.embdb)
    _load_synonyms()
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    threading.Thread(target=_load_vectors, daemon=True).start()  # warm /semantic at boot
    print("lantern-mcp on %s:%d  library=%s  db=%s  kiwix=%s  guard=%d drugs  synonyms=%d  embdb=%s"
          % (a.host, a.port, STATE.library, db, STATE.kiwix,
             len(STATE.guard_drugs), len(SYNONYMS),
             "present" if os.path.isfile(STATE.emb_db) else "absent"))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
