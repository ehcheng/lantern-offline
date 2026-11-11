#!/bin/zsh
# Tier-1 ZIM bulk download. Resumable (curl -C -). 2 concurrent. Logs only, no TTY output.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
set -u
DEST=$ROOT/library/zim
LOG=$ROOT/logs/zim_download.log
mkdir -p "$DEST" $ROOT/logs

URLS=(
https://download.kiwix.org/zim/other/zimgit-post-disaster_en_2024-05.zim
https://download.kiwix.org/zim/other/zimgit-knots_en_2024-08.zim
https://download.kiwix.org/zim/other/zimgit-medicine_en_2024-08.zim
https://download.kiwix.org/zim/other/zimgit-water_en_2024-08.zim
https://download.kiwix.org/zim/other/zimgit-food-preparation_en_2025-04.zim
https://download.kiwix.org/zim/other/appropedia_en_all_maxi_2026-02.zim
https://download.kiwix.org/zim/other/energypedia_en_all_maxi_2026-06.zim
https://download.kiwix.org/zim/other/trueprepper.com_en_all_2026-05.zim
https://download.kiwix.org/zim/wikipedia/wikipedia_en_medicine_maxi_2026-04.zim
https://download.kiwix.org/zim/wikipedia/wikipedia_en-simple_all_maxi_2026-06.zim
https://download.kiwix.org/zim/wikibooks/wikibooks_en_all_maxi_2026-04.zim
https://download.kiwix.org/zim/wikiversity/wikiversity_en_all_maxi_2026-05.zim
https://download.kiwix.org/zim/ifixit/ifixit_en_all_2025-12.zim
https://download.kiwix.org/zim/wikipedia/wikipedia_en_all_maxi_2026-08.zim
https://download.kiwix.org/zim/gutenberg/gutenberg_en_all_2025-11.zim
)

fetch() {
  local url=$1 f=${1##*/}
  echo "$(date '+%F %T') START $f" >>"$LOG"
  if curl -sS -C - -L --retry 10 --retry-delay 15 -o "$DEST/$f.part" "$url" 2>>"$LOG"; then
    mv "$DEST/$f.part" "$DEST/$f"
    echo "$(date '+%F %T') DONE  $f $(du -h "$DEST/$f" | cut -f1)" >>"$LOG"
  else
    echo "$(date '+%F %T') FAIL  $f" >>"$LOG"
  fi
}

# ponytail: fixed 2-way split queue, not a real pool; fine for one-shot bulk run
i=0
for url in "${URLS[@]}"; do
  f=${url##*/}
  [[ -f "$DEST/$f" ]] && { echo "$(date '+%F %T') SKIP  $f (exists)" >>"$LOG"; continue; }
  if (( i % 2 == 0 )); then Q1+=("$url"); else Q2+=("$url"); fi
  ((i++))
done
( for u in "${Q1[@]:-}"; do [[ -n $u ]] && fetch "$u"; done ) &
( for u in "${Q2[@]:-}"; do [[ -n $u ]] && fetch "$u"; done ) &
wait
echo "$(date '+%F %T') ALL QUEUES DRAINED" >>"$LOG"
