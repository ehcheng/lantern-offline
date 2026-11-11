#!/bin/bash
# Push a reseal to the Pi: every MANIFEST line that changed vs the last commit is
# rsynced (dereferencing bulk symlinks; -I: every listed file is sent even when size+mtime match, FIXES #119 VTTs), lines that vanished are removed on the Pi,
# then MANIFEST.sha256 + VERSION.json go last. Run WITHOUT the sandbox, in screen.
#   bash deploy/push_seal.sh [pi_ip]
set -uo pipefail
export LC_ALL=C   # FIXES #120: sort/comm under a UTF-8 locale mis-collate Arabic/Persian names, so a re-added path landed in rm.lst and was deleted
cd "$(dirname "$0")/.."
[ -f library/VERSION.json ] || { echo "no library/VERSION.json (seal rejected or not sealed): refusing to push"; exit 1; }
IP=${1:-${LANTERN_IP:-10.10.10.10}}; KEY=${LANTERN_KEY:-.keys/lantern_ed25519}; L=logs
BASE=${BASE:-HEAD}  # commit whose MANIFEST is what the Pi currently has (set it when seals were committed without a push)
SSH="ssh -i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
/usr/bin/git diff "$BASE" -- library/MANIFEST.sha256 | grep '^+[0-9a-f]\{64\}  library/' | cut -c76- > "$L/push_seal.add.lst"
/usr/bin/git diff "$BASE" -- library/MANIFEST.sha256 | grep '^-[0-9a-f]\{64\}  library/' | cut -c76- | sort > "$L/push_seal.gone.lst"
sort "$L/push_seal.add.lst" | comm -13 - "$L/push_seal.gone.lst" > "$L/push_seal.rm.lst"   # gone and not re-added
echo "$(date +%T) add/changed=$(wc -l < "$L/push_seal.add.lst") remove=$(wc -l < "$L/push_seal.rm.lst")"
rsync -aL -I --chmod=a+rX --partial --info=stats2 --files-from="$L/push_seal.add.lst" -e "$SSH" library/ "lantern@$IP:/data/library/" || { echo RSYNC_FAILED; exit 1; }
if [ -s "$L/push_seal.rm.lst" ]; then
  $SSH "lantern@$IP" 'cd /data/library && xargs -d "\n" rm -f' < "$L/push_seal.rm.lst"
fi
# FIXES #197 (RT4 b4 W1): --chmod=a+rX on both rsyncs. -a copies the source mode, and library/MANIFEST.sha256 is 0600
# on dev, so the Pi's nginx (www-data) answered 403 for /MANIFEST.sha256. a+r only adds read; nothing loses access.
rsync -aL --chmod=a+rX -e "$SSH" library/MANIFEST.sha256 library/VERSION.json "lantern@$IP:/data/library/" || { echo RSYNC_MANIFEST_FAILED; exit 1; }
echo "$(date +%T) PUSH_SEAL_DONE (files on the Pi; the box is not accepted until the three gates below pass)"
# Required gates against the Pi itself: live_test, T5, T4 (results/t5_<ip>.csv, t4_<ip>.csv sit beside the dev rows in REPORT.md).
exec bash deploy/pi_gates.sh "$IP"
