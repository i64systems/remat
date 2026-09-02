#!/bin/sh
# OB-5a builder 2b: the P3 120b A/A pair on the reserve/commit allocator.
# Two locked runs at the frozen configuration, then the A/A comparison.
# Every expectation is passed in on the command line from material committed
# before this leg, so no verdict is decided after seeing an output.

D=/mnt/f/f32/stage/research/ob5a
DRIVER=$D/run-120b-night.sh
LOGS=$D/logs-night
mkdir -p "$LOGS"

# The banked paged reference pair, from OB5A-ALLOC-1-PREREG.md section 7 P3a.
EXP_ID=9d20bd0365554989051d96b6ad4932625b0a6578002879f8253e6fcc21682019
EXP_RT=a32d0051bd6d68f2777e64c7b889ae48d56621e9701b107fcef88c0e30cd89c1

echo "########## OB5A NIGHT 120B P3 $(date -u +%Y-%m-%dT%H:%M:%SZ) ##########"
echo "box state before anything:"
echo "  vm.overcommit_memory $(cat /proc/sys/vm/overcommit_memory)"
echo "  vm.overcommit_ratio  $(cat /proc/sys/vm/overcommit_ratio)"
echo "  vm.max_map_count     $(cat /proc/sys/vm/max_map_count)"
echo "  guard_pids: $(ps -o pid= -p 654 | wc -l) openbob(654), $(ps -o pid= -p 489 | wc -l) searxng(489)"
echo "banked paged reference identity $EXP_ID"
echo "banked paged reference route    $EXP_RT"

sh "$DRIVER" p3-120b-k8-prose-a 8 "$EXP_ID" "$EXP_RT" > "$LOGS/p3-120b-k8-prose-a.log" 2>&1
ARC=$?
echo "=== run A rc=$ARC ==="
grep -E "^exit_rc|^wallclock_s|^overcommit_at_run|^overcommit_after_run|oom_score_adj_measured|identity: |route: |Maximum resident set size|P4c:" "$LOGS/p3-120b-k8-prose-a.log"

if [ $ARC -ne 0 ]; then
  echo "RUN A FAILED rc=$ARC. Run B is NOT attempted. Full log follows verbatim."
  cat "$LOGS/p3-120b-k8-prose-a.log"
  echo "overcommit_final: $(cat /proc/sys/vm/overcommit_memory)"
  exit $ARC
fi

sh "$DRIVER" p3-120b-k8-prose-b 8 "$EXP_ID" "$EXP_RT" > "$LOGS/p3-120b-k8-prose-b.log" 2>&1
BRC=$?
echo "=== run B rc=$BRC ==="
grep -E "^exit_rc|^wallclock_s|^overcommit_at_run|^overcommit_after_run|oom_score_adj_measured|identity: |route: |Maximum resident set size|P4c:" "$LOGS/p3-120b-k8-prose-b.log"

echo "########## P3e THE A/A COMPARISON ##########"
RA=/root/ob5a/runs/p3-120b-k8-prose-a
RB=/root/ob5a/runs/p3-120b-k8-prose-b
for f in identity.txt route.log; do
  if cmp -s "$RA/$f" "$RB/$f"; then echo "A/A $f: MATCH (byte for byte)"; else echo "A/A $f: *** DIFFER ***"; cmp "$RA/$f" "$RB/$f" | head -3; fi
done
echo "digests:"
sha256sum "$RA/identity.txt" "$RB/identity.txt" "$RA/route.log" "$RB/route.log" 2>&1
echo "against the banked paged reference:"
echo "  identity $EXP_ID"
echo "  route    $EXP_RT"
echo "alloc journal digests (P4b):"
grep '^alloc_journal_sha256=' "$RA/ob1-stats.txt" "$RB/ob1-stats.txt" 2>&1
echo "########## STATS A ##########"
cat "$RA/ob1-stats.txt" 2>&1
echo "########## STATS B ##########"
cat "$RB/ob1-stats.txt" 2>&1
echo "overcommit_final: $(cat /proc/sys/vm/overcommit_memory)"
echo "guard_pids_final: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "########## NIGHT 120B DONE $(date -u +%Y-%m-%dT%H:%M:%SZ) rc_a=$ARC rc_b=$BRC ##########"
