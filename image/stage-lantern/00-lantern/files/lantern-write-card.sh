#!/bin/bash
# Rewrite a recovery card from the running Pi (RUNBOOK "Rewriting the recovery
# cards"). FIXES #152 (a6 F10): the RUNBOOK's `of=/dev/sda` is whichever USB
# disk came up first; with the SSD plugged in that can be the only backup.
#   lantern-write-card.sh IMAGE            -> the one USB card reader
#   lantern-write-card.sh IMAGE slot       -> the microSD in the Pi's slot (mmcblk0)
#   lantern-write-card.sh IMAGE /dev/sdX   -> a named disk (still checked)
# After the read-back check the copy gets its own random disk ID, and its
# cmdline.txt and fstab follow it (FIXES #204, E3).
# Refuses: the disk the system runs from, any disk holding a LANTERN_BAK or
# LANTERN partition, a non-USB/non-mmc disk, a disk smaller than the image,
# more than one candidate.
set -eu
IMG=${1:?usage: $0 IMAGE [slot|/dev/sdX]}
[ -r "$IMG" ] || { echo "no image at $IMG" >&2; exit 1; }
SZ=$(stat -c %s "$IMG")
ROOTDISK=/dev/$(lsblk -no PKNAME "$(findmnt -no SOURCE /)" | head -1)

# newid DISK: give DISK a fresh random MBR disk ID and point that disk's own
# cmdline.txt (partition 1) and etc/fstab (partition 2) at it. Same function
# in lantern-firstboot.sh. FIXES #204 (E3, a6 F3).
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

labels() { lsblk -nro LABEL "$1" | grep -v '^$' || true; }
check() {  # check /dev/disk -> 0 if safe to write
  local d=$1 tran rm size
  # one column per call: the slot card has no TRAN, and an empty first column shifted SIZE out of a joint read (11-01)
  tran=$(lsblk -dnr -o TRAN "$d"); tran=${tran:--}; size=$(lsblk -dnrb -o SIZE "$d")
  [ "$d" != "$ROOTDISK" ]                       || { echo "$d is the running system disk" >&2; return 1; }
  ! labels "$d" | grep -qxE 'LANTERN_BAK|LANTERN' || { echo "$d holds a LANTERN/LANTERN_BAK partition (the backup SSD or a library disk)" >&2; return 1; }
  case "$d" in /dev/mmcblk*) ;; *) [ "$tran" = usb ] || { echo "$d is not a USB disk (transport: $tran)" >&2; return 1; };; esac
  [ -n "$size" ] && [ "$size" -ge "$SZ" ]       || { echo "$d ($size B) is smaller than the image ($SZ B)" >&2; return 1; }
}

case "${2:-}" in
  "")   CANDS=()
        for d in $(lsblk -dnro PATH,TRAN | awk '$2=="usb"{print $1}'); do check "$d" 2>/dev/null && CANDS+=("$d"); done
        [ ${#CANDS[@]} -eq 1 ] || { echo "need exactly one USB card reader without LANTERN labels, found ${#CANDS[@]}: ${CANDS[*]:-none}" >&2; lsblk -o NAME,SIZE,TRAN,MODEL,LABEL >&2; exit 1; }
        DEV=${CANDS[0]} ;;
  slot) DEV=/dev/mmcblk0 ;;
  *)    DEV=$2 ;;
esac
check "$DEV"
lsblk -o NAME,SIZE,TRAN,MODEL,LABEL "$DEV"
read -r -p "Write $IMG to $DEV? Everything on it is erased. [yes/N] " a; [ "$a" = yes ] || exit 1
for p in $(lsblk -nro PATH "$DEV" | tail -n +2); do umount "$p" 2>/dev/null || true; done
dd if="$IMG" of="$DEV" bs=4M conv=fsync status=progress
cmp -n "$SZ" "$IMG" "$DEV" || { echo "$DEV does not match $IMG: run this again" >&2; exit 1; }
# Own disk ID for this copy (E3): the image's ID would also match the NVMe's
# and the other card's partitions. (F4, refusing a booted card, is unchanged: D5.)
partprobe "$DEV"; udevadm settle
newid "$DEV" || { echo "$DEV: written and checked, but giving it its own disk ID failed: run this again" >&2; exit 1; }
echo "$DEV OK"
