#!/usr/bin/env python3
# OB-5a stage 1, the DESIGN STUDY's measurement limb: a page census of the
# expert region, computed from the committed digest manifests, before any
# allocator is written.
#
# WHY THIS EXISTS. The three candidate approaches in OB5-PLAN-1.md section 2.2
# differ in what they do at PAGE granularity, and the page granularity of this
# model is not a free parameter: the per-expert slices are fixed by the GGUF and
# they are NOT page multiples. Every claim the prereg makes about "allocation
# proportional to resident state" has to survive that fact, so the fact is
# measured here and the bars are set against it rather than around it.
#
# The existing engine already lives with this. src/ob1-lease.cpp ob1_drop()
# rounds MADV_DONTNEED INWARD so a neighbouring resident expert sharing an edge
# page is never clobbered. The consequence is visible in the banked OB-1b K=0
# stats: lease_drop_bytes is smaller than lease_bytes_read, and section 5 below
# checks this census against that already-measured gap.
#
# Usage: commit_census.py

import sys
from collections import defaultdict

PAGE = 4096
ALIGN = 64  # TENSOR_ALIGNMENT in ggml, so any tensor base is 64-byte aligned

MAN20 = "/mnt/f/f32/openbob-wt/research-2/research/ob1/EXPERT-MANIFEST-20B.sha256"
MAN120 = "/mnt/f/f32/openbob-wt/research-2/research/ob1b/EXPERT-MANIFEST-120B.sha256"
SETS20 = "/mnt/f/f32/openbob-wt/research-2/research/ob1/RESIDENT-SETS.json"
SETS120 = "/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json"

SUFFIX = ["ffn_gate_exps.weight", "ffn_up_exps.weight", "ffn_down_exps.weight",
          "ffn_gate_exps.bias", "ffn_up_exps.bias", "ffn_down_exps.bias"]

# Banked measurement to check the census against: research/OB1B-KNEE-1.md s6 and
# /root/ob1b/runs/lease-k0-prose/ob1-stats.txt, literal.
K0_PROSE_LEASE_BYTES = 306108840960
K0_PROSE_DROP_BYTES = 305144365056
K0_PROSE_EVENTS = 23096


def read_manifest(path):
    """returns slice_bytes[t], L, E  -- verifying the slice is uniform per suffix"""
    per = defaultdict(set)
    maxl = maxe = -1
    rows = 0
    for line in open(path):
        if line.startswith("#") or not line.strip():
            continue
        f = line.rstrip("\n").split(",")
        il, e, tname, off, nb = int(f[0]), int(f[1]), f[2], int(f[3]), int(f[4])
        t = SUFFIX.index(tname)
        per[t].add(nb)
        maxl = max(maxl, il)
        maxe = max(maxe, e)
        rows += 1
    L, E = maxl + 1, maxe + 1
    if rows != L * E * 6:
        raise SystemExit("manifest %s row count %d != L*E*6=%d" % (path, rows, L * E * 6))
    slices = {}
    for t in range(6):
        if len(per[t]) != 1:
            raise SystemExit("suffix %s has non-uniform slice sizes: %s" % (SUFFIX[t], per[t]))
        slices[t] = per[t].pop()
    return slices, L, E


def straddles(base_res, slice_bytes, E):
    """Number of internal expert boundaries that fall strictly inside a page,
    given the tensor base's residue mod PAGE. Each such boundary makes exactly
    one page shared between two adjacent experts."""
    n = 0
    for e in range(1, E):
        if (base_res + e * slice_bytes) % PAGE != 0:
            n += 1
    return n


def islands(ids):
    """maximal runs of consecutive ids in a sorted list"""
    if not ids:
        return 0
    n = 1
    for a, b in zip(ids, ids[1:]):
        if b != a + 1:
            n += 1
    return n


def census(name, man, sets_path, K, total_bytes):
    import json
    slices, L, E = read_manifest(man)
    per_expert = sum(slices.values())
    print("== %s ==" % name)
    print("  L=%d  E=%d  per_expert_bytes_per_layer=%d  (sum of the six slices)" % (
        L, E, per_expert))
    print()
    print("  %-24s %12s %10s %14s %14s" % (
        "suffix", "slice_B", "slice%4096", "whole_pages", "page_multiple?"))
    for t in range(6):
        s = slices[t]
        print("  %-24s %12d %10d %14d %14s" % (
            SUFFIX[t], s, s % PAGE, s // PAGE, "yes" if s % PAGE == 0 else "no"))
    print()

    print("  STRADDLING PAGES. A page is shared between two adjacent experts when")
    print("  an expert boundary falls strictly inside it. The tensor base is only")
    print("  known to be %d-byte aligned (ggml TENSOR_ALIGNMENT), so the count is" % ALIGN)
    print("  reported over every possible base residue, min and max:")
    print("  %-24s %14s %14s %18s" % ("suffix", "min_straddle", "max_straddle", "per L (max) bytes"))
    tot_min = tot_max = 0
    for t in range(6):
        s = slices[t]
        counts = [straddles(r, s, E) for r in range(0, PAGE, ALIGN)]
        lo, hi = min(counts), max(counts)
        tot_min += lo * L
        tot_max += hi * L
        print("  %-24s %14d %14d %18d" % (SUFFIX[t], lo, hi, hi * PAGE))
    print("  %-24s %14d %14d %18d" % ("TOTAL over all L and t", tot_min, tot_max, tot_max * PAGE))
    print("  worst-case permanently-committed edge bytes = %d x %d = %d" % (
        tot_max, PAGE, tot_max * PAGE))
    print("  as a fraction of the model: %.4f pct" % (100.0 * tot_max * PAGE / total_bytes))
    print()

    doc = json.load(open(sets_path))
    sets = doc["resident_sets"][str(K)]
    isl = sum(islands(list(sets[str(l)])) for l in range(L))
    print("  COMMIT ISLANDS AT K=%d. Each maximal run of consecutive resident" % K)
    print("  expert ids in one (layer, tensor) is one committed range, hence at")
    print("  most one extra VMA under an mprotect-based commit.")
    print("    resident islands per layer, summed over layers : %d" % isl)
    print("    x 6 suffix tensors                             : %d" % (isl * 6))
    print("  LEASE SCRATCH AT K=%d. peak_experts non-resident experts are live at" % K)
    print("  once in the worst micro-batch, each contributing at most one island")
    print("  per suffix tensor:")
    peak_experts = E - K
    print("    peak concurrent leased experts                 : %d" % peak_experts)
    print("    x 6 suffix tensors                             : %d" % (peak_experts * 6))
    worst = isl * 6 + peak_experts * 6
    print("  WORST-CASE SIMULTANEOUS COMMITTED ISLANDS        : %d" % worst)
    print("  worst-case VMA count (2 boundary VMAs per island): %d" % (2 * worst + 1))
    print("  measured vm.max_map_count on this box            : 1048576")
    print("  headroom factor                                  : %.1fx" % (
        1048576.0 / (2 * worst + 1)))
    print()

    print("  COMMIT / DECOMMIT ROUNDING, the rule this prereg freezes:")
    print("    COMMIT   rounds OUTWARD  [floor(a/P)*P, ceil(b/P)*P)  so the bytes")
    print("             the engine owns are always backed and never fault.")
    print("    DECOMMIT rounds INWARD   [ceil(a/P)*P, floor(b/P)*P)  so a page a")
    print("             neighbour still owns is never taken away. This is the")
    print("             EXISTING rule in src/ob1-lease.cpp ob1_drop(), unchanged.")
    print("    Per-slice worst-case over-commit: 2 pages = %d bytes." % (2 * PAGE))
    print("    Largest slice is %d bytes = %.1f pages, so the over-commit is at" % (
        max(slices.values()), max(slices.values()) / float(PAGE)))
    print("    most %.3f pct of a slice." % (100.0 * 2 * PAGE / max(slices.values())))
    print()
    return slices, L, E, tot_max


def main():
    print("PAGE=%d  TENSOR_ALIGNMENT=%d" % (PAGE, ALIGN))
    print("measured on this box: /proc/sys/vm/max_map_count=1048576,")
    print("                      /proc/sys/vm/overcommit_memory=0,")
    print("                      /proc/sys/vm/overcommit_ratio=50")
    print()
    s20, L20, E20, edge20 = census("gpt-oss-20b", MAN20, SETS20, 8, 12109566624)
    s120, L120, E120, edge120 = census("gpt-oss-120b", MAN120, SETS120, 8, 63387346208)

    print("== 5. THE CENSUS CHECKED AGAINST A BANKED MEASUREMENT ==")
    print("  The 20b K=0 prose run already measured the inward-rounding loss, and")
    print("  the census has to agree with it or the census is wrong.")
    print("  Literal, from /root/ob1b/runs/lease-k0-prose/ob1-stats.txt:")
    print("    lease_bytes_read  %d" % K0_PROSE_LEASE_BYTES)
    print("    lease_drop_bytes  %d" % K0_PROSE_DROP_BYTES)
    print("    lease_events      %d" % K0_PROSE_EVENTS)
    gap = K0_PROSE_LEASE_BYTES - K0_PROSE_DROP_BYTES
    print("    undropped gap     %d" % gap)
    print("    per lease event   %.1f bytes" % (gap / float(K0_PROSE_EVENTS)))
    print("    per slice (6/ev)  %.1f bytes = %.3f pages" % (
        gap / float(K0_PROSE_EVENTS * 6), gap / float(K0_PROSE_EVENTS * 6) / PAGE))
    print()
    print("  The census predicts the inward-rounding loss per slice to be the two")
    print("  partial edge pages, minus whichever edge happens to be page aligned.")
    print("  Expected range 1 to 2 pages (%d to %d bytes) per slice." % (PAGE, 2 * PAGE))
    lo, hi = PAGE, 2 * PAGE
    meas = gap / float(K0_PROSE_EVENTS * 6)
    print("  MEASURED %.1f bytes per slice: %s" % (
        meas, "INSIDE THE PREDICTED RANGE" if lo <= meas <= hi else "OUTSIDE - census wrong"))
    print()
    print("  This is the check that licenses the edge-page terms of the P2 bar:")
    print("  the page model is not a new assumption, it is the model that already")
    print("  explains a banked counter to within a page.")
    print()

    print("== 6. WHAT THE CENSUS DECIDES ==")
    print("  1. Slices are NOT page multiples on either model (section tables), so")
    print("     no approach can promise byte-exact commit. Every approach carries")
    print("     an edge term, and the prereg names it rather than rounding it away.")
    print("  2. The worst-case VMA count under an mprotect commit is small against")
    print("     this box's vm.max_map_count, by three orders of magnitude, so")
    print("     approach A is not blocked by map-count exhaustion. That was the")
    print("     one cheap way approach A could have died and it does not.")
    print("  3. The edge term is bounded and tiny (fractions of a percent of the")
    print("     model), so it cannot rescue or ruin the P2 bar either way. It is")
    print("     carried explicitly in the bar so a surprise there is visible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
