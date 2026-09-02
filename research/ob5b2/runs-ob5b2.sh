#!/bin/sh
# OB-5b P05 (C8-S8-2) limb (b): the two-arm live decode-shape run.
#
# ARM A is the CONTROL at the shape every receipt in this house was
# measured at (-ub 1024). ARM B is the same run at the product's own
# shape (-ub 1). Same engine, same model, same corpus, same resident
# sets, same seed, same thread count, one chunk each. The ONLY
# difference between the two command lines is the value of -ub, so any
# difference in the identity artifact, the route log or the counters is
# attributable to the micro-batch shape and to nothing else.
#
# Each arm takes and releases the runlock on its own so the heavy C4-S1
# sibling can interleave.
SETS=/mnt/f/f32/openbob-wt/research-2/research/ob1/RESIDENT-SETS.json
MODEL=/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf
MAN=/mnt/f/f32/openbob-wt/research-2/research/ob1/EXPERT-MANIFEST-20B.sha256
PROSE=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
LR=/mnt/f/f32/stage/research/ob5b2/sh/locked-run-ob5b2.sh
LOGS=/mnt/f/f32/stage/research/ob5b2/logs
mkdir -p $LOGS

echo "########## OB5B2 LIMB (b): THE LIVE DECODE-SHAPE RUN ##########"
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "engine:"
sha256sum /root/ob1b/llama.cpp/build/bin/llama-perplexity /root/ob1b/llama.cpp/build/bin/libllama.so.0
echo "corpus:"
sha256sum $PROSE
echo "resident sets:"
sha256sum $SETS
echo "model:"
ls -la $MODEL
echo

for R in \
  "armA-u1024-k16-prose $PROSE 16 $SETS $MODEL $MAN 1 8 1024" \
  "armB-u1-k16-prose    $PROSE 16 $SETS $MODEL $MAN 1 8 1" \
; do
  set -- $R
  NAME=$1
  echo "########## $NAME  $(date -u +%Y-%m-%dT%H:%M:%SZ) ##########"
  sh $LR "$@" > $LOGS/$NAME.log 2>&1
  RC=$?
  echo "=== $NAME rc=$RC ==="
  grep -E "^### LOCK|^exit_rc|^wallclock_s|Maximum resident set size|^lease_events=|^lease_bytes_read=|^peak_concurrent|^route_calls=|^\[1\]" $LOGS/$NAME.log
done
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
