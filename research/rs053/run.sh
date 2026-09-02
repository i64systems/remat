#!/bin/sh
# RS053 route-log run driver, verbatim as used on hyde 2026-08-31.
# usage: run.sh RUNNAME MODELPATH CORPUSPATH CTX CHUNKS NBATCH NUBATCH [extra args...]
#
# Route log is written to fast local ext4 first, then copied to the stage dir by
# stage.sh; drvfs write throughput is poor for 1.5M-line files. Digests are
# verified on both sides after the copy.
#
# Walls: at most 10 threads, nice 10. GPU is allowed for this lane.
RUNNAME=$1; shift
MODEL=$1; shift
CORPUS=$1; shift
CTX=$1; shift
CHUNKS=$1; shift
NB=$1; shift
NUB=$1; shift

BIN=/root/rs053/llama.cpp/build/bin/llama-perplexity
LOCAL=/root/rs053/runs/$RUNNAME
STAGE=/mnt/f/f32/stage/research/rs053/runs/$RUNNAME
mkdir -p "$LOCAL" "$STAGE"
RL=$LOCAL/route.log
rm -f "$RL"

echo "=== RS053 RUN $RUNNAME ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "collector_before: $(ps -eo pid,comm,args | grep -E 'route_stats|c4run|c5run' | grep -v grep | wc -l) proc(s)"
ps -eo pid,etime,args | grep -E 'route_stats|c4run|c5run' | grep -v grep

CMD="$BIN -m $MODEL -f $CORPUS --ctx-size $CTX --chunks $CHUNKS -b $NB -ub $NUB --threads 10 --threads-batch 10 --no-warmup --seed 1 $*"
echo "cmd: LLAMA_ROUTE_LOG=$RL nice -n 10 $CMD"

T0=$(date +%s.%N)
LLAMA_ROUTE_LOG=$RL nice -n 10 /usr/bin/time -v $CMD > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
RC=$?
T1=$(date +%s.%N)

echo "exit_rc $RC"
echo "wallclock_s $(echo "$T1 - $T0" | bc)"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "--- peak rss ---"
grep -E 'Maximum resident set size|Elapsed \(wall clock\)' "$LOCAL/stderr.txt"
echo "--- route log ---"
ls -l "$RL"
wc -l < "$RL"
echo "--- sha256 ---"
sha256sum "$RL"
echo "--- first 3 lines ---"
head -3 "$RL"
echo "--- last 3 lines ---"
tail -3 "$RL"
echo "collector_after: $(ps -eo pid,comm,args | grep -E 'route_stats|c4run|c5run' | grep -v grep | wc -l) proc(s)"
ps -eo pid,etime,args | grep -E 'route_stats|c4run|c5run' | grep -v grep
echo "=== END $RUNNAME rc=$RC ==="
