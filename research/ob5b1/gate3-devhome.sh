#!/bin/sh
# OB-5b S1 gate 3: stand up the DEV-SIDE fabric home.
#
# THE LIVE SERVE IS NEVER TOUCHED. openbob keeps every path it owns under $HOME
# (s8_home, s8_conf_dir, s8_data_dir), so a dev bob is HOME and nothing else:
# its register, its brain manifest, its counter and its journals all live under
# /root/ob5b2/devhome and the live ~/.config/openbob is neither read nor
# written by anything this leg runs. pid 654 is never signalled.
#
# WHAT THIS WRITES
#   $DEV/.config/openbob/openbob.c1    the dev permission register (OPENBOB-C-1)
#   $DEV/.config/openbob/openbob.bm1   the brain manifest (OPENBOB-BM-1, C4 5.2)
#   $DEV/worker.json                   the exposure worker's config
#
# THE REGISTER WIDENS NOTHING. An action with no matching rule is DENY by
# construction (c1_tier initialises the verdict to Deny), so a register that
# names ONE action and gives it ASK is the tightest register that can reach the
# brain at all. C4 section 9.3's line, applied early: an exam or a demonstration
# is a harder ask under the same law, never a looser law under a harder ask.
set -e
DEV=/root/ob5b2/devhome
CONF=$DEV/.config/openbob
GEN=/root/ob5b1/llama.cpp/build/bin/ob5b1-gen
SETS=/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json
MAN=/mnt/f/f32/openbob-wt/research-2/research/ob1b/EXPERT-MANIFEST-120B.sha256
MODEL=/root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf
ART=/root/openbob-l2s2/in/qwen3-4b-openbob-q1.bin
FABRIC=/root/ob5b2/fabric/openbob-br1
PORT=8907
WANT_RESIDENT="$1"     # "resident" to digest the 4 GB gatekeeper artifact too

mkdir -p "$CONF" "$DEV/.local/share/openbob" /root/ob5b2/worker

cat > "$CONF/openbob.c1" <<'EOF'
OPENBOB-C-1 version 1
# THE DEV REGISTER FOR THE OB-5b S1 GATE 3 SEAM DEMONSTRATION.
# One rule. Every other action of the closed OPENBOB-G-3 alphabet falls through
# to the tier's initial verdict, which is DENY, so this register can reach the
# brain and nothing else on this box.
rule bob.lease ASK
EOF

GEN_SHA=$(sha256sum "$GEN" | cut -d' ' -f1)
SETS_SHA=$(sha256sum "$SETS" | cut -d' ' -f1)
FAB_SHA=$(sha256sum "$FABRIC" | cut -d' ' -f1)
C1_SHA=$(sha256sum "$CONF/openbob.c1" | cut -d' ' -f1)
MODEL_BYTES=$(stat -c %s "$MODEL")

# MEASURED, from this leg's own gate 2 receipts at K=8, and named as measured
# constants wherever bob prints them. The receipt then prints what actually
# happened beside them, so a wrong estimate is a finding and not an excuse.
TTFT_MS_PER_PROMPT_BYTE=${TTFT_MS_PER_PROMPT_BYTE:-161}
MS_PER_TOKEN=${MS_PER_TOKEN:-3878}

{
  echo "openbob-bm-1 version 1"
  echo "# THE BRAIN MANIFEST (OPENBOB-BM-1, OB5-DESIGN-C4-1 section 5.2). One block"
  echo "# per brain this bob may call. THE DIGEST OF THIS FILE IS THE BRAIN SLOT OF"
  echo "# THE GOLDEN TRIPLE: a brain joining, leaving, changing weights, changing"
  echo "# engine binary or changing residency schedule all move it, and a bob whose"
  echo "# residency schedule moved IS a different bob for identity purposes."
  echo "---"
} > "$CONF/openbob.bm1"

if [ "$WANT_RESIDENT" = "resident" ]; then
  # The gatekeeper artifact is digested whole, once, and the digest is cached in
  # a file beside it so a re-run of this script does not read 4 GB again.
  if [ -s /root/ob5b2/g3/ART-SHA.txt ]; then
    ART_SHA=$(cut -d' ' -f1 < /root/ob5b2/g3/ART-SHA.txt)
  else
    echo "digesting the gatekeeper artifact whole ($(stat -c %s $ART) bytes)"
    nice -n 19 sha256sum "$ART" > /root/ob5b2/g3/ART-SHA.txt
    ART_SHA=$(cut -d' ' -f1 < /root/ob5b2/g3/ART-SHA.txt)
  fi
  {
    echo "brain          resident"
    echo "id             qwen3-4b-openbob-q1"
    echo "weights        sha256:$ART_SHA"
    echo "weights_bytes  $(stat -c %s $ART)"
    echo "frame          sha256:$C1_SHA"
    echo "engine         sha256:$FAB_SHA"
    echo "role           gatekeeper"
    echo "---"
  } >> "$CONF/openbob.bm1"
fi

{
  echo "brain          leased"
  echo "id             gpt-oss-120b-mxfp4"
  echo "weights        sha256:582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d"
  echo "weights_bytes  $MODEL_BYTES"
  echo "frame          sha256:$C1_SHA"
  echo "engine         sha256:$GEN_SHA"
  echo "residency      K=8-of-128"
  echo "residency_sets sha256:$SETS_SHA"
  echo "endpoint       127.0.0.1:$PORT"
  echo "role           called"
  echo "ttft_ms_per_prompt_byte $TTFT_MS_PER_PROMPT_BYTE"
  echo "ms_per_token   $MS_PER_TOKEN"
  echo "---"
} >> "$CONF/openbob.bm1"

# THE PATHS CONF. openbob keeps its budgets here beside the artifact paths, and
# l1_budget_lessee reads it, so a brain lease needs it even though this leg
# loads no gatekeeper model. Nothing in this file enters the hash chain; the two
# files that do are openbob.c1 and the brain manifest.
cat > "$CONF/openbob.conf" <<EOF
OPENBOB-CONF version 1
# THE DEV HOME FOR THE OB-5b S1 GATE 3 SEAM DEMONSTRATION.
# Written by research/ob5b1/gate3-devhome.sh. The live serve's conf dir is
# neither read nor written by this leg.
ucd = /root/openbob-l4s1/reg/ucd.obu1
tok = /root/openbob-l4s1/in/tokenizer.json
vocab = /root/openbob-l4s1/in/vocab.json
merges = /root/openbob-l4s1/in/merges.txt
config = /root/openbob-l4s1/in/config.json
art = $ART
tables = /root/openbob-l4s1/in/tables
mconfig = /root/openbob-l4s1/in/config.json
model_sha = ${ART_SHA:-0000000000000000000000000000000000000000000000000000000000000000}
threads = 8
tmax = 6
lease.max_new = 32
lease.seconds = 1800
lease.roles.brain = reasoner
EOF

cat > "$DEV/worker.json" <<EOF
{
  "bind": "127.0.0.1",
  "port": $PORT,
  "model": "$MODEL",
  "sets": "$SETS",
  "manifest": "$MAN",
  "gen_bin": "$GEN",
  "libdir": "/root/ob5b1/llama.cpp/build/bin",
  "runlock": "/mnt/f/f32/stage/research/runlock",
  "work": "/root/ob5b2/worker",
  "worker_log": "/root/ob5b2/worker/WORKER-LOG-1.jsonl",
  "k": 8,
  "n_ctx": 512,
  "ubatch": 64,
  "threads": 8,
  "guards": [654, 489],
  "lock_wait_s": 3600,
  "bm1_id": "gpt-oss-120b-mxfp4",
  "bm1_weights_sha": "582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d",
  "bm1_weights_bytes": $MODEL_BYTES,
  "bm1_engine_sha": "$GEN_SHA",
  "bm1_residency": "K=8-of-128",
  "bm1_residency_sha": "$SETS_SHA"
}
EOF

echo "=== the dev home ==="
echo "HOME            $DEV"
echo "register        $CONF/openbob.c1  $C1_SHA"
echo "paths conf      $CONF/openbob.conf"
echo "brain manifest  $CONF/openbob.bm1 $(sha256sum $CONF/openbob.bm1 | cut -d' ' -f1)"
echo "worker config   $DEV/worker.json"
echo "fabric binary   $FABRIC  $FAB_SHA"
echo "gen binary      $GEN  $GEN_SHA"
echo ""
echo "--- openbob.c1, verbatim ---"
cat "$CONF/openbob.c1"
echo "--- openbob.bm1, verbatim ---"
cat "$CONF/openbob.bm1"
echo ""
echo "--- the live conf dir was neither read nor written; it is not even named above ---"
