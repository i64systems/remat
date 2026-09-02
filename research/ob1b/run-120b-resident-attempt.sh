#!/bin/sh
# OB-1b: the gpt-oss-120b FULLY RESIDENT baseline attempt.
#
# This run is EXPECTED TO FAIL, and its failure is the finding. The arithmetic is
# not in doubt: the model file is 63387346208 bytes and this box's WSL guest has
# 24029 MB of RAM plus 6144 MB of swap, so a --no-mmap run, which must hold every
# expert tensor in anonymous memory, cannot fit by a factor of more than two.
#
# WHY IT IS RUN UNDER A CAP RATHER THAN LET LOOSE. An uncapped 63 GB allocation
# on a 24 GB box invites the kernel OOM killer, and the OOM killer picks its own
# victim: it could take pid 654 (openbob serve), pid 489 (searxng), or a sibling
# workflow's in-flight run, none of which this leg is allowed to disturb. So the
# attempt runs inside a subshell with an address-space cap (ulimit -v) and with
# its own oom_score_adj pinned to the maximum, which makes the allocation fail
# cleanly INSIDE this process and makes this process the OOM killer's first
# choice if it somehow still fires. The failure message is recorded verbatim.
#
# usage: run-120b-resident-attempt.sh CAP_KB
CAP_KB=${1:-22000000}
BIN=/root/ob1b/llama.cpp/build/bin/llama-perplexity
MODEL=/root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf
CORPUS=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
LOCAL=/root/ob1b/runs/res120-nomm-prose
STAGE=/mnt/f/f32/stage/research/ob1b/runs/res120-nomm-prose
mkdir -p "$LOCAL" "$STAGE"

echo "=== OB1B 120B RESIDENT BASELINE ATTEMPT (expected infeasible) ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "--- the arithmetic this run is testing ---"
echo "model_bytes      $(stat -c %s $MODEL)"
echo "wsl_ram_and_swap (free -m):"
free -m
echo "address_space_cap_kb $CAP_KB"

ARGS="-m $MODEL -f $CORPUS --ctx-size 1024 --chunks 8 -b 1024 -ub 1024 --threads 8 --threads-batch 8 --no-warmup --seed 1 -ngl 0 --no-mmap --no-repack"
echo "cmd: $BIN $ARGS"

T0=$(date +%s.%N)
(
  echo 1000 > /proc/self/oom_score_adj 2>/dev/null
  ulimit -v $CAP_KB
  CUDA_VISIBLE_DEVICES="" \
  OB1_STATS="$LOCAL/ob1-stats.txt" \
  exec nice -n 10 /usr/bin/time -v $BIN $ARGS
) > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
RC=$?
T1=$(date +%s.%N)

echo "exit_rc $RC"
echo "wallclock_s $(echo "$T1 - $T0" | bc)"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "--- stdout, verbatim ---"
cat "$LOCAL/stdout.txt"
echo "--- stderr, verbatim (this is the finding) ---"
cat "$LOCAL/stderr.txt"
echo "--- guards after ---"
echo "guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "--- any OOM kill in the kernel ring buffer? ---"
dmesg 2>/dev/null | tail -20 | grep -i -E "oom|killed process" || echo "(no oom lines in the last 20 dmesg lines)"
free -m

for f in stdout.txt stderr.txt ob1-stats.txt; do
  [ -f "$LOCAL/$f" ] && cp "$LOCAL/$f" "$STAGE/$f"
done
echo "=== END res120-nomm-prose rc=$RC ==="
