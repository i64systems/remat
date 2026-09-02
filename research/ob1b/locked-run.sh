#!/bin/sh
# OB-1b: the house runlock wrapper.
#
# House law: every gpt-oss model run holds /mnt/f/f32/stage/research/runlock,
# acquired with mkdir (the atomic primitive), reported on after 120 min, and
# released with rmdir IMMEDIATELY after the run. Free RAM must be at least 6 GB
# before the run starts. The lock is taken and released PER RUN so the sibling
# workflows on this box interleave between this leg s runs.
#
# TWO FAIRNESS ADJUSTMENTS, IN OPPOSITE DIRECTIONS, BOTH DELIBERATE.
#
# THE COURTESY YIELD (75 s after each release) exists because releasing with
# rmdir and immediately re-requesting wins the race essentially every time:
# measured on this leg s first two runs, the lock was re-acquired in the same
# second it was released while a sibling sat waiting. That is starvation dressed
# as compliance, and this leg does not do it.
#
# THE 5 SECOND POLL exists because the yield alone left this leg systematically
# behind. Measured: 70 minutes of continuous waiting for one run while a sibling
# released and re-took the lock back to back, with the lock observed free at some
# sample instants, meaning real gaps were being missed by a 30 s poll. Polling
# faster costs a sibling nothing (mkdir is atomic and a stat every 5 s is
# nothing) and does not shorten anyone else s run; it only stops this leg from
# sleeping through the gaps it is entitled to compete for. The generous half of
# the arrangement, the yield, is kept.
#
# usage: locked-run.sh RUNNAME CORPUS MODE K SETS MODEL MANIFEST CHUNKS THREADS
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
    echo "### GIVING UP on runlock after ${WAITED}s (120 min house bar) for $RUNNAME -- the box is busy tonight"
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

sh /mnt/f/f32/openbob-wt/research-2/research/ob1b/run-ob1b.sh "$@"
RC=$?

rmdir "$LOCK"
echo "### LOCK RELEASED $RUNNAME at $(date -u +%Y-%m-%dT%H:%M:%SZ) rc=$RC"
echo "### courtesy yield 75s so a sibling can take the lock before this leg asks again"
sleep 75
exit $RC
