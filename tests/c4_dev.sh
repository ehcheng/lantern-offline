#!/bin/bash
# C4 dev-side tiers against the fresh seal: T0 dev, T1 (resumable, -P 16), T3, T4 (dev :8765 + :8090), T8 (5 checks).
# screen -dmS c4dev bash tests/c4_dev.sh   (no sandbox: kiwix :8080, llamafile, Chrome)
set -uo pipefail
cd "$(dirname "$0")/.."
EX=tests; L=$EX/logs; T=$(date +%Y%m%d)
step() { echo "== $1 $(date +%T)"; }
step t0_dev;  bash $EX/t0_integrity.sh . $EX/results/t0_dev.csv 8 > $L/t0_dev_$T.log 2>&1; echo "t0_dev rc=$?"
step t1;      bash $EX/t1_format.sh 16 > $L/t1_$T.log 2>&1; echo "t1 rc=$?"
step t3;      python3 $EX/t3_reach.py > $L/t3_$T.log 2>&1; echo "t3 rc=$?"
step t4;      python3 $EX/t4_coverage.py > $L/t4_$T.log 2>&1; echo "t4 rc=$?"
for c in static links coverage parity; do step t8_$c; python3 $EX/t8_plain.py $c > $L/t8_${c}_$T.log 2>&1; echo "t8_$c rc=$?"; done
step t9_catalog; python3 $EX/t9_catalog.py > $L/t9_catalog_$T.log 2>&1; echo "t9_catalog rc=$?"
step t8_browser; python3 $EX/t8_plain.py browser > $L/t8_browser_$T.log 2>&1; echo "t8_browser rc=$?"
python3 $EX/report.py > $L/report_$T.log 2>&1
echo "C4_DEV DONE $(date +%T)"; grep -A30 "^| tier" $EX/REPORT.md | head -40
