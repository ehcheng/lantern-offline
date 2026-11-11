#!/bin/bash
# C4 Pi-side tiers: T0 on the Pi (sha256 over /data, ~1 h), T2 serving crawl, T6 box behaviour (after T2 is idle).
# T5/T4 against the Pi are run by push_seal.sh. screen -dmS c4pi bash deploy/c4_pi.sh [ip]   (no sandbox)
set -uo pipefail
cd "$(dirname "$0")/.."
IP=${1:-${LANTERN_IP:-10.10.10.10}}; EX=tests; L=$EX/logs; T=$(date +%Y%m%d); KEY=${LANTERN_KEY:-.keys/lantern_ed25519}
SSH="ssh -i $KEY -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
step() { echo "== $1 $(date +%T)"; }
step t0_pi
scp -i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR $EX/t0_integrity.sh lantern@$IP:/tmp/t0_integrity.sh
$SSH lantern@$IP "bash /tmp/t0_integrity.sh /data /tmp/t0_pi.csv 4" > $L/t0_pi_$T.log 2>&1; echo "t0_pi rc=$?"
scp -i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR lantern@$IP:/tmp/t0_pi.csv $EX/results/t0_pi.csv
step t2; python3 $EX/t2_serve.py $IP 16 > $L/t2_$T.log 2>&1; echo "t2 rc=$?"
step t6; bash $EX/t6_box.sh $IP > $L/t6_$T.log 2>&1; echo "t6 rc=$?"
python3 $EX/report.py > /dev/null 2>&1
echo "C4_PI DONE $(date +%T)"
