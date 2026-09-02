# OB5A-SCOUT-1: THE OVERCOMMIT SCOUT - THE 120B K=8 LEASED POINT ON
# THE LANDED ENGINE, UNDER THE KERNEL KNOB
# Architect-run 2026-09-01, 14:48:38Z to 15:19:46Z. Authorization:
# THREADS.md owner-orders line (commit d95cbd1: "quiet scout goes out
# tonight" amended to "run the overnight today ... in parallel"), her
# word again at the terminal: "lets get the scout moving again."
# Protocol: research/OB5-PLAN-1.md section 2.1 with the banked
# per-run lock etiquette. Pure ASCII. Every number literal.

## 0. WHAT THIS IS AND IS NOT
This scout measures the 120b K=8 leased point EARLY by letting the
kernel grant the landed engine's N-proportional allocation virtually
(vm.overcommit_memory=1). It does NOT discharge the owner's
resident-proportional ruling: the runtime still asked for
63374323968 bytes and the kernel politely said yes. The
architectural answer is the OB-5a allocator (research/
OB5A-ALLOC-1-PREREG.md; its own 120b row lands with the finish leg
receipt OB5A-ALLOC-1.md). This receipt exists so the regime was
measured twice by two different mechanisms in one day.

## 1. PROTOCOL AS EXECUTED (the sysctl trail, verbatim class)
Three lock cycles (smoke 1 chunk, run-a 8 chunks, run-b 8 chunks),
each: acquire /mnt/f/f32/stage/research/runlock -> record
overcommit_before (0 every cycle) -> sysctl -w vm.overcommit_memory=1
(overcommit_during: 1) -> run with oom_score_adj=1000 on the run
process -> sysctl -w vm.overcommit_memory=0 (overcommit_after: 0)
-> release lock -> 75 s courtesy yield. overcommit_initial 0,
overcommit_final 0. The box was never at overcommit=1 without the
lock held. Guard pids 654 (openbob serve) and 489 (searxng) alive
at start, after every cycle, and at the end. Free RAM 22 GB before
every cycle (bar 6). Lock waits: 97 s, 0 s, 0 s (the OB-5a finish
leg shared the lock politely).

## 2. THE RUNS (landed ob1b binary 1772264971eb456bf..., gpt-oss-
## 120b-MXFP4.gguf 582bd40f..., K=8 of 128 prose-ranked sets
## 8053f18a..., manifest c71ce2ce..., AC-PROSE, 8 threads nice 10)

  run              chunks  exit  wallclock_s     peak RSS KB
  sc120-smoke      1       0     101.378756546   8493152
  sc120-k8-prose-a 8       0     723.465495823   8830932
  sc120-k8-prose-b 8       0     717.464047541   8828004

IDENTITY (stop-ship limb): both 8-chunk runs byte-match the banked
paged reference pair on BOTH artifacts, and each other (A/A MATCH):

  identity  9d20bd0365554989051d96b6ad4932625b0a6578002879f8253e6fcc21682019  (a, b, and the paged pair)
  route     a32d0051bd6d68f2777e64c7b889ae48d56621e9701b107fcef88c0e30cd89c1  (a, b, and the paged pair)

The smoke's 1-chunk identity (59d9369f...) is a different artifact
by construction (1024 tokens, not 8192) and is not compared to the
full reference.

## 3. THE ENGINE'S OWN COUNTERS (identical across a and b on every
## deterministic field)
  resident_slices_loaded        1728
  resident_bytes_loaded         3817082880
  lease_events                  27403
  lease_bytes_read              363192785280
  peak_concurrent_lease_bytes   1590451200   (the prereg-predicted
                                              (E-K) x per_expert
                                              figure, measured)
  route_calls                   288          (36 layers x 8 chunks)
  per_layer_lease_events        identical vector, runs a and b

## 4. EXPOSURE, MEASURED
ACCT (the accounting rule licensed by OB-1/OB-1b, all three terms
now measured on this model):
  63387346208 / (2314020128 + 3817082880 + 1590451200)
  = 63387346208 / 7721554208 = 8.209143
By peak process RSS:
  run a: 63387346208 / 9042874368 = 7.009646
  run b: 63387346208 / 9039876096 = 7.011971
  A/A RSS spread: 0.0332 percent (the ENFORCED-footprint signature
  again; the paged pair's emergent spread was 17.17 percent).

## 5. COST (chunk_ns nearest-rank; 8 chunks yield 7 measured
## intervals, so p95-of-7 IS the maximum sample - stated plainly)
  run a: p50 86424.278105 ms, p95(max) 87783.560543 ms
  run b: p50 86671.396865 ms, p95(max) 88809.922279 ms
  vs the paged pair's p95 (49619.8 / 46732.3 ms):
    a: 1.7692 / 1.8784      b: 1.7899 / 1.9004
  whole-run wall vs the paged pair (410.282 / 390.655 s):
    a: 1.7634 / 1.8519      b: 1.7487 / 1.8365
  per token: 723.465 s / 8192 tokens = 88.3 ms/token, CPU only.
  Effective lease read rate 363192785280 B / 289.192 s = 1.256 GB/s
  (below the 20b legs' ~2.4: a 63 GB working set does not fit the
  page cache; reads are colder). Read+verify = 62.8 percent of
  process time. No latency BAR is claimed here: the frozen 2.0x bar
  belongs to the finish leg's row against the paged tau_0; these
  ratios are reported for the record and sit under 2.0x with a thin
  margin, on a max-of-7 statistic.

## 6. WHAT THE SCOUT SETTLES
1. The ~8.2x regime is REAL on this box: the accounting exposure
   8.209143 is measured (all terms), and identity held byte-exact
   against a reference computed by a completely different memory
   mechanism (mmap paging). Two mechanisms, one output, two days.
2. The leased path's footprint is enforced under the knob too:
   0.0332 percent A/A spread vs paging's 17.17.
3. The knob is not the product: RSS lands at 9.04 GB (7.01x by RSS)
   vs the allocator's smoke commit peak of 7715102720 B - the
   allocator is tighter AND needs no box-wide kernel change. The
   ruling stands: architecture over knob.

## 7. PROCESS
Runs under the runlock, per-run lock cycles with 75 s yields; pids
654/489 never touched, confirmed alive throughout; sysctl restored
to 0 after every cycle and verified 0 at exit; no weights
downloaded; sealed corpus untouched; run bytes off-repo under
/mnt/f/f32/stage/research/ob5a/runs-scout/ and /root/ob5a-scout/
runs/; scripts committed as research/ob5a/run-scout.src.sh and
scout-all.src.sh lineage (stage copies executed after CRLF strip).
Architect-run end to end; no builder tokens spent.
