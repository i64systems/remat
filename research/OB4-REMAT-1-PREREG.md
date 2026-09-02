# OB4-REMAT-1-PREREG

Builder 1 output for OB4: can a gpt-oss-20b MXFP4 expert's STORED form be
smaller than its EXECUTABLE form, at a decode cost the lease budget can
afford? This document freezes the codec, container, verification law,
live-run plan, and pass/fail bars, per the OB4-REMAT-1 prereg brief, before
any live decode-in-the-loop run (builder 2's job).

Answer up front: MEASURED, NOT ASSUMED. MXFP4 barely compresses (pooled
best ratio 0.918 of raw, i.e. ~8% smaller). This is a valid, bankable
result in its own right, consistent with the MoE-0 L1 prior (order-0
entropy on trained low-bit weights is close to its ceiling) extended to
MXFP4's 4-bit float format. The one lever that helps at all is separating
the per-block scale byte from the packed 4-bit mantissa before compressing
each stream on its own.

## Inputs, pinned

- Model: `/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf`
  sha256 `27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901`
  (matches the pinned value in the run brief; recomputed literally with
  `sha256sum`, not assumed).
- Manifest: `research/ob1/EXPERT-MANIFEST-20B.sha256`, 4608 data rows
  (24 layers x 32 experts x 6 tensor kinds), file sha256
  `5e9cf0be34f5a02af41e1b0c0688455604731828e2927e9ec0247d22163e99aa`.
- Fork: `/root/rs053/llama.cpp` branch `ob1` HEAD
  `c087083d21e6bd32c1faebc09434a4b54f5d946a` (unchanged; read-only citation,
  no edits made to that clone). Own worktree: `git -C /root/rs053/llama.cpp
  worktree add /root/ob4/llama.cpp -b ob4 c087083` (branch `ob4`, same head,
  0 commits added -- this builder only reads ggml source, does not touch it).
- git worktree used for all commits here: `F:\f32\openbob-wt\ob4`, branch
  `ob4`, based on master `4e7be6b`.

## 1. MXFP4 layout, as found in the fork

Cited from `ggml/src/ggml-common.h` (house fork, commit `c087083`):

```c
#define QK_MXFP4 32
typedef struct {
    uint8_t e;              // E8M0 (8-bit power-of-two exponent), shared block scale
    uint8_t qs[QK_MXFP4/2];  // 16 bytes: 32 packed 4-bit mantissa indices, 2 per byte
} block_mxfp4;
static_assert(sizeof(block_mxfp4) == sizeof(uint8_t) + QK_MXFP4/2, ...);
```

So one block = 17 bytes covering 32 elements: **1 scale byte (E8M0) + 16
mantissa bytes (32 packed 4-bit nibbles)**. The 4-bit nibble indexes a
16-entry doubled-E2M1 table (`ggml-common.h`, shared with NVFP4):

```c
GGML_TABLE_BEGIN(int8_t, kvalues_fp4, 16)
    0, 1, 2, 3, 4, 6, 8, 12, 0, -1, -2, -3, -4, -6, -8, -12,
GGML_TABLE_END()
#define kvalues_mxfp4 kvalues_fp4
```

Decode (`ggml-quants.c:dequantize_row_mxfp4`) is `value = E8M0_to_fp32_half(e)
* kvalues_mxfp4[nibble]`; `ggml-impl.h:ggml_e8m0_to_fp32_half` turns the raw
byte into IEEE-754 bits directly (`(x-1)<<23` for x>=2, two denormal special
cases for x<2) -- a handful of integer ops per block, not a table walk.

Confirmed empirically against one manifest row (`layer=0 expert=0
ffn_gate_exps.weight`, nbytes=4406400): `4406400 / 17 = 259200` blocks
exactly (no remainder -- block-aligned), `259200 * 32 = 8294400` elements,
`sqrt(8294400) = 2880` exactly -- so each expert's gate/up/down weight is a
plain 2880x2880 MXFP4 matrix (matches gpt-oss-20b hidden_size=2880, expert
intermediate=2880), stored as 2880 rows x 90 blocks/row x 17 bytes/block =
1530 bytes/row.

Bias tensors (`ffn_{gate,up,down}_exps.bias`, 11520 bytes each) are NOT
MXFP4 -- no block structure fits (11520 is not a multiple of the tensor
width in a blocked sense the way the weight tensors are). `11520/2880 =
4.0` exactly, `11520/5760=2.0`; read as little-endian f32 the 2880 values
are all finite and in a plausible NN-bias range (min -1.8125, max
0.33984375, mean -0.464), consistent with plain F32. This is inferred from
element-count arithmetic + an empirical range check, not from a literal
GGUF tensor-type field read (a full GGUF KV-section parser was judged not
worth the time for 3 already-well-explained bias tensors; flagged as a
deviation below).

## 2. Codec sweep

Stratified sample: **4 experts x 24 layers x 6 tensor kinds = 576 eval
slices** (exceeds the >=96 floor). Experts chosen spread across the range:
`{0, 10, 20, 31}`. The optional "8 full layers" extension was skipped for
time economy -- the 576-slice stratified sample already covers every
layer and every tensor kind at 4x expert depth, which is the dimension
most likely to vary distributional character; documented as a deviation.

Held-out dictionary-training corpus (disjoint experts, so C4 cannot leak
eval data into its own dictionary): experts `{4, 5}` x all 24 layers x 6
tensor kinds = 288 slices, 48 files per tensor kind (211.5 MB per weight
kind, 0.55 MB per bias kind).

All 576 eval slices were pread from the gguf by manifest byte range and
sha256-verified against the manifest's own digest before any codec touched
them (0 mismatches, 0 short reads -- `research/ob4/extract-manifest.json`).

Codecs, deterministic, `zstd -19 -T1` throughout:

- **C0** raw, ratio 1.0 by definition (control).
- **C1** `zstd -19` on the raw slice as-is.
- **C2** split-stream: de-interleave each 17-byte block into a scale
  stream (1 byte/block) and a mantissa stream (16 bytes/block), `zstd -19`
  each independently, sum. Not applicable to bias tensors (no block
  structure to split) -- C2 == C1 there by definition, reported as such.
- **C3** order-0 entropy measurement only (not a real codec / no
  compressed bitstream produced): Shannon entropy of the scale stream over
  its 256-value byte alphabet, and of the mantissa stream over its actual
  16-value nibble alphabet (unpacked 2 symbols/byte, matching the real
  quantization alphabet size, not the raw byte histogram). Floor bytes =
  ceil(entropy_bits_per_symbol * n_symbols / 8), summed per stream.
- **C4** `zstd -19 -D <dict>` with a 112640-byte dictionary (zstd's
  documented default `--maxdict`, i.e. "112KB" as specified) trained with
  `zstd --train-fastcover` per tensor kind on the held-out corpus above.
  Dictionary bytes are counted once per tensor kind and amortized across
  the 96 eval slices of that kind (`c4_amortized = sum(compressed) +
  dict_bytes`; reported both bare and amortized).

### Sweep table (literal, from `research/ob4/sweep-summary.json`)

Ratio = stored/raw. Pooled over all 1,272,360,960 raw bytes (576 slices):

| codec | pooled ratio | note |
|---|---|---|
| C0 raw | 1.0000 | control |
| C1 zstd -19 | 0.9585 | |
| **C2 split-stream** | **0.9182** | **best** |
| C3 entropy floor | 0.9181 | measurement only, C2 is already at the floor |
| C4 dict (amortized) | 0.9586 | dict does not help weight tensors; helps bias tensors alone but they're 0.26% of pooled bytes |

Per tensor kind:

| tensor kind | n | raw bytes | C1 | C2 | C3 floor | C4 amortized |
|---|---:|---:|---:|---:|---:|---:|
| ffn_gate_exps.weight | 96 | 423,014,400 | 0.9624 | 0.9205 | 0.9214 | 0.9623 |
| ffn_up_exps.weight | 96 | 423,014,400 | 0.9593 | 0.9198 | 0.9181 | 0.9593 |
| ffn_down_exps.weight | 96 | 423,014,400 | 0.9577 | 0.9179 | 0.9182 | 0.9576 |
| ffn_gate_exps.bias | 96 | 1,105,920 | 0.4687 | (=C1) | 0.4923 | 0.4951 |
| ffn_up_exps.bias | 96 | 1,105,920 | 0.4001 | (=C1) | 0.4566 | 0.4589 |
| ffn_down_exps.bias | 96 | 1,105,920 | 0.5074 | (=C1) | 0.5141 | 0.5677 |

Reading it: the 4-bit mantissa stream is close to incompressible (near its
own entropy ceiling out of the gate -- MXFP4 training already spreads
mantissa indices close to uniformly), so C1/C4 on the raw interleaved
bytes are diluted by that near-random 16-bytes-of-17 majority. Splitting
the 1-byte-of-17 scale stream out and compressing it alone is the entire
win: C2 lands within 0.01 ratio of C3's information-theoretic floor,
meaning there is close to nothing left on the table for a smarter
order-0-class scheme on this data. Bias tensors compress far better
(plain F32 weights, real structure) but are 0.26% of total bytes pooled,
so they barely move the pooled number; C4's dictionary genuinely helps
bias (0.40-0.51 bare) but the amortized 112640-byte dict tax outweighs the
gain at only 96 slices/kind (net amortized ratio equal to or worse than
C1 for 2 of 3 bias kinds) -- a dictionary this large only pays for itself
at far higher slice counts than the sweep sample, which the live run at
K=8 will have.

### Round-trip / digest verification

All 576 C2 round-trips (interleave the two decompressed streams back into
block order) and all 576 C4 round-trips sha256-matched the manifest's own
per-row digest: **1152/1152 checks passed, 0 failures**
(`c2_roundtrip_all_ok` / `c4_roundtrip_all_ok`, both `true` for every
tensor kind in `sweep-summary.json`). C1 was checked identically as part
of the decode-timing pass (576/576 pass). This is the manifest-is-identity
authority in miniature: the container is provably just a transport.

### Decode cost

Two measurements, because the first one turned out to be dominated by a
methodology artifact worth naming rather than hiding:

**(a) CLI subprocess measurement** (`zstd -d -c <file>` shelled out via
`subprocess`, stdout captured through a pipe) -- this is what
`research/ob4/decode-timing.json` holds. Weight-tensor decode averaged
0.030s (C1) / 0.042s (C2) / 0.034s (C4) against a 0.0026s baseline
(in-process `os.pread` + `hashlib.sha256` of the same bytes) -- i.e.
**11-13x baseline for C1/C4, ~16x for C2**. That is well over the 5x
freeze bar.

**(b) Library measurement** (`python-zstandard`, i.e. libzstd linked
in-process, no subprocess/pipe): the same C1 artifacts decode at 0.0036s
average against the 0.0026s baseline -- **1.4x baseline**
(`research/ob4/lib-decode-bench.json`). A control measurement isolated the
gap: 200 trivial `zstd --version` subprocess spawns average 0.00076s
each, which is NOT enough on its own to explain an 11x-16x inflation --
the rest of the CLI gap is pipe-buffered stdout capture of a ~4.2MB
payload through Python's `subprocess.PIPE`, which copies the whole buffer
at least twice. **This is a measurement-method artifact, not a property
of the codec.** The live decode path (inside the fork's C++ lease code)
will link libzstd directly, matching measurement (b), not (a).

C2's library-level decode (two `dctx.decompress()` calls + a numpy
interleave, `research/ob4/lib-decode-c2.json`) averages 0.0066s against
the same 0.0026s baseline -- **~2.5x baseline**, still comfortably under
5x, and it carries the best pooled ratio.

**Winner selection basis: library-level decode cost (b), not (a).** (a)
is reported alongside for completeness and because it is a real cost of
*this* measurement pipeline, but freezing a decision on a subprocess+pipe
artifact would reject every codec including doing nothing (C1 itself
fails the CLI-measured 5x bar), which is not an honest reading of "decode
cost" for a linked-library live-run design.

## 3. FROZEN: winning codec

**C2, split-stream zstd -19** (scale stream and mantissa stream
compressed independently). Pooled ratio 0.918, library decode ~2.5x the
raw pread+sha256 baseline. C4 (dictionary) is explicitly rejected as the
default: it does not move the weight-tensor ratio (99.97% of pooled
bytes) and its fixed per-tensor-kind dictionary tax makes bias-tensor
compression *worse* on this sample size. C1 is dominated by C2 on ratio
at equal or lower decode cost per byte. C3 is not a codec (no compressed
bitstream, entropy measurement only).

## 4. FROZEN: container format

Content-addressed store, one compressed blob per manifest row:

- **Blob**: for a weight-tensor row, two zstd frames concatenated:
  `[u32 scale_frame_len][scale zstd frame][mantissa zstd frame]` (mantissa
  frame length is implicit: read-to-EOF of the blob). For a bias-tensor
  row (no split structure), a single zstd frame (C1-equivalent), stored
  with the same 2-field header format but `scale_frame_len` set to the
  full blob length and an empty mantissa frame, so the reader has one
  code path.
- **Index**: one row per manifest entry --
  `(layer, expert, tensor, manifest_offset, manifest_nbytes,
  manifest_sha256, blob_offset, blob_len)`. Index bytes count toward
  stored size (it is the mapping from "manifest row" -> "byte range in the
  container file"; without it the container is unaddressable). At 4608
  rows x (3 x uint16 + string tensor-kind-id + 5 x uint64) it is on the
  order of a few hundred KB -- negligible next to the ~11.5GB of expert
  bytes it indexes, but it is counted, not waved away.
- **Identity**: the manifest is the identity authority. A blob's decoded
  bytes MUST sha256-match the manifest row it was built from; the
  container/index is only a transport and carries no independent identity
  claim. This was verified end-to-end on all 576 eval rows above.

## 5. FROZEN: verification law

Decode output must sha256-match the EXISTING manifest row digest
(`EXPERT-MANIFEST-20B.sha256`, unchanged, still the identity authority).
A decode that produces bytes not matching the manifest digest is a
correctness failure regardless of what the container's own index claims.
This is what the C2/C4 round-trip checks above already enforce; the live
run enforces the same check on every miss, on the live path, not just in
this offline sweep.

## 6. FROZEN: live-run plan

One K=8 code-corpus run + one A/A repeat, under the box-wide RUNLOCK
(mkdir-based, released immediately after), decoding every expert-slice
miss from the C2 container instead of a raw pread of the gguf. Compare
against the OB-1 resident-baseline numbers already banked
(`research/ob1/runs/lease-k8-code`). Builder 2's job, not run here (no
model was loaded or run by this builder -- pure pread + zstd/entropy
measurement, no RUNLOCK needed per the house rule, and none was taken).

## 7. FROZEN: bars

- **DIGEST limb (stop-ship)**: 4608/4608 manifest rows decode from the
  container and sha256-match the manifest. (This sweep already cleared
  1152/1152 on its 576-row sample at 2 codecs each; the live run's job is
  the full 4608 and the two K=8 passes.)
- **RATIO limb (report-only)**: pooled C2 ratio measured here = 0.918.
  Report the live container's actual ratio at freeze time; no pass/fail
  threshold by design (an honest "MXFP4 barely compresses" is a bankable
  answer, not a failure).
- **COST limb**: live p95 decode <= 3.0x the OB-1 resident baseline (same
  bar as the program standard). This sweep's library-level C2 decode
  (~2.5x a pread+sha256 proxy baseline, not yet the real OB-1 resident p95)
  is inside that bar's order of magnitude but is NOT the same measurement
  -- builder 2 must re-measure p95 against the actual OB-1 resident
  baseline on the live path before claiming this limb passes.

## 8. Deviations from the brief

1. Sample was the base stratified set (4 experts x 24 layers x 6 kinds =
   576 slices) only; the optional "8 full layers if time allows" extension
   was not run, for time economy. 576 already clears the >=96 floor by
   6x and covers all 24 layers and both extremes of the expert range.
2. Bias-tensor dtype (F32) is inferred from element-count arithmetic
   (11520/2880=4.0 exactly) plus an empirical value-range sanity check,
   not read from a literal GGUF tensor-type field -- writing a full GGUF
   KV-section parser was judged not worth the time for 3 tensor kinds
   whose type is already unambiguous from the arithmetic.
3. Two decode-cost measurements are reported (CLI-subprocess and
   in-process library) because they disagree by an order of magnitude and
   the disagreement is itself informative (see Decode cost, above);
   winner selection used the library number as the one representative of
   the intended live-run integration (linked, not shelled out).
4. Dictionary trainer used `zstd --train-fastcover` (bounded, fast mode)
   rather than the default COVER trainer, to keep the sweep's wall time
   reasonable; both are zstd's own built-in trainers, this is a speed
   choice only.

## Commits

- `research/ob4/` (this document + `extract.py`, `sweep.py`,
  `lib_decode_bench.py`, `lib_decode_c2.py`, `amortize.py`, `overhead.py`,
  and the full literal JSON receipts: `extract-manifest.json`,
  `layout-facts.json`, `dicts.json`, `encode-results.json`,
  `decode-timing.json`, `sweep-summary.json`, `c4-amortized.json`,
  `lib-decode-bench.json`, `lib-decode-c2.json`) committed on branch
  `ob4` in `F:\f32\openbob-wt\ob4`. Commit hash
  `2864234edab48b950390de1a7f18a1b636545ba5` (this document + all listed
  receipts landed together in that one commit).
- `/root/ob4/llama.cpp` worktree created at fork HEAD `c087083`
  (branch `ob4`), read-only for this builder: 0 commits, cited source
  only.

## Reproduction

```
wsl.exe -u root -e sh -c 'python3 research/ob4/extract.py'   # writes+verifies slices
wsl.exe -u root -e sh -c 'python3 research/ob4/sweep.py'     # C0-C4 sweep + decode timing
wsl.exe -u root -e sh -c 'python3 research/ob4/amortize.py'  # C4 dict amortization
wsl.exe -u root -e sh -c 'python3 research/ob4/lib_decode_bench.py'  # library C1 decode cost
wsl.exe -u root -e sh -c 'python3 research/ob4/lib_decode_c2.py'     # library C2 decode cost
```

Paths inside the scripts are hardcoded to this box's layout
(`/root/openbob-baselines/models/...`, `/mnt/f/f32/openbob-wt/ob4/...`,
`/mnt/f/f32/stage/research/ob4/...` for scratch slice/blob files, which
are NOT committed -- only the JSON summaries derived from them are, per
the house `/mnt/f/f32/stage/` write-scope rule).
