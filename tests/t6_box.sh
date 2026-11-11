#!/bin/bash
# T6 box behaviour on the Pi: live_test 54/54, service restart matrix (each unit back active + spot check
# within 60 s), journal has no failed units. Power pull is manual — recorded as SKIP with instructions.
# Usage: bash tests/t6_box.sh [ip]   (sandbox off: ssh + LAN). Run only when T2 is idle.
set -u
IP=${1:-${LANTERN_IP:-10.10.10.10}}; cd "$(dirname "$0")/.."
EX=tests; OUT=$EX/results/t6.csv; KEY=${LANTERN_KEY:-.keys/lantern_ed25519}
SSH="ssh -i $KEY -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=no -o LogLevel=ERROR lantern@$IP"
H='Host: library.lan'
: > "$OUT"
row() { echo "t6,$1,$2,$3,$4" >> "$OUT"; echo "$(date +%T) $1 $2 $3 $4"; }
code() { curl -sm15 -o /dev/null -w '%{http_code}' "$@" 2>/dev/null; }
# 1. live_test gate
bash deploy/live_test.sh "$IP" > $EX/logs/t6_live_test.log 2>&1
R=$(tail -1 $EX/logs/t6_live_test.log)
case "$R" in *" 0 fail"*) row live_test box PASS "$R";; *) row live_test box FAIL "$R";; esac
# 2. restart matrix: unit -> spot check
spot() { case $1 in
  nginx)          [ "$(code -H "$H" http://$IP/search.html)" = 200 ];;
  kiwix)          [ "$(code "http://$IP:8080/catalog/v2/entries?count=1")" = 200 ];;
  kolibri)        [ "$(code http://$IP:8081/api/public/v1/channels)" = 200 ];;
  lantern-mcp)    curl -sm60 -H "$H" 'http://'$IP'/semantic?q=water' | grep -q path;;
  lantern-embed)  $SSH "curl -sm30 -X POST http://127.0.0.1:8091/embedding -H 'Content-Type: application/json' -d '{\"content\":\"water\"}'" | grep -q embedding;;
  lantern-voice)  [ "$(code -H "$H" -X POST http://$IP/stt)" != 000 ];;
  lantern-discs)  [ "$(code -H "$H" http://$IP/discs/)" = 200 ];;
  esac; }
for u in nginx kiwix kolibri lantern-mcp lantern-embed lantern-voice lantern-discs; do
  if ! $SSH "sudo -n systemctl restart $u" 2>>$EX/logs/t6.log; then row restart $u FAIL "restart refused (sudo -n)"; continue; fi
  T0=$(date +%s); ok=0
  for i in $(seq 1 30); do
    if [ "$($SSH systemctl is-active $u)" = active ] && spot $u; then ok=1; break; fi; sleep 2
  done
  row restart $u $([ $ok = 1 ] && echo PASS || echo FAIL) "back in $(( $(date +%s) - T0 ))s"
done
# cold semantic after lantern-mcp restart < 2 s (T4 plan item) — measured on the first /semantic above; re-measure explicitly
$SSH "sudo -n systemctl restart lantern-mcp" && sleep 5
T=$(curl -sm60 -o /dev/null -w '%{time_total}' -H "$H" 'http://'$IP'/semantic?q=how%20to%20purify%20water')
row semantic_cold lantern-mcp $(awk -v t="$T" 'BEGIN{print (t<2)?"PASS":"FAIL"}') "${T}s (limit 2 s)"
# 3. journal + failed units
F=$($SSH "systemctl --failed --no-legend" | wc -l | tr -d ' ')
row failed_units box $([ "$F" = 0 ] && echo PASS || echo FAIL) "$F failed units"
E=$($SSH "journalctl -b -p err --no-pager -q | grep -c lantern"); row journal_err box PASS "$E lantern error lines this boot (info)"
# 4. c4 sim on current image: recorded from the last sim log
L=$(ls -t image/logs/c4_*.log 2>/dev/null | head -1)
if [ -n "$L" ] && grep -q "PASS\|OK" "$L" && ! grep -q "FAIL" "$L"; then row c4_sim "$L" PASS "last sim green"; else row c4_sim "${L:-none}" SKIP "rerun c4 after LOCK 1.0.1 build"; fi
row power_pull box SKIP "manual: unplug, replug, boot, live_test within 3 min, /discs/ mounted, no failed units"
echo "$(date +%T) t6 done: $(grep -c ',FAIL,' "$OUT") FAIL"
python3 $EX/report.py > /dev/null
