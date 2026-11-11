#!/usr/bin/env python3
"""Lantern build A4: generate _app/shelf/<slug>.html for every shelves.json
entry, render RUNBOOK/SKILLS_CHECKLIST to _app/runbook.html/_app/skills.html,
and patch a STATIC shelf grid into index.html (JS-off landing, acceptance 2).
Rerunnable. Data source: sealed MANIFEST via gen_index's loader + disk sizes.
Covers: <img> emitted only when _app/covers/<sha8>.jpg exists (A6 fills;
rerun this script after covers land)."""
import html
import json
import glob, os, re, sys, hashlib, time
from urllib.parse import quote

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = f"{BASE}/library"
OUT = f"{LIB}/_app/shelf"
sys.path.insert(0, os.path.dirname(__file__))
from gen_index import (SHELVES, HIST_PATHS, HEALTH_SHELVES, MEDICAL_MAX_AGE, LANG_NAME, humanize, load_paths, shelf_of,
                       doc_meta, doc_year, doc_lang, resolve_titles, kiwix_books, is_hist)

from refs import resolve   # ref:KEY links and summaries (refs.json)
from gen_places import DISPLAY as MWM_DISPLAY   # r9 a3 W2: Organic Maps region names, as map.html shows them

def sumhtml(s, root, links=True):
    """summaries.json is plain text plus optional [text](ref:KEY) links.
    links=False where the summary sits inside an <a> (index shelf cards): nested anchors split the card."""
    if not links:
        return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", esc(s))
    return resolve(re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', esc(s)), root)

def esc(s):
    return html.escape(str(s), quote=True)

def human_size(n):
    """Decimal units, as map.html (places.js, bytes / 1e6) and index_v1 give them (a3 W4: the shelf said 95.8 "MB" for
    100,477,089 bytes, which is MiB). One decimal under 10, whole numbers above, so 100,477,089 is "100 MB" on both."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 999.5 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" or n >= 9.95 else f"{n:.1f} {unit}"
        n /= 1000

def sha8(p):
    return hashlib.sha256(p.encode()).hexdigest()[:8]

# ── single source for page chrome (nav + tabbar), stamped everywhere ──
NAV_ITEMS = [("index.html", "Shelves", ""), ("search.html", "Search", ""),
             ("audio.html", "Listening", ""), ("chat.html", "Ask", "needs-chat"),
             ("map.html", "Map", "needs-maps hide-direct"),
             ("kids.html", "Kids", "")]

def nav_html(root="", current=""):
    out = ['<nav class="l-nav" aria-label="Primary">']
    for href, label, cls in NAV_ITEMS:
        attrs = f' class="{cls}"' if cls else ""
        if href == current:
            attrs += ' aria-current="page"'
        out.append(f'    <a href="{root}{href}"{attrs}>{label}</a>')
    out.append("  </nav>")
    return "\n".join(out)

FOOT_ITEMS = [("_app/runbook.html", "Operator runbook", ""), ("_app/skills.html", "Skills checklist", ""), ("_app/purchases.html", "Purchases &amp; print plan", ""),
              ("_app/about.html", "About Lantern", ""), ("_app/known_gaps.html", "Known gaps", ""), ("LICENSES.html", "Licenses", ""), ("index_v1.html", "Plain version", "")]
# library/PURCHASE_LIST.md is each box's own record (what this household bought and printed): no file, no link
if not os.path.exists(f"{LIB}/PURCHASE_LIST.md"):
    FOOT_ITEMS = [i for i in FOOT_ITEMS if i[0] != "_app/purchases.html"]
TAB_ITEMS = [("index.html", "home", "Home"), ("search.html", "search", "Search"),
             ("triage.html", "triage", "Hurt or sick"), ("audio.html", "listening", "Listening")]
MORE_ITEMS = [("chat.html", "chat", "Ask", "needs-chat"), ("map.html", "map", "Map", "needs-maps hide-direct"),
              ("kids.html", "kids", "Kids", ""), ("video.html", "video", "Video", ""),
              ("plants.html", "plants", "Plants", ""),
              ("tools/suncalc.html", "sun", "Sun &amp; moon", ""), ("tools/convert.html", "convert", "Converters", "")]
# inline SVG from the Claude Design handback (the private design notes)
TAB_ICON = {'home': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 11.5 12 4l9 7.5"></path><path d="M5.5 9.5V20h13V9.5"></path><path d="M10 20v-5.5h4V20"></path></svg>', 'search': '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.75" cy="10.75" r="6.75"></circle><path d="M15.75 15.75 20.5 20.5"></path></svg>', 'triage': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 6v12M6 12h12"></path></svg>', 'listening': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 15v-3a8 8 0 0 1 16 0v3"></path><path d="M4 14.5h2.5A1.5 1.5 0 0 1 8 16v3a1.5 1.5 0 0 1-1.5 1.5h-1A1.5 1.5 0 0 1 4 19z"></path><path d="M20 14.5h-2.5A1.5 1.5 0 0 0 16 16v3a1.5 1.5 0 0 0 1.5 1.5h1A1.5 1.5 0 0 0 20 19z"></path></svg>', 'more': '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="3.5" width="7" height="7" rx="2"></rect><rect x="13.5" y="3.5" width="7" height="7" rx="2"></rect><rect x="3.5" y="13.5" width="7" height="7" rx="2"></rect><rect x="13.5" y="13.5" width="7" height="7" rx="2"></rect></svg>'}
LINK_ICON = {'chat': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v8a2.5 2.5 0 0 1-2.5 2.5H10l-4.5 3.5V17H6.5A2.5 2.5 0 0 1 4 14.5z"></path></svg>', 'map': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6.5 9 4l6 2.5 6-2.5v13.5L15 20l-6-2.5L3 20z"></path><path d="M9 4v13.5M15 6.5V20"></path></svg>', 'kids': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3.5 2.6 5.4 5.9.8-4.3 4.1 1.1 5.9L12 16.9l-5.3 2.8 1.1-5.9-4.3-4.1 5.9-.8z"></path></svg>', 'video': '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2.5"></rect><path d="m10 9 5 3-5 3z"></path></svg>', 'plants': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19c0-8 5-13 14-14 0 9-5 14-13 14"></path><path d="M5 19c3-4 6-7 9-9"></path></svg>', 'runbook': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4.5A1.5 1.5 0 0 1 6.5 3H19v15H6.5A1.5 1.5 0 0 0 5 19.5z"></path><path d="M5 19.5A1.5 1.5 0 0 0 6.5 21H19v-3"></path></svg>'}
LINK_ICON['sun'] = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"></circle><path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"></path></svg>'
LINK_ICON['convert'] = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h13l-3-3M20 16H7l3 3"></path></svg>'

STATUS_PILL = '<button class="l-pill" data-role="status" onclick="lanternToggleTheme()"><span class="dot"></span>checking…</button>'

def operator_html(root=""):
    """Operator links, one block for the More sheet and the sidebar foot."""
    return ('<p class="l-caption">Operator</p><div class="l-shelflist">' + "".join(
        f'<a href="{root}{h}"{" class=%s" % chr(34) + c + chr(34) if c else ""}>{l}</a>' for h, l, c in FOOT_ITEMS) + '</div>')

# 5A (redteam 2026-10-05 W3): md-rendered pages double as plain pages; their Search/Ask
# entries say so. t8_plain.py accepts title/data-server or the word "server" nearby.
SERVER_MARK = ' title="Needs the server" data-server="1"'

# FIXES #206 (E6): Spanish pages (triage_es*.html via build_triage, es.html) get Spanish tab labels and Spanish targets;
# English pages never change. tabbar_html(..., lang="es")
TAB_ES = {"home": ("es.html", "Inicio"), "search": ("search.html?lang=spa", "Buscar"), "triage": ("triage_es.html", "Herido o enfermo"),
          "listening": ("audio.html", "Escuchar"), "chat": ("chat.html?lang=es", "Preguntar"), "map": ("map.html?lang=es", "Mapa"), "kids": ("kids.html", "Niños"),
          "video": ("video.html", "Videos"), "plants": ("plants.html?lang=es", "Plantas"), "sun": ("tools/suncalc.html", "Sol y luna"),
          "convert": ("tools/convert.html", "Conversiones")}

def tabbar_html(root="", current="", server=False, lang="en"):
    if lang == "es":
        es = lambda key, href, label: TAB_ES.get(key, (href, label))
        out = ['<nav class="l-tabbar" aria-label="Pestañas" lang="es">']
        for href, key, _ in TAB_ITEMS:
            h, label = es(key, href, "")
            cur = ' aria-current="page"' if h == current else ""
            icon = TAB_ICON[key] if key != "triage" else '<span class="cross">' + TAB_ICON[key] + '</span>'
            out.append(f'  <a href="{root}{h}" class="l-tab l-tab-{key}"{cur}>{icon}<span class="l-tab-label">{label}</span></a>')
        out.append(f'  <details class="l-more"><summary class="l-tab l-tab-more">{TAB_ICON["more"]}<span class="l-tab-label">Más</span></summary>')
        out.append('    <div class="l-msheet">')
        out.append('      <div class="l-msheet-head"><h2 class="l-msheet-title">Más</h2></div>')
        out.append('      <div class="l-msheet-body">')
        out.append('        <div class="l-msheet-links">')
        for href, key, _, cls in MORE_ITEMS:
            h, label = es(key, href, "")
            attrs = f' class="{cls}"' if cls else ""
            out.append(f'          <a href="{root}{h}"{attrs}>{LINK_ICON[key]}{label}</a>')
        out.append(f'          <a href="{root}index.html" lang="en" hreflang="en">{LINK_ICON["runbook"]}English</a>')
        out.append('        </div>')
        out.append('      </div>')
        out.append('      <div class="l-msheet-foot"><button class="l-pill" type="button" data-role="status" onclick="lanternToggleTheme()" aria-label="Estado del servidor. Cambiar tema"><span class="dot"></span>…</button></div>')
        out.append('    </div>')
        out.append('  </details>')
        out.append("</nav>")
        return "\n".join(out)
    mark = lambda key: SERVER_MARK if server and key in ("search", "chat") else ""
    suffix = lambda key: " (server)" if server and key in ("search", "chat") else ""
    out = ['<nav class="l-tabbar" aria-label="Tabs">']
    for href, key, label in TAB_ITEMS:
        cur = ' aria-current="page"' if href == current else ""
        icon = TAB_ICON[key] if key != "triage" else '<span class="cross">' + TAB_ICON[key] + '</span>'
        out.append(f'  <a href="{root}{href}" class="l-tab l-tab-{key}"{cur}{mark(key)}>{icon}<span class="l-tab-label">{label}{suffix(key)}</span></a>')
    # fifth tab: a <details> sheet with everything the desktop sidebar has (works with JS off)
    more_cur = ' aria-current="page"' if any(h == current for h, _, _, _ in MORE_ITEMS) else ""
    out.append(f'  <details class="l-more"><summary class="l-tab l-tab-more"{more_cur}>{TAB_ICON["more"]}<span class="l-tab-label">More</span></summary>')
    out.append('    <div class="l-msheet">')
    out.append('      <div class="l-msheet-head"><h2 class="l-msheet-title">More</h2></div>')
    out.append('      <div class="l-msheet-body">')
    out.append('        <div class="l-msheet-links">')
    for href, key, label, cls in MORE_ITEMS:
        attrs = f' class="{cls}"' if cls else ""
        if href == current:
            attrs += ' aria-current="page"'
        out.append(f'          <a href="{root}{href}"{attrs}{mark(key)}>{LINK_ICON[key]}{label}{suffix(key)}</a>')
    out.append('        </div>')
    out.append('        <p class="l-caption">Shelves</p>')
    out.append('        <div class="l-shelflist" data-fill="shelves"></div>')
    # sidebar .l-foot links, same home on phone (09-29: not in page footers)
    out.append('        ' + operator_html(root))
    out.append('      </div>')
    out.append('      <div class="l-msheet-foot"><button class="l-pill" type="button" data-role="status" onclick="lanternToggleTheme()" aria-label="Server status. Switch theme"><span class="dot"></span>checking…</button></div>')
    out.append('    </div>')
    out.append('  </details>')
    out.append("</nav>")
    return "\n".join(out)

def stamp_chrome():
    """Authored pages carry <!--NAV--> / <!--TABBAR--> markers; the blocks
    between them are generated here so chrome edits happen exactly once."""
    for page, current in [("index.html", "index.html"),
                          ("search.html", "search.html"),
                          ("plants.html", ""),
                          ("reader.html", ""),
                          ("audio.html", "audio.html"),
                          ("video.html", ""),
                          ("chat.html", "chat.html"),
                          ("map.html", "map.html"),
                          ("kids.html", "kids.html"),
                          ("triage.html", "triage.html"),
                          ("es.html", "es.html")]:   # FIXES #206: the Spanish landing page, Spanish tab bar
        lang = "es" if page == "es.html" else "en"
        f = f"{LIB}/{page}"
        s = open(f).read()
        s = re.sub(r"<!--NAV-->.*?<!--/NAV-->",
                   "<!--NAV-->\n  " + nav_html("", current) + "\n  <!--/NAV-->",
                   s, flags=re.S)
        s = re.sub(r"<!--TABBAR-->.*?<!--/TABBAR-->",
                   "<!--TABBAR-->\n" + tabbar_html("", current, lang=lang) + "\n<!--/TABBAR-->",
                   s, flags=re.S)
        # FIXES #232 (a7a W6): reader.html swaps in this Spanish tab bar when it is opened from a Spanish page
        s = re.sub(r"<!--TABBAR_ES-->.*?<!--/TABBAR_ES-->",
                   lambda m: '<!--TABBAR_ES-->\n<template id="tabbar-es">\n' + tabbar_html("", "", lang="es") + "\n</template>\n<!--/TABBAR_ES-->",
                   s, flags=re.S)
        # brand: every wordmark anchor (header + sidebar) and one favicon link
        s = re.sub(r'<a class="l-wordmark"[^>]*>.*?</a>', lambda m: brand_html(""), s, flags=re.S)
        # sidebar (09-29): server state at the top, operator list at the foot, same block as More
        if '<aside class="l-sidebar">' in s:
            foot = "  <!--SIDEFOOT-->\n  <div class=\"l-foot\">" + operator_html("") + "</div>\n  <!--/SIDEFOOT-->\n"
            if "<!--SIDEFOOT-->" in s:
                s = re.sub(r'  <!--SIDEFOOT-->.*?<!--/SIDEFOOT-->\n', foot, s, count=1, flags=re.S)
            else:
                s = re.sub(r'  <div class="l-foot">.*?</div>\n', foot, s, count=1, flags=re.S)
            s = re.sub(r'(<aside class="l-sidebar">\n  <a class="l-wordmark".*?</a>)\n(?:  <!--SIDEPILL-->.*?\n)?', lambda m: m.group(1) + "\n  <!--SIDEPILL-->" + STATUS_PILL + "\n", s, count=1, flags=re.S)
        if 'rel="icon"' not in s:
            s = s.replace('<link rel="stylesheet" href="_app/fonts/fonts.css">',
                          favicon_html("") + '\n<link rel="stylesheet" href="_app/fonts/fonts.css">', 1)
        open(f, "w").write(s)

def gen_allowed():
    """historical.html's ALLOWED list derives from gen_index.HIST_PATHS (the
    SHELVES historical flags + the cd3wd health prefix) — the same gate the shelf
    rows and search.html use, so nothing that links the interstitial dead-ends
    there (redteam 2026-10-05 F1: 348 cd3wd health rows did)."""
    hist = [k for k, m in SHELVES.items() if len(m) > 2 and m[2]]
    entries = [f"'{p.rstrip('/')}/'" for p in HIST_PATHS] + \
              [f"'_app/shelf/{k.replace('/', '_')}'" for k in hist]
    block = ("/*ALLOWED*/\n  var ALLOWED = [" + ", ".join(entries) + "];\n  /*/ALLOWED*/")
    f = f"{LIB}/_app/historical.html"
    s = open(f).read()
    s2 = re.sub(r"/\*ALLOWED\*/.*?/\*/ALLOWED\*/", block, s, flags=re.S)
    assert s2 != s or block in s, "ALLOWED markers missing in historical.html"
    open(f, "w").write(s2)
    # search.html HIST_PREFIX is hand-maintained (not generated here): every entry must be allowed through
    hp = re.search(r"var HIST_PREFIX = \[(.*?)\];", open(f"{LIB}/search.html").read()).group(1)
    missing = [x for x in re.findall(r"'([^']+)'", hp) if f"'{x}'" not in entries]
    assert not missing, f"search.html HIST_PREFIX not in historical.html ALLOWED: {missing}"


# Brand mark: the 2026-09-29 logo rework (the private design notes).
# Icon paths inlined so the mark follows the theme via currentColor; the
# wordmark is live text in Libre Baskerville (fonts.css). Favicon = same icon, amber.
BRAND_ICON = ('<svg class="l-mark" viewBox="0 0 100 144" aria-hidden="true" fill="currentColor">'
  '<path fill-rule="evenodd" d="M27 3H73Q77 3 77 7V18Q92 25 92 45V109Q92 126 73 129H67V134H78Q80 134 80 137V142H20V137Q20 134 22 134H33V129Q8 128 8 109V45Q8 25 23 18V7Q23 3 27 3ZM33 10V15H67V10ZM37 27Q19 27 19 46V107Q19 117 29 118H38L50 126L62 118H71Q81 117 81 107V46Q81 27 63 27Z"/>'
  '<path fill-rule="evenodd" d="M50 43C45 54 34 66 34 78C34 88 40 95 47 96C40 90 47 82 50 77C53 83 60 90 53 96C61 95 66 88 66 78C66 66 55 53 50 43Z"/>'
  '<path d="M24 99C33 98 43 101 48 107V120C41 114 33 112 24 112ZM52 107C57 101 67 98 76 99V112C67 112 59 114 52 120Z"/></svg>')

def brand_html(root=""):
    return f'<a class="l-wordmark" href="{root}index.html">{BRAND_ICON}Lantern</a>'

def favicon_html(root=""):
    return f'<link rel="icon" href="{root}_app/brand/lantern-icon.svg" type="image/svg+xml">'

def shell(title, body, root="../../", crumb="", server=False, lang="en"):
    # FIXES #201: a literal run of three backticks means a code fence leaked through md_render; fail the build
    if "`" * 3 in body:
        raise SystemExit(f"gen_shelves: three backticks in the rendered page {title!r} (md_render missed a fence)")
    # FIXES #206 (K2 hand-off): a page's language is on <html> (screen readers, Pagefind's language bucket); NOTE_LANG notes are "es"
    es = lang == "es"
    return f"""<!doctype html>
<html lang="{esc(lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — Lantern</title>
{favicon_html(root)}
<link rel="stylesheet" href="{root}_app/fonts/fonts.css">
<link rel="stylesheet" href="{root}_app/app.css">
<script src="{root}_app/app.js" defer></script>
</head>
<body>
<main>
<header class="l-header">
  {brand_html(root)}
  <a class="l-cta-triage l-cta-triage--side" href="{root}{"triage_es.html" if es else "triage.html"}"><span class="cross">+</span><span><b>{"Herido o enfermo" if es else "Hurt or sick"}</b></span></a>
  {STATUS_PILL}
</header>
<div class="l-wrap">
<p class="l-caption" style="margin-top:16px"><a href="{root}index.html"{' lang="en"' if lang != "en" else ""}>Library</a> › {crumb or esc(title)}</p>
{body}
</div>
</main>
{tabbar_html(root, server=server, lang="es" if es else "en")}
</body>
</html>"""

DOC_META = doc_meta()  # gen_doc_meta.py + gen_doc_answers.py: {path: {t, s, a?, y?, l?}}
TITLES = resolve_titles(DOC_META)  # E3: one display title per path, collisions carry year/language
THIS_YEAR = int(time.strftime("%Y"))

# E4 medical currency, decided by rule (2026-10-04, no manual review): on a health shelf every row shows its
# year ("year unknown" when none); over MEDICAL_MAX_AGE years old = "background, see newer" with the newest sibling
# on the same shelf that shares the most title words; fallback = the triage NOW source (refs.json wtnd_firstaid).
_STOP = set("the and for with from into over under your their this that these those about when what where which "
            "guide manual handbook book edition field care pocket chart "
            "chapter doctor there guidelines health injury wounds casualty children settings support".split())
def _topic_words(title):
    return {w for w in re.findall(r"[a-z]{4,}", title.lower()) if w not in _STOP}

def medical_currency(by_shelf):
    """{path: (year_or_"", stale_bool, newer_path_or_"")} for every PDF on a health shelf + the audit TSV."""
    out, rows = {}, []
    try:
        fallback = json.load(open(f"{BASE}/data/refs.json"))["docs"]["wtnd_firstaid"]["pdf"]
    except (OSError, KeyError):
        fallback = ""
    for shelf in HEALTH_SHELVES:
        pdfs = [p for p, _ in by_shelf.get(shelf, []) if p.lower().endswith(".pdf")]
        years = {p: doc_year(p, DOC_META) for p in pdfs}
        fresh = [p for p in pdfs if years[p] and THIS_YEAR - int(years[p]) <= MEDICAL_MAX_AGE]
        for p in pdfs:
            y = years[p]
            stale = bool(y) and THIS_YEAR - int(y) > MEDICAL_MAX_AGE
            newer, how = "", ""
            if stale:
                tw = _topic_words(TITLES.get(p, ""))
                best = max(fresh, key=lambda q: (len(tw & _topic_words(TITLES.get(q, ""))), years[q]), default="")
                # fix #102: a sibling needs 2+ real topic words; no sibling beats a wrong one. The first-aid fallback
                # only goes to a document that is itself first aid (it used to catch 13 off-topic books).
                if best and len(tw & _topic_words(TITLES.get(best, ""))) >= 2:
                    newer, how = best, "topic words: " + " ".join(sorted(tw & _topic_words(TITLES.get(best, ""))))
                elif "first aid" in TITLES.get(p, "").lower() and "psycholog" not in TITLES.get(p, "").lower() and fallback and (fallback in pdfs or os.path.exists(f"{LIB}/{fallback}")):
                    newer, how = fallback, "fallback: triage NOW source"
            out[p] = (y, stale, newer)
            rows.append((shelf, p, y or "unknown", "background" if stale else ("current" if y else "year unknown"), newer, how))
    os.makedirs(f"{BASE}/logs/audit", exist_ok=True)
    with open(f"{BASE}/logs/audit/medical_currency.tsv", "w") as f:
        f.write("shelf\tpath\tyear\tverdict\tnewer_sibling\thow_picked\n")
        f.writelines("\t".join(r) + "\n" for r in rows)
    return out
CURRENCY = {}  # filled in main() once by_shelf is known

def row_title(path):
    """The name a shelf row prints (r9 a3 W2: map.html's region names for Organic Maps files)."""
    return TITLES.get(path) or (MWM_DISPLAY.get(os.path.basename(path)[:-4]) if path.startswith("maps/organicmaps/") and path.endswith(".mwm") else None) or humanize(os.path.basename(path))

def doc_row(path, size, historical, root="../../"):
    meta = DOC_META.get(path, {})
    title = row_title(path)
    # E1c: the two-sentence "what this answers" (in the document's language) when gen_doc_answers has run, else the
    # one-line summary from gen_doc_meta
    blurb = f'<div class="meta">{esc(meta.get("a") or meta["s"])}</div>' if meta.get("a") or meta.get("s") else ""
    year = CURRENCY[path][0] if path in CURRENCY else ""
    lang = doc_lang(path, DOC_META)   # FIXES #232 (a7a W6): a Spanish PDF opens the reader with Spanish chrome (&lang=es)
    # PDFs open in reader.html like search results do (one path everywhere;
    # the reader saves the page for "Continue" and keeps an "Open the PDF file" link,
    # which is also its file:// / no-JS fallback). Other files stay direct.
    # FIXES #242 (a7a W2): a Spanish historical document gets the Spanish warning (historical.html reads &lang=es)
    # FIXES #277 (r10 b3 N-02): + #es, so the Spanish warning shows with JS off too (historical.html: #es:target)
    href = (f"{root}_app/historical.html?f=" + quote(path, safe="") + ("&lang=es#es" if lang == "es" else "")) if historical \
        else (f"{root}reader.html?f=" + quote(path, safe="") + "&t=" + quote(title, safe="") + (f"&y={year}" if year else "")
              + ("&lang=es" if lang == "es" else "")) if path.lower().endswith(".pdf") \
        else f"{root}{quote(path)}"
    cover_id = sha8(path)
    cov = f"{LIB}/_app/covers/{cover_id}.jpg"
    img = f'<img class="cover" loading="lazy" src="{root}_app/covers/{cover_id}.jpg" alt="">' \
        if os.path.exists(cov) and os.path.getsize(cov) > 0 else ""
    badge = ' <span class="l-badge l-badge--hist">HISTORICAL</span>' if historical else ""
    if lang != "en" and lang in LANG_NAME:
        badge += f' <span class="l-badge l-badge--lang">{esc(LANG_NAME[lang])}</span>'
    if path in CURRENCY:
        y, stale, newer = CURRENCY[path]
        badge += f' <span class="l-badge l-badge--year">{esc(y) if y else "year unknown"}</span>'
        if stale:
            # E4: the badge says "background" and the year badge says how old. The auto-picked newer sibling stays in
            # medical_currency.tsv only: rendered inside the row it nested an <a> in an <a> (broken cards, 10-05),
            # and 13 of 27 picks were the first-aid fallback, which pointed a surgery book at a first-aid chapter.
            badge += ' <span class="l-badge l-badge--stale">background</span>'
    note = ""
    if path.endswith(".md") and not blurb:
        # a library-written note carries its own one-line description: the first paragraph after the "# " title
        lead = next((l.strip() for l in open(f"{LIB}/{path}") if l.strip() and not l.startswith("#")), "")
        lead = re.sub(r"^[>\s]+|\*\*|`", "", lead)   # a blockquote or bold lead line shows as plain text, not markdown
        blurb = f'<div class="meta">{esc(lead)}</div>' if lead else ""
    if path in NOTE_LANG:
        # FIXES #206 (E6): an English shelf shows no Spanish text; the note is listed on es.html for Spanish readers
        blurb = f'<div class="meta">A library note in {esc(LANG_NAME.get(NOTE_LANG[path], NOTE_LANG[path]))}, listed on the Español page.</div>'
    if path.endswith(".md"):
        # the row opens the rendered page (gen_md_siblings); it links the raw file
        href = href[:-3] + ".html"
        note = " · opens as a page"
    return (f'<a class="l-doc-row" href="{href}">{img}<span><b>{esc(title)}</b>{badge}{blurb}'
            f'<div class="meta">{esc(path)} · {human_size(size)}{note}</div></span>'
            f'<span class="spacer">›</span></a>')

SPECIAL_INTRO = {
    "docs/plant_id": '<a class="l-btn" href="../../plants.html">← Back to the visual plant browser</a>'
                     '<p class="l-caption">Raw photo list: every image file, grouped by species.</p>',
    "docs/foraging_coastal": '<a class="l-btn" href="../../plants.html">Open the plant and coastal species browser →</a>'
                             '<p class="l-caption">Photos of 24 shoreline species are in the Coastal tab there; '
                             'the raw photo folders are at <a href="../../docs/coastal_id/">docs/coastal_id/</a>.</p>',
                             # FIXES #206 (E6): the Spanish shellfish paragraph (#167) moved to es.html; English pages carry no Spanish
    # FIXES #169 (a7b F2): a grease fire was unreachable in English; the Hesperian page is in the mirror
    "docs/fire_safety": '<p class="l-caption"><b>Fire in the kitchen, a pan of oil on fire:</b> do not put water on it; cover it with a lid, blanket or heavy cloth, '
                        'or throw sand or dirt on the grease. <a href="../../triage.html#fire">Hurt or sick: kitchen / grease fire</a> · '
                        '<a href="../../mirrors/hesperian/en.hesperian.org/hhg/A_Community_Guide_to_Environmental_Health:Fire_Safety.html">Hesperian, Fire Safety</a> · '
                        '<a href="../../mirrors/ready_gov/www.ready.gov/home-fires.html">Ready.gov, home fires</a>. '
                        'The PDFs below are about wildfire around the house.</p>',
    # FIXES #183 class 4 (a7a F1, a7b F3): the only water-heater answers were a nuclear flyer and a FEMA earthquake page.
    # FIXES #208 (a7a W2): the toilet-tank caveat, EPA p.2 cited beside Ready.gov. #206 (E6): the Spanish line moved to es.html.
    "docs/water": '<p class="l-caption"><b>No tap water?</b> The water heater tank holds safe drinking water. So does the toilet tank (not the bowl), '
                  'but only if no cleaning tablet or chemical has been put in the tank; the EPA sheet on the Water shelf says not to drink '
                  'flush-tank water, so treat it first if you can: '
                  '<a href="../../mirrors/ready_gov/www.ready.gov/sites/default/files/2023-01/ready-gov_nuclear-detonation-safety_flyer1.pdf">Ready.gov flyer</a> '
                  '("Water from your toilet tank (not bowl) and water heater is also safe") · '
                  '<a href="../../docs/water/epa_emergency_disinfection_drinking_water.pdf#page=2">EPA, Emergency Disinfection of Drinking Water, PDF page 2</a> '
                  '("You should not use water from toilet flush tanks or bowls") · '
                  '<a href="../../docs/emergency_mgmt/fema_p530_earthquake_safety_at_home_2020.pdf#page=32">FEMA P-530, PDF page 32</a> '
                  '("Water heaters are also a source of emergency water"). Is this water safe: <a href="../../triage.html#water">Hurt or sick, water card</a>.</p>',
    # FIXES #183 D9: the library's own note, written from NEETS module 1, Battery University and the Victron paper
    "docs/energy": '<p class="l-caption"><b>Phone dead and the power out?</b> <a href="../../docs/energy/charging_a_phone_from_a_car_battery.html">Charging a phone from a car battery</a>: '
                   'a one-page library note on the car socket, how much a starting battery can give without leaving the car unable to start, '
                   'carbon monoxide and battery safety, with page numbers into NEETS module 1.</p>',   # #206 (E6): the Spanish twin (#194) is on es.html
    "audio/librivox": '<a class="l-btn" href="../../audio.html">Open the audiobook player →</a>',
    "video/prelinger": '<a class="l-btn" href="../../video.html">Open the video player →</a>'
                       # FIXES #161 (a4 W8): no historical signpost on the 1940s first-aid films
                       '<p class="l-caption">Films from the 1920s to the 1970s, kept for their trade and farming skills. Their first-aid '
                       'advice (iodine on wounds, splint every fracture, nuclear "duck and cover") is out of date: for an injury or '
                       'illness use <a href="../../triage.html">Hurt or sick</a> and the current first-aid books. The two 1942 '
                       '<i>Emergency First Aid</i> films are silent (the archive copies have no soundtrack).</p>',
    "video/khan_academy": '<a class="l-btn" href="../../video.html?g=video/khan_academy">Open the video player →</a>'
                          '<p class="l-caption">Salman Khan\'s 2012 lessons from the CD3WD discs, re-encoded to play in any browser. '
                          'Each row is one lesson of 5 to 15 minutes; the folders follow the disc numbers.</p>',
    "video/preschool": '<a class="l-btn" href="../../video.html?g=video/preschool">Open the video player →</a>'
                       '<p class="l-caption">Short clips for small children: one word per clip for reading practice, clock faces for telling time, '
                       'letters A to Z, counting, and the Alice and Three Bears story chapters. From the CD3WD preschool discs.</p>',
    "maps": '<a class="l-btn" href="../../map.html">Open the map →</a>'
            '<p class="l-caption">Region files for phones (Organic Maps .mwm, OsmAnd .obf.zip) are listed below; copy to the phone once.</p>',  # a3 W3
    "tools": '<h2 class="l-h2">Use in the browser</h2>'
             '<p><a class="l-btn" href="../../tools/suncalc.html">Sun &amp; moon</a> '
             '<a class="l-btn" href="../../tools/convert.html">Converters</a> '
             '<a class="l-btn" href="../../chat.html">Ask the library (AI)</a> '
             '<a class="l-btn" href="../../discs/">Browse the CD3WD discs</a></p>'
             '<h2 class="l-h2">Install on your own phone or laptop</h2>'
             '<p class="l-caption">Each folder opens with its instructions page first, then the files to download. '
             'Technical notes for all of them: <a href="../../tools/README.html">tools README</a>.</p>',
    "docs/medical": '<div class="l-notice-dosing"><b>This library\'s own pages, summaries and search never state drug doses.</b> '
                    'The medical books on the shelf do: use the printed drug guide (Davis\'s, Lippincott pocket) for any dose.</div>',  # D2 wording, FIXES #150
    "docs/shelter": '<p class="l-caption">Building trades: plumbing, carpentry, concrete and masonry, wood. '
                    'For an emergency or cold-weather shelter open <a href="../../docs/military_manuals/fm_21-76_survival.pdf">FM 21-76 Survival</a>, '
                    'chapter 5 "Shelters" (printed page 47), on the <a href="docs_military_manuals.html">Military field manuals</a> shelf, '
                    'or the <a href="../../mirrors/ready_gov/www.ready.gov/index.html">Ready.gov mirror</a>.</p>',  # a7b F6
    "docs/survivor_library": '<div class="l-hazard"><span class="l-badge l-badge--hist">HISTORICAL</span> '
                             'Pre-industrial technology scans, mostly 1850–1950. Background and technique reference only — '
                             'never medicine, doses, or canning times from these.</div>',
    "docs/HISTORICAL": '<div class="l-hazard"><span class="l-badge l-badge--hist">HISTORICAL</span> '
                       'Outdated medical texts kept for context. Do not treat anyone from them.</div>',
    "docs/cd3wd": '<p class="l-caption">Aid-agency manuals (GTZ, VITA, ITDG, FAO, UNESCO, Peace Corps) written for villages without '
                  'grid power or a hardware store. Most are decades old: check anything medical against the Medical shelf; the '
                  'village-health manuals open through the historical notice. '
                  'The 26 disc images at the foot are data discs (these documents plus .avi lesson videos), not movie DVDs; '
                  'the box has every disc opened already, <a href="../../discs/">browse them like folders</a>. '
                  'To open an .iso on your own device: <a href="../video_players.html">disc image &amp; video players</a>.</p>',
}

# H30: one-line "what is this" per shelf/group (gen_summaries.py, hand-reviewed)
_SP = f"{BASE}/data/summaries.json"
SUMMARIES = json.load(open(_SP)) if os.path.exists(_SP) else {}
MISSING_SUMMARIES = []   # the owner: everything described — reported at the end of main()

# FIXES #217 (rt6 class 6, a2 B1): a species group summary must name every lookalike its README names, or the build stops.
# "Names" = (1) the README's "Do not confuse with:" species; (2) every other library species (plant_id, coastal_id) the English
# note names in a confusion sentence; (3) the plain names after "mistaken for" / "confused with" in the English note
# ("button mushroom", "Agaricus", "blue camas"). (1) and (2) count when the species name appears in order (plural s, case,
# _ - ' ignored), also reversed for two words ("giant puffball") or without a leading "amanita" ("death cap"); (3) counts when
# each of its words appears anywhere in the summary ("button, meadow and horse mushrooms" names all three).
_LOOK_CUE = re.compile(r"mistaken|confus|look-?alike|look-similar|looks? like|resembl", re.I)
_LOOK_OBJ = re.compile(r"\b(?:mistaken for|confused with|confuse with)\s+(?:it\s*:\s*)?", re.I)
_LOOK_END = re.compile(r"\s*[(;:.—]|,\s+(?:and|which|especially|whose|both)\b|\s+(?:because|which|especially|whose|when|is|has)\b")
_LOOK_LEAD = re.compile(r"^(?:(?:the|a|an|edible|poisonous|toxic|deadly|much|less|two|extremely|species|bulbs|including|plants)\s+|,\s*)+", re.I)

def _look_objects(english, self_title):
    out = []
    for m in _LOOK_OBJ.finditer(english):
        for it in re.split(r",\s*|\s+and\s+|\s+or\s+", _LOOK_END.split(english[m.end():], 1)[0]):
            it = _LOOK_LEAD.sub("", it.strip()).strip()
            w = set(_words(it))
            # drop pronouns, clause fragments, and the species itself ("pokeweed roots have been mistaken for Jerusalem artichoke")
            if w and len(w) <= 3 and not w <= {"it", "them", "specie", "this"} and not w <= set(_words(self_title)) and it not in out:
                out.append(it)
    return out

def _words(s):
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"[a-z]+", s.lower().replace("_", " "))]

def _names(text, name, reverse=True):
    t, n = " " + " ".join(_words(text)) + " ", _words(name)
    forms = [n, n[::-1] if reverse and len(n) == 2 else n, n[1:] if n[0] == "amanita" and len(n) > 2 else n]
    return any(f" {' '.join(f)} " in t for f in forms)

def stale_lookalikes(summaries=None, lib=None):
    """[(summary key, [lookalike names the summary leaves out])] for group:docs/{plant_id,coastal_id}/<slug> keys."""
    summaries, lib = summaries if summaries is not None else SUMMARIES, lib or LIB
    readme = {}   # slug -> (title, English note + "Do not confuse" line)
    for f in glob.glob(f"{lib}/docs/plant_id/*/README.txt") + glob.glob(f"{lib}/docs/coastal_id/*/README.txt"):
        lines = open(f).read().split("\n")
        readme[os.path.basename(os.path.dirname(f))] = (lines[0].strip(), "\n".join(lines[3:5]))
    out = []
    for key, summ in sorted(summaries.items()):
        m = re.match(r"group:docs/(?:plant_id|coastal_id)/([^/]+)$", key)
        if not m or m.group(1) not in readme:
            continue
        slug = m.group(1)
        body = readme[slug][1]
        need = re.findall(r"Do not confuse with: .*?\(folder \.\./([^/]+)/\)", body)
        english = body.split("Español —")[0]
        cues = [x for x in re.split(r"(?<=[.!?])\s+", english) if _LOOK_CUE.search(x)]
        # forward order only when reading the note: "hemlock water dropwort" is not "water hemlock"
        need += [o for o, (title, _) in sorted(readme.items()) if o != slug and o not in need and any(_names(c, title, False) for c in cues)]
        missing = [readme[o][0] for o in need if o in readme and not _names(summ or "", readme[o][0])]
        sw = set(_words(summ or ""))
        missing += [it for it in _look_objects(english, readme[slug][0])
                    if not set(_words(it)) <= sw and not any(_names(it, readme[o][0], False) for o in need if o in readme)]
        if missing:
            out.append((key, missing))
    return out

# H31: per-mirror entry page — a direct "open the site" link beside the
# file browser. Picked by hand: the page a reader would start from.
MIRROR_ENTRY = {
    "aredn_docs": "docs.arednmesh.org/index.html",
    "hesperian": "en.hesperian.org/hhg/HealthWiki.html",
    "journeytoforever": "journeytoforever.org/index.html",
    "meshtastic_docs": "meshtastic.org/docs/index.html",
    "nchfp": "nchfp.uga.edu/index.html",
    "ready_gov": "www.ready.gov/index.html",
    "sheldonbrown": "www.sheldonbrown.com/index.html",
}

# tools shelf: plain-language folder titles in reader order (phone first, then laptop, then AI)
TOOL_GROUPS = [("android", "Android apps: offline maps and Kiwix"),
               ("video_players", "VLC and Material Files: disc images and lesson videos"),
               ("kiwix_desktop", "Kiwix for laptops: the encyclopedias without the box"),
               ("opencpn", "OpenCPN: nautical charts on a laptop"),
               ("llamafile", "Llamafile: runs the AI models on any computer"),
               ("models", "AI models for llamafile and Ask"),
               ("whisper", "Whisper: speech to text"),
               ("piper", "Piper: text to speech"),
               ("argos", "Argos: English-Spanish translation")]
TOOL_TITLE = dict(TOOL_GROUPS)
TOOL_ORDER = {g: i for i, (g, _) in enumerate(TOOL_GROUPS)}

def group_key(shelf, path):
    rest = path[len(shelf):].lstrip("/")
    parts = rest.split("/")
    if shelf == "docs/survivor_library":
        # SurvivalLibrary/library/<Category>/file
        return parts[2] if len(parts) > 3 else "misc"
    if shelf == "audio/librivox":
        # age_shelf/album — one collapsible per album, ordered by age shelf
        return "/".join(parts[:2]) if len(parts) > 2 else parts[0]
    if shelf == "docs/cd3wd":
        # 2012/<category>/file -> category; the .iso folders -> one "Disc images" group (the owner decision 2)
        if parts[0] == "2012" and len(parts) > 2:
            return parts[1]
        return "disc_images" if parts[0] in ("2012_dvd", "2015_highschool", "2015_primary") else parts[0]
    if shelf in ("docs/mit_ocw", "docs/school_textbooks", "maps", "mirrors",
                 "video/prelinger", "video/khan_academy", "video/preschool", "tools", "docs/plant_id", "datasets"):
        return parts[0] if len(parts) > 1 else "top"
    return None  # flat list

def zim_row(z, root="../../"):
    """E6: one described row per encyclopedia from the kiwix catalog; data-path makes the .zim reachable for T3,
    data-kiwix is rewritten by app.js to the live kiwix host:port (same as the landing chips)."""
    lang = {"eng": "English", "spa": "Spanish", "mul": "many languages"}.get(z["lang"], z["lang"])
    return (f'<a class="l-doc-row" href="{root}search.html" data-kiwix="/viewer#{quote(z["stem"])}" data-path="zim/{esc(z["file"])}">'
            f'<span><b>{esc(z["title"])}</b><div class="meta">{esc(z["summary"])}</div>'
            f'<div class="meta">{esc(z["file"])} · {human_size(z["size"])} · {z["articles"]:,} articles · {esc(lang)} · {esc(z["date"])}</div></span>'
            f'<span class="spacer">›</span></a>')

GAPS = json.load(open(f"{BASE}/data/known_gaps.json")) if os.path.exists(f"{BASE}/data/known_gaps.json") else []
# E15 = B (red team 2026-10-23, PF2): the catalogue claims rate is tracked, not a stop bar, so the page says so plainly
CATALOGUE_NOTE = ('<p style="max-width:640px">Catalogue years, titles and summaries were written by machine from each document '
                  'and can be off. The document itself is the source.</p>'
                  # E18 = A (round 7, #223): Ask relevance on everyday health questions is tracked, not a stop bar
                  # E26 (round 9, #254): Search and the front page take their card rows from the same matcher
                  '<p style="max-width:640px">The Ask page, Search and the front page pick the emergency cards with one '
                  'matcher, from the words of the question. Its closest match can be the wrong one, or it can find none. '
                  # FIXES #282-#283 (R1, R2): a matching life-threat card first; a matched row always followed by the open list
                  'A matching card for a life-threatening emergency (severe bleeding, choking, unconscious or not breathing, '
                  'a severe allergic reaction, carbon monoxide) is always listed first. '
                  'Ask lists all the emergency cards with every answer; Search and the front page show the closest cards '
                  'followed by the list of all of them. If the closest match does not fit, open the right card from that list or '
                  'from Triage. '
                  # FIXES #278-#281 (D4): no quoted document text on any channel
                  'No page here quotes text from the books: the Ask page, Search and the search for assistant programs list '
                  'page titles with links, and you read the text on the page itself. For everyday '
                  'health and water questions the Ask page often misses, more so in Spanish. If the pages it lists do not '
                  'answer, use Search or the Medical and Water shelves.</p>')
# FIXES #286 (round 11): reader limits found in the last full check and not fixed, one plain line each, grouped by part of
# the library. Source: data/known_limits.tsv (surface, limit_line, rows; rows is provenance and never shown).
LIMITS = [l.rstrip("\n").split("\t") for l in open(f"{BASE}/data/known_limits.tsv")][1:]

def limits_html():
    # a reader line never carries a file name, a code word or a reviewer or card id
    bad = [l for _, l, _ in LIMITS if re.search(r"_|\.(html|pdf|md|json|txt|zim)\b|\b[a-z]+\d|\b[A-Z]{1,3}\d", l)]
    assert LIMITS and not bad, f"known_limits.tsv: lines with a code word {bad}"
    groups = {}
    for surface, line, _ in LIMITS:
        groups.setdefault(surface, []).append(line)
    return ('<h2 id="limits" style="margin:28px 0 4px">Known limits</h2>'
            '<p style="max-width:640px">Things that work less well than they should. They were found in the last full check '
            'of the library, in October 2026, and were not fixed. Most lines say what to do instead.</p>' +
            "".join(f'<h3 style="margin:18px 0 4px">{esc(s)}</h3><ul style="max-width:640px">' +
                    "".join(f"<li>{esc(l)}</li>" for l in ls) + "</ul>" for s, ls in groups.items()))

def gen_known_gaps():
    """E5: what the re-fetch doctrine could not recover, listed so nobody hunts for it (title, shelf, why, origin)."""
    # FIXES #242 (b3 B3-38): a reader-facing title, never a content hash, and no two lines that read the same
    assert not [g for g in GAPS if re.fullmatch(r"[0-9a-f]{32}", g["title"], re.I)], "known_gaps.json: title is a hash"
    # FIXES #254 (b3 B3-41): titles shared by several files (seven Sheldon Brown home.gif icons) carry the folder they sit in
    n_title = {}
    for g in GAPS:
        n_title[g["title"]] = n_title.get(g["title"], 0) + 1
    def gap_title(g):
        if n_title[g["title"]] < 2:
            return g["title"]
        where = os.path.dirname(g["path"])[len(g["shelf"]):].strip("/").split("/", 1)[-1]   # drop the host folder
        return f'{g["title"]} ({re.sub(r"/images$", "", where)} pages)'
    seen = [gap_title(g) for g in GAPS]
    assert len(set(seen)) == len(seen), f"known_gaps.json: lines that read the same {sorted({s for s in seen if seen.count(s) > 1})}"
    rows = "".join(f'<tr><td>{esc(gap_title(g))}</td><td>{esc(g["shelf"])}</td><td>{esc(g["why"])}</td>'
                   f'<td class="l-caption">{esc(g.get("origin", ""))}</td></tr>' for g in GAPS)
    body = ('<h1 style="font-family:var(--l-font-display);margin:8px 0 4px">Known gaps</h1>' + CATALOGUE_NOTE +
            '<p class="l-caption" style="max-width:640px">Files that were in the plan but could not be recovered in a readable form: the '
            'original upload was truncated or damaged and the origin, the Wayback Machine and archive.org held no better copy. '
            'They are not on the shelves, so you do not hunt for them. Each line says where it came from.</p>'
            f'<p class="l-caption">{len(GAPS)} items</p>'
            '<table class="l-table"><thead><tr><th>Title</th><th>Shelf</th><th>Why</th><th>Source tried</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>' if GAPS else
            '<h1 style="font-family:var(--l-font-display);margin:8px 0 4px">Known gaps</h1>' + CATALOGUE_NOTE +
            '<p>Nothing missing: every planned file is on its shelf.</p>') + limits_html()
    with open(f"{LIB}/_app/known_gaps.html", "w") as f:
        f.write(shell("Known gaps", body, root="../"))

def librivox_albums():
    """FIXES #175 (a4 F1): album headings from the README tables (| slug | Title | Author | ...), not folder slugs."""
    out = {}
    for line in open(f"{BASE}/data/library_notes/audio/librivox/README.md"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and re.match(r"^[a-z0-9_]+$", cells[0]) and cells[1] and cells[1] != "Title":
            out[cells[0]] = f"{cells[1]} — {cells[2]}" if cells[2] else cells[1]
    assert len(out) >= 50, f"librivox README: only {len(out)} albums parsed"
    return out

ALBUM_TITLE = librivox_albums()

def group_title(shelf, g):
    if shelf == "tools":
        return TOOL_TITLE.get(g, humanize(g))
    if shelf == "audio/librivox":
        return ALBUM_TITLE.get(g.rsplit("/", 1)[-1], humanize(g))
    # FIXES #186/#183 (a4 F1): disc folders get the series heading from gen_media_titles.py, not "1103 JHS MATH03"
    return TITLES.get(f"shelfgroup:{shelf}/{g}") or humanize(g)

# FIXES #186 (a4 F4): silent disc title cards (media_titles.json "hide:<path>") stay out of every list
HIDDEN = {k[5:] for k in TITLES if k.startswith("hide:")}
# FIXES #244 (a4 W2, b5 N6): parts filed out of order on disc sort by the key here, on the shelf rows and on video.html
# (stamped as SORTAS in the VGROUPS block; the page sorts by SORTAS[p] || p). ponytail: hand table, add a row per misfiled part.
SORTAS = {"video/prelinger/201293_Emergency_First_Aid_P2_Bandaging.mp4": "video/prelinger/0994_Emergency_First_Aid_",
          "video/khan_academy/1116_HS_STATS/math_16_Statistics_057_Proof_pt_2_Minimizing_Squared_Error_to_Line.mp4":
          "video/khan_academy/1116_HS_STATS/math_16_Statistics_053_Proof_pt_1_Minimizing_Squared_Error_to_Regression_Line.mp4~",
          # FIXES #254 (a4 r9 W2): the 4 s clip is labelled set 2, the 10 s clip set 1
          "video/preschool/100212_PRESCHOOL/dvd_player/count/no_text_no_voice/count_ntnv_addition_1_4s_dvdp_pal_ed_presch_video.mp4":
          "video/preschool/100212_PRESCHOOL/dvd_player/count/no_text_no_voice/count_ntnv_addition_1_10s_dvdp_pal_ed_presch_video.mp4~"}
# FIXES #254 (a4 r9 N1): Khan groups whose disc folder sits out of lesson order sort by the key here on video.html (stamped as
# GSORT; the page sorts groups by GSORT[g] || g): developmental math 154-196 after 1-153, CK-12 1-85 before 86-107, statistics
# 61-68 after 1-60. ponytail: hand table, add a row per misfiled group.
GSORT = {"video/khan_academy/1108_JHS_MATH08/math02_02_": "video/khan_academy/1101_PRIMARY_MATH/math02~1",
         "video/khan_academy/1112_JHS_MATH12_GEOMETRY/math02_3_": "video/khan_academy/1101_PRIMARY_MATH/math02~2",
         "video/khan_academy/1103_JHS_MATH03/math02_4_": "video/khan_academy/1101_PRIMARY_MATH/math02~3",
         "video/khan_academy/1108_JHS_MATH08/math09_algebra_we_2_1130MB": "video/khan_academy/1109_JHS_MATH09_ALGEBRA~",
         "video/khan_academy/1115_HS_TRI_PROB_STATS/math16_stats_2_640MB": "video/khan_academy/1116_HS_STATS~"}


def natkey(s):
    """FIXES #254 (a4 r9 W3): the shelf rows sort like video.html's localeCompare(..., {numeric: true}): chapter 2 before 12."""
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", s.lower())]

def stamp_video_groups():
    """video.html group headings and hidden rows come from media_titles.json (gen_media_titles.py), stamped
    between /*VGROUPS*/ markers so the page needs no extra fetch and works from a drive."""
    groups = {k[6:]: v for k, v in sorted(TITLES.items()) if k.startswith("group:video/")}
    block = ("/*VGROUPS*/\n  var GROUP_TITLE = " + json.dumps(groups, ensure_ascii=False) + ";\n"
             "  var HIDE = " + json.dumps({p: 1 for p in sorted(HIDDEN)}) + ";\n"
             "  var SORTAS = " + json.dumps(SORTAS, sort_keys=True) + ";\n"
             "  var GSORT = " + json.dumps(GSORT, sort_keys=True) + ";\n  /*/VGROUPS*/")
    f = f"{LIB}/video.html"
    s = open(f).read()
    s2, k = re.subn(r"/\*VGROUPS\*/.*?/\*/VGROUPS\*/", lambda m: block, s, flags=re.S)
    assert k == 1, "video.html: VGROUPS markers missing"
    open(f, "w").write(s2)
    return len(groups)

def gen_shelf(shelf, meta, files):
    title, desc = meta[0], meta[1]
    historical = len(meta) > 2 and meta[2]
    if shelf.startswith("docs/"):
        # FIXES #220 (E6 sweep, rt6): the Spanish library notes leave the English shelves too; es.html links each of them
        files = [r for r in files if NOTE_LANG.get(r[0]) != "es"]
        # FIXES #206 (E6, 10-18 option A): Spanish catalog documents leave the English shelves; es_docs.html lists them
        es = [(p, s) for p, s in files if p not in NOTE_LANG and p not in HIDDEN and doc_lang(p, DOC_META) == "es"]
        if es:
            ES_DOCS[shelf] = (title, historical, es)
            files = [r for r in files if r not in es]
    # FIXES #220 (a4 F2): the silent disc title cards video.html hides are not lessons; count what the rows and players list
    files = [(p, s) for p, s in files if p not in HIDDEN]
    # FIXES #175 (a4 F6): media shelves count the playable files; the README is listed but is not a 1,601st track
    n_files = len([p for p, _ in files if not p.endswith(".md")]) if shelf.startswith(("audio/", "video/")) else len(files)
    if shelf == "zim":
        books = [z for z in kiwix_books() if z["lang"] != "spa"]   # FIXES #220 (E6 sweep): the Spanish ones are on es.html (ENC block)
        body = [f'<h1 style="font-family:var(--l-font-display);margin:8px 0 4px">{esc(title)}</h1>',
                f'<p class="l-caption" style="max-width:640px">{sumhtml(SUMMARIES.get("shelf:" + shelf, desc), "../../")} · {len(books)} books · '
                f'{human_size(sum(z["size"] for z in books))} <span class="l-badge show-direct">NEEDS THE SERVER</span></p>',
                '<div class="needs-enc">' + "\n".join(zim_row(z) for z in books) + '</div>']
        with open(f"{OUT}/zim.html", "w") as f:
            f.write(shell(title, "\n".join(body)))
        return "zim", len(books)
    rows_by_group = {}
    if shelf == "tools":
        # buttons above cover top-level pages; hide checksum sidecars and the extracted
        # copies inside piper_*_aarch64/ (the .tar.gz rows are the downloads)
        files = [(p, s) for p, s in files if p.count("/") == 2 and not p.endswith(".md5")]
    for p, size in files:
        g = group_key(shelf, p)
        rows_by_group.setdefault(g, []).append((p, size))
    body = [f'<h1 style="font-family:var(--l-font-display);margin:8px 0 4px">{esc(title)}</h1>',
            f'<p class="l-caption" style="max-width:640px">{sumhtml(SUMMARIES.get("shelf:" + shelf, desc), "../../")} · {n_files:,} files</p>']
    if shelf in SPECIAL_INTRO:
        body.append(SPECIAL_INTRO[shelf])
    gaps = [g for g in GAPS if g["shelf"] == shelf]
    if gaps:
        body.append(f'<p class="l-caption">{len(gaps)} planned file{"s" if len(gaps) > 1 else ""} could not be recovered in readable form: '
                    f'<a href="../known_gaps.html">known gaps</a>.</p>')
    groups = sorted(rows_by_group.items(), key=lambda kv: (kv[0] is None, kv[0] == "disc_images", TOOL_ORDER.get(kv[0], 99), str(kv[0]).lower()))
    for g, rows in groups:
        order = natkey if shelf.startswith("video/") else str.lower   # audio.html sorts plain, video.html numeric-aware
        # FIXES #275 (r10 a3 W1): the region lists sort by the name the row prints, as map.html does (gen_places.rows), not by
        # file name; the other map groups keep the main file first
        key = (lambda p: row_title(p).lower()) if shelf == "maps" and g in ("organicmaps", "osmand") else (lambda p: order(SORTAS.get(p, p)))
        rows.sort(key=lambda r: (not r[0].endswith("README.md"), key(r[0])))  # instructions first
        # Bulk sets (NOAA cells, topo quads, mirror assets): one folder row,
        # not thousands of <a> rows — pages must stay phone-loadable.
        if len(rows) > 200 and not historical and shelf not in ("docs/cd3wd", "docs/school_textbooks", "video/khan_academy", "video/preschool"):  # per-doc rows like survivor_library
            folder = f"{shelf}/{g}" if g else shelf
            total = sum(s for _, s in rows)
            entry = f"{LIB}/{folder}/index.html"
            href = f"../../{quote(folder)}/" + ("index.html" if os.path.exists(entry) else "")
            # rendered like any group below (H10: a bulk course/set must not
            # jump out of the dropdown scheme its siblings use)
            site = MIRROR_ENTRY.get(g) if shelf == "mirrors" else None
            rendered = (f'<a class="l-doc-row" href="{href}"><span><b>'
                        + ("Browse the files" if site else esc(humanize(g or shelf))) + '</b>'
                        f'<div class="meta">{esc(folder)}/ · {len(rows):,} files · {human_size(total)}'
                        + (" · browse the folder" if not os.path.exists(entry) else "")
                        + '</div></span><span class="spacer">›</span></a>')
            if site:
                assert os.path.exists(f"{LIB}/{folder}/{site}"), f"MIRROR_ENTRY missing: {folder}/{site}"
                rendered = (f'<a class="l-doc-row" href="../../{quote(folder)}/{quote(site)}"><span>'
                            f'<b>Open the site →</b><div class="meta">starts at {esc(site)}</div></span>'
                            f'<span class="spacer">›</span></a>\n' + rendered)
        else:
            rendered = "\n".join(doc_row(p, s, historical or is_hist(p)) for p, s in rows)
        if g is None or len(groups) == 1:
            body.append(rendered)
        else:
            if f"group:{shelf}/{g}" not in SUMMARIES:
                MISSING_SUMMARIES.append(f"group:{shelf}/{g}")
            body.append(f'<details><summary style="font-family:var(--l-font-display);font-size:17px;'
                        f'padding:10px 0;cursor:pointer">{esc(group_title(shelf, g))} '
                        f'<span class="l-caption">({len(rows)})</span>'
                        + (f'<span class="l-sum">{sumhtml(SUMMARIES[f"group:{shelf}/{g}"], "../../")}</span>'
                           if f"group:{shelf}/{g}" in SUMMARIES else "")
                        + f'</summary>{rendered}</details>')
    slug = shelf.replace("/", "_")
    with open(f"{OUT}/{slug}.html", "w") as f:
        f.write(shell(title, "\n".join(body)))
    return slug, n_files

ES_DOCS = {}  # shelf -> (English shelf title, historical, [(path, size)]), filled by gen_shelf
ES_SHELF_NAME = {"docs/cd3wd": "Manuales prácticos (CD3WD)", "docs/school_textbooks": "Libros de texto"}

def gen_es_docs():
    """FIXES #206 (E6): one Spanish page for the Spanish catalog documents taken off the English shelves; es.html links it."""
    body = ['<h1 style="font-family:var(--l-font-display);margin:8px 0 4px">Documentos en español</h1>',
            f'<p class="l-caption" style="max-width:640px">{sum(len(v[2]) for v in ES_DOCS.values()):,} documentos en español. '
            'Los demás documentos de la biblioteca están en inglés.</p>']
    for shelf, (title, historical, rows) in sorted(ES_DOCS.items()):
        body.append(f'<h2>{esc(ES_SHELF_NAME.get(shelf, title))} <span class="l-caption">({len(rows)})</span></h2>')
        rows.sort(key=lambda r: (TITLES.get(r[0]) or r[0]).lower())
        body.append("\n".join(doc_row(p, s, historical or is_hist(p)) for p, s in rows))
    with open(f"{OUT}/es_docs.html", "w") as f:
        f.write(shell("Documentos en español", "\n".join(body), lang="es",
                      crumb='<a href="../../es.html">Español</a> › Documentos en español'))
    return sum(len(v[2]) for v in ES_DOCS.values())

# ── minimal markdown → HTML (headers, lists, bold, code, links, hr, checkbox) ──
def md_render(text):
    out, in_ul, in_ol = [], False, False
    para = []  # consecutive plain lines = one paragraph (hard-wrapped md)
    def close_lists():
        nonlocal in_ul, in_ol
        if para: out.append(f"<p>{' '.join(para)}</p>"); para.clear()
        if in_ul: out.append("</ul>"); in_ul = False
        if in_ol: out.append("</ol>"); in_ol = False
    def inline(s):
        s = esc(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
        # server-only pages get the same marking as the tab bar (t8 server_marked); renders as md and sibling .html alike
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                   lambda m: f'<a href="{m[2]}"' + (SERVER_MARK if re.match(r"(?:\.\./)*(?:search|chat|reader)\.html(?:[?#]|$)", m[2]) else "") + f'>{m[1]}</a>', s)
        s = s.replace("[ ]", '<span style="font-family:monospace">[&nbsp;&nbsp;]</span>')
        return s
    rows = []  # pending | table | lines
    def flush_table():
        if not rows: return
        head, body = rows[0], [r for r in rows[1:] if not re.match(r"^[\s|:-]+$", r)]
        cells = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
        out.append('<div style="overflow-x:auto"><table class="l-md-table"><thead><tr>'
                   + "".join(f"<th>{inline(c)}</th>" for c in cells(head)) + "</tr></thead><tbody>"
                   + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells(r)) + "</tr>"
                             for r in body) + "</tbody></table></div>")
        rows.clear()
    # ``` blocks pass through verbatim as <pre>. FIXES #201 (a6 F1): a fence may be indented (inside a list item; its <pre>
    # stays in that <li>) or quoted ("> ```"); its lines lose that same prefix. Before, only column-0 fences opened, so
    # RUNBOOK's list-item commands ran together as one line of text.
    fence, fence_pre, fence_li = None, "", False
    def close_fence():
        pre = "<pre>" + esc("\n".join(fence)) + "</pre>"
        if fence_li:
            out[-1] = out[-1][:-5] + pre + "</li>"
        else:
            out.append(pre)
    for line in text.split("\n"):
        l = line.rstrip()
        fm = re.match(r"^([>\s]*)```", l)
        if fm:
            if fence is None:
                fence_pre = fm.group(1)
                fence_li = bool(fence_pre) and not fence_pre.strip() and (in_ul or in_ol) and out[-1].endswith("</li>")
                if not fence_li:
                    close_lists(); flush_table()
                fence = []
            else:
                close_fence(); fence = None
            continue
        if fence is not None:
            fence.append(re.sub(r"^[>\s]{0,%d}" % len(fence_pre), "", line) if fence_pre else line); continue
        if l.startswith("|"):
            close_lists(); rows.append(l); continue
        flush_table()
        if not l.strip():
            close_lists(); continue
        m = re.match(r"^(#{1,3}) (.*)", l)
        if m:
            close_lists()
            n = len(m.group(1))
            hid = re.sub(r"[^a-z0-9]+", "-", m.group(2).lower()).strip("-")
            out.append(f'<h{n} id="{hid}">{inline(m.group(2))}</h{n}>')
            continue
        if l.strip() == "---":
            close_lists(); out.append("<hr>"); continue
        m = re.match(r"^\s*[-*] (.*)", l)
        if m:
            if in_ol or para: close_lists()
            if not in_ul: out.append("<ul>"); in_ul = True
            out.append(f"<li>{inline(m.group(1))}</li>"); continue
        m = re.match(r"^\s*\d+\. (.*)", l)
        if m:
            if in_ul or para: close_lists()
            if not in_ol: out.append("<ol>"); in_ol = True
            out.append(f"<li>{inline(m.group(1))}</li>"); continue
        if (in_ul or in_ol) and l[:1] == " " and out[-1].endswith("</li>"):
            out[-1] = out[-1][:-5] + " " + inline(l.strip()) + "</li>"  # wrapped list item
            continue
        if in_ul or in_ol:
            close_lists()
        para.append(inline(l.strip()))
    if fence is not None:
        close_fence()   # an unclosed fence keeps its text instead of dropping it
    flush_table()
    close_lists()
    # phone width (T5, 390 px): code blocks scroll, long URLs wrap, instead of the page overflowing sideways
    return '<style>.l-md{overflow-wrap:anywhere}.l-md pre{overflow-x:auto}</style>\n' + "\n".join(out)  # bare long words in li/p/td spilled; pre scrolls (app.css has it too, kept here so a md page stands alone)

def gen_md_page(md_path, out_name, title, transform=None):
    if not os.path.exists(md_path):   # PURCHASE_LIST.md and BINDER_1_TOC.md are each box's own, optional
        print(f"skip {out_name}: no {os.path.relpath(md_path, BASE)}")
        return
    text = open(md_path).read()
    if transform:
        text = transform(text)
    body = ('<style media="print">.l-header,.l-tabbar{display:none!important}'
            'h2,h3{break-after:avoid}ul,ol,table{break-inside:auto}li,tr{break-inside:avoid}</style>'
            f'<article class="l-md" style="max-width:720px">{resolve(md_render(text), "../")}</article>'
            f'<p><button class="l-btn" onclick="print()">Print</button></p>')
    with open(f"{LIB}/_app/{out_name}", "w") as f:
        f.write(shell(title, body, root="../", server=True))

# Every .md in the manifest gets a rendered sibling .html (README.md ->
# README.html) so "[view]" links (app.js decorateLinks) work on the box, from
# a drive, and in Pagefind. Relative links inside the .md resolve unchanged.
# library-written notes in another language: the article gets its lang, the page its "# " title (accents kept)
NOTE_LANG = {"docs/energy/cargar_el_telefono_con_la_bateria_del_carro.md": "es",   # FIXES #194 (a7b M28)
             # FIXES #208 E4 (K8 writes them; es.html links them)
             "docs/military_manuals/encender_fuego_con_lena_mojada.md": "es",
             "docs/homesteading_extension/cultivos_de_cosecha_rapida.md": "es",
             "docs/food_preservation/conservar_carne_con_sal.md": "es"}

def md_sibling(rel):
    root = "../" * rel.count("/")
    text = open(f"{LIB}/{rel}").read()
    lang = NOTE_LANG.get(rel)
    title = humanize(os.path.basename(rel)[:-3]) if os.path.basename(rel) != "README.md" \
        else humanize(os.path.basename(os.path.dirname(rel)) or "library") + " README"
    if lang:
        title = next((l[2:].strip() for l in text.split("\n") if l.startswith("# ")), title)
    raw = f'<a href="{esc(os.path.basename(rel))}" data-raw="1">{esc(os.path.basename(rel))}</a>'
    foot = (f'<p class="l-caption" lang="es">Texto original: {raw}. <button class="l-btn" onclick="print()">Imprimir</button></p>' if lang == "es" else
            f'<p class="l-caption">Rendered from {raw} (raw text). <button class="l-btn" onclick="print()">Print</button></p>')
    body = (f'<article class="l-md" style="max-width:720px"{f" lang={chr(34)}{lang}{chr(34)}" if lang else ""}>{resolve(md_render(text), root)}</article>' + foot)
    # FIXES #208 (a7a N10, a4 W3): the breadcrumb shows the title, not the raw .md path; a Spanish note leads back to es.html
    crumb = f'<a href="{root}es.html">Español</a> › {esc(title)}' if lang == "es" else esc(title)
    with open(f"{LIB}/{rel[:-3]}.html", "w") as f:
        f.write(shell(title, body, root=root, crumb=crumb, server=True, lang=lang or "en"))

def gen_md_siblings():
    mds = {l.rstrip("\n").split("  ", 1)[1] for l in open(f"{LIB}/MANIFEST.sha256") if l.rstrip("\n").endswith(".md")}
    # tools READMEs written between seals still need their page (chat.html links one)
    mds |= {"library/" + os.path.relpath(p, LIB) for p in glob.glob(f"{LIB}/tools/*/README.md")}
    # library notes written between seals (the E4 Spanish notes, FIXES #208) need their page before the manifest lists them
    mds |= {"library/" + rel for rel in NOTE_LANG if os.path.exists(f"{LIB}/{rel}")}
    for path in sorted(mds):
        md_sibling(path[len("library/"):])
    return len(mds)

# H29: PURCHASE_LIST.md is the owner's working check-off copy; purchases.html is
# the canonical reference — same data, personal order/check state stripped.
def canonical_purchases(text):
    subs = [
        (r"(?m)^(\s*)- \[[xX]\] ", r"\1- "),                    # ticked boxes: order state; the blank "[ ]" print boxes stay (#220, a5 H-2)
        (r" — ✅ ALL \d+ ORDERED [\d-]+", ""),                    # heading status
        (r"(?m)^Exact picks \(the owner, [\d-]+\) — ✅ ALL ORDERED [\d-]+ except tablets:",
         "Exact picks:"),
        (r"(?m)^\*\*Box hardware: ~\$(\d+) ✅ ordered \(storage owned\)\. Remaining to buy: ~\$(\d+) tablets\.\*\*",
         r"**Box hardware: ~$\1 + ~$\2 tablets (storage owned).**"),
        (r"(?m)^\(Paper \+ toner: ✅ owned\.\)\n", ""),
        (r"(?m)^\*\*Remaining spend:.*\*\*\n", ""),
    ]
    for pat, rep in subs:
        text = re.sub(pat, rep, text)
    # drop any table's Status column (ordered / to buy / optional)
    out, drop = [], None
    for l in text.split("\n"):
        if l.startswith("|"):
            cells = l.strip().strip("|").split("|")
            if drop is None and "Status" in [c.strip() for c in cells]:
                drop = [c.strip() for c in cells].index("Status")
            if drop is not None and len(cells) > drop:
                del cells[drop]
                l = "|" + "|".join(cells) + "|"
        else:
            drop = None
        out.append(l)
    text = "\n".join(out)
    assert "✅" not in text, "new check-state in PURCHASE_LIST.md — extend canonical_purchases"
    return text

# ── static landing shelf grid (acceptance 2: usable JS-off) ──
# F3 (red team 10-09, #156): index_v1.html figures come from the manifest at generation time, never typed by hand.
# The page carries <!--count:KEY-->n<!--/count--> markers; a pattern with a group counts distinct groups, else matching paths.
INDEX_V1_COUNTS = {
    "survivor_pdfs": r"^docs/survivor_library/.*\.pdf$",
    "textbook_pdfs": r"^docs/school_textbooks/.*\.pdf$",
    "plant_species": r"^docs/plant_id/([^/]+)/",
    "coastal_species": r"^docs/coastal_id/([^/]+)/",
    "khan_videos": r"^video/khan_academy/.*\.mp4$",
    "mwm_regions": r"^maps/organicmaps/.*\.mwm$",
    "librivox_books": r"^audio/librivox/[^/]+/([^/]+)/",
    "mit_courses": r"^docs/mit_ocw/([^/]+)/",
}

def index_v1_counts(paths):
    out = {}
    for key, pat in INDEX_V1_COUNTS.items():
        rx = re.compile(pat)
        hits = [m for m in map(rx.search, (p for p in paths if p not in HIDDEN)) if m]   # #220 (a4 F2): title cards are not videos
        out[key] = len({m.group(1) for m in hits}) if rx.groups else len(hits)
    out["all_species"] = out["plant_species"] + out["coastal_species"]   # F4: 86 = 62 + 24
    return out

def patch_index_v1(paths, path=None):
    path = path or f"{LIB}/index_v1.html"
    src = open(path).read()
    counts = index_v1_counts(paths)
    for key, n in counts.items():
        src, k = re.subn(rf"(<!--count:{key}-->).*?(<!--/count-->)", rf"\g<1>{n:,}\g<2>", src)
        assert k >= 1, f"index_v1.html: marker count:{key} missing"
        top = re.match(r"\^([^/]+/[^/]+)/", INDEX_V1_COUNTS.get(key, ""))   # 0 is right when the folder was not fetched
        assert n > 0 or not top or not os.path.isdir(f"{LIB}/{top.group(1)}"), f"index_v1.html: {key} counted 0 (manifest pattern broken?)"
    open(path, "w").write(src)
    return counts

def patch_index(shelf_counts):
    idx_path = f"{LIB}/index.html"
    src = open(idx_path).read()
    cards, side = [], []
    # order from shelves.json — single owner of the ordering convention
    # (priority shelves first, rest alphabetical; gen_index writes it)
    order = [s["path"] for s in
             json.load(open(f"{LIB}/_app/index/shelves.json"))]
    ordered = sorted(SHELVES.items(),
                     key=lambda kv: order.index(kv[0]) if kv[0] in order else 99)
    for shelf, meta in ordered:
        count = shelf_counts.get(shelf, 0)
        if not count:
            continue
        title, desc = meta[0], meta[1]
        historical = len(meta) > 2 and meta[2]
        slug = shelf.replace("/", "_")
        href = (f"_app/historical.html?f=_app%2Fshelf%2F{slug}.html" if historical
                else "plants.html" if shelf == "docs/plant_id"  # visual view is the default (H35)
                else f"_app/shelf/{slug}.html")
        badge = ' <span class="l-badge l-badge--hist">HISTORICAL</span>' if historical else ""
        plural = "item" if count == 1 else "items"
        cards.append(f'<a class="l-shelf-card" href="{href}"><b>{esc(title)}</b>'
                     f'<span>{sumhtml(SUMMARIES.get("shelf:" + shelf, desc), "", links=False)}</span><span class="l-caption">{count:,} {plural}</span>{badge}</a>')
        side.append(f'<a href="{href}">{esc(title)}</a>')
    src = re.sub(r'(<div class="l-grid" id="shelves">).*?(</div>)',
                 lambda m: m.group(1) + "\n" + "\n".join(cards) + "\n" + m.group(2),
                 src, flags=re.S)
    src = re.sub(r'(<div class="l-shelflist" id="sidebar-shelves">).*?(</div>)',
                 lambda m: m.group(1) + "".join(side) + m.group(2),
                 src, flags=re.S)
    src = re.sub(r'(<!--ENC-->).*?(<!--/ENC-->)',
                 lambda m: m.group(1) + "\n" + enc_section() + "\n" + m.group(2),
                 src, flags=re.S)
    # FIXES #168 neighbour: the HISTORICAL card's Survivor Library figure was typed by hand (7,448 for 7,164)
    src, k = re.subn(r"(<!--count:survivor_pdfs-->).*?(<!--/count-->)",
                     rf"\g<1>{shelf_counts.get('docs/survivor_library', 0):,}\g<2>", src)
    assert k == 1, "index.html: count:survivor_pdfs marker missing"
    # a build without the Survivor Library hides the card (hidden attribute) instead of pointing at an empty shelf
    hide = "" if shelf_counts.get("docs/survivor_library") else " hidden"
    src, k = re.subn(r'(<div class="l-hazard"[^>]* id="historical-card")(?: hidden)?>', rf"\g<1>{hide}>", src)
    assert k == 1, "index.html: historical-card missing"
    open(idx_path, "w").write(src)
    es_path = f"{LIB}/es.html"   # FIXES #206 (E6): the Spanish landing page, hand-written apart from this block
    es_src, k = re.subn(r'(<!--ENC-->).*?(<!--/ENC-->)', lambda m: m.group(1) + "\n" + enc_section(es=True) + "\n" + m.group(2),
                        open(es_path).read(), flags=re.S)
    assert k == 1, "es.html: ENC markers missing"
    open(es_path, "w").write(es_src)
    return len(cards)

# H25: landing entry point to the kiwix-served ZIMs. Built from zim/*.zim so
# dated filenames survive REFRESH.md swaps; kiwix-serve names each book by
# its filename stem. Chips use /viewer#<stem> (Kiwix UI with the search box);
# /content/<stem> is the bare article, no header. app.js rewrites data-kiwix to the live
# host:port; file:// mode keeps the search.html fallback + NEEDS THE SERVER.
ZIM_NAMES = [  # (filename prefix, display name) — first match wins, list order = display order
    ("wikipedia_en_all", "Wikipedia (full English)"),
    ("wikipedia_en-simple", "Simple English Wikipedia"),
    ("wikipedia_en_medicine", "WikiMed (medical Wikipedia)"),
    ("wiktionary_en", "Wiktionary"), ("wikibooks_en", "Wikibooks"),
    ("wikisource_en", "Wikisource"), ("wikiversity_en", "Wikiversity"),
    ("wikivoyage_en", "Wikivoyage"), ("gutenberg_en", "Project Gutenberg"),
    ("ifixit_en", "iFixit repair guides"), ("appropedia_en", "Appropedia"),
    ("energypedia_en", "Energypedia"),
    ("trueprepper", "TruePrepper"), ("phet_en", "PhET simulations"),
    ("zimgit-medicine", "Medical Library"), ("zimgit-water", "Water Treatment Library"),
    ("zimgit-food-preparation", "Food Preparation Library"), ("zimgit-knots", "Knots"),
    ("zimgit-post-disaster", "Post-Disaster Library"),
    ("wikipedia_es_top", "Wikipedia en español (lo mejor)"),
    ("wikipedia_es_medicine", "Wikipedia Médica"), ("wikibooks_es", "Wikilibros"),
    ("vikidia_es", "Vikidia (niños)"), ("medlineplus.gov_es", "MedlinePlus (español)"),
    ("ted_mul_biology", "TED talks: biology"), ("ted_mul_chemistry", "TED talks: chemistry"),
    ("ted_mul_health-care", "TED talks: health care"), ("ted_mul_medicine", "TED talks: medicine"),
    ("ted_mul_physics", "TED talks: physics"),
]

def enc_section(es=False):
    """es=False: index.html, every encyclopedia except the Spanish ones (FIXES #206, E6). es=True: es.html, Spanish only."""
    zdir = f"{LIB}/zim"
    stems = sorted(f[:-4] for f in os.listdir(zdir) if f.endswith(".zim") and ("_es_" in f) == es)
    def rank(stem):
        for i, (pre, name) in enumerate(ZIM_NAMES):
            if stem.startswith(pre):
                return (i, name)
        # StackExchange sites and anything new: after the curated list
        return (len(ZIM_NAMES), humanize(stem.split("_")[0]).replace(".stackexchange.com", " StackExchange"))
    items = sorted((rank(st), st) for st in stems)
    fallback = "search.html?lang=spa" if es else "search.html"
    chips = [f'<a class="l-chip" href="{fallback}" data-kiwix="/viewer#{quote(st)}">'
             + (f"<b>{esc(r[1])}</b>" if st.startswith(("wikipedia_en_all", "wikipedia_es_top")) else esc(r[1])) + '</a>'
             for r, st in items]
    if es:
        chips.append(f'<a class="l-chip" href="{fallback}" data-kiwix="/"><b>Todas las enciclopedias →</b></a>')
        return (f'<section class="l-enc needs-enc" id="enciclopedias"><h2>Enciclopedias</h2>'
                f'<p class="l-caption">{len(stems)} enciclopedias en español, servidas por la caja Lantern. '
                f'<span class="l-badge show-direct">NECESITA EL SERVIDOR</span> Desde el disco se abren con el programa Kiwix '
                f'(<a href="tools/kiwix_desktop/">tools/kiwix_desktop/</a>) o con la aplicación Kiwix para Android '
                f'(<a href="tools/android/">tools/android/</a>); los archivos están en <a href="zim/">zim/</a>.</p>'
                f'<div class="l-enc-list">' + "\n".join(chips) + '</div></section>')
    chips.append('<a class="l-chip" href="search.html" data-kiwix="/"><b>All encyclopedias →</b></a>')
    return (f'<section class="l-enc needs-enc" id="encyclopedias"><h2>Encyclopedias</h2>'
            f'<p class="l-caption">Offline Wikipedia (full English, 2026) and {len(stems) - 1} more reference sets, '
            f'served by the Lantern box. <span class="l-badge show-direct">NEEDS THE SERVER</span></p>'
            f'<div class="l-enc-list">' + "\n".join(chips) + '</div></section>')

def main():
    stale = stale_lookalikes()
    if stale:   # FIXES #217: never write a shelf page whose summary drops a lookalike the species README names
        raise SystemExit("gen_shelves: species summaries in data/summaries.json leave out lookalikes their README "
                         "names (regenerate them from the notes):\n" + "\n".join(f"  {k}: {', '.join(m)}" for k, m in stale))
    os.makedirs(OUT, exist_ok=True)
    paths = load_paths()
    by_shelf = {}
    for p in paths:
        shelf = shelf_of(p)
        if not shelf:
            continue
        base = os.path.basename(p)
        if base.startswith(".") or base.endswith((".part", ".tmp")):
            continue
        full = f"{LIB}/{p}"
        try:
            size = os.path.getsize(full)
        except OSError:
            print(f"WARN missing on disk: {p}", file=sys.stderr)
            continue
        by_shelf.setdefault(shelf, []).append((p, size))
    CURRENCY.update(medical_currency(by_shelf))
    gen_known_gaps()
    counts = {}
    for shelf, meta in SHELVES.items():
        files = by_shelf.get(shelf, [])
        slug, n = gen_shelf(shelf, meta, files)
        counts[shelf] = n
        print(f"{slug}.html {n}")
    print(f"es_docs.html {gen_es_docs()} Spanish documents off the English shelves")
    stamp_chrome()
    print(f"video.html {stamp_video_groups()} group headings")
    gen_allowed()
    # runbook links are written relative to the library root; the page lives in _app/
    gen_md_page(f"{LIB}/RUNBOOK.md", "runbook.html", "Operator runbook",
                transform=lambda t: re.sub(r"\]\((?!https?://|#|\.\./|ref:)", "](../", t))
    gen_md_page(f"{LIB}/SKILLS_CHECKLIST.md", "skills.html", "Skills checklist")
    gen_md_page(f"{LIB}/BINDER_1_TOC.md", "binder1_toc.html", "Binder 1 contents",
                transform=lambda t: re.sub(r"\]\((?!https?://|#|\.\./|ref:)", "](../", t))
    gen_md_page(f"{BASE}/data/library_notes/tools/video_players/README.md", "video_players.html", "Disc image & video players")
    gen_md_page(f"{LIB}/PURCHASE_LIST.md", "purchases.html", "Purchases & print plan",
                transform=lambda t: re.sub(r"\]\((?!https?://|#|\.\./|ref:)", "](../", canonical_purchases(t)))
    # 10-03: the external presentation guide is the About page; \$ escapes are for his md viewer only
    gen_md_page(f"{BASE}/docs/LANTERN_GUIDE.md", "about.html", "About Lantern", transform=lambda t: t.replace("\\$", "$"))
    print(f"{gen_md_siblings()} .md rendered to sibling .html")
    n = patch_index(counts)
    print(f"runbook.html skills.html + index.html static grid ({n} cards)")
    print("index_v1.html counts", patch_index_v1(paths))
    if MISSING_SUMMARIES:
        print(f"WARNING {len(MISSING_SUMMARIES)} groups have no one-line description (add to data/summaries.json): "
              + " ".join(MISSING_SUMMARIES))

if __name__ == "__main__":
    main()
