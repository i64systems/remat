#!/bin/sh
# OB-1b: the gpt-oss-120b wall-clock-bounding point.
#
# THIS SCRIPT WAS REWRITTEN AFTER A SMOKE TEST FOUND THAT THE LEASED 120B RUN IS
# BLOCKED ON THIS BOX, for a reason the task brief did not anticipate and that
# matters more than the number it was meant to produce.
#
# The brief expected the fully resident --no-mmap baseline to be infeasible (63
# GB of model against 24 GB of RAM) and prescribed mmap-paged execution as the
# identity reference instead, with the LEASED run still going ahead. It cannot.
# One 1024-token leased probe (smoke120-k8-prose, logged in full at
# research/ob1b/logs/smoke120-k8-prose.log) died at model load in 1.068 s:
#
#   ggml_aligned_malloc: insufficient memory (attempted to allocate 60438.47 MB)
#   ggml_backend_cpu_buffer_type_alloc_buffer: failed to allocate buffer of size 63374323968
#   alloc_tensor_range: failed to allocate CPU buffer of size 63374323968
#   llama_model_load: error loading model: unable to allocate CPU buffer
#
# The cause is structural, not incidental. The lease engine REQUIRES --no-mmap,
# because it can only fill and drop expert bytes that live in ordinary anonymous
# memory; under mmap the tensor data is a private file mapping the loader never
# writes. But --no-mmap makes llama.cpp allocate ONE CPU buffer for the whole
# model, 63374323968 bytes, BEFORE any leasing can happen, and Linux's default
# heuristic overcommit (vm.overcommit_memory=0, measured on this box) refuses a
# single allocation that far above RAM plus swap (24029 MB + 6144 MB). So the
# leasing never gets a chance to bound anything: the allocation that leasing is
# meant to avoid is the one that fails first.
#
# The same single cause blocks the resident baseline and the leased run alike,
# so this leg does not spend 40 minutes of a contended runlock re-running a
# one-second failure it already has verbatim. Run 1 below reproduces it at the
# frozen 8192-token configuration for the record (it also costs about a second),
# and the rest of the leg measures what IS measurable: mmap-paged execution of a
# 63 GB model on a 24 GB box, run twice, which bounds wall clock at the larger
# model and establishes the identity reference the brief asked for.
SETS=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json
MODEL=/root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf
MAN=/mnt/f/f32/openbob-wt/research-2/research/ob1b/EXPERT-MANIFEST-120B.sha256
PROSE=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
LR=/mnt/f/f32/openbob-wt/research-2/research/ob1b/locked-run.sh
LOCK=/mnt/f/f32/stage/research/runlock
LOGS=/mnt/f/f32/stage/research/ob1b/logs
mkdir -p $LOGS

echo "########## OB1B 120B POINT ##########"
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
sha256sum /root/ob1b/llama.cpp/build/bin/llama-perplexity
echo "model:"; sha256sum $MODEL
echo "manifest:"; sha256sum $MAN
echo "resident sets:"; sha256sum $SETS
echo

# --- run 1: the resident --no-mmap baseline attempt, for the record, at the
#     frozen configuration. Capped and oom-pinned so that if this box's
#     overcommit policy ever DID let the allocation through, the failure could
#     not make the OOM killer pick pid 654, pid 489, or a sibling's run. ---
echo "########## res120-nomm-prose (expected infeasible) ##########"
WAITED=0
while ! mkdir "$LOCK" 2>/dev/null; do
  WAITED=$((WAITED + 30))
  if [ $WAITED -ge 7200 ]; then echo "### GIVING UP on runlock after ${WAITED}s"; exit 75; fi
  sleep 30
done
echo "### LOCK ACQUIRED res120-nomm-prose at $(date -u +%Y-%m-%dT%H:%M:%SZ) after ${WAITED}s"
sh /mnt/f/f32/openbob-wt/research-2/research/ob1b/run-120b-resident-attempt.sh 22000000 \
   > $LOGS/res120-nomm-prose.log 2>&1
echo "=== res120-nomm-prose rc=$? ==="
rmdir "$LOCK"
echo "### LOCK RELEASED res120-nomm-prose at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
grep -E "^exit_rc|^wallclock_s|insufficient memory|failed to allocate|unable to allocate|unable to load model" $LOGS/res120-nomm-prose.log | head -10
echo "### courtesy yield 75s"
sleep 75
echo

# --- runs 2 and 3: mmap-paged execution, twice. These must be byte-identical to
#     each other before either is trusted as a reference. ---
for R in \
  "pag120-prose-a $PROSE paged -1 - $MODEL - 8 8" \
  "pag120-prose-b $PROSE paged -1 - $MODEL - 8 8" \
; do
  set -- $R
  NAME=$1
  if [ -s /root/ob1b/runs/$NAME/ob1-stats.txt ] && [ -s /root/ob1b/runs/$NAME/identity.txt ]; then
    echo "########## $NAME ALREADY LANDED, skipping ##########"
    continue
  fi
  echo "########## $NAME  $(date -u +%Y-%m-%dT%H:%M:%SZ) ##########"
  sh $LR "$@" > $LOGS/$NAME.log 2>&1
  RC=$?
  echo "=== $NAME rc=$RC ==="
  grep -E "^### LOCK|^exit_rc|^wallclock_s|Maximum resident set size|^chunk_count" $LOGS/$NAME.log
  if [ $RC -eq 75 ]; then
    echo "RUNLOCK NEVER FREED for $NAME -- the box is busy tonight. 120b leg stopped here."
    exit 75
  fi
  if [ $RC -ne 0 ]; then
    echo "$NAME FAILED rc=$RC -- last 40 lines verbatim:"
    tail -40 $LOGS/$NAME.log
  fi
done

echo "--- A/A check on the paged reference ---"
if cmp -s /root/ob1b/runs/pag120-prose-a/identity.txt /root/ob1b/runs/pag120-prose-b/identity.txt; then
  echo "PAGED A/A identity: MATCH"
else
  echo "PAGED A/A identity: DIFFER"
fi
if cmp -s /root/ob1b/runs/pag120-prose-a/route.log /root/ob1b/runs/pag120-prose-b/route.log; then
  echo "PAGED A/A route: MATCH"
else
  echo "PAGED A/A route: DIFFER"
fi
sha256sum /root/ob1b/runs/pag120-prose-a/identity.txt /root/ob1b/runs/pag120-prose-b/identity.txt 2>/dev/null

echo "########## 120B LEG DONE $(date -u +%Y-%m-%dT%H:%M:%SZ) ##########"
