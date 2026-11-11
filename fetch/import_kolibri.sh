#!/bin/bash
# B4: Kolibri content import on the Mac (pinned 0.19.5, same as the image).
# Idempotent — importchannel/importcontent resume/skip existing.
# Launch: screen -dmS kolibri bash fetch/import_kolibri.sh
ROOT=$(cd "$(dirname "$0")/.." && pwd)
set -uo pipefail
export KOLIBRI_HOME="$(cd "$(dirname "$0")/.." && pwd)/library/kolibri_data"
K=${KOLIBRI:-kolibri}   # Kolibri 0.19.5 CLI (pip install kolibri==0.19.5 in a venv; KOLIBRI=/path/to/venv/bin/kolibri)
LOG=$ROOT/logs/kolibri_import.log
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

# id | name (studio public API, 2026-09-18)
CHANNELS="
c9d7f950ab6b5a1199e3d6c10d7f0103|Khan Academy (English - US)
1d8f6d84618153c18c695d85074952a7|CK-12
fc47aee82e0153e2a30197d3fdee1128|OpenStax
d6e3b856125f5e6aa5fb40c8b112d5e9|EngageNY
0e173fca6e9052f8a474a2fb84055faf|Global Digital Library
"
mkdir -p "$KOLIBRI_HOME"
echo "$CHANNELS" | grep '|' | while IFS='|' read -r id name; do
  log "=== $name ($id): importchannel"
  for try in 1 2 3; do
    "$K" manage importchannel network "$id" >> "$LOG" 2>&1 && break
    log "importchannel retry $try failed for $name"; sleep 30
  done
  log "=== $name: importcontent (all)"
  for try in 1 2 3; do
    "$K" manage importcontent network "$id" >> "$LOG" 2>&1 && { log "=== $name DONE"; break; }
    log "importcontent retry $try failed for $name"; sleep 60
  done
done
log "ALL CHANNELS PROCESSED"
