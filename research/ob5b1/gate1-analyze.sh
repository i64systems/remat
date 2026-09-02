#!/bin/sh
# OB-5b S1: post-gate analysis. Re-reads gate 1's own routing trace with gate
# 0's definitions, and digests every artifact this leg banks.
set -e
PY=/root/openbob-train/venv/bin/python
SRC=/mnt/f/f32/openbob-wt/research-2/research/ob5b1
WORK=/root/ob5b1
tr -d '\r' < "$SRC/gate1_route_check.py" > "$WORK/gate1_route_check.py"
tr -d '\r' < "$SRC/sha-artifacts.sh"     > "$WORK/sha-artifacts.sh"

echo "=== OB5B1 POST-GATE ANALYSIS ==="
echo "utc $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
sha256sum "$WORK/gate1_route_check.py"
echo ""
nice -n 10 $PY "$WORK/gate1_route_check.py" \
  /root/ob5b1/runs/gen-120b-k8-a/route.log 56 32 \
  /root/ob5b1/runs/gen-120b-k8-a/ob1-stats.txt
echo ""
echo "=== ARTIFACT DIGESTS ==="
sh "$WORK/sha-artifacts.sh"
echo "guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
