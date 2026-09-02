#!/bin/sh
# OB-5b P05 limb (b): the house runlock wrapper, carried unchanged in
# behaviour from research/ob1b/locked-run.sh (mkdir as the atomic
# primitive, 5 s poll, free RAM >= 6 GB, release IMMEDIATELY after the
# run, 75 s courtesy yield so a sibling can take the lock before this
# leg asks again). The heavy C4-S1 sibling shares this box and this
# lock today; the yield is the whole reason it can.
#
# usage: locked-run-ob5b2.sh RUNNAME CORPUS K SETS MODEL MANIFEST CHUNKS THREADS UB
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

sh /mnt/f/f32/stage/research/ob5b2/sh/run-ob5b2.sh "$@"
RC=$?

rmdir "$LOCK"
echo "### LOCK RELEASED $RUNNAME at $(date -u +%Y-%m-%dT%H:%M:%SZ) rc=$RC"
echo "### courtesy yield 75s"
sleep 75
exit $RC
