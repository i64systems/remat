#!/bin/sh
# OB-5b S1 gate 0 driver. Analysis only: no model, no runlock, no serve contact.
# Runs the top-8 mass read over the BANKED RS053 120b route logs, twice on the
# primary input for the A/A reproducibility limb, and once each on the -b logs
# as a free end-to-end check.
set -e

PY=/root/openbob-train/venv/bin/python
SRC=/mnt/f/f32/openbob-wt/research-2/research/ob5b1
WORK=/root/ob5b1
OUT=/mnt/f/f32/stage/research/ob5b1/gate0
SETS=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json
RUNS=/mnt/f/f32/stage/research/rs053/runs

mkdir -p "$OUT" "$WORK"
tr -d '\r' < "$SRC/gate0_top8.py" > "$WORK/gate0_top8.py"

echo "=== OB5B S1 GATE 0: THE TOP-8 MASS READ ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "--- free -m ---"
free -m
echo "--- python ---"
$PY -c 'import sys, numpy; print("python", sys.version.split()[0]); print("numpy", numpy.__version__)'
echo "--- script digest (the one actually executed) ---"
sha256sum "$WORK/gate0_top8.py"
echo "--- inputs, digests ---"
sha256sum "$SETS" \
  "$RUNS/120b-prose-a/route.log" "$RUNS/120b-prose-b/route.log" \
  "$RUNS/120b-code-a/route.log"  "$RUNS/120b-code-b/route.log"

for L in 120b-prose-a 120b-prose-b 120b-code-a 120b-code-b; do
  echo "--- $L ---"
  nice -n 10 $PY "$WORK/gate0_top8.py" \
    --route "$RUNS/$L/route.log" --label "$L" --sets "$SETS" \
    --out "$OUT/$L.json"
done

echo "--- A/A DETERMINISM LIMB: same input, second output, byte compare ---"
nice -n 10 $PY "$WORK/gate0_top8.py" \
  --route "$RUNS/120b-prose-a/route.log" --label 120b-prose-a --sets "$SETS" \
  --out "$OUT/120b-prose-a.det2.json"
if cmp "$OUT/120b-prose-a.json" "$OUT/120b-prose-a.det2.json"; then
  echo "DETCHECK_CMP_RC=0 IDENTICAL"
else
  echo "DETCHECK_CMP_RC=$? *** NOT IDENTICAL ***"
fi

echo "--- FREE CHECK: -a vs -b reports, ignoring only label/path/digest fields ---"
nice -n 10 $PY - <<'PYEOF'
import json
base = "/mnt/f/f32/stage/research/ob5b1/gate0/"
skip = {"label", "route_log", "route_log_sha256"}
for pair in [("120b-prose-a", "120b-prose-b"), ("120b-code-a", "120b-code-b")]:
    a = json.load(open(base + pair[0] + ".json"))
    b = json.load(open(base + pair[1] + ".json"))
    for k in skip:
        a.pop(k, None)
        b.pop(k, None)
    print("%s vs %s: METRICS_EQUAL=%s" % (pair[0], pair[1], a == b))
PYEOF

echo "--- output digests ---"
sha256sum "$OUT"/*.json
echo "guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== END GATE 0 ANALYSIS ==="
