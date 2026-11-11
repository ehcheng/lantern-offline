#!/bin/bash
# E6: save the kiwix-serve OPDS catalog (titles, summaries, languages, sizes, dates) for gen_index/gen_shelves.
# Run while kiwix-serve is up (server/serve_kiwix_dev.sh, :8080; KIWIX=http://host:port for another): bash build/fetch_kiwix_catalog.sh
cd "$(dirname "$0")/.." || exit 1
OUT=data/kiwix_catalog.xml
curl -sf --max-time 60 "${KIWIX:-http://127.0.0.1:8080}/catalog/v2/entries?count=-1" > "$OUT.tmp" || { echo "kiwix catalog fetch failed (is kiwixdev up?)"; exit 1; }
grep -q '<entry>' "$OUT.tmp" && mv "$OUT.tmp" "$OUT" && echo "$(grep -c '<entry>' "$OUT") books -> $OUT"
