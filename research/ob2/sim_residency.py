#!/usr/bin/env python3
"""OB-2 Stage 1: deterministic residency policy simulator.

Replays a banked route log (research/ob1's frozen format: layer,
token_index, e0, e1, e2, e3; one row per (layer, token) pair, 4 router
picks per row) and, for a frozen policy, tracks the per-layer resident
set over time and counts per-pick misses.

Determinism wall: the resident set for any decision is a pure function
of (a) the route history strictly BEFORE the recompute boundary that
governs that decision, and (b) fixed policy constants. It never depends
on the current token's own routing (that would be non-causal: a live
engine cannot know the future), on timing, on cache state, or on floats.
All counters and comparisons below are plain Python ints; the only
non-integer values in this file are miss RATES printed for humans, which
are never fed back into any policy decision.

Route log loader is copied in spirit from research/ob1/resident_sets.py
load_route_log: builds each layer's token-ordered sequence with a
boolean mask (preserves file order, which is ubatch-ascending) and
verifies token_index comes out exactly 0..budget-1 in order.

Usage:
  sim_residency.py <route_log> <E> <L> <budget> <resident_sets_json> <out_prefix>

Writes <out_prefix>.rows.txt (one line per simulated
policy/corpus/K/variant row, literal miss counts) and
<out_prefix>.churn.txt (per-row resident-set churn).
"""

import sys
import json
import hashlib
import numpy as np


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_route_log(path, E, L, budget):
    data = np.loadtxt(path, delimiter=",", dtype=np.int64)
    expected_rows = L * budget
    if data.shape != (expected_rows, 6):
        raise SystemExit("SHAPE MISMATCH: got %r expected (%d, 6)" % (data.shape, expected_rows))
    layer_col = data[:, 0]
    token_col = data[:, 1]
    expert_ids = data[:, 2:6]

    if int((expert_ids < 0).sum()) != 0 or int((expert_ids >= E).sum()) != 0:
        raise SystemExit("EXPERT ID OUT OF RANGE")

    expected_tok = np.arange(budget)
    ids_by_layer = np.empty((L, budget, 4), dtype=np.int64)
    for l in range(L):
        mask = layer_col == l
        n = int(mask.sum())
        if n != budget:
            raise SystemExit("LAYER %d: got %d rows, expected budget=%d" % (l, n, budget))
        tok_l = token_col[mask]
        if not np.array_equal(tok_l, expected_tok):
            raise SystemExit("ORDER ASSUMPTION VIOLATED: layer %d" % l)
        ids_by_layer[l] = expert_ids[mask]
    return ids_by_layer


def top_k(counts, K, E):
    """counts: list/array of length E. Returns sorted list of K expert ids,
    ranked by (-count, expert_id) i.e. descending count, ties by lower id."""
    order = sorted(range(E), key=lambda e: (-int(counts[e]), e))
    return sorted(order[:K])


# ---------------------------------------------------------------------
# Policies. Each policy is simulated ONE LAYER AT A TIME (independent
# per-layer state), walking token index t = 0..budget-1 in order. At
# each recompute boundary (t a multiple of H, boundary 0 included) the
# policy may change the resident set for the upcoming window, using
# only data strictly before that boundary (or the fixed cold-start rule
# at t=0, since there is no "before" the first token).
# ---------------------------------------------------------------------

def sim_p0_static(ids_layer, K, frozen_set):
    """P0 STATIC-PROSE control: resident set fixed for the whole run,
    taken from RESIDENT-SETS.json (frozen from an external, disjoint
    prose route log). No churn by construction."""
    budget = ids_layer.shape[0]
    resident = set(frozen_set)
    picks = ids_layer.reshape(-1)
    misses = int(np.sum(~np.isin(picks, list(resident))))
    return misses, picks.size, 0  # 0 churn: never recomputed


def sim_p1_sliding(ids_layer, K, E, W_tokens, H):
    """P1 SLIDING-WINDOW: resident = top-K by count over the last
    W_tokens router decisions (this layer), recomputed every H tokens.
    Window and counts are built ONLY from decisions strictly before the
    current boundary. Cold start (t=0): no history -> uniform tie-break
    (lowest K ids)."""
    budget = ids_layer.shape[0]
    misses = 0
    churn = 0
    resident = set(range(K))  # cold-start uniform: ties all equal -> lowest ids
    t = 0
    while t < budget:
        boundary = t
        if boundary == 0:
            new_resident = set(range(K))
        else:
            lo = max(0, boundary - W_tokens)
            window = ids_layer[lo:boundary].reshape(-1)
            counts = np.bincount(window, minlength=E)
            new_resident = set(top_k(counts, K, E))
        if boundary > 0:
            churn += len(resident.symmetric_difference(new_resident))
        resident = new_resident
        hi = min(budget, t + H)
        seg = ids_layer[t:hi].reshape(-1)
        misses += int(np.sum(~np.isin(seg, list(resident))))
        t = hi
    return misses, budget * 4, churn


def sim_p2_decay(ids_layer, K, E, H, add=65536, shift=1):
    """P2 DECAY-COUNTER: integer counters per expert, +65536 per routed
    decision, >>=1 every H tokens (applied at each recompute boundary,
    BEFORE recomputing residency and BEFORE adding the new window's
    counts -- so the decay reflects history strictly before the
    boundary, then residency is read off the decayed counters). Cold
    start: all counters zero -> lowest K ids."""
    budget = ids_layer.shape[0]
    counters = [0] * E
    misses = 0
    churn = 0
    resident = set(range(K))
    t = 0
    first = True
    while t < budget:
        boundary = t
        if boundary > 0:
            # decay strictly-prior state, then recompute residency from it
            counters = [c >> shift for c in counters]
        new_resident = set(top_k(counters, K, E)) if not first else set(range(K))
        if not first:
            churn += len(resident.symmetric_difference(new_resident))
        resident = new_resident
        first = False
        hi = min(budget, t + H)
        seg = ids_layer[t:hi]  # (n,4)
        flat = seg.reshape(-1)
        misses += int(np.sum(~np.isin(flat, list(resident))))
        # accumulate counts for this window (used at the NEXT boundary)
        bc = np.bincount(flat, minlength=E)
        for e in range(E):
            counters[e] += add * int(bc[e])
        t = hi
    return misses, budget * 4, churn


def sim_p3_warmup(ids_layer, K, E, warmup_tokens):
    """P3 WARMUP-FREEZE: uniform (lowest K ids) resident set for the
    first warmup_tokens decisions; count routing during that window;
    at t=warmup_tokens, freeze top-K of that count for the rest of the
    run. One recompute boundary total."""
    budget = ids_layer.shape[0]
    resident = set(range(K))
    warm = min(warmup_tokens, budget)
    seg0 = ids_layer[0:warm].reshape(-1)
    misses = int(np.sum(~np.isin(seg0, list(resident))))
    churn = 0
    if warm < budget:
        counts = np.bincount(seg0, minlength=E)
        new_resident = set(top_k(counts, K, E))
        churn = len(resident.symmetric_difference(new_resident))
        resident = new_resident
        seg1 = ids_layer[warm:budget].reshape(-1)
        misses += int(np.sum(~np.isin(seg1, list(resident))))
    return misses, budget * 4, churn


def main():
    if len(sys.argv) != 7:
        raise SystemExit("usage: sim_residency.py <route_log> <E> <L> <budget> <resident_sets_json> <out_prefix>")
    route_log, E, L, budget, rs_json, out_prefix = sys.argv[1:7]
    E = int(E); L = int(L); budget = int(budget)

    route_sha = sha256_of(route_log)
    ids_by_layer = load_route_log(route_log, E, L, budget)

    with open(rs_json, "r") as f:
        rs = json.load(f)
    rs_sha_expected = rs["source_route_log_sha256"]

    K_VALUES = [16, 8]
    H = 256

    corpus = "code" if "code" in route_log else "prose"

    rows = []  # (policy, corpus, K, variant, total_picks, misses, miss_rate_pct, churn_per_1000tok)

    def emit(policy, K, variant, misses, total_picks, churn):
        rate = 100.0 * misses / total_picks
        churn_per_1000 = 1000.0 * churn / budget
        rows.append((policy, corpus, K, variant, total_picks, misses, rate, churn_per_1000))

    for K in K_VALUES:
        frozen = {l: rs["resident_sets"][str(K)][str(l)] for l in range(L)}
        tot_misses = 0
        tot_picks = 0
        for l in range(L):
            m, p, c = sim_p0_static(ids_by_layer[l], K, frozen[l])
            tot_misses += m
            tot_picks += p
        emit("P0-STATIC-PROSE", K, "-", tot_misses, tot_picks, 0)

        for W in (512, 2048, 8192):
            tot_misses = 0; tot_picks = 0; tot_churn = 0
            for l in range(L):
                m, p, c = sim_p1_sliding(ids_by_layer[l], K, E, W, H)
                tot_misses += m; tot_picks += p; tot_churn += c
            emit("P1-SLIDING-W%d" % W, K, "H=256", tot_misses, tot_picks, tot_churn)

        tot_misses = 0; tot_picks = 0; tot_churn = 0
        for l in range(L):
            m, p, c = sim_p2_decay(ids_by_layer[l], K, E, H)
            tot_misses += m; tot_picks += p; tot_churn += c
        emit("P2-DECAY", K, "H=256,add=65536,shift=1", tot_misses, tot_picks, tot_churn)

        tot_misses = 0; tot_picks = 0; tot_churn = 0
        for l in range(L):
            m, p, c = sim_p3_warmup(ids_by_layer[l], K, E, 2048)
            tot_misses += m; tot_picks += p; tot_churn += c
        emit("P3-WARMUP-FREEZE", K, "warmup=2048", tot_misses, tot_picks, tot_churn)

    with open(out_prefix + ".rows.txt", "w") as f:
        f.write("ROUTE_LOG=%s\n" % route_log)
        f.write("ROUTE_LOG_SHA256=%s\n" % route_sha)
        f.write("RESIDENT_SETS_JSON=%s\n" % rs_json)
        f.write("RESIDENT_SETS_SOURCE_SHA256=%s\n" % rs_sha_expected)
        f.write("%-20s %-6s %2s %-24s %10s %10s %10s %14s\n" % (
            "policy", "corpus", "K", "variant", "total_picks", "misses", "miss_pct", "churn/1000tok"))
        for (policy, corpus_, K, variant, total_picks, misses, rate, churn1000) in rows:
            f.write("%-20s %-6s %2d %-24s %10d %10d %9.4f%% %14.3f\n" % (
                policy, corpus_, K, variant, total_picks, misses, rate, churn1000))

    print("WROTE %s.rows.txt" % out_prefix)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
