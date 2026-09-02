#!/bin/bash
# BOB-MOE-0 stage-1 leg-1 driver. Usage: run_stage1.sh <moe|dense> <A|B>
# CPU only: CUDA_VISIBLE_DEVICES forced empty. Threads pinned to 8 per prereg s.1.
set -e
VENV=/root/openbob-train/venv/bin/python
CODE=/mnt/f/f32/openbob-wt/low-int/lowint/moe0/train
DATA=/mnt/f/f32/stage/lowint/data/enwik8/enwik8
CK=/mnt/f/f32/stage/lowint/moe0-ckpt
ARM="$1"
RUN="$2"
THREADS="${THREADS:-8}"
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS="$THREADS"
export MKL_NUM_THREADS="$THREADS"
export PYTHONHASHSEED=0
mkdir -p "$CK/$ARM/$RUN"
cd "$CODE"
exec "$VENV" bobmoe0.py --arm "$ARM" --stage 1 --run "$RUN" \
  --data "$DATA" --ckpt-dir "$CK/$ARM/$RUN" \
  --log "$CK/$ARM/$RUN/metrics.tsv" \
  --progress "$CK/$ARM/$RUN/progress.txt" --threads "$THREADS"
