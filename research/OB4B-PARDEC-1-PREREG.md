# OB4B-PARDEC-1-PREREG: PARALLEL DECODE IN THE REMATERIALIZING LEASE PATH

Builder 1 (patch + runs) for OB4B-PARDEC-1. Preregistered and committed
BEFORE the patch exists. Binding parent documents:
`research/OB4-REMAT-1-PREREG.md` (frozen codec, container format,
verification law) and `research/OB4-REMAT-1.md` (the accepted OB-4
receipt whose main finding this program attacks). Governing law:
`research/LAW-EXPOSURE-1.md`, ACCEPTANCE form.

## The question

OB-4 landed a rematerializing lease path and measured where its cost
lives: **91.57 pct (run a) / 92.06 pct (run b) of lease-get-bytes wall
time is the zstd decode call itself, running on one thread while ten
compute threads sit parked** (`research/ob4/run-analysis.json`,
`lease_decode_share_of_lease_get_bytes`). Decode was never parallelized
because OB-4 changed the byte SOURCE only and inherited OB-1's serial
per-slice loop unchanged.

OB-4b asks exactly one question:

  Does decoding the distinct missed experts of a (layer, micro-batch)
  callback in parallel collapse the decode share of lease-get-bytes time
  and pull p95 back toward the raw-pread path, with identity untouched?

## Inputs, pinned (all literal, none re-derived at run time)

| input | value |
|---|---|
| fork | `/root/rs053/llama.cpp`, branch `ob4`, head `c087083d21e6bd32c1faebc09434a4b54f5d946a` |
| OB-4 engine | UNCOMMITTED working-tree state of worktree `/root/ob4/llama.cpp`; its receipt is `research/ob4/remat-engine.patch` |
| this leg's worktree | `/root/ob4b/llama.cpp`, new branch `ob4b`, based on `c087083`, with `remat-engine.patch` applied as the baseline before any OB-4b edit |
| model | `/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf` sha256 `27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901` |
| container | `/root/ob4/EXPERT-STORE-20B.ob4` sha256 `a5a8fffd46230fb2752945588aa768e4a833c1f7cca985e3ea00f375dbd79314` |
| index | `EXPERT-STORE-20B.ob4.idx` sha256 `72c017badc0d141bdd39357265a12af93f3dc932ed748d2977eb7184dc101480` |
| manifest (identity authority) | `research/ob1/EXPERT-MANIFEST-20B.sha256` sha256 `5e9cf0be34f5a02af41e1b0c0688455604731828e2927e9ec0247d22163e99aa` |
| corpus | `/mnt/f/f32/stage/research/ob1/AC-CODE.txt`, 32 chunks, ctx 1024, b/ub 1024 |
| banked identity reference | `identity.txt` sha256 `9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8` (all 5 OB-4 era runs) |
| banked route reference | `route.log` sha256 `f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77` (all 5 OB-4 era runs) |
| banked resident control | `ob4-res-code`, p95 **15640.098009 ms** (this engine family's own K=0 run, 10 compute threads) |
| bar to beat | OB-4 run a, p95 27128.973022 ms = **1.734578198064283x** that control |

The banked OB-4 control artifacts are SUFFICIENT and are REUSED: the
control is a K=0 fully resident run of the same engine family on the same
corpus with the same flags, and this leg changes nothing that a K=0 run
executes (the pool is only ever entered from the lease callback, which a
K=0 run never takes). No new resident control is run. This is stated here
so the reuse is a preregistered decision, not a later convenience.

## The change, stated before it is written

A **fixed-size decode worker pool** inside the lease path.

1. Pool size `P` is read once from environment `OB4B_DECODE_THREADS`,
   default **8**. `P` counts the calling thread, so the pool spawns `P-1`
   persistent worker threads. `P=1` spawns nothing and is byte-for-byte
   the OB-4 code path (the calling thread walks the same canonical loop
   in the same order); it exists as the control arm of the unit test.
2. Threads are **persistent**, created once on first use and reused for
   every callback thereafter. Per-callback thread creation is rejected
   on purpose: the decoder's `ZSTD_DCtx` and its three scratch buffers
   are `thread_local`, so churning threads would rebuild them 768 times
   per run and measure allocator behaviour instead of decode.
3. On each route callback the main thread builds the work list of every
   `(expert, tensor)` slice that is needed and not resident, in canonical
   order (expert ascending, then tensor suffix ascending). Workers pull
   items off that list by atomic cursor and each runs the UNCHANGED
   `ob1_fetch_slice` body: rematerialize from the container, then
   sha256-verify against the manifest row.
4. **sha256 verification stays per-slice and stays mandatory.** It moves
   INTO the workers with the decode it guards, so verify parallelizes
   too; it is not batched, deferred, sampled, or made optional. A
   mismatch stays fatal.
5. After the pool drains, the main thread performs the ordered
   bookkeeping (`lease_bytes`, `active` lease list, `lease_events`,
   `per_layer_lease_events`, `peak_concurrent_lease_bytes`) by walking
   the same canonical order it always walked, so those series are
   produced in an order no thread can perturb.

### DESIGN INVARIANT (the reason identity cannot depend on scheduling)

**Deterministic result placement by expert id.** Every work item's
destination address is a pure function of `(layer, expert, tensor)`:
`dst = g_treg[layer,tensor].base + expert * slice_bytes`. It is computed
from the item's own ids, never from a completion counter, a queue
position, or a worker id. Distinct items therefore write to disjoint
byte ranges, and the set of bytes written by a callback is identical for
every possible interleaving of the workers. Output ordering cannot depend
on thread completion order because no output location is chosen by
completion order.

Three corollaries this leg holds itself to:

- The route log is written by the main thread after the hook returns,
  untouched by the pool.
- Every counter a worker touches is accumulated into a per-worker
  accumulator and merged after the drain. The merged values are sums of
  unsigned integers, so the merge is order independent.
- Nothing in the decode path reads mutable shared state. The container's
  row table and the manifest are read-only after init; `pread` with an
  explicit offset is thread safe; the zstd context and scratch buffers
  are `thread_local`.

### Explicitly NOT changed

Codec, container, index, manifest, verification law, model, corpus,
flags, thread counts of the compute pool, the resident load path (still
serial), the route log, the stats file's existing keys, and the p95
method. New stats keys are additive only.

## Run plan

All model runs hold the box-wide RUNLOCK
(`/mnt/f/f32/stage/research/runlock`, mkdir acquire, sleep-30 loop,
report after 120 min, rmdir immediately after the batch), require >= 6 GB
free RAM before starting, and run at `nice -n 10`.

**Build check (no runlock, no model).** Rebuild the OB-4 baseline
unpatched in the new worktree and prove the rebuild reproduces the
`ob4` engine's `.text` byte for byte before trusting the patched build,
using the OB-1b object-reuse verification pattern
(`research/ob1b/build-ob1b.sh`).

**Unit (runlock, short).** K=8 AC-CODE, first 4096 tokens (4 chunks),
same flags as the full runs, two arms:

| arm | `OB4B_DECODE_THREADS` |
|---|---|
| `unit-pool1` | 1 |
| `unit-pool8` | 8 |

Pass condition: `identity.txt` and `route.log` of the two arms are byte
identical to each other AND to the corresponding 4-chunk prefix of the
banked OB-4 artifacts. A unit failure stops the leg before any full run.

**Full runs (runlock).** Per the parent prereg's run plan shape, one run
plus its A/A repeat:

| run | K | corpus | chunks | store | pool |
|---|---|---|---|---|---|
| `ob4b-k8-code-a` | 8 | AC-CODE | 32 | C2 container | 8 |
| `ob4b-k8-code-b` | 8 | AC-CODE | 32 | C2 container | 8 |

Recorded per run, literal: identity digest, route digest, p95 (nearest
rank over the run's own `chunk_ns` series, `rank = ceil(0.95*n)`, the
method OB-1 validated and OB-4 reused), decode share of lease-get-bytes,
wall clock, peak RSS, store bytes read.

## FROZEN: bars

**IDENTITY limb (stop-ship).** ACCEPTANCE form, `assert(candidate.digest
== reference.digest)`:

```
sha256(identity.txt) == 9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8
sha256(route.log)    == f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77
```

for every full run of this leg. Any single byte of divergence stops the
leg: the operating point is not reported as a candidate, it is reported
as a defect, and no latency number from a diverging run is quoted as a
result.

**DECODE SHARE limb (report only, no threshold).** Report
`lease_decode_ns / lease_read_ns` before (OB-4: 0.9156801014760382 /
0.9205559462136544) and after. There is no pass/fail on this number by
design; it is the mechanism readout that explains whatever the p95 limb
does.

**COST limb (the decision).** With `tau_pool8` the p95 of a full OB-4b
run and `tau_0 = 15640.098009 ms` the banked `ob4-res-code` control:

```
ACCEPT the operating point  iff  tau_pool8 / tau_0  <  1.734578198064283
REJECT otherwise
```

Strictly less than OB-4's own run a ratio. Both full runs are reported;
the ACCEPT verdict is claimed only if the worse of the two clears it, and
if the two disagree across the line that is reported as the finding
rather than resolved by picking the friendlier run. The parent program's
3.0x governor still stands above this and is reported alongside, but this
leg's bar is the tighter one: beating OB-4, not merely surviving the
governor.

## Declared deviations and risks, before the fact

1. **Thread arithmetic exceeds the house 16-total guidance.** The
   compute pool stays at 10 threads because the control this leg is
   scored against ran at 10 and changing it would void the comparison;
   the decode pool is 8 as briefed. That is 10 + 7 spawned = 17 OS
   threads on a 24-logical-CPU box (AMD Ryzen 9 5900X, 12 cores / 24
   threads). Mitigation and reasoning: the route hook is a
   `ggml_backend_sched` eval callback, so it runs between graph splits
   with the CPU backend's compute call already returned; the compute
   threads are at their between-split wait for the whole window in which
   the decode pool is active, so runnable threads stay near 8, not 18.
   The box holds the exclusive RUNLOCK for the duration. Declared here
   rather than discovered later.
2. **The A/A repeat is a repeat of the same binary and pool size**, not
   a pool-size sweep. No sweep over `OB4B_DECODE_THREADS` is
   preregistered; if one is run opportunistically it is reported as
   exploratory and cannot move the ACCEPT/REJECT verdict.
3. **Resident load path stays serial.** Load-time decode of the 1152
   resident slices is not parallelized in this leg. It costs wall time
   but contributes nothing to `chunk_ns`, which is what p95 is computed
   over, so it is out of scope for the question asked. Named so the wall
   clock figures are read correctly.
4. **The control is reused, not re-run.** Stated above as a
   preregistered decision. Its risk is that box conditions drifted
   between OB-4's control and this leg's runs; the identity limb catches
   correctness drift but not performance drift, so any anomalous result
   will be reported with that caveat attached rather than explained away.

## Reproduction

```
wsl.exe -u root -e sh -c '/mnt/f/f32/openbob-wt/ob4/research/ob4b/build-ob4b.sh'
wsl.exe -u root -e sh -c '/mnt/f/f32/openbob-wt/ob4/research/ob4b/run-ob4b.sh <RUNNAME> <CORPUS> <K> <CHUNKS> <STORE> <POOL>'
```

END OB4B-PARDEC-1-PREREG
