# OB5A-ALLOC-1: THE RESIDENT-PROPORTIONAL ALLOCATOR, AND THE 120b
# LEASED ROW IT MAKES POSSIBLE
#
# OB-5a builder 3, the acceptance and receipt leg. Written 2026-09-01 on
# f32-HYDE after an INDEPENDENT re-derivation from the raw run bytes: every
# digest in this file was re-hashed for this document, every exposure figure
# recomputed from the byte arithmetic, every p95 recomputed nearest-rank from
# the raw chunk_ns vectors. No number below was copied from a builder's table.
# Pure ASCII, no em dashes. Failed and surprising numbers are quoted verbatim.

## 0. THE ANSWER, FIRST

On 2026-08-31 the leased 120b point could not start. The runtime asked the
kernel for one allocation of 63374323968 bytes on a box with 24029 MB of RAM,
and the kernel refused. The run died at model load in 1.068426206 seconds.

It now runs. Twice. Byte for byte identical to a reference produced by a
completely different memory mechanism.

  MODEL      gpt-oss-120b-MXFP4.gguf, 63387346208 bytes, sha256 582bd40f...
  CONFIG     K=8 of 128 prose-ranked resident sets, leased, 8192 tokens
             AC-PROSE, CPU only, 8 threads nice 10, no kernel knob
  RESULT     exit_rc 0 on both runs, wallclock 723.056845679 s and
             723.344961536 s

  alloc_va_model_bytes        63374323968   the reservation, DECLARED not charged
  alloc_commit_model_peak      7806517248   what the kernel was actually asked to back
  alloc_commit_peak_single      615333888   the largest single request, 586.83 MB
  VmHWM                        9034235904   bytes (8822496 kbytes), run A
  EXPOSURE_acct                   8.209143  the prediction banked before any run, hit exactly
  EXPOSURE_rss                    7.016348
  p95 per chunk                 89174.2 ms  against a frozen bar of 99239.6 ms

The allocation that leasing exists to avoid, and that used to fail first, is
gone. The largest single request the engine now makes is 102.9918 times smaller
than the one that killed it.

## 1. THE RULING THIS SERVES

The owner's words, as carried into OB5A-ALLOC-1-PREREG.md section 1 from
OB5-PLAN-1.md section 0:

  "If the whole premise is N >> M, then the runtime should eventually never
  require an allocation proportional to N. That makes the OB-5 allocator more
  than cleanup. It is part of the architecture. The result I'd prioritize now
  is: 120B live exposure with allocation proportional to resident state, not
  total model state."

Two clauses, and they are separable. The runtime must never require an
allocation proportional to N. The 120b must expose live. This receipt reports
both, measured, on the same runs.

## 2. THE BLOCKER, AS THE ENGINE PRINTED IT

From OB1B-KNEE-1.md section 9, verbatim:

  0.00.503.908 W common_fit_params: failed to fit params to free device memory:
               was unable to fit model into system memory by reducing context, abort
  0.00.806.033 E ggml_aligned_malloc: insufficient memory (attempted to allocate 60438.47 MB)
  0.00.806.050 E ggml_backend_cpu_buffer_type_alloc_buffer: failed to allocate buffer of size 63374323968
  0.00.806.050 E alloc_tensor_range: failed to allocate CPU buffer of size 63374323968
  0.00.878.238 E llama_model_load: error loading model: unable to allocate CPU buffer
  0.00.878.263 E llama_model_load_from_file_impl: failed to load model
  0.00.878.277 E llama_perplexity: unable to load model

  exit_rc 1   wallclock_s 1.068426206   Maximum resident set size 350856 KB

The CPU buffer type declares get_max_size as NULL, so the buffer split condition
in ggml_backend_alloc_ctx_tensors_from_buft_impl is never true and the entire
model context becomes ONE posix_memalign of 63374323968 bytes. Under Linux
heuristic overcommit that mapping is accountable, and it is refused. The lease
engine, which would have touched only 12.18 percent of those bytes, never got
the chance to prove it.

## 3. THE APPROACH, AND WHY IT WAS CHOSEN

The prereg ran a design study first, per the owner's margin-0 pattern, and read
the actual allocation path rather than a description of it. Three candidates
were judged from that code; approach A was frozen with C's trunk/expert split at
commit granularity, and B was rejected with reasons.

RESERVE, THEN COMMIT. The model buffer is taken once as a single PROT_NONE
reservation at the exact byte count, WITHOUT MAP_NORESERVE, deliberately. A
PROT_NONE mapping is not accountable, so the overcommit check does not run on
it, and the kernel backs nothing. Pages are then committed outward-rounded at
the moment the loader or the lease engine actually writes them, and decommitted
inward-rounded when a lease drops.

Four properties of the existing code made this safe, and each was verified in
the source rather than assumed:

  1. Nothing in the allocation walk writes a byte into the buffer. The CPU
     buffer interface declares init_tensor as NULL. A buffer that is entirely
     PROT_NONE survives the whole walk.
  2. ggml_backend_buffer_clear is not called on the model weights buffer. It is
     called on adapter, KV cache, recurrent memory and output buffers, none of
     which are the weights.
  3. The loader writes into cur->data DIRECTLY, not through
     ggml_backend_tensor_set. So the commit hook cannot live in the buffer
     interface; it has to live in the loader, beside the existing lease hook.
     It does.
  4. The decommit primitive is arm C: inward-rounded madvise(MADV_DONTNEED)
     followed by inward-rounded mprotect(PROT_NONE). The prereg measured that
     mprotect ALONE decommits nothing. That trap was measured, not warned about.

The one-line alternative was refused. Setting vm.overcommit_memory=1 makes the
120b start tonight and changes nothing about the architecture: the runtime still
asks for 63374323968 bytes and the kernel merely stops saying no. It is also a
box-wide kernel change on a machine running the owner's live serve. Section 7
reports what happens when you measure the same point both ways.

A PROT_NONE fault inside the expert region was declared, in advance, a
CORRECTNESS FINDING and not a crash to be patched around: it would mean a read
touched an expert the residency schedule said was absent, which under the older
madvise design would have silently returned zeros. None occurred.

## 4. THE DIFF

Against llama.cpp branch ob1b at c087083, plus the K=0 guard fix (prereg D3):

  ggml/src/ggml-backend.cpp    362 insertions      the reserve/commit buffer type
  src/ob1-lease.cpp            264 insertions      commit and decommit at lease
                                                   boundaries, the journal
  src/ob1-lease.h               56 insertions      the interface
  src/llama-model.cpp           26 insertions      reserve-mode buffer selection
  src/llama-model-loader.cpp    13 insertions      the commit next to the lease hook
  ----------------------------------------------------------------------------
  5 files changed, 715 insertions, 6 deletions

Six deletions across 715 insertions. The allocator is additive: it is a new
buffer type selected by mode, not a rewrite of the old path.

BUILD LINEAGE, three phases, each digest-verified in BUILD-1.txt:

  phase A  reproduces the LANDED engine exactly          SAME as required
  phase B  reproduces the OB-1b digest-banking engine    SAME as required
  phase C  the allocator, built on top                   .text differs by design

  the running binary, phase C:
    llama-perplexity              f9965806c98f5dce6cc7f4f44e52dd57e8d9b51cf27826ad4608db4599e23249
    libllama-perplexity-impl.so   5aea400e28040543c7f0f005d95e1a8d976650956b4d8a8c22774fdd90923c72

  Both digests re-verified for this receipt against the live build tree: MATCH.

## 5. P1, THE 20b IDENTITY REGRESSION (STOP-SHIP)

The prereg made P1 a gate, not a report: any mismatch ends the leg and the
allocator never touches the 120b. Four runs on gpt-oss-20b at the frozen
configuration, each required to hash to the BANKED pair for its corpus, which is
a stronger statement than matching its own reference.

  run             mode        identity (re-hashed today)   route (re-hashed today)   verdict
  res-prose       resident    96049ccf...d551925  MATCH    4777aa83...dffc3df  MATCH  PASS
  res-code        resident    9acdf5ef...62aa0ae8 MATCH    f0c3f341...9bff41c77 MATCH PASS
  lease-k8-code   lease K=8   9acdf5ef...62aa0ae8 MATCH    f0c3f341...9bff41c77 MATCH PASS
  lease-k0-prose  lease K=0   96049ccf...d551925  MATCH    4777aa83...dffc3df  MATCH  PASS

  banked prose identity  96049ccf8ca241bf58233afe13ed75e2ca43180d81973360d04cebc80d551925
  banked prose route     4777aa8319f25d6e367f761ef12c7bec81a9ff7896bfed1b8ea0326b5dffc3df
  banked code  identity  9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8
  banked code  route     f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77

EIGHT OF EIGHT. Re-hashed from the raw bytes for this receipt, in both the
off-repo run tree and its stage mirror, which agree exactly.

  P1a  identity and route hash to the banked pair, all four runs      PASS
  P1b  lease-k8-code   lease_events 18100, peak_concurrent 318090240  PASS
       lease-k0-prose  lease_events 23096, peak_concurrent 424120320  PASS
  P1c  res-prose and res-code report lease_events 0 and
       resident_bytes_loaded 0                                        PASS

The counters matter as much as the digests. The leased rows are simultaneously
banked measurements from OB-1b and predictions for this leg, so P1b proves the
allocator did not move the lease schedule while leaving the output alone.

P2 ON THE 20b, from the same runs:

  run             commit_model_peak   prereg bar    headroom    verdict
  lease-k0-prose         2359328768    2373083808    13755040   PASS
  lease-k8-code          4793679872    4811775648    18095776   PASS
  res-prose, res-code   12096561152   the whole model by construction (P2d control)

  P2c VmHWM within 1.25x of commit peak plus engine buffers:
    res-prose 1.0225   res-code 1.0238   lease-k8-code 1.0542   lease-k0-prose 1.0884
                                                                          all PASS

The K=0 leased commit peak of 2359328768 bytes sits 5.1271 times below the
12096558336-byte model-state request the old allocator makes for the same run.

## 6. THE 120b ROW, ON THE ALLOCATOR

THE HEADLINE. gpt-oss-120b, K=8 of 128, leased, 8192 tokens AC-PROSE, CPU only,
under the runlock, A/A repeated, no kernel knob.

| field                        | run A (p3-120b-k8-prose-a) | run B (p3-120b-k8-prose-b) |
|------------------------------|----------------------------|----------------------------|
| exit_rc                      | 0                          | 0                          |
| wallclock_s                  | 723.056845679              | 723.344961536              |
| identity sha256              | 9d20bd03...1682019 MATCH   | 9d20bd03...1682019 MATCH   |
| route sha256                 | a32d0051...0cd89c1 MATCH   | a32d0051...0cd89c1 MATCH   |
| EXPOSURE_acct                | 8.209143 on ACCT 7721554208| 8.209143 on ACCT 7721554208|
| EXPOSURE_rss                 | 7.016348                   | 7.014962                   |
| VmHWM                        | 9034235904 B (8822496 kb)  | 9036021760 B (8824240 kb)  |
| alloc_commit_model_peak      | 7806517248                 | 7806517248                 |
| alloc_commit_peak_single     | 615333888 (586.83 MB)      | 615333888                  |
| alloc_va_model_bytes         | 63374323968 (declared)     | 63374323968                |
| alloc_commit_calls           | 166617                     | 166617                     |
| alloc_decommit_calls         | 163920                     | 163920                     |
| alloc_vma_peak               | 48962                      | 48960                      |
| alloc_journal_sha256         | ff7c4b1d...c308d76         | ff7c4b1d...c308d76         |
| lease_events                 | 27403                      | 27403                      |
| peak_concurrent_lease_bytes  | 1590451200                 | 1590451200                 |
| lease_bytes_read             | 363192785280               | 363192785280               |
| p95 per chunk                | 89174.2 ms (1.7971x)       | 89061.1 ms (1.7949x)       |

  the banked paged reference pair, the identity target:
    identity 9d20bd0365554989051d96b6ad4932625b0a6578002879f8253e6fcc21682019
    route    a32d0051bd6d68f2777e64c7b889ae48d56621e9701b107fcef88c0e30cd89c1

  the identity line itself, verbatim, on both runs and on the reference:
    [1]88.3425,[2]50.2396,[3]30.1827,[4]30.7592,[5]25.4183,[6]21.7583,[7]20.3296,[8]19.6660,

### 6.1 The bars, each re-derived independently for this receipt

  P2a  ALLOCATION BAR. commit_model_peak 7806517248 <= bar 7833915680,
       headroom 27398432.                                              PASS
       Re-derived from the buffer, not from a builder's table:
         buffer trunk       63374323968 - 61073326080 = 2300997888
         K x L x per_expert  8 x 36 x 13253760        = 3817082880
         peak concurrent                                = 1590451200
         sum before edge                                = 7708531968
         edge actually paid  7806517248 - 7708531968    =   97985280
         census bound (prereg s3.5)                     =  112361472
         edge is 87.21 pct of its bound: predicted, not loose, not exceeded.

  P2b  THE 63 GB REQUEST IS GONE. peak single commit 615333888 <= the
       1073741824 ceiling; no request of 63374323968 bytes of any kind.
       The engine's line now reads a PROT_NONE reservation where the fatal
       used to be. Reduction 63374323968 / 615333888 = 102.9918x.       PASS

  P2c  VmHWM vs COMMITTED STATE. The denominator was RE-MEASURED on the
       120b (941195736 bytes of engine buffers at load), not carried over
       from the 20b's 915046871.
         run A  9034235904 / 8747712984 = 1.0328   bar 1.25             PASS
         run B  9036021760 / 8747712984 = 1.0330   bar 1.25             PASS
       The unaccounted column is 286522920 and 288308776 bytes. On the 20b
       it was 292589097 to 310087209. It DID NOT GROW across a model
       5.2345 times larger. That is the load-bearing observation: had the
       allocator been leaking anything proportional to N, this is the
       column it would have leaked into.

  P3a  IDENTITY vs the banked paged reference, both runs, both limbs.    PASS
  P3b  COUNTERS vs the banked predictions, exactly:
         lease_events        27403 = 27403
         peak_concurrent     1590451200 = 1590451200
         lease_bytes_read    363192785280 = 27403 x 13253760, re-derived  PASS
         per_layer_lease_events, all 36 layers, reproduced as banked       PASS
  P3c  EXPOSURE. ACCT 7721554208 = predicted; 63387346208 / 7721554208
       = 8.209143, recomputed here from the byte arithmetic.            PASS
  P3d  LATENCY. p95 nearest-rank recomputed from the raw chunk_ns vector:
       sorted run A gives 89174158085 ns as the seventh of seven, so
       89174.158085 ms. tau_0 exact is 49619800502 ns = 49619.800502 ms,
       bar 99239.601004 ms. Ratio 1.7971.                               PASS
  P3e  A/A. identity and route byte-identical between the two runs, and
       every deterministic counter identical to the event.              PASS
  P4b  alloc_journal_sha256 A == B, ff7c4b1d...c308d76.                  PASS
  P4c  the PRINTED digest equals the sha256 of the journal FILE. Verified
       here on both live journals (9404962 bytes each) and on both gzipped
       stage archives, which uncompress to the same ff7c4b1d...c308d76.  PASS
  P4d  alloc_commit_calls and alloc_decommit_calls identical A/B, and
       reconciled to the residency schedule.                            PASS
       See finding F-B3-2: the bar's literal wording needs amending.

  OB5A_120B_ANALYZE_FAILURES=0
  ALL BARS PASS: P1a P1b P1c P2a P2b P2c P2d P3a P3b P3c P3d P3e P4b P4c P4d

### 6.2 What the counters settle that argument could not

The prereg's deviation D4 corrected the plan's "~8.10x" to 8.209143 on a
reading of the route log: in the worst micro-batch all 128 experts of some layer
are routed, 8 of them are resident, so 120 are concurrently leased, and the peak
concurrent term is (E-K) x per_expert = 1590451200 rather than E x per_expert =
1696481280. That was an argument about a log. The engine has now MEASURED
peak_concurrent_lease_bytes at 1590451200, twice. D4 is settled by measurement.

## 7. THE SCOUT BESIDE IT: THE KNOB AND THE ARCHITECTURE

The architect ran an overcommit scout the same day (OB5A-SCOUT-1.md), measuring
the SAME 120b point on the LANDED engine with vm.overcommit_memory=1. It is the
control this receipt could not otherwise have: two allocation strategies, one
output.

  point                    mechanism              identity + route   RSS peak      p95 per chunk
  sc120-k8-prose-a         kernel knob, landed    both MATCH         9042874368 B  87783.560543 ms (1.7691x)
  sc120-k8-prose-b         kernel knob, landed    both MATCH         9039876096 B  88809.922279 ms (1.7898x)
  p3-120b-k8-prose-a       allocator, no knob     both MATCH         9034235904 B  89174.158085 ms (1.7971x)
  p3-120b-k8-prose-b       allocator, no knob     both MATCH         9036021760 B  89061.081299 ms (1.7949x)

FOUR RUNS, TWO ALLOCATION STRATEGIES, ONE OUTPUT. All four hash to
9d20bd03...1682019 and a32d0051...0cd89c1, and all four report lease_events
27403, peak_concurrent_lease_bytes 1590451200, lease_bytes_read 363192785280.

I verified the scout's own trail independently rather than accepting its
summary. Its logs record overcommit_at_run: 1 on all three cycles, as declared,
with guard_pids 1 openbob and 1 searxng before and after every cycle. The box
reads /proc/sys/vm/overcommit_memory = 0 now. The scout's stated p95 ratios of
1.7692 and 1.7899 recompute to 1.7691 and 1.7898 against the exact tau_0 of
49619.800502 ms; a last-digit rounding difference, recorded and immaterial
(finding F-B3-3).

THE COST OF DOING IT ARCHITECTURALLY, stated plainly:

  chunk time, run a of each   scout 607.022724 s   allocator 609.362892 s
  difference                  +2.340 s, +0.3855 pct
  mean of both pairs          scout 607.138701 s   allocator 609.514220 s
  difference                  +2.376 s, +0.3913 pct
  on p95                      +1.5841 pct
  scout's own A/A p95 noise    1.1692 pct

The prereg predicted +1.790 s of mprotect cost and its deviation D5 declared
that a LOWER BOUND, because the probe ran at 4 threads under house law while the
run uses 8, and TLB shootdown cost rises with the number of CPUs the address
space is active on. Measured is +2.340 s: 30.7 percent above the prediction, in
the declared direction. The p95 figure of +1.5841 pct overstates the cost,
because it sits only 1.35 times above the scout's own A/A noise of 1.1692 pct.

AND THE KNOB IS NOT THE PRODUCT. The scout's peak RSS is 9042874368 bytes and
requires a box-wide kernel change on a machine running the owner's live serve.
The allocator's peak COMMITTED model state is 7806517248 bytes, needs no kernel
change at all, and the same runs land VmHWM slightly lower than the scout's
(9034235904 against 9042874368). The architecture is tighter and cheaper in
permissions, for four tenths of one percent of chunk time.

## 8. THE MOONSHOT SLOPE

The prereg named the comparison before the run existed: at MATCHED resident
fraction K/E = 6.25 percent (20b K=2 of 32; 120b K=8 of 128),

  gpt-oss-20b    N 12109566624   ACCT 2964472224   EXPOSURE 4.084898   measured, OB-1b
  gpt-oss-120b   N 63387346208   ACCT 7721554208   EXPOSURE 8.209143   MEASURED, this leg

  N grows      5.2345x
  ACCT grows   2.6047x
  exposure ratio at matched resident fraction  2.0096x

The slope was arithmetic when the prereg banked it. It is now two measured
points. Model state grew 5.2345 times; the memory the runtime must actually hold
grew 2.6047 times. Exposure roughly doubles because the larger model is sparser
and more expert-heavy, so a fixed resident FRACTION buys proportionally more of
it. ACCT is 12.1815 percent of the model; the peak actually committed,
7806517248 bytes, is 12.3156 percent of it.

This is the direction the 1T horizon needs, and it is worth saying exactly what
it does and does not establish. It establishes that exposure rises with sparsity
at fixed resident fraction, on two real models, with byte-identical output at
both points. It does not establish the shape of the curve between or beyond
them. Two points are a slope, not a law.

## 9. HONEST LIMITATIONS

These are limitations of the measurement, not caveats bolted onto a claim.

  1. CHUNK-LEVEL TIMING. The engine reports 7 chunk intervals for an 8-chunk
     run, so a nearest-rank p95 of 7 samples IS the maximum sample. Every p95
     in this receipt, including the scout's and the paged reference's, is a
     max-of-7. It is the most pessimistic reading available and it is the one
     the prereg froze, but it is not a percentile in any useful statistical
     sense.

  2. tau_0 IS PAGED, NOT RESIDENT. A fully resident 120b baseline is
     UNMEASURABLE on a 24029 MB box. The latency bar is set against
     pag120-prose-a, an mmap-paged run, and is named as such rather than
     substituted. Every 120b latency ratio in this document is against a
     baseline that is itself doing memory work.

  3. THE NOISE FLOOR IS LARGE. OB1B-KNEE-1.md section 6 measured two
     BYTE-IDENTICAL runs, lease-k0-code and lease-k0-code-b, at p95 ratios
     1.5047 and 1.7738: 17.9 percent apart. The paged 120b pair's own A/A p95
     spread is 6.1787 percent. Against those floors, the allocator's +1.5841
     pct p95 cost and even the 1.7971x ratio itself carry real uncertainty. The
     bar passes with 10065.4 ms of margin (99239.601004 - 89174.158085), which
     is comfortable relative to the
     noise, but no latency claim finer than "under 2x" should be read out of
     these numbers.

  4. ONE MODEL, ONE CORPUS, ONE K AT 120b SCALE. The 120b row is K=8 on
     AC-PROSE. The K-sweep that produced the 20b knee does not exist at 120b
     scale and was never in this leg's scope.

  5. THE ENGINE SOURCE IS NOT COMMITTED TO THIS REPO. It lives as working-tree
     state in /root/ob5a/llama.cpp on branch ob5a. It is pinned two ways: by
     research/ob5a/alloc.patch, whose sha256
     5a6f636dbd29cf1ee282d5254f60a49688fa7a44d47e14161de6c8ec582837b3 I verified
     for this receipt to byte-match the live `git diff` output exactly, and by
     the phase-C binary digests of section 4. Pinned is not the same as
     committed, and this should be resolved before the fork is relied on
     further (finding F-B3-4).

## 10. DEVIATIONS AND FINDINGS

Carried from the day and night legs, verified here:

  D3 (prereg)   The K=0 guard fix was uncommitted in the sibling ob1b worktree
                and was reproduced in /root/ob5a/llama.cpp rather than the
                sibling being edited. Confirmed: ob1b is still at c087083.
  D4 (prereg)   "~8.10x" superseded by 8.209143. NOW SETTLED BY MEASUREMENT,
                not by argument: the engine measured peak_concurrent at
                1590451200 twice.
  D5 (prereg)   The mprotect cost probe ran at 4 threads under house law, not
                the 8 a run uses, so section 3.4's figure was declared a lower
                bound. Measured +2.340 s against the predicted +1.790 s: above,
                in the declared direction.
  D-B2b-1       The overcommit=1 sighting was NOT a deviation and the knob was
                never touched by the night leg. VERIFIED INDEPENDENTLY here from
                timestamps: the night driver opened at 15:09:03Z and recorded
                "vm.overcommit_memory 1" in its pre-flight, OUTSIDE the lock,
                while the architect's scout (14:48:38Z to 15:19:46Z) held the
                same runlock mid-cycle. Run A waited 569 s for the lock and then
                recorded overcommit_at_run: 0 INSIDE the locked window, as did
                run B, with overcommit_after_run: 0 on both and
                overcommit_final: 0. The scout's own driver reverts to 0 before
                releasing. The two legs never overlapped in the locked window.
                The driver treats a non-zero value as FATAL (exit 77) before the
                model loads, because at 1 the result would be correct and the
                claim worthless.

New findings from this acceptance leg:

  F-B3-1  THE BANKED COST EXPECTATION WAS MISSED BY 46 PERCENT, AND THAT IS THE
          MOST INTERESTING NUMBER IN THIS RECEIPT.
          Prereg section 6.6 banked a predicted lease overhead of 318.586 s for
          this run, derived from the 20b K=0 prose run's own measured
          throughputs. It was explicitly NOT a bar, and it was wrong:

            predicted read     147.325 s     measured  286.711586 s
            predicted verify   145.300 s     measured  154.163691 s
            predicted drop      24.171 s     measured   24.358835 s
            predicted mprotect   1.790 s     measured  +2.340 s (section 7)
            predicted TOTAL    318.586 s     measured  465.234 s
                                             delta    +146.648 s, +46.03 pct

          The whole miss is in READ. Verify came in at 2.356 GB/s against a 20b
          rate of 2.500 GB/s, within 6 percent. Read came in at 1.267 GB/s
          against a 20b rate of 2.465 GB/s, 48.6 percent slower. The cause is
          not the allocator: a 63 GB working set does not fit the page cache, so
          the reads are genuinely colder than a 12 GB model's. The scout,
          running the LANDED engine under the knob with no allocator at all,
          independently measured 1.256 GB/s. Two mechanisms, same cold-read
          rate, so the allocator is exonerated by the control.
          This matters beyond bookkeeping: it says the 20b's lease throughputs
          do not extrapolate to 120b scale, and any future cost model built on
          them will be optimistic by roughly a factor of two on the read term.
          Read plus verify is 62.36 percent of process time.

  F-B3-2  P4d's LITERAL WORDING DOES NOT MATCH ITS OWN INTENT, AND SHOULD BE
          AMENDED IN ANY SUCCESSOR PREREG.
          The bar says "decommits = 6 x lease_events". Measured decommits are
          163920; 6 x 27403 is 164418. The raw counters do not satisfy the
          sentence as written. They reconcile EXACTLY once the slices still live
          at process exit are counted: 163920 + lease_active_slices_at_exit 498
          = 164418. The run ends with leases outstanding, which were therefore
          never dropped, which is correct behaviour and not a leak
          (alloc_commit_live_at_exit is 0). The commit side reconciles the same
          way: 166617 - 1728 resident slices - 164418 = 471 trunk tensors.
          I record this as PASS under the correct accounting and as a defect in
          the bar's text, because a bar that requires a silent correction to
          pass is a bar that will be misread later.

  F-B3-3  The scout receipt's p95 ratios of 1.7692 and 1.7899 recompute to
          1.7691 and 1.7898 against the exact tau_0 of 49619.800502 ms. A
          last-digit rounding difference. Immaterial to every verdict; recorded
          because this receipt claims independent re-derivation and the two
          numbers differ.

  F-B3-4  The allocator source is uncommitted working-tree state (section 9.5).
          Pinned by a digest-verified patch and by binary digests, but not
          committed. Flagged for the architect.

## 11. ARTIFACTS AND DIGESTS

  IN REPO, branch research-2:
    research/OB5A-ALLOC-1-PREREG.md   the prereg that binds every bar here
    research/OB5A-ALLOC-1.md          this receipt
    research/OB5A-SCOUT-1.md          the knob control
    research/ob5a/RUNLOG-1.txt        day leg and night leg, append-only
    research/ob5a/alloc.patch         the engine diff, sha256 5a6f636d...837b3,
                                      verified to byte-match the live tree
    research/ob5a/ANALYZE-ALLOC-1.txt the 20b bar verdicts
    research/ob5a/ANALYZE-120B-1.txt  the 120b bar verdicts
    research/ob5a/NIGHT-120B-1.txt    the night driver trail
    research/ob5a/BUILD-1.txt         the three-phase build verification
    research/ob5a/SHA256SUMS-3.txt    39 files, re-verified 39/39 OK for this receipt

  OFF REPO, per the house law that run evidence stays off the repo:
    /mnt/f/f32/stage/research/ob5a/runs/p3-120b-k8-prose-{a,b}/
    /mnt/f/f32/stage/research/ob5a/runs/{res-prose,res-code,lease-k8-code,lease-k0-prose}/
    /mnt/f/f32/stage/research/ob5a/runs/diag-120b-k8/
    /mnt/f/f32/stage/research/ob5a/runs-scout/sc120-k8-prose-{a,b}/
    /root/ob5a/runs/  (the primary tree; stage is its mirror and agrees exactly)

  THE DECIDING DIGESTS, all re-hashed from raw bytes for this receipt:
    120b identity  9d20bd0365554989051d96b6ad4932625b0a6578002879f8253e6fcc21682019
    120b route     a32d0051bd6d68f2777e64c7b889ae48d56621e9701b107fcef88c0e30cd89c1
    alloc journal  ff7c4b1d851cb57f4243ce9d5251166e6484aec3bca80841c205af30dc308d76
    20b prose      96049ccf8ca241bf58233afe13ed75e2ca43180d81973360d04cebc80d551925
                   4777aa8319f25d6e367f761ef12c7bec81a9ff7896bfed1b8ea0326b5dffc3df
    20b code       9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8
                   f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77
    model          gpt-oss-120b-MXFP4.gguf 582bd40f..., 63387346208 bytes, re-measured
    resident sets  research/ob1b/RESIDENT-SETS-120B-K8.json 8053f18a...
    binary         f9965806c98f5dce6cc7f4f44e52dd57e8d9b51cf27826ad4608db4599e23249

## 12. PROCESS

  GUARDS. pid 654 (openbob serve) and pid 489 (searxng) were confirmed alive
  before and after every run of every leg, and are alive now. Neither was
  touched. The night driver logs guard_pids and guard_pids_final; the scout logs
  guard_pids and guard_pids_after on every cycle. All read 1 openbob, 1 searxng.

  RUNLOCK. Every model run held /mnt/f/f32/stage/research/runlock. The two legs
  queued on it rather than racing: run A of the night leg waited 569 s for the
  scout, the scout waited 97 s once for the night leg. The lock is free now.

  KERNEL. vm.overcommit_memory was 0 inside the locked window on both allocator
  runs and 0 after each; the night leg never set it in either direction. The
  scout set it to 1 and back to 0 within its own lock on each of three cycles.
  The box reads 0 now. The box was never at 1 without the lock held.

  LANE BOUNDARY. Nothing touched the retail lane, the mini, the messenger, the
  demo frame or the 4B serve path. No weights were downloaded. The sealed
  corpus and the LI-S5 route fixture were never read.

  GIT. This receipt is committed on branch research-2 in
  F:\f32\openbob-wt\research-2 only, adding only research/OB5A-ALLOC-1.md.
  No pull, no push, master untouched. THE ARCHITECT MERGES.

  THE STANDARD THIS LEG WAS HELD TO. Every bar was frozen in a prereg committed
  before the engine code existed, and every prediction was banked before any run
  of this leg was made. The numbers that came back could only confirm or refute.
  Fifteen bars confirmed. One banked expectation, explicitly not a bar, was
  refuted by 46 percent, and it is reported here at more length than any of the
  bars that passed.
