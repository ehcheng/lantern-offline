#!/bin/bash
# R3: MCP layer acceptance checks for the C4 nspawn simulator.
# Called from c4_test_image.sh OR standalone:
#   bash c4_mcp_checks.sh <container-ip> <data-dir>
# where <container-ip> is the veth address assigned to the container (10.99.0.2)
# and <data-dir> is the host path bound to /data in the container.
#
# Checks:
#  1. lantern-mcp.service active inside container
#  2. POST /mcp initialize via nginx :80 proxy → serverInfo.name == lantern-library
#  3. tools/call search_library returns hits from the fixture library
#  4. kiwix-merged result present (only if kiwix has a ZIM and is up)
#  5. dose NEG probe: "ibuprofen dose" → dose_guard + notice, no snippets
#  6. historical_warning present for a survivor_library hit
#  7. GET /.well-known/mcp.json → 200
#  8. GET /llms.txt → 200
set -uo pipefail

IP=${1:?usage: c4_mcp_checks.sh <container-ip> <data-dir>}
DATA=${2:?usage: c4_mcp_checks.sh <container-ip> <data-dir>}
M=${3:-lantern-c4}   # nspawn machine name (optional, for machinectl exec checks)

PASS=0; FAIL=0; SKIP=0

check() { # name, cmd, [retries]
  for i in $(seq 1 ${3:-20}); do
    if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; PASS=$((PASS+1)); return; fi
    sleep 3
  done
  echo "FAIL $1"; FAIL=$((FAIL+1))
}

check_skip() { echo "SKIP $1 — $2"; SKIP=$((SKIP+1)); }

# ── helper: MCP POST via nginx proxy (:80 /mcp) ──────────────────────────────
mcp_post() {  # json-body → response body (stdout); returns curl exit code
  curl -sm10 -X POST \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' -H 'Host: library.lan' \
    "http://$IP/mcp" -d "$1"
}

# ── 1. lantern-mcp.service active ────────────────────────────────────────────
check "mcp.service active" \
  "systemd-run -M '$M' --wait --pipe /bin/sh -c 'systemctl is-active lantern-mcp'" \
  25

# ── 2. POST /mcp initialize → serverInfo.name == lantern-library ─────────────
INIT_BODY='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"r3sim","version":"1"}}}'
check "mcp initialize serverInfo" \
  "mcp_post '$INIT_BODY' | grep -q 'lantern-library'" \
  20

# ── 3. tools/call search_library → hits ──────────────────────────────────────
# "water purification" hits every fixture library (medical, water shelf content)
SEARCH_BODY='{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_library","arguments":{"query":"water purification","limit":5}}}'
check "search_library hits" \
  "mcp_post '$SEARCH_BODY' | grep -qi 'hits'" \
  15

# Also verify the hits array is non-empty (at least one result item)
check "search_library non-empty hits" \
  "mcp_post '$SEARCH_BODY' | python3 -c \"import sys,json; d=json.load(sys.stdin); r=d.get('result',{}); c=r.get('content',[{}])[0].get('text','{}'); hits=json.loads(c).get('hits',[]); sys.exit(0 if hits else 1)\"" \
  10

# ── 4. kiwix-merged search hit ───────────────────────────────────────────────
# Only meaningful if kiwix-serve came up with the test ZIM.
# Soft check: SKIP if kiwix catalog returns no entries.
# Uses a broad single-word query to maximise kiwix hit chance; kiwix-serve
# may be slow to warm up its FTS index on first search (>2 s timeout means
# silent degrade → 0 zim hits). Retry up to 20 times (60 s).
KIWIX_UP=$(curl -sm5 "http://$IP:8080/catalog/v2/entries" 2>/dev/null | grep -ci entry || true)
# Use limit=20 so library FTS hits don't crowd out the kiwix result.
# library FTS for "water" returns ~5 docs; kiwix appends after, so limit
# must be > library_hit_count to include the zim entry.
KIWIX_SEARCH_BODY='{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"search_library","arguments":{"query":"water","limit":20}}}'
if [ "$KIWIX_UP" -gt 0 ] 2>/dev/null; then
  check "search_library kiwix-merged hit" \
    "mcp_post '$KIWIX_SEARCH_BODY' | python3 -c \"import sys,json; d=json.load(sys.stdin); r=d.get('result',{}); c=r.get('content',[{}])[0].get('text','{}'); hits=json.loads(c).get('hits',[]); sys.exit(0 if any('zim' in h.get('path','') for h in hits) else 1)\"" \
    20
else
  check_skip "search_library kiwix-merged hit" "kiwix catalog empty (ZIM not indexed yet)"
fi

# ── 5. dose NEG probe: "ibuprofen dose" → dose_guard + notice, no snippets ───
DOSE_BODY='{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_library","arguments":{"query":"ibuprofen dose","limit":5}}}'

check "dose_guard flag present" \
  "mcp_post '$DOSE_BODY' | python3 -c \"import sys,json; d=json.load(sys.stdin); r=d.get('result',{}); c=r.get('content',[{}])[0].get('text','{}'); obj=json.loads(c); sys.exit(0 if obj.get('dose_guard') else 1)\"" \
  10

check "dose notice present" \
  "mcp_post '$DOSE_BODY' | python3 -c \"import sys,json; d=json.load(sys.stdin); r=d.get('result',{}); c=r.get('content',[{}])[0].get('text','{}'); obj=json.loads(c); sys.exit(0 if obj.get('notice') else 1)\"" \
  10

# Snippets must be absent in guarded hits (dose guard suppresses them)
check "dose no snippets in hits" \
  "mcp_post '$DOSE_BODY' | python3 -c \"
import sys,json
d=json.load(sys.stdin)
r=d.get('result',{})
c=r.get('content',[{}])[0].get('text','{}')
hits=json.loads(c).get('hits',[])
bad=[h for h in hits if h.get('snippet')]
sys.exit(0 if not bad else 1)
\"" \
  10

# ── 6. historical_warning for survivor_library hit ───────────────────────────
# A query only the historical shelf answers ("beekeeping" stopped returning one in the top 10 once readers sink below
# modern-shelf rows, K348 r39)
HIST_BODY='{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"search_library","arguments":{"query":"dynamo electric machinery 1895","limit":10}}}'
check "historical_warning in response" \
  "mcp_post '$HIST_BODY' | python3 -c \"import sys,json; d=json.load(sys.stdin); r=d.get('result',{}); c=r.get('content',[{}])[0].get('text','{}'); obj=json.loads(c); sys.exit(0 if obj.get('historical_warning') else 1)\"" \
  10

# ── 7. GET /.well-known/mcp.json → 200 ───────────────────────────────────────
check "well-known mcp.json 200" \
  "curl -sm5 -o /dev/null -w '%{http_code}' -H 'Host: library.lan' http://$IP/.well-known/mcp.json | grep -q 200" \
  10

# ── 8. GET /llms.txt → 200 ───────────────────────────────────────────────────
check "llms.txt 200" \
  "curl -sm5 -o /dev/null -w '%{http_code}' -H 'Host: library.lan' http://$IP/llms.txt | grep -q 200" \
  10

# ── summary ──────────────────────────────────────────────────────────────────
echo ""
echo "C4-MCP RESULT: $PASS pass, $FAIL fail, $SKIP skip"
[ "$FAIL" = 0 ]
