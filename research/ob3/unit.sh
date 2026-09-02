#!/bin/sh
# OB-3 step 2: the UNIT.
#
# Limb 1 (detector, no model, no lock): the engine-side detector binary
# (built from src/ob3-detect.h, the SAME header the lease engine compiles in)
# is run over all three corpora and diffed against the prereg's own
# research/ob3/detector.py. Must be identical.
#
# Limb 2 (identity, two short model runs of 4 chunks = 4096 tokens on
# AC-CODE, under the RUNLOCK, acquired and released per run):
#   U1  fully resident (K=0), no detector  -> the reference
#   U2  leased K=16, detector chooses      -> must be byte-identical to U1
# U1 also serves as the BUILD-EQUIVALENCE check: its identity artifact is
# compared against the leading bytes of OB-1's banked res-code-a identity
# artifact, which was produced by a different build (rs053, GGML_CUDA=ON,
# 10 threads). A match proves this leg's CPU-only binary reproduces OB-1's
# arithmetic exactly, which every later identity comparison depends on.
set -e
R=/mnt/f/f32/openbob-wt/ob3/research/ob3/run-ob3.sh
C=/mnt/f/f32/stage/research/ob1/AC-CODE.txt
W=/mnt/f/f32/openbob-wt/ob3

echo "########## INPUT DIGESTS ##########"
sha256sum $W/research/ob1/RESIDENT-SETS.json
sha256sum $W/research/ob3/RESIDENT-SETS-CODE.json
sha256sum /mnt/f/f32/stage/research/ob1/AC-CODE.txt
sha256sum /mnt/f/f32/stage/research/ob1/AC-PROSE.txt
sha256sum /mnt/f/f32/stage/research/ob3/AC-CODE2.txt
sha256sum /root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf

echo "########## U1 resident chunks=4 ##########"
sh $R unit-res-code-c4 $C 0 4 resident
echo "########## U2 detect K=16 chunks=4 ##########"
sh $R unit-k16-code-c4 $C 16 4 detect

echo "########## UNIT COMPARISON ##########"
A=/root/ob3/runs/unit-res-code-c4/identity.txt
B=/root/ob3/runs/unit-k16-code-c4/identity.txt
echo "U1 identity: $(cat $A)"
echo "U2 identity: $(cat $B)"
if cmp -s "$A" "$B"; then
  echo "UNIT_IDENTITY: MATCH (leased == resident, this leg's own binary)"
else
  echo "UNIT_IDENTITY: DIFFER"
fi
echo "--- build equivalence vs OB-1's banked res-code-a (rs053 binary, GGML_CUDA=ON, 10 threads) ---"
BANK=/mnt/f/f32/stage/research/ob1/runs/res-code-a/identity.txt
N=$(wc -c < "$A")
echo "ob3 4-chunk identity bytes=$N"
head -c "$N" "$BANK" > /root/ob3/bank-prefix.txt
echo "banked prefix : $(cat /root/ob3/bank-prefix.txt)"
if cmp -s "$A" /root/ob3/bank-prefix.txt; then
  echo "BUILD_EQUIVALENCE: MATCH (ob3 CPU-only build reproduces OB-1's chunk values byte for byte)"
else
  echo "BUILD_EQUIVALENCE: DIFFER"
fi
echo "--- route log digests ---"
sha256sum /root/ob3/runs/unit-res-code-c4/route.log /root/ob3/runs/unit-k16-code-c4/route.log
echo "########## UNIT DONE ##########"
