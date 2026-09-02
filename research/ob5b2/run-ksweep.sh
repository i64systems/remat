#!/bin/sh
# OB-5b P05 limb (a), second pass: THE PRODUCT KNOB AT DECODE SHAPE.
#
# C4 section 6.1 calls its K-sweep "THE PRODUCT KNOB ... the first place
# in this program where exposure and usability trade against each other
# on a surface someone will actually touch". That table was built at batch
# shape arithmetic. This is the same knob measured at the shape the
# product runs at: for each resident-set size K, what read-bound
# tokens-per-second ceiling does the 120b actually have when it decodes
# one token at a time.
#
# The dynamic policies need no external resident-set file (they build
# residency from the route history), which is why this sweep can reach
# K values the house has never banked a frozen set for.
#
# ANALYSIS ONLY. No model, no runlock, no weights. nice 10 so the
# sibling holding the lock does not notice this leg exists.
OUT=$1
R=/mnt/f/f32/openbob-wt/research-2/research/ob5b2
S=/mnt/f/f32/stage/research
mkdir -p "$OUT"

nice -n 10 python3 $R/decode_replay.py \
  --route $S/ob5a/runs/p3-120b-k8-prose-a/route.log \
  --E 128 --L 36 --budget 8192 --k 4 --per-expert 13253760 \
  --trunk 2314020128 --logical 63387346208 --read-rate 1266753082 \
  --K 0 --policy P0-EMPTY --ubatch 1 --ubatch 1024 \
  --label KSWEEP-120B-K0-FLOOR \
  --out $OUT/KSWEEP-120B-K0.txt

nice -n 10 python3 $R/decode_replay.py \
  --route $S/ob5a/runs/p3-120b-k8-prose-a/route.log \
  --E 128 --L 36 --budget 8192 --k 4 --per-expert 13253760 \
  --trunk 2314020128 --logical 63387346208 --read-rate 1266753082 \
  --K 8 --K 16 --K 24 --K 32 --K 48 --K 64 \
  --policy P2-DECAY --ubatch 1 \
  --label KSWEEP-120B-P2DECAY-DECODE \
  --out $OUT/KSWEEP-120B-P2DECAY.txt

sha256sum $OUT/KSWEEP-120B-K0.txt $OUT/KSWEEP-120B-P2DECAY.txt
