#!/bin/sh
# OB-1 stage 2: resume of runs-ob1.sh after the harness terminated the process
# that had launched it (see RUNLOG-1.txt section 12, deviation D5). At that point
# res-prose-a, res-prose-b, res-code-a, lease-k16-prose-a and lease-k16-prose-b
# had completed and been staged; lease-k16-code was killed part way through and
# had produced no identity artifact and no stats file, so it is re-run here from
# the start. No guard process was signalled: pids 654 and 489 were verified alive
# immediately afterwards.
#
# Same driver, same binary, same flags as runs-ob1.sh.
SH=/mnt/f/f32/openbob-wt/research-2/research/ob1/run-ob1.sh
AC_PROSE=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
AC_CODE=/mnt/f/f32/stage/research/ob1/AC-CODE.txt

sh "$SH" lease-k16-code       "$AC_CODE"  16 0
sh "$SH" lease-k8-prose       "$AC_PROSE" 8  0
sh "$SH" lease-k8-code        "$AC_CODE"  8  0
sh "$SH" lease-k4-prose       "$AC_PROSE" 4  0
sh "$SH" lease-k4-code        "$AC_CODE"  4  0
sh "$SH" lease-k16-prose-fadv "$AC_PROSE" 16 1
echo "RESUME MATRIX COMPLETE"
