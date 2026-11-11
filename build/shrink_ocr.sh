#!/bin/bash
# Shrink OCR'd PDFs that ocrmypdf --force-ocr --oversample bloated (10-28x): gs /ebook recompress (150 dpi JPEG), text layer kept.
# Swap in only when the page count matches and pdftotext chars stay within 1%. Usage: bash shrink_ocr.sh <rel path>...
set -u; cd "$(dirname "$0")/.."; D=library/docs; S=${TMPDIR:-/tmp}/shrink; mkdir -p "$S"
for rel in "$@"; do f="$D/$rel"; o="$S/$(basename "$rel")"
  p0=$(pdfinfo "$f" 2>/dev/null | awk '/^Pages/{print $2}'); c0=$(pdftotext -enc UTF-8 "$f" - 2>/dev/null | tr -d '\f' | wc -c | tr -d ' '); s0=$(stat -f%z "$f")
  gs -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=pdfwrite -dPDFSETTINGS=/ebook -dCompatibilityLevel=1.5 -sOutputFile="$o" "$f" >/dev/null 2>&1 || { echo "FAIL gs $rel"; continue; }
  p1=$(pdfinfo "$o" 2>/dev/null | awk '/^Pages/{print $2}'); c1=$(pdftotext -enc UTF-8 "$o" - 2>/dev/null | tr -d '\f' | wc -c | tr -d ' '); s1=$(stat -f%z "$o")
  if [ "$p0" = "$p1" ] && [ "$c1" -ge $((c0*99/100)) ] && [ "$s1" -lt "$s0" ]; then mv "$o" "$f"; echo "OK $rel pages=$p1 chars=$c0->$c1 bytes=$s0->$s1"; else echo "FAIL verify $rel pages=$p0/$p1 chars=$c0/$c1 bytes=$s0/$s1"; rm -f "$o"; fi
done; echo "SHRINK DONE"
