# BOBMOE0-PREREG-1: THE STAGED 2-ARM, PREREGISTERED BEFORE ANY BUILD

Lane: low-int (funded ternary lane). Lead-authored, BOB-MOE-0 stage 1.
Branch low-int, worktree F:\f32\openbob-wt\low-int, venue hyde, on-machine.
Pure ASCII, no em dashes. Committed BEFORE any builder runs; nothing below
this line is renegotiated mid-run. Deviations are named or they are refusals.

Substrate at prereg time: HEAD b8e3860af25e2e82a1124152575aacf752db08be
(the LI-S12 receipt commit), ancestor of origin/master; LI-S12-PRIMITIVE.txt
13514 bytes; lowint/MANIFEST.sha256 10/10 OK against the pinned stage;
git status --porcelain: "?? .scratch-s11/" only (untracked prior-session
scratch, touches no lane file, ruled benign).

## 0. THE QUESTION (the falsifier, stated first)

Does a NATIVELY-TRAINED ternary MoE beat or match a natively-trained
ternary dense of the same ACTIVE parameter count on the house
bit-reproducible harness, and does it develop the locality structure
(expert popularity skew and co-activation skew) that the called-never-loaded
thesis (N4/A1) needs? Nobody in the field has trained a native ternary MoE
at any real scale (SYNTHESIS-1 s.3: only ternarized pretrained MoEs exist);
even the tiny version is ground truth nobody holds.

Stage 1 (THIS STAGE) is CPU STAGING ONLY: the card belongs to RS050
tonight. Stage 1 proves the machinery (G1 bit-repro, G2 instruments,
G3 spot-proof) on tiny twins. Stage 2 runs the funded arms on the 3090
in quiet windows and answers the question. No quality claim is made at
stage-1 scale; tiny-twin loss curves are banked as measured staging facts
only.

## 1. THE TWO ARMS, EXACT

Both arms: decoder-only transformer, BitNet b1.58-class ternary QAT.
Latent float master weights; forward quantizes weights per-tensor by the
absmean law W_t = round(clip(W/gamma, -1, +1)), gamma = mean(|W|), and
activations 8-bit absmax per token (BitNet b1.58 forward, the class the
pinned 2B reference uses). Straight-through estimator on backward.
RMSNorm, SwiGLU FFN (3 matrices: gate, up, down), rotary positions,
TIED embedding/output head, byte-level vocabulary of 259 symbols
(256 bytes + BOS + EOS + PAD): no tokenizer pin, no merge tables, the
identity tokenizer is its own law. Norm weights, embeddings, and router
stay float (BitNet class practice); all four attention projections and
all FFN matrices are ternary.

ROUTER FORM, FROZEN: linear router d_model x E per MoE layer, top-k=2
selection, DETERMINISTIC: no noise, no jitter, no stochastic dispatch.
TIE-BREAK NAMED: ties in router logits resolve to the LOWER expert index
(stable sort by (-logit, index)). Softmax over the selected k logits
weights the expert outputs. During QAT training the router computes in
float but deterministically (proven by G1, which would catch any
nondeterminism byte-for-byte); the exact-integer routing law for the
trained artifact is stage-3 work under the LI-S2 pattern and is not
claimed here. Load-balance auxiliary loss, Switch form
L_aux = alpha * E * sum_e f_e * P_e, alpha = 0.01, frozen. Stated
plainly: the aux loss pushes TOWARD uniform routing, so any popularity
skew G2 measures is skew that SURVIVED load balancing - the honest form
of the signal.

### Stage-2 arms (the funded run, 3090, quiet windows)

MoE arm:   d_model 512, layers 12, heads 8 (head_dim 64), E=8 experts
           per layer, k=2 active, expert d_ff 1024, ctx 512.
Dense arm: d_model 512, layers 12, heads 8, d_ff 2048, ctx 512.

MATCHING ARITHMETIC, LITERAL (per layer):
  attention (q,k,v,o):       4 * 512 * 512              =  1,048,576
  one expert (SwiGLU):       3 * 512 * 1024             =  1,572,864
  MoE FFN total:             8 * 1,572,864              = 12,582,912
  MoE FFN active (k=2):      2 * 1,572,864              =  3,145,728
  dense FFN:                 3 * 512 * 2048             =  3,145,728   EQUAL
  router:                    512 * 8                    =      4,096
  norms (2 x RMSNorm):       2 * 512                    =      1,024
Totals (embed 259*512 = 132,608 tied, final norm 512):
  MoE total:    12 * 13,636,608 + 133,120 = 163,772,416   (~163.8M, in the
                150-250M window)
  MoE active:   12 *  4,199,424 + 133,120 =  50,526,208
  Dense total = dense active:
                12 *  4,195,328 + 133,120 =  50,477,056
  ACTIVE DIFFERENCE = 49,152 = the 12 routers exactly = 0.0974 percent of
  the dense arm, in the MoE's favor. RULED: the router is the price of
  routing and belongs to the MoE arm; it is counted, reported, and not
  equalized away. It cannot carry a 0.03 bits/byte verdict.

### Stage-1 tiny twins (CPU staging, THIS stage)

MoE twin:   d_model 256, layers 5, heads 4, E=8, k=2, expert d_ff 512,
            ctx 256.
Dense twin: d_model 256, layers 5, heads 4, d_ff 1024, ctx 256.
Arithmetic, literal (per layer): attn 262,144; expert 393,216 (x8 =
3,145,728, active 786,432); dense FFN 786,432 EQUAL; router 2,048;
norms 512. Totals (embed 66,304, final norm 256):
  MoE twin total  17,118,720; MoE twin active 5,322,240;
  dense twin total = active 5,312,000; active diff 10,240 = the routers
  = 0.193 percent, same ruling as stage 2.

### Frozen training recipe (both arms, both stages; builders do not tune)

Optimizer AdamW, betas (0.9, 0.95), weight decay 0.1 (none on norms,
embeddings, router), grad clip 1.0, cosine schedule to 10 percent of
peak. Loss: cross-entropy per byte, plus L_aux (MoE arm only).
  Stage 1: peak lr 3e-3, warmup 100 steps, 500 steps total, batch 32
  sequences x 256 ctx = 8,192 tokens/step (4,096,000 tokens total).
  Stage 2: peak lr 1.5e-3, warmup 375 steps, 15,259 steps, batch 64
  sequences x 512 ctx = 32,768 tokens/step (~500,000,000 tokens/arm,
  identical budget, identical data order both arms).
SEEDS, FROZEN: master seed 2827; arm seed = master*10+{1 MoE, 2 dense};
data-order permutation seed = arm seed + 100. Same seed twice = the G1
claim; different arms differ ONLY in architecture and arm seed's init.
Determinism envelope: torch.manual_seed, use_deterministic_algorithms
(True), fixed thread count (8; if G1 fails at 8 the builder drops to 1
as NAMED deviation and banks which count passed), pinned env, pip
freeze digested before first import (train-1 T3a form).

## 2. THE GATES

G1 BIT-REPRO (stage 1, both arms, CPU). Same seed, two CLEAN processes,
byte-identical checkpoints at preregistered steps {30, 200, 500}: same
file bytes, same sha256, quoted literally in the receipt. The train-1
T3c standard is the law: same box, same seed, same bytes. Loss/gradnorm
logs agree to every printed digit. Stage-2 form (named now): the first
1,000 steps run twice byte-identical as a prefix proof, then the full
run banks a digest at every checkpoint so any future rerun verifies.

G2 LOCALITY (stage 1 proves the instruments on the tiny MoE twin;
stage 2 banks the verdict). STAT DEFINITIONS FROZEN NOW. Over the
frozen eval split, deterministic forward, for each MoE layer l with
selection sets S(l,t) (the k=2 experts, tie-break as frozen):
  c_l(e)   = count of positions t with e in S(l,t)
  P_half(l)= (sum of the E/2=4 largest c_l) / (sum of all c_l)
             [uniform routing gives 0.50; the field's measured skew on
             trained MoEs is ~0.95 through half - SYNTHESIS-1 s.3]
  p_l(e,f) = count of unordered co-activation pairs {e,f} = S(l,t)
  C_3(l)   = (sum of the 3 largest p_l) / (sum of all p_l)
             [3 of 28 pairs ~ top 10.7 percent; field: 60-80 percent]
  H_l      = normalized entropy of c_l/sum(c_l), base ln(E)
Banked per layer and as layer means, plus dead-expert count (experts
under 1 percent of a layer's traffic). COLLAPSE NAMED AS ITS OWN
OUTCOME: P_half near 1.0 with more than half the experts dead is
reported as routing collapse, never as locality. The stats artifact
must be byte-identical across two clean replay runs (digest quoted).

G3 VERIFIED REMAT (stage-1 spot-proof, foldable into leg 2). One
trained tiny-MoE checkpoint's quantized expert block is exported to the
LI-S12 packed-trit form, encoded to a generator container (order-0 and
order-2 forms), decoded by a fresh process, byte-exact against the
block digest, ratios banked. COEQUAL MEASUREMENT (the LI-S12 entropy
lesson binds both arms): at every preregistered checkpoint, BOTH arms
bank a compressibility curve - per-tensor-class and pooled order-0
entropy in bits/trit of the absmean-quantized weights, plus trit counts
(c_neg, c_zero, c_pos). The BitNet-2B pin measured 1.560314 bits/trit
pooled; whether OUR training leaves more compressibility, and when it
appears during training, is a primary measured output, not a footnote.

G4 CROSS-BACKEND EXACTNESS - NAMED as a stage-2/3 gate, not run here.
Venues named now: hyde WSL x86-64 CPU vs the 3090 CUDA path on the
trained artifact's exact-integer forward (LI-S2 pattern), horizon venue
the mini's aarch64. Stage 1 makes no cross-backend claim.

## 3. THE FALSIFIER BAR (what stage-2 kills, stated before any training)

Primary metric: bits per byte (bpb) on the frozen test split at the
final checkpoint, identical token budget, identical data order.
  MoE ARM KILLED if bpb_moe > bpb_dense + 0.03. (Equal-active compute
  bought nothing and 3.24x total params bought nothing callable.)
  MATCH if |bpb_moe - bpb_dense| <= 0.03: the MoE arm SURVIVES (equal
  quality at equal active size, with 8x FFN capacity addressable by
  call - exactly the called-never-loaded shape).
  BEAT if bpb_moe < bpb_dense - 0.03.
LOCALITY THESIS KILLED (independently) if layer-mean P_half < 0.60 at
the final checkpoint (uniform is 0.50; below 0.60 means no meaningful
skew survived, so a region-leased brain gains nothing from popularity-
ranked residency at this scale). C_3 and H are banked as evidence but
the kill rides on P_half alone - one number, hard to lawyer.
Routing COLLAPSE (the named outcome above) kills the MoE arm even with
a passing bpb, because a 2-of-8 MoE that uses 2 experts is a dense
model wearing a router.
Both verdicts bank independently; a live loss with dead locality says
so plainly, and the reverse too.

## 4. DATA, PINNED HOW

PRIMARY: enwik8 (the first 10^8 bytes of the English Wikipedia dump of
2006-03-03; the standard byte-modeling corpus). Acquired once under the
download law (R0 class): exact URL, retrieval date, byte count, sha256
of the compressed artifact and of the raw 100,000,000 bytes, verified
twice, banked in lowint/moe0/MANIFEST-DATA.sha256; raw bytes live
OFF-REPO at F:\f32\stage\lowint\data\enwik8\. The digests become the
pin; the URL is provenance, never the oracle.
FALLBACK (if the download is refused or unverifiable, named as a
deviation): the house corpus - every *.md file at master HEAD b8e3860's
tree, sorted bytewise by path, concatenated; the concatenation's sha256
is the pin. Deterministic from the repo alone, no network.
SPLIT RULE, FROZEN: bytes [0, 90%) train, [90%, 95%) validation,
[95%, 100%) test. Sequences are consecutive non-overlapping ctx-sized
windows; training order is the seeded permutation (s.1); eval order is
sequential, unshuffled. Stage 1 uses the same corpus and split (its
4.1M-token budget touches a fraction of train; the permutation decides
which, deterministically).

## 5. STAGE-2 PLAN (the 3090 leg, ready to fire the moment the card frees)

Arms and budget as frozen in s.1: ~163.8M-total/50.5M-active MoE vs
50.5M dense, 500M bytes each, identical data order.
ARITHMETIC: ~6 * N_active * T = 6 * 5.05e7 * 5e8 ~ 1.5e17 FLOPs/arm.
At a conservative effective 20-40k tokens/s for QAT on the 3090
(bf16 compute, absmean quantize in-graph), 500M tokens = 3.5 to 7 h
per arm; BOTH ARMS 8-14 h = one to two overnight quiet windows.
CHECKPOINT CADENCE: every 1,000 steps (~32.8M tokens, ~15-25 min), plus
optimizer state, so a preemption loses at most one interval.
QUIET-WINDOW RULES: legs run only in owner-quiet hours; before any leg,
the research lane's serve busy flag is honored and nvidia-smi must show
the card free of RS050/other compute processes - WAIT with a log, never
contend. DEMOS PREEMPT: a preempt check runs at every checkpoint
boundary (flag file lowint/moe0/PREEMPT); on preemption the leg exits
clean at the checkpoint and resumes later from it. G1 stage-2 prefix
proof (1,000 steps twice) runs FIRST, before the funded budget burns.
Memory law: free -m before any multi-GB step, wait until available
> 12288 MiB, wait logged; the 120B mappings have priority.
CUDA determinism envelope: deterministic algorithms on,
CUBLAS_WORKSPACE_CONFIG pinned, TF32 off, fixed seeds - the train-1
demonstrated standard, now on the card.

## 6. STAGE-1 LEGS, WALLS, CAPS

Builder legs, at most 3, sequential, opus/sonnet at xhigh or below:
  LEG 1 (harness): data pin per s.4; the minimal two-arm trainer
  (one codebase, config-driven); both tiny twins trained on CPU;
  G1 proven twice byte-identical, digests quoted; the compressibility
  curve instrument (s.2 G3 coequal measurement) banked for both arms.
  LEG 2 (stats, folds G3): G2 instruments proven on the tiny MoE twin,
  twice byte-identical; the G3 remat spot-proof on one expert block.
  LEG 3: reserve.
WALLS, ABSOLUTE: NO 3090 use of any kind this stage (a leg that needs
the card is a NAMED REFUSAL banked for stage 2, never worked around);
CUDA_VISIBLE_DEVICES set empty in every training process; nothing
touches the mini, the Telegram messenger, the demo frame, or the 4B
serve path; the stage pin is READ-ONLY; the sealed corpus
lowint/fixtures/LI-S5-ROUTES-1.txt is digest-verified only, NEVER
opened; F:\f32\li-s7-out untouched; nothing lane-related under C:\f32;
never kill any wsl.exe keepalive (pid file
C:\f32\agents\seats\software\.scratch\hyde-keepalive.pid); gate -1
(four legs, working-tree diff included per the LI-S4 kill-law lesson)
runs before and after every leg. Every number in the receipt is
literal command output. Receipt: lowint/moe0/BOBMOE0-STAGE1.txt, ending
in LESSONS-FOR-BIG-WEIGHTS (coequal, per the lane's standing bar).

END BOBMOE0-PREREG-1
