#!/bin/sh
# OB-1b: sample who is holding the house runlock, once a minute.
#
# Three sibling workflows (OB-2, OB-3, OB-4) share this box's runlock with this
# leg, and the receipt should be able to say how the night was actually shared
# rather than guessing. One `ps` per minute is far below any thread wall and
# touches nothing. Columns: UTC, lock present, and the worktree path of whatever
# llama-perplexity is executing, which identifies the leg holding it.
OUT=/mnt/f/f32/stage/research/ob1b/LOCKWATCH.txt
LOCK=/mnt/f/f32/stage/research/runlock
echo "# utc  lock_present  running_leg  loadavg1" >> $OUT
while true; do
  if [ -d "$LOCK" ]; then P=yes; else P=no; fi
  LEG=$(ps -eo args | grep llama-perplexity | grep -v grep \
        | grep -oE '/root/ob[0-9b]+/llama\.cpp' | head -1)
  [ -z "$LEG" ] && LEG=none
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $P $LEG $(cut -d' ' -f1 /proc/loadavg)" >> $OUT
  sleep 60
done
