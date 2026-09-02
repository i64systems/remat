#!/bin/sh
# OB-5a stage 2: the P1 regression matrix plus the P4 A/A pair.
#
# Every run takes and releases the house runlock on its own
# (locked-run-ob5a.sh), so a sibling can interleave between runs instead of
# waiting behind the whole matrix.
#
# RUN ORDER IS BY DECISIVENESS, NOT BY THE ORDER OF THE BRIEF'S LIST.
#   The A/A pair first, at 2 chunks: it is 3 minutes of lock time and it settles
#   P4b (allocator determinism) and P4d (the call-count relation) before an hour
#   of lock time is spent. If the two journals disagree, the allocator is
#   nondeterministic and no 32-chunk run is worth making.
#   Then lease-k0-prose, the PURE STREAMING point: it is the run with the most
#   commit/decommit traffic per second and the largest PROT_NONE churn, so it is
#   the run most likely to expose a fault or a rounding error.
#   Then lease-k8-code, the mixed point where resident islands and leased islands
#   share edge pages, which is where the inward/outward rounding rule earns its
#   keep.
#   Then the two RESIDENT controls, which commit the whole model by construction
#   (bar P2d) and prove the allocator does not disturb the ordinary path.
#
# ANY IDENTITY OR ROUTE MISMATCH IS STOP-SHIP. This script does not stop the
# remaining runs on a mismatch, because a second data point localises a fault
# better than an early exit does, but the receipt reports the mismatch verbatim
# and the 120b never fires. There is no retry-until-green.
SETSK=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-KNEE.json
SETS8=/mnt/f/f32/openbob-wt/research-2/research/ob1/RESIDENT-SETS.json
MODEL=/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf
MAN=/mnt/f/f32/openbob-wt/research-2/research/ob1/EXPERT-MANIFEST-20B.sha256
PROSE=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
CODE=/mnt/f/f32/stage/research/ob1/AC-CODE.txt
LR=/mnt/f/f32/openbob-wt/research-2/research/ob5a/locked-run-ob5a.sh
LOGS=/mnt/f/f32/stage/research/ob5a/logs
mkdir -p $LOGS

# the banked pairs, from the RULES block of this leg and re-verified reachable
IDP=96049ccf8ca241bf58233afe13ed75e2ca43180d81973360d04cebc80d551925
RTP=4777aa8319f25d6e367f761ef12c7bec81a9ff7896bfed1b8ea0326b5dffc3df
IDC=9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8
RTC=f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77

echo "########## OB5A 20B REGRESSION MATRIX ##########"
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "engine:"
sha256sum /root/ob5a/llama.cpp/build/bin/llama-perplexity \
          /root/ob5a/llama.cpp/build/bin/libllama.so.0 \
          /root/ob5a/llama.cpp/build/bin/libggml-base.so.0
echo "corpora:"; sha256sum $PROSE $CODE
echo "resident sets:"; sha256sum $SETSK $SETS8
echo "manifest:"; sha256sum $MAN
echo "banked pairs: prose $IDP / $RTP"
echo "              code  $IDC / $RTC"
echo

for R in \
  "aa-k0-prose-a  $PROSE lease 0 $SETSK $MODEL $MAN  2 8 - -" \
  "aa-k0-prose-b  $PROSE lease 0 $SETSK $MODEL $MAN  2 8 - -" \
  "lease-k0-prose $PROSE lease 0 $SETSK $MODEL $MAN 32 8 $IDP $RTP" \
  "lease-k8-code  $CODE  lease 8 $SETS8 $MODEL $MAN 32 8 $IDC $RTC" \
  "res-prose      $PROSE resident -1 - $MODEL - 32 8 $IDP $RTP" \
  "res-code       $CODE  resident -1 - $MODEL - 32 8 $IDC $RTC" \
; do
  set -- $R
  NAME=$1
  echo "########## $NAME  $(date -u +%Y-%m-%dT%H:%M:%SZ) ##########"
  sh $LR "$@" > $LOGS/$NAME.log 2>&1
  RC=$?
  echo "=== $NAME rc=$RC ==="
  grep -E "^### LOCK|^exit_rc|^wallclock_s|Maximum resident set size|^  identity:|^  route:|^  P4c:|^lease_events=|^peak_concurrent|^alloc_commit_model_peak=|^alloc_commit_peak_single=|^alloc_va_model_bytes=|^alloc_journal_sha256=|OB5A RESERVE FATAL|OB1 FATAL" $LOGS/$NAME.log
  if [ $RC -eq 75 ]; then
    echo "RUNLOCK NEVER FREED for $NAME -- matrix stopped here."
    exit 75
  fi
  if [ $RC -ne 0 ]; then
    echo "$NAME FAILED rc=$RC -- last 40 lines verbatim:"
    tail -40 $LOGS/$NAME.log
    echo "continuing to the next run; the failure is recorded, not hidden."
  fi
done

echo "########## MATRIX DONE $(date -u +%Y-%m-%dT%H:%M:%SZ) ##########"
