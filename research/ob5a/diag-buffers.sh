#!/bin/sh
# OB-5a stage 2: the P2c DENOMINATOR, measured rather than assumed.
#
# P2c reads VmHWM against "alloc_commit_model_peak plus the compute buffers the
# engine reports at load". At this build's default log level those buffer lines
# are not printed, so this run turns the log level up and reads them off. It is a
# DIAGNOSTIC, not one of the four P1 runs: it makes no identity claim and is not
# compared against any banked digest. The buffer sizes are a function of the
# configuration, not of the allocator, so one chunk is enough to read them.
#
# Two arms, both at 1 chunk, so the same denominator is available for the leased
# and the resident case:
#   diag-lease     OB5A_RESERVE=1, lease K=0
#   diag-resident  OB5A_RESERVE=1, no lease
# Both hold the runlock, like every model run on this box.
LOCK=/mnt/f/f32/stage/research/runlock
BIN=/root/ob5a/llama.cpp/build/bin/llama-perplexity
MODEL=/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf
PROSE=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
SETSK=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-KNEE.json
MAN=/mnt/f/f32/openbob-wt/research-2/research/ob1/EXPERT-MANIFEST-20B.sha256
ARGS="-m $MODEL -f $PROSE --ctx-size 1024 --chunks 1 -b 1024 -ub 1024 --threads 8 --threads-batch 8 --no-warmup --seed 1 -ngl 0 --no-mmap --no-repack -v"

echo "=== OB5A BUFFER DIAGNOSTIC ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"

for ARM in diag-lease diag-resident; do
  L=/root/ob5a/runs/$ARM
  mkdir -p $L
  T0=$(date +%s)
  echo "### LOCK REQUEST $ARM at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  while ! mkdir "$LOCK" 2>/dev/null; do
    if [ $(( $(date +%s) - T0 )) -ge 7200 ]; then echo "### GIVING UP on runlock for $ARM"; exit 75; fi
    sleep 5
  done
  echo "### LOCK ACQUIRED $ARM after $(( $(date +%s) - T0 ))s"
  AVAIL=$(free -g | awk "/^Mem:/{print \$7}")
  echo "### free RAM available: ${AVAIL} GB (house bar: 6 GB)"
  if [ "$AVAIL" -lt 6 ]; then echo "### ABORT $ARM: ${AVAIL} GB below the 6 GB bar"; rmdir "$LOCK"; exit 76; fi

  if [ "$ARM" = "diag-lease" ]; then
    CUDA_VISIBLE_DEVICES="" OB5A_RESERVE=1 OB1_STATS=$L/ob1-stats.txt \
      OB1_LEASE=$SETSK OB1_K=0 OB1_MANIFEST=$MAN OB1_GGUF=$MODEL \
      nice -n 10 $BIN $ARGS > $L/stdout.txt 2> $L/stderr.txt
  else
    CUDA_VISIBLE_DEVICES="" OB5A_RESERVE=1 OB1_STATS=$L/ob1-stats.txt \
      nice -n 10 $BIN $ARGS > $L/stdout.txt 2> $L/stderr.txt
  fi
  RC=$?
  rmdir "$LOCK"
  echo "### LOCK RELEASED $ARM rc=$RC"

  echo "--- $ARM: every buffer the engine reports, verbatim ---"
  grep -E "buffer size|buf_size|KV self|model buffer|compute buffer|CPU_Reserve|CPU_Mapped|graph nodes|graph splits" $L/stderr.txt || echo "(no buffer lines matched)"
  echo "--- $ARM: the reserve allocator's own announcement, verbatim ---"
  grep -E "OB5A reserved" $L/stderr.txt || echo "(none printed at this level)"
  echo "--- $ARM: allocation counters ---"
  grep -E "^alloc_|^proc_" $L/ob1-stats.txt
  echo "### courtesy yield 75s"
  sleep 75
done
echo "guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== END BUFFER DIAGNOSTIC ==="
