#!/bin/bash
# T0 integrity. Usage: t0_integrity.sh <root containing library/> <out.csv> [jobs]
# Runs on the Pi (sha256sum, /data) or the dev tree (shasum, repo root).
# Emits tier,check,path,status,detail rows. sha256 rows only for FAIL/PASS count summary
# plus per-file rows for failures (269k PASS rows would be noise; PASS count is one row).
set -u
ROOT=$1; OUT=$2; J=${3:-4}
cd "$ROOT" || exit 1
SUM=$(command -v sha256sum || echo "shasum -a 256")
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
: > "$OUT"
echo "$(date +%T) t0 start root=$ROOT jobs=$J"
# 1. hash verify, split into J chunks
awk -v J="$J" -v t="$TMP" '{print > (t "/m." NR%J)}' library/MANIFEST.sha256   # round-robin (BSD split lacks l/N)
for c in "$TMP"/m.[0-9]*; do $SUM -c "$c" 2>/dev/null > "$c.out" & done; wait
cat "$TMP"/m.[0-9]*.out > "$TMP/hash.out"
grep -c ': OK$' "$TMP/hash.out" | awk -v o="$OUT" '{print "t0,sha256,library/MANIFEST.sha256,PASS,ok=" $1 >> o}'
grep -v ': OK$' "$TMP/hash.out" | sed 's/: \(FAILED.*\)$/\t\1/' | awk -F'\t' -v o="$OUT" '{gsub(/,/,"%2C",$1); print "t0,sha256," $1 ",FAIL," $2 >> o}'
echo "$(date +%T) hash done: $(wc -l < "$TMP/hash.out") lines"
# 2. disk vs manifest (b5_reseal gate, standalone)
find -L library -type f ! -name 'MANIFEST.sha256*' ! -name VERSION.json ! -name '.DS_Store' \
  ! -name '.done*' ! -name '.all_encs_extracted' \
  ! -path 'library/kolibri_data/logs/*' ! -name server.pid ! -path 'library/kolibri_data/process_cache/*' \
  ! -regex 'library/kolibri_data/[^/]*\.sqlite3.*' 2>/dev/null | sort > "$TMP/disk"
cut -c67- library/MANIFEST.sha256 | sort > "$TMP/man"
comm -23 "$TMP/disk" "$TMP/man" | awk -v o="$OUT" '{gsub(/,/,"%2C"); print "t0,extra_on_disk," $0 ",FAIL,not in manifest" >> o}'
comm -13 "$TMP/disk" "$TMP/man" | awk -v o="$OUT" '{gsub(/,/,"%2C"); print "t0,missing_on_disk," $0 ",FAIL,in manifest only" >> o}'
echo "t0,setdiff,library,PASS,disk=$(wc -l < "$TMP/disk") manifest=$(wc -l < "$TMP/man")" >> "$OUT"
# 3. junk: zero-byte, dangling symlinks, sync-conflict / dotfile names
find -L library -type f -size 0 ! -name '.*' ! -path 'library/kolibri_data/logs/*' ! -path '*/process_cache/*' ! -name server.pid ! -regex 'library/kolibri_data/[^/]*\.sqlite3.*'   # same allow-list as gen_manifest gate0: kolibri runtime cache is not content | awk -v o="$OUT" '{gsub(/,/,"%2C"); print "t0,zero_byte," $0 ",FAIL,0 bytes" >> o}'
find library -type l ! -exec test -e {} \; -print | awk -v o="$OUT" '{gsub(/,/,"%2C"); print "t0,dangling_symlink," $0 ",FAIL,target missing" >> o}'
find -L library \( -name '*.Conflict*' -o -name '*conflicted copy*' -o -name '._*' -o -name '.DS_Store' -o -name '*.sync-conflict*' \) | awk -v o="$OUT" '{gsub(/,/,"%2C"); print "t0,junk_name," $0 ",FAIL,sync/dot junk" >> o}'
echo "t0,junk_scan,library,PASS,done" >> "$OUT"
echo "$(date +%T) t0 done: $(grep -c ',FAIL,' "$OUT") FAIL"
