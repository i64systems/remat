#!/bin/sh
# OB4-REMAT-1 run driver (phase 2).
#
# Identical in shape and flags to research/ob1/run-ob1.sh (the driver that
# produced the banked OB-1 reference runs), with two differences:
#
#   1. BIN is this leg's own build of the fork worktree /root/ob4/llama.cpp
#      (branch ob4, based on fork HEAD c087083), which carries the remat engine.
#   2. When STORE is a path rather than "-", OB4_STORE points the lease path at
#      the compressed container: every expert slice, resident-at-load and leased
#      alike, is rematerialized by deterministic split-stream zstd decode and
#      then sha256-verified against the SAME OB-1 manifest row as before.
#
# STORE="-" runs the engine in plain OB-1 mode. That is this leg's control arm:
# it isolates "did the store change the output" from "did rebuilding the binary
# change the output".
#
# usage: run-ob4.sh RUNNAME CORPUSPATH K CHUNKS STORE
RUNNAME=$1
CORPUS=$2
K=$3
CHUNKS=$4
STORE=$5

BIN=/root/ob4/llama.cpp/build/bin/llama-perplexity
MODEL=/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf
WT=/mnt/f/f32/openbob-wt/ob4/research/ob1
LOCAL=/root/ob4/runs/$RUNNAME
STAGE=/mnt/f/f32/stage/research/ob4/runs/$RUNNAME

mkdir -p "$LOCAL" "$STAGE"
RL=$LOCAL/route.log
rm -f "$RL"

echo "=== OB4 RUN $RUNNAME (K=$K CHUNKS=$CHUNKS STORE=$STORE) ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "runlock_held_by_me: $(ls -d /mnt/f/f32/stage/research/runlock 2>/dev/null)"

ARGS="-m $MODEL -f $CORPUS --ctx-size 1024 --chunks $CHUNKS -b 1024 -ub 1024 --threads 10 --threads-batch 10 --no-warmup --seed 1 -ngl 0 --no-mmap --no-repack"
echo "cmd: $BIN $ARGS"

T0=$(date +%s.%N)
if [ "$K" = "0" ]; then
  # fully resident reference, exactly as research/ob1/run-ob1.sh runs it: no
  # lease engine at all, stats only. This leg's own resident baseline, made with
  # THIS binary, so the cost limb compares like with like.
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
  nice -n 10 /usr/bin/time -v $BIN $ARGS > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
  RC=$?
else
  echo "env: OB4_STORE=$STORE"
  CUDA_VISIBLE_DEVICES="" \
  LLAMA_ROUTE_LOG="$RL" \
  OB1_STATS="$LOCAL/ob1-stats.txt" \
  OB1_LEASE="$WT/RESIDENT-SETS.json" \
  OB1_K="$K" \
  OB1_MANIFEST="$WT/EXPERT-MANIFEST-20B.sha256" \
  OB1_GGUF="$MODEL" \
  OB1_FADV=0 \
  OB4_STORE="$STORE" \
  nice -n 10 /usr/bin/time -v $BIN $ARGS > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
  RC=$?
fi
T1=$(date +%s.%N)

echo "exit_rc $RC"
echo "wallclock_s $(echo "$T1 - $T0" | bc)"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "--- OB4 banner ---"
grep -E '^OB4|^OB1' "$LOCAL/stderr.txt"
echo "--- peak rss / elapsed ---"
grep -E 'Maximum resident set size|Elapsed \(wall clock\)' "$LOCAL/stderr.txt"
echo "--- route log ---"
wc -l < "$RL"
sha256sum "$RL"
echo "--- identity artifact (the '[1]' per-chunk PPL line, same artifact OB-1 used) ---"
grep '^\[1\]' "$LOCAL/stdout.txt" > "$LOCAL/identity.txt"
wc -c < "$LOCAL/identity.txt"
sha256sum "$LOCAL/identity.txt"
cat "$LOCAL/identity.txt"
echo "--- stats ---"
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
