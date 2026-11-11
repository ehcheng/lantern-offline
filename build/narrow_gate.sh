#!/bin/bash
# L7 #218 narrow-text render check over the es and en Hesperian trees, with the round-9 #248 sliver check (a run of 3 or
# fewer characters a line with a mid-word break fails; SLIVER lines name the page) and the round-10 #262 off-screen check (text or a
# placed label left of 0 or past 390 px fails; OFF lines name the page and print off_fail=). Needs Chrome, so no sandbox.
# Usage: T=r34 bash build/narrow_gate.sh   (exit 1 on any check FAIL or page error)
cd "$(dirname "$0")/.."; T=${T:-r31}; out=logs/narrow_$T.log; : > $out; rc=0
for g in es en; do
  python3 build/fix_l7_narrow.py ${TMPDIR:-/tmp}/narrow_${T}_$g.jsonl \
    $PWD/library/mirrors/hesperian/$g.hesperian.org/hhg --check >> $out 2>&1 || rc=1
done
grep -E '^(fix_l7_narrow|  SLIVER|  OFF)' $out; echo "narrow rc=$rc"; exit $rc
