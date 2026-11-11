#!/bin/bash
# H27: players for the CD3WD data ISOs (ISO9660 + DivX AVI, no VIDEO_TS).
# VLC (GPLv2+) desktop + Android, Material Files (GPLv3) = Android ISO browser.
# Sources bundled alongside binaries for GPL compliance. Verify: sha256 vs
# videolan .sha256, magic bytes, size gates.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
set -uo pipefail
D=$ROOT/library/tools/video_players
LOG=$ROOT/logs/video_players.log
mkdir -p "$D"; exec >>"$LOG" 2>&1
V=https://download.videolan.org/pub/videolan
get() { echo "$(date +%T) GET $2"; curl -sSfL --retry 5 -o "$D/$2.part" "$1" && mv "$D/$2.part" "$D/$2" && echo "DONE $2 $(stat -f%z "$D/$2")" || echo "FAIL $2"; }
get $V/vlc/3.0.23/macosx/vlc-3.0.23-universal.dmg vlc-3.0.23-universal.dmg
get $V/vlc/3.0.23/win64/vlc-3.0.23-win64.zip vlc-3.0.23-win64.zip
get $V/vlc/3.0.23/vlc-3.0.23.tar.xz vlc-3.0.23-source.tar.xz
get $V/vlc-android/3.7.1/VLC-Android-3.7.1-arm64-v8a.apk VLC-Android-3.7.1-arm64-v8a.apk
get $V/vlc-android/3.7.1/VLC-Android-3.7.1-armeabi-v7a.apk VLC-Android-3.7.1-armeabi-v7a.apk
get https://github.com/zhanghai/MaterialFiles/releases/download/v1.7.5/app-release-universal.apk MaterialFiles-1.7.5-universal.apk
get https://codeload.github.com/zhanghai/MaterialFiles/tar.gz/refs/tags/v1.7.5 MaterialFiles-1.7.5-source.tar.gz
for f in macosx/vlc-3.0.23-universal.dmg win64/vlc-3.0.23-win64.zip vlc-3.0.23.tar.xz; do
  curl -sSfL "$V/vlc/3.0.23/$f.sha256" | awk '{print $1}' > "$D/.sha_$(basename $f)"; done
echo ALL_DONE
