#!/bin/bash
# Dev kiwix-serve on the build machine with every ZIM in library/zim, port 8080 (search chips, the Ask page,
# build/fetch_kiwix_catalog.sh). kiwix-tools comes from python3 fetch/fetch_all.py kiwix-tools.
# Run: screen -dmS kiwixdev bash server/serve_kiwix_dev.sh
cd "$(dirname "$0")/.."
case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) P=macos-arm64 ;;
  Linux-aarch64|Linux-arm64) P=linux-aarch64 ;;
  Linux-x86_64) P=linux-x86_64 ;;
  *) echo "no kiwix-tools build for $(uname -s)-$(uname -m)"; exit 1 ;;
esac
mkdir -p logs
exec "build/bin/kiwix-tools_$P-3.8.2/kiwix-serve" --port 8080 \
  library/zim/*.zim \
  > logs/kiwixdev.log 2>&1
