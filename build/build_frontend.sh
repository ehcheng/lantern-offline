#!/bin/bash
# A7: full frontend pipeline (BUILD_PLAN). Fail loudly at every step.
# Uses whatever MANIFEST.sha256 is sealed — do NOT regen the manifest here.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== media titles (gen_index.resolve_titles overlays them)"
python3 build/gen_media_titles.py

echo "== gen_index (titles/shelves/plants/coastal + budget assert)"
python3 build/gen_index.py

echo "== places.js (map drive mode) + species README/CREDITS verdicts (plant_id drive mode)"
python3 build/gen_places.py
python3 build/gen_species_readme.py

echo "== covers (idempotent, skips existing)"
python3 build/gen_covers.py

echo "== pdftotext wrappers + pagefind index (build_pagefind runs gen_text.py)"
build/build_pagefind.sh

echo "== shelves + landing + runbook/skills"
python3 build/gen_shelves.py

echo "== triage"
python3 build/build_triage.py

echo "== verify gate"
python3 build/verify_frontend.py --pre-hash

echo "== hash-suffix app.css/app.js (LAST — touches every page)"
python3 build/hash_assets.py

echo "== re-verify after hash rewrite"
python3 build/verify_frontend.py

echo "BUILD_FRONTEND OK"
