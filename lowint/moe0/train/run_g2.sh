#!/usr/bin/env bash
# BOB-MOE-0 stage-1 G2 driver. One clean process per invocation.
# CPU ONLY: CUDA_VISIBLE_DEVICES is exported empty and re-forced inside the
# instrument before torch is imported.
set -euo pipefail

RUN="$1"                       # run label, e.g. run1 / run2
OUTDIR=/mnt/f/f32/stage/lowint/moe0-g2/"$RUN"
CKPT=/mnt/f/f32/stage/lowint/moe0-ckpt/moe/A/step000500.safetensors
DATA=/mnt/f/f32/stage/lowint/data/enwik8/enwik8
PY=/root/openbob-train/venv/bin/python
SRC=/mnt/f/f32/openbob-wt/low-int/lowint/moe0/train

export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8
export PYTHONHASHSEED=0

mkdir -p "$OUTDIR"
cd "$SRC"
"$PY" route_stats.py \
  --stage 1 \
  --ckpt "$CKPT" \
  --data "$DATA" \
  --split val \
  --batch 32 \
  --threads 8 \
  --out-prefix "$OUTDIR"/route \
  --progress "$OUTDIR"/progress.txt
