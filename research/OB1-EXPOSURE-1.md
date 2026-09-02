# OB1-EXPOSURE-1: BOUNDED EXPERT RESIDENCY ON GPT-OSS-20B, ACCEPTANCE AND
# EXPOSURE RECEIPT

Lane: research (CUDA/inventor lane), venue hyde, on-machine, worktree
F:\f32\openbob-wt\research-2, branch research-2. This is builder 3 of OB-1
(acceptance + receipt). Pure ASCII, no em dashes. Every number below is
either literal output of a command this leg ran itself, or is carried
forward from research/OB1-EXPOSURE-1-PREREG.md (the frozen prereg) or
research/ob1/RUNLOG-1.txt (the lease-engine builder's log) with its source
named. Nothing below claims a verdict beyond what a measurement supports;
per house law the exposure numbers are reported, not scored.

Binding documents, in order: research/OB1-EXPOSURE-1-PREREG.md (frozen
2026-08-31, before the leased-residency instrument existed) and
research/ob1/RUNLOG-1.txt (the instrument's own run log, deviations D1-D8).
This receipt does not repeat their full derivations; it re-verifies their
headline claims independently and adds the routing-miss-rate figure and
the RS053 comparison the task asked for.

## 1. THE QUESTION

gpt-oss-20b is a mixture-of-experts (MoE) language model: 24 transformer
layers, each holding 32 independent "expert" feed-forward sub-networks, of
which a learned router picks 4 per token per layer. The other 28 experts
contribute nothing to that token. Serving the model the ordinary way keeps
all 24 x 32 experts resident in fast memory regardless, because that is
simply how a model file is loaded whole.

OB-1 asks: if only the K most-used experts per layer are kept resident
("warm"), and any other expert is fetched from local NVMe on demand when a
token's router actually asks for it ("cold": loaded into a scratch buffer,
verified byte-for-byte against a manifest, used, then discarded), does the
model's output stay EXACTLY the same as the fully-resident case, and how
much fast memory does that buy back? The chosen K's are 16, 8 and 4 (of
32); the resident set per layer is STATIC, chosen once from a route log
that recorded which experts the pretrained router actually favored, and
never updated during a run. No cache state, no LRU: the resident set at
any point in a run is a pure function of K and the layer, never of run
history, which is what makes a leased run replayable byte-for-byte by
construction.

## 2. METHOD SUMMARY (self-contained)

**Model.** /root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf, 24
layers, 32 experts/layer, 4 experts used/token, sha256
27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901. This leg
re-ran sha256sum against the live file and got the same digest; file size
12109566624 bytes, matching TOTAL_MODEL_BYTES below.

**Expert manifest.** Each of the 6 "fused" per-layer weight tensors (gate,
up, down, and their 3 biases) holds all 32 experts back to back, expert
index outermost, so one expert's bytes are a contiguous file range. Builder
1's manifest (research/ob1/EXPERT-MANIFEST-20B.sha256) records the file
offset, length and sha256 of all 24 x 32 x 6 = 4608 such ranges; this leg
re-counted the data rows (4608, via grep -vc '^#') and confirms the
header/footer comment lines are the only other content.

  PER_EXPERT_BYTES_PER_LAYER = 13253760
  TOTAL_EXPERT_BYTES         = 10178887680
  TOTAL_MODEL_BYTES          = 12109566624
  resident_always_bytes      = TOTAL_MODEL_BYTES - TOTAL_EXPERT_BYTES = 1930678944
    (embeddings, attention weights, layer norms, header: never leased,
    always mapped, at every K)

**Resident sets.** For K in {16, 8, 4}, the top-K experts per layer by
usage count, ranked from ONE route log: RS053's own 20b-prose-a run
(65536 router decisions over a DIFFERENT enwik8 byte range than either
acceptance corpus below). Ties broken by lower expert id. Frozen in
research/ob1/RESIDENT-SETS.json, never touched again after ranking.

**Acceptance corpora**, both extracted by builder 1, disjoint from the
ranking corpus:
  AC-PROSE  262144 bytes, enwik8 [96000000, 96262144)
  AC-CODE   RS053's corpus-code.txt, copied verbatim (1576144 bytes)
32768 tokens are evaluated from each, per llama-perplexity's
--ctx-size 1024 --chunks 32 (32 x 1024 = 32768).

**The lease engine.** A fork of the RS053 llama.cpp build (upstream
ca3d5a3 plus the route-log patch), a new branch "ob1", the diff committed
as research/ob1/lease-engine.patch. At model load it reads only the
resident set's byte ranges from disk, sha256-verifying each against the
manifest; non-resident ranges are never read, so the operating system
never faults those pages into memory. At run time, the same callback
RS053's route-log patch already uses (which fires after the router's
choice is computed but before that layer's expert matrix multiplies run)
lets the engine: drop the previous layer's leased pages
(madvise(MADV_DONTNEED)), pread() and sha256-verify the bytes of any
routed expert that is not resident directly into that expert's slot in
the tensor, then let the unmodified kernel run. Tensor shapes, addresses,
kernels and node order are identical to the fully-resident run; only the
provenance of a non-resident expert's bytes differs (freshly read from
disk instead of already mapped). This is why byte-identical output is a
structural expectation of a correct implementation, not a hoped-for
result.

**Runs.** All runs use the SAME binary and flags for both arms
(-ngl 0, GPU hidden via CUDA_VISIBLE_DEVICES="", --no-mmap, --no-repack,
--threads 10 --threads-batch 10, nice 10, seed 1). This departs from
builder 1's own GPU baseline (-ngl 99); the reasoning (a GPU allocation
cannot be partially unmapped by a lease, so leasing into VRAM would report
an exposure of exactly 1.0 regardless of K) is in RUNLOG-1.txt section 4
and is carried forward here as deviation D1. Builder 2 therefore made its
OWN fully-resident CPU reference run per corpus (res-prose-a, res-code-a)
and compares every leased run against that, not against builder 1's GPU
numbers; this receipt does the same.

## 3. INDEPENDENT RE-VERIFICATION (this leg's own commands)

All of the following were re-run by this leg directly against the
off-repo artifacts under /mnt/f/f32/stage/research/ob1/runs/, not copied
from RUNLOG-1.txt.

**Model file.** sha256sum on the live file: matches the digest above.
File size: matches TOTAL_MODEL_BYTES exactly.

**Manifest.** 4608 data rows (grep -vc '^#' on
EXPERT-MANIFEST-20B.sha256), matching the prereg's stated ROW_COUNT.

**Identity limb, sha256 re-hash of every run's identity.txt and
route.log**, compared against each corpus's own resident reference
(res-prose-a for AC-PROSE, res-code-a for AC-CODE):

  run                    vs corpus  identity  route
  lease-k16-prose-a      prose      MATCH     MATCH
  lease-k16-prose-b      prose      MATCH     MATCH
  lease-k16-prose-c      prose      MATCH     MATCH
  lease-k8-prose         prose      MATCH     MATCH
  lease-k4-prose         prose      MATCH     MATCH
  lease-k16-prose-fadv   prose      MATCH     MATCH
  lease-k16-code         code       MATCH     MATCH
  lease-k8-code          code       MATCH     MATCH
  lease-k4-code          code       MATCH     MATCH

  res-prose-a vs res-prose-b (A/A, the reference's own stability): MATCH

Nine of nine leased runs, byte-identical on both the perplexity-chunk
artifact and the 786432-line route log, at every K, on both corpora.
Every sha256 this leg computed matches the digest RUNLOG-1.txt section 13
already recorded for that run; nothing here contradicts the builder's own
numbers, this is an independent re-derivation from the same off-repo
bytes.

**Exposure arithmetic**, recomputed from raw literals (resident_always,
per_expert_bytes, and each run's own reported peak_concurrent_lease_bytes
and RSS_bytes), not copied from RUNLOG-1.txt's own division:

  K=16: ACCT_bytes=7232182944  EXPOSURE_ACCT=1.674400  (matches RUNLOG)
  K=8:  ACCT_bytes=4793491104  EXPOSURE_ACCT=2.526252  (matches RUNLOG)
  K=4:  ACCT_bytes=3574145184  EXPOSURE_ACCT=3.388101  (matches RUNLOG)

peak_concurrent_lease_bytes literal check: 16x13253760=212060160 (K=16),
24x13253760=318090240 (K=8), 28x13253760=371105280 (K=4); all three match
the engine's own reported figures.

**Cost limb, K=16 bar (<=3.0x baseline p95).** Recomputed p95_leased /
p95_baseline for every K=16 run:

  lease-k16-prose-a     20090.3 / 16025.8 = 1.2536   PASS
  lease-k16-prose-b     20583.7 / 16025.8 = 1.2844   PASS
  lease-k16-prose-c     20533.2 / 16025.8 = 1.2813   PASS
  lease-k16-code        20746.2 / 16073.7 = 1.2907   PASS
  lease-k16-prose-fadv  24691.8 / 16025.8 = 1.5408   PASS (cold page cache)

All five re-derived ratios match RUNLOG-1.txt's own figures and clear the
3.0x bar with more than half the budget to spare, even under the
cold-cache variant.

**Routing-miss rate, computed fresh (not in RUNLOG-1.txt).** RUNLOG-1.txt
reports "leases" as expert-LOAD events (one lease serves every token in a
1024-token micro-batch that needed that expert at that layer, deduplicated
within the batch, because the engine loads an expert once per
micro-batch-layer rather than once per token). That is the right number
for the COST limb (it is what the engine actually paid for), but it is
not directly comparable to RS053's own P_half statistic, which is a
per-decision figure. This leg instead computed a per-decision miss rate
directly from each corpus's own reference route log (res-prose-a /
res-code-a; 786432 lines, 24 layers x 32768 tokens, 4 router picks per
line = 3145728 total router decisions per corpus), checking every
individual pick against the frozen resident set for its layer:

  corpus  K    total_picks   misses    miss_rate
  prose   16   3145728       591548    18.8048%
  prose   8    3145728       1331123   42.3153%
  prose   4    3145728       1953318   62.0943%
  code    16   3145728       1905471   60.5733%
  code    8    3145728       2508167   79.7325%
  code    4    3145728       2841526   90.3297%

This is an independent, honest measurement, computed by this leg from the
route log and RESIDENT-SETS.json alone, cross-checked against nothing else
in this program (no prior document reports this number).

## 4. HEADLINE TABLE

  K   capacity exposure (ACCT)   RSS-based exposure   corpus   routing-miss rate   bytes moved/token   p95 vs baseline   identity
  16  1.674400                   1.4327 - 1.4358       prose    18.8048%            4382865.7 B         1.2536-1.2844x    PASS
  16  1.674400                   1.4327 - 1.4358       code     60.5733%            4890883.4 B         1.2907x           PASS
  8   2.526252                   2.0120 - 2.0179       prose    42.3153%            6857429.4 B         1.4145x (no bar)  PASS
  8   2.526252                   2.0120 - 2.0179       code     79.7325%            7320955.1 B         1.5139x (no bar)  PASS
  4   3.388101                   2.5221 - 2.5328       prose    62.0943%            8099160.5 B         1.5178x (no bar)  PASS
  4   3.388101                   2.5221 - 2.5328       code     90.3297%            8540440.1 B         1.5409x (no bar)  PASS

Column notes:
- "capacity exposure (ACCT)" = LOGICAL / RESIDENT(K), RESIDENT(K) built
  from the prereg's own formula (resident_always + K x 24 x
  13253760 + the engine's MEASURED peak concurrent lease bytes, not the
  prereg's illustrative one-slot guess). It does not vary by corpus at a
  given K in this data, because peak_concurrent_lease_bytes came out
  identical for prose and code at each K.
- "RSS-based exposure" = LOGICAL / process peak resident-set size
  (/usr/bin/time -v). Includes compute buffers, KV cache, tokenizer and
  allocator overhead, which is why it sits noticeably below the ACCT
  figure; it is what the operating system actually reports the process
  paying, not a parameter-only accounting.
- "routing-miss rate" (this leg's own figure, section 3) is a per-decision
  rate: the fraction of the 3145728 individual router picks per corpus
  that landed on a non-resident expert. It is corpus-specific because the
  resident sets were ranked from ONE prose route log and never
  re-ranked; code, being a different traffic pattern, misses far more.
- "bytes moved/token" is the engine's own figure (RUNLOG-1.txt section 8):
  total verified bytes read from disk divided by 32768 tokens. It reflects
  the ENGINE's per-micro-batch deduplication (one lease serves an entire
  1024-token batch's demand for that expert-layer pair), so it is smaller,
  relative to the miss rate, than a naive "one lease per missed pick"
  count would be.
- "p95 vs baseline" bar (<=3.0x) is frozen ONLY at K=16 (prereg section 8);
  K=8 and K=4 are report-only, named as such in the table.
- "identity" is PASS at all nine leased configurations (K x corpus, plus
  the K=16 cold-cache variant), independently re-verified in section 3,
  not merely re-stated from RUNLOG-1.txt.

## 5. LIMB VERDICTS AGAINST THE FROZEN BARS

**IDENTITY LIMB: PASS.** At every K in {16, 8, 4}, on both acceptance
corpora, the leased run's identity.txt (the perplexity-chunk artifact) and
its route.log are byte-identical (sha256 match) to that corpus's
fully-resident reference. Nine of nine leased runs, verified independently
by this leg in section 3, not merely re-stated. Per the prereg this is
the EXPECTED result of a correct implementation (the scratch mechanism
always loads the exact, manifest-verified bytes the router asked for), so
this is confirmation the implementation is correct, not a surprising
finding. A concrete demonstration named in RUNLOG-1.txt section 8 is worth
repeating here: at K=4, 87.5 percent of the model's expert parameter bytes
(8906526720 of 10178887680) were never loaded into memory at model-load
time at all, and the run still reproduced the fully-resident output to
four decimal places across all 32768 tokens on both corpora. A leased
region that went unread would have supplied zeros, and 87.5 percent
zeroed experts cannot give byte-identical perplexity; the identity match
is only possible if the cold-loaded bytes were genuinely read and used.

**EXPOSURE LIMB: report-only, no bar (per house measurement-language
law).** The measured ACCT-based exposure (1.674, 2.526, 3.388 at K=16, 8,
4) sits below the prereg's own illustrative pre-instrument arithmetic
(1.722, 2.698, 3.765, prereg section 7). The gap is explained and named as
deviation D3 in RUNLOG-1.txt: the prereg's formula assumed a single
13253760-byte scratch slot (one expert, sized for one-token-at-a-time
inference), but the frozen invocation processes 1024-token micro-batches,
so a layer's single fused matrix multiply needs every non-resident expert
that ANY of those 1024 tokens routed to, simultaneously. The measured
peak concurrent lease is exactly 16, 24 and 28 experts' worth (K=16, 8, 4
respectively): in the worst micro-batch of a run, every non-resident
expert of some layer was touched by at least one of its 1024 tokens,
which is unsurprising given 1024 tokens x 4 picks spread over 16-28
non-resident slots. This is a property of the batch shape, not a defect
of the lease design; a smaller micro-batch would shrink the scratch
requirement (and the exposure gap) at the cost of throughput, a genuine
trade-off named here rather than hidden.

**COST LIMB: PASS at the frozen K=16 bar.** Measured p95 ratios (leased
p95 / resident p95, over 31 nearest-rank samples per run, chunk-level not
token-level per RUNLOG-1.txt deviation D2) range 1.2536-1.2907x across
five K=16 configurations including the cold-page-cache variant, all well
inside the <=3.0x bar. At K=8 and K=4 (report-only, no bar per the
prereg), the ratios climb to 1.41-1.54x, tracking the extra disk read and
verify time as more of the model has to be fetched cold. Section 10 of
RUNLOG-1.txt attributes roughly half of the added latency to a
single-threaded sha256 verification step (2.43-2.49 GB/s warm-cache,
1.04 GB/s genuinely cold), which the same document names as the most
obvious place a later leg could improve throughput without touching the
identity guarantee.

## 6. RS053 CONTEXT ROW: DOES P_half PREDICT THE MEASURED MISS RATE?

RS053 (research/RS053-GPTOSS-LOCALITY-1.md section 4) measured P_half(l),
a per-layer concentration statistic: the fraction of a layer's total
router traffic, over a whole corpus, that lands on that layer's busiest
half of experts (top E/2 = 16 of 32, for this model). Under perfectly
uniform routing P_half = 0.50 for any E; it rises toward 1.0 as usage
concentrates onto fewer experts. RS053's own layer-mean figure for
gpt-oss-20b on prose text is P_half = 0.851591904958089230 (quoted to
full precision from that document's own table; the task brief's "0.8516"
is this same figure rounded).

Because P_half is computed by the SAME "sort by usage, take the top
half" method that OB-1's K=16 resident set uses, 1 - P_half is a natural
same-corpus prediction for what a static top-16 resident set's per-pick
MISS rate would be, if it were tested against the identical route log it
was ranked from. RS053's own prose route log is not the same run as OB-1's
AC-PROSE (different, non-overlapping enwik8 byte ranges, per the prereg's
disjointness law in section 3), so this is a held-out comparison, not a
replay of the same tokens.

  predicted miss ceiling from RS053, 1 - P_half         14.84%
  measured miss rate, this leg, K=16, AC-PROSE          18.80%
  measured miss rate, this leg, K=16, AC-CODE           60.57%

On AC-PROSE, a corpus of the same kind of text (enwik8/Wikipedia) as the
route log the resident set was ranked from, the measured miss rate (18.80
percent) sits reasonably close to the P_half-implied figure (14.84
percent): the static, cross-slice resident set generalizes about as well
as the single-corpus concentration statistic would suggest, for
same-domain text.

On AC-CODE, a genuinely different kind of text that was NEVER part of the
ranking corpus, the measured miss rate (60.57 percent) is more than four
times the P_half prediction. This is the honest, expected shape of the
result, not a surprise to soften: a static resident set ranked from ONE
domain's traffic does not transfer to a different domain's traffic nearly
as well, and this leg's own numbers say exactly how much worse (roughly
3.2x more misses on code than on prose, at the same K). This is a real
limitation of the "one static, popularity-ranked set" design as specified
by the prereg, not an implementation defect; the identity limb still
holds regardless (section 5), because a miss is always served correctly
from disk, it is simply served MORE OFTEN on unfamiliar text.

## 7. LIMITATIONS, STATED PLAINLY

- Single model (gpt-oss-20b), single box (f32-HYDE), single build of one
  llama.cpp fork. Nothing here has been checked against a second
  independent inference engine or a second GPU/CPU vendor.
- The residency policy is deliberately the simplest static design (one
  ranking pass, never updated); section 6 shows directly how much that
  costs when the traffic domain shifts (code vs. the prose it was ranked
  from). A policy that adapted per-domain, or that combined multiple
  ranking corpora, was out of scope for this leg and is named in the menu
  below, not attempted here.
- The CPU configuration (-ngl 0, GPU hidden, --no-mmap, --no-repack,
  deviation D1) is not the model's normal fast-path serving configuration;
  it was chosen because it is the configuration in which "peak resident
  bytes" is a meaningful, shrinkable quantity at all (a GPU's fixed VRAM
  allocation cannot be partially returned by a lease). The absolute
  wall-clock and p95 numbers in this receipt describe THIS configuration,
  not a GPU-served, -ngl 99 deployment; they should not be read as a claim
  about GPU-served latency.
- Verification throughput (2.43-2.49 GB/s warm, 1.04 GB/s genuinely cold)
  runs on a single thread while ten compute threads sit idle
  (RUNLOG-1.txt D8); the cost-limb numbers above are therefore not a
  floor on what a leased engine could achieve, only what this one, not
  yet latency-optimized, implementation achieved.
- The "capacity exposure" metric's ACCT variant depends on the observed
  peak concurrent lease size for a given batch shape (section 5); a
  different micro-batch size would move both the exposure figure and the
  cost figure, in opposite directions, and that trade-off curve was not
  swept in this leg.

## 8. HELD MENU: NEXT STEPS (nothing here fires; naming only, per the task)

- PREDICTION-ASSISTED LEASING: a small, cheap predictor (the kind of
  low-int scheduler tier named in the house's own research roadmap) that
  guesses which non-resident experts an upcoming micro-batch will need,
  prefetching them before the routing callback rather than after, to hide
  read/verify latency behind existing compute.
- REGION LEASING BY TASK: rank and swap resident sets per detected task or
  domain (prose vs. code, or finer), rather than one static set for the
  whole run, directly targeting the domain-transfer miss-rate gap section
  6 measured (60.57 percent on code vs. 18.80 percent on prose at K=16).
- 120b: repeat this program's three limbs on gpt-oss-120b (36 layers,
  E=128, k=4, per RS053's own 120b geometry card), where RS053 already
  measured a higher layer-mean P_half (0.919 prose, 0.915 code) than 20b,
  suggesting a larger, sparser model may have MORE to gain from bounded
  residency, not less.
- REMATERIALIZATION BEYOND UNPACK: this leg's "cold" path is a verified
  disk read of the expert's own stored bytes, unchanged. A further step
  would store experts in a compressed or generative form and
  reconstruct (rematerialize) them at lease time instead of merely
  reading them, trading CPU cycles for an even smaller on-disk and
  in-flight footprint, which is the direction named in the house's wider
  1T-class-brain roadmap.

## 9. ARTIFACTS AND DIGESTS

Off-repo run artifacts (route.log, identity.txt, stdout.txt, stderr.txt,
ob1-stats.txt per run) remain at /mnt/f/f32/stage/research/ob1/runs/<run>/,
digests recorded in RUNLOG-1.txt section 13 and independently re-verified
by this leg in section 3 above. This receipt and its section-3 checks were
produced by ad hoc commands run directly against those off-repo bytes
(sha256sum, grep, and a short stdlib-only Python pass over each
reference route log against RESIDENT-SETS.json for the miss-rate figure);
no new script is committed for the miss-rate computation, since it is a
direct, auditable read of already-committed data (RESIDENT-SETS.json) and
already-produced route logs, not a new instrument requiring its own
walls.

Committed with this receipt: this file only (research/OB1-EXPOSURE-1.md).
No prior artifact is modified.

END OB1-EXPOSURE-1
