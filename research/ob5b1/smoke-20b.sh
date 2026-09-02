#!/bin/sh
# OB-5b S1 gate 1 SMOKE: exercise ob5b1-gen end to end on the 20b before any
# 120b time is spent. Same engine, same allocator, same lease engine, same
# frozen bound state shape, a smaller model and a short generation.
#
# This is not a gate. It is the cheap check that the generation entry point
# tokenizes, prefills, samples, writes its files and reads its counters back,
# so that a 120b failure can only be a 120b failure.
#
# House run discipline applies in full: runlock, 6 GB free bar, guards before
# and after, nice 10, 8 threads, 75 s courtesy yield.
set -e

LOCK=/mnt/f/f32/stage/research/runlock
DST=/root/ob5b1/llama.cpp
BIN=$DST/build/bin/ob5b1-gen
MODEL=/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf
SETS=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-KNEE.json
MAN=/mnt/f/f32/openbob-wt/research-2/research/ob1/EXPERT-MANIFEST-20B.sha256
PROMPT=/mnt/f/f32/stage/research/ob5b1/PROMPT-1.txt
LOCAL=/root/ob5b1/runs/smoke-20b-k2
STAGE=/mnt/f/f32/stage/research/ob5b1/runs/smoke-20b-k2
mkdir -p "$LOCAL" "$STAGE"
JL=$LOCAL/alloc-journal.txt
rm -f "$JL" "$LOCAL"/gen-*.txt "$LOCAL"/prompt-ids.txt

echo "=== OB5B1 SMOKE: 20b K=2 leased, 8 new tokens ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "bin_sha256:  $(sha256sum $BIN | cut -d' ' -f1)"
echo "llama_sha256: $(sha256sum $DST/build/bin/libllama.so.0 | cut -d' ' -f1)"
echo "ggml_sha256:  $(sha256sum $DST/build/bin/libggml-base.so.0 | cut -d' ' -f1)"
echo "model_bytes: $(stat -c %s $MODEL)"
echo "prompt_sha256: $(sha256sum $PROMPT | cut -d' ' -f1)"

T0=$(date +%s)
echo "### LOCK REQUEST at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
while ! mkdir "$LOCK" 2>/dev/null; do
  W=$(( $(date +%s) - T0 ))
  if [ $W -ge 3600 ]; then echo "### GIVING UP on runlock after ${W}s"; exit 75; fi
  sleep 5
done
echo "### LOCK ACQUIRED after $(( $(date +%s) - T0 ))s"

AVAIL=$(free -g | awk '/^Mem:/{print $7}')
echo "### free RAM available: ${AVAIL} GB (house bar: 6 GB)"
if [ "$AVAIL" -lt 6 ]; then
  echo "### ABORT: free RAM ${AVAIL} GB below the 6 GB house bar"
  rmdir "$LOCK"; exit 76
fi
echo "overcommit_at_run: $(cat /proc/sys/vm/overcommit_memory)"
free -m

TS=$(date +%s.%N)
CUDA_VISIBLE_DEVICES="" \
OB5A_RESERVE=1 \
OB5A_ALLOC_JOURNAL="$JL" \
OB1_STATS="$LOCAL/ob1-stats.txt" \
OB1_LEASE="$SETS" \
OB1_K=2 \
OB1_MANIFEST="$MAN" \
OB1_GGUF="$MODEL" \
LD_LIBRARY_PATH="$DST/build/bin" \
nice -n 10 /usr/bin/time -v "$BIN" \
  --model "$MODEL" --prompt-file "$PROMPT" --out-dir "$LOCAL" \
  --n-predict 8 --ctx 512 --ubatch 64 --threads 8 \
  > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
RC=$?
TE=$(date +%s.%N)

echo "overcommit_after_run: $(cat /proc/sys/vm/overcommit_memory)"
rmdir "$LOCK"
echo "### LOCK RELEASED at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "exit_rc $RC"
echo "wallclock_s $(echo "$TE - $TS" | bc)"
echo "--- stdout, verbatim ---"
cat "$LOCAL/stdout.txt"
echo "--- generated text, verbatim ---"
cat "$LOCAL/gen-text.txt" 2>/dev/null || echo "(no gen-text.txt)"
echo ""
echo "--- generated ids ---"
cat "$LOCAL/gen-ids.txt" 2>/dev/null || echo "(no gen-ids.txt)"
echo "--- digests ---"
sha256sum "$LOCAL"/gen-ids.txt "$LOCAL"/gen-text.txt "$LOCAL"/prompt-ids.txt 2>/dev/null || true
echo "--- ob1 stats, verbatim ---"
cat "$LOCAL/ob1-stats.txt" 2>&1 || true
echo "--- any fatal, verbatim ---"
grep -E "OB5A RESERVE FATAL|OB1 FATAL|OB5B1-GEN FATAL|Segmentation fault" "$LOCAL/stderr.txt" || echo "(none)"
echo "--- last 20 lines of stderr, verbatim ---"
tail -20 "$LOCAL/stderr.txt"
echo "--- peak rss ---"
grep -E 'Maximum resident set size|Elapsed \(wall clock\)' "$LOCAL/stderr.txt" || true
for f in stdout.txt stderr.txt gen-ids.txt gen-text.txt prompt-ids.txt ob1-stats.txt; do
  [ -f "$LOCAL/$f" ] && cp "$LOCAL/$f" "$STAGE/$f"
done
echo "guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
free -m
echo "### courtesy yield 75 s"
sleep 75
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== END SMOKE rc=$RC ==="
