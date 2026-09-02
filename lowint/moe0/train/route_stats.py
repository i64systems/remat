"""
BOB-MOE-0 stage-1 G2 ROUTE STATS instrument.

Prereg s.2 G2, STAT DEFINITIONS FROZEN. Loads one MoE checkpoint, runs the
deterministic forward over the frozen eval split, records the per-layer
selection sets S(l,t) (k=2, tie-break to the LOWER expert index, identical to
the trainer's router), and banks:
  c_l(e)    counts
  P_half(l) (sum of the E/2 = 4 largest c_l) / (sum of all c_l)
  p_l(e,f)  unordered co-activation pair counts
  C_3(l)    (sum of the 3 largest p_l) / (sum of all 28)
  H_l       normalized entropy of c_l / sum(c_l), base ln(E)
  dead      experts under 1 percent of the layer's traffic
per layer and as layer means.

NO retraining. Reads a checkpoint and the pinned corpus only. Deterministic
function of (checkpoint bytes, corpus bytes, the frozen split arithmetic), so
two clean processes must produce BYTE-IDENTICAL artifacts.

CPU ONLY (stage-1 wall: the GPU is reserved for other work). Pure ASCII.

NAMED CHOICES (the prereg is silent on each; decided BEFORE any number was
seen, banked in lowint/moe0/evidence/leg2.txt so they can be overruled on review):
  D-L2-1 eval split = VALIDATION [90 percent, 95 percent). The prereg s.3
         falsifier reserves the TEST split for the stage-2 bpb metric; an
         instrument must not consume it.
  D-L2-2 windows tile the split from ITS OWN start byte: window j covers
         [val_start + j*ctx, val_start + (j+1)*ctx), j = 0 .. n_win-1,
         n_win = (val_end - val_start) // ctx. This is the same rule the
         trainer used for train (whose split starts at byte 0). Eval order
         sequential, unshuffled (prereg s.4).
  D-L2-3 ALL ctx forward positions of every window are counted, including
         position 0 (the BOS input position). A selection set exists at every
         forward position; dropping any would be an unnamed filter.
  D-L2-4 eval batch = 32, mirroring the training batch. Routing is per token
         and causal, so batching does not change a selection set; the size is
         fixed so both replay runs share it.
  D-L2-5 checkpoint = MoE run A, step 500. Run B is byte-identical (leg 1
         s.6), so the choice is immaterial; it is named anyway.

SELECTION CAPTURE: a forward hook on each MoEFFN.router captures the router
logits the model actually computed; the selection line is quoted verbatim from
bobmoe0.MoEFFN.forward. The capture is cross-checked against the model's own
returned aux value on every batch (the aux term is a function of the model's
own top_idx), so a wrong selection would show up as an aux mismatch.
"""

import os

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.setdefault("PYTHONHASHSEED", "0")

import argparse
import hashlib
import math

import numpy as np
import torch
from safetensors.torch import load_file

import bobmoe0
from bobmoe0 import BobMoE0, ByteCorpus, MoEFFN, STAGE_ARCH


def fmt(x):
    """Fixed float formatting, full precision, deterministic."""
    return "%.17e" % float(x)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, default=1, choices=[1, 2])
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--split", default="val", choices=["val", "test"])
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--out-prefix", required=True,
                    help="artifact prefix; writes <p>-stats.csv, <p>-experts.csv, <p>-pairs.csv")
    ap.add_argument("--progress", required=True, help="wall-clock log, not an artifact")
    args = ap.parse_args()

    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(args.threads)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass

    prog = open(args.progress, "w", buffering=1)

    def say(s):
        prog.write(s + "\n")
        print(s, flush=True)

    say("BOBMOE0 G2 ROUTE STATS stage=%d split=%s" % (args.stage, args.split))
    say("torch=%s threads=%d interop=%d" % (torch.__version__, torch.get_num_threads(),
                                            torch.get_num_interop_threads()))
    say("CUDA_VISIBLE_DEVICES=[%s] cuda.is_available=%s cuda.is_initialized=%s"
        % (os.environ.get("CUDA_VISIBLE_DEVICES", "UNSET"),
           torch.cuda.is_available(), torch.cuda.is_initialized()))

    cfg = STAGE_ARCH[args.stage]
    ctx = cfg["ctx"]
    E = cfg["n_experts"]
    k = cfg["top_k"]

    ckpt_sha = sha256_file(args.ckpt)
    say("CKPT_SHA256=%s" % ckpt_sha)

    model = BobMoE0(cfg, "moe")
    sd = load_file(args.ckpt)
    missing, unexpected = model.load_state_dict(sd, strict=True)
    say("LOAD missing=%d unexpected=%d tensors=%d" % (len(missing), len(unexpected), len(sd)))
    model.eval()

    corpus = ByteCorpus(args.data, ctx)
    say("CORPUS_SHA256=%s" % corpus.sha256)
    say("CORPUS_BYTES=%d TRAIN_END=%d VAL_END=%d" % (corpus.n, corpus.train_end, corpus.val_end))

    # D-L2-1 / D-L2-2: split region and its window tiling.
    if args.split == "val":
        s0, s1 = corpus.train_end, corpus.val_end
    else:
        s0, s1 = corpus.val_end, corpus.n
    n_win = (s1 - s0) // ctx
    say("SPLIT=%s START=%d END=%d BYTES=%d WINDOWS=%d POSITIONS=%d"
        % (args.split, s0, s1, s1 - s0, n_win, n_win * ctx))

    moe_layers = [m for m in model.modules() if isinstance(m, MoEFFN)]
    n_layers = len(moe_layers)
    say("MOE_LAYERS=%d E=%d k=%d EVAL_BATCH=%d" % (n_layers, E, k, args.batch))

    # --- selection capture: hook the router, keep the logits the model computed
    cap = [None] * n_layers
    for li, m in enumerate(moe_layers):
        def mk(i):
            def hook(mod, inp, out):
                cap[i] = out
            return hook
        m.router.register_forward_hook(mk(li))

    c_counts = [torch.zeros(E, dtype=torch.int64) for _ in range(n_layers)]
    pair_counts = [torch.zeros(E * E, dtype=torch.int64) for _ in range(n_layers)]
    aux_maxdiff = 0.0
    slot_check = 0

    arange_E = torch.arange(E).view(1, 1, E)
    n_batches = (n_win + args.batch - 1) // args.batch
    done = 0
    with torch.no_grad():
        for b in range(n_batches):
            lo = b * args.batch
            hi = min(n_win, lo + args.batch)
            w = np.stack([corpus.data[s0 + j * ctx: s0 + (j + 1) * ctx] for j in range(lo, hi)])
            tgt = torch.from_numpy(np.ascontiguousarray(w, dtype=np.int64))
            inp = torch.full_like(tgt, bobmoe0.BOS_ID)
            inp[:, 1:] = tgt[:, :-1]

            _, aux_model = model(inp)

            aux_recomp = []
            for li in range(n_layers):
                logits = cap[li]                                        # [N, E]
                N = logits.shape[0]
                # --- frozen selection, quoted from bobmoe0.MoEFFN.forward ---
                order = torch.argsort(-logits, dim=-1, stable=True)
                top_idx = order[:, :k].contiguous()                     # [N, k]
                # -----------------------------------------------------------
                c_counts[li] += torch.bincount(top_idx.reshape(-1), minlength=E)
                a = torch.minimum(top_idx[:, 0], top_idx[:, 1])
                z = torch.maximum(top_idx[:, 0], top_idx[:, 1])
                pair_counts[li] += torch.bincount(a * E + z, minlength=E * E)
                slot_check += int(N * k)

                # aux cross-check, quoted from bobmoe0.MoEFFN.forward
                probs = torch.softmax(logits, dim=-1)
                P = probs.mean(dim=0)
                onehot = (top_idx.unsqueeze(-1) == arange_E).any(dim=1)
                f = onehot.to(logits.dtype).sum(dim=0) / float(N * k)
                aux_recomp.append(E * (f * P).sum())
            d = abs(float(torch.stack(aux_recomp).mean()) - float(aux_model))
            if d > aux_maxdiff:
                aux_maxdiff = d

            done += hi - lo
            if b % 50 == 0 or b == n_batches - 1:
                say("batch=%d/%d windows=%d/%d" % (b + 1, n_batches, done, n_win))

    n_pos = n_win * ctx
    say("AUX_CROSSCHECK batches=%d max_abs_diff=%s" % (n_batches, repr(aux_maxdiff)))
    say("SLOT_CHECK slots=%d expected=%d ok=%s"
        % (slot_check, n_pos * k * n_layers, slot_check == n_pos * k * n_layers))

    # ---------------- FROZEN STAT DEFINITIONS (prereg s.2 G2) ----------------
    hdr = [
        "# BOBMOE0 G2 ROUTE STATS, prereg s.2 G2 definitions, frozen",
        "# arm=moe stage=%d ckpt_step=500" % args.stage,
        "# ckpt_sha256=%s" % ckpt_sha,
        "# corpus_sha256=%s" % corpus.sha256,
        "# corpus_bytes=%d train_end=%d val_end=%d" % (corpus.n, corpus.train_end, corpus.val_end),
        "# split=%s split_start=%d split_end=%d ctx=%d windows=%d positions=%d"
        % (args.split, s0, s1, ctx, n_win, n_pos),
        "# moe_layers=%d E=%d k=%d eval_batch=%d" % (n_layers, E, k, args.batch),
        "# all floats are %.17e; dead_count is emitted as a float in every row",
    ]

    rows_stats = []
    rows_exp = []
    rows_pair = []
    m_phalf = m_c3 = m_h = m_dead = 0.0
    lnE = math.log(E)
    for li in range(n_layers):
        c = [int(x) for x in c_counts[li].tolist()]
        tot = sum(c)
        cs = sorted(c, reverse=True)
        p_half = sum(cs[: E // 2]) / tot

        pm = pair_counts[li].tolist()
        pairs = []
        for e in range(E):
            for f_ in range(e + 1, E):
                pairs.append((e, f_, int(pm[e * E + f_])))
        ptot = sum(x[2] for x in pairs)
        ps = sorted((x[2] for x in pairs), reverse=True)
        c3 = sum(ps[:3]) / ptot

        h = 0.0
        for x in c:
            if x > 0:
                p = x / tot
                h -= p * math.log(p)
        h /= lnE

        dead = sum(1 for x in c if (x / tot) < 0.01)

        rows_stats.append("layer,%d,%d,%d,%d,%s,%s,%s,%s"
                          % (li, n_pos, tot, ptot, fmt(p_half), fmt(c3), fmt(h), fmt(dead)))
        for e in range(E):
            rows_exp.append("%d,%d,%d,%s" % (li, e, c[e], fmt(c[e] / tot)))
        for (e, f_, v) in pairs:
            rows_pair.append("%d,%d,%d,%d,%s" % (li, e, f_, v, fmt(v / ptot)))

        m_phalf += p_half
        m_c3 += c3
        m_h += h
        m_dead += dead

    nl = float(n_layers)
    rows_stats.append("mean,-1,%d,%d,%d,%s,%s,%s,%s"
                      % (n_pos, n_pos * k, n_pos, fmt(m_phalf / nl), fmt(m_c3 / nl),
                         fmt(m_h / nl), fmt(m_dead / nl)))

    def write(path, header_cols, rows):
        with open(path, "w", newline="\n") as fh:
            for line in hdr:
                fh.write(line + "\n")
            fh.write(header_cols + "\n")
            for r in rows:
                fh.write(r + "\n")

    p1 = args.out_prefix + "-stats.csv"
    p2 = args.out_prefix + "-experts.csv"
    p3 = args.out_prefix + "-pairs.csv"
    write(p1, "scope,layer,n_positions,slots,pair_total,P_half,C_3,H,dead_count", rows_stats)
    write(p2, "layer,expert,count,share", rows_exp)
    write(p3, "layer,e,f,count,share", rows_pair)
    for p in (p1, p2, p3):
        say("ARTIFACT %s sha256=%s bytes=%d" % (os.path.basename(p), sha256_file(p),
                                                os.path.getsize(p)))
    say("DONE")
    prog.close()


if __name__ == "__main__":
    main()
