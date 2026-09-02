#!/bin/sh
# OB-2 stage 2: one leased run, wrapped in the house RUNLOCK.
#
# RUNLOCK LAW as the venue states it: every gpt-oss model run must hold the
# box-wide lock first; acquire with `mkdir /mnt/f/f32/stage/research/runlock`
# (atomic: mkdir fails if the directory already exists, so exactly one waiter
# wins), loop with sleep 30 until it succeeds, give up and report after 90 min;
# release with rmdir IMMEDIATELY after the run exits, never holding it during
# analysis. Free RAM must be >= 6 GB before the run starts.
#
# The lock is taken and released PER RUN, not once around the whole matrix, so
# the sibling OB-3 workflow interleaves between this leg's runs.
#
# usage: locked-run.sh RUNNAME CORPUSPATH K CHUNKS [TRACE]
LOCK=/mnt/f/f32/stage/research/runlock
RUNNAME=$1
CORPUS=$2
K=$3
CHUNKS=$4
TRACE=$5

DRIVER=/mnt/f/f32/openbob-wt/research-2/research/ob2/run-ob2.sh

echo "### LOCKED-RUN $RUNNAME requesting lock at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
WAITED=0
LIMIT=5400          # 90 minutes
while :; do
  if mkdir "$LOCK" 2>/dev/null; then
    echo "### LOCK ACQUIRED for $RUNNAME after ${WAITED}s at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    break
  fi
  if [ "$WAITED" -ge "$LIMIT" ]; then
    echo "### LOCK GIVE-UP for $RUNNAME after ${WAITED}s (90 min limit). Lock still held by another leg."
    ls -ld "$LOCK"
    exit 42
  fi
  sleep 30
  WAITED=$((WAITED + 30))
done

# free RAM gate, checked while holding the lock so nothing can race in behind it
FREE=$(free -g | awk '/^Mem:/ {print $7}')
echo "### free RAM (available, GiB) = $FREE"
if [ "$FREE" -lt 6 ]; then
  echo "### ABORT $RUNNAME: free RAM ${FREE} GiB < 6 GiB bar. Releasing lock untouched."
  rmdir "$LOCK"
  exit 43
fi

sh "$DRIVER" "$RUNNAME" "$CORPUS" "$K" "$CHUNKS" "$TRACE"
RC=$?

# release IMMEDIATELY: no analysis happens under the lock
rmdir "$LOCK"
echo "### LOCK RELEASED after $RUNNAME (driver rc=$RC) at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
exit $RC
