#!/bin/sh
# OB-5b P05 (C8-S8-2) limb (a): the decode-shape replay. ANALYSIS ONLY.
# No model process, no runlock, no weights, no card. Every invocation
# below reads banked route logs and banked resident-set files and writes
# one literal row block.
#
# usage: sh run-replay.sh <stage_out_dir>
OUT=$1
R=/mnt/f/f32/openbob-wt/research-2/research/ob5b2
S=/mnt/f/f32/stage/research
mkdir -p "$OUT"

PE=13253760

# ---- the two calibration points (B1), at the shape that was measured --
echo "########## B1 CALIBRATION POINT 1: 120b K=8 P0-STATIC ubatch=1024 ##########"
python3 $R/decode_replay.py \
  --route $S/ob5a/runs/p3-120b-k8-prose-a/route.log \
  --E 128 --L 36 --budget 8192 --k 4 --per-expert $PE \
  --trunk 2314020128 --logical 63387346208 --read-rate 1266753082 \
  --sets $R/../ob1b/RESIDENT-SETS-120B-K8.json \
  --K 8 --policy P0-STATIC --ubatch 1024 \
  --label CAL1-120B-K8-STATIC-U1024 \
  --out $OUT/CAL1-120B-U1024.txt

echo "########## B1 CALIBRATION POINT 2: 20b K=16 P0-STATIC ubatch=1024 ##########"
python3 $R/decode_replay.py \
  --route $S/ob1/runs/lease-k16-prose-a/route.log \
  --E 32 --L 24 --budget 32768 --k 4 --per-expert $PE \
  --trunk 1930678944 --logical 12109566624 --read-rate 2465240935 \
  --sets $R/../ob1/RESIDENT-SETS.json \
  --K 16 --policy P0-STATIC --ubatch 1024 \
  --label CAL2-20B-K16-STATIC-U1024 \
  --out $OUT/CAL2-20B-U1024.txt

echo "########## B1 CALIBRATION POINT 3 (extra): 20b K=0 pure streaming ubatch=1024 ##########"
python3 $R/decode_replay.py \
  --route $S/ob1b/runs/lease-k0-prose/route.log \
  --E 32 --L 24 --budget 32768 --k 4 --per-expert $PE \
  --trunk 1930678944 --logical 12109566624 --read-rate 2465240935 \
  --sets $R/../ob1/RESIDENT-SETS.json \
  --K 0 --policy P0-EMPTY --ubatch 1024 \
  --label CAL3-20B-K0-STREAM-U1024 \
  --out $OUT/CAL3-20B-U1024.txt

# ---- the hinge: the 120b at DECODE shape, every candidate policy ------
echo "########## DECODE SHAPE: 120b K=8, all candidate policies, ubatch 1 and 1024 ##########"
python3 $R/decode_replay.py \
  --route $S/ob5a/runs/p3-120b-k8-prose-a/route.log \
  --E 128 --L 36 --budget 8192 --k 4 --per-expert $PE \
  --trunk 2314020128 --logical 63387346208 --read-rate 1266753082 \
  --sets $R/../ob1b/RESIDENT-SETS-120B-K8.json \
  --K 8 \
  --policy P0-STATIC --policy P2-DECAY --policy P1-SLIDING-W512 --policy P1-SLIDING-W2048 \
  --ubatch 1 --ubatch 1024 \
  --label DECODE-120B-K8-ALLPOL \
  --out $OUT/DECODE-120B-K8.txt

# ---- the 20b decode-shape prediction for limb (b) --------------------
echo "########## LIMB (b) PREDICTION: 20b K=16 P0-STATIC, 1 chunk, ubatch 1 and 1024 ##########"
python3 $R/decode_replay.py \
  --route $S/ob1b/runs/smoke-k0-prose/route.log \
  --E 32 --L 24 --budget 1024 --k 4 --per-expert $PE \
  --trunk 1930678944 --logical 12109566624 --read-rate 2465240935 \
  --sets $R/../ob1/RESIDENT-SETS.json \
  --K 16 --policy P0-STATIC --ubatch 1024 --ubatch 1 \
  --label PREDICT-20B-K16-1CHUNK \
  --out $OUT/REPLAY-20B-1CHUNK-1.txt

# ---- the 20b full-run decode shape, for the cross-check against OB-2 --
echo "########## CROSS-CHECK: 20b 32768-token decode shape, K=16 and K=8 ##########"
python3 $R/decode_replay.py \
  --route $S/ob1/runs/lease-k16-prose-a/route.log \
  --E 32 --L 24 --budget 32768 --k 4 --per-expert $PE \
  --trunk 1930678944 --logical 12109566624 --read-rate 2465240935 \
  --sets $R/../ob1/RESIDENT-SETS.json \
  --K 16 --K 8 --policy P0-STATIC --policy P2-DECAY \
  --ubatch 1 --ubatch 1024 \
  --label XCHECK-20B-PROSE-DECODE \
  --out $OUT/XCHECK-20B-PROSE.txt

echo "########## REPLAY DIGESTS ##########"
sha256sum $OUT/*.txt
