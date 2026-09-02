# OB5B-DECODESHAPE-1-PREREG: THE DECODE-SHAPE PROBE, PREDICTIONS BANKED
# BEFORE THE REPLAY RUNS
#
# Row P05 of research/OB5-DESIGN-SUMMARY-1.md (source slice C8-S8-2,
# research/OB5-DESIGN-C8-1.md section 7). Written on hyde, branch
# research-2, worktree F:\f32\openbob-wt\research-2, 2026-09-01.
# Pure ASCII, no em dashes. Every number cited to the receipt it came
# from by name. Arithmetic over cited literals is labelled THIS
# DOCUMENT'S ARITHMETIC. Anything not measured anywhere is UNVERIFIED.
#
# This file is banked BEFORE the replay is run and BEFORE any model
# process starts. Its sha256 is recorded in the receipt
# research/OB5B-DECODESHAPE-1.md together with the run timestamps, so
# the order can be checked by anyone.
#
# The sealed corpus lowint/fixtures/LI-S5-ROUTES-1.txt was not opened,
# read, grepped or hashed anywhere in this row.


## 0. WHAT IS BEING PREDICTED, AND WHY IT IS THE HINGE

Every exposure figure, miss rate, p95 and tok/s figure this house owns
was taken at a 1024-token micro-batch. The product decodes one token at
a time. C8 section 4.1 states the consequence: at batch shape policy
composition buys nothing on exposure and streaming the trunk is nearly
free; at decode shape composition is dominant and whole-trunk streaming
is ruinous, so every ranking of the design's levers flips, and the gap
"is exactly one experiment wide".

This row runs that experiment in two limbs:

  LIMB (a)  ANALYSIS ONLY. No model, no runlock, no weights. Replay the
            banked 120b route log at ubatch=1 through a deterministic
            integer residency/lease simulator under each candidate
            residency policy, and report loads, bytes moved, ACCT at
            decode shape, and the implied read-bound tok/s ceiling at
            the measured read rate.
  LIMB (b)  ONE RUNLOCK CYCLE. One live 20b decode run at ubatch=1 to
            convert the replay into a measurement.


## 1. THE HARNESS OF RECORD, AND ITS LINEAGE

research/ob5b2/decode_replay.py. The three policy bodies (P0-STATIC,
P1-SLIDING, P2-DECAY, with the frozen constants H=256, add=65536,
shift=1) are carried in behaviour from research/ob2/sim_residency.py,
which holds this house's only simulator-against-engine agreement record
(AGREE=PASS exact in all four cases, OB2-PREDICTIVE-1.md section 5 and
research/ob2/engine_walk_check.py).

WHAT IS NEW, and it is the reason the row exists: sim_residency.py
counts PICK-LEVEL MISSES. A pick-level miss is a decode-shape quantity
by accident (at ubatch=1 one missed pick is one lease event) and says
nothing at ubatch=1024, where the engine leases the DISTINCT
non-resident experts of a whole micro-batch once. decode_replay.py adds
the lease-accounting layer, so the same replay produces the counters the
engine's own ob1-stats.txt reports, at any micro-batch shape. That is
what makes bar B1 possible at all.

DEVIATION D1, DECLARED HERE. C8 section 3's C8-R09 names "the RS052
lineage, research/RS052-LEASE-BUILD-1.txt" as the deterministic integer
lease simulator to replay through. RS052's harness simulates a different
object: a fixed-point priority-lease RING with capacity, expiry and
take-late semantics, built for the CUDA research lineage. It does not
model expert residency over a route log and cannot produce
lease_events. The OB-2 residency simulator is the instrument that has
an agreement record against this engine, so the harness of record is
built on OB-2's lineage and RS052 is cited for the discipline
(deterministic, integer, dry-run against banked traces) rather than for
the code. Named as a deviation rather than done quietly.

THE ENGINE MODEL BEING REPLAYED, stated so it can be falsified:

  lease_events(layer, window) = |{experts routed in window} minus {resident}|
  lease_bytes_read            = lease_events x per_expert
  peak_concurrent_lease_bytes = max over (layer, window) of
                                lease_events(layer, window) x per_expert

with one route call per (layer, micro-batch) and every transient lease
dropped before the next layer's routing (OB1B-KNEE-1.md section 8;
OB2-PREDICTIVE-1.md section 7).


## 2. BAR B1  CALIBRATION. THE REPLAY MUST REPRODUCE THE BANKED
##            BATCH-1024 COUNTERS EXACTLY AT ubatch=1024

If the replay cannot reproduce the shape that was measured, its decode
figures mean nothing. Two independent calibration points are banked, on
two different models, so that a single lucky agreement cannot pass the
bar.

CALIBRATION POINT 1, THE 120B (the run every chapter cites).
  route log  /mnt/f/f32/stage/research/ob5a/runs/p3-120b-k8-prose-a/route.log
             sha256 a32d0051bd6d68f2777e64c7b889ae48d56621e9701b107fcef88c0e30cd89c1
             (byte-identical in run b and in ob1b/runs/pag120-prose-a; verified)
  sets       research/ob1b/RESIDENT-SETS-120B-K8.json, K=8 of E=128, L=36
  shape      ubatch 1024, 8192 tokens, AC-PROSE, policy P0-STATIC
  source of the target counters: /mnt/f/f32/stage/research/ob5a/runs/
             p3-120b-k8-prose-a/ob1-stats.txt, the run reported in
             OB5A-ALLOC-1.md section 6 and OB5A-SCOUT-1.md section 3.

  PREDICTED, and these are the engine's own banked literals:
    lease_events                27403
    lease_bytes_read            363192785280
    peak_concurrent_lease_bytes 1590451200
    route_calls                 288
    per_layer_lease_events      957,918,863,812,811,822,862,837,781,727,
                                666,642,643,656,760,763,706,740,749,776,
                                751,715,703,718,740,770,750,762,783,760,
                                784,848,776,726,682,644

CALIBRATION POINT 2, THE 20B (a different model, a different K, a
different E, the same accounting).
  route log  /mnt/f/f32/stage/research/ob1/runs/lease-k16-prose-a/route.log
  sets       research/ob1/RESIDENT-SETS.json, K=16 of E=32, L=24
             sha256 dc1ce20c4d5aed376b6a730a3596ae188f2b4509be73549bf8d05d4275125b85
  shape      ubatch 1024, 32768 tokens, AC-PROSE, policy P0-STATIC
  PREDICTED, from that run's own ob1-stats.txt:
    lease_events                10836
    lease_bytes_read            143617743360
    peak_concurrent_lease_bytes 212060160
    route_calls                 768
    per_layer_lease_events      512,509,493,478,480,472,497,492,452,402,
                                414,399,389,425,445,476,434,366,477,462,
                                453,429,440,440

B1 PASSES only if BOTH points reproduce on EVERY field, exactly, as
integers. A single event of deviation is a finding, not a variance.


## 3. BAR B2  THE DECODE-SHAPE ACCT PREDICTION, BANKED AS A LITERAL
##            BEFORE COMPUTATION, WITH BOTH COMPETING LITERALS AND THE
##            TERM DIFFERENCE LOCALIZED FIRST (summary section 4,
##            conflict 6, RULE R-2)

RULE R-2 requires that this preregistration bank BOTH published
literals with their owners named, and localize the term difference
BEFORE the run, because "a preregistration that contains two numbers
for one quantity is not a preregistration".

  LITERAL A   ACCT_decode 6184118048, exposure 10.250022
              OWNERS: OB5-DESIGN-C8-1.md section 4.1 (DERIVED there) and
              OB5-DESIGN-C1-1.md section 4.3, which arrive at it
              independently. Banked as S8-2's own bar B2 by C8 section 7.
              Form: trunk + K x L x per_expert + k x per_expert
                    2314020128 + 3817082880 + 4 x 13253760

  LITERAL B   ACCT_decode 6237133088, exposure 10.1629
              OWNER: OB5-DESIGN-C4-1.md section 6.1. C3 section 5.5
              builds 11.1794/11.2584 on top of it.
              Form: trunk + K x L x per_expert + d x k x per_expert at d=2
                    2314020128 + 3817082880 + 8 x 13253760

THE TERM DIFFERENCE, LOCALIZED. THIS DOCUMENT'S ARITHMETIC:

    6237133088 - 6184118048 = 53015040
    53015040 / 13253760     = 4 exactly

The difference is exactly one k-picks term, and C4 section 6.1 does not
hide it: it states "with a prefetch depth of d layers the bound is
d x 4 x per_expert", tabulates depth 1 = 53015040 and depth 2 =
106030080, and then labels its table "PROJECTED ACCT AND EXPOSURE IN THE
DECODE REGIME, AT PREFETCH DEPTH 2". The two literals are therefore NOT
two predictions of one quantity. They are one model evaluated at two
prefetch depths.

WHICH DEPTH THE ENGINE OF RECORD HAS IS ALREADY MEASURED, and this is
the part neither chapter was positioned to say. At batch shape the
engine's measured peak_concurrent_lease_bytes is 1590451200 =
(E - K) x per_expert = 120 x 13253760, which is EXACTLY ONE LAYER'S
non-resident set (OB5A-ALLOC-1.md section 6.2, measured twice, settling
deviation D4 by measurement). A runtime prefetching one layer ahead
would hold two layers' transient sets at once and could not report that
number. So d = 1 for the engine of record, MEASURED, not assumed.

THE PREDICTION THIS ROW BANKS: the replay at ubatch=1 returns
peak_concurrent_lease_bytes 53015040, ACCT 6184118048, exposure
10.250022, i.e. LITERAL A, because Literal A is the depth-1 evaluation
and the engine of record is depth 1.

WHAT THIS ROW DOES NOT DO. It does not withdraw Literal B. C4's
projection is a projection for a depth-2 prefetching runtime that has
not been built, and confirming Literal A on the current engine does not
refute it. Under R-2, withdrawing a chapter's published prediction is
not a builder's call: this is marked FOR THE ARCHITECT, with the
localization discharged and the recommendation stated plainly, which is
that C4 section 6.1 and C3 section 5.5 carry a "at prefetch depth 2, a
runtime not yet built" qualifier rather than being struck.


## 4. BAR B3  IDENTITY OF THE LIVE DECODE RUN. STOP-SHIP

C8's bar: "the live 20b decode run's identity hashes to the banked pair
for its corpus; a mismatch is stop-ship for the whole slice."

DEVIATION D2, DECLARED HERE, WITH ITS ARITHMETIC. The 20b banked pair
at 32768 tokens (identity 96049ccf..., route 4777aa83...) cannot be
reached at ubatch=1 inside this row's venue. THIS DOCUMENT'S
ARITHMETIC, from OB2-PREDICTIVE-1.md section 8's own replay counts and
OB1B-KNEE-1.md section 8's measured 20b warm read rate 2.4652 GB/s:
static K=16 prose moves 591548 x 13253760 = 7840917473280 B over 32768
tokens, which is 239283468 B per token, which is 97.07 ms per token of
READ ALONE, which is 3181 s for a 32768-token run before a single
byte is verified or a single matmul is run. Verification runs at
roughly the same cost as reading on this engine (lease_verify_ns
122462671606 against lease_read_ns 124169948910 on lease-k0-prose), so
the honest estimate is above 100 minutes of lock time for one arm. This
row is funded for one runlock cycle and shares the box with a heavy
sibling.

WHAT IS RUN INSTEAD, and why it is still an identity limb with a
BANKED reference rather than a self-graded one: a ONE-CHUNK
(1024-token) AC-PROSE run, which is the exact shape of a run this house
has already banked. research/ob1b's smoke-k0-prose is a 1-chunk AC-PROSE
lease run and its artifacts are on disk:

    identity.txt  "[1]131.2100,"
                  sha256 b0582867e00d2db9a5d8bb8802c7c1c31fb9dbd37d51bd0f56a775ae30c314d8
    route.log     24576 lines
                  sha256 8b8dee364ec4249b1bf59b6e1a9d0c17f9c5823f3ad1c01b5e37eca4807db97e

That reference was produced at K=0 and this row runs at K=16. Leasing is
identity-invariant across K on this engine and it is not a hope: OB1B-
KNEE-1.md section 12 records twenty-one 20b runs at six values of K from
16 down to an empty resident set, on two thread counts and two
binaries, producing four digests in total, two per corpus. So a K=16
1-chunk AC-PROSE run must produce that identity and that route log.

PREDICTED, BOTH ARMS:
  B3a  ARM A, the control at ubatch=1024, K=16, 1 chunk, AC-PROSE:
       identity.txt sha256 b0582867e00d2db9a5d8bb8802c7c1c31fb9dbd37d51bd0f56a775ae30c314d8
       route.log    sha256 8b8dee364ec4249b1bf59b6e1a9d0c17f9c5823f3ad1c01b5e37eca4807db97e
  B3b  ARM B, the decode arm at ubatch=1, K=16, 1 chunk, AC-PROSE:
       the same two digests.

B3b IS THE STOP-SHIP LIMB AND IT IS A REAL RISK, NOT A FORMALITY. At
ubatch=1 every matmul over the batch dimension becomes a matvec, and a
different accumulation order can move the low bits of a perplexity
figure. If ARM B's identity differs from ARM A's, byte-exact
determinism does not survive the change of micro-batch shape, which is
a first-order finding for the whole program and is reported as such
rather than smoothed. If ARM B's ROUTE LOG differs, the replay's own
input is shape-dependent and every decode-shape projection in this
document is void, including limb (a)'s.


## 5. BAR B4  THE LIVE RUN'S COUNTERS AGAINST THE REPLAY'S PREDICTION

The replay is run FIRST, on the banked smoke-k0-prose route log
(sha256 8b8dee36...), at K=16 under P0-STATIC with
research/ob1/RESIDENT-SETS.json, at ubatch 1024 and ubatch 1. Its output
is written to research/ob5b2/REPLAY-20B-1CHUNK-1.txt and that file's
sha256 is banked in the receipt BEFORE the live run is launched, with
the launch timestamp beside it.

PREDICTED: the live ARM A ob1-stats.txt lease_events and
lease_bytes_read equal the replay's ubatch=1024 row exactly, and the
live ARM B ob1-stats.txt lease_events and lease_bytes_read equal the
replay's ubatch=1 row exactly. Any gap IS THE FINDING and is reported
with both literals side by side; a gap means the simulator is not the
engine at decode shape and every decode-shape projection built on it is
void.

FROZEN TOLERANCE: ZERO. These are integer event counts over a
deterministic replay of a banked route log, not a variance-bearing
measurement. C3's invariant I4 reasoning applies: where a counter is
exactly predictable, a single event of deviation is a correctness
finding rather than a variance.


## 6. THE PERF POINT THIS ROW BANKS

P05's perf point, per summary section 3: "the implied read-bound tok/s
ceiling at decode shape at the measured 1.267 GB/s, which is the number
every hardware and scheduling decision below is actually keyed to".

THE READ RATES USED, each cited and each re-derived here rather than
carried as a round number. THIS DOCUMENT'S ARITHMETIC:

  120b, cold, the lease path's own effective rate:
    363192785280 B / 286.711586002 s = 1266764365 B/s
    (lease_bytes_read and lease_read_ns from p3-120b-k8-prose-a's
    ob1-stats.txt; this is the 1.2668 GB/s figure C6 and P06 use, and
    the "measured 1.267 GB/s" C8 section 3 quotes)
  20b, warm:
    306108840960 B / 124.169948910 s = 2465257248 B/s
    (lease-k0-prose's own ob1-stats.txt; this is OB1B-KNEE-1.md
    section 8's 2.4652 GB/s)

Both are integer byte-per-second values in the harness so no float
enters a counter.

THE KILL LINE, and the one honest thing that must be said about it.
C8-R09's kill line reads: if the decode-shape replay predicts a
read-bound ceiling below the daily-usable bar C4 and C6 preregister
(C8-R12), then BATCH-1024 EXPOSURE FIGURES MAY NOT BE QUOTED AS PRODUCT
FIGURES. C8-R12 records that that bar HAS NO NUMBER: it is owed from
the owner and its cheapest test is one question to her. This row
therefore cannot return a PASS or FAIL against a literal it does not
have. It returns the ceiling as a literal and states the threshold form
of the verdict: the kill line fires for any daily-usable bar above the
measured ceiling. That is the most a builder can honestly return here,
and the receipt says so in those words rather than inventing a bar.


## 7. VENUE, WALLS, AND WHAT THIS ROW WILL NOT TOUCH

  Limb (a): hyde, analysis only. No model process, no runlock, no
  weights, no card.
  Limb (b): hyde, WSL2, CPU only (-ngl 0, CUDA_VISIBLE_DEVICES=""),
  one runlock cycle per arm under research/ob1b/locked-run.sh lineage
  (mkdir on /mnt/f/f32/stage/research/runlock, 5 s poll, free RAM >= 6
  GB, release immediately after the run, 75 s courtesy yield). Max 8
  threads, nice 10.
  pid 654 (openbob serve) and pid 489 (searxng) are confirmed alive
  before and after every cycle and are never signalled. The mini is not
  touched. Nothing is downloaded.
  READ-NEVER, and not read: ~/.config/openbob/ anywhere, journals,
  tokens, pins, lowint/fixtures/LI-S5-ROUTES-1.txt.
  Run bytes stay off-repo under /mnt/f/f32/stage/research/ob5b2/.
