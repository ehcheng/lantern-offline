#!/bin/zsh
# Tier-3 bulk download: TED ZIMs, Survivor Library, CD3WD, Prelinger films.
# Idempotent (skip-existing, curl -C - resume). ALL output to LOG, never stdout.
# ponytail: fixed 2-way queue split (same as download_zims.sh); fine for one-shot bulk.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
set -u
LOG=$ROOT/logs/tier3.log
ZIM_DEST=$ROOT/library/zim   # flat: kiwix-serve and gen_index read zim/*.zim
VIDEO_DEST=$ROOT/library/video/prelinger
CD3WD_DEST=$ROOT/library/docs/cd3wd
SURV_DEST=$ROOT/library/docs/survivor_library

mkdir -p "$ZIM_DEST" "$VIDEO_DEST" "$CD3WD_DEST" "$SURV_DEST" \
         $ROOT/logs

ts() { date '+%F %T'; }

# ---------------------------------------------------------------------------
# DISK BUDGET CHECK: library ~482GB, keep total under 1.3TB
# ---------------------------------------------------------------------------
AVAIL_KB=$(df $ROOT | awk 'NR==2{print $4}')
AVAIL_GB=$(( AVAIL_KB / 1024 / 1024 ))
echo "$(ts) DISK_CHECK avail=${AVAIL_GB}GB (need ~275GB for full Tier-3 queue)" >>"$LOG"
if (( AVAIL_GB < 300 )); then
  echo "$(ts) ABORT insufficient disk: ${AVAIL_GB}GB free, need >=300GB" >>"$LOG"
  exit 1
fi

# ---------------------------------------------------------------------------
# SECTION 1: TED TOPIC ZIMS (~13.7 GB total)
# Verified 2026-09-16 against https://download.kiwix.org/zim/ted/
# Latest: 2026-04 for all 5 topics. Mirror: mirror.download.kiwix.org direct.
# ---------------------------------------------------------------------------
echo "$(ts) START section=TED_ZIMS" >>"$LOG"

TED_URLS=(
  https://mirror.download.kiwix.org/zim/ted/ted_mul_biology_2026-04.zim
  https://mirror.download.kiwix.org/zim/ted/ted_mul_medicine_2026-04.zim
  https://mirror.download.kiwix.org/zim/ted/ted_mul_health-care_2026-04.zim
  https://mirror.download.kiwix.org/zim/ted/ted_mul_physics_2026-04.zim
  https://mirror.download.kiwix.org/zim/ted/ted_mul_chemistry_2026-04.zim
)

fetch_zim() {
  local url=$1 f=${1##*/} dest=$2
  if [[ -f "$dest/$f" ]]; then
    echo "$(ts) SKIP  $f (exists)" >>"$LOG"
    return 0
  fi
  echo "$(ts) START $f" >>"$LOG"
  if curl -sS -C - -L --retry 10 --retry-delay 15 -o "$dest/$f.part" "$url" 2>>"$LOG"; then
    mv "$dest/$f.part" "$dest/$f"
    echo "$(ts) DONE  $f $(du -h "$dest/$f" | cut -f1)" >>"$LOG"
  else
    echo "$(ts) FAIL  $f" >>"$LOG"
  fi
}

# Run TED ZIMs 2-wide (same pattern as download_zims.sh)
TED_Q1=(); TED_Q2=(); i=0
for url in "${TED_URLS[@]}"; do
  if (( i % 2 == 0 )); then TED_Q1+=("$url"); else TED_Q2+=("$url"); fi
  (( i++ ))
done
( for u in "${TED_Q1[@]:-}"; do [[ -n $u ]] && fetch_zim "$u" "$ZIM_DEST"; done ) &
( for u in "${TED_Q2[@]:-}"; do [[ -n $u ]] && fetch_zim "$u" "$ZIM_DEST"; done ) &
wait
echo "$(ts) DONE  section=TED_ZIMS" >>"$LOG"

# ---------------------------------------------------------------------------
# SECTION 2: SURVIVOR LIBRARY (~122 GB)
# Source: archive.org/details/survival.library (verified 2026-09-16: 122.0GB, 7448 PDFs)
# Actual size: 122GB — UNDER 300GB threshold, proceeding with bulk download.
# Using archive.org compress/zip endpoint: streams a ZIP of all PDFs.
# ---------------------------------------------------------------------------
echo "$(ts) START section=SURVIVOR_LIBRARY size_verified=122.0GB threshold=300GB action=DOWNLOAD" >>"$LOG"

SURV_ZIP="$SURV_DEST/survival_library_pdfs.zip"
if [[ -f "$SURV_DEST/.done_survival_library" ]]; then
  echo "$(ts) SKIP  survival_library (already extracted)" >>"$LOG"
elif [[ -f "$SURV_ZIP" ]]; then
  echo "$(ts) SKIP  survival_library_pdfs.zip (exists, re-run unzip if needed)" >>"$LOG"
else
  echo "$(ts) START survival_library_pdfs.zip (~122GB zip-on-demand from archive.org)" >>"$LOG"
  # archive.org compress endpoint returns a streaming ZIP of all PDFs in the item
  if curl -sS -C - -L --retry 5 --retry-delay 30 \
      -o "$SURV_ZIP.part" \
      "https://archive.org/compress/survival.library/formats=PDF" 2>>"$LOG"; then
    mv "$SURV_ZIP.part" "$SURV_ZIP"
    SZ=$(du -h "$SURV_ZIP" | cut -f1)
    echo "$(ts) DONE  survival_library_pdfs.zip $SZ" >>"$LOG"
    # Extract in place and remove zip to save space
    echo "$(ts) START unzip survival_library to $SURV_DEST/" >>"$LOG"
    if unzip -n -q "$SURV_ZIP" -d "$SURV_DEST/" 2>>"$LOG"; then
      touch "$SURV_DEST/.done_survival_library"
      rm "$SURV_ZIP"
      echo "$(ts) DONE  survival_library extracted $(du -sh "$SURV_DEST" | cut -f1)" >>"$LOG"
    else
      echo "$(ts) FAIL  unzip survival_library" >>"$LOG"
    fi
  else
    echo "$(ts) FAIL  survival_library_pdfs.zip" >>"$LOG"
  fi
fi
echo "$(ts) DONE  section=SURVIVOR_LIBRARY" >>"$LOG"

# ---------------------------------------------------------------------------
# SECTION 3: CD3WD — archive.org ISO sets
# Verified 2026-09-16:
#   CD3WD12                          0.64GB (100 PDFs, disks 1&2)
#   2012_cdw3d_dvd_set              27.83GB (6 ISO files)
#   2015_cdw3d_primary_junior_school_dvd_set  50.47GB (11 ISOs)
#   2015_cdw3d_high_school_dvd_set  41.68GB  (9 ISOs)
# Combined: ~120.6GB — UNDER 150GB threshold, proceeding.
# Novels/misc/audit sets excluded (not practical survival content).
# ---------------------------------------------------------------------------
echo "$(ts) START section=CD3WD size_verified=120.6GB threshold=150GB action=DOWNLOAD" >>"$LOG"

fetch_ia_file() {
  local ia_id=$1 filename=$2 dest=$3
  local url="https://archive.org/download/${ia_id}/${filename}"
  if [[ -f "$dest/$filename" ]]; then
    echo "$(ts) SKIP  $filename (exists)" >>"$LOG"
    return 0
  fi
  echo "$(ts) START $filename" >>"$LOG"
  if curl -sS -C - -L --retry 8 --retry-delay 20 -o "$dest/$filename.part" "$url" 2>>"$LOG"; then
    mv "$dest/$filename.part" "$dest/$filename"
    echo "$(ts) DONE  $filename $(du -h "$dest/$filename" | cut -f1)" >>"$LOG"
  else
    echo "$(ts) FAIL  $filename" >>"$LOG"
  fi
}

# CD3WD12 — individual PDFs via compress endpoint (0.64GB)
CD3WD12_DONE="$CD3WD_DEST/.done_cd3wd12"
if [[ -f "$CD3WD12_DONE" ]]; then
  echo "$(ts) SKIP  cd3wd12 (already done)" >>"$LOG"
else
  echo "$(ts) START cd3wd12 pdfs (~640MB)" >>"$LOG"
  if curl -sS -C - -L --retry 5 --retry-delay 20 \
      -o "$CD3WD_DEST/cd3wd12_pdfs.zip.part" \
      "https://archive.org/compress/CD3WD12/formats=PDF" 2>>"$LOG"; then
    mv "$CD3WD_DEST/cd3wd12_pdfs.zip.part" "$CD3WD_DEST/cd3wd12_pdfs.zip"
    if unzip -n -q "$CD3WD_DEST/cd3wd12_pdfs.zip" -d "$CD3WD_DEST/" 2>>"$LOG"; then
      touch "$CD3WD12_DONE"
      rm "$CD3WD_DEST/cd3wd12_pdfs.zip"
      echo "$(ts) DONE  cd3wd12 extracted" >>"$LOG"
    else
      echo "$(ts) FAIL  unzip cd3wd12" >>"$LOG"
    fi
  else
    echo "$(ts) FAIL  cd3wd12_pdfs.zip" >>"$LOG"
  fi
fi

# 2012 DVD set ISOs (6 files, ~27.8GB total) — sequential, large files
mkdir -p "$CD3WD_DEST/2012_dvd"
for isofile in 1001_cd3wd.iso 1002_cd3wd.iso 1003_cd3wd.iso \
               1004_cd3wd.iso 1005_cd3wd.iso 1006_cd3wd.iso; do
  fetch_ia_file "2012_cdw3d_dvd_set" "$isofile" "$CD3WD_DEST/2012_dvd"
done

# 2015 Primary/Junior School ISOs (~50.5GB)
mkdir -p "$CD3WD_DEST/2015_primary"
for isofile in \
  CD3WD_100212_PRESCHOOL.iso \
  CD3WD_100213_PRESCHOOL_NTSC_READ.iso \
  CD3WD_10028_JHS_SIY.iso \
  CD3WD_1101_PRIMARY_MATH.iso \
  CD3WD_1103_JHS_MATH03.iso \
  CD3WD_1106_JHS_ALGEBRA.iso \
  CD3WD_1107_JHS_EARTH_SCIENCE.iso \
  CD3WD_1108_JHS_LIFE_SCIENCE.iso \
  CD3WD_1109_JHS_PHYSICAL_SCIENCE.iso \
  CD3WD_1110_JHS_CHEMISTRY.iso \
  CD3WD_1111_JHS_PHYSICS.iso; do
  fetch_ia_file "2015_cdw3d_primary_junior_school_dvd_set" "$isofile" "$CD3WD_DEST/2015_primary"
done

# 2015 High School ISOs (~41.7GB)
mkdir -p "$CD3WD_DEST/2015_highschool"
for isofile in \
  CD3WD_10029_HS_SIY_TEXTBOOKS.iso \
  CD3WD_1115_HS_TRI_PROB_STATS.iso \
  CD3WD_1116_HS_STATS.iso \
  CD3WD_1117_HS_PRECALC.iso \
  CD3WD_1118_HS_CALC.iso \
  CD3WD_1119_HS_CALC_INT_CALC_SEQ.iso \
  CD3WD_1120_HS_GEOMETRY.iso \
  CD3WD_1121_HS_LANGUAGE_ARTS.iso \
  CD3WD_1124_HS_CALC2.iso; do
  fetch_ia_file "2015_cdw3d_high_school_dvd_set" "$isofile" "$CD3WD_DEST/2015_highschool"
done

echo "$(ts) DONE  section=CD3WD" >>"$LOG"

# ---------------------------------------------------------------------------
# SECTION 4: PRELINGER FILMS — curated survival-relevant subset (~20 films)
# h.264 derivatives only (not originals). URL: archive.org/download/<id>/<id>.mp4
# Selection criteria: practical skills (first aid, food, farming, construction,
# civil defense, trades). Verified against Prelinger collection 2026-09-16.
# Estimated total: ~2.5GB (h.264 derivatives avg ~125MB each)
# ---------------------------------------------------------------------------
echo "$(ts) START section=PRELINGER" >>"$LOG"
echo "$(ts) INFO  Prelinger curated list (20 films, h.264 derivatives):" >>"$LOG"

# Format: "identifier|human-readable title"
PRELINGER_ITEMS=(
  "Survival1951|Survival Under Atomic Attack (1951) - civil defense basics"
  "0994_Emergency_First_Aid_A_Study_in_Motion_Pictures_to_Aid_Civil_Def_01_00_42_04|Emergency First Aid - Aid to Civil Defense (1942)"
  "201293_Emergency_First_Aid_P2_Bandaging|Emergency First Aid Part 2 - Bandaging Wounds and Burns (1942)"
  "ShakeHan1970|Shake Hands With Danger (1970) - farm/machinery safety"
  "victory_garden|Victory Gardens - food production"
  "Woodwork1940|Woodworker, The (1940) - carpentry skills"
  "FoodforF1943|Food for Fighters (1943) - wartime food preparation"
  "FromtheG1954|From the Ground Up (1954) - farming/agriculture"
  "Looktoth1953|Look to the Land (1953) - sustainable farming"
  "0169_Woodworker_The_E01724_10_24_17_24|Woodworker (1940) - alternate cut"
  "6139_Ready_on_the_Home_Front_01_22_01_29|Ready on the Home Front (1940) - wartime home preparedness"
  "AtomicAl1951|Atomic Alert Elementary (1951) - civil defense"
  "DuckandC1951|Duck and Cover (1951) - civil defense"
  "0555_Master_Hands_18_27_28_00|Master Hands (1936) - factory/trades craft"
  "Automoti1940|Automotive Service (1940) - vehicle repair"
  "0220_Golden_Harvest_Fifty_Years_of_Calpak_Progress_M06690_00_01_01_00|Golden Harvest - Calpak canning operations (1950)"
  "TimeSave1936|Time Savers for House Makers (1936) - home food preservation"
  "Chickeno1948|Chicken of Tomorrow (1948) - poultry farming"
  "0790_Maintenance_of_Roads_08_15_00_28|Maintenance of Roads (1920) - infrastructure repair"
  "0230_Pick_of_the_Pod_01_18_48_00-0037|Pick of the Pod (1939) - vegetable/canning"
)

# Log the full list before downloading
echo "$(ts) INFO  prelinger_list_start" >>"$LOG"
for entry in "${PRELINGER_ITEMS[@]}"; do
  echo "$(ts) LIST  ${entry%%|*} | ${entry#*|}" >>"$LOG"
done
echo "$(ts) INFO  prelinger_list_end count=${#PRELINGER_ITEMS[@]}" >>"$LOG"

fetch_prelinger() {
  local id=$1 label=$2
  local f="${id}.mp4"
  local url="https://archive.org/download/${id}/${f}"
  if [[ -f "$VIDEO_DEST/$f" ]]; then
    echo "$(ts) SKIP  $f (exists)" >>"$LOG"
    return 0
  fi
  echo "$(ts) START $f [$label]" >>"$LOG"
  if curl -sS -C - -L --retry 8 --retry-delay 15 -o "$VIDEO_DEST/$f.part" "$url" 2>>"$LOG"; then
    mv "$VIDEO_DEST/$f.part" "$VIDEO_DEST/$f"
    echo "$(ts) DONE  $f $(du -h "$VIDEO_DEST/$f" | cut -f1)" >>"$LOG"
  else
    echo "$(ts) FAIL  $f [$label]" >>"$LOG"
  fi
}

# ponytail: 2-wide same as rest of script; Prelinger files are small so this is fine
PREL_Q1=(); PREL_Q2=(); i=0
for entry in "${PRELINGER_ITEMS[@]}"; do
  id="${entry%%|*}"
  label="${entry#*|}"
  if (( i % 2 == 0 )); then PREL_Q1+=("${id}|||${label}"); else PREL_Q2+=("${id}|||${label}"); fi
  (( i++ ))
done

fetch_prel_list() {
  for item in "$@"; do
    [[ -n $item ]] || continue
    fetch_prelinger "${item%%|||*}" "${item#*|||}"
  done
}

( fetch_prel_list "${PREL_Q1[@]:-}" ) &
( fetch_prel_list "${PREL_Q2[@]:-}" ) &
wait
echo "$(ts) DONE  section=PRELINGER" >>"$LOG"

# ---------------------------------------------------------------------------
echo "$(ts) ALL_SECTIONS_DRAINED" >>"$LOG"
