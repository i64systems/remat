#!/bin/sh
# OB-5a stage 2: the P1 regression / P2 allocation run driver.
#
# Same lineage and the same invocation shape as research/ob1b/run-ob1b.sh, at the
# SAME frozen configuration, so that a digest that comes back different can only
# be the allocator. Three additions, each named as a deviation in the receipt:
#
#   1. OB5A_RESERVE=1 on every run, including the RESIDENT control runs. The
#      resident runs commit the whole model by construction; that is the control
#      the leased runs are read against (prereg bar P2d), not a bar failure.
#   2. OB5A_ALLOC_JOURNAL on every run, so P4c is provable on every run rather
#      than on a special one: the printed alloc_journal_sha256 must equal the
#      sha256 of the file, which is what stops P4a being a rolling hash of
#      nothing.
#   3. The banked digest verdict is rendered INLINE, against digests passed in on
#      the command line, so no run's verdict is decided after seeing its output.
#
# usage: run-ob5a.sh RUNNAME CORPUS MODE K SETS MODEL MANIFEST CHUNKS THREADS EXP_ID EXP_RT
#   MODE=resident  fully resident, --no-mmap  (the P2d control)
#   MODE=lease     leased with resident-set size K (K=0 is pure streaming)
#   EXP_ID/EXP_RT  banked identity / route sha256 to compare against, or "-"
RUNNAME=$1
CORPUS=$2
MODE=$3
K=$4
SETS=$5
MODEL=$6
MANIFEST=$7
CHUNKS=$8
THREADS=$9
shift 9
EXP_ID=$1
EXP_RT=$2

BIN=/root/ob5a/llama.cpp/build/bin/llama-perplexity
LOCAL=/root/ob5a/runs/$RUNNAME
STAGE=/mnt/f/f32/stage/research/ob5a/runs/$RUNNAME

mkdir -p "$LOCAL" "$STAGE"
RL=$LOCAL/route.log
JL=$LOCAL/alloc-journal.txt
rm -f "$RL" "$JL"

echo "=== OB5A RUN $RUNNAME (mode=$MODE K=$K chunks=$CHUNKS threads=$THREADS reserve=1) ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "bin_sha256: $(sha256sum $BIN | cut -d' ' -f1)"
echo "lib_sha256: $(sha256sum /root/ob5a/llama.cpp/build/bin/libllama.so.0 | cut -d' ' -f1) libllama.so.0"
echo "ggml_sha256: $(sha256sum /root/ob5a/llama.cpp/build/bin/libggml-base.so.0 | cut -d' ' -f1) libggml-base.so.0"
echo "model: $MODEL"
echo "corpus_sha256: $(sha256sum $CORPUS | cut -d' ' -f1)"
echo "free_before:"
free -m

ARGS="-m $MODEL -f $CORPUS --ctx-size 1024 --chunks $CHUNKS -b 1024 -ub 1024 --threads $THREADS --threads-batch $THREADS --no-warmup --seed 1 -ngl 0 --no-mmap --no-repack"
echo "cmd: $BIN $ARGS"

T0=$(date +%s.%N)
if [ "$MODE" = "lease" ]; then
  echo "env: OB5A_RESERVE=1 OB5A_ALLOC_JOURNAL=$JL LLAMA_ROUTE_LOG=$RL OB1_STATS=$LOCAL/ob1-stats.txt OB1_LEASE=$SETS OB1_K=$K OB1_MANIFEST=$MANIFEST"
  CUDA_VISIBLE_DEVICES="" \
  OB5A_RESERVE=1 \
  OB5A_ALLOC_JOURNAL="$JL" \
  LLAMA_ROUTE_LOG="$RL" \
  OB1_STATS="$LOCAL/ob1-stats.txt" \
  OB1_LEASE="$SETS" \
  OB1_K="$K" \
  OB1_MANIFEST="$MANIFEST" \
  OB1_GGUF="$MODEL" \
  nice -n 10 /usr/bin/time -v $BIN $ARGS > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
  RC=$?
else
  echo "env: OB5A_RESERVE=1 OB5A_ALLOC_JOURNAL=$JL LLAMA_ROUTE_LOG=$RL OB1_STATS=$LOCAL/ob1-stats.txt (no lease)"
  CUDA_VISIBLE_DEVICES="" \
  OB5A_RESERVE=1 \
  OB5A_ALLOC_JOURNAL="$JL" \
  LLAMA_ROUTE_LOG="$RL" \
  OB1_STATS="$LOCAL/ob1-stats.txt" \
  nice -n 10 /usr/bin/time -v $BIN $ARGS > "$LOCAL/stdout.txt" 2> "$LOCAL/stderr.txt"
  RC=$?
fi
T1=$(date +%s.%N)

echo "exit_rc $RC"
echo "wallclock_s $(echo "$T1 - $T0" | bc)"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "--- peak rss / elapsed ---"
grep -E 'Maximum resident set size|Elapsed \(wall clock\)' "$LOCAL/stderr.txt" || echo "(no time -v block: process did not exit normally)"
echo "--- the allocator announced itself (verbatim) ---"
grep -E "OB5A reserved|OB5A reserve allocator|allocation journal|OB1: lease engine" "$LOCAL/stderr.txt" || echo "(NO ALLOCATOR LINES -- the reserve path was not taken)"
echo "--- any OB5A/OB1 fatal, verbatim ---"
grep -E "OB5A RESERVE FATAL|OB1 FATAL|Segmentation fault" "$LOCAL/stderr.txt" || echo "(none)"
echo "--- last 25 lines of stderr (verbatim, whether or not the run succeeded) ---"
tail -25 "$LOCAL/stderr.txt"

echo "--- identity artifact (the '[1]' per-chunk PPL line) ---"
grep '^\[1\]' "$LOCAL/stdout.txt" > "$LOCAL/identity.txt" || true
wc -c < "$LOCAL/identity.txt"
GID=$(sha256sum "$LOCAL/identity.txt" | cut -d' ' -f1)
echo "identity_sha256 $GID"
echo "--- route log ---"
if [ -f "$RL" ]; then
  wc -l < "$RL"
  GRT=$(sha256sum "$RL" | cut -d' ' -f1)
  echo "route_sha256 $GRT"
else
  GRT="(no route log)"
  echo "(no route log)"
fi

echo "--- P1 VERDICT against the banked pair ---"
if [ "$EXP_ID" = "-" ]; then
  echo "  identity: (no banked digest passed for this run)"
else
  if [ "$GID" = "$EXP_ID" ]; then
    echo "  identity: MATCH   $GID"
  else
    echo "  identity: *** MISMATCH -- STOP SHIP ***"
    echo "    got  $GID"
    echo "    want $EXP_ID"
  fi
fi
if [ "$EXP_RT" = "-" ]; then
  echo "  route:    (no banked digest passed for this run)"
else
  if [ "$GRT" = "$EXP_RT" ]; then
    echo "  route:    MATCH   $GRT"
  else
    echo "  route:    *** MISMATCH -- STOP SHIP ***"
    echo "    got  $GRT"
    echo "    want $EXP_RT"
  fi
fi

echo "--- ob1 stats (verbatim) ---"
cat "$LOCAL/ob1-stats.txt" 2>&1

echo "--- P4c: the printed journal digest must equal sha256 of the journal FILE ---"
if [ -f "$JL" ]; then
  JF=$(sha256sum "$JL" | cut -d' ' -f1)
  JP=$(grep '^alloc_journal_sha256=' "$LOCAL/ob1-stats.txt" 2>/dev/null | cut -d= -f2)
  echo "  journal_file_bytes  $(stat -c %s $JL)"
  echo "  journal_file_lines  $(wc -l < $JL)"
  echo "  file   sha256 $JF"
  echo "  engine sha256 $JP"
  if [ "$JF" = "$JP" ]; then echo "  P4c: MATCH"; else echo "  P4c: *** MISMATCH ***"; fi
  echo "  first 3 records:"; head -3 "$JL" | sed 's/^/    /'
  echo "  last 3 records:";  tail -3 "$JL" | sed 's/^/    /'
  gzip -9 -c "$JL" > "$STAGE/alloc-journal.txt.gz"
else
  echo "  (no journal file)"
fi

echo "--- timings ---"
grep -E 'load time|prompt eval time|eval time|total time|seconds per pass' "$LOCAL/stderr.txt" || true
echo "free_after:"
free -m
echo "guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"

for f in route.log stdout.txt stderr.txt identity.txt ob1-stats.txt; do
  [ -f "$LOCAL/$f" ] && cp "$LOCAL/$f" "$STAGE/$f"
done
echo "=== END $RUNNAME rc=$RC ==="
