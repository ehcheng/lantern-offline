#!/bin/bash
BASE=$(cd "$(dirname "$0")/.." && pwd)
LOG=$BASE/logs/planet_pmtiles.log
OUT=$BASE/library/maps/pmtiles
mkdir -p "$OUT"
LATEST=""
for i in 0 1 2 3 4 5 6 7; do
  D=$(date -v-${i}d +%Y%m%d)
  if curl -sIf "https://build.protomaps.com/$D.pmtiles" >/dev/null; then LATEST=$D; break; fi
done
[ -z "$LATEST" ] && { echo "$(date +'%F %T') FAIL: no build in last 8 days" >>"$LOG"; exit 1; }
echo "$(date +'%F %T') downloading $LATEST.pmtiles (138G class, resumable)" >>"$LOG"
curl --http1.1 -C - -sS -o "$OUT/planet.pmtiles.part" "https://build.protomaps.com/$LATEST.pmtiles" >>"$LOG" 2>&1 \
  && mv "$OUT/planet.pmtiles.part" "$OUT/planet.pmtiles" \
  && echo "$(date +'%F %T') DONE $(ls -lh $OUT/planet.pmtiles | awk '{print $5}')" >>"$LOG" \
  || echo "$(date +'%F %T') FAIL curl — rerun script, resumes .part" >>"$LOG"
