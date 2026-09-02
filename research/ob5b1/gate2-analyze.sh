#!/bin/sh
# OB-5b S1 gate 2: run the decode-regime accounting over every banked run and
# emit one table plus the per-run detail. Analysis only: no model, no runlock,
# no serve contact.
set -e
S8=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json
SN=/root/ob5b2/g2/RESIDENT-SETS-120B-K8-16-24-32.json
A=/root/ob5b2/g2/gate2_decode_acct.py
R=/root/ob5b2/runs

row() {  # row <run> <K> <setsfile>
  [ -f "$R/$1/ob1-stats.txt" ] || { echo "### $1  (no run)"; return 0; }
  echo "=============================================================="
  echo "### $1   K=$2"
  nice -n 19 python3 "$A" "$R/$1" "$3" "$2"
}

echo "=== OB5B1 S1 GATE 2: THE DECODE-REGIME ACCOUNTING, EVERY RUN ==="
echo "utc $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""
row g2-k8-p1-a       8  "$S8"
row g2-k8-p1-b       8  "$S8"
row g2-k8-p2         8  "$S8"
row g2-k8-p3         8  "$S8"
row g2-k16-p1       16  "$SN"
row g2-k24-p1       24  "$SN"
row g2-k32-p1       32  "$SN"
row g2-k8-p4-narrow  8  "$S8"
row g2-k32-p2       32  "$SN"
row g2-k16-p2       16  "$SN"
row g2-k24-p2       24  "$SN"
row g2-k8-p2-ub32    8  "$S8"

echo ""
echo "=============================================================="
echo "=== THE PERF TABLE, LITERAL, ONE ROW PER RUN ==="
printf '%-18s %4s %5s %5s %14s %14s %14s %14s %14s %12s %12s\n' \
  run K n_pr n_gen ttft_s decode_s tok_s_decode tok_s_excl1 load_s VmHWM_bytes maxRSS_kb
for r in g2-k8-p1-a g2-k8-p1-b g2-k8-p2 g2-k8-p3 g2-k16-p1 g2-k24-p1 g2-k32-p1 \
         g2-k8-p4-narrow g2-k32-p2 g2-k16-p2 g2-k24-p2 g2-k8-p2-ub32; do
  S=$R/$r/stdout.txt
  [ -f "$S" ] || continue
  K=$(grep '^ob1_k=' $R/$r/ob1-stats.txt | cut -d= -f2)
  g() { grep -m1 "^$1  *" "$S" | awk '{print $2}'; }
  RSS=$(grep -m1 'Maximum resident set size' $R/$r/stderr.txt | awk '{print $6}')
  printf '%-18s %4s %5s %5s %14s %14s %14s %14s %14s %12s %12s\n' \
    "$r" "$K" "$(g n_prompt_tokens)" "$(g n_generated_tokens)" "$(g ttft_seconds)" \
    "$(g decode_seconds)" "$(g tok_s_decode)" "$(g tok_s_decode_excl_first)" \
    "$(g model_load_seconds)" "$(g VmHWM_bytes)" "$RSS"
done

echo ""
echo "=== THE COMMITTED STATE AND THE LEASE COUNTERS, ONE ROW PER RUN ==="
printf '%-18s %4s %14s %14s %14s %16s %16s %16s\n' \
  run K lease_events peak_conc resident_bytes commit_model_peak commit_peak_single lease_bytes_read
for r in g2-k8-p1-a g2-k8-p1-b g2-k8-p2 g2-k8-p3 g2-k16-p1 g2-k24-p1 g2-k32-p1 \
         g2-k8-p4-narrow g2-k32-p2 g2-k16-p2 g2-k24-p2 g2-k8-p2-ub32; do
  T=$R/$r/ob1-stats.txt
  [ -f "$T" ] || continue
  v() { grep -m1 "^$1=" "$T" | cut -d= -f2; }
  printf '%-18s %4s %14s %14s %14s %16s %16s %16s\n' \
    "$r" "$(v ob1_k)" "$(v lease_events)" "$(v peak_concurrent_lease_bytes)" \
    "$(v resident_bytes_loaded)" "$(v alloc_commit_model_peak)" \
    "$(v alloc_commit_peak_single)" "$(v lease_bytes_read)"
done

echo ""
echo "=== IDENTITY: THE A/A LIMB AND THE CROSS-RUN LIMBS ==="
for f in gen-ids.txt gen-text.txt prompt-ids.txt route.log alloc-journal.txt; do
  if [ -f "$R/g2-k8-p1-a/$f" ] && [ -f "$R/g2-k8-p1-b/$f" ]; then
    if cmp -s "$R/g2-k8-p1-a/$f" "$R/g2-k8-p1-b/$f"; then
      printf '  %-18s g2-k8-p1-a vs g2-k8-p1-b   IDENTICAL\n' "$f"
    else
      printf '  %-18s g2-k8-p1-a vs g2-k8-p1-b   *** DIFFER -- STOP SHIP ***\n' "$f"
    fi
  fi
done
echo ""
echo "  the 64 token run's first 32 ids against GATE 1's own 32:"
head -32 "$R/g2-k8-p1-a/gen-ids.txt" > /tmp/ob5b2-h32
if cmp -s /tmp/ob5b2-h32 /root/ob5b1/runs/gen-120b-k8-a/gen-ids.txt; then
  echo "    IDENTICAL. n_predict is not in the forward pass: the longer run"
  echo "    extends the shorter one byte for byte."
else
  echo "    *** DIFFER ***"
fi
echo ""
echo "  the schedule control, ubatch 64 against ubatch 32 on the SAME prompt:"
for f in gen-ids.txt gen-text.txt route.log; do
  if [ -f "$R/g2-k8-p2-ub32/$f" ]; then
    if cmp -s "$R/g2-k8-p2/$f" "$R/g2-k8-p2-ub32/$f"; then
      printf '    %-16s IDENTICAL\n' "$f"
    else
      printf '    %-16s DIFFER   %s\n' "$f" "$(cmp "$R/g2-k8-p2/$f" "$R/g2-k8-p2-ub32/$f" 2>&1 | head -1)"
    fi
  fi
done
echo ""
echo "=== ARTIFACT DIGESTS ==="
for r in g2-k8-p1-a g2-k8-p1-b g2-k8-p2 g2-k8-p3 g2-k16-p1 g2-k24-p1 g2-k32-p1 \
         g2-k8-p4-narrow g2-k32-p2 g2-k16-p2 g2-k24-p2 g2-k8-p2-ub32; do
  [ -f "$R/$r/gen-ids.txt" ] || continue
  sha256sum "$R/$r/gen-ids.txt" "$R/$r/gen-text.txt" "$R/$r/route.log" 2>/dev/null
done
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
