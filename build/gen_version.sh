#!/bin/bash
# Write library/VERSION.json after a manifest run. CalVer label + the MANIFEST
# hash as the real identity. Excluded from the manifest itself (circular).
cd "$(dirname "$0")/.." || exit 1
M=library/MANIFEST.sha256
DAY=$(date +%Y.%m.%d)
PREV=$(python3 -c "import json;print(json.load(open('library/VERSION.json'))['library'])" 2>/dev/null || true)
# same-day reseal -> .1 .2 ...
case "$PREV" in "$DAY") V="$DAY.1";; "$DAY".*) V="$DAY.$(( ${PREV##*.} + 1 ))";; *) V="$DAY";; esac
cat > library/VERSION.json <<JSON
{"library": "$V",
 "files": $(wc -l < "$M" | tr -d ' '),
 "manifest_sha256": "$(shasum -a 256 "$M" | cut -c1-64)",
 "git": "$(git rev-parse --short HEAD)",
 "sealed": "$(date -u +%FT%TZ)"}
JSON
cat library/VERSION.json
