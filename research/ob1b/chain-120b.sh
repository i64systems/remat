#!/bin/sh
# OB-1b: start the 120b leg the moment the 20b matrix finishes.
#
# Both legs take the house runlock per run, so they must not run at the same
# time as each other (they would just queue against themselves and against the
# three sibling workflows). This waits for the 20b matrix process to leave the
# process table -- which covers every way it can end, including the runlock
# give-up path and an outright failure, not just the happy "MATRIX DONE" -- and
# then starts the 120b leg. It exists so the box is not left idle between the
# two legs while nobody is watching.
LOG=/mnt/f/f32/stage/research/ob1b
echo "### chain: waiting for the 20b matrix to finish, $(date -u +%Y-%m-%dT%H:%M:%SZ)"
while pgrep -f "ob1b/runs-knee.sh" > /dev/null 2>&1; do
  sleep 60
done
echo "### chain: 20b matrix is gone at $(date -u +%Y-%m-%dT%H:%M:%SZ); its last lines were:"
tail -5 $LOG/matrix.log
echo "### chain: starting the 120b leg"
sh /mnt/f/f32/openbob-wt/research-2/research/ob1b/runs-120b.sh
echo "### chain: 120b leg returned $? at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
