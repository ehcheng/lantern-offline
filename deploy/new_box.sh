#!/bin/bash
# Build a new Lantern box on a blank Raspberry Pi 5 from the stamped release (deploy/release.env).
# Runs on the Mac, one step at a time; every step can be re-run. NAME labels the box's own keys and
# passwords under .keys/boxes/NAME/ (never in git).
#
#   bash deploy/new_box.sh NAME write /dev/diskN   1. image -> NVMe (in a USB enclosure) or card, on the Mac
#        (put it in the Pi, NO backup SSD plugged in, cable or LIBRARY Wi-Fi to the Mac, power on)
#   bash deploy/new_box.sh NAME wait               2. until firstboot is done and ssh answers
#   bash deploy/new_box.sh NAME eeprom             3. boot order NVMe > card > USB (reboots if it changed)
#   bash deploy/new_box.sh NAME identity           4. this box's own lantern key + console password
#   bash deploy/new_box.sh NAME content ssd        5. library from the backup SSD plugged into the Pi, or
#   bash deploy/new_box.sh NAME content DIR           from a library folder on the Mac/NAS (e.g. library/)
#   bash deploy/new_box.sh NAME check              6. sha256 of every file, reboot, live_test + t6
#
# The box answers at 10.10.10.10 (LANTERN_IP to override); its router needs the RUNBOOK's router setup
# (Part 3, "Setting up a replacement router"), with the fixed lease moved to the new Pi's MAC.
# Steps 5 and 6 take hours; run them in screen:  screen -dmS box bash deploy/new_box.sh NAME content ssd
set -euo pipefail
cd "$(dirname "$0")/.."
[ -s deploy/release.env ] || { echo "deploy/release.env missing: copy deploy/release.env.example and fill in your build"; exit 1; }
. deploy/release.env
NAME=${1:?usage: new_box.sh NAME STEP [ARG]}; STEP=${2:?step: write wait eeprom identity content check}; ARG=${3:-}
[[ $NAME =~ ^[a-z0-9_-]+$ ]] || { echo "NAME: lower-case letters, digits, - and _ only"; exit 1; }
IP=${LANTERN_IP:-10.10.10.10}; BOXKEYS=.keys/boxes/$NAME
# before step 4 the box only knows the release key; after it, only its own
KEY=${LANTERN_KEY:-$([ -s "$BOXKEYS/lantern_ed25519" ] && echo "$BOXKEYS/lantern_ed25519" || echo .keys/lantern_ed25519)}
SSHO=(-i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=10 -o BatchMode=yes)
pi() { ssh "${SSHO[@]}" "lantern@$IP" "$@"; }
die() { echo "new_box: $*" >&2; exit 1; }
say() { echo "[$(date +%T)] $NAME: $*"; }
# the image ships a shared, published first-boot console password: no box gets content before identity replaces it
need_identity() { pi 'test -s /etc/lantern/box-identity' || die "run identity first (the box still has the image's shared first-boot password)"; }

image_path() {
  [ -n "${IMG:-}" ] && { echo "$IMG"; return; }
  for d in $IMAGE_DIRS; do [ -s "$d/$IMAGE" ] && { echo "$d/$IMAGE"; return; }; done
  die "$IMAGE not found in: $IMAGE_DIRS (set IMG=/path/to/it)"
}

case $STEP in
write)
  D=${ARG:?give the whole disk, e.g. /dev/disk6 (diskutil list external)}
  [[ $D =~ ^/dev/disk[0-9]+$ ]] || die "$D: give the whole disk, e.g. /dev/disk6"
  I=$(image_path); info=$(diskutil info "$D") || die "no disk $D"
  grep -qE 'Device Location: +Internal' <<<"$info" && die "$D is an internal disk: refusing"
  grep -qE 'Virtual: +Yes|Protocol: +Disk Image' <<<"$info" && die "$D is a disk image or virtual disk: refusing"
  grep -qE 'Protocol: +USB|Protocol: +Secure Digital|SD Card' <<<"$info" || die "$D is not a USB or SD card disk: refusing"
  grep -qE 'Device Location: +External|Removable Media: +(Removable|Yes)' <<<"$info" || die "$D is not external or removable: refusing"
  diskutil list "$D" | grep -qE 'LANTERN_BAK' && die "$D holds LANTERN_BAK (the backup SSD): refusing"
  isz=$(stat -f%z "$I"); dsz=$(diskutil info -plist "$D" | plutil -extract TotalSize raw -)
  [ "$dsz" -ge "$isz" ] || die "$D ($dsz bytes) is smaller than the image ($isz)"
  say "checking $I"; [ "$(gsha256sum "$I" | cut -d' ' -f1)" = "$IMAGE_SHA256" ] || die "image sha256 does not match release.env"
  diskutil list "$D"
  read -r -p "ERASE $D ($((dsz / 1000000000)) GB) and write $IMAGE? Type yes: " a; [ "$a" = yes ] || die "not written"
  diskutil unmountDisk "$D"
  R=${D/disk/rdisk}; say "writing (a few minutes; sudo asks for the Mac password)"
  sudo dd if="$I" of="$R" bs=4m
  say "reading back"
  [ $((isz % 4194304)) = 0 ] || die "image size is not a multiple of 4 MiB; check by hand"
  [ "$(sudo dd if="$R" bs=4m count=$((isz / 4194304)) 2>/dev/null | gsha256sum | cut -d' ' -f1)" = "$IMAGE_SHA256" ] \
    || die "read-back does not match: write again or use another disk"
  diskutil eject "$D"; say "OK: written and verified. Put it in the Pi (no SSD plugged in) and power on, then: wait" ;;

wait)
  say "waiting for ssh at $IP (firstboot makes partitions and identity, about 2 minutes)"
  for _ in $(seq 120); do pi 'systemctl is-system-running 2>/dev/null | grep -qE "^(running|degraded)$" && test -f /var/lib/lantern/identity-done' 2>/dev/null && break; sleep 10; done
  pi true || die "no ssh at $IP after 20 minutes"
  pi 'cat /etc/lantern-release; findmnt -no SOURCE / /data'; say "up. Next: eeprom" ;;

eeprom)
  cur=$(pi 'sudo rpi-eeprom-config')
  if grep -qx 'BOOT_ORDER=0xf416' <<<"$cur" && grep -qx 'PCIE_PROBE=1' <<<"$cur"; then say "boot order already set"; exit 0; fi
  new=$(grep -vE '^(BOOT_ORDER|PCIE_PROBE)=' <<<"$cur"; printf 'BOOT_ORDER=0xf416\nPCIE_PROBE=1\n')
  pi "cat > /tmp/boot.conf && sudo rpi-eeprom-config --apply /tmp/boot.conf" <<<"$new"
  say "boot order applied; restarting"; pi 'sudo systemctl reboot' || true; sleep 30
  bash deploy/new_box.sh "$NAME" wait >/dev/null; pi 'sudo rpi-eeprom-config' | grep -E '^(BOOT_ORDER|PCIE_PROBE)='; say "Next: identity" ;;

identity)
  own=no; [ -s "$BOXKEYS/lantern_ed25519" ] && [ "$KEY" = "$BOXKEYS/lantern_ed25519" ] && pi true && own=yes
  [ $own = yes ] && pi 'test -s /etc/lantern/box-identity' && { say "own key already in place"; exit 0; }
  mkdir -p "$BOXKEYS"; chmod 700 "$BOXKEYS"
  [ -s "$BOXKEYS/lantern_ed25519" ] || ssh-keygen -q -t ed25519 -N '' -C "lantern@$NAME" -f "$BOXKEYS/lantern_ed25519"
  [ -s "$BOXKEYS/lantern.pw" ] || { (umask 077; openssl rand -base64 18 | tr -d '/+=' | cut -c1-16 > "$BOXKEYS/lantern.pw"); }
  if [ $own = no ]; then
    K=.keys/lantern_ed25519; SSHO[1]=$K
    pi 'cat > /tmp/k.pub && install -m 600 /tmp/k.pub ~/.ssh/authorized_keys && rm /tmp/k.pub' < "$BOXKEYS/lantern_ed25519.pub"
    SSHO[1]=$BOXKEYS/lantern_ed25519
    pi true || die "the new key does not log in; the box may now refuse both keys (recover from a card, RUNBOOK Part 2)"
  fi
  pi 'sudo chpasswd' <<<"lantern:$(cat "$BOXKEYS/lantern.pw")"   # replaces the image's shared first-boot password
  pi "sudo install -d /etc/lantern && echo $NAME | sudo tee /etc/lantern/box-identity >/dev/null"   # content and check refuse a box without it
  pi 'sudo cat /etc/lantern/kolibri-admin.pw' > "$BOXKEYS/kolibri-admin.pw" 2>/dev/null || true; chmod 600 "$BOXKEYS"/*.pw
  say "own key installed (the release key no longer logs in); console password set (ssh stays key-only)"
  echo "  binder card for $NAME: lantern console password $(cat "$BOXKEYS/lantern.pw")  kolibri admin: lantern / $(cat "$BOXKEYS/kolibri-admin.pw" 2>/dev/null || echo 'not set up yet, read it after step 6')"
  echo "  key: $BOXKEYS/lantern_ed25519   Next: content" ;;

content)
  S=${ARG:?content ssd | content DIR}
  need_identity
  pi 'mountpoint -q /data/library' && die "/data/library is a bind mount of the SSD (it was plugged in at first boot): unplug the SSD, restart the Pi, retry"
  if [ "$S" = ssd ]; then
    say "copying from the SSD on the Pi (1-2 h for 1.3 TB)"
    pi 'sudo mkdir -p /mnt/bak && (mountpoint -q /mnt/bak || sudo mount -o ro -L LANTERN_BAK /mnt/bak) && sudo rsync -aH --info=stats1 /mnt/bak/library/ /data/library/ && sudo umount /mnt/bak'
  else
    [ -s "$S/MANIFEST.sha256" ] || die "$S has no MANIFEST.sha256: not a sealed library folder"
    m=$(shasum -a 256 < "$S/MANIFEST.sha256" | cut -c1-64)
    [ "$m" = "$LIBRARY_MANIFEST" ] || die "$S is not library $LIBRARY (manifest $m, release wants $LIBRARY_MANIFEST). The working tree may hold a newer dev seal: use 'content ssd', or check out tag $RELEASE's library/ files first"
    say "copying $S to the Pi over the network (about 3-4 h for 1.3 TB on gigabit)"
    rsync -aL --chmod=a+rX --chown=lantern:lantern --partial --info=stats1 --rsync-path='sudo rsync' -e "ssh ${SSHO[*]}" "$S/" "lantern@$IP:/data/library/"
  fi
  say "copied. Next: check" ;;

check)
  need_identity
  pi 'test -s /data/library/MANIFEST.sha256' || die "no library on the box yet: run content first"
  v=$(pi 'cat /data/library/VERSION.json'); grep -q "\"$LIBRARY_MANIFEST\"" <<<"$v" || say "WARNING: the box's library is not release $LIBRARY: $v"
  say "hashing every file on the Pi (1.5-2 h, quiet until the end)"
  pi 'cd /data && sha256sum -c --quiet library/MANIFEST.sha256' || die "files damaged or missing (listed above): copy them again (content)"
  say "all files OK; restarting so every service picks up the library"
  pi 'sudo systemctl reboot' || true; sleep 30; bash deploy/new_box.sh "$NAME" wait >/dev/null
  LANTERN_KEY=$KEY bash deploy/live_test.sh "$IP" > "logs/new_box_${NAME}_live_test.log" 2>&1 && lt=PASS || lt=FAIL
  LANTERN_KEY=$KEY bash tests/t6_box.sh "$IP" > "logs/new_box_${NAME}_t6.log" 2>&1 && t6=PASS || t6=FAIL
  tail -3 "logs/new_box_${NAME}_live_test.log"
  say "live_test $lt, t6 $t6 (logs: logs/new_box_${NAME}_*.log). Last: a phone on LIBRARY opens http://library.lan" ;;

*) die "unknown step $STEP (write wait eeprom identity content check)" ;;
esac
