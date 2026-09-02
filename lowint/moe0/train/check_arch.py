"""Stage-1 architecture check: parameter totals against the prereg s.1 literal
arithmetic, and a short timing probe. CPU only. Pure ASCII."""

import os

os.environ["CUDA_VISIBLE_DEVICES"] = ""

import sys
import time

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bobmoe0 import (STAGE_ARCH, BobMoE0, init_weights, BitLinear, MoEFFN,
                     VOCAB_SIZE, ARM_CODE, MASTER_SEED)

torch.use_deterministic_algorithms(True)
torch.set_num_threads(int(os.environ.get("PROBE_THREADS", "8")))

cfg = STAGE_ARCH[1]
EXPECT = {"moe": 17118720, "dense": 5312000}
EXPECT_ACTIVE = {"moe": 5322240, "dense": 5312000}

for arm in ("moe", "dense"):
    torch.manual_seed(MASTER_SEED * 10 + ARM_CODE[arm])
    m = BobMoE0(cfg, arm)
    init_weights(m)
    total = sum(p.numel() for p in m.parameters())
    # active = total minus the 6 of 8 experts not used per token
    inactive = 0
    for mod in m.modules():
        if isinstance(mod, MoEFFN):
            per_expert = sum(p.numel() for p in mod.experts[0].parameters())
            inactive += per_expert * (mod.E - mod.k)
    active = total - inactive
    print("ARM=%s PARAM_TOTAL=%d EXPECT=%d MATCH=%s" %
          (arm, total, EXPECT[arm], total == EXPECT[arm]))
    print("ARM=%s PARAM_ACTIVE=%d EXPECT=%d MATCH=%s" %
          (arm, active, EXPECT_ACTIVE[arm], active == EXPECT_ACTIVE[arm]))

    x = torch.randint(0, 256, (32, cfg["ctx"]))
    y = torch.randint(0, 256, (32, cfg["ctx"]))
    t0 = time.time()
    for _ in range(3):
        logits, aux = m(x)
        loss = torch.nn.functional.cross_entropy(
            logits.reshape(-1, VOCAB_SIZE), y.reshape(-1))
        if aux is not None:
            loss = loss + 0.01 * aux
        loss.backward()
    print("ARM=%s three_fwdbwd_s=%.3f per_step_s=%.3f" %
          (arm, time.time() - t0, (time.time() - t0) / 3))
print("ACTIVE_DIFF=%d" % (EXPECT_ACTIVE["moe"] - EXPECT_ACTIVE["dense"]))
