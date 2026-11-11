#!/bin/bash
BASE=$(cd "$(dirname "$0")/.." && pwd)
LOG=$BASE/logs/manifest.log
cd "$BASE" || exit 1
# seal gate: a zero-byte file is a defect (truncated download, killed generator), never content. Allowed: dot markers
# (.done, .data_version), kolibri *.sqlite3-wal, and the kolibri runtime paths the manifest already excludes.
gate0() {
  local z; z=$(find -L library -type f -size 0 ! -name '.*' ! -name '*.sqlite3-wal' ! -path 'library/kolibri_data/logs/*' ! -path '*/process_cache/*')
  [ -z "$z" ] || { printf 'REFUSED: zero-byte files in library (fix or delete, then rerun):\n%s\n' "$z"; exit 1; }
}
gate0
echo "$(date +'%F %T') manifest start" >>"$LOG"
# -L: library subdirs are symlinks into the content folder
# Kolibri runtime state (sqlite dbs, logs, process cache) mutates on the live box; hashing it makes every verify report false FAILs
# round 10 b5 F-M1-4 (#275): the zero-byte download markers (.done*, .all_encs_extracted) are build state the download
# scripts read, not content: they stay on disk and out of the seal (b5_reseal.sh has the same exclusion)
find -L library -type f ! -name 'MANIFEST.sha256*' ! -name VERSION.json ! -name '.done*' ! -name '.all_encs_extracted' \
  ! -path 'library/kolibri_data/logs/*' ! -name server.pid ! -path 'library/kolibri_data/process_cache/*' \
  ! -regex 'library/kolibri_data/[^/]*\.sqlite3.*' -print0 | sort -z | \
  xargs -0 -n1 -P4 shasum -a 256 > library/MANIFEST.sha256.tmp 2>>"$LOG"
mv library/MANIFEST.sha256.tmp library/MANIFEST.sha256
echo "$(date +'%F %T') manifest done: $(wc -l < library/MANIFEST.sha256) files" >>"$LOG"
bash "$BASE/build/gen_version.sh" >>"$LOG"
