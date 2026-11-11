#!/usr/bin/env bash
# download_satellite.sh — USGS NAIP-backed aerial imagery → MBTiles
# Source: USGS National Map USGSImageryOnly (public domain, NAIP-backed)
#   https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer
# Coverage: San Mateo Co z0-16 | 9-county Bay Area z0-16 | N.CA z0-13
# Budget: ~5 GB total. Idempotent (skips existing tiles). 4 parallel workers.
# Usage: bash download_satellite.sh [--dry-run]
ROOT=$(cd "$(dirname "$0")/.." && pwd)
set -euo pipefail

LOG=$ROOT/logs/satellite.log
OUTDIR=$ROOT/library/maps/satellite_bayarea
TILE_SERVER="https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile"
WORKERS=4        # parallel curl; USGS is fine with this, be respectful
SLEEP_MS=50      # 50ms between each worker's requests = ~20 req/s per worker

mkdir -p "$OUTDIR" "$(dirname "$LOG")"
exec > >(tee -a "$LOG") 2>&1

echo "=== satellite download started $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true && echo "[DRY-RUN mode]"

# ── helpers ───────────────────────────────────────────────────────────────────

deg2xtile() { python3 -c "import math; z=$3; print(int((($2+180)/360)*(2**z)))"; }
deg2ytile() { python3 -c "import math; z=$3; lat=math.radians($1); print(int((1-math.log(math.tan(lat)+1/math.cos(lat))/math.pi)/2*(2**z)))"; }

init_mbtiles() {
  local db="$1" name="$2" desc="$3" minz="$4" maxz="$5"
  [[ -f "$db" ]] && return 0
  sqlite3 "$db" <<SQL
CREATE TABLE IF NOT EXISTS tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB, PRIMARY KEY(zoom_level,tile_column,tile_row));
CREATE TABLE IF NOT EXISTS metadata (name TEXT, value TEXT, PRIMARY KEY(name));
INSERT OR REPLACE INTO metadata VALUES ('name','$name');
INSERT OR REPLACE INTO metadata VALUES ('type','baselayer');
INSERT OR REPLACE INTO metadata VALUES ('version','1.1');
INSERT OR REPLACE INTO metadata VALUES ('description','$desc');
INSERT OR REPLACE INTO metadata VALUES ('format','jpg');
INSERT OR REPLACE INTO metadata VALUES ('minzoom','$minz');
INSERT OR REPLACE INTO metadata VALUES ('maxzoom','$maxz');
SQL
  echo "[init] $db"
}

# Download one tile and insert into MBTiles (TMS y-flip)
# Args: db zoom x y
fetch_tile() {
  local db="$1" z="$2" x="$3" y="$4"
  # MBTiles TMS convention: y is flipped
  local tms_y=$(( (1 << z) - 1 - y ))
  # Skip if already stored
  local exists
  exists=$(sqlite3 "$db" "SELECT COUNT(*) FROM tiles WHERE zoom_level=$z AND tile_column=$x AND tile_row=$tms_y;")
  [[ "$exists" == "1" ]] && return 0

  local tmp
  tmp=$(mktemp /tmp/sat_tile_XXXXXX.jpg)
  local url="$TILE_SERVER/$z/$y/$x"
  local http_code
  http_code=$(curl -s -o "$tmp" -w "%{http_code}" --max-time 15 --retry 3 --retry-delay 2 "$url")
  if [[ "$http_code" == "200" ]] && file "$tmp" 2>/dev/null | grep -q JPEG; then
    sqlite3 "$db" "INSERT OR REPLACE INTO tiles VALUES ($z,$x,$tms_y,readfile('$tmp'));"
  else
    echo "[warn] tile $z/$x/$y → HTTP $http_code" >&2
  fi
  rm -f "$tmp"
  sleep "0.$(printf '%03d' $SLEEP_MS)"
}
export -f fetch_tile deg2xtile deg2ytile
export TILE_SERVER SLEEP_MS

# Download all tiles for a bounding box into an MBTiles file
# Args: db lat_min lat_max lon_min lon_max zoom_min zoom_max
download_region() {
  local db="$1" lat_min="$2" lat_max="$3" lon_min="$4" lon_max="$5" z_min="$6" z_max="$7"

  for z in $(seq "$z_min" "$z_max"); do
    local x_min x_max y_min y_max
    x_min=$(python3 -c "import math; z=$z; print(int((($lon_min+180)/360)*(2**z)))")
    x_max=$(python3 -c "import math; z=$z; print(int((($lon_max+180)/360)*(2**z)))")
    y_min=$(python3 -c "import math; z=$z; lat=math.radians($lat_max); print(int((1-math.log(math.tan(lat)+1/math.cos(lat))/math.pi)/2*(2**z)))")
    y_max=$(python3 -c "import math; z=$z; lat=math.radians($lat_min); print(int((1-math.log(math.tan(lat)+1/math.cos(lat))/math.pi)/2*(2**z)))")

    local total=$(( (x_max - x_min + 1) * (y_max - y_min + 1) ))
    echo "[z$z] ${total} tiles x=[$x_min..$x_max] y=[$y_min..$y_max]"
    $DRY_RUN && continue

    # Parallel fetch: one line per tile "db z x y", split on tab as delimiter
    {
      for x in $(seq "$x_min" "$x_max"); do
        for y in $(seq "$y_min" "$y_max"); do
          printf '%s\t%s\t%s\t%s\n' "$db" "$z" "$x" "$y"
        done
      done
    } | xargs -P "$WORKERS" -I{} bash -c \
        'IFS=$'"'"'\t'"'"' read -r db z x y <<< "{}"; fetch_tile "$db" "$z" "$x" "$y"'
  done
}

# ── size gate (20 GB) ─────────────────────────────────────────────────────────
SIZE_LIMIT_GB=20
check_size() {
  local used_gb
  used_gb=$(du -sk "$OUTDIR" 2>/dev/null | awk '{print int($1/1048576)}')
  if (( used_gb >= SIZE_LIMIT_GB )); then
    echo "[ABORT] Size limit ${SIZE_LIMIT_GB}GB reached (${used_gb}GB used). Stopping."
    exit 1
  fi
}

# ── region 1: San Mateo County — z0-16 (max res, ~330 MB) ────────────────────
SM_DB="$OUTDIR/san_mateo_co_z0-16.mbtiles"
init_mbtiles "$SM_DB" \
  "USGS NAIP San Mateo County" \
  "USGS USGSImageryOnly (NAIP-backed, public domain). San Mateo County CA. z0-16 (~0.6m at z16)." \
  0 16

echo "--- San Mateo County z0-16 ---"
download_region "$SM_DB" 37.10 37.70 -122.55 -122.05 0 16
check_size
echo "[done] San Mateo County: $(du -sh "$SM_DB" | awk '{print $1}')"

# ── region 2: 9-county Bay Area — z0-16 (~3.6 GB) ────────────────────────────
BAY_DB="$OUTDIR/bayarea_9county_z0-16.mbtiles"
init_mbtiles "$BAY_DB" \
  "USGS NAIP Bay Area 9-county" \
  "USGS USGSImageryOnly (NAIP-backed, public domain). 9-county SF Bay Area. z0-16 (~0.6m at z16)." \
  0 16

echo "--- 9-county Bay Area z0-16 ---"
download_region "$BAY_DB" 36.90 38.85 -123.10 -121.20 0 16
check_size
echo "[done] Bay Area: $(du -sh "$BAY_DB" | awk '{print $1}')"

# ── region 3: Northern California — z0-13 (~350 MB) ──────────────────────────
NCA_DB="$OUTDIR/northern_ca_z0-13.mbtiles"
init_mbtiles "$NCA_DB" \
  "USGS NAIP Northern California" \
  "USGS USGSImageryOnly (NAIP-backed, public domain). Northern California. z0-13 (overview/planning)." \
  0 13

echo "--- Northern California z0-13 ---"
download_region "$NCA_DB" 36.00 42.00 -124.50 -119.00 0 13
check_size
echo "[done] N.California: $(du -sh "$NCA_DB" | awk '{print $1}')"

# ── README ────────────────────────────────────────────────────────────────────
cat > "$OUTDIR/README.md" << 'README'
# Satellite / Aerial Imagery — SF Bay Area

## Source
**USGS National Map — USGSImageryOnly basemap**
- URL: https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer
- Imagery: USDA NAIP (National Agriculture Imagery Program), public domain
- Resolution: ~0.6 m/px at zoom 16 (best available for CONUS)
- Vintage: 2017–2021 CONUS, refreshed June 2024
- License: Public domain (US federal government work, 17 USC §105)

## Files

| File | Coverage | Zoom | Approx Size | Best for |
|------|----------|------|-------------|---------|
| san_mateo_co_z0-16.mbtiles | San Mateo County | 0–16 | ~330 MB | Max-res home area |
| bayarea_9county_z0-16.mbtiles | 9-county Bay Area | 0–16 | ~3.6 GB | Bay Area land nav |
| northern_ca_z0-13.mbtiles | Northern California | 0–13 | ~350 MB | Wide-area planning |

## Viewing offline

### Phone/tablet (recommended)
- **Guru Maps** (iOS/Android) — import MBTiles directly
- **Locus Map** (Android) — supports MBTiles as offline map layer
- **MAPCARTA / AlpineQuest** — MBTiles support

### Desktop
- **QGIS**: Layer → Add Layer → Add Raster Layer → select .mbtiles
- **TileServer GL** (Node): `tileserver-gl san_mateo_co_z0-16.mbtiles` then open http://localhost:8080
- **pmtiles** CLI can inspect/convert: `pmtiles show <file>` (though these are MBTiles not PMTiles)

### Self-hosted (serving box)
```
# Any HTTP server that speaks XYZ tiles from MBTiles:
npx tileserver-gl-light --mbtiles bayarea_9county_z0-16.mbtiles
```
Tile URL pattern: `http://localhost:8080/styles/basic-preview/{z}/{x}/{y}.jpg`

## Notes
- MBTiles uses TMS tile convention (y-flipped vs XYZ/Google). Apps handle this automatically.
- z16 = ~0.6m ground resolution. At z15 = ~1.2m. z13 = ~5m (planning overview).
- San Mateo County tiles are fully included within the Bay Area file — keep both for fast
  single-county access vs. full Bay Area.
- Downloaded: $(date +%Y-%m-%d)
README

echo "=== satellite download COMPLETE $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "Total: $(du -sh "$OUTDIR" | awk '{print $1}')"
