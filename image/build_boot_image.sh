#!/bin/bash
# Lantern golden boot image build (BUILD_PLAN C1). Runs INSIDE the lima VM
# (see lima-lantern.yaml) as root:  sudo bash /workspace/image/build_boot_image.sh
# Output: /workspace/image/deploy/lantern-boot-<LANTERN_VERSION>+g<sha>.img (+ .sha256)
set -euo pipefail

WORK=/opt/lantern-build
STAGE_SRC=/workspace/image/stage-lantern
DEPLOY=/workspace/image/deploy

[ "$(id -u)" = 0 ] || { echo "run as root (sudo)"; exit 1; }
[ -d "$STAGE_SRC" ] || { echo "missing $STAGE_SRC"; exit 1; }

# Apple Silicon has no 32-bit ARM mode; register qemu-arm emulation for
# pi-gen's armhf check. Non-persistent — re-register every run (self-heal).
if ! arch-test armhf >/dev/null 2>&1; then
  printf ':qemu-arm:M::\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x28\x00:\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:/usr/bin/qemu-arm-static:FPOC' \
    > /proc/sys/fs/binfmt_misc/register 2>/dev/null || true
  arch-test armhf || { echo "armhf emulation unavailable"; exit 1; }
fi

mkdir -p "$WORK" "$DEPLOY"
cd "$WORK"
# master hardcodes ARCH=armhf. Attempt-10 fail: the `arm64` branch tracks
# CURRENT RaspiOS = trixie now — its stage2 wants rpi-swap/rpi-loop-utils/
# rpi-usb-gadget which don't exist in bookworm's archives. `bookworm-arm64`
# is the maintained bookworm 64-bit branch (= 2026-09-15-raspios-bookworm-arm64).
# Pinned to the bookworm-arm64 commit the 1.0.5 image was built from (2026-09-14)
# so a rebuild gets the same stages. To move the pin: update the hash, rebuild,
# boot the image on hardware.
PIGEN_COMMIT=850ee74bdd025e44975581efbbe8623bdd17bd1d
if [ ! -d pi-gen ]; then
  git init -q pi-gen
  git -C pi-gen fetch -q --depth 1 https://github.com/RPi-Distro/pi-gen.git "$PIGEN_COMMIT"
  git -C pi-gen checkout -q FETCH_HEAD
fi
[ "$(git -C pi-gen rev-parse HEAD)" = "$PIGEN_COMMIT" ] || \
  { echo "pi-gen is not at $PIGEN_COMMIT (rm -rf $WORK/pi-gen and rerun)"; exit 1; }
cd pi-gen

# Debian rotated its archive signing keys in 2025; Ubuntu 24.04's
# debian-archive-keyring predates the rotation, so the bootstrapped rootfs
# can't verify deb.debian.org. Fetch the CURRENT keyring from Debian and
# seed it into the rootfs before stage0's apt update.
KEYRING_DEB=debian-archive-keyring_2025.1_all.deb
KEYRING_SHA256=9ea7778e443144ca490668737a8ab22dd3e748bb99e805e22ec055abeb3c7fac
[ -f "$WORK/$KEYRING_DEB" ] || curl -fsSL \
  "http://deb.debian.org/debian/pool/main/d/debian-archive-keyring/$KEYRING_DEB" \
  -o "$WORK/$KEYRING_DEB"
echo "$KEYRING_SHA256  $WORK/$KEYRING_DEB" | sha256sum -c --quiet || \
  { rm -f "$WORK/$KEYRING_DEB"; echo "keyring sha256 mismatch"; exit 1; }
rm -rf "$WORK/keyring-extract"
dpkg-deb -x "$WORK/$KEYRING_DEB" "$WORK/keyring-extract"
cp "$WORK/keyring-extract/usr/share/keyrings/debian-archive-keyring.gpg" /usr/share/keyrings/
# THREE paths: trusted.gpg.d, /usr/share/keyrings/*.gpg, AND *.pgp —
# attempt 9 fail: pi-gen's debian.sources pins
# Signed-By: /usr/share/keyrings/debian-archive-keyring.pgp (.pgp!); the
# 2025.1 deb ships .pgp real files with .gpg symlinks, we'd seeded only the
# .gpg name so apt still hit NO_PUBKEY. All rotated keys ARE in 2025.1
# (verified 6ED0E7B8/78DBA3BC/F8D2585B/54404762/BDE6D2B9 present).
# Delete any previously injected line first (clone persists across attempts).
sed -i '/install -m 644 \/usr\/share\/keyrings\/debian-archive-keyring.gpg/d' \
  stage0/00-configure-apt/00-run.sh
sed -i '1a install -m 644 /usr/share/keyrings/debian-archive-keyring.gpg "${ROOTFS_DIR}/etc/apt/trusted.gpg.d/" && install -m 644 /usr/share/keyrings/debian-archive-keyring.gpg "${ROOTFS_DIR}/usr/share/keyrings/debian-archive-keyring.gpg" && install -m 644 /usr/share/keyrings/debian-archive-keyring.gpg "${ROOTFS_DIR}/usr/share/keyrings/debian-archive-keyring.pgp"' \
  stage0/00-configure-apt/00-run.sh
# hard-fail if the patched file changed (a moved pi-gen pin)
grep -q debian-archive-keyring.pgp stage0/00-configure-apt/00-run.sh || \
  { echo "stage0 patch target moved — update build_boot_image.sh"; exit 1; }

# our custom stage after the lite base (stage0-2)
rm -rf stage-lantern
cp -r "$STAGE_SRC" stage-lantern
# the builder's own ssh public key (gitignored .keys/, never in the repo): the box is key-only, so a build without it
# would be a locked box. Make one with: ssh-keygen -t ed25519 -f .keys/lantern_ed25519
[ -s /workspace/.keys/lantern_ed25519.pub ] || { echo ".keys/lantern_ed25519.pub missing (ssh-keygen -t ed25519 -f .keys/lantern_ed25519)"; exit 1; }
install -m 644 /workspace/.keys/lantern_ed25519.pub stage-lantern/00-lantern/files/lantern_ed25519.pub
# pagefind for on-box reseals (fetched by fetch/fetch_all.py)
PF=/workspace/build/bin/pagefind/linux-arm64/pagefind
[ -x "$PF" ] || { echo "$PF missing: run python3 fetch/fetch_all.py Pagefind on the host first"; exit 1; }
install -m 755 "$PF" stage-lantern/00-lantern/files/pagefind
# release stamp -> /etc/lantern-release (01-run.sh installs it). LANTERN_VERSION
# from the host wrapper; GIT = repo head the stage files came from.
VER=${LANTERN_VERSION:-0.0.0-dev}
GIT=$(git -C /workspace rev-parse --short HEAD 2>/dev/null || echo unknown)
cat > stage-lantern/00-lantern/files/lantern-release <<EOF
IMAGE=$VER
GIT=$GIT
BUILT=$(date -u +%FT%TZ)
HW=pi5-16g-nvme
LIBRARY_MIN=${LANTERN_LIBRARY_MIN:-2026.09.27}
EOF
# skip lite-image export of stage2; export ours instead
rm -f stage2/EXPORT_IMAGE
touch stage-lantern/EXPORT_IMAGE

cat > config <<'EOF'
IMG_NAME=lantern-boot-v1
RELEASE=bookworm
ARCH=arm64
DEPLOY_COMPRESSION=none
STAGE_LIST="stage0 stage1 stage2 stage-lantern"
ENABLE_SSH=1
FIRST_USER_NAME=lantern
TARGET_HOSTNAME=library
FIRST_USER_PASS=lantern-setup
DISABLE_FIRST_BOOT_USER_RENAME=1
TIMEZONE_DEFAULT=${LANTERN_TZ:-Etc/UTC}
EOF

./build.sh
rm -f stage-lantern/00-lantern/files/lantern_ed25519.pub
OUT="$DEPLOY/lantern-boot-${VER}+g${GIT}.img"
cp -v deploy/*.img "$OUT"
sha256sum "$OUT" | sed "s#$DEPLOY/##" > "$OUT.sha256"
echo "DONE: $(ls -lh "$OUT")"
