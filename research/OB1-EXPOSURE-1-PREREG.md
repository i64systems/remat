# OB1-EXPOSURE-1-PREREG: BOUNDED EXPERT RESIDENCY ON PRETRAINED GPT-OSS-20B,
# FROZEN BEFORE THE LEASED-RESIDENCY INSTRUMENT EXISTS

Lane: research (CUDA/inventor lane), venue hyde, on-machine. Branch
research-2, worktree F:\f32\openbob-wt\research-2. Builder 1 of OB-1
(prereg + baseline + manifest). Pure ASCII, no em dashes. Every number
below is literal command output from this leg's own script runs, or is
quoted verbatim from a cited file. This document is committed before the
leased-residency (bounded-expert-set) instrument is written by any later
leg; nothing below is renegotiated after that instrument exists except
where explicitly named as a deviation in section 8.

Substrate at prereg time: worktree HEAD 4bbf260128456502b2e4b574dbca0a1ef22cc344,
branch research-2, `git status --porcelain` empty except this file being
added.

## 0. WHAT THIS PROGRAM IS, IN ONE PARAGRAPH

gpt-oss-20b is a mixture-of-experts (MoE) language model: 24 transformer
layers, each with 32 "expert" feed-forward sub-networks, of which only 4
are actually used per token per layer (a "top-4 router" picks which 4,
per token, per layer, from the token's own hidden state -- this is a
property of the pretrained weights, not something OB-1 changes). Keeping
all 32 experts at every layer loaded in fast memory at once is wasteful if
usage is skewed: RS053 (research/RS053-GPTOSS-LOCALITY-1.md, the direct
predecessor to this leg) already measured that gpt-oss-20b's real,
pretrained router usage IS skewed (not uniform across the 32 experts per
layer). OB-1 asks a follow-on, more concrete question: if you keep only
the K most-used experts per layer warm ("resident") and fetch any other
expert from local disk (NVMe) on demand when a token actually needs it
("cold", loaded into one reusable scratch buffer, verified against a
digest, then usable), does the model's output stay EXACTLY the same as
keeping every expert warm all the time, and how much fast-memory
("capacity exposure") does that buy you? This document is the prereg for
that question: architecture facts, the residency policy definition, the
K sweep, the acceptance corpora, the frozen bars, and a banked baseline
(the always-fully-resident case) to compare a later "leased" instrument
against.

## 1. ARCHITECTURE FACTS (carried forward from RS053, re-cited)

gpt-oss-20b, from RS053-GPTOSS-LOCALITY-1-PREREG.md section 1 (that
document's own two-source cross-check: the house's v11 prompt doc AND a
direct GGUF metadata read, MATCH on every field), re-verified independently
by this leg's own GGUF tensor-info reader (section 2 below, which reads a
DIFFERENT section of the file -- tensor-info, not KV-metadata -- so this is
a genuine second independent read, not a repeat of the same parse):

  L (layers)              = 24
  E (experts per layer)   = 32
  k (experts used/token)  = 4
  h (hidden/embed dim)    = 2880
  attention heads / kv    = 64 / 8
  expert_feed_forward_len = 2880

Model file: /root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf,
sha256 27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901
(registry-verified 2026-08-31, per this leg's task brief; RS053's own
independent sha256sum run on 2026-08-31 got the same digest, section 2
of RS053-GPTOSS-LOCALITY-1-PREREG.md).

## 2. EXPERT DIGEST MANIFEST (task step 1, DONE)

Tool: research/ob1/gguf_expert_manifest.py (stdlib only: struct, hashlib,
no third-party gguf/torch dependency). It reads the GGUF header and
tensor-info section (magic + version + kv-count + kv pairs, then the
tensor list of name/dims/type/offset), the same parsing method RS053
builder 3's research/rs053/gguf-expert-bytes.py already validated
(RUNLOG-1.txt section 5), extended here to per-expert byte ranges + sha256
(gguf-expert-bytes.py stopped at per-tensor and per-layer totals; it did
not hash anything).

GGUF LAYOUT FACT, gpt-oss-20b: each of the 6 "fused expert" tensors per
layer (ffn_gate_exps.weight, ffn_up_exps.weight, ffn_down_exps.weight,
ffn_gate_exps.bias, ffn_up_exps.bias, ffn_down_exps.bias) holds ALL 32
experts' data in ONE tensor, not one tensor per expert. The expert axis is
the GGUF dims' outermost (slowest-varying) index (weight tensor dims listed
as (2880, 2880, 32)), so expert e's bytes are the contiguous slice
[e * per_expert, (e+1) * per_expert) of that tensor's byte span, where
per_expert = tensor_byte_span / 32. The tool VERIFIES tensor_byte_span is
exactly divisible by 32 for every one of the 144 expert tensors (24 layers
x 6 suffixes) before trusting this division, and additionally verifies
every layer's total expert bytes (summed over the 6 suffixes) are IDENTICAL
across all 24 layers -- both checks passed, no SystemExit raised.

PACKING ASSUMPTION, STATED PLAINLY (not independently verified against a
second, ground-truth expert-extraction tool in this leg; carried forward
as a design law, not a proven fact beyond the two checks above): this is
the standard llama.cpp / GGML convention for MoE expert-parallel tensors
(get_rows-style indexing along the outermost axis selects one expert's
contiguous byte range); it is the same convention research/rs053's own
gguf-expert-bytes.py relied on to report PER_EXPERT_BYTES_PER_LAYER, and
this leg's independent computation of that same number (below) matches
RS053's banked value exactly, which is the closest thing to an
independent confirmation available without a second, unrelated GGUF
reader implementation.

MANIFEST OUTPUT, literal (research/ob1/EXPERT-MANIFEST-20B.sha256, one
row per layer x expert x tensor-suffix, columns layer,expert,tensor,
offset,nbytes,sha256):

  ROW_COUNT              = 4608   (24 layers x 32 experts x 6 tensor suffixes)
  PER_EXPERT_BYTES_PER_LAYER = 13253760
      (one expert's combined bytes across all 6 suffixes: 3 x 4406400
      MXFP4-quantized weight bytes + 3 x 11520 F32 bias bytes)
  TOTAL_EXPERT_BYTES     = 10178887680   (= 24 layers x 32 experts x 13253760)
  TOTAL_MODEL_BYTES      = 12109566624   (the GGUF file's own byte size)
  gguf_data_start         = 13008288   (header + tensor-info section length,
                                        rounded up to the 32-byte alignment)
  ELAPSED_SECONDS         = 10.814   (this run; a second run measured
                                      19.857s including page-cache-cold
                                      first reads -- both runs' manifest
                                      file content were not diffed since
                                      the fix-and-rerun below changed only
                                      print labels, not row content; see
                                      deviation 1)

CROSS-CHECK: TOTAL_EXPERT_BYTES and PER_EXPERT_BYTES_PER_LAYER computed
here independently MATCH RS053's own banked numbers exactly
(research/rs053/RUNLOG-1.txt section 5: PER_EXPERT_BYTES_PER_LAYER=13253760,
TOTAL_EXPERT_TENSOR_BYTES=10178887680 for the 20b model). Two independent
tools (RS053's gguf-expert-bytes.py, this leg's gguf_expert_manifest.py),
same file, same numbers.

DERIVED CONSTANT USED BELOW: resident_always_bytes (the bytes that must be
mapped regardless of K -- everything that is NOT a per-layer fused expert
tensor: embeddings, attention weights, layer norms, the GGUF header and
tensor-info section itself) = TOTAL_MODEL_BYTES - TOTAL_EXPERT_BYTES =
12109566624 - 10178887680 = 1930678944.

Sample rows (first and last, verbatim from the manifest file):
  0,0,ffn_gate_exps.weight,1413665184,4406400,178373dffcca0561bfcdedb1592f4bc2e679bd10746a78bba1481167bd1a9223
  23,31,ffn_down_exps.bias,11685423136,11520,bd25930f8546807f23793316f2284ef2f24b36ccc35614443d9a0a4487a156b0

Commit: 65f52119c1589aafce24c1e29068a95e4e70c740 (tool + manifest).

## 3. RESIDENT SETS (task step 2, DONE)

Tool: research/ob1/resident_sets.py. Reads ONE route log -- RS053's own
20b-prose-a run only (per-token, per-layer record of which 4 experts the
pretrained router picked) -- computes per-layer usage counts c_l(e) using
the SAME loader RS053 builder 3 used (research/rs053/rs053-metrics.py
load_route_log: the log is grouped by ubatch not by layer, so each layer's
token-ordered sequence is rebuilt with a boolean mask over the layer
column and VERIFIED to cover token_index 0..budget-1 in order before being
trusted), then for K in {16, 8, 4} takes the top-K experts per layer by
usage count, ties broken by LOWER EXPERT ID (RS053's own tie-break
convention, prereg section 5.0 / deviation 2).

RANKING CORPUS, STATED PER THE HONESTY LAW: ranks come from the PROSE
route log ONLY (/mnt/f/f32/stage/research/rs053/runs/20b-prose-a/route.log,
sha256 a0bb972ec5a02e18ab685000c72b512751e579e243deecc3c095d8340c4b50aa --
this leg's own independent sha256sum of the file, MATCHES RS053's own
recorded digest in stage/research/rs053/SHA256SUMS-route-logs.txt line
for runs/20b-prose-a/route.log). This route log's tokens are 65536
positions from RS053's corpus-prose.txt (enwik8 bytes [95000000,
95262144)), which is NEVER the same byte range as this leg's own
acceptance corpus AC-PROSE (enwik8 bytes [96000000, 96262144), section 4).
The RS053 code route log (20b-code-a) is NOT used for ranking anywhere in
this leg.

RESULT, literal (research/ob1/RESIDENT-SETS.json):

  E=32 L=24 budget=65536, tie_break=lower expert id

  K=16  resident_expert_pool_bytes = 5089443840   (16 x 24 x 13253760)
  K=8   resident_expert_pool_bytes = 2544721920   (8  x 24 x 13253760)
  K=4   resident_expert_pool_bytes = 1272360960   (4  x 24 x 13253760)

The JSON also carries the full L x E usage histogram (histogram_c_l_e)
and, per K, the frozen per-layer expert-id list (resident_sets["16"]["0"]
etc, ascending expert id).

Commit: 98b5a71de98da34b57be6af59966ded21c7b1d3a (tool + RESIDENT-SETS.json).

## 4. ACCEPTANCE CORPORA (task step 3, DONE)

Tool: research/ob1/extract_corpora.py.

DIFFERENT-SLICE LAW: the ranking corpus (section 3) and both acceptance
corpora below are disjoint byte ranges / disjoint files, so no acceptance
text was ever seen by the ranking pass.

AC-PROSE: enwik8 bytes [96000000, 96262144) (262144 bytes), extracted by a
stdlib-only Python offset-seek + fixed-length read (no transform) from
/mnt/f/f32/stage/lowint/data/enwik8/enwik8 (a read-only staged asset of the
low-int lane; this leg only reads it). This is a DIFFERENT 262144-byte
slice of the same underlying enwik8 file than RS053's own prose corpus
([95000000, 95262144), the source of the section-3 ranking route log) --
adjacent-ish but non-overlapping (95262144 < 96000000, a 737856-byte gap
between them).

  Written to: /mnt/f/f32/stage/research/ob1/AC-PROSE.txt (off-repo)
  bytes: 262144 (literal, matches the slice length by construction)
  sha256: 310710a1f3e04484fcef2d0cb4ac1de93a8a6e02ced07ed3f2c9b79505e81a8e

AC-CODE: the RS053 code corpus, copied byte-exact (verbatim, per the task
brief) from /mnt/f/f32/stage/research/rs053/corpus-code.txt. This corpus
was NEVER used for ranking (section 3 used the prose route log only), so
reusing it verbatim here does not leak ranking information into the
acceptance test.

  Written to: /mnt/f/f32/stage/research/ob1/AC-CODE.txt (off-repo)
  bytes: 1576144 (literal, matches the source file's own size)
  sha256: d2db5c682d5f52a4383d188fee9d25f592a15d69763dbf886b5614c953e7f3fc
  (MATCHES the task brief's own stated digest for this file exactly.)

TOKEN BUDGET: 32768 tokens per corpus, FROZEN NOW. TRUNCATION RULE: the
baseline run (section 5) invokes llama-perplexity with --ctx-size 1024
--chunks 32 (1024 x 32 = 32768 exactly), which requires the corpus to
tokenize to AT LEAST 32768 tokens or the tool exits with an explicit "not
enough tokens" error; neither run hit that error (both completed, exit
code 0 on all four runs, section 5), which is the tool's own confirmation
that both corpora tokenize to >= 32768 tokens under gpt-oss's tokenizer.
The exact total tokenized length of each corpus beyond that threshold was
NOT separately measured (llama-perplexity does not print a bare token
count, only a tokenization-time-in-ms line); this is not needed for the
frozen rule, which only requires knowing whether the budget was met (it
was, on both corpora) or fell short (it did not). Actual tokens
EVALUATED, cross-verified independently from each run's own route.log
line count (786432 lines = 24 layers x 32768 token positions, matching on
all 4 runs, section 5): 32768 on every run, the full frozen budget, no
corpus fell short.

Commit: 4bbf260128456502b2e4b574dbca0a1ef22cc344 (extraction tool; the
corpus bytes themselves are off-repo per house rule, digests above are
the in-repo record).

## 5. BASELINE: FULLY-RESIDENT FORWARD, A/A, BOTH CORPORA (task step 4, DONE)

Tool: research/ob1/run.sh (baseline run driver) + research/ob1/runs-all.sh
(the four invocations, in order). Binary: /root/rs053/llama.cpp/build/bin/
llama-perplexity, the SAME instrumented build RS053 already used and
route-log-A/A-verified (RS053 RUNLOG-1.txt: llama.cpp fork, upstream
commit ca3d5a3, route-log patch applied; this leg did not rebuild it).
Route log ON via the LLAMA_ROUTE_LOG environment variable (same mechanism
RS053 used).

INVOCATION SHAPE: --ctx-size 1024 --chunks 32 -b 1024 -ub 1024 --threads
10 --threads-batch 10 --no-warmup --seed 1 -ngl 99, nice 10. This
ctx-size/batch-size relationship (n_batch == n_ctx, both 1024) keeps
llama-perplexity's internal sequence count n_seq at 1, the same safe
shape RS053's own runs used (their ctx=4096 > batch=2048 also gives
n_seq=1); this was chosen deliberately after checking llama.cpp's
batching assertions in tools/perplexity/perplexity.cpp, not found by
trial and error. -ngl 99 offloads all layers to GPU (GPU is available to
this lane per the house rules; RS053 used the same flag for its own
20b/120b runs).

IDENTITY ARTIFACT, DEFINED (per the task's instruction to pick the
strongest byte-comparable artifact the tool emits and name it here):

  CONSIDERED AND REJECTED: llama-perplexity's --save-all-logits /
  --kl-divergence-base flag, which dumps a per-token, near-full-vocabulary
  log-probability array to a binary file (source: tools/perplexity/
  perplexity.cpp, log_probs.resize(n_ctx * (2*((n_vocab+1)/2)+4)) as
  uint16 per value). With n_vocab approximately 201088 (the 120b geometry
  card's vocab figure, section 1 cross-reference; this leg did not
  re-derive 20b's exact vocab size since the file-size estimate below
  already makes the decision clear either way) and 32768 tokens, this file
  would be on the order of 32768 x 201092 x 2 bytes = approximately 13.2
  GB PER RUN. Across 2 corpora x 2 (A/A) for the baseline alone, and again
  at every K for a later leased instrument, this is impractical under this
  leg's disk and I/O budget, and unnecessary: the OB-1 residency design
  (section 6) computes the EXACT SAME forward math on a cold-loaded expert
  as on a resident one (a miss is a disk fetch, not an approximation), so
  the identity claim does not need full-vocabulary logit-level resolution
  to be checkable -- any real computation divergence would still perturb
  the artifact chosen below.

  CHOSEN: the tool's own comma-separated per-chunk perplexity list
  (source: perplexity.cpp, LOG("[%d]%.4lf,", i+1, exp(nll/count)) at
  --ppl-output-type 0, the default), one value per --ctx-size-token chunk,
  32 values per run at this budget/ctx-size. This is the "perplexity
  chunk output" option the task brief named.

  A/A INVESTIGATION, NAMED AS A FINDING (not a silent fix): this leg's
  first A/A pass compared the FULL raw stdout capture and found prose-a
  and prose-b differed by exactly one line: a wall-clock preamble
  ("0.30 minutes" vs "0.25 minutes", printed by a plain LOG() call, not
  LOG_INF, so it lands in stdout rather than stderr) -- NOT the perplexity
  values themselves, which were already byte-identical beneath that line
  on inspection (code-a vs code-b happened to print the same rounded
  minutes value by coincidence and so did not surface this on the first
  pair checked). The identity artifact is therefore redefined as ONLY the
  line beginning "[1]" (the per-chunk PPL list, with the nondeterministic
  timing preamble excluded), extracted by `grep '^\[1\]'`. research/ob1/
  run.sh was updated to produce this as identity.txt directly for any
  later leg reusing this driver. This is recorded as deviation 2 in
  section 8, not silently absorbed.

FOUR RUNS, EACH EXECUTED ONCE (an A/A PAIR per corpus, 4 executions total,
matching the task's "run ... TWICE each (A/A)" instruction):

  label     corpus     tokens  wallclock_s   exit  route_log_sha256 (24x32768=786432 lines, every run)
  prose-a   AC-PROSE   32768   11.474663389  0     a29fe23fad3425135a9f943144a7d156ef39f0e7da1ae663281e3ff0e75048fd
  prose-b   AC-PROSE   32768   10.427532740  0     a29fe23fad3425135a9f943144a7d156ef39f0e7da1ae663281e3ff0e75048fd
  code-a    AC-CODE    32768    9.708499632  0     5fa42a1c135b2eb5571a8487636205ac943853a3345a2e990b64430d05d01805
  code-b    AC-CODE    32768   10.183602254  0     5fa42a1c135b2eb5571a8487636205ac943853a3345a2e990b64430d05d01805

  label     identity.txt sha256 (the redefined artifact, section 5 above)          bytes  Final PPL (stderr, both runs of a pair agree)
  prose-a   f120af4f8bef225154a47e314aaba4a726fef5d77ce220937ca8f0b9af5b770f        408    236.7280 +/- 5.93411
  prose-b   f120af4f8bef225154a47e314aaba4a726fef5d77ce220937ca8f0b9af5b770f        408    236.7280 +/- 5.93411
  code-a    bbe0f9dcd54629758d79437e47e10e68e6d9c48ccf6ec4182c86578de921560e        345    4.2771 +/- 0.08489
  code-b    bbe0f9dcd54629758d79437e47e10e68e6d9c48ccf6ec4182c86578de921560e        345    4.2771 +/- 0.08489

A/A VERDICT: BOTH route.log (routing/expert-selection identity, the same
check RS053's G1 does) AND identity.txt (the perplexity-chunk identity
artifact, after the timing-line fix) are BYTE-IDENTICAL within each pair,
on both corpora. No divergence found; nothing to stop and report per the
task's "if not, stop and report" instruction.

TIMING, literal, no p95 available (see deviation 3): wallclock_s per run
in the table above (each run's own `date +%s.%N` delta around the whole
process, mirroring RS053's run.sh method); /usr/bin/time -v Maximum
resident set size was 12202308-12203976 kbytes across the four runs
(approximately 11.9 GB, essentially the whole model resident, expected
for this baseline). llama-perplexity printed one coarse rate estimate per
run ("X seconds per pass", an early ETA figure computed from partial
progress, not a per-token or per-chunk time series): 0.59s, 0.49s, 0.56s,
0.59s for prose-a, prose-b, code-a, code-b respectively. Average ms/token
derived from total wallclock_s / 32768: prose-a 0.3502, prose-b 0.3183,
code-a 0.2963, code-b 0.3108.

Commit: this leg's baseline run scripts are the same commit as section 4
(4bbf260128456502b2e4b574dbca0a1ef22cc344); the run OUTPUTS (route.log,
stdout.txt, identity.txt per run) are off-repo at
/mnt/f/f32/stage/research/ob1/runs/<label>/, digests recorded in this
document.

## 6. THE RESIDENCY POLICY (design law, restated for this document's
metric definitions)

STATIC, popularity-ranked per-layer resident expert set (section 3),
chosen ONCE from the prose ranking route log, never updated during a run
(no LRU, no cache-state dependence -- this is what makes replay byte-exact
by construction: which experts are warm at any point in a run is a pure
function of the frozen K and layer, never of run history). Plus ONE
deterministic scratch slot: a single reusable buffer, sized to hold
exactly one layer's one expert (PER_EXPERT_BYTES_PER_LAYER = 13253760
bytes, section 2), into which a cold (non-resident) expert is loaded from
NVMe, sha256-verified against the manifest (section 2) row for that
(layer, expert), used for that token's forward computation, then
discarded (the buffer is reused for the next miss, whether at the same
layer or a later one). Because the scratch slot always holds a
manifest-verified, byte-correct copy of the actual expert the router
selected (never an approximation, never a different expert), the
computation performed is IDENTICAL whether an expert happens to be
resident or was just cold-loaded -- which is the basis for the identity
limb's frozen bar in section 7 (byte-identical output is the EXPECTED
result of a correct implementation, not a hoped-for one; a mismatch would
indicate an implementation bug, not an approximation trade-off).

## 7. THE EXPOSURE METRIC, EXACT FORMULA (frozen now)

CAPACITY EXPOSURE = logical parameter bytes on disk / peak fast-resident
bytes (the ratified metric, per house law; measured, never claimed as a
verdict by itself).

  LOGICAL = TOTAL_MODEL_BYTES (section 2) = 12109566624

  RESIDENT(K) = resident_always_bytes + resident_expert_pool_bytes(K) + SCRATCH_BYTES

    resident_always_bytes = TOTAL_MODEL_BYTES - TOTAL_EXPERT_BYTES
                           = 12109566624 - 10178887680 = 1930678944
      (everything that is not a per-layer fused expert tensor: embeddings,
      attention weights, layer norms, and the GGUF header/tensor-info
      section itself -- always mapped, at every K, per the design law.)

    resident_expert_pool_bytes(K) = K x L x PER_EXPERT_BYTES_PER_LAYER
                                   = K x 24 x 13253760   (section 3 JSON)
      K=16: 5089443840   K=8: 2544721920   K=4: 1272360960

    SCRATCH_BYTES = PER_EXPERT_BYTES_PER_LAYER = 13253760
      (one deterministic scratch slot, section 6)

  EXPOSURE(K) = LOGICAL / RESIDENT(K)

ILLUSTRATIVE NUMBERS (computed today from the manifest and resident-set
figures above; NOT a claim about a running system, since no leased
instrument exists yet -- section 0's "measurement, not a verdict"
discipline applies here exactly as it did in RS053):

  K   RESIDENT(K)   EXPOSURE(K)
  16  7033376544    1.721729
  8   4488654624    2.697817
  4   3216293664    3.765069

## 8. THE FROZEN BARS (no instrument exists yet; these bind whoever
builds the leased-residency instrument next)

IDENTITY LIMB: at every K in {16, 8, 4}, on BOTH acceptance corpora
(AC-PROSE, AC-CODE), the leased run's identity.txt (section 5's artifact
definition: the `grep '^\[1\]'` line of llama-perplexity's stdout, i.e.
the per-chunk PPL list at --ppl-output-type 0 with the given ctx-size/
chunks) MUST be byte-identical (sha256 match) to this document's baseline
identity.txt for that corpus (prose:
f120af4f8bef225154a47e314aaba4a726fef5d77ce220937ca8f0b9af5b770f, code:
bbe0f9dcd54629758d79437e47e10e68e6d9c48ccf6ec4182c86578de921560e). Per
section 6, this is expected to PASS at every K by design (the scratch
slot always loads the exact, verified expert), so a failure here is a
correctness bug in the leased implementation, not evidence of a
performance/accuracy trade-off.

EXPOSURE LIMB: report-only, no pass/fail (per house measurement-language
law). The instrument reports the measured RESIDENT(K)/EXPOSURE(K) it
actually achieved (its own peak fast-resident byte count, not assumed
from section 7's illustrative arithmetic) at every K, on both corpora.

COST LIMB: leased p95 latency <= 3.0x baseline p95 latency, AT K=16, is
the frozen number from the task brief. DEVIATION NAMED (see section 8
below, deviation 3): llama-perplexity, the baseline tool, does not emit a
per-token or per-chunk timing SERIES -- only a total wallclock figure and
one coarse early-ETA "seconds per pass" estimate (section 5) -- so no
p95 baseline figure exists to compare against yet. This document freezes
the BAR (<= 3.0x at K=16) and the BASELINE WALLCLOCK figures (section 5)
as what exists today; it is the leased-instrument-building leg's
responsibility to either (a) instrument per-token or per-chunk
timestamps itself (the leased instrument necessarily differs from plain
llama-perplexity -- it must intercept expert loads -- so it is better
positioned to add timing hooks than this leg was), and compare its own
p95 against a rerun of this leg's baseline WITH THE SAME timing
instrumentation added symmetrically, or (b) report average latency
(wallclock/tokens, section 5's numbers: 0.2963-0.3502 ms/token across the
four baseline runs) in place of p95 with that substitution explicitly
named, per the same deviation-naming discipline used throughout this
document. At K=8 and K=4, cost is report-only (no bar), matching the task
brief.

## 9. WALLS AND SCOPE (per the house rules handed to this builder)

CPU: at most 12 threads under nice 10 for any heavy run (this leg used
10, matching RS053's own convention, within the wall). At least 4 GB WSL
RAM free at all times (not separately re-verified per run by this leg
beyond the /usr/bin/time -v peak RSS figures in section 5, which stayed
well under the 24 GB WSL RAM ceiling with the baseline's ~11.9 GB peak;
the box reported 16106 MB free / 23127 MB available before this leg's
work began, per a `free -m` check at the start of the session). GPU
available and used (-ngl 99), leaving the approximately 1.2 GB already
resident on the card alone (this leg never queried or touched that
process). Never touched, signaled, reniced, or killed: pid 654 (openbob
serve), searxng pid 489, or any wsl.exe keepalive; this leg's run.sh
counts collector-pattern processes before/after each run for the same
discipline RS053 used, though no MoE-0 collector legs were observed
running during this leg's window (collector_before/after: 0 proc(s) on
all four runs). Read-never: ~/.config/openbob/, journal blobs, tokens,
pins, and the sealed corpus lowint/fixtures/LI-S5-ROUTES-1.txt (none
opened by this leg). Stage dirs under /mnt/f/f32/stage/ read-only except
this leg's own /mnt/f/f32/stage/research/ob1/ (created by this leg). No
weight downloads (none needed; the model was already on disk, digest
confirmed against the registry per the task brief). Every wsl.exe
invocation in this leg ran a script file written to the Windows
filesystem first (script-to-file law); python.exe (never python3) is not
applicable here since this leg's Python work all ran on the WSL/hyde side
under /root/openbob-train/venv/bin/python (python3), consistent with the
house rule's "python3 on the WSL/hyde side" clause. Git work happens only
in F:\f32\openbob-wt\research-2 on branch research-2; master is never
touched, nothing is pushed; the architect merges.

## 10. DEVIATIONS, COLLECTED

  1. The manifest tool (research/ob1/gguf_expert_manifest.py) was run
     twice during development: an initial run printed a mislabeled
     summary line (PER_EXPERT_BYTES_PER_LAYER was, by a variable-naming
     bug, actually the PER-LAYER TOTAL across all 32 experts, i.e.
     424120320, not one expert's share). This was caught before the
     manifest's row content was used for anything (the CSV rows
     themselves were always computed correctly; only the printed/footer
     summary labels were wrong), fixed, and the tool rerun. The committed
     manifest and this document use only the corrected run's numbers.

  2. The identity artifact's first definition (raw stdout, whole file)
     was found NOT to be A/A-stable during this leg's own baseline runs
     (a wall-clock preamble line varies run to run); redefined to exclude
     that line, per section 5's A/A INVESTIGATION paragraph. The
     underlying computation was NOT nondeterministic (the PPL values
     themselves, and the route logs, were byte-identical throughout);
     only this leg's first choice of artifact boundary was too broad.

  3. p95 per-token latency (named in the task brief and in section 8's
     cost limb) is NOT measurable from llama-perplexity's own output;
     only total wallclock and one coarse early-ETA estimate are printed.
     Baseline wallclock and derived average ms/token are banked instead
     (section 5); the frozen cost-limb bar is carried forward as stated
     by the task brief, with the substitution/instrumentation
     responsibility handed to the leased-instrument-building leg,
     explicitly (section 8).

  4. Section 2's "packing assumption" (expert axis is the outermost GGUF
     dimension, so per-expert byte ranges are contiguous slices) is
     checked internally (divisibility, per-layer-uniformity) and
     cross-checked against RS053's independently-computed
     PER_EXPERT_BYTES_PER_LAYER number, but was NOT verified against a
     third, unrelated GGUF/MoE reference implementation. Named here as a
     real (if currently unfalsified) assumption, not asserted as proven
     beyond what two convergent readers of the same file can show.

  5. Section 4's exact tokenized length of each acceptance corpus (beyond
     "at least 32768 tokens, confirmed by the run not erroring") was not
     separately measured, since llama-perplexity does not print a bare
     token count and the frozen truncation rule does not require it
     (section 4).

No other deviations. Nothing above was renegotiated after this document
was committed.

END OB1-EXPOSURE-1-PREREG
