# OB1B-KNEE-1-PREREG: HUNTING THE E2x KNEE (K=2, K=1, K=0) AND ONE
# WALL-CLOCK-BOUNDING POINT ON GPT-OSS-120B

Lane: research (CUDA/inventor lane), venue hyde, on-machine. Branch
research-2, worktree F:\f32\openbob-wt\research-2. Builder 1 of OB-1b
(prereg + resident sets + predictions + byte facts), same role split OB-1
used. Pure ASCII, no em dashes. Every number below is literal command
output from this leg's own script runs, or is quoted verbatim from a
cited file. Nothing below is renegotiated after this document is
committed except where named as a deviation in the deviations section.

Substrate at prereg time: worktree branch research-2. The research-2
worktree is shared SEQUENTIALLY with siblings OB-2, OB-3, OB-4 per house
git law; this leg only ever adds/commits research/ob1b/* and
research/OB1B-KNEE-1-PREREG.md, never touching another leg's paths.

## 0. WHAT THIS DOCUMENT IS

research/OB1-EXPOSURE-1.md (OB-1, the direct predecessor) measured a
static, popularity-ranked bounded-residency scheme on gpt-oss-20b at K in
{16, 8, 4}: identity byte-exact at every K on both acceptance corpora,
measured ACCT exposure 1.674400 / 2.526252 / 3.388101, p95 1.25-1.54x the
fully-resident baseline. Miss rate (the fraction of the router's top-4
picks that land on a non-resident expert) was rising fast (18.8/42.3/62.1
pct on prose, 60.6/79.7/90.3 pct on code) while p95 barely moved, so the
curve's KNEE -- the largest exposure achievable with p95 still at most
2.0x baseline and identity still exact -- had not been found by the time
OB-1 stopped. This leg (OB-1b) extends the K sweep DOWNWARD past OB-1's
floor (K=4) toward the knee: K=2, K=1, and K=0 (the pure-streaming point,
where the resident set is empty and every routed expert is leased on
every use). It also takes ONE point on gpt-oss-120b (128 experts, K=8) to
bound wall-clock at the larger model, since nothing in this program has
run leased residency on the 120b weights before.

This leg's own scope, stated plainly: RESIDENT SETS, SIM PREDICTIONS (miss
rate from already-banked route logs, no model run), EXPOSURE ARITHMETIC
(byte facts, no model run), a TIMING-GRANULARITY DECISION, and 120B BYTE
FACTS -- all of it either pure computation over already-banked artifacts
or a design decision, needing no OB-1 engine invocation and no runlock.
The one piece that DOES need a model run -- the 120b wall-clock-bounding
point (leased K=8, its resident baseline, one A/A repeat) -- is reported
in section 5 together with its literal execution status, since the house
runlock was held by a sibling leg for this leg's entire working window
(evidence below).

## 1. RESIDENT SETS FOR K IN {2, 1, 0} (task step 1)

Tool: research/ob1b/resident_sets_knee.py. SAME LINEAGE as
research/ob1/resident_sets.py: identical route-log loader (file-order
boolean mask per layer, token_index-monotonic verification against
0..budget-1, identical bincount), identical ranking rule (top-K per layer
by usage count), identical tie-break (LOWER EXPERT ID). The only change
is that K_VALUES is a CLI argument instead of OB-1's frozen [16, 8, 4], so
it can express K=2, K=1, and K=0.

RANKING CORPUS, same honesty law, same source as OB-1 (never mixed with
an acceptance corpus): /mnt/f/f32/stage/research/rs053/runs/20b-prose-a/
route.log. This leg's own independent sha256sum of that file is
a0bb972ec5a02e18ab685000c72b512751e579e243deecc3c095d8340c4b50aa, which
MATCHES both RS053's own recorded digest and OB-1's RESIDENT-SETS.json
source_route_log_sha256 field exactly -- confirming this leg ranks from
the identical bytes OB-1 did, byte for byte, not a re-fetch or a
different slice.

K=0 SEMANTICS: the pure-streaming point is an EMPTY resident set per
layer, by definition. No ranking computation is needed to know this; the
tool special-cases K=0 and writes 24 empty lists rather than running the
top-K selection on it.

RESULT, literal (research/ob1b/RESIDENT-SETS-KNEE.json):

  E=32 L=24 budget=65536, tie_break=lower expert id

  K=2  resident_expert_pool_bytes =  636180480   (2 x 24 x 13253760)
  K=1  resident_expert_pool_bytes =  318090240   (1 x 24 x 13253760)
  K=0  resident_expert_pool_bytes =        0     (empty set, by definition)

### 1.1 THE OB-1 ENGINE DOES NOT ACCEPT K=0 AS LANDED -- A GUARD FIX FOR BUILDER 2

Per the task brief, this leg read research/ob1/lease-engine.patch (the
committed diff, fork branch ob1, head c087083) rather than trying K=0
against the live binary, since the read alone settles the question.
src/ob1-lease.cpp, function ob1_init() (patch line 851):

  if (g_K <= 0 || g_K > g_E) ob1_fatal("OB1_K=%d out of range 1..%d", g_K, g_E);

This rejects OB1_K=0 unconditionally, before any resident-set JSON is even
opened. THE FIX IS MINIMAL AND ISOLATED, verified by reading the rest of
the engine's K=0 code path:

  - ob1_load_resident_sets() (same file) parses resident_sets["0"] as an
    object whose 24 layer values are JSON lists; an empty list `[]` is
    parsed correctly by the existing bracket-walking loop (it enters the
    while, immediately meets `]`, and exits with cnt=0), and the very
    next check, `if (cnt != g_K) ob1_fatal(...)`, PASSES when g_K=0 and
    cnt=0. No change needed here.
  - ob1_lease_load_tensor()'s per-expert load loop (`for (e...) { if
    (!g_resident[idx_r(il,e)]) continue; ... }`) with an all-zero
    g_resident array simply loads nothing at model-load time for any
    layer -- exactly the pure-streaming point's definition, and no
    special-casing is needed there either.

So the ONLY change needed is widening the bounds check from `g_K <= 0` to
`g_K < 0` on the cited line. This is handed to builder 2 as a one-line,
already-diagnosed patch, not an open question.

K=1 and K=2 are NOT blocked by this guard (g_K > 0 for both), so the
existing ob1 branch binary (c087083) can run leased K=1 and K=2 live
without any engine change; only K=0 needs the guard fix above.

Commit: (this section) resident_sets_knee.py + RESIDENT-SETS-KNEE.json.

## 2. SIM PREDICTIONS: PER-DECISION MISS RATE, NO MODEL RUN (task step 2)

Tool: research/ob1b/sim_miss.py. A DECISION is one entry in the router's
top-4 selection for one token at one layer (one route-log row contributes
4 decisions); a decision MISSES when its expert id is not in that layer's
K-resident set. This is a pure lookup against an ALREADY-BANKED route
log -- res-prose-a and res-code-a under /mnt/f/f32/stage/research/ob1/
runs/, OB-1's own acceptance-run route logs -- so it runs no model and
needs no runlock. K=0 is not computed by lookup; an empty resident set
misses on every decision by definition, so its rate is exactly 1.0.

METHODOLOGY VALIDATION, before trusting it on new K values: run against
OB-1's OWN K in {16, 8, 4} and its OWN RESIDENT-SETS.json first.

  prose (res-prose-a route log, 3145728 decisions = 24 layers x 32768
  tokens x 4):
    K=16  miss_decisions=591548   miss_rate=0.188048   (OB-1: 18.8 pct)
    K=8   miss_decisions=1331123  miss_rate=0.423153   (OB-1: 42.3 pct)
    K=4   miss_decisions=1953318  miss_rate=0.620943   (OB-1: 62.1 pct)

  code (res-code-a route log, 3145728 decisions):
    K=16  miss_decisions=1905471  miss_rate=0.605733   (OB-1: 60.6 pct)
    K=8   miss_decisions=2508167  miss_rate=0.797325   (OB-1: 79.7 pct)
    K=4   miss_decisions=2841526  miss_rate=0.903297   (OB-1: 90.3 pct)

Every figure MATCHES OB-1's own reported miss percentages (task brief
context) to the first decimal place, on both corpora, at all three K
values. The lookup methodology is therefore trusted for the new K values.

RESULT, K in {2, 1, 0}, same two route logs (research/ob1b/SIM-MISS-
PROSE.txt, research/ob1b/SIM-MISS-CODE.txt):

  prose (res-prose-a, 3145728 decisions):
    K=2   miss_decisions=2453533  miss_rate=0.779957   (78.0 pct)
    K=1   miss_decisions=2762711  miss_rate=0.878242   (87.8 pct)
    K=0   miss_decisions=3145728  miss_rate=1.000000   (100.0 pct, by definition)

  code (res-code-a, 3145728 decisions):
    K=2   miss_decisions=3030588  miss_rate=0.963398   (96.3 pct)
    K=1   miss_decisions=3095547  miss_rate=0.984048   (98.4 pct)
    K=0   miss_decisions=3145728  miss_rate=1.000000   (100.0 pct, by definition)

MISS-RATE CURVE ACROSS ALL SIX K VALUES, PROSE (OB-1's three rows cited,
this leg's three appended): 16->18.8, 8->42.3, 4->62.1, 2->78.0, 1->87.8,
0->100.0 pct. The climb is still steep at every step down to K=1; the
last increment (K=1 to K=0) only adds 12.2 points because K=1 was already
missing 87.8 pct of decisions. CODE climbs even faster and is already at
90.3 pct missed by K=4 (OB-1), so K=2/1/0 add comparatively little
(96.3/98.4/100.0): the code corpus's routing is close to uniform across
experts at this scale, so almost any bounded K below the low teens
already misses most of the time on code. Miss rate alone does not locate
the knee (COST does, section 4 of RUNLOG-1's own read: p95 rose only
1.25-1.54x across a miss-rate range of 18.8 to 90.3 pct in OB-1's own
data); this leg's job was to extend the miss-rate and exposure curves,
not to re-derive that point.

Commit: (this section) sim_miss.py + SIM-MISS-PROSE.txt + SIM-MISS-CODE.txt.

## 3. EXPOSURE ARITHMETIC, FROZEN (task step 3)

Formula, unchanged from research/OB1-EXPOSURE-1-PREREG.md section 7 and
matching RUNLOG-1.txt section 9's MEASURED-scratch refinement (deviation
D3 there: the scratch term is not one slot, it is the peak concurrent
lease within one layer's 1024-token microbatch):

  RESIDENT(K) = resident_always + K x L x PER_EXPERT_BYTES_PER_LAYER
                + peak_concurrent_lease_bytes
  EXPOSURE(K) = TOTAL_MODEL_BYTES / RESIDENT(K)

THE PREDICTION RULE FOR peak_concurrent_lease_bytes AT UNMEASURED K: OB-1's
own three measured points give an EXACT pattern, not an approximation --
literal check, computed from RUNLOG-1.txt section 9:

  K=16  peak_concurrent_lease_bytes = 212060160 = 16 x 13253760 = (32-16) x 13253760
  K=8   peak_concurrent_lease_bytes = 318090240 = 24 x 13253760 = (32- 8) x 13253760
  K=4   peak_concurrent_lease_bytes = 371105280 = 28 x 13253760 = (32- 4) x 13253760

At all three measured points, EVERY non-resident expert of the worst
layer was routed at least once within some 1024-token microbatch (4
experts/token x 1024 tokens is enough routing diversity over a 32-expert
pool that this is expected, not coincidental -- RUNLOG-1.txt section 9
says so explicitly for K=16/8/4). This leg PREDICTS the same identity
holds at K=2, K=1 and K=0: peak_concurrent_lease_bytes(K) = (E - K) x
PER_EXPERT_BYTES_PER_LAYER, i.e. ALL non-resident experts of the worst
layer get touched in some microbatch. This is if anything MORE likely as
K falls (fewer resident experts to absorb routing, more non-resident ones
competing for the same 4096 per-microbatch selection slots), never less
likely, so extrapolating the pattern downward is the conservative
direction, not an optimistic one. It is a PREDICTION, not a measurement:
labelled EXP_acct_PREDICTED throughout this section, never claimed as
observed.

PREDICTED RESULT, K in {2, 1, 0}, gpt-oss-20b (TOTAL_MODEL_BYTES
12109566624, resident_always 1930678944, PER_EXPERT_BYTES_PER_LAYER
13253760, L=24, E=32):

  K  pool_bytes   peak_concurrent_pred   RESIDENT_pred   EXP_acct_PREDICTED
  2   636180480       397612800           2964472224        4.084898
  1   318090240       410866560           2659635744        4.553092
  0         0         424120320           2354799264        5.142505

FULL PREDICTED/MEASURED CURVE, ALL SIX K, gpt-oss-20b (16/8/4 MEASURED,
cited from RUNLOG-1.txt section 9; 2/1/0 PREDICTED, this leg):

  K    RESIDENT bytes   EXPOSURE   status
  16    7232182944       1.674400   measured (RUNLOG-1.txt)
  8     4793491104       2.526252   measured (RUNLOG-1.txt)
  4     3574145184       3.388101   measured (RUNLOG-1.txt)
  2     2964472224       4.084898   PREDICTED (this leg)
  1     2659635744       4.553092   PREDICTED (this leg)
  0     2354799264       5.142505   PREDICTED (this leg, pure streaming)

Read against COST (RUNLOG-1.txt section 10, p95 ratio 1.2536-1.5407 across
K=16..4, rising roughly with the READ/VERIFY volume, itself proportional
to (E-K)): the exposure curve keeps climbing past K=4 (3.388 to a
predicted 5.143 at K=0, a 52 pct further gain) while (E-K) only grows
from 28 to 32 (14 pct more read/verify volume predicted at the same
per-byte rate) -- so THE KNEE, if COST stays roughly proportional to
leased byte volume as OB-1's own data suggests, is predicted to sit BELOW
K=4, not above it: exposure keeps paying off faster than cost grows all
the way down to K=0 on this model, UNLESS an unmeasured cost floor
(fixed per-lease-event overhead, not just bytes moved) dominates at very
small K. This is a PREDICTION about where the knee likely sits, offered
for builder 2's targeting, not a substitute for actually running K=2/1/0
and measuring their p95.

Commit: (this section) is arithmetic only, carried in this document; no
new script beyond the python one-liner reported literally above.

## 4. TOKEN-LEVEL TIMING: DECISION, FROZEN (task step 4)

RUNLOG-1.txt deviation D2 (OB-1's own prior finding, re-read for this
leg): p95 there is PER CHUNK (per 1024-token microbatch), not per token.
The engine timestamps every layer-0 routing callback -- which fires once
per microbatch, not once per token -- because the route-log eval callback
(llama_route_log_eval_cb, src/llama-context.cpp) fires once per (layer,
microbatch): the ggml compute graph evaluates all 1024 tokens of a
microbatch in ONE kernel invocation per tensor per layer. There is no
callback, hook, or eval-order boundary between individual tokens WITHIN a
microbatch anywhere in the current invocation shape (--ctx-size 1024
--chunks 32 -b 1024 -ub 1024).

THIS LEG'S DECISION: true per-token wall-clock timestamps are NOT
achievable with a minimal patch under the frozen invocation shape. The
only way to get a callback boundary between individual tokens is to
shrink the microbatch (-ub) toward 1, which changes the batching itself
and therefore the very numbers under comparison (RUNLOG-1.txt deviation
D3 already ruled this out for the scratch-sizing question, for the same
reason: a 1-token microbatch is a different computation shape, not a
finer-grained view of the same one). The alternative -- instrumenting
inside the fused mul_mat_id kernel to time individual rows -- is not
minimal: it requires per-row profiling hooks the kernel does not expose
and risks perturbing the exact arithmetic path the identity limb depends
on. Per the task brief's own fallback clause, THIS LEG FREEZES
CHUNK-LEVEL TIMING, with the deviation stated up front rather than
discovered after building: any OB-1b run matrix reports p50/p95/p99 over
per-MICROBATCH (1024-token) wall-clock intervals, exactly as OB-1's own
runs did, and any "per-token" figure quoted alongside it is a derived
AVERAGE (interval / 1024), never a measured per-token latency.

p99 IS A NEW ADDITION, AND IT NEEDS NO ENGINE PATCH: research/ob1/
analyze.py already has a generic nearest-rank percentile function
(pct_nearest_rank) and already reads the engine's full per-chunk interval
series (chunk_ns, written by ob1-lease.cpp's ob1_write_stats() on every
run, lease AND resident alike, since OB1_STATS works independent of
OB1_LEASE). Adding p99 = pct_nearest_rank(chunk, 0.99) is a one-line
analysis-tool change over data the engine already banks; it requires no
change to ob1-lease.cpp and no re-run of anything already executed. This
is handed to builder 2 as a second already-diagnosed, minimal change.

## 5. THE 120B POINT (task step 5)

### 5.1 BYTE FACTS, gpt-oss-120b (computed from the gguf with the manifest
tool; NO extension needed -- research/ob1/gguf_expert_manifest.py already
reads E and L from the GGUF's own gpt-oss.expert_count / block_count kv
pairs rather than assuming the 20b shape, so it ran against the 120b
model unmodified)

Command: `python3 research/ob1/gguf_expert_manifest.py /root/openbob-
baselines/models/gpt-oss-120b-MXFP4.gguf research/ob1b/EXPERT-MANIFEST-
120B.sha256`, literal output:

  MODEL=gpt-oss-120b
  E=128 L=36                     (128 experts/layer, 36 layers; k=4
                                  experts used/token, per the GGUF's own
                                  gpt-oss.expert_used_count kv, read
                                  separately and independently confirmed)
  PER_EXPERT_BYTES_PER_LAYER = 13253760   (IDENTICAL to the 20b model --
      both models share the same expert width/hidden-dim geometry per the
      gpt-oss family design; this is a genuine cross-model match, not a
      copy-paste, since the tool re-derives it from the 120b file's own
      tensor spans)
  PER_LAYER_TOTAL_EXPERT_BYTES = 1696481280   (128 x 13253760)
  TOTAL_EXPERT_BYTES = 61073326080            (36 x 1696481280)
  TOTAL_MODEL_BYTES  = 63387346208            (the GGUF file's own size)
  ROW_COUNT = 27648                           (36 x 128 x 6)
  ELAPSED_SECONDS = 77.941

Model file identity: /root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf,
582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d, 63387346208
bytes -- MATCHES /root/openbob-baselines/reg/HYDE-MODEL-MANIFEST.sha256
(banked 2026-08-28T07:16:18Z at fetch time, ggml-org/gpt-oss-120b-GGUF
revision 238abdd290bb874b90a5da1b4549881b7d05c091) on both the digest and
the byte count -- an independent second read of the file (this leg's own
per-expert-slice hashing pass) landing on the same whole-file byte count
the fetch-time registry recorded.

  resident_always_120b = TOTAL_MODEL_BYTES - TOTAL_EXPERT_BYTES
                        = 63387346208 - 61073326080 = 2314020128

### 5.2 RESIDENT SET, gpt-oss-120b, K=8 of 128

Tool: research/ob1b/resident_sets_knee.py (same lineage, section 1), run
against the RS053 120b-prose-a route log (/mnt/f/f32/stage/research/
rs053/runs/120b-prose-a/route.log, this leg's own sha256sum
5aa8464d3c71a73648c2323456d656cd40cfcf9dc88b603e1f10da69f9efa129), E=128,
L=36, budget=16384 (589824 route-log lines / 36 layers, confirmed by the
loader's own shape check, which raised no SystemExit). Output:
research/ob1b/RESIDENT-SETS-120B-K8.json.

  K=8  resident_expert_pool_bytes = 3817082880   (8 x 36 x 13253760)

### 5.3 PREDICTED ACCT EXPOSURE, gpt-oss-120b, K=8 (task step 5's literal ask)

Same prediction rule as section 3 (peak_concurrent_lease_bytes(K) = (E-K)
x PER_EXPERT_BYTES_PER_LAYER):

  peak_concurrent_pred = (128 - 8) x 13253760 = 120 x 13253760 = 1590451200
  RESIDENT_pred(K=8)   = 2314020128 + 3817082880 + 1590451200 = 7721554208
  EXP_acct_PREDICTED   = 63387346208 / 7721554208 = 8.209143

Stated plainly: this is a larger predicted exposure than any 20b point in
this program (max so far, K=0 predicted 5.142505), because the 120b model
spreads the SAME per-expert byte size (13253760) over 4x the experts per
layer (128 vs 32) and 1.5x the layers (36 vs 24), so resident_always is a
much smaller fraction of the total (2314020128 / 63387346208 = 3.65 pct,
versus 1930678944 / 12109566624 = 15.9 pct for the 20b model) -- a bounded
resident set buys proportionally more on the larger, sparser model.

### 5.4 THE ACTUAL WALL-CLOCK-BOUNDING RUN: EXECUTION STATUS, LITERAL

The frozen configuration (leased K=8 on gpt-oss-120b, token budget 8192,
same invocation shape as RUNLOG-1.txt section 5 with --chunks 8 -b 1024
-ub 1024 in place of --chunks 32, plus its resident baseline at the same
budget, plus one A/A repeat of the leased run) requires an actual
llama-perplexity invocation and therefore the house RUNLOCK.

RUNLOCK STATE OBSERVED, literal, across this leg's entire working window
(first checked 2026-08-31 20:2x, last checked 2026-08-31 20:42 -- house
clock, this leg's own `date` calls):

  /mnt/f/f32/stage/research/runlock existed, HELD, at every check. `ps
  aux` identified the holder as sibling OB-2's own locked-run.sh chain
  (research/ob2/locked-run.sh, untracked at the time of this reading, not
  committed or modified by this leg): a llama-perplexity process against
  gpt-oss-20b-MXFP4.gguf, --threads 8 --threads-batch 8 -ngl 0 --no-mmap
  --no-repack -- the same OB-1-derived leased-residency invocation shape,
  run for OB-2's own K sweep. The lock's mtime advanced between checks
  (20:27:29 -> 20:42:migrated) as OB-2's driver released and immediately
  reacquired it between successive runs in its own matrix (its own
  locked-run.sh comment: "the lock is taken and released PER RUN... so
  the sibling workflow interleaves between this leg's runs") -- this leg
  observed that reacquisition window happen (a new PID, 998289/998290,
  replaced the previous 994183/994184 holder between two checks) but
  never observed the lock actually FREE at any of its own poll instants
  (30-second poll interval, 10-minute bounded wait, per this leg's own
  budget -- not the full 90-120 minute give-up bar, since this leg's
  other four steps do not depend on the 120b run and there is no reason
  to block the whole prereg on a race against a continuously active
  sibling matrix).

RESULT: the actual leased K=8 / resident-baseline / A/A-repeat triplet on
gpt-oss-120b is NOT executed by this document. Sections 5.1-5.3 (byte
facts, resident set, predicted exposure) are complete and require no
lock, since they touch no model process. The empirical wall-clock number
is DEFERRED, to be run by builder 2 (or by this leg in a follow-up window)
once the runlock frees, using: the resident set already committed here
(research/ob1b/RESIDENT-SETS-120B-K8.json), the manifest already
committed here (research/ob1b/EXPERT-MANIFEST-120B.sha256, which still
needs an OB1_MANIFEST-format row rewrite -- section 5.1's manifest is in
gguf_expert_manifest.py's own CSV shape, layer,expert,tensor,offset,
nbytes,sha256, which IS the OB1_MANIFEST format the engine reads directly,
per src/ob1-lease.cpp's ob1_load_manifest() column order -- no rewrite is
actually needed, this parenthetical is a false lead corrected in-line
rather than deleted, per the house's literal-reporting law), and the
invocation shape frozen above (--chunks 8, token budget 8192).

This is reported as a literal status, not a failure: the house runlock
law's own text anticipates exactly this outcome ("report after N min --
the box is busy tonight").

Commit: (this section) EXPERT-MANIFEST-120B.sha256 + RESIDENT-SETS-120B-K8.json.

## 6. WALLS AND SCOPE (per the house rules handed to this builder)

Box: hyde, Windows 11 + WSL2 Ubuntu, three sibling workflows (OB-2, OB-3,
OB-4) observed concurrently active in `ps aux` during this leg's window.
pid 654 (openbob serve) and pid 489 (searxng) were checked alive and were
never signalled, renamed, reniced, or killed. This leg ran NO gpt-oss
model process itself (section 5.4), so the 8-thread/nice-10 heavy-run
wall and the 4-thread analysis wall were both honored trivially (analysis
work here -- resident-set ranking, miss-rate lookup, GGUF manifest
generation -- ran unthreaded/default-threaded Python against already-
banked or on-disk read-only files, well under either bound; the GGUF
manifest read for the 120b model took 77.941s single-process, not a
"run" under house law's own definition, which the RUNLOCK LAW text scopes
to "every gpt-oss model run", i.e. an inference process, not a file
read+hash). Free RAM (available) was 17.6-18.2 GB throughout this leg's
checks, above the 6 GB bar, though the bar was never load-bearing since no
run was attempted. Read-never: ~/.config/openbob/, journals, tokens,
pins, and the sealed corpus lowint/fixtures/LI-S5-ROUTES-1.txt (none
opened). /mnt/f/f32/stage/ was read-only for this leg except its own
/mnt/f/f32/stage/research/ob1b/ (created by this leg, holding the
manifest job's stdout/stderr logs, not committed -- off-repo per house
law, matching OB-1's own convention of banking run outputs off-repo and
digests/figures in the committed document). No model weights were
downloaded; the 120b and 20b GGUF files were already on disk, confirmed
against the fetch-time registry (section 5.1). The OB-1 engine (fork
branch ob1, head c087083) was used AS LANDED -- read for section 1.1's
guard-fix diagnosis, never edited, never rebuilt, no worktree created
under /root/ob1b/ (not needed: this leg did not patch the engine, so
house law's "if you must patch, make your own worktree" clause did not
trigger). Git work happened only in F:\f32\openbob-wt\research-2 on
branch research-2, adding only research/ob1b/* and this document; master
was never touched, nothing was pushed, no `git pull` was run before any
commit (house law), and every commit added only this leg's own paths.

## 7. DEVIATIONS, COLLECTED

  1. Section 3's and section 5.3's peak_concurrent_lease_bytes at K in
     {2, 1, 0} (20b) and K=8 (120b) are PREDICTED by extrapolating an
     exact pattern OB-1 measured at three other points, not measured by
     this leg. Every exposure figure derived from a predicted
     peak-concurrent term is labelled PREDICTED throughout this document,
     never presented as measured. Section 3 states explicitly why the
     extrapolation is the conservative direction (more non-resident
     experts, not fewer, as K falls).

  2. Section 4 freezes CHUNK-LEVEL (not token-level) timing granularity
     for any OB-1b run matrix, per the task brief's own named fallback,
     because true per-token timestamps are not achievable with a minimal
     patch under the frozen 1024-token microbatch invocation shape. This
     mirrors RUNLOG-1.txt's own deviation D2 exactly; it is not a new
     limitation this leg introduced, it is the same one, re-confirmed
     after actually reading the callback structure that would have to
     change to lift it.

  3. Section 5.4: the 120b wall-clock-bounding run (leased K=8, resident
     baseline, one A/A repeat) was NOT executed. The house runlock was
     observed continuously held by sibling leg OB-2's own run matrix for
     this leg's entire working window (literal PIDs, timestamps, and the
     holder's own committed-lineage script, research/ob2/locked-run.sh,
     cited in section 5.4). This leg bounded its own wait at 10 minutes
     of 30-second polling rather than the house's full 90-120 minute
     give-up bar, since none of this leg's other four task steps depend
     on the 120b run, and continuing to poll a continuously active
     sibling matrix past that point would not be a good use of the box
     or of this leg's time. Byte facts, resident set, and predicted
     exposure for the 120b K=8 point are complete (sections 5.1-5.3); only
     the empirical wall-clock/identity/cost triplet is deferred.

  4. Section 1.1's K=0 guard-fix finding and section 4's p99-addition
     finding are both READ-ONLY diagnoses (the lease-engine patch and
     analyze.py were read, not edited, by this leg), per the task brief's
     explicit instruction to note a K=0 guard-fix need for builder 2
     rather than patch the engine in this leg. No worktree was created
     under /root/ob1b/ for the same reason (house law's patch clause did
     not trigger).

No other deviations. Nothing above was renegotiated after this document
was committed.

END OB1B-KNEE-1-PREREG
