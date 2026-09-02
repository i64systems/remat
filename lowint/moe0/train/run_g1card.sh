#!/bin/bash
# BOB-MOE-0 STAGE 2, G1-CARD PREFIX PROOF (BOBMOE0-STAGE2-PLAN.txt s.2).
# Both arms, MoE FIRST, SEQUENTIAL inside ONE launcher so no manual step sits between
# them. Three CLEAN OS processes per arm:
#   A        steps 1..1100 straight,  checkpoints {100, 1000, 1100}
#   B        steps 1..1000, clean exit, checkpoints {100, 1000}
#   Bresume  a THIRD process resuming B's step-1000, steps 1001..1100, ckpt 1100
# Pre-run gates L1/L2/L3 are logged literally before EVERY process and WAIT
# (poll 60 s) rather than contend. The hyde serve is a BYSTANDER: its pid is
# read, never signalled, never killed.
# Pure ASCII.
set -u

REPO=/mnt/f/f32/openbob-wt/low-int
PY=/root/openbob-train/venv/bin/python
DATA=/mnt/f/f32/stage/lowint/data/enwik8/enwik8
ROOT=/mnt/f/f32/stage/lowint/moe0-ckpt/stage2/g1card
SERVE_PID_FILE=/root/.local/share/openbob/serve.pid
GATELOG=$ROOT/gates.log

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
  gl "GATES PASS $tag"
}

run_arm() {
  local arm="$1"
  local ad="$ROOT/$arm"
  mkdir -p "$ad/A" "$ad/B" "$ad/Bresume"
  local DL="$ad/CKPT-DIGESTS.txt"

  gates "$arm/A"
  gl "LAUNCH $arm runA steps 1..1100 ckpt {100,1000,1100}"
  $PY "$REPO/lowint/moe0/train/bobmoe0.py" \
    --arm "$arm" --stage 2 --run A --device cuda --grad-ckpt \
    --data "$DATA" --ckpt-dir "$ad/A" \
    --log "$ad/A/metrics.tsv" --progress "$ad/A/progress.txt" \
    --digest-log "$DL" --threads 8 \
    --stop-after-step 1100 --ckpt-steps 100,1000,1100 \
    > "$ad/A/run.out" 2>&1
  gl "EXIT $arm runA rc=$?"

  gates "$arm/B"
  gl "LAUNCH $arm runB steps 1..1000 ckpt {100,1000}"
  $PY "$REPO/lowint/moe0/train/bobmoe0.py" \
    --arm "$arm" --stage 2 --run B --device cuda --grad-ckpt \
    --data "$DATA" --ckpt-dir "$ad/B" \
    --log "$ad/B/metrics.tsv" --progress "$ad/B/progress.txt" \
    --digest-log "$DL" --threads 8 \
    --stop-after-step 1000 --ckpt-steps 100,1000 \
    > "$ad/B/run.out" 2>&1
  gl "EXIT $arm runB rc=$?"

  gates "$arm/Bresume"
  gl "LAUNCH $arm runB-resume steps 1001..1100 ckpt {1100} from B/step001000"
  $PY "$REPO/lowint/moe0/train/bobmoe0.py" \
    --arm "$arm" --stage 2 --run Bresume --device cuda --grad-ckpt \
    --data "$DATA" --ckpt-dir "$ad/Bresume" \
    --log "$ad/Bresume/metrics.tsv" --progress "$ad/Bresume/progress.txt" \
    --digest-log "$DL" --threads 8 \
    --resume "$ad/B/step001000.safetensors" \
    --stop-after-step 1100 --ckpt-steps 1100 \
    > "$ad/Bresume/run.out" 2>&1
  gl "EXIT $arm runB-resume rc=$?"

  touch "$ad/ARM-G1CARD-DONE"
  gl "ARM DONE $arm"
}

gl "G1CARD BEGIN"
run_arm moe
run_arm dense
touch "$ROOT/G1CARD-DONE"
gl "G1CARD DONE"
