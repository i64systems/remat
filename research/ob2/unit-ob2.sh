#!/bin/sh
# OB-2 stage 2, step 2: the UNIT, under the RUNLOCK.
#
# K=16, code corpus, first 4096 tokens (4 chunks of 1024). Two limbs:
#
#  (a) IDENTITY. The 4-chunk run's identity artifact must be the exact prefix of
#      OB-1's banked 32-chunk fully-resident reference identity artifact for the
#      same corpus, and the run's route log must be the exact byte prefix of that
#      reference's route log (the log is written in graph order -- all 24 layers
#      of ubatch 0, then all 24 of ubatch 1 -- so a 4-ubatch run's log is the
#      first 24*4096 lines of a 32-ubatch run's log if and only if every routing
#      decision matched).
#
#  (b) SCHEDULE. The engine's resident-set trace must byte-match the committed
#      simulator's trace over the same prefix. Both sides are sorted by
#      (layer, boundary) first: the engine emits in graph order, the simulator
#      walks layer-major, so the sort is what makes two identical schedules into
#      two identical files. It reorders lines, never changes one.
set -e
OB2=/mnt/f/f32/openbob-wt/research-2/research/ob2
AC_CODE=/mnt/f/f32/stage/research/ob1/AC-CODE.txt
REF=/mnt/f/f32/stage/research/ob1/runs/res-code-a
OUT=/mnt/f/f32/stage/research/ob2/runs/unit-k16-code
LOCAL=/root/ob2/runs/unit-k16-code

mkdir -p "$OUT"

echo "########## UNIT: engine run (K=16, AC-CODE, 4 chunks = 4096 tokens) ##########"
sh "$OB2/locked-run.sh" unit-k16-code "$AC_CODE" 16 4 /root/ob2/unit-trace.txt
echo "########## UNIT: analysis (lock already released) ##########"

echo "--- (b1) sort both traces by (layer, boundary) ---"
sort -t, -k1,1n -k2,2n /root/ob2/unit-trace.txt > "$OUT/engine-trace.sorted.txt"
wc -l "$OUT/engine-trace.sorted.txt"

echo "--- (b2) simulator trace over the same prefix, from the banked reference route log ---"
python3 "$OB2/sim_trace.py" "$REF/route.log" 32 24 32768 16 256 "$OUT/sim-trace.sorted.txt" 4096

echo "--- (b3) BYTE COMPARE engine schedule vs simulator schedule ---"
if cmp "$OUT/engine-trace.sorted.txt" "$OUT/sim-trace.sorted.txt"; then
  echo "TRACE_MATCH=PASS (byte identical)"
else
  echo "TRACE_MATCH=FAIL"
  echo "--- first 10 differing lines ---"
  diff "$OUT/engine-trace.sorted.txt" "$OUT/sim-trace.sorted.txt" | head -20 || true
fi
sha256sum "$OUT/engine-trace.sorted.txt" "$OUT/sim-trace.sorted.txt"

echo "--- (a1) identity artifact prefix check ---"
python3 - "$LOCAL/identity.txt" "$REF/identity.txt" <<'PY'
import sys
run = open(sys.argv[1]).read().strip()
ref = open(sys.argv[2]).read().strip()
print("run_identity: %s" % run)
print("ref_prefix  : %s" % ref[:len(run)])
print("IDENTITY_PREFIX=%s" % ("PASS" if ref.startswith(run) and run else "FAIL"))
PY

echo "--- (a2) route log prefix check (24 layers x 4096 tokens = 98304 lines) ---"
head -n 98304 "$REF/route.log" > /root/ob2/ref-prefix.log
wc -l < /root/ob2/ref-prefix.log
wc -l < "$LOCAL/route.log"
if cmp /root/ob2/ref-prefix.log "$LOCAL/route.log"; then
  echo "ROUTE_PREFIX=PASS (byte identical)"
else
  echo "ROUTE_PREFIX=FAIL"
fi
sha256sum /root/ob2/ref-prefix.log "$LOCAL/route.log"
rm -f /root/ob2/ref-prefix.log

echo "--- engine stats ---"
cat "$LOCAL/ob2-stats.txt"
echo "########## UNIT DONE ##########"
