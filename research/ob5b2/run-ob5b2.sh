#!/bin/sh
# OB-5b P05 (C8-S8-2) limb (b): one live run at a chosen micro-batch shape.
#
# Same lineage and the same invocation shape as research/ob1b/run-ob1b.sh,
# with ONE difference, which is the whole point of this row: -ub is an
# argument instead of being hard-wired to 1024. Everything else (engine,
# model, corpus, sets, manifest, ctx-size, -b, threads, seed, --no-mmap,
# --no-repack, --no-warmup, -ngl 0, CUDA_VISIBLE_DEVICES="") is byte-for-byte
# the ob1b driver's, so that a difference in the output is a difference in
# the micro-batch shape and nothing else.
#
# usage: run-ob5b2.sh RUNNAME CORPUS K SETS MODEL MANIFEST CHUNKS THREADS UB
RUNNAME=$1
CORPUS=$2
K=$3
SETS=$4
MODEL=$5
MANIFEST=$6
CHUNKS=$7
THREADS=$8
UB=$9

BIN=/root/ob1b/llama.cpp/build/bin/llama-perplexity
LOCAL=/root/ob5b2/runs/$RUNNAME
STAGE=/mnt/f/f32/stage/research/ob5b2/runs/$RUNNAME

mkdir -p "$LOCAL" "$STAGE"
RL=$LOCAL/route.log
rm -f "$RL"

echo "=== OB5B2 RUN $RUNNAME (K=$K chunks=$CHUNKS threads=$THREADS ubatch=$UB) ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "bin_sha256: $(sha256sum $BIN | cut -d' ' -f1)"
echo "model: $MODEL"
echo "corpus_sha256: $(sha256sum $CORPUS | cut -d' ' -f1)"
echo "sets_sha256: $(sha256sum $SETS | cut -d' ' -f1)"
echo "free_before:"
free -m

ARGS="-m $MODEL -f $CORPUS --ctx-size 1024 --chunks $CHUNKS -b 1024 -ub $UB --threads $THREADS --threads-batch $THREADS --no-warmup --seed 1 -ngl 0 --no-mmap --no-repack"
echo "cmd: $BIN $ARGS"
echo "env: LLAMA_ROUTE_LOG=$RL OB1_STATS=$LOCAL/ob1-stats.txt OB1_LEASE=$SETS OB1_K=$K OB1_MANIFEST=$MANIFEST"

T0=$(date +%s.%N)
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
echo "--- last 25 lines of stderr (verbatim, whether or not the run succeeded) ---"
tail -25 "$LOCAL/stderr.txt"
echo "--- route log ---"
if [ -f "$RL" ]; then wc -l < "$RL"; sha256sum "$RL"; else echo "(no route log)"; fi
echo "--- identity artifact (the '[1]' per-chunk PPL line) ---"
grep '^\[1\]' "$LOCAL/stdout.txt" > "$LOCAL/identity.txt" || true
wc -c < "$LOCAL/identity.txt"
cat "$LOCAL/identity.txt"
sha256sum "$LOCAL/identity.txt"
echo "--- ob1 stats ---"
cat "$LOCAL/ob1-stats.txt" 2>&1
echo "--- timings ---"
grep -E 'load time|prompt eval time|eval time|total time|seconds per pass' "$LOCAL/stderr.txt" || true
echo "free_after:"
free -m
echo "guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"

for f in route.log stdout.txt stderr.txt identity.txt ob1-stats.txt; do
  [ -f "$LOCAL/$f" ] && cp "$LOCAL/$f" "$STAGE/$f"
done
echo "=== END $RUNNAME rc=$RC ==="
