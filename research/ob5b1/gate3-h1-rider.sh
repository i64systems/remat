#!/bin/sh
# OB-5b S1 gate 3: THE H1 RIDER for the prepared install.
#
# The house install law: every install is versioned and its version report
# carries the H1 litmus, PROMPT AND RESPONSE VERBATIM, as a rider; SHA digests
# remain the deciding bytes. The litmus for an install is the capability it
# adds, so the rider for OB5B-S1-BRAIN-LEASE is one brain lease: our question
# in, the leased brain's answer out, and the counters that say which brain
# answered and what it cost.
set -e
W=/root/ob5b2/worker/w-000001
PKG="$1"
{
echo "OB5B-S1-BRAIN-LEASE v1   H1 RIDER"
echo ""
echo "Taken 2026-09-01 on f32-HYDE against the dev fabric binary and the live"
echo "exposure worker. The live serve (pid 654) was not involved and was not"
echo "touched. Nothing is quoted from memory: every line below is a file on disk"
echo "and its digest is printed beside it."
echo ""
echo "== THE PROMPT, VERBATIM =="
echo "----------------------------------------------------------------"
cat "$W/prompt.txt"
echo ""
echo "----------------------------------------------------------------"
echo "prompt bytes   $(stat -c %s $W/prompt.txt)"
echo "prompt sha256  $(sha256sum $W/prompt.txt | cut -d' ' -f1)"
echo ""
echo "== THE RESPONSE, VERBATIM =="
echo "----------------------------------------------------------------"
cat "$W/gen-text.txt"
echo ""
echo "----------------------------------------------------------------"
echo "answer bytes   $(stat -c %s $W/gen-text.txt)"
echo "answer sha256  $(sha256sum $W/gen-text.txt | cut -d' ' -f1)"
echo "turn identity  $(sha256sum $W/gen-ids.txt | cut -d' ' -f1)   (the generated token ids)"
echo ""
echo "IT IS A BASE MODEL CONTINUATION AND IT READS LIKE ONE. gpt-oss-120b is"
echo "being called with no chat frame: the brain lease proves the SEAM, not a"
echo "conversational frame for the called brain, and pretending otherwise would"
echo "be the kind of dressing-up our show-dont-tell law forbids. The frame for"
echo "the called brain is later work and is named as such."
echo ""
echo "== WHICH BRAIN ANSWERED, AND WHAT IT COST =="
grep -E '^(n_prompt_tokens|n_generated_tokens|ttft_seconds|decode_seconds|tok_s_decode|model_load_seconds|wall_seconds|VmHWM_bytes|alloc_commit_model_peak|alloc_commit_peak_single)' "$W/stdout.txt" || true
grep -E '^(resident_slices_loaded|resident_bytes_loaded|lease_events|lease_bytes_read|peak_concurrent_lease_bytes|route_calls|alloc_journal_sha256)=' "$W/ob1-stats.txt" || true
echo ""
echo "weights        sha256:582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d  63387346208 bytes"
echo "engine         sha256:$(sha256sum /root/ob5b1/llama.cpp/build/bin/ob5b1-gen | cut -d' ' -f1)"
echo "residency      K=8 of 128, sets sha256:8053f18a70030ad2ac2e59fe220a064ee26f35ad4eb3876bbb7c65f6e994530b"
echo "brain manifest sha256:$(sha256sum /root/ob5b2/devhome/.config/openbob/openbob.bm1 | cut -d' ' -f1)"
echo "worker log     sha256:$(sha256sum /root/ob5b2/worker/WORKER-LOG-1.jsonl | cut -d' ' -f1)"
echo "route log      sha256:$(sha256sum $W/route.log | cut -d' ' -f1)"
echo ""
echo "THE ARITHMETIC OF THE RIDER, SHOWN:"
python3 - <<'PY'
import re
st = dict(l.strip().split("=", 1) for l in open("/root/ob5b2/worker/w-000001/ob1-stats.txt") if "=" in l)
TRUNK = 2314020128
MODEL = 63387346208
r = int(st["resident_bytes_loaded"]); p = int(st["peak_concurrent_lease_bytes"])
acct = TRUNK + r + p
print("  ACCT      %d + %d + %d = %d bytes" % (TRUNK, r, p, acct))
print("  EXPOSURE  %d / %d = %.6f" % (MODEL, acct, MODEL / acct))
print("  peak concurrent is %.6f experts of 13253760 bytes" % (p / 13253760))
print("  leased    %s slices, %d bytes, every one sha256 verified against the"
      % (st["lease_events"], int(st["lease_bytes_read"])))
print("            27648 row expert manifest before the kernel saw it")
PY
echo ""
echo "== WHAT THE FABRIC SAID, VERBATIM, AROUND IT =="
echo "(from research/ob5b1/gate3-seam.sh, banked whole in SEAM-1.txt)"
echo "----------------------------------------------------------------"
sed -n '/LIMB 2: THE FIRST LEASE/,/END LIMB 2/p' /root/ob5b2/g3/SEAM-1.txt \
  | sed -n '/^this one needs the big brain/,/^nothing on this box changed\./p'
echo "----------------------------------------------------------------"
echo "and the wall that answered the second question while this one was running:"
echo "----------------------------------------------------------------"
sed -n '/LIMB 3: THE SECOND LEASE/,/END LIMB 3/p' /root/ob5b2/g3/SEAM-1.txt \
  | sed -n '/^refused: brain.busy/p'
echo "----------------------------------------------------------------"
} > "$PKG/H1-RIDER-1.txt"
echo "wrote $PKG/H1-RIDER-1.txt"
cat "$PKG/H1-RIDER-1.txt"
