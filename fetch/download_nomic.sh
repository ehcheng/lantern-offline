#!/bin/bash
# R12: nomic-embed-text-v1.5 f16 GGUF (~274MB) for embedding sidecar
set -uo pipefail
cd "$(dirname "$0")/.."
DST=library/tools/models/nomic-embed-text-v1.5.f16.gguf
URL="https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF/resolve/main/nomic-embed-text-v1.5.f16.gguf"
LOG=logs/download_nomic.log
{
  echo "[$(date +%F\ %T)] start $URL"
  curl -L --fail --retry 3 -o "$DST.part" "$URL" && mv "$DST.part" "$DST"
  echo "[$(date +%F\ %T)] exit $?"
  # verify GGUF magic + size gate
  head -c4 "$DST" | xxd -p
  ls -l "$DST"
} >> "$LOG" 2>&1
