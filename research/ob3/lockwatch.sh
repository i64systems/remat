#!/bin/sh
# Read-only observation of the box-wide RUNLOCK. Takes no lock, changes
# nothing; samples existence at 1 Hz and prints every transition with a UTC
# timestamp, so the real width of the release window between the sibling
# workflow's back-to-back runs can be measured rather than guessed.
#
# Used to produce the contention evidence in
# research/ob3/RUNLOG-1.txt section 5.
PREV=""
END=$(( $(date +%s) + 3600 ))
while [ "$(date +%s)" -lt "$END" ]; do
  if [ -d /mnt/f/f32/stage/research/runlock ]; then S=HELD; else S=FREE; fi
  if [ "$S" != "$PREV" ]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $S"
    PREV=$S
  fi
  sleep 1
done
