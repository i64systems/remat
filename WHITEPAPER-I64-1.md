# EXACT COMPUTATION FROM LEASED MEMORY
# The i64 white paper. Assembled from the receipts it cites; every
# number is a literal from a named, attached receipt. Approved for
# disclosure 2026-09-01. (c) 2026 i64. Claims discipline: section 8.
# A portion of this document is subject to copyright protection. The
# copyright holder has no objection to reproduction of the document
# by the U.S. Patent and Trademark Office as part of the patent file
# or records, but otherwise reserves all copyright rights whatsoever.

    "Truth is fixed; only the cost of reaching it may move."
                                        - Harriett Little

## 1. THESIS
Model capacity and resident memory are treated as the same number by
the entire industry: to run N bytes of model, buy N bytes of fast
memory. We break that equivalence. A model's weights live cold on
cheap storage; the exact executable state needed by the current
computation is rematerialized on demand, verified by digest against a
ledger, used, and discarded - and the output is byte-identical to the
fully resident computation, every time, on commodity hardware. The
governing law (research/LAW-EXPOSURE-1.md): identity decides whether
computation exists; latency decides whether the operating point is
retained; exposure is what the controller maximizes afterward.
Formally: max N/M subject to dy = 0 and tau <= 2*tau_0, where
CAPACITY EXPOSURE = logical model bytes / peak fast-resident bytes.

## 2. SUBSTRATE AND METHOD
All results in this draft ran on one owned consumer box: a Ryzen
5900X / RTX 3090-class / 24GB-WSL-RAM Windows machine. Instruments are
preregistered before they exist; kill conditions are committed before
runs; every artifact carries a sha256; every headline run is executed
twice and must reproduce byte-for-byte (A/A); acceptance legs
re-derive figures from raw bytes with independently written readers.
Subject model for the exposure results: gpt-oss-20b/120b (MXFP4 MoE,
Apache 2.0), served by an instrumented fork with a digest-verified
expert lease path.

## 3. RESULTS: THE EXPOSURE CURVE (receipts OB1-EXPOSURE-1.md,
## OB1B-KNEE-1.md)
Static popularity residency, gpt-oss-20b, identity exact at every
point (leased output and route logs byte-identical to fully resident):

    K resident   exposure (acct)   p95 vs baseline
    16           1.674400          1.25-1.29x
    8            2.526252          1.41-1.51x
    4            3.388101          1.52-1.54x
    2            4.084898          1.52-1.58x
    1            4.553092          1.58-1.60x
    0            5.142505          1.48-1.77x (A/A spread = noise floor)

At K=0 (pure streaming, empty resident set, one hundred percent miss)
output identity held byte-exact and the 2.0x latency bar still
passed. THE KNEE DOES NOT EXIST ON THIS MODEL: E2x = 5.142505 is a
ceiling set by the design (82.0 percent of the K=0 residency is
non-expert trunk), not a knee set by cost. Twenty-one runs across
six K values, two thread counts, and two binaries produced exactly
one identity digest and one route digest per corpus, two corpora:
four digests total.

WHY THE KNEE DOES NOT EXIST, measured rather than argued: across
all sixteen leased runs of both legs, every lease event moves
exactly 13253760 bytes and the read/verify rates are FLAT from
K=16 to an empty resident set (within 4 and 1.3 percent, smaller
than the box's own A/A noise). Cost tracks bytes moved and nothing
else; the feared per-lease-event overhead floor does not exist.

ENFORCED VS EMERGENT FOOTPRINT (the leg's sharpest finding): plain
mmap paging of the 63 GB model reaches a similar-looking exposure
(3.29x by RSS) with no engine at all - but its footprint varied
17.17 percent between two byte-identical runs, whatever the kernel
happened to retain that minute. The leased footprint reproduced to
0.1765 percent same-night and 0.0022 percent across OB-1's repeats,
with every byte digest-verified before use. An exposure figure
from paging is an observation about one run; from leasing it is an
enforced bound. The paged pair also bounds the big model's wall
clock: 63 GB through a 24 GB box, CPU-only, byte-identical A/A,
about 50 ms per token.

THE 120B ROW IS MEASURED (receipts OB5A-ALLOC-1.md, OB5A-SCOUT-1.md).
The engine originally preallocated the full 63.4 GB tensor range
before leasing began, impossible in 24 GB RAM; that allocation is
now GONE by architecture: the runtime reserves the address range
without charge and commits memory only for resident state (largest
single model-state allocation on the 63 GB model: 586.83 MB, a
102.99x reduction; commit peak 7806517248 bytes, inside its
preregistered bar). The measured row, CPU-only, no kernel setting
changed: exposure 8.209143 accounted (7.016 by peak RSS), output
and routing byte-identical to the paged reference AND across the
A/A repeat, all four preregistered lease-counter predictions exact
including the full 36-layer series, p95 1.7971x the reference
(frozen bar 2.0x), 11.3 tokens/s of batch EVALUATION throughput
(the perplexity harness; interactive decode is a different, lower
number and is measured, not extrapolated, in the serving design's
first slice). Four runs by two different
allocation strategies (a kernel-overcommit scout and the
resident-proportional allocator) hash to the same output pair; the
architectural path costs +0.39 percent of chunk time over the
kernel shortcut and needs no box-wide change. THE SLOPE IS NOW A
MEASUREMENT: at the same resident fraction (6.25 percent), the
12 GB model exposes 4.084898 and the 63 GB model exposes 8.209143.
Sparser, more expert-heavy models expose more under the same
discipline; the structural ceiling on the large model is 15.805342.

## 4. RESULTS: LOCALITY AND POLICY (RS053-GPTOSS-LOCALITY-1.md,
## OB2-PREDICTIVE-1.md, OB3-REGION-1.md)
Pretrained large MoE routers carry strong, exploitable structure:
layer-mean P_half 0.9188 (120b prose), and task regions are real
(top-32 expert-set Jaccard between prose and code: 0.1868).
Two deterministic policies - both pure functions of route history and
input bytes, replayable by construction:
- Dynamic integer decay-counter residency: cross-domain miss 60.5733
  -> 14.3759 percent at K=16; the live engine's residency schedule
  byte-matches its committed simulator; measured miss equals
  simulated miss to the exact integer. The adaptive policy even
  edges the in-domain static set measured live in the region leg
  (14.3759 vs 14.4536 percent, same corpus, same K) without being
  told the domain.
- Task-region selection by a frozen integer byte-detector compiled
  into the engine: on a genuinely held-out slice, cross-domain miss
  58.5814 -> 16.9796 percent (3.45x); switching beats merging
  (counterfactual replay on the same live route log); the prose
  no-regression row reproduces the static result byte-identically.

## 5. RESULTS: VERIFIED REMATERIALIZATION (OB4-REMAT-1.md,
## OB4B-PARDEC-1.md)
All 4608 expert slices encoded into a content-addressed compressed
store; every miss decodes, digest-verifies against the ledger, then
executes. Identity: one output digest across seven runs spanning both
engine generations. Stored/executable ratio 0.9182 - honestly small,
and the mechanism is named: trained MXFP4 mantissas sit at their own
entropy floor, replicating our from-scratch ternary finding (below);
the saving is format-structural (scale-stream separation). With an
8-worker decode pool the compressed path costs LESS than raw reads:
p95 1.2072x vs 1.5139x against the same resident control,
deterministic placement invariant held (pool-8 output
byte-identical to pool-1).

## 6. RESULTS: THE TRAINING TRAJECTORY (lowint/moe0/BOBMOE0-RESULT-1
## .txt, REPORT-BOBMOE0-2026-08-31.md)
A fully ternary mixture-of-experts transformer trained from scratch
on a single consumer RTX 3090 under WSL2 with a BIT-EXACT TRAINING
TRAJECTORY: byte-identical checkpoints, optimizer state, and metrics
across independent processes, with crash recovery proven at a real
mid-run boundary (the failing step predicted exactly by arithmetic
before the fix). Preregistered outcomes: the MoE arm matched its
active-size dense twin (bpb 1.25757 vs 1.26010) with 8x addressable
capacity and no routing collapse; the natural-locality limb was
KILLED by its own bar (P_half 0.55196 < 0.60) and is reported as
such. Cross-format law from this run plus section 5: trained low-bit
weight values converge to maximum entropy; compression must come
from structure or generators, never order-0 statistics.

## 7. WHAT THIS MEANS
Roughly three orders of magnitude separate accelerator memory from
NVMe per gigabyte. Measured exposure is the conversion machine
between them: on the reported curve, resident-memory requirements
fall 3.4x on the small model and 8.2x MEASURED on the large
(ceilings 5.1x and 15.8x) while outputs remain byte-identical and
measured p95 spans 1.25x to 1.80x, every run inside the 2.0x bar
(the worst small-model observation is an A/A repeat whose spread
is the box's own noise floor). A cold
reader can re-derive the bandwidth arbitrage in an afternoon; the
contributions that do not follow from the idea are the identity
discipline (the zero displacement lock, held across every run in
this program's history), the measured policy results (misses cut
by factors of 3.45x and 4.21x below the policy-free bound), and the
enforced-versus-emergent distinction: paging's footprint is
whatever the kernel kept that minute, leasing's is a promise.

## 8. CLAIMS DISCIPLINE AND LIMITATIONS
We do not claim the first ternary MoE (MoTE, TC-MoE, ButterflyMoE
exist); the training claim is the bit-exact trajectory as defined in
section 6. Exposure results: one model family, one box, chunk-level
p95 (token-level tail latency is measured in [TBD-A]), prose/code
corpora only, static and two dynamic policies; the 90-day scope of
this draft is CPU-dominant compute, which shelters streaming cost -
the accelerated-compute knee is future work on disclosed hardware.
Every limitation above is also written in the receipt it applies to.

## 9. REPRODUCTION
The dossier (assembly spec: advisory/DOSSIER-SPEC-F32-1.md) ships
the reproduction kit: manifests, preregistrations, run drivers, and
digests. Determinism is verifiable by construction on the reader's
own machine; we would rather you test us than believe us.
