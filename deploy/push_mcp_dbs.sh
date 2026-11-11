#!/bin/bash
# After build_mcp_index + build_embeddings: re-hash the two db lines in MANIFEST
# (they are sealed but rebuilt after pass A), bump VERSION.json, push dbs + manifest
# + version to the Pi and restart lantern-mcp. No sandbox, in screen.
set -uo pipefail
cd "$(dirname "$0")/.."
IP=${1:-${LANTERN_IP:-10.10.10.10}}; KEY=${LANTERN_KEY:-.keys/lantern_ed25519}
SSH="ssh -i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
for f in library/_app/mcp/mcp.db library/_app/mcp/embeddings.db; do
  grep -v "  $f\$" library/MANIFEST.sha256 > library/MANIFEST.sha256.tmp && shasum -a 256 "$f" >> library/MANIFEST.sha256.tmp && mv library/MANIFEST.sha256.tmp library/MANIFEST.sha256
done
sort -k2 -o library/MANIFEST.sha256 library/MANIFEST.sha256
bash build/gen_version.sh
rsync -aL --partial --info=stats2 -e "$SSH" library/_app/mcp/mcp.db library/_app/mcp/embeddings.db "lantern@$IP:/data/library/_app/mcp/" || { echo RSYNC_DB_FAILED; exit 1; }
rsync -aL -e "$SSH" library/MANIFEST.sha256 library/VERSION.json "lantern@$IP:/data/library/" || { echo RSYNC_MANIFEST_FAILED; exit 1; }
$SSH "lantern@$IP" 'sudo systemctl restart lantern-mcp && sleep 3 && systemctl is-active lantern-mcp'
echo "$(date +%T) PUSH_MCP_DONE"
