#!/bin/bash
# D2: prepare a unit that LEAVES the household. See library/LICENSES.md.
#
#   strip_restricted.sh <data-root> gifted   # verify notices, remove nothing
#   strip_restricted.sh <data-root> sold     # remove NC/trademark content
#
# Run against a STAGING COPY (e.g. rsync --link-dest clone), never the
# household master. After a 'sold' strip: rerun build_frontend.sh and the
# manifest pass-B reseal against the staging tree so indexes/links regen
# without the stripped items, THEN rsync to the unit. Writes STRIPPED.txt
# at the data root so D1 verification can exclude removed paths.
# NOTE (LICENSES.md): 'sold' covers the three named classes only — WHO/MSF
# medical PDFs and Kolibri NC channels still need per-item clearance.
set -euo pipefail

ROOT=${1:?usage: strip_restricted.sh <data-root> gifted|sold}
MODE=${2:?usage: strip_restricted.sh <data-root> gifted|sold}
cd "$ROOT"

# notices that must ship on EVERY unit leaving the household
for f in LICENSES.md tools/models/LICENSE-llama-3.1.txt tools/models/LICENSE-llama-3.2.txt; do
  [ -f "$f" ] || { echo "FAIL missing notice: $f"; exit 1; }
done
echo "notices OK (Llama license texts + LICENSES.md present)"

case "$MODE" in
  gifted)
    echo "gifted: nothing to strip"
    ;;
  sold)
    # Hesperian (noncommercial) + its derived search wrappers;
    # Gutenberg ZIM (trademark on sold copies)
    STRIP=(
      mirrors/hesperian
      _app/text/mirrors/hesperian
      zim/gutenberg_en_all_2025-11.zim
      # G2 additions 09-19: free/publicly posted but not sale-cleared
      docs/sanitation/hesperian_community_guide_environmental_health_2012.pdf
      '_app/text/docs/sanitation/hesperian_community_guide_environmental_health_2012.pdf.c*.html'
      docs/comms/arrl_ares_manual_2015.pdf
      docs/comms/itu_international_morse_code_m1677.pdf
      docs/emergency_mgmt/ucanr_home_survival_wildfire_prone_areas_8939.pdf
      docs/emergency_mgmt/firesafemarin_wildfire_retrofitting_guide.pdf
      # R6 additions 09-19: Interweave Press (c) — free PDF but not open license
      docs/textiles/interweave_spinning_beginners.pdf
      '_app/text/docs/textiles/interweave_spinning_beginners.pdf.c*.html'
    )
    : > STRIPPED.txt
    for pat in "${STRIP[@]}"; do
     for p in $pat; do   # glob-expand (quoted entries); no spaces in these paths
      if [ -e "$p" ]; then
        find "$p" -type f 2>/dev/null >> STRIPPED.txt || echo "$p" >> STRIPPED.txt
        rm -rf "$p"
        echo "stripped $p"
      else
        echo "already absent: $p"
      fi
     done
    done
    echo "$(wc -l < STRIPPED.txt) files stripped -> STRIPPED.txt"
    echo "NOW rerun build_frontend.sh + manifest pass B against this tree"
    echo "REMINDER: WHO/MSF + Kolibri NC content not covered — see LICENSES.md"
    ;;
  *)
    echo "unknown mode: $MODE (gifted|sold)"; exit 1;;
esac
