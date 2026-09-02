# OB3-REGION-1: TASK-CHOSEN RESIDENT SETS, ACCEPTANCE AND RECEIPT

Lane: research (CUDA/inventor lane), venue hyde, on-machine, worktree
F:\f32\openbob-wt\ob3, branch ob3, master untouched, nothing pushed. This is
builder 3 of OB-3 (acceptance + receipt). Pure ASCII, no em dashes. Every
number below is either literal output of a command this leg ran itself
against the off-repo run artifacts, or is carried forward from
research/OB3-REGION-1-PREREG.md (builder 1, frozen) or
research/ob3/RUNLOG-1.txt (builder 2's own run log) with its source named.

Binding documents, in order: research/OB3-REGION-1-PREREG.md (frozen before
the region-switching engine existed) and research/ob3/RUNLOG-1.txt (the
engine's own run log). This receipt does not repeat their full derivations;
it independently re-derives every digest, every miss rate and every p95
ratio the frozen bars are judged against, from the raw off-repo bytes, not
by copying either document's tables.

## 1. THE QUESTION

OB-1 (research/OB1-EXPOSURE-1.md) measured that a single, static,
popularity-ranked resident set of experts transfers badly across domains:
18.8048 percent per-decision miss rate on prose at K=16, but 60.5733
percent on code (42.3153 / 79.7325 at K=8), because the set was ranked once
from prose traffic and never updated. OB-1's own held menu named the
obvious next step: rank and swap resident sets per detected domain instead
of keeping one static set for the whole run. OB-3 is that step.

OB-3 asks: does choosing the resident set BY TASK, switching to a
same-domain-ranked set when the input looks like code, collapse most of
that cross-domain miss penalty, decided by a cheap, frozen, DETERMINISTIC
detector (never a learned or improvised choice, per house product law)?

## 2. METHOD SUMMARY (self-contained)

**Model and manifest.** Same pinned gpt-oss-20b-MXFP4.gguf as OB-1
(sha256 27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901),
same expert manifest and per-expert byte geometry (E=32, L=24,
per_expert_bytes_per_layer=13253760). No weight was downloaded or re-read
by this leg; the digest was verified by builder 2 against the pinned value
(RUNLOG-1.txt section 2) and this leg's own filesystem user has no read
access to /root/openbob-baselines to re-hash it directly, a permission
boundary named here rather than worked around.

**Two new resident sets.** research/ob3/resident_sets_ob3.py, same
loader/ranking lineage as OB-1's own tool. SET-CODE ranks top-K experts per
layer on res-code-a's route log only; SET-MIX ranks on res-code-a and
res-prose-a's usage histograms summed. K in {16, 8}. SET-PROSE (OB-1's
original set, research/ob1/RESIDENT-SETS.json) is reused unmodified as the
control and as the "prose leg" of the switch.

**The held-out probe.** AC-CODE2.txt: the next slice of the same source
file as OB-1's AC-CODE.txt (openbob_s11_cpu.rs), extracted by
research/ob3/extract_ac_code2.py via vocab-only tokenization at a
newline-safe cut point, so its bytes were never seen by SET-CODE's own
ranking pass. This is the one row in this leg that carries real
generalization weight; every other in-domain row is an upper bound (see
section 6).

**The detector.** research/ob3/detector.py, a frozen deterministic integer
byte-classifier: reads the first 4096 bytes of the input, counts four
byte classes (P = code punctuation `{}();=<>_`, D = ASCII digits, N =
newlines, L = ASCII letters), SCORE = 4P + 3D + 2N - (L // 10), integer
arithmetic only, SCORE > 90 -> CODE else PROSE (ties to PROSE, the
no-op/status-quo branch). The identical logic is compiled into the engine
as src/ob3-detect.h, so the live run's classification is not a lookalike
reimplementation of the frozen tool, it is the same code.

**The engine.** research/ob3/region-engine.patch against the house fork
(c087083, this leg's own worktree /root/ob3/llama.cpp per fork discipline,
CPU-only build, never touching /root/rs053/llama.cpp directly): one
startup decision (score the detector input, load OB3_SETS_CODE or
OB3_SETS_PROSE) and nothing else changed; with OB3_DETECT unset the engine
is OB-1 exactly. Everything downstream (manifest load, per-lease sha256
verification, route logging, chunk timing) is OB-1's own code, untouched.

**Runs.** Six runs (research/ob3/run-ob3.sh), same frozen invocation shape
as OB-1: llama-perplexity, --ctx-size 1024, --chunks 32, -ngl 0, --no-mmap,
--no-repack, CUDA_VISIBLE_DEVICES="", nice 10, seed 1, box-wide RUNLOCK held
for each run's full duration, 8 threads (this leg's CPU wall, OB-1 used 10;
named as a deviation, its effect on the cost limb is spelled out in
section 5).

## 3. INDEPENDENT RE-VERIFICATION (this leg's own commands)

All of the following were re-run by this leg directly against the off-repo
artifacts under /mnt/f/f32/stage/research/ob3/runs/ and
/mnt/f/f32/stage/research/ob1/runs/, not copied from either prior document.
Guard pids 654 (openbob serve) and 489 (searxng) were confirmed alive
before and after this leg's own commands and never touched; the box-wide
RUNLOCK was never acquired by this leg (every command here is read-only
analysis over already-produced bytes, <=4 threads, per house law) and was
found held by a live peer at verification time, untouched.

**Document and input digests, recomputed:**

  research/ob3/RESIDENT-SETS-CODE.json  e72faaf13db00a204d8fcaf5cf55816775307f71d484e639e42e65bd948b2a1a  MATCH
  research/ob3/RESIDENT-SETS-MIX.json   a6e5e93e209836904a0cab293be8c474254b4e308248fda088c54d4efd286c66  MATCH
  research/ob1/RESIDENT-SETS.json       dc1ce20c4d5aed376b6a730a3596ae188f2b4509be73549bf8d05d4275125b85  MATCH
  research/ob3/region-engine.patch      592dabb051e2c0fda665c9e7d37285558b4391dec57f98232e099420805cbd1a  MATCH
  research/ob3/resident_sets_ob3.py     bdf9759ef539b5343e13af675b5504cd5fffaf6206c4637dc49bcd4e26189581  MATCH
  research/ob3/sim_predict.py           921fee116f94877916e2bd311402b79b8a3a463de657daff1d76b506f17194f1  MATCH
  research/ob3/detector.py              5f00ce513ec9168e3ba62008b1c99fffea15e25ae35ee0195da88cb8f83a7ea3  MATCH
  AC-CODE2.txt (off-repo)               03aef0bce2f69706a6db66ae8f2ca38de2d9fdd600fb3a6082e32746f71ba1c2  MATCH
  AC-CODE.txt  (off-repo)               d2db5c682d5f52a4383d188fee9d25f592a15d69763dbf886b5614c953e7f3fc  MATCH
  AC-PROSE.txt (off-repo)               310710a1f3e04484fcef2d0cb4ac1de93a8a6e02ced07ed3f2c9b79505e81a8e  MATCH

Every one of the ten matches the digest either prereg section 9 or RUNLOG-1
section 2 already recorded. Model gguf digest not independently re-hashed
by this leg (permission boundary, see section 2); already verified by
builder 2 against the pinned value.

**Detector, re-run fresh against the actual corpus files (not read from
either document's table):**

  AC-PROSE.txt   bytes=4096 P= 44 D=  4 N= 20 L=3236 SCORE=  -95 THRESH=90 -> PROSE
  AC-CODE.txt    bytes=4096 P= 30 D=104 N= 66 L=2826 SCORE=  282 THRESH=90 -> CODE
  AC-CODE2.txt   bytes=4096 P=352 D= 24 N=119 L=1164 SCORE= 1602 THRESH=90 -> CODE

All three match the prereg's frozen literal scores exactly, run fresh by
this leg's own invocation of research/ob3/detector.py.

**Identity limb, re-hashed from the off-repo bytes, compared over
min(length)-1 bytes to avoid the framing-byte artifact RUNLOG-1 section 4
already named** (each run's identity.txt ends with a trailing chunk marker
whose presence depends on chunk count, not on the compared values):

  run              vs reference          identity   route.log
  r1-k16-code      OB-1 res-code-a       MATCH      MATCH (f0c3f341...)
  r2-k8-code       OB-1 res-code-a       MATCH      MATCH (f0c3f341...)
  r5-k16-code-aa   OB-1 res-code-a       MATCH      MATCH (f0c3f341...)
  r4-k16-prose     OB-1 res-prose-a      MATCH      MATCH (4777aa83...)
  r3-k16-code2     this leg's r0         MATCH      MATCH (82e8e59b...)
  r1 vs r5 (A/A)   each other            MATCH      MATCH

Six of six leased/reference comparisons byte-identical, independently
re-derived by this leg from the off-repo bytes; every digest above matches
what RUNLOG-1.txt section 5 already recorded, this is an independent
re-derivation, not a re-statement.

**Miss-vs-sim, recomputed by replaying each run's OWN live route.log
through research/ob3/sim_predict.py** (bar: within 2.0 percentage points
of the section-4 sim prediction, for the three rows with one):

  run              corpus         K  set    misses    measured%   sim%      delta_pp
  r1-k16-code      AC-CODE.txt    16 CODE   454671    14.4536%    14.4536   +0.0000  PASS
  r2-k8-code       AC-CODE.txt     8 CODE   1162160   36.9441%    36.9441   -0.0000  PASS
  r4-k16-prose     AC-PROSE.txt   16 PROSE  591548    18.8048%    18.8048   +0.0000  PASS
  r5-k16-code-aa   AC-CODE.txt    16 CODE   454671    14.4536%    14.4536   +0.0000  PASS
  r3-k16-code2     AC-CODE2.txt   16 CODE   534133    16.9796%    none      -        (no prediction, held out)

All four figures with a prediction reproduce it exactly (0.0000pp delta,
well inside the 2.0pp bar), matching RUNLOG-1.txt section 5 exactly.

**Held-out counterfactual, recomputed by replaying r3's own live AC-CODE2
route.log against SET-PROSE and SET-MIX** (this is the headline
comparison: same tokens, same live routing, only the resident set
differs):

  set               K   misses    miss_rate
  SET-PROSE         16  1842813   58.5814%
  SET-CODE (r3)     16  534133    16.9796%
  SET-MIX           16  769687    24.4677%
  SET-PROSE          8  2487641   79.0800%
  SET-CODE           8  1259788   40.0476%
  SET-MIX             8  1626807   51.7148%

Matches RUNLOG-1.txt section 1 and section 6's counterfactual exactly.

**Cost limb, p50/p95 recomputed independently from each run's own raw
chunk_ns array** (ob1-stats.txt, nearest-rank over the 31 inter-chunk
intervals, not read from either document's precomputed table):

  run                n   p50_ms     p95_ms
  r1-k16-code        31  22816.0    23106.9
  r2-k8-code         31  23871.1    24690.3
  r3-k16-code2       31  21648.1    22435.0
  r4-k16-prose       31  21351.5    22035.7
  r5-k16-code-aa     31  22613.9    24333.3
  r0-res-code2       31  17476.3    17795.7
  OB1 res-code-a     31  15549.0    16073.7
  OB1 res-prose-a    31  15709.3    16025.8

  bar: leased p95 <= 3.0x resident p95, K=16 rows only
  r1-k16-code       23106.9 / 16073.7 = 1.4376x   PASS
  r4-k16-prose      22035.7 / 16025.8 = 1.3750x   PASS
  r5-k16-code-aa    24333.3 / 16073.7 = 1.5139x   PASS
  r2-k8-code        24690.3 / 16073.7 = 1.5361x   (report only, K=8)
  r3-k16-code2      22435.0 / 17795.7 = 1.2607x   (report only, no fully-
                                                     resident AC-CODE2
                                                     baseline predates r0)

Every p50, p95 and ratio matches RUNLOG-1.txt section 5 exactly, re-derived
here from the raw per-chunk nanosecond timings rather than the run script's
own precomputed summary.

## 4. HEADLINE TABLE

  AC-CODE2, K=16, held-out bytes, SAME live route log, only the resident set differs:
    SET-PROSE (OB-1's static prose-ranked set)   58.5814%  miss
    SET-CODE  (this leg, detector-selected)      16.9796%  miss
    SET-MIX   (pooled ranking, no switching)     24.4677%  miss
    -> 41.6018 points absolute, a 3.45x reduction in miss rate

  AC-CODE2, K=8, same comparison:
    SET-PROSE   79.0800%  miss
    SET-CODE    40.0476%  miss
    SET-MIX     51.7148%  miss

  For context, OB-1's own cross-domain figure (static set, no switching,
  AC-CODE not AC-CODE2, but the same design):
    K=16  60.5733%  miss   K=8  79.7325%  miss

  In-domain ceiling and generalization gap (SET-CODE only):
    r1, AC-CODE.txt (ranked on)     14.4536%  miss   K=16
    r3, AC-CODE2.txt (held out)     16.9796%  miss   K=16
    gap                              2.5260 points

  No-regression row (prose, unchanged set):
    r4, AC-PROSE.txt, K=16          18.8048%  miss, byte-identical to
                                      OB-1's own K=16 prose result

## 5. LIMB VERDICTS AGAINST THE FROZEN BARS

**IDENTITY LIMB: PASS, stop-ship, all six.** Every leased run reproduces
its fully-resident reference exactly: perplexity identity artifact and the
786432-line route log both byte-identical, independently re-hashed by this
leg in section 3, not merely re-stated. The route logs matching, not only
the final perplexity numbers, is the stronger claim: region switching did
not merely land on the same answer, it produced the exact same per-token
router decisions as the fully-resident run, at every K, on every corpus,
including the held-out one.

**MEASURED-VS-SIM AGREEMENT LIMB: PASS, all three rows with a prediction,
0.0000pp delta, independently re-derived in section 3.** As RUNLOG-1.txt
section 9 already names, and this leg confirms by re-deriving it fresh:
this agreement is a determinism statement (the live route logs came out
byte-identical to the banked logs the simulation replayed), not an
independent numerical confirmation. It is real and it is not nothing,
since it proves the simulation and the live engine compute the same
function over the same bytes, but it should not be read as two
independent measurements happening to land on the same number.

**HEADLINE BAR: measured plainly, no pass/fail threshold frozen on it per
the prereg.** Region leasing cuts the held-out, cross-domain miss rate
from 58.5814 percent (SET-PROSE replayed on AC-CODE2, the counterfactual a
static undetected design would have produced) to 16.9796 percent
(SET-CODE, detector-selected, this leg's own live run), a 41.6018-point
absolute reduction, a 3.45x reduction in miss rate. The generalization gap
against the in-domain ceiling (2.5260 points) is small: the prereg's own
stop-ship condition ("if row 3 comes in dramatically worse than row 1,
that gap IS the finding") did not fire.

**COST LIMB: PASS at the frozen K=16 bar, all three barred rows.**
1.4376x, 1.3750x, 1.5139x against the <=3.0x bar, independently recomputed
from raw chunk timings in section 3, all comfortably inside budget. Named
plainly, as RUNLOG-1.txt already named it: these three ratios divide this
leg's 8-thread leased p95 by OB-1's 10-thread resident p95, so they are
CONSERVATIVE (inflated by the thread difference, not like-for-like). The
one clean same-thread pair (r3 over its own r0-res-code2 baseline, both 8
threads) comes in at 1.2607x, consistent with OB-1's own same-thread range
(1.2536-1.5408x). The bar clears on either reading.

## 6. THE IN-DOMAIN UPPER-BOUND HONESTY NOTE

Per the prereg's own "honesty split" (section 2): SET-CODE and SET-MIX
were ranked on the SAME route logs (res-code-a, res-prose-a) that most of
this leg's acceptance runs replay against. Rows r1, r2, r4, r5 and every
SET-MIX figure are therefore IN-DOMAIN UPPER BOUNDS: the best a static
top-K-by-usage set ranked on that exact traffic can do, not a
generalization test. r3, the AC-CODE2 row, is the one genuinely held-out
measurement in this leg, and it is the row named as the headline in
sections 1 and 4 above precisely because it is the one that carries
generalization weight. Read the 14.4536 percent in-domain figure as a
ceiling this design approaches on familiar bytes, and the 16.9796 percent
held-out figure as the honest answer to the question this leg actually
asked.

A second scope note on the held-out row itself: AC-CODE2 is held out in
BYTES (SET-CODE's ranking pass never saw them) but is the same source file
as AC-CODE (openbob_s11_cpu.rs), so it is a same-file, different-slice
transfer test, not a different-project or different-language one. The
2.5260-point generalization gap should be read at that scope, not
extrapolated to arbitrary unseen code.

## 7. SCHEDULER-TIER PRODUCT NOTE

Per the house research roadmap (N4, the low-int/1T-class-brain line), a
classification seat that decides which region of a model's weights to
keep resident belongs, at product scale, to the low-int SCHEDULER TIER:
deterministic, sub-millisecond, integer arithmetic, running on both boxes.
The detector this leg exercised (four integer byte counts, one integer
score, one threshold) is explicitly a v1 STAND-IN for that tier, not a
claim that a 4096-byte punctuation count is the scheduler design. What it
demonstrates is the SHAPE of the win available to that tier: a cheap,
frozen, auditable, non-learned decision, made once per run before any
expert weight is touched, that cut a held-out cross-domain miss rate by
3.45x. This is a data point for the coequal "lessons for larger weights"
bar the low-int lane's charter names, not a substitute for that lane's own
scheduler work: the mechanism here (byte-level heuristic, two candidate
sets) is far simpler than the low-int lane's own frozen LI-S5 bar
(routing accuracy >= the 4B's own on the same corpus, p95 <= 250ms per
decision, on CPU), and this leg's detector was never measured against that
bar because it decides a different, coarser thing (which weight region to
keep resident, once per run, not which expert to route a token to).

## 8. LIMITATIONS, STATED PLAINLY

- Single model (gpt-oss-20b), single box (f32-HYDE), single build of one
  llama.cpp fork, same limitation OB-1 already named and carried forward
  unchanged here.
- Two candidate sets only (SET-PROSE, SET-CODE), one binary detector. A
  domain space with more than two clusters, or a continuum rather than a
  hard boundary, was out of scope for this leg.
- The held-out probe (AC-CODE2) tests generalization within one source
  file, one language (Rust), against one prose baseline (enwik8). It says
  nothing about how SET-CODE would fare on a different programming
  language, a different codebase's style, or a genuinely novel domain the
  detector was never tuned against.
- The detector's threshold (90) was chosen from the two corpora that
  DEFINE its classes (AC-PROSE, AC-CODE); AC-CODE2 was deliberately held
  out of that choice and used only to verify it generalizes, per the
  prereg. A single held-out file is a real check but a small one; the
  detector's robustness to genuinely adversarial or ambiguous input
  (mixed prose/code files, non-English text, binary-adjacent formats) is
  untested.
- SET-CODE and SET-MIX's own in-domain figures are upper bounds, not
  generalization tests (section 6); only r3 is a real held-out
  measurement in this leg.
- 8 threads not OB-1's 10 (named in the prereg, its effect on the cost
  limb spelled out in section 5); the barred ratios are conservative as a
  result, not optimistic.
- The measured-vs-sim agreement being exact (0.0000pp) is a determinism
  confirmation, not an independent numerical check, as section 5 already
  states; readers should not read three 0.0000pp rows as three separate
  pieces of evidence.
- The 58.5814 percent SET-PROSE-on-AC-CODE2 figure is a replay of r3's own
  live route log against a different resident set, not a live SET-PROSE
  run of AC-CODE2. It is a fair counterfactual (the identity limb proves
  leased computation is exact, and the resident set does not change which
  experts the router chooses, only which are already in memory) but it is
  named here as a replay, not an independent live run, matching RUNLOG-1's
  own caveat.

## 9. HELD MENU: NEXT STEPS (nothing here fires; naming only)

- MORE THAN TWO DOMAINS: extend the detector and the resident-set family
  beyond a prose/code binary (for example separate sets for different
  programming languages, or a small ranked shortlist rather than a single
  switch), and measure whether the same collapse holds as the domain
  space grows.
- CROSS-PROJECT, CROSS-LANGUAGE HELD-OUT: repeat the AC-CODE2-style probe
  against code from a different project and a different language than
  openbob_s11_cpu.rs, to test whether SET-CODE's generalization
  (2.5260-point gap on same-file held-out bytes) holds at a wider scope.
- SCHEDULER-TIER HANDOFF: replace this leg's byte-classifier with (or
  compare it against) the low-int lane's own LI-S5 scheduler once that
  bar is measured, since both decide a related question (which learned
  state to keep near) at very different granularity and cost.
- 120B: repeat this leg's three limbs on gpt-oss-120b, where RS053 already
  measured region structure differs by domain even more sharply (higher
  layer-mean P_half than 20b at both domains), suggesting a larger,
  sparser model may show an even bigger switching win.
- LIVE SET-PROSE-ON-AC-CODE2 RUN: promote the 58.5814 percent
  counterfactual (section 8's replay) to a genuinely live run, closing the
  one named gap in this leg's own headline row.

## 10. ARTIFACTS AND DIGESTS

Off-repo run artifacts (route.log, identity.txt, stdout.txt, stderr.txt,
ob1-stats.txt per run) remain at /mnt/f/f32/stage/research/ob3/runs/<run>/,
digests recorded in RUNLOG-1.txt section 7 and independently re-verified
by this leg in section 3 above, by direct sha256sum and a fresh
research/ob3/sim_predict.py replay of each run's own live route.log, not
copied from either prior document's tables. No new instrument script is
committed for this leg's own verification pass: every check above is an
ad hoc, auditable read (sha256sum, cmp, research/ob3/detector.py,
research/ob3/sim_predict.py, a short stdlib-only Python pass over each
run's own ob1-stats.txt chunk_ns array for the p95 recheck) over
already-committed tools and already-produced bytes, matching the same
convention OB1-EXPOSURE-1.md's own builder 3 receipt used.

Committed with this receipt: this file only (research/OB3-REGION-1.md). No
prior artifact is modified; research/ob1/*, research/OB3-REGION-1-PREREG.md
and research/ob3/RUNLOG-1.txt are untouched.

END OB3-REGION-1
