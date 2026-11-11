#!/bin/bash
# fmt.py must FAIL truncated/corrupt copies and PASS the originals. Run WITHOUT the sandbox (kiwix on :8080, llamafile exec).
# Usage: bash tests/checks/fmt_selftest.sh
set -uo pipefail; cd "$(dirname "$0")/../.."
S=$(mktemp -d); trap 'rm -rf "$S"' EXIT
PDF=library/docs/cd3wd/2012/about_cd3wd/__ReadMe_cd3wd_20120723_new_release_.pdf
MP4=library/video/khan_academy/1101_PRIMARY_MATH/math01/math_01_arith_001_Basic_Addition.mp4
ZIM=library/zim/vikidia_es_all_nopic_2026-09.zim
GGUF=library/tools/models/nomic-embed-text-v1.5.f16.gguf
PF=$(ls library/_app/pagefind_dev/fragment/*.pf_fragment | head -1)
cut70() { head -c $(( $(stat -L -f %z "$1") * 7 / 10 )) "$1" > "$2"; }
mkdir -p "$S/zim"; cut70 "$PDF" "$S/t.pdf"; head -c $(( $(stat -L -f %z "$PDF") - 200 )) "$PDF" > "$S/t99.pdf"
cut70 "$MP4" "$S/t.mp4"; cut70 "$ZIM" "$S/zim/t.zim"; cut70 "$GGUF" "$S/t.gguf"; cut70 "$PF" "$S/t.pf_fragment"
cp "$ZIM" "$S/zim/$(basename "$ZIM")"; printf 'XXXX' | dd of="$S/zim/$(basename "$ZIM")" bs=1 seek=5000000 conv=notrunc 2>/dev/null   # same name as the catalog entry, 4 bytes flipped: MD5 must catch it
printf '<!doctype html><html>404</html>' > "$S/err.css"; printf '<html>' > "$S/err.whl"; : > "$S/empty.js"
python3 tests/checks/fmt.py "$S"/t.pdf "$S"/t99.pdf "$S"/t.mp4 "$S"/zim/t.zim "$S/zim/$(basename "$ZIM")" "$S"/t.gguf "$S"/t.pf_fragment "$S"/err.css "$S"/err.whl "$S"/empty.js "$PDF" "$MP4" "$ZIM" "$GGUF" "$PF" > "$S/out.csv" 2>&1
bad=0
while IFS=, read -r _ _ path st _; do
  case "$path" in "$S"/*) want=FAIL;; *) want=PASS;; esac
  [ "$st" = "$want" ] || { echo "WRONG: $(grep -F ",$path," "$S/out.csv" | cut -c1-200)"; bad=1; }
done < <(python3 -c "import csv,sys; [print(','.join(r[:4])) for r in csv.reader(open(sys.argv[1]))]" "$S/out.csv")
cut -c1-160 "$S/out.csv"
[ $bad = 0 ] && echo "fmt_selftest: OK (10 corrupt FAIL, 5 originals PASS)" || { echo "fmt_selftest: FAILED"; exit 1; }
