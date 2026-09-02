#!/bin/sh
# OB-1b: the 20b knee matrix, K in {2, 1, 0} on both acceptance corpora.
#
# Every run takes and releases the house runlock on its own (locked-run.sh), so
# the three sibling workflows on this box interleave between runs instead of
# waiting behind the whole matrix.
#
# THE FIRST ENTRY IS A SMOKE TEST, NOT A RESULT. K=0 is the point the landed ob1
# binary refused outright (its guard rejected OB1_K=0 before reading anything),
# so before spending an hour of lock time on three full K=0 runs, one 1024-token
# run proves the patched binary accepts an empty resident set and streams every
# routed expert. If it fails, the matrix stops there instead of grinding on.
#
# THREE BASELINE RUNS ARE THIS LEG'S OWN. OB-1's published p95 figures were taken
# at --threads 10; the house wall for this leg is 8. A cost ratio against a
# baseline measured at a different thread count would be meaningless, so this leg
# measures its own fully resident references at 8 threads and compares to those.
# Whether those 8-thread references reproduce OB-1's 10-thread OUTPUT BYTES is a
# separate question the receipt answers from the identity digests.
SETS=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-KNEE.json
MODEL=/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf
MAN=/mnt/f/f32/openbob-wt/research-2/research/ob1/EXPERT-MANIFEST-20B.sha256
PROSE=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
CODE=/mnt/f/f32/stage/research/ob1/AC-CODE.txt
LR=/mnt/f/f32/openbob-wt/research-2/research/ob1b/locked-run.sh
LOGS=/mnt/f/f32/stage/research/ob1b/logs
mkdir -p $LOGS

echo "########## OB1B 20B KNEE MATRIX ##########"
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "engine: /root/ob1b/llama.cpp/build/bin/llama-perplexity"
sha256sum /root/ob1b/llama.cpp/build/bin/llama-perplexity /root/ob1b/llama.cpp/build/bin/libllama.so.0
echo "corpora:"
sha256sum $PROSE $CODE
echo "resident sets:"
sha256sum $SETS
echo

# --- smoke test: does the patched binary accept K=0 at all? ---
sh $LR smoke-k0-prose $PROSE lease 0 $SETS $MODEL $MAN 1 8 > $LOGS/smoke-k0-prose.log 2>&1
RC=$?
echo "=== smoke-k0-prose rc=$RC ==="
grep -E "^exit_rc|OB1: lease engine ON|OB1 FATAL|lease_events=|^\[1\]" $LOGS/smoke-k0-prose.log | head
if [ $RC -ne 0 ]; then
  echo "SMOKE TEST FAILED (rc=$RC). Matrix stopped. Log verbatim:"
  cat $LOGS/smoke-k0-prose.log
  exit 1
fi
echo "smoke test passed: the patched engine runs K=0 (pure streaming)."
echo

# RUN ORDER IS DELIBERATE, AND IT IS NOT THE ORDER OF THE CURVE. Three sibling
# workflows share this box's runlock, so a matrix this long may not finish. The
# order below is therefore by DECISIVENESS, not by descending K:
#   the two baselines first, since no cost statement is possible without them;
#   then K=0, the PURE STREAMING extreme, because it alone settles the open
#   question -- if p95 at an empty resident set is still within the 2.0x bar with
#   identity exact, the maximum exposure of this scheme is its K=0 floor and the
#   intermediate points only colour in the curve; if K=0 breaches the bar, the
#   knee is between K=4 and K=0 and K=1/K=2 are then needed to locate it;
#   then the A/A repeat, which the task names explicitly;
#   then K=1 and K=2, which fill in the curve.
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

echo "########## MATRIX DONE $(date -u +%Y-%m-%dT%H:%M:%SZ) ##########"
