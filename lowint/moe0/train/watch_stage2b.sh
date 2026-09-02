#!/bin/bash
# BOB-MOE-0 STAGE 2B seg02 WATCHER (BOBMOE0-STAGE2B-PLAN s.4,
# FAILURE-AWARE MONITORING).
#
# This watcher OBSERVES ONLY. It never signals, never kills, never writes any
# file except its own log and the FAILED-seg02 marker. The hyde serve is a
# bystander; no pid is ever read for signalling purposes.
#
# Poll 60 s:
#   - append "[UTC] arm=<moe|dense> <last line of that arm's progress-seg02.txt>"
#     to watch-seg02.log (the active arm is the one whose progress file was
#     modified most recently; moe runs first, dense second)
#   - on "ARM FAILED" in launcher-seg02.out: write FAILED-seg02 carrying the
#     quoted line plus UTC, then exit
#   - on the DONE marker: write a final line, then exit
#   - on PREEMPTED / TEMPSTOP / PREEMPTED-BETWEEN-ARMS markers: note in the log,
#     then exit (resumable states, not failures)
# Pure ASCII.
set -u

ROOT=/mnt/f/f32/stage/lowint/moe0-ckpt/stage2
LOG=$ROOT/watch-seg02.log
LAUNCHER_OUT=$ROOT/launcher-seg02.out
FAILED=$ROOT/FAILED-seg02
DONE=$ROOT/DONE
POLL=60

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
wl() { echo "[$(ts)] $*" >> "$LOG"; }

wl "WATCHER BEGIN pid=$$ poll=${POLL}s root=$ROOT (observe only, never signals)"

while true; do
  # (ii) failure marker: one file an external monitor can watch
  if [ -f "$LAUNCHER_OUT" ]; then
    line=$(grep -m1 "ARM FAILED" "$LAUNCHER_OUT" 2>/dev/null || true)
    if [ -n "$line" ]; then
      {
        echo "utc=$(ts)"
        echo "$line"
        echo "source=$LAUNCHER_OUT"
      } > "$FAILED"
      wl "ARM FAILED SEEN: [$line] -- FAILED-seg02 written at $FAILED. WATCHER EXIT"
      exit 0
    fi
  fi

  # (iii) success marker
  if [ -f "$DONE" ]; then
    wl "DONE MARKER SEEN: [$(cat "$DONE" 2>/dev/null | tr '\n' ' ')] both arms complete. WATCHER EXIT"
    exit 0
  fi

  # (iv) resumable stop markers
  for m in "$ROOT/PREEMPTED-BETWEEN-ARMS" "$ROOT/moe/PREEMPTED" "$ROOT/dense/PREEMPTED" \
           "$ROOT/moe/TEMPSTOP" "$ROOT/dense/TEMPSTOP"; do
    if [ -f "$m" ]; then
      wl "RESUMABLE MARKER SEEN: $m [$(cat "$m" 2>/dev/null | tr '\n' ' ')] WATCHER EXIT"
      exit 0
    fi
  done

  # (i) monitor line from the active arm's progress file
  active=""
  newest=0
  for arm in moe dense; do
    p=$ROOT/$arm/progress-seg02.txt
    if [ -f "$p" ]; then
      m=$(stat -c %Y "$p" 2>/dev/null || echo 0)
      if [ "$m" -ge "$newest" ]; then
        newest=$m
        active=$arm
      fi
    fi
  done
  if [ -n "$active" ]; then
    last=$(tail -n 1 "$ROOT/$active/progress-seg02.txt" 2>/dev/null || true)
    wl "arm=$active $last"
  else
    wl "arm=none no progress-seg02.txt yet (gates or startup)"
  fi

  sleep "$POLL"
done
