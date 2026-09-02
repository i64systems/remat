#!/bin/sh
# OB4B-PARDEC-1 run driver.
#
# Identical in shape and flags to research/ob4/run-ob4.sh (the driver that
# produced the banked OB-4 runs and the ob4-res-code control this leg is scored
# against), with two differences:
#
#   1. BIN is this leg's own build of the fork worktree /root/ob4b/llama.cpp
#      (branch ob4b, baseline = the OB-4 remat engine, plus research/ob4b/
#      pardec.patch).
#   2. OB4B_DECODE_THREADS sets the decode pool size. It COUNTS THE CALLING
#      THREAD, so POOL=1 spawns no worker at all and walks the OB-4 code path.
#
# Compute threads stay at 10 because the control ran at 10; changing them would
# void the comparison. See the prereg's declared deviation 1.
#
# usage: run-ob4b.sh RUNNAME CORPUSPATH K CHUNKS STORE POOL
RUNNAME=$1
CORPUS=$2
K=$3
CHUNKS=$4
STORE=$5
POOL=$6

BIN=/root/ob4b/llama.cpp/build/bin/llama-perplexity
MODEL=/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf
WT=/mnt/f/f32/openbob-wt/ob4/research/ob1
LOCAL=/root/ob4b/runs/$RUNNAME
STAGE=/mnt/f/f32/stage/research/ob4b/runs/$RUNNAME

mkdir -p "$LOCAL" "$STAGE"
RL=$LOCAL/route.log
rm -f "$RL"

echo "=== OB4B RUN $RUNNAME (K=$K CHUNKS=$CHUNKS STORE=$STORE POOL=$POOL) ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "runlock_held_by_me: $(ls -d /mnt/f/f32/stage/research/runlock 2>/dev/null)"
echo "free before:"; free -g | head -2
echo "bin: $(sha256sum $BIN | cut -d' ' -f1)"
echo "lib: $(sha256sum /root/ob4b/llama.cpp/build/bin/libllama.so.0.3.0 | cut -d' ' -f1)"

ARGS="-m $MODEL -f $CORPUS --ctx-size 1024 --chunks $CHUNKS -b 1024 -ub 1024 --threads 10 --threads-batch 10 --no-warmup --seed 1 -ngl 0 --no-mmap --no-repack"
echo "cmd: $BIN $ARGS"

T0=$(date +%s.%N)
if [ "$K" = "0" ]; then
  echo "env: fully resident (K=0), no lease engine, no OB4_STORE"
  CUDA_VISIBLE_DEVICES="" \
  LLAMA_ROUTE_LOG="$RL" \
  OB1_STATS="$LOCAL/ob1-stats.txt" \
  nice -n 10 /usr/bin/time -v $BIN $ARGS > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
  RC=$?
elif [ "$STORE" = "-" ]; then
  echo "env: OB1 mode (control), no OB4_STORE"
  CUDA_VISIBLE_DEVICES="" \
  LLAMA_ROUTE_LOG="$RL" \
  OB1_STATS="$LOCAL/ob1-stats.txt" \
  OB1_LEASE="$WT/RESIDENT-SETS.json" \
  OB1_K="$K" \
  OB1_MANIFEST="$WT/EXPERT-MANIFEST-20B.sha256" \
  OB1_GGUF="$MODEL" \
  OB1_FADV=0 \
  OB4B_DECODE_THREADS="$POOL" \
  nice -n 10 /usr/bin/time -v $BIN $ARGS > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
  RC=$?
else
  echo "env: OB4_STORE=$STORE OB4B_DECODE_THREADS=$POOL"
  CUDA_VISIBLE_DEVICES="" \
  LLAMA_ROUTE_LOG="$RL" \
  OB1_STATS="$LOCAL/ob1-stats.txt" \
  OB1_LEASE="$WT/RESIDENT-SETS.json" \
  OB1_K="$K" \
  OB1_MANIFEST="$WT/EXPERT-MANIFEST-20B.sha256" \
  OB1_GGUF="$MODEL" \
  OB1_FADV=0 \
  OB4_STORE="$STORE" \
  OB4B_DECODE_THREADS="$POOL" \
  nice -n 10 /usr/bin/time -v $BIN $ARGS > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
  RC=$?
fi
T1=$(date +%s.%N)

echo "exit_rc $RC"
echo "wallclock_s $(echo "$T1 - $T0" | bc)"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "--- OB4B / OB4 / OB1 banner ---"
grep -E '^OB4B|^OB4|^OB1' "$LOCAL/stderr.txt"
echo "--- peak rss / elapsed ---"
grep -E 'Maximum resident set size|Elapsed \(wall clock\)' "$LOCAL/stderr.txt"
echo "--- route log ---"
wc -l < "$RL"
sha256sum "$RL"
echo "--- identity artifact (the '[1]' per-chunk PPL line, same artifact OB-1 and OB-4 used) ---"
grep '^\[1\]' "$LOCAL/stdout.txt" > "$LOCAL/identity.txt"
wc -c < "$LOCAL/identity.txt"
sha256sum "$LOCAL/identity.txt"
cat "$LOCAL/identity.txt"
echo "--- stats ---"
grep -v '^chunk_ns' "$LOCAL/ob1-stats.txt"
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
exit $RC
