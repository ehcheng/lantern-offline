#!/bin/bash
# A6: 640px derivatives beside originals as <name>.640.<ext>
set -u
n=0; skip=0
cd "$(dirname "$0")/.." || exit 1
for base in library/docs/plant_id library/docs/coastal_id; do
  find "$base" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) ! -name '*.640.*' | while read -r img; do
    ext="${img##*.}"; out="${img%.*}.640.$ext"
    [ -f "$out" ] && continue
    sips -Z 640 "$img" --out "$out" >/dev/null 2>&1 && echo "OK $out" || echo "FAIL $img"
  done
done
echo ALLDONE
