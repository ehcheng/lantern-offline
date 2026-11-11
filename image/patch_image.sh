#!/bin/bash
# Make image 1.0.5 from the tested 1.0.4 image by replacing the one stage file that changed since
# (kiwix.service, 58aee663) and the release stamp. Run INSIDE the lima VM as root:
#   limactl shell --workdir / lantern-build sudo bash /workspace/image/patch_image.sh
# Why not a pi-gen build: on 11-06 a fresh build pulled kernel 6.12.115 (the box and 1.0.4 run
# 6.12.109, never tested on the new one) and failed anyway (VM disk full in mkinitramfs).
set -euo pipefail
D=/workspace/image/deploy
SRC=$D/lantern-boot-1.0.4+g20333bf4.img
GIT=$(git -C /workspace log -1 --format=%h -- image/stage-lantern)
OUT=$D/lantern-boot-1.0.5+g$GIT.img
UNIT=/workspace/image/stage-lantern/00-lantern/files/kiwix.service
(cd $D && sha256sum -c "$(basename $SRC).sha256")
cp --sparse=always "$SRC" "$OUT"
L=$(losetup -fP --show "$OUT"); udevadm settle
M=$(mktemp -d); trap 'umount "$M" 2>/dev/null; losetup -d "$L"; rmdir "$M"' EXIT
mount "${L}p2" "$M"
echo "--- kiwix.service, image 1.0.4 vs repo:"; diff "$M/etc/systemd/system/kiwix.service" "$UNIT" || true
install -m 644 "$UNIT" "$M/etc/systemd/system/kiwix.service"
cat > "$M/etc/lantern-release" <<EOF
IMAGE=1.0.5
GIT=$GIT
BUILT=$(date -u +%FT%TZ)
HW=pi5-16g-nvme
LIBRARY_MIN=2026.09.27
PATCHED_FROM=1.0.4+g20333bf4
EOF
chmod 644 "$M/etc/lantern-release"; cat "$M/etc/lantern-release"
umount "$M"; e2fsck -fn "${L}p2" >/dev/null && echo "rootfs fsck clean"
losetup -d "$L"; rmdir "$M"; trap - EXIT
(cd $D && sha256sum "$(basename $OUT)" > "$(basename $OUT).sha256" && cat "$(basename $OUT).sha256")
echo "PATCH_IMAGE_DONE $OUT"
