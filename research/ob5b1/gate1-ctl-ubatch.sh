#!/bin/sh
# OB-5b S1 gate 1, DECLARED CONTROL: is the batch schedule really in the bound
# state?
#
# OB5-DESIGN-C4-1.md section 4.3 asserts it in words: "THE BATCH SCHEDULE IS IN
# THE BOUND STATE AND THAT IS NOT BOOKKEEPING. Floating point summation order in
# a CPU matmul depends on how many rows are computed together. A prefill batched
# at 512 and a prefill batched at 384 can produce different logits, and a
# different argmax at one position produces a different token and a different
# answer."
#
# Nothing in this program had measured that. This control runs the identical
# bound state with ONE member changed, n_ubatch 64 -> 32, so the 56-token prompt
# is submitted in two pieces instead of one, and asks whether the generated
# bytes move. Either answer is a result:
#   they MOVE      -> section 4.3 is measured, not merely argued, and the schedule
#                     must be pinned in the manifest and the receipt.
#   they DO NOT    -> the assertion is untested at this scale and the design may
#                     be carrying a constraint it does not need. Report it plainly.
#
# It is also a POSITIVE CONTROL on the A/A harness itself: a harness that cannot
# report DIFFER has not proven IDENTICAL.
set -e

LOCK=/mnt/f/f32/stage/research/runlock
DST=/root/ob5b1/llama.cpp
BIN=$DST/build/bin/ob5b1-gen
MODEL=/root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf
SETS=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json
MAN=/mnt/f/f32/openbob-wt/research-2/research/ob1b/EXPERT-MANIFEST-120B.sha256
PROMPT=/mnt/f/f32/stage/research/ob5b1/PROMPT-1.txt
RUNNAME=gen-120b-k8-ub32
LOCAL=/root/ob5b1/runs/$RUNNAME
STAGE=/mnt/f/f32/stage/research/ob5b1/runs/$RUNNAME
mkdir -p "$LOCAL" "$STAGE"
RL=$LOCAL/route.log
JL=$LOCAL/alloc-journal.txt
rm -f "$RL" "$JL" "$LOCAL"/gen-*.txt "$LOCAL"/prompt-ids.txt

echo "=== OB5B1 GATE 1 CONTROL: n_ubatch 32 (everything else identical to run A) ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"

T0=$(date +%s)
while ! mkdir "$LOCK" 2>/dev/null; do
  W=$(( $(date +%s) - T0 ))
  if [ $W -ge 7200 ]; then echo "### GIVING UP on runlock after ${W}s"; exit 75; fi
  sleep 5
done
echo "### LOCK ACQUIRED after $(( $(date +%s) - T0 ))s"
AVAIL=$(free -g | awk '/^Mem:/{print $7}')
echo "### free RAM available: ${AVAIL} GB (house bar: 6 GB)"
if [ "$AVAIL" -lt 6 ]; then echo "### ABORT: free RAM below bar"; rmdir "$LOCK"; exit 76; fi
OC=$(cat /proc/sys/vm/overcommit_memory)
echo "### overcommit_at_run: $OC"
if [ "$OC" != "0" ]; then echo "### ABORT: overcommit is $OC"; rmdir "$LOCK"; exit 77; fi

TS=$(date +%s.%N)
CUDA_VISIBLE_DEVICES="" \
OB5A_RESERVE=1 \
OB5A_ALLOC_JOURNAL="$JL" \
LLAMA_ROUTE_LOG="$RL" \
OB1_STATS="$LOCAL/ob1-stats.txt" \
OB1_LEASE="$SETS" \
OB1_K=8 \
OB1_MANIFEST="$MAN" \
OB1_GGUF="$MODEL" \
LD_LIBRARY_PATH="$DST/build/bin" \
nice -n 10 /usr/bin/time -v "$BIN" \
  --model "$MODEL" --prompt-file "$PROMPT" --out-dir "$LOCAL" \
  --n-predict 32 --ctx 512 --ubatch 32 --threads 8 \
  > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
RC=$?
TE=$(date +%s.%N)
echo "### overcommit_after_run: $(cat /proc/sys/vm/overcommit_memory)"
rmdir "$LOCK"
echo "### exit_rc $RC  wallclock_s $(echo "$TE - $TS" | bc)"
echo "### guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"

A=/root/ob5b1/runs/gen-120b-k8-a
echo "--- stdout, verbatim ---"
cat "$LOCAL/stdout.txt"
echo "--- generated text, verbatim ---"
cat "$LOCAL/gen-text.txt"
echo ""
echo "=== CONTROL VERDICT ==="
echo "run A (ubatch 64) prefill_pieces: $(grep '^prefill_pieces' $A/stdout.txt | awk '{print $2}')"
echo "control (ubatch 32) prefill_pieces: $(grep '^prefill_pieces' $LOCAL/stdout.txt | awk '{print $2}')"
for f in gen-ids.txt gen-text.txt prompt-ids.txt route.log; do
  if cmp -s "$A/$f" "$LOCAL/$f"; then
    printf "  %-16s ubatch 64 vs ubatch 32   IDENTICAL\n" "$f"
  else
    printf "  %-16s ubatch 64 vs ubatch 32   DIFFER\n" "$f"
    echo "      first differing byte: $(cmp "$A/$f" "$LOCAL/$f" 2>&1 | head -1)"
  fi
done
echo "--- digests, run A then control ---"
sha256sum "$A/gen-ids.txt" "$LOCAL/gen-ids.txt"
sha256sum "$A/gen-text.txt" "$LOCAL/gen-text.txt"
sha256sum "$A/route.log" "$LOCAL/route.log"
echo "--- ob1 stats, verbatim ---"
cat "$LOCAL/ob1-stats.txt"
echo "--- peak rss / elapsed ---"
grep -E 'Maximum resident set size|Elapsed \(wall clock\)' "$LOCAL/stderr.txt" || true
for f in stdout.txt stderr.txt gen-ids.txt gen-text.txt prompt-ids.txt ob1-stats.txt route.log; do
  [ -f "$LOCAL/$f" ] && cp "$LOCAL/$f" "$STAGE/$f"
done
echo "### courtesy yield 75 s"
sleep 75
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== END CONTROL rc=$RC ==="
