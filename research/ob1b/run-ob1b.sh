#!/bin/sh
# OB-1b lease-engine run driver.
#
# Same lineage and the same invocation shape as research/ob1/run-ob1.sh, with
# three differences, each named as a deviation in OB1B-KNEE-1.md:
#
#   1. AN EXPLICIT MODE ARGUMENT. OB-1's driver overloaded K=0 to mean "fully
#      resident baseline". OB-1b needs K=0 to mean the PURE STREAMING point (an
#      empty resident set, every routed expert leased on every use), which is a
#      different run entirely, so mode and K are separate arguments here.
#   2. --threads 8 --threads-batch 8, not 10, per this leg's house thread wall.
#      Because that changes the cost baseline, this leg runs its OWN fully
#      resident references at 8 threads rather than quoting OB-1's 10-thread p95.
#   3. mode=paged, an mmap-backed fully resident run, added for the 120b point
#      where a --no-mmap resident baseline cannot fit in this box's RAM.
#
# usage: run-ob1b.sh RUNNAME CORPUS MODE K SETS MODEL MANIFEST CHUNKS THREADS
#   MODE=resident  fully resident, --no-mmap  (the identity/cost reference)
#   MODE=lease     leased with resident-set size K (K=0 is pure streaming)
#   MODE=paged     fully resident, mmap ON, so the OS pages the file in and out
RUNNAME=$1
CORPUS=$2
MODE=$3
K=$4
SETS=$5
MODEL=$6
MANIFEST=$7
CHUNKS=$8
THREADS=$9

BIN=/root/ob1b/llama.cpp/build/bin/llama-perplexity
LOCAL=/root/ob1b/runs/$RUNNAME
STAGE=/mnt/f/f32/stage/research/ob1b/runs/$RUNNAME

mkdir -p "$LOCAL" "$STAGE"
RL=$LOCAL/route.log
rm -f "$RL"

echo "=== OB1B RUN $RUNNAME (mode=$MODE K=$K chunks=$CHUNKS threads=$THREADS) ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "bin_sha256: $(sha256sum $BIN | cut -d' ' -f1)"
echo "model: $MODEL"
echo "corpus_sha256: $(sha256sum $CORPUS | cut -d' ' -f1)"
echo "free_before:"
free -m

MMAP="--no-mmap"
if [ "$MODE" = "paged" ]; then MMAP=""; fi

ARGS="-m $MODEL -f $CORPUS --ctx-size 1024 --chunks $CHUNKS -b 1024 -ub 1024 --threads $THREADS --threads-batch $THREADS --no-warmup --seed 1 -ngl 0 $MMAP --no-repack"
echo "cmd: $BIN $ARGS"

T0=$(date +%s.%N)
if [ "$MODE" = "lease" ]; then
  echo "env: LLAMA_ROUTE_LOG=$RL OB1_STATS=$LOCAL/ob1-stats.txt OB1_LEASE=$SETS OB1_K=$K OB1_MANIFEST=$MANIFEST"
  CUDA_VISIBLE_DEVICES="" \
  LLAMA_ROUTE_LOG="$RL" \
  OB1_STATS="$LOCAL/ob1-stats.txt" \
  OB1_LEASE="$SETS" \
  OB1_K="$K" \
  OB1_MANIFEST="$MANIFEST" \
  OB1_GGUF="$MODEL" \
  nice -n 10 /usr/bin/time -v $BIN $ARGS > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
  RC=$?
else
  echo "env: LLAMA_ROUTE_LOG=$RL OB1_STATS=$LOCAL/ob1-stats.txt (no lease)"
  CUDA_VISIBLE_DEVICES="" \
  LLAMA_ROUTE_LOG="$RL" \
  OB1_STATS="$LOCAL/ob1-stats.txt" \
  nice -n 10 /usr/bin/time -v $BIN $ARGS > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
  RC=$?
fi
T1=$(date +%s.%N)

echo "exit_rc $RC"
echo "wallclock_s $(echo "$T1 - $T0" | bc)"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "--- peak rss / elapsed ---"
grep -E 'Maximum resident set size|Elapsed \(wall clock\)' "$LOCAL/stderr.txt" || echo "(no time -v block: process did not exit normally)"
echo "--- last 25 lines of stderr (verbatim, whether or not the run succeeded) ---"
tail -25 "$LOCAL/stderr.txt"
echo "--- route log ---"
if [ -f "$RL" ]; then wc -l < "$RL"; sha256sum "$RL"; else echo "(no route log)"; fi
echo "--- identity artifact (the '[1]' per-chunk PPL line) ---"
grep '^\[1\]' "$LOCAL/stdout.txt" > "$LOCAL/identity.txt" || true
wc -c < "$LOCAL/identity.txt"
sha256sum "$LOCAL/identity.txt"
echo "--- ob1 stats ---"
cat "$LOCAL/ob1-stats.txt" 2>&1 | head -40
echo "--- timings ---"
grep -E 'load time|prompt eval time|eval time|total time|seconds per pass' "$LOCAL/stderr.txt" || true
echo "free_after:"
free -m
echo "guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"

for f in route.log stdout.txt stderr.txt identity.txt ob1-stats.txt; do
  [ -f "$LOCAL/$f" ] && cp "$LOCAL/$f" "$STAGE/$f"
done
echo "=== END $RUNNAME rc=$RC ==="
