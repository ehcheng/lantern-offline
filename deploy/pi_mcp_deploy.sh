#!/bin/bash
# Deploy mcp_server.py + the nginx site to the Pi (nginx: /semantic, /mcp, .csv type; /rerank route removed in FIXES #100). Run WITHOUT the sandbox, before push_seal.sh.
# Source of truth: image/stage-lantern/00-lantern/files/{mcp_server.py,nginx-lantern.conf}
# (server/mcp_server.py is a symlink to the staged copy, so dev, tests and the image share one file).
set -euo pipefail
cd "$(dirname "$0")/.."
PI=${1:-${LANTERN_IP:-10.10.10.10}}; KEY=${LANTERN_KEY:-.keys/lantern_ed25519}; SSH="ssh -i $KEY -o ConnectTimeout=10 lantern@$PI"
scp -i $KEY server/mcp_server.py image/stage-lantern/00-lantern/files/nginx-lantern.conf lantern@$PI:/tmp/
$SSH 'sudo install -m 644 /tmp/mcp_server.py /opt/lantern/mcp_server.py && sudo install -m 644 /tmp/nginx-lantern.conf /etc/nginx/sites-available/lantern && sudo nginx -t && sudo systemctl reload nginx && sudo systemctl restart lantern-mcp && sleep 3 && systemctl is-active lantern-mcp'
curl -sf --max-time 20 -H 'Host: library.lan' "http://$PI/semantic?q=water&limit=1" | head -c 120; echo
echo "PI_MCP_DEPLOY_DONE"
