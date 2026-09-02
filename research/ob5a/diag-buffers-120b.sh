#!/bin/sh
# OB-5a builder 2b: THE P2c DENOMINATOR FOR THE 120b, MEASURED ON THE 120b.
#
# The day leg measured the compute/KV/output buffers on the 20b
# (research/ob5a/DIAG-BUFFERS-1.txt, 915046871 bytes) and P2c on the 20b rows
# used that figure. Those buffers are a function of the CONFIGURATION AND THE
# MODEL, and the 120b is a different model: n_embd, n_layer and the KV geometry
# all differ, so the 20b denominator must not be carried across. This run reads
# the 120b's own buffer sizes off the engine at -v, at the same frozen
# configuration as the P3 runs, one chunk, leased K=8.
#
# It is a DIAGNOSTIC. It makes no identity claim and is compared against no
# banked digest. It holds the runlock like every model run on this box and it
# records vm.overcommit_memory inside the locked window like every run of this
# leg.
LOCK=/mnt/f/f32/stage/research/runlock
BIN=/root/ob5a/llama.cpp/build/bin/llama-perplexity
MODEL=/root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf
SETS=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json
MAN=/mnt/f/f32/openbob-wt/research-2/research/ob1b/EXPERT-MANIFEST-120B.sha256
PROSE=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
L=/root/ob5a/runs/diag-120b-k8
STAGE=/mnt/f/f32/stage/research/ob5a/runs/diag-120b-k8
mkdir -p "$L" "$STAGE"
ARGS="-m $MODEL -f $PROSE --ctx-size 1024 --chunks 1 -b 1024 -ub 1024 --threads 8 --threads-batch 8 --no-warmup --seed 1 -ngl 0 --no-mmap --no-repack -v"

echo "=== OB5A 120B BUFFER DIAGNOSTIC (P2c denominator) ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "overcommit_before_lock: $(cat /proc/sys/vm/overcommit_memory)"

T0=$(date +%s)
echo "### LOCK REQUEST diag-120b-k8 at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
while ! mkdir "$LOCK" 2>/dev/null; do
  if [ $(( $(date +%s) - T0 )) -ge 7200 ]; then echo "### GIVING UP on runlock"; exit 75; fi
  sleep 5
done
echo "### LOCK ACQUIRED after $(( $(date +%s) - T0 ))s"
AVAIL=$(free -g | awk "/^Mem:/{print \$7}")
echo "### free RAM available: ${AVAIL} GB (house bar: 6 GB)"
if [ "$AVAIL" -lt 6 ]; then echo "### ABORT: ${AVAIL} GB below the 6 GB bar"; rmdir "$LOCK"; exit 76; fi
OC=$(cat /proc/sys/vm/overcommit_memory)
echo "overcommit_at_run: $OC"
if [ "$OC" != "0" ]; then echo "### ABORT: overcommit is $OC, not 0"; rmdir "$LOCK"; exit 77; fi

echo "cmd: $BIN $ARGS"
T1=$(date +%s.%N)
( echo 1000 > /proc/self/oom_score_adj
  exec env CUDA_VISIBLE_DEVICES="" OB5A_RESERVE=1 OB1_STATS=$L/ob1-stats.txt \
    OB1_LEASE=$SETS OB1_K=8 OB1_MANIFEST=$MAN OB1_GGUF=$MODEL \
    nice -n 10 /usr/bin/time -v $BIN $ARGS
) > $L/stdout.txt 2> $L/stderr.txt
RC=$?
T2=$(date +%s.%N)
rmdir "$LOCK"
echo "### LOCK RELEASED rc=$RC"
echo "exit_rc $RC"
echo "wallclock_s $(echo "$T2 - $T1" | bc)"
echo "overcommit_after_run: $(cat /proc/sys/vm/overcommit_memory)"

echo "--- every buffer the engine reports on the 120b, verbatim ---"
grep -E "buffer size|buf_size|KV self|model buffer|compute buffer|CPU_Reserve|CPU_Mapped|graph nodes|graph splits" $L/stderr.txt || echo "(no buffer lines matched)"
echo "--- the reserve allocator's own announcement, verbatim ---"
grep -E "OB5A reserved|OB5A reserve allocator" $L/stderr.txt || echo "(none printed at this level)"
echo "--- any fatal, verbatim ---"
grep -E "OB5A RESERVE FATAL|OB1 FATAL|Segmentation fault|Killed" $L/stderr.txt || echo "(none)"
echo "--- allocation counters ---"
grep -E "^alloc_|^proc_|^peak_|^lease_" $L/ob1-stats.txt 2>&1
echo "--- peak rss ---"
grep -E "Maximum resident set size" $L/stderr.txt
for f in stdout.txt stderr.txt ob1-stats.txt; do [ -f "$L/$f" ] && cp "$L/$f" "$STAGE/$f"; done
echo "guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "### courtesy yield 75s"
sleep 75
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== END 120B BUFFER DIAGNOSTIC rc=$RC ==="
