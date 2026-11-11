#!/bin/zsh
# Maps + datasets + Tier-1 ZIM stragglers. URLs verified in docs/sources/source_map.md 2026-09-14.
# Resumable. 2 concurrent queues. Logs only.
set -u
BASE=$(cd "$(dirname "$0")/.." && pwd)
LOG=$BASE/logs/maps_datasets.log
mkdir -p $BASE/library/{zim,maps/{osmand,pmtiles,geofabrik},datasets/{climate_normals,dailymed,ephemeris,fcc}} $BASE/logs
export PATH=$BASE/build/bin:$PATH

fetch() { # fetch <url> <destdir> [filename]
  local url=$1 dest=$2 f=${3:-${1##*/}}
  f=${f%%\?*}
  [[ -f "$dest/$f" ]] && { echo "$(date '+%F %T') SKIP $f" >>"$LOG"; return 0; }
  echo "$(date '+%F %T') START $f" >>"$LOG"
  if curl -sS -C - -L --retry 10 --retry-delay 15 -o "$dest/$f.part" "$url" 2>>"$LOG"; then
    mv "$dest/$f.part" "$dest/$f"
    echo "$(date '+%F %T') DONE  $f $(du -h "$dest/$f" | cut -f1)" >>"$LOG"
  else
    echo "$(date '+%F %T') FAIL  $f" >>"$LOG"
  fi
}

queue_zims() { # Tier-1 stragglers + Tier-2 ZIMs (exact names from source_map.md)
  for u in \
    https://download.kiwix.org/zim/stack_exchange/ham.stackexchange.com_en_all_2026-02.zim \
    https://download.kiwix.org/zim/phet/phet_en_all_2026-08.zim \
    https://download.kiwix.org/zim/wikipedia/wikipedia_es_medicine_maxi_2026-04.zim \
    https://download.kiwix.org/zim/stack_exchange/diy.stackexchange.com_en_all_2026-08.zim \
    https://download.kiwix.org/zim/stack_exchange/electronics.stackexchange.com_en_all_2026-08.zim \
    https://download.kiwix.org/zim/stack_exchange/gardening.stackexchange.com_en_all_2026-08.zim \
    https://download.kiwix.org/zim/stack_exchange/outdoors.stackexchange.com_en_all_2026-08.zim \
    https://download.kiwix.org/zim/stack_exchange/medicalsciences.stackexchange.com_en_all_2026-02.zim \
    https://download.kiwix.org/zim/stack_exchange/physics.stackexchange.com_en_all_2026-08.zim \
    https://download.kiwix.org/zim/stack_exchange/chemistry.stackexchange.com_en_all_2026-07.zim \
    https://download.kiwix.org/zim/wiktionary/wiktionary_en_all_nopic_2026-08.zim \
    https://download.kiwix.org/zim/wikivoyage/wikivoyage_en_all_maxi_2026-06.zim \
    https://download.kiwix.org/zim/wikisource/wikisource_en_all_maxi_2026-05.zim \
  ; do fetch "$u" $BASE/library/zim; done
}

queue_maps_datasets() {
  # Geofabrik US PBF + checksum
  fetch https://download.geofabrik.de/north-america/us-latest.osm.pbf $BASE/library/maps/geofabrik
  fetch https://download.geofabrik.de/north-america/us-latest.osm.pbf.md5 $BASE/library/maps/geofabrik
  # OsmAnd per-state OBFs — discover file list live (no single US file exists)
  curl -sS https://download.osmand.net/list.php 2>>"$LOG" \
    | grep -oE 'Us_[a-z_-]+_northamerica_2\.obf\.zip' | sort -u > $BASE/library/maps/osmand/filelist.txt
  echo "$(date '+%F %T') OSMAND file count: $(wc -l < $BASE/library/maps/osmand/filelist.txt)" >>"$LOG"
  while read -r f; do
    fetch "https://download.osmand.net/download?standard=yes&file=$f" $BASE/library/maps/osmand "$f"
  done < $BASE/library/maps/osmand/filelist.txt
  # NOAA climate normals (467 station CSVs, dir scrape)
  curl -sS https://www.ncei.noaa.gov/data/normals-hourly/1991-2020/access/ 2>>"$LOG" \
    | grep -oE 'href="[^"]+\.csv"' | cut -d'"' -f2 | sort -u | while read -r c; do
      fetch "https://www.ncei.noaa.gov/data/normals-hourly/1991-2020/access/$c" $BASE/library/datasets/climate_normals
    done
  # JPL DE440s ephemeris
  fetch https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp $BASE/library/datasets/ephemeris
  # FCC ULS amateur dump
  fetch https://data.fcc.gov/download/pub/uls/complete/l_amat.zip $BASE/library/datasets/fcc
  # DailyMed Rx SPL (6 parts)
  for i in 1 2 3 4 5 6; do
    fetch "https://dailymed-data.nlm.nih.gov/public-release-files/dm_spl_release_human_rx_part${i}.zip" $BASE/library/datasets/dailymed
  done
  # Protomaps US extract — needs pmtiles CLI
  if command -v pmtiles >/dev/null; then
    BUILD_KEY=$(curl -sS https://build-metadata.protomaps.dev/builds.json | grep -oE '[0-9]{8}\.pmtiles' | tail -1)
    echo "$(date '+%F %T') PMTILES extract from $BUILD_KEY" >>"$LOG"
    pmtiles extract "https://build.protomaps.com/$BUILD_KEY" $BASE/library/maps/pmtiles/us.pmtiles --bbox=-180,18,-66,72 >>"$LOG" 2>&1 \
      && echo "$(date '+%F %T') DONE us.pmtiles" >>"$LOG" || echo "$(date '+%F %T') FAIL us.pmtiles" >>"$LOG"
  else
    echo "$(date '+%F %T') SKIP pmtiles extract — pmtiles CLI not installed (brew install pmtiles)" >>"$LOG"
  fi
}

queue_zims &
queue_maps_datasets &
wait
echo "$(date '+%F %T') MAPS+DATASETS DRAINED" >>"$LOG"
