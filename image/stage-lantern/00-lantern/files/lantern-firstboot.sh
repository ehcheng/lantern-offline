#!/bin/bash
# Lantern first boot (BUILD_PLAN C2 fleet hygiene + C3 data partition).
# Idempotent — runs every boot, exits fast when nothing to do.
set -u

MARK=/var/lib/lantern
mkdir -p "$MARK"
FRESH=; [ -f "$MARK/identity-done" ] || FRESH=1        # first start of this copy

# newid DISK: give DISK a fresh random MBR disk ID and point that disk's own
# cmdline.txt (partition 1) and etc/fstab (partition 2) at it. Same function
# in lantern-write-card.sh. FIXES #204 (E3, a6 F3).
newid() {
  local disk=$1 old new p m rc=0 mnt=() tmp=()
  old=$(sfdisk --disk-id "$disk") || return 1
  echo "$old" | grep -qx '0x[0-9a-f]\{8\}' || { echo "$disk: no MBR disk ID ($old), left alone" >&2; return 0; }
  old=${old#0x}; new=$old
  while [ "$new" = "$old" ] || [ "$new" = 00000000 ]; do new=$(od -An -N4 -tx4 /dev/urandom | tr -d ' \n'); done
  for p in $(lsblk -nro PATH "$disk" | sed -n 2,3p); do
    m=$(findmnt -nfo TARGET --source "$p")
    if [ -z "$m" ]; then m=$(mktemp -d) && mount "$p" "$m" || { rmdir "$m"; rc=1; break; }; tmp+=("$m"); fi
    mnt+=("$m")
  done
  [ $rc = 0 ] && [ -f "${mnt[0]}/cmdline.txt" ] && [ -f "${mnt[1]}/etc/fstab" ] || rc=1
  if [ $rc = 0 ] && sfdisk --no-reread --no-tell-kernel --disk-id "$disk" "0x$new" >/dev/null 2>&1 && \
     [ "$(sfdisk --disk-id "$disk")" = "0x$new" ]; then
    if sed -i "s/PARTUUID=$old-/PARTUUID=$new-/g" "${mnt[0]}/cmdline.txt" "${mnt[1]}/etc/fstab"; then
      echo "$disk: disk ID $old -> $new"
    else  # put everything back rather than leave a disk its cmdline cannot find
      sed -i "s/PARTUUID=$new-/PARTUUID=$old-/g" "${mnt[0]}/cmdline.txt" "${mnt[1]}/etc/fstab"
      sfdisk --no-reread --no-tell-kernel --disk-id "$disk" "0x$old" >/dev/null 2>&1; rc=1
    fi
    sync
  else rc=1; fi
  for m in "${tmp[@]}"; do umount "$m"; rmdir "$m"; done
  return $rc
}

# ── fleet hygiene: unique ssh host keys + machine-id per unit (C2) ──
# Runs once per CLONE: rpi-clone/dd copies delete the stamp pre-boot via
# the documented E4 step; belt-and-braces check on empty/missing keys too.
if [ ! -f "$MARK/identity-done" ] || [ ! -s /etc/ssh/ssh_host_ed25519_key ]; then
  rm -f /etc/ssh/ssh_host_*
  # ssh-keygen -A, not dpkg-reconfigure: the openssh postinst blocks on
  # systemctl inside a still-starting system (hung C4 container boot)
  ssh-keygen -A >/dev/null 2>&1
  rm -f /etc/machine-id /var/lib/dbus/machine-id
  systemd-machine-id-setup
  ln -sf /etc/machine-id /var/lib/dbus/machine-id
  touch "$MARK/identity-done"
fi

# ── C3: LANTERN data partition on the BOOT disk (not by label: an SD spare
# left in the slot may carry its own LANTERN). Root is capped at 20 GiB; the
# stock resizer is stripped from cmdline.txt at build (see 01-run.sh).
ROOTDEV=$(findmnt -no SOURCE /)                       # e.g. /dev/nvme0n1p2
DISK=/dev/$(lsblk -no PKNAME "$ROOTDEV" | head -1)
ROOTNUM=${ROOTDEV##*[!0-9]}                           # trailing digits; util-linux 2.38 lacks PARTN

# ── E3 (FIXES #204, a6 F3): one disk ID per disk. Every dd of the image
# carries the build's disk ID, so with the slot card in place two disks answer
# root=PARTUUID=<id>-02. On the first start of a copy, or whenever another
# attached disk shows this disk's ID, re-roll it. Done before the data
# partition below, so its fstab line gets the new ID. Takes effect for root
# from the next start; this start already found its root.
PTID=$(lsblk -dno PTUUID "$DISK")
if [ -n "$FRESH" ] || { [ -n "$PTID" ] && \
     lsblk -dnro PATH,PTUUID | awk -v d="$DISK" -v id="$PTID" '$1!=d && $2==id {f=1} END {exit !f}'; }; then
  newid "$DISK" && { udevadm trigger --action=change $(lsblk -nro PATH "$DISK"); udevadm settle; }
fi
DATAPART=$(lsblk -nro PATH,LABEL "$DISK" | awk '$2=="LANTERN"{print $1}' | head -1)
if [ -z "$DATAPART" ] && [ -n "$ROOTNUM" ] && \
   [ "$(lsblk -nro TYPE "$DISK" | grep -c part)" -le "$ROOTNUM" ]; then
  # ponytail: parted 3.5 resizes an in-use partition; the Yes answers its
  # "partition is busy" prompt. Disks under 20 GiB just keep the stock root.
  echo Yes | parted ---pretend-input-tty "$DISK" resizepart "$ROOTNUM" 20GiB >/dev/null 2>&1 && \
    resize2fs "$ROOTDEV" >/dev/null 2>&1
  START=$(parted -sm "$DISK" unit MiB print free | awk -F: '/free/ {s=$2} END {print s}')
  if [ -n "$START" ] && parted -s "$DISK" -- mkpart primary ext4 "$START" 100%; then
    partprobe "$DISK"; udevadm settle
    DATAPART=$(lsblk -nro PATH,TYPE "$DISK" | awk '$2=="part"{p=$1} END {print p}')
    mkfs.ext4 -q -F -L LANTERN "$DATAPART"
  fi
fi
if [ -n "$DATAPART" ]; then
  PU=$(blkid -c /dev/null -s PARTUUID -o value "$DATAPART")   # no cache: the ID may be new
  mkdir -p /data
  if ! grep -q "^PARTUUID=$PU /data " /etc/fstab; then
    sed -i '\| /data |d' /etc/fstab
    echo "PARTUUID=$PU /data ext4 defaults,noatime,nofail 0 2" >> /etc/fstab
    systemctl daemon-reload
  fi
  mountpoint -q /data || mount /data || true
fi

# ── degraded mode: no library on this disk (card boot, or fresh NVMe) but the
# cold-backup SSD (label LANTERN_BAK, rsync of /data/library at /library) is
# plugged in -> serve straight from it. RUNBOOK Part 2 step 3a. Bind mount,
# nothing written to the SSD; the placeholder below is skipped.
if [ ! -e /data/library/MANIFEST.sha256 ]; then
  for i in 1 2 3 4 5 6; do BAK=$(blkid -L LANTERN_BAK); [ -n "$BAK" ] && break; udevadm settle; sleep 2; done  # USB enumerates late
fi
if [ ! -e /data/library/MANIFEST.sha256 ] && [ -n "${BAK:-}" ]; then
  mkdir -p /mnt/bak /data/library
  mountpoint -q /mnt/bak || mount -o ro "$BAK" /mnt/bak
  [ -e /mnt/bak/library/MANIFEST.sha256 ] && ! mountpoint -q /data/library && \
    mount --bind /mnt/bak/library /data/library
fi

# ── empty-data placeholder (C3): nginx serves a "copy the library" page ──
if [ ! -e /data/library/index.html ]; then
  mkdir -p /data/library/_app
  cp -n /opt/lantern/copy-the-library.html /data/library/index.html 2>/dev/null || true
fi
# kolibri.service uses KOLIBRI_HOME=/data/kolibri_data; the shipped home lives
# inside the rsynced library tree.
[ -e /data/kolibri_data ] || ln -s /data/library/kolibri_data /data/kolibri_data

# ── Kolibri provisioning (FIXES #151, a8 F1): without a facility Kolibri shows
# /en/setup/ to anyone on the Wi-Fi and the first visitor becomes super-admin.
# kolibri.service points KOLIBRI_AUTOMATIC_PROVISION_FILE at this JSON; Kolibri
# applies it on start while unprovisioned (also after a library re-sync drops
# an unprovisioned db.sqlite3 back in). Password: generated once per box into
# /etc/lantern/kolibri-admin.pw (root only, outside the web root); admin user
# "lantern". Learners browse without login (landing_page learn + guest access,
# kolibri/core/device/utils.py provision_from_file). Preset informal.
PW=/etc/lantern/kolibri-admin.pw
PROV=/etc/lantern/kolibri-provision.json
install -d -m 755 /etc/lantern
if [ ! -s "$PW" ]; then
  (umask 077; tr -dc 'A-Za-z0-9' </dev/urandom | head -c 24 > "$PW"; echo >> "$PW")
fi
if [ ! -s "$PROV" ]; then
  (umask 027; cat > "$PROV" <<EOF2
{
  "facility_name": "Lantern Library",
  "preset": "informal",
  "facility_settings": {"learner_can_login_with_no_password": true, "learner_can_edit_password": false, "learner_can_sign_up": true},
  "device_settings": {"language_id": "en", "landing_page": "learn", "allow_guest_access": true,
                      "allow_learner_unassigned_resource_access": true, "name": "Lantern",
                      "allow_other_browsers_to_connect": true},
  "superuser": {"username": "lantern", "password": "$(head -1 "$PW")"}
}
EOF2
  )
  chgrp lantern "$PROV" 2>/dev/null || true   # kolibri.service runs as User=lantern
fi

exit 0
