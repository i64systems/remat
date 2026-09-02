# OB2-PREDICTIVE-1: DETERMINISTIC DYNAMIC RESIDENCY ON GPT-OSS-20B,
# ACCEPTANCE AND EXPOSURE RECEIPT

Lane: research (CUDA/inventor lane), venue hyde, on-machine. Branch
research-2, worktree F:\f32\openbob-wt\research-2. This is OB-2's builder
3 leg (acceptance re-verification + receipt, per this leg's task brief).
Pure ASCII, no em dashes. Every number below is either copied forward from
research/OB2-PREDICTIVE-1-PREREG.md / research/ob2/RUNLOG-1.txt and
independently re-derived by this leg's own commands, or is new arithmetic
this leg performed on already-committed engine counters; every such
command and its literal output is named. A command that fails is reported
verbatim, never replaced with a plausible value.

Binding documents, in order: research/OB2-PREDICTIVE-1-PREREG.md (frozen
before any engine existed), research/ob2/RUNLOG-1.txt (the builder 2 run
log this leg re-verifies). Nothing here overrides either; per house
measurement-language law, exposure figures are reported, not scored.

## 0. THE QUESTION, AND THE ONE-LINE ANSWER

OB-1 (research/OB1-EXPOSURE-1.md) showed a MoE model can be served
correctly from a BOUNDED resident expert set, byte-identical to a
fully-resident run, but that a STATIC popularity-ranked set is right
about the wrong workload: 18.80% miss on same-domain prose at K=16, but
60.57% on out-of-domain code -- a domain-transfer gap. OB-2 asked: can a
DETERMINISTIC DYNAMIC residency policy (a pure function of route history
strictly before each recompute boundary, never of timing, cache state, or
a float) cut that miss rate at the same K, with identity preserved?

ANSWER: YES on the miss rate, with identity held byte for byte in every
run, and the engine's live schedule agreeing with a committed simulator
of the frozen policy exactly, not approximately. At K=16 the domain gap
that was OB-1's headline weakness is gone: dynamic code misses 14.38%
against dynamic prose's 14.93% (code is now marginally EASIER), against
static's 60.57% (code) vs 18.80% (prose). This receipt independently
re-verifies every stop-ship and report-only bar builder 2 claimed, adds a
peak-and-mean whole-model memory-exposure accounting (not present in
RUNLOG-1.txt), and finds no discrepancy anywhere.

## 1. THE FROZEN POLICY (prereg sections 3, 7; RUNLOG-1.txt section 1;
   not renegotiated here)

P2 DECAY-COUNTER. Per layer, one integer counter per expert (E=32),
starting at zero. At each boundary b, a multiple of H=256 tokens, b > 0:

  1. every counter is right-shifted by 1 (integer halving), reflecting
     all history strictly before b;
  2. the resident set for window [b, b+256) is the top K of the
     just-decayed counters, ranked by descending count then ascending
     expert id;
  3. the window is served;
  4. each pick served in that window adds 65536 to its expert's counter,
     consumed at the NEXT boundary.

Cold start (b=0): all counters zero, so the lowest K expert ids serve
tokens [0, 256). Four integer operations and a 32-item sort per boundary,
per layer. Frozen by simulation (prereg section 7) before any engine
existed; the engine is research/ob2/policy-engine.patch (sha256
eaa0cbb00454d62a10d89f4c7a4777d708a34799feb5cd85652d44ef68c3594e,
independently re-hashed by this leg, matches).

## 2. RE-VERIFICATION METHOD

This leg wrote and ran research/ob2/verify-acceptance.py (sha256
61d5df8b832782c18a83b303b87c798cc8dc8a488592c33b06060cb741746f8f,
committed with this receipt), a SEPARATE implementation from
analyze_ob2.py that re-derives every bar from the off-repo run artifacts
directly, importing nothing from RUNLOG-1.txt or from analyze_ob2.py's
own arithmetic:

  - re-hashes every dyn-* run's identity.txt and route.log and compares
    against a fresh re-hash of OB-1's own banked res-prose-a / res-code-a
    references (not against a digest copied from a document);
  - recomputes miss_pct from ob2-stats.txt's raw ob2_misses/ob2_picks and
    compares against the P2-DECAY row parsed fresh out of the committed
    SIM-PROSE-TABLE-1.txt / SIM-CODE-TABLE-1.txt;
  - recomputes p95 from the raw chunk_ns series using the same
    nearest-rank-of-31 method as OB-1 and OB-2, and the cost ratio against
    the frozen per-corpus baselines;
  - re-checks the A/A pair (dyn-k16-code-a vs -b) on identity, route and
    miss count;
  - computes a whole-model PEAK and MEAN memory-pool-bytes figure and
    both exposure bases (section 7), which RUNLOG-1.txt's own instrument
    does not produce.

Run under house law: wsl.exe -e sh invoking a script file on the Windows
filesystem, no runlock (pure analysis over already-banked artifacts, no
model process, 1 thread), guard pids not touched. Literal command and
full output:

    wsl.exe -e sh /mnt/c/.../run-verify.sh
      -> python3 /mnt/f/f32/openbob-wt/research-2/research/ob2/verify-acceptance.py

    == IDENTITY REFERENCES (re-hashed from OB-1 banked runs) ==
      code   identity=9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8 route=f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77
      prose  identity=96049ccf8ca241bf58233afe13ed75e2ca43180d81973360d04cebc80d551925 route=4777aa8319f25d6e367f761ef12c7bec81a9ff7896bfed1b8ea0326b5dffc3df

    run              K corpus ident  route    miss_pct    sim_pct  delta_pp  exact     p95_ms cost_ratio cost
    dyn-k16-code-a  16 code   MATCH  MATCH    14.3759%   14.3759%   +0.0000    YES    25948.2    1.6143x PASS
    dyn-k16-code-b  16 code   MATCH  MATCH    14.3759%   14.3759%   +0.0000    YES    26399.5    1.6424x PASS
    dyn-k16-prose   16 prose  MATCH  MATCH    14.9343%   14.9343%   +0.0000    YES    22738.2    1.4188x PASS
    dyn-k8-code      8 code   MATCH  MATCH    36.3824%   36.3824%   +0.0000    YES    26502.9    1.6488x PASS
    dyn-k8-prose     8 prose  MATCH  MATCH    36.7640%   36.7640%   +0.0000    YES    25917.8    1.6173x PASS

    == A/A LIMB ==
      identity match: True   route match: True   misses match: True -> IDENTICAL

    ALL_LIMBS_PASS=True

Every number this leg's own script produced matches RUNLOG-1.txt's stated
figures exactly (identity digests, miss percentages, p95 milliseconds,
cost ratios); nothing here contradicts builder 2, this is an independent
re-derivation from the same off-repo bytes, not a copy.

## 3. LIMB VERDICTS

  IDENTITY (stop-ship): PASS, all 5 runs, both artifacts, re-verified by
  this leg's own sha256 re-hash against a fresh re-hash of the OB-1
  reference (not a digest taken on faith from either document).

  A/A (reproducibility): PASS. dyn-k16-code-a vs dyn-k16-code-b:
  identical identity artifact, identical route log, identical miss count
  (452228 both), re-confirmed by this leg.

  MISS RATE (report-only, bar: within 2.0 percentage points of the
  simulator): PASS with the gap at exactly zero in all 5 rows, not merely
  within bar. The engine and the committed model of it print the same
  integer every time, over 3145728 picks each run. Taken with the unit's
  byte-identical 384-boundary schedule trace (RUNLOG-1.txt section 6,
  TRACE_MATCH=PASS, both sides hash
  5e97bc27afc2502ee7b8316c60ec8186107f964e9ea030c8f7a8696c7330cc45), the
  live engine and the frozen simulator are the same function, not two
  functions that happen to agree on a scalar.

  COST (bar: leased p95 <= 3.0x OB-1's per-corpus fully-resident
  baseline): PASS, all 5, ratios 1.4188x to 1.6488x, independently
  recomputed by this leg from raw chunk_ns and matching RUNLOG-1.txt
  exactly. Read as an UPPER BOUND per deviation D1 (8 threads here vs
  OB-1's 10): a thread-matched comparison could only move these numbers
  down, never up.

## 4. HEADLINE DELTA TABLE (static vs dynamic, same K, same corpus --
   the delta IS the result)

Static rows: research/OB1-EXPOSURE-1.md section 4 (K=16, K=8; the OB-1
acceptance receipt, itself independently re-verified against RUNLOG). All
runs 32768 tokens, 3145728 router picks, identical corpora
(AC-PROSE.txt/AC-CODE.txt), identical model, identical -b/-ub 1024.

  K   corpus  policy   miss_pct   delta_pp   rel_cut   p95_ratio    ident
  16  code    static   60.5733%     --         --      1.2907x      PASS
  16  code    dynamic  14.3759%   -46.1974pp   76.3%    1.6143-1.6424x PASS
  16  prose   static   18.8048%     --         --      1.2536x      PASS
  16  prose   dynamic  14.9343%   -3.8705pp    20.6%    1.4188x      PASS
  8   code    static   79.7325%     --         --      1.5139x      PASS
  8   code    dynamic  36.3824%   -43.3501pp   54.4%    1.6488x      PASS
  8   prose   static   42.3153%     --         --      1.4145x      PASS
  8   prose   dynamic  36.7640%   -5.5513pp    13.1%    1.6173x      PASS

rel_cut = delta_pp / static_miss_pct, this leg's own division, matching
RUNLOG-1.txt section 9's stated percentages (76.3, 54.4, 20.6, 13.1) to
the tenth.

READ: at K=16 the OUT-OF-DOMAIN case is where the dynamic policy wins
biggest (76.3% relative cut) and the domain-transfer gap that was OB-1's
headline finding is gone -- dynamic code (14.38%) is now marginally
EASIER than dynamic prose (14.93%), where static code was 3.2x WORSE than
static prose. The same-domain (prose) win is real but smaller (20.6% at
K=16, 13.1% at K=8): the static set's home-court advantage from being
ranked on a disjoint prose log does not survive against a policy that
adapts to the SAME run's own traffic, on either corpus. p95 cost rose
(1.25-1.51x static to 1.42-1.65x dynamic) but stayed well inside the 3.0x
bar throughout; the extra cost is the per-256-token top-K re-rank plus
promotion/eviction bookkeeping, not disk I/O (section 7).

## 5. SIM-VS-LIVE AGREEMENT (why "the same function" is not rhetoric)

Two independent checks, both PASS, both exact rather than within-bar:

  UNIT SCHEDULE TRACE (RUNLOG-1.txt section 6): K=16, AC-CODE, first 4096
  tokens. The engine's own OB2_TRACE dump and the committed simulator's
  walk, sorted the same way and compared byte for byte: 384 boundaries (24
  layers x 16), both sides hash
  5e97bc27afc2502ee7b8316c60ec8186107f964e9ea030c8f7a8696c7330cc45. Every
  one of 384 resident-set decisions matched, not just the miss count they
  produced.

  ENGINE-SHAPED DRY RUN (RUNLOG-1.txt section 7): before any model
  process ran, research/ob2/engine_walk_check.py re-expressed the
  engine's actual loop shape (ubatch-major, carried per-layer state,
  boundaries split inside a ubatch, the awkward case the flat simulator
  never faces) and replayed it over the full 32768-token banked route
  log: misses=452228, churn=9116, boundaries=3072, AGREE=PASS exact
  against the committed simulator. This is why the live matrix needed
  zero debug rounds.

Both checks are read from committed digests and script output, not
retyped from RUNLOG's prose.

## 6. WHAT THE POLICY ACTUALLY DID (RUNLOG-1.txt section 9, carried
   forward)

  run              K  boundaries  churn  promotions  evictions  transient  phys_max  phys_mean
  dyn-k16-code-a  16       3072   9116        2022          2      11799        32     31.363
  dyn-k16-prose   16       3072  10394        2340         30      10872        32     30.156
  dyn-k8-code      8       3072   5966        1409          1      17940        32     31.359
  dyn-k8-prose     8       3072   7356        1655          2      16971        32     30.098

Churn is cheap: about a fifth of symmetric-difference events at K=16
become actual promotions (the rest cancel within the same window). The
policy is domain-blind by construction (churn and promotion counts are
close across prose and code at a given K), which is the point.

## 7. EXPOSURE: PEAK AND MEAN POOL BYTES, BOTH BASES (report-only, per
   house measurement-language law -- new in this receipt)

Constants (research/ob1/OB1-EXPOSURE-1-PREREG.md section 8, re-used
unmodified): LOGICAL=12109566624, RESIDENT_ALWAYS=1930678944,
PER_EXPERT_BYTES_PER_LAYER=13253760, L=24.

Dynamic residency has time-varying membership (WHICH experts are
resident changes every H=256 tokens), but that is not the same claim as
time-varying POOL SIZE, and this section is careful not to conflate the
two. Two whole-model pool-bytes figures are computed, each with an
explicit, checkable derivation:

  PEAK pool = RESIDENT_ALWAYS + K x L x PER_EXPERT + peak_concurrent_lease_bytes.
  This is the engine's own measured worst-case simultaneous transient-lease
  burden for whichever ONE layer is being computed at that instant, added
  to the K-per-layer resident sets, which genuinely ARE concurrent across
  all 24 layers throughout a run (the whole point of "resident"). This is
  the same ACCT_bytes formula OB-1 froze; it is NOT re-derived differently
  here, only re-verified.

  MEAN pool = RESIDENT_ALWAYS + K x L x PER_EXPERT + (physneed_mean_experts - K) x PER_EXPERT.
  physneed_mean_experts is the engine's own per-layer, per-ubatch mean of
  the union of resident+transient experts needed (ob2-stats.txt,
  ob2_physneed_mean_experts). Subtracting K isolates the TRANSIENT portion
  of that mean and applies it to one active layer at a time -- the same
  single-active-layer model as the peak formula, consistent with the
  engine's own design (a layer's transient leases are dropped before the
  next layer's routing is computed, RUNLOG-1.txt section 5). A naive
  physneed_mean x 24 x PER_EXPERT was considered and REJECTED: it would
  assume all 24 layers' transient pools sit in RAM simultaneously, which
  the engine's own drop-before-next-layer design contradicts, and would
  overstate the mean pool by roughly 24x on the transient term alone.

Literal output (this leg's verify-acceptance.py, section 2):

  run              K     peak_pool  EXP_peak      mean_pool  EXP_mean       RSS_peak   EXP_rss
  dyn-k16-code-a  16    7232182944  1.674400   7223744023.2  1.676356    8453492736  1.432493
  dyn-k16-code-b  16    7232182944  1.674400   7223744023.2  1.676356    8453492736  1.432493
  dyn-k16-prose   16    7232182944  1.674400   7207746324.0  1.680077    8431726592  1.436191
  dyn-k8-code      8    4793491104  2.526252   4785000414.0  2.530735    6018863104  2.011936
  dyn-k8-prose     8    4793491104  2.526252   4768277893.2  2.539610    5998309376  2.018830

Static (OB-1) comparison at the same K, from research/ob1/RUNLOG-1.txt
section 4 and research/OB1-EXPOSURE-1.md section 3 (recomputed by this
leg from the same literals, matches both documents):

  K   static EXP_peak(ACCT)   static EXP_rss (code / prose)
  16  1.674400                1.432742 / 1.435663
  8   2.526252                2.012048 / 2.017932

FINDING: at this batch size (-b/-ub 1024), the peak-pool exposure basis
is IDENTICAL between static and dynamic at the same K, by construction --
both formulas reduce to the same K-sized resident term plus the same
peak_concurrent_lease_bytes, which came out numerically equal for both
policies because a 1024-token micro-batch drives the transient term to
its ceiling ((32-K) experts, the worst case) regardless of which K
experts the policy calls resident. The mean-pool and RSS exposure bases
tell the same story to within 0.3%: this leg's mean-pool EXP_mean
(1.676-1.680 at K=16, 2.531-2.540 at K=8) and OB-1's static EXP_rss
(1.433-1.436, 2.012-2.018) sit in the same neighborhood as this leg's own
dynamic EXP_rss (1.432-1.436, 2.012-2.019). THE MISS-RATE WIN IS NOT A
MEMORY-EXPOSURE WIN AT BATCH 1024. This confirms RUNLOG-1.txt section 9's
finding independently, from a different (whole-model pool-bytes, not
bytes-moved-per-token) accounting.

## 8. DECODE-SHAPE REPLAY (ubatch=1; no model process; RUNLOG-1.txt
   section 9's replay, re-derived here with the same peak/mean pool
   method as section 7, for comparability)

At -ub 1 (a real decode step, one token at a time), the bound per layer
is exactly K+4 (the resident set plus that token's own 4 router picks),
measured by replaying the frozen policy over the banked route logs
(research/ob2/engine_walk_check.py, AGREE=PASS exact against the
simulator in all four cases, no runlock needed):

  K   corpus  phys_max(=K+4)  phys_mean  dyn EXP_peak  dyn EXP_mean  static EXP_peak  static EXP_mean
  16  code    20               16.5750    1.712050      1.723109      1.712050         1.717124
  16  prose   20               16.5974    1.712050      1.723036      1.712050         1.722533
  8   code    12                9.4553    2.674129      2.694195      2.674129         2.680489
  8   prose   12                9.4706    2.674129      2.694073      2.674129         2.692311

(static EXP_peak/EXP_mean here use the same peak/mean pool formula as
section 7, with the transient term for static computed from its own
per-(layer,token) mean miss count: total static misses / 786432,
e.g. code K=16: 1905471/786432=2.4230 average missed picks out of 4 per
layer per token, against dynamic's 0.575.)

FINDING, distinct from and complementary to section 7: at decode
granularity, the PEAK exposure is identical between static and dynamic
(both bounded at exactly K+4, the same formula, same number) -- but the
MEAN exposure is measurably better for dynamic on every row (e.g. K=16
code: dynamic mean transient 0.575 experts vs static's 2.423, a policy
that has usually already loaded what is coming next, against one that
has not). This is the same phenomenon the load-count ratio already
reports (RUNLOG-1.txt section 9), stated instead in memory-pool terms:

  K   corpus  expert-loads(dyn)  expert-loads(static=its misses)  ratio
  16  code    456515             1905471                          4.174x fewer
  16  prose   474711             591548                           1.246x fewer
  8   code    1147145            2508167                           2.186x fewer
  8   prose   1159785            1331123                           1.148x fewer

These two accountings answer different questions and are kept separate
deliberately (RUNLOG-1.txt section 9 makes the same point): pool-bytes
exposure measures how much must be SIMULTANEOUSLY resident; expert-loads
measures how many DISK READS happen over the whole run. A policy can cut
load count sharply (fewer distinct experts fetched over time) while its
peak simultaneous footprint stays capped at the same K+4 ceiling a static
set would also hit in the worst case -- which is exactly what these
numbers show.

## 9. HONEST LIMITATIONS

  BATCH GRANULARITY, NOT DECODE, IS WHAT WAS ACTUALLY MEASURED LIVE. The
  five acceptance runs (section 4) used -b/-ub 1024 because that is what
  OB-1's own baseline used and the identity/route comparison requires the
  same batching on both arms. Section 8's decode-shape numbers are a
  REPLAY over banked route logs, not a live measurement; no model process
  ran at ubatch=1 under this policy. Turning the decode-shape memory
  result into a live number is future work (RUNLOG-1.txt section 12,
  item 1).

  HISTORY-WARMUP TRANSIENT. The unit's first 4096 tokens (cold start,
  lowest-K-ids residency) missed 16.66%, above the full-run 14.38%
  figure (RUNLOG-1.txt section 6). A run shorter than a few thousand
  tokens would see a worse miss rate than these numbers promise; the
  32768-token acceptance runs are long enough that the cold-start tail is
  a small fraction of the total, but this receipt does not claim the
  policy is warmup-free.

  SINGLE MODEL, SINGLE BOX. Every number in this document is gpt-oss-20b
  MXFP4 (sha256 27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901)
  on f32-HYDE, CPU-only (-ngl 0), 8 threads. Router geometry (L=24, E=32,
  k=4), expert size (13253760 bytes/layer), and even the constant H=256
  are specific to this model; nothing here has been tested on a second
  model or a second box.

  TWO CORPORA, ONE SOURCE. AC-PROSE and AC-CODE (research/ob1's own
  acceptance corpora) are the only traffic tested. "Domain-blind" is
  demonstrated between exactly these two domains, not proven in general.

  THE COST BAR COMPARISON IS AN UPPER BOUND, NOT A LIKE-FOR-LIKE RATIO
  (deviation D1, both builder 2's and this leg's own re-verification):
  8 threads here vs OB-1's 10 for the fully-resident baseline. The
  absolute p95 numbers are honest; the RATIOS are conservative (a
  thread-matched baseline could only lower them).

  BYTE MOVEMENT AT UBATCH GRANULARITY (deviation D2, inherited from
  OB-1's D3): one mul_mat_id call needing 1024 tokens' worth of routing
  drives phys_mean to 30.1-31.4 of 32 experts regardless of policy,
  which is exactly why section 7 finds no batch-1024 exposure win even
  though the miss rate falls sharply.

  MADVISE DROPS ONLY WHOLE INTERIOR PAGES (deviation D3, inherited from
  OB-1's D4): a 0.32% shortfall between bytes leased and bytes dropped,
  measured on K=16/AC-CODE (156407621760 leased vs 155913744384 dropped).

  A DRIVER BUG AND A HARNESS INTERRUPTION, BOTH RECOVERED WITHOUT DATA
  LOSS (deviations D4, D5): a shell prefix-assignment parsing bug caught
  by its own exit 127 before any model process started (no measurement to
  doubt); a harness interruption during the fifth run, finished cleanly
  by a pre-armed detached supervisor that skipped four already-complete
  runs on a completeness test and re-ran the fifth from scratch, never
  touching guard pids 654/489 or stealing the runlock from the sibling
  OB-3 workflow. Full detail: RUNLOG-1.txt section 11.

  FULL-RUN SCHEDULE EQUALITY RESTS ON MISS-COUNT AGREEMENT, NOT A FULL
  TRACE COMPARE (deviation D6): the byte-for-byte schedule trace (section
  5) covers the unit's first 4096 tokens (384 boundaries); the full
  32768-token runs' equality claim rests on 5 exact miss-count matches
  over 3145728 picks each, which RUNLOG-1.txt states plainly is not the
  same strength of evidence as a full compare, and names the 14-minute
  cost of the stronger form if wanted.

  THE RESEARCH-2 WORKTREE IS SHARED IN PRACTICE. Builder 2 flagged that
  a concurrent OB-1b sibling leg committed into this same worktree
  (commits 7190b7a, a782231) despite the house brief's stated isolation
  assumption. This leg's own `git status` at start showed one further
  OB-1b file modified and two untracked OB-1b files (research/ob1b/*),
  none of which this leg touched, staged, or committed; this receipt
  commits only research/ob2/verify-acceptance.py and this file.

## 10. HELD MENU (not adopted, named for the architect)

  1. LIVE DECODE-SHAPE MEASUREMENT. Section 8's memory-exposure win is a
     replay, not a live number. A leg that runs the policy at -ub 1 on
     the real model would turn "up to 4.17x fewer loads, mean exposure
     measurably better" into a live-measured result rather than a
     route-log replay.

  2. WARM-START SEEDING. RUNLOG-1.txt section 12 item 3: seed the
     counters from a banked profile instead of the lowest-K-ids cold
     start. Needs its own prereg since seeding from a profile
     reintroduces the domain assumption this policy was built to remove;
     the honest comparison is cold-start miss rate (this receipt) vs
     seeded miss rate on the SAME corpus, not vs a different corpus's
     static set.

  3. H AND SHIFT TUNING AGAINST LIVE COST. H=256 and shift=1 were frozen
     from the simulator, never tuned against measured promotion cost.
     RUNLOG-1.txt section 12 item 2 notes churn (9116-10394 events per
     run at K=16) is cheap but not free; if a decode leg finds promotion
     cost material, these are the two dials.

  4. THREAD-MATCHED COST RE-RUN. Re-run the cost limb at 10 threads (OB-1
     parity) to convert the upper-bound ratios in section 4 into a
     like-for-like number.

  5. A THIRD CORPUS. Domain-blindness is currently a two-domain claim
     (prose, code); a third, structurally different corpus would harden
     or break it.

## 11. ARTIFACTS AND DIGESTS

Committed to research/ob2/ on branch research-2, this leg:

  verify-acceptance.py   sha256 61d5df8b832782c18a83b303b87c798cc8dc8a488592c33b06060cb741746f8f

Committed to research/ (this file):

  research/OB2-PREDICTIVE-1.md   (this file)

Inputs, re-verified not re-copied (this leg's own commands, section 2):
  research/OB2-PREDICTIVE-1-PREREG.md (builder 1, commit 0a6d6843e395fa019dcb3ebe6857fc19074d149a)
  research/ob2/RUNLOG-1.txt, policy-engine.patch, sim_residency.py,
    sim_trace.py, engine_walk_check.py, SIM-PROSE-TABLE-1.txt,
    SIM-CODE-TABLE-1.txt (builder 2, commit 37f1080), all digests re-hashed
    by this leg and matched to RUNLOG-1.txt section 10's stated values.

Off-repo, this leg's own stage subdirectory per house law
(/mnt/f/f32/stage/research/ob2/): unmodified, read only. The five dyn-*
run directories and the unit-k16-code directory this leg re-hashed live
there; nothing was written to them.

Worktree state at commit time: `git status --porcelain` showed one
modified and two untracked files under research/ob1b/, belonging to the
concurrent OB-1b sibling leg (section 9); this leg's commit touches only
research/ob2/verify-acceptance.py and research/OB2-PREDICTIVE-1.md.

## 12. VERDICT

OB-2's question is answered YES: P2 DECAY-COUNTER, a deterministic,
four-integer-operation-per-boundary policy frozen by simulation before
any engine existed, cuts out-of-domain (code) misses at K=16 from
60.5733% to 14.3759% (76.3% relative), removes OB-1's domain-transfer
gap, and does so with byte-identical output in every one of 5 leased
runs, an exact (not within-bar) match between the live engine's miss
count and the frozen simulator's prediction, and a byte-identical
384-boundary schedule trace proving the two are the same function. The
honest caveat, independently reconfirmed by this leg with a whole-model
peak/mean pool-bytes accounting rather than only a bytes-moved-per-token
one: at the batch-1024 granularity actually measured live, this is a
miss-rate win and not yet a memory-exposure win (peak and mean exposure
both land within 0.3% of static's). At decode granularity (replayed, not
live), the peak exposure ceiling is unchanged from static (both bounded
at K+4) but the mean exposure is measurably better, consistent with the
load-count reduction already reported. All limbs this leg re-verified
independently agree with builder 2's own numbers to the last digit; this
receipt introduces no new disagreement, only a new, honest accounting.

END OB2-PREDICTIVE-1
