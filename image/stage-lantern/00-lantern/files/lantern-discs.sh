#!/bin/bash
# Loop-mount every disc image in the library read-only under /srv/discs/<name>
# so nginx can serve the contents at /discs/ — no client-side ISO tool needed
# (iPhones, old Windows, Chromebooks). Idempotent; safe to re-run.
# ponytail: one flat directory, no per-shelf nesting; add it if a second ISO shelf appears.
set -u
mkdir -p /srv/discs
for iso in /data/library/docs/cd3wd/*/*.iso; do
  [ -e "$iso" ] || continue
  name=$(basename "$iso" .iso)
  mp=/srv/discs/$name
  mkdir -p "$mp"
  mountpoint -q "$mp" && continue
  mount -o loop,ro "$iso" "$mp" || echo "lantern-discs: cannot mount $iso" >&2
done
echo "lantern-discs: $(ls /srv/discs | wc -l) discs, $(mount | grep -c ' /srv/discs/') mounted"
