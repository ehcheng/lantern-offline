#!/usr/bin/env bash
# download_tools.sh — Tier-1 offline AI stack
# Idempotent: skips existing files. All output to tools.log.
# Budget: ~8-9 GB (well within 15 GB spec)
ROOT=$(cd "$(dirname "$0")/.." && pwd)
set -euo pipefail

TOOLS=$ROOT/library/tools
LOG=$ROOT/logs/tools.log
mkdir -p "$TOOLS"/{llamafile,models,piper,argos,whisper} "$ROOT/logs"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }
dl() {
  local url=$1 dest=$2 min_bytes=${3:-1048576}
  local name
  name=$(basename "$dest")
  if [[ -f "$dest" ]]; then
    local sz
    sz=$(stat -f%z "$dest" 2>/dev/null || stat -c%s "$dest" 2>/dev/null || echo 0)
    if (( sz >= min_bytes )); then
      log "SKIP $name ($sz bytes already present)"
      return 0
    else
      log "PARTIAL $name ($sz bytes) — re-downloading"
      rm -f "$dest"
    fi
  fi
  log "START $name"
  curl -fsSL --retry 3 --retry-delay 5 -o "$dest" "$url" 2>>"$LOG" && {
    local sz
    sz=$(stat -f%z "$dest" 2>/dev/null || stat -c%s "$dest" 2>/dev/null || echo 0)
    log "DONE $name ($sz bytes)"
  } || {
    log "FAIL $name — curl exited $?"
    return 1
  }
}
verify_gguf() {
  local f=$1
  local magic
  magic=$(xxd -p -l 4 "$f" 2>/dev/null || od -An -N4 -tx1 "$f" | tr -d ' \n')
  # GGUF magic: 47475546 (ASCII "GGUF")
  if [[ "$magic" == "47475546" ]]; then
    log "GGUF-OK $f"
  else
    log "GGUF-WARN $f magic=$magic (may still be valid if compressed)"
  fi
}

log "=== download_tools.sh START ==="

# ── 1. llamafile binary (runtime for all GGUF models on Mac/Pi) ──────────────
dl "https://github.com/mozilla-ai/llamafile/releases/download/0.10.6/llamafile-0.10.6" \
   "$TOOLS/llamafile/llamafile-0.10.6" \
   100000000
chmod +x "$TOOLS/llamafile/llamafile-0.10.6" 2>/dev/null || true

# whisperfile (bundled Whisper runner — same release)
dl "https://github.com/mozilla-ai/llamafile/releases/download/0.10.6/whisperfile-0.10.6" \
   "$TOOLS/whisper/whisperfile-0.10.6" \
   1000000
chmod +x "$TOOLS/whisper/whisperfile-0.10.6" 2>/dev/null || true

# ── 2. LLM models ─────────────────────────────────────────────────────────────
# Pi-class: Llama 3.2 3B Q4_K_M (~2 GB, fits in 4 GB RAM)
dl "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf" \
   "$TOOLS/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf" \
   1500000000
verify_gguf "$TOOLS/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

# Mac-class: Llama 3.1 8B Q4_K_M (~5 GB, good quality)
dl "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf" \
   "$TOOLS/models/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf" \
   4000000000
verify_gguf "$TOOLS/models/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
# the Llama community licenses must ship beside the models (LICENSES.md)
dl "https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_2/LICENSE" "$TOOLS/models/LICENSE-llama-3.2.txt" 1000
dl "https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_1/LICENSE" "$TOOLS/models/LICENSE-llama-3.1.txt" 1000

# ── 3. Argos Translate packages (EN↔ES) ───────────────────────────────────────
dl "https://argos-net.com/v1/translate-en_es-1_0.argosmodel" \
   "$TOOLS/argos/translate-en_es-1_0.argosmodel" \
   50000000
dl "https://argos-net.com/v1/translate-es_en-1_9.argosmodel" \
   "$TOOLS/argos/translate-es_en-1_9.argosmodel" \
   50000000

# ── 4. Piper TTS binaries ─────────────────────────────────────────────────────
# macOS Apple Silicon (serving box primary)
dl "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_macos_aarch64.tar.gz" \
   "$TOOLS/piper/piper_macos_aarch64.tar.gz" \
   10000000

# Linux ARM64 (Pi fallback)
dl "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz" \
   "$TOOLS/piper/piper_linux_aarch64.tar.gz" \
   10000000

# Extract if not already extracted
if [[ ! -d "$TOOLS/piper/piper_macos_aarch64" ]]; then
  log "EXTRACT piper_macos_aarch64.tar.gz"
  mkdir -p "$TOOLS/piper/piper_macos_aarch64"
  tar -xzf "$TOOLS/piper/piper_macos_aarch64.tar.gz" -C "$TOOLS/piper/piper_macos_aarch64" 2>>"$LOG" && log "DONE extract piper_macos_aarch64" || log "FAIL extract piper_macos_aarch64"
fi
if [[ ! -d "$TOOLS/piper/piper_linux_aarch64" ]]; then
  log "EXTRACT piper_linux_aarch64.tar.gz"
  mkdir -p "$TOOLS/piper/piper_linux_aarch64"
  tar -xzf "$TOOLS/piper/piper_linux_aarch64.tar.gz" -C "$TOOLS/piper/piper_linux_aarch64" 2>>"$LOG" && log "DONE extract piper_linux_aarch64" || log "FAIL extract piper_linux_aarch64"
fi

# ── 5. Piper voice models ──────────────────────────────────────────────────────
# en_US lessac medium (~63 MB)
dl "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" \
   "$TOOLS/piper/en_US-lessac-medium.onnx" \
   50000000
dl "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" \
   "$TOOLS/piper/en_US-lessac-medium.onnx.json" \
   100

# es_ES davefx medium (~63 MB)
dl "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx" \
   "$TOOLS/piper/es_ES-davefx-medium.onnx" \
   50000000
dl "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json" \
   "$TOOLS/piper/es_ES-davefx-medium.onnx.json" \
   100

# ── 6. Whisper STT — ggml-small.bin + whisper.cpp source ──────────────────────
# ggml-small.bin (~488 MB) — fits in budget
dl "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin" \
   "$TOOLS/whisper/ggml-small.bin" \
   400000000

# whisper.cpp source zip (for Pi compilation)
dl "https://api.github.com/repos/ggml-org/whisper.cpp/zipball/v1.9.4" \
   "$TOOLS/whisper/whisper.cpp-v1.9.4.zip" \
   1000000

log "=== download_tools.sh COMPLETE ==="
log "Final sizes:"
du -sh "$TOOLS"/*/ 2>/dev/null | tee -a "$LOG"
du -sh "$TOOLS" 2>/dev/null | tee -a "$LOG"
