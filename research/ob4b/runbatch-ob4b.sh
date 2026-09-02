#!/bin/sh
# OB4B-PARDEC-1 phase 1: the whole run plan of research/OB4B-PARDEC-1-PREREG.md,
# in one batch, under the box-wide RUNLOCK.
#
# RUNLOCK discipline, per operating convention: mkdir to acquire, sleep 30 between attempts,
# report if still waiting after 120 minutes, and rmdir to release IMMEDIATELY
# after EACH run rather than holding the lock across the batch. Free RAM is
# checked before every run and the run is skipped (loudly) if it is under 6 GB.
#
# Order:
#   1. unit-pool1  K=8, 4 chunks, pool 1  (the OB-4 code path, control arm)
#   2. unit-pool8  K=8, 4 chunks, pool 8
#      -> identity and route must be byte identical to each other AND to the
#         4-chunk prefix of the banked OB-4 artifacts. A failure stops the batch
#         before any full run.
#   3. ob4b-k8-code-a  K=8, 32 chunks, pool 8
#   4. ob4b-k8-code-b  K=8, 32 chunks, pool 8   (the A/A repeat)

LOCK=/mnt/f/f32/stage/research/runlock
WT=/mnt/f/f32/openbob-wt/ob4/research/ob4b
CORPUS=/mnt/f/f32/stage/research/ob1/AC-CODE.txt
STORE=/root/ob4/EXPERT-STORE-20B.ob4
BANKED=/root/ob4/runs/ob4-k8-code-a

echo "##### OB4B RUN BATCH #####"
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"

acquire() {
  W=0
  while ! mkdir "$LOCK" 2>/dev/null; do
    if [ "$W" -ge 7200 ]; then
      echo "RUNLOCK: STILL WAITING after 120 minutes, reporting and giving up on this run"
      return 1
    fi
    if [ $((W % 600)) -eq 0 ]; then
      echo "runlock: held by another workflow, waited ${W}s ($(date -u +%H:%M:%SZ))"
    fi
    sleep 30
    W=$((W+30))
  done
  echo "runlock: ACQUIRED after ${W}s at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  return 0
}

release() {
  rmdir "$LOCK" 2>/dev/null && echo "runlock: RELEASED at $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    || echo "runlock: RELEASE FAILED (not held?) at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

ramok() {
  AV=$(free -g | awk '/^Mem:/ {print $7}')
  echo "free RAM available: ${AV} GiB"
  [ "$AV" -ge 6 ]
}

do_run() {
  NAME=$1; K=$2; CHUNKS=$3; POOL=$4
  echo ""
  echo "########## $NAME ##########"
  # Explicit resume switch, off unless the caller asks for it. Used once, to
  # resume this batch after the FIRST unit gate reported a false FAIL: the two
  # unit runs were already banked and correct, and re-running the model to
  # re-derive artifacts a fixed comparison already accepted would have burned
  # the RUNLOCK for nothing. Never on by default, so a plain run of this script
  # always executes every run.
  if [ "$OB4B_SKIP_EXISTING" = "1" ] && [ -s "/root/ob4b/runs/$NAME/identity.txt" ]; then
    echo "SKIP $NAME: artifacts already present and OB4B_SKIP_EXISTING=1"
    return 0
  fi
  acquire || return 1
  if ! ramok; then
    echo "ABORT $NAME: free RAM under the 6 GB floor"
    release
    return 1
  fi
  sh $WT/run-ob4b.sh "$NAME" "$CORPUS" "$K" "$CHUNKS" "$STORE" "$POOL"
  RC=$?
  release
  return $RC
}

do_run unit-pool1 8 4 1 || { echo "BATCH STOP: unit-pool1 failed"; exit 1; }
do_run unit-pool8 8 4 8 || { echo "BATCH STOP: unit-pool8 failed"; exit 1; }

echo ""
echo "########## UNIT GATE ##########"
python3 $WT/unit-gate.py /root/ob4b/runs/unit-pool1 /root/ob4b/runs/unit-pool8 "$BANKED"
if [ $? -ne 0 ]; then
  echo "BATCH STOP: UNIT GATE FAILED, no full run is started"
  exit 1
fi
echo "UNIT GATE: PASS"

do_run ob4b-k8-code-a 8 32 8 || { echo "BATCH STOP: ob4b-k8-code-a failed"; exit 1; }
do_run ob4b-k8-code-b 8 32 8 || { echo "BATCH STOP: ob4b-k8-code-b failed"; exit 1; }

echo ""
echo "runlock present at end (should be absent): $(ls -d $LOCK 2>/dev/null || echo none)"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "##### END OB4B RUN BATCH #####"
