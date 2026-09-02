# OB4-REMAT-1: EXPERT REMATERIALIZATION ON GPT-OSS-20B MXFP4 -- ACCEPTANCE
# AND RECEIPT

Builder 3 (acceptance) for OB4-REMAT-1. Binding documents, in order:
`research/OB4-REMAT-1-PREREG.md` (frozen codec, container, verification
law, live-run plan, bars -- builder 1) and the two builder reports it
governs (builder 1's sweep, builder 2's container build + live run). This
document re-verifies the load-bearing claims independently, states the
limb verdicts, and lands the receipt.

Question this program answers: can the STORED form of a gpt-oss-20b
expert be smaller than its EXECUTABLE form, with rematerialization
(deterministic decode + digest equality against the existing manifest) at
a decode cost the lease budget can afford? Answer, measured not assumed:
**yes, modestly** -- MXFP4 barely compresses (8.2% smaller stored),
consistent with the MoE-0 L1 prior that order-0 entropy on trained
low-bit weights sits near its own ceiling; unlike the ternary case,
splitting the per-block scale byte from the packed mantissa nibbles
before compression is a real, measured, non-zero lever. That is a
bankable result on its own, not a shortfall.

## Headline table

| axis | figure | source |
|---|---:|---|
| pooled stored/raw ratio (with index) | **0.9182230416359207** | `store-build.json` |
| pooled stored/raw ratio (container only) | 0.9181917989294485 | `store-build.json` |
| bytes saved | 832,398,474 B (0.7752 GiB) | `store-build.json` |
| decode share of lease-get-bytes time | 91.57% (run a) / 92.06% (run b) | `run-analysis.json` |
| decode share of total process time | 27.07% (run a) / 27.81% (run b) | `run-analysis.json` |
| live p95 vs OB-1 banked resident baseline | 1.6878x / 1.7817x | `run-analysis.json` |
| live p95 vs this build's own resident control | 1.7346x / 1.8310x | `run-analysis.json` |
| COST bar (<=3.0x) | **PASS**, 1.62-1.38x of budget spent | vs prereg section 7 |
| DIGEST limb, full container | **PASS 4608/4608** | `store-verify.json`, builder 2 |
| DIGEST limb, independent 256-row sample | **PASS 256/256** | `verify-sample256.json`, this builder |
| identity across 5 runs (2 builds + 2 provenances + 1 A/A repeat) | **PASS**, one sha256 each for `identity.txt` and `route.log` | re-derived below |

Per tensor-kind stored/raw ratio (`store-build.json`, `by_tensor_kind`):

| tensor kind | n | ratio |
|---|---:|---:|
| ffn_gate_exps.weight | 768 | 0.9203690465383685 |
| ffn_up_exps.weight | 768 | 0.9195211702603977 |
| ffn_down_exps.weight | 768 | 0.9183476768166757 |
| ffn_gate_exps.bias | 768 | 0.462342212818287 |
| ffn_up_exps.bias | 768 | 0.38415922941984953 |
| ffn_down_exps.bias | 768 | 0.5071616843894676 |

Weight tensors are 99.74% of pooled bytes (10,152,345,600 of
10,178,887,680), so the pooled ratio is dominated by the ~0.918-0.920
weight-tensor rows; the bias rows compress far better in relative terms
but move the pooled number by less than 0.3 points. This matches builder
1's 576-slice sweep prediction (pooled 0.9182) to four decimal places on
the full 4608-row build -- the stratified sample generalized cleanly to
the whole model.

## Limb verdicts

**DIGEST limb (stop-ship): PASS.** Builder 2's full-container run decoded
and sha256-matched all 4608/4608 manifest rows in 12.69 s on 6 workers,
0 failures (`store-verify.json`). This builder re-verified independently
with a script written fresh against the prereg's section-4 container spec
(not a copy of `build_store.py` or `verify_store.py`): a seeded
(20260901), disclosed, reproducible random sample of 256 of the 4608 rows
(`verify_sample256.py`), decoded through the same ctypes-linked libzstd
path the live engine uses, checked against the manifest's own digest.
Result: **256/256 PASS, 0 failures**, 10.54 s wall
(`research/ob4/verify-sample256.json`). Two independently-written readers
agree on every row they both touched (the sample is a subset of the
full-container pass); the container/index format is correctly specified
and correctly built.

**RATIO limb (report-only, no threshold by design): 0.9182230416359207
pooled.** Reported, not scored, per the prereg's own framing -- an honest
"MXFP4 barely compresses" is a valid result. It held on the full build to
four decimal places against the 576-slice sweep's prediction.

**COST limb (<=3.0x OB-1 resident baseline p95): PASS.** Two live K=8
AC-CODE runs (`ob4-k8-code-a`, `ob4-k8-code-b`, an A/A repeat) measured
p95 1.6878x and 1.7817x of OB-1's banked resident baseline
(16073.670240 ms), and 1.7346x / 1.8310x of this build's own freshly-run
resident control (15640.098009 ms) -- both readings clear the bar with
40-45% of the budget unspent. The dominant cost inside that number is
decode itself: 91.57-92.06% of lease-get-bytes time, 27.1-27.8% of total
process time, running on **one** thread (the zstd decode call) while ten
compute threads sit idle -- named as the main finding below, not folded
into the pass/fail verdict.

**Identity: PASS, beyond the bar.** Re-derived independently by this
builder, not copied from builder 2's JSON:

```
sha256sum ob4/runs/ob4-res-code/identity.txt ob4/runs/ob4-k8-code-a/identity.txt \
          ob4/runs/ob4-k8-code-b/identity.txt ob1/runs/res-code-a/identity.txt \
          ob1/runs/lease-k8-code/identity.txt
  -> 9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8  (all 5)

sha256sum ob4/runs/ob4-res-code/route.log ob4/runs/ob4-k8-code-a/route.log \
          ob4/runs/ob4-k8-code-b/route.log ob1/runs/res-code-a/route.log \
          ob1/runs/lease-k8-code/route.log
  -> f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77  (all 5)
```

One output digest and one route-log digest across two separate builder
sessions (OB-1 built the resident and lease-K8 references; this program
built the resident control and the remat-container leases), two byte
provenances (raw gguf pread vs C2-decoded container), and an A/A repeat
of the remat path against itself. Container and index digests were also
independently re-summed by this builder directly from the store files
(`sha256sum EXPERT-STORE-20B.ob4 EXPERT-STORE-20B.ob4.idx`) and matched
`a5a8fffd46230fb2752945588aa768e4a833c1f7cca985e3ea00f375dbd79314` /
`72c017badc0d141bdd39357265a12af93f3dc932ed748d2977eb7184dc101480`
literally, as did the manifest file
(`5e9cf0be34f5a02af41e1b0c0688455604731828e2927e9ec0247d22163e99aa`) and
the container's on-disk size (9,346,171,190 B).

## MoE-0 L1 contrast: ternary order-0 dead vs MXFP4 split-stream measured here

The house's prior low-bit compression finding (`REPORT-BOBMOE0-2026-08-31.md`
section 5-6, banked lesson L1) is a from-scratch ternary MoE: pooled
order-0 entropy on trained ternary weights rises to and sits flat at
1.584358-1.584962 bits/trit against the ternary maximum log2(3) =
1.5849625 -- i.e. **order-0 compression of trained ternary weights is
dead**, the distribution converges to maximum entropy and there is
nothing left for any order-0 scheme, split-stream or otherwise. L1's own
words: "never budget compression on order-0 ternary skew... use context
models or remat generators."

MXFP4 is a different format and the measurement here confirms it behaves
differently, not identically: gpt-oss's MXFP4 blocks pack two distinct
streams at different information densities in one interleaved byte
sequence -- a near-uniform 4-bit mantissa nibble stream (close to its own
entropy ceiling, matching L1's finding almost exactly for that half: C2's
mantissa-adjacent pooled ratio sits within 0.0001 of C3's order-0 entropy
floor) and an 8-bit E8M0 scale-byte stream that is measurably less
uniform. De-interleaving the two before compressing each independently
(C2) recovers a real, non-zero, non-trivial win: pooled ratio 0.9182
against C1's (compress-as-is) 0.9585 -- roughly 4.4 points of the pooled
byte budget, entirely attributable to a structural fact about the
*format* (per-block scale metadata is separable from payload) rather
than to any residual skew in the trained values themselves. Put plainly:
where ternary weight *values* carry no exploitable order-0 skew, MXFP4's
*layout* still does, one layer up from the value distribution. Neither
result contradicts the other; both are the same underlying phenomenon
(trained low-bit weight *values* converge to maximum entropy) observed
through two different container shapes.

## The composed figure, stated as two separate factors

Per house acceptance instruction, these are NOT multiplied into one
number -- they are two different axes, measured by two different
programs, and composing them is a design question for a future box, not
an arithmetic operation to perform here.

- **(a) Residency exposure (RAM axis, OB-1, `OB1-EXPOSURE-1.md`).** At the
  same operating point this program's live run used (K=8, code corpus):
  capacity exposure (ACCT, logical bytes / resident-budget bytes) =
  **2.526252**; RSS-based exposure (logical bytes / actual measured
  process peak RSS) = **2.0120-2.0179**. This is "how much more model a
  box can serve than it keeps resident," at a routing-miss rate of
  79.73% for code, cost 1.41-1.51x baseline (report-only limb, no bar at
  K=8).
- **(b) Storage ratio (disk axis, OB-4, this program).** The container
  that backs each miss is **0.9182x** the size of the raw manifest bytes
  it replaces -- "how much smaller the thing being fetched on a miss is,"
  at a decode cost of 1.69-1.78x the resident baseline p95 (COST limb,
  bar <=3.0x, PASS).

**What composing them would mean for a future box:** exposure (a) is a
RAM-residency multiplier realized today by NOT keeping the full model
resident; ratio (b) is a disk-footprint multiplier on the bytes read on
each miss that (a)'s design already creates. They compose along
different resources (RAM budget vs disk/transport bytes), not into one
scalar: a box running OB-1's K=8 policy already gets the 2.5x RAM
headroom whether or not OB-4's container is in use; layering OB-4's
container on top would shrink the on-disk/on-network footprint of that
same K=8 traffic by a further ~8.2%, at the additional CPU cost measured
here (COST limb, currently PASS with margin, single-threaded decode being
the identified lever for improving that margin further -- see below).
The honest statement is "two multipliers on two different resources,"
never "a single 2.32x number" -- no such number was computed by either
program and none should be quoted from this pair of documents.

## Main finding: decode is single-threaded and the whole cost

91.57-92.06% of lease-get-bytes wall time is the zstd decode call itself,
running on one thread while ten compute threads are idle
(`run-analysis.json`: `lease_decode_share_of_lease_get_bytes` 0.9157 /
0.9206). Store-blob reads took only 21.4-20.6 s total against OB-1's
banked 100.6 s for preading the equivalent raw bytes -- a ~4.7x gap for
an 8.2% smaller payload, larger than the ratio alone would predict.
**Flagged as an observation, not a controlled result**: it is consistent
with page-cache residency (the 9.35 GB container fits comfortably beside
other resident state on a 24 GB box where the 12.11 GB raw gguf is
tighter), but this program did not run the controlled cold-cache /
warm-cache A/B needed to isolate that from the codec itself. It may be a
bigger lever on total wall time than the compression ratio is, and is
named here as the natural next step, not claimed as a result.

## Limitations, named plainly

- **Single model.** All measurements are on one pinned checkpoint
  (`gpt-oss-20b-MXFP4.gguf`, sha256
  `27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901`).
  Nothing here claims to generalize to other MoE architectures, other
  block-float formats, or other expert counts/widths without re-running
  the same sweep.
- **One codec class.** The winning codec (C2, split-stream zstd -19) is
  a generic byte-level compressor applied after a format-aware
  de-interleave. No arithmetic coder, no MXFP4-specific entropy model,
  and no learned/neural codec was built or measured. C3's order-0 entropy
  floor bounds what any *order-0* scheme (arithmetic coding included)
  could do on this data; it does not bound higher-order schemes.
- **No generator representations.** This program's own question (can the
  stored form be smaller than the executable form) was answered with
  "decode is decompression," not "decode is regeneration from a smaller
  generative description" -- the more ambitious rematerialization idea
  named in the house N4 roadmap (store the generator, not the bytes) is
  the held ambition for a future program, not attempted here. What was
  built is a real point on that spectrum (stored bytes != executable
  bytes, decode is deterministic and digest-checked) but a conservative
  one: a lossless byte-transform, not a learned generator.
- **Bias tensor dtype inferred, not read.** Per the prereg's own
  deviation 2, the three bias tensor kinds' F32 layout is inferred from
  element-count arithmetic (11520/2880=4.0 exactly) plus an empirical
  value-range check, not from a literal GGUF tensor-type field read. This
  is well-supported (unambiguous arithmetic on 3 already-small tensor
  kinds that are 0.26% of pooled bytes) but is a deviation from reading
  the format specification directly, and is repeated here rather than
  silently inherited.
- **Cost measurement is this program's harness, not the production lease
  engine.** The 1.69-1.78x p95 figures come from the `ob4` worktree's own
  engine build (`remat-engine.patch` on top of the `ob1` lease engine),
  CPU-only, against OB-1's CUDA-built resident baseline -- flagged by
  builder 2 as deviation D4, not assumed harmless: the K=0 build-control
  arm (`ob4-res-code` vs `ob1-banked-res-code-a`, both resident, no
  container) shares the identical `identity.txt`/`route.log` digest pair
  used throughout this document, which is the check that catches a
  CPU-vs-CUDA build divergence if one existed. None was found.
- **Decode-cost residency observation is unverified.** As stated above,
  the ~4.7x blob-read speed gap (larger than the 0.918 ratio alone
  predicts) is named as a hypothesis (page-cache effect), not measured
  with a controlled A/B.

## Discipline

RUNLOCK: builder 2's live-run batch acquired the box-wide lock after
900 s of queueing, held it 2026-09-01T01:35:50Z-02:17:23Z (2493 s across
four runs: the resident control, both K=8 lease runs, and one more),
released it immediately after
(`research/ob4/RUNLOG-1.txt` lines 333-334, 567). Guard processes pid 654
(openbob serve) and pid 489 (searxng) were present before and after every
run (`RUNLOG-1.txt` line 337-338). This builder's own two verification
passes (full-container re-run implicit in trusting builder 2's receipt,
plus the independent 256-row sample) are pure pread + zstd decode with no
model loaded, so per house rule needed no RUNLOCK and took none; RAM was
checked before running (`free -h`: 19 GiB available, well above the 6 GB
floor) and the sample script ran under `nice -n 10`. `/mnt/f/f32/stage/`
was read from, never written outside `research/ob4/` (this program's own
scratch subtree). The shared fork clone `/root/rs053/llama.cpp` was not
touched by this builder; this program's own worktree,
`/root/ob4/llama.cpp` (branch `ob4`, based on fork HEAD `c087083`), was
not edited by this builder either -- only read for the container-format
citation already frozen in the prereg. `git -C /root/rs053/llama.cpp`
remained clean.

## Reproduction

```
# full-container digest verification (builder 2's script, 4608/4608):
wsl.exe -u root -e sh -c 'python3 /mnt/f/f32/openbob-wt/ob4/research/ob4/verify_store.py'

# this builder's independent 256-row sample, seeded and reproducible:
wsl.exe -u root -e sh -c \
  'python3 /mnt/f/f32/openbob-wt/ob4/research/ob4/verify_sample256.py \
   /root/ob4/EXPERT-STORE-20B.ob4 20260901'

# independent digest re-derivation of runs, container, index, manifest
# (no WSL needed, all paths on the F: drive):
sha256sum EXPERT-STORE-20B.ob4 EXPERT-STORE-20B.ob4.idx   # under research/ob4/
sha256sum research/ob1/EXPERT-MANIFEST-20B.sha256
sha256sum research/ob4/runs/*/identity.txt research/ob1/runs/{res-code-a,lease-k8-code}/identity.txt
sha256sum research/ob4/runs/*/route.log    research/ob1/runs/{res-code-a,lease-k8-code}/route.log
```

## Commit

`research/OB4-REMAT-1.md` (this document), `research/ob4/verify_sample256.py`
(independent re-verification script, written fresh by this builder), and
`research/ob4/verify-sample256.json` (its receipt, 256/256 PASS) committed
on branch `ob4` in `F:\f32\openbob-wt\ob4`, based on master `4e7be6b`, on
top of builder 2's landing commit `b6226d5`. Master untouched, unpushed,
unmerged, per house law.

END OB4-REMAT-1
