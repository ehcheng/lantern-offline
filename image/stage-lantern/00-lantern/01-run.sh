#!/bin/bash -e
# stage-lantern: bake the 5-service Lantern stack (BUILD_PLAN C2).
# NO IIAB — hand-rolled for image reproducibility.

KIWIX_VER=3.7.0-2
KOLIBRI_VER=0.19.5   # PINNED — must match the B4 import on the Mac (BUILD_STATE)

# /mnt/bak: the RUNBOOK's backup, rebuild and card-rewrite steps mount the
# backup SSD there (FIXES #202, a6 F2: images had an empty /mnt).
install -d "${ROOTFS_DIR}/opt/lantern" "${ROOTFS_DIR}/data" "${ROOTFS_DIR}/mnt/bak"

# ── kiwix-tools (static arm64) ──
curl -fsSL "https://download.kiwix.org/release/kiwix-tools/kiwix-tools_linux-aarch64-${KIWIX_VER}.tar.gz" \
  -o /tmp/kiwix-tools.tgz
tar -xzf /tmp/kiwix-tools.tgz -C /tmp
install -m 755 /tmp/kiwix-tools_linux-aarch64-${KIWIX_VER}/kiwix-serve  "${ROOTFS_DIR}/usr/local/bin/"
install -m 755 /tmp/kiwix-tools_linux-aarch64-${KIWIX_VER}/kiwix-manage "${ROOTFS_DIR}/usr/local/bin/"

# ── kolibri, pinned, in its own venv ──
# Wheel cached on the VM once (piwheels truncated mid-download and failed the
# hash check). Pure-python wheel straight from pypi.
WHEEL_CACHE=/opt/lantern-build/kolibri-${KOLIBRI_VER}-py2.py3-none-any.whl
[ -f "$WHEEL_CACHE" ] || pip3 download --no-deps --dest /opt/lantern-build \
  --index-url https://pypi.org/simple "kolibri==${KOLIBRI_VER}" --no-binary :none:
install -m 644 "$WHEEL_CACHE" "${ROOTFS_DIR}/tmp/$(basename "$WHEEL_CACHE")"
on_chroot <<EOF
python3 -m venv /opt/kolibri
/opt/kolibri/bin/pip install --no-cache-dir /tmp/kolibri-${KOLIBRI_VER}-py2.py3-none-any.whl
EOF
rm -f "${ROOTFS_DIR}"/tmp/kolibri-*.whl

# ── pagefind binary (linux-arm64, staged by build_boot_image.sh from fetch/fetch_all.py) ──
install -m 755 files/pagefind "${ROOTFS_DIR}/usr/local/bin/pagefind" 2>/dev/null || \
  echo "NOTE: pagefind binary not staged (run python3 fetch/fetch_all.py Pagefind before the build)"

# ── nginx: captive-portal vhosts (PRIMARY responder — router serves no HTTP) ──
install -m 644 files/nginx-lantern.conf "${ROOTFS_DIR}/etc/nginx/sites-available/lantern"
on_chroot <<EOF
ln -sf /etc/nginx/sites-available/lantern /etc/nginx/sites-enabled/lantern
rm -f /etc/nginx/sites-enabled/default
EOF

# ── MCP server (source of truth: server/mcp_server.py, copied into
# files/ at build time like pagefind) ──
install -m 644 files/mcp_server.py "${ROOTFS_DIR}/opt/lantern/mcp_server.py" 2>/dev/null || \
  echo "NOTE: mcp_server.py not staged (copy from server/mcp_server.py before build)"

# ── release stamp (written by build_boot_image.sh) ──
install -m 644 files/lantern-release "${ROOTFS_DIR}/etc/lantern-release"

# ── services ──
install -m 644 files/kiwix.service            "${ROOTFS_DIR}/etc/systemd/system/"
install -m 644 files/kolibri.service          "${ROOTFS_DIR}/etc/systemd/system/"
install -m 644 files/lantern-mcp.service      "${ROOTFS_DIR}/etc/systemd/system/"
install -m 644 files/lantern-embed.service    "${ROOTFS_DIR}/etc/systemd/system/"
install -m 644 files/avahi-lantern.service    "${ROOTFS_DIR}/etc/avahi/services/lantern.service"
install -m 644 files/lantern-voice.service    "${ROOTFS_DIR}/etc/systemd/system/"
install -m 755 files/lantern-voice.py         "${ROOTFS_DIR}/opt/lantern/lantern-voice.py"
install -m 644 files/lantern-discs.service    "${ROOTFS_DIR}/etc/systemd/system/"
install -m 755 files/lantern-discs.sh         "${ROOTFS_DIR}/opt/lantern/"
install -m 644 files/lantern-firstboot.service "${ROOTFS_DIR}/etc/systemd/system/"
install -m 755 files/lantern-firstboot.sh     "${ROOTFS_DIR}/opt/lantern/"
install -m 644 files/copy-the-library.html    "${ROOTFS_DIR}/opt/lantern/"
install -m 755 files/lantern-write-card.sh    "${ROOTFS_DIR}/opt/lantern/"   # a6 F10: replaces dd of=/dev/sda
on_chroot <<EOF
systemctl enable nginx kiwix kolibri lantern-mcp lantern-embed lantern-voice lantern-discs lantern-firstboot chrony avahi-daemon nftables
EOF

# ── sshd key-only + nftables (FIXES #152, D4-A). The router bridges eth0 onto
# the open Wi-Fi, so "wired-only by omission" (v3) never held (a8 F3, a6 F9).
# No ExecStartPre tricks (the v1/v2 iptables drop-in broke sshd): a plain
# sshd_config.d drop-in and the stock nftables.service. The build fails
# without the public key: key-only sshd with no key is a locked box.
[ -s files/lantern_ed25519.pub ] || { echo "files/lantern_ed25519.pub missing (build_boot_image.sh copies it from .keys/)"; exit 1; }
install -m 644 files/sshd-lantern.conf "${ROOTFS_DIR}/etc/ssh/sshd_config.d/lantern.conf"
install -m 755 files/nftables.conf     "${ROOTFS_DIR}/etc/nftables.conf"
install -d -m 700 "${ROOTFS_DIR}/home/lantern/.ssh"
install -m 600 files/lantern_ed25519.pub "${ROOTFS_DIR}/home/lantern/.ssh/authorized_keys"
on_chroot <<EOF
chown -R lantern:lantern /home/lantern/.ssh
EOF
# ── cmdline: strip the stock first-boot resizer. It would grow rootfs over
# the whole disk and leave lantern-firstboot no room for LANTERN (E1 finding).
# The stock step also gave each copy a fresh disk ID; lantern-firstboot.sh and
# lantern-write-card.sh now do that instead (FIXES #204, a6 F3).
sed -i 's| init=/usr/lib/raspberrypi-sys-mods/firstboot||' "${ROOTFS_DIR}/boot/firmware/cmdline.txt"
grep -q "init=" "${ROOTFS_DIR}/boot/firmware/cmdline.txt" && { echo "cmdline still has init="; exit 1; }

# ── hostname: mDNS library.local (TARGET_HOSTNAME is applied by the cached
# stage1 only on a clean build, so set it here too) ──
echo library > "${ROOTFS_DIR}/etc/hostname"
sed -i 's/^127\.0\.1\.1.*/127.0.1.1\tlibrary/' "${ROOTFS_DIR}/etc/hosts"

# ── eth0: DHCP plus a permanent 10.10.10.10/24 so a laptop cabled straight
# to the box (no router) reaches http://10.10.10.10 (RUNBOOK network plan) ──
install -m 600 files/lantern-eth0.nmconnection "${ROOTFS_DIR}/etc/NetworkManager/system-connections/"

# ── Pi 5 config: RTC + USB current ──
CONFIG="${ROOTFS_DIR}/boot/firmware/config.txt"
grep -q usb_max_current_enable "$CONFIG" || cat >> "$CONFIG" <<EOF
usb_max_current_enable=1
dtparam=rtc=on
EOF
