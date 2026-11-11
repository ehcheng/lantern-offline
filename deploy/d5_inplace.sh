#!/bin/bash
# D5 in-place upgrade: bring the Pi's running NVMe system to the boot image 1.0.1 configuration
# (owner decision 2026-10-30: no re-image, no library restore). Runs on the Mac, sandbox OFF (ssh + LAN).
#   bash deploy/d5_inplace.sh               = --dry-run: plan + diffs. On the Pi it only reads
#                                                        (plus `nft -c` from stdin, a check that commits nothing)
#   bash deploy/d5_inplace.sh --apply       back up, apply, verify. Idempotent: a re-run skips what matches
#   bash deploy/d5_inplace.sh --fetch-debs  Mac + lima VM: .debs for the missing packages, resolved
#                                                        against the box's own dpkg status (needs the 1.0.1 build rootfs)
#   bash deploy/d5_inplace.sh --apply-debs  install those .debs on the Pi offline (apt simulation first)
# Never touches /data/library, never partitions, never dd. Report: logs/audit/d5_inplace_20261030.md
set -euo pipefail
cd "$(dirname "$0")/.."
MODE=${1:---dry-run}
case $MODE in --dry-run|--apply|--fetch-debs|--apply-debs) ;; *) echo "usage: $0 [--dry-run|--apply|--fetch-debs|--apply-debs]"; exit 2;; esac
IP=${LANTERN_IP:-10.10.10.10}; PI=lantern@$IP; KEY=${LANTERN_KEY:-.keys/lantern_ed25519}; H='Host: library.lan'
F=image/stage-lantern/00-lantern/files
DEBS=image/deploy/inplace-debs
STAMP=$(date +%Y%m%d-%H%M%S); BK=/opt/lantern/backup-$STAMP; STG=/tmp/d5-$STAMP
LOG=${LOG:-logs/d5_inplace_${MODE#--}_$STAMP.log}
exec > >(tee -a "$LOG") 2>&1
echo "=== d5_inplace $MODE $(date) log $LOG"

T=$(mktemp -d); SOCK=$T/s
O=(-i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=10 -o BatchMode=yes)
# The kept session: every command rides this one connection, so an sshd reload or a new firewall rule
# (established traffic stays accepted) never cuts us off mid-run. New-login tests bypass it.
ssh "${O[@]}" -o ControlMaster=yes -o ControlPersist=yes -S "$SOCK" -fN "$PI" || { echo "ABORT: no ssh to $PI"; exit 1; }
trap 'ssh -S "$SOCK" -O exit "$PI" 2>/dev/null; rm -rf "$T"' EXIT
R() { ssh "${O[@]}" -S "$SOCK" "$PI" "$@"; }
fresh() { ssh "${O[@]}" -o ControlPath=none -o PreferredAuthentications=publickey -o PasswordAuthentication=no "$PI" true; }
# Methods sshd offers to a client with no key ("publickey,password" now; "publickey" after). No password is sent.
methods() { ssh "${O[@]}" -o ControlPath=none -o PubkeyAuthentication=no "$PI" true 2>&1 | grep -o 'Permission denied ([^)]*)' || true; }
code() { curl -s -o /dev/null -m 20 -w '%{http_code}' "$@" || true; }
say() { echo; echo "== $*"; }
die() { echo "ABORT: $*"; exit 1; }

PKGS=$(grep -v '^$' image/stage-lantern/00-lantern/00-packages | tr '\n' ' ')
missing_pkgs() { R "bash -s $PKGS" <<'EOF' | tr '\n' ' '
for p; do [ "$(dpkg-query -W -f='${db:Status-Status}' "$p" 2>/dev/null)" = installed ] || echo "$p"; done
EOF
}

# ── --fetch-debs: download the closure the BOX needs (its dpkg status, the 1.0.1 rootfs's apt lists and keys) ──
if [ "$MODE" = --fetch-debs ]; then
  M=$(missing_pkgs); [ -n "${M// /}" ] || { echo "nothing missing"; exit 0; }
  echo "missing on the box: $M"
  mkdir -p "$DEBS/partial"
  R 'cat /var/lib/dpkg/status' > "$DEBS/box-dpkg-status"
  # ponytail: needs the lima VM's stage-lantern rootfs from the last build (run_build.sh deletes it at the next start)
  limactl shell lantern-build sudo bash -c "set -e; R=/opt/lantern-build/pi-gen/work/lantern-boot-v1/stage-lantern/rootfs
    test -d \$R/var/lib/apt/lists || { echo 'no 1.0.1 stage rootfs in the VM'; exit 1; }
    apt-get -o Dir=\$R -o Dir::State::status=/workspace/$DEBS/box-dpkg-status -o Dir::Cache::archives=/workspace/$DEBS \
      -o Dir::Cache::pkgcache= -o Dir::Cache::srcpkgcache= -o Debug::NoLocking=1 -y --download-only install $M"
  echo "$(ls "$DEBS"/*.deb | wc -l) .debs, $(du -sh "$DEBS" | cut -f1) in $DEBS"
  exit 0
fi

# ── --apply-debs: offline install. Sources switched off, so apt sees only dpkg status + these files and
#    refuses before changing anything if a dependency is missing. ──
if [ "$MODE" = --apply-debs ]; then
  ls "$DEBS"/*.deb >/dev/null 2>&1 || die "no .debs in $DEBS: run --fetch-debs first"
  COPYFILE_DISABLE=1 tar -C "$DEBS" -cf - $(cd "$DEBS" && ls *.deb) | R "mkdir -p $STG/debs && tar -C $STG/debs -xf -"
  A="-o Dir::Etc::SourceList=/dev/null -o Dir::Etc::SourceParts=/dev/null -o Dir::Cache::pkgcache= -o Dir::Cache::srcpkgcache="
  SIM=$(R "sudo -n apt-get $A -s install --no-download $STG/debs/*.deb" 2>&1 || true)
  grep -E '^(Inst|Remv|E:)|upgraded' <<<"$SIM" || true
  grep -q '^E:' <<<"$SIM" && die "apt simulation failed (above): nothing installed"
  grep -q '^Remv' <<<"$SIM" && die "apt would REMOVE packages: not installing"
  R "sudo -n apt-get $A -y install --no-download $STG/debs/*.deb" | tail -5
  echo "still missing: $(missing_pkgs)"; R "rm -rf $STG"; exit 0
fi

# ── the change list: what 01-run.sh installs (src | dst | mode | owner) ──
V=1.0.5   # 1.0.1: Kolibri provision JSON (fixed 1.0.2); 1.0.2: write-card slot size (fixed 1.0.3); 1.0.4: an extra password login, and kiwix crash-looped on a fresh /data (fixed 1.0.5)
# GIT: last commit of the stage files = the image's own GIT (328c2ef2) while they are unchanged since the build
GIT=$(git log -1 --format=%h -- image/stage-lantern); [ -z "$(git status --porcelain -- image/stage-lantern 2>/dev/null)" ] || GIT=$GIT-dirty
if R "grep -qx IMAGE=$V /etc/lantern-release && grep -qx INSTALL=in-place /etc/lantern-release"; then
  R 'cat /etc/lantern-release' > "$T/lantern-release"            # already stamped: keep it (idempotent)
else
  # Same keys as build_boot_image.sh writes, plus two in-place markers. No spaces: live_test splits on whitespace.
  # LIBRARY_MIN: run_build.sh does not pass LANTERN_LIBRARY_MIN into the VM, so the image carries the default too.
  # UPGRADED_FROM: kept from an earlier in-place stamp (the 10-30 first try wrote 1.0.1), else the box's IMAGE
  FROM=$(R "sed -n 's/^UPGRADED_FROM=//p' /etc/lantern-release"); [ -n "$FROM" ] || FROM=$(R "sed -n 's/^IMAGE=//p' /etc/lantern-release")
  printf 'IMAGE=%s\nGIT=%s\nBUILT=%s\nHW=pi5-16g-nvme\nLIBRARY_MIN=%s\nINSTALL=in-place\nUPGRADED_FROM=%s\n' \
    "$V" "$GIT" "$(date -u +%FT%TZ)" "${LIBRARY_MIN:-2026.09.27}" "$FROM" > "$T/lantern-release"
fi
FILES="$F/lantern-firstboot.sh /opt/lantern/lantern-firstboot.sh 755 root
$F/copy-the-library.html /opt/lantern/copy-the-library.html 644 root
$F/lantern-write-card.sh /opt/lantern/lantern-write-card.sh 755 root
$F/lantern-discs.sh /opt/lantern/lantern-discs.sh 755 root
$F/lantern-voice.py /opt/lantern/lantern-voice.py 755 root
$F/mcp_server.py /opt/lantern/mcp_server.py 644 root
$F/pagefind /usr/local/bin/pagefind 755 root
$F/kiwix.service /etc/systemd/system/kiwix.service 644 root
$F/kolibri.service /etc/systemd/system/kolibri.service 644 root
$F/lantern-mcp.service /etc/systemd/system/lantern-mcp.service 644 root
$F/lantern-embed.service /etc/systemd/system/lantern-embed.service 644 root
$F/lantern-voice.service /etc/systemd/system/lantern-voice.service 644 root
$F/lantern-discs.service /etc/systemd/system/lantern-discs.service 644 root
$F/lantern-firstboot.service /etc/systemd/system/lantern-firstboot.service 644 root
$F/avahi-lantern.service /etc/avahi/services/lantern.service 644 root
$F/nginx-lantern.conf /etc/nginx/sites-available/lantern 644 root
$T/lantern-release /etc/lantern-release 644 root"
SSHD="$F/sshd-lantern.conf /etc/ssh/sshd_config.d/lantern.conf 644 root"    # own guarded step
NFT="$F/nftables.conf /etc/nftables.conf 755 root"                         # own guarded step
# Must already match. Never replaced over the network: a wrong key or eth0 profile is a lockout.
CHECK="$F/lantern_ed25519.pub /home/lantern/.ssh/authorized_keys 600 lantern
$F/lantern-eth0.nmconnection /etc/NetworkManager/system-connections/lantern-eth0.nmconnection 600 root"
DROPIN=/etc/systemd/system/lantern-embed.service.d/home.conf   # v5 hand fix; 1.0.1 has these lines in the unit itself
UNITS="nginx kiwix kolibri lantern-mcp lantern-embed lantern-voice lantern-discs lantern-firstboot chrony avahi-daemon"
ALL=$(printf '%s\n%s\n%s\n%s\n' "$FILES" "$SSHD" "$NFT" "$CHECK" | awk '{print $2}' | tr '\n' ' ')

state() { R "sudo -n bash -s $ALL" <<'EOF'
for f; do if [ -e "$f" ]; then echo "$(sha256sum < "$f" | cut -c1-64) $(stat -c %a:%U "$f") $f"; else echo "missing -:- $f"; fi; done
EOF
}
# same SRC DST MODE OWN STATE -> 0 when the Pi's file has the repo's bytes, mode and owner
same() { local l; l=$(grep " $2\$" <<<"$5" || true)
  [ "$(shasum -a 256 "$1" | cut -c1-64) $3:$4" = "$(cut -d' ' -f1,2 <<<"$l")" ]; }

gates() { R 'bash -s' <<'EOF'
ok(){ echo "OK   $1"; }; no(){ echo "FAIL $1"; }
root=$(findmnt -no SOURCE /); disk=/dev/$(lsblk -no PKNAME "$root" | head -1)
[ "$root" = /dev/nvme0n1p2 ] && ok "root is $root" || no "root is $root, not /dev/nvme0n1p2"
[ "$(lsblk -no LABEL /dev/nvme0n1p3)" = LANTERN ] && [ "$(findmnt -no SOURCE /data)" = /dev/nvme0n1p3 ] \
  && ok "/data = nvme0n1p3 LANTERN (firstboot will not partition)" || no "/data is not nvme0n1p3 LANTERN"
n=$(lsblk -nro TYPE "$disk" | grep -c part); [ "$n" -ge 3 ] && ok "$disk has $n partitions" || no "$disk has $n partitions"
[ -e /data/library/MANIFEST.sha256 ] && ok "library present (SSD fallback bind mount stays off)" || no "no /data/library/MANIFEST.sha256"
[ -f /var/lib/lantern/identity-done ] && ok "identity-done (no host-key or machine-id regen)" || no "no /var/lib/lantern/identity-done"
sudo -n test -s /etc/ssh/ssh_host_ed25519_key && ok "host key present" || no "host key missing or empty"
id=$(lsblk -dno PTUUID "$disk")
n=$(lsblk -dnro PATH,PTUUID | awk -v d="$disk" -v id="$id" '$1!=d && $2==id' | wc -l)
[ "$n" = 0 ] && ok "disk ID $id is unique (newid will not re-roll the NVMe)" || no "another disk shares $id: newid WOULD re-roll the NVMe"
pu=$(lsblk -no PARTUUID /dev/nvme0n1p3)
grep -q "^PARTUUID=$pu /data " /etc/fstab && ok "fstab /data = PARTUUID=$pu" || no "fstab /data line is not PARTUUID=$pu"
c=${SSH_CLIENT%% *}; case $c in 10.10.10.*) ok "ssh from $c, inside 10.10.10.0/24";; *) no "ssh from $c: the firewall would refuse new ssh";; esac
sudo -n true && ok "passwordless sudo" || no "no passwordless sudo"
EOF
}

say "preflight gates (read-only)"
G=$(gates); echo "$G"
say "release: box has"; R 'cat /etc/lantern-release'
say "files (repo vs Pi: sha256, mode, owner)"
S=$(state); CHANGED=
while read -r src dst mode own; do
  if same "$src" "$dst" "$mode" "$own" "$S"; then echo "same    $dst"
  else echo "CHANGE  $dst  [Pi: $(grep " $dst\$" <<<"$S" | cut -d' ' -f2) -> $mode:$own]"; CHANGED="$CHANGED $src|$dst|$mode|$own"; fi
done < <(printf '%s\n%s\n%s\n' "$FILES" "$SSHD" "$NFT")
BADCHECK=
while read -r src dst mode own; do
  same "$src" "$dst" "$mode" "$own" "$S" && echo "same    $dst (check only)" || { echo "DIFFERS $dst (check only, never pushed)"; BADCHECK=1; }
done <<<"$CHECK"
R "test -e $DROPIN" && echo "REMOVE  $DROPIN (lines now in lantern-embed.service; effective config unchanged)" || echo "absent  $DROPIN"
R 'test -d /mnt/bak' && echo "exists  /mnt/bak" || echo "CREATE  /mnt/bak"
R 'test -s /etc/lantern/kolibri-admin.pw && test -s /etc/lantern/kolibri-provision.json' 2>/dev/null && echo "exists  /etc/lantern/kolibri-*" \
  || echo "CREATE  /etc/lantern/kolibri-admin.pw (600 root) + kolibri-provision.json (640 root:lantern), by lantern-firstboot.sh"
say "units"
for u in $UNITS nftables; do echo "$u $(R "systemctl is-enabled $u 2>/dev/null" || true) $(R "systemctl is-active $u 2>/dev/null" || true)"; done
say "packages (00-packages)"; MISS=$(missing_pkgs); echo "missing: ${MISS:-none}"
[ -z "${MISS// /}" ] || echo "  -> offline: --fetch-debs (lima VM, after the 1.0.1 build), then --apply-debs; $(ls "$DEBS"/*.deb 2>/dev/null | wc -l | tr -d ' ') .debs staged now"
say "sshd -T (now)"; R 'sudo -n sshd -T' | grep -E '^(passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|permitrootlogin) '
echo "no-key client is offered: $(methods)"
say "nft ruleset (now)"; R 'sudo -n nft list ruleset' || true
say "nft -c on the 1.0.1 ruleset (check only, commits nothing)"
R 'sudo -n nft -c -f -' < "$F/nftables.conf" && echo "nft -c OK" || echo "nft -c FAILED"
say "Kolibri"
FAC=$(curl -s -m 15 "http://$IP:8081/api/public/v1/facility/" || true); echo "facilities: $FAC"
echo "root lands on: $(curl -sL -m 30 -o /dev/null -w '%{url_effective}' "http://$IP:8081/" || true)"
say "diffs (Pi -> repo)"
for e in $CHANGED; do IFS='|' read -r src dst mode own <<<"$e"
  case $dst in */pagefind) echo "--- $dst: binary, hash differs";; *) diff -u --label "Pi:$dst" --label "repo:$src" <(R "sudo -n cat $dst 2>/dev/null" </dev/null || true) "$src" || true;; esac
done

verify() {
  say "verify (D5 plan step 13 spot checks)"
  R 'sudo -n sshd -T' | grep -E '^(passwordauthentication|kbdinteractiveauthentication|permitrootlogin) '
  echo "no-key client is offered: $(methods)   (want: publickey only)"
  R 'sudo -n nft list ruleset'
  echo "kolibri root lands on: $(curl -sL -m 30 -o /dev/null -w '%{url_effective}' "http://$IP:8081/" || true)   (want: not /setup/)"
  echo "kolibri facilities: $(curl -s -m 15 "http://$IP:8081/api/public/v1/facility/" || true)"
  R 'sudo -n stat -c "%n %a %U:%G %s bytes" /etc/lantern/kolibri-admin.pw /etc/lantern/kolibri-provision.json' || true
  R 'ls -l /opt/lantern/lantern-write-card.sh /opt/lantern/copy-the-library.html; test -d /mnt/bak && echo "/mnt/bak present"' || true
  echo "image-release.txt (footer reads IMAGE=):"; curl -s -m 10 -H "$H" "http://$IP/image-release.txt" || true
  R "systemctl is-active $UNITS nftables | paste -sd' '" || true
  R 'systemctl --failed --no-legend' || true
  echo "library $(code -H "$H" "http://$IP/")  kiwix $(code "http://$IP:8080/")  kolibri $(code "http://$IP:8081/")  semantic $(code -H "$H" "http://$IP/semantic?q=water&limit=1")"
  echo "next: bash deploy/live_test.sh      (expect only the router DNS row to FAIL, X2a)"
  echo "      bash tests/t6_box.sh      (restart matrix; run when T2 is idle)"
  echo "      FIXES #151 #152 #202 rows; PTUUIDs after card writes (#204)"
}

if [ "$MODE" = --dry-run ]; then verify; say "DRY RUN: nothing changed on the Pi"; exit 0; fi

# ════════════════════════════ --apply ════════════════════════════
say "APPLY $STAMP"
grep -q '^FAIL' <<<"$G" && die "a preflight gate failed (above)"
[ -z "$BADCHECK" ] || die "authorized_keys or the eth0 profile differ from the repo: settle that by hand first"
R 'sudo -n nft -c -f -' < "$F/nftables.conf" >/dev/null || die "nft -c rejects the 1.0.1 ruleset"
fresh || die "a fresh key-only login fails before any change"

say "backup -> $BK"
R "sudo -n bash -s $BK $ALL $DROPIN" <<'EOF'
bk=$1; shift; mkdir -p "$bk"
for f; do if [ -e "$f" ]; then cp -a --parents "$f" "$bk/"; else echo "$f" >> "$bk/ABSENT.before"; fi; done
nft list ruleset > "$bk/nft-ruleset.before"; sshd -T > "$bk/sshd-T.before"
systemctl list-unit-files --state=enabled --no-legend > "$bk/units-enabled.before"
cat > "$bk/RESTORE.txt" <<R2
Undo this run: sudo cp -a $bk/etc $bk/opt $bk/usr $bk/home / 2>/dev/null; sudo xargs rm -f < $bk/ABSENT.before
sudo systemctl daemon-reload; sudo systemctl reload ssh; sudo systemctl restart kolibri nginx
firewall: sudo nft flush ruleset; sudo systemctl disable nftables  (the v5 box ran with none)
R2
echo "backed up $(find "$bk" -type f | wc -l) files"
EOF
R "mkdir -p $STG"

say "files"
RELOAD=; RESTART=; KOLI=; i=0
for e in $CHANGED; do IFS='|' read -r src dst mode own <<<"$e"
  case $dst in /etc/ssh/*|/etc/nftables.conf) continue;; esac
  i=$((i+1)); R "cat > $STG/$i" < "$src"
  R "sudo -n install -D -m $mode -o $own -g $own $STG/$i $dst"; echo "installed $dst"
  case $dst in
    /etc/systemd/system/*) RELOAD=1;;
    /etc/nginx/*) R 'sudo -n nginx -t && sudo -n systemctl reload nginx' || die "nginx -t failed: restore $dst from $BK";;
    */mcp_server.py) RESTART="$RESTART lantern-mcp";;
    */lantern-voice.py) RESTART="$RESTART lantern-voice";;
  esac
  case $dst in */kolibri.service) KOLI=1;; */kiwix.service) RESTART="$RESTART kiwix";; */lantern-mcp.service) RESTART="$RESTART lantern-mcp";; */lantern-voice.service) RESTART="$RESTART lantern-voice";; esac
done
R "test -e $DROPIN" && { R "sudo -n rm -f $DROPIN && sudo -n rmdir --ignore-fail-on-non-empty ${DROPIN%/*}"; echo "removed $DROPIN"; RELOAD=1; } || true
[ -z "$RELOAD" ] || R 'sudo -n systemctl daemon-reload'
[ -z "$RESTART" ] || R "sudo -n systemctl restart $RESTART"
for u in $UNITS; do R "systemctl is-enabled -q $u" || { R "sudo -n systemctl enable $u"; echo "enabled $u"; }; done
R 'test -d /mnt/bak || sudo -n install -d -m 755 /mnt/bak'

say "Kolibri provisioning (#151)"
# lantern-firstboot.sh is the image's own path to /etc/lantern/*. Gates re-checked first: with them green its
# identity, newid, partition, fstab and SSD-fallback branches are all no-ops on this box (report, section 3).
grep -q '^FAIL' <<<"$(gates)" && die "gates changed since preflight"
# 10-30 first apply: its JSON lacked learner_can_edit_password=false, and Kolibri refuses informal + no-password login without it
R 'sudo -n grep -q learner_can_edit_password /etc/lantern/kolibri-provision.json 2>/dev/null || sudo -n rm -f /etc/lantern/kolibri-provision.json'
R 'sudo -n /opt/lantern/lantern-firstboot.sh' || die "lantern-firstboot.sh failed"
R 'sudo -n test -s /etc/lantern/kolibri-admin.pw && sudo -n test -s /etc/lantern/kolibri-provision.json' || die "firstboot did not write /etc/lantern/kolibri-*"
if ! grep -q '"name"' <<<"$(curl -s -m 15 "http://$IP:8081/api/public/v1/facility/" || true)"; then
  R 'sudo -n systemctl restart kolibri'   # kolibri.service now carries the provision file + DISABLE_PING
  for s in $(seq 1 36); do grep -q '"name"' <<<"$(curl -s -m 10 "http://$IP:8081/api/public/v1/facility/" || true)" && break; sleep 5; done
  grep -q '"name"' <<<"$(curl -s -m 10 "http://$IP:8081/api/public/v1/facility/" || true)" && echo "Kolibri provisioned" || {
    R 'sudo -n journalctl -u kolibri -n 40 --no-pager' | grep -i -e provision -e error || true
    # 10-30: a provision error makes Kolibri exit at every start, so the old unit (no provision file) goes back
    R "sudo -n cp -a $BK/etc/systemd/system/kolibri.service /etc/systemd/system/kolibri.service && sudo -n systemctl daemon-reload && sudo -n systemctl restart kolibri"
    die "Kolibri provisioning failed (above): old kolibri.service restored and restarted"; }
else echo "Kolibri already has a facility: provisioning skipped"
  [ -z "$KOLI" ] || { R 'sudo -n systemctl restart kolibri'; echo "kolibri restarted for its new unit (DISABLE_PING)"; }; fi

say "sshd key-only (#152)"
read -r src dst mode own <<<"$SSHD"
if same "$src" "$dst" "$mode" "$own" "$(state)"; then echo "drop-in already in place"
else
  fresh || die "fresh key-only login fails: not touching sshd"
  R "cat > $STG/sshd.conf" < "$src"
  R "sudo -n install -m 644 -o root -g root $STG/sshd.conf $dst"
  R 'sudo -n sshd -t' || { R "sudo -n rm -f $dst"; die "sshd -t rejected the drop-in (removed again)"; }
  # dead-man switch: unless cancelled below, the drop-in goes and sshd reloads in 5 minutes
  # 11-01: systemd-run mangled the ';' of a "sh -c" command line (the 10-30 nft rollback ran nothing); a script file in $BK instead (not $STG: the ssh session has its own /tmp)
  printf 'rm -f %s\nsystemctl reload ssh\n' "$dst" | R "sudo -n tee $BK/sshd-rb.sh >/dev/null"
  R "sudo -n systemd-run --quiet --unit=d5-sshd-rb-$STAMP --on-active=300 /bin/sh $BK/sshd-rb.sh"
  R 'sudo -n systemctl reload ssh'; sleep 2
  M=$(methods)
  if fresh && [ -n "$M" ] && ! grep -q password <<<"$M"; then
    R "sudo -n systemctl stop d5-sshd-rb-$STAMP.timer"; echo "key login OK in a new connection; no-key client offered: $M"
  else
    R "sudo -n rm -f $dst && sudo -n systemctl reload ssh; sudo -n systemctl stop d5-sshd-rb-$STAMP.timer"
    die "new key login or password-off check failed ($M): drop-in removed, sshd as before"
  fi
fi

say "nftables (#152)"
read -r src dst mode own <<<"$NFT"
if same "$src" "$dst" "$mode" "$own" "$(state)" && R 'systemctl is-active -q nftables && systemctl is-enabled -q nftables && sudo -n nft list table inet lantern >/dev/null'; then
  echo "ruleset already loaded and enabled"
else
  R "cat > $STG/nftables.conf" < "$src"
  R "sudo -n nft -c -f $STG/nftables.conf" || die "nft -c failed"
  R "sudo -n install -m 755 -o root -g root $STG/nftables.conf $dst"
  # dead-man switch: unless cancelled, in 2 minutes the rules go, the unit is disabled and the old file returns
  printf 'nft flush ruleset\nsystemctl disable nftables\ncp -a %s/etc/nftables.conf /etc/nftables.conf\n' "$BK" | R "sudo -n tee $BK/nft-rb.sh >/dev/null"
  R "sudo -n systemd-run --quiet --unit=d5-nft-rb-$STAMP --on-active=120 /bin/sh $BK/nft-rb.sh"
  R 'sudo -n systemctl enable nftables && sudo -n systemctl restart nftables'; sleep 2
  L=$(code -H "$H" "http://$IP/"); K=$(code "http://$IP:8080/"); B=$(code "http://$IP:8081/"); Q=$(code -H "$H" "http://$IP/semantic?q=water&limit=1")
  echo "after load: library $L kiwix $K kolibri $B semantic(lo->mcp->embed) $Q"
  if fresh && [ "$L" = 200 ] && [ "${K:-000}" != 000 ] && [ "${B:-000}" != 000 ] && [ "$Q" = 200 ]; then
    R "sudo -n systemctl stop d5-nft-rb-$STAMP.timer"; echo "firewall kept"
  else
    R "sudo -n systemctl start d5-nft-rb-$STAMP.service; sudo -n systemctl stop d5-nft-rb-$STAMP.timer" || true
    die "new ssh or a library port failed under the new rules: rolled back (flushed, disabled, old file back)"
  fi
fi

R "rm -rf $STG"
verify
say "APPLY DONE. Backup and RESTORE.txt in $BK on the Pi. Missing packages: ${MISS:-none} (--fetch-debs, --apply-debs)"
