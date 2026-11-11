#!/bin/bash
# Download argostranslate + deps as wheels per platform/python for offline install.
# Usage: bash fetch/argos_wheels.sh  (log: logs/argos_wheels.log)
set -u
OUT=library/tools/argos/wheels
mkdir -p "$OUT"
PY=${PY:-python3}   # any python3 with pip: --platform/--python-version pick the wheels
for pv in 3.11 3.12; do
  for plat in "--platform=macosx_11_0_arm64 macos-arm64" "--platform=win_amd64 windows-x64" "--platform=manylinux_2_28_x86_64 --platform=manylinux2014_x86_64 --platform=manylinux_2_17_x86_64 linux-x86_64" "--platform=manylinux_2_28_aarch64 --platform=manylinux2014_aarch64 --platform=manylinux_2_17_aarch64 linux-aarch64"; do
    set -- $plat; name=${@: -1}; tag="${@:1:$#-1}"
    d="$OUT/$name-py$pv"
    echo "== $d"
    $PY -m pip download argostranslate \
      --dest "$d" --only-binary=:all: \
      $tag --python-version "$pv" \
      --extra-index-url https://download.pytorch.org/whl/cpu \
      --no-cache-dir 2>&1 | tail -3
    echo "RC=${PIPESTATUS[0]} $(du -sh "$d" | cut -f1)"
  done
done
echo ALLDONE
