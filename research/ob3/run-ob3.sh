#!/bin/sh
# OB-3 region-leasing run driver.
#
# Same frozen invocation shape as OB-1's research/ob1/run-ob1.sh (llama-perplexity,
# -ngl 0, --no-mmap, --no-repack, CPU-only, nice 10, --seed 1, --no-warmup,
# --ctx-size 1024, -b/-ub 1024), with exactly three differences, all named in
# OB3-REGION-1-PREREG and RUNLOG-1.txt:
#
#   1. --threads 8 --threads-batch 8, not 10. This leg's CPU wall is 8 threads
#      per heavy run (house rule); OB-1 used 10. Named as a deviation: it makes
#      this leg's wall-clock and p95 figures NOT directly comparable to OB-1's
#      own, and the cost-limb ratio against OB-1's banked 10-thread resident
#      baseline is therefore CONSERVATIVE (inflated).
#   2. The binary is this leg's own fork worktree build (/root/ob3/llama.cpp,
#      branch ob3 off c087083, GGML_CUDA=OFF CPU-only) carrying the region
#      selection patch, not /root/rs053/llama.cpp's build. FORK DISCIPLINE.
#   3. OB3_DETECT / OB3_SETS_PROSE / OB3_SETS_CODE: the frozen detector reads
#      the input file's first 4096 bytes at engine startup and chooses the
#      resident set. Everything after that choice is OB-1's engine, unmodified.
#
# The box-wide RUNLOCK is acquired before the model process starts and released
# IMMEDIATELY after it exits (no analysis is done under the lock).
#
# usage: run-ob3.sh RUNNAME CORPUSPATH K CHUNKS MODE
#   MODE=resident  K is ignored, fully resident baseline, no detector
#   MODE=detect    leased, the detector chooses between SET-PROSE and SET-CODE

RUNNAME=$1
CORPUS=$2
K=$3
CHUNKS=$4
MODE=$5

BIN=/root/ob3/llama.cpp/build/bin/llama-perplexity
MODEL=/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf
WT=/mnt/f/f32/openbob-wt/ob3
SETS_PROSE=$WT/research/ob1/RESIDENT-SETS.json
SETS_CODE=$WT/research/ob3/RESIDENT-SETS-CODE.json
MANIFEST=$WT/research/ob1/EXPERT-MANIFEST-20B.sha256
LOCK=/mnt/f/f32/stage/research/runlock

LOCAL=/root/ob3/runs/$RUNNAME
STAGE=/mnt/f/f32/stage/research/ob3/runs/$RUNNAME
mkdir -p "$LOCAL" "$STAGE"
RL=$LOCAL/route.log
rm -f "$RL"

# Run metadata, written for every run (leased or resident) so the analysis
# tool knows which corpus a resident baseline used; the detector only records
# its own input path on leased runs.
{
  echo "runname=$RUNNAME"
  echo "corpus=$CORPUS"
  echo "k=$K"
  echo "chunks=$CHUNKS"
  echo "mode=$MODE"
} > "$LOCAL/ob3-run.txt"

echo "=== OB3 RUN $RUNNAME (K=$K CHUNKS=$CHUNKS MODE=$MODE) ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "corpus $CORPUS"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"

# ---- free RAM bar (>= 6 GB) --------------------------------------------------
AVAIL_GB=$(awk '/MemAvailable/ {printf "%d", $2/1048576}' /proc/meminfo)
echo "mem_available_gb $AVAIL_GB (bar >=6)"
if [ "$AVAIL_GB" -lt 6 ]; then
  echo "ABORT: free RAM below bar"
  exit 90
fi

# ---- RUNLOCK: atomic mkdir, sleep 30, give up after 90 minutes ---------------
WAITED=0
until mkdir "$LOCK" 2>/dev/null; do
  if [ "$WAITED" -ge 5400 ]; then
    echo "ABORT: RUNLOCK not acquired after 5400s"
    exit 91
  fi
  sleep 30
  WAITED=$((WAITED + 30))
done
echo "runlock_acquired utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) waited_s=$WAITED"

ARGS="-m $MODEL -f $CORPUS --ctx-size 1024 --chunks $CHUNKS -b 1024 -ub 1024 --threads 8 --threads-batch 8 --no-warmup --seed 1 -ngl 0 --no-mmap --no-repack"
echo "cmd: $BIN $ARGS"

T0=$(date +%s.%N)
if [ "$MODE" = "resident" ]; then
  echo "env: LLAMA_ROUTE_LOG=$RL OB1_STATS=$LOCAL/ob1-stats.txt (no lease, no detector)"
  CUDA_VISIBLE_DEVICES="" \
  LLAMA_ROUTE_LOG="$RL" \
  OB1_STATS="$LOCAL/ob1-stats.txt" \
  nice -n 10 /usr/bin/time -v $BIN $ARGS > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
  RC=$?
else
  echo "env: OB1_LEASE=$SETS_PROSE (status-quo default) OB1_K=$K OB3_DETECT=$CORPUS"
  echo "     OB3_SETS_PROSE=$SETS_PROSE"
  echo "     OB3_SETS_CODE=$SETS_CODE"
  CUDA_VISIBLE_DEVICES="" \
  LLAMA_ROUTE_LOG="$RL" \
  OB1_STATS="$LOCAL/ob1-stats.txt" \
  OB1_LEASE="$SETS_PROSE" \
  OB1_K="$K" \
  OB1_MANIFEST="$MANIFEST" \
  OB1_GGUF="$MODEL" \
  OB1_FADV="0" \
  OB3_DETECT="$CORPUS" \
  OB3_SETS_PROSE="$SETS_PROSE" \
  OB3_SETS_CODE="$SETS_CODE" \
  nice -n 10 /usr/bin/time -v $BIN $ARGS > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
  RC=$?
fi
T1=$(date +%s.%N)

# ---- release the lock IMMEDIATELY, before any reporting ----------------------
rmdir "$LOCK"
echo "runlock_released utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "exit_rc $RC"
echo "wallclock_s $(echo "$T1 - $T0" | bc)"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "--- OB3 detector line (engine's own stderr) ---"
grep -E '^OB3:' "$LOCAL/stderr.txt"
echo "--- peak rss / elapsed ---"
grep -E 'Maximum resident set size|Elapsed \(wall clock\)' "$LOCAL/stderr.txt"
echo "--- route log ---"
wc -l < "$RL"
sha256sum "$RL"
echo "--- identity artifact ---"
grep '^\[1\]' "$LOCAL/stdout.txt" > "$LOCAL/identity.txt"
wc -c < "$LOCAL/identity.txt"
sha256sum "$LOCAL/identity.txt"
cat "$LOCAL/identity.txt"
echo "--- ob1/ob3 stats ---"
cat "$LOCAL/ob1-stats.txt"
echo "--- timings ---"
grep -E 'load time|prompt eval time|eval time|total time|seconds per pass' "$LOCAL/stderr.txt"
echo "guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"

cp "$RL" "$STAGE/route.log"
cp "$LOCAL/stdout.txt" "$STAGE/stdout.txt"
cp "$LOCAL/stderr.txt" "$STAGE/stderr.txt"
cp "$LOCAL/identity.txt" "$STAGE/identity.txt"
cp "$LOCAL/ob1-stats.txt" "$STAGE/ob1-stats.txt"
echo "--- post-copy digest check ---"
sha256sum "$RL" "$STAGE/route.log"
sha256sum "$LOCAL/identity.txt" "$STAGE/identity.txt"
echo "=== END $RUNNAME rc=$RC ==="
