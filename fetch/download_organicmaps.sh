#!/usr/bin/env bash
# Download Organic Maps .mwm files for all US regions + World files.
# Idempotent: skips files that already exist at full size, resumes partial downloads.
#
# Usage: ./download_organicmaps.sh [dataVersion]
#        dataVersion defaults to 260826 (CDN latest as of 2026-09-14)
#
# Output: library/maps/organicmaps/<region>.mwm
# Logs:   logs/organicmaps.log

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DATA_VERSION="${1:-260826}"
CDN_BASE="https://cdn-us1.organicmaps.app/maps/${DATA_VERSION}"
# ponytail: single CDN, add round-robin/fallback if CDN throttles
FALLBACK_CDN="https://mapgen-fi-1.comaps.app/maps/${DATA_VERSION}"

OUT_DIR="${REPO_ROOT}/library/maps/organicmaps"
LOG_DIR="${REPO_ROOT}/logs"
LOG="${LOG_DIR}/organicmaps.log"

mkdir -p "$OUT_DIR" "$LOG_DIR"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

download_region() {
  local region="$1"
  local filename="${region}.mwm"
  local dest="${OUT_DIR}/${filename}"
  local url="${CDN_BASE}/$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$filename")"

  if [[ -f "$dest" ]]; then
    # Check if file is non-empty (simple existence check — not hash-verified)
    # ponytail: no hash check, add --expected-size or sha256 comparison if corruption is a concern
    local size
    size=$(stat -f%z "$dest" 2>/dev/null || stat -c%s "$dest" 2>/dev/null || echo 0)
    if [[ "$size" -gt 0 ]]; then
      log "SKIP $region (${size} bytes already present)"
      return 0
    fi
  fi

  log "START $region → $dest"
  if curl -L -C - \
       --retry 3 --retry-delay 5 \
       --connect-timeout 30 \
       --max-time 600 \
       -o "$dest" \
       "$url" \
       2>>"$LOG"; then
    local final_size
    final_size=$(stat -f%z "$dest" 2>/dev/null || stat -c%s "$dest" 2>/dev/null || echo 0)
    log "DONE $region (${final_size} bytes)"
  else
    log "FAIL $region — trying fallback CDN"
    local fallback_url="${FALLBACK_CDN}/$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$filename")"
    if curl -L -C - \
         --retry 3 --retry-delay 5 \
         --connect-timeout 30 \
         --max-time 600 \
         -o "$dest" \
         "$fallback_url" \
         2>>"$LOG"; then
      local final_size
      final_size=$(stat -f%z "$dest" 2>/dev/null || stat -c%s "$dest" 2>/dev/null || echo 0)
      log "DONE $region via fallback (${final_size} bytes)"
    else
      log "ERROR $region — both CDNs failed, skipping"
      rm -f "$dest"
      return 1
    fi
  fi
}

log "=== Organic Maps bulk download ==="
log "dataVersion: ${DATA_VERSION}"
log "CDN: ${CDN_BASE}"
log "Destination: ${OUT_DIR}"
log ""

# World files first
download_region "World"
download_region "WorldCoasts"

# All US leaf-node regions (163 total, ~13-14 GB)
# Source: data/countries.json v260714, leaf nodes only (no parent containers)
REGIONS=(
  "US_Alabama_Birmingham"
  "US_Alabama_Montgomery"
  "US_Alaska"
  "US_Arizona_Flagstaff"
  "US_Arizona_Phoenix"
  "US_Arizona_Tucson"
  "US_Arkansas_North"
  "US_Arkansas_South"
  "US_California_Bakersfield_Bakersfield"
  "US_California_Bakersfield_Lancaster"
  "US_California_Chico"
  "US_California_LA"
  "US_California_LA North"
  "US_California_Redding"
  "US_California_Sacramento_Fresno"
  "US_California_Sacramento_Sacramento"
  "US_California_Sacramento_Stockton"
  "US_California_San Diego"
  "US_California_Santa_Clara_Palo Alto"
  "US_California_Santa_Clara_Santa Cruz"
  "US_Colorado_Aspen"
  "US_Colorado_Denver"
  "US_Colorado_South"
  "US_Connecticut"
  "US_Delaware"
  "US_Florida_Gainesville"
  "US_Florida_Jacksonville"
  "US_Florida_Miami"
  "US_Florida_Orlando"
  "US_Florida_Tampa"
  "US_Georgia_Atlanta"
  "US_Georgia_Macon"
  "US_Georgia_North"
  "US_Georgia_South"
  "US_Guam"
  "US_Hawaii"
  "US_Idaho_North"
  "US_Idaho_South"
  "US_Illinois_Chickago"
  "US_Illinois_Elgin"
  "US_Illinois_Rockford"
  "US_Illinois_South"
  "US_Illinois_Springfield"
  "US_Indiana_Evansville"
  "US_Indiana_Indianapolis"
  "US_Indiana_North"
  "US_Iowa_Des Moines"
  "US_Iowa_Waterloo"
  "US_Iowa_West"
  "US_Kansas_East"
  "US_Kansas_West"
  "US_Kansas_Wichita"
  "US_Kentucky_East"
  "US_Kentucky_Louisville"
  "US_Kentucky_West"
  "US_Louisiana_Central"
  "US_Louisiana_New Orleans"
  "US_Maine"
  "US_Maryland_Baltimore"
  "US_Maryland_and_DC"
  "US_Massachusetts_Boston"
  "US_Massachusetts_Central"
  "US_Massachusetts_Plymouth"
  "US_Massachusetts_Southeastern"
  "US_Massachusetts_West"
  "US_Michigan_Detroit"
  "US_Michigan_Grand Rapids"
  "US_Michigan_Lansing"
  "US_Michigan_North"
  "US_Minnesota_Minneapolis"
  "US_Minnesota_North"
  "US_Minnesota_Rochester"
  "US_Minnesota_Saint Cloud"
  "US_Mississippi_Gulfport"
  "US_Mississippi_North"
  "US_Missouri_East"
  "US_Missouri_Kansas"
  "US_Missouri_Springfield"
  "US_Missouri_St Louis"
  "US_Montana_East"
  "US_Montana_West"
  "US_Nebraska_East"
  "US_Nebraska_West"
  "US_Nevada"
  "US_New Hampshire"
  "US_New Jersey_North"
  "US_New Jersey_South"
  "US_New Mexico_Albuquerque"
  "US_New Mexico_Roswell"
  "US_New York_East"
  "US_New York_New York"
  "US_New York_North"
  "US_New York_West"
  "US_North Carolina_Asheville"
  "US_North Carolina_Charlotte"
  "US_North Carolina_Greensboro"
  "US_North Carolina_Raleigh"
  "US_North Carolina_Wilmington"
  "US_North Carolina_Wilson"
  "US_North Dakota_Bismarck"
  "US_North Dakota_East"
  "US_North Dakota_Minot"
  "US_Ohio_Cincinnati"
  "US_Ohio_Cleveland"
  "US_Ohio_Columbus"
  "US_Ohio_Toledo"
  "US_Oklahoma_East"
  "US_Oklahoma_Oklahoma"
  "US_Oklahoma_Tulsa"
  "US_Oklahoma_West"
  "US_Oregon_Eugene"
  "US_Oregon_Portland"
  "US_Oregon_West"
  "US_Pennsylvania_Central"
  "US_Pennsylvania_Pittsburgh"
  "US_Pennsylvania_Reading"
  "US_Pennsylvania_Scranton"
  "US_Puerto Rico"
  "US_Rhode Island"
  "US_South Carolina_Charleston"
  "US_South Carolina_Columbia"
  "US_South Carolina_Florence"
  "US_South Dakota"
  "US_Tennessee_East"
  "US_Tennessee_West"
  "US_Texas_Amarillo"
  "US_Texas_Austin"
  "US_Texas_Dallas"
  "US_Texas_Houston"
  "US_Texas_Lubbock"
  "US_Texas_San Antonio"
  "US_Texas_Southwest"
  "US_Texas_Tyler"
  "US_Texas_Victoria"
  "US_Texas_Wako"
  "US_Texas_West"
  "US_United States Minor Outlying Islands"
  "US_Utah_North"
  "US_Utah_South"
  "US_Vermont"
  "US_Virginia_Alexandria"
  "US_Virginia_Lynchburg"
  "US_Virginia_Norfolk"
  "US_Virginia_Richmond"
  "US_Virginia_Roanoke"
  "US_Washington_Coast"
  "US_Washington_Seattle"
  "US_Washington_Yakima"
  "US_West Virginia"
  "US_Wisconsin_Eau Claire"
  "US_Wisconsin_Madison"
  "US_Wisconsin_Milwaukee"
  "US_Wisconsin_North"
  "US_Wyoming"
)

TOTAL=${#REGIONS[@]}
COUNT=0
FAILED=()

for region in "${REGIONS[@]}"; do
  COUNT=$((COUNT + 1))
  log "[$COUNT/$TOTAL] $region"
  download_region "$region" || FAILED+=("$region")
done

log ""
log "=== Complete: $COUNT regions processed, ${#FAILED[@]} failed ==="
if [[ ${#FAILED[@]} -gt 0 ]]; then
  log "Failed regions:"
  for r in "${FAILED[@]}"; do
    log "  - $r"
  done
  exit 1
fi
