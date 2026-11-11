#!/bin/bash
# D1: copy the library onto a unit's LANTERN partition and verify it.
#   make_data.sh /Volumes/LANTERN        (or any mounted target root)
# rsync -aL dereferences the library/* symlinks (bulk dirs live in
# the content folder). Budget 70-90 min/unit over USB3.
# Verify: file count vs MANIFEST, 20 spot-hashes, landing/triage link check.
# (kiwix catalog curl runs on the booted unit, not here — see RUNBOOK.)
set -euo pipefail
DST=${1:?usage: make_data.sh <mounted-LANTERN-root>}
SRC="$(cd "$(dirname "$0")/.." && pwd)/library"

[ -d "$DST" ] || { echo "FAIL: $DST not mounted"; exit 1; }

echo "== rsync (dereference symlinks) $SRC/ -> $DST/"
rsync -aL --info=progress2 --delete --exclude .DS_Store "$SRC/" "$DST/"

echo "== verify: file count vs manifest"
want=$(wc -l < "$DST/MANIFEST.sha256" | tr -d ' ')
have=$(find "$DST" -type f ! -name 'MANIFEST.sha256' ! -name '.DS_Store' ! -name 'STRIPPED.txt' | wc -l | tr -d ' ')
echo "manifest=$want on-disk=$have"
if [ -f "$DST/STRIPPED.txt" ]; then
  echo "(stripped unit: $(wc -l < "$DST/STRIPPED.txt") removed files expected missing)"
elif [ "$want" != "$have" ]; then
  echo "FAIL: count mismatch"; exit 1
fi

echo "== verify: 20 random spot-hashes"
python3 - "$DST" <<'PY'
import random, sys
lines = open(f"{sys.argv[1]}/MANIFEST.sha256").read().splitlines()
open("/tmp/lantern_spot20.txt", "w").write("\n".join(random.sample(lines, 20)) + "\n")
PY
# manifest paths start with library/ — check from the parent of a symlink
ln -sfn "$DST" /tmp/lantern_verify_root/library 2>/dev/null || {
  mkdir -p /tmp/lantern_verify_root && ln -sfn "$DST" /tmp/lantern_verify_root/library; }
(cd /tmp/lantern_verify_root && shasum -a 256 -c /tmp/lantern_spot20.txt)

echo "== verify: landing + triage links resolve on target"
python3 - "$DST" <<'PY'
import html, os, re, sys, urllib.parse
root = sys.argv[1]
bad = 0
for page in ("index.html", "triage.html"):
    src = open(os.path.join(root, page), encoding="utf-8", errors="replace").read()
    for raw in re.findall(r"""(?:href|src)=["']([^"']+)["']""", src):
        u = html.unescape(raw)
        if u.startswith(("http", "//", "mailto:", "#", "javascript:", "data:")) or "${" in u:
            continue
        p = urllib.parse.unquote(u.split("?")[0].split("#")[0])
        if p and not os.path.exists(os.path.join(root, p)):
            print("BROKEN", page, u[:100]); bad += 1
sys.exit(1 if bad else print("links OK") or 0)
PY

echo "D1 MAKE_DATA OK — boot the unit and curl the kiwix catalog to finish"
