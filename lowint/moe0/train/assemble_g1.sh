#!/bin/bash
# BOB-MOE-0 stage-1 leg-1 G1 assembly: quote every checkpoint digest, diff the
# metrics logs, emit the verdict. Pure ASCII. Literal command output only.
CK=/mnt/f/f32/stage/lowint/moe0-ckpt
echo "===================== G1 BIT-REPRO: CHECKPOINT DIGESTS ====================="
for ARM in moe dense; do
  echo "--- ARM=$ARM ---"
  for S in 000030 000200 000500; do
    A=$(sha256sum "$CK/$ARM/A/step$S.safetensors" | cut -d' ' -f1)
    B=$(sha256sum "$CK/$ARM/B/step$S.safetensors" | cut -d' ' -f1)
    SZ=$(stat -c%s "$CK/$ARM/A/step$S.safetensors")
    if [ "$A" = "$B" ]; then M="IDENTICAL"; else M="*** MISMATCH ***"; fi
    echo "step$S bytes=$SZ"
    echo "  runA $A"
    echo "  runB $B"
    echo "  $M"
  done
  echo "--- ARM=$ARM cmp (byte compare, not just digest) ---"
  for S in 000030 000200 000500; do
    if cmp -s "$CK/$ARM/A/step$S.safetensors" "$CK/$ARM/B/step$S.safetensors"; then
      echo "  cmp step$S: byte-identical"
    else
      echo "  cmp step$S: DIFFER"
    fi
  done
  echo "--- ARM=$ARM metrics log diff (loss/gradnorm, every printed digit) ---"
  if diff -q "$CK/$ARM/A/metrics.tsv" "$CK/$ARM/B/metrics.tsv" > /dev/null; then
    echo "  diff metrics.tsv: NO DIFFERENCES (all 500 steps agree to every printed digit)"
  else
    echo "  diff metrics.tsv: DIFFERENCES FOUND"
    diff "$CK/$ARM/A/metrics.tsv" "$CK/$ARM/B/metrics.tsv" | head -20
  fi
  echo "  sha256 metrics.tsv runA: $(sha256sum "$CK/$ARM/A/metrics.tsv" | cut -d' ' -f1)"
  echo "  sha256 metrics.tsv runB: $(sha256sum "$CK/$ARM/B/metrics.tsv" | cut -d' ' -f1)"
done
echo "===================== WALL CLOCK ====================="
grep -h "^DONE" "$CK"/moe/A/progress.txt "$CK"/moe/B/progress.txt \
  "$CK"/dense/A/progress.txt "$CK"/dense/B/progress.txt
