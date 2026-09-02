#!/bin/sh
# OB-5b S1 gate 3: build the DEV-SIDE fabric binary from the openbob source.
# Never installs. Never touches pid 654. Output tree is /root/ob5b2/fabric.
set -e
SRC="$1"       # source .rs to build
OUT="$2"       # output binary path
LOG="$3"
mkdir -p "$(dirname "$OUT")"
echo "=== gate3-fabric-build ==="            >  "$LOG"
echo "src      $SRC"                          >> "$LOG"
echo "src_sha  $(sha256sum "$SRC" | cut -d' ' -f1)" >> "$LOG"
echo "src_lines $(wc -l < "$SRC")"            >> "$LOG"
echo "rustc    $(/root/.cargo/bin/rustc --version)" >> "$LOG"
echo "started  $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG"
START=$(date +%s.%N)
set +e
nice -n 10 /root/.cargo/bin/rustc -O --edition 2021 "$SRC" -o "$OUT" >> "$LOG" 2>&1
RC=$?
set -e
END=$(date +%s.%N)
echo "rc       $RC"                           >> "$LOG"
echo "seconds  $(echo "$END - $START" | bc)"  >> "$LOG"
if [ "$RC" = "0" ]; then
  echo "out_sha  $(sha256sum "$OUT" | cut -d' ' -f1)" >> "$LOG"
  echo "out_size $(stat -c %s "$OUT")"        >> "$LOG"
fi
echo "ended    $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG"
exit $RC
