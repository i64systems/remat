# OB5B-DECODESHAPE-1: THE DECODE-SHAPE PROBE, AND THE REPLAY HARNESS OF
# RECORD
#
# Row P05 of research/OB5-DESIGN-SUMMARY-1.md, source slice C8-S8-2
# (research/OB5-DESIGN-C8-1.md sections 3/C8-R09, 4.1 and 7). Run on
# hyde 2026-09-01, branch research-2, worktree
# F:\f32\openbob-wt\research-2. Pure ASCII, no em dashes. Every number
# is literal command output or arithmetic over cited literals, and
# arithmetic done in this document is labelled THIS DOCUMENT'S
# ARITHMETIC. Anything not measured is labelled UNVERIFIED.
#
# Predictions were banked before the work in
# research/OB5B-DECODESHAPE-1-PREREG.md
# sha256 919dde360ad4b4eb7d868289c85b7451823485c1eacc15432fa68746b0066beb
# at 2026-09-01T19:20:29Z, which is before the first replay
# (19:20:43Z) and before the first model process (19:30:05Z).
#
# The sealed corpus lowint/fixtures/LI-S5-ROUTES-1.txt was not opened,
# read, grepped or hashed. No weights were downloaded. pid 654
# (openbob serve) and pid 489 (searxng) were confirmed alive before and
# after every lock cycle and were never signalled. The mini was not
# touched.


## 0. THE ANSWER FIRST

THE HINGE IS SETTLED AND IT MOVED IN THE DIRECTION C8 FEARED, HARDER
THAN C8 GUESSED, AND FOR A REASON NO CHAPTER HAD. Replaying the banked
120b route log at ubatch=1 through a harness calibrated to reproduce
three live engine counter sets exactly:

  1. EXPOSURE IMPROVES EXACTLY AS PREDICTED. Decode-shape ACCT is
     6184118048 and exposure is 10.250022, the literal C8 section 4.1
     and C1 section 4.3 banked, confirmed to the byte by measurement of
     the replay rather than by arithmetic. Bar B2 PASSES on Literal A.

  2. THROUGHPUT COLLAPSES BY 31.25x ON THE SAME RUN. The same 8192
     tokens that move 363192785280 bytes of expert weight at ubatch=1024
     move 11350493556480 bytes at ubatch=1: 44335056.7969 bytes per
     token becomes 1385558295.4688 bytes per token. At the 120b's own
     measured lease read rate that is 1093.7872 ms per token of READ
     ALONE, a read-bound ceiling of 0.914255 tokens per second, against
     an 11.32 tok/s figure the house has been quoting.

  3. AND THE LEVER C8 EXPECTED TO SAVE IT DOES NOT WORK AT THIS SCALE.
     C8 section 4.1's headline is that at decode shape "policy
     composition is DOMINANT", evidenced by OB-2's 4.17x load-count
     difference at K=16 of E=32 on the 20b. On the 120b at K=8 of
     E=128, measured here for the first time, the best candidate policy
     buys 1.192997x, not 4.17x: 856398 loads static against 717854
     loads under OB-2's own frozen decay policy. Composition is real
     and it is worth having; it is not a rescue. THE INVERSION IS
     CONFIRMED AND ITS SECOND CLAUSE IS REFUTED.

  4. AND THE LIVE LIMB FAILED ITS IDENTITY BAR, WHICH IS THE MOST
     VALUABLE THING IN THIS RECEIPT. Two live 20b runs differing ONLY
     in the value of -ub produced different answers: PPL 131.2100 at
     ubatch=1024, byte-matching the banked reference, against 132.2931
     at ubatch=1. B3 is a declared stop-ship bar and it FAILED.
     MICRO-BATCH SHAPE IS PART OF THE STATE. Determinism at a fixed
     shape is untouched and the control arm proves it byte-for-byte;
     what is now measured is that the shape itself is an input, and the
     house had been treating it as a free parameter. Section 7 has the
     divergence localized to the row: it begins as a router RANK swap
     between two near-tied experts at layer 0 token 228 and compounds
     with depth to 1.729329 percent of picks.

WHAT THAT MEANS IN ONE SENTENCE, AND IT IS THE SENTENCE THIS ROW EXISTS
TO PRODUCE: at the product's own shape, on this box, the 120b is a
sub-one-token-per-second machine before a single byte is verified or a
single matmul is run, and every batch-1024 figure in the house record
describes a regime the product never enters.

WHAT IT DOES NOT MEAN. It does not kill the design. Section 6's K sweep
is the same measurement turned into a knob, and it says where the
ceiling goes when the resident set grows: 7.498524 tok/s at K=64, which
hyde cannot hold, and about 3.5 tok/s at the largest K hyde can. The
number that decides the product is not exposure and it is not the
policy; it is RESIDENT SET SIZE, and that is a hardware line, which is
C6's to own.


## 1. WHAT WAS RUN, IN WHAT ORDER, AND THE PROOF OF ORDER

  19:20:29Z  prereg banked, sha256 919dde36...
             harness banked, decode_replay.py sha256 690cda63...
  19:20:43Z  limb (a) replay starts. No model, no runlock, no weights.
  19:24:01Z  limb (a) replay ends, rc=0.
  19:26:37Z  limb (a) outputs digested and banked, including
             REPLAY-20B-1CHUNK-1.txt sha256
             2d5b49a01365cb7ce41a6b627175b1d7c7981f2009190eed009955566e04a7f0,
             which carries the limb (b) prediction.
  19:26:46Z  limb (b) launched; ARM A requests the runlock.
  19:27:39Z  the K sweep (limb (a), second pass) runs, nice 10, while
             the sibling holds the lock.
  19:30:05Z  ARM A acquires the runlock after 199 s of waiting.
  19:30:51Z  ARM A releases the lock, rc=0, 46.556995037 s wall.
  19:32:08Z  ARM B requests the runlock after the 75 s courtesy yield.
  19:35:11Z  ARM B acquires the runlock after 183 s of waiting.
  19:35:44Z  the corrected-constant replay pass (deviation D3) ends.
  19:40:57Z  ARM B releases the lock, rc=0, 346.620840198 s wall.
  19:42:14Z  limb (b) ends after ARM B's 75 s courtesy yield.
             Total lock held by this row: 392 s of the 1528 s elapsed.

The prediction file's digest was recorded at 19:26:37Z and the first
model process started at 19:30:05Z. The order is on the record and can
be checked by anyone against the digests in section 12.


## 2. BAR B1  CALIBRATION. PASS ON THREE POINTS, EXACTLY

If the replay cannot reproduce the shape that was measured, its decode
figures mean nothing. Three live counter sets were reproduced, on two
models, at three resident-set sizes, under two accounting regimes.
Every field below is an integer and every one matched.

  CALIBRATION POINT 1  120b, K=8 of 128, L=36, P0-STATIC, ubatch 1024,
  8192 tokens AC-PROSE. Target: the run OB5A-ALLOC-1.md section 6 and
  OB5A-SCOUT-1.md section 3 report.

    field                        predicted     replay        verdict
    lease_events                 27403         27403         MATCH
    lease_bytes_read             363192785280  363192785280  MATCH
    peak_concurrent_lease_bytes  1590451200    1590451200    MATCH
    route_calls                  288           288           MATCH
    per_layer_lease_events       36 values     36 values     MATCH

    the per-layer vector, reproduced element for element:
    957,918,863,812,811,822,862,837,781,727,666,642,643,656,760,763,
    706,740,749,776,751,715,703,718,740,770,750,762,783,760,784,848,
    776,726,682,644

  CALIBRATION POINT 2  20b, K=16 of 32, L=24, P0-STATIC, ubatch 1024,
  32768 tokens AC-PROSE (run lease-k16-prose-a).

    lease_events                 10836         10836         MATCH
    lease_bytes_read             143617743360  143617743360  MATCH
    peak_concurrent_lease_bytes  212060160     212060160     MATCH
    route_calls                  768           768           MATCH
    per_layer_lease_events       24 values     24 values     MATCH
    512,509,493,478,480,472,497,492,452,402,414,399,389,425,445,476,
    434,366,477,462,453,429,440,440

  CALIBRATION POINT 3  20b, K=0 (pure streaming, no expert ever
  resident), ubatch 1024, 32768 tokens AC-PROSE (run lease-k0-prose).
  This point is the sharpest of the three because it exercises the
  peak term at its absolute ceiling, E x per_expert rather than
  (E-K) x per_expert.

    lease_events                 23096         23096         MATCH
    lease_bytes_read             306108840960  306108840960  MATCH
    peak_concurrent_lease_bytes  424120320     424120320     MATCH
    route_calls                  768           768           MATCH
    per_layer_lease_events       24 values     24 values     MATCH
    1024,1021,1005,989,982,984,1009,1004,964,914,926,909,900,937,957,
    988,946,877,989,974,965,936,951,945

  A FOURTH AGREEMENT, NOT PLANNED AND WORTH MORE THAN THE OTHERS. The
  harness also reproduces OB-2's own banked simulator table
  (research/ob2/SIM-PROSE-TABLE-1.txt) exactly on every row this row
  re-ran, which is an agreement with a DIFFERENT INSTRUMENT rather than
  with the same engine:

    policy    K   OB-2 banked   this harness  verdict
    P0-STATIC 16  591548        591548        MATCH
    P2-DECAY  16  469793        469793        MATCH
    P0-STATIC  8  1331123       1331123       MATCH
    P2-DECAY   8  1156494       1156494       MATCH

B1 VERDICT: PASS. Three live counter sets and four independent
simulator rows, all exact, no tolerance used.

  WHAT B1 ALSO SETTLED, AND IT WAS AN OPEN AMBIGUITY. When a policy
  recomputes residency more often than the micro-batch (H=256 inside
  ubatch=1024) the lease accounting has two readings, and the prereg
  banked both rather than choosing. The measured peak decides it:
  under the sub-window reading the dynamic policies would report
  peak_concurrent_lease_bytes 6003953280 on the 120b, a number no run
  has ever produced, against the window-start reading's 1590451200,
  which every run produces. THE ENGINE TAKES ONE RESIDENT SET PER ROUTE
  CALL. Every decode-shape figure in this receipt uses that reading,
  and the sub-window rows are kept in the artifacts as the refuted
  alternative rather than deleted.


## 3. BAR B2  THE TWO PREREGISTERED LITERALS, RECONCILED, AND THE
##            MEASUREMENT

Summary section 4 conflict 6 handed this row two published predictions
for one quantity and RULE R-2 required the term difference localized
before the run. It was, in the prereg, and the localization is clean.

  THE DIFFERENCE, THIS DOCUMENT'S ARITHMETIC:
    6237133088 - 6184118048 = 53015040
    53015040 / 13253760     = 4 exactly

  It is one k-picks term, and C4 section 6.1 labels its own table "AT
  PREFETCH DEPTH 2" and tabulates depth 1 = 53015040 beside depth 2 =
  106030080. The two literals are one model at two prefetch depths, not
  two predictions of one number.

  WHICH DEPTH THE ENGINE HAS IS MEASURED, NOT ASSUMED. At batch shape
  the engine reports peak_concurrent_lease_bytes 1590451200 =
  (E-K) x per_expert = 120 x 13253760, exactly ONE layer's non-resident
  set (OB5A-ALLOC-1.md section 6.2, measured twice). A runtime
  prefetching one layer ahead would hold two layers' transient sets and
  could not report that number. d = 1.

  THE MEASUREMENT. The replay at ubatch=1, 120b, K=8, every candidate
  policy, returns peak_events_one_window 4 and therefore

    peak_concurrent_lease_bytes  53015040
    ACCT_bytes                   2314020128 + 3817082880 + 53015040
                                 = 6184118048
    exposure                     63387346208 / 6184118048 = 10.250022

  and it returns 53015040 under P0-STATIC, P2-DECAY, P1-SLIDING-W512
  and P1-SLIDING-W2048 alike, because at decode shape the peak term is
  a property of the router's top-k and not of the policy at all.

B2 VERDICT: PASS ON LITERAL A. ACCT_decode 6184118048 and exposure
10.250022, the figure C8 section 4.1 and C1 section 4.3 each derived
independently, is the engine of record's decode-shape accounting.

  FOR THE ARCHITECT, per R-2, because withdrawing a chapter's published
  prediction is not a builder's call: C4 section 6.1's 6237133088 /
  10.1629 and C3 section 5.5's 11.1794 / 11.2584 built on it are NOT
  refuted by this row. They are the depth-2 evaluation of the same
  model and the recommendation is that they carry an explicit "at
  prefetch depth 2, a runtime not yet built" qualifier rather than
  being struck. Confirming Literal A on a depth-1 engine says nothing
  about a depth-2 engine except that the house does not have one.

  ONE CONSEQUENCE WORTH SAYING OUT LOUD. Prefetch depth is now a
  PRICED design decision rather than an implementation detail: each
  layer of prefetch costs exactly 4 x 13253760 = 53015040 bytes of
  ACCT on the 120b, which is 0.857 percent of ACCT at depth 1 (THIS
  DOCUMENT'S ARITHMETIC: 53015040 / 6184118048). Given section 4's
  finding that the machine is read-bound by an order of magnitude at
  decode shape, that is the cheapest byte any part of this design has
  ever been offered, and C2's overlap work should have it.


## 4. THE HINGE. THE 120B AT DECODE SHAPE

All rows below: gpt-oss-120b, E=128, L=36, k=4, per_expert 13253760,
8192 tokens AC-PROSE, route log sha256 a32d0051..., replayed under the
window-start engine model calibrated in section 2. Read rate
1266753082 B/s, which is the 120b's own measured lease read rate
(THIS DOCUMENT'S ARITHMETIC: 363192785280 B / 286.711586002 s of
lease_read_ns from p3-120b-k8-prose-a's ob1-stats.txt).

  shape / policy        lease_events  bytes per token  ms/token  read-bound tok/s
  ubatch 1024 STATIC    27403         44335056.7969    34.9990   28.572267
  ubatch 1 STATIC       856398        1385558295.4688  1093.7872  0.914255
  ubatch 1 P2-DECAY     717854        1161409256.7188  916.8395   1.090703
  ubatch 1 P1-SLIDE-512 725689        1174085429.7656  926.8463   1.078928
  ubatch 1 P1-SLIDE-2048 742600       1201445578.1250  948.4450   1.054357

  exposure, same run, both shapes:
    ubatch 1024   63387346208 / 7721554208 = 8.209143   (measured live)
    ubatch 1      63387346208 / 6184118048 = 10.250022  (this replay)

THE THREE NUMBERS THAT MATTER, THIS DOCUMENT'S ARITHMETIC:

  LOADS      856398 / 27403 = 31.2519797102507x more expert loads for
             the same 8192 tokens, same route log, same resident set.
  EXPOSURE   10.250022 / 8.209143 = 1.2486104822391326x better.
  CEILING    28.572267 / 0.914255 = 31.251966902013113, the same
             31.25x in the other direction (the last-digit difference
             against the load ratio is the printed ceilings' rounding,
             not a second effect).

THE EXPOSURE WIN AND THE THROUGHPUT LOSS ARE THE SAME EVENT SEEN FROM
TWO SIDES, and the loss is 25 times the size of the win. Decode shape
holds less at once (4 experts instead of 120) and therefore holds it
for less time, so it must fetch it again, and again, 31 times more
often. C8 section 4.1 said the exposure arithmetic improves while
bytes moved rise "by roughly an order of magnitude and nobody has
measured the cost". It is 31.25x and this is the measurement.

### 4.1 THE PART C8 GOT WRONG, AND IT IS THE PART THAT WAS SUPPOSED TO
###     BE THE GOOD NEWS

C8 section 4.1's second clause: "policy composition is DOMINANT. OB-2's
own replay measures a 4.17x load-count difference between dynamic and
static at K=16 on code (456515 against 1905471), which is a 4.17x
difference in the read-bound throughput ceiling."

On the 120b, measured here:

  policy            loads at decode  ratio against static
  P0-STATIC          856398          1.000000
  P2-DECAY           717854          1.192997461879435
  P1-SLIDING-W512    725689          1.1801171025053432
  P1-SLIDING-W2048   742600          1.153242660921088

1.19x, not 4.17x. THE REASON IS IN OB-2'S OWN NUMBERS AND NOBODY
LOOKED: the 4.17x is not a measurement of what composition buys, it is
a measurement of what a CORPUS-MISMATCHED FROZEN SET COSTS. OB-2's
static control is prose-ranked (P0-STATIC-PROSE) and its 4.17x row is
scored on CODE. On PROSE, against its own corpus, the same comparison
in OB-2's own banked table is 591548 static against 469793 dynamic,
which is 1.2591673354009105x (THIS DOCUMENT'S ARITHMETIC over
research/ob2/SIM-PROSE-TABLE-1.txt). The 120b figure measured here,
1.19x on prose against prose-ranked sets, sits exactly where the 20b's
own like-for-like figure sits.

  WHAT THE 4.17x ACTUALLY MEASURES, and it is still valuable: a
  dynamic policy is DOMAIN-ROBUST and a frozen set is not. Send code to
  a prose-ranked resident set and you pay 4.17x; a policy that learns
  from the route history pays 1.2x. That is an argument for
  composition, and a good one, but it is an argument about robustness
  to domain shift, not about throughput on the domain you ranked for.

  CONSEQUENCE FOR THE LADDER, marked FOR THE ARCHITECT. Rows justified
  on "composition is dominant at decode shape" should be re-read
  against 1.19x, not 4.17x. This does not void C1's composition work:
  domain robustness alone is worth the row, and section 6 shows the
  policy scaling with K rather than washing out (K=64 under the decay
  policy moves 104416 loads against the K=0 floor's 1179648, a factor
  of 11.297578915108796, though most of that factor is K and not the
  policy). It does mean composition cannot be the answer to the
  throughput question, and section 6 says what is. WHAT THIS ROW DID
  NOT MEASURE, and the next row on this harness should: the static
  policy above K=8 on the 120b, which needs frozen resident sets the
  house has not banked for K>8, so the composition ratio at larger K
  is UNVERIFIED.


## 5. WHAT DECODE SHAPE DOES TO EVERY OTHER LEVER IN THE PROGRAM

  THE TRUNK. C8 section 4.1 DERIVED 18.96 TB of whole-trunk streaming
  for one 8192-token answer and concluded it "would make the trunk the
  largest traffic term in the system". This row supplies the term it
  was being compared against, which did not exist until now: the EXPERT
  traffic for that same answer is 11350493556480 B = 11.3505 TB at K=8
  static and 9514264631040 B = 9.5143 TB under the best policy. THE
  TRUNK IS INDEED THE LARGER TERM, by 1.6704x against static and
  1.9928x against the best policy (THIS DOCUMENT'S ARITHMETIC), but it
  is the same order of magnitude rather than a category apart, and at
  K=32 (section 6) the expert term falls to 4.0698 TB and the trunk
  becomes 4.66x it. C8's conclusion holds and gets sharper as K grows.
  Delegated to C3, which owns trunk economics, with all four literals.

  THE READ PATH IS THE WHOLE MACHINE. C8 section 4.2's framing (144 s
  of compute inside 723 s of wall at batch shape) understates it at
  decode shape. THIS DOCUMENT'S ARITHMETIC on the measured 120b run:
  8192 tokens / 723.465495823 s = 11.323276710910648 tok/s achieved
  against a 28.572267 tok/s read-bound ceiling, so the engine achieves
  0.39629951849929973 of its own read ceiling at batch shape.

  A CEILING IS NOT A RATE, AND SECTION 7 SUPPLIES THE CONVERSION
  FACTOR AT THE RIGHT SHAPE. The live decode arm achieved
  3.0813673567645643 tok/s against its own replay-computed ceiling of
  11.834672, an achieved-over-ceiling fraction of 0.2603677868524421
  MEASURED AT DECODE SHAPE rather than carried from batch shape.
  Applying it to the 120b (a transfer across models, so UNVERIFIED, but
  a transfer at the right shape):

    120b K=8 static   0.914255 x 0.2603677868524421 = 0.238 tok/s
    120b K=8 P2-DECAY 1.090703 x 0.2603677868524421 = 0.284 tok/s

  which is 4.200929606619597 and 3.521326059889814 SECONDS PER TOKEN.
  A 200-token answer is between 11.737753532966048 and
  14.00309868873199 minutes.

  P06 IS NOW THE MOST VALUABLE ROW IN TIER 1. The entire result above
  is one division by 1266753082 B/s. P06 (the device census) exists to
  find out whether that number can be beaten by queue depth, mount mode
  or path. Every tok/s figure in this receipt scales linearly with it.
  A 2x read rate is a 2x product.

  THE 20B IS NOT SPARED, IT IS ONLY SMALLER. Same harness, same
  corpus, 32768 tokens:

    model  K   policy     loads at ubatch 1  ms/token  read-bound tok/s
    20b    16  P0-STATIC  591548             97.0554   10.303392
    20b    16  P2-DECAY   469793             77.0790   12.973694
    20b     8  P0-STATIC  1331123            218.3977   4.578804
    20b     8  P2-DECAY   1156494            189.7462   5.270197

  C7 section 3.2's corrected table gives the 20b fully resident on
  prose at 51.12 tok/s AT THE SAME 8 THREADS (its 59.68 figure is a
  10-thread row and that chapter's own defect note forbids mixing
  them). The comparison is a CEILING against an ACHIEVEMENT and is
  stated as such: at decode shape the read term ALONE caps the K=16
  leased path at 10.303392 tok/s against 51.12 achieved fully
  resident, a factor of 4.9614 (THIS DOCUMENT'S ARITHMETIC) before
  verification or compute is counted. At batch shape the same
  configuration's read term was 1.7779 ms per token and invisible.


## 6. THE PRODUCT KNOB, MEASURED AT THE PRODUCT'S SHAPE

C4 section 6.1 calls its K table "THE PRODUCT KNOB ... the first place
in this program where exposure and usability trade against each other
on a surface she will actually touch". That table was arithmetic at
batch shape. This is the same knob measured at decode shape, on the
120b's own route log, under OB-2's frozen decay policy, at read rate
1266753082 B/s. The dynamic policy needs no banked resident-set file,
which is why this sweep reaches K values the house has never frozen a
set for.

  K   loads      ACCT_bytes    exposure   ms/token   read-bound tok/s  resident expert GB
  0   1179648    2367035168    26.779216  1506.6405  0.663728          0.000
  8   717854     6184118048    10.250022   916.8395  1.090703          3.817
  16  525700     10001200928    6.337973   671.4214  1.489378          7.634
  24  398267     13818283808    4.587208   508.6646  1.965932         11.451
  32  307068     17635366688    3.594331   392.1857  2.549813         15.268
  48  182155     25269532448    2.508450   232.6474  4.298349         22.902
  64  104416     32903698208    1.926451   133.3596  7.498524         30.537

READ THAT TABLE FROM BOTH ENDS AND THE PRODUCT ARGUMENT IS RIGHT THERE.

  FROM THE LEFT: K=0, pure streaming, is the highest exposure figure
  this house has ever produced, 26.779216, and it is the least usable
  machine in the table at 0.663728 tok/s. EXPOSURE IS MAXIMIZED EXACTLY
  WHERE USABILITY IS MINIMIZED, and the relationship is not a tension
  to be managed but an identity: exposure counts what you did not hold,
  and what you did not hold you have to read.

  FROM THE RIGHT: the ceiling only reaches 7.498524 tok/s at K=64, and
  K=64 needs 30.537 GB of resident expert bytes on a box with 24029 MB.
  THE KNOB RUNS OUT BEFORE THE BAR IS MET.

  WHERE HYDE ACTUALLY STOPS, THIS DOCUMENT'S ARITHMETIC. Each unit of K
  costs 36 x 13253760 = 477135360 bytes of resident expert state.
  Against the 24029 MB box, with the measured trunk 2314020128 and the
  measured engine buffers at load 941195736 and the measured
  unaccounted column 286522920 (all three from OB5A-ALLOC-1.md P2c),
  and the house's own 6 GB free-RAM rule left standing:

    box            24029 MiB           = 25196232704 B
    minus trunk                          2314020128
    minus engine buffers at load          941195736
    minus the unaccounted column          286522920
    minus the 6 GiB free-RAM rule        6442450944
    expert budget                     = 15212042976 B
    divided by 477135360 per unit of K  = 31.882028143963172

  So hyde's honest ceiling is K = 31, a read-bound 2.5 tok/s, and a
  projected 1.0 tok/s achieved at section 5's measured 0.396 fraction.

  THAT IS THE PURCHASE ARGUMENT, AND IT IS NOW A NUMBER RATHER THAN A
  FEELING. The gap between hyde and a daily-usable 120b is a RAM gap of
  a specific size, and the table prices it: every 477135360 bytes of
  RAM buys one unit of K. Delegated to C6 and to P51's purchase memos,
  with the caveat that the same table would be redrawn entirely by a
  faster read path (section 5, P06).


## 7. LIMB (b). THE LIVE DECODE RUN, AND BARS B3 AND B4

Two arms, one chunk of AC-PROSE each, K=16, the ob1b engine
(sha256 1772264971eb456bf6a60d5204c48fb96eeb5a9b026c42ea1dd6f3690b192932),
8 threads, nice 10, -ngl 0, CUDA_VISIBLE_DEVICES="", --no-mmap,
--no-repack, --no-warmup, --seed 1, --ctx-size 1024, -b 1024. The ONLY
difference between the two command lines is the value of -ub, so any
difference in output is attributable to micro-batch shape and to
nothing else. Each arm took and released the runlock on its own with
the 75 s courtesy yield.

### 7.1 ARM A, THE CONTROL AT ubatch=1024

  exit_rc                      0
  wallclock_s                  46.556995037
  seconds per pass             30.16
  peak RSS                     8203144 kbytes
  identity                     [1]131.2100,
  identity sha256              b0582867e00d2db9a5d8bb8802c7c1c31fb9dbd
                               37d51bd0f56a775ae30c314d8
  route sha256                 8b8dee364ec4249b1bf59b6e1a9d0c17f9c5823
                               f3ad1c01b5e37eca4807db97e

  BOTH DIGESTS BYTE-MATCH THE BANKED 1-CHUNK AC-PROSE REFERENCE
  (research/ob1b's smoke-k0-prose), which was produced at K=0 by the
  same engine. Identity is K-invariant, as OB1B-KNEE-1.md section 12's
  twenty-one runs already said, and now also at one chunk.

  against the replay's prediction, banked at 19:26:37Z:

    field                        predicted     measured      verdict
    lease_events                 351           351           MATCH
    lease_bytes_read             4652069760    4652069760    MATCH
    peak_concurrent_lease_bytes  212060160     212060160     MATCH
    route_calls                  24            24            MATCH
    per_layer_lease_events       16,16,15,15,14,16,15,16,15,14,14,13,
                                 13,13,14,15,15,14,15,15,16,14,14,14
                                 MATCH, element for element

  B3a PASS. B4, ARM A LIMB: PASS, EXACTLY, ZERO TOLERANCE USED.

### 7.2 ARM B, THE DECODE ARM AT ubatch=1

  exit_rc                      0
  wallclock_s                  346.620840198
  seconds per pass             332.32
  peak RSS                     7614940 kbytes
  identity                     [1]132.2931,
  identity sha256              4bb4eac84118c93f8b353f736acbb2baa4ca3f5
                               945646126051ab2b384f3f33c
  route sha256                 65cb7b568cbdcc4d4bebcc39478c1ba6bc88418
                               efcd84da8907cbe1a2e6d8024

  NEITHER DIGEST MATCHES THE BANKED PAIR, AND NEITHER MATCHES ARM A.
  B3b FAILS. It is a declared stop-ship bar and this receipt reports it
  as one.

  against the same banked prediction:

    field                        predicted     measured      verdict
    peak_concurrent_lease_bytes  53015040      53015040      MATCH
    route_calls                  24576         24576         MATCH
    lease_events                 16094         16032         GAP 62
    lease_bytes_read             213306013440  212484280320  GAP 821733120
    per_layer_lease_events       layers 0 and 1 MATCH exactly
                                 (1325 and 1029); layers 2 through 23
                                 all differ

    predicted 1325,1029,651,643,411,567,864,1013,587,506,349,293,789,
              657,974,933,571,360,932,671,483,488,566,432
    measured  1325,1029,648,647,413,565,871,1011,586,507,342,290,797,
              661,972,925,569,355,920,670,479,480,551,419

  THE GAP IS 0.3852367341866534 PERCENT on both counters (they are the
  same counter times a constant). B4 FAILS at its frozen zero
  tolerance, and per the bar's own wording the gap is the finding.

### 7.3 THE GAP, LOCALIZED TO THE ROW

The two route logs cannot be compared by digest, because the engine
emits route rows in the order it computes them: at ubatch=1024 it emits
all 1024 tokens of layer 0 and then layer 1, and at ubatch=1 it emits
layers 0 through 23 for token 0 and then token 1. A digest difference
alone cannot tell an ORDERING difference from a ROUTING difference, so
this row wrote research/ob5b2/route_compare.py, which compares by
(layer, token) key. Literal output, banked as
out2/ROUTE-COMPARE-1.txt:

  EMISSION ORDER IDENTICAL: False
  KEY SETS IDENTICAL: True  (A only 0, B only 0)
  ROWS COMPARED BY (layer,token): 24576
  ROWS WITH A DIFFERENT PICK SET: 3333
  FIRST DIVERGENCE: layer 0 token 228  A[6, 23, 12, 10]  B[6, 23, 10, 12]
  PICK-LEVEL AGREEMENT: 96604 of 98304 = 98.270671 pct
  DIVERGENT ROWS PER LAYER: 0:3,1:21,2:43,3:36,4:62,5:66,6:86,7:96,
    8:99,9:124,10:160,11:165,12:161,13:183,14:172,15:188,16:179,
    17:202,18:166,19:209,20:193,21:199,22:226,23:294
  CANONICAL (layer,token)-SORTED DIGEST A: 8b8dee364ec4249b1bf59b6e1a9
    d0c17f9c5823f3ad1c01b5e37eca4807db97e
  CANONICAL (layer,token)-SORTED DIGEST B: c373be09aef59e0b8249d21426e
    ab690b08bcae020fdde47d101e8bd71ed95d1

READ THAT FIRST DIVERGENCE LINE CAREFULLY, BECAUSE IT IS THE WHOLE
MECHANISM IN ONE ROW. At layer 0, token 228, both arms route to the
same four experts. They disagree only about the RANK of experts 12 and
10, which means two router logits that are equal at ubatch=1024's
accumulation order are not equal at ubatch=1's, or the reverse. Nothing
is wrong; a matmul over 1024 rows and a matvec over 1 row add the same
products in a different order, and floating point is not associative.
That is the seed. Three rows differ at layer 0, twenty-one at layer 1,
and the count climbs monotonically to 294 at layer 23 as each layer's
slightly different output re-enters the next layer's router. The
per-layer lease counts say the same thing from the other side: layers 0
and 1 match the prediction to the event, and layer 2 is the first to
move.

At the end of that cascade the model has computed with a 1.729329
percent different set of experts and reports a perplexity 0.8254706196
174085 percent higher (132.2931 against 131.2100). It is not noise and
it is not a bug; it is the same model taking a very slightly different
path.

### 7.4 WHAT B3's FAILURE DOES AND DOES NOT VOID

  IT DOES NOT TOUCH DETERMINISM AT A FIXED SHAPE. ARM A reproduced a
  banked reference byte-for-byte on both artifacts, at a K the
  reference was not taken at. OB-1 and OB-1b's twenty-one-run identity
  record stands untouched. Two bobs with the same memory, the same
  input AND THE SAME MICRO-BATCH SHAPE still answer identically.

  IT ADDS A TERM TO THE DETERMINISM CLAIM, AND THE HOUSE HAS BEEN
  OMITTING IT. Determinism is defined over state plus input; this row
  measures that MICRO-BATCH SHAPE IS PART OF THAT INPUT. Any published
  determinism claim, any golden, and any digest triple that does not
  pin the batching schedule is under-specified, and a serve that
  batches opportunistically (variable prefill chunking, continuous
  batching, a second request joining a batch) would not be
  byte-reproducible even with the frame, register and brain digests all
  identical. THIS IS A PRODUCT-LAW FINDING AND IT IS HANDED UP, not
  resolved here: it belongs to the goldens law and to C4's serve
  integration.

  IT DOES NOT VOID THE REPLAY, AND THE KILL LINE'S OWN WORDING IS THE
  REASON. C8-S8-2's kill line says a live/replay disagreement means
  "the simulator is not the engine at decode shape". ARM A settles that
  directly: given a route log, the simulator IS the engine, exactly, on
  every counter. What is shape-dependent is the route log, which is the
  simulator's INPUT and not the simulator. The measured cost of
  transferring a batch-shape route log into a decode-shape prediction
  is 0.3852367341866534 percent on the 20b at K=16 on prose, and that
  is the honest error bar to attach to every 120b figure in sections 4
  and 6.

  ON THE 120b THAT TRANSFER ERROR IS UNVERIFIED AND COULD BE LARGER.
  128 experts give more near-ties for a rank swap to find, and 36
  layers give the cascade eight more layers to compound in. Measuring
  it needs a live 120b run at ubatch=1, which section 4 prices at about
  1093.8 ms per token of read alone: 2.5 hours of lock time for one
  8192-token pass. That is the next row, and it is now a priced
  decision rather than an open question.

### 7.5 WHAT THE LIVE ARMS MEASURED THAT NOTHING ELSE COULD

  THE DECODE-SHAPE ACCT TERM IS NOW MEASURED ON A LIVE PROCESS. ARM B
  reports peak_concurrent_lease_bytes 53015040 = 4 x 13253760 = k x
  per_expert, exactly the term B2's Literal A is built on, under a live
  engine at ubatch=1 for the first time in this house. The FORM of the
  decode-shape exposure denominator is no longer a projection. Only the
  120b's VALUE for it remains a replay.

  THE THROUGHPUT COLLAPSE IS NOW MEASURED, NOT PROJECTED. Same model,
  same K, same corpus, same chunk, same lock session, one flag apart:

  every term below is that arm's own measured counter, not a projection:

    arm          tok/s achieved      ms/token  lease_read  lease_verify
    ubatch 1024  33.95225464190982    29.453    6.034 ms    2.045 ms
                                                (20.486 pct) (6.942 pct)
    ubatch 1      3.0813673567645643 324.531  113.210 ms   92.596 ms
                                                (34.884 pct) (28.532 pct)

  an 11.018567639257295x collapse in achieved throughput while bytes
  moved rose 45.675213675213676x (212484280320 / 4652069760, THIS
  DOCUMENT'S ARITHMETIC). The two factors differ because at ubatch=1024
  the machine was compute-bound and read plus verify was 27.4 percent
  of the pass; at ubatch=1 it is 63.4 percent.

  AND A CAUTION ABOUT EVERY READ RATE IN THIS RECEIPT, INCLUDING THE
  ONE ITS HEADLINE DIVIDES BY. Three effective lease read rates are now
  on the record for the same 20b on the same box, and they span 3.3x:

    run                            bytes         seconds        B/s
    armA, 1 chunk, ubatch 1024     4652069760    6.178451142     752950804
    armB, 1 chunk, ubatch 1        212484280320  115.927167664  1832911858
    lease-k0-prose, 32 chunks      306108840960  124.169948910  2465240935

  ARM A, the SHORT run, is the SLOWEST of the three, and arm B, the
  decode run, is faster than it. So this row does NOT support "decode
  shape reads slower"; the variable that moves these rates is run
  length and page-cache warmth, not micro-batch shape. Arm A pays
  17.602424905982904 ms per lease event against arm B's
  7.2309860069860274 ms for the same 13253760 bytes, and the plain
  reading is that arm B re-reads a small working set: 16032 events over
  at most 768 distinct experts is 20.875 reads of each, almost all of
  them warm, while arm A's 351 events are mostly first touches.

  WHAT THAT MEANS FOR SECTION 4's CEILINGS, said plainly: they divide
  by 1266753082 B/s, which is the 120b's own measured rate on a 63 GB
  working set that does not fit the page cache. Nothing here shows that
  rate is wrong for the 120b, and the warm-re-read effect that helps
  the 20b cannot help a model whose experts do not fit. But the spread
  above is 3.3x on one model on one box, which is a large enough spread
  that P06 (the device census) is not a nice-to-have: every tok/s
  figure in this receipt is one division by a number the house has
  measured three different values of.

### 7.6 A DISTRIBUTION NOBODY ASKED FOR AND EVERY LATENCY ROW NEEDS

At ubatch=1 the engine's own chunk timer fires once per micro-batch,
which at this shape is once per token, so ARM B's ob1-stats.txt carries
1023 per-token intervals. THIS IS THE FIRST PER-TOKEN LATENCY
DISTRIBUTION AT DECODE SHAPE IN THIS HOUSE. Nearest-rank, computed from
the raw chunk_ns vector, which is banked verbatim in the run artifacts:

  n        1023 intervals
  min      113054644 ns   =  113.054644 ms
  p50      273578395 ns   =  273.578395 ms
  p95      612734702 ns   =  612.734702 ms
  p99      721048699 ns   =  721.048699 ms
  max     1035075727 ns   = 1035.075727 ms
  mean                       316.933159 ms
  p95/p50  2.239704279279802
  max/min  9.155534796076134

TWO CONSEQUENCES, both for chapters that are not this one.

  FOR C8-R13 (the latency gate can close on noise) AND C5's SEAT BAR.
  Her frozen scheduler bar is p95 <= 250 ms per decision. On this box
  at this shape ONE TOKEN OF DECODE COSTS 273.578395 ms at p50. A
  decision budgeted at 250 ms is 0.914 of a token, and at the p95 token
  it is 0.408. Summary conflict 7 recorded C5's worry that the bar
  could be met-but-dominant and asked that it be said out loud; this is
  the number to say it with, and it is measured rather than argued.

  FOR ANY LATENCY GATE THAT SAMPLES. A distribution with p95/p50 of
  2.24 and max/min of 9.16 on a QUIET box under the runlock is not a
  distribution a controller can threshold on a single sample without
  closing on noise, which is exactly C8-R13's story. The raw vector is
  banked so a gate design can be tested against it offline before any
  gate runs live.

### 7.7 THE LIMB (b) VERDICT

  B3a  ARM A identity and route against the banked pair       PASS
  B3b  ARM B identity and route against the banked pair       FAIL
       STOP-SHIP, declared, reported, localized in 7.3, and its scope
       bounded in 7.4.
  B4   ARM A counters against the replay prediction           PASS exact
       ARM B counters against the replay prediction           FAIL,
       gap 0.3852367341866534 percent, localized and explained.
  B2's decode-shape peak term, live                           CONFIRMED


## 8. THE PERF POINTS THIS ROW BANKS

Reported in C7 section 3.1's frozen row schema. P07 (the schema's
checker) has not run yet, so these rows are written to the schema by
hand and will be the first rows it eats.

P07 (the claims table, its frozen row schema and the checker that
refuses an incomplete row) LANDED WHILE THIS ROW WAS RUNNING, at commit
2c6a282. This row's blocks are therefore written to CLAIMS-RULES-1's
actual grammar and checked with research/claims/claims_check.py rather
than written to the schema by hand. They live in
research/ob5b2/CLAIMS-OB5B2-DECODESHAPE-1.txt with P05-local ids
(CR-P05-nnn) so they cannot collide, because this row commits only its
own paths and research/claims/CLAIMS-OB5B-1.txt belongs to another row.
MERGING THEM INTO THE TABLE OF RECORD IS OWED to whoever holds it next.

  CR-P05-001  ROW. 120b K=8 P0-STATIC at decode shape (the replay).
              exposure 10.250022 on 6184118048; 0.914255 tok/s decode,
              a read-bound ceiling; 1093.7872 ms per token.
  CR-P05-002  ROW. 120b K=8 P2-DECAY at decode shape (the replay).
              exposure 10.250022 on 6184118048; 1.090703 tok/s decode,
              a read-bound ceiling; 916.8395 ms per token.
  CR-P05-003  ROW. 20b K=16 ubatch=1024, 1 chunk, LIVE (arm A).
              33.952255 tok/s eval; identity and route MATCH the banked
              1-chunk reference.
  CR-P05-004  ROW. 20b K=16 ubatch=1, 1 chunk, LIVE (arm B).
              3.081367 tok/s decode; identity and route REFUSED against
              the banked reference; published because it failed.
  CC-P05-001  CLAIM. The decode-shape load factor, 31.2519797102507.
  CC-P05-002  CLAIM. Composition buys 1.192997461879435x, not 4.17x.
  CC-P05-003  CLAIM. Hyde's resident-set ceiling is K=31 and its decode
              ceiling at K=32 is 2.549813 tok/s.
  CC-P05-004  CLAIM. Micro-batch shape is part of the determinism state.
  CC-P05-005  CLAIM. The first per-token latency distribution at decode
              shape: p50 273.578395 ms, p95 612.734702 ms.

CHECKER OUTPUT, literal, `python3 claims_check.py` run from
research/claims against this row's file:

  claims_check.py CHECK-CLAIMS-1
  file: /mnt/f/f32/openbob-wt/research-2/research/ob5b2/CLAIMS-OB5B2-DECODESHAPE-1.txt
  blocks: 9
  surfaces: 0
  refusals: 0
  hazards: 0
  verdict: ACCEPTED
  EXIT=0

IT REFUSED THE FIRST DRAFT SIXTEEN TIMES, which is worth recording
because it is the first evidence outside P07's own fixtures that the
checker does the job it was built for. The refusals were all format and
arithmetic, not content: X10 on a COMMIT field that was prose rather
than a 40-hex, X6 on a THROUGHPUT string that wrote "regime decode
ubatch=1" where the grammar wants "regime decode B=1", X8 on a MODEL
line carrying an explanatory parenthesis inside the byte count, and X8
on an EXPOSURE_RSS line that showed its own division where the grammar
wants the value and the peak. One of those refusals caught a real
rounding error: EXPOSURE_RSS on the decode arm was written 1.552966 and
12109566624 / 7797698560 rounds to 1.552967 at six places. A prose
receipt would have published it.


## 9. THE KILL LINE, AND EXACTLY WHAT IT DOES AND DOES NOT FIRE

C8-R09's kill line: "If the decode-shape replay predicts a read-bound
ceiling below the daily-usable bar C4 and C6 preregister (C8-R12), then
BATCH-1024 EXPOSURE FIGURES MAY NOT BE QUOTED AS PRODUCT FIGURES."

C8-R12 records that that bar HAS NO NUMBER. It is owed from the owner
and its cheapest test is one question to her. This row will not invent
a bar it does not have, so the verdict is returned in threshold form,
which is the most a builder can honestly return:

  THE MEASURED CEILING, 120b, hyde, decode shape, best candidate
  policy, K=8: 1.090703 tokens per second, read alone.
  THE KILL LINE FIRES for any preregistered daily-usable bar above
  1.090703 tok/s at K=8, above 2.549813 tok/s at K=32, or above
  7.498524 tok/s at any K, since no K this box can hold reaches it.
  IT DOES NOT FIRE only if her answer to "what is the slowest bob you
  would use daily" is below roughly one word per second on the 120b.

  AND THE CEILING IS NOT THE RATE. Section 5 converts it with a
  fraction measured at decode shape on a live process: the projected
  ACHIEVED rate is 0.238 tok/s static and 0.284 tok/s under the best
  policy, or one word every 3.5 to 4.2 seconds.

  RECOMMENDATION, one line, for her, in her register: the 120b on hyde
  answers at about one word every four seconds, so either the box gets
  a lot more memory or the big brain is not the daily driver. The
  question C8-R12 wants asked is now worth asking, because there is
  finally a number to hold it against.

  WHAT IS NOT CLAIMED. The 8.209143 exposure figure remains an honest
  measurement of what it measured and this row does not touch it. What
  this row establishes is that it is a LABORATORY figure at a shape the
  product does not use, and that the product's own exposure figure is
  10.250022 at a throughput nobody has yet called acceptable.

  ONE HONEST HEDGE THAT CUTS THE OTHER WAY. Every ceiling here divides
  by a read rate measured on a 63 GB working set that does not fit the
  page cache (OB5A-SCOUT-1.md section 5). A serve holding a large
  resident set warm may read faster than 1266753082 B/s in steady
  state, and P06 is the row that finds out. If the read path is 2x
  faster, every tok/s figure in this receipt doubles and the K=32 row
  reaches 5.1 tok/s. That is the single largest UNVERIFIED lever
  touching this result.


## 10. FINDINGS

  F-P05-1  THE 4.17x IS A DOMAIN-SHIFT FIGURE, NOT A COMPOSITION
           FIGURE. C8 section 4.1 and every row that cites it read
           OB-2's 456515-against-1905471 as what policy composition
           buys. It is what a prose-ranked frozen set costs on code.
           Like-for-like, composition buys 1.2591673354009105x on the
           20b (OB-2's own prose table) and 1.192997461879435x on the
           120b (this row). FOR THE ARCHITECT: the ladder's
           composition rows keep their justification (domain
           robustness) but lose this number.

  F-P05-2  OB2-PREDICTIVE-1.md SECTION 8's DYNAMIC LOAD COLUMN DOES
           NOT MATCH ITS OWN SECTION 3 SIMULATOR TABLE. Section 8
           reports dynamic loads 456515 (code K=16), 474711 (prose
           K=16), 1147145 (code K=8), 1159785 (prose K=8);
           research/ob2/SIM-PROSE-TABLE-1.txt and SIM-CODE-TABLE-1.txt
           report 452228, 469793, 1144492 and 1156494 for the same
           policy, corpus and K. The static column matches exactly in
           every case (1905471, 591548, 2508167, 1331123), so the gap
           is confined to the dynamic policy and is 0.28 to 1.05
           percent, in the same direction every time. This row
           reproduces the SIMULATOR TABLE exactly and cannot reproduce
           the section 8 column. It changes no verdict here (the ratio
           moves from 4.173950472602215 to 4.213518402221888) and it is
           reported because a receipt that disagrees with its own
           banked artifact should be reconciled before it is published
           outside the house. For the falsifier standing duty (P58 /
           C8-S8-11).

  F-P05-3  THE READ-RATE CONSTANT IN THE PREREG WAS 0.00089 PERCENT
           HIGH. See deviation D3. Self-caught, corrected, both sets of
           outputs banked.

  F-P05-4  PREFETCH DEPTH IS NOW PRICED AND IT IS ALMOST FREE. Section
           3. 53015040 bytes per layer of depth, 0.857 percent of ACCT,
           against a machine that is read-bound by 31x. For C2.

  F-P05-5  THE PEAK TERM AT DECODE SHAPE IS POLICY-INDEPENDENT. All
           four candidate policies return peak_concurrent_lease_bytes
           53015040, and the live decode arm measures the same term on
           a running process. At decode shape the exposure denominator
           is set by the router's top-k and the trunk, and no residency
           policy can move it. Every exposure-motivated policy row in
           the ladder is therefore a BANDWIDTH row at the product's
           shape, not an exposure row. This is C1 section 4.3's own
           "DESIGN CONSEQUENCE" confirmed by measurement, and it
           deserves to be stated as a law rather than a consequence.

  F-P05-6  MICRO-BATCH SHAPE IS PART OF THE DETERMINISM STATE, AND
           THIS IS THE FINDING OF THE ROW. Two live runs one flag
           apart produced different perplexities (131.2100 against
           132.2931) and different routing on 3333 of 24576
           (layer, token) rows. It is a stop-ship failure of B3, it is
           reported as one (section 7.7), and its mechanism is a router
           rank swap between near-tied experts compounding with depth
           (section 7.3). CONSEQUENCE, handed up rather than resolved:
           every determinism claim, every golden and every digest
           triple in this program is under-specified unless it pins the
           batching schedule, and a serve that batches opportunistically
           cannot be byte-reproducible even with the frame, register and
           brain digests identical. FOR THE ARCHITECT, and it touches
           the goldens law and C4's serve integration before it touches
           anything in this chapter.

  F-P05-7  THE HOUSE HAS THREE EFFECTIVE READ RATES FOR ONE MODEL ON
           ONE BOX AND THEY SPAN 3.3x (section 7.5: 752950804,
           1832911858 and 2465240935 B/s). Every tok/s figure in this
           program is one division by that number. P06 should treat
           run length and cache warmth as first-class variables
           alongside queue depth, path and mount mode, because this row
           shows they move the rate more than shape does.

  F-P05-8  TWO ROWS ARE WRITING INTO ONE STAGE DIRECTORY. The C4-S1
           sibling's gate-2 sweep stages to
           /mnt/f/f32/stage/research/ob5b2/runs/ and writes to
           /root/ob5b2/ (research/ob5b1/gate2-sweep.sh lines 59 and
           60), which is this row's stage and local run path. Its
           "ob5b2" means OB-5b slice 2 and this row's means OB-5b row
           P05's own directory, and the two meanings collided by
           accident. No file was overwritten (the run names differ,
           g2-* against armA/armB-*), and this row read nothing of
           theirs, but a name collision or a cleanup by either row
           would destroy the other's evidence. FOR THE ARCHITECT: the
           stage namespace needs a rule, and until it has one, the
           safest fix is that whoever is second renames. Named rather
           than fixed unilaterally because the sibling is mid-flight
           and this row does not touch another row's paths.

  F-P05-9  THE SAME SWEEP IS BEING RUN TWICE. That sibling's gate-2
           inputs include RESIDENT-SETS-120B-K8-16-24-32.json and a
           gate2_decode_acct.py, which is a 120b decode-shape
           accounting sweep over the same K values as section 6 of this
           receipt. This row did not read their results and does not
           know whether the two agree. FOR THE ARCHITECT: reconcile
           them deliberately rather than publishing two K tables, and
           note that a genuine independent agreement between two
           separately built instruments would be worth more than either
           table alone.


### 10.1 SCOPE-LEDGER ENTRIES THIS ROW TOUCHES

Named by SUBJECT, not by id. Summary section 4 conflict 5 records that
C4 and C8 both claimed OB5-017 through OB5-023 for different subjects
and that LEDGER-FORMAT-1 section 1.1's banking order resolves it
(C4 at OB5-033..040, C8 at OB5-051..057, summary section 6.2). P07 has
not run, so this row does not assign ids; it names what it settled so
whoever banks them can:

  C8's H-SHAPE (the decode-shape hypothesis). SETTLED IN THE
  AFFIRMATIVE by section 4. Every measurement is at the wrong shape and
  the correction factor is 31.25x on bytes moved.

  C4's DECODE-REGIME EXPOSURE (its projection ACCT_decode 6237133088,
  exposure 10.1629, and the K-sweep table of C4 section 6.1). REFINED,
  NOT REFUTED: the projection is the depth-2 evaluation, the engine of
  record is depth 1, and section 6 supersedes the K-sweep table with a
  measured one at the product's shape.

  C4's TOK/S DISTINCTION (eval against decode). DISCHARGED with
  numbers: the house's 11.32 tok/s is eval at batch shape, and the
  decode-shape read-bound ceiling for the same configuration is
  0.914255 tok/s.


## 11. DEVIATIONS

  D1  THE HARNESS IS NOT RS052's. C8-R09 names "the RS052 lineage,
      research/RS052-LEASE-BUILD-1.txt" as the simulator to replay
      through. RS052 simulates a fixed-point priority-lease RING with
      capacity, expiry and take-late semantics for the CUDA lineage; it
      does not model expert residency over a route log and cannot
      produce lease_events. The harness of record is built on OB-2's
      residency simulator, which is the only instrument in the house
      with an agreement record against this engine, and RS052 is cited
      for its discipline rather than its code. Declared in the prereg
      before the work, not after.

  D2  THE IDENTITY LIMB RUNS AT ONE CHUNK, NOT 32. B3 asks the live
      decode run to hash to the banked pair for its corpus. The 32768-
      token 20b pair cannot be reached at ubatch=1 inside one runlock
      cycle: THIS DOCUMENT'S ARITHMETIC, 591548 x 13253760 =
      7840235220480 B at 2465240935 B/s is 3180.3 s of read alone for
      one arm, before verification (which costs about as much again on
      this engine) or compute, on a box shared with a heavy sibling.
      The run is therefore one chunk, which is a shape this house has
      ALREADY BANKED a reference for (smoke-k0-prose), so the identity
      limb keeps a banked reference rather than becoming self-graded.
      Declared in the prereg with its arithmetic before the run.

  D3  THE PREREG'S READ-RATE CONSTANT WAS WRONG IN THE FOURTH DECIMAL.
      The prereg states 363192785280 / 286.711586002 = 1266764365 B/s.
      The correct value is 1266753082 B/s (integer floor of
      363192785280 x 10^9 / 286711586002 ns), and the prereg's figure
      is 0.0008907023918336123 percent high; the 20b constant was
      2465257248 against a correct 2465240935, 0.0006617203117309099
      percent high. The first replay pass ran with the prereg's
      constants and is banked unchanged in
      /mnt/f/f32/stage/research/ob5b2/out/. The scripts were corrected
      and every rate-derived figure was recomputed in a second pass
      banked in out2/, which is the source of every ms/token and tok/s
      figure in this receipt. No event count, byte count, ACCT or
      exposure figure is affected: those are integers over the route
      log and are identical in both passes. The correction moves the
      headline ceiling from 0.914263 to 0.914255 tok/s.

  D4  THE K SWEEP IS AN ADDITION, NOT A SUBSTITUTION. Section 6 was not
      asked for by C8-S8-2. It was added because the row's own kill
      line is unanswerable without knowing where the knob runs out, and
      because C4 section 6.1 had already declared the K table the
      product knob at the wrong shape. It cost no lock time and no
      model process.


## 12. ARTIFACTS AND DIGESTS

Committed in this repository under research/ob5b2/:

  decode_replay.py       the harness of record, sha256 690cda631812970d
                         f31cc0291f1087c9847cbffada410fab978299b82e19b6ae
                         at the moment the prereg was banked
  run-replay.sh          limb (a), the calibration and decode passes
  run-ksweep.sh          limb (a) second pass, the product knob
  run-ob5b2.sh           limb (b), one run at a chosen -ub
  locked-run-ob5b2.sh    the runlock wrapper, ob1b lineage
  runs-ob5b2.sh          the two-arm live leg
  route_compare.py       compares two route logs by (layer, token)
                         instead of by file order, which is what
                         separated an ordering difference from a
                         routing difference in section 7.3
  CLAIMS-OB5B2-DECODESHAPE-1.txt  this row's nine blocks in P07's
                         frozen row schema, ACCEPTED by its checker

and beside this receipt:

  research/OB5B-DECODESHAPE-1-PREREG.md
  sha256 919dde360ad4b4eb7d868289c85b7451823485c1eacc15432fa68746b0066beb

Off-repo run bytes, per house law, under
/mnt/f/f32/stage/research/ob5b2/ (out/ first pass, out2/ corrected
pass, runs/ the two live arms, logs/ the run logs).

  research/ob5b2/decode_replay.py
    690cda631812970df31cc0291f1087c9847cbffada410fab978299b82e19b6ae
  research/ob5b2/route_compare.py
    2e408e4ad45f29bae8fa3bc32e16cbfdfbdb540a2ec25779d8623e77e976e631
  research/ob5b2/CLAIMS-OB5B2-DECODESHAPE-1.txt
    9916b3553e048c17a67aeb0513125a9e364ae4d2464f11205e79d3f71b06928b
  research/ob5b2/run-replay.sh
    cbe8caf0b6098e05f940e9bb307fe5ddd686c70d604ed7cfea5a0c4e8de69b79
  research/ob5b2/run-ksweep.sh
    4fac86d8349856628be90fab4ce56f49f57066063e7e6d493ef42387827493b5
  research/ob5b2/run-ob5b2.sh
    603f9cb9fe242e10dee1526531bd5f3e09625205b0c8bd2e7d3e66bed6515f4d
  research/ob5b2/locked-run-ob5b2.sh
    0b6c0032413f46d8346d03006404bab9ce31540b55f8a8b2ba504e211e032da7
  research/ob5b2/runs-ob5b2.sh
    5cd773379eb073af76c9d79d5fe5f02c6f4a6ea02b11c45218ecf250833cf16c

  the replay outputs, first pass (the prereg's read-rate constants,
  kept unchanged so deviation D3 can be checked):
    out/CAL1-120B-U1024.txt   df6c0f51c566d67c4b0abc2cc40bcafb4a283bd141dbaf0c934dd6dbe8fa12f0
    out/CAL2-20B-U1024.txt    522b979422fd8c6d00ab9955fe228b0cab3d51f29392e8e158c73cab87fc36f4
    out/CAL3-20B-U1024.txt    10c95ba39177665455e04fff3b8274845b9fed909ecebc19aebc3d7819843b15
    out/DECODE-120B-K8.txt    2541c0f954282f55e78ca4ad696901f9c4b31057a37aa953c7181c2489be4f50
    out/KSWEEP-120B-K0.txt    e1d07b8d526f809f6e7d8d4741895a7baa1957489743b6f883c0e09eec1ce827
    out/KSWEEP-120B-P2DECAY.txt 796cc85946cfe5ead1ba74940aa4d3c0ff9f47f38ae3fc99b76bdc87687bd699
    out/REPLAY-20B-1CHUNK-1.txt 2d5b49a01365cb7ce41a6b627175b1d7c7981f2009190eed009955566e04a7f0
                                (the limb (b) prediction, digested at
                                19:26:37Z, before the first model process)
    out/XCHECK-20B-PROSE.txt  e15e420666a633ed34e3a59d7a8fa7d46aa04e20c6572ee42d9c057db47e3d83
    out/REPLAY-RUNLOG-1.txt   3e64ebefb8f0198bcf4a8f07b0ea79f01455679061b5c8dfa0412b262df9149a
    out/KSWEEP-RUNLOG-1.txt   b55e88061ee112b676f7c1b43f20afebbe30d2a8b6a0a8275becef01d1349a9d

  the replay outputs, corrected pass (the source of every rate-derived
  figure in this receipt):
    out2/CAL1-120B-U1024.txt  d796c4e8c46a9b5c523cbc04a15da1cd43aa1344c901df1e60ce9c3a83a48ec9
    out2/CAL2-20B-U1024.txt   9752afdc25c62cc455ff699cdf7aaf9bc5d8a2c5d146f42378514084ef18a933
    out2/CAL3-20B-U1024.txt   a464e80dc0796bf7a4af406e9f791569d5f5a5727a5c261efab51805a7cf9f26
    out2/DECODE-120B-K8.txt   bd43632018e9c0212646cc85361bfe3559f413c7058a900a773d5f9d7c16544f
    out2/KSWEEP-120B-K0.txt   e19f2e90a2937aaf8bde7c658be6c2a270ab10e1e9301fe04e84155d5525dd80
    out2/KSWEEP-120B-P2DECAY.txt 23640c5900bd93df5bccfbb40cc6733716597b63c0a8c8f26f70f1e8119c9e2f
    out2/REPLAY-20B-1CHUNK-1.txt b9a7ad12fe32e26825e0a5e2c889ceabdcc0011381f287b2ee334ec61cf92f5f
    out2/XCHECK-20B-PROSE.txt 12f6f413314514a08aaa35bd7c6d6462a63d12c95209116a6f47f0b69acd9703
    out2/ROUTE-COMPARE-1.txt  9f1029b47b18735f34aba3707f12623dd4a4bb3b8074c6be24c033a90f79d5a0
    out2/REPLAY-RUNLOG-2.txt  dd1200dbbfb75951b6af2db4f4d4369e06ccde0659a8e07a12c77b74d08baab4
    out2/KSWEEP-RUNLOG-2.txt  fdc1c3b558ec5a159b5b75b3a4ea9cd36f59c2d0ff5d3773adc08a88d231d6bf

  the two live arms:
    runs/armA-u1024-k16-prose/identity.txt
      b0582867e00d2db9a5d8bb8802c7c1c31fb9dbd37d51bd0f56a775ae30c314d8
    runs/armA-u1024-k16-prose/route.log
      8b8dee364ec4249b1bf59b6e1a9d0c17f9c5823f3ad1c01b5e37eca4807db97e
    runs/armA-u1024-k16-prose/ob1-stats.txt
      80799a9e9cf5b05eba96a3d86306fc2c148a32825e2c3bd4f01a2cf504c973f8
    runs/armB-u1-k16-prose/identity.txt
      4bb4eac84118c93f8b353f736acbb2baa4ca3f5945646126051ab2b384f3f33c
    runs/armB-u1-k16-prose/route.log
      65cb7b568cbdcc4d4bebcc39478c1ba6bc88418efcd84da8907cbe1a2e6d8024
    runs/armB-u1-k16-prose/ob1-stats.txt
      58af6f89b72de001c3b4b07c498a99c078df606d515b037b437d0cc7d35f143f
    logs/RUNLOG-LIMB-B-1.txt
      ada8f842012ded52ee7a6de070fa00f931c67d36044441a8bae764f13b4428b8
    logs/armA-u1024-k16-prose.log
      2eb773875cb31711b3295cba6719f4fc256fef129b1d6fbae7bb367f6306ac50
    logs/armB-u1-k16-prose.log
      cba2aef85c22368efcdc7b809b5226e126ef0f5c149a46dfea39ef6ae6978268

  NOT THIS ROW'S: /mnt/f/f32/stage/research/ob5b2/runs/ also contains
  g2-* directories written by the C4-S1 sibling, whose gate-2 sweep
  stages to this same path (research/ob5b1/gate2-sweep.sh line 60).
  They are named here so nobody mistakes them for this row's artifacts,
  and they were neither read nor touched. See finding F-P05-8.

Inputs, all pre-existing and unmodified by this row:

  120b route log   a32d0051bd6d68f2777e64c7b889ae48d56621e9701b107fcef88c0e30cd89c1
  20b prose route  4777aa8319f25d6e367f761ef12c7bec81a9ff7896bfed1b8ea0326b5dffc3df
  20b 1-chunk route 8b8dee364ec4249b1bf59b6e1a9d0c17f9c5823f3ad1c01b5e37eca4807db97e
  RESIDENT-SETS-120B-K8.json  8053f18a70030ad2ac2e59fe220a064ee26f35ad4eb3876bbb7c65f6e994530b
  RESIDENT-SETS.json          dc1ce20c4d5aed376b6a730a3596ae188f2b4509be73549bf8d05d4275125b85
  AC-PROSE.txt                310710a1f3e04484fcef2d0cb4ac1de93a8a6e02ced07ed3f2c9b79505e81a8e
  llama-perplexity            1772264971eb456bf6a60d5204c48fb96eeb5a9b026c42ea1dd6f3690b192932
  libllama.so.0               bfa8166ed641ea664e559af5402d56ef580fc6f90cc226d0b5859d6e023b37b0
  gpt-oss-20b-MXFP4.gguf      12109566624 bytes


## 13. PROCESS

Limb (a) ran with no model process, no runlock, no weights and no card
contact. Limb (b) ran under the house runlock, taken and released per
arm with the 75 s courtesy yield, free RAM checked at 22 GB against the
6 GB bar before each arm, 8 threads at nice 10, CUDA_VISIBLE_DEVICES
empty. pid 654 and pid 489 were counted alive at the start and end of
every arm and were never signalled, renamed, reniced or killed. The
mini was not contacted. Nothing was downloaded. Every script was
written to a file and CRLF-stripped before execution per house law.
