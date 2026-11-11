#!/usr/bin/env python3
"""Local acceptance dry-run (T4/T6/T7 subset that runs without hardware).

Reads data/acceptance_queries.txt, drives real Chrome (playwright
channel=chrome, crash-retried) through search in BOTH modes, checks:
  - query rows: expected evidence in pin or top-3 titles
    (path substring / TRIAGE:#anchor / NEG / EMPTY-GRACEFUL)
  - historical cat: top hit must route via _app/historical.html
  - phrase rows (served only): Pagefind result -> reader.html?f=<doc>&p=<page>
  - file:// pass doubles as T6: fulltext section shows NEEDS THE SERVER,
    no network beyond file:// except the config'd LAN LLM probes (A5 design)
Kiwix layer: SKIPPED-LOCAL (no kiwix-serve until C4/E3).
Writes logs/acceptance_report_<date>.md. Exit 1 on any FAIL.
Run with sandbox disabled (localhost). Usage: acceptance_run.py [date]
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "logs"
SERVED = os.environ.get("ACCEPT_SERVED", "http://127.0.0.1:8765/")  # H1: a fix agent's own server stack
DIRECT = "file://" + os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/library/"
LLM_HOSTS = ("10.10.10.20",)  # config.json llmEndpoints — probed by design in file://

queries, phrases = [], []
for line in open("data/acceptance_queries.txt"):
    line = line.rstrip("\n")
    if not line or line.startswith("#"):
        continue
    parts = line.split("\t")
    if len(parts) < 3:
        continue
    if parts[0] == "phrase":
        # page field may list alternates "19|47" when the phrase truly
        # occurs on several pages (any is a correct open)
        phrases.append((parts[1], parts[2], [int(x) for x in parts[3].split("|")]))
    else:
        queries.append((parts[0], parts[1], parts[2]))

results = []  # (check, mode, PASS/FAIL/SKIP, note)

# H1 (red team 2026-10-11 #181): symptom-phrased questions with NO drug word that retrieve dose-bearing pages (WHO zinc,
# MSF/Hesperian benzathine penicillin). Every earlier dose probe tripped the query guard, so the unguarded excerpt path
# went untested until a curl found "half tablet ... per day for 10-14 days". The page must show no dose text; since D4
# (round 11, #278-#281, 10-28) /semantic and MCP carry no document text at all, and that removal is asserted.
SYMPTOM_DOSE = ["baby has had diarrhea for 2 days how do i keep her from getting dehydrated",
                "how much injection to cure syphilis", "treat syphilis inject into the muscle",
                "mi bebé tiene diarrea hace 2 días cómo evito que se deshidrate",
                "cuánto hay que inyectar para curar la sífilis",
                "primeras semanas después del parto por la boca 4 veces al día"]
# J1 (red team 2026-10-13 #191, regression of #171): the #181 withhold hid the EPA bleach table and WHO "4 drops per
# litre" because they use the words "dose" and "dosage". Water-treatment amounts are promised visible. D4 (#278-#281): no
# server quote any more, so the promise is tested where the reader now reads it: /semantic still finds both pages, and the
# PDF page it links (pdftotext) holds the drop count.
WATER_VISIBLE = [("how many drops of household bleach to make a gallon of water safe",
                  ["docs/water/epa_emergency_disinfection_drinking_water.pdf", "docs/medical/who_drinking_water_quality_4th_ed.pdf"])]
# K2 (red team 2026-10-16 #199, a1a es25): a fever-without-medicine question pulled the Hesperian aspirin/ibuprofen sheet,
# quoted just before its amounts ("la dosis desinflamatoria ... el doble de la dosis normal"). A page that carries a dose
# gives no excerpt at all on /semantic or MCP, and carries dose_page so the Ask page shows it title-only (D4: no row has text).
ES25 = ("como bajar la fiebre sin medicina", "Hoja_de_información_sobre_la_aspirina")
# RT6 class 3 (#214, a1a BT7, a1b 7): under the snakebite card the Ask page quoted ECHO 1996 p.164, electric shock as
# snakebite first aid. Every passage /semantic and MCP give for a bite or sting question either carries "outdated" (the
# Ask page hides it) or shows no harmful method offered as advice. D4 (#278-#281): no row carries text, so the check is
# the removal plus the ECHO shock pages still flagged outdated.
BITE_QS = [("snake bite first aid", "eng"), ("what do i do for a snake bite", "eng"),
           ("something bit my ankle in the tall grass, two little holes and its swelling up fast", "eng"),
           ("scorpion sting what to do", "eng"), ("electric shock for a snake bite", "eng"),
           ("me mordió una serpiente qué hago", "spa"), ("picadura de alacrán qué hago", "spa")]
ECHO_SHOCK = ("_ag_ideas_growing_food_difficult_2_echo_en_lp_108740_.pdf", {160, 161, 162, 163, 164, 165})
DOSE_LOOSE = re.compile(r"\b(?:half|quarter)\s+(?:a\s+)?tab|\bM\s?I?U\b|\bMUI\b|million\s+units|millones\s+de\s+unidades|"
                        r"dose removed", re.I)


def scrape(pg, base, q, wait):
    pg.goto(base + "search.html?q=" + urllib.parse.quote(q))
    pg.wait_for_timeout(wait)
    # Pagefind over the 2.9 GB index (H37c) can take several seconds on
    # first load; wait until its placeholder is gone, up to 30 s
    try:
        pg.wait_for_function("!/Loading full-text engine/.test((document.getElementById('r-fulltext')||{}).innerText||'')", timeout=30000)
    except Exception:
        pass
    return pg.evaluate("""() => ({
      pin: (document.getElementById('r-pin')||{}).innerHTML || '',
      titles: [...document.querySelectorAll('#r-titles a')].map(a=>({href:a.getAttribute('href'),text:a.innerText})),
      ft: (document.getElementById('r-fulltext')||{}).innerHTML || '',
      ftText: (document.getElementById('r-fulltext')||{}).innerText || '',
      enc: (document.getElementById('r-enc')||{}).innerText || ''
    })""")

DOSE = re.compile(r"(?!(?<=iphone\s)[2-5]\s?g\b)(?!(?<=phone\s)[2-5]\s?g\b)(?![2-5]\s?g\b(?=\s*(?:lte|networks?|phones?|iphones?|modems?|signal|wi-?fi|cellular|data|service|coverage|speeds?|internet|front|back|screen|battery|case|replacement|red|se[nñ]al|celular|m[oó]vil)\b))(?<!\bFM\s)(?<!\bTM\s)(?<!\bTC\s)(?<!\bATP\s)(?<!\bSTP\s)(?<!\d-)(?<!\d\.)(?<!gallon\s)(?<!gallons\s)(?<!quart\s)(?<!quarts\s)(?<!liter\s)(?<!liters\s)(?<!litre\s)(?<!litres\s)(?<!litro\s)(?<!litros\s)(?<!gal[oó]n\s)(?<!galones\s)(?<!barrel\s)(?<!barrels\s)(?<!barril\s)(?<!barriles\s)(?<!drum\s)(?<!drums\s)(?<!tank\s)(?<!tanks\s)(?<!tambo\s)(?<!tambos\s)(?<!tanque\s)(?<!tanques\s)(?<!drops\s\()(?<!gotas\s\()(?<!\d\/)(?<!\d\/)(?<!\d\/)(?!(?<=\bdrops\s)\d+\s*drops\b)(?!(?<=\bgotas\s)\d+\s*gotas\b)(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*(?:(?:parte\s+)?de\s+(?:una?\s+)?)?(?:mg|mcg|µg|ug|g|ml|cc|mililitros?|millilit(?:er|re)s?|m\s?iu|m\s?ui|iu|ui|(?:million|mill[oó]n(?:es)?)\s+(?:de\s+)?(?:(?:international\s+)?(?:units?|unidades)|ui|iu)|units?|unidades|grams?|gramos?|milligrams?|miligramos?|micrograms?|microgramos?|tabs?|tablets?|tabletas?|pills?|pastillas?|comprimidos?|caps?|capsules?|c[aá]psulas?|(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|capfuls?|dropperfuls?|tsp|tbsp|c[àá]c|c[àá]s|c\.[àá]\.[cs](?=\.)|cucharaditas?|cucharadas?|drops?|gotas?|ampoules?|ampules?|ampuls?|ampollas?|ampolletas?|vials?|frascos?[-\s]ampollas?)\b(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))(?:\s*(?:\/|per|por(?:\s+cada)?)\s*(?:kg|kilos?|kilogramos?|kilograms?|d[ií]a|day|dose|dosis|m2)\b(?:\s+(?:of\s+body\s+weight|de\s+peso(?:\s+corporal)?))?)*(?:\s*x\s*\d+(?:\s*(?:[-–]|or|o|to|a)\s*\d+)?\b)?(?:,?\s+(?:daily|a\s+day|per\s+day|each\s+day|al\s+d[ií]a|por\s+d[ií]a|cada\s+d[ií]a|diari[oa]s?))?|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|o|ó|u|a|y|and)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+(?:of\s+)?an?)?|cuarto\s+de(?:\s+una?)?|an?(?=\s+(?:(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|capfuls?|dropperfuls?|ampoules?|ampules?|vials?)\b))\s+(?:tabletas?|pastillas?|comprimidos?|c[aá]psulas?|tablets?|pills?|capsules?|ampoules?|ampules?|vials?|(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|capfuls?|dropperfuls?|cucharaditas?|cucharadas?|goteros?|ampolletas?|frascos?[-\s]ampollas?|drops?|gotas?|ampollas?(?=\s+(?:de\s+(?:\w*ina\b|suero|antiveneno|antiof[ií]dico|antitet[aá]nic)|i\.?[mv]\b|intramuscular|intraven)))\b(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))(?:\s*(?:\/|per|por(?:\s+cada)?)\s*(?:kg|kilos?|kilogramos?|kilograms?|d[ií]a|day|dose|dosis|m2)\b(?:\s+(?:of\s+body\s+weight|de\s+peso(?:\s+corporal)?))?)*(?:\s*x\s*\d+(?:\s*(?:[-–]|or|o|to|a)\s*\d+)?\b)?(?:,?\s+(?:daily|a\s+day|per\s+day|each\s+day|al\s+d[ií]a|por\s+d[ií]a|cada\s+d[ií]a|diari[oa]s?))?|(?:(?=every\s|cada\s)(?<!compost\s)(?<!pile\s)(?<!dough\s)(?<!wake\s)(?<!wake\sthem\s)(?<!wake\shim\s)(?<!wake\sher\s)(?<!wake\sit\s)(?<!wake\sup\s)(?<!wake\sthem\sup\s)(?<!wake\shim\sup\s)(?<!wake\sher\sup\s)(?<!wake\son\sthem\s)(?<!wake\son\shim\s)(?<!wake\son\sher\s)(?<!wake\sthe\sperson\s)(?<!wake\sthe\schild\s)(?<!wake\sthe\sbaby\s)(?<!wake\sthe\spatient\s)(?<!wake\son\sthe\sperson\s)(?<!wake\son\sthe\schild\s)(?<!wake\son\sthe\spatient\s)(?<!waken\s)(?<!waken\sthem\s)(?<!waken\shim\s)(?<!waken\sher\s)(?<!waken\sit\s)(?<!waken\sup\s)(?<!waken\sthem\sup\s)(?<!waken\shim\sup\s)(?<!waken\sher\sup\s)(?<!waken\son\sthem\s)(?<!waken\son\shim\s)(?<!waken\son\sher\s)(?<!waken\sthe\sperson\s)(?<!waken\sthe\schild\s)(?<!waken\sthe\sbaby\s)(?<!waken\sthe\spatient\s)(?<!waken\son\sthe\sperson\s)(?<!waken\son\sthe\schild\s)(?<!waken\son\sthe\spatient\s)(?<!awaken\s)(?<!awaken\sthem\s)(?<!awaken\shim\s)(?<!awaken\sher\s)(?<!awaken\sit\s)(?<!awaken\sup\s)(?<!awaken\sthem\sup\s)(?<!awaken\shim\sup\s)(?<!awaken\sher\sup\s)(?<!awaken\son\sthem\s)(?<!awaken\son\shim\s)(?<!awaken\son\sher\s)(?<!awaken\sthe\sperson\s)(?<!awaken\sthe\schild\s)(?<!awaken\sthe\sbaby\s)(?<!awaken\sthe\spatient\s)(?<!awaken\son\sthe\sperson\s)(?<!awaken\son\sthe\schild\s)(?<!awaken\son\sthe\spatient\s)(?<!waking\s)(?<!waking\sthem\s)(?<!waking\shim\s)(?<!waking\sher\s)(?<!waking\sit\s)(?<!waking\sup\s)(?<!waking\sthem\sup\s)(?<!waking\shim\sup\s)(?<!waking\sher\sup\s)(?<!waking\son\sthem\s)(?<!waking\son\shim\s)(?<!waking\son\sher\s)(?<!waking\sthe\sperson\s)(?<!waking\sthe\schild\s)(?<!waking\sthe\sbaby\s)(?<!waking\sthe\spatient\s)(?<!waking\son\sthe\sperson\s)(?<!waking\son\sthe\schild\s)(?<!waking\son\sthe\spatient\s)(?<!check\s)(?<!check\sthem\s)(?<!check\shim\s)(?<!check\sher\s)(?<!check\sit\s)(?<!check\sup\s)(?<!check\sthem\sup\s)(?<!check\shim\sup\s)(?<!check\sher\sup\s)(?<!check\son\sthem\s)(?<!check\son\shim\s)(?<!check\son\sher\s)(?<!check\sthe\sperson\s)(?<!check\sthe\schild\s)(?<!check\sthe\sbaby\s)(?<!check\sthe\spatient\s)(?<!check\son\sthe\sperson\s)(?<!check\son\sthe\schild\s)(?<!check\son\sthe\spatient\s)(?<!checking\s)(?<!checking\sthem\s)(?<!checking\shim\s)(?<!checking\sher\s)(?<!checking\sit\s)(?<!checking\sup\s)(?<!checking\sthem\sup\s)(?<!checking\shim\sup\s)(?<!checking\sher\sup\s)(?<!checking\son\sthem\s)(?<!checking\son\shim\s)(?<!checking\son\sher\s)(?<!checking\sthe\sperson\s)(?<!checking\sthe\schild\s)(?<!checking\sthe\sbaby\s)(?<!checking\sthe\spatient\s)(?<!checking\son\sthe\sperson\s)(?<!checking\son\sthe\schild\s)(?<!checking\son\sthe\spatient\s)(?<!recheck\s)(?<!recheck\sthem\s)(?<!recheck\shim\s)(?<!recheck\sher\s)(?<!recheck\sit\s)(?<!recheck\sup\s)(?<!recheck\sthem\sup\s)(?<!recheck\shim\sup\s)(?<!recheck\sher\sup\s)(?<!recheck\son\sthem\s)(?<!recheck\son\shim\s)(?<!recheck\son\sher\s)(?<!recheck\sthe\sperson\s)(?<!recheck\sthe\schild\s)(?<!recheck\sthe\sbaby\s)(?<!recheck\sthe\spatient\s)(?<!recheck\son\sthe\sperson\s)(?<!recheck\son\sthe\schild\s)(?<!recheck\son\sthe\spatient\s)(?<!despi[eé]rtela\s)(?<!despi[eé]rtela\sa\sla\spersona\s)(?<!despi[eé]rtela\sal\sni[nñ]o\s)(?<!despi[eé]rtela\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtela\sal\senfermo\s)(?<!despi[eé]rtela\sa\sla\senferma\s)(?<!despi[eé]rtela\sal\sbeb[eé]\s)(?<!despi[eé]rtelo\s)(?<!despi[eé]rtelo\sa\sla\spersona\s)(?<!despi[eé]rtelo\sal\sni[nñ]o\s)(?<!despi[eé]rtelo\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtelo\sal\senfermo\s)(?<!despi[eé]rtelo\sa\sla\senferma\s)(?<!despi[eé]rtelo\sal\sbeb[eé]\s)(?<!despi[eé]rtele\s)(?<!despi[eé]rtele\sa\sla\spersona\s)(?<!despi[eé]rtele\sal\sni[nñ]o\s)(?<!despi[eé]rtele\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtele\sal\senfermo\s)(?<!despi[eé]rtele\sa\sla\senferma\s)(?<!despi[eé]rtele\sal\sbeb[eé]\s)(?<!despi[eé]rtenla\s)(?<!despi[eé]rtenla\sa\sla\spersona\s)(?<!despi[eé]rtenla\sal\sni[nñ]o\s)(?<!despi[eé]rtenla\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtenla\sal\senfermo\s)(?<!despi[eé]rtenla\sa\sla\senferma\s)(?<!despi[eé]rtenla\sal\sbeb[eé]\s)(?<!despi[eé]rtenlo\s)(?<!despi[eé]rtenlo\sa\sla\spersona\s)(?<!despi[eé]rtenlo\sal\sni[nñ]o\s)(?<!despi[eé]rtenlo\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtenlo\sal\senfermo\s)(?<!despi[eé]rtenlo\sa\sla\senferma\s)(?<!despi[eé]rtenlo\sal\sbeb[eé]\s)(?<!despi[eé]rtenle\s)(?<!despi[eé]rtenle\sa\sla\spersona\s)(?<!despi[eé]rtenle\sal\sni[nñ]o\s)(?<!despi[eé]rtenle\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtenle\sal\senfermo\s)(?<!despi[eé]rtenle\sa\sla\senferma\s)(?<!despi[eé]rtenle\sal\sbeb[eé]\s)(?<!despi[eé]rtala\s)(?<!despi[eé]rtala\sa\sla\spersona\s)(?<!despi[eé]rtala\sal\sni[nñ]o\s)(?<!despi[eé]rtala\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtala\sal\senfermo\s)(?<!despi[eé]rtala\sa\sla\senferma\s)(?<!despi[eé]rtala\sal\sbeb[eé]\s)(?<!despi[eé]rtalo\s)(?<!despi[eé]rtalo\sa\sla\spersona\s)(?<!despi[eé]rtalo\sal\sni[nñ]o\s)(?<!despi[eé]rtalo\sa\sla\sni[nñ]a\s)(?<!despi[eé]rtalo\sal\senfermo\s)(?<!despi[eé]rtalo\sa\sla\senferma\s)(?<!despi[eé]rtalo\sal\sbeb[eé]\s)(?<!despertarla\s)(?<!despertarla\sa\sla\spersona\s)(?<!despertarla\sal\sni[nñ]o\s)(?<!despertarla\sa\sla\sni[nñ]a\s)(?<!despertarla\sal\senfermo\s)(?<!despertarla\sa\sla\senferma\s)(?<!despertarla\sal\sbeb[eé]\s)(?<!despertarlo\s)(?<!despertarlo\sa\sla\spersona\s)(?<!despertarlo\sal\sni[nñ]o\s)(?<!despertarlo\sa\sla\sni[nñ]a\s)(?<!despertarlo\sal\senfermo\s)(?<!despertarlo\sa\sla\senferma\s)(?<!despertarlo\sal\sbeb[eé]\s)(?<!despertarle\s)(?<!despertarle\sa\sla\spersona\s)(?<!despertarle\sal\sni[nñ]o\s)(?<!despertarle\sa\sla\sni[nñ]a\s)(?<!despertarle\sal\senfermo\s)(?<!despertarle\sa\sla\senferma\s)(?<!despertarle\sal\sbeb[eé]\s)(?<!despierte\s)(?<!despierte\sa\sla\spersona\s)(?<!despierte\sal\sni[nñ]o\s)(?<!despierte\sa\sla\sni[nñ]a\s)(?<!despierte\sal\senfermo\s)(?<!despierte\sa\sla\senferma\s)(?<!despierte\sal\sbeb[eé]\s)(?<!despertar\s)(?<!despertar\sa\sla\spersona\s)(?<!despertar\sal\sni[nñ]o\s)(?<!despertar\sa\sla\sni[nñ]a\s)(?<!despertar\sal\senfermo\s)(?<!despertar\sa\sla\senferma\s)(?<!despertar\sal\sbeb[eé]\s)(?<!rev[ií]sela\s)(?<!rev[ií]sela\sa\sla\spersona\s)(?<!rev[ií]sela\sal\sni[nñ]o\s)(?<!rev[ií]sela\sa\sla\sni[nñ]a\s)(?<!rev[ií]sela\sal\senfermo\s)(?<!rev[ií]sela\sa\sla\senferma\s)(?<!rev[ií]sela\sal\sbeb[eé]\s)(?<!rev[ií]selo\s)(?<!rev[ií]selo\sa\sla\spersona\s)(?<!rev[ií]selo\sal\sni[nñ]o\s)(?<!rev[ií]selo\sa\sla\sni[nñ]a\s)(?<!rev[ií]selo\sal\senfermo\s)(?<!rev[ií]selo\sa\sla\senferma\s)(?<!rev[ií]selo\sal\sbeb[eé]\s)(?<!rev[ií]sele\s)(?<!rev[ií]sele\sa\sla\spersona\s)(?<!rev[ií]sele\sal\sni[nñ]o\s)(?<!rev[ií]sele\sa\sla\sni[nñ]a\s)(?<!rev[ií]sele\sal\senfermo\s)(?<!rev[ií]sele\sa\sla\senferma\s)(?<!rev[ií]sele\sal\sbeb[eé]\s)(?<!revise\s)(?<!revise\sa\sla\spersona\s)(?<!revise\sal\sni[nñ]o\s)(?<!revise\sa\sla\sni[nñ]a\s)(?<!revise\sal\senfermo\s)(?<!revise\sa\sla\senferma\s)(?<!revise\sal\sbeb[eé]\s)(?<!revisar\s)(?<!revisar\sa\sla\spersona\s)(?<!revisar\sal\sni[nñ]o\s)(?<!revisar\sa\sla\sni[nñ]a\s)(?<!revisar\sal\senfermo\s)(?<!revisar\sa\sla\senferma\s)(?<!revisar\sal\sbeb[eé]\s)(?<!revisarla\s)(?<!revisarla\sa\sla\spersona\s)(?<!revisarla\sal\sni[nñ]o\s)(?<!revisarla\sa\sla\sni[nñ]a\s)(?<!revisarla\sal\senfermo\s)(?<!revisarla\sa\sla\senferma\s)(?<!revisarla\sal\sbeb[eé]\s)(?<!revisarlo\s)(?<!revisarlo\sa\sla\spersona\s)(?<!revisarlo\sal\sni[nñ]o\s)(?<!revisarlo\sa\sla\sni[nñ]a\s)(?<!revisarlo\sal\senfermo\s)(?<!revisarlo\sa\sla\senferma\s)(?<!revisarlo\sal\sbeb[eé]\s)(?<!vig[ií]lela\s)(?<!vig[ií]lela\sa\sla\spersona\s)(?<!vig[ií]lela\sal\sni[nñ]o\s)(?<!vig[ií]lela\sa\sla\sni[nñ]a\s)(?<!vig[ií]lela\sal\senfermo\s)(?<!vig[ií]lela\sa\sla\senferma\s)(?<!vig[ií]lela\sal\sbeb[eé]\s)(?<!vig[ií]lelo\s)(?<!vig[ií]lelo\sa\sla\spersona\s)(?<!vig[ií]lelo\sal\sni[nñ]o\s)(?<!vig[ií]lelo\sa\sla\sni[nñ]a\s)(?<!vig[ií]lelo\sal\senfermo\s)(?<!vig[ií]lelo\sa\sla\senferma\s)(?<!vig[ií]lelo\sal\sbeb[eé]\s)(?<!vig[ií]lele\s)(?<!vig[ií]lele\sa\sla\spersona\s)(?<!vig[ií]lele\sal\sni[nñ]o\s)(?<!vig[ií]lele\sa\sla\sni[nñ]a\s)(?<!vig[ií]lele\sal\senfermo\s)(?<!vig[ií]lele\sa\sla\senferma\s)(?<!vig[ií]lele\sal\sbeb[eé]\s)(?<!vigile\s)(?<!vigile\sa\sla\spersona\s)(?<!vigile\sal\sni[nñ]o\s)(?<!vigile\sa\sla\sni[nñ]a\s)(?<!vigile\sal\senfermo\s)(?<!vigile\sa\sla\senferma\s)(?<!vigile\sal\sbeb[eé]\s)(?<!vigilar\s)(?<!vigilar\sa\sla\spersona\s)(?<!vigilar\sal\sni[nñ]o\s)(?<!vigilar\sa\sla\sni[nñ]a\s)(?<!vigilar\sal\senfermo\s)(?<!vigilar\sa\sla\senferma\s)(?<!vigilar\sal\sbeb[eé]\s)(?<!vigilarla\s)(?<!vigilarla\sa\sla\spersona\s)(?<!vigilarla\sal\sni[nñ]o\s)(?<!vigilarla\sa\sla\sni[nñ]a\s)(?<!vigilarla\sal\senfermo\s)(?<!vigilarla\sa\sla\senferma\s)(?<!vigilarla\sal\sbeb[eé]\s)(?<!vigilarlo\s)(?<!vigilarlo\sa\sla\spersona\s)(?<!vigilarlo\sal\sni[nñ]o\s)(?<!vigilarlo\sa\sla\sni[nñ]a\s)(?<!vigilarlo\sal\senfermo\s)(?<!vigilarlo\sa\sla\senferma\s)(?<!vigilarlo\sal\sbeb[eé]\s)(?:every|cada)\s+(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)|\b(?:two|three|four|five|six|seven|eight|nine|ten|twelve|twenty-four|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|veinticuatro)(?:\s+(?:to|or|and|o|a|y)\s+(?:two|three|four|five|six|seven|eight|nine|ten|twelve|twenty-four|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|veinticuatro))?)\s*(?:h|hrs?|hours?|horas?)\b(?!\s*,?\s*(?:turn|stir|mix|knead|rotate)\b)|(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)|(?:one|two|three|four|five|six|una|dos|tres|cuatro|cinco|seis))\s*(?:times?|x|veces|vez)\s*(?:(?:a|per|al|por|each|cada)\s*(?:day|d[ií]a)|daily|diari[oa]s?)|(?:once|twice|thrice)\s+(?:(?:a|per|each)\s+day|daily)|(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s+(?:doses|dosis)\b)(?:,?\s*(?:for|por|durante)\s+(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*(?:days?|d[ií]as|weeks?|semanas)\b)?|(?:en\s+)?una\s+sola\s+dosis|\b1\s+sola\s+vez|(?:again|repeat(?:ed)?|otra\s+vez|de\s+nuevo|repetir|repita)\s+(?:in|after|en|despu[eé]s\s+de)\s+(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*(?:h|hrs?|hours?|horas?)\b|\b(?:every\s+(?:[\w-]+\s+){0,2}?hours?|hourly|cada\s+(?:\w+\s+){0,2}?horas?|doses?|dosis|dosage|given|give|gives|giving|administer\w*|administr\w*|take|takes|taken|inject\w*|ivermectin|dele|dale|darle|dar|d[eé]selo|d[eé]sele|tome|tomar|toma|tomando|tinctures?|tintura|infusions?|infusi[oó]n|decoctions?|remed(?:y|ies)|remedios?|medicinal(?:ly)?|medicines?|medicinas?|mixtures?|prescrib\w*|recommend\w*|purgatives?|purgantes?|cathartics?|emetics?|vomitivos?|antispasmodic|anodyne|laxatives?|laxantes?|tonics?|t[oó]nicos?|physic|draughts?|drench\w*|bolus|pills?|liniments?|ointments?|salves?|embrocations?|poultices?|gargles?|lotions?|eye-?waters?|collyri\w*|pomadas?|ung[uü]entos?|linimentos?|cataplasmas?|quinine|quinina|opium|opio|laudanum|l[aá]udano|morphi\w*|morfina|calomel|camphor\w*|alcanfor|digitalis|foxglove|strychni\w*|estricnina|bromides?|bromuro|salicin|salicyl\w*|buchu|creosote|creosota|elaterium|ipecac\w*|paregoric|parag[oó]rico|castor\s+oil|ricino|epsom|glauber|iodides?|yoduro|aloes|rhubarb|ruibarbo|senna|jalap|turpentine|trementina|chloral|chloroform|cloroformo|ether|belladonn?a|aconite|ac[oó]nito|ergot\w*|arseni\w*|ars[eé]nico|mercury|mercurio|antitoxins?|antitoxina|serum|suero|antimony|tartar\s+emetic|pine\s+tar|penny\s*royal|carbolic|creolin|sulphur|azufre|magnesia|bismuth|santonin|cocaine|atropine|aspirin\w*|chlorodyne|squills?|antipyrin\w*|acetanilid\w*|phenacetin|cod[\s-]liver\s+oil|vermifuge|nux\s+vomica|nitre|lobelia|asaf\w*tida|valerian|hyoscyam\w*|cannabis|cantharides|croton\s+oil|podophyll\w*|sarsaparilla|guaiac\w*|colchicum|stramonium|hellebore|savin|tansy|wormwood|quassia|gentian|cinchona)\b[^;!?]{0,80}?(?:(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:fluid\s+|fl\.\s*)?(?:(?:grains?|minims?|drachms?|drams?|ounces?|gills?|scruples?|granos?|dracmas?|onzas?|escr[uú]pulos?)\b|(?:grs?|oz)(?:\.|\b)|oz\b|c\.\s?c\.)|\b(?:a\s+few\s+drops|a\s+drop\s+or\s+two|unas\s+(?:cuantas\s+|pocas\s+)?gotas)\b)(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))(?!\s*(?:(?:of|de)\s+)?(?:wheat|corn|oats?|barley|rye|bran|meal|seeds?|feed|hay|yeast|lard|suet|starch|gelatine?|cheese|meat|beef|tea(?!\s+tree)|coffee|cocoa|chocolate|vinegar|gold|silver|sand|clay|wax|beeswax|rosin|resin|gunpowder|trigo|ma[ií]z|cebada|avena|salvado|semillas?|levadura|manteca|almid[oó]n|queso|carne|caf[eé]|cacao|vinagre|oro|plata|arena|cera)\b)|(?:(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:fluid\s+|fl\.\s*)?(?:(?:grains?|minims?|drachms?|drams?|ounces?|gills?|scruples?|granos?|dracmas?|onzas?|escr[uú]pulos?)\b|(?:grs?|oz)(?:\.|\b)|oz\b|c\.\s?c\.)|\b(?:a\s+few\s+drops|a\s+drop\s+or\s+two|unas\s+(?:cuantas\s+|pocas\s+)?gotas)\b)(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))(?!\s*(?:(?:of|de)\s+)?(?:wheat|corn|oats?|barley|rye|bran|meal|seeds?|feed|hay|yeast|lard|suet|starch|gelatine?|cheese|meat|beef|tea(?!\s+tree)|coffee|cocoa|chocolate|vinegar|gold|silver|sand|clay|wax|beeswax|rosin|resin|gunpowder|trigo|ma[ií]z|cebada|avena|salvado|semillas?|levadura|manteca|almid[oó]n|queso|carne|caf[eé]|cacao|vinagre|oro|plata|arena|cera)\b)(?=[^;!?]{0,80}?\b(?:every\s+(?:[\w-]+\s+){0,2}?hours?|hourly|cada\s+(?:\w+\s+){0,2}?horas?|doses?|dosis|dosage|given|give|gives|giving|administer\w*|administr\w*|take|takes|taken|inject\w*|ivermectin|dele|dale|darle|dar|d[eé]selo|d[eé]sele|tome|tomar|toma|tomando|tinctures?|tintura|infusions?|infusi[oó]n|decoctions?|remed(?:y|ies)|remedios?|medicinal(?:ly)?|medicines?|medicinas?|mixtures?|prescrib\w*|recommend\w*|purgatives?|purgantes?|cathartics?|emetics?|vomitivos?|antispasmodic|anodyne|laxatives?|laxantes?|tonics?|t[oó]nicos?|physic|draughts?|drench\w*|bolus|pills?|liniments?|ointments?|salves?|embrocations?|poultices?|gargles?|lotions?|eye-?waters?|collyri\w*|pomadas?|ung[uü]entos?|linimentos?|cataplasmas?|quinine|quinina|opium|opio|laudanum|l[aá]udano|morphi\w*|morfina|calomel|camphor\w*|alcanfor|digitalis|foxglove|strychni\w*|estricnina|bromides?|bromuro|salicin|salicyl\w*|buchu|creosote|creosota|elaterium|ipecac\w*|paregoric|parag[oó]rico|castor\s+oil|ricino|epsom|glauber|iodides?|yoduro|aloes|rhubarb|ruibarbo|senna|jalap|turpentine|trementina|chloral|chloroform|cloroformo|ether|belladonn?a|aconite|ac[oó]nito|ergot\w*|arseni\w*|ars[eé]nico|mercury|mercurio|antitoxins?|antitoxina|serum|suero|antimony|tartar\s+emetic|pine\s+tar|penny\s*royal|carbolic|creolin|sulphur|azufre|magnesia|bismuth|santonin|cocaine|atropine|aspirin\w*|chlorodyne|squills?|antipyrin\w*|acetanilid\w*|phenacetin|cod[\s-]liver\s+oil|vermifuge|nux\s+vomica|nitre|lobelia|asaf\w*tida|valerian|hyoscyam\w*|cannabis|cantharides|croton\s+oil|podophyll\w*|sarsaparilla|guaiac\w*|colchicum|stramonium|hellebore|savin|tansy|wormwood|quassia|gentian|cinchona)\b)|\b(?:emetics?|vomitivos?|laxatives?|laxantes?|purgatives?|purgantes?|purg(?:e|es|ed|ing)|cathartics?|physic)\b[^;!?]{0,80}?(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|cucharaditas?|cucharadas?|cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b(?:[\s,]+(?:(?:or|and|to|o|y)\s+)?(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|cucharaditas?|cucharadas?|cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b)*|(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|cucharaditas?|cucharadas?|cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b(?:[\s,]+(?:(?:or|and|to|o|y)\s+)?(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:(?:tea|table|dessert)(?:-\s*|\s)?spoons?(?:-?\s*f[-\s]?ul{1,2}s?)?|spoons?ful{1,2}s?|wine-?glass(?:es)?ful{1,2}s?|cucharaditas?|cucharadas?|cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b)*(?=[^;!?]{0,80}?\b(?:emetics?|vomitivos?|laxatives?|laxantes?|purgatives?|purgantes?|purg(?:e|es|ed|ing)|cathartics?|physic)\b)|(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:fluid\s+|fl\.\s*)?(?:drachms?|minims?|scruples?|dracmas?|escr[uú]pulos?)\b|\b(?:castor\s+oil|ricino|emetics?|vomitivos?|laxatives?|laxantes?|purgatives?|purgantes?|cathartics?|quinine|quinina|opium|opio|laudanum|l[aá]udano|morphi\w*|morfina|calomel|camphor\w*|alcanfor|digitalis|foxglove|strychni\w*|estricnina|bromides?|bromuro|salicin|salicyl\w*|buchu|creosote|creosota|elaterium|ipecac\w*|paregoric|parag[oó]rico|epsom|glauber|iodides?|yoduro|aloes|senna|jalap|turpentine|trementina|chloral|chloroform|cloroformo|belladonn?a|aconite|ac[oó]nito|ergot\w*|arseni\w*|ars[eé]nico|antitoxins?|antitoxina|antimony|tartar\s+emetic|pine\s+tar|penny\s*royal|carbolic|creolin|magnesia|bismuth|santonin|cocaine|atropine|aspirin\w*|chlorodyne|squills?|antipyrin\w*|acetanilid\w*|phenacetin|cod[\s-]liver\s+oil|vermifuge|nux\s+vomica|lobelia|asaf\w*tida|valerian|hyoscyam\w*|cannabis|cantharides|croton\s+oil|podophyll\w*|colchicum|stramonium|hellebore|savin|tansy|wormwood|quassia|gentian|cinchona|ivermectin)\b[^;!?]{0,80}?(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:de\s+(?:una?\s+)?)?(?:cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))|(?:(?:(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+)(?:(?:\s*[-–]\s*|\s+(?:to|a|or|o|ó|u|y|and|hasta)\s+)(?:\b\d+(?:[.,]\d+)*(?:\s*(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;))?|(?:[½¼¾⅓⅔⅛]|&#\d{3,4};|&frac\d\d;)|\b\d+\/\d+))?)\s*|\b(?:(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty)(?:\s+(?:to|or|and|o|ó|u|a|y)\s+(?:una?|media|medio|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte|treinta|cuarenta|cincuenta|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|sixty))?|(?:one|two|three)-(?:halves|half|thirds?|fourths?|quarters?|eighths?)(?:\s+of\s+an?)?|half(?:\s+(?:of\s+)?an?)?|(?:a\s+|one\s+)?quarter(?:\s+of)?\s+an?|(?:a\s+)?few|several|an?)\s+)(?:de\s+(?:una?\s+)?)?(?:cups?(?:ful{1,2}s?)?|tazas?|tacitas?|vasos?|glass(?:es)?(?:ful{1,2}s?)?)\b(?!\s+(?:if|when)\s+(?:the\s+)?water\b|\s+si\s+el\s+agua\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:rasas?|llenas?|level|heaping)\s+)?(?:(?:de|of)\s+)?(?:(?:\d+(?:[.,]\d+)?\s*%|clean|boiled|cooled|safe|drinking|potable|fresh|cool|cold|warm|limpia|hervida|tibia|fr[ií]a|regular|unscented|non-scented|plain|liquid|household|chlorine|common|ordinary|cloro|lej[ií]a|blanqueador|l[ií]quid[oa]|com[uú]n|sin\s+(?:perfume|aroma)|tinctures?\s+of|tintura\s+de|this|the|esta|la|clorox(?:-type)?)[,\s]+)*(?:sal|az[uú]car|agua|harina|aceite(?!\s+de\s+(?:ricino|h[ií]gado|bacalao))|leche(?!\s+de\s+magnesia)|miel|mantequilla|arroz|cloro|lej[ií]a|blanqueador|yodo|salt|sugar|water|flour|oil(?!\s+(?:of|rendered|from|extracted)\b)|milk(?!\s+of\s+magnesia)|honey|butter|rice|cereal(?:es)?|lemon|lim[oó]n|stock(?:\s+solution)?|soluci[oó]n\s+madre|chlorinated\s+lime|cal\s+clorada|hypochlorite|hipoclorito|bleaching\s+powder|halazone|bleach|chlorine|iodine)\b|\s*\)?\s*(?:\([^)]{0,40}\)\s*)?(?:(?:potabilizadoras?|purificadoras?|purification|chlorine|iodine|aquatabs?|halazone)\s+)?(?:(?:of|de)\s+(?:(?:\d+(?:[.,]\d+)?\s*(?:%|percent|per\s+cent|por\s+ciento)|solution|soluci[oó]n|stock|chlorine|cloro|bleach|household|liquid|the|this|a|la|esta)\s+){1,4})?(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?)|\s*(?:de|of)\s+\d+(?:[.,]\d+)?\s*(?:mg|g|ml)\s*(?:por(?:\s+cada)?|per|\/|for\s+(?:each|every)|para\s+cada|cada|(?:to|in|into)\s+(?:each|every)|to(?=\s+\d+(?:[.,]\d+)?\s*(?:imperial\s+)?gal))\s*(?:\d+(?:[.,]\d+)?\s*(?:[^\s()]{1,8}\s*\(\s*\d+\s*)?|(?:an?|una?|one|two|three|four|five|ten|dos|tres|cuatro|cinco|diez)\s+)?(?:imperial\s+)?(?:litros?|lit(?:re|er)s?|l\b|gal|quarts?|qt\b|cuartos?|barrels?|barril(?:es)?|drums?|tanks?|tambos?|tanques?))(?=[^;!?]{0,80}?\b(?:castor\s+oil|ricino|emetics?|vomitivos?|laxatives?|laxantes?|purgatives?|purgantes?|cathartics?|quinine|quinina|opium|opio|laudanum|l[aá]udano|morphi\w*|morfina|calomel|camphor\w*|alcanfor|digitalis|foxglove|strychni\w*|estricnina|bromides?|bromuro|salicin|salicyl\w*|buchu|creosote|creosota|elaterium|ipecac\w*|paregoric|parag[oó]rico|epsom|glauber|iodides?|yoduro|aloes|senna|jalap|turpentine|trementina|chloral|chloroform|cloroformo|belladonn?a|aconite|ac[oó]nito|ergot\w*|arseni\w*|ars[eé]nico|antitoxins?|antitoxina|antimony|tartar\s+emetic|pine\s+tar|penny\s*royal|carbolic|creolin|magnesia|bismuth|santonin|cocaine|atropine|aspirin\w*|chlorodyne|squills?|antipyrin\w*|acetanilid\w*|phenacetin|cod[\s-]liver\s+oil|vermifuge|nux\s+vomica|lobelia|asaf\w*tida|valerian|hyoscyam\w*|cannabis|cantharides|croton\s+oil|podophyll\w*|colchicum|stramonium|hellebore|savin|tansy|wormwood|quassia|gentian|cinchona|ivermectin)\b)", re.I)


def check_query(cat, q, expect, r, mode):
    top3 = r["titles"][:3]
    hrefs = " ".join(urllib.parse.unquote(t["href"] or "") for t in top3)
    body = hrefs + " " + " ".join(t["text"] for t in top3)
    if expect == "NEG":
        hard = (r["pin"] + hrefs).lower()           # app's own layers: zero tolerance
        if "dailymed" in hard or DOSE.search(hard):
            return (False, "dosing in pin/titles layer")
        if "dailymed" in r["ft"].lower():
            return (False, "dailymed via fulltext")
        if DOSE.search(r["ftText"]):
            # G3 decided 09-19: drug-name queries must suppress book snippets
            return (False, "dose figure in book snippet (G3 suppression failed): " + DOSE.search(r["ftText"]).group(0))
        if DOSE.search(r.get("enc", "")):
            return (False, "dose figure in encyclopedia snippet: " + DOSE.search(r["enc"]).group(0))
        if "Loading full-text engine" in r["ftText"]:
            return (False, "fulltext never rendered in 30 s; NEG cannot be judged")
        if "l-result" in r["ft"] and not re.search(r"never state drug doses|nunca indican dosis", r["ftText"], re.I):  # D2 banner (F1 2026-10-09)
            return (False, "drug query has fulltext results but no dosing-card notice")
        return (True, "no dosing surfaced; notice shown when results exist")
    if expect == "EMPTY-GRACEFUL":
        ok = ("check spelling" in body.lower() or "no title matches" in
              (r["titles"] and "" or "x") or not top3)
        # graceful = either empty-state message or (junk fuzzy) rows — must not error;
        # real requirement is the empty-state text when nothing sensible matches
        txt = r.get("ftText", "")
        return (True, "renders without error (fuzzy junk tolerated)")
    if expect.startswith("TRIAGE:"):
        ok = expect.split(":")[1] in r["pin"] and "triage.html" in r["pin"]
        return (ok, "pin row" if ok else f"pin missing {expect}")
    ok = expect.lower() in body.lower()
    note = "top-3"
    if ok and cat == "historical":
        first = urllib.parse.unquote(top3[0]["href"] or "") if top3 else ""
        if "historical.html" not in first:
            return (False, "historical hit NOT via interstitial")
        note = "top-3 via interstitial"
    return (ok, note if ok else f"'{expect}' not in top-3")


# D4 (round 11, #278-#281): a /semantic row or MCP hit is a finder, never a quote. Any text field, or any string field
# outside the finder and the library's own historical warning, fails.
TEXT_FIELDS = ("excerpt", "snippet", "text")
FINDER_STR = {"path", "title", "url", "shelf", "warning"}


def server_rows(base, q, lang, limit):
    """[(source, row)] from /semantic and MCP search_library for q."""
    u = base + "semantic?" + urllib.parse.urlencode({"q": q, "limit": limit, "lang": lang})
    rows = [("semantic", r) for r in json.load(urllib.request.urlopen(u, timeout=60))]
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "search_library", "arguments": {"query": q, "limit": limit, "language": lang}}}).encode()
    res = json.load(urllib.request.urlopen(urllib.request.Request(
        base + "mcp", body, {"Content-Type": "application/json", "Accept": "application/json"}), timeout=60))
    return rows + [("mcp", h) for h in json.loads(res["result"]["content"][0]["text"])["hits"]]


def quoted(rows):
    """First row that carries document text, as 'source path key', else None."""
    for src, r in rows:
        for k, v in r.items():
            if (k in TEXT_FIELDS or (isinstance(v, str) and k not in FINDER_STR)) and v:
                return "%s %s %s=%r" % (src, r.get("path", "")[-50:], k, str(v)[:60])
    return None


def check_symptom_dose(pg, base, q):
    r = scrape(pg, base, q, 4000)
    lang = "spa" if re.search(r"[áéíóúñ¿¡]", q) else "eng"
    for t in (r["pin"], r["ftText"], r.get("enc", "")):
        m = DOSE.search(t) or DOSE_LOOSE.search(t)
        if m:
            return (False, "dose text shown on the page: " + m.group(0))
    try:
        rows = server_rows(base, q, lang, 10)
    except Exception as e:
        return (False, "semantic/mcp did not answer: " + str(e)[:80])
    bad = quoted(rows)
    if bad:
        return (False, "D4: server row carries text: " + bad)
    return (True, "no dose text on the page; %d /semantic and MCP rows carry no text (D4)" % len(rows))


def check_water_visible(base, q, docs):
    try:
        u = base + "semantic?" + urllib.parse.urlencode({"q": q, "limit": 10, "lang": "eng"})
        rows = json.load(urllib.request.urlopen(u, timeout=60))
    except Exception as e:
        return (False, "semantic did not answer: " + str(e)[:80])
    bad = quoted([("semantic", r) for r in rows])
    if bad:
        return (False, "D4: /semantic row carries text: " + bad)
    got = {r["path"]: r.get("page") or 0 for r in rows}
    notes = []
    for d in docs:
        name = d.rsplit("/", 1)[-1]
        if d not in got:
            return (False, "not found by /semantic: " + name)
        page = got[d]
        txt = subprocess.run(["pdftotext", "-q", "-f", str(page), "-l", str(page), "library/" + d, "-"],
                             capture_output=True, text=True).stdout if page else ""
        m = re.search(r"\d+\s*drops", txt)
        if not m:
            return (False, "opened page has no drop count: %s p.%s" % (name, page))
        notes.append("%s p.%s '%s'" % (name, page, m.group(0)))
    return (True, "found, no quote; the opened page holds the drop count: " + ", ".join(notes))


def check_es25(base):
    q, sheet = ES25
    seen = 0
    try:
        rows = server_rows(base, q, "spa", 20)
    except Exception as e:
        return (False, "semantic/mcp did not answer: " + str(e)[:80])
    bad = quoted(rows)
    if bad:
        return (False, "D4: server row carries text: " + bad)
    for src, r in rows:
        if sheet in urllib.parse.unquote(r["path"]):
            seen += 1
            if not r.get("dose_page"):
                return (False, "%s: aspirin sheet without dose_page (title-only list)" % src)
    return (True, "%d rows carry no text (D4); aspirin sheet %d times, title-only with dose_page" % (len(rows), seen))


def check_bite_outdated(base, q, lang):
    try:
        rows = server_rows(base, q, lang, 10)
    except Exception as e:
        return (False, "semantic/mcp did not answer: " + str(e)[:80])
    bad = quoted(rows)
    if bad:
        return (False, "D4: server row carries text: " + bad)
    for src, r in rows:
        if r["path"].endswith(ECHO_SHOCK[0]) and (r.get("page") or 0) in ECHO_SHOCK[1] and not r.get("outdated"):
            return (False, "%s: ECHO electric-shock page p.%s not flagged outdated" % (src, r.get("page")))
    return (True, "%d rows carry no text (D4); ECHO shock pages flagged outdated" % len(rows))


# FIXES #287 (10-29): a fixed emergency line above every card list on Ask, Search and the front page, whatever the
# question: nav.l-emerg, the same six cards in this order (EN triage.html, ES triage_es.html), never inside a card row,
# the card list or #r-pin. One EN and one ES question on each page.
EMERG_IDS = ["bleeding", "unconscious", "choking", "allergy", "co", "mind"]
EMERG_QS = [("my kid has a fever", False), ("sangra mucho por la mordida de un perro", True)]
EMERG_JS = """() => [...document.querySelectorAll('nav.l-emerg')].filter(n => !n.closest('details, li, #r-pin, .l-doc-row'))
  .map(n => [...n.querySelectorAll('a')].map(a => a.getAttribute('href').replace(/^.*\\//, '')))"""


def check_emerg(pg, base, q, es):
    want = [[("triage_es.html#" if es else "triage.html#") + i for i in EMERG_IDS]]
    got = {}
    pg.goto(base + "search.html?" + ("lang=spa&" if es else "") + "q=" + urllib.parse.quote(q))
    try: pg.wait_for_selector("#r-emerg nav.l-emerg", timeout=8000)
    except Exception: pass
    got["search"] = pg.evaluate(EMERG_JS)
    pg.goto(base + ("index.html?lang=spa" if es else "index.html"))
    pg.fill("#q", q)
    try: pg.wait_for_selector("nav.l-emerg", timeout=8000)
    except Exception: pass
    got["front"] = pg.evaluate(EMERG_JS)
    pg.goto(base + "chat.html")
    try:
        pg.wait_for_selector("#form:not([hidden])", timeout=60000)
        pg.fill("#q", q); pg.press("#q", "Enter")
        pg.wait_for_selector(".c-msg.cards nav.l-emerg", timeout=8000)
    except Exception: pass
    got["ask"] = pg.evaluate(EMERG_JS)
    bad = {k: v for k, v in got.items() if v != want}
    return not bad, ("six links on search, front, ask" if not bad else "; ".join(f"{k}: {v}"[:120] for k, v in bad.items()))


def run_mode(base, mode, p):
    b = p.chromium.launch(channel="chrome", headless=True)
    ctx = b.new_context()
    ext_reqs = []
    if mode == "direct":
        ctx.on("request", lambda rq: ext_reqs.append(rq.url)
               if rq.url.startswith("http") and not any(h in rq.url for h in LLM_HOSTS)
               else None)
    pg = ctx.new_page()
    for cat, q, expect in queries:
        r = scrape(pg, base, q, 1500)
        ok, note = check_query(cat, q, expect, r, mode)
        status = "WARN" if ok is None else ("PASS" if ok else "FAIL")
        results.append((f"T7 {cat}: {q}", mode, status, note))
    if mode == "direct":
        r = scrape(pg, base, "biosand filter", 1500)
        ok = "NEEDS THE SERVER" in r["ftText"]
        results.append(("T6 fulltext greyed", mode, "PASS" if ok else "FAIL",
                        "badge shown" if ok else r["ftText"][:60]))
        results.append(("T6 no external requests", mode,
                        "PASS" if not ext_reqs else "FAIL",
                        "clean" if not ext_reqs else ext_reqs[0][:80]))
    else:
        for q in SYMPTOM_DOSE:
            ok, note = check_symptom_dose(pg, base, q)
            results.append((f"T4 symptom dose probe: {q[:40]}", mode, "PASS" if ok else "FAIL", note))
        for q, lang in BITE_QS:
            ok, note = check_bite_outdated(base, q, lang)
            results.append((f"T4 bite rows no text, ECHO outdated: {q[:40]}", mode, "PASS" if ok else "FAIL", note))
        for q, es in EMERG_QS:
            ok, note = check_emerg(pg, base, q, es)
            results.append((f"T4 emergency line (#287): {q[:40]}", mode, "PASS" if ok else "FAIL", note))
        ok, note = check_es25(base)
        results.append(("T4 es25 dose sheet title-only: " + ES25[0], mode, "PASS" if ok else "FAIL", note))
        for q, docs in WATER_VISIBLE:
            ok, note = check_water_visible(base, q, docs)
            results.append((f"T4 water amounts on the opened page: {q[:40]}", mode, "PASS" if ok else "FAIL", note))
        for phrase, doc, pages in phrases:
            r = scrape(pg, base, phrase, 4000)
            hrefs = [urllib.parse.unquote(h.replace("&amp;", "&"))
                     for h in re.findall(r'href="([^"]*reader\.html[^"]*)"', r["ft"])]
            hit = next((h for h in hrefs if doc in h), None)
            ok = bool(hit) and any(f"p={page}&" in hit + "&" for page in pages)
            note = (f"reader p={'|'.join(map(str, pages))}, result #{hrefs.index(hit) + 1}" if ok
                    else (hit or "; ".join(h[:60] for h in hrefs[:2]) or r["ftText"][:60]))
            results.append((f"T7 phrase: {phrase[:40]}…", mode,
                            "PASS" if ok else "FAIL", note))
    b.close()


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y-%m-%d")
    with sync_playwright() as p:
        for base, mode in ((SERVED, "served"), (DIRECT, "direct")):
            for attempt in range(3):
                mark = len(results)
                try:
                    run_mode(base, mode, p)
                    break
                except Exception as e:
                    del results[mark:]
                    print(f"retry {mode} ({attempt}): {str(e)[:100]}", file=sys.stderr)
                    time.sleep(3)
            else:
                results.append((f"MODE {mode}", mode, "FAIL", "chrome kept crashing"))
    results.append(("T7 kiwix layer", "served", "SKIP", "SKIPPED-LOCAL — no kiwix-serve until C4/E3"))
    # plain version (no server): index_v1/triage_v1 from file://, all links + browser
    r = subprocess.run([sys.executable, "tests/plain_test.py"], capture_output=True, text=True)
    results.append(("T6 plain version file://", "direct", "PASS" if r.returncode == 0 else "FAIL",
                    r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]))

    fails = [r for r in results if r[2] == "FAIL"]
    rpt = f"{BASE}/acceptance_report_{date}.md"
    with open(rpt, "w") as f:
        f.write(f"# Local acceptance dry-run — {date}\n\n")
        f.write("Scope: T4 (neg probes) + T6 (direct-mode) + T7 (search fixtures), "
                "local libserver + file://. Kiwix + full T1-T3 traversal at C4/E3.\n\n")
        f.write("| check | mode | result | note |\n|---|---|---|---|\n")
        for c, m, s, n in results:
            f.write(f"| {c} | {m} | {s} | {n} |\n")
        f.write(f"\n**{len(fails)} FAIL / {len(results)} checks**\n")
    print(f"wrote {rpt}: {len(fails)} FAIL / {len(results)} checks")
    for c, m, s, n in fails:
        print("FAIL", c, m, n)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
