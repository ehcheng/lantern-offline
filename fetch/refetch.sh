#!/bin/bash
# refetch.sh <library-relative path>   (E5 re-fetch doctrine; see PROGRESS.md)
# Tries origin, then Wayback, then same-item alternates (archive.org metadata API) or the cd3wd ISOs.
# Every download lands in its own new empty directory under $TMPDIR and is gated there (size,
# magic, pdfinfo/qpdf/PIL/ffprobe, md5 differs from the damaged copy). It NEVER replaces the library copy: the caller
# edition-gates the staged file (pdftotext the copyright page vs MASTER_LIST) and installs it by hand.
# Logs one line per attempt to logs/refetch_<date>.log. Prints one RESULT line on stdout:
# path, STAGED|DEAD, source, size, pages, year, staged file. REFETCH_BAD_MD5="md5 ..." adds known-damaged md5s.
# Network hosts: archive.org, *.archive.org, web.archive.org, the mirror hosts, studio.learningequality.org.
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
P="${1:?usage: refetch.sh <library-relative path>}"
DEST="$ROOT/library/$P"
OLD="$DEST"
OLDSIZE=0; [ -f "$OLD" ] && OLDSIZE=$(wc -c < "$OLD" | tr -d ' ')
LOG="$ROOT/logs/refetch_$(date +%Y%m%d).log"
STAGE=$(mktemp -d "${TMPDIR:-/tmp}/refetch_$(date +%Y%m%d).XXXXXX") || exit 2   # fresh, empty
PART="$STAGE/$(basename "$P")"
BAD_MD5="${REFETCH_BAD_MD5:-} $( [ -f "$OLD" ] && md5 -q "$OLD")"
EXT="${P##*.}"; EXT=$(echo "$EXT" | tr A-Z a-z)
PAGES=-; YEAR=-
log() { printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$(date +%FT%T)" "$P" "$1" "$2" "$3" "$4" >> "$LOG"; }

# candidate list: "<source>\t<url-or-iso>" lines; also prints the archive.org md5 of the origin file if known
CANDS=$(python3 - "$ROOT" "$P" <<'PY'
import sys, json, os, urllib.parse
root, p = sys.argv[1], sys.argv[2]
q = lambda s: urllib.parse.quote(s, safe='/')
out = []
def wb(u): out.append(('wayback', 'https://web.archive.org/web/2/' + u))
if p.startswith('docs/survivor_library/'):
    name = p.split('docs/survivor_library/', 1)[1]
    files = {f['name']: f for f in json.load(open(root + '/logs/survival_library_files.json'))['files']}
    if name in files:
        u = 'https://archive.org/download/survival.library/' + q(name)
        out.append(('origin', u)); wb(u); print('MD5\t' + files[name].get('md5', ''))
    else: print('MD5\t'); print('NOTE\tnot in survival.library metadata', file=sys.stderr)
    stem = os.path.splitext(os.path.basename(name))[0].lower()
    for n in files:
        if n != name and n.lower().endswith('.pdf') and stem in n.lower():
            out.append(('alt', 'https://archive.org/download/survival.library/' + q(n)))
elif p.startswith('docs/cd3wd/2012/'):
    name = os.path.basename(p)
    files = {f['name'] for f in json.load(open(root + '/logs/cd3wd12_files.json'))['files']}
    hits = [n for n in files if n.endswith('/' + name)]
    for n in hits:
        u = 'https://archive.org/download/CD3WD12/' + q(n); out.append(('origin', u)); wb(u)
    out.append(('iso', name)); print('MD5\t')
elif p.startswith('mirrors/'):
    rest = p.split('/', 2)[2]; u = 'https://' + rest
    out.append(('origin', u)); wb(u); print('MD5\t')
elif p.startswith('kolibri_data/content/storage/'):
    u = 'https://studio.learningequality.org/' + p.split('kolibri_data/', 1)[1]
    out.append(('origin', u)); wb(u); print('MD5\t')
for s, u in out: print(s + '\t' + u)
PY
)
ORIGMD5=$(echo "$CANDS" | awk -F'\t' '$1=="MD5"{print $2}')

gate() {  # gate <file> -> sets VERDICT (PASS or reason), PAGES, YEAR
  local f="$1" sz; sz=$(wc -c < "$f" | tr -d ' '); SIZE=$sz
  case "$EXT" in jpg|jpeg|gif|png) ;;   # tiny icons are legitimate; PIL below is the real gate for images
    *) if [ "$sz" -le 1024 ]; then VERDICT="fail: size $sz <= 1KB"; return 1; fi ;; esac
  if [ "$OLDSIZE" -gt 0 ] && [ "$sz" -lt $((OLDSIZE / 2)) ]; then VERDICT="fail: size $sz < 50% of old $OLDSIZE"; return 1; fi
  local magic; magic=$(head -c 12 "$f" | xxd -p | tr -d '\n')
  case "$EXT" in
    pdf) [ "${magic:0:10}" = "255044462d" ] || { VERDICT="fail: no %PDF- header"; return 1; } ;;
    jpg|jpeg) [ "${magic:0:6}" = "ffd8ff" ] || { VERDICT="fail: no JPEG magic"; return 1; } ;;
    gif) [ "${magic:0:8}" = "47494638" ] || { VERDICT="fail: no GIF magic"; return 1; } ;;
    png) [ "${magic:0:16}" = "89504e470d0a1a0a" ] || { VERDICT="fail: no PNG magic"; return 1; } ;;
    mov|mp4) case "${magic:8:8}" in 66747970|6d6f6f76|6d646174|77696465) ;; *) VERDICT="fail: no ftyp/moov atom"; return 1 ;; esac ;;
  esac
  case "$EXT" in
    pdf)
      pdfinfo "$f" > "$f.info" 2>/dev/null || { VERDICT="fail: pdfinfo cannot open"; return 1; }
      PAGES=$(awk '/^Pages:/{print $2}' "$f.info"); rm -f "$f.info"
      qpdf --check "$f" > /dev/null 2>&1; local rc=$?
      [ $rc -eq 0 ] || [ $rc -eq 3 ] || { VERDICT="fail: qpdf --check rc $rc"; return 1; }
      YEAR=$(pdftotext -l 5 "$f" - 2>/dev/null | grep -oE '\b(1[5-9]|20)[0-9]{2}\b' | sort | uniq -c | sort -rn | head -3 | awk '{printf "%s%s", (NR>1?"/":""), $2}')
      [ -n "$YEAR" ] || YEAR="none-in-first-5pp" ;;
    jpg|jpeg|gif|png)
      python3 -c "import sys; sys.path.insert(0,'$ROOT/tests/checks'); from fmt import c_img; print(c_img(sys.argv[1]))" "$f" > /dev/null 2>"$f.err" \
        || { VERDICT="fail: PIL $(tail -1 "$f.err" | cut -c1-120)"; rm -f "$f.err"; return 1; }; rm -f "$f.err" ;;
    mov|mp4)
      python3 -c "import sys; sys.path.insert(0,'$ROOT/tests/checks'); from fmt import c_media; print(c_media(sys.argv[1]))" "$f" > /dev/null 2>"$f.err" \
        || { VERDICT="fail: ffprobe $(tail -1 "$f.err" | cut -c1-120)"; rm -f "$f.err"; return 1; }; rm -f "$f.err" ;;
  esac
  case " $BAD_MD5 " in *" $(md5 -q "$f") "*) VERDICT="fail: md5 identical to a known-damaged copy"; return 1 ;; esac
  VERDICT=PASS; return 0
}

finish() {  # finish <source>
  printf 'RESULT\t%s\tSTAGED\t%s\t%s\t%s\t%s\t%s\n' "$P" "$1" "$SIZE" "$PAGES" "$YEAR" "$PART"; exit 0
}

[ -n "$CANDS" ] || { log none - - "no origin rule for this path"; printf 'RESULT\t%s\tDEAD\t-\t-\t-\t-\n' "$P"; exit 1; }
LASTSRC=-
while IFS=$'\t' read -r SRC URL; do
  [ "$SRC" = MD5 ] && continue
  LASTSRC="$SRC: $URL"
  rm -f "$PART"
  if [ "$SRC" = iso ]; then
    # the file came from the CD3WD DVD images; mount each read-only and look for it
    found=
    for iso in "$ROOT"/library/docs/cd3wd/2012_dvd/*.iso; do
      [ -f "$iso" ] || continue
      mp=$(hdiutil attach -nobrowse -readonly -mountpoint "${TMPDIR:-/tmp}/cd3wd_mnt_$$" "$iso" 2>/dev/null | awk -F'\t' 'END{print $NF}' | sed 's/^ *//')
      [ -d "$mp" ] || { log "iso $(basename "$iso")" - - "mount failed"; continue; }
      src=$(find "$mp" -name "$URL" -type f 2>/dev/null | head -1)
      if [ -n "$src" ]; then cp "$src" "$PART"; found="iso:$(basename "$iso")"; fi
      hdiutil detach "$mp" -quiet 2>/dev/null
      [ -n "$found" ] && break
    done
    [ -n "$found" ] || { log iso - - "not on any ISO"; continue; }
    if gate "$PART"; then log "$found" - "$SIZE" "PASS pages=$PAGES year=$YEAR"; finish "$found"; fi
    log "$found" - "$SIZE" "$VERDICT"; continue
  fi
  if [ "$SRC" = origin ] && [ -n "$ORIGMD5" ] && [ -f "$OLD" ] && [ "$(md5 -q "$OLD" 2>/dev/null || md5sum "$OLD" | cut -d' ' -f1)" = "$ORIGMD5" ]; then
    log "origin $URL" - "$OLDSIZE" "skip: archive.org md5 $ORIGMD5 identical to the damaged local copy"; continue
  fi
  HTTP=$(curl -sSL --retry 3 --retry-delay 5 --retry-connrefused --connect-timeout 30 --max-time 3600 -A 'Mozilla/5.0 (offline-survival refetch)' -o "$PART" -w '%{http_code}' "$URL" 2>"$PART.err"); rc=$?
  if [ $rc -ne 0 ]; then
    log "$SRC $URL" "$HTTP" "$( [ -f "$PART" ] && wc -c < "$PART" | tr -d ' ' || echo 0)" "curl rc $rc: $(head -c 120 "$PART.err" | tr '\n' ' ')"; rm -f "$PART" "$PART.err"; continue
  fi
  rm -f "$PART.err"
  [ "$HTTP" = 200 ] || { log "$SRC $URL" "$HTTP" "$(wc -c < "$PART" | tr -d ' ')" "http $HTTP"; rm -f "$PART"; continue; }
  if gate "$PART"; then log "$SRC $URL" "$HTTP" "$SIZE" "PASS pages=$PAGES year=$YEAR"; finish "$SRC"; fi
  log "$SRC $URL" "$HTTP" "$SIZE" "$VERDICT"; rm -f "$PART"
done <<< "$CANDS"
rm -f "$PART"
printf 'RESULT\t%s\tDEAD\t%s\t-\t-\t-\n' "$P" "$LASTSRC"; exit 1
