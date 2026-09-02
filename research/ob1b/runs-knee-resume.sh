#!/bin/sh
# OB-1b: the remainder of the 20b knee matrix, resumable.
#
# WHY A RESUME SCRIPT EXISTS, in the same spirit as OB-1's own
# runs-ob1-resume.sh. Four workflows share this box's runlock and this leg's
# runs were waiting 20 to 40 minutes apiece for it. That made the ORDER of the
# remaining work matter more than finishing the original list in one pass:
#
#   the K=0 endpoint and both resident references are already measured, and
#   they are what settles the open question, because K=0 is the end of the
#   curve rather than a waypoint;
#   the 120b point is a DIFFERENT deliverable on a model nothing in this
#   program has ever run leased residency on, so it cannot be interpolated
#   from anything already measured;
#   K=1 and K=2 only fill in the curve BETWEEN two endpoints that are both
#   already measured, and cannot change the verdict.
#
# So the 120b leg is given the lock ahead of K=1 and K=2, and this script picks
# up whatever 20b rows are still missing afterwards.
#
# EVERY RUN IS SKIPPED IF IT ALREADY LANDED, so this can be re-run safely as
# often as the night requires without repeating an hour of lock time.
SETS=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-KNEE.json
MODEL=/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf
MAN=/mnt/f/f32/openbob-wt/research-2/research/ob1/EXPERT-MANIFEST-20B.sha256
PROSE=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
CODE=/mnt/f/f32/stage/research/ob1/AC-CODE.txt
LR=/mnt/f/f32/openbob-wt/research-2/research/ob1b/locked-run.sh
LOGS=/mnt/f/f32/stage/research/ob1b/logs
mkdir -p $LOGS

echo "########## OB1B 20B KNEE MATRIX (RESUME) ##########"
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"

for R in \
  "res8-prose-a    $PROSE resident -1 - $MODEL - 32 8" \
  "res8-code-a     $CODE  resident -1 - $MODEL - 32 8" \
  "lease-k0-prose  $PROSE lease     0 $SETS $MODEL $MAN 32 8" \
  "lease-k0-code   $CODE  lease     0 $SETS $MODEL $MAN 32 8" \
  "lease-k0-code-b $CODE  lease     0 $SETS $MODEL $MAN 32 8" \
  "lease-k1-prose  $PROSE lease     1 $SETS $MODEL $MAN 32 8" \
  "lease-k1-code   $CODE  lease     1 $SETS $MODEL $MAN 32 8" \
  "lease-k2-prose  $PROSE lease     2 $SETS $MODEL $MAN 32 8" \
  "lease-k2-code   $CODE  lease     2 $SETS $MODEL $MAN 32 8" \
; do
  set -- $R
  NAME=$1
  if [ -s /root/ob1b/runs/$NAME/ob1-stats.txt ] && [ -s /root/ob1b/runs/$NAME/identity.txt ]; then
    echo "########## $NAME ALREADY LANDED, skipping ##########"
    continue
  fi
  echo "########## $NAME  $(date -u +%Y-%m-%dT%H:%M:%SZ) ##########"
  sh $LR "$@" > $LOGS/$NAME.log 2>&1
  RC=$?
  echo "=== $NAME rc=$RC ==="
  grep -E "^### LOCK|^exit_rc|^wallclock_s|Maximum resident set size|^lease_events=|^peak_concurrent" $LOGS/$NAME.log
  if [ $RC -eq 75 ]; then
    echo "RUNLOCK NEVER FREED for $NAME -- the box is busy tonight. Matrix stopped here."
    exit 75
  fi
  if [ $RC -ne 0 ]; then
    echo "$NAME FAILED rc=$RC -- last 30 lines verbatim:"
    tail -30 $LOGS/$NAME.log
    echo "continuing to the next run; the failure is recorded, not hidden."
  fi
done

echo "########## MATRIX RESUME DONE $(date -u +%Y-%m-%dT%H:%M:%SZ) ##########"
