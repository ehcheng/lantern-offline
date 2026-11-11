#!/bin/bash
# T1 format validity over every MANIFEST path. Resumable: paths already PASS in results/t1.csv are skipped.
# Run WITHOUT the sandbox: c_zim needs kiwix on :8080 (KIWIX env overrides) and c_gguf execs llamafile; both FAIL otherwise.
# Self-test of the validators against truncated copies: bash tests/checks/fmt_selftest.sh
# Usage: bash tests/t1_format.sh [jobs]
set -uo pipefail
cd "$(dirname "$0")/.."
J=${1:-16}; EX=tests; OUT=$EX/results/t1.csv
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
[ -s library/MANIFEST.sha256 ] || { echo "t1: library/MANIFEST.sha256 missing or empty" >&2; exit 1; }
# a PASS only carries over if the manifest line (sha + path) is unchanged since it was earned: results/t1.manifest
# is the manifest as of the last completed run, so a reseal that rewrites a file re-validates it
# the LATEST row per path decides (csv-aware: paths with commas are quoted); an old PASS must not hide a newer FAIL
[ -f "$OUT" ] && python3 -c '
import csv, sys
last = {}
for r in csv.reader(open(sys.argv[1])):
    if len(r) >= 4: last[r[2]] = r[3]
sys.stdout.write("".join(p + "\n" for p, st in last.items() if st in ("PASS", "SKIP")))' "$OUT" | sort > "$TMP/done_path" || : > "$TMP/done_path"
[ -f "$EX/results/t1.manifest" ] && sort "$EX/results/t1.manifest" | comm -12 - <(sort library/MANIFEST.sha256) | cut -c67- | sort > "$TMP/same" || : > "$TMP/same"
comm -12 "$TMP/done_path" "$TMP/same" > "$TMP/done"
cut -c67- library/MANIFEST.sha256 | sort | comm -23 - "$TMP/done" > "$TMP/todo"
echo "$(date +%T) t1 start todo=$(wc -l < "$TMP/todo") done=$(wc -l < "$TMP/done") jobs=$J"
# heavy/serial groups first with low parallelism (iso mounts, big binaries), everything else -P $J
grep -Ei '\.(iso|gguf|onnx|apk|dmg|exe|pkg|appimage|zim|db)$' "$TMP/todo" > "$TMP/heavy"
grep -Eiv '\.(iso|gguf|onnx|apk|dmg|exe|pkg|appimage|zim|db)$' "$TMP/todo" > "$TMP/light"
tr '\n' '\0' < "$TMP/heavy" | xargs -0 -n 4 -P 2 python3 $EX/checks/fmt.py >> "$OUT"
echo "$(date +%T) heavy done"
tr '\n' '\0' < "$TMP/light" | xargs -0 -n 200 -P $J python3 $EX/checks/fmt.py >> "$OUT"
cp library/MANIFEST.sha256 "$EX/results/t1.manifest"
echo "$(date +%T) t1 done: PASS=$(grep -c ',PASS,' "$OUT") FAIL=$(grep -c ',FAIL,' "$OUT") (unchecked vs manifest in REPORT.md)"
python3 $EX/report.py > /dev/null
