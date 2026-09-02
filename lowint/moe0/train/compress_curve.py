"""
BOB-MOE-0 stage-1 COMPRESSIBILITY CURVE instrument.

Prereg s.2 G3, COEQUAL MEASUREMENT (the entropy-floor lesson binds both arms):
at every preregistered checkpoint, BOTH arms bank a compressibility curve -
per-tensor-class and pooled order-0 entropy in bits/trit of the absmean-quantized
weights, plus trit counts (c_neg, c_zero, c_pos).

Reads checkpoints only. Deterministic function of the checkpoint bytes, so a
byte-identical checkpoint pair yields a byte-identical CSV.

CPU ONLY. Pure ASCII.
"""

import os

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.setdefault("PYTHONHASHSEED", "0")

import argparse
import math

import torch
from safetensors.torch import load_file

QUANT_EPS = 1e-5

# Tensors that stay FLOAT per prereg s.1 (norms, embeddings, router) and are
# therefore NOT part of the ternary class.
FLOAT_SUFFIXES = ("embed.weight", "nf.weight", ".n1.weight", ".n2.weight",
                  ".router.weight")


def is_ternary(key):
    for s in FLOAT_SUFFIXES:
        if key.endswith(s) or key == s:
            return False
    return key.endswith(".weight")


def tensor_class(key):
    """attn.wq/wk/wv/wo and ffn.gate/up/down. MoE experts pool into the same
    ffn.* classes as the dense arm's FFN, so the classes are comparable across
    arms."""
    parts = key.split(".")
    leaf = parts[-2]
    if ".attn." in key:
        return "attn." + leaf
    if ".ffn." in key:
        return "ffn." + leaf
    return "other." + leaf


def trit_counts(w):
    """Absmean ternary law, prereg s.1: round(clip(W/gamma, -1, +1)),
    gamma = mean(|W|)."""
    w = w.to(torch.float32)
    gamma = w.abs().mean().clamp(min=QUANT_EPS)
    t = torch.clamp(w / gamma, -1.0, 1.0).round()
    n = t.numel()
    c_neg = int((t < -0.5).sum())
    c_pos = int((t > 0.5).sum())
    c_zero = n - c_neg - c_pos
    return c_neg, c_zero, c_pos


def entropy_bits(c_neg, c_zero, c_pos):
    n = c_neg + c_zero + c_pos
    h = 0.0
    for c in (c_neg, c_zero, c_pos):
        if c > 0:
            p = c / n
            h -= p * math.log2(p)
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--ckpt-dir", required=True)
    ap.add_argument("--steps", required=True, help="comma separated, e.g. 30,200,500")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    steps = [int(s) for s in args.steps.split(",")]
    rows = []
    for step in steps:
        path = os.path.join(args.ckpt_dir, "step%06d.safetensors" % step)
        sd = load_file(path)
        per_class = {}
        pooled = [0, 0, 0]
        for key in sorted(sd.keys()):
            if not is_ternary(key):
                continue
            cn, cz, cp = trit_counts(sd[key])
            cls = tensor_class(key)
            acc = per_class.setdefault(cls, [0, 0, 0])
            acc[0] += cn
            acc[1] += cz
            acc[2] += cp
            pooled[0] += cn
            pooled[1] += cz
            pooled[2] += cp
        for cls in sorted(per_class.keys()):
            cn, cz, cp = per_class[cls]
            rows.append((args.arm, step, "class", cls, cn, cz, cp))
        rows.append((args.arm, step, "pooled", "ALL", pooled[0], pooled[1], pooled[2]))

    with open(args.out, "w", newline="\n") as f:
        f.write("arm,step,scope,class,n_trits,c_neg,c_zero,c_pos,"
                "p_neg,p_zero,p_pos,bits_per_trit\n")
        for arm, step, scope, cls, cn, cz, cp in rows:
            n = cn + cz + cp
            h = entropy_bits(cn, cz, cp)
            f.write("%s,%d,%s,%s,%d,%d,%d,%d,%.9f,%.9f,%.9f,%.6f\n"
                    % (arm, step, scope, cls, n, cn, cz, cp,
                       cn / n, cz / n, cp / n, h))
    print("WROTE %s rows=%d" % (args.out, len(rows)))


if __name__ == "__main__":
    main()
