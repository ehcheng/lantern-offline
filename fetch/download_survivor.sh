#!/usr/bin/env bash
# download_survivor.sh — idempotent per-file fetcher for survival.library (7448 PDFs, ~122GB)
# Uses archive.org metadata API to enumerate files, curl -C - for resume, max 2 concurrent.
# Logs to logs/survivor.log. Never streams to stdout.
# Also fetches CD3WD12 PDFs (105 files, 0.64GB) which had a bad HTML zip.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG="$REPO_ROOT/logs/survivor.log"
SURV_DEST="$REPO_ROOT/library/docs/survivor_library"
CD3WD_DEST="$REPO_ROOT/library/docs/cd3wd"
MAX_JOBS=2

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "$(ts) $*" >> "$LOG"; }

mkdir -p "$SURV_DEST" "$CD3WD_DEST" "$(dirname "$LOG")"

# fetch one file: fetch_file <ia_id> <remote_name> <local_path>
fetch_file() {
  local ia_id="$1" remote_name="$2" local_path="$3"
  # ponytail: encode spaces only; extend to full urlencode if other chars FAIL
  local url="https://archive.org/download/${ia_id}/${remote_name// /%20}"
  mkdir -p "$(dirname "$local_path")"

  if [[ -f "$local_path" && -s "$local_path" ]]; then
    log "SKIP  $remote_name (exists)"
    return 0
  fi

  log "START $remote_name"
  if curl -sSf -C - -L --retry 5 --retry-delay 20 \
      -o "${local_path}.part" "$url" 2>>"$LOG"; then
    mv "${local_path}.part" "$local_path"
    local sz
    sz=$(du -h "$local_path" | cut -f1)
    log "DONE  $remote_name $sz"
  else
    rm -f "${local_path}.part"
    log "FAIL  $remote_name"
  fi
}

# simple semaphore: wait until fewer than MAX_JOBS children running
wait_for_slot() {
  while true; do
    local running
    running=$(jobs -r | wc -l | tr -d ' ')
    if [[ "$running" -lt "$MAX_JOBS" ]]; then
      return 0
    fi
    sleep 1
  done
}

# -----------------------------------------------------------------------
# SECTION 1: survival.library — 7448 PDFs
# -----------------------------------------------------------------------
log "START section=SURVIVOR_LIBRARY identifier=survival.library"

FILELIST_JSON="$REPO_ROOT/logs/survival_library_files.json"
if [[ ! -f "$FILELIST_JSON" ]]; then
  log "FETCH metadata survival.library"
  if ! curl -sSf -L -o "$FILELIST_JSON" "https://archive.org/metadata/survival.library" 2>>"$LOG"; then
    log "FAIL  metadata fetch survival.library"
    exit 1
  fi
fi

PDF_LIST=$(python3 - "$FILELIST_JSON" <<'PYEOF'
import sys, json
with open(sys.argv[1]) as f:
    d = json.load(f)
for item in d.get('files', []):
    name = item.get('name', '')
    if name.lower().endswith('.pdf'):
        print(name)
PYEOF
)

TOTAL=$(echo "$PDF_LIST" | wc -l | tr -d ' ')
log "INFO  survival.library: $TOTAL PDFs to check"

while IFS= read -r fname; do
  local_path="$SURV_DEST/$fname"
  if [[ -f "$local_path" && -s "$local_path" ]]; then
    continue  # skip silently to avoid spamming log with 7k SKIPs
  fi
  wait_for_slot
  fetch_file "survival.library" "$fname" "$local_path" &
done <<< "$PDF_LIST"

wait  # drain remaining jobs

ACTUAL_DONE=$(find "$SURV_DEST" -name "*.pdf" | wc -l | tr -d ' ')
ACTUAL_SIZE=$(du -sh "$SURV_DEST" 2>/dev/null | cut -f1)
log "SUMMARY survival.library: $ACTUAL_DONE/$TOTAL PDFs on disk, $ACTUAL_SIZE (expected 7448/122GB)"
log "DONE  section=SURVIVOR_LIBRARY"

# -----------------------------------------------------------------------
# SECTION 2: CD3WD12 — 105 PDFs (fix: HTML fake-zip was downloaded before)
# -----------------------------------------------------------------------
log "START section=CD3WD12 identifier=CD3WD12"

BAD_ZIP="$CD3WD_DEST/cd3wd12_pdfs.zip"
if [[ -f "$BAD_ZIP" ]]; then
  FTYPE=$(file -b "$BAD_ZIP")
  if [[ "$FTYPE" == *HTML* ]] || [[ $(wc -c < "$BAD_ZIP") -lt 10000 ]]; then
    log "DELETE $BAD_ZIP (was HTML error page)"
    rm -f "$BAD_ZIP"
  fi
fi

CD3WD12_JSON="$REPO_ROOT/logs/cd3wd12_files.json"
if [[ ! -f "$CD3WD12_JSON" ]]; then
  if ! curl -sSf -L -o "$CD3WD12_JSON" "https://archive.org/metadata/CD3WD12" 2>>"$LOG"; then
    log "FAIL  metadata fetch CD3WD12"
    exit 1
  fi
fi

CD3WD_PDF_LIST=$(python3 - "$CD3WD12_JSON" <<'PYEOF'
import sys, json
with open(sys.argv[1]) as f:
    d = json.load(f)
for item in d.get('files', []):
    name = item.get('name', '')
    if name.lower().endswith('.pdf'):
        print(name)
PYEOF
)

CD3_TOTAL=$(echo "$CD3WD_PDF_LIST" | wc -l | tr -d ' ')
log "INFO  CD3WD12: $CD3_TOTAL PDFs to check"

while IFS= read -r fname; do
  local_path="$CD3WD_DEST/$fname"
  if [[ -f "$local_path" && -s "$local_path" ]]; then
    continue
  fi
  wait_for_slot
  fetch_file "CD3WD12" "$fname" "$local_path" &
done <<< "$CD3WD_PDF_LIST"

wait

CD3_DONE=$(find "$CD3WD_DEST" -name "*.pdf" | wc -l | tr -d ' ')
CD3_SIZE=$(du -sh "$CD3WD_DEST" 2>/dev/null | cut -f1)
log "SUMMARY CD3WD12: $CD3_DONE/$CD3_TOTAL PDFs on disk, $CD3_SIZE (expected 105/0.64GB)"
log "DONE  section=CD3WD12"
