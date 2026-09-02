"""
BOB-MOE-0 stage-1 G3 packer.

Takes ONE expert FFN weight tensor out of a trained MoE checkpoint, applies the
trainer's absmean ternary quantization law (prereg s.1, imported from
bobmoe0.weight_trits so the law is not restated), and writes the
packed-trit block: 4 trits per byte, symbol s = trit + 1, packed by the row
law
    P[r][c] = sum_i s(i*rows_packed + r, c) << 2i,  i = 0..3
so the block is exactly what the paired decoder repacks to.

TENSOR PICK, FROZEN BEFORE ANY NUMBER WAS SEEN (a fixed rank rule so
the spot-proof cannot be a flattering outlier):
  candidates = every key blocks.<l>.ffn.experts.<e>.<gate|up|down>.weight
               (5 layers x 8 experts x 3 matrices = 120 tensors)
  order      = order-0 entropy of the tensor's own trit histogram, bits/trit,
               ASCENDING; ties broken by bytewise key name
  pick       = rank 60 of 120, 1-based (the lower of the two middle
               ranks)

CPU ONLY. Pure ASCII.
"""

import os

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.setdefault("PYTHONHASHSEED", "0")

import argparse
import hashlib
import math
import re

import numpy as np
import torch
from safetensors.torch import load_file

from bobmoe0 import weight_trits

EXPERT_RE = re.compile(r"^blocks\.\d+\.ffn\.experts\.\d+\.(gate|up|down)\.weight$")
PICK_RANK = 60          # 1-based, of 120


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def h0_bits(c_neg, c_zero, c_pos):
    n = c_neg + c_zero + c_pos
    h = 0.0
    for c in (c_neg, c_zero, c_pos):
        if c > 0:
            p = c / n
            h -= p * math.log2(p)
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out-bin", required=True)
    ap.add_argument("--census", required=True)
    args = ap.parse_args()

    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(8)

    print("CUDA_VISIBLE_DEVICES=[%s] cuda.is_available=%s cuda.is_initialized=%s"
          % (os.environ.get("CUDA_VISIBLE_DEVICES", "UNSET"),
             torch.cuda.is_available(), torch.cuda.is_initialized()), flush=True)
    print("CKPT_SHA256=%s" % sha256_file(args.ckpt), flush=True)

    sd = load_file(args.ckpt)
    keys = sorted([k for k in sd.keys() if EXPERT_RE.match(k)])
    print("CANDIDATES=%d" % len(keys), flush=True)

    rows = []
    for k in keys:
        t = weight_trits(sd[k].to(torch.float32))
        a = t.to(torch.int8).numpy()
        c_neg = int((a == -1).sum())
        c_zero = int((a == 0).sum())
        c_pos = int((a == 1).sum())
        n = a.size
        if c_neg + c_zero + c_pos != n:
            raise SystemExit("REFUSE trit.range.%s" % k)
        rows.append((k, tuple(sd[k].shape), n, c_neg, c_zero, c_pos, h0_bits(c_neg, c_zero, c_pos)))

    order = sorted(range(len(rows)), key=lambda i: (rows[i][6], rows[i][0]))

    with open(args.census, "w", newline="\n") as fh:
        fh.write("# BOBMOE0 G3 expert-FFN trit census, MoE run A step 500\n")
        fh.write("# absmean law: bobmoe0.weight_trits, prereg s.1\n")
        fh.write("# pick rule frozen: rank %d of %d, H0 ascending, ties by bytewise name\n"
                 % (PICK_RANK, len(rows)))
        fh.write("rank,name,shape,n_trits,c_neg,c_zero,c_pos,H0_bits_per_trit\n")
        for r, i in enumerate(order):
            k, shp, n, cn, cz, cp, h = rows[i]
            fh.write("%d,%s,%dx%d,%d,%d,%d,%d,%.17e\n"
                     % (r + 1, k, shp[0], shp[1], n, cn, cz, cp, h))

    pick = rows[order[PICK_RANK - 1]]
    name, shape, n_trits, c_neg, c_zero, c_pos, h0 = pick
    print("PICK_RANK=%d of %d" % (PICK_RANK, len(rows)), flush=True)
    print("PICK_NAME=%s" % name, flush=True)
    print("PICK_SHAPE=%dx%d PICK_DTYPE=%s" % (shape[0], shape[1], sd[name].dtype), flush=True)
    print("PICK_TRITS n=%d c_neg=%d c_zero=%d c_pos=%d" % (n_trits, c_neg, c_zero, c_pos),
          flush=True)
    print("PICK_H0_bits_per_trit=%.17e" % h0, flush=True)
    print("PICK_NEIGHBOURS rank59=%s rank61=%s"
          % (rows[order[PICK_RANK - 2]][0], rows[order[PICK_RANK]][0]), flush=True)
    print("PICK_H0_MIN=%.17e PICK_H0_MAX=%.17e"
          % (rows[order[0]][6], rows[order[-1]][6]), flush=True)

    w = sd[name].to(torch.float32)
    gamma = float(w.abs().mean())
    print("PICK_GAMMA=%.17e" % gamma, flush=True)

    t = weight_trits(w).to(torch.int8).numpy()      # [out, in], values -1/0/+1
    syms = (t + 1).astype(np.uint8)                 # 0/1/2
    out_rows, cols = syms.shape
    if out_rows % 4 != 0:
        raise SystemExit("REFUSE pack.rows_not_div4.%s" % name)
    rows_packed = out_rows // 4

    # P[r][c] = sum_i s(i*rows_packed + r, c) << 2i
    P = np.zeros((rows_packed, cols), dtype=np.uint8)
    for i in range(4):
        P |= (syms[i * rows_packed:(i + 1) * rows_packed, :] << (2 * i)).astype(np.uint8)

    blk = P.tobytes(order="C")
    with open(args.out_bin, "wb") as fh:
        fh.write(blk)

    print("PACK rows_packed=%d cols=%d block_bytes=%d n_trits=%d"
          % (rows_packed, cols, len(blk), 4 * len(blk)), flush=True)
    print("BLOCK_SHA256=%s" % hashlib.sha256(blk).hexdigest(), flush=True)
    print("CENSUS_SHA256=%s" % sha256_file(args.census), flush=True)

    # self-check: unpack by the same row law and compare to the source symbols
    back = np.zeros_like(syms)
    for i in range(4):
        back[i * rows_packed:(i + 1) * rows_packed, :] = (P >> (2 * i)) & 3
    print("PACK_SELFCHECK unpack_equals_source=%s" % bool((back == syms).all()), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
