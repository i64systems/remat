#!/bin/bash
# BOB-MOE-0 STAGE 2, THE FUNDED RUN (BOBMOE0-STAGE2-PLAN.txt s.3).
# Both arms, MoE FIRST, SEQUENTIAL inside ONE launcher so no manual step sits between
# them. Each arm RESUMES from its own G1-CARD runA step-1000 checkpoint (prefix
# compute reused, plan s.2 BUDGET NOTE) and runs to the frozen total 15259 with
# the frozen stage-2 cadence: every 1000 steps plus 15259.
#
# Pre-launch gates L1/L2/L3 are logged literally before EVERY arm and WAIT
# (poll 60 s, timestamped) rather than contend. The hyde serve is a BYSTANDER:
# its pid is read, never signalled, never killed. SCHEDULED DEMOS PREEMPT: the PREEMPT
# file is honored by the trainer at every checkpoint boundary (W5) and by this
# launcher BETWEEN arms. The W6 temp rule is armed inside the trainer.
#
# Markers, all under /mnt/f/f32/stage/lowint/moe0-ckpt/stage2/ :
#   <arm>/ARM-DONE   this launcher, when the arm reached step 15259
#   DONE             this launcher, when BOTH arms completed (collector trigger;
#                    Windows F:\f32\stage\lowint\moe0-ckpt\stage2\DONE)
#   <arm>/PREEMPTED  the trainer, on a PREEMPT-file boundary exit
#   <arm>/TEMPSTOP   the trainer, on the 3-consecutive-sample >= 90 C rule
#   PREEMPTED-BETWEEN-ARMS  this launcher, if PREEMPT appears between the arms
# No DONE is ever written on an early exit.
#
# SEG names this launch attempt's log files so a later resume segment cannot
# overwrite this segment's evidence (plan s.5, the segment chain). SEG=seg01 by
# default; a resume launch passes SEG=seg02 and its own RESUME_<arm> override.
# Pure ASCII.
set -u

REPO=/mnt/f/f32/openbob-wt/low-int
PY=/root/openbob-train/venv/bin/python
DATA=/mnt/f/f32/stage/lowint/data/enwik8/enwik8
ROOT=/mnt/f/f32/stage/lowint/moe0-ckpt/stage2
G1ROOT=$ROOT/g1card
SERVE_PID_FILE=/root/.local/share/openbob/serve.pid
PREEMPT=$REPO/lowint/moe0/PREEMPT
SEG=${SEG:-seg01}
GATELOG=$ROOT/gates-stage2-$SEG.log
FINAL_STEP=15259

# THE PROVEN G1-CARD ENVELOPE, CARRIED EXACTLY (leg-g1card.txt s.2).
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONHASHSEED=0
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8

mkdir -p "$ROOT"
: > "$GATELOG"

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
gl() { echo "[$(ts)] $*" >> "$GATELOG"; echo "[$(ts)] $*"; }

gates() {
  local tag="$1"
  gl "GATES BEGIN $tag"
  local serve
  serve=$(cat "$SERVE_PID_FILE" 2>/dev/null || echo NONE)
  gl "L1 serve.pid=$serve (BYSTANDER, never signalled)"
  # busy-flag literal search: no busy-flag file exists today.
  local busy
  busy=$(ls -1 /root/.local/share/openbob/ 2>/dev/null | grep -i -E 'busy|lock' || true)
  if [ -n "$busy" ]; then
    gl "L1 BUSY FLAG PRESENT: $busy -- WAITING"
    while [ -n "$busy" ]; do
      sleep 60
      busy=$(ls -1 /root/.local/share/openbob/ 2>/dev/null | grep -i -E 'busy|lock' || true)
      gl "L1 busy poll: [$busy]"
    done
  else
    gl "L1 busy-flag literal search: NO BUSY FLAG FILE PRESENT"
  fi
  # L1 compute apps: nothing on the card but the serve.
  while true; do
    local apps others
    apps=$(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader)
    gl "L1 compute-apps: [$(echo "$apps" | tr '\n' ';')]"
    others=$(echo "$apps" | awk -F, 'NF{gsub(/ /,"",$1); print $1}' | grep -v "^${serve}$" || true)
    if [ -z "$others" ]; then break; fi
    gl "L1 FOREIGN COMPUTE PID(S) [$others] -- WAITING 60 s, never contend, never signal"
    sleep 60
  done
  # L2 host memory
  while true; do
    local avail
    avail=$(free -m | awk '/^Mem:/{print $7}')
    gl "L2 free -m available=$avail MiB (bar > 12288)"
    if [ "$avail" -gt 12288 ]; then break; fi
    gl "L2 BELOW BAR -- WAITING 60 s"
    sleep 60
  done
  # L3 card memory
  while true; do
    local gfree gtemp
    gfree=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits)
    gtemp=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits)
    gl "L3 gpu memory.free=$gfree MiB (bar >= 8192) gpu_temp_c=$gtemp"
    if [ "$gfree" -ge 8192 ]; then break; fi
    gl "L3 BELOW BAR -- WAITING 60 s"
    sleep 60
  done
  # Informational only, NOT a gate (s.3 names L1-L3 and no other bar):
  gl "INFO checkpoint volume free: $(df -m "$ROOT" | awk 'NR==2{print $4" MiB"}')"
  gl "GATES PASS $tag"
}

# run_arm <arm>
#   rc 0 = arm reached step 15259, ARM-DONE written
#   rc 1 = failure or incomplete (no marker)
#   rc 2 = PREEMPTED by the demo-preemption file at a checkpoint boundary (resumable)
#   rc 3 = TEMPSTOP by the frozen temp rule (resumable)
#   rc 4 = named refusal: the resume anchor is missing
run_arm() {
  local arm="$1"
  local ad="$ROOT/$arm"
  local rc pypid
  mkdir -p "$ad"
  local DL="$ad/CKPT-DIGESTS.txt"

  # Resume source: this arm's own G1-CARD runA step-1000 checkpoint, unless a
  # resume launch overrides it (RESUME_MOE / RESUME_DENSE).
  local anchor
  if [ "$arm" = "moe" ]; then
    anchor="${RESUME_MOE:-$G1ROOT/moe/A/step001000.safetensors}"
  else
    anchor="${RESUME_DENSE:-$G1ROOT/dense/A/step001000.safetensors}"
  fi
  local sidecar="${anchor%.safetensors}.resume.pt"
  if [ ! -f "$anchor" ] || [ ! -f "$sidecar" ]; then
    gl "REFUSAL $arm: resume anchor incomplete [$anchor] [$sidecar]"
    return 4
  fi
  gl "ANCHOR $arm safetensors=$(sha256sum "$anchor")"
  gl "ANCHOR $arm sidecar=$(sha256sum "$sidecar")"

  gates "$arm"
  gl "LAUNCH $arm FUNDED seg=$SEG resume=$anchor to step $FINAL_STEP, frozen cadence"
  $PY "$REPO/lowint/moe0/train/bobmoe0.py" \
    --arm "$arm" --stage 2 --run "FUNDED-$SEG" --device cuda --grad-ckpt \
    --data "$DATA" --ckpt-dir "$ad" \
    --log "$ad/metrics-$SEG.tsv" --progress "$ad/progress-$SEG.txt" \
    --digest-log "$DL" --threads 8 \
    --preempt-file "$PREEMPT" \
    --resume "$anchor" \
    > "$ad/run-$SEG.out" 2>&1 &
  pypid=$!
  gl "PYTHON_PID $arm=$pypid"
  wait "$pypid"
  rc=$?
  gl "EXIT $arm rc=$rc"

  if [ "$rc" -ne 0 ]; then
    gl "ARM FAILED $arm rc=$rc: see $ad/run-$SEG.out"
    return 1
  fi
  if [ -f "$ad/PREEMPTED" ]; then
    gl "ARM PREEMPTED $arm: [$(cat "$ad/PREEMPTED")] resumable, no ARM-DONE"
    return 2
  fi
  if [ -f "$ad/TEMPSTOP" ]; then
    gl "ARM TEMPSTOP $arm: [$(cat "$ad/TEMPSTOP")] resumable, no ARM-DONE"
    return 3
  fi
  if [ ! -f "$ad/step0$FINAL_STEP.safetensors" ]; then
    gl "ARM INCOMPLETE $arm: step$FINAL_STEP checkpoint absent, no ARM-DONE"
    return 1
  fi
  touch "$ad/ARM-DONE"
  gl "ARM-DONE $arm (final checkpoint present)"
  return 0
}

gl "STAGE2 FUNDED RUN BEGIN seg=$SEG launcher_pid=$$"
gl "ENVELOPE cublas=[$CUBLAS_WORKSPACE_CONFIG] pythonhashseed=[$PYTHONHASHSEED] omp=[$OMP_NUM_THREADS] mkl=[$MKL_NUM_THREADS]"

if [ -f "$PREEMPT" ]; then
  gl "PREEMPT PRESENT AT LAUNCH: nothing started. Scheduled demos preempt. exit 0"
  exit 0
fi

run_arm moe
RC_MOE=$?
if [ "$RC_MOE" -ne 0 ]; then
  gl "STOP after moe rc=$RC_MOE. dense NOT started. NO DONE marker."
  exit "$RC_MOE"
fi

if [ -f "$PREEMPT" ]; then
  gl "PREEMPT BETWEEN ARMS: dense NOT started, resumable, NO DONE marker"
  date -u +%Y-%m-%dT%H:%M:%SZ > "$ROOT/PREEMPTED-BETWEEN-ARMS"
  exit 0
fi

run_arm dense
RC_DENSE=$?
if [ "$RC_DENSE" -ne 0 ]; then
  gl "STOP after dense rc=$RC_DENSE. NO DONE marker."
  exit "$RC_DENSE"
fi

date -u +%Y-%m-%dT%H:%M:%SZ > "$ROOT/DONE"
gl "STAGE2 DONE both arms. DONE marker written: $ROOT/DONE"
