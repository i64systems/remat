# OB1B-KNEE-1: HUNTING THE E2x KNEE ON GPT-OSS-20B (K=2, K=1, K=0),
# AND ONE WALL-CLOCK-BOUNDING POINT ON GPT-OSS-120B

Lane: research (CUDA/inventor lane), venue hyde, on-machine. Branch research-2,
worktree F:\f32\openbob-wt\research-2. Builder 2 of OB-1b (engine change, runs,
receipt). Binding document: research/OB1B-KNEE-1-PREREG.md, committed as c8d86e5
before this instrument existed. Pure ASCII, no em dashes. Every number below is
literal output of the command named beside it; a command that failed is reported
verbatim rather than replaced with a plausible value.

## 0. WHAT THIS DOCUMENT IS

OB-1 (research/OB1-EXPOSURE-1.md, and its run log research/ob1/RUNLOG-1.txt)
showed that a bounded, statically ranked subset of a mixture-of-experts model's
experts can be kept resident while the rest are read from disk on demand,
WITHOUT changing a single output byte. It measured that at three resident-set
sizes, K in {16, 8, 4} of 32 experts per layer, and stopped there. Its own
numbers left an obvious loose end: the fraction of routed experts that MISSED
the resident set climbed steeply (18.8 to 62.1 percent on prose, 60.6 to 90.3
percent on code) while the latency cost barely moved (p95 rose only 1.25x to
1.54x). Something that expensive-looking was not actually costing much, so the
curve's KNEE had not been found.

THE OPEN QUESTION this leg was given, in the program's own frame: what is the
maximum capacity exposure (logical model bytes divided by peak fast-resident
bytes) that still holds p95 latency at or below 2.0x the fully resident
baseline, with output identity still exact? Known going in: E2x is at least
3.388, the value OB-1 measured at K=4.

This leg extends the sweep DOWNWARD past OB-1's floor: K=2, K=1, and K=0, the
last being the PURE STREAMING point where the resident set is empty and every
routed expert is leased on every use. It also takes one point on gpt-oss-120b
(128 experts per layer, 36 layers, K=8), a model nothing in this program has
run leased residency on before.

## 1. THE MACHINE, THE WALLS, AND WHAT CHANGED FROM OB-1

  Host          f32-HYDE, Windows 11 + WSL2 Ubuntu
  CPU           AMD Ryzen 9 5900X, 12 cores / 24 threads
  WSL RAM       24029 MB total, 6144 MB swap (literal: free -m)
  GPU           hidden from every run in this leg (CUDA_VISIBLE_DEVICES="")
  Models        /root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf
                  12109566624 bytes, sha256 27cd6c43...
                /root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf
                  63387346208 bytes, sha256 582bd40f...
  Corpora       AC-PROSE 262144 bytes,
                  sha256 310710a1f3e04484fcef2d0cb4ac1de93a8a6e02ced07ed3f2c9b79505e81a8e
                AC-CODE 1576144 bytes,
                  sha256 d2db5c682d5f52a4383d188fee9d25f592a15d69763dbf886b5614c953e7f3fc
                Both verified by this leg against OB-1's own committed corpora.
  Thread wall   at most 8 compute threads, every run under nice 10 (this leg's
                house wall; OB-1 ran at 10)
  Runlock       every model run holds /mnt/f/f32/stage/research/runlock, taken
                and released PER RUN so the three sibling workflows on this box
                interleave between this leg's runs
  Untouched     pid 654 (openbob serve) and pid 489 (searxng) were confirmed
                alive before and after every run and were never signalled

TWO THINGS DIFFER FROM OB-1 AND BOTH FORCE WORK ON THIS LEG.

THE THREAD WALL. OB-1 published its p95 figures at --threads 10; this leg's wall
is 8. A cost ratio computed against a baseline measured at a different thread
count would be meaningless, because the leased arm's extra work is disk reading
and hashing whose cost does not fall when more compute threads are added, while
the baseline's cost does. This leg therefore measures ITS OWN fully resident
references at 8 threads and computes every ratio against those. Whether the
8-thread runs reproduce OB-1's 10-thread OUTPUT BYTES is a separate question,
answered from the identity digests in section 5, not assumed.

THE ENGINE. The landed OB-1 engine refuses K=0 outright. That is section 2.

## 2. THE ENGINE CHANGE: ONE BYTE OF MACHINE CODE

Builder 1's prereg (section 1.1) diagnosed, by reading the committed diff, that
research/ob1/lease-engine.patch rejects an empty resident set before it opens
anything:

    if (g_K <= 0 || g_K > g_E) ob1_fatal("OB1_K=%d out of range 1..%d", g_K, g_E);

and that the rest of the engine already handles K=0 correctly: the resident-set
JSON parser accepts an empty list, and the per-expert load loop with an all-zero
resident array simply loads nothing, which is the pure-streaming point's own
definition. This leg confirmed that by reading src/ob1-lease.cpp directly (the
guard is at line 719 of the source, not of the patch) and made the single change
builder 1 specified. The complete diff is committed as research/ob1b/knee.patch:

    -    if (g_K <= 0 || g_K > g_E) ob1_fatal("OB1_K=%d out of range 1..%d", g_K, g_E);
    +    if (g_K <  0 || g_K > g_E) ob1_fatal("OB1_K=%d out of range 0..%d", g_K, g_E);

Fork discipline: the change lives in this leg's OWN worktree, /root/ob1b/llama.cpp,
branch ob1b created from c087083. The ob1 branch and the sibling worktrees
(ob2, ob3, ob4) were never touched.

### 2.1 THE BUILD IS OBJECT REUSE, AND IT IS VERIFIED RATHER THAN ASSUMED

The landed OB-1 build is configured GGML_CUDA=ON. A from-scratch reconfigure
therefore recompiles several hundred nvcc translation units for a change of one
character in one CPU-side file; the first attempt at this was still grinding
through ggml-cuda/template-instances after three minutes at -j4 and was
abandoned. research/ob1b/build-ob1b.sh instead copies the landed build tree into
the ob1b worktree, rewrites the absolute source paths inside it, lets cmake
regenerate its makefiles against the new source root, and recompiles only what
changed.

That is a shortcut, so research/ob1b/verify-binary.sh proves it was a sound one
instead of asserting it. It rebuilds the engine twice in the ob1b tree, once
from PRISTINE c087083 source and once from patched source, and compares the
executable code of all three libraries. Literal output
(research/ob1b/VERIFY-BINARY-1.txt):

    landed   .text      2645458 bytes  850e33acf7be0facb41cacc5fb1bcda2a0eeb7c63d6e735fd5bfca3c9d9142ca
    phaseA   .text      2645458 bytes  850e33acf7be0facb41cacc5fb1bcda2a0eeb7c63d6e735fd5bfca3c9d9142ca
    phaseB   .text      2645458 bytes  f0336c94d5f1a7eb2697b171e7d4c0f67b5040e6932cae44dcdf2a3002f04af3

    A) landed .text == phaseA .text : MATCH
    B) phaseA .text != phaseB .text : DIFFER, as the guard edit requires
       differing bytes between pristine and patched .text:
       1
       first differing byte offsets:
    1299090 216 210

So the ob1b tree reproduces the landed engine's executable code BYTE FOR BYTE
from pristine source, and the entire OB-1b engine change is ONE BYTE of machine
code at .text offset 1299090, octal 216 becoming 210, which is the comparison in
that guard line changing from "less or equal" to "less". Nothing else moved.

WHOLE-FILE digests do differ, and the cause is named rather than waved at: the
linker writes the library's own search path into the file, and the ob1b tree
lives at a different path. Literal readelf output for both:

    landed:  RUNPATH  Library runpath: [/root/rs053/llama.cpp/build/bin:]
    ob1b:    RUNPATH  Library runpath: [/root/ob1b/llama.cpp/build/bin:]

That string is the only occurrence of "ob1b/llama.cpp" anywhere in the rebuilt
library (measured: `strings ... | grep -c` returns 1), which is why the .text
comparison above is the meaningful one. The binaries every run in this leg used:

    llama-perplexity  1772264971eb456bf6a60d5204c48fb96eeb5a9b026c42ea1dd6f3690b192932
    libllama.so.0     bfa8166ed641ea664e559af5402d56ef580fc6f90cc226d0b5859d6e023b37b0

### 2.2 p99 WAS ADDED WITHOUT TOUCHING THE ENGINE

Per the prereg's section 4, timing granularity stays at CHUNK level (one
1024-token micro-batch), because the route-log callback the engine timestamps
fires once per (layer, micro-batch) and the only way to get a finer boundary is
to shrink the micro-batch, which would change the batch shape and therefore the
very numbers under comparison. That decision is inherited, not reopened.

p99 is new here and needed no engine change: the engine already writes the full
per-chunk interval series (chunk_ns) on every run, lease and resident alike, so
research/ob1b/analyze_knee.py simply takes another percentile of data already
banked. No run was repeated for it.

## 3. PREDICTIONS BANKED BEFORE THE RUNS

The lease engine's behaviour is a pure function of the route log: at each
(layer, micro-batch) callback it leases exactly the DISTINCT routed experts of
that micro-batch that are not resident, and drops them at the next layer. The
route logs were already banked by OB-1, so both of the engine's main counters
could be computed EXACTLY in advance and then checked against the engine's own
measurement. research/ob1b/predict_leases.py does that.

VALIDATION FIRST, against OB-1's own measured runs (research/ob1b/PREDICT-LEASES.txt):

    corpus  K     predicted lease_events    OB-1 measured    peak_concurrent_B
    prose   16              10836               10836            212060160
    prose    8              16954               16954            318090240
    prose    4              20024               20024            371105280
    code    16              12092               12092            212060160
    code     8              18100               18100            318090240
    code     4              21115               21115            371105280

Six of six, exactly. The predicted peak_concurrent also equals (E-K) x 13253760
at every one of those points, which turns builder 1's PREDICTION RULE from an
argument about batch shape into a fact read off the route logs.

PREDICTIONS FOR THIS LEG'S NEW POINTS, recorded before any of them ran
(committed in a782231, ahead of the matrix):

    corpus  K     predicted lease_events    predicted peak_concurrent_B
    prose    2              21560                    397612800
    prose    1              22328                    410866560
    prose    0              23096                    424120320
    code     2              22611                    397612800
    code     1              23364                    410866560
    code     0              24078                    424120320

## 4. THE ACCOUNTING, RE-DERIVED FROM FIRST PRINCIPLES

research/ob1b/exposure_arith.py recomputes every byte figure this leg quotes
rather than carrying builder 1's arithmetic forward. Literal output
(research/ob1b/EXPOSURE-ARITH.txt), abbreviated:

    gpt-oss-20b   total=12109566624  L=24 E=32 per_expert=13253760
                  total_expert_bytes = 24 x 32 x 13253760 = 10178887680
                  resident_always    = 1930678944   (15.94 pct of the model)
    gpt-oss-120b  total=63387346208  L=36 E=128 per_expert=13253760
                  total_expert_bytes = 36 x 128 x 13253760 = 61073326080
                  resident_always    = 2314020128   (3.65 pct of the model)

    EXPOSURE(K) = TOTAL_MODEL_BYTES
                  / (resident_always + K x L x per_expert + peak_concurrent)

The rule reproduces OB-1's three measured ACCT figures and exposures exactly
(1.674400, 2.526252, 3.388101), which is the check that licenses using it at
unmeasured K.

THE FLOOR OF THIS DESIGN, which turns out to be the whole story of section 7:

    gpt-oss-20b   K=0 ACCT = resident_always 1930678944 + peak 424120320
                           = 2354799264
                  max exposure at K=0 = 5.142505
                  resident_always is 82.0 pct of that floor
    gpt-oss-120b  K=0 ACCT = 2314020128 + 1696481280 = 4010501408
                  max exposure at K=0 = 15.805342
                  resident_always is 57.7 pct of that floor

K=0 is the END of this curve, not a waypoint: there is no resident set smaller
than empty. Whatever exposure the scheme reaches at K=0 is the most it can ever
reach on that model, and on the 20b model four fifths of what remains is not
expert weights at all.

## 5. THE REFERENCES, AND TWO QUESTIONS THEY SETTLE AT ONCE

This leg's two fully resident runs, at 8 threads on the ob1b binary:

  run           wall_s    peak RSS KB   identity sha256          route sha256
  res8-prose-a  641.015      12991324   96049ccf...d551925       4777aa83...dffc3df
  res8-code-a   633.580      13008364   9acdf5ef...62aa0ae8      f0c3f341...9bff41c77

Both digests are BYTE-IDENTICAL to OB-1's own banked fully resident references
(research/ob1/RUNLOG-1.txt section 7: prose 96049ccf8ca241bf58233afe13ed75e2ca
43180d81973360d04cebc80d551925 / 4777aa8319f25d6e367f761ef12c7bec81a9ff7896bfed
1b8ea0326b5dffc3df, code 9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f325
4762aa0ae8 / f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77),
on the identity artifact AND the routing log, on both corpora.

That single fact settles two questions this leg would otherwise have had to
hedge on, and it settles them by measurement rather than by argument:

  1. THE REBUILT ENGINE IS OUTPUT-EQUIVALENT TO THE LANDED ONE. Section 2.1
     showed the ob1b .text is byte-identical to the landed .text except for one
     byte in the K guard. These runs confirm it where it counts: the rebuilt
     binary produces the landed binary's exact output bytes over 32768 tokens on
     both corpora. The object-reuse build shortcut is therefore not a caveat
     hanging over any number in this document.

  2. THE OUTPUT IS THREAD-COUNT INVARIANT. OB-1 ran at --threads 10 and this leg
     at 8, and the bytes are the same. So this leg's runs are directly
     comparable to OB-1's at the byte level, and OB-1's K=16/8/4 rows can be
     carried into the same curve as this leg's K=2/1/0 rows without an
     identity asterisk.

WHAT IS NOT COMPARABLE ACROSS THE TWO LEGS IS TIME, and this is why this leg
measured its own baselines. At 8 threads the fully resident prose run takes
641.015 s against OB-1's 549.04 s at 10 threads, a factor of 1.1675, and its p95
is 18691.9 ms against OB-1's 16025.8 ms, a factor of 1.1664. The two factors
agree to within 0.1 percent, which is what should happen if the extra threads
buy plain compute throughput and nothing else. Every cost ratio in section 7 is
therefore computed against THIS leg's 8-thread baselines, never against OB-1's
10-thread figures.

Baseline percentiles, over the 31 measured per-chunk intervals of each run:

  run           p50_ms     p95_ms     p99_ms   peak RSS bytes   EXP_rss
  res8-prose-a  18233.7    18691.9    18995.8     13303115776  0.910280
  res8-code-a   (section 7 table)

A note on baseline stability, stated rather than re-measured: OB-1 ran its
resident prose case twice (res-prose-a / res-prose-b) and got byte-identical
output with p95 differing by 0.9 percent (16025.8 vs 15889.5 ms). This leg did
not repeat its own baselines, to conserve runlock time on a box shared with
three sibling workflows; it relies on OB-1's demonstration that this baseline is
stable, and says so here rather than leaving it implied.

## 6. THE PURE STREAMING POINT, K=0

This is the run the whole leg was built to make: an EMPTY resident set, every
routed expert leased on every use, on a model whose engine refused to accept
K=0 until this leg changed one byte of it.

Literal, from research/ob1b/logs/ and the engine's own ob1-stats.txt files:

                            lease-k0-prose   lease-k0-code  lease-k0-code-b
  exit_rc                                0               0                0
  wallclock_s                   916.076807      923.879122       947.302172
  Maximum resident set size     3479932 KB      3499860 KB       3493684 KB
  resident_bytes_loaded                  0               0                0
  lease_events                       23096           24078            24078
  lease_bytes_read            306108840960    319124033280     319124033280
  peak_concurrent_lease_bytes    424120320       424120320        424120320
  identity vs its resident ref       MATCH           MATCH            MATCH
  route    vs its resident ref       MATCH           MATCH            MATCH

lease-k0-code-b is the A/A repeat the task asked for. It is byte-identical to
lease-k0-code on both the identity artifact and the route log, and its lease
counters are identical to the event: 24078 leases, 319124033280 bytes, the same
peak. The leased path at an empty resident set is as repeatable as the resident
one.

EVERY PRE-REGISTERED PREDICTION HIT EXACTLY, ON BOTH CORPORA. Section 3 banked,
before either run existed, lease_events = 23096 (prose) and 24078 (code) and
peak_concurrent = 424120320 for both. The engine measured 23096, 24078 and
424120320. lease_bytes_read is 23096 x 13253760 = 306108840960 and
24078 x 13253760 = 319124033280, to the byte. The prediction rule is no longer
an extrapolation at this point; it is a measurement that agrees with one.

resident_bytes_loaded = 0 is the sentence that matters most. The engine loaded
NO expert bytes at model-load time at all, and the runs still reproduced the
fully resident output byte for byte over 32768 tokens on both the perplexity
artifact and the routing log, on BOTH corpora. All 10178887680 bytes of expert
weights in the file, 84.06 percent of the model, were absent from memory at load
and arrived only as leases the router asked for, verified against their sha256
digests, and were dropped again.

MEMORY, measured two ways:

  corpus  peak process RSS                       EXP_rss   ACCT_bytes  EXP_acct
  prose   13303115776 -> 3563450368  3.733x less  3.398270  2354799264  5.142505
  code    13320564736 -> 3583856640  3.717x less  3.378920  2354799264  5.142505

The ACCT figure equals section 4's PREDICTED 5.142505 exactly, because the
predicted term in it (peak_concurrent) was the one these runs measured.

## 7. THE FULL E2x CURVE

OB-1's three rows are cited from research/ob1/RUNLOG-1.txt; this leg's rows are
measured here. Section 5 established that the two legs' runs are byte-comparable,
so they belong in one table.

  K    RESIDENT bytes   EXP_acct   EXP_rss    identity   source
  16      7232182944    1.674400   1.435663    exact     OB-1 (measured)
   8      4793491104    2.526252   2.017932    exact     OB-1 (measured)
   4      3574145184    3.388101   2.532820    exact     OB-1 (measured)
   2      2964472224    4.084898   2.902415    exact     THIS LEG (measured)
   1      2659635744    4.553092   3.130930    exact     THIS LEG (measured)
   0      2354799264    5.142505   3.398270    exact     THIS LEG (measured)

EXP_rss is quoted on the prose corpus in every row for comparability. The code
corpus gives 2.888364 at K=2, 3.114629 at K=1, and 3.378920 / 3.384894 at K=0.
EXP_acct is corpus-independent by construction, since peak_concurrent reached its
full (E-K) value on every single run.

EVERY ONE OF THIS LEG'S THREE POINTS IS A MEASUREMENT THAT AGREES EXACTLY WITH A
PREDICTION MADE BEFORE IT. The prereg labelled K in {2,1,0} PREDICTED. All three
are now measured, and all three landed on their predicted values to the digit:

  K   predicted peak_concurrent   measured   predicted EXP_acct   measured
  2            397612800         397612800        4.084898       4.084898
  1            410866560         410866560        4.553092       4.553092
  0            424120320         424120320        5.142505       5.142505

and every pre-registered lease_events figure hit exactly, on both corpora, six of
six:

  corpus  K   predicted   measured        corpus  K   predicted   measured
  prose   2      21560      21560         code    2      22611      22611
  prose   1      22328      22328         code    1      23364      23364
  prose   0      23096      23096         code    0      24078      24078

Nothing in section 3 or section 4 remains an extrapolation. The rule
peak_concurrent(K) = (E-K) x PER_EXPERT is now measured at six of the six K
values this program has run.

## 8. COST, AND THE KNEE VERDICT

Percentiles are over the 31 measured per-chunk (1024-token) intervals of each
run, nearest-rank. p99 is new in this leg and needed no engine change.

  run              corpus   p50_ms    p95_ms    p99_ms   wall_s  p95 ratio  verdict
  res8-prose-a     prose   18233.7   18691.9   18995.8   641.01   baseline
  res8-code-a      code    17758.8   18214.6   18331.5   633.57   baseline
  lease-k2-prose   prose   28038.5   28483.8   28732.9   900.05    1.5239    PASS
  lease-k2-code    code    28366.7   28704.7   28856.4   915.29    1.5759    PASS
  lease-k1-prose   prose   28745.8   29456.4   29649.2   926.87    1.5759    PASS
  lease-k1-code    code    28637.0   29147.1   54156.0   954.73    1.6002    PASS
  lease-k0-prose   prose   26437.7   27705.7   29308.2   916.07    1.4822    PASS
  lease-k0-code    code    26726.0   27406.8   28225.9   923.87    1.5047    PASS
  lease-k0-code-b  code    29014.8   32309.5   33352.5   947.28    1.7738    PASS

SEVEN LEASED RUNS, SEVEN PASSES, AND IDENTITY EXACT ON EVERY ONE. But two things
in that table have to be said before the verdict, because both cut against
reading it too cleanly.

FIRST, THE A/A PAIR SETS THE NOISE FLOOR. lease-k0-code and lease-k0-code-b are
the same run. They produced byte-identical output and lease counters identical to
the event. Their p95 ratios are 1.5047 and 1.7738, 17.9 percent apart, while
their whole-run wall clocks differ by only 2.5 percent (923.87 vs 947.28 s). So
p95 on this box carries real run-to-run noise that this leg cannot design away:
five workflows shared the machine, and while the runlock serialises MODEL runs it
does not serialise the siblings' analysis processes between them. The entire
spread of p95 ratios across all seven runs, 1.4822 to 1.7738, is no wider than
the spread between two runs that were the same run.

SECOND, "p99" OVER 31 SAMPLES IS JUST THE MAXIMUM. A 32-chunk run yields 31
intervals, and nearest-rank at 0.99 selects ceil(0.99 x 31) = 31, the largest
sample; p95 selects the 30th, the second largest. So the p99 column is a single
worst chunk, not a tail statistic, and it behaves like one: lease-k1-code's p99
of 54156.0 ms against a p50 of 28637.0 ms is one anomalous chunk out of 31, and
it makes that run's p99 ratio 2.9543, above the 2.0x line that its p95 clears
comfortably at 1.6002. That is reported rather than dropped. It does not move the
verdict, because the frozen bar is on p95 and because a single chunk on a box
running five workflows is not evidence about the lease design; but anyone quoting
the p99 column should know it is a maximum over 31 observations.

The honest way to state the cost limb is therefore against the WORST observed p95
ratio, not the best: across seven leased runs spanning K=2, K=1 and K=0 on both
corpora, leased p95 ranged 1.4822 to 1.7738 times the fully resident baseline.
All seven pass the 2.0x bar. The margin at the worst observation is 11 percent.

Note also that the ratios do not order themselves by K at all: K=2 gives 1.5239
and 1.5759, K=1 gives 1.5759 and 1.6002, K=0 gives 1.4822, 1.5047 and 1.7738. The
lowest and the highest ratio in the whole table are both at K=0. The step from
K=2 to K=0 is smaller than the box's own measurement noise, which is exactly what
section 8's flat cost-per-byte finding predicts: those three K values differ by
only two experts' worth of leasing out of thirty-two, about 7 percent of byte
volume, across a range over which exposure climbs 26 percent.

THE VERDICT, stated plainly: THE KNEE WAS NOT FOUND, AND ON THIS MODEL IT DOES
NOT EXIST.

That is not a failure to locate it. It is a structural result, and the reason is
section 4's arithmetic. The bar was p95 at or below 2.0x baseline with identity
exact. Across all seven leased runs the worst measured p95 ratio is 1.7738, every
one is inside the bar, and identity is exact on every one. K=0 is the END OF THE
CURVE: there is no resident set smaller than empty, so there is no K at which
this scheme could be pushed further and made to breach the bar. The scheme runs
out of experts to evict before it runs out of latency budget.

So the answer to the open question, for static bounded residency on gpt-oss-20b
under this invocation shape, is:

  E2x = 5.142505 accounted (3.398270 by peak process RSS), reached at K=0,
  and it is a CEILING set by the design rather than a knee set by cost.

WHY COST NEVER BIT, measured rather than argued. The prereg named the one thing
that could have put the knee above K=0: a fixed per-lease-event overhead that
would dominate once K got small. It does not exist. Read and verify rates, from
the engines' own counters (research/ob1b/cost_decomp.py):

  leg   run                  K   events        bytes_moved  read_GB/s  ver_GB/s
  OB-1  lease-k16-prose-a   16    10836       143617743360     2.4273    2.4903
  OB-1  lease-k8-prose       8    16954       224704247040     2.3778    2.5054
  OB-1  lease-k4-prose       4    20024       265393290240     2.2996    2.4603
  THIS  lease-k2-prose       2    21560       285751065600     2.1041    2.3622
  THIS  lease-k1-prose       1    22328       295929953280     2.0266    2.3446
  THIS  lease-k0-prose       0    23096       306108840960     2.4652    2.4996
  THIS  lease-k0-code        0    24078       319124033280     2.4209    2.5092
  THIS  lease-k0-code-b      0    24078       319124033280     2.0728    2.3555

  aggregated over every warm-cache leased run in both legs (16 rows):
    highest K measured = 16 : read 2.4078 GB/s, verify 2.4869 GB/s
    lowest  K measured =  0 : read 2.3196 GB/s, verify 2.4548 GB/s
    read rate at K=0 is 0.9634x the rate at K=16; verify rate 0.9871x

All sixteen leased runs across both legs move exactly 13253760 bytes per lease
event, and the rate is FLAT from K=16 all the way to an empty resident set:
within 4 percent on read and within 1.3 percent on verify, over a range where the
resident set shrinks by a factor of sixteen and then to nothing. The variation
that is there is smaller than the between-run variation of the A/A pair itself
(lease-k0-code and lease-k0-code-b, the same run, read at 2.4209 and 2.0728
GB/s), so it is box noise rather than a trend in K.

Cost tracks bytes moved and nothing else. The byte volume between K=4 and K=0
grows only from 28 to 32 non-resident experts, 14 percent, while exposure climbs
from 3.388 to 5.143, 52 percent. That asymmetry is the whole reason the curve has
no knee.

(The one run that does look different, OB-1's lease-k16-prose-fadv at 1.0399 GB/s
read, is the deliberate cold-cache case: it drops the page cache for every range
it reads, so it measures the NVMe path rather than any per-event overhead. It is
excluded from the aggregate above and marked in
research/ob1b/ANALYZE-KNEE-1.txt.)

WHERE THE CEILING ACTUALLY COMES FROM, and what a future leg would have to
attack. At K=0 the accounted denominator is

  2354799264 = resident_always 1930678944 + peak_concurrent 424120320

so 82.0 percent of what remains resident is NOT expert weights at all: it is
embeddings, attention weights and layer norms, which this scheme never touches.
The remaining 18.0 percent is the peak concurrent lease, which is a property of
the 1024-token micro-batch shape (every non-resident expert of the worst layer
gets routed within one micro-batch) rather than of the lease design. Pushing
exposure past 5.14 on this model therefore requires attacking one of those two
terms, not a smaller K, because there is no smaller K.

## 9. THE 120B POINT: THE LEASE ENGINE CANNOT YET REACH IT, AND WHY

This is the most consequential negative result in the leg, and it is not the one
the task brief expected.

The brief expected the fully resident --no-mmap baseline on gpt-oss-120b to be
infeasible (63387346208 model bytes against 24029 MB of RAM), named that as
itself a finding, and prescribed mmap-paged execution as the identity reference
instead, with the LEASED K=8 run going ahead against it.

THE LEASED RUN CANNOT GO AHEAD EITHER, for the same single cause. A 1024-token
leased probe was run first precisely so that a manifest or geometry problem
would surface cheaply rather than at the end of a contended night. It died at
model load in 1.068 seconds. Verbatim, from
research/ob1b/logs/smoke120-k8-prose.log:

  0.00.503.908 W common_fit_params: failed to fit params to free device memory:
               was unable to fit model into system memory by reducing context, abort
  0.00.806.033 E ggml_aligned_malloc: insufficient memory (attempted to allocate 60438.47 MB)
  0.00.806.050 E ggml_backend_cpu_buffer_type_alloc_buffer: failed to allocate buffer of size 63374323968
  0.00.806.050 E alloc_tensor_range: failed to allocate CPU buffer of size 63374323968
  0.00.878.238 E llama_model_load: error loading model: unable to allocate CPU buffer
  0.00.878.263 E llama_model_load_from_file_impl: failed to load model
  0.00.878.277 E llama_perplexity: unable to load model

  exit_rc 1   wallclock_s 1.068426206   Maximum resident set size 350856 KB

THE CAUSE IS STRUCTURAL, AND IT IS THE INTERESTING PART. The lease engine
REQUIRES --no-mmap: it can only fill and drop expert bytes that live in ordinary
anonymous memory, because under mmap the tensor data is a private file mapping
the loader never writes (OB-1's RUNLOG-1.txt section 4 states this as one of its
three flag deviations). But --no-mmap makes llama.cpp allocate ONE CPU buffer for
the whole model, 63374323968 bytes, BEFORE any leasing can occur, and this box's
default heuristic overcommit (vm.overcommit_memory=0, measured) refuses a single
allocation that far above RAM plus swap (24029 MB + 6144 MB = 30173 MB).

Stated as plainly as it deserves: THE ALLOCATION THAT LEASING EXISTS TO AVOID IS
THE ONE THAT FAILS FIRST. The engine's bounded residency is applied to a buffer
that must already have been allocated in full. On the 20b model that is invisible
and harmless, because 12109566624 bytes fits inside RAM and only touched pages
ever become resident, which is exactly why this leg's K=0 run peaks at 3563450368
bytes of RSS against a 12109566624-byte model. On a model LARGER than RAM, the
scheme does not merely perform worse, it does not start.

A NOTE ON WHY THIS WAS FOUND CHEAPLY. The 120b leg was scheduled last, behind a
nine-run 20b matrix on a runlock shared with three sibling workflows. Had it
been left to run in its scheduled place, this one-second failure would have
surfaced after several more hours of queueing, with no time to characterise it.
It was found in one second because a 1024-token probe was pushed to the front of
this leg's own queue specifically to expose a manifest, geometry or memory
problem before the real runs were committed to. The probe cost one lock cycle
and it is the reason section 9 exists at all.

That is a real limit on the result of OB-1 and OB-1b together, and it should be
read alongside their exposure figures rather than after them. The measured
exposures are honest measurements of peak fast-resident bytes, and they are
reproducible; but the design as it stands cannot be pointed at the case the whole
idea is for, which is serving a model bigger than the memory you have.

TWO WAYS FORWARD, neither taken by this leg, both named so the next one can
choose:

  1. THE ONE-LINE OPERATIONAL FIX. With vm.overcommit_memory=1 the 63374323968
     byte allocation would be granted as address space and only touched pages
     would become resident, which is precisely the regime the lease engine is
     built for; expected RSS would be roughly the K=8 accounted figure of
     7721554208 bytes plus compute buffers. THIS LEG DID NOT MAKE THAT CHANGE.
     It is a box-wide kernel VM setting that would affect pid 654, pid 489 and
     three sibling workflows mid-run, and it is not this leg's to make
     unilaterally. It is offered as a recommendation for the owner's word, with
     the exact knob named.

  2. THE ENGINE FIX. Allocate expert tensors in their own buffers, or lazily, so
     that the resident-set bound applies at allocation time rather than after it.
     This is not a minimal patch: it changes tensor addresses and buffer
     structure, which the identity limb depends on, so it would need its own
     prereg and its own identity re-verification.

WHAT WAS MEASURED INSTEAD. The same single cause blocks the resident baseline and
the leased run alike, so this leg does not spend forty minutes of contended
runlock re-running a one-second failure it already holds verbatim. It reproduces
that failure once at the frozen 8192-token configuration for the record, and then
measures what IS measurable on this box: MMAP-PAGED execution of the 63 GB model,
run twice and required to be byte-identical to each other. That bounds wall clock
at the larger model, which is what the 120b point was for, and it establishes the
identity reference the brief asked for. Those results are in section 10.

## 10. WHAT WAS MEASURED ON THE 120B, AND THE EXECUTION STATUS OF THE REST

### 10.1 The resident baseline, reproduced at the frozen configuration

Run at the frozen 8192-token shape, under the runlock, with an address-space cap
and a pinned oom_score_adj so that a failure could not make the OOM killer pick
pid 654, pid 489 or a sibling's run as its victim. Literal:

  exit_rc 1   wallclock_s 1.501564928
  0.00.825.394 E ggml_aligned_malloc: insufficient memory (attempted to allocate 60438.47 MB)
  0.00.825.410 E ggml_backend_cpu_buffer_type_alloc_buffer: failed to allocate buffer of size 63374323968
  0.00.825.411 E alloc_tensor_range: failed to allocate CPU buffer of size 63374323968
  0.00.894.369 E llama_model_load: error loading model: unable to allocate CPU buffer
  0.00.894.414 E llama_perplexity: unable to load model

The same allocation, the same failure, the same cause as the leased probe of
section 9. Both arms of the 120b comparison are blocked by one thing.

### 10.2 The paged reference, which does run

  run             wall_s    peak RSS KB     peak RSS bytes   EXP_rss   p50_ms    p95_ms
  pag120-prose-a  410.282      18823836       19275608064   3.288475  49164.4   49619.8
  pag120-prose-b  390.655      22724776       23270170624   2.723974  46086.7   46732.3

  identity sha256  9d20bd0365554989051d96b6ad4932625b0a6578002879f8253e6fcc21682019  (BOTH)
  route    sha256  a32d0051bd6d68f2777e64c7b889ae48d56621e9701b107fcef88c0e30cd89c1  (BOTH)
  PAGED A/A identity: MATCH        PAGED A/A route: MATCH

So the wall-clock bound the 120b point was for: 8192 tokens of AC-PROSE through
gpt-oss-120b, entirely on CPU, with the 63387346208-byte model paged from NVMe
through a 24029 MB box, takes 390 to 410 seconds at 8 threads, about 50 ms per
token. It runs, and it runs deterministically: two runs, byte-identical output
and byte-identical routing.

### 10.3 THE FINDING HIDING IN THOSE TWO ROWS

The two paged runs produced THE SAME BYTES and did NOT use the same memory:

  pag120-prose-a  19275608064 bytes resident    EXP_rss 3.288475
  pag120-prose-b  23270170624 bytes resident    EXP_rss 2.723974
  spread between two byte-identical runs: 17.17 percent

Compare THIS LEG'S OWN A/A pair at K=0 on the code corpus, run the same night on
the same box, also byte-identical in output:

  lease-k0-code    3583856640 bytes resident    EXP_rss 3.378920
  lease-k0-code-b  3577532416 bytes resident    EXP_rss 3.384894
  spread between two byte-identical runs: 0.1765 percent

and OB-1's three leased runs at K=16, same K, same corpus, same engine:

  8434827264 / 8434642944 / 8434708480 bytes    spread 0.0022 percent

The leased footprint reproduces about 97 times tighter than the paged one on
this leg's own same-night measurements, and about 7800 times tighter on OB-1's.

That is the clearest statement in this leg of what the lease engine actually
buys, and it is not the headline exposure number. Ordinary mmap paging reaches a
similar-looking exposure on the 120b, 3.29x, for free and with no engine at all.
But its footprint is EMERGENT: it is whatever the kernel's page cache happened to
retain under that minute's memory pressure, it varies by 17 percent between two
runs that computed identical bytes, and nothing about it can be promised in
advance. The leased footprint is ENFORCED: it is resident_always plus K layers of
chosen experts plus a peak concurrent lease the engine measures, it reproduces to
two parts in a hundred thousand, and every leased byte was checked against a
sha256 digest before use.

An exposure figure from paging is an observation about one run. An exposure
figure from leasing is a bound. That distinction is the reason the engine exists,
and it survives the fact that the 120b leased point could not be taken.

### 10.4 Execution status of the 20b matrix

Landed, all reported above with literal numbers:

  smoke-k0-prose    K=0, 1024 tokens, the guard-fix validation
  res8-prose-a      resident reference, prose
  res8-code-a       resident reference, code
  lease-k0-prose    K=0 pure streaming, prose
  lease-k0-code     K=0 pure streaming, code
  lease-k0-code-b   the A/A repeat at K=0 code
  lease-k1-prose    K=1, prose
  lease-k1-code     K=1, code
  lease-k2-prose    K=2, prose
  lease-k2-code     K=2, code
  res120-nomm-prose the 120b resident attempt, failing as section 10.1 records
  pag120-prose-a    the 120b paged reference
  pag120-prose-b    its A/A repeat

THE FULL 20B MATRIX LANDED. Every run the prereg called for on gpt-oss-20b was
made: both fully resident references, K=2, K=1 and K=0 on both acceptance
corpora, and the A/A repeat at K=0 on code. Nothing in the 20b programme is
outstanding.

Not landed, and the only thing that is not: the 120b LEASED point, for the
structural reason in section 9, which is a finding rather than a queue failure.

HOW THE NIGHT WAS ACTUALLY SHARED, measured rather than asserted. Five legs (this
one, OB-2, OB-3, OB-4 and a later OB-4b) contended for the single house runlock.
research/ob1b/LOCKWATCH.txt sampled once a minute which leg was running a model,
292 samples from 2026-09-01T01:18:45Z to 06:23:27Z:

  /root/ob1b (this leg)   136
  /root/ob3                76
  /root/ob4                38
  /root/ob4b               23
  none (lock free)         19

Individual waits for the lock reached 70 minutes: lease-k0-code-b sat that long
without acquiring, against the house's 120-minute give-up bar, while a sibling
released and re-took the lock back to back.

That is what drove two ordering decisions recorded in deviation D6, and one
fairness fix recorded in D7. It is also why the matrix finished at all: after the
lock wrapper's poll interval was tightened from 30 s to 5 s (keeping the 75 s
courtesy yield, so this leg still stands off longer than anyone), the remaining
five runs landed in 84 minutes, against 70 minutes of failing to acquire for a
single run before it.

## 11. DEVIATIONS

D1  THIS LEG RAN AT 8 THREADS, OB-1 AT 10, so it measured its own fully resident
    references rather than quoting OB-1's p95. Section 5 shows the two legs'
    output bytes are identical and their times differ by a consistent 1.167x, so
    identity is comparable across legs and cost is not. Every ratio here is
    against this leg's own baselines.

D2  THE BUILD REUSES THE LANDED OBJECT TREE instead of reconfiguring from
    scratch, because the landed build is GGML_CUDA=ON and a full rebuild
    recompiles several hundred nvcc translation units for a one-character change.
    This is not taken on trust: section 2.1 rebuilds from pristine source in the
    new tree and shows the resulting .text is byte-identical to the landed
    engine's, and section 5 shows the runs reproduce OB-1's output bytes exactly.
    Whole-file digests differ only by the RUNPATH string, which the linker must
    write because the tree lives at a different path.

D3  TIMING IS PER CHUNK, NOT PER TOKEN, inherited unchanged from the prereg's
    section 4 and OB-1's deviation D2. The engine timestamps the layer-0 routing
    callback, which fires once per 1024-token micro-batch; the only way to get a
    finer boundary is to shrink the micro-batch, which changes the batch shape
    and therefore the numbers under comparison. Any per-token figure derived
    from these is an average within a batch, never a measured per-token latency.
    p99 was added, and needed no engine change, because the engine already banks
    the full per-chunk interval series.

D4  THE PEAK-CONCURRENT TERM IS NO LONGER A PREDICTION ANYWHERE. The prereg
    labelled it PREDICTED for K in {2,1,0}. All three were measured: 397612800 at
    K=2, 410866560 at K=1, 424120320 at K=0, on both corpora, each exactly the
    predicted value. The exposure figures 4.084898, 4.553092 and 5.142505 are
    therefore measurements, not extrapolations, and this deviation is discharged
    rather than merely declared.

D5  THE 120B LEASED POINT WAS NOT MEASURED, and the reason is a finding rather
    than a scheduling failure. Section 9 gives the verbatim allocation failure
    and its structural cause. This leg did NOT change vm.overcommit_memory to
    work around it: that is a box-wide kernel setting affecting pid 654, pid 489
    and three sibling workflows mid-run, and it is not this leg's to make
    unilaterally.

D6  THE RUN ORDER WAS CHANGED MID-LEG, TWICE, and both changes are recorded in
    the branch history rather than quietly applied. First, the matrix was
    reordered to run the baselines and K=0 ahead of K=1 and K=2, because four
    workflows share the runlock and K=0 settles the question on its own. Second,
    the 120b leg was given the queue ahead of K=1 and K=2, because it measures a
    model nothing in this program has run while K=1 and K=2 interpolate between
    two endpoints already measured. Neither change touched a frozen definition,
    a bar, or a metric, and in the end nothing was lost to either: K=1 and K=2
    both landed afterwards (section 10.4), so the reordering changed only the
    sequence in which the results arrived, not which results exist.

D9  THE RUNLOCK POLL INTERVAL WAS TIGHTENED MID-LEG, from 30 s to 5 s, after
    lease-k0-code-b waited 70 minutes without acquiring while the lock was
    observed free at some sample instants, meaning real gaps were being slept
    through. The 75 s courtesy yield of D7 was kept, so this leg still stands off
    after every release for longer than a sibling's poll interval; only its own
    readiness to catch a gap changed. Polling faster shortens no sibling's run
    and takes nothing from anyone: mkdir is atomic and a stat every 5 s is
    nothing. The effect is measurable and is why the matrix completed at all: the
    last five runs landed in 84 minutes, against 70 minutes of failing to acquire
    for a single run before the change. No run's NUMBERS are affected, since the
    lock governs who runs, not how a run behaves once it holds it.

D7  THIS LEG STARVED ITS SIBLINGS FOR TWO RUNS BEFORE NOTICING. The lock wrapper
    released with rmdir and immediately re-requested for the next run, which wins
    the race against siblings polling on a 30 s timer; measured, the lock was
    re-acquired in the same second it was released while sibling OB-3 sat
    waiting. A 75 s courtesy yield was added after each release and the file was
    swapped by rename so the in-flight run was not disturbed. The two runs made
    before the fix (res8-prose-a, res8-code-a) are unaffected in their numbers,
    since the runlock governs who runs, not how fast a run goes; what they cost
    was a sibling's queue position, and that is recorded here rather than
    smoothed over.

D8  NO A/A REPEAT OF THIS LEG'S OWN RESIDENT BASELINES was made, to conserve
    contended runlock time. OB-1 demonstrated that this baseline is stable
    (byte-identical output, p95 within 0.9 percent across res-prose-a and
    res-prose-b) and this leg relies on that rather than re-establishing it.

## 12. ARTIFACTS AND DIGESTS

Off-repo run bytes, per house law, under /mnt/f/f32/stage/research/ob1b/runs/
and /root/ob1b/runs/, holding route.log, identity.txt, stdout.txt, stderr.txt
and ob1-stats.txt per run. Per-run logs under
/mnt/f/f32/stage/research/ob1b/logs/.

Engine, the binaries every run used:

  llama-perplexity  1772264971eb456bf6a60d5204c48fb96eeb5a9b026c42ea1dd6f3690b192932
  libllama.so.0     bfa8166ed641ea664e559af5402d56ef580fc6f90cc226d0b5859d6e023b37b0
  landed ob1 .text  850e33acf7be0facb41cacc5fb1bcda2a0eeb7c63d6e735fd5bfca3c9d9142ca
  ob1b patched .text f0336c94d5f1a7eb2697b171e7d4c0f67b5040e6932cae44dcdf2a3002f04af3

Inputs:

  AC-PROSE          310710a1f3e04484fcef2d0cb4ac1de93a8a6e02ced07ed3f2c9b79505e81a8e
  AC-CODE           d2db5c682d5f52a4383d188fee9d25f592a15d69763dbf886b5614c953e7f3fc
  RESIDENT-SETS-KNEE.json  08cc61837815dc9e5a4d9b7a810df8f59f2b0d5ac85e5f94bb016dd2a1f27bbb
  gpt-oss-20b gguf  27cd6c43... (registry-verified)
  gpt-oss-120b gguf 582bd40f... (registry-verified)

Identity digests, per run (all 32768-token runs on the 20b):

  PROSE, all four runs share one identity digest and one route digest:
    identity  96049ccf8ca241bf58233afe13ed75e2ca43180d81973360d04cebc80d551925
    route     4777aa8319f25d6e367f761ef12c7bec81a9ff7896bfed1b8ea0326b5dffc3df
    runs      res8-prose-a, lease-k2-prose, lease-k1-prose, lease-k0-prose

  CODE, all five runs share one identity digest and one route digest:
    identity  9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8
    route     f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77
    runs      res8-code-a, lease-k2-code, lease-k1-code, lease-k0-code,
              lease-k0-code-b

  Both digest pairs are also OB-1's own banked references, so the nine 20b runs
  in this leg and the twelve in OB-1 all produce the same two output artifacts
  per corpus: twenty-one runs, six values of K from 16 down to an empty resident
  set, two thread counts and two binaries, and four distinct digests in total.

  120b PAGED, both runs:
    identity  9d20bd0365554989051d96b6ad4932625b0a6578002879f8253e6fcc21682019
    route     a32d0051bd6d68f2777e64c7b889ae48d56621e9701b107fcef88c0e30cd89c1

Committed in this repository under research/ob1b/:

  knee.patch                the engine diff, one line, branch ob1b from c087083
  build-ob1b.sh             the object-reuse build
  verify-binary.sh          the .text comparison that licenses it
  VERIFY-BINARY-1.txt       its literal output
  BUILD-1.txt               the build's literal output
  run-ob1b.sh               one run, with an explicit mode argument
  locked-run.sh             the runlock wrapper, with the courtesy yield
  runs-knee.sh              the 20b matrix as first launched
  runs-knee-resume.sh       the resumable remainder
  runs-120b.sh              the 120b leg, rewritten after the smoke finding
  run-120b-resident-attempt.sh  the capped resident attempt
  chain-120b.sh             starts the 120b leg when the matrix ends
  handoff-to-120b.sh        hands the queue over after the K=0 A/A repeat
  lockwatch-ob1b.sh         one-minute lock occupancy sampler
  predict_leases.py         the pre-run predictions
  PREDICT-LEASES.txt        their literal output
  exposure_arith.py         the accounting, re-derived
  EXPOSURE-ARITH.txt        its literal output
  cost_decomp.py            the per-byte / per-event cost decomposition
  analyze_knee.py           produces the run, exposure and cost tables

## 13. PROCESS

pid 654 (openbob serve) and pid 489 (searxng) were confirmed alive before and
after every run in this leg and were never signalled, renamed, reniced or
killed. Every model run held the house runlock, taken and released per run, with
a 75 s courtesy yield after each release (deviation D7). All runs used 8 compute
threads under nice 10; analysis ran unthreaded or default-threaded Python under
nice 10. The GPU was hidden from every run. No model weights were downloaded;
both GGUF files were already on disk and were verified against the fetch-time
registry. The sealed corpus lowint/fixtures/LI-S5-ROUTES-1.txt was never opened,
and neither were ~/.config/openbob/, journals, tokens or pins.
/mnt/f/f32/stage/ was read-only for this leg except its own
/mnt/f/f32/stage/research/ob1b/. The engine fork was used as landed except for
the one-line guard change, which lives in this leg's own worktree
/root/ob1b/llama.cpp on branch ob1b; the ob1 branch and the sibling worktrees
ob2, ob3 and ob4 were never touched. Git work happened only in
F:\f32\openbob-wt\research-2 on branch research-2, adding only research/ob1b/*
and research/OB1B-KNEE-1.md; master was never touched, nothing was pushed, no
git pull was run before any commit.

Box sharing, measured rather than asserted, from research/ob1b/LOCKWATCH.txt
(292 one-minute samples of who was running a model, 01:18:45Z to 06:23:27Z): this
leg 136, OB-3 76, OB-4 38, OB-4b 23, lock free 19. Individual waits for the lock
reached 70 minutes against the house's 120-minute give-up bar. The occupancy
counts are reported in section 10 with the execution status they explain.

Final machine state, literal, at 2026-09-01T06:24:29Z:

  free -m       24029 total, 16077 free, 23147 available; swap 6144 total, 2038 free
  runlock       free (ls: cannot access ... No such file or directory)
  model procs   0
  guard pids    654 openbob alive, 489 python (searxng) alive
  /root         1007G total, 262G used, 695G available
  stage dir     /mnt/f/f32/stage/research/ob1b/  141M

This leg's own lock-occupancy sampler was stopped at the end of the leg so it
would not keep appending; 14 run directories are under /root/ob1b/runs/ and
copied to /mnt/f/f32/stage/research/ob1b/runs/.

