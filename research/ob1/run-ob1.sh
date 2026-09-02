#!/bin/sh
# OB-1 lease-engine run driver (stage 2).
#
# Same shape as research/ob1/run.sh (stage 1's baseline driver) and the same
# binary lineage (research/rs053's llama.cpp fork, upstream commit ca3d5a3,
# route-log patch applied, plus this leg's lease engine on branch ob1), with
# three differences that are named in RUNLOG-1.txt as deviations:
#
#   1. -ngl 0 + CUDA_VISIBLE_DEVICES="" : the whole model is computed on the
#      CPU, in host RAM. The lease engine's cold tier is the GGUF file on NVMe
#      and its fast tier is host RAM, so peak process RSS is a direct measure
#      of the exposure metric's denominator. Stage 1's committed baseline ran
#      -ngl 99 (all weights in VRAM), where the fast tier is a fixed-size VRAM
#      allocation that a lease cannot shrink without changing tensor shapes and
#      therefore the kernel.
#   2. --no-mmap : the expert tensors must be ordinary anonymous memory that the
#      lease engine can fill per expert and drop per expert (madvise). Under
#      mmap the tensor data is a private file mapping the loader never writes.
#   3. --no-repack : with weight repacking on, the CPU backend rewrites MXFP4
#      expert tensors into an interleaved layout at load time, so a GGUF byte
#      range is no longer the tensor's own bytes. Repacking is disabled for the
#      leased AND the resident runs alike, so the only difference between the
#      two is where the expert bytes came from.
#
# usage: run-ob1.sh RUNNAME CORPUSPATH K FADV
#   K=0    fully resident (baseline for this leg)
#   K>0    leased with that resident-set size
#   FADV=1 posix_fadvise(DONTNEED) each leased range after reading it
RUNNAME=$1
CORPUS=$2
K=$3
FADV=$4

BIN=/root/rs053/llama.cpp/build/bin/llama-perplexity
MODEL=/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf
WT=/mnt/f/f32/openbob-wt/research-2/research/ob1
LOCAL=/root/ob1/runs/$RUNNAME
STAGE=/mnt/f/f32/stage/research/ob1/runs/$RUNNAME

mkdir -p "$LOCAL" "$STAGE"
RL=$LOCAL/route.log
rm -f "$RL"

echo "=== OB1 RUN $RUNNAME (K=$K FADV=$FADV) ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"

ARGS="-m $MODEL -f $CORPUS --ctx-size 1024 --chunks 32 -b 1024 -ub 1024 --threads 10 --threads-batch 10 --no-warmup --seed 1 -ngl 0 --no-mmap --no-repack"
echo "cmd: $BIN $ARGS"
echo "env: LLAMA_ROUTE_LOG=$RL OB1_STATS=$LOCAL/ob1-stats.txt OB1_K=$K OB1_FADV=$FADV"

T0=$(date +%s.%N)
if [ "$K" = "0" ]; then
  CUDA_VISIBLE_DEVICES="" \
  LLAMA_ROUTE_LOG="$RL" \
  OB1_STATS="$LOCAL/ob1-stats.txt" \
  nice -n 10 /usr/bin/time -v $BIN $ARGS > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
  RC=$?
else
  CUDA_VISIBLE_DEVICES="" \
  LLAMA_ROUTE_LOG="$RL" \
  OB1_STATS="$LOCAL/ob1-stats.txt" \
  OB1_LEASE="$WT/RESIDENT-SETS.json" \
  OB1_K="$K" \
  OB1_MANIFEST="$WT/EXPERT-MANIFEST-20B.sha256" \
  OB1_GGUF="$MODEL" \
  OB1_FADV="$FADV" \
  nice -n 10 /usr/bin/time -v $BIN $ARGS > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
  RC=$?
fi
T1=$(date +%s.%N)

echo "exit_rc $RC"
echo "wallclock_s $(echo "$T1 - $T0" | bc)"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "--- peak rss / elapsed ---"
grep -E 'Maximum resident set size|Elapsed \(wall clock\)' "$LOCAL/stderr.txt"
echo "--- route log ---"
wc -l < "$RL"
sha256sum "$RL"
echo "--- identity artifact (the '[1]' per-chunk PPL line, per prereg section 5) ---"
grep '^\[1\]' "$LOCAL/stdout.txt" > "$LOCAL/identity.txt"
wc -c < "$LOCAL/identity.txt"
sha256sum "$LOCAL/identity.txt"
echo "--- ob1 stats ---"
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
