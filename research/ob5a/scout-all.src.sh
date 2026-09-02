#!/bin/sh
# OB-5a OVERCOMMIT SCOUT, architect-run. Authorization: THREADS.md
# authorization recorded at commit d95cbd1; reconfirmed 2026-09-01
# afternoon: "lets get the scout moving again."
# Protocol per research/OB5-PLAN-1.md section 2.1 with the banked
# per-run lock etiquette: acquire lock, flip overcommit to 1, run,
# flip back to 0, release, yield. The box is never at overcommit=1
# without the lock held. All output literal.

SETS=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json
MODEL=/root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf
MAN=/mnt/f/f32/openbob-wt/research-2/research/ob1b/EXPERT-MANIFEST-120B.sha256
PROSE=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
D=/mnt/f/f32/stage/research/ob5a
LOCK=/mnt/f/f32/stage/research/runlock
DRIVER=$D/run-scout.sh
LOGS=$D/logs-scout
mkdir -p "$LOGS"

echo "########## OB5A SCOUT $(date -u +%Y-%m-%dT%H:%M:%SZ) ##########"
echo "inputs:"
sha256sum "$SETS" "$MAN"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "overcommit_initial: $(cat /proc/sys/vm/overcommit_memory)"

cycle() {
  NAME=$1
  CHUNKS=$2
  echo "########## CYCLE $NAME chunks=$CHUNKS ##########"
  T0=$(date +%s)
  while ! mkdir "$LOCK" 2>/dev/null; do
    W=$(( $(date +%s) - T0 ))
    if [ $W -ge 7200 ]; then echo "### GIVING UP on runlock after ${W}s for $NAME"; return 75; fi
    sleep 5
  done
  echo "### LOCK ACQUIRED $NAME at $(date -u +%Y-%m-%dT%H:%M:%SZ) after $(( $(date +%s) - T0 ))s"
  AVAIL=$(free -g | awk '/^Mem:/{print $7}')
  echo "### free RAM available: ${AVAIL} GB (bar 6)"
  if [ "$AVAIL" -lt 6 ]; then
    echo "### ABORT $NAME: below RAM bar"
    rmdir "$LOCK"
    return 76
  fi
  echo "### overcommit_before: $(cat /proc/sys/vm/overcommit_memory)"
  sysctl -w vm.overcommit_memory=1
  echo "### overcommit_during: $(cat /proc/sys/vm/overcommit_memory)"
  ( echo 1000 > /proc/self/oom_score_adj; exec sh "$DRIVER" "$NAME" "$PROSE" lease 8 "$SETS" "$MODEL" "$MAN" "$CHUNKS" 8 ) > "$LOGS/$NAME.log" 2>&1
  RC=$?
  sysctl -w vm.overcommit_memory=0
  echo "### overcommit_after: $(cat /proc/sys/vm/overcommit_memory)"
  rmdir "$LOCK"
  echo "### LOCK RELEASED $NAME at $(date -u +%Y-%m-%dT%H:%M:%SZ) rc=$RC"
  echo "### guard_pids_after_cycle: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
  grep -E "^exit_rc|^wallclock_s|Maximum resident set size|^overcommit_at_run|identity|insufficient memory|failed to allocate" "$LOGS/$NAME.log" | head -12
  echo "### courtesy yield 75s"
  sleep 75
  return $RC
}

cycle sc120-smoke 1
SMRC=$?
echo "=== smoke rc=$SMRC ==="
if [ $SMRC -ne 0 ]; then
  echo "SMOKE FAILED - full log follows verbatim; the 8-chunk runs are NOT attempted."
  tail -60 "$LOGS/sc120-smoke.log"
  echo "overcommit_final: $(cat /proc/sys/vm/overcommit_memory)"
  exit $SMRC
fi

cycle sc120-k8-prose-a 8
ARC=$?
echo "=== run-a rc=$ARC ==="
cycle sc120-k8-prose-b 8
BRC=$?
echo "=== run-b rc=$BRC ==="

echo "########## COMPARISONS ##########"
RA=/root/ob5a-scout/runs/sc120-k8-prose-a
RB=/root/ob5a-scout/runs/sc120-k8-prose-b
if cmp -s "$RA/identity.txt" "$RB/identity.txt"; then echo "SCOUT A/A identity: MATCH"; else echo "SCOUT A/A identity: DIFFER"; fi
if cmp -s "$RA/route.log" "$RB/route.log"; then echo "SCOUT A/A route: MATCH"; else echo "SCOUT A/A route: DIFFER"; fi
echo "digests (paged reference: identity 9d20bd0365554989051d96b6ad4932625b0a6578002879f8253e6fcc21682019 route a32d0051bd6d68f2777e64c7b889ae48d56621e9701b107fcef88c0e30cd89c1):"
sha256sum "$RA/identity.txt" "$RB/identity.txt" "$RA/route.log" "$RB/route.log" 2>/dev/null
echo "overcommit_final: $(cat /proc/sys/vm/overcommit_memory)"
echo "guard_pids_final: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "########## SCOUT DONE $(date -u +%Y-%m-%dT%H:%M:%SZ) ##########"
