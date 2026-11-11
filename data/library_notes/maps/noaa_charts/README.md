# NOAA Nautical Charts

Offline US nautical charts for coastal/inland navigation. Two formats acquired:

## Formats

### ENC — Electronic Navigational Charts (vector, S-57 format)
- **Location:** `enc/cells/` — individual S-57 cell files (`.000` extension)
- **Source:** `charts.noaa.gov/ENCs/All_ENCs.zip` — official NOAA distribution, updated daily
- **Size:** 834 MB zip (`enc/All_ENCs.zip`) / 2.28 GB extracted, 7,320 cells
- **Coverage:** All US waters (coastal, Great Lakes, inland rivers)
- **Format:** IHO S-57 vector — encodes depth contours, aids to navigation, hazards as queryable objects
- **Catalog:** `enc/ENCProdCat_19115.xml` — ISO 19115 metadata for all cells

### RNC — Raster Navigational Charts (BSB/KAP format)
- **Location:** `rnc/` — `.kap` and `.bsb` sidecar files
- **Source:** archive.org `NOAA_RNC` item — the final NOAA RNC set
- **Charts:** 660 charts (one `.bsb` file each) in 1,456 chart images (`.kap` files; a chart with insets has several), 2,116 files
- **Size:** 4.27 GB
- **Coverage:** Full US coastal coverage; NOAA sunset RNC production in 2025 (ENC is the successor)
- **Format:** BSB/KAP raster — scanned chart images georeferenced, visually identical to paper charts

## What opens these

| Software | ENC | RNC | Platform | Notes |
|----------|-----|-----|----------|-------|
| **OpenCPN** | ✅ | ✅ | macOS/Win/Linux/iOS/Android | Best all-around; free, offline-capable |
| **SeaClear II** | ❌ | ✅ | Windows | Lightweight KAP viewer |
| **qtVlm** | ✅ | ✅ | macOS/Win/Linux | Route planning focus |
| **QGIS** | ✅ | ✅ | macOS/Win/Linux | GIS power tool; needs S-57 plugin |
| **iNavX** | ✅ | ✅ | iOS | Mobile chartplotter |

**Recommended for offline survival use: OpenCPN** — free, cross-platform, handles both formats, works with no internet after install.

**Installers are on the Tools shelf:** [tools/opencpn/](../../tools/opencpn/) (Mac and Windows, with setup steps in its [README](../../tools/opencpn/README.md)).

OpenCPN ENC setup: Preferences → Charts → Add chart directory → point at `enc/cells/`.
OpenCPN RNC setup: same, point at `rnc/`.

## Currency
- ENC: NOAA updates the cells daily. Refreshing needs the internet and the download script `download_noaa_charts.sh`, which is in the build repository, not on the box
- RNC: static archive (NOAA ceased raster production ~2025); use ENC for current data
