#!/bin/sh
# OB-5b S1 gate 0, derived half: the 64-token window limb and the decode
# arithmetic. Analysis only.
set -e
PY=/root/openbob-train/venv/bin/python
SRC=/mnt/f/f32/openbob-wt/research-2/research/ob5b1
WORK=/root/ob5b1

tr -d '\r' < "$SRC/gate0_window.py"  > "$WORK/gate0_window.py"
tr -d '\r' < "$SRC/gate0_project.py" > "$WORK/gate0_project.py"

echo "=== OB5B S1 GATE 0 DERIVED ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
sha256sum "$WORK/gate0_window.py" "$WORK/gate0_project.py"
echo "--- window limb ---"
nice -n 10 $PY "$WORK/gate0_window.py"
echo "--- window limb, second run, byte compare (A/A) ---"
cp /mnt/f/f32/stage/research/ob5b1/gate0/window64.json /root/ob5b1/window64.first.json
nice -n 10 $PY "$WORK/gate0_window.py" > /dev/null
if cmp /root/ob5b1/window64.first.json /mnt/f/f32/stage/research/ob5b1/gate0/window64.json; then
  echo "WINDOW_DETCHECK_CMP_RC=0 IDENTICAL"
else
  echo "WINDOW_DETCHECK *** NOT IDENTICAL ***"
fi
echo ""
nice -n 10 $PY "$WORK/gate0_project.py"
echo "guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
