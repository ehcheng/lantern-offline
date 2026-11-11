#!/usr/bin/env python3
"""E7: per-mirror allow-list. Shop, donate, REST dumps, feeds, pagination and cache-buster duplicates leave the mirror
BEFORE fix_mirror_links / staging, so they are never indexed or sealed. Links that pointed at a pruned page are
rewritten to the page's canonical form (query string stripped) when that file exists, else left alone (fix_mirror_links
marks them unresolved). Counts go to stdout for FIXES.md.
Usage: python3 prune_mirrors.py [--dry-run] [--backup DIR] [--list FILE] [mirror ...]   (default: every rule below)
       run WITHOUT the sandbox. --list FILE: also prune the library-relative paths it names (FIXES #107: hollow
       tables of contents whose chapters were never mirrored, logs/audit/fix104_prune_hollow.txt; #197: the 5
       hesperian.org app-promo and blog-paging pages left hollow by the E3 strip,
       the private test record). After a --list prune run
       fix_mirror_links.py --offline-chrome: it points the links into pruned pages at the live page, marked.
       --backup DIR: copy each pruned or relinked file to DIR/library/mirrors/... first.
"""
import os, re, shutil, sys, unicodedata, urllib.parse
from collections import Counter

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "library", "mirrors")
# (mirror, [regex over the path below library/mirrors/<mirror>/, matched with re.search]); keep = everything else
RULES = {
    "hesperian": [
        r"^(store|donate|library|www|test)\.hesperian\.org/",          # shop, donations, empty stubs
        r"^hesperian\.org/(wp-json|xmlrpc\.php|feed|category|wp-includes|portfolio_entries|20\d\d)(/|\?|$)",
        r"/feed/",                                                     # per-post feeds
        r"\?(s|action|sort_by|page|url|v|ver|title|variant|printable)=", # search, rsd, sort/pagination, cache busters
        r"/w/index\.php",                                              # MediaWiki action urls (login, history)
        r"/hhg/Special:Upload",                                        # wiki upload form (red team 10-16 b2 F15, #208)
    ],
    "ready_gov": [
        r"\?page=\d",                                                  # listing pagination (page 0 = the page itself)
        r"kids-resource-library\?combine=",                            # faceted search duplicates
    ],
    "meshtastic_docs": [
        r"index\.html\?[a-z-]+=",                                      # docs tabs: the same page per tab
    ],
    "nchfp": [
        r"/resources/tag/",                                            # tag listings; the papers themselves stay
    ],
    "journeytoforever": [
        r"/fund/donate\.html$",
    ],
    "sheldonbrown": [
        # harris/shop-*.html and bicycle-shops.html are articles: nothing to prune
    ],
    "aredn_docs": [], "meshtastic_aredn": [],
}


LISTED = set()   # library-relative paths from --list
BACKUP = None


def backup(full):
    if BACKUP:
        dst = os.path.join(BACKUP, "library", os.path.relpath(full, os.path.join(LIB, "..")))
        if not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(full, dst)


def canonical(root, rel):
    """rel without its query part, if that file exists; else None."""
    base = rel.split("?", 1)[0]
    if base == rel:
        return None
    for c in (base, base + ".html", base.rstrip("/") + "/index.html"):   # wget --adjust-extension names
        if os.path.exists(os.path.join(root, c)):
            return c
    return None


def prune(mirror, dry):
    root = os.path.join(LIB, mirror)
    rules = [re.compile(r) for r in RULES[mirror]]
    gone, kept, rewrite = [], 0, {}
    for dp, _, files in os.walk(root):
        for fn in files:
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, root)
            if any(r.search(rel) for r in rules) or unicodedata.normalize("NFC", f"mirrors/{mirror}/{rel}") in LISTED:
                gone.append(rel)
                c = canonical(root, rel)
                if c:
                    rewrite[rel] = c
            else:
                kept += 1
    rewrite = {k: v for k, v in rewrite.items() if v not in set(gone)}   # never relink to a page pruned in this run
    if not dry:
        for rel in gone:
            backup(os.path.join(root, rel)); os.unlink(os.path.join(root, rel))
        # relink: hrefs that named a pruned duplicate point at its canonical page
        if rewrite:
            enc = {urllib.parse.quote(k, safe="/?=&%:"): v for k, v in rewrite.items()}
            enc.update(rewrite)
            pat = re.compile("|".join(re.escape(k) for k in sorted(enc, key=len, reverse=True)))
            for dp, _, files in os.walk(root):
                for fn in files:
                    if not fn.lower().endswith((".html", ".htm")):
                        continue
                    fp = os.path.join(dp, fn)
                    try:
                        s = open(fp, encoding="utf-8", errors="replace").read()
                    except OSError:
                        continue
                    s2 = pat.sub(lambda m: enc[m.group(0)], s)
                    if s2 != s:
                        backup(fp); open(fp, "w", encoding="utf-8").write(s2)
        # empty dirs
        for dp, dirs, files in os.walk(root, topdown=False):
            if not dirs and not files and dp != root:
                os.rmdir(dp)
    by_rule = Counter()
    for rel in gone:
        by_rule[next((r.pattern for r in rules if r.search(rel)), "--list")] += 1
    print(f"{mirror}: kept={kept} pruned={len(gone)} relinked={len(rewrite)}{' (dry-run)' if dry else ''}")
    for r, n in by_rule.most_common():
        print(f"  {n:6d}  {r}")
    return len(gone)


if __name__ == "__main__":
    argv = sys.argv[1:]
    dry = "--dry-run" in argv
    opts = {k: argv[i + 1] for i, k in enumerate(argv) if k in ("--backup", "--list")}
    BACKUP = opts.get("--backup")
    if "--list" in opts:
        LISTED = {unicodedata.normalize("NFC", l.strip()) for l in open(opts["--list"], encoding="utf-8") if l.strip()}
    names = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] not in opts)] or [m for m in RULES if RULES[m]]
    total = sum(prune(m, dry) for m in names)
    print(f"TOTAL pruned={total}{' (dry-run)' if dry else ''}")
