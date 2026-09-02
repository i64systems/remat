#!/bin/sh
# OB-1 baseline run driver. Adapted from research/rs053/run.sh (RS053's own
# route-log run driver) -- same binary lineage (research/rs053's llama.cpp
# fork, upstream commit ca3d5a3, route-log patch applied), same walls (at
# most 10 threads, nice 10, GPU allowed).
#
# IDENTITY ARTIFACT: this leg captures the tool's own stdout (the
# comma-separated per-chunk perplexity list, LOG("[%d]%.4lf,",...) at
# --ppl-output-type 0, the default) as the byte-comparable baseline
# artifact. See research/OB1-EXPOSURE-1-PREREG.md section on the identity
# artifact for why --save-all-logits/--kl-divergence-base (full per-token
# top-logprob dump, ~13 GB per run at this token budget) was considered and
# rejected.
#
# usage: run.sh RUNNAME MODELPATH CORPUSPATH CTX CHUNKS NBATCH NUBATCH [extra args...]
RUNNAME=$1; shift
MODEL=$1; shift
CORPUS=$1; shift
CTX=$1; shift
CHUNKS=$1; shift
NB=$1; shift
NUB=$1; shift

BIN=/root/rs053/llama.cpp/build/bin/llama-perplexity
LOCAL=/root/ob1/runs/$RUNNAME
STAGE=/mnt/f/f32/stage/research/ob1/runs/$RUNNAME
mkdir -p "$LOCAL" "$STAGE"
RL=$LOCAL/route.log
rm -f "$RL"

echo "=== OB1 RUN $RUNNAME ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "collector_before: $(ps -eo pid,comm,args | grep -E 'route_stats|c4run|c5run' | grep -v grep | wc -l) proc(s)"

CMD="$BIN -m $MODEL -f $CORPUS --ctx-size $CTX --chunks $CHUNKS -b $NB -ub $NUB --threads 10 --threads-batch 10 --no-warmup --seed 1 $*"
echo "cmd: LLAMA_ROUTE_LOG=$RL nice -n 10 $CMD"

T0=$(date +%s.%N)
LLAMA_ROUTE_LOG=$RL nice -n 10 /usr/bin/time -v $CMD > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
RC=$?
T1=$(date +%s.%N)

echo "exit_rc $RC"
echo "wallclock_s $(echo "$T1 - $T0" | bc)"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "--- peak rss / elapsed ---"
grep -E 'Maximum resident set size|Elapsed \(wall clock\)' "$LOCAL/stderr.txt"
echo "--- route log ---"
wc -l < "$RL"
sha256sum "$RL"
echo "--- stdout (raw, NOT the identity artifact -- see below) ---"
wc -c < "$LOCAL/stdout.txt"
sha256sum "$LOCAL/stdout.txt"
# IDENTITY ARTIFACT: raw stdout's first line is a wall-clock "N.NN minutes"
# preamble (plain LOG(), not LOG_INF, so it lands in stdout not stderr) that
# is NOT deterministic run to run (observed to differ between two otherwise
# byte-identical A/A runs on 2026-08-31: "0.30 minutes" vs "0.25 minutes"
# with an IDENTICAL per-chunk PPL line beneath it). The identity artifact is
# therefore the single line beginning "[1]" -- the comma-separated per-chunk
# perplexity list, LOG("[%d]%.4lf,",...) at --ppl-output-type 0 (default) --
# with that timing preamble excluded.
grep '^\[1\]' "$LOCAL/stdout.txt" > "$LOCAL/identity.txt"
cp "$LOCAL/identity.txt" "$STAGE/identity.txt"
echo "--- identity.txt (the actual identity artifact) ---"
wc -c < "$LOCAL/identity.txt"
sha256sum "$LOCAL/identity.txt"
echo "--- tokenization line ---"
grep -E 'tokeniz|have.*tokens' "$LOCAL/stderr.txt" | head -3
echo "--- timings ---"
grep -E 'load time|prompt eval time|eval time|total time' "$LOCAL/stderr.txt"
echo "collector_after: $(ps -eo pid,comm,args | grep -E 'route_stats|c4run|c5run' | grep -v grep | wc -l) proc(s)"

cp "$RL" "$STAGE/route.log"
cp "$LOCAL/stdout.txt" "$STAGE/stdout.txt"
cp "$LOCAL/stderr.txt" "$STAGE/stderr.txt"
echo "--- post-copy digest check ---"
sha256sum "$RL" "$STAGE/route.log"
sha256sum "$LOCAL/stdout.txt" "$STAGE/stdout.txt"
echo "=== END $RUNNAME rc=$RC ==="
