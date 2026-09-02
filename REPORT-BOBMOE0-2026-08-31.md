# BOB-MOE-0: RESULTS OF THE FIRST FUNDED TERNARY-MOE TRAINING RUN
# Architect's report to the owner, 2026-08-31. Publishable-grade under
# the living-white-paper law. Every number below is a literal from the
# receipts named in section 8; nothing is rounded or inferred.

## 1. WHAT WAS RUN
Two arms, trained from scratch on enwik8 (100,000,000 bytes, corpus
sha256 2b49720e...c024a8, train/val/test split frozen in the
preregistration BOBMOE0-PREREG-1.md, committed before training):
- MOE ARM: a fully ternary mixture-of-experts transformer. 12 MoE
  layers, 8 experts per layer, top-2 routing by a deterministic
  integer router. 163.8M total parameters, 50.5M active per token.
- DENSE ARM: an active-size-matched fully ternary dense twin (50.5M).
Both arms ran 15,259 steps on the house RTX 3090-class card under
WSL2, single data-order permutation (seed 28471, amendment A1), bf16
compute with a determinism envelope (fixed thread counts, pinned
kernel workspace config). The run survived a real mid-run crash at
the first epoch boundary (step 2748): the wrap fix was preregistered
before the fix landed, crash arithmetic predicted the failing step
exactly, and the boundary was proven byte-identical twice before
relaunch (BOBMOE0-STAGE2B-PLAN.txt, G1-WRAP).

## 2. VERDICTS ON THE FROZEN BARS
The kill conditions were committed before training. Outcomes:

BPB BAR: KILL if bpb_moe > bpb_dense + 0.03.
  bpb_moe   = 1.25756923216550298e+00
  bpb_dense = 1.26009954223008691e+00
  delta     = -2.53031006458392937e-03
  THE MOE ARM SURVIVES: equal quality at equal active size, with 8x
  the FFN capacity addressable by call and 3.24x total parameters.
  (Not a BEAT: the prereg's BEAT bar required delta < -0.03.)

COLLAPSE BAR: KILL if the router degenerates to a fixed expert set.
  Dead experts: 0 of 96 slots. Smallest single-expert share:
  7.98027073732718861e-02. NO COLLAPSE. The Switch-style balancing
  term (alpha 0.01) fully prevented collapse at this scale.

LOCALITY BAR: KILL if layer-mean P_half < 0.60 at the final
checkpoint. P_half is the fraction of routing traffic carried by the
most-used half of each layer's experts; uniform routing gives 0.50.
  layer-mean P_half = 5.51962400593637992e-01
  LOCALITY THESIS KILLED on its own bar. Every layer is individually
  below 0.60 (min 5.22820260496671740e-01 at layer 5; max
  6.16665066564260123e-01 at layer 11).

## 3. THE TRAJECTORY CLAIM (what makes this run citable)
The claim of record, in the sharpened language adopted after outside
adversarial review: a BIT-EXACT TRAINING TRAJECTORY. Witnessed by:
- Checkpoint estate re-hashed clean: 30/30 digest lines per arm
  verified against CKPT-DIGESTS.txt (36.5 GB re-hashed, coverage
  checked in both directions).
- Final-checkpoint evaluation run twice per arm as clean separate
  processes: byte-identical artifacts (moe 1a33cd86..., dense
  5339aa1e..., cmp rc 0 both).
- Routing statistics computed twice under different machine load:
  3/3 artifacts byte-identical.
- Resume equivalence proven at a real boundary (the epoch-wrap
  relaunch chain), not a staged one.
We do NOT claim "first ternary MoE" (MoTE, TC-MoE, ButterflyMoE
exist). Narrow novelty per the house survey (SYNTHESIS-1): N1 the
first NATIVELY TRAINED from-scratch ternary MoE known to the survey,
at honestly stated small scale; N2 the first from-scratch ternary-MoE
compressibility curve; N3 bit-reproducible routing statistics where
the field reports single-run numbers.

## 4. THE LOCALITY STORY (the honest negative, and its resolution)
Routing drifted TOWARD uniform as training progressed: P_half
5.83890268977214522e-01 at step 2000 falling to 0.55196 at the end;
routing entropy rising 9.87476665521694774e-01 to
9.94974377152421208e-01. Field reference for trained MoEs is P_half
around 0.95; ours barely clears the 0.50 uniform floor. The prereg's
own honesty clause anticipated the mechanism: the balancing term that
prevents collapse also pushes toward uniform, and at this scale
almost no natural skew survived it.

RESOLUTION, measured the same afternoon (RS053, merged 705ba11): the
identical instrument family applied to large PRETRAINED open MoEs
found strong skew: gpt-oss-120b layer-mean P_half analog
0.918757120768229130 (prose) / 0.914716932508680580 (code);
gpt-oss-20b 0.851591904958089230 / 0.836227258046468136; and on the
120b, prose and code light substantially different expert sets
(top-32 Jaccard 0.186798397125065851). The two-by-two resolves: ours
flat, theirs skewed. Routing locality emerges with scale and data
richness and comes free with existing open weights; the tiny model's
flatness is a scale artifact, not a verdict on the leasing thesis.
Consequence already acted on: the exposure program (OB-1) builds on
existing pretrained weights, per the owner's funding word.

## 5. THE COMPRESSIBILITY STORY
First such curve on a from-scratch ternary MoE per the house survey.
Pooled order-0 entropy in bits per trit, against the ternary maximum
log2(3) = 1.5849625:
- MoE arm: rises from 1.584358 (step 2000) to 1.584961, flat from
  step 12000 on.
- Dense arm: rises to 1.584962 at step 8000, then falls monotonically
  to 1.584940 (the one non-monotone arm).
The BitNet-2B pin's zero-skew (1.560314 bits/trit) did NOT reproduce
in from-scratch training at this scale; only the attention q/k
projections carry slight skew (moe wq 1.583552, p_zero 0.354).
Reading: order-0 compression of trained ternary weights is
essentially dead; compression gains must come from higher-order
structure, context models, or generator-based rematerialization
(store the generator, not the bytes).

## 6. LESSONS FOR THE BIG WEIGHTS (coequal bar, banked)
L1 Never budget compression on order-0 ternary skew; trained ternary
   converges to maximum entropy. Use context models or remat
   generators.
L2 Called-never-loaded survives on quality (the bpb verdict) but dies
   on NATURAL skew at tiny scale; pretrained large MoEs supply the
   skew instead. Replay-journal prefetch (lookup, not prediction) is
   unaffected.
L3 Routing drifts toward uniform during from-scratch training with
   balancing on: residency policies tuned early are wrong at
   convergence.
L4 The determinism envelope scales: bf16 training, preemption, and a
   crash-recovery segment chain all held byte-exact across
   independent runs on consumer hardware.
L5 Balancing alpha 0.01 fully prevents collapse at this scale; weaker
   settings are unproven here.

## 7. WHAT THIS FUNDS NEXT (status, not a request)
OB-1, the capacity-exposure harness on gpt-oss-20b, fired on the
owner's word at this report's landing: experts cold on NVMe, loaded
on miss, sha256-verified against a per-expert manifest, byte-identity
required against the fully-resident baseline; capacity exposure
(logical bytes on disk / peak fast-resident bytes) measured, never
claimed. All other follow-ons (M1-M7 in the receipt: exact-integer
routing law, skew-engineering ladder, order-2 generator pass,
gpt-oss compression fold-in, header fix, checkpoint disposition,
owner CLI demo) are HELD as a menu under the owner's word.

## 8. RECEIPTS
- lowint/moe0/BOBMOE0-RESULT-1.txt (the collector receipt of record)
- lowint/moe0/BOBMOE0-PREREG-1.md (bars frozen before training)
- lowint/moe0/evidence/ (route stats, compressibility curves, leg
  logs; all digests inline)
- research/RS053-GPTOSS-LOCALITY-1.md + -PREREG.md (the resolution)
- Checkpoint digests: final moe 9e7f5cf8..., final dense da7ce35d...,
  anchor 936462e5...; full 64-hex forms in the receipts.
- Checkpoint bytes (36.5 GB) live off-repo under
  F:\f32\stage\lowint\moe0-ckpt\stage2\ per the checkpoint law;
  disposition is menu item M6.
