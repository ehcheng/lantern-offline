#!/bin/zsh
# R9 Spanish basket (approved 2026-09-21). Resumable. Sequential — only ~3GB.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
set -u
DEST=$ROOT/library/zim
LOG=$ROOT/logs/zim_download_es.log
mkdir -p "$DEST" "${LOG:h}"

# wikipedia_es_medicine_maxi_2026-04 already on disk — not re-downloaded
URLS=(
https://download.kiwix.org/zim/zimit/medlineplus.gov_es_all_2024-12.zim
https://download.kiwix.org/zim/wikipedia/wikipedia_es_top_nopic_2026-07.zim
https://download.kiwix.org/zim/vikidia/vikidia_es_all_nopic_2026-09.zim
https://download.kiwix.org/zim/wikibooks/wikibooks_es_all_nopic_2025-10.zim
)

for url in "${URLS[@]}"; do
  f=${url##*/}
  [[ -f "$DEST/$f" ]] && { echo "$(date '+%F %T') SKIP  $f (exists)" >>"$LOG"; continue; }
  echo "$(date '+%F %T') START $f" >>"$LOG"
  if curl -sS -C - -L --retry 10 --retry-delay 15 -o "$DEST/$f.part" "$url" 2>>"$LOG"; then
    mv "$DEST/$f.part" "$DEST/$f"
    echo "$(date '+%F %T') DONE  $f $(du -h "$DEST/$f" | cut -f1)" >>"$LOG"
  else
    echo "$(date '+%F %T') FAIL  $f" >>"$LOG"
  fi
done
echo "$(date '+%F %T') ES BASKET DRAINED" >>"$LOG"
