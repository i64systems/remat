#!/bin/sh
# OB-5b S1 GATE 2: DECODE MEASURED HONESTLY ON THE 120b.
#
# THE BAR (OB5-DESIGN-C4-1.md section 12, gate 2): "tok/s decode and time-to-
# first-token at K=8 and at the largest K whose committed state fits with 6 GB
# free, with the decode-regime ACCT reported. BAR: the numbers are literal
# command output; section 6.1's 10.1629 prediction is confirmed or refuted by
# measurement; K2 and K3 are evaluated."
#
# THE ENGINE IS BIT-FOR-BIT GATE 1's. No source of the lease engine, the
# allocator or the generation entry point was touched by this leg, so gate 1's
# .text lineage proof still covers every run below and gate 1's identity claim
# is directly comparable to gate 2's. Leg A's item (a) offered two ways to
# get a decode-only peak concurrent figure and called either acceptable; this
# leg takes the second (a turn whose prefill is as narrow as its decode) plus an
# exact derivation from each run's own route log, because the first would change
# libllama's .text and void the lineage proof gate 1 rests on.
#
# House run discipline in full, per run: mkdir runlock with a 5 s poll, free RAM
# >= 6 GB inside the lock, overcommit read inside the lock with a non-zero value
# fatal, guards 654 and 489 confirmed before and after, nice 10, 8 threads, 75 s
# courtesy yield. Every perf data point our standing order names is banked.
set -e

LOCK=/mnt/f/f32/stage/research/runlock
DST=/root/ob5b1/llama.cpp
BIN=$DST/build/bin/ob5b1-gen
MODEL=/root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf
SETS8=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json
SETSN=/root/ob5b2/g2/RESIDENT-SETS-120B-K8-16-24-32.json
MAN=/mnt/f/f32/openbob-wt/research-2/research/ob1b/EXPERT-MANIFEST-120B.sha256
P=/mnt/f/f32/stage/research/ob5b1
N_CTX=512
THREADS=8
TRUNK=2314020128
PEREXP=13253760

echo "=== OB5B1 S1 GATE 2: DECODE MEASURED HONESTLY, gpt-oss-120b LEASED ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "--- the engine under test (gate 1's, unchanged) ---"
echo "gen_bin_sha256   $(sha256sum $BIN | cut -d' ' -f1)"
echo "gen_src_sha256   $(sha256sum $DST/ob5b1-gen.cpp | cut -d' ' -f1)"
echo "libllama_sha256  $(sha256sum $DST/build/bin/libllama.so.0 | cut -d' ' -f1)"
echo "libggmlbase_sha  $(sha256sum $DST/build/bin/libggml-base.so.0 | cut -d' ' -f1)"
echo "libggmlcpu_sha   $(sha256sum $DST/build/bin/libggml-cpu.so.0 | cut -d' ' -f1)"
echo "--- the bound state's file members ---"
echo "model_bytes      $(stat -c %s $MODEL)"
echo "sets_K8_sha256   $(sha256sum $SETS8 | cut -d' ' -f1)"
echo "sets_sweep_sha   $(sha256sum $SETSN | cut -d' ' -f1)"
echo "manifest_sha256  $(sha256sum $MAN | cut -d' ' -f1)"
for f in PROMPT-1.txt PROMPT-2.txt PROMPT-3.txt PROMPT-4.txt; do
  echo "prompt $f  $(stat -c %s $P/$f) bytes  $(sha256sum $P/$f | cut -d' ' -f1)"
done
echo ""

one_run() {   # one_run <runname> <K> <setsfile> <promptfile> <ubatch> <npredict>
  RUNNAME=$1; K=$2; SETS=$3; PROMPT=$4; UB=$5; NP=$6
  LOCAL=/root/ob5b2/runs/$RUNNAME
  STAGE=/mnt/f/f32/stage/research/ob5b2/runs/$RUNNAME
  mkdir -p "$LOCAL" "$STAGE"
  RL=$LOCAL/route.log
  JL=$LOCAL/alloc-journal.txt
  rm -f "$RL" "$JL" "$LOCAL"/gen-*.txt "$LOCAL"/prompt-ids.txt

  echo "--------------------------------------------------------------"
  echo "### RUN $RUNNAME  K=$K  prompt=$(basename $PROMPT)  ubatch=$UB  n_predict=$NP"
  echo "### sets $SETS"
  echo "### utc $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "### guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"

  T0=$(date +%s)
  echo "### LOCK REQUEST at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  while ! mkdir "$LOCK" 2>/dev/null; do
    W=$(( $(date +%s) - T0 ))
    if [ $W -ge 7200 ]; then echo "### GIVING UP on runlock after ${W}s"; return 75; fi
    sleep 5
  done
  echo "### LOCK ACQUIRED after $(( $(date +%s) - T0 ))s"

  AVAIL=$(free -g | awk '/^Mem:/{print $7}')
  echo "### free RAM available: ${AVAIL} GB (house bar: 6 GB)"
  if [ "$AVAIL" -lt 6 ]; then
    echo "### ABORT $RUNNAME: free RAM ${AVAIL} GB below the 6 GB house bar"
    rmdir "$LOCK"; return 76
  fi
  OC=$(cat /proc/sys/vm/overcommit_memory)
  echo "### overcommit_at_run: $OC"
  if [ "$OC" != "0" ]; then
    echo "### ABORT $RUNNAME: vm.overcommit_memory is $OC, not 0."
    rmdir "$LOCK"; return 77
  fi
  echo "### free_before:"; free -m

  TS=$(date +%s.%N)
  set +e
  ( cd "$LOCAL" && \
    CUDA_VISIBLE_DEVICES="" \
    OB5A_RESERVE=1 \
    OB5A_ALLOC_JOURNAL="$JL" \
    LLAMA_ROUTE_LOG="$RL" \
    OB1_STATS="$LOCAL/ob1-stats.txt" \
    OB1_LEASE="$SETS" \
    OB1_K=$K \
    OB1_MANIFEST="$MAN" \
    OB1_GGUF="$MODEL" \
    LD_LIBRARY_PATH="$DST/build/bin" \
    nice -n 10 /usr/bin/time -v "$BIN" \
      --model "$MODEL" --prompt-file "$PROMPT" --out-dir "$LOCAL" \
      --n-predict $NP --ctx $N_CTX --ubatch $UB --threads $THREADS \
      > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt" )
  RC=$?
  set -e
  TE=$(date +%s.%N)

  echo "### overcommit_after_run: $(cat /proc/sys/vm/overcommit_memory)"
  rmdir "$LOCK"
  echo "### LOCK RELEASED at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "### exit_rc $RC"
  echo "### wallclock_s $(echo "$TE - $TS" | bc)"
  echo "### guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
  echo "### free_after:"; free -m

  echo "--- any fatal, verbatim ---"
  grep -E "OB5A RESERVE FATAL|OB1 FATAL|OB5B1-GEN FATAL|Segmentation fault|std::bad_alloc|Killed|out of memory" \
    "$LOCAL/stderr.txt" || echo "(none)"
  echo "--- stdout, verbatim ---"
  cat "$LOCAL/stdout.txt"
  echo "--- the allocator announced itself, verbatim ---"
  grep -E "OB5A reserved|OB5A reserve allocator|allocation journal|OB1: lease engine" \
    "$LOCAL/stderr.txt" || echo "(NO ALLOCATOR LINES)"
  echo "--- generated text, verbatim ---"
  cat "$LOCAL/gen-text.txt" 2>/dev/null || echo "(no gen-text.txt)"
  echo ""
  echo "--- ob1 stats, verbatim ---"
  cat "$LOCAL/ob1-stats.txt" 2>&1 || true
  echo "--- peak rss / elapsed, verbatim ---"
  grep -E 'Maximum resident set size|Elapsed \(wall clock\)' "$LOCAL/stderr.txt" || true
  echo "--- artifact digests ---"
  sha256sum "$LOCAL/gen-ids.txt" "$LOCAL/gen-text.txt" "$LOCAL/prompt-ids.txt" 2>/dev/null || true
  if [ -f "$RL" ]; then
    echo "route_log_lines  $(wc -l < "$RL")"
    sha256sum "$RL"
  else
    echo "(no route log)"
  fi
  if [ -f "$JL" ]; then
    echo "alloc_journal_file_bytes $(stat -c %s "$JL")"
    sha256sum "$JL"
    gzip -9 -c "$JL" > "$STAGE/alloc-journal.txt.gz"
    rm -f "$JL"
  fi
  for f in stdout.txt stderr.txt gen-ids.txt gen-text.txt prompt-ids.txt ob1-stats.txt route.log; do
    [ -f "$LOCAL/$f" ] && cp "$LOCAL/$f" "$STAGE/$f"
  done
  echo "### ACCT, from this run's own counters plus the frozen trunk $TRUNK"
  RB=$(grep '^resident_bytes_loaded=' "$LOCAL/ob1-stats.txt" | cut -d= -f2 || echo 0)
  PC=$(grep '^peak_concurrent_lease_bytes=' "$LOCAL/ob1-stats.txt" | cut -d= -f2 || echo 0)
  if [ -n "$RB" ] && [ -n "$PC" ] && [ "$RB" != "0" ]; then
    python3 -c "
t=$TRUNK; r=$RB; p=$PC
a=t+r+p
print('  resident_always      %d' % t)
print('  resident_bytes       %d' % r)
print('  peak_concurrent      %d  = %.10f experts' % (p, p/$PEREXP))
print('  ACCT_whole_run       %d' % a)
print('  EXPOSURE_acct        %.6f' % (63387346208/a))
"
  fi
  echo "### courtesy yield 75 s"
  sleep 75
  return $RC
}

PHASE="$1"

if [ "$PHASE" = "A" ] || [ "$PHASE" = "ALL" ]; then
  one_run g2-k8-p1-a   8  "$SETS8" "$P/PROMPT-1.txt" 64 64 || echo "### run returned $?"
  one_run g2-k8-p1-b   8  "$SETS8" "$P/PROMPT-1.txt" 64 64 || echo "### run returned $?"
  one_run g2-k8-p2     8  "$SETS8" "$P/PROMPT-2.txt" 64 64 || echo "### run returned $?"
  one_run g2-k8-p3     8  "$SETS8" "$P/PROMPT-3.txt" 64 64 || echo "### run returned $?"
fi

# PHASES B2 AND C2 ARE THE SAME RUNS IN PRIORITY ORDER. They were written after
# a SIBLING RESEARCH WORKFLOW took the house runlock for a 20b run at
# 2026-09-01T19:35:11Z, which is the runlock law working exactly as designed and
# is declared as deviation D2 of this leg rather than worked around. Under
# contention the K sweep on one prompt is what the gate 2 bar needs first.
if [ "$PHASE" = "B2" ]; then
  one_run g2-k16-p1   16  "$SETSN" "$P/PROMPT-1.txt" 64 64 || echo "### run returned $?"
  one_run g2-k24-p1   24  "$SETSN" "$P/PROMPT-1.txt" 64 64 || echo "### run returned $?"
  one_run g2-k32-p1   32  "$SETSN" "$P/PROMPT-1.txt" 64 64 || echo "### run returned $?"
fi

if [ "$PHASE" = "C2" ]; then
  # THE NARROW-PREFILL CONTROL FIRST: it is the direct engine measurement of
  # the decode-regime peak concurrent lease bytes, which is the gate's own
  # "with the decode-regime ACCT reported" clause.
  one_run g2-k8-p4-narrow  8 "$SETS8" "$P/PROMPT-4.txt" 64 32 || echo "### run returned $?"
  one_run g2-k32-p2       32 "$SETSN" "$P/PROMPT-2.txt" 64 64 || echo "### run returned $?"
  one_run g2-k16-p2       16 "$SETSN" "$P/PROMPT-2.txt" 64 64 || echo "### run returned $?"
  one_run g2-k24-p2       24 "$SETSN" "$P/PROMPT-2.txt" 64 64 || echo "### run returned $?"
  one_run g2-k8-p2-ub32    8 "$SETS8" "$P/PROMPT-2.txt" 32 64 || echo "### run returned $?"
fi

if [ "$PHASE" = "B" ] || [ "$PHASE" = "ALL" ]; then
  one_run g2-k16-p1   16  "$SETSN" "$P/PROMPT-1.txt" 64 64 || echo "### run returned $?"
  one_run g2-k16-p2   16  "$SETSN" "$P/PROMPT-2.txt" 64 64 || echo "### run returned $?"
  one_run g2-k24-p1   24  "$SETSN" "$P/PROMPT-1.txt" 64 64 || echo "### run returned $?"
  one_run g2-k24-p2   24  "$SETSN" "$P/PROMPT-2.txt" 64 64 || echo "### run returned $?"
fi

if [ "$PHASE" = "C" ] || [ "$PHASE" = "ALL" ]; then
  one_run g2-k32-p1   32  "$SETSN" "$P/PROMPT-1.txt" 64 64 || echo "### run returned $?"
  one_run g2-k32-p2   32  "$SETSN" "$P/PROMPT-2.txt" 64 64 || echo "### run returned $?"
fi

if [ "$PHASE" = "D" ] || [ "$PHASE" = "ALL" ]; then
  # THE NARROW-PREFILL CONTROL: leg A item (a). A three byte prompt so the
  # prefill route call is as narrow as a decode route call, which makes the
  # engine's own peak_concurrent_lease_bytes a DECODE-REGIME figure.
  one_run g2-k8-p4-narrow  8 "$SETS8" "$P/PROMPT-4.txt" 64 32 || echo "### run returned $?"
  # THE SCHEDULE CONTROL: leg A item (f). PROMPT-2 is longer than 64 tokens,
  # so ubatch 64 and ubatch 32 give different piece counts on the SAME prompt.
  one_run g2-k8-p2-ub32    8 "$SETS8" "$P/PROMPT-2.txt" 32 64 || echo "### run returned $?"
fi

echo "=============================================================="
echo "guard_pids_final: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== END GATE 2 PHASE $PHASE ==="
