#!/bin/sh
# OB-5b S1 GATE 1: BYTE-EXACT GENERATION ON THE 120b.
#
# THE BAR (OB5-DESIGN-C4-1.md section 12, gate 1, STOP-SHIP): two A/A generation
# runs byte-identical; a third run from the same state after a serve restart
# also byte-identical.
#
# DECLARED INTERPRETATION OF THE THIRD LIMB. This leg's HARD WALLS forbid
# touching pid 654, the live openbob serve, and gate 3 has not yet built an
# exposure worker serve, so there is no serve of this gate's own to restart. The
# third limb is therefore taken in its evident sense: a run that shares the
# BOUND STATE (C4 s4.3) with A and B and differs in everything that is NOT in
# the bound state. Run C is a fresh process started from a different working
# directory, writing to a different output directory, after 4 GiB of the model
# file has been read into the page cache to change the machine's I/O state under
# it. If any of that moved a byte, the bound state was incompletely specified,
# which is exactly what this limb exists to catch.
#
# House run discipline in full, per run: mkdir runlock with a 5 s poll, free RAM
# >= 6 GB, overcommit read INSIDE the locked window with a non-zero value fatal,
# guards confirmed before and after, nice 10, 8 threads, 75 s courtesy yield.
#
# Every perf data point our standing order names is banked per run: tok/s
# (labelled DECODE, per OB5-024), TTFT, wall, peak RSS, VmHWM, the lease
# counters and the commit-peak counters.
set -e

LOCK=/mnt/f/f32/stage/research/runlock
DST=/root/ob5b1/llama.cpp
BIN=$DST/build/bin/ob5b1-gen
MODEL=/root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf
SETS=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json
MAN=/mnt/f/f32/openbob-wt/research-2/research/ob1b/EXPERT-MANIFEST-120B.sha256
PROMPT=/mnt/f/f32/stage/research/ob5b1/PROMPT-1.txt
N_PREDICT=32
N_CTX=512
N_UBATCH=64
THREADS=8

echo "=== OB5B1 S1 GATE 1: BYTE-EXACT GENERATION, gpt-oss-120b K=8 of 128 leased ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "--- the engine under test ---"
echo "gen_bin_sha256   $(sha256sum $BIN | cut -d' ' -f1)"
echo "gen_src_sha256   $(sha256sum $DST/ob5b1-gen.cpp | cut -d' ' -f1)"
echo "libllama_sha256  $(sha256sum $DST/build/bin/libllama.so.0 | cut -d' ' -f1)"
echo "libggmlbase_sha  $(sha256sum $DST/build/bin/libggml-base.so.0 | cut -d' ' -f1)"
echo "libggmlcpu_sha   $(sha256sum $DST/build/bin/libggml-cpu.so.0 | cut -d' ' -f1)"
echo "--- the bound state's file members ---"
echo "model_bytes      $(stat -c %s $MODEL)"
echo "model_sha256     (63 GB, not re-hashed here; OB5A-ALLOC-1 banks 582bd40f...)"
echo "sets_sha256      $(sha256sum $SETS | cut -d' ' -f1)"
echo "manifest_sha256  $(sha256sum $MAN | cut -d' ' -f1)"
echo "prompt_sha256    $(sha256sum $PROMPT | cut -d' ' -f1)"
echo "prompt_bytes     $(stat -c %s $PROMPT)"
echo "n_predict $N_PREDICT  n_ctx $N_CTX  n_ubatch $N_UBATCH  threads $THREADS"
echo ""

one_run() {   # one_run <runname> <cwd>
  RUNNAME=$1
  CWD=$2
  LOCAL=/root/ob5b1/runs/$RUNNAME
  STAGE=/mnt/f/f32/stage/research/ob5b1/runs/$RUNNAME
  mkdir -p "$LOCAL" "$STAGE"
  RL=$LOCAL/route.log
  JL=$LOCAL/alloc-journal.txt
  rm -f "$RL" "$JL" "$LOCAL"/gen-*.txt "$LOCAL"/prompt-ids.txt

  echo "--------------------------------------------------------------"
  echo "### RUN $RUNNAME  cwd=$CWD"
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
    echo "### ABORT $RUNNAME: vm.overcommit_memory is $OC, not 0. The claim would be worthless."
    rmdir "$LOCK"; return 77
  fi
  echo "### free_before:"; free -m

  TS=$(date +%s.%N)
  ( cd "$CWD" && \
    CUDA_VISIBLE_DEVICES="" \
    OB5A_RESERVE=1 \
    OB5A_ALLOC_JOURNAL="$JL" \
    LLAMA_ROUTE_LOG="$RL" \
    OB1_STATS="$LOCAL/ob1-stats.txt" \
    OB1_LEASE="$SETS" \
    OB1_K=8 \
    OB1_MANIFEST="$MAN" \
    OB1_GGUF="$MODEL" \
    LD_LIBRARY_PATH="$DST/build/bin" \
    nice -n 10 /usr/bin/time -v "$BIN" \
      --model "$MODEL" --prompt-file "$PROMPT" --out-dir "$LOCAL" \
      --n-predict $N_PREDICT --ctx $N_CTX --ubatch $N_UBATCH --threads $THREADS \
      > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt" )
  RC=$?
  TE=$(date +%s.%N)

  echo "### overcommit_after_run: $(cat /proc/sys/vm/overcommit_memory)"
  rmdir "$LOCK"
  echo "### LOCK RELEASED at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "### exit_rc $RC"
  echo "### wallclock_s $(echo "$TE - $TS" | bc)"
  echo "### guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
  echo "### free_after:"; free -m

  echo "--- any fatal, verbatim ---"
  grep -E "OB5A RESERVE FATAL|OB1 FATAL|OB5B1-GEN FATAL|Segmentation fault|std::bad_alloc" \
    "$LOCAL/stderr.txt" || echo "(none)"
  echo "--- stdout, verbatim ---"
  cat "$LOCAL/stdout.txt"
  echo "--- the allocator announced itself, verbatim ---"
  grep -E "OB5A reserved|OB5A reserve allocator|allocation journal|OB1: lease engine" \
    "$LOCAL/stderr.txt" || echo "(NO ALLOCATOR LINES -- the reserve path was not taken)"
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
  fi
  for f in stdout.txt stderr.txt gen-ids.txt gen-text.txt prompt-ids.txt ob1-stats.txt route.log; do
    [ -f "$LOCAL/$f" ] && cp "$LOCAL/$f" "$STAGE/$f"
  done
  echo "### courtesy yield 75 s"
  sleep 75
  return $RC
}

mkdir -p /root/ob5b1/cwd-a /root/ob5b1/cwd-c
one_run gen-120b-k8-a /root/ob5b1/cwd-a
one_run gen-120b-k8-b /root/ob5b1/cwd-a

echo "--------------------------------------------------------------"
echo "### PERTURB THE PAGE CACHE BEFORE RUN C (outside the bound state)"
echo "### reading 4 GiB of the model file to /dev/null"
dd if="$MODEL" of=/dev/null bs=1M count=4096 2>&1 | tail -2
free -m
one_run gen-120b-k8-c /root/ob5b1/cwd-c

echo "=============================================================="
echo "=== GATE 1 VERDICT ==="
A=/root/ob5b1/runs/gen-120b-k8-a
B=/root/ob5b1/runs/gen-120b-k8-b
C=/root/ob5b1/runs/gen-120b-k8-c
V=0
cmpf() {  # cmpf <file> <label>
  for P in "$B" "$C"; do
    if cmp -s "$A/$1" "$P/$1"; then
      printf "  %-16s A vs %-22s IDENTICAL\n" "$1" "$(basename $P)"
    else
      printf "  %-16s A vs %-22s *** DIFFER -- STOP SHIP ***\n" "$1" "$(basename $P)"
      cmp -l "$A/$1" "$P/$1" 2>/dev/null | head -5
      V=1
    fi
  done
}
echo "IDENTITY LIMB (the bytes the model produced):"
cmpf gen-ids.txt
cmpf gen-text.txt
echo "INPUT LIMB (the tokenizer's own output on the frozen prompt):"
cmpf prompt-ids.txt
echo "ROUTE LIMB (every routing decision of every layer of every token):"
cmpf route.log
echo "ALLOCATOR LIMB (the commit/decommit journal):"
cmpf alloc-journal.txt
echo ""
echo "--- the three runs' digests, side by side ---"
sha256sum "$A"/gen-ids.txt "$B"/gen-ids.txt "$C"/gen-ids.txt
sha256sum "$A"/gen-text.txt "$B"/gen-text.txt "$C"/gen-text.txt
sha256sum "$A"/route.log "$B"/route.log "$C"/route.log
sha256sum "$A"/alloc-journal.txt "$B"/alloc-journal.txt "$C"/alloc-journal.txt
echo ""
echo "--- deterministic counters, side by side (any difference is a finding) ---"
for k in lease_events lease_bytes_read peak_concurrent_lease_bytes \
         resident_slices_loaded resident_bytes_loaded route_calls \
         alloc_commit_model_peak alloc_commit_peak_single alloc_va_model_bytes \
         alloc_commit_calls alloc_decommit_calls alloc_commit_live_at_exit \
         alloc_journal_sha256 lease_active_slices_at_exit; do
  printf "  %-30s a=%-22s b=%-22s c=%s\n" "$k" \
    "$(grep "^$k=" $A/ob1-stats.txt | cut -d= -f2)" \
    "$(grep "^$k=" $B/ob1-stats.txt | cut -d= -f2)" \
    "$(grep "^$k=" $C/ob1-stats.txt | cut -d= -f2)"
done
echo ""
echo "--- perf data points, per run (our standing order) ---"
for k in n_prompt_tokens n_generated_tokens stop_reason prefill_seconds \
         ttft_seconds decode_seconds tok_s_decode tok_s_decode_excl_first \
         tok_s_prefill model_load_seconds wall_seconds VmHWM_bytes VmPeak_kb; do
  printf "  %-28s a=%-22s b=%-22s c=%s\n" "$k" \
    "$(grep "^$k  *" $A/stdout.txt | awk '{print $2}')" \
    "$(grep "^$k  *" $B/stdout.txt | awk '{print $2}')" \
    "$(grep "^$k  *" $C/stdout.txt | awk '{print $2}')"
done
echo ""
if [ "$V" = "0" ]; then
  echo "GATE 1: PASS. Byte-exact generation on all five limbs across three runs."
else
  echo "GATE 1: *** FAIL -- STOP SHIP *** (kill line K1 of OB5-DESIGN-C4-1 section 11)"
fi
echo "guard_pids_final: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== END GATE 1 ==="
