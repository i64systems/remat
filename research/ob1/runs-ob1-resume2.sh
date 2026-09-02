#!/bin/sh
# OB-1 stage 2: second resume, after the resident-set JSON key scan was fixed
# (fork commit c087083; see RUNLOG-1.txt deviation D6). The K=8 and K=4 runs had
# aborted loudly at startup with "resident_sets[\"8\"] is not an object", because
# a bare search for the key "8" matched layer key 8 inside the K=16 set. No run
# produced a wrong number: the engine refused to start.
#
# lease-k16-prose-c re-runs an already-completed K=16 case with the REBUILT
# binary. Its identity artifact must equal lease-k16-prose-a's, which ties the
# two builds together and makes the runs from before the rebuild comparable with
# the ones after it.
SH=/mnt/f/f32/openbob-wt/research-2/research/ob1/run-ob1.sh
AC_PROSE=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
AC_CODE=/mnt/f/f32/stage/research/ob1/AC-CODE.txt

sh "$SH" lease-k16-prose-c "$AC_PROSE" 16 0
sh "$SH" lease-k8-prose    "$AC_PROSE" 8  0
sh "$SH" lease-k8-code     "$AC_CODE"  8  0
sh "$SH" lease-k4-prose    "$AC_PROSE" 4  0
sh "$SH" lease-k4-code     "$AC_CODE"  4  0
echo "RESUME2 MATRIX COMPLETE"
