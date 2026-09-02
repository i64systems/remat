#!/bin/sh
# OB-5b S1 gate 1, POSITIVE CONTROL ON THE IDENTITY COMPARATOR.
#
# The ubatch control (gate1-ctl-ubatch.sh) proved the harness reports DIFFER on
# route.log, but the limb that carries the STOP-SHIP bar is gen-ids.txt, and a
# comparator that has only ever said IDENTICAL on that file has not been shown
# to be able to say anything else. This flips exactly one byte of a COPY of run
# A's gen-ids.txt and requires the same comparison to report DIFFER.
#
# No model, no runlock, no serve contact. Nothing under runs/ is modified: the
# mutant is written to a scratch path and deleted.
set -e
A=/root/ob5b1/runs/gen-120b-k8-a
T=/root/ob5b1/ctl-harness
mkdir -p "$T"
cp "$A/gen-ids.txt" "$T/gen-ids.mutant.txt"
echo "=== POSITIVE CONTROL ON THE IDENTITY COMPARATOR ==="
echo "original digest: $(sha256sum "$A/gen-ids.txt" | cut -d' ' -f1)"
echo "original first line: $(head -1 "$A/gen-ids.txt")"
# flip the last digit of the first token id: 168394 -> 168395
sed -i '1s/^168394$/168395/' "$T/gen-ids.mutant.txt"
echo "mutant first line:   $(head -1 "$T/gen-ids.mutant.txt")"
echo "mutant digest:   $(sha256sum "$T/gen-ids.mutant.txt" | cut -d' ' -f1)"
echo "byte counts: original $(stat -c %s "$A/gen-ids.txt")  mutant $(stat -c %s "$T/gen-ids.mutant.txt")"
if cmp -s "$A/gen-ids.txt" "$T/gen-ids.mutant.txt"; then
  echo "RESULT: IDENTICAL  *** THE COMPARATOR IS BROKEN: it cannot see a one-byte change ***"
  RC=1
else
  echo "RESULT: DIFFER     as required"
  cmp "$A/gen-ids.txt" "$T/gen-ids.mutant.txt" 2>&1 | head -1
  RC=0
fi
rm -rf "$T"
echo "scratch removed; run A untouched: $(sha256sum "$A/gen-ids.txt" | cut -d' ' -f1)"
echo "=== END POSITIVE CONTROL rc=$RC ==="
exit $RC
