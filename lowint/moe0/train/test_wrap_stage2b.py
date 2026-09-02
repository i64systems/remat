# BOBMOE0-STAGE2B unit rows U1-U6 (plan s.2): the epoch-wrap rule.
# Literal-output evidence tool; CPU only; no card, no corpus download.
# Run: python test_wrap_stage2b.py   (from lowint/moe0/train/)
import os
import sys
import tempfile

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bobmoe0  # noqa: E402

N = 175781            # stage-2 TRAIN_WINDOWS = 90000000 // 512
B = 64                # stage-2 frozen batch
LAST = 15259          # stage-2 frozen total steps
SEED = bobmoe0.STAGE2_SHARED_PERM_SEED

g = torch.Generator()
g.manual_seed(SEED)
perm = torch.randperm(N, generator=g)
print("perm_seed=%d N=%d B=%d last=%d PERM_HEAD=%s"
      % (SEED, N, B, LAST, perm[:8].tolist()))


def new_ids(step):
    return perm[torch.arange((step - 1) * B, step * B) % N].tolist()


def old_ids(step):
    return perm[(step - 1) * B: step * B].tolist()


# U1: steps 1..2746 - new rule == old slice, every step.
mismatch = 0
for s in range(1, 2747):
    if new_ids(s) != old_ids(s):
        mismatch += 1
print("U1 steps 1..2746 compared=2746 mismatches=%d -> %s"
      % (mismatch, "PASS" if mismatch == 0 else "FAIL"))

# U2: step 2747 = old 37 ids + perm[0:27], length 64.
n2747 = new_ids(2747)
expect2747 = old_ids(2747) + perm[0:27].tolist()
print("U2 step 2747 len=%d old_partial_len=%d wrap_head=%s -> %s"
      % (len(n2747), len(old_ids(2747)), n2747[37:40],
         "PASS" if (len(n2747) == 64 and n2747 == expect2747) else "FAIL"))

# U3: step 2748 (the crash step) = perm[27:91], length 64; old slice EMPTY.
n2748 = new_ids(2748)
print("U3 step 2748 old_len=%d new_len=%d equals_perm[27:91]=%s -> %s"
      % (len(old_ids(2748)), len(n2748), n2748 == perm[27:91].tolist(),
         "PASS" if (len(old_ids(2748)) == 0 and len(n2748) == 64
                    and n2748 == perm[27:91].tolist()) else "FAIL"))

# U4: every step 1..15259 yields exactly B ids (empty batch unreachable).
bad = sum(1 for s in range(1, LAST + 1) if len(new_ids(s)) != B)
print("U4 steps 1..%d wrong_length_count=%d -> %s"
      % (LAST, bad, "PASS" if bad == 0 else "FAIL"))

# U5: the empty-window case - ByteCorpus.batch([]) STILL raises loudly.
with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as fh:
    fh.write(bytes(range(256)) * 4096)  # 1 MiB synthetic corpus
    tmp = fh.name
corpus = bobmoe0.ByteCorpus(tmp, 512)
try:
    corpus.batch([])
    print("U5 batch([]) DID NOT RAISE -> FAIL")
except ValueError as e:
    print("U5 batch([]) raises ValueError('%s') -> PASS" % e)
os.unlink(tmp)

# U6: the budget identity.
draws = LAST * B
print("U6 draws=%d = 5*%d + %d; bytes=%d (prereg 500006912) -> %s"
      % (draws, N, draws - 5 * N, draws * 512,
         "PASS" if (draws == 976576 and draws == 5 * N + 97671
                    and draws * 512 == 500006912) else "FAIL"))

# Stage-1 no-wrap arithmetic (D4): 500 steps * 32 = 16000 draws, ctx 256.
n1 = 90000000 // 256
print("STAGE1 draws=16000 N_stage1=%d wraps=%s (16000 <= N: stage-1 bytes untouched)"
      % (n1, 16000 > n1))
