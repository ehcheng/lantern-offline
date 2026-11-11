#!/bin/bash
# Sequential wget site mirrors. Idempotent: wget -N/--mirror re-checks, done sites skip fast.
BASE=$(cd "$(dirname "$0")/.." && pwd)
LOG=$BASE/logs/mirrors.log
UA="Mozilla/5.0"  # no spaces — $WGET expands unquoted; spaced UA becomes bogus URLs
WGET="wget --mirror --convert-links --adjust-extension --page-requisites --no-parent --no-verbose --wait=1 --random-wait -e robots=off --user-agent=$UA"

log() { echo "$(date +'%F %T') $*" >>"$LOG"; }

# Wait for any already-running NCHFP wget to finish before starting the queue
while pgrep -f 'wget.*nchfp' >/dev/null 2>&1; do sleep 60; done

mirror() { # mirror <name> <url> [extra wget args...]
  local name=$1 url=$2; shift 2
  if [ -e "$BASE/library/mirrors/$name/.done" ]; then log "SKIP $name"; return; fi
  log "START $name $url"
  $WGET "$@" -P "$BASE/library/mirrors/$name/" "$url" >>"$LOG" 2>&1
  local n; n=$(find "$BASE/library/mirrors/$name" -type f | wc -l | tr -d ' ')
  if [ "$n" -gt 50 ]; then
    touch "$BASE/library/mirrors/$name/.done"
    log "DONE $name files=$n size=$(du -sh "$BASE/library/mirrors/$name" | cut -f1)"
  else
    log "FAIL $name files=$n"
  fi
}

# mark nchfp done if its wget already finished
[ -d "$BASE/library/mirrors/nchfp" ] && [ "$(find "$BASE/library/mirrors/nchfp" -type f | wc -l)" -gt 10 ] \
  && touch "$BASE/library/mirrors/nchfp/.done" && log "DONE nchfp (pre-existing wget) size=$(du -sh "$BASE/library/mirrors/nchfp" | cut -f1)"

mirror nchfp https://nchfp.uga.edu/
mirror ready_gov https://www.ready.gov/
mirror journeytoforever https://journeytoforever.org/
mirror sheldonbrown https://www.sheldonbrown.com/
mirror hesperian https://en.hesperian.org/hhg/Special:AllPages --span-hosts --domains=en.hesperian.org,hesperian.org
mirror meshtastic_docs https://meshtastic.org/docs/
mirror aredn_docs https://docs.arednmesh.org/

# Firmware releases (latest only)
REL=$BASE/library/mirrors/meshtastic_aredn/releases
mkdir -p "$REL"
if [ ! -e "$REL/.done" ]; then
  log "START firmware releases"
  for repo in meshtastic/firmware aredn/aredn; do
    curl -sL "https://api.github.com/repos/$repo/releases/latest" \
      | grep -oE '"browser_download_url": *"[^"]+"' | cut -d'"' -f4 \
      | while read -r u; do
          f="$REL/$(echo "$repo" | tr / _)_$(basename "$u")"
          [ -e "$f" ] || curl -sL --retry 3 -o "$f" "$u" >>"$LOG" 2>&1
        done
  done
  touch "$REL/.done"
  log "DONE firmware releases size=$(du -sh "$REL" | cut -f1)"
fi
log "MIRRORS DRAINED"

# es.hesperian.org (R3, 2026-10-06): the first pass caught only the Spanish landing pages. Pull the chapter pages the two
# Spanish cover pages link (Donde no hay dentista, Nuevo Donde no hay doctor) plus requisites into the SAME hesperian tree.
# Marker is separate because hesperian/.done already exists. Afterwards run fix_mirror_links.py --strip-external and
# prune_mirrors.py on the es host only (fix_mirror_links over the whole tree re-prefixes data-src -> data-data-src).
ES=$BASE/library/mirrors/hesperian/es.hesperian.org/hhg
if [ ! -e "$BASE/library/mirrors/hesperian/.done_es" ]; then
  log "START hesperian_es chapters"
  { grep -ohE 'href="[^"]*Where_There_Is_No_Dentist:[^"#]*' "$ES/Donde_no_hay_dentista.html"
    grep -ohE 'href="[^"]*New_Where_There_Is_No_Doctor:[^"#]*' "$ES/Nuevo_Donde_no_hay_doctor.html"; } \
    | sed -E 's|href="(https?://es\.hesperian\.org)?/?(hhg/)?|https://es.hesperian.org/hhg/|; s|\.html$||' | sort -u > "$BASE/logs/hesperian_es_urls.txt"
  $WGET --no-recursive --input-file="$BASE/logs/hesperian_es_urls.txt" --span-hosts --domains=es.hesperian.org,hesperian.org \
    -P "$BASE/library/mirrors/hesperian/" >>"$LOG" 2>&1
  touch "$BASE/library/mirrors/hesperian/.done_es"
  log "DONE hesperian_es files=$(ls "$ES" | wc -l | tr -d ' ')"
fi
