#!/usr/bin/env bash
# download_noaa_charts.sh — idempotent, resumable NOAA chart acquisition
# Sources:
#   1. NOAA ENC All_ENCs.zip  (~834 MB, vector S-57, current as of 2026-09)
#   2. NOAA ENC catalog XML   (~50  MB, metadata/catalog)
#   3. archive.org NOAA_RNC   (~5.7 GB, final BSB raster .kap/.bsb set, circa 2024)
# Opens with: OpenCPN (ENC+RNC), SeaClear, JOSM; KAP/BSB also in QGIS
# Total budget: ~6.6 GB
ROOT=$(cd "$(dirname "$0")/.." && pwd)

set -euo pipefail

OUTDIR="$ROOT/library/maps/noaa_charts"
LOGFILE="$ROOT/logs/noaa_charts.log"
TMPDIR_CUSTOM="${TMPDIR:-/tmp}/noaa_charts_tmp"  # r9 a8 N1: never inside library/
MIN_ENC_BYTES=800000000   # 800 MB gate for All_ENCs.zip (actual: 834 MB)
MIN_CAT_BYTES=40000000    # 40 MB gate for catalog XML (actual: 52 MB)
MIN_KAP_FILES=2000        # expect ~2134 .kap files in RNC set

mkdir -p "$OUTDIR/enc" "$OUTDIR/rnc" "$TMPDIR_CUSTOM"

log() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*" | tee -a "$LOGFILE"; }

log "=== NOAA charts download starting ==="

# ── 1. ENC All_ENCs.zip ──────────────────────────────────────────────────────
ENC_URL="https://charts.noaa.gov/ENCs/All_ENCs.zip"
ENC_ZIP="${OUTDIR}/enc/All_ENCs.zip"
ENC_DONE="${OUTDIR}/enc/.all_encs_extracted"

if [[ ! -f "$ENC_DONE" ]]; then
  log "Downloading All_ENCs.zip (~834 MB)..."
  curl -L --retry 5 --retry-delay 10 --continue-at - \
    -o "${ENC_ZIP}.part" "$ENC_URL" 2>>"$LOGFILE" \
    && mv "${ENC_ZIP}.part" "$ENC_ZIP"

  ACTUAL_SIZE=$(stat -f%z "$ENC_ZIP" 2>/dev/null || stat -c%s "$ENC_ZIP")
  if (( ACTUAL_SIZE < MIN_ENC_BYTES )); then
    log "ERROR: All_ENCs.zip too small (${ACTUAL_SIZE} bytes) — aborting ENC extract"
    exit 1
  fi
  log "All_ENCs.zip OK (${ACTUAL_SIZE} bytes). Extracting..."
  unzip -o "$ENC_ZIP" -d "${OUTDIR}/enc/cells/" >>"$LOGFILE" 2>&1
  touch "$ENC_DONE"
  log "ENC extraction complete."
else
  log "SKIP: ENC already extracted ($ENC_DONE exists)"
fi

# ── 2. ENC product catalog XML ────────────────────────────────────────────────
CAT_URL="https://charts.noaa.gov/ENCs/ENCProdCat_19115.xml"
CAT_FILE="${OUTDIR}/enc/ENCProdCat_19115.xml"

if [[ ! -f "$CAT_FILE" ]] || (( $(stat -f%z "$CAT_FILE" 2>/dev/null || stat -c%s "$CAT_FILE") < MIN_CAT_BYTES )); then
  log "Downloading ENC product catalog XML (~50 MB)..."
  curl -L --retry 3 --retry-delay 5 --continue-at - \
    -o "${CAT_FILE}.part" "$CAT_URL" 2>>"$LOGFILE" \
    && mv "${CAT_FILE}.part" "$CAT_FILE"
  log "Catalog XML downloaded: $(stat -f%z "$CAT_FILE" 2>/dev/null || stat -c%s "$CAT_FILE") bytes"
else
  log "SKIP: Catalog XML already present"
fi

# ── 3. archive.org NOAA_RNC — BSB raster charts ───────────────────────────────
# Fetch file list from archive.org metadata API, then download each .kap/.bsb
RNC_DIR="${OUTDIR}/rnc"
RNC_DONE="${OUTDIR}/rnc/.rnc_complete"

if [[ ! -f "$RNC_DONE" ]]; then
  log "Fetching NOAA_RNC file list from archive.org..."
  META_URL="https://archive.org/metadata/NOAA_RNC"
  FILELIST="${TMPDIR_CUSTOM}/noaa_rnc_files.txt"

  curl -sL --max-time 30 "$META_URL" 2>>"$LOGFILE" \
    | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d.get('files', []):
    name = f['name']
    if name.endswith('.kap') or name.endswith('.bsb'):
        print(name)
" > "$FILELIST"

  KAP_COUNT=$(wc -l < "$FILELIST")
  log "RNC file list: ${KAP_COUNT} files (.kap + .bsb)"

  if (( KAP_COUNT < 100 )); then
    log "ERROR: too few RNC files listed (${KAP_COUNT}) — archive.org issue?"
    exit 1
  fi

  BASE_URL="https://archive.org/download/NOAA_RNC"
  DOWNLOADED=0
  SKIPPED=0
  FAILED=0

  while IFS= read -r fname; do
    destfile="${RNC_DIR}/${fname}"
    if [[ -f "$destfile" ]] && (( $(stat -f%z "$destfile" 2>/dev/null || stat -c%s "$destfile") > 500 )); then
      (( SKIPPED++ )) || true
      continue
    fi
    mkdir -p "$(dirname "$destfile")"
    if curl -L --retry 3 --retry-delay 5 --max-time 120 --continue-at - \
        -o "${destfile}.part" "${BASE_URL}/${fname}" >>"$LOGFILE" 2>&1; then
      mv "${destfile}.part" "$destfile"
      (( DOWNLOADED++ )) || true
    else
      log "WARN: failed to download ${fname}"
      rm -f "${destfile}.part"
      (( FAILED++ )) || true
    fi
    # progress heartbeat every 100 files
    TOTAL=$(( DOWNLOADED + SKIPPED ))
    if (( TOTAL % 100 == 0 )); then
      log "RNC progress: ${DOWNLOADED} downloaded, ${SKIPPED} skipped, ${FAILED} failed / ${KAP_COUNT} total"
    fi
  done < "$FILELIST"

  log "RNC download complete: ${DOWNLOADED} new, ${SKIPPED} skipped, ${FAILED} failed"

  ACTUAL_KAP=$(find "$RNC_DIR" -name "*.kap" | wc -l)
  if (( ACTUAL_KAP < MIN_KAP_FILES )); then
    log "WARN: only ${ACTUAL_KAP} .kap files on disk (expected >=${MIN_KAP_FILES}) — may need re-run"
  else
    touch "$RNC_DONE"
    log "RNC verified: ${ACTUAL_KAP} .kap files on disk."
  fi
else
  log "SKIP: RNC already complete ($RNC_DONE exists)"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
ENC_CELLS=$(find "${OUTDIR}/enc/cells" -type f 2>/dev/null | wc -l || echo 0)
KAP_FILES=$(find "${OUTDIR}/rnc" -name "*.kap" 2>/dev/null | wc -l || echo 0)
TOTAL_GB=$(du -sh "$OUTDIR" 2>/dev/null | cut -f1 || echo "?")

log "=== DONE === ENC cells: ${ENC_CELLS}, RNC .kap files: ${KAP_FILES}, total on-disk: ${TOTAL_GB}"
