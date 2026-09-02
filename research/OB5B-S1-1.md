OB5B-S1-1: SLICE 1 ACCEPTANCE AND RECEIPT, BUILDER C

Lane: research (CUDA/inventor lane), venue f32-HYDE, Windows 11 + WSL2.
Branch research-2, worktree F:\f32\openbob-wt\research-2.
Bound by research/OB5-DESIGN-C4-1.md slice S1, gates 0 to 3, against
research/OB5A-ALLOC-1.md, builder A's research/OB5B-S1-RUNLOG-1.txt and
builder B's research/OB5B-S1-RUNLOG-2.txt.

THIS IS AN ACCEPTANCE LEG. It ran no model, took no runlock, started no
worker, connected to nothing, and added no state to the box beyond its own
scripts and their output. Everything below is re-derived from the raw bytes
on disk by instruments written from the definitions in the C4 spec rather
than from either builder's code. Where this leg agrees with a runlog it says
so with a count. Where it disagrees it says so first, at more length, and
shows the arithmetic that settles it.

Pure ASCII, no em dashes. Every number is literal command output from this
leg's own scripts or is quoted verbatim from a cited file. Deviations are in
section 12 and are not renegotiated anywhere else.

--------------------------------------------------------------------------
0. THE VERDICTS, FIRST
--------------------------------------------------------------------------

  GATE 0  THE TOP-8 MASS READ                        PASS, ACCEPTED
  GATE 1  BYTE-EXACT GENERATION (STOP-SHIP)          PASS, ACCEPTED
  GATE 2  DECODE MEASURED HONESTLY                   PASS, ACCEPTED
  GATE 3  THE SEAM                                   PASS, ACCEPTED

  SLICE 1: ACCEPTED. All four C4 bars are met on the evidence as it stands
  on disk. No kill line is tripped. The prepared install is prepared and not
  applied, and the live serve was not touched.

  500 COUNTED CHECKS, 0 DISAGREEMENTS, across five limbs:

    limb 1  artifact re-hash from raw bytes                  81   0
    limb 2A gate 0 tables, cell by cell against RUNLOG-1    228   0
    limb 2B route derivation vs the engine's own counters    32   0
    limb 3  rates and derived figures from raw counters      138   0
    limb 6  the gate 3 served turn, from its own bytes        21   0
                                                            ---  ---
                                                            500   0

  Two further limbs are diagnoses rather than agreements and are counted
  separately: limb 5, the schedule control (section 8.1 to 8.5), and limb 7,
  the chunk_ns series (section 8.6 to 8.10), which reproduces 21 of 21 of
  RUNLOG-2's published cells under the hypothesis that explains them.

  AND TWO CORRECTIONS THE COUNT DOES NOT CAPTURE, BOTH IN SECTION 8. They are
  the same mistake twice: a quantity was read out of a data structure whose
  shape was misread, and the misreading survived because the number it
  produced was plausible.

  CORRECTION ONE. The schedule control in BOTH runlogs was read through a
  positional comparison of two files whose emission order differs with the
  schedule. Re-read as routing decisions, the n_ubatch 64 against n_ubatch 32
  control moved ZERO of 3168 routing decisions in gate 1 and ZERO of 4572 in
  gate 2. Finding F-A5 and finding F-B9 are both refuted in their central
  claim. What changes is the program's belief about whether it has ever
  measured the batch schedule moving anything. It has not.

  CORRECTION TWO. RUNLOG-2 section 4.7 reads chunk_ns as "one entry per
  llama_decode call". It is one entry per INTERVAL between consecutive
  layer-0 route calls, so entry 0 spans the PREFILL and is not a token at
  all. Every "max" in that table is the prefill, and every "first quarter
  mean" carries it. With the prefill removed the within-run per-token spread
  is 1.44x to 5.75x, not "a factor of 15 to 22", and the first-to-last-quarter
  drift is 0.761 to 1.046 on six of the seven runs rather than "0.44 to 0.55
  on every run after [the first]". THE CORRECTED READING IS BETTER NEWS THAN
  THE ORIGINAL: within a run the decode rate is close to flat, and the
  variation the slice measured lives BETWEEN runs, in the page cache a
  process is born into. Finding F-B4's headline stands; its within-run limb
  does not.

  NO GATE VERDICT CHANGES ON EITHER. Both belong to declared extras and no
  C4 bar rests on either.

  AND ONE GAP CLOSED THAT BOTH BUILDERS DECLARED OPEN: the 63387346208 byte
  model file, a member of the frozen bound state, was re-hashed whole by this
  leg. Builder A deviation D7 and builder B deviation D6 are DISCHARGED.

--------------------------------------------------------------------------
1. THE HEADLINE: THE DECODE ROW
--------------------------------------------------------------------------

Sixteen generation runs of gpt-oss-120b on a 24029 MB box, every one of them
on the OB-5a reserve/commit allocator with K of 128 experts per layer leased
and verified against a 27648 row manifest. tok/s DECODE is recomputed here as
n_generated_tokens / decode_seconds from each run's own raw counters, not
copied from a runlog.

run                K  npr ngen         ttft_s        decode_s  tok/s decode   tok/s excl1   VmHWM_bytes   MaxRSS_kb     lease_ev
gen-120b-k8-a      8   56   32   40.421992879    77.013305363   0.415512616   0.402528978    7405826048     7232252         6049
gen-120b-k8-b      8   56   32   37.165344090    72.226891872   0.443048277   0.429203944    7406714880     7233120         6049
gen-120b-k8-c      8   56   32   36.840228521    72.903030414   0.438939230   0.425223065    7403458560     7229940         6049
gen-120b-k8-ub32   8   56   32   53.007984199    74.122468449   0.431717948   0.418236617    7217737728     7048572         6972
g2-k8-p1-a         8   56   64   40.313243448   248.163195190   0.257894810   0.253865315    7405543424     7231976        10262
g2-k8-p1-b         8   56   64   44.930562558   190.394067643   0.336144927   0.330893066    7405600768     7232032        10262
g2-k8-p2           8   63   64   41.640432405   172.591897372   0.370816944   0.365023141    7509954560     7333940         9810
g2-k8-p3           8   59   64   36.062630445   142.881315796   0.447924206   0.440925771    7510695936     7334664         9317
g2-k8-p4-narrow    8    1   32    2.607288103    75.706478525   0.422685094   0.409476694    6537732096     6383212         4474
g2-k8-p2-ub32      8   63   64   52.736329828   146.365130604   0.437262617   0.430431091    7252459520     7082480        10566
g2-k16-p1         16   56   64   37.672590362   151.940919703   0.421216353   0.414635447   11153657856    10892244         9548
g2-k16-p2         16   63   64   34.730626425   136.788235061   0.467876495   0.460566572   11240476672    10977028         8778
g2-k24-p1         24   56   64   34.021878742   144.788436777   0.442024249   0.435117913   14907207680    14557820         8835
g2-k24-p2         24   63   64   31.635591862   130.455698619   0.490587998   0.482923031   14931312640    14581360         7807
g2-k32-p1         32   56   64   33.555524593   135.928857303   0.470834533   0.463478071   18660970496    18223604         7921
g2-k32-p2         32   63   64   29.700507911   120.471405756   0.531246395   0.522946083   18145042432    17719768         6845

  n_generated_tokens is 64 on every row except the three gate 1 runs and the
  narrow control, which are 32. stop_reason is n_predict on every row. exit
  status 0 on every row. Every row carries its own tok/s, TTFT, wall clock,
  peak RSS, VmHWM, lease counters and commit-peak counters, which is her
  standing perf-data-points order, and section 10 checks it field by field.

THE OPERATING POINT THE GATE'S OWN BAR NAMES, and the number this slice is
about:

  K=32, the largest residency schedule whose committed state fits the box
  with 6 GB free, on an in-corpus prompt:

      0.531246395 tok/s DECODE      29.700507911 s to the first word
      VmHWM 18145042432 bytes       headroom 6535262208 bytes (6232 MiB)

  and the whole measured band, across four values of K, four prompts and two
  ubatch widths, is 0.257894810 to 0.531246395 tok/s decode. A 2.06x band on
  the same binary at the same bound state. The bytes have no band; the
  seconds do.

THE DECODE-REGIME ACCT, INDEPENDENTLY RE-DERIVED. C4 section 6.1 projected
ACCT_decode 6237133088 and exposure 10.1629 at K=8 on a depth-2 prefetch
allowance. The engine holds depth 1. This leg recomputed the decode-phase
peak concurrent lease bytes from each run's own route log, by an
implementation written from ob1_on_route's stated semantics, and got
53015040 bytes, exactly 4 experts, ON ALL SIXTEEN RUNS AT ALL FOUR VALUES OF
K, including the narrow-prefill control where the engine's own counter is
already a decode-width figure and printed 53015040 itself.

  2314020128 + 3817082880 + 53015040 = 6184118048
  63387346208 / 6184118048 = 10.250022

  K   resident bytes   ACCT_decode measured   EXPOSURE measured   C4 projected   ratio
   8      3817082880             6184118048           10.250022      10.162898  1.008573
  16      7634165760            10001200928            6.337973       6.304554  1.005301
  24     11451248640            13818283808            4.587208       4.569676  1.003837
  32     15268331520            17635366688            3.594331       3.583558  1.003006

  Scope-ledger entry OB5-023 is CONFIRMED, and it is now the only projection
  in C4 section 6.1 that measurement confirmed rather than corrected.
  Decode BUYS exposure: 10.250022 against the batch regime's measured
  8.209143, a rise of 24.8610 percent.

--------------------------------------------------------------------------
2. WHAT THIS LEG DID, AND WHAT IT DELIBERATELY DID NOT DO
--------------------------------------------------------------------------

DID. Re-hashed 81 artifacts from raw bytes, including the 63 GB model file.
Re-implemented the gate 0 mass analysis and the gate 2 route derivation from
the definitions in the C4 spec, in plain python with no numpy, so the
arithmetic path differs from both builders' instruments as well as the code.
Re-parsed builder A's own printed gate 0 tables out of RUNLOG-1 and compared
them cell by cell. Recomputed every rate in both runlogs from the ns counters
in each run's ob1-stats.txt. Re-derived the gate 3 served turn's identity,
counters and receipt from the turn's own files. Reconstructed the chunk_ns
series' actual shape against ttft and the prefill piece count. Verified the
prepared install against its own SHA256SUMS. Proved the live serve untouched
from /proc.

DID NOT. No model was loaded. No runlock was taken, because no model run was
made and the house law binds the lock to model runs. The exposure worker was
not started. The live serve on 127.0.0.1:8899 was never connected to, not
even for /health, because reading its health is a connection and this leg did
not need one to prove what section 11 proves. ~/.config/openbob was never
opened; only the directory's own inode was stat'ed. The sealed corpus
lowint/fixtures/LI-S5-ROUTES-1.txt was never opened. No weights were
downloaded. No Telegram was sent. The mini, the messenger, the demo frame and
the 4B serve path were never touched. No sibling worktree or branch was
written to.

ONE THING THIS LEG COULD NOT DO, AND IT IS THE LARGEST HOLE IN THE SLICE.
Builder A's F-A9 and builder B's item (d) both name it: there is no second
generation implementation to check ob5b1-gen against. Every identity limb in
gates 1, 2 and 3, and every re-derivation in this document, would pass
unchanged if ob5b1-gen contained a DETERMINISTIC bug. Acceptance cannot close
that by re-reading bytes; it needs another entry point and a model run.
Section 13 carries it forward, and it is not softened here.

--------------------------------------------------------------------------
3. LIMB 1: THE ARTIFACTS RE-HASHED
--------------------------------------------------------------------------

research/ob5b1/accept_hash.py transcribes every digest either runlog claims
into a table and re-reads the bytes.

  HASH_CHECKS 80  MATCH 80  MISMATCH 0  MISSING 0

covering: all 32 in-repo scripts of both legs; the two pinned inputs
RESIDENT-SETS-120B-K8.json (8053f18a...) and EXPERT-MANIFEST-120B.sha256
(c71ce2ce...); all five identity limbs of all three gate 1 runs; the gate 1
schedule control's route log; all four prompts; the four banked RS053 route
logs; the six gate 0 output JSONs including the A/A pair whose equality IS
the determinism limb; the six ob5a and ob5b1 binaries; gate 2's A/A identity
pair; the gate 3 worker log; the 4027740408 byte gatekeeper artifact; and the
32607 line fabric source.

AND THE EIGHTY-FIRST, WHICH NEITHER BUILDER DID:

  $ nice -n 19 /usr/bin/time -v sha256sum /root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf
  582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d  /root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf
      Elapsed (wall clock) time (h:mm:ss or m:ss): 0:46.64
      Maximum resident set size (kbytes): 3284
  $ stat -c "%s %n" /root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf
  63387346208 /root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf

  It matches the digest OB5A-ALLOC-1 banked and the digest the gate 3 brain
  manifest pins. Builder A's D7 and builder B's D6 both said the cost was not
  worth what the leg's claims rested on. The cost was 46.64 seconds, and what
  it buys is that the brain manifest's weights row is now verified from the
  bytes rather than carried from a bank. Since the manifest digest is the
  model digest of every journal chain gate 3 wrote, that row is load bearing.

--------------------------------------------------------------------------
4. LIMB 2: GATE 0 AND THE ROUTE LOGS, RE-DERIVED
--------------------------------------------------------------------------

4.1 GATE 0, CELL BY CELL AGAINST BUILDER A's OWN PRINTED TABLES

research/ob5b1/accept_gate0_cells.py parses the tables out of RUNLOG-1 and
compares them against a recomputation from the four banked route logs.

  per-layer rows parsed from the runlog and re-derived: 36
  GATE 0 CELL CHECKS 228   DISAGREEMENTS 0

That is all 36 layers times 5 printed columns, plus the run-level block, plus
the cross-domain block, plus all 6 rows of the K sweep on both corpora. Every
figure in RUNLOG-1 sections 3.3, 3.4 and 3.5 reproduces to every printed
digit from a different implementation.

The load-bearing ones, restated:

  banked K=8 set re-derives from 120b-prose-a's own counts       True
  banked K=8 set re-derives from 120b-code-a's own counts        False
  top8_decisions_hit                                             953164 of 2359296
  run top8_mass in domain                                        0.4040035672
  run top8_mass cross domain                                     0.0793007745
  misses/token drop-on-use, in domain, mean/min/p50/p95/max      85.8234863281 / 40 / 85.0 / 115.0 / 141
  misses/token drop-on-use, cross domain, mean/max               132.5806884766 / 144
  layer-min mass                                                 0.2023162842 (layer 0)
  layer-max mass                                                 0.7522735596 (layer 34)
  duplicate_expert_rows on all four logs                         0
  token order 0..T-1 verified on all four logs                   True

AND THE FREE CROSS-CHECK, RE-RUN AT FULL PRECISION. RS053 computed the
120b-prose layer-mean P_half independently, by other code, for another
purpose. P_half at E/2 = 64 is the same statistic as this leg's K=64
self-ranked mass:

  this leg   9.18757120768229130e-01
  RS053      9.18757120768229130e-01

  Seventeen significant figures, two implementations, two programs, one
  number. That is the strongest single agreement in the slice and it belongs
  to gate 0 rather than to either identity limb.

4.2 EVERY GENERATION RUN, DERIVED FROM ITS OWN ROUTE LOG

research/ob5b1/accept_route.py reconstructs the ubatch pieces from the log's
own emission structure, applies the resident set, and derives lease events
and peak concurrent lease bytes under the HELD-FOR-THE-UBATCH model builder A
settled by measurement in F-A1. It then compares both against the engine's
own counters.

run                  K  n_pr  pieces  derivedLease  engineLease  M   derivedPeak  enginePeak  M   decodePeak  decMass       decMis/tok
gen-120b-k8-a         8    56      33          6049         6049  T    954270720   954270720  T    53015040  0.0861545139  131.5937500
gen-120b-k8-b         8    56      33          6049         6049  T    954270720   954270720  T    53015040  0.0861545139  131.5937500
gen-120b-k8-c         8    56      33          6049         6049  T    954270720   954270720  T    53015040  0.0861545139  131.5937500
gen-120b-k8-ub32      8    56      34          6972         6972  T    742210560   742210560  T    53015040  0.0861545139  131.5937500
g2-k8-p1-a            8    56      65         10262        10262  T    954270720   954270720  T    53015040  0.0859375000  131.6250000
g2-k8-p1-b            8    56      65         10262        10262  T    954270720   954270720  T    53015040  0.0859375000  131.6250000
g2-k8-p2              8    63      65          9810         9810  T   1060300800  1060300800  T    53015040  0.1350911458  124.5468750
g2-k8-p3              8    59      65          9317         9317  T   1060300800  1060300800  T    53015040  0.1585286458  121.1718750
g2-k8-p4-narrow       8     1      33          4474         4474  T     53015040    53015040  T    53015040  0.0562065972  135.9062500
g2-k8-p2-ub32         8    63      66         10566        10566  T    808479360   808479360  T    53015040  0.1350911458  124.5468750
g2-k16-p1            16    56      65          9548         9548  T    888001920   888001920  T    53015040  0.1496310764  122.4531250
g2-k16-p2            16    63      65          8778         8778  T    967524480   967524480  T    53015040  0.2236328125  111.7968750
g2-k24-p1            24    56      65          8835         8835  T    821733120   821733120  T    53015040  0.2137586806  113.2187500
g2-k24-p2            24    63      65          7807         7807  T    888001920   888001920  T    53015040  0.3070746528   99.7812500
g2-k32-p1            32    56      65          7921         7921  T    768718080   768718080  T    53015040  0.2982855903  101.0468750
g2-k32-p2            32    63      65          6845         6845  T    808479360   808479360  T    53015040  0.3921440972   87.5312500

  ROUTE-DERIVATION COMPARISONS 32  AGREE 32  DISAGREE 0

  The decMass and decMis/tok columns reproduce every row of RUNLOG-2 section
  4.5 to every printed digit, and gate 1's own decode-phase figures
  (0.0861545139 and 131.5937500) reproduce RUNLOG-1 section 5.

  THE PIECES COLUMN IS THE QUIET CONFIRMATION. 33 pieces for a 32 token
  generation, 65 for a 64 token one, 34 and 66 when the ubatch is halved and
  the prefill takes two pieces. One prefill piece plus one piece per decoded
  token. That is F-A1's residency model visible in the log's own structure,
  and it is why the lease counter is exactly predictable from routing alone.

  THE DECODE-PHASE PEAK IS 53015040 ON EVERY ROW. That is builder B's central
  measurement, and this leg reaches it by a third route: not the engine's
  counter, not builder B's derivation, but an independent reconstruction of
  the piece structure. With the narrow-prefill control's own counter that
  makes four independent readings, and section 9 adds a fifth from outside
  this workflow entirely.

--------------------------------------------------------------------------
5. LIMB 3: THE RATES, RECOMPUTED FROM RAW COUNTERS
--------------------------------------------------------------------------

research/ob5b1/accept_arith.py recomputes 138 derived figures. Its verdict:

  ARITH CHECKS 138   DISAGREEMENTS 0

Everything both runlogs derive is confirmed, including:

  the OB-5a read and verify rates re-derived from their own literals
    363192785280 / 286.711586 = 1266753082.242027 bytes/s
    363192785280 / 154.163691 = 2355890566.216399 bytes/s
  tok_s_decode == n_generated_tokens / decode_seconds on all 17 runs
  lease_events x 13253760 == lease_bytes_read, exactly, on all 16 120b runs
  resident_bytes_loaded == K x 36 x 13253760, exactly, at every K
  peak_concurrent_lease_bytes an exact multiple of 13253760 on every run
  alloc_commit_peak_single == 615333888 on all 17 runs including the 20b smoke
  C4 section 6.1's own projected exposures, all four, to 1e-6
  gate 1's ACCT 7085373728 and EXPOSURE_acct 8.946225
  gate 1's mean tok/s 0.432500041, mean TTFT 38.142521830, the 1.827657 ratio
    to C4's P-C, the 0.720468 read-plus-verify share, and both measured rates
  gate 2's A/A decode wall-clock ratio 1.303419 on byte-identical output
  the measured/model residual band 0.743809 to 0.805983, mean 0.7732
  F-B3's per-gigabyte pricing, all three baselines
  the K=32 headroom 6535262208 bytes and the three commit-peak slopes
  the K=40 projection 22126559232 commit, 2767278080 headroom, 2639 MiB

THE FIT DECISION, RECOMPUTED FROM THE MEASURED COMMIT PEAKS:

  box bytes 24029 MiB = 25196232704
  K=8   commit_model_peak   7081930752  VmHWM   7405543424  headroom 17790689280 (16966 MiB)
  K=16  commit_model_peak  10835841024  VmHWM  11153657856  headroom 14042574848 (13392 MiB)
  K=24  commit_model_peak  14590590976  VmHWM  14907207680  headroom 10289025024 ( 9812 MiB)
  K=32  commit_model_peak  18358575104  VmHWM  18660970496  headroom  6535262208 ( 6232 MiB)
  slopes per K: 469238784.0  469343744.0  470998016.0
  K=40 projected commit 22126559232  VmHWM 22428954624  headroom 2767278080 (2639 MiB)
  K=32 headroom above the 6144 MiB house bar: True
  K=40 headroom above the 6144 MiB house bar: False

  K=32 IS THE LARGEST FITTING K, and the fact carrying the weight is that
  K=32 was DECIDED BY RUNNING IT rather than by the table. K=40 is a
  projection from this leg's own three measured slopes and is declared as
  such.

A CORROBORATION FROM A DIFFERENT INSTRUMENT, re-checked: the narrow control's
alloc_commit_model_peak is 6230409216 against a derived ACCT_decode of
6184118048. The difference is 46291168 bytes, 0.7486 percent, which is the
engine's non-expert buffers. Two instruments, within a percent, on the same
quantity.

--------------------------------------------------------------------------
6. LIMB 4: THE CROSS-RUN IDENTITY LIMB
--------------------------------------------------------------------------

C4's gate 1 bar asks for "a third run from the same state after a serve
restart". Builder A could not take that literally (the hard wall forbids
touching pid 654 and gate 3's worker did not exist yet) and declared the
reinterpretation in D2 before the run: a fresh process, a different working
directory, a different output directory, and the page cache perturbed by a
4 GiB read of the model file. THIS LEG ACCEPTS THAT DEVIATION, and records
that gate 2 later supplied, without meaning to, a stronger limb than the one
D2 replaced.

  gate 1 ids 32 tokens, gate 2 ids 64 tokens
  GATE1_PREFIX_MATCHES_GATE2 True

n_predict is not a member of the forward pass, so a 64-token run from the
same bound state must extend a 32-token run exactly. It does. The gate 2 runs
were made roughly forty minutes later, in fresh processes, from a different
tree, with a different n_predict, under a different page cache, after a
sibling workflow had put its own 12 GB working set through the box. The first
32 generated ids are identical:

  168394 279 12253 382 261 52287 3926 328 290 27853 484 6664 261 945 14633
  30547 328 1495 290 2359 382 13991 326 2061 1402 26178 7450 976 3992 382
  261 21402

That is the limb the serve-restart clause was reaching for, and it landed.

--------------------------------------------------------------------------
7. LIMB 6: THE SEAM, RE-DERIVED FROM THE TURN'S OWN BYTES
--------------------------------------------------------------------------

research/ob5b1/accept_gate3.py: GATE 3 CHECKS 21   DISAGREEMENTS 0.

IDENTITY, RECOMPUTED OVER THE TURN'S ARTIFACTS:

  turn_id == sha256(gen-ids.txt)         55df750df27733224d3df21726cafc50b1e6ca6051909f66d8c813dd5a2e2f86
  answer_sha256 == sha256(gen-text.txt)  613dd289c02ca2cf5eecfc432781b4931c602a1d6099d224e3f1966133299850
  route_log_sha256 == sha256(route.log)  fbb2f4ab32d2da8cc61f555b6001005235f0ffbb0f53319d8b797eb386c72ae5
  prompt_sha256 == sha256(prompt.txt)    251e634f0feb9957bc77954b327d2c676eaa4e16036c8537d7b7174a9ff24e26
  alloc_journal_sha256 == the file       4af4cb9b30b8bd3bf85dd7509467f44314d78c9cc619e22c6bf153d302242332
  engine_sha256 == the gate 1/2 binary   daca8fb74f626c186950c2882dfd1fdfe191056ca5feacccd51201db3e625740
  residency_sha256 == the banked K=8 set 8053f18a70030ad2ac2e59fe220a064ee26f35ad4eb3876bbb7c65f6e994530b
  weights_sha256                         582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d
                                         re-hashed whole by this leg, section 3

  Every digest the worker log asserts is a digest this leg recomputed over
  the bytes. The turn identity is not a label the worker chose; it is the
  sha256 of the token ids the model produced, and it is reproducible by
  anyone holding the file.

THE RECEIPT'S NUMBERS, RECOMPUTED FROM THE COUNTER BLOCK:

  leased slices                    5461
  leased bytes                     5461 x 13253760 = 72378783360, and the
                                   engine's lease_bytes_read is 72378783360
  peak concurrent                  609672960 = exactly 46 experts
  ACCT                             2314020128 + 3817082880 + 609672960
                                   = 6740775968
  EXPOSURE                         63387346208 / 6740775968 = 9.403568
  tok/s decode                     32 / 75.177166512 = 0.425661161
  ttft                             25.340207310 s
  resident bytes                   8 x 36 x 13253760 = 3817082880
  alloc_commit_peak_single         615333888
  guards before the turn           {"489": true, "654": true}
  guards after the turn            {"489": true, "654": true}
  runlock wait                     0.002 s

AND THE TURN'S OWN ROUTE LOG, DERIVED:

  derived lease_events == engine's                   5461
  derived peak concurrent == engine's                609672960
  derived DECODE-phase peak == 4 x 13253760          53015040
  route pieces (1 prefill + 32 decode)               33

  So the served turn is not a special case: the same derivation that
  reproduces the sweep reproduces the product surface. Every number bob
  printed came from a counter, and every counter is reproducible from the
  bytes. That is the dashboard law satisfied mechanically rather than
  asserted.

THE ANSWER, VERBATIM, 160 BYTES, because show-dont-tell forbids dressing it:

    ?

    Holding a large model in a small amount of memory means that the model is
    designed to be efficient and compact, allowing it to be stored and
    processed within

  It is a base-model continuation and it reads like one. C4 gate 3 asks for a
  seam, not for a frame, and builder B named the missing frame as later work
  rather than adding one. That is the right call and this leg endorses it.

THE FOUR REFUSALS. brain.not_resident fired with the worker genuinely down.
brain.busy fired against a live turn from another shell, and was refused
rather than queued. brain.identity.violation fired on a real digest mismatch
against a sandbox copy of the residency schedule, and the sandbox turn
directory holds a prompt.txt and nothing else, so the model was never loaded.
C4's B1 behavioural limb is discharged: the stopped-worker control produced
the named refusal, not a weaker 4B answer.

ONE COSMETIC ITEM, NAMED BECAUSE IT IS ON A PRODUCT SURFACE. The receipt
prints "leased 5461 slices, 72.37 gb". 72378783360 bytes is 72.378783 GB,
which rounds to 72.38 and truncates to 72.37. The number comes from the
counter, as the law requires; the formatter floors rather than rounds. It is
not a defect and it is not worth a rebuild, but a formatter that floors will
one day print 6.99 for 7.00 and somebody will file it as a bug.

--------------------------------------------------------------------------
8. THE TWO CORRECTIONS
--------------------------------------------------------------------------

This is where acceptance disagrees with the record, and it is reported at
more length than any of the 500 agreements. Both corrections have the same
shape: a data structure's layout was misread, the misreading produced a
plausible number, and the plausible number became a finding.

==========================================================================
CORRECTION ONE: THE SCHEDULE CONTROL MOVED NO ROUTING DECISION
==========================================================================

8.1 WHAT BOTH RUNLOGS SAID

RUNLOG-1 finding F-A5: "THE BATCH SCHEDULE MOVED THE ROUTING AND DID NOT MOVE
THE ANSWER. Changing n_ubatch from 64 to 32 changed the route log from byte
552, line 33 ... the router selected different experts from that token
onward."

RUNLOG-2 finding F-B9, at more length and with a phase split: "PREFILL rows
(token_index < 63): 1085 of 2268 rows DIFFER, 47.8 percent ... A batch
schedule change rewrote nearly HALF the prefill's routing decisions ... IT
CONFIRMS THE MECHANISM more strongly than F-A5 did."

8.2 WHAT THE BYTES SAY

research/ob5b1/accept_sched.py reads each route log not as a file but as a
map from (layer, token) to the four experts selected, which is what a routing
decision IS.

  GATE 1 CONTROL (R1 s4.6, F-A5)
    rows                                     3168 vs 3168
    FILE ORDER identical                     False
    MULTISET of (layer, token, experts) equal True
    keys equal                               True
    ROUTING DECISIONS that differ            0 of 3168
      of which prefill 0, decode 0
    CANONICAL (layer,token) digest ub64      f7f4356da866fe4d81836dcbc39ffdacb296378760154a8c549706366eb8f1f6
    CANONICAL (layer,token) digest ub32      f7f4356da866fe4d81836dcbc39ffdacb296378760154a8c549706366eb8f1f6
    CANONICAL digests equal                  True

  GATE 2 CONTROL (R2 s4.8, F-B9)
    rows                                     4572 vs 4572
    FILE ORDER identical                     False
    MULTISET of (layer, token, experts) equal True
    keys equal                               True
    ROUTING DECISIONS that differ            0 of 4572
      of which prefill 0, decode 0
    CANONICAL (layer,token) digest ub64      eaa790921ead8d6a801096bb04417ac9c1d346f4e3e8f91a133713f6ca88d07e
    CANONICAL (layer,token) digest ub32      eaa790921ead8d6a801096bb04417ac9c1d346f4e3e8f91a133713f6ca88d07e
    CANONICAL digests equal                  True

  Not one of the 3168 routing decisions in gate 1's control, and not one of
  the 4572 in gate 2's, differs. 18288 individual expert selections in gate
  2's pair alone, all identical. The two route logs are PERMUTATIONS of each
  other.

8.3 WHY THE RUNLOGS SAW A DIFFERENCE

The route log is emitted layer-major WITHIN A UBATCH PIECE. At n_ubatch 64 a
63 token prompt is one piece, so the file reads layer 0 for tokens 0..62,
then layer 1 for tokens 0..62, and so on. At n_ubatch 32 it is two pieces, so
the file reads layer 0 for tokens 0..31, layer 1 for tokens 0..31, ... layer
35 for tokens 0..31, and only then layer 0 for tokens 32..62. THE SAME
DECISIONS, IN A DIFFERENT ORDER.

A positional comparison therefore lines row i of one order against row i of
the other and reports a difference that is entirely emission order:

    ub64 file line 33: (0, 32, (65, 45, 98, 49))
    ub32 file line 33: (1,  0, (93, 28, 52, 103))

Those are not the same routing decision. They are layer 0 token 32 and layer
1 token 0. "differ: byte 546, line 33" is the first row at which the two
emission orders diverge, which for these two schedules is exactly the 33rd
row, because the ub32 piece is 32 tokens wide.

The diagnosis is confirmed to the digest. Hashing the PREFILL rows in FILE
order reproduces builder B's own three published digests exactly:

    B claims  ub64 prefill cd35c527383c9edda705fe9b4293dc63755e3f3c342c4d6e67a6285cba20adaa
    file-order ub64 prefill cd35c527383c9edda705fe9b4293dc63755e3f3c342c4d6e67a6285cba20adaa
    B claims  ub32 prefill a2eb8217f59291245d7cd3ea0f3dea4dcaa1cda459291a84488742c1510a12ff
    file-order ub32 prefill a2eb8217f59291245d7cd3ea0f3dea4dcaa1cda459291a84488742c1510a12ff
    B claims  decode both   0a7f2b114f87665390dbeef0fe148f27bbb342c252797a9064b95b0ed2b15c8d
    file-order decode ub64  0a7f2b114f87665390dbeef0fe148f27bbb342c252797a9064b95b0ed2b15c8d
    file-order decode ub32  0a7f2b114f87665390dbeef0fe148f27bbb342c252797a9064b95b0ed2b15c8d

    positional differing prefill rows: 2205 of 2268
    ub32 prefill is a PERMUTATION of ub64 prefill: True

The ub64 prefill digest matches under both orderings because at one piece the
file order IS the canonical order. The ub32 digest differs only because its
file order is not. The decode digests match under both orderings because a
decode piece is one token wide, so there is nothing to permute, which is
exactly why builder B's decode limb was sound while its prefill limb was not.

This leg does not reconstruct which variant of a positional comparison
produced builder B's figure of 1085 rather than 2205, and does not need to:
both are artifacts of the same class, and the count of differing routing
decisions is 0.

8.4 WHAT IS AND IS NOT LICENSED BY THIS

REFUTED. F-A5's claim that "the router selected different experts from that
token onward". F-B9's claim that "47.8 percent of the prefill's routing rows
moved, so the numerics genuinely differ" and its conclusion that the control
"CONFIRMS THE MECHANISM". F-B9's closing claim that the route log "saw one
[a silent numeric change] the identity limb could not" is refuted twice over:
the route log saw nothing either.

ALSO REFUTED, and this one matters to the receipt design: builder A's
argument that the route log belongs in the receipt beside the answer because
it is "the limb that CAN see a silent numeric change" now rests on no
measurement at all. Keeping the route log in the receipt is still right, for
replay and for exposure accounting, but not for that reason.

NOT REFUTED, AND NOT WEAKENED AS A DESIGN CONSTRAINT. C4 section 4.3 puts the
batch schedule in the bound state because floating-point summation order in a
CPU matmul depends on how many rows are computed together. That argument is a
priori and correct. What has changed is that the program has now looked twice,
at two prompts and two generation lengths, and found NO OBSERVABLE
CONSEQUENCE OF ANY KIND: not in the sampled tokens, not in the routing, not
in any byte either instrument records. The honest state of the evidence is
that n_ubatch 64 against n_ubatch 32 on this model at this operating point is
an unobserved perturbation, not a measured one. KEEP THE SCHEDULE IN THE
BOUND STATE. It costs one line in a receipt and it forecloses a whole class
of silent divergence. But the program must stop saying it has confirmed the
mechanism, because it has not.

WHAT THE CONTROL DID MOVE, and it is not nothing:

    lease_events                 9810 -> 10566
    peak_concurrent_lease_bytes  1060300800 (80 experts) -> 808479360 (61)
    ttft_seconds                 41.640432405 -> 52.736329828

  The schedule moves the LEASE GROUPING and therefore ACCT's third term and
  therefore the run's exposure figure, without moving a single routing
  decision. That is a sharper version of builder A's F-A4 than F-A4 itself:
  the batch schedule binds the EXPOSURE ARITHMETIC of a served turn while
  leaving its ANSWER and its ROUTING untouched. C3 and C2 should read it that
  way.

8.5 WHY NO GATE VERDICT MOVES

The schedule control is a declared extra in both legs (RUNLOG-1 deviation D6,
RUNLOG-2 section 4.8). No C4 bar names it. Gate 1's STOP-SHIP bar is three
A/A generation runs and it passed on five limbs. Gate 2's bar is decode
measured at K=8 and at the largest fitting K, and it passed. The correction
changes two findings and one design argument, not a verdict.

==========================================================================
CORRECTION TWO: chunk_ns[0] IS THE PREFILL, NOT A TOKEN
==========================================================================

8.6 WHAT THE RUNLOG SAID

RUNLOG-2 section 4.7: "The ob1 stats carry chunk_ns, the wall time between
layer-0 route calls, which is one entry per llama_decode call, so the
per-token decode time is a measured series and not an average." Its table
then reports, per run, a first-quarter mean, a last-quarter mean, a min and a
max, and concludes: "Within one run the per-token time varies by a factor of
15 to 22 (min against max), and the drift between the first and last quarter
goes BOTH WAYS: 1.42 on the first run of a cold box and 0.44 to 0.55 on every
run after it."

8.7 WHAT chunk_ns IS

research/ob5b1/accept_chunk.py. A run makes ONE PREFILL CALL plus n_gen
decode calls, and chunk_ns holds the intervals BETWEEN consecutive layer-0
route calls. So there are n_gen intervals for n_gen+1 calls, entry 0 spans
the prefill, and the last decoded token's own time is never recorded.

  run             n_gen    len   pieces    chunk_ns[0]   ttft_seconds     difference
  g2-k8-p1-a         64     64        1      40.302140      40.313243       0.011103
  g2-k8-p1-b         64     64        1      44.919939      44.930563       0.010624
  g2-k8-p2           64     64        1      41.622151      41.640432       0.018281
  g2-k8-p3           64     64        1      36.048212      36.062630       0.014419
  g2-k16-p1          64     64        1      37.654195      37.672590       0.018396
  g2-k24-p1          64     64        1      33.988706      34.021879       0.033173
  g2-k32-p1          64     64        1      33.535756      33.555525       0.019769
  gen-120b-k8-ub32   32     33        2      52.999963      53.007984       0.008021
  g2-k8-p2-ub32      64     65        2      52.731799      52.736330       0.004531

  (the pieces column is len(chunk_ns) - n_gen + 1, and the chunk_ns[0] column
  is the sum of that many leading intervals)

The leading intervals sum to ttft to within 4 to 33 milliseconds, which is
the sampling of the first token. And the two ubatch-32 runs carry ONE EXTRA
ENTRY each, because their prefill is two pieces. The structure is not in
doubt.

8.8 THE ARTIFACT, REPRODUCED TO THE CELL

Reproducing RUNLOG-2 section 4.7's published cells on the hypothesis that the
prefill interval is included in the series:

  run              pub first       repro     pub max chunk_ns[0]     pub min   repro min
  g2-k8-p1-a        4.761383    4.761383   40.302140   40.302140    2.143400    2.143400
  g2-k8-p1-b        6.066317    6.066317   44.919939   44.919939    2.192653    2.192653
  g2-k8-p2          5.069841    5.069841   41.622151   41.622151    2.189204    2.189204
  g2-k8-p3          4.453211    4.453211   36.048212   36.048212    1.874372    1.874372
  g2-k16-p1         4.629770    4.629770   37.654195   37.654195    1.889135    1.889135
  g2-k24-p1         4.245819    4.245819   33.988706   33.988706    1.745247    1.745247
  g2-k32-p1         4.091415    4.091415   33.535756   33.535756    1.492057    1.492057

  CELLS REPRODUCED UNDER THE INCLUDE-PREFILL HYPOTHESIS: 21 of 21

The published max is chunk_ns[0] in every single row. So "the per-token time
varies by a factor of 15 to 22" is the ratio of the PREFILL to the fastest
decoded token, and the first-quarter mean is inflated by roughly one prefill
divided by sixteen, which is why every first quarter reads 4.09 to 6.07
seconds while no decoded token in any of those runs took more than 12.3.

8.9 THE SAME TABLE, CORRECTED

  run             n_dec first quarter  last quarter        min        max   max/min  last/first
  g2-k8-p1-a         63      2.391999      6.880262   2.143400  12.321797    5.7487    2.876364
  g2-k8-p1-b         63      3.476075      2.646582   2.192653   3.970570    1.8109    0.761371
  g2-k8-p2           63      2.633020      2.753601   2.189204   3.153743    1.4406    1.045796
  g2-k8-p3           63      2.346878      2.200992   1.874372   2.802250    1.4950    0.937838
  g2-k16-p1          63      2.428141      2.429133   1.889135   2.902297    1.5363    1.000408
  g2-k24-p1          63      2.262960      2.357749   1.745247   2.743228    1.5718    1.041887
  g2-k32-p1          63      2.128459      2.226152   1.492057   2.499102    1.6749    1.045899

  within-run decode spread max/min: 1.4406 to 5.7487
  first-to-last-quarter drift:      0.761371 to 2.876364, and six of the
                                    seven runs lie between 0.761 and 1.046

REFUTED. "Within one run the per-token time varies by a factor of 15 to 22."
It varies by 1.44 to 1.81 on five of seven runs, 1.67 on the gate's own
operating point, and 5.75 on exactly one run. "The drift between the first
and last quarter goes BOTH WAYS: 1.42 ... and 0.44 to 0.55 on every run after
it." Six of seven runs are within 24 percent of flat and four are within 5
percent. The one genuine outlier is g2-k8-p1-a, the first run of the evening
on a cold box, which drifts 2.88 in the SLOWING direction, opposite to the
sign the runlog reports for every run after the first.

WHAT THIS CHANGES, AND IT IS THE MORE USEFUL VERSION. RUNLOG-2 concluded
"NO, AND THE ANSWER IS NOT 'USE MORE TOKENS' ... it is the page cache filling
and emptying under a 63 GB working set". The page-cache reading is right and
this leg's own numbers support it, but it acts BETWEEN runs, not within them.
Within a run, once the prefill is out of the series, the per-token decode
time is close to stationary on six of seven runs. That has a product
consequence C4 section 7.2 can use: A TURN'S OWN RATE IS ESTIMABLE FROM ITS
FIRST FEW TOKENS, because it does not drift much afterwards, so bob's
announcement can be corrected mid-turn from a counter rather than left as a
manifest constant. The between-run band (0.257894810 to 0.447924206 tok/s at
K=8 on identical or near-identical bound states) is the real uncertainty and
it belongs to the wait class, not to the turn.

8.10 WHY NO GATE VERDICT MOVES HERE EITHER

Section 4.7 answers builder A's item (d), a handoff question, not a C4 bar.
Gate 2's bar names tok/s decode and TTFT, both of which are measured from
prefill_seconds and decode_seconds, neither of which comes from chunk_ns.
Every decode rate in this slice is unaffected.

--------------------------------------------------------------------------
9. OTHER FINDINGS THIS LEG OWNS
--------------------------------------------------------------------------

F-C1  See section 8, correction one. The schedule control moved zero routing
      decisions.

F-C8  See section 8, correction two. chunk_ns[0] is the prefill interval.

F-C2  THE MODEL FILE RE-HASHES, AND THE COST OF THE CHECK BOTH BUILDERS
      DECLINED WAS 46.64 SECONDS. Section 3. D7 and D6 discharged.

F-C3  "tok/s DECODE excl first" IS NOT A WARM-UP-EXCLUDED RATE, AND SHOULD
      NOT BE HEADLINED AS ONE. Builder A's item (d) proposes it as the figure
      to headline under OB5-024. Solving for the denominator the engine
      actually divides by:

        gen-120b-k8-a  n 32  decode_s 77.013305363   excl1 0.402528978
                       implied denominator 77.013088981
                       decode_s - implied  0.000216382
        g2-k32-p2      n 64  decode_s 120.471405756  excl1 0.522946083
                       implied denominator 120.471310615
                       decode_s - implied  0.000095141

      The field removes the first TOKEN from the numerator and removes about
      a tenth of a millisecond from the denominator. It is therefore
      (n_gen - 1) divided by essentially the whole decode window: a figure
      strictly LOWER than tok/s decode, by a factor of (n-1)/n, for a reason
      that has nothing to do with warm-up.

      AND THERE IS NO WARM-UP TO EXCLUDE. This leg looked, expecting to find
      a slow first token that would justify the field's name, and did not:

        run            first decode s median decode s      ratio
        g2-k8-p1-a           2.603594       3.034301     0.8581
        g2-k8-p1-b           3.263074       2.847563     1.1459
        g2-k8-p2             2.583285       2.706046     0.9546
        g2-k8-p3             2.737648       2.201438     1.2436
        g2-k16-p1            2.386909       2.369376     1.0074
        g2-k24-p1            2.082917       2.249553     0.9259
        g2-k32-p1            1.865677       2.099283     0.8887

      The first decoded token runs at 0.86 to 1.24 times the run median, in
      both directions, with no systematic penalty. So the field corrects for
      an effect that is not present, in a direction that makes the reported
      rate worse, under a name that suggests the opposite. HEADLINE tok/s
      DECODE, defined as n_generated_tokens divided by decode_seconds, which
      is what section 1 does. Keep the excl1 column if it is cheap, and
      rename it: it is a conservative variant, not a steady-state rate.

F-C4  A FIFTH INDEPENDENT READING OF THE DECODE-WIDTH PEAK CAME FREE, FROM
      OUTSIDE THIS WORKFLOW. The sibling P05 decode-shape leg
      (research/OB5B-DECODESHAPE-1.md) ran gpt-oss-20b under llama-perplexity
      at ubatch 1, which is decode width, on a DIFFERENT MODEL (24 layers, 32
      experts), a DIFFERENT BINARY (/root/ob1b/llama.cpp) and a different
      residency schedule (K=16). Its banked ob1-stats reads:

        peak_concurrent_lease_bytes=53015040

      the same 4 x 13253760. Builder B's central decode-regime number now has
      readings from the engine's own counter, from builder B's derivation,
      from this leg's independent reconstruction, from the narrow-prefill
      control, and from another workflow's run on another model. The
      per-expert tensor size 13253760 is identical in both GGUFs, which is
      why the figures coincide exactly rather than merely in shape.

F-C5  TWO CONCURRENT LEGS SHARED ONE OFF-REPO NAMESPACE. /root/ob5b2/runs and
      /mnt/f/f32/stage/research/ob5b2 hold both builder B's g2-* runs and the
      P05 leg's armA/armB runs, interleaved by timestamp (armA 15:30:51,
      g2-k8-p1-a 15:24:29, armB 15:40:57 local). Nothing was corrupted:
      builder B's artifact list is correctly scoped by the g2-* prefix, every
      g2-* digest in this document re-derives, and the P05 leg names the
      overlap on its own side. It is recorded as a REPLAY HAZARD, not a
      defect: a future reader told to look in /root/ob5b2/runs will find runs
      from two legs with two different models and two different binaries in
      one directory, and only the prefix tells them apart. It also
      independently corroborates builder B's deviation D2: the runlock
      contention builder B declared at 2026-09-01T19:35:11Z for "a gpt-oss-20b
      perplexity run (llama-perplexity, -ub 1, 8 threads)" is armB, whose own
      time -v block shows 5.53 minutes ending 15:40:57 local, that is
      19:35:24Z to 19:40:57Z.

F-C6  K3 IS NOT TRIPPED ACROSS BOTH LEGS JOINTLY, WHICH NEITHER RUNLOG
      STATED. Each builder scoped the kill line to its own runs. Over all 17
      generation runs in the slice the worst time to first token is
      53.007984199 s, on builder A's ub32 schedule control, on a 56 token
      prompt, which scales to 60.580553 s on a 64 token prompt against C4's
      120 s bar. The worst on the frozen schedule is 44.930562558 s on 56
      tokens. The floor, on a one token prompt, is 2.607288103 s. K3 NOT
      TRIPPED, with a factor of 1.98 in hand at the worst point in the slice.

F-C7  THE A/A LIMB IS STRONGER THAN THE RUNLOGS CLAIM, BECAUSE THE TWO LEGS
      ARE AN A/A PAIR OF EACH OTHER. Section 6. Gate 1's 32 ids are the
      prefix of gate 2's 64, across four days of page cache, two output
      trees, two n_predict values and a sibling workflow's 12 GB working set
      in between. Nobody designed that limb; it fell out of builder B
      choosing n_predict 64 on builder A's advice, and it is worth more than
      the third run D2 had to reinterpret.

--------------------------------------------------------------------------
10. THE PERF-DATA-POINTS LAW, CHECKED FIELD BY FIELD
--------------------------------------------------------------------------

Her standing order: every run banks tok/s, TTFT, wall, peak RSS, VmHWM, lease
counters and commit-peak counters, literal, in the runlog.

  tok/s decode           present on all 17 runs, and recomputed here from
                         n_generated_tokens / decode_seconds on every one
  TTFT                   present on all 17, section 1
  wall                   present on all 17, both the program's wall_seconds
                         and /usr/bin/time -v's own Elapsed line
  peak RSS               present on all 17, from each run's own time -v
                         "Maximum resident set size (kbytes)" block
  VmHWM                  present on all 17, in bytes and in kb
  lease counters         resident_slices_loaded, resident_bytes_loaded,
                         resident_read_ns, resident_verify_ns, lease_events,
                         lease_bytes_read, lease_read_ns, lease_verify_ns,
                         lease_drop_bytes, lease_drop_ns,
                         peak_concurrent_lease_bytes, route_calls,
                         per_layer_lease_events, chunk_ns: present on all 17
  commit-peak counters   alloc_commit_peak_single, alloc_commit_model_peak,
                         alloc_commit_total_bytes, alloc_commit_calls,
                         alloc_decommit_calls, alloc_decommit_bytes,
                         alloc_vma_peak, alloc_journal_records,
                         alloc_journal_bytes, alloc_journal_sha256:
                         present on all 17
  exit status            0 on all 17

  PERF-DATA-POINTS LAW: HONORED. No run in either leg is missing a field, and
  no field in either runlog's tables fails to re-derive from the raw counter
  files.

  ONE OBSERVATION ON COMPLETENESS RATHER THAN CORRECTNESS. RUNLOG-2 section
  4.7's per-token drift table leaves five of its twelve rows with the note
  "(in GATE2-ANALYZE-1.txt)" or blank instead of the numbers. The numbers
  exist and are banked off repo; the runlog is the publishable artifact and
  should carry them. This leg recomputed the missing cells and they are in
  section 8.9 in corrected form, since that whole table needed correcting for
  a different reason.

--------------------------------------------------------------------------
11. THE LIVE SERVE WAS NEVER TOUCHED
--------------------------------------------------------------------------

Proven from /proc rather than from a claim, and without connecting to it.

  $ tr "\0" " " < /proc/654/cmdline
  /root/.local/bin/openbob serve --tmax 6
  $ awk "{print \$22}" /proc/654/stat        (process start time, in ticks
  38695                                       since boot; invariant across a
                                              process's life)
  $ awk "/^btime/{print \$2}" /proc/stat
  1788026539
  $ getconf CLK_TCK
  100

  Start time = 1788026539 + 38695/100 = 1788026925.95, which is 2026-08-29.
  The field was read THREE times, spread across this leg's work from its
  first command to its last, and read 38695 every time, while etime advanced
  from 3-02:39:11 to 3-03:09:59. A restarted process would carry a new value.

  $ ls -l /proc/654/exe
  lrwxrwxrwx 1 root root 0 Sep  1 17:03 /proc/654/exe -> /root/.local/bin/openbob

  No "(deleted)" suffix, so the running image is still backed by that file's
  inode: the binary was not replaced under it.

  $ stat -c "%s %n %y" /root/.local/bin/openbob
  2431640 /root/.local/bin/openbob 2026-08-29 03:00:24.803265913 -0400
  $ sha256sum /root/.local/bin/openbob
  75dd58b963d0119e9a74f19e7eb47cece9f442ec93983afbd7f7b58fa246c0ca

  Size, mtime and digest are exactly what RUNLOG-2 section 5.1 recorded, and
  the mtime predates this slice by three days. THE INSTALL WAS NOT APPLIED.

  $ stat -c "%n mtime=%y ctime=%z nlink=%h" /root/.config/openbob
  /root/.config/openbob mtime=2026-08-28 22:43:38.764576789 -0400 ctime=2026-08-28 22:43:38.764576789 -0400 nlink=2

  The conf directory's own inode has not been written since 2026-08-28, four
  days before this slice, so no file was created, removed or renamed in it.
  Its CONTENTS were never opened by this leg, per the READ-NEVER wall; the
  directory inode is all that was read and it is all that is needed.

  $ ss -lntp | grep -E "8899|8907|8888"
  LISTEN 0 128 127.0.0.1:8899 0.0.0.0:* users:(("openbob",pid=654,fd=4))
  LISTEN 0 128 127.0.0.1:8888 0.0.0.0:* users:(("python",pid=489,fd=24))

  pid 654 still owns 8899. Port 8907 is free: the exposure worker is down, as
  it should be after a demonstration.

  $ ps -o pid,lstart,etime,cmd -p 654,489
  489 Sat Aug 29 14:07:02 2026  3-02:56:14 /opt/searxng/venv/bin/python -m searx.webapp
  654 Sat Aug 29 14:08:45 2026  3-02:54:31 /root/.local/bin/openbob serve --tmax 6

  A CAVEAT WORTH ONE PARAGRAPH, BECAUSE A CARELESS READER WOULD MISREAD IT.
  Earlier in this same session ps printed the start of pid 654 as
  "Sat Aug 29 14:08:24" and later as "Sat Aug 29 14:08:45", for a process
  that never restarted. ps derives lstart from /proc/stat's btime plus the
  process's start ticks, and under WSL2 btime is recomputed from uptime and
  jitters by tens of seconds. RUNLOG-2 quotes an etime of 3-01:59:30 and this
  leg reads 3-02:54:31 an hour later, which is consistent. THE INVARIANT IS
  FIELD 22 OF /proc/654/stat, and it is 38695 in every reading. Any future
  leg proving a guard process untouched should quote that field and not
  lstart.

--------------------------------------------------------------------------
12. THE PREPARED, VERSIONED INSTALL
--------------------------------------------------------------------------

  path  /mnt/f/f32/stage/research/ob5b2/install/OB5B-S1-BRAIN-LEASE-v1/

  $ sha256sum -c SHA256SUMS.txt
  ./BUILD-1.txt: OK          ./DEVHOME-1.txt: OK       ./H1-RIDER-1.txt: OK
  ./PATCH-1.txt: OK          ./SEAM-1.txt: OK          ./VERSION-REPORT-1.txt: OK
  ./br1-region.rs: OK        ./br1.patch: OK           ./gate3-patch.py: OK
  ./ob5b2-worker.py: OK      ./openbob-br1: OK         ./openbob.bm1.example: OK
  ./openbob.c1.example: OK   ./openbob_s11_cpu_br1.rs: OK

  Fourteen of fourteen. The package carries its version report and an H1
  rider, per the install law, and the rider is the brain lease itself with
  prompt and response verbatim and the counters that say which brain answered
  and what it cost. That is the right rider for this install, because the
  thing being installed IS the capability to call a leased brain.

  THE GAP THE VERSION REPORT NAMES ITSELF, and this leg endorses naming it
  rather than papering it: the base binary builder B built from
  /root/k4b/src/openbob_s11_cpu.rs is 6691776 bytes and the binary the live
  serve runs is 2431640 bytes. They were built from different flags and
  possibly different source. THE INSTALL DECISION NEEDS THE SOURCE AND BUILD
  COMMAND THE LIVE BINARY CAME FROM, so the brain lease is added to that
  lineage and not to a parallel one. Until that is supplied this package
  should not be applied even if she gates it, and the version report says so
  in its own words.

  The seven of eight model-free regression batteries that came back
  byte-identical between the base and patched binaries is the right evidence
  for "the patch changed nothing else", and the one that differed is a live
  GPU-utilization line, which is a clock-like reading and correctly quoted in
  full rather than hidden.

--------------------------------------------------------------------------
13. C4 KILL LINES, EVALUATED ON THE ACCEPTED EVIDENCE
--------------------------------------------------------------------------

  K1  BYTE-EXACT GENERATION FAILS       NOT TRIPPED. Three gate 1 runs
                                        identical on five limbs; gate 2's A/A
                                        pair identical on five limbs with a
                                        30.3 percent wall-clock difference;
                                        gate 1's 32 ids are the prefix of
                                        gate 2's 64 (section 6). All identity
                                        digests re-hashed here from the bytes.
                                        THE STANDING WEAKNESS IS F-A9, NOT
                                        THE EVIDENCE: one implementation.
  K2  DECODE UNUSABLE AT EVERY
      FITTING K                         NOT TRIPPED. The fitting K values are
                                        8, 16, 24 and 32; all four measured.
                                        Best at each: 0.447924206, 0.467876495,
                                        0.490587998, 0.531246395. K=32 on an
                                        in-corpus prompt is above 0.5 with no
                                        policy stack. K2's condition is "below
                                        0.5 at EVERY fitting K" and it is
                                        false at K=32 on a measurement.
                                        READ IT NARROWLY: 0.53 tok/s is a
                                        token every 1.88 seconds. It clears a
                                        kill line. It does not make a daily
                                        driver, and the wait class C4 section
                                        6.2 asks her to declare has to cover
                                        a band 2.06x wide.
  K3  TTFT ABOVE 120 s ON 64 TOKENS     NOT TRIPPED, jointly across both legs.
                                        Worst 53.007984199 s on 56 tokens,
                                        60.580553 s scaled. See F-C6.
  K5  DECODE COSTS EXPOSURE             NOT TRIPPED. Decode-phase peak
                                        concurrent is 53015040 on every run at
                                        every K, against the batch regime's
                                        1590451200. Exposure rises from
                                        8.209143 to 10.250022, 24.8610 percent.
  K6  PAIN CANNOT BE LOCALIZED          NOT TRIPPED on the limb gate 3
                                        reached: brain.identity.violation
                                        named the file, the digest it got and
                                        the digest the manifest pins, did not
                                        retry, and did not load the model. The
                                        SLICE-level limb, a corrupted expert
                                        slice localized to layer and expert,
                                        is S2's and is untouched here.
  K4, K7, K8, K9                        Out of scope for slice 1.

--------------------------------------------------------------------------
14. HONEST LIMITATIONS
--------------------------------------------------------------------------

L1  ONE GENERATION IMPLEMENTATION. Everything in this slice, including all
    500 checks in this document, would pass unchanged against a deterministic
    bug inside ob5b1-gen. This is the single largest hole and it is owed.
    Builder A's F-A9 and builder B's item (d) both name it; acceptance
    confirms it cannot be closed by re-reading bytes.

L2  ACCEPTANCE RE-DERIVED, IT DID NOT RE-RUN. This leg made no model run, so
    the physical claims (that these runs happened on this box, at these
    times, holding the runlock, with the guards alive) rest on each run's own
    banked driver output, which acceptance read but did not witness. The
    guards' liveness at the time of the gate 3 turn is the worker log's own
    guards_before and guards_after fields, and those are the worker's word.
    What acceptance CAN prove independently is that the live serve was not
    restarted at any point (section 11), which is the claim that matters.

L3  THE DECODE RATE IS A BAND BETWEEN RUNS AND SIXTEEN RUNS DO NOT NARROW IT.
    Two byte-identical runs differed by 30.3 percent in decode wall clock.
    The read rate ranged 793821816 to 1567086343 bytes/s between runs of the
    same binary, a factor of 1.974, driven by the page cache a process is
    born into. Every tok/s figure in this document should be read with that
    band around it. Section 8.9 sharpens where the band lives: BETWEEN runs,
    not within them. The byte figures, the lease counts and the ACCT have no
    band and are exact.

L4  THE STATIC RESIDENT SET'S RANKED VALUE DOES NOT TRANSFER, AND THIS LEG
    CONFIRMS IT RATHER THAN SOFTENING IT. Gate 0 measures 0.4040035672 top-8
    mass in its own corpus; a served prompt cut from that very corpus scored
    0.1585286458 in decode. Builder B refuted small sample as the explanation
    with a window study. The regime gap between a perplexity harness at
    ub 4096 and a served prefill at ub 64 from position 0 remains unmeasured,
    and section 8's correction narrows the candidate causes: the ubatch width
    alone changes NO routing decision at 64 against 32, so if the ubatch
    width is the cause it must act at a much larger width than this control
    tested. Context position is now the stronger candidate, and the run that
    separates them is still owed to whoever next holds the RS053 harness.

L5  n_ubatch 64 AGAINST 32 IS ONE POINT ON ONE AXIS. The correction in
    section 8 says this control observed nothing. It does not say a batch
    schedule can never move an answer, and no reader should take it that way.

L6  x1_spell AND NON-ASCII ANSWERS. Builder B's F-B8 stands unexamined here:
    a called brain that answers in mathematics currently cannot be banked,
    because the fabric refuses x1.noncanonical rather than mangling. That is
    the right direction and a real product limit, and it is slice 2's.

--------------------------------------------------------------------------
15. DEVIATIONS
--------------------------------------------------------------------------

DC1  NO RUNLOCK WAS TAKEN. The house law binds the lock to model runs and
     this leg made none. The one heavy operation, the 63 GB model hash, ran
     at nice 19 outside the lock, on an idle box (load average 0.02, no
     model process running, both guards idle), for 46.64 seconds. Declared
     rather than left silent, because it is a large sequential read that
     evicts page cache and the page cache is this slice's largest
     uncontrolled term (F-B6).

DC2  ~/.config/openbob's DIRECTORY INODE WAS STAT'ED. The READ-NEVER wall
     names the directory's contents (tokens, pins). No file inside it was
     opened, listed or read; only `stat` on the directory itself, whose
     mtime and ctime are what proves nothing was added or removed. If the
     wall is meant to forbid even that, the claim in section 11 about the
     conf directory should be struck and the rest of section 11 stands
     without it.

DC3  BUILDER A's D2 IS ACCEPTED AS DECLARED. Gate 1's third limb, "after a
     serve restart", could not be taken literally under the hard walls.
     Acceptance accepts the reinterpretation, records that it is a
     reinterpretation and not a satisfaction of the literal clause, and notes
     in section 6 that gate 2 supplied a stronger substitute after the fact.

DC4  THE 1085 FIGURE WAS NOT RECONSTRUCTED. Section 8.3. This leg reproduces
     builder B's three published digests exactly and shows the two row lists
     are permutations, which settles the question; it does not reconstruct
     which positional variant produced 1085 rather than 2205.

DC5  BUILDER B's PHASE A SCRIPT REVISION IS ACCEPTED AS DECLARED. RUNLOG-2
     section 11 declares that phase A ran an earlier revision of
     gate2-sweep.sh, digest 79f685a8..., differing from the committed file by
     a pure insertion of 22 lines and nothing else. Acceptance did not
     re-derive that diff, because the earlier revision is not on disk under
     that name; the declaration is taken at its word and named here as taken
     at its word.

No other deviations. Nothing in OB5-DESIGN-C4-1.md, OB5A-ALLOC-1.md,
OB5B-S1-RUNLOG-1.txt or OB5B-S1-RUNLOG-2.txt was renegotiated by this leg,
and the two findings corrected in section 8 are corrected by measurement and
not by argument.

--------------------------------------------------------------------------
16. WHAT SLICE 2 AND THE POLICY CHAPTERS INHERIT
--------------------------------------------------------------------------

a) A SECOND GENERATION IMPLEMENTATION (L1, F-A9). The only limb that tests
   the instrument rather than the machine. Nothing else in the ladder is
   worth more per token.

b) THE LIVE BINARY's LINEAGE, before any install of the brain lease is
   applied (section 12).

c) THE REGIME QUESTION (L4), narrowed: context position now outranks ubatch
   width as the candidate cause, because the ubatch control changed no
   routing decision at all.

d) THE POLICY STACK's TARGETS ARE NOW NUMBERS. At K=32, 0.470834533 tok/s out
   of corpus at 101.046875 decode misses per token, and 0.531246395 in corpus
   at 87.531250. research/ob5b1/gate2-sweep.sh and gate2_decode_acct.py, and
   this leg's accept_route.py, all take a resident-set file and a K and
   produce the whole row with no new instrument.

e) THE ANNOUNCEMENT ARITHMETIC should be anchored on measured TTFT per prompt
   token: 0.471437 s at K=32 and 0.719879 s at K=8 on the harder prompt, and
   NOT on C4's P-C, which misses by 1.827657. AND IT CAN BE CORRECTED
   MID-TURN. Section 8.9 shows the per-token decode time is close to
   stationary within a run on six of seven runs, so after a handful of tokens
   the turn's own rate is known and the estimate can be replaced by a
   measurement. Under the dashboard law that is the better surface: an
   announcement that says "about 40 seconds" from a manifest constant and
   then never moves is exactly the needle her law objects to, and this leg's
   numbers say a moving one is available for free.

f) A FRAME FOR THE CALLED BRAIN (RUNLOG-2 item a), and x1_spell (L6).

g) THE OFF-REPO NAMESPACE (F-C5). Give each leg its own directory.

--------------------------------------------------------------------------
17. ARTIFACTS AND DIGESTS
--------------------------------------------------------------------------

IN REPO, branch research-2, added by this leg only under its own paths:

  research/OB5B-S1-1.md                 this file
  research/ob5b1/accept_hash.py         7ef0a00f76d1c38320aed7bc80c29fe427e1ef1f7ef6b2d56afd7345116b54ff
  research/ob5b1/accept_route.py        9ce3bdf34f2f5a64788d7bdf4b1169667beecf4595e6543ac6f9bbbb5b6bfb35
  research/ob5b1/accept_gate0_cells.py  04e21299d263758dd30da8b37972b68ed970ef9e10a43358ae17c27ff4af07bb
  research/ob5b1/accept_arith.py        0c79e76434380480ef9a415db610c52caf6fde61f2e3f545f59e13a976e9d761
  research/ob5b1/accept_cross.py        0cf2c517832643e0278a069d3d29a8c43492d9727c26c98f115369d3c7c5cd04
  research/ob5b1/accept_sched.py        68c119b9f20d68d31de4d2111940dac6a7ed9cb446c9e6c0fce7a5ca5fe8f0a4
  research/ob5b1/accept_chunk.py        a6481aece18bf57cf5a947b521a8cc4403835c0798e5d196b31642259847bc1e
  research/ob5b1/accept_gate3.py        847f88882a504cb2ebbd403ec2f0c5ddf654bab5fd7c1a33fb8e7b359e53c7d3

  Every one is LF-only and pure ASCII. The sweep over all 34 files this slice
  committed before this leg, plus these eight, reads CR 0, non-ASCII bytes 0,
  em dashes 0.

  BOTH PRIOR COMMITS ARE APPEND-ONLY, verified rather than assumed:
    4c5c2d9  insertions 3389  deletions 0   18 files, all status A
    9007d83  insertions 3995  deletions 0   16 files, all status A

THE DECIDING DIGESTS OF THE SLICE, ALL RE-HASHED BY THIS LEG FROM THE BYTES:

  gpt-oss-120b-MXFP4.gguf     582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d
                              63387346208 bytes, hashed whole by this leg
  gate 1 identity (ids)       5855bcebe6b98f73879a79527b2a9e32fc7b8e43ca8808ac48e6d17634e993e4
  gate 1 identity (text)      99417b7488e53ca611f5d9a9e1211ea3491ec0e34e38c4353520ed8f7fe805b4
  gate 1 prompt ids           a5e714dacc907126af664f8d512a3bed55a54a325692e4e44cd5eef2c21715d5
  gate 1 route                50b8554c38627be594c5ab4314f680380e43fb9f60aaf5e42bc30a742cad5b32
  gate 1 alloc journal        0beefc532904765a029f2ab8dee6ddf72e2b6ebd87fa3b58cb4caaaaef14b6f0
  gate 2 identity (ids)       5b751861465660a73ec9e895f03f01d81f0522e5ef27c713efb44746c38b7686
  gate 2 identity (text)      539e71d138c3c7b15e379b0b6f0729a691d7569884182a9617fabf462ea5da55
  gate 3 turn identity        55df750df27733224d3df21726cafc50b1e6ca6051909f66d8c813dd5a2e2f86
  gate 3 answer bytes         613dd289c02ca2cf5eecfc432781b4931c602a1d6099d224e3f1966133299850
  gate 3 worker log           021b0dddc3e867ad4002a1f6b56562074c0a95135be069f428abb293326b7719
  gate 3 alloc journal        4af4cb9b30b8bd3bf85dd7509467f44314d78c9cc619e22c6bf153d302242332
  brain manifest (BM-1)       711fcff626e0a6d4c5d5069e28ad27b222609a4199ac51b34517074adcf8eb4e
  engine (ob5b1-gen)          daca8fb74f626c186950c2882dfd1fdfe191056ca5feacccd51201db3e625740
  fabric binary (BR1)         0ef39cbe990a15ba6d628b7e193515f1382e023e57d301ef391e8e835baab0d1
  live serve binary, UNMOVED  75dd58b963d0119e9a74f19e7eb47cece9f442ec93983afbd7f7b58fa246c0ca

  AND THIS LEG's OWN NEW DIGESTS, from section 8:
  gate 1 ctl canonical route  f7f4356da866fe4d81836dcbc39ffdacb296378760154a8c549706366eb8f1f6
                              (identical at n_ubatch 64 and 32)
  gate 2 ctl canonical route  eaa790921ead8d6a801096bb04417ac9c1d346f4e3e8f91a133713f6ca88d07e
                              (identical at n_ubatch 64 and 32)

OFF REPO, per the house law that run evidence stays off the repo:

  /root/ob5c1/MODEL-SHA-1.txt, MODEL-SHA-1.time   the 63 GB hash and its time -v
  /root/ob5c1/c1_*.py                              the executed copies. Each
                                                   was compared to its
                                                   committed accept_*.py:
                                                   7 of 7 MATCH, so the file
                                                   in the repo is the file
                                                   that produced the numbers
                                                   above. accept_chunk.py was
                                                   written into the repo and
                                                   executed from there.
  /root/ob5b1/runs/, /root/ob5b2/runs/             the runs read by this leg
  /root/ob5b2/worker/                              the gate 3 turn
  /mnt/f/f32/stage/research/ob5b2/install/OB5B-S1-BRAIN-LEASE-v1/
                                                   the prepared install

--------------------------------------------------------------------------
18. THE STANDARD THIS LEG WAS HELD TO
--------------------------------------------------------------------------

The four bars were written in OB5-DESIGN-C4-1.md before any of the three
builders existed and none was renegotiated. All four passed, and acceptance
re-derived them from raw bytes by different code rather than confirming them
by reading.

What is reported at greater length than the passes is what the slice got
wrong, and both of the two things are the same mistake.

In the first, two runlogs, two builders, two independent instruments and two
separate findings all read a difference in a file where there was no
difference in the machine, because both compared two logs positionally when
the logs were permutations of each other. In the second, a table of
per-token times was built on a series whose first entry is not a token but
the whole prefill, so a 40 second prefill was averaged in with 2 second
tokens and reported as within-run variance.

Both are the same failure: a derived statistic taken from a data structure
whose layout was assumed rather than checked, producing a number plausible
enough that nobody checked it. Both survived a verifier. RUNLOG-1's
verify-runlog-arith.py reports CHECKS 49, DISAGREEMENTS 0 and RUNLOG-2's
reports CHECKS 70, DISAGREEMENTS 0, and both are honest: they recompute the
ARITHMETIC a runlog does on figures it has already read off a run. Neither
re-reads the run. A verifier that recomputes a document's arithmetic cannot
catch a figure that was wrong before the arithmetic started. THAT IS THE
PROCESS LESSON OF THIS SLICE, and it is why an acceptance leg re-derives
from raw bytes rather than re-checking a runlog against itself.

Neither error was load bearing on a gate, which is why the slice still
passes; both were load bearing on how the next chapter reads the evidence,
which is why the corrections come first, after the verdicts.

The measurement the slice most wanted, the decode-regime exposure, is
confirmed: 10.250022 against a projection of 10.162898, on a number now read
five independent ways, on a box holding 6184118048 bytes of a 63387346208
byte brain.

END OB5B-S1-1.
