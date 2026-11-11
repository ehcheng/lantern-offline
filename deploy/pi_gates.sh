#!/bin/bash
# The three gates a Pi must pass after a push: live_test, T5 render, T4 coverage (red team 2026-10-03 A5).
# push_seal.sh ends with it; run it alone after a fix that needs no re-push (nginx conf, DNS).   bash deploy/pi_gates.sh [pi_ip]
set -uo pipefail
cd "$(dirname "$0")/.."
IP=${1:-${LANTERN_IP:-10.10.10.10}}; L=logs; TAG=$(printf '%s' "$IP" | tr -c 'A-Za-z0-9' '_')
bash deploy/live_test.sh "$IP" > "$L/live_test_$(date +%Y%m%d_%H%M).log" 2>&1 || { echo "CHAIN_FAIL_LIVE_TEST see $L/live_test_*.log"; exit 1; }
# T5 needs a browser; macOS Local Network privacy blocks Playwright's Chrome from the LAN (python is allowed), so Chrome
# goes through the stdlib forwarding proxy (every host:port the pages touch: :80, :8080 kiwix, :8090)
pkill -f lan_proxy.py 2>/dev/null; screen -dmS lanproxy bash -c "python3 tests/lan_proxy.py 8766 2> $L/lan_proxy.log"; sleep 2
T5_PROXY=127.0.0.1:8766 python3 tests/t5_render.py 8 "http://$IP/" > "$L/t5_pi_$(date +%Y%m%d_%H%M).log" 2>&1
T5_PROXY=127.0.0.1:8766 python3 tests/t4_coverage.py "http://$IP/" > "$L/t4_pi_$(date +%Y%m%d_%H%M).log" 2>&1
pkill -f lan_proxy.py 2>/dev/null
python3 tests/report.py > /dev/null
for t in "t5_$TAG" "t4_$TAG"; do
  f=$(grep "^| $t |" tests/REPORT.md | awk -F'|' '{print $4}' | tr -d ' ')
  [ "$f" = 0 ] || { echo "CHAIN_FAIL_$t unexplained FAIL=$f (see tests/REPORT.md)"; exit 1; }
done
echo "$(date +%T) PUSH_SEAL_ACCEPTED: live_test, t5 and t4 green against http://$IP/"
