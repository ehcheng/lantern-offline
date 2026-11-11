#!/bin/bash
# Khan Academy + preschool DivX .avi (CD3WD discs) -> H.264 480p MP4 for video.html / Kids.
# Input: the CD3WD 2015 disc ISOs (fix_cd3wd_isos.sh) mounted under M as ka_CD3WD_<disc>/ or ka_<disc>/
# (e.g. hdiutil attach -readonly -mountpoint "$M/ka_CD3WD_1103_JHS_MATH03" <iso>). The .avi list is
# logs/khan_avi.lst, made from M when missing. Resumable: skips existing non-empty mp4.
# Usage: M=/path/to/mounts bash khan_transcode.sh [jobs]   (in screen; log logs/khan_transcode.log)
# VENC picks the encoder: h264_videotoolbox (macOS, default) or libx264 (Linux).
cd "$(dirname "$0")/.."
J=${1:-4}; M=${M:?set M to the folder holding the mounted CD3WD discs}; VENC=${VENC:-h264_videotoolbox}
mkdir -p logs
[ -s logs/khan_avi.lst ] || find "$M"/ka_* -name '*.avi' > logs/khan_avi.lst
one() {
  src="$1"; rel="${src#$M/ka_CD3WD_}"           # 1103_JHS_MATH03/math03_2250MB/218340__ka_..._218340_.avi
  rel="${rel#$M/ka_}"                            # ka_1101 mount
  disc="${rel%%/*}"; rest="${rel#*/}"; stem="$(basename "$rest" .avi)"; sub="$(dirname "$rest")"
  case "$disc" in 100212*|100213*) top=preschool;; *) top=khan_academy;; esac
  clean=$(echo "$stem" | sed -E 's/^[0-9]+_+//; s/_[0-9]+_?$//; s/^(ka_)?//; s/_+/_/g; s/^_//; s/_$//')
  out="library/video/$top/$disc/$sub/$clean.mp4"
  [ -s "$out" ] && { echo "skip $out"; return; }
  mkdir -p "$(dirname "$out")"
  if ffmpeg -nostdin -hide_banner -loglevel error -y -i "$src" -vf "scale=-2:480" \
       -c:v "$VENC" -b:v 600k -c:a aac -b:a 96k -ac 2 -movflags +faststart "$out.part.mp4" \
     && mv "$out.part.mp4" "$out"; then echo "ok $out"; else rm -f "$out.part.mp4"; echo "FAIL $src"; fi
}
export -f one; export M VENC
echo "$(date +%T) start jobs=$J n=$(wc -l < logs/khan_avi.lst)"
xargs -P "$J" -I{} bash -c 'one "$1"' _ {} < logs/khan_avi.lst
echo "$(date +%T) KHAN_DONE ok=$(grep -c '^ok' logs/khan_transcode.log) fail=$(grep -c '^FAIL' logs/khan_transcode.log)"
