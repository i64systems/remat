#!/bin/sh
# OB-1b: hand the runlock queue from the 20b matrix to the 120b leg.
#
# WHY. Four workflows share this box's runlock and this leg is waiting 20 to 40
# minutes per run. The 20b matrix has already measured what settles the open
# question (both resident references, and K=0 on both corpora, K=0 being the END
# of the curve rather than a waypoint). What remains in it, K=1 and K=2, only
# interpolates between two measured endpoints. The 120b point does not
# interpolate from anything: it is a different model this program has never run.
# So once the A/A repeat at K=0 lands, the matrix stands down, chain-120b.sh
# notices it leave the process table and starts the 120b leg, and
# runs-knee-resume.sh picks up K=1 and K=2 afterwards.
#
# SAFETY. This script only ever signals THIS LEG'S OWN processes, by matching
# the ob1b paths, and only at a moment when this leg cannot be holding the lock:
# after the A/A run has written its stats and while no ob1b model process is
# running. A sibling's run and a sibling's lock are never touched.
LOCK=/mnt/f/f32/stage/research/runlock
echo "### handoff: waiting for lease-k0-code-b to land, $(date -u +%Y-%m-%dT%H:%M:%SZ)"
while [ ! -s /root/ob1b/runs/lease-k0-code-b/ob1-stats.txt ]; do
  if ! pgrep -f "ob1b/runs-knee.sh" > /dev/null 2>&1; then
    echo "### handoff: the matrix left on its own before the A/A landed; nothing to do"
    exit 0
  fi
  sleep 30
done
echo "### handoff: lease-k0-code-b landed at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Wait until no ob1b model process is running, so this leg is provably not
# holding the lock when the matrix is stopped.
while pgrep -f "/root/ob1b/llama.cpp/build/bin/llama-perplexity" > /dev/null 2>&1; do
  sleep 10
done
echo "### handoff: no ob1b model process running; stopping the matrix"

for P in $(pgrep -f "ob1b/runs-knee.sh"); do kill -TERM $P 2>/dev/null; done
sleep 2
for P in $(pgrep -f "ob1b/locked-run.sh"); do kill -TERM $P 2>/dev/null; done
sleep 5
echo "### handoff: remaining ob1b driver processes: $(pgrep -cf 'ob1b/(runs-knee|locked-run)' 2>/dev/null)"

# If the lock is present but NOTHING at all is running a model a full minute
# later, this leg left it stale and must clear it. A sibling that had just taken
# the lock would have exec'd its model process well inside that minute.
sleep 60
if [ -d "$LOCK" ] && ! pgrep -f "llama-perplexity" > /dev/null 2>&1; then
  echo "### handoff: runlock present with no model running anywhere; clearing this leg's stale lock"
  rmdir "$LOCK" 2>/dev/null && echo "### handoff: stale lock cleared" || echo "### handoff: rmdir failed, leaving it alone"
else
  echo "### handoff: runlock is held by a live run or already free; not touching it"
fi
echo "### handoff: done at $(date -u +%Y-%m-%dT%H:%M:%SZ); chain-120b.sh takes over"
