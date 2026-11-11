#!/bin/bash
# r19: the fix-all pass (FIXES #72-#115). Order (memory regen-verify-order): regen, verify, regen the dropped, empty gate,
# then every derived layer from scratch, then seal. EMPTY_MAX = the empty-summary floor reported by the content owner.
#   normally via build/reseal_dev.sh with FULL=1   (sandbox off)
set -uo pipefail
cd "$(dirname "$0")/.."
# extended regex for -regex: BSD find takes -E before the path, GNU find -regextype after it
findx() { if [ "$(uname)" = Darwin ]; then find -E -L "$@"; else local p=$1; shift; find -L "$p" -regextype posix-extended "$@"; fi; }
L=logs; T=${T:-r19}; EMPTY_MAX=${EMPTY_MAX:-0}
if [ "${START:-}" != frontend ]; then   # START=frontend resumes after a failure past the summary steps
echo "== orphan wrappers $(date)"; python3 build/prune_orphan_wrappers.py
echo "== regen 1 $(date)"; python3 build/gen_doc_answers.py --threads 4 > $L/regen1_$T.log 2>&1; tail -1 $L/regen1_$T.log
echo "== kiwix catalog $(date)"; bash build/fetch_kiwix_catalog.sh || { echo "R19 FAIL kiwix catalog"; exit 1; }
echo "== verify $(date)"; python3 build/gen_doc_answers.py --verify >> $L/verify_$T.log 2>&1 || { echo "R19 FAIL verify"; exit 1; }; tail -1 $L/verify_$T.log
echo "== regen 2 (what verify dropped) $(date)"; python3 build/gen_doc_answers.py --threads 4 > $L/regen2_$T.log 2>&1; tail -1 $L/regen2_$T.log
E=$(python3 -c "import json;d=json.load(open('data/docs.curated.json'));print(sum(1 for v in d.values() if not v.get('a') and 'a' not in v.get('c1', '')))"); echo "empty summaries: $E (max $EMPTY_MAX)"
[ "$E" -le "$EMPTY_MAX" ] || { echo "R19 FAIL: $E empty summaries"; exit 1; }
echo "== gen_text --force $(date)"; python3 build/gen_text.py --force > $L/gen_text_$T.log 2>&1; tail -1 $L/gen_text_$T.log
fi
# r26: content changed on disk since the last seal (deleted mirror stubs/PDFs, new mp3s, places.js): gen_index reads the
# sealed MANIFEST, so refresh its content half first (same find as b5_reseal pass A; b5 redoes it at seal time).
echo "== interim manifest (content pass) $(date)"
findx library -type f ! -name 'MANIFEST.sha256*' ! -name VERSION.json ! -name '.DS_Store' \
    ! -path 'library/_app/*' ! -regex 'library/[^/]*\.html' \
    ! -path 'library/kolibri_data/logs/*' ! -name server.pid ! -path 'library/kolibri_data/process_cache/*' \
    ! -regex 'library/kolibri_data/[^/]*\.sqlite3.*' -print0 | sort -z | xargs -0 -n8 -P6 shasum -a 256 > $L/manifest.interim_$T
grep -E '^[0-9a-f]{64}  library/_app/|^[0-9a-f]{64}  library/[^/]*\.html$' library/MANIFEST.sha256 >> $L/manifest.interim_$T
sort -k2 $L/manifest.interim_$T > library/MANIFEST.sha256; echo "interim manifest: $(wc -l < library/MANIFEST.sha256) lines"
echo "== build_frontend (gen_index, covers, pagefind, shelves, triage, verify, hash) $(date)"
bash build/build_frontend.sh > $L/build_frontend_$T.log 2>&1 || { echo "R19 FAIL build_frontend"; tail -5 $L/build_frontend_$T.log; exit 1; }
grep -E "titles=|Indexed .* page|OK|FAIL" $L/build_frontend_$T.log | tail -8
python3 build/check_titles.py || { echo "R19 FAIL check_titles"; exit 1; }
echo "== mcp index $(date)"; python3 server/build_mcp_index.py > $L/mcp_index_$T.log 2>&1 || { echo "R19 FAIL mcp_index"; exit 1; }; tail -1 $L/mcp_index_$T.log
echo "== embeddings $(date)"; python3 server/build_embeddings.py > $L/embeddings_$T.log 2>&1 || { echo "R19 FAIL embeddings"; exit 1; }; grep "pruned\|done" $L/embeddings_$T.log | tail -2
echo "== restart h37mcp $(date)"; screen -S h37mcp -X quit 2>/dev/null; pkill -f mcp_server.py; sleep 2
screen -dmS h37mcp bash -c "python3 server/mcp_server.py --library library --port 8090 --kiwix http://127.0.0.1:8080 > $L/h37c_mcp.log 2>&1"; sleep 3
echo "== t3 $(date)"; python3 tests/t3_reach.py > $L/t3_$T.log 2>&1; echo "t3 rc=$?"
echo "== t4 dev $(date)"; python3 tests/t4_coverage.py > $L/t4_dev_$T.log 2>&1; echo "t4 rc=$?"
echo "== t8_mirror_entry $(date)"; python3 tests/t8_mirror_entry.py > $L/t8_mirror_entry_$T.log 2>&1; echo "t8_mirror_entry rc=$?"
python3 tests/report.py >/dev/null; grep -E '^\| t(3|4|8_mirror)' tests/REPORT.md
# Red-team seed guard (10-09, keep): planted defects carry RTSEED<date>; any hit in the library stops the seal.
# Bare RTSEED would false-match an OCR'd Webster's dictionary page, so the date digit is required.
hits=$(grep -rlI 'RTSEED[0-9]' library/ data/ | head -5); [ -z "$hits" ] || { echo "R19 FAIL rtseed leak: $hits"; exit 1; }
echo "== seal_chain $T $(date)"; bash build/seal_chain.sh $T; rc=$?
echo "R19 DONE rc=$rc $(date)"
