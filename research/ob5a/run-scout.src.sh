#!/bin/sh
# OB-5a SCOUT run driver. Clone of research/ob1b/run-ob1b.sh with scout
# paths; the binary is the LANDED ob1b engine (the scout measures the
# knob, not the new allocator). usage:
#   run-scout.sh RUNNAME CORPUS MODE K SETS MODEL MANIFEST CHUNKS THREADS
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
LOCAL=/root/ob5a-scout/runs/$RUNNAME
STAGE=/mnt/f/f32/stage/research/ob5a/runs-scout/$RUNNAME

mkdir -p "$LOCAL" "$STAGE"
RL=$LOCAL/route.log
rm -f "$RL"

echo "=== SCOUT RUN $RUNNAME (mode=$MODE K=$K chunks=$CHUNKS threads=$THREADS) ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "bin_sha256: $(sha256sum $BIN | cut -d' ' -f1)"
echo "model: $MODEL"
echo "corpus_sha256: $(sha256sum $CORPUS | cut -d' ' -f1)"
echo "overcommit_at_run: $(cat /proc/sys/vm/overcommit_memory)"
echo "free_before:"
free -m

MMAP="--no-mmap"
if [ "$MODE" = "paged" ]; then MMAP=""; fi

ARGS="-m $MODEL -f $CORPUS --ctx-size 1024 --chunks $CHUNKS -b 1024 -ub 1024 --threads $THREADS --threads-batch $THREADS --no-warmup --seed 1 -ngl 0 $MMAP --no-repack"
echo "cmd: $BIN $ARGS"

T0=$(date +%s.%N)
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
T1=$(date +%s.%N)

echo "exit_rc $RC"
echo "wallclock_s $(echo "$T1 - $T0" | bc)"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "--- peak rss / elapsed ---"
grep -E 'Maximum resident set size|Elapsed \(wall clock\)' "$LOCAL/stderr.txt" || echo "(no time -v block: process did not exit normally)"
echo "--- last 25 lines of stderr (verbatim) ---"
tail -25 "$LOCAL/stderr.txt"
echo "--- route log ---"
if [ -f "$RL" ]; then wc -l < "$RL"; sha256sum "$RL"; else echo "(no route log)"; fi
echo "--- identity artifact ---"
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
exit $RC
