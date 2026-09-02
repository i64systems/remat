#!/bin/sh
# OB-1 stage 2: the negative controls. Each run below MUST abort; a run that
# completes is a failed control and is reported as such.
BIN=/root/rs053/llama.cpp/build/bin/llama-perplexity
MODEL=/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf
WT=/mnt/f/f32/openbob-wt/research-2/research/ob1
CORPUS=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
CTL=/mnt/f/f32/stage/research/ob1/controls
OUTL=/root/ob1/controls
mkdir -p "$OUTL"

python3 "$WT/controls.py" || exit 1

ARGS="-m $MODEL -f $CORPUS --ctx-size 1024 --chunks 1 -b 1024 -ub 1024 --threads 10 --threads-batch 10 --no-warmup --seed 1 -ngl 0 --no-mmap --no-repack"

for C in C1-bad-sha-nonresident C2-bad-sha-resident C3-bad-offset-resident; do
  echo "=== CONTROL $C ==="
  CUDA_VISIBLE_DEVICES="" \
  OB1_LEASE="$WT/RESIDENT-SETS.json" OB1_K=16 \
  OB1_MANIFEST="$CTL/$C.sha256" OB1_GGUF="$MODEL" \
  nice -n 10 $BIN $ARGS > "$OUTL/$C.out" 2> "$OUTL/$C.err"
  echo "exit_rc=$?"
  grep -A4 "OB1 FATAL" "$OUTL/$C.err" | head -8
  echo "--- completed a perplexity line? (must be empty) ---"
  grep -c '^\[1\]' "$OUTL/$C.out"
done

echo "=== CONTROL C4: real manifest, K=16, must NOT abort (1 chunk) ==="
CUDA_VISIBLE_DEVICES="" \
OB1_LEASE="$WT/RESIDENT-SETS.json" OB1_K=16 \
OB1_MANIFEST="$WT/EXPERT-MANIFEST-20B.sha256" OB1_GGUF="$MODEL" \
nice -n 10 $BIN $ARGS > "$OUTL/C4-clean.out" 2> "$OUTL/C4-clean.err"
echo "exit_rc=$?"
grep -c '^\[1\]' "$OUTL/C4-clean.out"
grep '^\[1\]' "$OUTL/C4-clean.out"
