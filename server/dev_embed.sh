#!/bin/bash
# Dev embed server on :8091. Default CPU, 4 threads, the Pi's flags: query vectors then equal the Pi's bit for bit
# (round 10, the private test record Metal differs by up to 8.5e-4 in score and broke E7).
# MODE=gpu only for a bulk build_embeddings run (document vectors ship to the Pi, so the build box mode does not matter).
#   screen -dmS h37embed bash server/dev_embed.sh
cd "$(dirname "$0")/.." || exit 1
G="--gpu disable -ngl 0 -t 4"; [ "$MODE" = gpu ] && G=""
exec sh library/tools/llamafile/llamafile-0.10.6 --server --embedding -m library/tools/models/nomic-embed-text-v1.5.f16.gguf \
  --host 127.0.0.1 --port 8091 -c 2048 -b 2048 -ub 2048 $G
