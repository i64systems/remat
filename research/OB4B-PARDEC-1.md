# OB4B-PARDEC-1: PARALLEL DECODE IN THE REMATERIALIZING LEASE PATH -- ACCEPTANCE AND RECEIPT

Builder 2 (acceptance) for OB4B-PARDEC-1. Binding documents, in order:
`research/OB4B-PARDEC-1-PREREG.md` (frozen design, bars, run plan --
builder 1) and builder 1's data report (patch + build + runs, this
branch's commits e6bcae0, 9e5e077, b317b77). Parent programs:
`research/OB4-REMAT-1.md` (the accepted rematerializing lease path whose
cost this leg attacks) and `research/LAW-EXPOSURE-1.md` (ACCEPTANCE
form). This document re-derives every load-bearing number from the raw
run artifacts independently (own script, not `analyze_ob4b.py`), states
the limb verdicts, and lands the receipt.

Question this program answers: OB-4 found that 91.57-92.06 pct of
lease-get-bytes wall time was one thread doing zstd decode while ten
compute threads sat parked between graph splits. OB-4b asks: does
decoding the distinct missed experts of a (layer, micro-batch) callback
in parallel, on a fixed 8-worker pool, collapse that decode share and
pull p95 back toward the raw-pread lease path, with identity untouched?
Answer, measured not assumed: **yes**. p95/control drops from 1.7346x
(OB-4, serial decode) to 1.2407x / 1.2396x (OB-4b, 8-way pooled decode),
strictly under the frozen bar of 1.734578198064283, and every byte of
model output and every route decision stays identical to the five
banked OB-4-era runs.

## The one-invariant design

A fixed-size, persistent decode worker pool inside the lease path
(`OB4B_DECODE_THREADS`, default 8, `P=1` reduces to OB-4's own serial
loop and is the unit control arm). On each route callback the main
thread builds the work list of missed `(expert, tensor)` slices in
canonical order; workers pull items off an atomic cursor and each runs
the unchanged `ob1_fetch_slice` body (rematerialize, then mandatory
per-slice sha256 verify, moved into the workers with the decode it
guards). After the pool drains, the main thread does the ordered
bookkeeping (lease_bytes, lease_events, per-layer counters) by walking
the same canonical order it always walked.

**Deterministic result placement by expert id** is the reason identity
does not depend on scheduling: every work item's destination address is
`dst = g_treg[layer,tensor].base + expert * slice_bytes`, a pure function
of the item's own ids, never of completion order, queue position, or
worker id. Distinct items write disjoint byte ranges, so the set of bytes
a callback writes is identical for every possible worker interleaving.
The route log is written by the main thread after the hook returns,
untouched by the pool; every counter a worker touches is a per-worker
accumulator merged after the drain (sums of unsigned integers, order
independent).

## Before/after table

31-chunk (32nd is context-only) p95 over `chunk_ns`, nearest-rank,
`rank = ceil(0.95*31) = 30`. K=8, AC-CODE, ctx 1024, b/ub 1024, 10
compute threads, nice 10. Control: `ob4-res-code`, this engine family's
own K=0 fully resident run, p95 15640.098009 ms (banked, reused by
prereg).

| run | decode pool | p95 ms | p95/control | identity sha256 (8) | route sha256 (8) |
|---|---:|---:|---:|---|---|
| ob4-banked-k8-code-a (OB-4, cited) | 1 (serial) | 27128.973022 | 1.734578198064283 | 9acdf5ef | f0c3f341 |
| ob4-banked-k8-code-b (OB-4, cited) | 1 (serial) | 28637.733919 | 1.831045681588478 | 9acdf5ef | f0c3f341 |
| ob4b-k8-code-a | 8 | 19404.681527 | 1.240700762606072 | 9acdf5ef | f0c3f341 |
| ob4b-k8-code-b | 8 | 19387.119691 | 1.239577890102978 | 9acdf5ef | f0c3f341 |

Decode share of lease-get-bytes wall time (`lease_decode_ns /
lease_read_ns`, raw counters from `ob1-stats.txt`):

| run | lease_decode_ns | lease_read_ns | share |
|---|---:|---:|---:|
| ob4-banked-k8-code-a | 232554046922 | 253968658429 | 0.9156801014760382 |
| ob4-banked-k8-code-b | 239606544579 | 260284609061 | 0.9205559462136544 |
| ob4b-k8-code-a | 374285810724 | 464674300312 | 0.8054799038222907 |
| ob4b-k8-code-b | 359602734793 | 448922621638 | 0.8010350057230456 |

`lease_read_ns` in the pooled runs is a sum of per-worker CPU-ns, not
wall-ns (8 threads decoding concurrently), so this ratio alone does not
show the wall-clock win. The wall-clock quantity that does is the actual
elapsed time the lease phase adds to the process:

| run | lease-phase wall ns | of process wall | elapsed speedup vs OB-4 |
|---|---:|---:|---:|
| ob4-banked-k8-code-a (lr+lv, serial = actual wall) | 347629808362 | 40.463 pct of 859125574377 | -- |
| ob4b-k8-code-a (pool_wall_ns = actual wall) | 74993038234 | 12.085 pct of 620544037498 | 4.635494394523587x |
| ob4-banked-k8-code-b (lr+lv, serial = actual wall) | 356148151959 | 40.850 pct of 871841742794 | -- |
| ob4b-k8-code-b (pool_wall_ns = actual wall) | 72930066992 | 11.869 pct of 614466260060 | 4.883420057711827x |

The "before" figure is `lease_read_ns + lease_verify_ns`: in OB-4's
serial path decode and verify run on the one calling thread, so their
sum IS the wall time the lease phase adds. The "after" figure is
`ob4b_pool_wall_ns`: the actual wall time the pool was busy draining a
callback's work list, read straight from the stats file, not derived. A
separate number, `pool_speedup_vs_serial_equivalent` = 7.68x/7.68x
(`(lease_read_ns+lease_verify_ns)/pool_wall_ns` inside OB-4b itself), is
the pool's own CPU-ns-summed-over-wall-ns slot utilisation figure. It is
reported in `run-analysis.json` and is explicitly NOT the number this
receipt cites as the win: the 4.64x/4.88x figures above, built from two
independently-real wall-clock quantities across the OB-4 to OB-4b
boundary, are.

Cross-program: on OB-1's own banked resident baseline (16073.67024 ms,
`research/ob1/ANALYZE-1.txt` line 18) OB-4b's p95 is 1.2072340191918731x
/ 1.2061414351250248x, against OB-1's own raw-pread lease path at
1.5139x (`research/ob1/RUNLOG-1.txt` line 390, "lease-k8-code p95
24334.4 ms vs 16073.7 ms ratio 1.5139"). Decoding from the 8.2 pct
smaller rematerializing container, with an 8-way decode pool, is now
cheaper than preading the raw uncompressed bytes serially.

Cost paid: peak RSS +88,940,544 B (+1.52 pct) for run a
(5,946,462,208 vs 5,857,521,664 B), consistent for run b
(5,946,564,608 vs 5,857,406,976 B). Store bytes read and lease event
counts (18,100, 222,597,631,923 B total) are identical to OB-4's,
because nothing about what is fetched changed, only how its decode is
scheduled.

## Limb verdicts

**IDENTITY limb (stop-ship): PASS, independently re-hashed.** This
builder computed sha256 directly against the run files on disk (not
through `analyze_ob4b.py`), for both OB-4b full runs and, as a
sanity check, all three cited OB-4-era banked runs:

```
sha256(ob4b-k8-code-a/identity.txt) = 9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8   MATCH
sha256(ob4b-k8-code-a/route.log)    = f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77   MATCH
sha256(ob4b-k8-code-b/identity.txt) = 9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8   MATCH
sha256(ob4b-k8-code-b/route.log)    = f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77   MATCH
sha256(ob4-k8-code-a/identity.txt)  = 9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8   MATCH
sha256(ob4-k8-code-a/route.log)     = f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77   MATCH
sha256(ob4-k8-code-b/identity.txt)  = 9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8   MATCH
sha256(ob4-k8-code-b/route.log)     = f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77   MATCH
sha256(ob4-res-code/identity.txt)   = 9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8   MATCH
sha256(ob4-res-code/route.log)      = f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77   MATCH
```

Six of six runs land in one identity group and one route group. Every
byte the pool touches is bit-for-bit what the serial OB-4 and OB-1
resident paths produced. **UNIT gate re-verified**: `unit-pool1` and
`unit-pool8` (K=8, first 4 chunks, pool 1 vs pool 8) are byte-identical
to each other (`c8049cb5...` identity, `ff192e39...` route, both arms)
and this builder independently confirmed their `route.log` (98,304
lines) is an exact byte prefix of the banked 32-chunk `route.log`
(786,432 lines, `diff -q` clean against the first 98,304 lines of
`ob4-k8-code-a/route.log`).

**DECODE SHARE limb (report only, no threshold by design):** see table
above, re-derived from raw `ob1-stats.txt` counters, not copied from
`run-analysis.json`. `lease_decode_ns/lease_read_ns` falls from
0.9157/0.9206 (serial) to 0.8055/0.8010 (8-way); the wall-clock lease
phase share of process falls from 40.46/40.85 pct to 12.09/11.87 pct.
Both numbers independently reproduce builder 1's report to full float
precision.

**COST limb (the decision): ACCEPT.**

```
ob4b-k8-code-a: p95/control = 1.2407007626060715 < bar 1.734578198064283  -> ACCEPT
ob4b-k8-code-b: p95/control = 1.2395778901029777 < bar 1.734578198064283  -> ACCEPT
```

Both runs clear the frozen bar with margin; the worse of the two
(run a) is the one the ACCEPT is claimed against, per the prereg's own
rule. The parent program's 3.0x governor is cleared by a wide margin as
well (1.24x well under 3.0x).

**BUILD REPRODUCTION limb: re-checked.** `verify-phaseA.log` shows the
rebuild's `.text` section sha256
(`00452ac4ff15060f84d344b6a00f9171237139ee25e44c04ca14428014bda448`)
matching `/root/ob4/llama.cpp`'s `.text` exactly, along with `.rodata`,
`.data`, `.data.rel.ro`, and every other section except three:
`.note.gnu.build-id`, `.dynstr`, `.dynamic`. All three are direct
consequences of `RUNPATH` differing between the two build directories
(`/root/ob4/llama.cpp/build/bin` vs `/root/ob4b/llama.cpp/build/bin`),
confirmed by the log's own RUNPATH readout. The section-level check,
not a whole-file hash, is the correct instrument here and it passes.

**OVERALL VERDICT: operating point ACCEPTED. Identity untouched.**

## Deviations, confirmed as reported

1. **Thread arithmetic above house guidance, as declared in the
   prereg.** 10 compute + up to 7 spawned decode workers = 17 OS
   threads. Declared before the fact with the between-split-wait
   reasoning; not re-litigated here, the identity limb is the check
   that would have caught any resulting corruption and it is clean.
2. **Unit gate false-FAIL, fixed in-branch.** Builder 1's first
   `unit-gate.py` run prefix-compared a 4-chunk `identity.txt` that ends
   in a newline against the 32-chunk banked file and reported FAIL. This
   builder confirms the underlying files ARE consistent (unit runs form
   their own identity/route group, distinct from the 32-chunk reference
   by design, and their route logs are exact 98,304-line prefixes of the
   banked 786,432-line file, verified above). The grader fix is in
   `research/ob4b/unit-gate.py`; the `OB4B_SKIP_EXISTING=1` resume
   switch it forced is in `research/ob4b/runbatch-ob4b.sh` (line 66,
   confirmed present) and is evidenced firing twice in `runbatch.log`
   ("SKIP unit-pool1/unit-pool8: artifacts already present"). The unit
   runs were not re-executed after the grader fix, only re-graded,
   which this builder judges acceptable since the artifacts the fixed
   grader reads are unchanged.
3. **Control reused, not re-run**, per the prereg's preregistered
   decision. Its stated risk (box drift between OB-4's control and this
   leg's runs) is not something the identity limb can catch (it catches
   correctness drift, not performance drift); no anomaly was observed
   in this leg's numbers, so the risk did not materialize, but it
   remains an open assumption of the comparison.

## Limitations

- The COST bar this leg is scored against (1.7346x, OB-4 run a) is
  itself a serial-decode number carried forward from a prior program;
  the comparison is internally consistent (same control, same corpus,
  same flags) but is not a comparison against a from-scratch optimal
  decode schedule.
- `pool_speedup_vs_serial_equivalent` (~7.68x) is reported in
  `run-analysis.json` and cited above only to name it as NOT the claimed
  result: it divides a CPU-ns sum across 8 threads by a wall-ns figure
  and reads as a slot-utilisation number, not an elapsed-time speedup.
  The elapsed speedup this receipt claims (4.64x/4.88x) is built from
  two independently wall-clock-real quantities on either side of the
  OB-4 to OB-4b boundary and is the correct comparison for "how much
  faster did the lease phase get."
- Resident load-time decode (1152 slices) stays serial in this leg and
  is out of scope for `chunk_ns`-based p95, so it does not appear in
  the win; it is a small, fixed, one-time cost (peak RSS and total
  wall clock both still include it).
- Peak RSS grew 1.52 pct. Small and paid once per process, but not
  zero, and not analyzed further here.

## What remains on the table

Decode is now parallel but still sits fully inside the lease
callback's critical path: the route hook blocks on the pool drain
before the compute graph can proceed past that split. The next lever,
named and NOT spent by this leg, is overlapping decode with compute by
prefetching a callback's missed experts ahead of the split that needs
them (the miss set for layer N+1 is knowable once layer N's route
decision is made), which would move decode off the critical path
entirely rather than merely parallelizing it on the path. That is the
natural OB-4c question and is out of scope here.

## Reproduction

```
wsl.exe -u root -e sh -c '/mnt/f/f32/openbob-wt/ob4/research/ob4b/build-ob4b.sh'
wsl.exe -u root -e sh -c '/mnt/f/f32/openbob-wt/ob4/research/ob4b/run-ob4b.sh <RUNNAME> <CORPUS> <K> <CHUNKS> <STORE> <POOL>'
python3 research/ob4b/analyze_ob4b.py   # or re-derive independently as this builder did
```

Independent re-derivation for this receipt used a fresh script (not
`analyze_ob4b.py`) reading `/mnt/f/f32/stage/research/ob4b/runs/*/ob1-stats.txt`
and the banked `/mnt/f/f32/stage/research/ob4/runs/*/ob1-stats.txt`
directly; every figure in the before/after table above reproduced to
full float precision against builder 1's report.

END OB4B-PARDEC-1
