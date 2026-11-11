#!/bin/bash
# Corrective pass: tier3 agent guessed ISO names; real lists fetched from archive.org metadata.
# Deletes error-page ISOs (<100MB), downloads every real ISO missing from disk, size-verified.
BASE=$(cd "$(dirname "$0")/.." && pwd)
LOG=$BASE/logs/tier3.log
log() { echo "$(date +'%F %T') $*" >>"$LOG"; }

find "$BASE/library/docs/cd3wd" -name '*.iso' -size -100M -print -delete | while read -r f; do log "DELETED-junk $(basename "$f")"; done

fetch_set() { # fetch_set <ia_id> <destdir> <iso...>
  local id=$1 dest=$2; shift 2
  mkdir -p "$dest"
  for iso in "$@"; do
    [ -s "$dest/$iso" ] && [ "$(stat -f%z "$dest/$iso")" -gt 100000000 ] && continue
    log "START-fix $iso"
    if curl -sSf -C - -L --retry 8 --retry-delay 20 -o "$dest/$iso.part" "https://archive.org/download/$id/$iso" 2>>"$LOG" \
       && [ "$(stat -f%z "$dest/$iso.part")" -gt 100000000 ]; then
      mv "$dest/$iso.part" "$dest/$iso"
      log "DONE-fix $iso $(du -h "$dest/$iso" | cut -f1)"
    else
      rm -f "$dest/$iso.part"
      log "FAIL-fix $iso"
    fi
  done
}

D=$BASE/library/docs/cd3wd
fetch_set 2015_cdw3d_primary_junior_school_dvd_set "$D/2015_primary" \
  CD3WD_100212_PRESCHOOL.iso CD3WD_100213_PRESCHOOL_NTSC_READ.iso CD3WD_10028_JHS_SIY.iso \
  CD3WD_1101_PRIMARY_MATH.iso CD3WD_1103_JHS_MATH03.iso CD3WD_1106_JHS_ALGEBRA.iso \
  CD3WD_1108_JHS_MATH08.iso CD3WD_1109_JHS_MATH09_ALGEBRA.iso CD3WD_1111_JHS_MATH11_ALGEBRA.iso \
  CD3WD_1112_JHS_MATH12_GEOMETRY.iso CD3WD_1148_JHS_SCIENCE.iso
fetch_set 2015_cdw3d_high_school_dvd_set "$D/2015_highschool" \
  CD3WD_10029_HS_SIY_TEXTBOOKS.iso CD3WD_1115_HS_TRI_PROB_STATS.iso CD3WD_1116_HS_STATS.iso \
  CD3WD_1117_HS_PRECALC.iso CD3WD_1118_HS_CALC.iso CD3WD_1124_HS_CALC2.iso \
  CD3WD_1149_HS_SCIENCE.iso CD3WD_133_HS_CNX.iso CD3WD_136_HS_PAST_EXAM.iso
fetch_set 2012_cdw3d_dvd_set "$D/2012_dvd" \
  1001_cd3wd.iso 1002_cd3wd.iso 1003_cd3wd.iso 1004_cd3wd.iso 1005_cd3wd.iso 1006_cd3wd.iso
log "CD3WD-FIX DRAINED"
