#!/bin/sh
# verify.sh: check a copy of the library against its seal.
#   sh verify.sh                 checks the library this script sits in
#   sh verify.sh /data/library   checks that copy
#   sh verify.sh --full          also hashes every file (1.5 to 2 hours on the Pi)
# Prints the seal from VERSION.json, hashes MANIFEST.sha256, prints MATCH or MISMATCH.
# Exits 0 only when every check passed. Needs sha256sum (Debian) or shasum (macOS).
FULL=0; LIB=
for a in "$@"; do case "$a" in --full) FULL=1 ;; *) LIB=$a ;; esac; done
[ -n "$LIB" ] || LIB=$(dirname "$0")
LIB=$(cd "$LIB" 2>/dev/null && pwd) || { echo "no such directory: $LIB"; exit 2; }
[ -f "$LIB/VERSION.json" ] && [ -f "$LIB/MANIFEST.sha256" ] || { echo "not a library: $LIB has no VERSION.json or MANIFEST.sha256"; exit 2; }
if command -v sha256sum >/dev/null 2>&1; then SUM=sha256sum
elif command -v shasum >/dev/null 2>&1; then SUM="shasum -a 256"
else echo "need sha256sum or shasum"; exit 2; fi

field() { sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"\{0,1\}\([^\",}]*\).*/\1/p" "$LIB/VERSION.json" | head -1; }
echo "library:  $(field library)"
echo "sealed:   $(field sealed)"
echo "files:    $(field files)"
WANT=$(field manifest_sha256)
GOT=$($SUM "$LIB/MANIFEST.sha256" | cut -c1-64)
echo "manifest: $WANT  (sealed)"
echo "          $GOT  (this copy)"
if [ "$GOT" = "$WANT" ]; then echo "MATCH: MANIFEST.sha256 is the sealed manifest"; rc=0
else echo "MISMATCH: MANIFEST.sha256 differs from the seal in VERSION.json"; rc=1; fi

if [ "$FULL" = 1 ]; then
  # manifest lines read "library/<path>", so the check runs from the parent of a folder named library
  if [ "$(basename "$LIB")" = library ]; then WD=$(dirname "$LIB")
  else WD=$(mktemp -d) && ln -s "$LIB" "$WD/library"; fi
  echo "full check: hashing $(field files) files, 1.5 to 2 hours on the Pi ..."
  # one line per damaged or missing file; GNU prints "x: FAILED open or read" for a missing file, BSD only "No such file"
  OUT=$(cd "$WD" && $SUM -c --quiet "$LIB/MANIFEST.sha256" 2>&1 | awk -F': ' '{st=""} /: FAILED/ {p=$1; st="FAILED"} /No such file/ {p=$2; sub(/^ +/,"",p); st="MISSING"} st!="" && !(p in seen) {seen[p]=1; print p ": " st}')
  FAILS=$(printf '%s' "$OUT" | grep -c .)
  [ -z "$OUT" ] || printf '%s\n' "$OUT"
  if [ "$FAILS" = 0 ]; then echo "full check: all files OK"
  else echo "full check: $FAILS files damaged or missing (listed above); copy them back from the SSD"; rc=1; fi
  [ "$(basename "$LIB")" = library ] || rm -rf "$WD"
fi
[ "$rc" = 0 ] && echo "RESULT: PASS" || echo "RESULT: FAIL"
exit $rc
