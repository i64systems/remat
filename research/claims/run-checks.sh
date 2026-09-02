#!/bin/sh
# run-checks.sh - RELEASE SCOPE. The claims-checker acceptance bars that
# ship in this public cut, fail-fast. The full P07 acceptance (pitch-page
# regeneration and surface checks) runs in the private research repository
# where the pitch materials live; this script checks exactly what is here.
#
# Usage, from research/claims/:   sh run-checks.sh
# Exit 0 = every bar green. Any failure exits non-zero at that bar.

PY=${PY:-python3}
FAIL=0

echo "=== REMAT RELEASE CLAIMS ACCEPTANCE ==="
echo
echo "--- interpreter"
$PY -c "import sys; print(sys.version.split()[0])" || exit 2
echo
echo "--- LF and ASCII sweep over every file this cut ships here"
for f in claims_check.py run-checks.sh CLAIMS-OB5B-1.txt \
         fixtures/BAD-A-EMPTY-CAVEAT.txt \
         fixtures/BAD-B-INCOMPLETE-ROW.txt fixtures/BAD-C-CHERRYPICK.txt
do
  cr=`tr -dc '\r' < "$f" | wc -c`
  na=`LC_ALL=C grep -c '[^ -~	]' "$f"`
  echo "$f  cr_bytes=$cr  non_ascii_lines=$na"
done
echo
echo "=== BAR 1: THE TABLE OF RECORD IS ACCEPTED ==="
$PY claims_check.py CLAIMS-OB5B-1.txt
rc=$?
echo "exit=$rc"
[ $rc -eq 0 ] || { echo "BAR 1 FAILED"; exit 1; }
echo
echo "=== BAR 2: THREE MALFORMED FIXTURES, EACH REFUSED ==="
for f in fixtures/BAD-A-EMPTY-CAVEAT.txt fixtures/BAD-B-INCOMPLETE-ROW.txt \
         fixtures/BAD-C-CHERRYPICK.txt
do
  echo "--- $f"
  $PY claims_check.py "$f"
  rc=$?
  echo "exit=$rc"
  if [ $rc -eq 0 ]; then
    echo "BAR 2 FAILED: a malformed fixture was ACCEPTED"
    FAIL=1
  fi
  echo
done
[ $FAIL -eq 0 ] || exit 1
echo "=== NOTE ON CITATIONS ==="
echo "Commit-hash citations inside the claims table refer to the private"
echo "research repository this cut was exported from. They do not resolve"
echo "against this repository's history. The verification bridge is the"
echo "digest: every shipped file is pinned in /MANIFEST-SHA256.txt, and"
echo "the filed provisional's USPTO acknowledgement receipt carries"
echo "SHA-512 digests of the white paper and appendix bundles."
echo
echo "=== ALL SHIPPED BARS GREEN ==="
exit 0
