#!/bin/sh
# OB-2 stage 2, step 3: the leg's full run matrix, frozen in
# research/OB2-PREDICTIVE-1-PREREG.md section 8.
#
#   K in {16, 8} x {AC-PROSE, AC-CODE}   4 leased runs under the dynamic policy
#   dyn-k16-code-b                       the A/A repeat of the hardest case, to
#                                        show the dynamic policy is reproducible
#                                        run to run and not merely byte-exact
#                                        against a reference within one run
#
# No new fully-resident run is needed: OB-1's banked res-prose-a and res-code-a
# are the identity and cost comparison points (prereg section 8).
#
# Each run takes and releases the box-wide RUNLOCK on its own (see
# locked-run.sh), so the sibling workflow interleaves BETWEEN runs rather than
# waiting out the whole matrix.
OB2=/mnt/f/f32/openbob-wt/research-2/research/ob2
AC_PROSE=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
AC_CODE=/mnt/f/f32/stage/research/ob1/AC-CODE.txt

# hardest case first: at K=16 on code the frozen winner's predicted advantage
# over OB-1's static set is largest (14.3759% vs 60.5733%), so a policy or
# boundary bug shows up here first and cheapest
sh "$OB2/locked-run.sh" dyn-k16-code-a  "$AC_CODE"  16 32
sh "$OB2/locked-run.sh" dyn-k16-code-b  "$AC_CODE"  16 32
sh "$OB2/locked-run.sh" dyn-k16-prose   "$AC_PROSE" 16 32
sh "$OB2/locked-run.sh" dyn-k8-code     "$AC_CODE"   8 32
sh "$OB2/locked-run.sh" dyn-k8-prose    "$AC_PROSE"  8 32
echo "########## MATRIX DONE ##########"
