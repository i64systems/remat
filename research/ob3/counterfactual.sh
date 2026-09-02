#!/bin/sh
# OB-3 analysis step: the held-out counterfactual.
#
# Replays the AC-CODE2 route log (produced live by this leg's r3 run; no such
# log existed before, which is why the prereg has no sim prediction for that
# row) against all three resident sets at K=16 and K=8. Same tokens, same
# routing decisions -- the identity limb proves the leased computation is
# exact, so the route log is the model's true routing -- and only the resident
# set differs. This isolates the region CHOICE from everything else, and gives
# the honest held-out comparison the leg exists to produce:
#
#   SET-PROSE on AC-CODE2   what OB-1's static prose-ranked set would have cost
#   SET-CODE  on AC-CODE2   what the detector-selected set actually cost
#   SET-MIX   on AC-CODE2   what merging instead of switching would have cost
#
# Analysis only: numpy over an already-banked log, <=4 threads, NO RUNLOCK.
#
# usage: counterfactual.sh <route.log>
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export MKL_NUM_THREADS=4
W=/mnt/f/f32/openbob-wt/ob3
S=$W/research/ob3/sim_predict.py
RL=$1
for K in 16 8; do
  python3 $S $W/research/ob1/RESIDENT-SETS.json      "$RL" $K "SET-PROSE_on_AC-CODE2"
  python3 $S $W/research/ob3/RESIDENT-SETS-CODE.json "$RL" $K "SET-CODE_on_AC-CODE2"
  python3 $S $W/research/ob3/RESIDENT-SETS-MIX.json  "$RL" $K "SET-MIX_on_AC-CODE2"
done
