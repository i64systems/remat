#!/bin/sh
# OB-3 step 3: the frozen live-run plan (OB3-REGION-1-PREREG
# section 6), plus the one resident baseline that section 7's IDENTITY limb
# requires for the AC-CODE2 row. Row 3 has no banked fully-resident reference
# because OB-1 never ran AC-CODE2, and the identity limb is stop-ship for
# every leased run in section 6; r0-res-code2 supplies it, and doubles as a
# same-thread cost baseline for the AC-CODE2 row.
#
# run-ob3.sh acquires and releases the box-wide RUNLOCK per run, so a sibling
# workflow interleaves between runs.
R=/mnt/f/f32/openbob-wt/ob3/research/ob3/run-ob3.sh
P=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
C=/mnt/f/f32/stage/research/ob1/AC-CODE.txt
C2=/mnt/f/f32/stage/research/ob3/AC-CODE2.txt

sh $R r1-k16-code     $C  16 32 detect   # in-domain row,   sim 14.4536 pct
sh $R r0-res-code2    $C2  0 32 resident # identity + cost reference for r3
sh $R r3-k16-code2    $C2 16 32 detect   # HELD-OUT HEADLINE, no sim exists
sh $R r4-k16-prose    $P  16 32 detect   # no-regression,   sim 18.8048 pct
sh $R r2-k8-code      $C   8 32 detect   #                  sim 36.9441 pct
sh $R r5-k16-code-aa  $C  16 32 detect   # A/A repeat of r1
echo "########## ALL FULL RUNS DONE ##########"
date -u +%Y-%m-%dT%H:%M:%SZ
