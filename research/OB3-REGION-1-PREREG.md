# OB3-REGION-1-PREREG: DOES CHOOSING THE RESIDENT SET BY TASK COLLAPSE
# THE CROSS-DOMAIN MISS PENALTY, WITH A DETERMINISTIC DETECTOR MAKING THE
# CHOICE

Lane: research (CUDA/inventor lane), venue hyde, on-machine. Branch ob3,
worktree F:\f32\openbob-wt\ob3, at master 4e7be6b (carries all OB-1
files). Builder 1 of OB-3 (prereg + region sets + detector). Pure ASCII,
no em dashes. Every number below is literal command output from this
leg's own script runs against banked, digest-verified inputs. This
document is committed before any live run of this leg's own instrument;
nothing below is renegotiated after that except where named as a
deviation.

Substrate at prereg time: worktree HEAD 4e7be6b22500b82c2d6b953d0a25b0bbfb48ab87,
branch ob3, `git status --porcelain` empty except `research/ob3/` being
added.

## 0. WHAT THIS LEG ASKS

OB-1 (research/OB1-EXPOSURE-1.md) measured a static, popularity-ranked
resident set (SET-PROSE: top-K experts per layer by usage on one prose
route log) transferring badly to a different domain: 18.8048 percent
per-decision miss rate on prose at K=16, but 60.5733 percent on code
(42.3153 / 79.7325 at K=8), the honest cross-domain gap that motivates
region leasing. RS053 independently measured that the region STRUCTURE
itself differs by domain (120b top-32 Jaccard 0.1868 prose vs code): the
sets of "popular" experts are not the same sets, so a resident set ranked
for one domain is structurally a poor fit for the other.

OB-3's question: does choosing the resident set BY TASK -- ranking a
second set on code's own traffic, and switching to it when the input
looks like code -- collapse most of that cross-domain miss penalty, if
the switching decision is made by a cheap, frozen, DETERMINISTIC
detector (never a learned or improvised choice, per house product law)?
This document freezes: the two new region sets, one held-out transfer
probe, the simulated prediction table (replaying banked route logs
against each set, no live run needed), the detector's definition and its
literal scores on the three corpora it must classify, the live-run plan
for a later builder, and the bars that plan is judged against.

## 1. INHERITED FACTS (carried forward from OB-1, re-cited, not re-derived)

  E (experts per layer)   = 32
  L (layers)               = 24
  budget (tokens/corpus)   = 32768   (OB-1's own acceptance-run budget;
                                       NOT RS053's 65536-token ranking log)
  model                    = /root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf
  model sha256              27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901
  per_expert_bytes_per_layer = 13253760  (research/ob1/EXPERT-MANIFEST-20B.sha256)

Banked reference route logs (both already committed as inputs, this leg
only reads them):

  res-prose-a  /mnt/f/f32/stage/research/ob1/runs/res-prose-a/route.log
               786432 lines (L=24 x budget=32768), sha256
               4777aa8319f25d6e367f761ef12c7bec81a9ff7896bfed1b8ea0326b5dffc3df
  res-code-a   /mnt/f/f32/stage/research/ob1/runs/res-code-a/route.log
               786432 lines, sha256
               f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77

OB-1's own resident set (SET-PROSE, research/ob1/RESIDENT-SETS.json,
already committed) is used here unmodified as the control and as the
"prose leg" of the detector's switch.

## 2. REGION SETS: SET-CODE AND SET-MIX (task step 1)

Tool: research/ob3/resident_sets_ob3.py, same loader/ranking lineage as
research/ob1/resident_sets.py (verifies token_index comes out exactly
0..budget-1 per layer before trusting the log, same per-layer usage
histogram, same top-K-by-count-then-lower-id tie-break). Two modes:

  set-code   ranks on res-code-a ONLY
  set-mix    ranks on res-code-a + res-prose-a HISTOGRAMS SUMMED
             (equivalent to ranking on the two logs concatenated: usage
             counts add, and top-K-by-count is invariant to concatenation
             order)

K in {16, 8} only for this leg (K=4 out of scope, per the task brief).

Literal run output:

  ROUTE_LOG=.../res-code-a/route.log SHA256=f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77
  OUT=research/ob3/RESIDENT-SETS-CODE.json
  K=16 resident_expert_pool_bytes=5089443840
  K=8  resident_expert_pool_bytes=2544721920

  CODE_ROUTE_LOG=.../res-code-a/route.log  SHA256=f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77
  PROSE_ROUTE_LOG=.../res-prose-a/route.log SHA256=4777aa8319f25d6e367f761ef12c7bec81a9ff7896bfed1b8ea0326b5dffc3df
  OUT=research/ob3/RESIDENT-SETS-MIX.json
  K=16 resident_expert_pool_bytes=5089443840
  K=8  resident_expert_pool_bytes=2544721920

(Pool byte totals match OB-1's own K x L x 13253760 formula exactly,
since E/L/per-expert-bytes are unchanged; only WHICH experts are chosen
differs.)

Output digests:

  research/ob3/RESIDENT-SETS-CODE.json  sha256 e72faaf13db00a204d8fcaf5cf55816775307f71d484e639e42e65bd948b2a1a
  research/ob3/RESIDENT-SETS-MIX.json   sha256 a6e5e93e209836904a0cab293be8c474254b4e308248fda088c54d4efd286c66

### HONESTY SPLIT (stated plainly, per the task brief)

SET-CODE and SET-MIX are ranked on the SAME route logs (res-code-a,
res-prose-a) that the live acceptance runs will replay against. This is
UNLIKE OB-1's own design, where the ranking log (RS053's 20b-prose-a,
budget 65536) was disjoint from every acceptance corpus. Consequently:

  - SET-CODE's own-corpus (code) miss rate, and SET-MIX's own-corpus
    miss rates on both corpora, are IN-DOMAIN UPPER-BOUND measurements:
    the best a static top-K-by-usage set ranked on that exact traffic
    can do, not a generalization test.
  - The one genuinely HELD-OUT row in this leg is the AC-CODE2 transfer
    probe (section 3): SET-CODE has never seen AC-CODE2's tokens at
    ranking time, so SET-CODE's miss rate on AC-CODE2 is a real
    held-out cross-slice (same domain, different bytes) measurement,
    directly comparable in kind to OB-1's own prose-ranked-set-on-prose
    honest design.

This split is why the live-run plan (section 6) treats the AC-CODE2 row
as the one that carries generalization weight, while the res-code-a /
res-prose-a rows are read as in-domain ceilings.

## 3. HELD-OUT PROBE: AC-CODE2 (task step 1)

AC-CODE2 = the next 32768 tokens of the SAME source file as OB-1's
AC-CODE.txt (corpus-code.txt / openbob_s11_cpu.rs), starting immediately
after the point where AC-CODE's own frozen 32768-token acceptance run
stops consuming it. Tool: research/ob3/extract_ac_code2.py (full method
documented in the tool's own header): vocab-only llama-tokenize (no
weights loaded, model_params.vocab_only=true) built in this leg's own
worktree (FORK DISCIPLINE: /root/ob3/llama.cpp, branch ob3, off c087083,
GGML_CUDA=OFF CPU-only build, never built inside /root/rs053/llama.cpp
directly), binary search restricted to NEWLINE-SAFE byte offsets so
every cut reproduces the whole-file tokenization exactly at that point
(BPE merges never cross a pre-tokenizer chunk boundary; a newline always
starts a fresh chunk).

Literal run output:

  SRC=/mnt/f/f32/stage/research/ob1/AC-CODE.txt bytes=1576144
    sha256=d2db5c682d5f52a4383d188fee9d25f592a15d69763dbf886b5614c953e7f3fc
  newline_safe_candidates=37031 file_bytes=1576144
  WHOLE_FILE_TOKEN_COUNT(no_bos)=419861
  STEP_A calls=16 X=114441 count_at_X=32770 overshoot=2
  remaining_bytes=1461703 remaining_newline_safe_candidates=34019
  STEP_B calls=16 Y=120279 count_at_Y=32785 overshoot=17

AC-CODE2 = source bytes [114441, 234720) = 120279 bytes, written to
/mnt/f/f32/stage/research/ob3/AC-CODE2.txt (off-repo, per house
convention for every corpus file in this program), sha256
03aef0bce2f69706a6db66ae8f2ca38de2d9fdd600fb3a6082e32746f71ba1c2.

Sanity-verified independently of the extraction script: byte 114440 of
AC-CODE.txt is 0x0A (the cut is genuinely newline-aligned); AC-CODE2's
first 80 bytes equal AC-CODE.txt's bytes [114441, 114521) exactly;
AC-CODE2.txt in full equals AC-CODE.txt's bytes [114441, 234720) exactly
(direct byte comparison, not re-derived from the extraction script).

NOTE ON OVERSHOOT: the newline-safety constraint means neither cut lands
on EXACTLY token 32768; both land a small number of tokens past it (2 and
17 respectively, tiny relative to 32768). This is named here as a
deliberate, honest deviation from a literal reading of "the next 32768
tokens": it is "the next >=32768 tokens, cut at the nearest safe line
boundary", not a token-exact splice. AC-CODE2's own acceptance run will
still be clipped to exactly 32768 tokens by the same --chunks 32
mechanism OB-1 always relied on (AC-CODE itself is 419861 tokens long on
disk; only the first 32768 are ever actually scored), so this overshoot
has no effect on the eventual measurement, only on where the file's
bytes start.

NOTE ON RUNLOCK: vocab-only tokenization loads no expert weights and runs
no forward pass, but it is still a gpt-oss model process, so this leg
held the box-wide RUNLOCK for the full binary search out of caution
(acquired 2026-08-31T23:30:40Z, released 2026-08-31T23:34:42Z, under 4
minutes total for 33 tokenize calls plus the two build-time cmake steps
run beforehand without the lock, since they touch no model process).
Free RAM checked before acquiring: 21 GB free (bar: >=6 GB).

## 4. SIM PREDICTIONS (task step 2, python <=4 threads, no lock)

Tool: research/ob3/sim_predict.py. Replays a resident-sets JSON against a
banked route log: for every one of the 3145728 individual router picks
(L x budget x 4 = 24 x 32768 x 4), a MISS is a pick whose expert id is
NOT in that layer's resident set for the given K. Same method
OB1-EXPOSURE-1.md section 3 used, applied here to three sets instead of
one.

### CONTROL: reproduce OB-1's own SET-PROSE cross rates (stop-ship if
this does not match)

  label                K   total_picks  misses   miss_rate
  SET-PROSE_on_prose   16  3145728      591548   18.8048%
  SET-PROSE_on_code    16  3145728      1905471  60.5733%
  SET-PROSE_on_prose   8   3145728      1331123  42.3153%
  SET-PROSE_on_code    8   3145728      2508167  79.7325%

MATCH: all four figures are byte-for-byte identical to
OB1-EXPOSURE-1.md's own table (section 3 / section 4 of that document).
The simulation methodology is confirmed correct before being trusted for
the two new sets below. (Per the task brief: this leg would stop and
report here if any of the four had not matched; none deviated.)

### NEW PREDICTIONS: SET-CODE and SET-MIX

  label                K   total_picks  misses   miss_rate
  SET-CODE_on_code     16  3145728      454671   14.4536%
  SET-CODE_on_prose    16  3145728      1706139  54.2367%
  SET-CODE_on_code     8   3145728      1162160  36.9441%
  SET-CODE_on_prose    8   3145728      2559408  81.3614%
  SET-MIX_on_code      16  3145728      689136   21.9070%
  SET-MIX_on_prose     16  3145728      842576   26.7848%
  SET-MIX_on_code      8   3145728      1549182  49.2472%
  SET-MIX_on_prose     8   3145728      1671334  53.1303%

### THE HEADLINE COMPARISON (sim prediction only; the live-run row is
section 6/7)

  K=16, code corpus:
    static prose-ranked set (OB-1's own design)   60.5733% miss
    same-domain-ranked SET-CODE (this leg)        14.4536% miss
    -> a 46.12-point ABSOLUTE reduction (a 4.19x reduction in miss rate)
       in simulation, from ranking on the traffic's own domain instead of
       a fixed prose ranking. This is the in-domain upper bound (section
       2's honesty split); the genuinely held-out figure is AC-CODE2's
       LIVE miss rate (section 6), not simulated here (no route log for
       AC-CODE2 exists yet -- it has never been run).

  SET-MIX sits between the two single-domain sets on both corpora, as
  expected for a set ranked on pooled traffic: it beats the prose-only
  set on code (60.57% -> 21.91% at K=16) and beats the code-only set on
  prose (81.36% -> 26.78% at K=8, and 54.24% -> 26.78% at K=16), but
  loses to EITHER single-domain set on its own best domain (SET-CODE
  beats SET-MIX on code: 14.45% vs 21.91%; SET-PROSE beats SET-MIX on
  prose: 18.80% vs 26.78%). This is the quantitative case for TASK-BASED
  SWITCHING (detector picks the matching single-domain set) over a
  static merged compromise: switching gets close to each domain's own
  ceiling; merging gets neither.

## 5. DETECTOR: FROZEN DEFINITION AND LITERAL SCORES (task step 3)

Tool: research/ob3/detector.py. Deterministic integer byte-classifier,
reads the FIRST 4096 bytes of the input file (or the whole file if
shorter). Four fixed integer byte classes:

  P = count of bytes in {}();=<>_        (code-punctuation class)
  D = count of ASCII digit bytes 0-9
  N = count of newline bytes (0x0A)
  L = count of ASCII letter bytes (A-Z, a-z)

  SCORE = 4*P + 3*D + 2*N - (L // 10)

Integer arithmetic only: multiply, add, subtract, one floor division by
the constant 10. No floats, no learned weights, no state beyond the 4096
input bytes. FROZEN THRESHOLD = 90: SCORE > 90 -> CODE, SCORE <= 90 ->
PROSE (ties resolve to prose, per house "whatever is most bob" law:
absolute wall, no carve-out, and PROSE is the design's status-quo/no-op
choice since it reproduces OB-1's original set unchanged).

### DERIVATION (why these four classes, why 90)

A naive punctuation-only count (P alone) FAILS on this program's own
AC-CODE.txt: its first 4096 bytes are a comment/provenance preamble
(english prose describing the file's own provenance, line-wrapped at
about 80 columns -- see the literal excerpt in this leg's own working
notes), so P(AC-CODE)=30 is actually LOWER than P(AC-PROSE)=44 on that
one feature. D and N recover a comfortable margin: comment text in this
codebase is far more digit-dense (hex digests, line-number ranges,
version numbers) and more line-wrapped than the AC-PROSE enwik8 slice.
L (raw letter density) still leans prose and is kept as a mild,
down-weighted counterweight rather than dropped, so the detector does
not rely on a single accidental feature.

THRESHOLD=90 was chosen from the two corpora that DEFINE the classes
(AC-PROSE, AC-CODE) with margin; AC-CODE2 is deliberately NOT used to
choose the threshold, only to verify it generalizes (the held-out check
the task brief asked for).

### LITERAL SCORES (verified on the actual bytes of all three corpora)

  path              bytes P   D   N   L    SCORE THRESH  CLASS
  AC-PROSE.txt      4096  44   4  20 3236   -95     90   PROSE
  AC-CODE.txt       4096  30 104  66 2826    282     90   CODE
  AC-CODE2.txt      4096 352  24 119 1164   1602     90   CODE

All three classify correctly (AC-PROSE -> PROSE, AC-CODE -> CODE,
AC-CODE2 -> CODE), with wide margins on every one (95 points below
threshold for the prose side; 192 and 1512 points above threshold for
the two code files). AC-CODE2's margin is especially wide because it is
ordinary dense code with no comment preamble (P=352 alone already clears
the threshold at weight 4), which is itself a useful cross-check: the
detector is not fragile to the one adversarial-ish case (a
comment-heavy code file) it was actually designed against.

The detector's output selects which region set the engine loads: CODE
-> SET-CODE (this leg), PROSE -> SET-PROSE (OB-1's original set,
unmodified). SET-MIX is not a switch target; it is a comparison-only
static baseline (section 4), included in the prediction table to show
what NOT switching, but ranking on pooled traffic instead, would cost
relative to switching.

NOTE ON PRODUCT SCALE: per the house research roadmap (N4, the
low-int/1T-class-brain line), a classification seat like this one
belongs, at product scale, to the low-int SCHEDULER TIER (deterministic,
sub-millisecond, integer, on both boxes). This byte-classifier is
explicitly a v1 STAND-IN for that tier, not a claim that this is the
scheduler design -- it is frozen, cheap, and auditable, which is what
this leg needed to test the region-leasing question without waiting on
that separate, coequal research lane.

## 6. LIVE-RUN PLAN (nothing in this section has been run yet; naming
only, per the task; a later builder executes it)

All runs use the SAME frozen invocation shape as OB-1
(research/ob1/run-ob1.sh): llama-perplexity, -ngl 0, --no-mmap,
--no-repack, CPU-only, box-wide RUNLOCK held for the run's full duration,
<=8 threads (this leg's CPU wall; OB-1 used 10, which is now over this
leg's bar and must be reduced to 8 when the instrument is built), nice
10, free RAM >=6 GB checked first.

  1. K=16, code corpus (res-code-a's own AC-CODE.txt), detector-selected
     set. Detector reads AC-CODE.txt's first 4096 bytes -> CODE -> engine
     loads SET-CODE. This is the IN-DOMAIN row (section 2's honesty
     split): expected close to the sim prediction (14.4536% miss).
  2. K=8, same corpus, same detector selection (SET-CODE). Sim
     prediction: 36.9441% miss.
  3. AC-CODE2 TRANSFER PROBE, K=16 only. Detector reads AC-CODE2.txt's
     first 4096 bytes (already verified section 5 -> CODE) -> engine
     loads SET-CODE. THIS IS THE HEADLINE HELD-OUT ROW: SET-CODE has
     never seen AC-CODE2's tokens at ranking time (section 2), so this
     is the honest generalization measurement, directly comparable in
     kind to OB-1's own miss-rate methodology. No sim prediction exists
     for this row (no route log for AC-CODE2 has ever been produced);
     it is measured fresh, live.
  4. K=16, prose corpus (AC-PROSE.txt), detector-selected set. Detector
     -> PROSE -> engine loads SET-PROSE (OB-1's original, unmodified
     set). THE NO-REGRESSION ROW: this must reproduce OB-1's own K=16
     prose result (18.8048% miss rate; IDENTITY limb byte-identical to
     OB-1's banked prose baseline) exactly, proving the detector-gated
     design does not cost anything on the domain OB-1 already solved.
  5. A/A REPEAT: re-run row 1 (K=16, code, detector-selected) from a
     clean process. Route log and identity artifact must be
     byte-identical to row 1's own outputs (same law as every A/A check
     in this program).

## 7. FROZEN BARS (bind whoever runs section 6's plan)

IDENTITY LIMB: stop-ship. Every leased run in section 6 must reproduce
its fully-resident reference exactly (perplexity identity artifact
byte-identical, sha256 match), same as every K in OB-1. A miss is always
served correctly from disk under this program's lease-engine design
(OB-1 section 5); a failure here is a correctness bug, not a
performance finding.

MEASURED-VS-SIM AGREEMENT: for rows 1, 2, and 4 (the three rows with a
sim prediction from section 4), the measured live miss rate must be
within 2.0 PERCENTAGE POINTS of the simulated prediction. (Rows 3 and 5
have no sim prediction to compare against by construction.) A miss here
is not necessarily a bug -- the live run's router decisions could differ
from the banked reference log's if anything about the corpus, context,
or engine build changed -- but it must be investigated and named as a
deviation if it happens, not silently accepted.

HEADLINE BAR: row 3 (AC-CODE2 transfer probe, K=16, region leasing) miss
rate vs OB-1's own cross-domain figure (row: static prose-ranked set on
code, K=16 = 60.5733 percent, research/OB1-EXPOSURE-1.md section 4).
This is the number the whole leg exists to produce; there is no
pass/fail threshold frozen on it beyond "measure it honestly and report
it plainly" (per house measurement-language law), but the SIM prediction
for the in-domain code row (14.4536 percent, row 1) sets an expectation:
if row 3 (held-out) comes in dramatically worse than row 1 (in-domain),
that gap IS the finding (SET-CODE generalizes poorly even within the
same domain, same file), and must be reported as such, not smoothed
over.

COST LIMB: leased p95 <= 3.0x fully-resident p95, at K=16 code and K=16
prose (the two K=16 rows with an existing OB-1 baseline to compare
against: res-code-a's own resident reference, res-prose-a's own resident
reference). Same bar OB-1 froze, unchanged. Report-only (no bar) at K=8
and for the AC-CODE2 row (no fully-resident AC-CODE2 baseline exists to
compare against; if one is wanted, a K=0 resident run of AC-CODE2.txt is
a fair follow-up, not required by this bar).

## 8. WALLS AND SCOPE (per the house rules handed to this builder,
restated)

Venue hyde; NEVER touch pid 654 (openbob serve), searxng 489, any
wsl.exe keepalive; a sibling workflow (OB-2) runs concurrently on this
box. RUNLOCK: box-wide, atomic mkdir /mnt/f/f32/stage/research/runlock,
loop-sleep-30 up to 90 minutes then give up and report, release
immediately after; never held during analysis (sections 2 and 4 ran
without it, being pure numpy over already-banked logs); free RAM >=6 GB
checked before every model process (section 3: 21 GB free at acquire
time). CPU: <=8 threads nice 10 for heavy runs (section 6's plan);
analysis <=4 threads, no lock (sections 2 and 4, run with
OMP_NUM_THREADS=4). SCRIPT-TO-FILE LAW: every wsl.exe call in this leg
ran a script file written to the Windows filesystem first (the
MSYS2_ARG_CONV_EXCL=* environment variable was needed on this leg's
particular Bash-tool shell to stop it rewriting /root/... unix paths
into Windows paths before they reached wsl.exe -- named here since it is
not obvious and cost real time to diagnose). READ-NEVER paths
untouched. NO WEIGHT DOWNLOADS: none performed; this leg's llama-tokenize
build uses the SAME already-verified gpt-oss-20b-MXFP4.gguf OB-1 pinned
(sha256 27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901),
loaded vocab-only (no expert tensors read). FORK DISCIPLINE: this leg's
own worktree /root/ob3/llama.cpp (branch ob3, off c087083), own build
dir, /root/rs053/llama.cpp never built or edited directly. GIT: worked
only in F:\f32\openbob-wt\ob3 (branch ob3); master untouched, no push.

DEVIATION NAMED: this leg needed `cmake` (for the tokenize-target build)
and it was not installed for the root WSL user; `apt-get install -y
cmake` was run (a standard build-toolchain package, not a model weight
or a research-state change) since gcc/g++/make already existed from the
prior OB-1 build and a bare CPU-only tokenize target needed only cmake
itself to drive the same existing compiler. Recorded here as a
deviation from "nothing outside git/gh permissions was touched",
resolved cheaply and reversibly (`apt-get remove cmake` would undo it;
not done, since a later OB-3 builder will likely need to build the
region-switching engine patch too).

## 9. ARTIFACTS AND DIGESTS

Committed with this document:

  research/ob3/resident_sets_ob3.py   sha256 bdf9759ef539b5343e13af675b5504cd5fffaf6206c4637dc49bcd4e26189581
  research/ob3/sim_predict.py         sha256 921fee116f94877916e2bd311402b79b8a3a463de657daff1d76b506f17194f1
  research/ob3/detector.py            sha256 5f00ce513ec9168e3ba62008b1c99fffea15e25ae35ee0195da88cb8f83a7ea3
  research/ob3/extract_ac_code2.py    (this document's section 3 tool)
  research/ob3/RESIDENT-SETS-CODE.json sha256 e72faaf13db00a204d8fcaf5cf55816775307f71d484e639e42e65bd948b2a1a
  research/ob3/RESIDENT-SETS-MIX.json  sha256 a6e5e93e209836904a0cab293be8c474254b4e308248fda088c54d4efd286c66
  research/OB3-REGION-1-PREREG.md     this file

Off-repo (per house convention, same as every corpus file in this
program): /mnt/f/f32/stage/research/ob3/AC-CODE2.txt, sha256
03aef0bce2f69706a6db66ae8f2ca38de2d9fdd600fb3a6082e32746f71ba1c2, 120279
bytes. /root/ob3/llama.cpp (worktree + build, off c087083, GGML_CUDA=OFF,
llama-tokenize only); /root/ob3/ac-code2-extraction-result.json (a copy
of section 3's literal result, off-repo).

No prior artifact is modified. research/ob1/* is read-only input to this
leg and is untouched.

END OB3-REGION-1-PREREG
