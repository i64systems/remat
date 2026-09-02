#!/bin/sh
# OB-5a stage 2: THE STARTABILITY SMOKE ON THE 120b.
#
# This is NOT P3. P3 is the night leg's: 8 chunks, A/A, against the banked paged
# pair, with the exposure and latency limbs. This is ONE chunk, and it exists to
# answer the single question this whole leg was funded to answer, before the
# night leg discovers the answer at 3 a.m.:
#
#   OB1B-KNEE-1.md section 9 recorded the leased 120b point dying at model load
#   in 1.068 s with "ggml_aligned_malloc: insufficient memory (attempted to
#   allocate 60438.47 MB)". DOES IT START NOW?
#
# It also carries a real identity limb, which is why it is worth the lock time
# rather than being a bare "did it load". llama-perplexity accumulates its
# per-chunk PPL figures on one line, so a 1-chunk run's identity artifact is a
# BYTE-EXACT PREFIX of the 8-chunk one. The banked paged reference's first chunk
# is [1]88.3425, so a passing 1-chunk leased run must produce exactly
#
#     [1]88.3425,
#     sha256 59d9369f09d49f2cecfcc3454f8ab6e8378a7facc2d70b6ea4e84fb5aaefd759
#
# and its route.log must be the first 36864 lines of the banked route log, byte
# for byte. Both expectations are computed from committed material and written
# into this script BEFORE the run. A mismatch here is a P3a mismatch found early,
# and is reported as a finding, not retried.
LOCK=/mnt/f/f32/stage/research/runlock
BIN=/root/ob5a/llama.cpp/build/bin/llama-perplexity
MODEL=/root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf
SETS=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json
MAN=/mnt/f/f32/openbob-wt/research-2/research/ob1b/EXPERT-MANIFEST-120B.sha256
PROSE=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
REF=/root/ob1b/runs/pag120-prose-a
L=/root/ob5a/runs/smoke120-k8-prose
STAGE=/mnt/f/f32/stage/research/ob5a/runs/smoke120-k8-prose
EXP_ID=59d9369f09d49f2cecfcc3454f8ab6e8378a7facc2d70b6ea4e84fb5aaefd759
mkdir -p $L $STAGE
rm -f $L/route.log $L/alloc-journal.txt

echo "=== OB5A 120B STARTABILITY SMOKE (1 chunk, K=8 of 128, leased) ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "bin:"; sha256sum $BIN /root/ob5a/llama.cpp/build/bin/libggml-base.so.0
echo "model:"; ls -l $MODEL
echo "sets:"; sha256sum $SETS
echo "manifest:"; sha256sum $MAN
echo "the failure this is testing against, from OB1B-KNEE-1.md section 9, verbatim:"
echo "  E ggml_aligned_malloc: insufficient memory (attempted to allocate 60438.47 MB)"
echo "  E alloc_tensor_range: failed to allocate CPU buffer of size 63374323968"
echo "  exit_rc 1   wallclock_s 1.068426206"

T0=$(date +%s)
echo "### LOCK REQUEST at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
while ! mkdir "$LOCK" 2>/dev/null; do
  if [ $(( $(date +%s) - T0 )) -ge 7200 ]; then echo "### GIVING UP on runlock"; exit 75; fi
  sleep 5
done
echo "### LOCK ACQUIRED after $(( $(date +%s) - T0 ))s"
AVAIL=$(free -g | awk "/^Mem:/{print \$7}")
echo "### free RAM available: ${AVAIL} GB (house bar: 6 GB)"
if [ "$AVAIL" -lt 6 ]; then echo "### ABORT: ${AVAIL} GB below the 6 GB bar"; rmdir "$LOCK"; exit 76; fi
free -m

ARGS="-m $MODEL -f $PROSE --ctx-size 1024 --chunks 1 -b 1024 -ub 1024 --threads 8 --threads-batch 8 --no-warmup --seed 1 -ngl 0 --no-mmap --no-repack"
echo "cmd: $BIN $ARGS"
T1=$(date +%s.%N)
CUDA_VISIBLE_DEVICES="" \
OB5A_RESERVE=1 \
OB5A_ALLOC_JOURNAL="$L/alloc-journal.txt" \
LLAMA_ROUTE_LOG="$L/route.log" \
OB1_STATS="$L/ob1-stats.txt" \
OB1_LEASE="$SETS" \
OB1_K=8 \
OB1_MANIFEST="$MAN" \
OB1_GGUF="$MODEL" \
nice -n 10 /usr/bin/time -v $BIN $ARGS > "$L/stdout.txt" 2> "$L/stderr.txt"
RC=$?
T2=$(date +%s.%N)
rmdir "$LOCK"
echo "### LOCK RELEASED rc=$RC"

echo "exit_rc $RC"
echo "wallclock_s $(echo "$T2 - $T1" | bc)"
echo "--- did the 63374323968-byte allocation appear at all? ---"
grep -E "insufficient memory|failed to allocate buffer|alloc_tensor_range|unable to allocate CPU buffer|unable to load model" "$L/stderr.txt" \
  && echo "*** THE OLD FAILURE IS STILL PRESENT ***" \
  || echo "NO ggml_aligned_malloc FAILURE, NO 63374323968-BYTE REQUEST: the model-state"
echo "     allocation that blocked OB-1b did not happen."
echo "--- allocator lines, verbatim ---"
grep -E "OB5A reserved|OB5A reserve allocator|allocation journal|OB1: lease engine" "$L/stderr.txt" || echo "(none)"
echo "--- any fatal, verbatim ---"
grep -E "OB5A RESERVE FATAL|OB1 FATAL|Segmentation fault|Killed" "$L/stderr.txt" || echo "(none)"
echo "--- peak rss ---"
grep -E "Maximum resident set size" "$L/stderr.txt"

echo "--- IDENTITY: must be the byte-exact first-chunk prefix of the banked paged reference ---"
grep '^\[1\]' "$L/stdout.txt" > "$L/identity.txt" || true
echo "  got:  $(cat $L/identity.txt)"
echo "  ref:  $(cut -c1-12 $REF/identity.txt)   (first chunk of $REF/identity.txt)"
GID=$(sha256sum "$L/identity.txt" | cut -d' ' -f1)
echo "  got  sha256 $GID"
echo "  want sha256 $EXP_ID"
if [ "$GID" = "$EXP_ID" ]; then echo "  IDENTITY: MATCH"; else echo "  IDENTITY: *** MISMATCH ***"; fi

echo "--- ROUTE: must be the byte-exact prefix of the banked route log ---"
N=$(wc -l < "$L/route.log")
echo "  this run's route.log lines: $N   banked 8-chunk route.log lines: $(wc -l < $REF/route.log)"
head -n "$N" "$REF/route.log" > /tmp/ob5a-ref-prefix.txt
if cmp -s "$L/route.log" /tmp/ob5a-ref-prefix.txt; then
  echo "  ROUTE PREFIX: MATCH (this run's route trace is the banked trace's first $N lines, byte for byte)"
else
  echo "  ROUTE PREFIX: *** MISMATCH ***"
  cmp "$L/route.log" /tmp/ob5a-ref-prefix.txt | head -3
fi
rm -f /tmp/ob5a-ref-prefix.txt
echo "  route sha256 $(sha256sum $L/route.log | cut -d' ' -f1)"

echo "--- ob1 stats, verbatim ---"
cat "$L/ob1-stats.txt" 2>&1
echo "--- P4c on the 120b ---"
JF=$(sha256sum "$L/alloc-journal.txt" | cut -d' ' -f1)
JP=$(grep '^alloc_journal_sha256=' "$L/ob1-stats.txt" | cut -d= -f2)
echo "  file   $JF"
echo "  engine $JP"
if [ "$JF" = "$JP" ]; then echo "  P4c: MATCH"; else echo "  P4c: *** MISMATCH ***"; fi
gzip -9 -c "$L/alloc-journal.txt" > "$STAGE/alloc-journal.txt.gz"

echo "--- THE ARITHMETIC, shown ---"
echo "  120b file bytes            63387346208"
echo "  L x E x per_expert         36 x 128 x 13253760 = 61073326080"
VA=$(grep '^alloc_va_model_bytes=' $L/ob1-stats.txt | cut -d= -f2)
PK=$(grep '^alloc_commit_model_peak=' $L/ob1-stats.txt | cut -d= -f2)
PC=$(grep '^peak_concurrent_lease_bytes=' $L/ob1-stats.txt | cut -d= -f2)
echo "  reservation (VA)           $VA"
echo "  buffer trunk               $VA - 61073326080 = $((VA - 61073326080))"
echo "  K=8 pool                   8 x 36 x 13253760 = 3817082880"
echo "  peak concurrent (1 chunk)  $PC"
echo "  predicted commit peak      $(( (VA - 61073326080) + 3817082880 + PC ))"
echo "  measured commit peak       $PK"
echo "  edge actually paid         $(( PK - ((VA - 61073326080) + 3817082880 + PC) ))"
echo "  120b edge census bound     112361472"
echo "  prereg P3 ACCT (8 chunks)  7721554208   EXPOSURE_acct 8.209143"
echo "  NOTE: the peak_concurrent above is ONE chunk's worst micro-batch. The banked"
echo "        prediction 1590451200 is the worst over all EIGHT chunks, so this figure"
echo "        is a lower bound on it and is not a P3b comparison."

echo "free_after:"; free -m
echo "guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
for f in route.log stdout.txt stderr.txt identity.txt ob1-stats.txt; do
  [ -f "$L/$f" ] && cp "$L/$f" "$STAGE/$f"
done
echo "### courtesy yield 75s"
sleep 75
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== END 120B STARTABILITY SMOKE rc=$RC ==="
