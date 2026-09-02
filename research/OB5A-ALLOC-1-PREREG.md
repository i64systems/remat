# OB5A-ALLOC-1-PREREG: THE RESIDENT-PROPORTIONAL ALLOCATOR
# OB-5a builder 1. Written 2026-09-01 on f32-HYDE, before any engine code
# exists and before any model run of this leg is made. Pure ASCII, no em
# dashes. Every number here is either a literal from a committed receipt, a
# literal from a command run for this document, or an arithmetic derivation
# shown in full.

## 0. WHAT THIS DOCUMENT IS, AND WHAT IT BINDS

This is the prereg for track A of OB5-PLAN-1.md: the allocator that makes the
120b leased point startable. It does three things and nothing else.

  1. THE DESIGN STUDY (the owner's margin-0 pattern: design study first). It
     reads the actual allocation path in the fork, names what each candidate
     approach costs FROM THAT CODE rather than from a description of it,
     measures the two things that could kill the leading candidate, and FREEZES
     one approach with its proof obligations.
  2. It settles the 120b K=8 resident sets and shows they re-derive from their
     own named source.
  3. It BANKS every prediction, before any run, so tomorrow's numbers can only
     confirm or refute, never be fitted.

Bars frozen here are frozen. Builder 2 does not start until this file is
committed. The kill lines of OB5-PLAN-1.md section 2.4 apply unchanged and are
restated in section 7.

WHAT THIS DOCUMENT DOES NOT DO. It does not flip a kernel setting. It does not
run a model. It does not touch the retail lane, the mini, the serve, or the
funded low-int lane. It holds no runlock, because it makes no model run: the
four measurements it does make (sections 3.4, 3.5, 3.6) are user-space probes
that allocate at most 564 MB and hold it for seconds. pid 654 (openbob serve)
and pid 489 (searxng) were confirmed alive before and after every one of them.

## 1. THE RULING THIS SERVES

Her words, quoted in OB5-PLAN-1.md section 0:

  "If the whole premise is N >> M, then the runtime should eventually never
  require an allocation proportional to N. That makes the OB-5 allocator more
  than cleanup. It is part of the architecture. The result I'd prioritize now
  is: 120B live exposure with allocation proportional to resident state, not
  total model state."

The blocker, from OB1B-KNEE-1.md section 9, verbatim as the engine printed it:

  0.00.503.908 W common_fit_params: failed to fit params to free device memory:
               was unable to fit model into system memory by reducing context, abort
  0.00.806.033 E ggml_aligned_malloc: insufficient memory (attempted to allocate 60438.47 MB)
  0.00.806.050 E ggml_backend_cpu_buffer_type_alloc_buffer: failed to allocate buffer of size 63374323968
  0.00.806.050 E alloc_tensor_range: failed to allocate CPU buffer of size 63374323968
  0.00.878.238 E llama_model_load: error loading model: unable to allocate CPU buffer
  0.00.878.263 E llama_model_load_from_file_impl: failed to load model
  0.00.878.277 E llama_perplexity: unable to load model

  exit_rc 1   wallclock_s 1.068426206   Maximum resident set size 350856 KB

Section 9's own sentence for it: THE ALLOCATION THAT LEASING EXISTS TO AVOID IS
THE ONE THAT FAILS FIRST.

## 2. THE ALLOCATION PATH AS IT ACTUALLY IS

Read at /root/ob5a/llama.cpp, a fresh worktree of branch ob1b at c087083, with
the K=0 guard fix applied (section 9, deviation D3). Line numbers are that tree.

### 2.1 Why there is exactly one buffer, and why it is the whole model

ggml/src/ggml-alloc.c:1168 ggml_backend_alloc_ctx_tensors_from_buft_impl walks
every tensor in the model context and accumulates cur_buf_size, splitting into a
new buffer only when

    if (cur_buf_size > 0 && (cur_buf_size + this_size) > max_size)

and max_size comes from ggml/src/ggml-backend.cpp:52 ggml_backend_buft_get_max_size:

    // get_max_size is optional, defaults to SIZE_MAX
    if (buft->iface.get_max_size) { return buft->iface.get_max_size(buft); }
    return SIZE_MAX;

The CPU buffer type declares get_max_size as NULL (ggml-backend.cpp:2409), so
max_size is SIZE_MAX, the split condition is never true, and the whole model
context becomes ONE call to alloc_tensor_range with size 63374323968.

### 2.2 What that one call does

ggml/src/ggml-alloc.c:1132, then ggml/src/ggml-backend.cpp:2379:

    static ggml_backend_buffer_t ggml_backend_cpu_buffer_type_alloc_buffer(
            ggml_backend_buffer_type_t buft, size_t size) {
        void * data = ggml_aligned_malloc(size);

and ggml/src/ggml.c:331 ggml_aligned_malloc reaches, on Linux,

    int result = posix_memalign(&aligned_memory, alignment, size);

For a request of this size glibc satisfies posix_memalign with one anonymous
MAP_PRIVATE mapping that is PROT_READ|PROT_WRITE. In the kernel that is an
ACCOUNTABLE mapping, so the heuristic overcommit check runs on it and refuses
it. This box measures /proc/sys/vm/overcommit_memory=0 and
/proc/sys/vm/overcommit_ratio=50 against 24029 MB of RAM and 6144 MB of swap.

### 2.3 What the allocation walk does NOT do

This matters, because it is what makes a reservation safe.

ggml-alloc.c:1148 calls ggml_tallocr_alloc, which (ggml-alloc.c:76) computes an
address and calls ggml_backend_tensor_alloc (ggml-backend.cpp:2066), which sets
tensor->buffer and tensor->data and then calls ggml_backend_buffer_init_tensor.
The CPU buffer interface declares init_tensor as NULL (ggml-backend.cpp:2344,
"no initialization required"). NOTHING IN THE ALLOCATION WALK WRITES A BYTE INTO
THE BUFFER. A buffer that is entirely PROT_NONE survives the whole walk.

ggml_backend_buffer_clear is called on adapter, KV cache, recurrent memory and
output buffers (llama-adapter.cpp:87, llama-kv-cache.cpp:294 and :378,
llama-kv-cache-dsv4.cpp:990 and :1021, llama-memory-recurrent.cpp:123 and :154,
llama-context.cpp:2243). It is NOT called on the model weights buffer allocated
at llama-model.cpp:1747. Verified by grep over src/ and ggml/src/.

### 2.4 How the weights actually get written, which is not through set_tensor

src/llama-model-loader.cpp:1613 onward, the host non-mmap path:

    if (ggml_backend_buffer_is_host(cur->buffer)) {
        if (!ob1_lease_load_tensor(ggml_get_name(cur), cur->data, n_size, (uint64_t) weight->offs)) {
            file->seek(weight->offs, SEEK_SET);
            file->read_raw(cur->data, n_size);
        }

The loader writes into cur->data DIRECTLY. It does not go through
ggml_backend_tensor_set, so a buffer interface's set_tensor hook is NOT a
sufficient place to hang a commit. The commit has to be hung where the write
happens: in the loader, next to the existing lease hook.

### 2.5 What the lease engine does with those bytes

src/ob1-lease.cpp. ob1_lease_load_tensor (line 832) registers the fused expert
tensor's base pointer and per-expert slice, then loads ONLY resident slices:

    for (int e = 0; e < g_E; ++e) {
        if (!g_resident[idx_r(il, e)]) continue;
        ob1_fetch_slice(il, e, t, &g_res_read_ns, &g_res_verify_ns);

ob1_on_route (line 887) leases the distinct routed non-resident experts of the
current micro-batch into g.base + e*g.slice, and ob1_release_active (line 801)
drops the previous layer's leases through ob1_drop (line 790):

    static void ob1_drop(uint8_t * p, size_t n) {
        const uintptr_t pg = (uintptr_t) g_pagesz;
        const uintptr_t a = ((uintptr_t) p + pg - 1) & ~(pg - 1);
        const uintptr_t b = ((uintptr_t) p + n) & ~(pg - 1);
        if (b <= a) return;
        if (madvise((void *) a, (size_t) (b - a), MADV_DONTNEED) != 0) {

Two facts follow, and the whole design study turns on them.

  FACT 1. The set of pages the process ever needs BACKED inside the expert
  region is exactly: the resident slices, plus the current layer's leased
  slices. Everything else is never read and never written. This is not an
  inference; it is measured. OB1B-KNEE-1.md section 6 records
  resident_bytes_loaded=0 at K=0 with output byte-identical to the fully
  resident reference over 32768 tokens on both corpora. All 10178887680 bytes
  of 20b expert weights were absent from memory at load and the answer did not
  change.

  FACT 2. The existing drop rounds INWARD, so a neighbouring resident expert
  sharing an edge page is never clobbered. That rule is already load-bearing and
  is carried into this design unchanged.

## 3. THE DESIGN STUDY

### 3.1 The three candidates, judged against the code above

A. RESERVE/COMMIT. Back the model-weights buffer with a PROT_NONE anonymous
   reservation. Commit pages only for trunk tensors, resident-set slices and
   live lease scratch.
   FOR, from the code: section 2.3 shows the allocation walk writes nothing, so
   a PROT_NONE buffer survives it; section 2.5 FACT 1 shows the engine only ever
   touches a bounded subset; tensor OFFSETS inside the buffer are produced by
   ggml_tallocr from get_alignment and get_alloc_size, which a reserve buffer
   type leaves identical, so the tensor layout is bit-identical and only the
   base pointer value differs; kernels are untouched; the lease code changes by
   two calls.
   AGAINST: the VIRTUAL address reservation is still N bytes. Named as a
   deliberate non-goal in section 4.3, not hidden.

B. PER-EXPERT BUFFERS. Give each expert tensor its own allocation.
   AGAINST, from the code: the expert tensors are FUSED. One tensor
   blk.<il>.ffn_gate_exps.weight holds all E experts contiguously and
   mul_mat_id indexes it by a row stride, which is why ob1_lease_load_tensor
   asserts nbytes % g_E == 0 and writes at g.base + e*g.slice. "Each expert its
   own allocation" would mean splitting a tensor, which requires changing the
   kernel's addressing. The buildable reading of B is one buffer per FUSED
   tensor: L*6 buffers, 216 on the 120b, about 283 MB each. Each individual
   request would then pass the heuristic check, so B WOULD START on this box
   today. But the aggregate model-state request is still 63374323968 bytes; B
   reduces the peak SINGLE allocation and not the TOTAL, which is the opposite
   of what the ruling asks. It also fails outright under vm.overcommit_memory=2.
   And per OB5-PLAN-1 section 2.2 it changes tensor addresses and buffer
   structure, so the identity limb must be re-proven from scratch. Rejected: it
   pays the full identity cost to buy the wrong axis.

C. SPLIT BUFFER TYPES. Trunk in one committed buffer, experts in a lease-owned
   pool.
   AGAINST, from the code: the trunk/expert split would have to be made in
   llama-model.cpp's per-tensor buft selection (make_cpu_buft_list at
   llama-model.cpp:1026 and the buft_list machinery), which is a wider blast
   radius than A for the same outcome, and it splits the weights context into
   two buffers whose relative addresses are no longer fixed by one tallocr walk.
   FOR: the trunk/expert distinction it is built around is real and necessary.

### 3.2 THE CHOICE, FROZEN

  CHOSEN: A, RESERVE/COMMIT, with C's trunk/expert distinction realised at
  COMMIT GRANULARITY inside the single reservation rather than at BUFFER
  granularity. B is rejected.

The one sentence: keep exactly one buffer with exactly the layout it has today,
change what backs it from committed anonymous memory to a PROT_NONE reservation,
and commit the trunk once and the experts on the residency schedule.

### 3.3 The measurement that had to be made first

Approach A rests on one claim: that this box will hold the 63374323968-byte
address range without committing it. That claim was tested at the exact byte
count before anything else was decided. research/ob5a/reserve_probe.c, output at
research/ob5a/RESERVE-PROBE-1.txt, literal:

  == 1. posix_memalign(64, 63374323968), the current path ==
    FAILED rc=12 (ENOMEM)  -- reproduces OB1B-KNEE-1.md section 9

  == 2. mmap PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS ==
    FAILED errno=12 (Cannot allocate memory)  -- an accountable mapping, refused

  == 3. mmap PROT_NONE, MAP_PRIVATE|MAP_ANONYMOUS -- THE RESERVATION ==
    SUCCEEDED at 0x7b9cf8988000
    RSS before 421 pages, after 421 pages, delta 0 pages (0 bytes)
    VmSize 61891684 KB   VmRSS 1684 KB   VmHWM 1684 KB
    address space cost: 63374323968 bytes = 0.0450 pct of a 128 TB user VA space

  == 4. mprotect a resident-sized slab of it to READ|WRITE, and touch it ==
    mprotect(7721553920 bytes -> RW) SUCCEEDED
    VmSize 61891684 KB   VmRSS 1684 KB   VmHWM 1684 KB   (nothing touched yet)
    after touching one byte per page of the first 268435456 bytes:
    VmRSS 263828 KB   VmHWM 263828 KB   (expected roughly 262144 KB more)

The current path fails, an ordinary read-write mapping of the same size fails
for the same reason, and the PROT_NONE reservation succeeds with ZERO resident
pages. A 7721553920-byte slab of it, the size of the predicted K=8 committed
peak, then becomes writable and stays uncommitted until touched. No kernel
setting was changed to get any of that.

The mechanism, stated plainly: the kernel accounts a mapping only when it is
private, anonymous and WRITABLE. A PROT_NONE mapping carries no VM_WRITE, is
therefore not an accountable mapping, and never meets the overcommit check.
mprotect to read-write is where the charge is taken, and it is taken for exactly
the range asked for. That is why the commit axis is the axis this design moves.

### 3.4 THE TRAP THIS STUDY EXISTS TO CATCH

The obvious reading of "reserve/commit" is: commit with mprotect(PROT_READ |
PROT_WRITE), decommit with mprotect(PROT_NONE). THAT DOES NOT DECOMMIT
ANYTHING. mprotect changes access permission; it does not free pages. Measured,
research/ob5a/mprotect_cost.c, 12800 commit-write-drop cycles per arm over a
268.9 MB region at the real slice size of 4406400 bytes. The probe was run
TWICE (MPROTECT-COST-1.txt and MPROTECT-COST-2.txt) because a single timing run
is not a measurement. Both runs, identical to the page:

  == DID IT ACTUALLY DECOMMIT? RSS AFTER 12800 CYCLES OVER A 268.9 MB REGION ==
    arm                                     RSS_pages         RSS_MB       VMAs
    (baseline before any arm)                     422            1.6         29
    A madvise(DONTNEED)                           588            2.3         30
    B mprotect(PROT_NONE)                       69448          271.3        154
    C madvise + mprotect(PROT_NONE)               732            2.9        154
    D mmap(MAP_FIXED, PROT_NONE)                  804            3.1        154
    region size in pages, for scale: 68850 (268.9 MB)

Arm B holds 271.3 MB resident over a 268.9 MB region. It decommitted nothing.
An allocator built that way would pass every page-table audit and fail the RSS
bar completely, and it would have failed it at 3 a.m. on the 120b rather than
here. The same finding shows up a second way in the per-cycle table: arm B's
write costs 246710 ns against arm A's 2093790 ns, because arm B never had to
re-fault and re-zero the pages it claimed to have released. THAT THE TWO RUNS
AGREE ON ALL FOUR RSS FIGURES TO THE PAGE is what makes this a finding rather
than an observation.

Arms C and D both genuinely decommit (2.9 MB and 3.1 MB resident, against arm
A's 2.3 MB baseline behaviour). Their cost, per slice cycle, against arm A, both
runs:

  == SYSCALL OVERHEAD PER SLICE CYCLE, AGAINST ARM A ==   (MPROTECT-COST-1.txt)
    A madvise(DONTNEED)                syscalls  204253.8 ns   delta vs A       +0.0 ns   wall   29.416 s
    B mprotect(PROT_NONE)              syscalls  136998.3 ns   delta vs A   -67255.4 ns   wall    5.029 s
    C madvise + mprotect(PROT_NONE)    syscalls  215140.7 ns   delta vs A   +10887.0 ns   wall   29.658 s
    D mmap(MAP_FIXED, PROT_NONE)       syscalls  215144.8 ns   delta vs A   +10891.0 ns   wall   29.656 s

  == SYSCALL OVERHEAD PER SLICE CYCLE, AGAINST ARM A ==   (MPROTECT-COST-2.txt)
    A madvise(DONTNEED)                syscalls  205653.4 ns   delta vs A       +0.0 ns   wall   29.585 s
    B mprotect(PROT_NONE)              syscalls  131253.8 ns   delta vs A   -74399.6 ns   wall    4.841 s
    C madvise + mprotect(PROT_NONE)    syscalls  207733.2 ns   delta vs A    +2079.8 ns   wall   28.861 s
    D mmap(MAP_FIXED, PROT_NONE)       syscalls  211379.2 ns   delta vs A    +5725.8 ns   wall   29.306 s

  C, projected onto the runs that matter (delta x 6 slices x lease events), at
  the WORSE of the two runs (+10887.0 ns), MPROTECT-COST-1.txt:
    20b lease-k0-prose (banked 916.077 s)              +1.5087 s = +0.1647 pct of wall
    20b lease-k0-code  (banked 923.879 s)              +1.5728 s = +0.1702 pct of wall
    20b lease-k8-code  (OB-1 banked 778.10 s, 10 thr)  +1.1823 s = +0.1520 pct of wall
    120b K=8 predicted (paged ref 410.282 s)           +1.7900 s = +0.4363 pct of wall
  and at the better run (+2079.8 ns), MPROTECT-COST-2.txt: +0.2882 s, +0.3005 s,
  +0.2259 s, +0.3420 s respectively.

FROZEN: the decommit is arm C, madvise(MADV_DONTNEED) inward-rounded followed by
mprotect(PROT_NONE) inward-rounded.

C OVER D IS NOT A COST DECISION AND IS NOT PRESENTED AS ONE. The two arms differ
by 4.0 ns in run 1 and 3646.0 ns in run 2, against a run-to-run spread within
arm C alone of 8807.2 ns. The timing does not separate them and this document
does not pretend it does. C is chosen because it is the SMALLER CHANGE to a path
the identity limb depends on: it keeps ob1_drop's existing madvise call verbatim
and adds one line beside it, where D replaces the drop with a different syscall
that also replaces the VMA. C is never worse than D on cost in either run, so
nothing is being paid for that preference.

CAVEAT DECLARED: this probe ran at 4 threads, the house analysis wall, and a
model run has 8. TLB shootdown cost rises with the number of CPUs the address
space is active on, so every syscall figure above is a LOWER BOUND on the cost
in a run. The margin is wide (0.03 to 0.44 percent of wall across both runs and
all four projections) but it is not infinite, and P3's latency limb is measured
on the run, never inferred from this probe.

### 3.5 The page census, and the edge term nobody gets to round away

Per-expert slices are not page multiples. research/ob5a/commit_census.py, output
at research/ob5a/COMMIT-CENSUS-1.txt, computed from the committed digest
manifests:

  suffix                        slice_B slice%4096    whole_pages page_multiple?
  ffn_gate_exps.weight          4406400       3200           1075             no
  ffn_up_exps.weight            4406400       3200           1075             no
  ffn_down_exps.weight          4406400       3200           1075             no
  ffn_gate_exps.bias              11520       3328              2             no
  ffn_up_exps.bias                11520       3328              2             no
  ffn_down_exps.bias              11520       3328              2             no

Identical on both models. Every internal expert boundary that does not land on a
page boundary makes one page shared between two adjacent experts. Counted over
every possible tensor base residue (ggml guarantees only 64-byte alignment):

  gpt-oss-20b   straddling pages, all L and t:  min 4248   max 4464
                worst-case permanently committed edge bytes  18284544
                as a fraction of the model                   0.1510 pct
  gpt-oss-120b  straddling pages, all L and t:  min 26136   max 27432
                worst-case permanently committed edge bytes  112361472
                as a fraction of the model                   0.1773 pct

THE ROUNDING RULE, FROZEN:

  COMMIT   rounds OUTWARD  [floor(a/P)*P, ceil(b/P)*P)   so a byte the engine
           owns is always backed and a legitimate access never faults.
  DECOMMIT rounds INWARD   [ceil(a/P)*P, floor(b/P)*P)   so a page a neighbour
           still owns is never taken away. This is ob1_drop's existing rule,
           unchanged.

The census is not a new assumption. It is checked against a banked counter. From
/root/ob1b/runs/lease-k0-prose/ob1-stats.txt, literal:

    lease_bytes_read  306108840960
    lease_drop_bytes  305144365056
    lease_events      23096
    undropped gap     964475904
    per slice (6/ev)  6959.9 bytes = 1.699 pages

The census predicts the inward-rounding loss to be one to two partial edge pages
per slice, that is 4096 to 8192 bytes. The already-measured value is 6959.9.
The page model explains a banked counter to within a page, which is what
licenses using it in the P2 bar.

### 3.6 The VMA count, the one cheap way A could have died

An mprotect-based commit splits VMAs. If the count could approach
vm.max_map_count the approach would be dead. Counted from the actual K=8
resident sets (maximal runs of consecutive resident expert ids per layer, one
committed island each, times six suffix tensors, plus the worst-case
simultaneous lease scratch):

  gpt-oss-20b   resident islands 158 x 6 = 948; lease scratch 24 x 6 = 144
                worst-case simultaneous islands 1092, worst-case VMAs 2185
  gpt-oss-120b  resident islands 277 x 6 = 1662; lease scratch 120 x 6 = 720
                worst-case simultaneous islands 2382, worst-case VMAs 4765

  measured /proc/sys/vm/max_map_count on this box: 1048576
  headroom 479.9x (20b), 220.1x (120b)

Independently confirmed by the cost probe, which reached 154 VMAs over 64 slices
against a baseline of 29, consistent with two boundary VMAs per island.

### 3.7 The alternative that is one line and is refused

There is a one-line change that makes the 63374323968-byte allocation succeed:
add MAP_NORESERVE, or equivalently flip vm.overcommit_memory to 1. Named here so
nobody reaches for it later thinking it was overlooked.

It is refused as the ALLOCATOR, on the plan's own words: with overcommit=1 "the
runtime still ASKS for N bytes and the kernel politely lies" (OB5-PLAN-1 section
2.1). MAP_NORESERVE is the same lie taken privately instead of box-wide. It
makes no allocation-side promise, it leaves a routing bug reading silent zeros
out of a dropped page, and mprotect on a VM_NORESERVE mapping is not charged, so
the kernel's own accounting would stop being a witness. The reservation is
therefore taken WITHOUT MAP_NORESERVE, deliberately, so that every commit is a
charge the kernel takes and P2 has a second witness besides the engine's own
counter.

Its legitimate use, offered and not taken by this leg: as a CONTROL that
separates "the buffer is now a reservation" from "the commit discipline is now
enforced". Builder 2 may run it as a diagnostic if P1 fails and the cause is not
immediately localised. It is not a bar and it is not on the critical path.

## 4. THE IMPLEMENTATION SHAPE, FROZEN FOR BUILDER 2

Frozen means: builder 2 may differ, and if it differs it says so as a declared
deviation in the receipt with the reason, before the runs.

### 4.1 Where the reservation is made

A new buffer type in ggml/src/ggml-backend.cpp, ggml_backend_cpu_reserve_buffer_type(),
identical to the CPU buffer type in get_alignment (TENSOR_ALIGNMENT, 64),
get_alloc_size (NULL, so ggml_nbytes), get_max_size (NULL, so SIZE_MAX) and
is_host (true), differing only in:

  alloc_buffer  mmap(NULL, size, PROT_NONE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0)
                explicitly WITHOUT MAP_NORESERVE (section 3.7)
  free_buffer   munmap, because ggml_backend_cpu_buffer_free_buffer calls
                ggml_aligned_free which calls free() and would abort on an
                mmap'd pointer
  clear         fatal; it must never be called on the weights buffer, and
                section 2.3 verifies that it is not
  get_tensor,
  cpy_tensor    fatal on any range not currently committed

Because the four sizing predicates are identical, ggml_backend_alloc_ctx_tensors_from_buft_impl
produces byte-identical tensor OFFSETS. Only the base pointer value differs, and
mmap returns page-aligned memory, so every tensor's alignment is preserved or
improved. That is the identity argument, and P1 is the test of it.

Selected at src/llama-model.cpp:1747 (the weights call
ggml_backend_alloc_ctx_tensors_from_buft(ctx, buft)) by substituting the buft
when the reserve mode is on and buft is the plain CPU buffer type.
ggml_backend_cpu_device_supports_buft (ggml/src/ggml-cpu/ggml-cpu.cpp:482)
returns ggml_backend_buft_is_host(buft) || is_extra, so the scheduler accepts
it.

### 4.2 Where the commits are made

NOT in set_tensor. Section 2.4 shows the host non-mmap loader writes into
cur->data directly with file->read_raw and never calls set_tensor. Therefore:

  src/llama-model-loader.cpp:1616, immediately before the existing lease hook:
      ob1_commit(cur->data, n_size)     for every tensor the lease engine does
                                        not claim, i.e. the trunk. Committed
                                        once, never decommitted.
  src/ob1-lease.cpp ob1_lease_load_tensor: commit each RESIDENT slice, outward
                                        rounded, before ob1_fetch_slice writes
                                        it. Never decommitted.
  src/ob1-lease.cpp ob1_on_route:       commit each leased slice, outward
                                        rounded, before ob1_fetch_slice.
  src/ob1-lease.cpp ob1_drop:           after the existing inward-rounded
                                        madvise(MADV_DONTNEED), add an
                                        inward-rounded mprotect(PROT_NONE) over
                                        the same range. Arm C of section 3.4.

### 4.3 What is deliberately NOT made proportional to resident state

THE VIRTUAL ADDRESS RESERVATION IS N BYTES AND STAYS N BYTES. It is 63374323968
bytes, 0.0450 percent of a 128 TB user address space, measured as VmSize
61891684 KB in section 3.3.

This is forced by the fused tensor layout: mul_mat_id addresses expert e at a
fixed row stride from the tensor base, so the whole [E x slice] range has to be
ADDRESSABLE even when almost none of it is BACKED. Making the VA sub-linear
requires per-expert tensors and a gather, which is approach B, which costs the
identity limb.

It is also the right thing to spend. Address space on this box is 128 TB and
unmetered; commit is 30173 MB and is the thing that failed. The ruling's word
"allocation" is read here as the resource whose exhaustion produced the error in
section 1, and that resource is commit. This reading is declared rather than
assumed, so that if she meant address space too, the answer is B and this
prereg is wrong in a way that is visible rather than buried.

### 4.4 Guards, all fatal under reserve mode

Each of these would touch or lock the whole buffer including uncommitted
ranges. None is used by the frozen configuration. Each becomes a loud fatal
rather than a silent SIGSEGV.

  use_mlock          llama-model.cpp:1754 mlock's the whole buffer
  check_tensors      llama-model-loader.cpp validation walks whole tensors,
                     including non-resident expert slices
  mmap enabled       the lease engine already requires --no-mmap
  repack extra bufts --no-repack (common/arg.cpp:2420, no_extra_bufts) is
                     load-bearing: without it the weights land in a repack buft
                     that converts tensor data at init time
  non-host buffer    ggml_backend_buffer_is_host false

## 5. THE 120b K=8 RESIDENT SETS

FOUND, NOT REBUILT. research/ob1b/RESIDENT-SETS-120B-K8.json is committed at
c8d86e5 (OB-1b builder 1's prereg), sha256
8053f18a70030ad2ac2e59fe220a064ee26f35ad4eb3876bbb7c65f6e994530b.

Verified in the strong sense by research/ob5a/verify_sets_120b.py, output at
research/ob5a/VERIFY-SETS-120B-1.txt: not merely that the file hashes to
something, but that its CONTENT re-derives from the route log it names, by the
ranking rule it names, with the tie-break it names.

  source_route_log         /mnt/f/f32/stage/research/rs053/runs/120b-prose-a/route.log
  source_route_log_sha256  5aa8464d3c71a73648c2323456d656cd40cfcf9dc88b603e1f10da69f9efa129
  measured sha256          5aa8464d3c71a73648c2323456d656cd40cfcf9dc88b603e1f10da69f9efa129  MATCH
  histogram_c_l_e re-derived and compared elementwise: MATCH (36 x 128)
  resident_sets['8'] re-derived for all 36 layers:     MATCH
  resident_expert_pool_bytes = 8 x 36 x 13253760 = 3817082880   MATCH
  VERIFY_SETS_FAILURES=0

The ranking-corpus honesty law holds: the ranking source (5aa8464d...) and the
acceptance route trace (a32d0051...) are different files.

research/ob5a/RESIDENT-SETS-120B.json IS NOT CREATED. The brief says rebuild IF
ABSENT; it is not absent, and a second copy under a new name would split the
lineage for nothing. The night leg points OB1_LEASE at
research/ob1b/RESIDENT-SETS-120B-K8.json.

## 6. PREDICTIONS, BANKED BEFORE ANY RUN

All from research/ob5a/predict_120b.py, output at
research/ob5a/PREDICT-120B-1.txt. The rule is re-implemented for this leg rather
than imported, and is validated before use.

### 6.1 The rule, validated against eight already-measured 20b points

  corpus K      pred_events    meas_events       ev          pred_peak_B          meas_peak_B     peak
  code   4            21115          21115    MATCH            371105280            371105280    MATCH
  code   8            18100          18100    MATCH            318090240            318090240    MATCH
  code   16           12092          12092    MATCH            212060160            212060160    MATCH
  prose  4            20024          20024    MATCH            371105280            371105280    MATCH
  prose  8            16954          16954    MATCH            318090240            318090240    MATCH
  prose  16           10836          10836    MATCH            212060160            212060160    MATCH
  code   0            24078          24078    MATCH            424120320            424120320    MATCH
  prose  0            23096          23096    MATCH            424120320            424120320    MATCH
  EIGHT OF EIGHT REPRODUCED: True

### 6.2 THE 120b K=8 PREDICTION

  route source  /mnt/f/f32/stage/research/ob1b/runs/pag120-prose-a/route.log
  route sha256  a32d0051bd6d68f2777e64c7b889ae48d56621e9701b107fcef88c0e30cd89c1
  sets source   research/ob1b/RESIDENT-SETS-120B-K8.json
  config        E=128 L=36 budget=8192 chunk_tokens=1024 chunks=8

  K     lease_events   peak_experts    peak_concurrent_B  rule (E-K)*per_expert    rule?
  8            27403            120           1590451200             1590451200  MATCHES
  0            29698            128           1696481280             1696481280  MATCHES

  lease_bytes_read predicted for K=8 = 27403 x 13253760 = 363192785280

  per-layer lease_events K=8, the series the engine prints:
    957,918,863,812,811,822,862,837,781,727,666,642,643,656,760,763,706,740,
    749,776,751,715,703,718,740,770,750,762,783,760,784,848,776,726,682,644

### 6.3 THE ACCT EXPOSURE ARITHMETIC, RE-DERIVED

    TOTAL(120b)          = 63387346208     (measured file size)
    L = 36   E = 128   PER_EXPERT = 13253760
    total_expert_bytes   = 36 x 128 x 13253760 = 61073326080
    resident_always      = 63387346208 - 61073326080 = 2314020128  (3.6506 pct)
    CHECK vs OB1B-KNEE-1.md s4 (2314020128): True

    K=8 pool_bytes       = 8 x 36 x 13253760 = 3817082880
    K=8 peak_concurrent  = 1590451200       (PREDICTED in 6.2, not assumed)
    K=8 ACCT             = 2314020128 + 3817082880 + 1590451200 = 7721554208
    K=8 EXPOSURE_acct    = 63387346208 / 7721554208 = 8.209143
    K=8 ACCT as pct of the model                    = 12.1815 pct

    K=0 ACCT (the floor) = 2314020128 + 1696481280 = 4010501408
    K=0 EXPOSURE_acct    = 63387346208 / 4010501408 = 15.805342   (prereg ceiling)
    CHECK vs OB5-PLAN-1 s1 ceiling 15.805342: True

  THE LITERAL PREDICTED EXPOSURE IS 8.209143, NOT 8.10. OB5-PLAN-1 section 1
  carries "~8.10x" beside the ACCT figure 7721554208, and those two are not the
  same point: 8.09795 is what you get from ACCT 7827584288, which uses a peak
  concurrent term of E x per_expert = 1696481280 instead of (E-K) x per_expert
  = 1590451200. The route log settles it. In the worst micro-batch of
  pag120-prose-a all 128 experts of some layer are routed, 8 of them are
  resident, so 120 are concurrently leased. 7721554208 and 8.209143 are the
  consistent pair and are what this leg predicts. The plan's 7721554208 was
  already right; only its "~8.10" was the approximation.

### 6.4 The moonshot slope

  K/E = 6.25 percent on both models (20b K=2 of 32; 120b K=8 of 128).
  gpt-oss-20b   K=2   ACCT     2964472224  EXPOSURE 4.084898   (OB1B measured)
  gpt-oss-120b  K=8   ACCT     7721554208  EXPOSURE 8.209143   (PREDICTED)
  N grows 5.2345x (12109566624 -> 63387346208)
  ACCT grows 2.6047x (2964472224 -> 7721554208)
  exposure ratio at matched resident fraction: 2.0096x

### 6.5 The 20b regression expectation, which is P1's whole content

The four banked digests, byte for byte, verified reachable today by
research/ob5a/verify_inputs.py (VERIFY_INPUTS_FAILURES=0):

  prose identity 96049ccf8ca241bf58233afe13ed75e2ca43180d81973360d04cebc80d551925
  prose route    4777aa8319f25d6e367f761ef12c7bec81a9ff7896bfed1b8ea0326b5dffc3df
  code  identity 9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8
  code  route    f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77

Every one of the four P1 runs must hash to the pair for its corpus. That is a
stronger statement than "matches its own reference", and it is available because
OB-1b already demonstrated that leasing does not change output: lease-k0-prose
hashes to the resident prose pair today.

  run              K     lease_events    peak_concurrent_B       ACCT_bytes
  res-prose        -                0                    0      12109566624
  res-code         -                0                    0      12109566624
  lease-k8-code    8            18100            318090240       4793491104
  lease-k0-prose   0            23096            424120320       2354799264

The two leased rows are simultaneously predictions and banked measurements, so
the counters are a regression too: the allocator must not move them either.

### 6.6 The predicted cost floor of the 120b leased run

Not a bar. A banked expectation so the night leg knows what it is looking at.
Derived from the 20b K=0 prose run's own measured lease throughputs
(/root/ob1b/runs/lease-k0-prose/ob1-stats.txt):

  measured read   306108840960 B / 124.169948910 s = 2465240935 B/s
  measured verify 306108840960 B / 122.462671606 s = 2499609366 B/s
  measured drop   20.372103 s over 23096 events

  120b K=8 predicted read     363192785280 / 2465240935 = 147.325 s
  120b K=8 predicted verify   363192785280 / 2499609366 = 145.300 s
  120b K=8 predicted drop     20.372103 x 27403 / 23096 =  24.171 s
  120b K=8 predicted mprotect 10887 ns x 6 x 27403      =   1.790 s
                              (the worse of the two probe runs, section 3.4)
  120b K=8 predicted lease overhead TOTAL               = 318.586 s
  spread over 8 chunks                                  =  39.823 s per chunk

For scale, the same accounting on the 20b K=0 prose run is 267.005 s, 29.15
percent of its 916.076807 s wall. The 39.776 s per chunk is a FLOOR on the
leased 120b p95, because it is lease work alone with no compute in it.

## 7. THE BARS, FROZEN

### P1  THE 20b IDENTITY REGRESSION, STOP-SHIP

Four runs on gpt-oss-20b with the new allocator, at the frozen configuration
(--ctx-size 1024 --chunks 32 -b 1024 -ub 1024 --threads 8 --threads-batch 8
--no-warmup --seed 1 -ngl 0 --no-mmap --no-repack):

  res-prose       mode=resident, AC-PROSE
  res-code        mode=resident, AC-CODE
  lease-k8-code   mode=lease K=8, AC-CODE, research/ob1/RESIDENT-SETS.json
  lease-k0-prose  mode=lease K=0, AC-PROSE, research/ob1b/RESIDENT-SETS-KNEE.json

PASS requires ALL of:
  P1a identity.txt and route.log of each run hash to the banked pair for its
      corpus (section 6.5), byte for byte
  P1b lease_events and peak_concurrent_lease_bytes of the two leased runs equal
      the banked values of section 6.5 exactly
  P1c the two resident runs report resident_bytes_loaded and lease_events of 0

ANY MISMATCH STOPS THE LEG. The allocator never touches the 120b. The finding is
banked with the mismatching digest quoted verbatim beside the expected one.
There is no retry-until-green.

### P2  THE ALLOCATION BAR, MEASURED NOT ASSERTED

The engine logs, into ob1-stats.txt, from its own counters:

  alloc_va_model_bytes        total virtual bytes reserved for model state
  alloc_commit_peak_single    largest single commit request, bytes
  alloc_commit_model_peak     peak SIMULTANEOUSLY COMMITTED model-state bytes,
                              maintained as a running counter over every commit
                              and decommit
  alloc_commit_total_bytes    cumulative committed bytes over the run
  alloc_commit_calls,
  alloc_decommit_calls        syscall counts
  alloc_vma_peak              peak line count of /proc/self/maps

and, from /proc/self/status at exit: VmHWM, VmRSS, VmSize.

PASS requires ALL of:

  P2a ON THE LEASED RUNS, no model-state COMMIT is a function of total expert
      bytes. alloc_commit_model_peak must equal

          resident_always + K x L x per_expert + peak_concurrent + edge

      where the first three terms are the literal predictions of section 6 and
      edge is bounded by the census of section 3.5. Concretely:

        20b lease-k0-prose  <= 2354799264 + 18284544 = 2373083808
        20b lease-k8-code   <= 4793491104 + 18284544 = 4811775648
        120b K=8 (P3)       <= 7721554208 + 112361472 = 7833915680

      and the 20b figure must be BELOW the model-state request the current
      allocator makes, 12109566624 bytes, which it is by 5.10x at K=0.

  P2b THE 63 GB REQUEST IS GONE. On the 120b run, alloc_commit_peak_single must
      be at most 1 GB and there must be NO allocation request, of any kind, of
      63374323968 bytes. The reservation is reported as
      alloc_va_model_bytes = 63374323968 and is DECLARED, not counted against
      the bar, per section 4.3.

  P2c VmHWM must be within 1.25x of alloc_commit_model_peak plus the compute
      buffers the engine reports at load. A larger gap means the allocator is
      leaking N-proportional state somewhere and section 7's fourth kill line
      applies.

  P2d ON THE RESIDENT CONTROL RUNS, alloc_commit_model_peak is the whole model
      by construction. This is the control, not a bar failure, and the receipt
      must say so where it reports it.

### P3  THE 120b ROW

Fires only after P1 passes. gpt-oss-120b, K=8 of 128, leased, CPU only, at the
frozen 8192-token configuration (--ctx-size 1024 --chunks 8 -b 1024 -ub 1024
--threads 8 --threads-batch 8 --no-warmup --seed 1 -ngl 0 --no-mmap
--no-repack), under the runlock, A/A repeated.

  P3a IDENTITY. identity.txt hashes to
      9d20bd0365554989051d96b6ad4932625b0a6578002879f8253e6fcc21682019 and
      route.log to
      a32d0051bd6d68f2777e64c7b889ae48d56621e9701b107fcef88c0e30cd89c1,
      the banked paged reference pair, on both the A and the B run.
  P3b COUNTERS. lease_events 27403, peak_concurrent_lease_bytes 1590451200,
      lease_bytes_read 363192785280, exactly.
  P3c EXPOSURE. ACCT 7721554208, EXPOSURE_acct 8.209143.
  P3d LATENCY. p95 per chunk <= 2.0x the paged reference. tau_0 on this model is
      the paged pair, because a fully resident baseline is UNMEASURABLE on a
      24029 MB box and is named as such rather than substituted. The bar is set
      on pag120-prose-a, p95 49619.8 ms, so the bar is 99239.6 ms. The A/A
      partner pag120-prose-b measured 46732.3 ms, implying 93464.6 ms; both are
      recorded here so the friendlier one cannot be chosen after the fact. The
      binding number is 99239.6 ms.
  P3e A/A. The two 120b runs must be byte-identical to each other on identity
      and route, and their lease counters identical to the event.

### P4  ALLOCATOR DETERMINISM

The commit and decommit decisions are a pure function of the residency schedule
and the route trace, and are journaled like every other lease decision.

  P4a The engine maintains a rolling sha256 over the record stream
      (op, layer, expert, tensor, page_start, page_end) in issue order, and
      prints it as alloc_journal_sha256 in ob1-stats.txt.
  P4b On every A/A pair in this leg, alloc_journal_sha256 must MATCH.
  P4c Under OB5A_ALLOC_JOURNAL=<path> the full record stream is written, and
      alloc_journal_sha256 must equal the sha256 of that file. This is how P4a
      is prevented from being a rolling hash of nothing.
  P4d alloc_commit_calls and alloc_decommit_calls must match between A/A runs
      exactly, and must equal the values implied by the residency schedule:
      commits = trunk tensors + resident slices + 6 x lease_events, decommits
      = 6 x lease_events.

## 8. KILL LINES (OB5-PLAN-1 section 2.4, restated and made specific)

  - P1 regression mismatch: STOP SHIP. The allocator never touches the 120b.
    Banked as a finding with the mismatching digests verbatim.
  - 120b identity mismatch vs the paged pair: stop, localize. The pain-signal
    law: a pain signal obliges causal localization before any action. Never
    worked around, never retried until green.
  - p95 > 99239.6 ms: the row lands honest as a fail of the latency limb. The
    exposure figure is still reported, with its cost.
  - VmHWM materially above alloc_commit_model_peak plus compute buffers (P2c):
    the allocator leaks N-proportional state somewhere. Find it or report it.
  - A PROT_NONE fault (SIGSEGV) inside the expert region: this is a CORRECTNESS
    FINDING, not a crash to be patched around. It means a kernel read touched an
    expert the residency schedule said was not there, which under the old
    madvise design would have silently read zeros. Localize it, report it, and
    do not widen the commit to make it go away.
  - pid 654 or pid 489 not alive before or after any run: stop the leg.

## 9. DEVIATIONS

D1  THE 120b PREDICTION IS NOT MADE FROM THE RS053 ROUTE LOG. The brief says to
    predict lease_events and peak_concurrent "from the RS053 120b route log".
    That log cannot produce this leg's prediction. Measured, from the two runs'
    own command lines:

      RS053 120b-prose-a:  -f rs053/corpus-prose.txt --ctx-size 4096 --chunks 4
                           -b 4096 -ub 4096 --threads 10 -ngl 99 -ncmoe 36
      this leg's frozen:   -f ob1/AC-PROSE.txt --ctx-size 1024 --chunks 8
                           -b 1024 -ub 1024 --threads 8 -ngl 0 --no-repack

    Different corpus, different micro-batch (4096 vs 1024), different budget
    (16384 vs 8192). Both counters are defined per micro-batch, so a
    4096-token chunking cannot predict a 1024-token run even on the same text.
    The RS053 log's role is unchanged and unmixed: it is the RANKING source that
    produced the resident sets, and section 5 verifies exactly that. The
    counters are predicted from the route trace of the run the 120b row is
    compared against, pag120-prose-a, digest a32d0051..., which is at the frozen
    configuration and is byte-identical to its own A/A repeat. This is also what
    OB-1b did for the 20b: it predicted from the acceptance runs' own resident
    route logs, and hit six of six.

D2  research/ob5a/RESIDENT-SETS-120B.json IS NOT CREATED. Step 2 says rebuild by
    the same lineage IF ABSENT. The file is not absent; it is committed at
    c8d86e5 and section 5 re-derives its content from its own named source.
    A second copy under a new name would split the lineage for nothing.

D3  THE K=0 GUARD FIX WAS UNCOMMITTED IN THE SIBLING WORKTREE. The brief says
    branch ob1b carries it. It does not: ob1b at c087083 still has the
    K <= 0 guard, and the fix lived as an uncommitted working-tree change in
    /root/ob1b/llama.cpp (git diff, 1 insertion 1 deletion). The sibling
    worktree was NOT edited. The one-line change was reproduced in
    /root/ob5a/llama.cpp on branch ob5a:

      -    if (g_K <= 0 || g_K > g_E) ob1_fatal("OB1_K=%d out of range 1..%d", g_K, g_E);
      +    if (g_K <  0 || g_K > g_E) ob1_fatal("OB1_K=%d out of range 0..%d", g_K, g_E);

D4  OB5-PLAN-1's "~8.10x" IS SUPERSEDED BY 8.209143. See section 6.3. The plan's
    ACCT figure 7721554208 stands; only the exposure quoted beside it was an
    approximation computed with peak = E x per_expert instead of
    (E-K) x per_expert. The route log settles the term at 120 experts.

D5  THE COST PROBE RAN AT 4 THREADS, NOT 8. House law caps analysis at 4
    threads; a model run uses 8. TLB shootdown cost rises with the number of
    CPUs the address space is active on, so section 3.4's syscall figures are a
    lower bound on the in-run cost. Declared rather than extrapolated. P3d is
    measured on the run.

D6  NO RUNLOCK WAS HELD BY THIS BUILDER. The runlock law binds model runs. This
    builder made none: four user-space probes and four analysis scripts. Free
    RAM was 22 GB or more throughout and pid 654 and pid 489 were confirmed
    alive before and after each probe.

## 10. ARTIFACTS

  research/OB5A-ALLOC-1-PREREG.md      this file
  research/ob5a/verify_inputs.py       every input digested, prior expectations
                                       named; VERIFY-INPUTS-1.txt
  research/ob5a/predict_120b.py        the rule, validated then applied;
                                       PREDICT-120B-1.txt
  research/ob5a/verify_sets_120b.py    the resident sets re-derived;
                                       VERIFY-SETS-120B-1.txt
  research/ob5a/commit_census.py       the page census and VMA census;
                                       COMMIT-CENSUS-1.txt
  research/ob5a/reserve_probe.c        the reservation, at the exact byte count;
                                       RESERVE-PROBE-1.txt
  research/ob5a/mprotect_cost.c        four decommit primitives, measured
                                       twice; MPROTECT-COST-1.txt and
                                       MPROTECT-COST-2.txt

  fork worktree                        /root/ob5a/llama.cpp, branch ob5a,
                                       based on ob1b at c087083, plus D3
  scratch                              /mnt/f/f32/stage/research/ob5a/

## 11. WHAT BUILDER 2 INHERITS

  1. Approach A is frozen, with C's trunk/expert split at commit granularity.
     B is rejected with reasons from the code.
  2. The decommit primitive is arm C: inward-rounded madvise(MADV_DONTNEED)
     followed by inward-rounded mprotect(PROT_NONE). mprotect alone decommits
     nothing; that trap is measured, not warned about.
  3. The commit rounds outward, the decommit rounds inward, and the inward rule
     is ob1_drop's existing one.
  4. The reservation is taken WITHOUT MAP_NORESERVE, deliberately.
  5. Every bar in section 7 is frozen and every prediction in section 6 is
     banked. Numbers that come back different are findings.
  6. P1 before P3, always. A P1 mismatch ends the leg.
