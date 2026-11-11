#!/bin/sh
# RUNBOOK Part 4 item 5 (library backup to the SSD), run ON THE PI. A full sha256 check follows the copy: rsync's quick
# check once skipped 137 Kolibri .vtt files with the same size and mtime but old content (11-02). On FAILED lines, rerun
# the rsync with --ignore-times on those paths, then the check again. From the Mac (lantern key):
#   ssh lantern@10.10.10.10 'sudo tee /opt/lantern/ssd_sync.sh >/dev/null' < deploy/pi_ssd_sync.sh
#   ssh lantern@10.10.10.10 'sudo systemd-run --unit=ssd-sync-<tag> /bin/sh /opt/lantern/ssd_sync.sh'
# Log: /opt/lantern/ssd_sync.log, last line SSD_SYNC_DONE or SSD_SYNC_FAIL. The SSD stays mounted at /mnt/bak.
L=/opt/lantern/ssd_sync.log
exec >"$L" 2>&1
echo "start $(date)"
mkdir -p /mnt/bak
mountpoint -q /mnt/bak || mount -L LANTERN_BAK /mnt/bak
mountpoint -q /mnt/bak || { echo "SSD_SYNC_FAIL not mounted"; exit 1; }
rsync -aH --delete --stats /data/library/ /mnt/bak/library/ || { echo "SSD_SYNC_FAIL rsync rc=$?"; exit 1; }
echo "rsync done $(date)"
(cd /mnt/bak && sha256sum -c --quiet library/MANIFEST.sha256) || { echo "SSD_SYNC_FAIL sha256 rc=$?"; exit 1; }
echo "sha256 done $(date)"
sh /mnt/bak/library/verify.sh /mnt/bak/library || { echo "SSD_SYNC_FAIL verify rc=$?"; exit 1; }
echo "SSD_SYNC_DONE $(date)"
