#!/bin/sh
# OB-1 stage 2, step 3: the leg's full run matrix.
#
#   res-*     fully resident on this leg's CPU configuration -- the byte-identity
#             reference the leased runs are compared against (stage 1's
#             committed baseline is a different backend; see run-ob1.sh header)
#   lease-*   leased, K in {16, 8, 4}, both acceptance corpora
#   *-a/*-b   an A/A pair (same run twice) to show the run itself is stable
#   *-fadv    the same K=16 prose run with the OS page cache dropped for every
#             leased range, so the cold tier is genuinely cold NVMe
set -e
SH=/mnt/f/f32/openbob-wt/research-2/research/ob1/run-ob1.sh
AC_PROSE=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
AC_CODE=/mnt/f/f32/stage/research/ob1/AC-CODE.txt

sh "$SH" res-prose-a        "$AC_PROSE" 0  0
sh "$SH" res-prose-b        "$AC_PROSE" 0  0
sh "$SH" res-code-a         "$AC_CODE"  0  0
sh "$SH" lease-k16-prose-a  "$AC_PROSE" 16 0
sh "$SH" lease-k16-prose-b  "$AC_PROSE" 16 0
sh "$SH" lease-k16-code     "$AC_CODE"  16 0
sh "$SH" lease-k8-prose     "$AC_PROSE" 8  0
sh "$SH" lease-k8-code      "$AC_CODE"  8  0
sh "$SH" lease-k4-prose     "$AC_PROSE" 4  0
sh "$SH" lease-k4-code      "$AC_CODE"  4  0
sh "$SH" lease-k16-prose-fadv "$AC_PROSE" 16 1
