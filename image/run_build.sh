#!/bin/bash
# Host-side wrapper: run pi-gen build inside lima VM, log to file. Run via screen.
cd "$(dirname "$0")/.."
LANTERN_VERSION=${LANTERN_VERSION:-1.0.0}
LOG=image/logs/build_${LANTERN_VERSION}.log
{
  echo "=== build $LANTERN_VERSION start $(date)"
  # fresh stage-lantern + export (stage0-2 rootfs cache kept)
  limactl shell lantern-build sudo bash -c 'rm -rf /opt/lantern-build/pi-gen/work/lantern-boot-v1/stage-lantern /opt/lantern-build/pi-gen/work/lantern-boot-v1/export-image /opt/lantern-build/pi-gen/deploy/*'
  limactl shell lantern-build sudo env LANTERN_VERSION=$LANTERN_VERSION bash /workspace/image/build_boot_image.sh
  echo "=== build $LANTERN_VERSION exit $? $(date)"
} > "$LOG" 2>&1
