#!/bin/sh
STAGE=/mnt/f/f32/stage/research/rs053
RUNS="unit-aa-a unit-aa-b 20b-prose-a 20b-prose-b 20b-code-a 20b-code-b 120b-probe 120b-prose-a 120b-prose-b 120b-code-a 120b-code-b"
mkdir -p $STAGE/runs
echo "=== COPY ==="
for r in $RUNS; do
  mkdir -p $STAGE/runs/$r
  cp /root/rs053/runs/$r/route.log   $STAGE/runs/$r/route.log
  cp /root/rs053/runs/$r/stdout.txt  $STAGE/runs/$r/stdout.txt
  cp /root/rs053/runs/$r/stderr.txt  $STAGE/runs/$r/stderr.txt
  echo "copied $r"
done
echo "=== LOCAL vs STAGE DIGEST VERIFY ==="
for r in $RUNS; do
  A=$(sha256sum /root/rs053/runs/$r/route.log | cut -d' ' -f1)
  B=$(sha256sum $STAGE/runs/$r/route.log      | cut -d' ' -f1)
  if [ "$A" = "$B" ]; then V=MATCH; else V=MISMATCH; fi
  echo "$r local=$A stage=$B $V"
done
echo "=== BUILD LOG + PATCH TO STAGE ==="
cp /root/rs053/logs/build.log $STAGE/build.log
cd /root/rs053/llama.cpp && git diff > $STAGE/route-log.patch
sha256sum $STAGE/route-log.patch
wc -l $STAGE/route-log.patch
echo "=== SHA256SUMS ==="
cd $STAGE && find runs -name 'route.log' | sort | xargs sha256sum > $STAGE/SHA256SUMS-route-logs.txt
cat $STAGE/SHA256SUMS-route-logs.txt
echo "=== STAGE TREE ==="
du -sh $STAGE
ls -la $STAGE
