#!/usr/bin/env bash
# verify_manifest.sh — full MANIFEST.sha256 verify
# Usage: ./verify_manifest.sh [manifest] [library_root] [logfile]
# Defaults: manifest=library/MANIFEST.sha256  root=.  log=/tmp/verify_manifest.log
# Run under screen for overnight jobs. Outputs ONLY failures + summary.
# ponytail: linear scan, no resume; re-run from scratch on interruption

set -euo pipefail

MANIFEST="${1:-library/MANIFEST.sha256}"
ROOT="${2:-.}"
LOG="${3:-/tmp/verify_manifest_$(date +%Y%m%d_%H%M%S).log}"

if [ ! -f "$MANIFEST" ]; then
  echo "ERROR: manifest not found: $MANIFEST" >&2
  exit 1
fi

TOTAL=$(grep -c '' "$MANIFEST")
PASS=0
FAIL=0
MISSING=0
COUNT=0

echo "=== verify_manifest.sh ===" | tee "$LOG"
echo "Manifest : $MANIFEST"       | tee -a "$LOG"
echo "Root     : $ROOT"           | tee -a "$LOG"
echo "Log      : $LOG"            | tee -a "$LOG"
echo "Total    : $TOTAL entries"  | tee -a "$LOG"
echo "Started  : $(date)"         | tee -a "$LOG"
echo "---"                        | tee -a "$LOG"

while IFS= read -r line; do
  # skip blank lines and comments
  [[ -z "$line" || "$line" == \#* ]] && continue

  EXPECTED_HASH="${line%% *}"
  # path is everything after the two spaces (shasum -c format)
  REL_PATH="${line#*  }"

  FULL_PATH="$ROOT/$REL_PATH"
  COUNT=$((COUNT + 1))

  # progress every 1000 files to stdout (not log) so screen shows life
  if (( COUNT % 1000 == 0 )); then
    printf "\r  %d / %d  (fail=%d missing=%d)" "$COUNT" "$TOTAL" "$FAIL" "$MISSING" >&2
  fi

  if [ ! -f "$FULL_PATH" ]; then
    MISSING=$((MISSING + 1))
    echo "MISSING  $REL_PATH" | tee -a "$LOG"
    continue
  fi

  ACTUAL_HASH=$(shasum -a 256 "$FULL_PATH" 2>/dev/null | cut -d' ' -f1)
  if [ "$ACTUAL_HASH" = "$EXPECTED_HASH" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "CORRUPT  $REL_PATH" | tee -a "$LOG"
    echo "  expected: $EXPECTED_HASH"  | tee -a "$LOG"
    echo "  actual:   $ACTUAL_HASH"    | tee -a "$LOG"
  fi
done < "$MANIFEST"

printf "\r%*s\r" 60 "" >&2  # clear progress line

echo "---"                             | tee -a "$LOG"
echo "Finished : $(date)"              | tee -a "$LOG"
echo "Checked  : $COUNT"               | tee -a "$LOG"
echo "OK       : $PASS"                | tee -a "$LOG"
echo "CORRUPT  : $FAIL"                | tee -a "$LOG"
echo "MISSING  : $MISSING"             | tee -a "$LOG"

if (( FAIL > 0 || MISSING > 0 )); then
  echo "RESULT   : FAILURES — see $LOG" | tee -a "$LOG"
  exit 1
else
  echo "RESULT   : ALL OK"              | tee -a "$LOG"
fi
