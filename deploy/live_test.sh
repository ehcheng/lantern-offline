#!/bin/bash
# Live test battery against the REAL Lantern box (E3 harness, repeatable).
# Run from a machine on the LIBRARY wifi (or any host that can reach the Pi):
#   bash deploy/live_test.sh            # default host 10.10.10.10
#   bash deploy/live_test.sh <box address>
# Needs curl, python3, ssh. ssh checks use .keys/lantern_ed25519 if
# present, else are SKIPped. Log: logs/live_test_<timestamp>.log
# Exit 0 only if every check passes.
set -u   # no pipefail: grep -q closing a pipe would fail curl with SIGPIPE
IP=${1:-${LANTERN_IP:-10.10.10.10}}
cd "$(dirname "$0")/.."
KEY=${LANTERN_KEY:-.keys/lantern_ed25519}
LOG=logs/live_test_$(date +%Y%m%d_%H%M%S).log
EXPECT_ZIMS=38            # bump when ZIMs are added (count in library/zim)
H='Host: library.lan'
PASS=0; FAIL=0; SKIP=0
ok()   { echo "PASS $1" | tee -a "$LOG"; PASS=$((PASS+1)); }
bad()  { echo "FAIL $1${2:+ — $2}" | tee -a "$LOG"; FAIL=$((FAIL+1)); }
skip() { echo "SKIP $1 — $2" | tee -a "$LOG"; SKIP=$((SKIP+1)); }
check() { # name, command (eval'd, quiet)
  if eval "$2" >/dev/null 2>>"$LOG"; then ok "$1"; else bad "$1"; fi
}
code() { curl -sm10 -o /dev/null -w '%{http_code}' "$@" 2>/dev/null; }
mcp()  { curl -sm20 -X POST -H 'Content-Type: application/json' \
           -H 'Accept: application/json, text/event-stream' -H "$H" \
           "http://$IP/mcp" -d "$1" 2>/dev/null; }
hits() { python3 -c "import sys,json; d=json.load(sys.stdin); c=json.loads(d['result']['content'][0]['text']); $1"; }

echo "=== live_test $(date) host=$IP" | tee "$LOG"

# ── 1. reachability + nginx ─────────────────────────────────────────────
check "ping"                    "ping -c1 -W2 $IP"
check "landing by IP 200"       "[ \$(code http://$IP/) = 200 ]"
check "router DNS library.lan -> Pi" "[ \"\$(dig +short +time=3 @${IP%.*}.1 library.lan | tail -1)\" = $IP ]"
check "pdf.mjs served as javascript" "curl -sIm10 -H '$H' http://$IP/_app/vendor/pdfjs/pdf.mjs | grep -qi 'content-type: \(text\|application\)/javascript'"
check "landing library.lan 200" "[ \$(code -H '$H' http://$IP/) = 200 ]"
check "landing library.local 200 (mDNS)" "[ \$(code http://library.local/) = 200 ]"
check "search.html 200"         "[ \$(code -H '$H' http://$IP/search.html) = 200 ]"
check "plants.html 200"         "[ \$(code -H '$H' http://$IP/plants.html) = 200 ]"
check "map.html 200"            "[ \$(code -H '$H' http://$IP/map.html) = 200 ]"
check "well-known mcp.json 200" "[ \$(code -H '$H' http://$IP/.well-known/mcp.json) = 200 ]"
check "llms.txt 200"            "[ \$(code -H '$H' http://$IP/llms.txt) = 200 ]"
check "VERSION.json 200"        "[ \$(code -H '$H' http://$IP/VERSION.json) = 200 ]"
check "image-release.txt IMAGE=" "curl -sm10 -H '$H' http://$IP/image-release.txt | grep -q '^IMAGE='"
check "plain version (index_v1/triage_v1) links all 200" "python3 tests/plain_test.py http://$IP/ >/dev/null"
check "image LIBRARY_MIN <= library" "python3 -c \"import json,urllib.request as u;h={'Host':'library.lan'};r=dict(l.split('=',1) for l in u.urlopen(u.Request('http://$IP/image-release.txt',headers=h)).read().decode().split());v=json.load(u.urlopen(u.Request('http://$IP/VERSION.json',headers=h)))['library'];print(r['IMAGE'],v);assert v>=r['LIBRARY_MIN']\""
check "unknown host -> 302"     "[ \$(code -H 'Host: example.com' http://$IP/) = 302 ]"

# ── 2. captive-portal probes (must be 302, never 204/200 bodies) ────────
check "probe gstatic generate_204 -> 302" "[ \$(code -H 'Host: connectivitycheck.gstatic.com' http://$IP/generate_204) = 302 ]"
check "probe apple hotspot-detect -> 302" "[ \$(code -H 'Host: captive.apple.com' http://$IP/hotspot-detect.html) = 302 ]"
check "probe msft connecttest -> 302"     "[ \$(code -H 'Host: msftconnecttest.com' http://$IP/connecttest.txt) = 302 ]"

# ── 3. kiwix ────────────────────────────────────────────────────────────
CAT=$(curl -sm15 "http://$IP:8080/catalog/v2/entries?count=-1" 2>/dev/null)
N=$(printf '%s' "$CAT" | grep -c '<entry>')
[ "$N" = "$EXPECT_ZIMS" ] && ok "kiwix catalog $N ZIMs" || bad "kiwix catalog" "$N entries, expected $EXPECT_ZIMS"
WP=$(printf '%s' "$CAT" | grep -o 'href="/content/wikipedia_en_all[^"]*' | head -1 | sed 's|href="/content/||')
if [ -n "$WP" ]; then
  check "wikipedia article 200 w/ title" "curl -sLm30 http://$IP:8080/content/$WP/A/Water_purification | grep -q '<title>Water purification'"
  check "kiwix search 200"              "[ \$(code \"http://$IP:8080/search?books.name=$WP&pattern=water\") = 200 ]"
else bad "wikipedia book present in catalog"; fi

# ── 4. MCP ──────────────────────────────────────────────────────────────
check "mcp initialize serverInfo" "mcp '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-03-26\",\"capabilities\":{},\"clientInfo\":{\"name\":\"live\",\"version\":\"1\"}}}' | grep -q lantern-library"
S='{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_library","arguments":{"query":"water purification","limit":10}}}'
check "search_library non-empty"  "mcp '$S' | hits 'sys.exit(0 if c[\"hits\"] else 1)'"
check "search_library has zim hit" "mcp '$S' | hits 'sys.exit(0 if any(\"zim\" in h.get(\"path\",\"\") for h in c[\"hits\"]) else 1)'"
D='{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_library","arguments":{"query":"ibuprofen dose","limit":5}}}'
check "dose guard flag + no snippets" "mcp '$D' | hits 'sys.exit(0 if c.get(\"dose_guard\") and not any(h.get(\"snippet\") for h in c[\"hits\"]) else 1)'"
check "historical_warning present"   "mcp '$S' | grep -q historical_warning"

# ── 4b. every MCP tool ──────────────────────────────────────────────────
check "tools/list has 6 tools" "mcp '{\"jsonrpc\":\"2.0\",\"id\":9,\"method\":\"tools/list\"}' | python3 -c 'import sys,json; t=[x[\"name\"] for x in json.load(sys.stdin)[\"result\"][\"tools\"]]; sys.exit(0 if set(t)>={\"search_library\",\"read_document\",\"list_shelves\",\"sun_times\",\"climate_normals\",\"callsign_lookup\"} else 1)'"
DOCP=$(mcp "$S" | hits 'print(next((h["path"] for h in c["hits"] if h.get("path","").startswith("docs/")),""))' 2>/dev/null)
if [ -n "$DOCP" ]; then
  check "read_document returns text" "mcp '{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"read_document\",\"arguments\":{\"path\":\"$DOCP\",\"page\":1,\"pages\":1}}}' | hits 'sys.exit(0 if len(json.dumps(c))>200 and \"error\" not in c else 1)'"
else bad "read_document" "no docs/ hit to read"; fi
check "list_shelves non-empty"  "mcp '{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"params\":{\"name\":\"list_shelves\",\"arguments\":{}}}' | hits 'sys.exit(0 if len(json.dumps(c))>100 else 1)'"
check "sun_times home region"    "mcp '{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"tools/call\",\"params\":{\"name\":\"sun_times\",\"arguments\":{\"lat\":37.485,\"lon\":-122.236}}}' | grep -i sunrise"
check "climate_normals July"     "mcp '{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"tools/call\",\"params\":{\"name\":\"climate_normals\",\"arguments\":{\"lat\":37.485,\"lon\":-122.236,\"month\":7}}}' | hits 'sys.exit(0 if \"error\" not in c and len(json.dumps(c))>60 else 1)'"
check "callsign_lookup W1AW"     "mcp '{\"jsonrpc\":\"2.0\",\"id\":8,\"method\":\"tools/call\",\"params\":{\"name\":\"callsign_lookup\",\"arguments\":{\"callsign\":\"W1AW\"}}}' | hits 'sys.exit(0 if \"error\" not in c and len(json.dumps(c))>40 else 1)'"

# ── 4c. content surfaces: every ZIM, both pagefind indexes, shelves, media ─
BAD=0; for bk in $(printf '%s' "$CAT" | grep -o 'href="/content/[^"]*' | sed 's|href="/content/||'); do
  [ "$(curl -sLm20 -o /dev/null -w '%{http_code}' "http://$IP:8080/content/$bk")" = 200 ] || { BAD=$((BAD+1)); echo "  zim main page fail: $bk" >>"$LOG"; }
done; [ $BAD = 0 ] && ok "all $N ZIM main pages 200" || bad "ZIM main pages" "$BAD failed (see log)"
check "pagefind entry json"      "curl -sm10 -H '$H' http://$IP/_app/pagefind/pagefind-entry.json | grep -q '\"version\"'"
check "pagefind_hist entry json" "curl -sm10 -H '$H' http://$IP/_app/pagefind_hist/pagefind-entry.json | grep -q '\"version\"'"
BAD=0; for sh in $(curl -sm10 -H "$H" http://$IP/ | grep -o '_app/shelf/[^"]*\.html' | sort -u); do
  [ "$(code -H "$H" "http://$IP/$sh")" = 200 ] || { BAD=$((BAD+1)); echo "  shelf fail: $sh" >>"$LOG"; }
done; [ $BAD = 0 ] && ok "all landing shelf pages 200" || bad "shelf pages" "$BAD failed"
check "cover image 200"          "[ \$(code -H '$H' http://$IP/_app/covers/0002c574.jpg) = 200 ]"
check "audio mp3 range 206"      "[ \$(code -H '$H' -r 0-1023 http://$IP/audio/librivox/01_young_child/aesop_fables/fablesofaesop_001_aesop_64kb.mp3) = 206 ]"
check "video mp4 range 206"      "[ \$(code -H '$H' -r 0-1023 http://$IP/video/prelinger/0169_Woodworker_The_E01724_10_24_17_24.mp4) = 206 ]"
check "map pmtiles range 206"    "[ \$(code -H '$H' -r 0-127 http://$IP/maps/pmtiles/planet.pmtiles) = 206 ]"
check "chat.html + config.json"  "[ \$(code -H '$H' http://$IP/chat.html) = 200 ] && curl -sm10 -H '$H' http://$IP/_app/config.json | grep -q llmEndpoints"

# ── 5. semantic, embed, voice, kolibri, LLM ─────────────────────────────
check "semantic 200 with results" "curl -sm60 -H '$H' 'http://$IP/semantic?q=how%20to%20purify%20water' | python3 -c 'import sys,json; d=json.load(sys.stdin); sys.exit(0 if d else 1)'"
WAV=$(mktemp -t lt).wav; python3 - "$WAV" <<'PY'
import sys,wave,struct,math
w=wave.open(sys.argv[1],'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
w.writeframes(b''.join(struct.pack('<h',int(3000*math.sin(2*math.pi*440*i/16000))) for i in range(16000))); w.close()
PY
check "voice /stt answers json"  "curl -sm90 -H '$H' -F file=@$WAV http://$IP/stt | grep -q '\"text\"'"
rm -f "$WAV"
check "kolibri channels api"     "curl -sm20 http://$IP:8081/api/public/v1/channels | python3 -c 'import sys,json; sys.exit(0 if json.load(sys.stdin) else 1)'"
for ep in $(curl -sm10 -H "$H" http://$IP/_app/config.json | python3 -c 'import sys,json; print(" ".join(json.load(sys.stdin).get("llmEndpoints",[])))'); do
  c=$(code "$ep/v1/models"); [ "$c" = 000 ] && c=$(code "$ep/api/tags")
  [ "$c" = 200 ] && echo "INFO llm endpoint $ep reachable" | tee -a "$LOG" || echo "INFO llm endpoint $ep unreachable (external box, chat.html degrades)" | tee -a "$LOG"
done

# ── 6. on-box checks over ssh (optional) ─────────────────────────────────
if [ -f "$KEY" ]; then
  SSH="ssh -i $KEY -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR lantern@$IP"
  if $SSH true 2>/dev/null; then
    check "root on nvme"        "$SSH findmnt -no SOURCE / | grep -q nvme"
    check "/data mounted"       "$SSH findmnt -no SOURCE /data | grep -q nvme"
    check "services active"     "$SSH systemctl is-active nginx kiwix kolibri lantern-mcp lantern-embed lantern-voice ssh chrony avahi-daemon"
    check "no failed units"     "[ -z \"\$($SSH systemctl --failed --no-legend)\" ]"
    check "not throttled/undervolt" "[ \"\$($SSH vcgencmd get_throttled | cut -d= -f2)\" = 0x0 ]"
    check "boot order 0xf416"   "$SSH vcgencmd bootloader_config | grep -q BOOT_ORDER=0xf416"
    check "hostname library"    "[ \"\$($SSH hostname)\" = library ]"
    check "eth0 has 10.10.10.10" "$SSH ip -4 -br addr show eth0 | grep -q 10.10.10.10/24"
    check "manifest count"      "$SSH 'cd /data/library && [ \$(find . -type f ! -name MANIFEST.sha256 ! -name .DS_Store | wc -l) -ge \$(wc -l < MANIFEST.sha256) ]'"
    check "20 spot hashes"      "$SSH 'cd /data/library && shuf -n 20 MANIFEST.sha256 | sed \"s|  library/|  |\" | sha256sum -c --quiet'"
    EMB=$($SSH "curl -sm30 -X POST http://127.0.0.1:8091/embedding -H 'Content-Type: application/json' -d '{\"content\":\"water\"}'" 2>/dev/null)
    check "embed /embedding >=512 dims" "printf '%s' '$EMB' | python3 -c 'import sys,json; d=json.load(sys.stdin); e=(d[0] if isinstance(d,list) else d)[\"embedding\"]; e=e[0] if e and isinstance(e[0],list) else e; sys.exit(0 if len(e)>=512 else 1)'"
    NB=$($SSH grep -c "'<book '" /data/library.xml 2>/dev/null)
    [ "$NB" = "$EXPECT_ZIMS" ] && ok "kiwix library.xml lists $NB books" || bad "kiwix library.xml" "$NB books, expected $EXPECT_ZIMS"
    E=$($SSH "journalctl -b -p err --no-pager -q | grep -c lantern" 2>/dev/null); echo "INFO lantern-* error-level journal lines this boot: ${E:-?}" | tee -a "$LOG"
    T=$($SSH vcgencmd measure_temp 2>/dev/null | tr -dc '0-9.'); U=$($SSH df -h /data 2>/dev/null | awk 'END{print $5" used, "$4" free"}')
    echo "INFO temp=${T}C  /data ${U}" | tee -a "$LOG"
  else skip "ssh checks" "cannot ssh to lantern@$IP"; fi
else skip "ssh checks" "no $KEY"; fi

echo "=== RESULT: $PASS pass, $FAIL fail, $SKIP skip ($LOG)" | tee -a "$LOG"
[ "$FAIL" = 0 ]
