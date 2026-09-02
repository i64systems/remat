#!/bin/sh
# OB-2 lease-engine run driver.
#
# Same binary lineage, same flags and the same three deviations as OB-1's
# research/ob1/run-ob1.sh (-ngl 0 with CUDA_VISIBLE_DEVICES="" so the fast tier
# is host RAM and peak RSS is a real measurement; --no-mmap so expert tensors are
# ordinary anonymous memory the engine can fill and drop per expert; --no-repack
# so a GGUF byte range is still the tensor's own bytes). The ONLY difference is
# the residency policy: OB-1 read a fixed set out of RESIDENT-SETS.json, OB-2
# recomputes it every OB2_H tokens from the route history it has already seen.
#
# RUNLOCK LAW: this script does NOT take the box-wide lock itself. The caller
# (runs-ob2.sh) acquires it before the run and releases it immediately after the
# model process exits, so the sibling workflow can interleave between runs.
#
# usage: run-ob2.sh RUNNAME CORPUSPATH K CHUNKS [TRACE]
#   K       resident-set size for the dynamic policy (16 or 8)
#   CHUNKS  32 for a full acceptance run, fewer for the unit
#   TRACE   optional path: dump the resident-set schedule for a byte-compare
#           against research/ob2/sim_trace.py. Passed through as OB2_TRACE
#           unconditionally: the engine treats an EMPTY env value as unset (see
#           ob1_env), and a conditional ${TRACE:+OB2_TRACE=$TRACE} prefix does
#           NOT work here -- sh parses assignments in the command prefix
#           grammatically, so an expansion that produces "VAR=value" is taken as
#           a command name and fails with 127.
RUNNAME=$1
CORPUS=$2
K=$3
CHUNKS=$4
TRACE=$5

BIN=/root/ob2/llama.cpp/build/bin/llama-perplexity
MODEL=/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf
WT=/mnt/f/f32/openbob-wt/research-2/research/ob1
LOCAL=/root/ob2/runs/$RUNNAME
STAGE=/mnt/f/f32/stage/research/ob2/runs/$RUNNAME

mkdir -p "$LOCAL" "$STAGE"
RL=$LOCAL/route.log
rm -f "$RL"

echo "=== OB2 RUN $RUNNAME (K=$K CHUNKS=$CHUNKS TRACE=${TRACE:-off}) ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "free_ram_gb: $(free -g | awk '/^Mem:/ {print $7}')"
echo "runlock_held_by_this_leg: $(ls -d /mnt/f/f32/stage/research/runlock 2>/dev/null || echo MISSING)"

ARGS="-m $MODEL -f $CORPUS --ctx-size 1024 --chunks $CHUNKS -b 1024 -ub 1024 --threads 8 --threads-batch 8 --no-warmup --seed 1 -ngl 0 --no-mmap --no-repack"
echo "cmd: $BIN $ARGS"
echo "env: OB2_POLICY=p2decay OB2_K=$K OB2_H=256 OB2_ADD=65536 OB2_SHIFT=1"

T0=$(date +%s.%N)
CUDA_VISIBLE_DEVICES="" \
LLAMA_ROUTE_LOG="$RL" \
OB1_STATS="$LOCAL/ob2-stats.txt" \
OB1_MANIFEST="$WT/EXPERT-MANIFEST-20B.sha256" \
OB1_GGUF="$MODEL" \
OB1_FADV=0 \
OB2_POLICY=p2decay \
OB2_K="$K" \
OB2_H=256 \
OB2_ADD=65536 \
OB2_SHIFT=1 \
OB2_TRACE="$TRACE" \
nice -n 10 /usr/bin/time -v $BIN $ARGS > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
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
echo "--- identity artifact (the per-chunk PPL line, same artifact OB-1 used) ---"
grep '^\[1\]' "$LOCAL/stdout.txt" > "$LOCAL/identity.txt"
wc -c < "$LOCAL/identity.txt"
sha256sum "$LOCAL/identity.txt"
echo "--- ob2 stats ---"
cat "$LOCAL/ob2-stats.txt"
echo "--- timings ---"
grep -E 'load time|prompt eval time|eval time|total time|seconds per pass' "$LOCAL/stderr.txt"
echo "guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"

cp "$RL" "$STAGE/route.log"
cp "$LOCAL/stdout.txt" "$STAGE/stdout.txt"
cp "$LOCAL/stderr.txt" "$STAGE/stderr.txt"
cp "$LOCAL/identity.txt" "$STAGE/identity.txt"
cp "$LOCAL/ob2-stats.txt" "$STAGE/ob2-stats.txt"
if [ -n "$TRACE" ] && [ -f "$TRACE" ]; then
  cp "$TRACE" "$STAGE/engine-trace.raw.txt"
fi
echo "--- post-copy digest check ---"
sha256sum "$RL" "$STAGE/route.log"
sha256sum "$LOCAL/identity.txt" "$STAGE/identity.txt"
echo "=== END $RUNNAME rc=$RC ==="
exit $RC
