#!/bin/bash
# B5: final manifest reseal, two passes so A7 can regen over the new content.
#   pass A: all content (follows library/* symlinks; excludes _app + root html,
#           which A7 regenerates) -> interim MANIFEST.sha256
#   then:   build_frontend.sh (indexes over the new manifest)
#   pass B: _app/** + root html -> appended, path-sorted -> final MANIFEST
set -euo pipefail
cd "$(dirname "$0")/.."
# extended regex for -regex: BSD find takes -E before the path, GNU find -regextype after it
findx() { if [ "$(uname)" = Darwin ]; then find -E -L "$@"; else local p=$1; shift; find -L "$p" -regextype posix-extended "$@"; fi; }
TMP=logs; mkdir -p $TMP
# seal gate: a zero-byte file is a defect (truncated download, killed generator), never content. Allowed: dot markers
# (.done, .data_version), kolibri *.sqlite3-wal, and the kolibri runtime paths the manifest already excludes.
gate0() {
  local z; z=$(find -L library -type f -size 0 ! -name '.*' ! -name '*.sqlite3-wal' ! -path 'library/kolibri_data/logs/*' ! -path '*/process_cache/*')
  [ -z "$z" ] || { printf 'REFUSED: zero-byte files in library (fix or delete, then rerun):\n%s\n' "$z"; exit 1; }
}

# the library's own READMEs and notes for content folders (data/library_notes/), installed where that content was fetched
(cd data/library_notes && find . -type f) | while IFS= read -r f; do
  d=$(dirname "$f")   # ./tools (the page tools themselves) always; a content folder's notes only when it was fetched
  if [ "$d" = ./tools ]; then mkdir -p library/tools; fi
  if [ -d "library/$d" ]; then cp -p "data/library_notes/$f" "library/$f"; fi
done

gate0

echo "$(date +'%F %T') pass A (content) start"
# Kolibri runtime state (sqlite, logs, process cache) mutates on the live box: keep it out (matches gen_manifest.sh)
# round 10 b5 F-M1-4 (#275): so are the zero-byte download markers (.done*, .all_encs_extracted), read only by the
# download scripts; they stay on disk. Same exclusion in the disk gate below and in gen_manifest.sh.
findx library -type f ! -name 'MANIFEST.sha256*' ! -name VERSION.json ! -name '.DS_Store' \
    ! -name '.done*' ! -name '.all_encs_extracted' \
    ! -path 'library/_app/*' ! -regex 'library/[^/]*\.html' \
    ! -path 'library/kolibri_data/logs/*' ! -name server.pid ! -path 'library/kolibri_data/process_cache/*' \
    ! -regex 'library/kolibri_data/[^/]*\.sqlite3.*' -print0 | sort -z > "$TMP/manifest.listA"
xargs -0 -n8 -P6 shasum -a 256 < "$TMP/manifest.listA" > "$TMP/manifest.partA"
# r43: the parallel hash drops 1-4 paths a seal (r41 240141, r42 240143, r43 240144 of 240145); the final gate below
# heals the manifest, but build_frontend reads this interim one, so a dropped PDF lost its title row (t3 mcp_parity).
# Same self-heal here: hash what pass A missed serially, and stop if anything is still missing.
tr '\0' '\n' < "$TMP/manifest.listA" | comm -23 - <(cut -c67- "$TMP/manifest.partA" | sort) > "$TMP/manifest.missA"
if [ -s "$TMP/manifest.missA" ]; then
  echo "pass A: $(wc -l < "$TMP/manifest.missA") paths dropped by the parallel hash, hashing them serially"
  while IFS= read -r f; do shasum -a 256 "$f"; done < "$TMP/manifest.missA" >> "$TMP/manifest.partA"
  tr '\0' '\n' < "$TMP/manifest.listA" | comm -23 - <(cut -c67- "$TMP/manifest.partA" | sort) > "$TMP/manifest.missA"
  [ ! -s "$TMP/manifest.missA" ] || { echo "PASS A MISMATCH ($(wc -l < "$TMP/manifest.missA") paths, see $TMP/manifest.missA)"; exit 1; }
fi
echo "$(date +'%F %T') pass A done: $(wc -l < "$TMP/manifest.partA") files"

LC_ALL=C sort -k2 "$TMP/manifest.partA" > library/MANIFEST.sha256   # interim for the generators; sorted so their output does not depend on hash-race order

echo "$(date +'%F %T') A7 rerun over new manifest"
build/build_frontend.sh

gate0   # build_frontend regenerated covers and pages
echo "$(date +'%F %T') pass B (_app + root html)"
findx library -type f ! -name 'MANIFEST.sha256*' ! -name VERSION.json ! -name '.DS_Store' \
    \( -path 'library/_app/*' -o -regex 'library/[^/]*\.html' \) -print0 |
  sort -z | xargs -0 -n8 -P6 shasum -a 256 > "$TMP/manifest.partB"
# gen_shelves renders every .md to a sibling .html (tools/*/README.html ...): r14 sealed their pass-A hashes, stale
find -L library -name '*.md' -not -path 'library/docs/*' -not -path 'library/mirrors/*' -not -path 'library/kolibri_data/*' -not -path 'library/_app/*' |
  sed 's/\.md$/.html/' | while IFS= read -r f; do [ -f "$f" ] && shasum -a 256 "$f"; done >> "$TMP/manifest.partB"

# pass B wins where both passes hashed a path (the rendered .md siblings)
cat "$TMP/manifest.partB" "$TMP/manifest.partA" | awk '!seen[substr($0, 67)]++' | sort -k2 > library/MANIFEST.sha256
# gate: every file on disk has a manifest line (a parallel xargs once dropped one)
findx library -type f ! -name 'MANIFEST.sha256*' ! -name VERSION.json ! -name '.DS_Store' \
    ! -name '.done*' ! -name '.all_encs_extracted' \
    ! -path 'library/kolibri_data/logs/*' ! -name server.pid ! -path 'library/kolibri_data/process_cache/*' \
    ! -regex 'library/kolibri_data/[^/]*\.sqlite3.*' | sort > "$TMP/manifest.disk"
cut -c67- library/MANIFEST.sha256 | sort | comm -3 "$TMP/manifest.disk" - > "$TMP/manifest.diff"
# self-heal once: paths on disk that the parallel hash dropped (seen r7: 1 kolibri h5p) get hashed serially and appended
if [ -s "$TMP/manifest.diff" ]; then
  echo "gate: $(wc -l < "$TMP/manifest.diff") paths differ, hashing the on-disk ones serially"
  while IFS= read -r f; do [ -f "$f" ] && shasum -a 256 "$f"; done < "$TMP/manifest.diff" >> library/MANIFEST.sha256
  sort -k2 -o library/MANIFEST.sha256 library/MANIFEST.sha256
  cut -c67- library/MANIFEST.sha256 | sort | comm -3 "$TMP/manifest.disk" - > "$TMP/manifest.diff"
fi
if [ -s "$TMP/manifest.diff" ]; then echo "SEAL MISMATCH ($(wc -l < "$TMP/manifest.diff") paths, see $TMP/manifest.diff)"; exit 1; fi
echo "$(date +'%F %T') SEALED: $(wc -l < library/MANIFEST.sha256) files"
bash build/gen_version.sh
echo B5_RESEAL_DONE
