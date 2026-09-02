#!/bin/bash
# BOB-MOE-0 G1-CARD verdict assembly (BOBMOE0-STAGE2-PLAN.txt s.2).
# Reads only; decides nothing it does not quote. Three limbs per arm:
#   (i)   step 100 and step 1000 safetensors byte-identical runA vs runB
#   (ii)  step 1100 safetensors byte-identical runA straight vs runB resumed
#   (iii) deterministic metrics data lines byte-identical over the shared steps
# Metrics COMPARE METHOD, stated: only DATA lines (lines beginning with a digit)
# are compared. The '#' provenance lines and the column-header line are
# metadata, and the resumed process writes one extra '# resumed_from=' line by
# design, so comparing whole files would compare bookkeeping, not metrics.
# Pure ASCII.
set -u
ROOT=/mnt/f/f32/stage/lowint/moe0-ckpt/stage2/g1card
FAILS=0

hash_cmp() {
  local label="$1" f1="$2" f2="$3"
  echo "--- $label"
  if [ ! -f "$f1" ] || [ ! -f "$f2" ]; then
    echo "MISSING: $f1 or $f2"; FAILS=$((FAILS+1)); return
  fi
  ls -l "$f1" "$f2" | awk '{print $5"  "$9}'
  sha256sum "$f1" "$f2"
  if cmp "$f1" "$f2"; then
    echo "CMP IDENTICAL"
  else
    echo "CMP DIFFERS"; FAILS=$((FAILS+1))
  fi
}

ARMS="${*:-moe dense}"
echo "ARMS CHECKED: $ARMS"
for arm in $ARMS; do
  A=$ROOT/$arm/A
  B=$ROOT/$arm/B
  R=$ROOT/$arm/Bresume
  echo "==================== ARM $arm ===================="

  echo "=== limb (i): runA vs runB at steps 100 and 1000 ==="
  hash_cmp "$arm step 100 A vs B"  "$A/step000100.safetensors" "$B/step000100.safetensors"
  hash_cmp "$arm step 1000 A vs B" "$A/step001000.safetensors" "$B/step001000.safetensors"

  echo "=== limb (ii): runA straight vs runB resumed at step 1100 ==="
  hash_cmp "$arm step 1100 A vs Bresume" "$A/step001100.safetensors" "$R/step001100.safetensors"

  echo "=== limb (iii): deterministic metrics data lines ==="
  grep -E '^[0-9]' "$A/metrics.tsv" > "$ROOT/$arm.A.data"
  cat <(grep -E '^[0-9]' "$B/metrics.tsv") <(grep -E '^[0-9]' "$R/metrics.tsv") > "$ROOT/$arm.BR.data"
  echo "line counts: A=$(wc -l < "$ROOT/$arm.A.data")  B+Bresume=$(wc -l < "$ROOT/$arm.BR.data")"
  echo "first step A=$(head -1 "$ROOT/$arm.A.data" | cut -f1)  last step A=$(tail -1 "$ROOT/$arm.A.data" | cut -f1)"
  echo "B last step=$(grep -E '^[0-9]' "$B/metrics.tsv" | tail -1 | cut -f1)  Bresume first step=$(grep -E '^[0-9]' "$R/metrics.tsv" | head -1 | cut -f1)"
  sha256sum "$ROOT/$arm.A.data" "$ROOT/$arm.BR.data"
  if cmp "$ROOT/$arm.A.data" "$ROOT/$arm.BR.data"; then
    echo "METRICS IDENTICAL over steps 1..1100"
  else
    echo "METRICS DIFFER: first divergent line follows"
    diff "$ROOT/$arm.A.data" "$ROOT/$arm.BR.data" | head -6
    FAILS=$((FAILS+1))
  fi

  echo "=== sidecars present (W4) ==="
  ls -l "$B/step001000.resume.pt" 2>&1 | awk '{print $5"  "$9}'

  echo "=== W8 digest log ==="
  cat "$ROOT/$arm/CKPT-DIGESTS.txt"

  echo "=== temperatures (W6, progress logs only) ==="
  for d in A B Bresume; do
    echo "$arm/$d max/min sampled:"
    grep -o 'gpu_temp_c=[0-9]*' "$ROOT/$arm/$d/progress.txt" | cut -d= -f2 | sort -n | \
      awk 'NR==1{mn=$1} {mx=$1} END{print "  min="mn" max="mx" samples="NR}'
    grep -m1 'gpu_temp_c=' "$ROOT/$arm/$d/progress.txt"
  done

  echo "=== wall clocks and stop reasons ==="
  for d in A B Bresume; do
    echo -n "$arm/$d: "; grep -E '^(DONE|STOP_REASON|CUDA_MAX_MEM)' "$ROOT/$arm/$d/progress.txt" | tr '\n' ' '; echo
  done
done

echo "==================== TOTAL FAILED LIMB CHECKS: $FAILS ===================="
if [ "$FAILS" -eq 0 ]; then
  echo "G1-CARD VERDICT: PASS for arms [$ARMS]"
else
  echo "G1-CARD VERDICT: REFUSAL for arms [$ARMS]"
fi
