#!/usr/bin/env python3
"""Resolve named link references at build time (one table: data/refs.json).

Source forms:
  HTML      <a data-ref="KEY">text</a>
  markdown  [text](ref:KEY)   -> md_render emits href="ref:KEY", resolved here
Keys:
  wikimed:Article Title   -> live WikiMed article via data-kiwix (search.html fallback)
  wikimed_es:Título        -> same, Spanish ZIM
  zim:water               -> ZIM landing (/viewer#<stem>) via data-kiwix
  <doc key>               -> href from refs.json; optional pdf appended as " (PDF)"
An unknown key raises. A known key whose target is not on disk (content this build did not fetch) becomes plain
text with a warning on stderr, so a partial library builds without dead links.
"""
import glob
import html
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.abspath(os.path.join(HERE, "..", "library"))
from gen_index import HIST_SHELVES as HIST  # one source for the historical gate
REFS = json.load(open(os.path.join(HERE, "..", "data", "refs.json")))

_ATTR = re.compile(r'<a\s+data-ref="([^"]+)"([^>]*)>(.*?)</a>', re.S)
_CODE = re.compile(r"<code>([A-Za-z0-9_][A-Za-z0-9_./ -]{2,200})</code>")   # backticked path -> link when on disk
_HREF = re.compile(r'<a\s+href="ref:([^"]+)"([^>]*)>(.*?)</a>', re.S)


class NotFetched(Exception):
    """a known ref whose content is not in this library"""


def shelf_of(rel):
    """The content folder holding library-relative path rel: the first two parts (docs/medical, mirrors/hesperian,
    tools/argos/), or the first for a file at the second level (tools/suncalc.html, zim/x.zim)."""
    parts = rel.strip("/").split("/")
    return "/".join(parts[:1] if len(parts) == 2 and "." in parts[1] else parts[:2])


def shelf_fetched(rel):
    """Was rel's content folder fetched? A missing file in a fetched folder is breakage, not a partial library."""
    return os.path.isdir(os.path.join(LIB, shelf_of(rel)))


def zim_stem(key):
    prefix = REFS["zims"][key]
    hits = sorted(glob.glob(os.path.join(LIB, "zim", prefix + "*.zim")))
    if not hits:
        raise NotFetched(f"no ZIM on disk for {key} ({prefix}*)")
    return os.path.basename(hits[-1])[:-4]


def resolve_one(key, root, text, extra="", after=""):
    try:
        return _resolve_one(key, root, text, extra, after)
    except NotFetched as e:
        print(f"WARN refs: {key}: {e}; written as plain text", file=sys.stderr)
        return text


def _resolve_one(key, root, text, extra="", after=""):
    """after = markup following the anchor; a hand page (triage_v1) may already carry the fallback href and the (PDF) link."""
    key = html.unescape(key)
    extra = re.sub(r'\s+(?:href|data-kiwix)="[^"]*"', "", extra)   # we emit these; drop the hand-written copies
    kind, _, arg = key.partition(":")
    if kind in ("wikimed", "wikimed_es", "zim") and arg and "data-server" not in extra:
        extra += ' title="Needs the server" data-server="1"'   # fix #98: these open the kiwix server, search.html is the no-server fallback
    if kind in ("wikimed", "wikimed_es") and arg:
        stem = zim_stem(kind)
        art = urllib.parse.quote(arg.strip().replace(" ", "_"), safe="_(),'")
        fb = f'{root}search.html?q={urllib.parse.quote(arg.strip())}'
        return f'<a href="{fb}" data-kiwix="/content/{stem}/{art}"{extra}>{text}</a>'
    if kind == "zim" and arg:
        return f'<a href="{root}search.html" data-kiwix="/viewer#{zim_stem(arg)}"{extra}>{text}</a>'
    d = REFS["docs"].get(key)
    if d is None:
        raise KeyError(f"refs: unknown key {key!r}")
    have = {}
    for p in (d["href"], d.get("pdf")):
        if p:
            rel = urllib.parse.unquote(p.split("#")[0])
            have[p] = os.path.exists(os.path.join(LIB, rel))
            if not have[p] and shelf_fetched(rel):
                raise FileNotFoundError(f"refs: {key} -> {p} not on disk")
    if not have[d["href"]]:
        raise NotFetched(f"{d['href']} not fetched")
    out = f'<a href="{root}{html.escape(d["href"])}"{extra}>{text}</a>'
    if d.get("pdf") and have[d["pdf"]] and html.escape(d["pdf"]) not in after:
        out += f' (<a href="{root}{html.escape(d["pdf"])}">PDF</a>)'
    return out


def resolve(markup, root=""):
    """root = path prefix from the output page back to library/ ('' , '../', '../../')."""
    markup = _ATTR.sub(lambda m: resolve_one(m.group(1), root, m.group(3), m.group(2), markup[m.end():m.end() + 160]), markup)
    markup = _HREF.sub(lambda m: resolve_one(m.group(1), root, m.group(3), m.group(2)), markup)
    def code_link(m):
        path = html.unescape(m.group(1)).rstrip("/")
        # historical shelves only via the interstitial (verify_frontend invariant 3): leave those unlinked
        if "/" in m.group(1) and not path.startswith(HIST) and os.path.exists(os.path.join(LIB, path)):
            return f'<a href="{root}{html.escape(path)}{"/" if os.path.isdir(os.path.join(LIB, path)) else ""}">{m.group(0)}</a>'
        return m.group(0)
    return _CODE.sub(code_link, markup)


if __name__ == "__main__":
    # the not-fetched rule (no content needed); the checks after it need the reference library
    for rel, shelf in [("tools/android", "tools/android"), ("tools/android/", "tools/android"), ("tools/suncalc.html", "tools"),
                       ("zim/x.zim", "zim"), ("docs/medical/a.pdf", "docs/medical"), ("mirrors/hesperian/en/x.html", "mirrors/hesperian")]:
        assert shelf_of(rel) == shelf, (rel, shelf_of(rel))
    # self-check: every doc key resolves, every zim key finds a file, the three forms render
    for k in REFS["docs"]:
        resolve_one(k, "", "x")
    for k in REFS["zims"]:
        zim_stem(k)
    s = resolve('<a data-ref="wikimed:Heat stroke">Heat stroke</a> [x](ref:wtnd_burns)'.replace("[x](ref:wtnd_burns)", '<a href="ref:wtnd_burns">burns</a>'), "../")
    assert 'data-kiwix="/content/wikipedia_en_medicine' in s and "/Heat_stroke" in s and 'href="../search.html?q=Heat%20stroke"' in s, s
    c = resolve("<code>tools/models</code> <code>nope/x.pdf</code> <code>docs/HISTORICAL/</code> <code>docs/medical/fm_4-25.11_first_aid.pdf</code>", "../")
    assert c.count("<a ") == 2 and 'href="../tools/models/"' in c and "nope" in c and "<a " not in c.split("nope")[0][-10:], c
    assert 'Burns.html"' in s and "(PDF)" not in s and 'PDF</a>)' in s, s
    t = resolve('<a data-ref="wtnd_burns" href="old" data-kiwix="old">b</a> (<a href="docs/medical/hesperian_where_there_is_no_doctor/en_nwtnd_2014_03g.pdf">PDF</a>)')
    assert t.count("href=") == 2 and t.count("PDF") == 1 and "old" not in t, t
    print(f"refs ok: {len(REFS['docs'])} docs, {len(REFS['zims'])} zims")
