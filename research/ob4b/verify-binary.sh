#!/bin/sh
# OB4B-PARDEC-1 phase 1: section-level comparison of two ELF shared objects.
#
# Phase A of build-ob4b.sh compares whole-file sha256 and reported DIFFER. This
# script says WHERE. The bar the brief sets is that the unpatched rebuild
# reproduces the ob4 engine's .text before the patched build is trusted; a
# whole-file digest also carries link-time artefacts of the build DIRECTORY
# (RUNPATH), which are not code.
#
# usage: verify-binary.sh REF CAND
set -e
REF=$1
CAND=$2
W=/root/ob4b/secdiff
rm -rf $W; mkdir -p $W/a $W/b

echo "REF  $REF"
echo "CAND $CAND"
sha256sum "$REF" "$CAND"
ls -l "$REF" "$CAND"

SECS=$(readelf -S -W "$REF" | sed -n 's/^ *\[[ 0-9]*\] \(\.[^ ]*\).*/\1/p')

echo ""
printf '%-24s %-18s %-18s %s\n' SECTION REF CAND VERDICT
NDIFF=0
for s in $SECS; do
  objcopy --dump-section "$s=$W/a/x" "$REF"  /dev/null 2>/dev/null || continue
  objcopy --dump-section "$s=$W/b/x" "$CAND" /dev/null 2>/dev/null || continue
  A=$(sha256sum $W/a/x | cut -c1-16)
  B=$(sha256sum $W/b/x | cut -c1-16)
  if [ "$A" = "$B" ]; then
    V=SAME
  else
    V=DIFFER
    NDIFF=$((NDIFF+1))
  fi
  printf '%-24s %-18s %-18s %s\n' "$s" "$A" "$B" "$V"
done

echo ""
echo "sections differing: $NDIFF"
echo "--- RUNPATH (a property of the build directory, not of the code) ---"
readelf -d -W "$REF"  | grep -iE 'rpath|runpath' || true
readelf -d -W "$CAND" | grep -iE 'rpath|runpath' || true

echo "--- .text verdict (the bar) ---"
objcopy --dump-section .text=$W/a/t "$REF"  /dev/null
objcopy --dump-section .text=$W/b/t "$CAND" /dev/null
TA=$(sha256sum $W/a/t | cut -d" " -f1)
TB=$(sha256sum $W/b/t | cut -d" " -f1)
echo "  ref  .text sha256 $TA"
echo "  cand .text sha256 $TB"
if [ "$TA" = "$TB" ]; then
  echo "  .text: MATCH"
else
  echo "  .text: DIFFER"
fi
