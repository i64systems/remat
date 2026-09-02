#!/bin/sh
# OB-5a builder 2b: THE 120b P3 ROW ON THE NEW ALLOCATOR, WITH NO KERNEL KNOB.
#
# This is the architectural answer. The concurrent architect-run SCOUT measured
# the same 120b point on the LANDED engine with vm.overcommit_memory flipped to
# 1; this run measures it on the RESERVE/COMMIT allocator with the kernel left
# alone. If this run needed the knob, it would prove nothing that the scout has
# not already proven, so the knob's value is recorded INSIDE the locked window,
# immediately before and immediately after the model process, and a value other
# than 0 ABORTS the run rather than producing a worthless claim.
#
# This closes the gap the day leg declared in RUNLOG-1.txt section 9.3:
#   "Add overcommit_at_run: $(cat /proc/sys/vm/overcommit_memory) to the run
#    driver; this leg did not, and says so as a declared gap."
#
# Lock etiquette is the house law and is taken PER RUN: mkdir to acquire, 5 s
# poll, free RAM >= 6 GB, rmdir immediately after the model process exits, 75 s
# courtesy yield. The scout uses the same lock and only flips overcommit while
# it holds it, so holding the lock is what guarantees the 0 this run records.
#
# usage: run-120b-night.sh RUNNAME CHUNKS EXP_ID EXP_RT
RUNNAME=$1
CHUNKS=$2
EXP_ID=$3
EXP_RT=$4

LOCK=/mnt/f/f32/stage/research/runlock
BIN=/root/ob5a/llama.cpp/build/bin/llama-perplexity
MODEL=/root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf
SETS=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json
MAN=/mnt/f/f32/openbob-wt/research-2/research/ob1b/EXPERT-MANIFEST-120B.sha256
CORPUS=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
LOCAL=/root/ob5a/runs/$RUNNAME
STAGE=/mnt/f/f32/stage/research/ob5a/runs/$RUNNAME

mkdir -p "$LOCAL" "$STAGE"
RL=$LOCAL/route.log
JL=$LOCAL/alloc-journal.txt
rm -f "$RL" "$JL"

echo "=== OB5A 120B P3 RUN $RUNNAME (K=8 of 128, leased, chunks=$CHUNKS, threads=8, reserve=1) ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "overcommit_before_lock: $(cat /proc/sys/vm/overcommit_memory)"
echo "bin_sha256:  $(sha256sum $BIN | cut -d' ' -f1)"
echo "ggml_sha256: $(sha256sum /root/ob5a/llama.cpp/build/bin/libggml-base.so.0 | cut -d' ' -f1) libggml-base.so.0"
echo "model_bytes: $(stat -c %s $MODEL)"
echo "sets_sha256: $(sha256sum $SETS | cut -d' ' -f1)"
echo "man_sha256:  $(sha256sum $MAN | cut -d' ' -f1)"
echo "corpus_sha256: $(sha256sum $CORPUS | cut -d' ' -f1)"
echo "expect_identity: $EXP_ID"
echo "expect_route:    $EXP_RT"

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
    echo "### GIVING UP on runlock after ${WAITED}s (120 min house bar) for $RUNNAME"
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
echo "free_before:"
free -m

# THE KNOB CHECK. This is the whole point of the run and it is fatal.
OC_AT_RUN=$(cat /proc/sys/vm/overcommit_memory)
echo "overcommit_at_run: $OC_AT_RUN"
echo "overcommit_ratio:  $(cat /proc/sys/vm/overcommit_ratio)"
if [ "$OC_AT_RUN" != "0" ]; then
  echo "### ABORT $RUNNAME: vm.overcommit_memory is $OC_AT_RUN, not 0."
  echo "### This run exists to show the allocation succeeds with the kernel left"
  echo "### alone. At $OC_AT_RUN the result would be correct and the claim worthless."
  rmdir "$LOCK"
  exit 77
fi

ARGS="-m $MODEL -f $CORPUS --ctx-size 1024 --chunks $CHUNKS -b 1024 -ub 1024 --threads 8 --threads-batch 8 --no-warmup --seed 1 -ngl 0 --no-mmap --no-repack"
echo "cmd: $BIN $ARGS"
echo "env: OB5A_RESERVE=1 OB5A_ALLOC_JOURNAL=$JL LLAMA_ROUTE_LOG=$RL OB1_STATS=$LOCAL/ob1-stats.txt OB1_LEASE=$SETS OB1_K=8 OB1_MANIFEST=$MAN"
echo "oom_score_adj: 1000 requested on the run process"

# oom_score_adj sampler: the request above is ASSERTED, this MEASURES it on the
# actual model process, so the receipt carries what the kernel had, not what the
# driver asked for.
( sleep 45
  P=$(pgrep -f "ob5a/llama.cpp/build/bin/llama-perplexity" | head -1)
  if [ -n "$P" ]; then
    echo "oom_score_adj_measured: pid $P -> $(cat /proc/$P/oom_score_adj 2>&1)  oom_score $(cat /proc/$P/oom_score 2>&1)"
  else
    echo "oom_score_adj_measured: (model process not found at +45 s)"
  fi
) > "$LOCAL/oom-sample.txt" 2>&1 &
SAMPLER=$!

T1=$(date +%s.%N)
( echo 1000 > /proc/self/oom_score_adj
  exec env CUDA_VISIBLE_DEVICES="" \
    OB5A_RESERVE=1 \
    OB5A_ALLOC_JOURNAL="$JL" \
    LLAMA_ROUTE_LOG="$RL" \
    OB1_STATS="$LOCAL/ob1-stats.txt" \
    OB1_LEASE="$SETS" \
    OB1_K=8 \
    OB1_MANIFEST="$MAN" \
    OB1_GGUF="$MODEL" \
    nice -n 10 /usr/bin/time -v $BIN $ARGS
) > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
RC=$?
T2=$(date +%s.%N)

OC_AFTER=$(cat /proc/sys/vm/overcommit_memory)
wait $SAMPLER 2>/dev/null
rmdir "$LOCK"
echo "### LOCK RELEASED $RUNNAME at $(date -u +%Y-%m-%dT%H:%M:%SZ) rc=$RC"

echo "exit_rc $RC"
echo "wallclock_s $(echo "$T2 - $T1" | bc)"
echo "overcommit_after_run: $OC_AFTER"
cat "$LOCAL/oom-sample.txt" 2>/dev/null
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "--- did the 63374323968-byte allocation appear at all? ---"
if grep -E "insufficient memory|failed to allocate buffer|alloc_tensor_range|unable to allocate CPU buffer|unable to load model" "$LOCAL/stderr.txt"; then
  echo "*** THE OLD FAILURE IS STILL PRESENT ***"
else
  echo "NO ggml_aligned_malloc FAILURE, NO 63374323968-BYTE REQUEST."
fi
echo "--- peak rss / elapsed ---"
grep -E 'Maximum resident set size|Elapsed \(wall clock\)' "$LOCAL/stderr.txt" || echo "(no time -v block: process did not exit normally)"
echo "--- the allocator announced itself (verbatim) ---"
grep -E "OB5A reserved|OB5A reserve allocator|allocation journal|OB1: lease engine" "$LOCAL/stderr.txt" || echo "(NO ALLOCATOR LINES -- the reserve path was not taken)"
echo "--- any OB5A/OB1 fatal, verbatim ---"
grep -E "OB5A RESERVE FATAL|OB1 FATAL|Segmentation fault|Killed" "$LOCAL/stderr.txt" || echo "(none)"
echo "--- last 20 lines of stderr (verbatim) ---"
tail -20 "$LOCAL/stderr.txt"

echo "--- identity artifact ---"
grep '^\[1\]' "$LOCAL/stdout.txt" > "$LOCAL/identity.txt" || true
echo "  got: $(cat $LOCAL/identity.txt)"
GID=$(sha256sum "$LOCAL/identity.txt" | cut -d' ' -f1)
echo "identity_sha256 $GID"
if [ -f "$RL" ]; then
  echo "route_lines $(wc -l < $RL)"
  GRT=$(sha256sum "$RL" | cut -d' ' -f1)
  echo "route_sha256 $GRT"
else
  GRT="(no route log)"
  echo "(no route log)"
fi

echo "--- P3a VERDICT against the banked paged reference pair ---"
if [ "$GID" = "$EXP_ID" ]; then echo "  identity: MATCH   $GID"; else
  echo "  identity: *** MISMATCH ***"; echo "    got  $GID"; echo "    want $EXP_ID"; fi
if [ "$GRT" = "$EXP_RT" ]; then echo "  route:    MATCH   $GRT"; else
  echo "  route:    *** MISMATCH ***"; echo "    got  $GRT"; echo "    want $EXP_RT"; fi

echo "--- ob1 stats (verbatim) ---"
cat "$LOCAL/ob1-stats.txt" 2>&1

echo "--- P4c: the printed journal digest must equal sha256 of the journal FILE ---"
if [ -f "$JL" ]; then
  JF=$(sha256sum "$JL" | cut -d' ' -f1)
  JP=$(grep '^alloc_journal_sha256=' "$LOCAL/ob1-stats.txt" 2>/dev/null | cut -d= -f2)
  echo "  journal_file_bytes  $(stat -c %s $JL)"
  echo "  journal_file_lines  $(wc -l < $JL)"
  echo "  file   sha256 $JF"
  echo "  engine sha256 $JP"
  if [ "$JF" = "$JP" ]; then echo "  P4c: MATCH"; else echo "  P4c: *** MISMATCH ***"; fi
  gzip -9 -c "$JL" > "$STAGE/alloc-journal.txt.gz"
else
  echo "  (no journal file)"
fi

echo "free_after:"
free -m
echo "guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"

for f in route.log stdout.txt stderr.txt identity.txt ob1-stats.txt oom-sample.txt; do
  [ -f "$LOCAL/$f" ] && cp "$LOCAL/$f" "$STAGE/$f"
done
echo "### courtesy yield 75s"
sleep 75
echo "=== END $RUNNAME rc=$RC ==="
exit $RC
