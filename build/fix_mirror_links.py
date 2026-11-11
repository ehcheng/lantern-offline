#!/usr/bin/env python3
"""Rewrite root-absolute href/src links in wget mirrors to relative paths.

usage: fix_mirror_links.py [--dry-run] [--backup DIR] [--strip-external] [--repair] [--stubs --keep FILE] [--offline-chrome]
                           [--exact-case] [--scrub] [--dedupe-pdf] [--unhtml-media] [--dedupe-query] [--report FILE]
                           [--only FILE] MIRROR_DIR...
  --only FILE (round 10): --offline-chrome and --scrub touch only the pages listed (absolute paths, one per line); a fix
  row writes its named pages and the orchestrator runs the full pass at the regen.

POST-CRAWL ORDER (run WITHOUT the sandbox after every wget fetch or re-crawl, per mirror, each with --backup):
  1. python3 build/prune_mirrors.py <mirror>                        (allow-list prune; E7, #107 --list)
  2. python3 build/fix_mirror_links.py --strip-external --repair library/mirrors/<mirror>
  3. python3 build/fix_mirror_links.py --unhtml-media --dedupe-pdf library/mirrors/<mirror>
  4. python3 build/fix_mirror_links.py --stubs --keep <outside-linked list> library/mirrors/<mirror>
  5. python3 build/fix_mirror_links.py --offline-chrome --report FILE library/mirrors/<mirror>
     (hesperian, nchfp; D12 #187: wiki-skin chrome out, breadcrumb redlinks to the cover, external links marked;
     #197: chapter-list dialog -> <details>, a meta refresh to another site (sheldonbrown bbpress) -> a marked link,
     /hhg/ root links resolved, HealthWiki search box, org-site (E3) chrome and trackers out, pictures still online-only
     marked; run it again after the E2 image fetch + --repair; red team 10-16 K7 #208: phone-width style, unstyled wiki
     leftovers, frozen carousels, buy buttons, store links to books on the box, dead scripts, live-wiki forms;
     red team 10-20 #218 #216: picture tables stack on a phone, cell padding / gutters / indents fit a phone, wide floats
     stop floating, the dengue notes, Spanish book links to local covers, the feedback button, Spanish drug cautions;
     red team 10-27 #262 #274: a zoomed drawing keeps its margin and its placed labels are fitted again after the margin and
     zoom passes (dental instrument lists at -25 to -51 px), right-to-left overflow, labels keep whole words, fragment
     anchors found or dropped, wiki markup and English leftovers on Spanish pages, wiki "Page|label" links and org PDFs local)
  5b. python3 build/fix_mirror_links.py --exact-case --report FILE library/mirrors/<mirror>
     (#197: links that only match on the case-insensitive Mac point at the exact on-disk name, for the Linux Pi)
  5c. python3 build/fix_mirror_links.py --scrub --report FILE library/mirrors/<mirror>   (every mirror)
     (red team 10-25 #122: inline scripts that inject trackers at run time, tracker-only local script files and
     <noscript> tracker pixels out; same-site URLs in inline scripts local; the .gov banner's <title>Lock</title> out;
     red team 10-27 #274 #272: live-site forms out (search boxes become the library search), shop/cart/donate links marked,
     NCHFP's repeated tab and order boxes and Ready.gov's banner/header/menu/footer data-pagefind-ignore;
     check: the private test record, 0 remote requests in Chromium)
  6. python3 tests/t8_mirror_entry.py   (after the mcp.db/embeddings rebuild: expect 0 FAIL)
  7. python3 -I build/fix_l7_narrow.py OUT.jsonl library/mirrors/hesperian/<es|en>.hesperian.org/hhg --check
     (red team 10-20 #218 render check, no sandbox: exit 1 when any article text run is under 3 em, about 6 characters, a line on a
     390 px phone, or any run of 3 or fewer characters a line with a mid-word break (round 9 #248, placed labels too since
     round 10), or any text or placed label left of 0 or past 390 px (round 10 #262, off_fail); expect 0;
     the same check over both trees: T=<name> bash build/narrow_gate.sh)
  Every step is idempotent; a second run changes 0 files.

  MIRROR_DIR holds one subdir per host (e.g. mirrors/hesperian/en.hesperian.org).
  For each .html/.htm under a host dir, every href/src="/X" (not "//") is
  resolved under that host dir as X, X.html, X/index.html, X/index.htm
  (raw and URL-decoded). Resolvable -> relative path (+fragment, query dropped).
  Unresolvable -> untouched. Idempotent: rewritten links no longer start with "/".
  --strip-external: after rewriting, drop every <link> and <script src> tag whose URL
  still leaves the mirror (http(s):// or //host) or hits MediaWiki load.php. Offline
  those only fail silently (font-awesome, analytics, resource loader) and a page
  that requests them cannot pass the T8 no-request-leaves-file:// check.
  An <img> whose src points at another host of the same mirror (pool.hesperian.org
  from en.hesperian.org) is relativised when the file is on disk; otherwise its
  src/srcset become data-src/data-srcset (no request, alt text shows, the URL is
  kept so a later image fetch can restore it). Dropped URLs are appended to
  logs/audit/missing_<mirror>_images.txt.
  --repair (FIXES #104): undo the data-data-src double pass; drop MediaWiki <link> head tags whose root-absolute href
  is not on disk (opensearch_desc.php, the Atom feed, the favicon); decode Cloudflare-obfuscated e-mail (/cdn-cgi/l/email-protection
  links and __cf_email__ spans) into plain mailto:; put an <img> data-src back to src when the image is now on disk.
  --stubs (FIXES #105, #157): a page that is only a meta-refresh (the <title> is not visible text) redirects to a local
  relative URL when the target (followed through chained stubs) is in the mirror, and gains a visible link; otherwise
  it is deleted unless a path in --keep FILE (one library path per line: what Lantern/index_v1/triage/refs/MCP link) names it.
  --dedupe-query (red team 10-09, b2): X?utm_source=...html / X?_gl=...html saved beside X.html with the same <title> is
  a tracking-URL copy: deleted, every link to it points at X.html.
  Cross-host links (FIXES #149): href/src to another host dir of the same mirror (en.hesperian.org -> es.hesperian.org)
  become relative when the target is on disk; an <a> whose target section is mirrored but the page is not gets
  " (not mirrored)" appended to its text.
  --dedupe-pdf (FIXES #107): an .html that is a PDF byte-identical to a .pdf in the same mirror is deleted and every
  link to it (or its folder) points at the .pdf.
  --unhtml-media (FIXES #113): an image saved under .html (wget --adjust-extension) is renamed to its real extension
  and every link follows. Run it after each crawl, with the other post-crawl steps.
  --backup DIR: copy every file before it is changed or deleted to DIR/<path> (same relative path).
"""
import hashlib
import html as htmlmod
import os
import re
import shutil
import sys
import unicodedata
from collections import Counter
from urllib.parse import quote, unquote

LINK = re.compile(r'(href|src)=(["\'])(/[^"\'>]*|https?://[^/"\'>]+/[^"\'>]*)\2', re.I)
# FIXES #18: wget --convert-links left links to never-fetched pages as absolute
# https://<host>/X; after the recrawl those resolve too, so same-host absolute
# URLs are rewritten like root-absolute ones. Other hosts stay untouched.
# ponytail: regex over raw HTML, not a parser; fine for wget output, skips srcset.
EXT_TAG = re.compile(r'<link\b[^>]*\bhref=(["\'])(?:https?:)?//[^"\']*\1[^>]*>|'
                     r'<script\b[^>]*\bsrc=(["\'])(?:https?:)?//[^"\']*\2[^>]*>\s*</script>|'
                     r'<link\b[^>]*\bhref=(["\'])[^"\']*load\.php[^"\']*\3[^>]*>|'
                     r'<script\b[^>]*\bsrc=(["\'])[^"\']*load\.php[^"\']*\4[^>]*>\s*</script>', re.I | re.S)


def resolve(host, path):
    """Return absolute file path for site-root path, or None."""
    base = path.split("#", 1)[0].split("?", 1)[0]
    for p in dict.fromkeys((base, unquote(base))):
        for cand in (p, p + ".html", p + "/index.html", p + "/index.htm"):
            f = os.path.normpath(os.path.join(host, cand.lstrip("/")))
            if os.path.isfile(f):
                return f
    return None


def materialize_variants(host, dry, stats):
    """FIXES #122: wget keeps the query in the file name (css_X.css?delta=2&language=ar...) and pages of another
    language ask for css_X.css?delta=2&language=en, which is not on disk. A Drupal css/js aggregate is named by its
    content hash, so every query variant of css_X.css is the same file: give it its plain name once (nginx types a
    plain .css as text/css; a 'X.css?...' name has no extension it knows) and the links resolve to that."""
    for root, _, files in os.walk(host):
        have = set(files)
        for name in sorted(files):
            base = name.split("?", 1)[0]
            if "?" in name and base.lower().endswith((".css", ".js")) and base not in have:
                have.add(base); stats["variant_materialized"] += 1
                if not dry:
                    shutil.copy2(os.path.join(root, name), os.path.join(root, base))
                    if CREATED is not None:
                        CREATED.append(os.path.join(root, base))


IMG = re.compile(r'<img\b[^>]*>', re.I | re.S)
IMG_SRC = re.compile(r'(?<![-\w])(src|srcset)=(["\'])((?:https?:)?//[^"\']*)\2', re.I)  # not data-src: idempotent


def fix_img(tag, mirror, here, stats):
    def sub(m):
        attr, q, url = m.groups()
        if attr.lower() == "src":
            hostname = url.split("/")[2]; rest = url.split("/", 3)[3] if url.count("/") >= 3 else ""
            target = resolve(os.path.join(mirror, hostname), "/" + rest) if os.path.isdir(os.path.join(mirror, hostname)) else None
            if target:
                stats["img_local"] += 1
                return f"{attr}={q}{quote(os.path.relpath(target, here), safe='/')}{q}"
            stats["img_missing"][url.split("?", 1)[0]] += 1
        return f"data-{attr}={q}{url}{q}"
    return IMG_SRC.sub(sub, tag)


BACKUP = None
CREATED = []   # files this run adds (materialized css/js), for the changed-paths list


def backup(fpath):
    if BACKUP:
        dst = os.path.join(BACKUP, os.path.relpath(os.path.abspath(fpath), REPO))
        if not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(fpath, dst)


REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DATADATA = re.compile(r'\bdata-(?:data-)+(src|srcset)=', re.I)
HEAD_LINK = re.compile(r'<link\b[^>]*\bhref=(["\'])(/(?:w/|hesp_fav)[^"\']*)\1[^>]*>', re.I)   # MediaWiki head links
CF_A_TEXT = re.compile(r'(<a\b[^>]*\bdata-cfemail="([0-9a-fA-F]+)"[^>]*>)\[email(?:&#160;|&nbsp;|\s)protected\]', re.I)
CF_SPAN = re.compile(r'<span class="__cf_email__" data-cfemail="([0-9a-fA-F]+)">\[email(?:&#160;|&nbsp;|\s)protected\]</span>', re.I)
CF_A = re.compile(r'<a\b[^>]*\bhref=(["\'])[^"\']*/cdn-cgi/l/email-protection(?:#([0-9a-fA-F]+))?\1[^>]*>', re.I)
DATA_SRC_REL = re.compile(r'(?<![-\w])data-src=(["\'])(?!\s*(?:https?:)?//)([^"\']+)\1', re.I)
DATA_SRC = re.compile(r'(?<![-\w])data-src=(["\'])((?:https?:)?//[^"\']*)\1', re.I)


# pages the origin served from another site under a mirrored URL (ready.gov/cert -> fema.gov): their root-absolute
# links mean that site, so unresolvable ones become absolute links to it instead of dead library.lan paths
FOREIGN = {"| FEMA.gov": "https://www.fema.gov"}
ROOT_HREF = re.compile(r'(<a\b[^>]*\shref=)(["\'])(/[^/"\'][^"\']*)\2', re.I)


def cf_decode(h):
    """Cloudflare email obfuscation: first byte is the XOR key for the rest"""
    k = int(h[:2], 16)
    return "".join(chr(int(h[i:i + 2], 16) ^ k) for i in range(2, len(h), 2))


def repair(text, host, here, stats):
    text, n = DATADATA.subn(r"data-\1=", text); stats["datadata"] += n
    title = re.search(r"<title>([^<]*)</title>", text, re.I)
    site = next((v for k, v in FOREIGN.items() if title and title.group(1).strip().endswith(k)), None)
    if site:
        def foreign(m):
            if resolve(host, m.group(3)): return m.group(0)
            stats["foreign_abs"] += 1; return f"{m.group(1)}{m.group(2)}{site}{m.group(3)}{m.group(2)}"
        text = ROOT_HREF.sub(foreign, text)
    def head(m):
        if resolve(host, m.group(2)): return m.group(0)
        stats["head_links_dropped"] += 1; return ""
    text = HEAD_LINK.sub(head, text)
    def a_text(m):
        stats["cf_text"] += 1; return m.group(1) + htmlmod.escape(cf_decode(m.group(2)))
    text = CF_A_TEXT.sub(a_text, text)
    def span(m):
        stats["cf_text"] += 1; return htmlmod.escape(cf_decode(m.group(1)))
    text = CF_SPAN.sub(span, text)
    def a(m):
        tag, hexed = m.group(0), m.group(2) or (re.search(r'data-cfemail="([0-9a-fA-F]+)"', m.group(0)) or [None, None])[1]
        if not hexed: return tag
        stats["cf_href"] += 1
        tag = re.sub(r'\bhref=(["\'])[^"\']*\1', 'href="mailto:%s"' % htmlmod.escape(cf_decode(hexed)), tag, count=1)
        return re.sub(r'\s(?:class="__cf_email__"|data-cfemail="[0-9a-fA-F]+")', "", tag)
    text = CF_A.sub(a, text)
    def img(m):
        url = m.group(2); hostname = url.split("/")[2]; rest = url.split("/", 3)[3] if url.count("/") >= 3 else ""
        mirror = os.path.dirname(host)
        t = resolve(os.path.join(mirror, hostname), "/" + rest) if os.path.isdir(os.path.join(mirror, hostname)) else None
        if not t: return m.group(0)
        stats["img_restored"] += 1
        return f'src={m.group(1)}{quote(os.path.relpath(t, here), safe="/")}{m.group(1)}'
    text = IMG.sub(lambda m: m.group(0) if IMG_SRC.search(m.group(0)) else DATA_SRC.sub(img, m.group(0)), text)
    # #197: the LINK pass above also relativises a kept data-src once its picture is on disk (LINK has no lookbehind);
    # such an <img> with no src gets its src back here
    def img_rel(m):
        tag = m.group(0)
        d = DATA_SRC_REL.search(tag)
        if re.search(r'(?<![-\w])src=', tag) or not d or not os.path.isfile(
                os.path.normpath(os.path.join(here, unquote(htmlmod.unescape(d.group(2)).split("?", 1)[0])))):
            return tag
        stats["img_restored"] += 1
        return tag[:d.start()] + f"src={d.group(1)}{d.group(2)}{d.group(1)}" + tag[d.end():]
    text = IMG.sub(img_rel, text)
    # #197: a picture that is local again loses its "needs internet" mark (mark_offline_img, --offline-chrome)
    text, n = IMG_BACK.subn(r"\1", text); stats["img_mark_removed"] += n
    return text


IMG_BACK = re.compile(r'(<img\b(?:"[^"]*"|\'[^\']*\'|[^>"\'])*?(?<![-\w])src=(["\'])\s*[^"\'\s][^"\']*\2(?:"[^"]*"|\'[^\']*\'|[^>"\'])*>)'
                      r'<span class="library-note img-offline">[^<]*</span>', re.I)


# FIXES #122: nothing a page LOADS may leave the box (t8_plain browser, file:// with JS off). Ordinary <a href> stays.
_V = r"(?:\"[^\"]*\"|'[^']*'|[^\s>\"']+)"
OFF = re.compile(r"^\s*(?:https?:)?//", re.I)
SCRIPT_OFF = re.compile(r"<script\b(?:\"[^\"]*\"|'[^']*'|[^>\"'])*?(?<![-\w])src\s*=\s*"
                        r"(?:\"\s*(?:https?:)?//[^\"]*\"|'\s*(?:https?:)?//[^']*'|(?:https?:)?//[^\s>]*)"
                        r"(?:\"[^\"]*\"|'[^']*'|[^>\"'])*>.*?</script\s*>", re.I | re.S)
SUBRES_TAG = re.compile(r"<(link|img|source|iframe|frame|embed|video|audio|input|object|track|body|table|td|th|tr)\b"
                        r"((?:\"[^\"]*\"|'[^']*'|[^>\"'])*)>", re.I)
SUBRES_ATTR = re.compile(r"(?<![-\w])(src|srcset|data|poster|background|href)(\s*=\s*)(" + _V + ")", re.I)
LOAD_REL = re.compile(r"stylesheet|preload|prefetch|preconnect|dns-prefetch|icon|manifest|image_src|mask-icon", re.I)
CSS_IMPORT_OFF = re.compile(r"@import\s+(?:url\(\s*)?[\"']?\s*(?:https?:)?//[^;]*;?", re.I)
CSS_URL_OFF = re.compile(r"url\(\s*(?:&quot;|[\"'])?\s*(?:https?:)?//[^)]*\)", re.I)
STYLE_BLOCK = re.compile(r"(<style\b[^>]*>)(.*?)(</style\s*>)", re.I | re.S)
SCRIPT_BLOCK = re.compile(r"(<script\b[^>]*>)(.*?)(</script\s*>)", re.I | re.S)
STYLE_ATTR = re.compile(r"(?<![-\w])(style\s*=\s*)(\"[^\"]*\"|'[^']*')", re.I)


def unq(v):
    return v[1:-1] if v[:1] in "\"'" and v[-1:] == v[:1] else v


def same_mirror(mirror, here, url):
    """relative path to url's file when url's host is another host dir of this mirror and the file is on disk"""
    m = re.match(r"\s*(?:https?:)?//([^/\s\"')]+)(/[^\s\"')]*)?", url)
    if not m or not mirror or not os.path.isdir(os.path.join(mirror, m.group(1))):
        return None
    t = resolve(os.path.join(mirror, m.group(1)), m.group(2) or "/")
    return quote(os.path.relpath(t, here), safe="/") if t else None


CSS_URL_ROOT = re.compile(r"url\(\s*(&quot;|[\"'])?\s*(/(?!/)[^)\"'&]*)(?:&quot;|[\"'])?\s*\)", re.I)
QREF = re.compile(r"((?:href|src)\s*=\s*)([\"'])([^\"':]*?\.(?:css|js))((?:%3F|\?)[^\"']*)\2", re.I)


def plain_ref(text, here, stats):
    """FIXES #122b: a local css/js ref with a query in its file name (bootstrap.js%3Fdigest=...) points at the plain
    name when that file is on disk with the same bytes; Chrome on file:// does not open the %3F form"""
    def sub(m):
        plain = os.path.normpath(os.path.join(here, unquote(m.group(3))))
        varf = os.path.normpath(os.path.join(here, unquote(htmlmod.unescape(m.group(3) + m.group(4)))))
        if not (os.path.isfile(plain) and os.path.isfile(varf)) or open(plain, "rb").read() != open(varf, "rb").read():
            return m.group(0)
        stats["qref_plain"] += 1
        return f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(2)}"
    return QREF.sub(sub, text)


def css_strip(css, stats, mirror=None, here=None, host=None):
    css, n = CSS_IMPORT_OFF.subn("", css); stats["css_import_dropped"] += n
    if host and here:   # FIXES #122b: url(/profiles/...) in a mirror css means the site root, not file:///
        def root(m):
            t = resolve(host, m.group(2))
            if not t:
                return m.group(0)
            stats["css_url_root_local"] += 1
            return f"url({quote(os.path.relpath(t, here), safe='/')})"
        css = CSS_URL_ROOT.sub(root, css)
    def url(m):
        inner = re.sub(r"^url\(\s*(?:&quot;|[\"'])?|(?:&quot;|[\"'])?\s*\)$", "", m.group(0))
        rel = same_mirror(mirror, here, htmlmod.unescape(inner))
        if rel:
            stats["css_url_local"] += 1; return f"url({rel})"
        stats["css_url_dropped"] += 1; return "none"
    return CSS_URL_OFF.sub(url, css)


def local_missing(host, here, url):
    u = htmlmod.unescape(url).split("#", 1)[0]
    if not u or OFF.match(u) or re.match(r"[a-z]+:", u, re.I):
        return False
    if u.startswith("/"):
        return resolve(host, u) is None
    f = os.path.normpath(os.path.join(here, unquote(u)))
    return not (os.path.isfile(f) or os.path.isfile(f.split("?", 1)[0]))


def strip_subresources(text, host, here, stats):
    text, n = SCRIPT_OFF.subn("", text); stats["script_dropped"] += n
    mirror = os.path.dirname(host)
    def tag(m):
        name, attrs = m.group(1).lower(), m.group(2)
        if name == "link":
            href = next((unq(v) for a, _, v in SUBRES_ATTR.findall(attrs) if a.lower() == "href"), "")
            rel = re.search(r"(?<![-\w])rel\s*=\s*(" + _V + ")", attrs, re.I)
            if href and OFF.match(href):
                stats["link_dropped"] += 1; return ""
            # a script preload is only a hint (the <script> tag still loads it); with JS off Chrome refuses it
            # (requestfailed 'csp'), so it reads as a missing sub-resource on every no-script open
            if rel and re.fullmatch(r"\s*preload\s*", unq(rel.group(1)), re.I) and re.search(r"(?<![-\w])as\s*=\s*[\"']?script\b", attrs, re.I):
                stats["script_preload_dropped"] += 1; return ""
            if href and rel and LOAD_REL.search(unq(rel.group(1))) and local_missing(host, here, href):
                stats["link_missing_dropped"] += 1; return ""
            return m.group(0)
        def attr(a):
            k, eq, v = a.groups()
            kl, val = k.lower(), unq(v)
            if kl == "href" or not (OFF.match(val) or (kl == "srcset" and re.search(r"(?:^|,)\s*(?:https?:)?//", val))):
                return a.group(0)
            if name == "img" and kl == "src":
                hostname = re.sub(r"^\s*(?:https?:)?//", "", val).split("/")[0]
                rest = re.sub(r"^\s*(?:https?:)?//[^/]*", "", val)
                t = resolve(os.path.join(mirror, hostname), rest or "/") if os.path.isdir(os.path.join(mirror, hostname)) else None
                if t:
                    stats["img_local"] += 1
                    return f'{k}{eq}"{quote(os.path.relpath(t, here), safe="/")}"'
            stats["subres_disabled"] += 1
            return f"data-{k}{eq}{v}"
        new = SUBRES_ATTR.sub(attr, attrs)
        return m.group(0) if new == attrs else f"<{m.group(1)}{new}>"
    text = SUBRES_TAG.sub(tag, text)
    text = plain_ref(text, here, stats)
    text = STYLE_BLOCK.sub(lambda m: m.group(1) + css_strip(m.group(2), stats, mirror, here, host) + m.group(3), text)
    # #122 residual: a Blogger template config inside <script> carries url(//www.blogblog.com/...) strings
    text = SCRIPT_BLOCK.sub(lambda m: m.group(1) + CSS_URL_OFF.sub(lambda u: stats.__setitem__("css_url_dropped", stats["css_url_dropped"] + 1) or "none", m.group(2)) + m.group(3), text)
    return STYLE_ATTR.sub(lambda m: m.group(1) + css_strip(m.group(2), stats, mirror, here, host), text)


def fix_css(fpath, mirror, stats, dry):
    s = open(fpath, "rb").read().decode("utf-8", "surrogateescape")
    rel = os.path.relpath(fpath, mirror).split(os.sep)
    new = css_strip(s, stats, mirror, os.path.dirname(fpath), os.path.join(mirror, rel[0]) if len(rel) > 1 else None)
    if new != s:
        stats["css_files_written"] += 1
        if not dry:
            backup(fpath); open(fpath, "wb").write(new.encode("utf-8", "surrogateescape"))


def fix_file(host, fpath, stats, dry, strip=False, rep=False):
    raw = open(fpath, "rb").read()
    text = raw.decode("utf-8", "surrogateescape")
    here = os.path.dirname(fpath)

    def sub(m):
        attr, q, url = m.groups()
        if url.startswith("//"):
            return m.group(0)
        if url.startswith(("http://", "https://")):
            hostname, rest = url.split("/")[2], (url.split("/", 3)[3] if url.count("/") >= 3 else "")
            if hostname != os.path.basename(host):
                other = os.path.join(os.path.dirname(host), hostname)   # FIXES #149: sister host of this mirror
                if not os.path.isdir(other):   # #180 (b2 F1): es.dev.hesperian.org is the staging copy of es.hesperian.org
                    other = os.path.join(os.path.dirname(host), hostname.replace(".dev.", ".", 1))
                if not os.path.isdir(other):
                    return m.group(0)
                t = resolve(other, "/" + rest)
                if not t:
                    stats["xhost_unresolved"] += 1; return m.group(0)
                stats["xhost_resolved"] += 1
                frag = "#" + rest.split("#", 1)[1] if "#" in rest else ""
                return f"{attr}={q}{quote(os.path.relpath(t, here), safe='/')}{frag}{q}"
            url = "/" + rest
        stats["links"] += 1
        target = resolve(host, url)
        if not target:
            stats["unresolved"][url.split("#", 1)[0].split("?", 1)[0]] += 1
            return m.group(0)
        stats["resolved"] += 1
        frag = "#" + url.split("#", 1)[1] if "#" in url else ""
        rel = quote(os.path.relpath(target, here), safe="/")
        return f"{attr}={q}{rel}{frag}{q}"

    new = LINK.sub(sub, text)
    new = mark_not_mirrored(new, host, here, stats)
    if strip:
        new, n = EXT_TAG.subn("", new)
        stats["stripped"] += n
        new = IMG.sub(lambda m: fix_img(m.group(0), os.path.dirname(host), here, stats) if IMG_SRC.search(m.group(0)) else m.group(0), new)
        new = strip_subresources(new, host, here, stats)
    if rep:
        new = repair(new, host, here, stats)
    if new != text and not dry:
        backup(fpath)
        open(fpath, "wb").write(new.encode("utf-8", "surrogateescape"))
        stats["written"] += 1


XHOST_A = re.compile(r'(<a\b[^>]*\bhref=(["\'])https?://([^/"\']+)/([^"\'#?]*)[^"\']*\2[^>]*>)(.*?)(</a>)', re.I | re.S)
NOT_MIRRORED = " (not mirrored)"
# round 9 b2 N4: on a Spanish page the mark is Spanish; the same words as ES_MARK (the link opens the live site), which
# every link checker already reads as a mark
NOT_MIRRORED_ES = " (sitio web: necesita internet)"


def mark_not_mirrored(text, host, here, stats):
    """FIXES #149: an <a> from a page in section S (hhg) to the same section on a sister host of this mirror, i.e. a
    language switch, whose target page is not on disk (es.hesperian.org/hhg/Especial:Categorías) says so in its text.
    Nav links to other sections (hesperian.org/blog/) are left alone. Idempotent. Links the LINK pass resolved are
    relative by now, so only unresolvable ones are still absolute here."""
    mirror = os.path.dirname(host)
    section = os.path.relpath(here, host).split(os.sep)[0]
    domain = "." + ".".join(os.path.basename(host).split(".")[-2:])   # ".hesperian.org"
    def sub(m):
        hostdir = os.path.join(mirror, m.group(3))
        seg = unquote(m.group(4)).split("/", 1)[0]
        # #180 (b2 F1): a sister host with no folder at all (bm.hesperian.org, ko.dev.hesperian.org) is just as unmirrored
        sister = os.path.isdir(os.path.join(hostdir, seg)) or m.group(3).endswith(domain)
        if NOT_MIRRORED in m.group(5) or NOT_MIRRORED_ES in m.group(5) or seg != section or hostdir == host or not sister \
                or "<a" in m.group(5).lower():
            return m.group(0)
        stats["not_mirrored_marked"] += 1
        return m.group(1) + m.group(5) + (NOT_MIRRORED_ES if os.path.basename(host) == "es.hesperian.org" else NOT_MIRRORED) + m.group(6)
    return XHOST_A.sub(sub, text)


REFRESH = re.compile(r'<meta\b[^>]*http-equiv=["\']?refresh["\']?[^>]*>', re.I)
REFRESH_URL = re.compile(r'(content=(["\'])\s*\d+\s*;\s*url=)([^"\']+)(\2)', re.I)


def visible_text(s):
    # FIXES #157: <title> is not visible body text (the Sheldon Brown stubs carry <title>to http://...</title>)
    s = re.sub(r"<!--.*?(-->|$)|<(script|style|title)\b.*?</\2>", "", s, flags=re.I | re.S)
    s = re.sub(r"\[an error occurred while processing this directive\]", "", s)   # Apache SSI failure text
    return re.sub(r"<[^>]+>", "", s).strip()


def is_stub(fpath):
    s = open(fpath, encoding="utf-8", errors="replace").read()
    return bool(REFRESH.search(s)) and not visible_text(s), s


def stub_target(mirror, fpath, seen=()):
    """local file a meta-refresh stub means (chained stubs followed), or None"""
    ok, s = is_stub(fpath)
    m = REFRESH_URL.search(REFRESH.search(s).group(0)) if ok else None
    if not m:
        return None
    url = htmlmod.unescape(m.group(3)).strip()
    here, frag = os.path.dirname(fpath), ("#" + url.split("#", 1)[1] if "#" in url else "")
    path = url.split("#", 1)[0]
    hosts = {e.name: e.path for e in os.scandir(mirror) if e.is_dir()}
    hostdir = os.path.join(mirror, os.path.relpath(fpath, mirror).split(os.sep)[0])
    am = re.match(r"https?://([^/]+)(/.*)?$", path)
    if am:
        h = am.group(1)
        h = h if h in hosts else ("www." + h if "www." + h in hosts else None)
        if not h:
            return None   # another site (a blog, a university page): nothing local
        cands = [os.path.join(hosts[h], (am.group(2) or "/").lstrip("/"))]
    elif re.match(r"[a-z]+:", path, re.I):
        return None
    else:
        bare = re.sub(r"^(\.\./|\./)+", "", path)
        # as written; from the host root; under the stub's own folder (harris/203.html -> ../tires/203.html lives at
        # harris/tires/203.html in the crawl)
        cands = [os.path.normpath(os.path.join(here, path)), os.path.join(hostdir, bare), os.path.join(here, bare)]
    for c in cands:
        for f in (c, c + ".html", c.rstrip("/") + "/index.html"):
            if os.path.isfile(f) and os.path.realpath(f) != os.path.realpath(fpath):
                if f in seen:
                    return None
                if is_stub(f)[0]:
                    t = stub_target(mirror, f, seen + (fpath,))
                    if t:
                        return t
                    continue
                return f, frag
    # singlespeed.html -> ../singlespeed.html is a self-loop on disk (wget flattened the path); the page it means is
    # the one file of that name elsewhere in the host (harris/singlespeed.html)
    base = os.path.basename(path.rstrip("/"))
    if base and base != "index.html" and not seen:
        twins = [os.path.join(r, base) for r, _, fs in os.walk(hostdir) for n in fs
                 if n == base and os.path.realpath(os.path.join(r, n)) != os.path.realpath(fpath) and not is_stub(os.path.join(r, n))[0]]
        if len(twins) == 1:
            return twins[0], frag
    return None


def fix_stubs(mirror, keep, dry, report):
    stats = Counter()
    for root, _, files in os.walk(mirror):
        for name in files:
            f = os.path.join(root, name)
            if not name.lower().endswith((".html", ".htm")) or not is_stub(f)[0]:
                continue
            stats["stubs"] += 1
            t = stub_target(mirror, f)
            if t:
                rel = quote(os.path.relpath(t[0], root), safe="/") + t[1]
                s = open(f, encoding="utf-8", errors="replace").read()
                meta = REFRESH.search(s).group(0)
                s = s.replace(meta, REFRESH_URL.sub(lambda m: m.group(1) + rel + m.group(4), meta), 1)
                link = f'<p>Moved: <a href="{rel}">{htmlmod.escape(os.path.basename(t[0]))}</a></p>'
                s = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + link, s, count=1, flags=re.I) if re.search(r"<body", s, re.I) else s + link
                report.append(f"LOCAL\t{f}\t{t[0]}{t[1]}")
                stats["local"] += 1
                if not dry:
                    backup(f); open(f, "w", encoding="utf-8").write(s)
            elif os.path.relpath(os.path.abspath(f), REPO + "/library") in keep:
                report.append(f"KEPT_LINKED_OUTSIDE\t{f}\t"); stats["kept"] += 1
            else:
                m = REFRESH_URL.search(REFRESH.search(is_stub(f)[1]).group(0))
                report.append(f"DELETED\t{f}\t{m.group(3) if m else ''}")
                stats["deleted"] += 1
                if not dry:
                    backup(f); os.unlink(f)
    print(f"{mirror}: stubs={stats['stubs']} local_redirect={stats['local']} deleted={stats['deleted']} "
          f"kept_linked_outside={stats['kept']}{' (dry-run)' if dry else ''}")


HREF_ANY = re.compile(r'((?:href|src)=)(["\'])([^"\'#?]+)([^"\']*)\2', re.I)


def relink(mirror, old, new, dry, mapping=None):
    """every href/src in the mirror that resolves to file `old` (or its folder, when old is index.html) -> `new`;
    or, with mapping {realpath(old): new}, many files in one walk"""
    if mapping is None:
        mapping = {os.path.realpath(old): new}
        if os.path.basename(old) == "index.html":
            mapping[os.path.realpath(os.path.dirname(old))] = new
    n = 0
    for root, _, files in os.walk(mirror):
        for name in files:
            if not name.lower().endswith((".html", ".htm")):
                continue
            f = os.path.join(root, name)
            if os.path.realpath(f) in mapping:
                continue
            s = open(f, "rb").read().decode("utf-8", "surrogateescape")
            def sub(m):
                nonlocal n
                u = m.group(3)
                if u.startswith(("http:", "https:", "//", "mailto:", "data:", "/")):
                    return m.group(0)
                t = mapping.get(os.path.realpath(os.path.join(root, unquote(htmlmod.unescape(u)))))
                if not t:
                    return m.group(0)
                n += 1
                return f"{m.group(1)}{m.group(2)}{quote(os.path.relpath(t, root), safe='/')}{m.group(2)}"
            s2 = HREF_ANY.sub(sub, s)
            if s2 != s and not dry:
                backup(f); open(f, "wb").write(s2.encode("utf-8", "surrogateescape"))
    return n


MEDIA_MAGIC = ((b"\x89PNG", ".png"), (b"GIF8", ".gif"), (b"\xff\xd8\xff", ".jpg"))


def media_ext(head):
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return next((e for m, e in MEDIA_MAGIC if head.startswith(m)), None)


def unhtml_media(mirror, dry, report):
    """FIXES #113: images wget saved as X.webp.html (--adjust-extension on a text/html content type) get their real
    name back, X.webp, and every <img src> follows; they stop being 'pages' in search and serve as images"""
    mapping, pairs = {}, []   # mapping keys are realpaths (library/mirrors may be a symlink); pairs keep library paths
    for root, _, files in os.walk(mirror):
        for name in files:
            f = os.path.join(root, name)
            if not name.lower().endswith((".html", ".htm")):
                continue
            with open(f, "rb") as fh:
                ext = media_ext(fh.read(12))
            if not ext:
                continue
            base = f[: f.lower().rindex(".htm")]
            dst = base if base.lower().endswith((ext, ".jpeg") if ext == ".jpg" else ext) else base + ext
            if os.path.exists(dst) and open(dst, "rb").read() != open(f, "rb").read():
                report.append(f"MEDIA_AS_HTML_NAME_TAKEN\t{f}\t{dst}"); continue
            mapping[os.path.realpath(f)] = dst; pairs.append((f, dst))
            if not os.path.exists(base):   # pages that link the name without wget's .html (sheldonbrown preview/X.jpg1)
                mapping[os.path.realpath(base)] = dst
    n = relink(mirror, None, None, dry, mapping)
    for src, dst in pairs:
        report.append(f"MEDIA_AS_HTML_RENAMED\t{os.path.relpath(src, REPO)}\t{os.path.relpath(dst, REPO)}")
        if not dry:
            backup(src)
            if os.path.exists(dst): os.unlink(src)
            else: os.rename(src, dst)
    print(f"{mirror}: media saved as .html renamed={len(pairs)} links repointed={n}{' (dry-run)' if dry else ''}")


def dedupe_pdf(mirror, dry, report):
    md5 = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
    fake, pdfs = [], {}
    for root, _, files in os.walk(mirror):
        for name in files:
            f = os.path.join(root, name)
            if name.lower().endswith((".html", ".htm")):
                with open(f, "rb") as fh:
                    if fh.read(4) == b"%PDF":
                        fake.append(f)
            elif name.lower().endswith(".pdf"):
                pdfs.setdefault(os.path.getsize(f), []).append(f)
    for f in fake:
        twin = next((p for p in pdfs.get(os.path.getsize(f), []) if md5(p) == md5(f)), None)
        if not twin:
            report.append(f"PDF_AS_HTML_NO_TWIN\t{f}\t"); continue
        n = relink(mirror, f, twin, dry)
        report.append(f"PDF_AS_HTML_DELETED\t{f}\t{twin}\trelinked={n}")
        if not dry:
            backup(f); os.unlink(f)
        print(f"{mirror}: {f} is a copy of {twin}; {n} links repointed{' (dry-run)' if dry else ''}")


def dedupe_query(mirror, dry, report):
    """red team 10-09 b2: X?utm_source=...html next to X.html with the same <title> is the same page under a tracking
    URL (search showed Coronavirus twice); delete it and point its links at X.html. index.html?p=NNN (WordPress
    shortlinks) have other titles and stay."""
    title = lambda f: (re.search(r"<title>([^<]*)", open(f, encoding="utf-8", errors="replace").read(), re.I) or [None, ""])[1].strip()
    n = 0
    for root, _, files in os.walk(mirror):
        for name in files:
            if "?" not in name or not name.lower().endswith((".html", ".htm")):
                continue
            base = name.split("?", 1)[0]
            plain = os.path.join(root, base if base.lower().endswith((".html", ".htm")) else base + ".html")
            f = os.path.join(root, name)
            if not os.path.isfile(plain) or open(f, "rb").read(4) == b"%PDF" or not title(f) or title(f) != title(plain):
                continue
            k = relink(mirror, f, plain, dry)
            report.append(f"QUERY_DUP_DELETED\t{os.path.relpath(f, REPO)}\t{os.path.relpath(plain, REPO)}\trelinked={k}")
            n += 1
            if not dry:
                backup(f); os.unlink(f)
    print(f"{mirror}: tracking-URL duplicate pages deleted={n}{' (dry-run)' if dry else ''}")


ES_MARK, EN_MARK = " (sitio web: necesita internet)", " (website: needs internet)"
MARKED = (ES_MARK, EN_MARK, NOT_MIRRORED, NOT_MIRRORED_ES)
# D12 = B (red team 10-11 b2 F2/F4, FIXES #187): Hesperian wiki-skin chrome that only leads to the live web offline
HHG_DROP = [re.compile(p, re.I) for p in (
    r'<(div) id="hm-mobile-header"', r'<(div) id="mobile-navigation"', r'<(div) id="nav2?" ',
    r'<(div) class="languageSelectorContainer', r'<(ul) class="sidelinks">', r'<(div) id="backorglink"',
    r'<(div) class="printfooter"', r'<(div) class="footer simple-footer')]
HHG_COMMENT_BLOCKS = re.compile(r"<!-- Google (Tag Manager|Analytics) -->.*?<!-- End Google \1 -->", re.S)
EXT_A = re.compile(r'(<a\b[^>]*?\shref=(["\'])\s*(?:https?:)?//[^"\']*\2[^>]*>)(.*?)(</a>)', re.I | re.S)
REDLINK_A = re.compile(r'<a\b[^>]*\shref=(["\'])[^"\']*redlink=1[^"\']*\1[^>]*>(.*?)</a>', re.I | re.S)
BCT = re.compile(r'<div id="bct">.*?</div>', re.S)
COVER = re.compile(r'class="coverimg">\s*<a href="([^"#:]+)"')
PSU = re.compile(r'(Visite el siguiente sitio web[^<]*<a\b[^>]*href="https?://[^"]+"[^>]*>)([^<]*)(</a>)')


# class 6 (red team 10-11 a7a F4b, a7b F6): the Spanish rabies/bat-bite page was linked from nowhere. Page -> (anchor,
# insert before/after it, html, guard). Skipped when the page already holds the guard text, so a rerun adds nothing.
# Red team 10-20 class 5 (#216, E9): the Community Guide dengue pages (2012) say "ibuprofen or paracetamol"; a library
# note under their Treatment heading gives the current guidance, the same sentence as the fever cards.
RABIA = "New_Where_There_Is_No_Doctor%3AMedicinas_para_las_mordeduras_de_animales%3APrimeros_auxilios.html"
NWTND22 = "../../../../docs/medical/hesperian_where_there_is_no_doctor/en_nwtnd_2019_22a.pdf#page=10"
MSF37 = "../../../../docs/medical/msf/msf_clinical_guidelines.pdf#page=37"
WHO26 = "../../../../docs/medical/who_pocket_book_hospital_care_children.pdf#page=50"   # printed p.26 (a poison centre)
WHO27 = "../../../../docs/medical/who_pocket_book_hospital_care_children.pdf#page=51"   # printed p.27
WHO33 = "../../../../docs/medical/who_pocket_book_hospital_care_children.pdf#page=57"   # printed p.33
INBOUND = {
    "es.hesperian.org/hhg/New_Where_There_Is_No_Doctor:Picaduras_y_mordeduras.html": (
        '<div id="toc" class="toc">', "before",
        f'<p class="library-note"><b>Mordeduras de perro, murciélago u otro animal que podría tener rabia:</b> vea '
        f'<a href="{RABIA}" title="Medicinas para las mordeduras de animales">Medicinas para las mordeduras de animales</a>.</p>\n', RABIA),
    "es.hesperian.org/hhg/Nuevo_Donde_no_hay_doctor.html": (
        'title="Picaduras y mordeduras">Picaduras y mordeduras</a></li>', "after",
        f'\n<li><a href="{RABIA}" title="Medicinas para las mordeduras de animales">Medicinas para las mordeduras de '
        f'animales (rabia)</a></li>', RABIA),
    "es.hesperian.org/hhg/A_Community_Guide_to_Environmental_Health:Fiebre_del_dengue_(fiebre_rompehuesos).html": (
        '<span class="mw-headline" id="Tratamiento">Tratamiento</span></h5>\n', "after",
        f'<p class="library-note"><b>Nota de la biblioteca. Dengue:</b> para la fiebre y el dolor use paracetamol, nunca '
        f'ibuprofeno ni aspirina. Algunas páginas antiguas de esta caja dicen ibuprofeno; la guía actual es otra ('
        f'<a href="{NWTND22}">New Where There Is No Doctor cap.22 p.10</a>; <a href="{MSF37}">MSF Clinical Guidelines '
        f'p.37</a>, en inglés).</p>\n', "Nota de la biblioteca. Dengue:"),
    "en.hesperian.org/hhg/A_Community_Guide_to_Environmental_Health:Dengue_Fever_(Breakbone_Fever).html": (
        '<span class="mw-headline" id="Treatment">Treatment</span></h5>\n', "after",
        f'<p class="library-note"><b>Library note. Dengue:</b> use paracetamol (acetaminophen) for fever and pain, never '
        f'ibuprofen or aspirin. Some older pages on this box say ibuprofen; current guidance differs ('
        f'<a href="{NWTND22}">New Where There Is No Doctor ch.22 p.10</a>; <a href="{MSF37}">MSF Clinical Guidelines '
        f'p.37</a>).</p>\n', "Library note. Dengue:"),
    # round 7 (#229, a7a W3): the Spanish fever card's «Fiebre (calentura)» link lands here, on «paracetamol o ibuprofeno»
    "es.hesperian.org/hhg/New_Where_There_Is_No_Doctor:Problemas_de_la_salud_de_los_niños.html": (
        '<span class="mw-headline" id="Fiebre_.28calentura.29">Fiebre (calentura)</span></h3>\n', "after",
        f'<p class="library-note"><b>Nota de la biblioteca. Dengue:</b> para la fiebre y el dolor use paracetamol, nunca '
        f'ibuprofeno ni aspirina. Algunas páginas antiguas de esta caja dicen ibuprofeno; la guía actual es otra ('
        f'<a href="{NWTND22}">New Where There Is No Doctor cap.22 p.10</a>; <a href="{MSF37}">MSF Clinical Guidelines '
        f'p.37</a>, en inglés).</p>\n', "Nota de la biblioteca. Dengue:"),
    # round 7 (#231, a7a W2, a7b F3): the Poison pages say "drink large amounts of water" and "a spoonful of salt";
    # WHO Pocket Book 2013 ch.1 1.6.1 (printed p.27, PDF p.51) and 1.6.5 (p.33): water or milk only after a corrosive or
    # petrol product, "never use salt as an emetic, as this can be fatal", "do not induce vomiting"
    "en.hesperian.org/hhg/New_Where_There_Is_No_Doctor:Poison.html": (
        'For most poisons: quickly flush the poison out', "before",
        f'<p class="library-note"><b>Library note. Poisoning:</b> do not make the person vomit, and never give salt to '
        f'cause vomiting: it can kill a child. This page says to drink large amounts of water for most poisons. The WHO '
        f'book gives water or milk to drink only after bleach, a cleaner, battery acid, fuel or kerosene, and activated '
        f'charcoal, if there is any, for other poisons; it does not say to flush the poison out with water. Get medical '
        f'help, and if any phone works, call a poison centre (<a href="{WHO26}">WHO Pocket Book of Hospital Care for '
        f'Children, 2013, ch.1 p.26</a>; the rest: <a href="{WHO27}">p.27</a> and <a href="{WHO33}">p.33</a>).</p>\n',
        "Library note. Poisoning:"),
    "es.hesperian.org/hhg/New_Where_There_Is_No_Doctor:Envenenamiento.html": (
        'Para la mayoría de los venenos, beber', "before",
        f'<p class="library-note"><b>Nota de la biblioteca. Envenenamiento:</b> no haga vomitar a la persona y nunca le dé '
        f'sal para que vomite: puede matar a un niño. Esta página dice que se tome mucha agua para la mayoría de los '
        f'venenos. El libro de la OMS da agua o leche para beber solo después de cloro, un limpiador, ácido de batería, '
        f'gasolina o queroseno, y carbón activado, si lo hay, para los demás venenos; no dice que se saque el veneno con '
        f'agua. Consiga ayuda médica y, si algún teléfono funciona, llame al centro de control de envenenamientos ('
        f'<a href="{WHO26}">WHO Pocket Book of Hospital Care for Children, 2013, cap.1 p.26</a>; lo demás: <a href="'
        f'{WHO27}">p.27</a> y <a href="{WHO33}">p.33</a>, en inglés).</p>\n', "Nota de la biblioteca. Envenenamiento:"),
    # b2 B2-11: the Community Guide (2008) pesticide pages give "a glass of very salty water" and raw egg white
    "en.hesperian.org/hhg/A_Community_Guide_to_Environmental_Health:Treatment_for_Pesticide_Poisoning.html": (
        '<span class="mw-headline" id="Treatment_2">Treatment</span></h5>\n', "after",
        f'<p class="library-note"><b>Library note. Swallowed pesticide:</b> never give salty water to cause vomiting: it '
        f'can kill a child. Most pesticides are mixed in a petrol-based liquid, so do not make the person vomit; give '
        f'water or milk to drink and get medical help. The WHO book gives water or milk, not raw egg white (<a href="'
        f'{WHO27}">WHO Pocket Book of Hospital Care for Children, 2013, ch.1 p.27</a>).</p>\n', "Library note. Swallowed pesticide:"),
    "es.hesperian.org/hhg/A_Community_Guide_to_Environmental_Health:Tratamiento_en_casos_de_envenenamiento_por_plaguicidas.html": (
        '<span class="mw-headline" id="Tratamiento_2">Tratamiento</span></h5>\n', "after",
        f'<p class="library-note"><b>Nota de la biblioteca. Si se tragó un plaguicida:</b> nunca le dé agua salada para que '
        f'vomite: puede matar a un niño. La mayoría de los plaguicidas vienen mezclados en un líquido a base de petróleo, '
        f'así que no haga vomitar a la persona; dele agua o leche para beber y consiga ayuda médica. El libro de la OMS da '
        f'agua o leche, no la clara de huevo crudo (<a href="{WHO27}">WHO Pocket Book of Hospital Care for Children, '
        f'2013, cap.1 p.27</a>, en inglés).</p>\n', "Nota de la biblioteca. Si se tragó un plaguicida:"),
}


def add_inbound(text, fpath, stats):
    key = next((k for k in INBOUND if fpath.replace(os.sep, "/").endswith("/" + k)), None)
    if not key:
        return text
    anchor, where, snippet, guard = INBOUND[key]
    if guard in text or unquote(guard) in text:
        # round 9 b2 W14: a library note whose wording changed is rewritten in place (the guard names the note)
        g = text.find(guard)
        a = text.rfind('<p class="library-note">', 0, g)
        b = text.find("</p>\n", g)
        if guard.startswith(("Library note", "Nota de la biblioteca")) and snippet.startswith('<p class="library-note">') \
                and a >= 0 and b > g and "</p>" not in text[a:g] and text[a:b + 5] != snippet:
            stats["inbound_updated"] += 1
            return text[:a] + snippet + text[b + 5:]
        return text
    i = text.find(anchor)
    if i < 0:
        stats["inbound_anchor_missing"] += 1; return text
    i = i if where == "before" else i + len(anchor)
    stats["inbound_added"] += 1
    return text[:i] + snippet + text[i:]


def drop_el(text, start, stats, key):
    """remove each element whose start tag matches `start` (group 1 = tag name) through its balanced end tag"""
    while (m := start.search(text)):
        depth, end = 0, None
        for t in re.compile(r"<(/?)%s\b[^>]*>" % m.group(1), re.I).finditer(text, m.start()):
            depth += -1 if t.group(1) else 1
            if depth == 0:
                end = t.end(); break
        if end is None:
            stats[key + "_unbalanced"] += 1; break
        text = text[:m.start()] + text[end:]; stats[key] += 1
    return text


def mark_ext(text, mark, stats, key, only=None):
    def sub(m):
        if only and not only.search(m.group(0)):
            return m.group(0)
        if any(x in m.group(3) for x in MARKED) or "<a" in m.group(3).lower():
            return m.group(0)
        stats[key] += 1
        return m.group(1) + m.group(3) + mark + m.group(4)
    return EXT_A.sub(sub, text)


# red team 10-13 b2 F3 / a7b F9 (#197): "In this chapter:" is a button that opens a <dialog> only through the live
# skin's script, which is gone, so the chapter list never shows. A native <details> opens with JS off, file:// and Pi.
SIDETOC = re.compile(r'<div class="sidedoc-controls"><button class="hm-button dialog-open" data-dialog="#sidetoc">(.*?)'
                     r'</button></div>\s*<dialog id="sidetoc" class="dialog-left">\s*'
                     r'<div class="dialog-nav"><form method="dialog"><button>&#160;</button></form></div>(.*?)</dialog>', re.S)


def sidetoc_details(text, stats):
    def sub(m):
        stats["sidetoc_to_details"] += 1
        label = m.group(1) if m.group(1).strip() else "&#9776;"   # 7 km pages have no label: a menu glyph
        return f'<details id="sidetoc" class="sidedoc-controls"><summary>{label}</summary>{m.group(2)}</details>'
    return SIDETOC.sub(sub, text)


# b2 F6 (#197): /hhg/X root-relative links on other-language pages (the LINK pass could not resolve them on their own
# host) 404 on the box. Same page on a sister host (Kyrgyz template pages saved into en) -> that copy; HealthWiki -> the
# host's own front page or the English one; else the live page, which mark_ext then marks as needing internet.
ROOT_HHG = re.compile(r'(<a\b[^>]*?\shref=)(["\'])(/hhg/[^"\']*)\2', re.I)
REL_HW = re.compile(r'(<a\b[^>]*?\shref=)(["\'])(HealthWiki\.html)\2')


def hhg_rootabs(text, fpath, mirror, stats):
    here = os.path.dirname(fpath)
    host = os.path.join(mirror, os.path.relpath(fpath, mirror).split(os.sep)[0])
    en = os.path.join(mirror, "en.hesperian.org")
    rel = lambda t: quote(os.path.relpath(t, here), safe="/")

    def sub(m):
        path, _, frag = htmlmod.unescape(m.group(3)).partition("#")
        frag = "#" + frag if frag else ""
        t = resolve(host, path)
        if not t and unquote(path).rstrip("/").rsplit("/", 1)[-1] in ("HealthWiki", "HealthWiki.html"):
            t = resolve(host, "/hhg/HealthWiki") or resolve(en, "/hhg/HealthWiki")
        if not t:
            for h in [en] + sorted(e.path for e in os.scandir(mirror) if e.is_dir() and e.path not in (en, host)):
                if (t := resolve(h, path)):
                    break
        if t:
            stats["hhg_rootabs_local"] += 1
            return f"{m.group(1)}{m.group(2)}{rel(t)}{frag}{m.group(2)}"
        stats["hhg_rootabs_live"] += 1
        return f"{m.group(1)}{m.group(2)}https://{os.path.basename(host)}{m.group(3)}{m.group(2)}"
    text = ROOT_HHG.sub(sub, text)
    if not os.path.exists(os.path.join(here, "HealthWiki.html")) and (hw := resolve(en, "/hhg/HealthWiki")):
        text, n = REL_HW.subn(lambda m: f"{m.group(1)}{m.group(2)}{rel(hw)}{m.group(2)}", text)
        stats["healthwiki_to_en"] += n
    return text


# b2 F9 (#197): the HealthWiki front pages say "use the search bar in the upper right" (the strip removed the live
# one), and the "most popular topics" box is an empty live widget. A library search box goes after that sentence (it
# opens the library's own search, Spanish on es); the empty widget box goes.
SEARCH_SENT = re.compile(r"barra de búsqueda|search bar")
TOPTEN = re.compile(r'<(div) class="topTen libraryBox headerBar">')
EMPTY_TOP = re.compile(r'<div id="hesp_10_[^"]*">\s*</div>')


def healthwiki_front(text, fpath, stats):
    if os.path.basename(fpath) == "HealthWiki.html" and 'class="library-search"' not in text and (m := SEARCH_SENT.search(text)):
        i = text.find("</p>", m.end())
        if i > 0:
            es = "/es.hesperian.org/" in fpath.replace(os.sep, "/")
            form = ('<form class="library-search" action="../../../../search.html" method="get"><label>'
                    + ("Buscar en esta biblioteca: " if es else "Search this library: ")
                    + '<input type="search" name="q"></label>' + ('<input type="hidden" name="lang" value="spa">' if es else "")
                    + ' <button type="submit">' + ("Buscar" if es else "Search") + "</button></form>\n")
            text = text[:i + 4] + "\n" + form + text[i + 4:]; stats["healthwiki_search_added"] += 1
    if (m := TOPTEN.search(text)):
        box = drop_el(text[m.start():], TOPTEN, Counter(), "x")
        block = text[m.start():len(text) - len(box)]
        if EMPTY_TOP.search(block):
            text = text[:m.start()] + box; stats["empty_widget_box_dropped"] += 1
    text, n = EMPTY_TOP.subn("", text); stats["empty_widget_dropped"] += n
    return text


def hhg_chrome(text, fpath, stats, mirror=None):
    """strip nav, footer, social, sidebar buy/print/download/donate buttons, the inert mobile language <select>,
    the print footer and the Google Tag Manager/Analytics bootstrap; breadcrumb redlinks (live-wiki edit forms) point
    at the local book cover; other redlinks become plain text; every external link left says it needs internet;
    viewport width=720 becomes device-width; the dead chapter-list dialog becomes <details>. Article text is
    untouched. Idempotent."""
    text = sidetoc_details(text, stats)
    if mirror:
        text = healthwiki_front(dead_local(hhg_rootabs(text, fpath, mirror, stats), fpath, mirror, stats), fpath, stats)
    text, n = HHG_COMMENT_BLOCKS.subn("", text); stats["tracking_blocks_dropped"] += n
    text, n = re.subn(r'(<meta name="viewport" content=")width=720(")', r"\1width=device-width, initial-scale=1\2", text)
    stats["viewport_fixed"] += n
    for p in HHG_DROP:
        text = drop_el(text, p, stats, "chrome_el_dropped")
    cover = COVER.search(text)
    cover = cover.group(1) if cover and os.path.isfile(os.path.join(os.path.dirname(fpath), unquote(htmlmod.unescape(cover.group(1))))) else None
    def bct(m):
        def a(r):
            if cover:
                stats["bct_redlink_to_cover"] += 1; return f'<a href="{cover}">{r.group(2)}</a>'
            stats["bct_redlink_unlinked"] += 1; return r.group(2)
        return REDLINK_A.sub(a, m.group(0))
    text = BCT.sub(bct, text, count=1)
    text, n = REDLINK_A.subn(r"\2", text); stats["redlink_unlinked"] += n
    return mark_ext(text, ES_MARK if "/es.hesperian.org/" in fpath.replace(os.sep, "/") else EN_MARK, stats, "ext_marked")


# red team 10-13 b5 N2 (#197): sheldonbrown bbpress.html ("Tech Forum", 177 pages link it) forwards to Facebook after
# 5 s with no mark. A page with visible text whose meta refresh leaves the mirror keeps its text, loses the refresh, and
# shows the address as a marked link instead; a refresh to an absolute URL of the mirrored site points at the local
# copy. (Text-less stubs are --stubs' job.)
EXT_REFRESH = re.compile(r'<meta\b[^>]*http-equiv=["\']?refresh["\']?[^>]*?url=(https?://[^"\'\s>]+)[^>]*>[ \t]*\n?', re.I)
REDIRECT_SENTENCE = re.compile(r"You will be redirected there in \d+ seconds\.", re.I)


def ext_refresh(text, fpath, mirror, stats):
    m = EXT_REFRESH.search(text)
    if not m or not visible_text(text):
        return text
    host, rest = (m.group(1).split("/", 3) + [""])[2:4]
    hostdir = next((os.path.join(mirror, h) for h in (host, "www." + host) if os.path.isdir(os.path.join(mirror, h))), None)
    if hostdir:   # same site (harris/white-freewheels.html -> sheldonbrown.com/harris/singlespeed.html): the local copy
        t = resolve(hostdir, "/" + rest)
        if not t:
            stats["refresh_same_site_unresolved"] += 1; return text
        frag = "#" + rest.split("#", 1)[1] if "#" in rest else ""
        stats["refresh_made_local"] += 1
        return text[:m.start(1)] + quote(os.path.relpath(t, os.path.dirname(fpath)), safe="/") + frag + text[m.end(1):]
    stats["ext_refresh_dropped"] += 1
    text = text[:m.start()] + text[m.end():]
    link = f'<a href="{m.group(1)}">{m.group(1)}</a>{EN_MARK}'
    text, n = REDIRECT_SENTENCE.subn(lambda _: f"It is at {link}.", text, count=1)
    if not n:
        text = re.sub(r"(<body[^>]*>)", lambda b: b.group(1) + f"<p>This page used to forward to {link}.</p>", text, count=1, flags=re.I)
    return text


URL_ATTR = re.compile(r'(?<![-\w])(href|src|srcset)=(["\'])([^"\']*)\2', re.I)


def exact_case(mirror, dry, report):
    """--exact-case, red team 10-13 b2 F5 (#197): the Pi is Linux (case- and Unicode-form-sensitive), APFS on the dev
    Mac is not, so a link to Healthwiki.html opens HealthWiki.html here and is a 404 on the box. Every relative
    href/src/srcset whose target exists only under another case or Unicode form points at the real name. Idempotent."""
    stats, ls = Counter(), {}
    root = os.path.abspath(mirror)

    def real(path):
        """on-disk spelling of an existing path under the mirror; None when a segment is missing or ambiguous"""
        cur = root
        for part in os.path.relpath(path, root).split(os.sep):
            if cur not in ls:
                ent = os.listdir(cur) if os.path.isdir(cur) else []
                idx = {}
                for e in ent:
                    idx.setdefault(unicodedata.normalize("NFC", e).casefold(), []).append(e)
                ls[cur] = (set(ent), idx)
            have, idx = ls[cur]
            if part not in have:
                c = idx.get(unicodedata.normalize("NFC", part).casefold(), [])
                if len(c) != 1:
                    return None
                part = c[0]
            cur = os.path.join(cur, part)
        return cur

    for dp, _, files in os.walk(root):
        for name in files:
            if not name.lower().endswith((".html", ".htm")):
                continue
            f = os.path.join(dp, name)
            s = open(f, "rb").read().decode("utf-8", "surrogateescape")

            def one(u):
                if not u or u.startswith(("#", "/")) or re.match(r"[a-zA-Z][a-zA-Z+.-]*:", u):
                    return u
                path, hs, frag = u.partition("#")
                path, qs, query = path.partition("?")
                t = os.path.normpath(os.path.join(dp, unquote(htmlmod.unescape(path))))
                if not t.startswith(root + os.sep) or not os.path.exists(t):
                    return u
                if os.path.isdir(t):
                    t = os.path.join(t, "index.html")
                    if not os.path.exists(t):
                        return u
                r = real(t)
                if r is None:
                    stats["case_ambiguous"] += 1; return u
                if r == t:
                    return u
                new = quote(os.path.relpath(r, dp), safe="/") + qs + query + hs + frag
                stats["case_fixed"] += 1
                report.append(f"CASE_FIXED\t{os.path.relpath(f, REPO)}\t{u}\t{new}")
                return new

            def attr(m):
                k, q, v = m.groups()
                if k.lower() == "srcset":
                    parts = [p.split() for p in v.split(",") if p.strip()]
                    fixed = [[one(p[0])] + p[1:] for p in parts]
                    return m.group(0) if fixed == parts else f'{k}={q}{", ".join(" ".join(p) for p in fixed)}{q}'
                v2 = one(v)
                return m.group(0) if v2 == v else f"{k}={q}{v2}{q}"
            new = URL_ATTR.sub(attr, s)
            if new != s:
                stats["written"] += 1
                if not dry:
                    backup(f); open(f, "wb").write(new.encode("utf-8", "surrogateescape"))
    print(f"{mirror}: " + " ".join(f"{k}={v}" for k, v in sorted(stats.items())) + (" (dry-run)" if dry else ""))


# E3 (10-13: A, #197): the mirrored organisation site (hesperian.org WordPress, languages.hesperian.org, the 2 Qgiv
# donate pages) gets the D12 treatment: site header/menus, footers (shop, donate, newsletter, social) and every tracker
# (gtag, GTM, Matomo, Qgiv/Bloomerang) go; book lists, language lists and article text stay; embedded live frames
# become a marked link; every internet link left is marked.
ORG_DROP = [re.compile(p, re.I) for p in (
    r"<(header) id='header'", r"<(div) class='container_wrap footer_color' id='footer'",
    r"<(footer) class='container_wrap socket_color'", r'<(div) class="container-fluid fixed-top"',
    r'<(nav) class="footer"', r"<(footer)>", r'<(footer) class="page-footer js-page-footer')]
TRACK = re.compile(r"gtag\(|googletagmanager|google-analytics|dataLayer|matomo|_paq|qgiv|bloomerang|fbevents|fbq\(|hotjar|clarity\.ms", re.I)
EMOJI = re.compile(r"wp-emoji|wpemoji|emoji-release|_wpemojiSettings", re.I)   # WordPress loads its emoji script from the live site
SCRIPT_EL = re.compile(r"<script\b([^>]*)>(.*?)</script\s*>", re.I | re.S)
NOSCRIPT_EL = re.compile(r"<noscript\b[^>]*>.*?</noscript\s*>", re.I | re.S)
IFRAME_EL = re.compile(r"<iframe\b([^>]*)>.*?</iframe\s*>", re.I | re.S)
QGIV_FORM = re.compile(r'<(div) class="(?:donation-form-container|qgiv-embed-container)')
ORG_HOSTS = ("hesperian.org", "languages.hesperian.org")


def org_chrome(text, fpath, mirror, stats):
    host = os.path.join(mirror, os.path.relpath(fpath, mirror).split(os.sep)[0])
    mark = ES_MARK if re.search(r'<html[^>]*\slang=["\']?es', text, re.I) else EN_MARK

    no_jq = not re.search(r"<script\b[^>]*\ssrc=[^>]*jquery", text, re.I)

    def needs_jq(src, body):
        if not src:
            return "jQuery" in body
        f = os.path.normpath(os.path.join(os.path.dirname(fpath), unquote(src.split("?", 1)[0])))
        return os.path.isfile(f) and b"jQuery" in open(f, "rb").read()

    def script(m):
        src = re.search(r'\bsrc=["\']([^"\']+)', m.group(1))
        if (TRACK.search(m.group(0)) or EMOJI.search(m.group(0)) or (src and src.group(1).startswith("/") and not resolve(host, src.group(1)))
                or (no_jq and needs_jq(src.group(1) if src else None, m.group(2)))):   # jQuery itself was never local: dead, throws
            stats["org_script_dropped"] += 1; return ""
        return m.group(0)
    text = SCRIPT_EL.sub(script, text)
    def nos(m):
        if not TRACK.search(m.group(0)): return m.group(0)
        stats["org_noscript_dropped"] += 1; return ""
    text = NOSCRIPT_EL.sub(nos, text)
    for p in ORG_DROP:
        text = drop_el(text, p, stats, "org_chrome_dropped")
    while (m := QGIV_FORM.search(text)):
        depth, end = 0, None
        for t in re.finditer(r"<(/?)div\b[^>]*>", text[m.start():]):
            depth += -1 if t.group(1) else 1
            if not depth: end = m.start() + t.end(); break
        if end is None: stats["org_donation_form_unbalanced"] += 1; break
        text = (text[:m.start()] + f'<p class="library-note">The donation form needs internet: '
                f'<a href="https://hesperian.org/donate/">hesperian.org/donate{EN_MARK}</a></p>' + text[end:])
        stats["org_donation_form_noted"] += 1
    def frame(m):
        u = re.search(r'(?<![-\w])(?:data-)?src=(["\'])\s*((?:https?:)?//[^"\']*)\1', m.group(1))
        if not u: return m.group(0)
        if TRACK.search(u.group(2)):
            stats["org_tracker_frame_dropped"] += 1; return ""
        t = re.search(r'\stitle=(["\'])(.*?)\1', m.group(1))
        label = t.group(2) if t and t.group(2).strip() else (re.match(r"(?:https?:)?//([^/]+)", u.group(2)).group(1))
        stats["org_frame_to_link"] += 1
        return f'<p class="library-note"><a href="{u.group(2)}">{label}{mark}</a></p>'
    text = IFRAME_EL.sub(frame, text)
    return mark_ext(text, mark, stats, "org_ext_marked")


# fix-all (#197; b2 F2 "190 org pages have broken local links", the HealthWiki front pages' covers of books that are not
# mirrored in that language, org-site links to pruned feed/category/post pages): a relative or root <a> whose page is
# not on disk points at the live page, and mark_ext then marks it; a <link> head tag to a missing file goes; an <img>
# whose local file is missing keeps its live URL as data-src (mark_offline_img marks it). Hesperian mirror only.
HREF_ATTR = re.compile(r'(<(a|link|img)\b(?:"[^"]*"|\'[^\']*\'|[^>"\'])*?(?<![-\w])(href|src)=)(["\'])([^"\']*)\4', re.I)


def live_url(mirror, t):
    rel = os.path.relpath(t, mirror).replace(os.sep, "/")
    host, _, p = rel.partition("/")
    p, _, q = p.partition("?")
    if p == "index.html" or p.endswith("/index.html"): p = p[:-len("index.html")]
    elif p.startswith("hhg/") and p.endswith(".html"): p = p[:-5]
    q = re.sub(r"\.html$", "", q)
    return f"https://{host}/{quote(p, safe='/:,()')}" + ("?" + q if q else "")


def dead_local(text, fpath, mirror, stats):
    here = os.path.dirname(fpath); mroot = os.path.abspath(mirror)
    host = os.path.join(mroot, os.path.relpath(fpath, mirror).split(os.sep)[0])

    def sub(m):
        tag, attr, u = m.group(2).lower(), m.group(3).lower(), htmlmod.unescape(m.group(5)).strip()
        if (tag == "img") != (attr == "src") or not u or u.startswith(("#", "//")) or re.match(r"[a-zA-Z][a-zA-Z+.-]*:", u):
            return m.group(0)
        path, _, frag = u.partition("#")
        if tag == "a" and path.startswith("www."):
            stats["dead_local_domain"] += 1
            return f"{m.group(1)}{m.group(4)}https://{path}{'#' + frag if frag else ''}{m.group(4)}"
        if path.startswith("/"):
            if resolve(host, path): return m.group(0)
            t = os.path.join(host, path.lstrip("/"))
        else:
            t = os.path.normpath(os.path.join(os.path.abspath(here), unquote(path.split("?", 1)[0])))
            q = path.partition("?")[2]
            if os.path.exists(t) or os.path.exists(t + ".html") or os.path.isfile(os.path.join(t, "index.html")) or not t.startswith(mroot + os.sep):
                return m.group(0)
            t = t + ("?" + q if q else "")
        live = live_url(mroot, t)
        if tag == "link":
            stats["dead_local_link_tag_dropped"] += 1; return f"{m.group(1)}{m.group(4)}\0DROP\0{m.group(4)}"
        if tag == "img":
            stats["dead_local_img_to_live"] += 1
            return m.group(1)[:-len("src=")] + f"data-src={m.group(4)}{live}{m.group(4)}"
        stats["dead_local_a_to_live"] += 1
        return f"{m.group(1)}{m.group(4)}{live}{'#' + frag if frag else ''}{m.group(4)}"
    text = HREF_ATTR.sub(sub, text)
    return re.sub(r"<link\b[^>]*\0DROP\0[^>]*>\s*", "", text) if "\0DROP\0" in text else text


# E2 (10-13: A, #197): an <img> whose picture is still only on the live site (a fetch failed or the origin is not
# Hesperian's) says so instead of leaving a blank. Run after the image fetch and --repair.
IMG_MARK_ES, IMG_MARK_EN = " (dibujo: necesita internet)", " (picture needs internet)"
IMG_NOSRC = re.compile(r'(<img\b(?:"[^"]*"|\'[^\']*\'|[^>"\'])*>)(\s*<span class="library-note img-offline">)?', re.I)


def mark_offline_img(text, fpath, stats):
    es = "/es.hesperian.org/" in fpath.replace(os.sep, "/")
    def sub(m):
        tag = m.group(1)
        if m.group(2) or re.search(r'(?<![-\w])src=(["\'])\s*[^"\'\s]', tag) or not re.search(r'(?<![-\w])data-src=(["\'])\s*[^"\'\s]', tag):
            return m.group(0)
        stats["img_marked_needs_internet"] += 1
        return tag + f'<span class="library-note img-offline">{IMG_MARK_ES if es else IMG_MARK_EN}</span>'
    return IMG_NOSRC.sub(sub, text)


# Red team 10-16 b2 (K7, FIXES #208), Hesperian mirror only, every page:
#  F1  pages wider than a phone: a small local style makes tables, <pre> scroll inside the page, a labelled drawing fixed wider than 360 px shrinks to the phone (over 800 px it scrolls), and
#      caps image width (labelled drawings inside a positioned div keep their size, so the labels stay on the picture);
#  F2  the unstyled wiki leftovers: the print-only "Hesperian Health Guides" heading and the wiki-editor "Edit links" /
#      "Editar los enlaces" item go, and the arrow for the other text direction goes (both showed: "←→ Anterior");
#  F5  the Bootstrap carousels on languages.hesperian.org cannot move (no script): every item shows, the arrows go;
#  F3, F18, F4  dead or live third-party script: the ga() PDF-click hook, the SurveyMonkey loader, the donate stub's
#      logo redirect to the live site, the Cloudflare e-mail decoder (every address was decoded by --repair), and the
#      donate stub's root @import that 404s;
#  F6  buy buttons (a.btn / avia-button to store.hesperian.org) go;
#  F8  wiki body links to the store for a book that is on the box point at the local book cover;
#  F15 wiki forms posting to the live wiki (Special:AllPages ...) go, links to the wiki upload form ("300px") go, and a
#      relative link whose page is on disk only as X.html points at X.html.
PHONE_CSS = ('<style id="lantern-phone">/* Lantern: phone width and offline leftovers (red team 10-16 b2 F1 F2 F5, 10-20 b2 F1) */\n'
             'img,video{max-width:100%;height:auto}\n'
             'table,pre{display:block;max-width:100%;overflow-x:auto;box-sizing:border-box}\n'
             'table.lantern-fit{display:table;table-layout:fixed;width:100%!important;margin-left:0!important}\n'
             '.lantern-fit td,.lantern-fit th{hyphens:auto;-webkit-hyphens:auto}\n'
             # red team 10-20 b2 F1 (#218): on a phone a picture table stacks, picture above text, instead of a 7-15 px text column
             '@media (max-width:600px){table.lantern-stack,.lantern-stack>tbody,.lantern-stack>thead,.lantern-stack>tfoot,'
             '.lantern-stack>*>tr,.lantern-stack>*>tr>td,.lantern-stack>*>tr>th{display:block;width:auto!important;box-sizing:border-box}\n'
             # and a desktop cell padding (200 px each side) or list indent does not eat a phone column; a cell of a table
             # that scrolls in its box keeps 6 em (the box scrolls) instead of 5 characters a line
             '#mw-content-text td,#mw-content-text th{padding-left:4px!important;padding-right:4px!important}'
             '#mw-content-text td ul,#mw-content-text td ol{padding-inline-start:1em!important}'
             '#mw-content-text table:not(.lantern-fit) td,#mw-content-text table:not(.lantern-fit) th{min-width:6em}'
             # b2 F3: a desktop indent (a drawing shifted with left:, a table with margin-left) pushed the page past the phone
             '#mw-content-text [style*="position: relative"],#mw-content-text [style*="position:relative"]{left:0!important}'
             '#mw-content-text table{margin-left:0!important;margin-right:0!important}'
             '.lantern-gutter{margin-left:0!important;margin-right:0!important;padding-left:0!important;padding-right:0!important}'
             # round 7 B2-02: a desktop hanging indent (text-indent:-25px over padding-left:25px) put "12." and "Q:" left of
             # the screen once the cell padding is 4 px; on a phone the first line starts with the rest
             '#mw-content-text [style*="text-indent: -"],#mw-content-text [style*="text-indent:-"]{text-indent:0!important}'
             # and a desktop negative margin (a chart with margin-left:-25px) started its box left of the screen
             '#mw-content-text [style*="margin-left: -"],#mw-content-text [style*="margin-left:-"]{margin-left:0!important}'
             # round 9 b2 W11 W12: the wiki pushes a quote's credit right with ten nested ":" indents (40 px each), which on a
             # phone left it 1 letter a line past the right edge; a nested indent is 0.6 em on a phone
             '#mw-content-text dd dd{margin-left:.6em}'
             # and a note box sized in percent (width:18%, 30%) left 4-10 letters a line inside it: full width on a phone
             '#mw-content-text .box[style*="%"]{width:auto!important;float:none!important}'
             # and a fitted table set at 170 percent type (NWTND diabetes «¿Cómo quitarse la sed?») broke its first column 2
             # letters a line: on a phone a fitted table's type is the page's
             'table.lantern-fit[style*="font-size"]{font-size:100%!important}'
             # round 10 b2 W7: on a right-to-left page a picture table's left overflow escaped its sideways scroll box
             # and widened the page (392-674 px, also with JS off); the article clips sideways overflow (the table still
             # scrolls in its own box; b2_offscreen counts any clipped text as lost)
             'html[dir=rtl] #mw-content-text{overflow-x:clip}}\n'
             '.lantern-wide{max-width:100%;overflow-x:auto;box-sizing:border-box}\n'
             # round 8 b2 F10 (#241): a picture label is a fixed narrow box (55-70 px wide on the wiki too); a word longer
             # than the box was split mid-word by body{overflow-wrap} ("izquierd-o."). The box takes at least its longest
             # word, and a list inside a label keeps the wiki's own 1.6 em indent, not the browser's 40 px, which left one
             # or two words a line
             '#mw-content-text [style*="position: absolute"],#mw-content-text [style*="position:absolute"]{min-width:min-content;overflow-wrap:normal;hyphens:manual;-webkit-hyphens:manual}\n'
             '#mw-content-text [style*="position: absolute"] ul,#mw-content-text [style*="position:absolute"] ul{margin:.3em 0 0 1.6em;padding:0}\n'
             # round 8 b2 F11: the org site's theme hides closed toggles and other tabs at left:120% and stacks slider
             # slides on top of each other until its script runs; the script is gone (jQuery was never local), so the
             # text sat clipped off the right edge. Offline every toggle is open, every tab and slide shows, and the dead
             # slider arrows and the hidden structured-data line go
             '.js_active .toggle_wrap,.js_active .tab_content{visibility:visible!important;position:static!important;left:auto!important;width:auto!important}\n'
             '.tab_inner_content{left:0!important}\n'
             # white text written for the open toggle's colour band, which lives in a per-page theme file that is not on
             # the box: on the plain background it was invisible
             '.toggle_content [style*="color: #ffffff"],.toggle_content [style*="color:#ffffff"]{color:inherit!important}\n'
             '.avia-content-slider-active .slide-entry-wrap{position:static!important;visibility:visible!important}\n'
             '.avia-slideshow-arrows,.av-structured-data{display:none!important}\n'
             # round 9 b2 W3: the languages site's app tiles sit in a box that hides overflow, which cut the
             # "(sitio web: necesita internet)" mark at the right edge; nothing in it is hidden (the page stays 390 px wide)
             '.icon-links{overflow:visible!important}\n'
             '@media (max-width:600px){.lantern-zoom{zoom:var(--lz)}.lantern-zoom .lantern-zoom{zoom:1}}\n'
             'div[style*="position: relative"] img,div[style*="position:relative"] img{max-width:none}\n'
             'body{overflow-wrap:break-word}\n'
             '.printonly{display:none}\n'
             'html:not([dir=rtl]) .rtl-only,html[dir=rtl] .ltr-only{display:none}\n'
             '.carousel-item{display:block!important;float:none!important;margin-right:0!important;'
             'transform:none!important;position:static!important}\n'
             '.carousel-control-prev,.carousel-control-next,.carousel-indicators{display:none!important}\n'
             '</style>\n'
             # on a phone, after load: a fitted table whose cells still hold something wider falls back to a sideways
             # scroll box; then any block that still runs past the right edge (a drawing with captions placed outside
             # its box, a framed text box with margins) is shrunk to fit with zoom, a captioned drawing as one piece
             # (its positioned container), so captions stay on the picture. Local, no request; JS off keeps the CSS.
             '<script id="lantern-phone-js">addEventListener("load",function(){try{var W=document.documentElement.clientWidth;'
             'if(W>600)return;document.querySelectorAll("table.lantern-fit").forEach(function(t){'
             'if(t.scrollWidth>t.clientWidth+2||t.getBoundingClientRect().right>W+2){t.classList.remove("lantern-fit")}});'
             # #218: a float that leaves the text beside it under 150 px (one letter or word a line) stops floating and
             # sits above the text (margins kept: centring pushed drawings with outside captions past the edge); a float that is
             # part of a captioned drawing (positioned container) stays. Before the zoom pass, so zoom fits what is left.
             # Round 9 #248 (b2 B1-B3): the room is what is left beside every float on the same band, so a drawing floated
             # left and another floated right (180 px each on a 374 px column) no longer leave a 1-2 letter column between
             # them; the first stops floating, and its desktop top offset goes (it would lie over the text below it)
             'var FL=[].slice.call(document.body.querySelectorAll("*")).filter(function(e){var p=e.parentElement;'
             'return getComputedStyle(e).cssFloat!=="none"&&p&&!p.closest("[style*=position]")});'
             'var MW=function(e){var s=getComputedStyle(e);return e.getBoundingClientRect().width+(parseFloat(s.marginLeft)||0)+(parseFloat(s.marginRight)||0)};'
             'FL.forEach(function(e){var p=e.parentElement;while(p&&!p.clientWidth)p=p.parentElement;var r=e.getBoundingClientRect(),w=r.width&&MW(e);'
             'if(!p||!w||getComputedStyle(e).cssFloat==="none")return;var pr=p.getBoundingClientRect();FL.forEach(function(f){if(f===e||f.contains(e)||e.contains(f)'
             '||getComputedStyle(f).cssFloat==="none")return;var q=f.getBoundingClientRect();'
             'if(q.width&&q.top<r.bottom-1&&q.bottom>r.top+1&&q.left<pr.right&&q.right>pr.left)w+=MW(f)});'
             'if(p.clientWidth-w<150){e.style.cssFloat="none";if(getComputedStyle(e).position==="relative")e.style.top="0px"}});'
             # and a desktop side padding (a list indented 320 px past a drawing, a heading padded 120 px each side) keeps a
             # phone-sized one: 2.5 em before a list's numbers, 1 em elsewhere (table cells: the CSS above)
             'document.querySelectorAll("#mw-content-text [style*=padding]").forEach(function(l){var s=getComputedStyle(l);'
             'if(/^T[DH]$/.test(l.tagName)||s.position==="absolute")return;["padding-left","padding-right"].forEach(function(k){'
             'if(parseFloat(s.getPropertyValue(k))>48)l.style.setProperty(k,k==="padding-left"&&/^[OU]L$/.test(l.tagName)?"2.5em":"1em","important")})});'
             # round 7 B2-02 (#231): picture labels and speech bubbles placed absolutely (right:525px, left:-50px) sat past
             # the left or right edge, which the page cannot scroll to. Each outermost box that holds them (their
             # offsetParent, or the label itself when that is the page) is measured with everything inside it; if that
             # runs off the screen, its width is fixed in px, it is zoomed to fit (labels stay on the picture) and moved
             # sideways with translateX.
             'var B=[];document.querySelectorAll("#mw-content-text *").forEach(function(e){if(getComputedStyle(e).position!=="absolute")return;'
             'var c=e.offsetParent;if(!c||c===document.body||c===document.documentElement||!c.closest("#mw-content-text"))c=e;if(B.indexOf(c)<0)B.push(c)});'
             # extent: every element box and every line of text (a centred label wider than its box spills past it)
             'var U=function(c){var L=1e9,R=-1e9,F=function(r){if(r.width&&r.height){L=Math.min(L,r.left);R=Math.max(R,r.right)}};'
             '[c].concat([].slice.call(c.querySelectorAll("*"))).forEach(function(e){F(e.getBoundingClientRect())});'
             'var t=document.createTreeWalker(c,4),n,g=document.createRange();while((n=t.nextNode())){if(!n.textContent.trim())continue;'
             'g.selectNodeContents(n);[].forEach.call(g.getClientRects(),F)}return[L,R]};'
             # In a box that scrolls sideways (.lantern-wide, a wide table) only text left of the box is lost (a scroll
             # box cannot scroll to negative overflow): that box's content, or the holder inside it, moves right instead.
             'var T=function(e,x){var k=e.getBoundingClientRect().width/(e.offsetWidth||1)||1,t=getComputedStyle(e).transform,o=t&&t!=="none"?new DOMMatrixReadOnly(t).m41:0;'
             'e.style.setProperty("transform","translateX("+(o+x/k)+"px)","important")};'
             'var FIT=function(){B.forEach(function(c){if(B.some(function(d){return d!==c&&d.contains(c)}))return;var sb=c.closest("table:not(.lantern-fit),pre,.lantern-wide");'
             # (its start side: the right one on a right-to-left page)
             'if(sb){var q=c===sb?[].slice.call(c.children):[c],L=1e9,R=-1e9,br=sb.getBoundingClientRect();q.forEach(function(e){var v=U(e);L=Math.min(L,v[0]);R=Math.max(R,v[1])});'
             'var x=getComputedStyle(sb).direction==="rtl"?Math.min(0,br.right-2-R):Math.max(0,br.left+2-L);if(x)q.forEach(function(e){T(e,x)});return}'
             # the room is the screen, or the box that clips it (a fitted table scrolls, so it clips its left side)
             'var X0=0,X1=W;for(var a=c.parentElement;a&&a!==document.body;a=a.parentElement){if(getComputedStyle(a).overflowX!=="visible"){'
             'var ar=a.getBoundingClientRect();X0=Math.max(X0,ar.left);X1=Math.min(X1,ar.right)}}X0+=2;X1-=2;'
             # The width it is fixed at is the desktop room its labels need: a label placed by right:525px with no width
             # got a few px on a phone (one word a line, labels on top of each other), so the box gets right (or left) +
             # the label's own width (its text on one line, at most 250 px), as on a wide screen.
             'var u=U(c);if(u[0]>=X0-2&&u[1]<=X1+2)return;var s=getComputedStyle(c),D=parseFloat(s.width)||0;'
             'if(s.position!=="absolute")c.querySelectorAll("*").forEach(function(e){if(e.offsetParent!==c||getComputedStyle(e).position!=="absolute")return;'
             'var o=e.style.width,v;if(o)v=e.offsetWidth;else{e.style.width="max-content";v=Math.min(e.offsetWidth,250);e.style.width=o}'
             'var r=/px$/.test(e.style.right)?parseFloat(e.style.right):NaN,l=/px$/.test(e.style.left)?parseFloat(e.style.left):NaN;'
             'D=Math.max(D,r>=0?r+v:l>=0?l+v:0)});c.style.setProperty("width",D+"px","important");'
             # the wiki's .floatright / .floatleft rule is not in the mirrored page, so a drawing meant to sit right of
             # its labels sat under them; inside a label box it floats as on the live site
             'c.querySelectorAll(".floatright,.floatleft").forEach(function(e){e.style.cssFloat=e.classList.contains("floatright")?"right":"left"});'
             # and the box holds those floats and stands on its own line, so text after it is not squeezed beside it
             'if(s.display==="block")c.style.setProperty("display","flow-root","important");c.style.setProperty("float","none","important");u=U(c);'
             # The zoom that fits it (f) stops where its smallest label would go under 9 px on the screen (g, never above
             # the desktop size); then the drawing scrolls sideways in its own box, labels first, instead of shrinking more.
             'var m=99;[c].concat([].slice.call(c.querySelectorAll("*"))).forEach(function(e){if(getComputedStyle(e).position!=="absolute"||!e.textContent.trim())return;'
             'var z=1;for(var a=e;a;a=a.parentElement)z*=parseFloat(getComputedStyle(a).zoom)||1;m=Math.min(m,parseFloat(getComputedStyle(e).fontSize)*z)});'
             'var z0=parseFloat(s.zoom)||1,f=Math.min(1,(X1-X0)/(u[1]-u[0])),g=s.position==="absolute"?f:Math.min(1/z0,Math.max(f,9/m));'
             'if(g!==1)c.style.setProperty("zoom",String(z0*g),"important");'
             'if(g>f){var w=document.createElement("div");w.className="lantern-wide";c.parentNode.insertBefore(w,c);w.appendChild(c);'
             'u=U(c);var wr=w.getBoundingClientRect(),x=getComputedStyle(w).direction==="rtl"?Math.min(0,wr.right-2-u[1]):Math.max(0,wr.left+2-u[0]);if(x)T(c,x);return}'
             'u=U(c);var d=u[0]<X0?X0-u[0]:u[1]>X1?X1-u[1]:0;if(d)T(c,d)})};FIT();'
             # round 9 b2 W12, b5 N3: a picture kept its desktop side margin (margin-right:85px, 25px) once it stopped
             # floating, and the margin alone ran past the screen (8-17 px of sideways scroll): that margin goes
             # (and on a right-to-left page the left margin); run again after the zoom pass below.
             # Round 10 #262 (b2 B3, b5 W8): the margin is in the element's own px and the box in screen px; a zoomed drawing
             # (zoom 0.542, margin-left 140px: 76 px on the screen) lost its margin because 84 - 140 < 0, and its instrument
             # labels at left:-65px then sat at -27 px. The margin is scaled by the element's zoom (k) before the test.
             'var M=function(){[].slice.call(document.querySelectorAll("#mw-content-text *")).forEach(function(e){var r=e.getBoundingClientRect(),s=getComputedStyle(e);'
             'if(!r.width||r.right>W+1||r.left<-1||e.closest("table:not(.lantern-fit),pre,.lantern-wide"))return;var k=r.width/(e.offsetWidth||1)||1;'
             'if(r.right+(parseFloat(s.marginRight)||0)*k>W+1)e.style.setProperty("margin-right","0px","important");'
             'if(r.left-(parseFloat(s.marginLeft)||0)*k<-1)e.style.setProperty("margin-left","0px","important")})};M();'
             # (b2 W7, round 10: on a right-to-left page the overflow is past the left edge, measured from the box's right side)
             'var RTL=getComputedStyle(document.body).direction==="rtl",OUT=function(r){return RTL?r.left<-1:r.right>W+1};'
             'for(var k=0;k<3&&(document.documentElement.scrollWidth>W+1||RTL&&[].some.call(document.body.querySelectorAll("*"),function(e){var r=e.getBoundingClientRect();return r.width&&r.left<-1&&!e.closest("table:not(.lantern-fit),pre,.lantern-wide")}));k++){'
             '[].slice.call(document.body.querySelectorAll("*")).forEach(function(e){var r=e.getBoundingClientRect();'
             'if(!OUT(r)||!r.width||e.closest("table:not(.lantern-fit),pre,.lantern-wide"))return;var p=e.parentElement;if(p&&p!==document.body&&OUT(p.getBoundingClientRect()))return;'
             'var a=e,s=getComputedStyle(e);if(s.position==="absolute"){a=e.offsetParent||e}'
             'var ar=a.getBoundingClientRect(),z=RTL?(ar.right-2)/(ar.right-r.left):(W-ar.left-2)/(r.right-ar.left);'
             'if(z>0.3&&z<1){a.style.zoom=z*(parseFloat(getComputedStyle(a).zoom)||1)}})}M();'
             # round 10 #262: any placed label the margin and zoom passes left before 0 or past the screen is fitted again
             'FIT();'
             '}catch(x){}})</script>\n')
DIV_TAG = re.compile(r'<div\b[^>]*>', re.I)
DIV_ANY = re.compile(r'<(/?)div\b[^>]*>', re.I)
WIDE_PX, ZOOM_MAX_PX, PHONE_PX, GUTTER_PX = 340, 800, 340, 150
PX = lambda prop, style: [int(x) for x in re.findall(r'(?<![-\w])%s\s*:\s*(-?\d+)px' % prop, style)]
STYLE = re.compile(r'\sstyle=(["\'])(.*?)\1', re.S)


def mark_wide_divs(text, stats):
    """Labelled drawings (a fixed-width or position:relative div with absolutely placed captions) are what make Hesperian
    pages wider than a phone. Extent E = the div's own left/margin-left + max(its width, every absolute child's
    left + width). E <= PHONE_PX and a child sticks out: min-width E (the box holds its captions). E up to ZOOM_MAX_PX:
    class lantern-zoom, --lz = PHONE_PX/E, and on a phone (CSS below) the drawing and its captions shrink together, so
    nothing is cut off or trapped in an inner scroll box; a wide screen keeps the size. Wider (the 4,000 px tooth strip):
    lantern-wide, it scrolls sideways inside the page. Earlier markings are stripped and recomputed: idempotent."""
    out, last = [], 0
    for m in DIV_TAG.finditer(text):
        tag = m.group(0)
        clean = re.sub(r'\sclass="lantern-(?:wide|zoom|gutter)"', "", re.sub(r" lantern-(?:wide|zoom|gutter)\b", "", tag))
        clean = re.sub(r"\s*--lz:[0-9.]+;?|\s*--lm:\d+px;\s*min-width:var\(--lm\);?", "", clean)
        st = STYLE.search(clean)
        style = st.group(2) if st else ""
        w = (PX("width", style) or [0])[0]
        child, lo = 0, 0
        if re.search(r"position\s*:\s*relative", style):
            depth, end = 0, len(text)
            for t in DIV_ANY.finditer(text, m.start()):
                depth += -1 if t.group(1) else 1
                if depth == 0:
                    end = t.start(); break
            for cm in DIV_TAG.finditer(text, m.end(), end):
                cs = STYLE.search(cm.group(0))
                if cs and re.search(r"position\s*:\s*absolute", cs.group(2)) and PX("width", cs.group(2)):
                    child = max(child, (PX("left", cs.group(2)) or [0])[0] + PX("width", cs.group(2))[0])
                    lo = min(lo, (PX("left", cs.group(2)) or [0])[0])
        if not w and not child:
            new = clean
        else:
            # own offsets count when positive (the phone style zeroes a negative margin and a relative left); round 10
            # #262: a label placed left of the box (left:-65px) past the box's own offset widens the extent too
            own = sum(max(0, x) for x in PX("left", style) + PX("margin-left", style))
            e = own + max(w, child) - min(0, own + lo)
            new, cls, add = clean, None, ""
            if e > ZOOM_MAX_PX:
                cls = "lantern-wide"
            elif e > WIDE_PX:
                cls, add = "lantern-zoom", f" --lz:{round(PHONE_PX / e, 3)};"
            elif child > w:
                add = f" --lm:{child}px; min-width:var(--lm);"
            if add:
                st = STYLE.search(new)
                if st:
                    sep = "" if st.group(2).rstrip().endswith(";") or not st.group(2).strip() else ";"
                    new = new[:st.end(2)] + sep + add + new[st.end(2):]
                else:
                    new = new[:4] + f' style="{add.strip()}"' + new[4:]
            if cls:
                c = re.search(r'\sclass=(["\'])(.*?)\1', new)
                new = new[:c.end(2)] + " " + cls + new[c.end(2):] if c else new[:4] + f' class="{cls}"' + new[4:]
        # #218: a desktop gutter (margin-right:350px beside a floated picture, padding-left:325px under a drawing) left
        # 0-9 px for the text on a phone; class lantern-gutter drops it at phone width
        if max(PX("margin-left", style) + PX("margin-right", style) + PX("padding-left", style) + PX("padding-right", style) or [0]) >= GUTTER_PX:
            c = re.search(r'\sclass=(["\'])(.*?)\1', new)
            new = new[:c.end(2)] + " lantern-gutter" + new[c.end(2):] if c else new[:4] + ' class="lantern-gutter"' + new[4:]
        if new != tag:
            stats["drawing_div_remarked"] += 1
        out.append(text[last:m.start()]); out.append(new); last = m.end()
    out.append(text[last:])
    return "".join(out)


TABLE_TAG = re.compile(r'<table\b[^>]*>', re.I)
TABLE_ANY = re.compile(r'<(/?)table\b[^>]*>', re.I)
INNER_TABLE = re.compile(r'<table\b[^>]*>(?:(?!<table\b).)*?</table\s*>', re.I | re.S)
ROW = re.compile(r'<tr\b.*?(?=<tr\b|$)', re.I | re.S)
CELL = re.compile(r'<t[dh]\b(?:[^>]*\bcolspan=["\']?(\d+))?[^>]*>', re.I)
CELL_START = re.compile(r'<t[dh]\b', re.I)
FIT_COLS = 3


def table_own(text, start):
    """the table's own rows: its markup up to the matching </table>, each nested table cut to a <tablecut> marker"""
    depth, end = 0, len(text)
    for t in TABLE_ANY.finditer(text, start):
        depth += -1 if t.group(1) else 1
        if depth == 0:
            end = t.start(); break
    inner, prev = text[text.index(">", start) + 1:end], None
    while prev != inner:
        prev, inner = inner, INNER_TABLE.sub(" <tablecut> ", inner)
    return inner


def mark_fit_tables(text, stats):
    """a table of at most FIT_COLS columns (the poisoning tables: kind / signs / what to do) gets class lantern-fit:
    fixed layout at 100 percent width, so every column, the "what to do" one included, shows on a phone instead of
    sitting off the right edge; wider tables (chemical charts) scroll inside the page. Columns are counted on every
    row, not the first: a later colspan=6 row adds columns to a fixed layout and left the text 7 px (red team 10-20 b2
    F1, #218). A fitted table with pictures also gets lantern-stack (on a phone its cells stack, picture above text,
    instead of a picture keeping its width beside a 7-15 px text column, #218), unless it is a picture grid (a row of
    only pictures and a row of only text: stacking would part pictures from their captions). Earlier marks are
    stripped and recomputed: idempotent."""
    out, last = [], 0
    for m in TABLE_TAG.finditer(text):
        tag = m.group(0)
        clean = re.sub(r"\s+lantern-(?:fit|stack)\b", "", re.sub(r'\sclass="lantern-(?:fit|stack)(?: lantern-(?:fit|stack))?"', "", tag))
        own = table_own(text, m.start())
        cols, pics, words, first = 0, False, False, None
        for row in ROW.findall(own):
            n = sum(int(c or 1) for c in CELL.findall(row))
            first = n if first is None else first
            cols = max(cols, n)
            cells = [(("<img" in x), len(re.sub(r"<[^>]+>|&#?\w+;|\s", "", x)) > 15) for x in CELL_START.split(row)[1:]]
            pics |= any(i and not t for i, t in cells) and not any(t for i, t in cells)
            words |= any(t for i, t in cells) and not any(i for i, t in cells)
        add = []
        # a fixed layout takes its columns from the first row: a first row that spans fewer columns than a later one
        # (colspan=2 over a 3-column table) left 79 px columns, so such a table keeps the auto layout (rt6 ht page)
        if 0 < cols <= FIT_COLS and first == cols:
            add.append("lantern-fit")
            if ("<img" in own or "<tablecut>" in own) and not (pics and words):   # a nested table is layout, not a picture
                add.append("lantern-stack")
        new = clean
        if add:
            c = re.search(r'\sclass=(["\'])(.*?)\1', new)
            new = new[:c.end(2)] + " " + " ".join(add) + new[c.end(2):] if c else new[:6] + ' class="%s"' % " ".join(add) + new[6:]
            stats["table_fit_marked"] += 1
            stats["table_stack_marked"] += len(add) - 1
        if new != tag:
            stats["table_remarked"] += 1
        out.append(text[last:m.start()]); out.append(new); last = m.end()
    out.append(text[last:])
    return "".join(out)


PRINTONLY = re.compile(r'<(h1) class="printonly"')
EDITLINKS = re.compile(r'<(li) class="interwiki-interlanguage"')
LIVE_FORM = re.compile(r'<(form)\b[^>]*\saction=(["\'])/(?:hhg|w)/')
DIR_SPAN = {False: re.compile(r'<span class="rtl-only">[^<]*</span>'), True: re.compile(r'<span class="ltr-only">[^<]*</span>')}
DEAD_SCRIPT = re.compile(r"ga\('send'|surveymonkey|window\.location\.href\s*=\s*[\"']https?://|email-decode\.min\.js", re.I)
ROOT_IMPORT = re.compile(r"@import url\('/resources/core/fonts/fonts\.css'\);")
SURVEY_A = re.compile(r'<a\b[^>]*surveymonkey[^>]*>.*?</a>', re.I | re.S)   # the survey's credit link (unquoted href=www...)
UPLOAD_A = re.compile(r'<a\b[^>]*\shref=(["\'])[^"\']*Special:Upload[^"\']*\1[^>]*>[^<]*</a>', re.I)
BUY_A = re.compile(r'<a\b(?=[^>]*\sclass=(["\'])[^"\']*\b(?:btn|avia-button)\b[^"\']*\1)(?=[^>]*\shref=(["\'])https?://store\.'
                   r'hesperian\.org[^"\']*\2)[^>]*>.*?</a>\s*', re.I | re.S)
STORE_A = re.compile(r'(<a\b[^>]*?\shref=)(["\'])(https?://store\.hesperian\.org/[^"\']*)\2([^>]*>)((?:(?!</?a\b).)*?)(</a>)', re.I | re.S)
NOT_A_BOOK = re.compile(r"bookstore|\bbuy\b|order|purchase|comprar|tienda|pedido|acheter|achte", re.I)
_EN, _ES = "en.hesperian.org/hhg/", "es.hesperian.org/hhg/"
STORE_BOOK = {   # store product (lower case, no .html) -> (cover for pages outside es, cover for es pages)
    "where_there_is_no_doctor": (_EN + "New_Where_There_Is_No_Doctor.html", _ES + "Nuevo_Donde_no_hay_doctor.html"),
    "where-there-is-no-doctor": (_EN + "New_Where_There_Is_No_Doctor.html", _ES + "Nuevo_Donde_no_hay_doctor.html"),
    "where_there_is_no_doctor_spanish": (_ES + "Nuevo_Donde_no_hay_doctor.html",) * 2,
    "where_women_have_no_doctor": (_EN + "Where_Women_Have_No_Doctor.html", _ES + "Donde_no_hay_doctor_para_mujeres.html"),
    "where_women_have_no_doctor_spanish": (_ES + "Donde_no_hay_doctor_para_mujeres.html",) * 2,
    "a_book_for_midwives": (_EN + "A_Book_for_Midwives.html", _ES + "Un_libro_para_parteras.html"),
    "health_actions_for_women": (_EN + "Health_Actions_for_Women.html",
                                 _ES + "Guía_práctica_para_promover_la_salud_de_las_mujeres.html"),
    "helping_children_who_are_deaf": (_EN + "Helping_Children_Who_Are_Deaf.html", _ES + "Ayudar_a_los_niños_sordos.html"),
    "helping_children_who_are_blind": (_EN + "Helping_Children_Who_Are_Blind.html", _ES + "Ayudar_a_los_niños_ciegos.html"),
    "helping_children_live_with_hiv": (_EN + "Helping_Children_Live_with_HIV.html",) * 2,
    "disabled_village_children": (_EN + "Disabled_Village_Children.html", _ES + "El_niño_campesino_deshabilitado.html"),
    "community_guide_to_environmental_health": (_EN + "A_Community_Guide_to_Environmental_Health.html",
                                                _ES + "Guía_comunitaria_para_la_salud_ambiental.html"),
}
REL_HREF = re.compile(r'(<a\b[^>]*?\shref=)(["\'])([^"\'#?:]+)(#[^"\']*)?\2', re.I)


def store_local(text, fpath, mirror, stats):
    es = "/es.hesperian.org/" in fpath.replace(os.sep, "/")
    here = os.path.dirname(fpath)

    def sub(m):
        key = htmlmod.unescape(m.group(3)).split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1].lower()
        key = key[:-5] if key.endswith(".html") else key
        inner = m.group(5)
        if key not in STORE_BOOK or NOT_A_BOOK.search(re.sub(r"<[^>]+>", " ", inner)):
            return m.group(0)
        t = os.path.join(mirror, STORE_BOOK[key][1 if es else 0])
        if not os.path.isfile(t):
            stats["store_cover_missing"] += 1; return m.group(0)
        stats["store_to_local_cover"] += 1
        for mk in (ES_MARK, EN_MARK):
            inner = inner.replace(mk, "")
        return f"{m.group(1)}{m.group(2)}{quote(os.path.relpath(t, here), safe='/')}{m.group(2)}{m.group(4)}{inner}{m.group(6)}"
    return STORE_A.sub(sub, text)


def html_suffix(text, fpath, stats):
    here = os.path.dirname(fpath)

    def sub(m):
        path = unquote(htmlmod.unescape(m.group(3)))
        t = os.path.normpath(os.path.join(here, path))
        if os.path.exists(t) or not os.path.isfile(t + ".html"):
            return m.group(0)
        stats["rel_link_html_added"] += 1
        return f"{m.group(1)}{m.group(2)}{m.group(3)}.html{m.group(4) or ''}{m.group(2)}"
    return REL_HREF.sub(sub, text)


# red team 10-20 b2 F4: on a Spanish page, a needs-internet link to hesperian.org (the resources-in-spanish list, the
# order page, the chapter PDF) whose text names a Spanish book mirrored here points at the book's local cover instead
ES_BOOK = ("El niño campesino deshabilitado", "Ayudar a los niños ciegos", "Ayudar a los niños sordos",
           "Donde no hay doctor para mujeres", "Donde no hay dentista", "Un libro para parteras",
           "Guía comunitaria para la salud ambiental",
           "Donde no hay doctor")   # round 7 B2-03: last, after "... para mujeres"; any case ("Donde No Hay Doctor")
ES_BOOK_FILE = {"Donde no hay doctor": "Nuevo_Donde_no_hay_doctor.html"}   # the current edition's cover
# round 7 B2-03: "hesperain.org" is a typo in one source link, the same resources page
HESP_A = re.compile(r'(<a\b[^>]*?\shref=)(["\'])(https?://(?:www\.)?hesper(?:ian|ain)\.org/[^"\']*)\2([^>]*>)((?:(?!</?a\b).)*?)(</a>)',
                    re.I | re.S)
# b2 F5: the live-site "Tell us what you think" button (its page is two Google Docs links) goes
TELLUS_A = re.compile(r'<a\b[^>]*\bclass=(["\'])linkbutton tellus\1[^>]*>.*?</a>\s*', re.I | re.S)
# round 7 B2-05: the French Environmental Health cover has the same button as a plain link around En_tellus.png
TELLUS_IMG_A = re.compile(r'<a\b[^>]*>\s*<img\b[^>]*\bsrc=["\'][^"\']*_tellus\.png["\'][^>]*>[^<]*</a>\s*', re.I)
# round 7 B2-06: a live Google Forms survey (data-src only, so a 442 px blank box offline) on the English Mpox pages
GFORM_IFRAME = re.compile(r'<iframe\b[^>]*docs\.google\.com/forms[^>]*>.*?</iframe\s*>\s*', re.I | re.S)
# b2 F6: the pregnancy / breastfeeding cautions are drawings on the live site; offline their English alt text showed
# in every drug heading of 4 Spanish medicine lists. Spanish in Hesperian's own words where Hesperian has them
# ("no deben tomar esta medicina", Un libro para parteras, Lista de medicinas), and a library note says so.
CAUTION_ES = {"Pregnant women need to take special care": "Las mujeres que están embarazadas deben tener un cuidado especial con esta medicina",
              "Breastfeeding women need to take special care": "Las mujeres que están dando el pecho deben tener un cuidado especial con esta medicina",
              "Pregnant women should not take this medicine": "Las mujeres que están embarazadas no deben tomar esta medicina",
              "Breastfeeding women should not take this medicine": "Las mujeres que están dando el pecho no deben tomar esta medicina"}
CAUTION_GUARD = "los avisos para mujeres embarazadas o que dan pecho venían en inglés"


def es_hhg(fpath):
    f = fpath.replace(os.sep, "/")
    i = f.find("/es.hesperian.org/hhg/")
    return f[:i + len("/es.hesperian.org/hhg")] if i >= 0 else None


def es_book_local(text, fpath, stats):
    root = es_hhg(fpath)
    if not root:
        return text
    here = os.path.dirname(fpath)

    def sub(m):
        inner = m.group(5)
        name = unicodedata.normalize("NFC", re.sub(r"<[^>]+>", "", inner)).strip()
        book = next((b for b in ES_BOOK if name.lower().startswith(b.lower())), None)
        if not book or ES_MARK not in inner:
            return m.group(0)
        t = os.path.join(root, ES_BOOK_FILE.get(book, book.replace(" ", "_") + ".html"))
        if not os.path.isfile(t):
            stats["es_book_cover_missing"] += 1; return m.group(0)
        stats["es_book_to_local_cover"] += 1
        return f"{m.group(1)}{m.group(2)}{quote(os.path.relpath(t, here), safe='/')}{m.group(2)}{m.group(4)}{inner.replace(ES_MARK, '').replace(' (pdf)', '')}{m.group(6)}"
    return HESP_A.sub(sub, text)


def es_cautions(text, fpath, stats):
    root = es_hhg(fpath)
    if not root or not any(en in text for en in CAUTION_ES):
        return text
    for en, es in CAUTION_ES.items():
        stats["caution_es"] += text.count(en)
        text = text.replace(en, f" {es}. ")
    if CAUTION_GUARD not in text:
        m = re.search(r'<div class="mw-parser-output">', text)
        if m:
            src = quote(os.path.relpath(os.path.join(root, "A_Book_for_Midwives:Lista_de_medicinas.html"), os.path.dirname(fpath)), safe="/")
            note = (f'<p class="library-note"><b>Nota de la biblioteca:</b> en esta página {CAUTION_GUARD} (en el sitio de '
                    f'Hesperian son dibujos). Aquí están en español, con las palabras de Hesperian («no deben tomar esta '
                    f'medicina», <a href="{src}">Un libro para parteras, Lista de medicinas</a>).</p>\n')
            text = text[:m.end()] + note + text[m.end():]; stats["caution_note_added"] += 1
    return text


# red team 10-25 b2 F2 F3 (#241): a marked link whose page IS mirrored ("Workers' Guide ... (website: needs internet)",
# the hesperian.org topic buttons to /mental-health/ ...) points at the local page and loses its mark. The LINK pass
# could not take these: an apostrophe in the URL ended its match, and /mental-health/ is saved as mental-health.html.
# Exact on-disk names (the Pi is case-sensitive). /donate/ stays marked: the donation form itself needs internet.
# b2 F1: on a Spanish page, a link into the English tree whose text names a Spanish book on the box opens that book.
ANY_EXT_A = re.compile(r'(<a\b[^>]*?\shref=)(?:"(https?://[^"]*)"|\'(https?://[^\']*)\')([^>]*>)((?:(?!</?a\b).)*?)(</a>)', re.I | re.S)
EN_TREE_A = re.compile(r'(<a\b[^>]*?\shref=)(["\'])((?:\.\./)+en\.hesperian\.org/hhg/[^"\'#]*)\2([^>]*>)((?:(?!</?a\b).)*?)(</a>)', re.I | re.S)
_LS = {}


def exact_file(p):
    d, f = os.path.split(p)
    if d not in _LS:
        _LS[d] = set(os.listdir(d)) if os.path.isdir(d) else set()
    return f in _LS[d]


_PDF = {}


def local_pdf(mirror, name):
    """round 9 b2 W2: a Hesperian PDF the library keeps under docs/medical/hesperian*/ (one file of that name); round 10
    b2 W1: or one the org mirror holds in another folder (wp-content/uploads/pdf/en_misc/en_hclhiv_2019_05.pdf for a link
    to …/pdf/en_hclhiv_2019/en_hclhiv_2019_05.pdf), again only a name that is one file there"""
    if not _PDF:
        docs = os.path.join(os.path.dirname(os.path.dirname(mirror.rstrip("/"))), "docs", "medical")
        seen = Counter()
        for d in sorted(os.listdir(docs)) if os.path.isdir(docs) else []:
            if d.startswith("hesperian") and os.path.isdir(os.path.join(docs, d)):
                for f in os.listdir(os.path.join(docs, d)):
                    if f.lower().endswith(".pdf"):
                        seen[f] += 1
                        _PDF[f] = os.path.join(docs, d, f)
        for f, n in seen.items():
            if n > 1:
                del _PDF[f]
        up, seen = os.path.join(mirror, "hesperian.org", "wp-content", "uploads", "pdf"), Counter()
        found = {}
        for dp, _, fs in os.walk(up):
            for f in fs:
                if f.lower().endswith(".pdf"):
                    seen[f] += 1; found[f] = os.path.join(dp, f)
        for f, n in seen.items():
            if n == 1:
                _PDF.setdefault(f, found[f])
        _PDF.setdefault("", None)
    return _PDF.get(name)


def mirrored_page(mirror, url):
    from urllib.parse import urlsplit, parse_qsl
    u = urlsplit(htmlmod.unescape(url))
    host = (u.hostname or "").lower()
    path = unquote(u.path)
    # round 9 b2 W1: the wiki's other URL forms for a page on the box: www.<host>, the editors' <lang>.dev.hesperian.org,
    # /w/index.php?title=Page (with or without a _gl= / utm_ tracking tail)
    host = re.sub(r"^www\.(?=[a-z]+\.hesperian\.org$)", "", host).replace(".dev.hesperian.org", ".hesperian.org")
    q = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True) if k != "_gl" and not k.startswith("utm_")]
    if path in ("/w/index.php", "/index.php") and len(q) == 1 and q[0][0] == "title" and q[0][1]:
        path, q = "/hhg/" + q[0][1], []
    hd = os.path.join(mirror, host)
    if host == "hesperian.org" and not q and path.lower().endswith(".pdf") and \
            not os.path.isfile(os.path.join(hd, path.strip("/"))) and local_pdf(mirror, os.path.basename(path)):
        return local_pdf(mirror, os.path.basename(path)), ""
    if q or not host or not os.path.isdir(hd) or not path.strip("/") or path.rstrip("/") == "/donate":
        return None
    if path.startswith("/hhg/"):
        # round 10 b2 W1: a broken wiki link kept its label ("…Pregnancy%7Cmalaria" is Page|label)
        t = path[5:].split("|", 1)[0].replace(" ", "_")
        cands = [os.path.join(hd, "hhg", x + ".html") for x in (t, t.replace(":", "%3A"))]
    else:
        p = os.path.join(hd, path.strip("/"))
        cands = [p, p + "/index.html", p + ".html"] if not path.endswith("/") else [p + "/index.html", p + ".html"]
    t = next((c for c in cands if exact_file(c) and os.path.isfile(c)), None)
    return t and (t, "#" + u.fragment if u.fragment else "")


def local_targets(text, fpath, mirror, stats):
    here = os.path.dirname(fpath)

    def ext(m):
        hit = mirrored_page(mirror, m.group(2) or m.group(3))
        if not hit:
            return m.group(0)
        t, frag = hit
        inner = m.group(5)
        for mk in MARKED:
            inner = inner.replace(mk, "")
        stats["marked_link_to_local"] += 1
        return f'{m.group(1)}"{quote(os.path.relpath(t, here), safe="/")}{htmlmod.escape(frag)}"{m.group(4)}{inner}{m.group(6)}'
    text = ANY_EXT_A.sub(ext, text)
    root = es_hhg(fpath)
    if root:
        def en_tree(m):
            name = unicodedata.normalize("NFC", re.sub(r"<[^>]+>", "", m.group(5))).strip()
            book = next((b for b in ES_BOOK if name.lower().startswith(b.lower())), None)
            t = book and os.path.join(root, ES_BOOK_FILE.get(book, book.replace(" ", "_") + ".html"))
            if not t or not os.path.isfile(t):
                return m.group(0)
            stats["es_link_to_es_book"] += 1
            return f"{m.group(1)}{m.group(2)}{quote(os.path.relpath(t, here), safe='/')}{m.group(2)}{m.group(4)}{m.group(5)}{m.group(6)}"
        text = EN_TREE_A.sub(en_tree, text)
    return text


# round 10 b2 W2 (#274): a fragment link whose anchor is not on the target page landed at the page top (ES 357 links on 191
# pages, EN 488, other trees 161, org site 98). The anchor is looked up again: the same id written another way (the wiki's
# old ".28" escapes, case, "_" for a space), one letter off (#gentamycin -> gentamicin), then the same id on one other
# page of the same book; else the fragment goes (a link to the page itself, an alphabet letter with no entries, becomes
# plain text, and its entry in the phone's jump menu goes).
FRAG_A = re.compile(r'(<a\b[^>]*?\shref=)(["\'])((?![a-zA-Z][a-zA-Z+.-]*:|//)(?:(?!\2)[^#>])*)#((?:(?!\2)[^>])*)\2([^>]*>)((?:(?!</?a\b).)*?)(</a>)', re.I | re.S)
ID_ATTR = re.compile(r'\b(?:id|name)="([^"]+)"')
FRAG_OPT = re.compile(r'[ \t]*<option value="#([^"]+)">[^<]*</option>\n?')
_IDS, _BOOK = {}, {}


def anchor_key(x):
    x = htmlmod.unescape(x)
    x = unquote(re.sub(r"\.([0-9A-Fa-f]{2})", r"%\1", x)) if re.search(r"\.[0-9A-F]{2}", x) else unquote(x)
    return unicodedata.normalize("NFC", x).replace(" ", "_").lower()


def page_ids(p, text=None):
    """(the page's ids as written, {anchor_key(id): id})"""
    if text is not None or p not in _IDS:
        t = text if text is not None else open(p, "rb").read().decode("utf-8", "replace")
        raw = ID_ATTR.findall(t)
        d = (set(raw), {})
        for i in raw:
            d[1].setdefault(anchor_key(i), i)
        if text is not None:
            return d
        _IDS[p] = d
    return _IDS[p]


def one_off(a, b):
    if abs(len(a) - len(b)) > 1 or a == b:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    s, l = (a, b) if len(a) < len(b) else (b, a)
    return any(l[:i] + l[i + 1:] == s for i in range(len(l)))


def fix_fragments(text, fpath, stats):
    here = os.path.dirname(fpath)
    own = page_ids(fpath, text)

    def sub(m):
        path, frag = m.group(3), m.group(4)
        if not frag or frag == "top":
            return m.group(0)
        t = os.path.normpath(os.path.join(here, unquote(htmlmod.unescape(path)))) if path else fpath
        if not t.endswith(".html") or not os.path.isfile(t):
            return m.group(0)
        raw, ids = own if t == fpath else page_ids(t)
        k = anchor_key(frag)
        if frag in raw or htmlmod.unescape(frag) in raw or unquote(htmlmod.unescape(frag)) in raw:
            return m.group(0)
        hit = ids.get(k)
        if not hit and len(k) >= 5:
            near = {v for kk, v in ids.items() if one_off(kk, k)}
            hit = near.pop() if len(near) == 1 else None
        href = path
        if hit:
            stats["fragment_respelled"] += 1
        else:
            d, name = os.path.split(t)
            book = unicodedata.normalize("NFC", name[:-5]).split(":", 1)[0]
            if (d, book) not in _BOOK:
                _BOOK[(d, book)] = [os.path.join(d, x) for x in sorted(os.listdir(d)) if x.endswith(".html") and
                                    unicodedata.normalize("NFC", x[:-5]).split(":", 1)[0] == book]
            # (not an alphabet letter: "#s" on another glossary of the book is another list's S)
            others = [p for p in _BOOK[(d, book)] if p != t and k in page_ids(p)[1]] if len(k) >= 3 else []
            if len(others) == 1:
                hit = page_ids(others[0])[1][k]
                href = quote(os.path.relpath(others[0], here), safe="/")
                stats["fragment_to_other_page"] += 1
            elif not path:
                stats["fragment_self_unlinked"] += 1
                return m.group(6)
            else:
                stats["fragment_dropped"] += 1
                return f"{m.group(1)}{m.group(2)}{path}{m.group(2)}{m.group(5)}{m.group(6)}{m.group(7)}"
        return f"{m.group(1)}{m.group(2)}{href}#{htmlmod.escape(quote(hit, safe='-._~:!$()*,;=@/?'))}{m.group(2)}{m.group(5)}{m.group(6)}{m.group(7)}"
    text = FRAG_A.sub(sub, text)

    def opt(m):   # the phone's alphabet jump menu offers the same letters
        if m.group(1) in own[0] or anchor_key(m.group(1)) in own[1]:
            return m.group(0)
        stats["fragment_option_dropped"] += 1; return ""
    return FRAG_OPT.sub(opt, text)


# round 10 b2 W3 (#274): wiki markup the live wiki failed to render shows as text ([[#chemical|"Envenenamiento…" ], an
# [[Image:…|alt=…]] whose picture never rendered, {{HowToBox|Cómo hacer un corsé de plástico| … }}, {{spannote|||,
# "Plantilla:Importante"): an anchor link keeps its label, a box title becomes a heading, the rest goes.
WIKI_LEFT = [(re.compile(r'\[\[#[^|\]<]*\|([^\]<]*)\]{0,2}'), r"\1"),
             (re.compile(r'\[\[(?:Image|File|Imagen|Archivo):[^<\n]*'), ""),
             (re.compile(r'<p>\{\{HowToBox\|([^|<]*)\|\s*</p>'), r'<h4 class="library-howto">\1</h4>'),
             (re.compile(r'<p>(?:\{\{\w+\|*|\}\}|\]\])\s*</p>\s*'), ""),
             (re.compile(r'<p>(?:Plantilla|Template):[^<]*</p>\s*'), "")]
# and on Spanish pages, English the wiki left in the text (b2 W3 broken-link labels; W4 lines with a Spanish twin go, three
# with none get Hesperian-style Spanish and a library note saying so)
ES_TR = ' <span class="library-note">(traducción de la biblioteca: en el sitio de Hesperian esta línea venía en inglés)</span>'
ES_LEFT = [("usted debe:misoprostol]]", "usted debe:"),
           (" prolapse]] when the waters break.", "."),
           ("otras personas.antibiotic eye ointment or drops]].", "otras personas."),
           ("prevenir el sangrado]] después", "prevenir el sangrado después"),
           (" doses for children]].", ""),
           (" dislocated jaw]].", ""),
           ("<p>If you get a little chemical on you and wash it off very quickly, this may not be much exposure. If you are splashed "
            "with a chemical and breathe it, this may be a lot of exposure. Different chemicals are dangerous in different amounts.\n</p>", ""),
           ('<h4><span class="mw-headline" id="Prevent_or_reduce_exposure:">Prevent or reduce exposure:</span></h4>\n', ""),
           ("<p>If you do not have good results with omeprazole, try a different PPI instead.\n</p>",
            "<p>Si no obtiene buenos resultados con el omeprazol, pruebe otro IBP." + ES_TR + "\n</p>"),
           ("<p><b>kidneys</b> Two large organs in the lower back that make urine by cleaning waste from the blood. \n</p>",
            "<p><b>riñones</b> Dos órganos grandes en la parte baja de la espalda que producen la orina al limpiar la sangre de "
            "desechos." + ES_TR + "\n</p>"),
           ("<p><b>Weight-bearing</b> Supporting the weight of the body on a particular joint or limb. For example, weight-bearing on "
            "the knee is possible if the strength of the thigh muscle is good, but not if it is poor.\n</p>",
            "<p><b>Apoyar el peso</b> Sostener el peso del cuerpo sobre una coyuntura o un miembro. Por ejemplo, se puede apoyar el "
            "peso sobre la rodilla si el músculo del muslo tiene buena fuerza, pero no si está débil." + ES_TR + "\n</p>")]


def wiki_leftovers(text, fpath, stats):
    m = re.search(r'<div id="mw-content-text".*?(?=<!-- /bodytext -->|$)', text, re.S)
    if not m:
        return text
    b = m.group(0)
    for rx, to in WIKI_LEFT:
        b, n = rx.subn(to, b); stats["wiki_markup_fixed"] += n
    if es_hhg(fpath):
        for en, es in ES_LEFT:
            stats["es_english_left_fixed"] += b.count(en); b = b.replace(en, es)
    return text[:m.start()] + b + text[m.end():]


P_LANG = '<div id="p-lang" class="noprint navigation-not-searchable">'


def phone_and_leftovers(text, fpath, mirror, stats):
    text = fix_fragments(local_targets(text, fpath, mirror, stats), fpath, stats)
    # round 9 #207 (b5 W6): the "In other languages" switch is page chrome, not text: search does not index it
    text, n = re.subn(re.escape(P_LANG), P_LANG[:-1] + ' data-pagefind-ignore="all">', text); stats["lang_switch_unindexed"] += n
    # round 9 b2 N4: on a Spanish page the not-mirrored mark is in Spanish
    if "/es.hesperian.org/" in fpath.replace(os.sep, "/"):
        text, n = re.subn(re.escape(NOT_MIRRORED), NOT_MIRRORED_ES, text); stats["not_mirrored_es"] += n
    if "skin-hhgskin" in text:
        text = drop_el(text, PRINTONLY, stats, "printonly_dropped")
        text = drop_el(text, EDITLINKS, stats, "edit_links_dropped")
        text = store_local(text, fpath, mirror, stats)
        text = wiki_leftovers(es_cautions(es_book_local(text, fpath, stats), fpath, stats), fpath, stats)
    text, n = TELLUS_A.subn("", text); stats["feedback_button_dropped"] += n
    text, n = TELLUS_IMG_A.subn("", text); stats["feedback_button_dropped"] += n
    text, n = GFORM_IFRAME.subn("", text); stats["google_form_dropped"] += n
    rtl = bool(re.search(r'<html\b[^>]*\sdir=["\']?rtl', text, re.I))
    text, n = DIR_SPAN[rtl].subn("", text); stats["other_direction_arrow_dropped"] += n
    text = drop_el(text, LIVE_FORM, stats, "live_wiki_form_dropped")
    text, n = UPLOAD_A.subn("", text); stats["upload_link_dropped"] += n
    text, n = SURVEY_A.subn("", text); stats["survey_link_dropped"] += n

    def script(m):
        if not DEAD_SCRIPT.search(m.group(0)):
            return m.group(0)
        stats["dead_script_dropped"] += 1; return ""
    text = SCRIPT_EL.sub(script, text)
    text, n = ROOT_IMPORT.subn("", text); stats["root_import_dropped"] += n
    text, n = BUY_A.subn("", text); stats["buy_button_dropped"] += n
    text = mark_fit_tables(mark_wide_divs(html_suffix(text, fpath, stats), stats), stats)
    old = re.search(r'<style id="lantern-phone">.*?</style>\n(?:<script id="lantern-phone-js">.*?</script>\n)?', text, re.S)
    if old and old.group(0) != PHONE_CSS:   # an older version of the style: replace it
        text = text[:old.start()] + PHONE_CSS + text[old.end():]; stats["phone_style_updated"] += 1
    elif not old:
        # not text.lower().find(): lower() lengthens "İ" (Turkish), the index drifted and split "</head>" (r31 t4, 4 tr pages)
        m = re.search(r"</head>", text, re.I)
        if m:
            text = text[:m.start()] + PHONE_CSS + text[m.start():]; stats["phone_style_added"] += 1
    return text


# red team 10-25 b5 W2 (#122 regression): --strip-external took out every remote <script src>, but inline scripts that
# build one at run time stayed (GTM, gtag, Pinterest, The Trade Desk, the Facebook / Twitter / Google+ SDKs, Google CSE,
# AdSense, reCAPTCHA, ga.js via document.write) and so did a local file that only injects Siteimprove: offline they fail
# silently, with any internet they phone home. --scrub, every mirror: such an inline script goes, a local script file
# under 8 KB that only does tracking goes (Drupal's google_analytics.js calls gtag, which goes with it), and a <noscript>
# tracker pixel or frame goes. A same-site absolute URL inside an inline script (the Harris logo rollover, a
# window.location to a mirrored page) points at the local copy. a7b W11 / a7a note 9: the .gov banner's lock drawing
# carries <title>Lock</title>; indexers read every <title>, so Ready.gov pages were titled "... | Ready.govLock". The
# drawing keeps its <desc> (aria-labelledby names both). Page text and layout are untouched (fix_m5_runtime.py).
SCRUB_JS = re.compile(r"googletagmanager|google-analytics|\bgtag\(|\bdataLayer\b|\b_gaq\b|GoogleAnalyticsObject|pintrk|siteimprove|"
                      r"TTDUniversalPixelApi|ttd_dom_ready|connect\.facebook\.net|facebook-jssdk|<fb:|platform\.twitter\.com|"
                      r"apis\.google\.com/js|\bgcse\b|googlesyndication|dmRosAds|recaptcha|wp-emoji|_wpemojiSettings|\b_jaSkin\b|jalbum\.net", re.I)
SCRUB_NOSCRIPT = re.compile(r"googletagmanager|google-analytics|/akam/\d+/pixel_|geo\.yahoo\.com|facebook\.com/tr\b", re.I)
LOCK_TITLE = re.compile(r'<title id="banner-lock-title">Lock</title>')
LOCAL_IMG = []   # the local pictures named in the inline script being scrubbed
LOCAL_IMG_RE = re.compile(r'["\']((?![a-zA-Z][a-zA-Z+.-]*:|//)[^"\'\s<>]+\.(?:gif|jpe?g|png))["\']', re.I)
NO_IMG = "data:,"   # an empty data URL: no request, and the picture shows its alt text as it did before the hover
JS_URL = re.compile(r'(["\'])https?://([a-z0-9.-]+)/([^"\'\s<>]*\.(?:html?|gif|jpe?g|png))\1', re.I)
_JS_FILE = {}
SCRUBBED = Counter()   # what --scrub --dry-run took out, for review


def tracker_file(f):
    if f not in _JS_FILE:
        _JS_FILE[f] = (os.path.isfile(f) and os.path.getsize(f) < 8192
                       and bool(SCRUB_JS.search(open(f, "rb").read().decode("utf-8", "replace"))))
    return _JS_FILE[f]


# round 10 b5 F-M1-1 (#274): live-site forms on the other mirrors (Sheldon Brown's Google search on 1,009 pages and PayPal
# donate on 467, Harris Cyclery search 110, NCHFP's search POSTed to a static index.html on 971, follow.it / Yahoo / egroups
# sign-ups, Ready.gov plan and contact forms) do nothing offline or ask the internet. A form whose action is off the box (and
# not a page on disk), or that POSTs with no script of its own (a static box cannot take a POST), goes: a search box becomes
# the library's own search, anything else a library note. Script-driven forms (the gear calculators) and the library's own
# search stay. Shop, cart and donate links off the box get the needs-internet mark (b5: buy buttons 181, cart links 217,
# NCHFP "Order Information" on 738 pages).
FORM_EL = re.compile(r'<form\b[^>]*>', re.I)
FORM_END = re.compile(r'</form\s*>', re.I)
SEARCHY = re.compile(r'search|buscar|google|sitesearch|\bquery\b', re.I)
SHOP_A = re.compile(r'\shref=(["\'])\s*(?:https?:)?//(?:[^/"\']*(?:store|estore|shop|cart|paypal|donate|harriscyclery)[^/"\']*|[^"\']*(?:cart|itemdetails|checkout))', re.I)
FORM_NOTE = {False: '<p class="library-note">A form from the live website was here (website: needs internet).</p>',
             True: '<p class="library-note">Aquí había un formulario del sitio web (sitio web: necesita internet).</p>'}


def live_forms(text, fpath, mirror, stats):
    here = os.path.dirname(fpath)
    es = bool(re.search(r'<html\b[^>]*\blang=["\']?es\b', text[:3000], re.I)) or "/es.hesperian.org/" in fpath.replace(os.sep, "/")
    pos, out = 0, []
    for m in FORM_EL.finditer(text):
        if m.start() < pos or "library-search" in m.group(0):
            continue
        e = FORM_END.search(text, m.end())
        if not e:   # no </form> (one Harris Cyclery page): an off-box action becomes a note and an inert form
            if re.search(r'\saction=["\']?(?:https?:)?//', m.group(0), re.I):
                out.append(text[pos:m.start()] + FORM_NOTE[es] + '<form onsubmit="return false">'); pos = m.end()
                stats["form_unbalanced_noted"] += 1
            continue
        tag, body = m.group(0), text[m.end():e.start()]
        act = htmlmod.unescape((re.search(r'\saction=(["\']?)([^"\'>\s]*)\1', tag, re.I) or [None, "", ""])[2]).strip()
        post = bool(re.search(r'\smethod=["\']?post', tag, re.I))
        js = bool(re.search(r'\son\w+\s*=', tag + body, re.I))
        off = bool(re.match(r'(?:https?:)?//', act))
        if off:
            from urllib.parse import urlsplit
            u = urlsplit(act if not act.startswith("//") else "http:" + act)
            h = (u.hostname or "").lower()
            d = next((os.path.join(mirror, x) for x in (h, "www." + h, h[4:] if h.startswith("www.") else None)
                      if x and os.path.isdir(os.path.join(mirror, x))), None)
            t = d and not post and resolve(d, u.path or "/")
            if t:   # a GET form whose page is on the box (Sphinx search.html): point it there
                stats["form_action_local"] += 1
                new = re.sub(r'\saction=(["\']?)[^"\'>\s]*\1', ' action="%s"' % quote(os.path.relpath(t, here), safe="/"), tag, count=1, flags=re.I)
                out.append(text[pos:m.start()] + new); pos = m.end(); continue
        if not (off or (post and not js)):
            continue
        searchy = bool(re.search(r'<input\b[^>]*\btype=["\']?(?:text|search)', body, re.I)) and \
            bool(SEARCHY.search(act + " " + tag + " " + re.sub(r"<[^>]+>", " ", body)))
        if searchy:
            lib = os.path.dirname(os.path.dirname(os.path.abspath(mirror)))
            rel = quote(os.path.relpath(os.path.join(lib, "search.html"), here), safe="/")
            new = (f'<form class="library-search" action="{rel}" method="get"><label>'
                   + ("Buscar en esta biblioteca: " if es else "Search this library: ")
                   + '<input type="search" name="q"></label>' + ('<input type="hidden" name="lang" value="spa">' if es else "")
                   + ' <button type="submit">' + ("Buscar" if es else "Search") + "</button></form>")
            stats["form_search_to_library"] += 1
        else:
            new = FORM_NOTE[es]; stats["form_live_noted"] += 1
        out.append(text[pos:m.start()] + new); pos = e.end()
    text = "".join(out) + text[pos:]
    return mark_ext(text, ES_MARK if es else EN_MARK, stats, "shop_link_marked", only=SHOP_A)


# round 10 a7a F12 / a7b W7 (#272, #271 page side): blocks repeated on every page are chrome to search. NCHFP's
# "Resources / Articles / FAQ / Videos" tab box (553 pages; eight canning rows shared one thawing-FAQ excerpt) and the
# So Easy to Preserve order box (775); Ready.gov's .gov banner, header, menu, footer and ARIA navigation blocks (2,122
# pages: "FIFA World Cup 2026 Evacuación Refugio…" was quoted as a passage). Pagefind skips them; the page shows them.
PF_IGNORE = {"nchfp": re.compile(r'<section class="section-(?:secondary section-secondary--black section-secondary--smaller|callout) d-print-none"(?=>)'),
             "ready_gov": re.compile(r'<(?:nav|header|footer)\b(?![^>]*data-pagefind-ignore)[^>]*?(?=\s*/?>)|'
                                     r'<(?:section|div)\b(?![^>]*data-pagefind-ignore)(?=[^>]*(?:class="usa-banner"|\srole="(?:navigation|banner|contentinfo)"))[^>]*?(?=\s*/?>)')}


def pagefind_chrome(text, mirror, stats):
    rx = PF_IGNORE.get(os.path.basename(os.path.abspath(mirror)))
    if not rx:
        return text
    text, n = rx.subn(lambda m: m.group(0) + ' data-pagefind-ignore="all"', text); stats["chrome_pagefind_ignored"] += n
    return text


# b5 F-M1-1: the Sheldon Brown landing page was 728 px wide at 390: an empty AdSense slot (its script was scrubbed) fixed at
# 728 px, and 398 px pictures on a site with no phone style. The dead slot goes on every mirror; Sheldon Brown pages get a
# picture width cap.
AD_SLOT = re.compile(r'<ins\b[^>]*\badsbygoogle\b[^>]*>\s*</ins>\s*', re.I)
SB_STYLE = '<style id="lantern-mirror">img{max-width:100%;height:auto;box-sizing:border-box}</style>\n'


def scrub(text, fpath, mirror, stats):
    here = os.path.dirname(fpath)
    text = pagefind_chrome(text, mirror, stats)
    text, n = AD_SLOT.subn("", text); stats["scrub_ad_slot_dropped"] += n
    if os.path.basename(os.path.abspath(mirror)) == "sheldonbrown":
        text, n = re.subn(r'<style id="lantern-mirror">.*?</style>\n', lambda m: SB_STYLE, text, flags=re.S)
        if not n and (m := re.search(r"</head>", text, re.I)):
            text = text[:m.start()] + SB_STYLE + text[m.start():]; stats["scrub_img_cap_added"] += 1

    def same_site(m):
        h = m.group(2).lower()
        d = next((os.path.join(mirror, x) for x in (h, "www." + h, h[4:] if h.startswith("www.") else None)
                  if x and os.path.isdir(os.path.join(mirror, x))), None)
        t = d and resolve(d, "/" + m.group(3))
        if not t:
            # round 9 b5 W8 (#122): a banner hover swap to a same-site picture that is not on the box
            # (harris_logo-h.gif) asked the live site on every hover; it shows the script's local picture instead (the
            # one the mouse-out puts back, so the hover changes nothing), or no picture (its alt text) when there is none
            if d and re.search(r"\.(?:gif|jpe?g|png)$", m.group(3), re.I):
                stats["scrub_js_img_offline"] += 1
                return m.group(1) + (LOCAL_IMG[0] if len(LOCAL_IMG) == 1 else NO_IMG) + m.group(1)
            return m.group(0)
        stats["scrub_js_url_local"] += 1
        return m.group(1) + quote(os.path.relpath(t, here), safe="/") + m.group(1)

    def script(m):
        src = re.search(r'(?<![-\w])src\s*=\s*(["\'])([^"\']+)\1', m.group(1))
        if src:
            u = htmlmod.unescape(src.group(2)).split("?", 1)[0]
            if not re.match(r"[a-zA-Z][a-zA-Z+.-]*:|//", u) and tracker_file(os.path.normpath(os.path.join(here, unquote(u)))):
                stats["scrub_tracker_file_dropped"] += 1; return ""
            return m.group(0)
        if re.search(r'type\s*=\s*["\']?application/(?:ld\+)?json', m.group(1), re.I):
            return m.group(0)
        if SCRUB_JS.search(m.group(2)):
            stats["scrub_inline_dropped"] += 1; SCRUBBED[(len(m.group(2)) // 200 * 200, re.sub(r"\s+", " ", m.group(2)).strip()[:150])] += 1
            return ""
        LOCAL_IMG[:] = sorted({x for x in LOCAL_IMG_RE.findall(m.group(2)) if os.path.isfile(os.path.normpath(os.path.join(here, unquote(x))))})
        body = JS_URL.sub(same_site, m.group(2))
        return m.group(0) if body == m.group(2) else f"<script{m.group(1)}>{body}</script>"
    text = SCRIPT_EL.sub(script, text)

    def nos(m):
        if not SCRUB_NOSCRIPT.search(m.group(0)): return m.group(0)
        stats["scrub_noscript_dropped"] += 1; return ""
    text = NOSCRIPT_EL.sub(nos, text)
    text, n = LOCK_TITLE.subn("", text); stats["scrub_lock_title_dropped"] += n
    return live_forms(text, fpath, mirror, stats)


def scrub_mirror(mirror, dry, report):
    """--scrub: scrub() on every page of one mirror"""
    stats = Counter()
    for root, _, files in os.walk(mirror):
        for name in files:
            if not name.lower().endswith((".html", ".htm")):
                continue
            f = os.path.join(root, name)
            if ONLY is not None and os.path.abspath(f) not in ONLY:
                continue
            s = open(f, "rb").read().decode("utf-8", "surrogateescape")
            new = scrub(s, f, mirror, stats)
            if new != s:
                stats["written"] += 1
                report.append(f"SCRUB\t{os.path.abspath(f)}")
                if not dry:
                    backup(f); open(f, "wb").write(new.encode("utf-8", "surrogateescape"))
    print(f"{mirror}: " + " ".join(f"{k}={v}" for k, v in sorted(stats.items())) + (" (dry-run)" if dry else ""))
    if dry:
        for (size, head), n in SCRUBBED.most_common():
            print(f"  SCRUBBED {n:5d} ~{size}B  {head}")
        SCRUBBED.clear()


def offline_chrome(mirror, dry, report):
    """--offline-chrome: hhg_chrome on every Hesperian wiki-skin page; NCHFP 'Visite el siguiente sitio web de Penn
    State' pointers (the Spanish stubs) get the Spanish needs-internet mark"""
    stats = Counter()
    for root, _, files in os.walk(mirror):
        for name in files:
            if not name.lower().endswith((".html", ".htm")):
                continue
            f = os.path.join(root, name)
            if ONLY is not None and os.path.abspath(f) not in ONLY:
                continue
            s = open(f, "rb").read().decode("utf-8", "surrogateescape")
            hesp = os.path.basename(os.path.abspath(mirror)) == "hesperian"
            new = add_inbound(hhg_chrome(s, f, stats, mirror if hesp else None), f, stats) if "skin-hhgskin" in s else s
            if hesp and os.path.relpath(f, mirror).split(os.sep)[0] in ORG_HOSTS:
                new = org_chrome(dead_local(new, f, mirror, stats), f, mirror, stats)
            if hesp:
                new = phone_and_leftovers(mark_offline_img(new, f, stats), f, mirror, stats)
            def psu(m):
                if ES_MARK in m.group(2): return m.group(0)
                stats["psu_marked"] += 1; return m.group(1) + m.group(2) + ES_MARK + m.group(3)
            new = ext_refresh(PSU.sub(psu, new), f, mirror, stats)
            if new != s:
                stats["written"] += 1
                report.append(f"OFFLINE_CHROME\t{os.path.abspath(f)}")
                if not dry:
                    backup(f); open(f, "wb").write(new.encode("utf-8", "surrogateescape"))
    print(f"{mirror}: " + " ".join(f"{k}={v}" for k, v in sorted(stats.items())) + (" (dry-run)" if dry else ""))


ONLY = None   # --only FILE: --offline-chrome / --scrub write only these pages (absolute paths, one per line)


def main():
    global BACKUP, ONLY
    argv = sys.argv[1:]
    opts = {k: argv[i + 1] for i, k in enumerate(argv) if k in ("--backup", "--keep", "--report", "--only")}
    BACKUP = opts.get("--backup")
    if "--only" in opts:
        ONLY = {os.path.abspath(l.rstrip("\n")) for l in open(opts["--only"], encoding="utf-8") if l.strip()}
    dry = "--dry-run" in argv
    strip = "--strip-external" in argv
    rep = "--repair" in argv
    dirs = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] not in opts)]
    if "--offline-chrome" in argv or "--exact-case" in argv or "--scrub" in argv:
        report = []
        for mirror in dirs:
            (offline_chrome if "--offline-chrome" in argv else exact_case if "--exact-case" in argv else scrub_mirror)(mirror, dry, report)
        if "--report" in opts:
            open(opts["--report"], "a").writelines(r + "\n" for r in report)
        return
    if "--stubs" in argv or "--dedupe-pdf" in argv or "--unhtml-media" in argv or "--dedupe-query" in argv:
        keep = set(l.strip() for l in open(opts["--keep"])) if "--keep" in opts else set()
        report = []
        for mirror in dirs:
            if "--dedupe-pdf" in argv:
                dedupe_pdf(mirror, dry, report)
            if "--unhtml-media" in argv:
                unhtml_media(mirror, dry, report)
            if "--dedupe-query" in argv:
                dedupe_query(mirror, dry, report)
            if "--stubs" in argv:
                fix_stubs(mirror, keep, dry, report)
        if "--report" in opts:
            open(opts["--report"], "a").writelines(r + "\n" for r in report)
        return
    for mirror in dirs:
        stats = Counter(unresolved=Counter(), img_missing=Counter())
        for host in sorted(os.scandir(mirror), key=lambda e: e.name):
            if not host.is_dir():
                continue
            if strip:
                materialize_variants(host.path, dry, stats)
            for root, _, files in os.walk(host.path):
                for name in files:
                    if name.lower().endswith((".html", ".htm")):
                        stats["files"] += 1
                        fix_file(host.path, os.path.join(root, name), stats, dry, strip, rep)
                    elif strip and re.search(r"\.css($|\?)", name, re.I):
                        fix_css(os.path.join(root, name), mirror, stats, dry)
        print(f"{mirror}: files={stats['files']} links={stats['links']} "
              f"resolvable={stats['resolved']} unresolvable={sum(stats['unresolved'].values())} "
              f"stripped={stats['stripped']} img_local={stats['img_local']} img_missing={sum(stats['img_missing'].values())} "
              f"xhost_resolved={stats['xhost_resolved']} xhost_unresolved={stats['xhost_unresolved']} not_mirrored_marked={stats['not_mirrored_marked']} "
              f"written={stats['written']}{' (dry-run)' if dry else ''}"
              + (f" script_dropped={stats['script_dropped']} link_dropped={stats['link_dropped']} "
                 f"link_missing_dropped={stats['link_missing_dropped']} subres_disabled={stats['subres_disabled']} "
                 f"css_import_dropped={stats['css_import_dropped']} css_url_dropped={stats['css_url_dropped']} css_url_local={stats['css_url_local']} css_url_root_local={stats['css_url_root_local']} qref_plain={stats['qref_plain']} script_preload_dropped={stats['script_preload_dropped']} "
                 f"css_files_written={stats['css_files_written']} variant_materialized={stats['variant_materialized']}" if strip else "")
              + (f" datadata={stats['datadata']} head_links_dropped={stats['head_links_dropped']} cf_href={stats['cf_href']} "
                 f"cf_text={stats['cf_text']} img_restored={stats['img_restored']} img_mark_removed={stats['img_mark_removed']} foreign_abs={stats['foreign_abs']}" if rep else ""))
        if stats["img_missing"] and not dry:
            lst = f"logs/audit/missing_{os.path.basename(mirror.rstrip('/'))}_images.txt"
            os.makedirs(os.path.dirname(lst), exist_ok=True)
            with open(lst, "a") as f:
                f.writelines(u + "\n" for u in sorted(stats["img_missing"]))
            print(f"  {len(stats['img_missing'])} external image URLs without a local copy -> {lst}")
        for c in CREATED:
            print(f"  created {c}")
        CREATED.clear()
        for url, n in stats["unresolved"].most_common(20):
            print(f"  {n:6d}  {url}")


if __name__ == "__main__":
    main()
