"""
BOB-MOE-0 two-arm trainer. One codebase, config-driven for arm and stage.
Law: lowint/moe0/BOBMOE0-PREREG-1.md (commit ea06508), amendment A1
(BOBMOE0-STAGE1.txt s.6), stage-2 addendum BOBMOE0-STAGE2-PLAN.txt s.1 (W1-W8).
Nothing here tunes the frozen recipe; every constant below is quoted from the
prereg.

DEVICE: --device defaults to cpu. On the cpu path CUDA_VISIBLE_DEVICES is forced
empty before torch is imported and no CUDA context is ever opened, exactly as in
stage 1. --device cuda (stage-2 card path, W1) leaves the card visible and pins
the full CUDA determinism envelope named in the stage-2 plan.

Pure ASCII.
"""

import os
import sys


def _peek_arg(argv, name, default):
    """Read one argument out of argv BEFORE torch is imported. Needed because the
    CUDA wall and CUBLAS_WORKSPACE_CONFIG must be decided pre-import."""
    flag = "--" + name
    for i, a in enumerate(argv):
        if a == flag and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return default


_DEVICE_PEEK = _peek_arg(sys.argv[1:], "device", "cpu")

# ---- WALL: cpu path opens no CUDA context, ever. Set before torch import. ----
if _DEVICE_PEEK != "cuda":
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
else:
    # stage-2 plan s.1 CUDA DETERMINISM ENVELOPE: cuBLAS workspace pinned before
    # any cuBLAS handle exists, or use_deterministic_algorithms(True) refuses.
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
os.environ.setdefault("PYTHONHASHSEED", "0")

import argparse
import hashlib
import json
import math
import subprocess
import time
from collections import OrderedDict
from contextlib import nullcontext

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.utils.checkpoint
from safetensors.torch import save_file, load_file

# ============================ FROZEN PREREG CONSTANTS ========================
# s.1 SEEDS, FROZEN
MASTER_SEED = 2827
ARM_CODE = {"moe": 1, "dense": 2}          # arm seed = master*10 + {1 MoE, 2 dense}
PERM_SEED_OFFSET = 100                      # data-order permutation seed = arm seed + 100

# W2 / AMENDMENT A1 (BOBMOE0-STAGE1.txt s.6, ruled before any stage-2 token):
# stage 2 uses ONE SHARED data-order permutation seed for BOTH arms; the arm
# seeds (28271 moe / 28272 dense) continue to govern INITIALIZATION ONLY.
# Stage 1 keeps the literal frozen rule (arm seed + 100) untouched.
STAGE2_SHARED_PERM_SEED = 28471

# s.1 architectures
STAGE_ARCH = {
    1: {  # stage-1 tiny twins (CPU staging)
        "d_model": 256, "n_layers": 5, "n_heads": 4,
        "n_experts": 8, "top_k": 2, "expert_d_ff": 512,
        "dense_d_ff": 1024, "ctx": 256,
    },
    2: {  # stage-2 funded arms (named here, not run in stage 1)
        "d_model": 512, "n_layers": 12, "n_heads": 8,
        "n_experts": 8, "top_k": 2, "expert_d_ff": 1024,
        "dense_d_ff": 2048, "ctx": 512,
    },
}

# s.1 frozen training recipe
STAGE_RECIPE = {
    1: {"peak_lr": 3e-3, "warmup": 100, "steps": 500, "batch": 32,
        "ckpt_steps": (30, 200, 500)},
    # W3: the falsifier reads the FINAL checkpoint, so the final step 15259 is
    # added to the stage-2 cadence. A wiring fix the prereg's own bar requires,
    # not a recipe change (the recipe's step count, lr, warmup, batch are as
    # frozen).
    2: {"peak_lr": 1.5e-3, "warmup": 375, "steps": 15259, "batch": 64,
        "ckpt_steps": tuple(range(1000, 15260, 1000)) + (15259,)},
}
ADAM_BETAS = (0.9, 0.95)
WEIGHT_DECAY = 0.1          # none on norms, embeddings, router
GRAD_CLIP = 1.0
COSINE_FLOOR = 0.10         # cosine schedule to 10 percent of peak
AUX_ALPHA = 0.01            # Switch form load-balance aux, frozen

# s.1 vocabulary: 256 bytes + BOS + EOS + PAD = 259, identity tokenizer
VOCAB_SIZE = 259
BOS_ID, EOS_ID, PAD_ID = 256, 257, 258

# s.4 split rule, frozen
SPLIT_TRAIN_END = 0.90
SPLIT_VAL_END = 0.95

RMS_EPS = 1e-6
QUANT_EPS = 1e-5
INIT_STD = 0.02   # implementation choice: prereg does not freeze the init
                  # distribution. Identical rule both arms; only the arm seed
                  # differs, per s.1 ("differ ONLY in architecture and arm seed's
                  # init").


# ============================ QUANTIZATION LAW (s.1) =========================
def weight_quant_ste(w):
    """BitNet b1.58 absmean ternary, prereg s.1 literal form:
       W_t = round(clip(W/gamma, -1, +1)), gamma = mean(|W|).
       Returned dequantized as W_t * gamma; straight-through estimator on
       backward."""
    gamma = w.abs().mean().clamp(min=QUANT_EPS)
    wt = torch.clamp(w / gamma, -1.0, 1.0).round()
    wq = wt * gamma
    return w + (wq - w).detach()


def weight_trits(w):
    """The trit stream itself (no STE, no scale) for the compressibility curve."""
    gamma = w.abs().mean().clamp(min=QUANT_EPS)
    return torch.clamp(w / gamma, -1.0, 1.0).round()


def act_quant_ste(x):
    """8-bit absmax per token (prereg s.1). Scale is per-row over the last dim."""
    scale = 127.0 / x.abs().amax(dim=-1, keepdim=True).clamp(min=QUANT_EPS)
    xq = torch.clamp((x * scale).round(), -128.0, 127.0) / scale
    return x + (xq - x).detach()


class BitLinear(nn.Module):
    """Ternary-weight, 8-bit-activation linear. No bias (the prereg parameter
    arithmetic carries no bias terms)."""

    def __init__(self, d_in, d_out):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(d_out, d_in))

    def forward(self, x):
        return F.linear(act_quant_ste(x), weight_quant_ste(self.weight))


class RMSNorm(nn.Module):
    """Float norm (BitNet class practice: norms stay float)."""

    def __init__(self, d):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(d))

    def forward(self, x):
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + RMS_EPS) * self.weight


# ============================== ARCHITECTURE (s.1) ===========================
def build_rope(ctx, head_dim):
    inv = 1.0 / (10000.0 ** (torch.arange(0, head_dim, 2, dtype=torch.float32) / head_dim))
    t = torch.arange(ctx, dtype=torch.float32)
    f = torch.outer(t, inv)
    return torch.cos(f), torch.sin(f)


def apply_rope(x, cos, sin):
    # x: [B, H, T, hd]
    x1, x2 = x[..., 0::2], x[..., 1::2]
    c = cos[None, None, :, :]
    s = sin[None, None, :, :]
    o1 = x1 * c - x2 * s
    o2 = x1 * s + x2 * c
    out = torch.empty_like(x)
    out[..., 0::2] = o1
    out[..., 1::2] = o2
    return out


class Attention(nn.Module):
    """All four projections ternary (prereg s.1)."""

    def __init__(self, d_model, n_heads):
        super().__init__()
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.wq = BitLinear(d_model, d_model)
        self.wk = BitLinear(d_model, d_model)
        self.wv = BitLinear(d_model, d_model)
        self.wo = BitLinear(d_model, d_model)

    def forward(self, x, cos, sin, mask):
        B, T, D = x.shape
        H, hd = self.n_heads, self.head_dim
        q = self.wq(x).view(B, T, H, hd).transpose(1, 2)
        k = self.wk(x).view(B, T, H, hd).transpose(1, 2)
        v = self.wv(x).view(B, T, H, hd).transpose(1, 2)
        q = apply_rope(q, cos, sin)
        k = apply_rope(k, cos, sin)
        att = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(hd)
        att = att.masked_fill(mask, float("-inf"))
        att = torch.softmax(att, dim=-1)
        y = torch.matmul(att, v).transpose(1, 2).reshape(B, T, D)
        return self.wo(y)


class SwiGLU(nn.Module):
    """3 ternary matrices: gate, up, down (prereg s.1)."""

    def __init__(self, d_model, d_ff):
        super().__init__()
        self.gate = BitLinear(d_model, d_ff)
        self.up = BitLinear(d_model, d_ff)
        self.down = BitLinear(d_ff, d_model)

    def forward(self, x):
        return self.down(F.silu(self.gate(x)) * self.up(x))


class MoEFFN(nn.Module):
    """Deterministic top-2 router, prereg s.1 ROUTER FORM, FROZEN.
    Tie-break: LOWER expert index, via a stable sort on (-logit, index).
    No noise, no jitter, no stochastic dispatch. Router stays float."""

    def __init__(self, d_model, d_ff, n_experts, top_k):
        super().__init__()
        self.E = n_experts
        self.k = top_k
        self.router = nn.Linear(d_model, n_experts, bias=False)
        self.experts = nn.ModuleList([SwiGLU(d_model, d_ff) for _ in range(n_experts)])

    def forward(self, x):
        B, T, D = x.shape
        xf = x.reshape(B * T, D)
        N = xf.shape[0]
        logits = self.router(xf)                                   # [N, E] float
        # stable ascending sort of -logits == descending by logit, ties to lower index
        order = torch.argsort(-logits, dim=-1, stable=True)
        top_idx = order[:, : self.k].contiguous()                   # [N, k]
        gates = torch.softmax(logits.gather(-1, top_idx), dim=-1)   # softmax over selected

        out = torch.zeros_like(xf)
        for e in range(self.E):                                     # fixed order
            m = top_idx.eq(e)
            if not bool(m.any()):
                continue
            pos, slot = m.nonzero(as_tuple=True)                    # row-major, deterministic
            y = self.experts[e](xf.index_select(0, pos))
            y = y * gates[pos, slot].unsqueeze(-1)
            out = out.index_add(0, pos, y)                          # pos unique per expert

        # Switch aux: L_aux = alpha * E * sum_e f_e * P_e (alpha applied by caller).
        # f_e = fraction of the N*k assignment slots landing on e (sum_e f_e = 1);
        # P_e = mean router probability for e over tokens.
        probs = torch.softmax(logits, dim=-1)
        P = probs.mean(dim=0)
        # W1: arange must be built on the tensors' own device (CPU-era code had
        # an implicit cpu literal here). Value-identical on the cpu path.
        ar = torch.arange(self.E, device=logits.device).view(1, 1, self.E)
        onehot = (top_idx.unsqueeze(-1) == ar).any(dim=1)
        f = onehot.to(logits.dtype).sum(dim=0) / float(N * self.k)
        aux = self.E * (f * P).sum()
        return out.reshape(B, T, D), aux


class Block(nn.Module):
    def __init__(self, cfg, arm):
        super().__init__()
        d = cfg["d_model"]
        self.n1 = RMSNorm(d)
        self.attn = Attention(d, cfg["n_heads"])
        self.n2 = RMSNorm(d)
        self.is_moe = arm == "moe"
        if self.is_moe:
            self.ffn = MoEFFN(d, cfg["expert_d_ff"], cfg["n_experts"], cfg["top_k"])
        else:
            self.ffn = SwiGLU(d, cfg["dense_d_ff"])

    def forward(self, x, cos, sin, mask):
        x = x + self.attn(self.n1(x), cos, sin, mask)
        if self.is_moe:
            h, aux = self.ffn(self.n2(x))
            return x + h, aux
        return x + self.ffn(self.n2(x)), None


def _blk_moe(b, x, cos, sin, mask):
    return b(x, cos, sin, mask)


def _blk_dense(b, x, cos, sin, mask):
    y, _ = b(x, cos, sin, mask)
    return y


class BobMoE0(nn.Module):
    def __init__(self, cfg, arm):
        super().__init__()
        d = cfg["d_model"]
        self.cfg = cfg
        self.arm = arm
        # Activation rematerialization switch (memory strategy only, arithmetic
        # unchanged: forward is recomputed deterministically, no RNG in forward).
        # Default OFF so stage-1 behavior is untouched.
        self.grad_ckpt = False
        self.embed = nn.Embedding(VOCAB_SIZE, d)          # float, TIED to the head
        self.blocks = nn.ModuleList([Block(cfg, arm) for _ in range(cfg["n_layers"])])
        self.nf = RMSNorm(d)
        cos, sin = build_rope(cfg["ctx"], d // cfg["n_heads"])
        self.register_buffer("rope_cos", cos, persistent=False)
        self.register_buffer("rope_sin", sin, persistent=False)
        mask = torch.triu(torch.ones(cfg["ctx"], cfg["ctx"], dtype=torch.bool), diagonal=1)
        self.register_buffer("causal", mask, persistent=False)

    def forward(self, idx):
        B, T = idx.shape
        x = self.embed(idx)
        cos, sin = self.rope_cos[:T], self.rope_sin[:T]
        mask = self.causal[:T, :T]
        auxes = []
        use_ck = self.grad_ckpt and torch.is_grad_enabled()
        for b in self.blocks:
            if use_ck:
                if b.is_moe:
                    x, aux = torch.utils.checkpoint.checkpoint(
                        _blk_moe, b, x, cos, sin, mask, use_reentrant=False)
                else:
                    x = torch.utils.checkpoint.checkpoint(
                        _blk_dense, b, x, cos, sin, mask, use_reentrant=False)
                    aux = None
            else:
                x, aux = b(x, cos, sin, mask)
            if aux is not None:
                auxes.append(aux)
        x = self.nf(x)
        logits = F.linear(x, self.embed.weight)           # tied head
        aux = torch.stack(auxes).mean() if auxes else None
        return logits, aux


def init_weights(model):
    """Identical rule both arms; only the arm seed differs."""
    for m in model.modules():
        if isinstance(m, BitLinear):
            nn.init.normal_(m.weight, mean=0.0, std=INIT_STD)
        elif isinstance(m, nn.Linear):                    # the float router
            nn.init.normal_(m.weight, mean=0.0, std=INIT_STD)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, mean=0.0, std=INIT_STD)


def param_counts(model):
    total = sum(p.numel() for p in model.parameters())
    return total


# ================================ DATA (s.4) =================================
class ByteCorpus:
    """enwik8 (or the named fallback), split [0,90%) train, [90,95%) val,
    [95,100%) test. Sequences are consecutive non-overlapping ctx-sized windows;
    training order is the seeded permutation. Input is [BOS] + w[:-1], target is
    w, so each window yields exactly ctx predicted bytes."""

    def __init__(self, path, ctx):
        with open(path, "rb") as fh:
            raw = fh.read()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.data = np.frombuffer(raw, dtype=np.uint8)
        self.n = self.data.shape[0]
        self.ctx = ctx
        self.train_end = int(self.n * SPLIT_TRAIN_END)
        self.val_end = int(self.n * SPLIT_VAL_END)
        self.n_train_windows = self.train_end // ctx

    def batch(self, window_ids):
        ctx = self.ctx
        w = np.stack([self.data[i * ctx:(i + 1) * ctx] for i in window_ids])
        tgt = torch.from_numpy(np.ascontiguousarray(w, dtype=np.int64))
        inp = torch.full_like(tgt, BOS_ID)
        inp[:, 1:] = tgt[:, :-1]
        return inp, tgt

    def span_windows(self, lo, hi):
        """Non-overlapping ctx windows fully inside [lo, hi), in file order.
        Returns the list of absolute byte offsets of each window start (W7)."""
        ctx = self.ctx
        n = (hi - lo) // ctx
        return [lo + i * ctx for i in range(n)]

    def batch_at(self, offsets):
        """Same BOS-shifted form as training, for absolute byte offsets."""
        ctx = self.ctx
        w = np.stack([self.data[o:o + ctx] for o in offsets])
        tgt = torch.from_numpy(np.ascontiguousarray(w, dtype=np.int64))
        inp = torch.full_like(tgt, BOS_ID)
        inp[:, 1:] = tgt[:, :-1]
        return inp, tgt


# ============================== SCHEDULE (s.1) ===============================
def lr_at(step, peak, warmup, total):
    """Linear warmup then cosine to COSINE_FLOOR * peak. step is 1-based."""
    if step <= warmup:
        return peak * step / warmup
    prog = (step - warmup) / max(1, total - warmup)
    cos = 0.5 * (1.0 + math.cos(math.pi * prog))
    return peak * (COSINE_FLOOR + (1.0 - COSINE_FLOOR) * cos)


def param_groups(model):
    """No weight decay on norms, embeddings, router (prereg s.1)."""
    decay, no_decay = [], []
    for name, p in model.named_parameters():
        if (".router." in name) or name.endswith("embed.weight") or (".n1." in name) \
                or (".n2." in name) or name.startswith("nf."):
            no_decay.append(p)
        else:
            decay.append(p)
    return [{"params": decay, "weight_decay": WEIGHT_DECAY},
            {"params": no_decay, "weight_decay": 0.0}], len(decay), len(no_decay)


# ============================ CHECKPOINT (deterministic) =====================
def save_ckpt(model, path):
    """Canonical order: keys sorted bytewise, contiguous float32 tensors, no
    metadata. Same state = same bytes. THE G1-COMPARED ARTIFACT: form unchanged
    from stage 1 (tensors are pulled to CPU before serialization so the bytes do
    not depend on the device the run used)."""
    sd = model.state_dict()
    out = OrderedDict()
    for k in sorted(sd.keys()):
        out[k] = sd[k].detach().to("cpu", torch.float32).contiguous().clone()
    save_file(out, path)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ============================ STAGE-2 WIRING HELPERS =========================
def sidecar_path(ckpt_path):
    """W4: resume sidecar sits beside its safetensors, never inside it."""
    return ckpt_path[:-len(".safetensors")] + ".resume.pt"


def save_sidecar(path, opt, step, device):
    """W4: optimizer state, torch CPU RNG state, CUDA RNG state, step index."""
    blob = {
        "step": step,
        "opt": opt.state_dict(),
        "cpu_rng": torch.get_rng_state(),
        "cuda_rng": (torch.cuda.get_rng_state_all()
                     if device.type == "cuda" else []),
    }
    torch.save(blob, path)


def load_sidecar(path, opt, device):
    blob = torch.load(path, map_location="cpu", weights_only=False)
    opt.load_state_dict(blob["opt"])
    torch.set_rng_state(blob["cpu_rng"].to(torch.uint8).cpu())
    if device.type == "cuda" and blob["cuda_rng"]:
        torch.cuda.set_rng_state_all([s.to(torch.uint8).cpu() for s in blob["cuda_rng"]])
    return int(blob["step"])


def gpu_temp_c():
    """W6: nvidia-smi query. PROGRESS LOG ONLY, never the deterministic metrics
    log. Returns an int, or None when unreadable."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=20)
        if out.returncode != 0:
            return None
        return int(out.stdout.strip().splitlines()[0].strip())
    except Exception:
        return None


def bank_digests(digest_log, paths):
    """W8: append 'sha256  filename' for every saved file of a checkpoint."""
    if not digest_log:
        return
    os.makedirs(os.path.dirname(digest_log), exist_ok=True)
    with open(digest_log, "a", buffering=1) as fh:
        for p in paths:
            fh.write("%s  %s\n" % (sha256_file(p), os.path.basename(p)))


def make_ce(device, say):
    """Cross-entropy under torch.use_deterministic_algorithms(True).

    On CPU the stage-1 call is used verbatim (F.cross_entropy) so stage-1 bytes
    are untouched. On CUDA the native kernel is PROBED once; if deterministic
    mode refuses it (nll_loss backward is the known candidate), it is replaced by
    the arithmetic-equivalent composite

        ce = -mean( log_softmax(logits, -1) gathered at the target class )

    which is the definition F.cross_entropy computes. Any substitution is
    reported by the returned name and NAMED in the leg receipt."""
    def native(logits, tgt):
        return F.cross_entropy(logits, tgt)

    def composite(logits, tgt):
        lp = torch.log_softmax(logits, dim=-1)
        return -lp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1).mean()

    if device.type != "cuda":
        return native, "native:F.cross_entropy"
    try:
        z = torch.randn(8, VOCAB_SIZE, device=device, requires_grad=True)
        t = torch.zeros(8, dtype=torch.long, device=device)
        native(z, t).backward()
        del z, t
        return native, "native:F.cross_entropy"
    except Exception as exc:
        say("CE_PROBE_FAILED %s: %s" % (type(exc).__name__, str(exc).splitlines()[0]))
        return composite, "SUBSTITUTED:log_softmax+gather+mean"


def eval_bpb(model, corpus, device, batch, out_path, ckpt_path, arm, stage, say):
    """W7: deterministic sequential forward over the FROZEN test split
    [95%, 100%) in non-overlapping ctx windows, BOS-shifted exactly as training.
    bpb = total_ce_nats / (n_bytes * ln 2). No training state is mutated.
    Runs in full fp32 (no autocast): the bpb is the science number and must not
    inherit the training compute dtype. NAMED as such in the artifact."""
    model.eval()
    offsets = corpus.span_windows(corpus.val_end, corpus.n)
    n_windows = len(offsets)
    n_bytes = n_windows * corpus.ctx
    total_nats = 0.0
    t0 = time.time()
    with torch.no_grad():
        for i in range(0, n_windows, batch):
            chunk = offsets[i:i + batch]
            inp, tgt = corpus.batch_at(chunk)
            inp = inp.to(device)
            tgt = tgt.to(device)
            logits, _ = model(inp)
            s = F.cross_entropy(logits.reshape(-1, VOCAB_SIZE), tgt.reshape(-1),
                                reduction="sum")
            total_nats += float(s)
            if (i // batch) % 25 == 0:
                say("EVAL batch_start=%d/%d elapsed_s=%.3f" % (i, n_windows, time.time() - t0))
    bpb = total_nats / (n_bytes * math.log(2.0))
    lines = [
        "BOBMOE0 EVAL-BPB (stage-2 plan W7)",
        "arm=%s stage=%d" % (arm, stage),
        "ckpt=%s" % os.path.basename(ckpt_path),
        "ckpt_sha256=%s" % sha256_file(ckpt_path),
        "corpus_sha256=%s" % corpus.sha256,
        "split=test[95pct,100pct) lo=%d hi=%d ctx=%d" % (corpus.val_end, corpus.n, corpus.ctx),
        "n_windows=%d n_bytes=%d" % (n_windows, n_bytes),
        "compute_dtype=fp32_no_autocast",
        "total_ce_nats=%.17e" % total_nats,
        "total_ce_nats_repr=%r" % total_nats,
        "bpb=%.17e" % bpb,
        "bpb_repr=%r" % bpb,
    ]
    with open(out_path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    say("EVAL_BPB=%.17e n_bytes=%d wall_clock_s=%.3f" % (bpb, n_bytes, time.time() - t0))
    return bpb


# ================================== TRAIN ====================================
PREEMPT_DEFAULT = "/mnt/f/f32/openbob-wt/low-int/lowint/moe0/PREEMPT"
TEMP_STOP_C = 90            # W6 frozen temp rule
TEMP_STOP_CONSECUTIVE = 3
PROGRESS_EVERY = 25


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["moe", "dense"])
    ap.add_argument("--stage", type=int, default=1, choices=[1, 2])
    ap.add_argument("--run", required=True, help="run label, e.g. A or B")
    ap.add_argument("--data", required=True)
    ap.add_argument("--ckpt-dir", default="")
    ap.add_argument("--log", default="", help="deterministic metrics log (diffed by G1)")
    ap.add_argument("--progress", required=True, help="wall-clock/progress log (not diffed)")
    ap.add_argument("--threads", type=int, default=8)
    # ---- stage-2 additions (BOBMOE0-STAGE2-PLAN.txt s.1) ----
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"],
                    help="W1; DEFAULT cpu, the stage-1 path")
    ap.add_argument("--resume", default="",
                    help="W4; path to a step*.safetensors to resume from")
    ap.add_argument("--stop-after-step", type=int, default=0,
                    help="W4; stop cleanly after this step. 0 = the full frozen "
                         "step count. The lr schedule ALWAYS uses the frozen "
                         "total, so lr at step s is unchanged by this flag.")
    ap.add_argument("--ckpt-steps", default="",
                    help="comma list overriding the frozen cadence. Used ONLY by "
                         "the G1-CARD prefix runs; the funded run leaves it empty.")
    ap.add_argument("--digest-log", default="",
                    help="W8; default <ckpt-dir>/CKPT-DIGESTS.txt")
    ap.add_argument("--preempt-file", default=PREEMPT_DEFAULT, help="W5")
    ap.add_argument("--no-autocast", action="store_true",
                    help="the ONE named dtype fallback: full fp32, no autocast")
    ap.add_argument("--grad-ckpt", action="store_true",
                    help="activation rematerialization (memory strategy; "
                         "arithmetic unchanged)")
    ap.add_argument("--eval-bpb", default="", help="W7; path to a checkpoint")
    ap.add_argument("--eval-out", default="", help="W7; artifact path")
    args = ap.parse_args()

    is_eval = bool(args.eval_bpb)
    if not is_eval:
        for need in ("ckpt_dir", "log"):
            if not getattr(args, need):
                ap.error("--%s is required for training" % need.replace("_", "-"))

    # ---- determinism envelope (prereg s.1; stage-2 plan s.1 for the card) ----
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(args.threads)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass   # already initialized in this process; harmless, count is 1 by env

    device = torch.device(args.device if args.device == "cpu" else "cuda:0")
    if device.type == "cuda":
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False

    cfg = STAGE_ARCH[args.stage]
    rec = STAGE_RECIPE[args.stage]
    arm_seed = MASTER_SEED * 10 + ARM_CODE[args.arm]
    # W2 / A1: stage 2 shares ONE data-order seed across arms; stage 1 unchanged.
    perm_seed = STAGE2_SHARED_PERM_SEED if args.stage == 2 else arm_seed + PERM_SEED_OFFSET

    torch.manual_seed(arm_seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(arm_seed)

    prog = open(args.progress, "w", buffering=1)

    def say(s):
        prog.write(s + "\n")
        print(s, flush=True)

    say("BOBMOE0 stage=%d arm=%s run=%s" % (args.stage, args.arm, args.run))
    say("torch=%s threads=%d interop=%d" % (torch.__version__, torch.get_num_threads(),
                                            torch.get_num_interop_threads()))
    say("CUDA_VISIBLE_DEVICES=[%s] cuda.is_available=%s cuda.is_initialized=%s"
        % (os.environ.get("CUDA_VISIBLE_DEVICES", "UNSET"),
           torch.cuda.is_available(), torch.cuda.is_initialized()))
    say("DEVICE=%s" % device)
    if device.type == "cuda":
        say("ENVELOPE cublas_workspace=[%s] pythonhashseed=[%s] omp=[%s] mkl=[%s]"
            % (os.environ.get("CUBLAS_WORKSPACE_CONFIG", "UNSET"),
               os.environ.get("PYTHONHASHSEED", "UNSET"),
               os.environ.get("OMP_NUM_THREADS", "UNSET"),
               os.environ.get("MKL_NUM_THREADS", "UNSET")))
        say("ENVELOPE cudnn.deterministic=%s cudnn.benchmark=%s matmul.tf32=%s cudnn.tf32=%s"
            % (torch.backends.cudnn.deterministic, torch.backends.cudnn.benchmark,
               torch.backends.cuda.matmul.allow_tf32, torch.backends.cudnn.allow_tf32))
        say("GPU_NAME=%s" % torch.cuda.get_device_name(0))
    say("arm_seed=%d perm_seed=%d master_seed=%d" % (arm_seed, perm_seed, MASTER_SEED))

    model = BobMoE0(cfg, args.arm)
    init_weights(model)
    model.grad_ckpt = bool(args.grad_ckpt)
    model.to(device)
    model.train()
    say("GRAD_CKPT=%s" % model.grad_ckpt)

    total_params = param_counts(model)
    say("PARAM_TOTAL=%d" % total_params)

    corpus = ByteCorpus(args.data, cfg["ctx"])
    say("CORPUS_BYTES=%d TRAIN_END=%d VAL_END=%d TRAIN_WINDOWS=%d"
        % (corpus.n, corpus.train_end, corpus.val_end, corpus.n_train_windows))
    say("CORPUS_SHA256=%s" % corpus.sha256)

    # ---- autocast policy (stage-2 plan s.1 COMPUTE DTYPE, RULED) ----
    use_autocast = (device.type == "cuda") and (not args.no_autocast)
    dtype_name = "bf16_autocast" if use_autocast else "fp32_no_autocast"
    say("COMPUTE_DTYPE=%s" % dtype_name)

    def amp():
        if use_autocast:
            return torch.autocast("cuda", dtype=torch.bfloat16)
        return nullcontext()

    # ---- W7 eval mode: no training state is mutated, no optimizer is built ----
    if is_eval:
        sd = load_file(args.eval_bpb)
        model.load_state_dict(sd, strict=True)
        model.to(device)
        out_path = args.eval_out or (args.eval_bpb + ".bpb.txt")
        eval_bpb(model, corpus, device, rec["batch"], out_path, args.eval_bpb,
                 args.arm, args.stage, say)
        say("EVAL_ARTIFACT=%s sha256=%s" % (out_path, sha256_file(out_path)))
        prog.close()
        return

    g = torch.Generator()
    g.manual_seed(perm_seed)
    perm = torch.randperm(corpus.n_train_windows, generator=g)
    say("PERM_HEAD=%s" % perm[:8].tolist())

    groups, nd, nnd = param_groups(model)
    say("PARAM_GROUPS decay_tensors=%d nodecay_tensors=%d" % (nd, nnd))
    opt = torch.optim.AdamW(groups, lr=rec["peak_lr"], betas=ADAM_BETAS, eps=1e-8)

    ce_fn, ce_impl = make_ce(device, say)
    say("CE_IMPL=%s" % ce_impl)

    B = rec["batch"]
    steps = rec["steps"]                       # FROZEN total; drives the lr schedule
    if args.ckpt_steps:
        ckpt_steps = set(int(s) for s in args.ckpt_steps.split(",") if s.strip())
        say("CKPT_STEPS_OVERRIDE=%s" % sorted(ckpt_steps))
    else:
        ckpt_steps = set(rec["ckpt_steps"])
    os.makedirs(args.ckpt_dir, exist_ok=True)
    digest_log = args.digest_log or os.path.join(args.ckpt_dir, "CKPT-DIGESTS.txt")

    # ---- W4 resume ----
    start = 1
    if args.resume:
        sd = load_file(args.resume)
        model.load_state_dict(sd, strict=True)
        model.to(device)
        sc = sidecar_path(args.resume)
        done = load_sidecar(sc, opt, device)
        start = done + 1
        say("RESUME from=%s sha256=%s" % (args.resume, sha256_file(args.resume)))
        say("RESUME sidecar=%s sha256=%s resumed_step=%d start_step=%d"
            % (sc, sha256_file(sc), done, start))

    last = steps if args.stop_after_step <= 0 else min(steps, args.stop_after_step)
    say("STEP_RANGE start=%d last=%d frozen_total=%d" % (start, last, steps))

    log = open(args.log, "w", buffering=1)
    log.write("# BOBMOE0 stage=%d arm=%s deterministic metrics log\n" % (args.stage, args.arm))
    log.write("# arm_seed=%d perm_seed=%d param_total=%d\n" % (arm_seed, perm_seed, total_params))
    if args.resume:
        log.write("# resumed_from=%s start_step=%d\n" % (os.path.basename(args.resume), start))
    log.write("step\tlr\tce\taux\tloss\tgradnorm\n")

    hot = 0
    stop_reason = "COMPLETE"

    def checkpoint_now(step, tag):
        p = os.path.join(args.ckpt_dir, "step%06d.safetensors" % step)
        if tag:
            p = os.path.join(args.ckpt_dir, "step%06d.%s.safetensors" % (step, tag))
        save_ckpt(model, p)
        sc = sidecar_path(p)
        save_sidecar(sc, opt, step, device)
        bank_digests(digest_log, [p, sc])
        say("CKPT step=%d path=%s elapsed_s=%.3f" % (step, p, time.time() - t0))
        say("CKPT_SHA256 step=%d %s  %s" % (step, sha256_file(p), os.path.basename(p)))
        return p

    t0 = time.time()
    for step in range(start, last + 1):
        # THE ONE WRAP RULE (BOBMOE0-STAGE2B-PLAN s.2): the single seeded
        # permutation cycles modularly, so every step draws exactly B windows
        # (the frozen equal-token budget) and the epoch boundary never yields
        # a partial or empty slice. Pure function of step; for s*B <= N this
        # reproduces the pre-fix slice byte-for-byte (unit rows U1-U6).
        ids = perm[torch.arange((step - 1) * B, step * B)
                   % corpus.n_train_windows].tolist()
        inp, tgt = corpus.batch(ids)
        if device.type != "cpu":
            inp = inp.to(device)
            tgt = tgt.to(device)

        lr = lr_at(step, rec["peak_lr"], rec["warmup"], steps)
        for pg in opt.param_groups:
            pg["lr"] = lr

        with amp():
            logits, aux = model(inp)
            ce = ce_fn(logits.reshape(-1, VOCAB_SIZE), tgt.reshape(-1))
            if aux is None:
                loss = ce
            else:
                loss = ce + AUX_ALPHA * aux
        aux_v = 0.0 if aux is None else float(aux.detach())

        opt.zero_grad(set_to_none=True)
        loss.backward()
        gn = torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
        opt.step()

        log.write("%d\t%.17e\t%.17e\t%.17e\t%.17e\t%.17e\n"
                  % (step, lr, float(ce.detach()), aux_v, float(loss.detach()), float(gn)))

        if step in ckpt_steps:
            checkpoint_now(step, "")
            # W5 PREEMPT: scheduled demos preempt. Boundary checkpoint is already saved.
            if os.path.exists(args.preempt_file):
                with open(os.path.join(args.ckpt_dir, "PREEMPTED"), "w") as fh:
                    fh.write("step=%d utc=%s\n" % (step, time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                                      time.gmtime())))
                say("PREEMPT seen at step=%d, checkpoint saved, exiting clean" % step)
                stop_reason = "PREEMPTED"
                break
        elif step % PROGRESS_EVERY == 0:
            # W6: temperature to the PROGRESS log only, never the metrics log.
            t = gpu_temp_c() if device.type == "cuda" else None
            say("step=%d ce=%.6f elapsed_s=%.3f gpu_temp_c=%s"
                % (step, float(ce.detach()), time.time() - t0,
                   "NA" if t is None else t))
            if t is not None and t >= TEMP_STOP_C:
                hot += 1
                say("TEMP_HIGH step=%d gpu_temp_c=%d consecutive=%d" % (step, t, hot))
                if hot >= TEMP_STOP_CONSECUTIVE:
                    say("TEMPSTOP step=%d gpu_temp_c=%d: off-cadence checkpoint" % (step, t))
                    checkpoint_now(step, "tempstop")
                    with open(os.path.join(args.ckpt_dir, "TEMPSTOP"), "w") as fh:
                        fh.write("step=%d gpu_temp_c=%d utc=%s\n"
                                 % (step, t, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
                    stop_reason = "TEMPSTOP"
                    break
            else:
                hot = 0

    log.close()
    if device.type == "cuda":
        say("CUDA_MAX_MEM_ALLOCATED_MIB=%.1f CUDA_MAX_MEM_RESERVED_MIB=%.1f"
            % (torch.cuda.max_memory_allocated() / 1048576.0,
               torch.cuda.max_memory_reserved() / 1048576.0))
    say("STOP_REASON=%s" % stop_reason)
    say("DONE steps=%d wall_clock_s=%.3f" % (last, time.time() - t0))
    prog.close()


if __name__ == "__main__":
    main()
