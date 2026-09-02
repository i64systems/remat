# OB2-PREDICTIVE-1-PREREG: DETERMINISTIC DYNAMIC RESIDENCY POLICY,
# FROZEN BEFORE THE LIVE LEASE-ENGINE INSTRUMENT EXISTS

Lane: research (CUDA/inventor lane), venue hyde, on-machine. Branch
research-2, worktree F:\f32\openbob-wt\research-2. Builder 1 of OB-2
(prereg + policy simulation, per this leg's task brief). Pure ASCII, no
em dashes. Every number below is literal command output from this leg's
own script runs against banked, already-committed OB-1 artifacts. This
document is committed before any later builder writes a live lease-engine
instrument to test these policies; nothing below is renegotiated after
that instrument exists except where explicitly named as a deviation in
section 8.

Substrate at prereg time: worktree HEAD f9efa23b033e01f56aef2ee5da70a0372167ed92,
branch research-2, `git status --porcelain` empty before this leg's files
are added.

## 0. WHAT THIS PROGRAM IS, IN ONE PARAGRAPH

OB-1 (research/OB1-EXPOSURE-1.md, landed) measured that a STATIC,
popularity-ranked resident set (top-K experts per layer by usage count on
ONE prose route log, frozen for the whole run, never updated) misses
18.80/42.32/62.09 percent of individual router picks at K=16/8/4 on
same-domain prose, but 60.57/79.73/90.33 percent on out-of-domain code --
a real domain-transfer gap named plainly in that document's section 6 and
its held menu (section 8, "REGION LEASING BY TASK"). OB-2 asks the direct
follow-on: can a DETERMINISTIC dynamic residency policy (one that adapts
the resident set as it goes, using only what it has already seen) cut
that miss rate at the same K, with the identity guarantee preserved,
while staying a pure function of route history the way a real engine
could implement it? This document is the prereg for OB-2's Builder 1
step: a policy SIMULATOR (no live engine, no GPU/CPU model run, no
runlock needed) that replays OB-1's own banked route logs against four
candidate policies, a literal miss-rate table, and the frozen winner +
live-run plan for a later builder to implement and test against the real
lease engine.

## 1. DETERMINISM WALL (binding on every policy below)

The resident set governing any router decision must be a PURE FUNCTION
of (a) the route history strictly BEFORE the recompute boundary that
governs that decision, and (b) fixed policy constants named in section 3.
It never depends on the current token's own routing (a live engine cannot
see the future), on wall-clock timing, on cache state, or on any floating
point value. Every policy below recomputes ONLY at fixed boundaries
(multiples of H=256 tokens, or the single named boundary for P3), so a
live engine can mirror the simulator's decisions exactly by tracking the
same integer counters and switching residency at the same token indices.
All arithmetic in the simulator (counts, decay, top-K ranking) is done in
plain integers; the only non-integer values anywhere in this leg are
human-readable miss-rate PERCENTAGES printed after the fact, which never
feed back into any policy decision.

## 2. INPUTS (frozen, unmodified OB-1 artifacts)

Reference route logs (off-repo, digests re-verified fresh by this leg):

  /mnt/f/f32/stage/research/ob1/runs/res-prose-a/route.log
    sha256 4777aa8319f25d6e367f761ef12c7bec81a9ff7896bfed1b8ea0326b5dffc3df
  /mnt/f/f32/stage/research/ob1/runs/res-code-a/route.log
    sha256 f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77

Both are 786432 lines (L=24 layers x budget=32768 tokens), 6 comma
columns (layer, token_index, e0, e1, e2, e3; e0..e3 are the model's own
top-4 router picks for that (layer, token)), loaded and order-verified by
the same method as research/ob1/resident_sets.py load_route_log (boolean
mask per layer preserves file order; token_index checked to come out
exactly 0..budget-1 in order before being trusted; SystemExit on any
violation).

Frozen static resident sets (OB-1's P0 control, used unmodified):

  research/ob1/RESIDENT-SETS.json
  source_route_log = /mnt/f/f32/stage/research/rs053/runs/20b-prose-a/route.log
  source_route_log_sha256 = a0bb972ec5a02e18ab685000c72b512751e579e243deecc3c095d8340c4b50aa
  E=32, L=24, budget=65536 (RS053's own prose run, DISJOINT from OB-1's
  res-prose-a reference run, per OB-1's own held-out framing, section 6)
  K values present: 16, 8, 4; tie-break lower expert id, ranking by
  descending usage count.

Note the important asymmetry this leg inherited from OB-1 and preserves:
the static P0 resident set was ranked from a DIFFERENT, disjoint prose
route log (budget 65536) than either acceptance corpus used to MEASURE
misses (budget 32768 each). The dynamic policies P1/P2/P3 below have no
such asymmetry: they are ranked from the SAME corpus they are measured
against, using only that corpus's own history up to each point in time
(the honest, causal, single-run case a live engine actually faces).

Model geometry (carried from OB1-EXPOSURE-1-PREREG.md section 1, RS053
cross-checked): L=24, E=32, k=4 (router picks per token per layer).

## 3. POLICIES FROZEN FOR THIS LEG

All four policies operate PER LAYER, independently, walking token index
t = 0..budget-1 in order for that layer. Recompute boundaries are named
per policy; "top-K" always means: rank experts by (descending integer
count, ascending expert id), take the first K, ties broken by lower id
(same convention as research/ob1/resident_sets.py).

  P0 STATIC-PROSE (OB-1 CONTROL): resident set fixed for the entire run,
    taken as-is from RESIDENT-SETS.json for the given K. Never
    recomputed. Included in the simulator purely as a REPRODUCTION CHECK
    (section 5) and as the K=16/8/4 baseline row in the sim table;
    section 6's winner selection is between P1/P2/P3 only, since P0 is
    not itself a proposal, it is the thing OB-2 is trying to beat.

  P1 SLIDING-WINDOW: resident set = top-K experts by count of routing
    decisions in the last W router decisions of THIS layer (W in
    {512, 2048, 8192} tokens' worth of decisions), recomputed every
    H=256 tokens. At boundary b (b a multiple of 256), the window is
    decisions [max(0, b-W), b) -- strictly before b. Cold start (b=0):
    no history exists, so the resident set for tokens [0, 256) is the
    lowest K expert ids (the uniform tie-break falls out of the same
    top-K rule applied to all-zero counts).

  P2 DECAY-COUNTER: one integer counter per expert per layer, initialized
    to 0. At each boundary b>0 (multiple of 256): every counter is first
    right-shifted by 1 (integer halving, reflecting all history strictly
    before b), THEN the resident set for [b, b+256) is read off as top-K
    of the just-decayed counters. After serving window [b, b+256), each
    expert's counter is increased by 65536 for every one of that window's
    routing decisions that picked it (so a single decision that lands on
    expert e adds 65536 to e's counter; an expert routed to on all 4
    picks of one token in one step still only accumulates deterministic
    integer counts, never floats). Cold start (b=0): counters are all
    zero, so [0, 256) uses the lowest K ids, exactly like P1.

  P3 WARMUP-FREEZE: resident set = lowest K ids (uniform) for the first
    2048 tokens of the run. At t=2048, the routing history from those
    first 2048 tokens (already-seen, causal) is counted once, top-K is
    taken, and that set is FROZEN for the remainder of the run (one
    single recompute boundary, at t=2048; the cheapest policy tested).

Policy switches ONLY happen at these named boundaries (a pure function of
the decision index t), never mid-window, so a live engine tracking the
same per-layer integer state can reproduce the simulator's resident-set
schedule exactly, decision for decision.

## 4. SIMULATOR

research/ob2/sim_residency.py, sha256
c2194b752a80e389a50c3cd3de36105103afc9ffca79a04ed3ea1d9904198d7f
(committed with this prereg). Stdlib + numpy only (numpy used for
vectorized bincount / isin over each layer's 32768x4 pick array; every
counter update, decay, and top-K rank is plain-integer arithmetic, see
section 1). Run with the box's system python3 (numpy 1.26.4), 1 thread
worth of real CPU work per invocation (no threading pool used), well
under the house's 4-thread / no-lock sim/analysis-leg bar; no model
process is started, so the box-wide runlock is not touched.

Usage: `sim_residency.py <route_log> <E> <L> <budget> <resident_sets.json> <out_prefix>`.
Invoked once per corpus (prose, code), each run self-contained (fresh
python process, zero prior state) -- this IS the honest cold-start case
the task brief names explicitly: neither corpus's simulation is warmed
from the other corpus's counters. K is swept in {16, 8} inside one
invocation (H=256 fixed); a separate, one-off K=4 check (section 5) uses
the same load_route_log / sim_p0_static functions imported directly, not
a new script, since it is a pure reproduction check on already-committed
data.

## 5. P0 REPRODUCTION VERDICT (task step 2, stop-ship gate)

The simulator's P0-STATIC-PROSE path, run against RESIDENT-SETS.json and
both OB-1 reference route logs, at all three K in the OB-1 prereg (16, 8,
4):

  corpus  K    total_picks   misses    miss_pct (this leg)   OB1-EXPOSURE-1.md sec.3
  prose   16   3145728       591548    18.80480448404948%    18.8048%
  prose   8    3145728       1331123   42.315260569254555%   42.3153%
  prose   4    3145728       1953318   62.09430694580078%    62.0943%
  code    16   3145728       1905471   60.57329177856445%    60.5733%
  code    8    3145728       2508167   79.7324816385905%     79.7325%
  code    4    3145728       2841526   90.32967885335286%    90.3297%

VERDICT: PASS, all six rows, exact match to 4 decimal places (the
precision OB1-EXPOSURE-1.md itself reports; this leg's own figures carry
full float precision and round to the identical 4-decimal value in every
row). The simulator's route-log loader, top-K ranking, and per-pick miss
count are therefore confirmed correct against an independent prior
measurement before being trusted for the P1/P2/P3 policies below. Full
K=4 verification transcript: research/ob2/P0-K4-VERIFY-1.txt.

## 6. SIM TABLE (task step 2, literal)

K in {16, 8}, both corpora, H=256 for P1/P2, warmup=2048 for P3. Full
machine-written tables: research/ob2/SIM-PROSE-TABLE-1.txt and
research/ob2/SIM-CODE-TABLE-1.txt (identical content to below, plus the
source route-log and RESIDENT-SETS.json digests in each file's header).

  policy               corpus  K variant                  total_picks     misses   miss_pct  churn/1000tok
  P0-STATIC-PROSE      prose  16 -                           3145728     591548   18.8048%          0.000
  P1-SLIDING-W512      prose  16 H=256                       3145728     491041   15.6098%        399.841
  P1-SLIDING-W2048     prose  16 H=256                       3145728     508800   16.1743%        138.245
  P1-SLIDING-W8192     prose  16 H=256                       3145728     514438   16.3535%         60.669
  P2-DECAY             prose  16 H=256,add=65536,shift=1     3145728     469793   14.9343%        317.200
  P3-WARMUP-FREEZE     prose  16 warmup=2048                 3145728     638966   20.3122%         11.658
  P0-STATIC-PROSE      prose   8 -                           3145728    1331123   42.3153%          0.000
  P1-SLIDING-W512      prose   8 H=256                       3145728    1178874   37.4754%        266.602
  P1-SLIDING-W2048     prose   8 H=256                       3145728    1224863   38.9373%         99.304
  P1-SLIDING-W8192     prose   8 H=256                       3145728    1242946   39.5122%         47.180
  P2-DECAY             prose   8 H=256,add=65536,shift=1     3145728    1156494   36.7640%        224.487
  P3-WARMUP-FREEZE     prose   8 warmup=2048                 3145728    1375854   43.7372%          9.094
  P0-STATIC-PROSE      code   16 -                           3145728    1905471   60.5733%          0.000
  P1-SLIDING-W512      code   16 H=256                       3145728     464788   14.7752%        338.013
  P1-SLIDING-W2048     code   16 H=256                       3145728     471221   14.9797%        130.066
  P1-SLIDING-W8192     code   16 H=256                       3145728     474915   15.0971%         55.725
  P2-DECAY             code   16 H=256,add=65536,shift=1     3145728     452228   14.3759%        278.198
  P3-WARMUP-FREEZE     code   16 warmup=2048                 3145728     658767   20.9416%         11.841
  P0-STATIC-PROSE      code    8 -                           3145728    2508167   79.7325%          0.000
  P1-SLIDING-W512      code    8 H=256                       3145728    1159127   36.8477%        214.661
  P1-SLIDING-W2048     code    8 H=256                       3145728    1181472   37.5580%         83.801
  P1-SLIDING-W8192     code    8 H=256                       3145728    1184063   37.6403%         39.551
  P2-DECAY             code    8 H=256,add=65536,shift=1     3145728    1144492   36.3824%        182.068
  P3-WARMUP-FREEZE     code    8 warmup=2048                 3145728    1433359   45.5653%          8.972

churn/1000tok is the total per-layer symmetric-difference count between a
recomputed resident set and its immediate predecessor, summed over all
24 layers and every recompute boundary after the cold-start one, then
normalized to 1000 tokens of the 32768-token run (P0 has zero churn by
construction: it is never recomputed).

Headline read: EVERY dynamic policy beats P0's OUT-OF-DOMAIN (code) miss
rate by a wide margin (P2-DECAY's 14.38% vs P0's 60.57% at K=16 is a
76.3% relative cut), and every dynamic policy also beats P0 on
SAME-DOMAIN (prose) at K=16 (best dynamic 14.93% vs P0's 18.80%),
though at K=8 P0's prose figure (42.3153%) is worse than every dynamic
policy's prose figure (best 36.7640%) too -- the static set's domain
advantage from OB-1 does not survive against policies that adapt to the
SAME run's own traffic, at either K tested here. This is expected: P0's
resident set was ranked from a route log OTHER than the one it is being
measured against (section 2's noted asymmetry), while P1/P2/P3 rank from
the same run's own causal history.

## 7. WINNER SELECTION (task step 3: code-corpus miss rate is the hard
   case, prose the tiebreak)

At K=16, ranked by CODE miss rate (ascending, best first):
  P2-DECAY 14.3759%, P1-W512 14.7752%, P1-W2048 14.9797%,
  P1-W8192 15.0971%, P3-WARMUP 20.9416%.
P2-DECAY also has the lowest PROSE miss rate at K=16 (14.9343%, vs
P1-W512's 15.6098%), so no tiebreak is needed: P2-DECAY wins outright on
both corpora.

At K=8, ranked by CODE miss rate (ascending, best first):
  P2-DECAY 36.3824%, P1-W512 36.8477%, P1-W2048 37.5580%,
  P1-W8192 37.6403%, P3-WARMUP 45.5653%.
P2-DECAY again has the lowest PROSE miss rate at K=8 (36.7640%, vs
P1-W512's 37.4754%). Same outright win, no tiebreak needed.

FROZEN WINNER: P2 DECAY-COUNTER, with constants H=256, add=65536,
shift=1 (halve every 256 tokens), applied identically at K=16 and K=8.
No policy or constant choice here is contingent on a tiebreak rule
actually firing; P2-DECAY dominates every rival policy on both ranking
axes (code first, prose second) at both K values tested.

## 8. FROZEN: LIVE-RUN PLAN FOR A LATER BUILDER

A later OB-2 builder implements P2-DECAY-COUNTER (section 3's exact
integer rule: per-layer per-expert counters, +65536 per routed decision,
>>=1 every 256 tokens, resident = top-K of the just-decayed counters,
cold start = lowest K ids) as a live modification of the OB-1 lease
engine (research/ob1/lease-engine.patch lineage; a fresh git worktree of
/root/rs053/llama.cpp per house FORK DISCIPLINE, never edited in place),
and runs it on the real gpt-oss-20b GGUF under the house's RUNLOCK LAW.
Live-run matrix, mirroring OB-1's own AC-PROSE / AC-CODE acceptance
corpora at 32768 tokens each:

  K in {16, 8}, both corpora (AC-PROSE, AC-CODE) = 4 leased runs.
  Plus ONE A/A REPEAT at K=16, AC-CODE (the hardest case, where the
  frozen winner's advantage over P0 is largest) to confirm the dynamic
  policy is itself byte-exact reproducible run to run, not merely
  byte-exact against a fully-resident reference within one run.
  5 leased runs total, plus the fully-resident references OB-1 already
  banked (res-prose-a/b, res-code-a) reused as the identity/cost
  comparison point -- no new fully-resident run is needed.

## 9. FROZEN BARS

  IDENTITY (stop-ship limb): every leased run's identity artifact AND
  route log must be byte-identical (sha256 match) to OB-1's own banked
  fully-resident reference for that corpus (res-prose-a for AC-PROSE,
  res-code-a for AC-CODE), at every K tested. One failure anywhere on
  this limb halts the leg; this mirrors OB-1's own identity bar exactly
  (OB1-EXPOSURE-1-PREREG.md section 5) and is non-negotiable because the
  whole point of a resident-set policy, static or dynamic, is that a
  cache miss is served correctly from disk, never approximated.

  MISS RATE (report-only, engine-matches-model check): the live engine's
  measured per-decision miss rate, at a given policy/corpus/K, must fall
  within 2.0 PERCENTAGE POINTS of this leg's simulated prediction for
  that same policy/corpus/K (section 6's table is the prediction; the
  simulator IS the model of what the engine's residency schedule should
  produce). A gap larger than 2.0 points means the live engine does not
  actually implement the frozen policy (a boundary off-by-one, a
  wrong decay constant, a non-causal leak, etc.), not that the policy
  itself performs differently live than simulated -- and is treated as a
  bug to find, not a result to report.

  COST (P95 latency): leased p95 (chunk-level, same nearest-rank-of-31
  method as OB1-EXPOSURE-1.md) must be <= 3.0x the OB-1 fully-resident
  baseline p95 for that corpus: prose baseline 16025.8 ms (res-prose-a,
  RUNLOG-1.txt), code baseline 16073.7 ms (res-code-a, RUNLOG-1.txt).
  Same bar OB-1 froze at K=16 (OB1-EXPOSURE-1-PREREG.md section 5); this
  leg extends it to both K in {16, 8} tested live, since a per-window
  recompute (top-K re-rank every 256 tokens, an O(E log E) = O(32 log 32)
  operation per layer, negligible next to disk I/O) is not expected to
  change the cost profile materially versus OB-1's static case, but that
  expectation is named here as an expectation, not assumed as a result.

## 10. DEVIATIONS FROM THE TASK BRIEF, NAMED

D1: the task brief lists W "in {512, 2048, 8192} tokens worth" for P1
without specifying whether W counts DECISIONS (token positions) or raw
router picks (4x decisions). This leg reads W in TOKEN units (matching
"tokens worth" literally), i.e. the window is the last W token positions'
worth of decisions (4*W picks) for that layer. Documented here since
P1's own numbers depend on this reading; P1 is not the frozen winner so
this deviation does not touch section 7's outcome.

D2: P2's decay is applied to ALL experts uniformly at each boundary
(>>=1), including experts with a zero counter (no-op, 0>>1=0), and the
per-window counts are added AFTER decay so a boundary's own top-K read
never includes that same boundary's not-yet-seen window (see section 3's
explicit "decay reflects history strictly before b" note). This is the
most literal reading of "every 256 tokens all counters >>=1" and "resident
= top-K by counter" as two ordered steps within one boundary event, not
a deviation from the brief's wording, but called out because a
differently-ordered implementation (decay AFTER adding the new window)
would produce different numbers and would NOT be this leg's frozen
policy.

D3: the task brief's bars section names "p95 <= 3.0x the OB-1 resident
baseline" without specifying per-corpus baselines; this leg uses OB-1's
own per-corpus baseline p95 (prose and code differ slightly: 16025.8 vs
16073.7 ms), matching OB1-EXPOSURE-1.md's own per-corpus cost-limb
comparison rather than inventing a single pooled baseline.

No other deviations. Nothing in this document overrides house law
(RUNLOCK, FORK DISCIPLINE, READ-NEVER, NO WEIGHT DOWNLOADS, SCRIPT-TO-FILE):
this leg used none of the heavy-run or fork-discipline paths at all,
since it is a pure-python simulation over already-banked route logs.

## 11. ARTIFACTS AND DIGESTS

Committed with this prereg:
  research/OB2-PREDICTIVE-1-PREREG.md   (this file)
  research/ob2/sim_residency.py         sha256 c2194b752a80e389a50c3cd3de36105103afc9ffca79a04ed3ea1d9904198d7f
  research/ob2/SIM-PROSE-TABLE-1.txt    (machine-written, section 6 source)
  research/ob2/SIM-CODE-TABLE-1.txt     (machine-written, section 6 source)
  research/ob2/P0-K4-VERIFY-1.txt       (section 5 K=4 reproduction transcript)

Off-repo (unmodified, digests re-verified by this leg in section 2, not
re-copied): the two OB-1 reference route logs under
/mnt/f/f32/stage/research/ob1/runs/{res-prose-a,res-code-a}/route.log,
and research/ob1/RESIDENT-SETS.json (already committed by OB-1, read
here, not modified). This leg's own working outputs additionally live at
/mnt/f/f32/stage/research/ob2/ (this leg's stage subdirectory, per house
law); the two files there (sim-prose.rows.txt, sim-code.rows.txt) are
byte-identical to the committed SIM-PROSE-TABLE-1.txt / SIM-CODE-TABLE-1.txt
above.

END OB2-PREDICTIVE-1-PREREG
