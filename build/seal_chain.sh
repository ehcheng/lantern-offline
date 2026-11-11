#!/bin/bash
# Seal + acceptance as ONE gate (red team 2026-10-03: r11/r12 chains discarded acceptance's exit code, so a FAIL
# still left a versioned seal). Run WITHOUT the sandbox in screen:  screen -dmS seal bash build/seal_chain.sh <tag>
# A failing acceptance moves VERSION.json to logs/VERSION.json.REJECTED_<tag>; push_seal.sh then has nothing to push.
set -u
cd "$(dirname "$0")/.."; T=${1:-$(date +%Y%m%d_%H%M)}; L=logs; mkdir -p $L
bash build/b5_reseal.sh > $L/b5_reseal_$T.log 2>&1
grep -q B5_RESEAL_DONE $L/b5_reseal_$T.log || { echo CHAIN_FAIL_RESEAL; exit 1; }
python3 build/acceptance_run.py > $L/acceptance_$T.log 2>&1; A=$?
echo ACC_EXIT=$A >> $L/acceptance_$T.log
# a rejected stamp goes to the logs, never stays in library/ (r13: VERSION.json.REJECTED got sealed into the next manifest)
if [ "$A" != 0 ]; then mv library/VERSION.json $L/VERSION.json.REJECTED_$T; echo "CHAIN_FAIL_ACCEPTANCE seal rejected, see $L/acceptance_$T.log"; exit 1; fi
echo CHAIN_DONE
