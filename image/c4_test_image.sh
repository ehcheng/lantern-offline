#!/bin/bash
# BUILD_PLAN C4: image sanity WITHOUT a Pi. QEMU has no Pi 5 machine model —
# so this nspawn-boots the built rootfs and checks:
#  1. services start (nginx, kiwix; kolibri against a COPY of the B4
#     kolibri_data home if provided)
#  2. nginx answers captive probes with correct codes (302, not 204/Success)
#  3. kiwix-serve catalog responds against a sample zim
# The golden image is NEVER written: ro loop mount + nspawn --ephemeral
# (overlay/copy snapshot), /data staged via --bind of a scratch dir.
# Sample zim lives in the repo at image/test_data/ (the bulk zim
# store is a mac-side symlink the VM can't see).
# Runs inside the lima VM: sudo bash c4_test_image.sh <image.img> [kolibri_home_copy]
set -uo pipefail
IMG=${1:?usage: c4_test_image.sh <image.img> [kolibri_home]}
KHOME=${2:-}

MNT=/mnt/lantern-img
M=lantern-c4
DATA=/tmp/c4-data
mkdir -p "$MNT"

cleanup() {
  machinectl poweroff "$M" 2>/dev/null
  sleep 3
  machinectl terminate "$M" 2>/dev/null
  umount -R "$MNT" 2>/dev/null
  [ -n "${LOOP:-}" ] && losetup -d "$LOOP" 2>/dev/null
}
trap cleanup EXIT

# Boot a throwaway COPY of the rootfs on VM disk (--ephemeral snapshots into
# the source fs — the image partition has no headroom). Image stays ro.
COPY=/var/lib/machines/$M
LOOP=$(losetup -rfP --show "$IMG")
mount -o ro "${LOOP}p2" "$MNT"
mount -o ro "${LOOP}p1" "$MNT/boot/firmware"
rm -rf "$COPY"
mkdir -p "$COPY"
cp -a "$MNT/." "$COPY/"

rm -rf "$DATA"
mkdir -p "$DATA/library/zim"
SAMPLE=$(ls /workspace/image/test_data/*.zim 2>/dev/null | head -1 || true)
[ -n "$SAMPLE" ] && cp "$SAMPLE" "$DATA/library/zim/" || echo "WARN: no sample zim staged"
echo '<h1>test library</h1>' > "$DATA/library/index.html"

# ── MCP library subset (R3: sim MCP acceptance) ──────────────────────────────
# Stage the minimum files mcp_server.py needs at startup:
#   _app/mcp/mcp.db       — FTS index (256 MB, symlinked from mac workspace)
#   _app/index/shelves.json + config.json — server State() reads these
#   .well-known/mcp.json + llms.txt       — nginx static, no server needed
#   docs/HISTORICAL/README-WARNING.txt    — historical_warning fallback text
# The full 1TB zim/kolibri/pdf corpus is NOT staged — FTS covers extracted
# text already baked into mcp.db; zim search runs live via kiwix-serve.
WKSPC=/workspace
LIB="$WKSPC/library"
MCP_DB="$LIB/_app/mcp/mcp.db"
if [ -f "$MCP_DB" ]; then
  mkdir -p "$DATA/library/_app/mcp" \
           "$DATA/library/_app/index" \
           "$DATA/library/.well-known" \
           "$DATA/library/docs/HISTORICAL"
  cp "$MCP_DB"                             "$DATA/library/_app/mcp/mcp.db"
  cp "$LIB/_app/index/shelves.json"        "$DATA/library/_app/index/shelves.json"
  cp "$LIB/_app/config.json"               "$DATA/library/_app/config.json"
  cp "$LIB/.well-known/mcp.json"           "$DATA/library/.well-known/mcp.json"
  cp "$LIB/llms.txt"                       "$DATA/library/llms.txt"
  [ -f "$LIB/docs/HISTORICAL/README-WARNING.txt" ] && \
    cp "$LIB/docs/HISTORICAL/README-WARNING.txt" \
       "$DATA/library/docs/HISTORICAL/README-WARNING.txt"
  echo "INFO: MCP library subset staged (mcp.db $(du -sh "$MCP_DB" | cut -f1))"
else
  echo "WARN: mcp.db not found at $MCP_DB — MCP checks will fail"
fi

chmod -R a+rX "$DATA"; chown root:root "$DATA"; chmod 755 "$DATA"   # as firstboot leaves a fresh /data: only root writes it (a+w here hid the 1.0.4 kiwix crash loop, 11-06)
[ -n "$KHOME" ] && { rsync -a "$KHOME/" "$DATA/kolibri_data/";
  chmod -R a+rwX "$DATA/kolibri_data"; }   # kolibri (User=lantern) writes the db

# ── inject MCP server into ephemeral COPY (image predates MCP, 09-18 < 09-19) ─
# The 2026-09-18 image does not contain lantern-mcp.service or mcp_server.py.
# Inject them into the nspawn COPY so the sim reflects the current stack.
# This is NOT modifying the golden image (that stays ro); $COPY is the
# ephemeral snapshot that nspawn boots from.
MCP_SRC="$WKSPC/server/mcp_server.py"
SVC_SRC="$WKSPC/image/stage-lantern/00-lantern/files/lantern-mcp.service"
NGINX_SRC="$WKSPC/image/stage-lantern/00-lantern/files/nginx-lantern.conf"
if [ -f "$MCP_SRC" ] && [ -f "$SVC_SRC" ]; then
  install -m 644 "$MCP_SRC" "$COPY/opt/lantern/mcp_server.py"
  install -m 644 "$SVC_SRC" "$COPY/etc/systemd/system/lantern-mcp.service"
  ln -sf /etc/systemd/system/lantern-mcp.service \
    "$COPY/etc/systemd/system/multi-user.target.wants/lantern-mcp.service"
  echo "INFO: MCP service injected into nspawn COPY"
else
  echo "WARN: MCP source files not found — lantern-mcp will not start"
fi
# Also inject current nginx config (image 09-18 predates /mcp proxy block)
if [ -f "$NGINX_SRC" ]; then
  install -m 644 "$NGINX_SRC" "$COPY/etc/nginx/sites-available/lantern"
  echo "INFO: nginx config updated with /mcp proxy block"
fi

systemd-nspawn -D "$COPY" -M "$M" -b --network-veth \
  --bind="$DATA":/data --console=pipe > /tmp/c4-console.log 2>&1 &

# wait for the machine, then give both veth ends static addresses (nothing
# inside the image is configured to DHCP over host0)
IP=10.99.0.2
up=""
for i in $(seq 1 60); do
  machinectl status "$M" >/dev/null 2>&1 && { up=1; break; }
  sleep 2
done
[ -n "$up" ] || { echo "FAIL: container never registered"; tail -40 /tmp/c4-console.log; exit 1; }
ip addr add 10.99.0.1/24 dev "ve-$M" 2>/dev/null; ip link set "ve-$M" up
for i in $(seq 1 30); do
  systemd-run -M "$M" --wait --pipe /bin/sh -c \
    "ip addr add $IP/24 dev host0 2>/dev/null; ip link set host0 up" 2>/dev/null && break
  sleep 2
done

PASS=0; FAIL=0
check() { # name, cmd, [retries] — retried, services may still be starting
  for i in $(seq 1 ${3:-15}); do
    if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; PASS=$((PASS+1)); return; fi
    sleep 2
  done
  echo "FAIL $1"; FAIL=$((FAIL+1))
}
check "nginx up"            "curl -sm3 -o /dev/null http://$IP/"
check "generate_204 -> 302" "curl -sm3 -o /dev/null -w '%{http_code}' -H 'Host: connectivitycheck.gstatic.com' http://$IP/generate_204 | grep -q 302"
check "apple probe -> 302"  "curl -sm3 -o /dev/null -w '%{http_code}' -H 'Host: captive.apple.com' http://$IP/hotspot-detect.html | grep -q 302"
check "ms probe -> 302"     "curl -sm3 -o /dev/null -w '%{http_code}' -H 'Host: msftconnecttest.com' http://$IP/connecttest.txt | grep -q 302"
check "kiwix catalog"       "curl -sm3 http://$IP:8080/catalog/v2/entries | grep -qi entry"
# kolibri first start against a fresh home copy takes ~90s (migrations)
[ -n "$KHOME" ] && check "kolibri answers" "curl -sm5 -o /dev/null http://$IP:8081/" 90

# ── R3: MCP acceptance checks ─────────────────────────────────────────────────
MCP_SCRIPT=/workspace/image/c4_mcp_checks.sh
if [ -f "$MCP_SCRIPT" ]; then
  bash "$MCP_SCRIPT" "$IP" "$DATA" "$M"
  MCP_EXIT=$?
  [ "$MCP_EXIT" != 0 ] && FAIL=$((FAIL+1))
else
  echo "WARN: c4_mcp_checks.sh not found — MCP checks skipped"
fi

echo "C4 RESULT: $PASS pass, $FAIL fail"
[ "$FAIL" = 0 ]
