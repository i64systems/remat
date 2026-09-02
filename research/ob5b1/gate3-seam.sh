#!/bin/sh
# OB-5b S1 GATE 3: THE SEAM, PROVEN DEV SIDE.
#
# THE BAR (OB5-DESIGN-C4-1.md section 12, gate 3): "THE SEAM. One typed action
# (working name bob.brain) under the tier, journaled, pointing at the worker's
# own log; the minimal announcement (7.2) and the receipt block (7.3), both
# computed from counters; brain.busy and brain.not_resident refusals live."
#
# THE LIVE SERVE IS NEVER TOUCHED. Everything below runs under a DEV HOME
# (/root/ob5b2/devhome) against a DEV FABRIC BINARY built by this leg. pid 654
# is read with kill(0) to confirm it is alive and is otherwise not addressed at
# all: not signalled, not restarted, not reconfigured, not even connected to.
# The worker binds 127.0.0.1:8907 and the live API keeps 8899.
#
# THE FOUR LIMBS, in the order they run:
#   L1  brain.not_resident, worker down.  Taken BEFORE the worker starts, so it
#       is a refusal about a real absence and not a simulated one.
#   L2  THE ANSWER.  One brain lease end to end: tier ASK, the question, the
#       answer at the terminal journaled as data, the announcement, the worker's
#       turn, the receipt from counters, the chain verified from genesis.
#   L3  brain.busy.  A second lease fired while the first still holds the
#       worker. Refused by name, not queued.
#   L4  brain.identity.violation.  The residency schedule the brain manifest
#       pins is moved in a SANDBOX COPY and the worker is pointed at the copy,
#       so the refusal fires on a real digest mismatch, before the model loads.
set -e
DEV=/root/ob5b2/devhome
FAB=/root/ob5b2/fabric/openbob-br1
WCFG=$DEV/worker.json
WLOG=/root/ob5b2/g3/worker.out
ASK1='in one short paragraph, what does it mean to hold a large model in a small amount of memory'
ASK2='name one thing a lease engine must check before it uses a byte it just read'

say() { echo ""; echo "=============================================================="; echo "$1"; echo "=============================================================="; }

say "GUARDS AND VENUE"
echo "utc            $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids     $(ps -o pid= -p 654 | wc -l) openbob (654), $(ps -o pid= -p 489 | wc -l) searxng (489)"
echo "dev HOME       $DEV"
echo "fabric binary  $FAB  $(sha256sum $FAB | cut -d' ' -f1)"
echo "worker config  $WCFG"
echo "live serve     pid 654, port 8899, NOT TOUCHED. the worker takes 8907."
ss -lntp 2>/dev/null | grep -E ':8899|:8907' || echo "(ss listed no 8899/8907 line)"

say "LIMB 1  brain.not_resident, WITH THE WORKER GENUINELY DOWN"
HOME=$DEV $FAB lease hold 2>&1 || true
echo ""
HOME=$DEV $FAB lease brain --text "$ASK1" --answer yes 2>&1 || true

say "STARTING THE EXPOSURE WORKER"
nohup python3 /root/ob5b2/g3/ob5b2-worker.py "$WCFG" > "$WLOG" 2>&1 &
WPID=$!
echo "worker pid $WPID"
i=0
while [ $i -lt 60 ]; do
  if grep -q '^worker: listening' "$WLOG" 2>/dev/null; then break; fi
  sleep 1
  i=$((i+1))
done
cat "$WLOG"
echo ""
echo "--- the worker is a listener on loopback and nothing else ---"
ss -lntp 2>/dev/null | grep -E ':8907' || echo "(no 8907 line)"

say "LIMB 2 AND LIMB 3  THE ANSWER, AND brain.busy FIRED AGAINST IT"
HOME=$DEV $FAB lease hold 2>&1 || true
echo ""
echo "--- firing the second lease 90 seconds into the first, from another shell ---"
( sleep 90
  echo ""
  echo "############ LIMB 3: THE SECOND LEASE, WHILE THE FIRST HOLDS THE WORKER"
  HOME=$DEV $FAB lease brain --text "$ASK2" --answer yes 2>&1 || true
  echo "############ END LIMB 3"
) > /root/ob5b2/g3/LIMB3.txt 2>&1 &
BUSYPID=$!

echo ""
echo "############ LIMB 2: THE FIRST LEASE"
HOME=$DEV $FAB lease brain --text "$ASK1" --answer yes 2>&1 || true
echo "############ END LIMB 2"
wait $BUSYPID 2>/dev/null || true
cat /root/ob5b2/g3/LIMB3.txt

say "THE WORKER'S OWN RUN LOG"
echo "worker log $(sha256sum /root/ob5b2/worker/WORKER-LOG-1.jsonl 2>/dev/null | cut -d' ' -f1)"
cat /root/ob5b2/worker/WORKER-LOG-1.jsonl 2>/dev/null || echo "(no worker log)"

say "STOPPING THE WORKER FOR LIMB 4"
kill $WPID 2>/dev/null || true
sleep 2

say "LIMB 4  brain.identity.violation, ON A REAL DIGEST MISMATCH"
# A SANDBOX COPY of the residency schedule is moved by one byte of content: the
# copy is a valid JSON resident-set file, so the engine would happily run it,
# and the ONLY thing that refuses is the manifest digest. Nothing under
# research/ob1b is touched.
SB=/root/ob5b2/g3/sandbox
mkdir -p "$SB"
SRC=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json
cp "$SRC" "$SB/sets-moved.json"
printf '\n' >> "$SB/sets-moved.json"
echo "original sets  $(sha256sum $SRC | cut -d' ' -f1)"
echo "sandbox copy   $(sha256sum $SB/sets-moved.json | cut -d' ' -f1)"
echo "the copy is one newline longer; it is still a valid resident-set file."
python3 - "$WCFG" "$SB/sets-moved.json" "$SB/worker-moved.json" <<'PY'
import json, sys
c = json.load(open(sys.argv[1]))
c["sets"] = sys.argv[2]
c["work"] = "/root/ob5b2/g3/sandbox/work"
c["worker_log"] = "/root/ob5b2/g3/sandbox/WORKER-LOG-SANDBOX.jsonl"
json.dump(c, open(sys.argv[3], "w"), indent=1, sort_keys=True)
print("sandbox worker config %s (the brain manifest row is UNCHANGED)" % sys.argv[3])
PY
nohup python3 /root/ob5b2/g3/ob5b2-worker.py "$SB/worker-moved.json" > "$SB/worker.out" 2>&1 &
WPID2=$!
i=0
while [ $i -lt 60 ]; do
  if grep -q '^worker: listening' "$SB/worker.out" 2>/dev/null; then break; fi
  sleep 1
  i=$((i+1))
done
cat "$SB/worker.out"
echo ""
HOME=$DEV $FAB lease brain --text "$ASK1" --answer yes 2>&1 || true
kill $WPID2 2>/dev/null || true
sleep 1
echo ""
echo "--- did the sandbox worker load the model? its own log says ---"
cat "$SB/worker.out"
echo "--- the sandbox turn directory. a turn that LOADED the model would have left"
echo "    a gen-ids.txt, an ob1-stats.txt and a route.log in it ---"
ls -laR /root/ob5b2/g3/sandbox/work 2>&1 | head -20 || echo "(no sandbox work directory)"
echo "sandbox worker log: $(ls -la /root/ob5b2/g3/sandbox/WORKER-LOG-SANDBOX.jsonl 2>&1)"

say "THE JOURNAL, AND THE LIVE SERVE AFTERWARDS"
echo "runs under the dev home:"
ls -1 $DEV/.local/share/openbob/runs 2>/dev/null || true
for d in $DEV/.local/share/openbob/runs/*/; do
  [ -f "$d/HEAD" ] || continue
  echo "  $(basename $d)  $(cat $d/HEAD)"
done
echo ""
echo "guard_pids_final $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
ps -o pid=,etime=,cmd= -p 654
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
