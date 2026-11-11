#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf library/_app/text
# corrupt PDFs (FAIL extract lines) must not block the index; gen_text exits 1 on any
python3 build/gen_text.py || echo 'gen_text: some PDFs failed to extract (see FAIL lines above)'
STAGE=${TMPDIR:-/tmp}/pfsite
rm -rf "$STAGE"; mkdir -p "$STAGE/mirrors" "$STAGE/_app"
MIRRORS=$(for m in hesperian nchfp ready_gov; do if [ -d library/mirrors/$m ]; then echo library/mirrors/$m; fi; done)
[ -z "$MIRRORS" ] || rsync -a --include '*/' --include '*.html' --include '*.htm' --exclude '*' $MIRRORS "$STAGE/mirrors/"
# nchfp paper pages are SSI fragments without <body>; pagefind indexes <body> only (r14: 23 pages missing)
python3 build/pf_add_body.py "$STAGE/mirrors"
# shelf READMEs (docs/<shelf>/README.html) are pages too
for r in library/docs/*/README.html; do [ -f "$r" ] || continue; mkdir -p "$STAGE/${r#library/}" && rmdir "$STAGE/${r#library/}" && cp "$r" "$STAGE/${r#library/}"; done
# library-written notes (docs/**/<name>.md, not READMEs, e.g. the D9 car-battery note): pagefind reads html only and
# build_frontend runs gen_shelves (which renders the .html sibling) after this script, so stage our own rendering at the
# sibling's path. Prints each staged page. (H8 2026-10-12, FIXES #183)
python3 - "$STAGE" <<'EOF'
import glob, os, sys, html
sys.path.insert(0, "build")
from gen_shelves import md_render
for md in sorted(glob.glob("library/docs/**/*.md", recursive=True)):
    if os.path.basename(md).lower().startswith("readme"):
        continue
    text = open(md, encoding="utf-8").read()
    title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), os.path.basename(md)[:-3])
    out = os.path.join(sys.argv[1], md[len("library/"):-3] + ".html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(f'<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title></head>'
                                           f'<body><article>{md_render(text)}</article></body></html>')
    print("pagefind note:", out)
EOF
# H37c: two indexes. Modern (mirrors + modern shelves) keeps its own IDF and
# ~100 MB footprint; historical (survivor_library/cd3wd/HISTORICAL, ~1.9M
# pages) lives in _app/pagefind_hist and only loads when a query runs there.
# One shared index let historical word statistics reorder modern results.
HIST='docs/survivor_library docs/cd3wd/2012/health docs/HISTORICAL'
# 2026-09-30: CD3WD 2012 handbooks get a third, document-level index (gen_text DEV_PREFIX);
# only its health category is historical-gated
DEV='docs/cd3wd/2012 docs/school_textbooks'
# modern index = everything except the historical trees and the dev tier (r8c regression: survivor_library leaked in)
mkdir -p library/_app/text   # empty when no PDF shelf was fetched
rsync -a $(for h in $HIST $DEV; do echo "--exclude=/$h/"; done) --exclude=/docs/cd3wd/ library/_app/text/ "$STAGE/_app/text/"
case "$(uname -s)-$(uname -m)" in   # fetched by fetch/fetch_all.py
  Darwin-arm64) PF=build/bin/pagefind/darwin-arm64/pagefind ;;
  Linux-aarch64|Linux-arm64) PF=build/bin/pagefind/linux-arm64/pagefind ;;
  Linux-x86_64) PF=build/bin/pagefind/linux-x86_64/pagefind ;;
  *) echo "no pagefind binary for $(uname -s)-$(uname -m)"; exit 1 ;;
esac
$PF --site "$STAGE" --output-subdir _app/pagefind
rm -rf library/_app/pagefind
mv "$STAGE/_app/pagefind" library/_app/pagefind
HSTAGE="$STAGE"_hist
rm -rf "$HSTAGE"; mkdir -p "$HSTAGE/_app/text/docs"
for h in $HIST; do [ -d "library/_app/text/$h" ] && mkdir -p "$HSTAGE/_app/text/$(dirname $h)" && cp -R "library/_app/text/$h" "$HSTAGE/_app/text/$h"; done
rm -rf library/_app/pagefind_hist
# the historical and dev indexes are optional in search.html: a build without those shelves has none
if [ -n "$(find "$HSTAGE" -name '*.html' -print -quit)" ]; then
  $PF --site "$HSTAGE" --output-subdir _app/pagefind_hist
  mv "$HSTAGE/_app/pagefind_hist" library/_app/pagefind_hist
fi
rm -rf "$HSTAGE"
DSTAGE="$STAGE"_dev
rm -rf "$DSTAGE"
for d in $DEV; do if [ -d "library/_app/text/$d" ]; then mkdir -p "$DSTAGE/_app/text/$d" && rsync -a --exclude=/health/ "library/_app/text/$d/" "$DSTAGE/_app/text/$d/"; fi; done
mkdir -p "$DSTAGE/_app/text"
# English CD3WD handbooks: one 3,000-char record each (0.8M pages would panic the wasm like pagefind_hist); non-English books full text (FIXES #116, pf_dev_stage.py)
python3 build/pf_dev_stage.py "$DSTAGE/_app/text"
rm -rf library/_app/pagefind_dev
if [ -n "$(find "$DSTAGE" -name '*.html' -print -quit)" ]; then
  $PF --site "$DSTAGE" --output-subdir _app/pagefind_dev
  mv "$DSTAGE/_app/pagefind_dev" library/_app/pagefind_dev
fi
rm -rf "$DSTAGE" "$STAGE"
echo REBUILD_DONE
