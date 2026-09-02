#!/bin/sh
# OB-5a stage 2: the house runlock wrapper. Unchanged in substance from
# research/ob1b/locked-run.sh; only the run driver it wraps differs.
#
# House law: every model run holds /mnt/f/f32/stage/research/runlock, acquired
# with mkdir (the atomic primitive), released with rmdir IMMEDIATELY after the
# run, with a 75 s courtesy yield after each release and a 5 s poll while
# waiting. Free RAM must be at least 6 GB before the run starts. The lock is
# taken and released PER RUN.
#
# usage: locked-run-ob5a.sh RUNNAME CORPUS MODE K SETS MODEL MANIFEST CHUNKS THREADS EXP_ID EXP_RT
LOCK=/mnt/f/f32/stage/research/runlock
RUNNAME=$1
T0=$(date +%s)
NEXT_REPORT=600

echo "### LOCK REQUEST $RUNNAME at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
while ! mkdir "$LOCK" 2>/dev/null; do
  WAITED=$(( $(date +%s) - T0 ))
  if [ $WAITED -ge $NEXT_REPORT ]; then
    echo "### still waiting for runlock: ${WAITED}s  holder mtime $(stat -c %y "$LOCK" 2>/dev/null)"
    NEXT_REPORT=$((NEXT_REPORT + 600))
  fi
  if [ $WAITED -ge 7200 ]; then
    echo "### GIVING UP on runlock after ${WAITED}s (120 min house bar) for $RUNNAME"
    exit 75
  fi
  sleep 5
done
echo "### LOCK ACQUIRED $RUNNAME at $(date -u +%Y-%m-%dT%H:%M:%SZ) after $(( $(date +%s) - T0 ))s"

AVAIL=$(free -g | awk "/^Mem:/{print \$7}")
echo "### free RAM available: ${AVAIL} GB (house bar: 6 GB)"
if [ "$AVAIL" -lt 6 ]; then
  echo "### ABORT $RUNNAME: free RAM ${AVAIL} GB is below the 6 GB house bar"
  rmdir "$LOCK"
  exit 76
fi

sh /mnt/f/f32/openbob-wt/research-2/research/ob5a/run-ob5a.sh "$@"
RC=$?

rmdir "$LOCK"
echo "### LOCK RELEASED $RUNNAME at $(date -u +%Y-%m-%dT%H:%M:%SZ) rc=$RC"
echo "### courtesy yield 75s so a sibling can take the lock before this leg asks again"
sleep 75
exit $RC
