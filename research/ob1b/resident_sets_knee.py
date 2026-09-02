#!/usr/bin/env python3
# OB-1b, step 1: static popularity-ranked resident sets, extended
# past OB-1's K in {16,8,4} to the knee-hunting points K in {2,1,0}.
#
# This is the SAME lineage as research/ob1/resident_sets.py: same route-log
# loader (file-order boolean mask per layer, token_index-monotonic
# verification, same bincount), same ranking rule (top-K by per-layer usage
# count, ties broken by LOWER EXPERT ID), same ranking-corpus honesty law
# (ranks come from ONE route log, passed as an argument -- never mixed with
# an acceptance corpus). The only extension is that K_VALUES is a CLI
# argument instead of the frozen [16, 8, 4] list, so it can express K=2, K=1
# and the K=0 pure-streaming point (an empty set per layer, by definition --
# no ranking computation is needed to know K=0 is empty, but the histogram is
# still computed and reported for continuity with the OB-1 artifact shape).
#
# Usage: resident_sets_knee.py <route_log> <E> <L> <budget> <out_json> <K1,K2,...> <per_expert_bytes_per_layer>

import sys, json, hashlib
import numpy as np


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_route_log(path, E, L, budget):
    # Identical to research/ob1/resident_sets.py load_route_log.
    data = np.loadtxt(path, delimiter=",", dtype=np.int64)
    expected_rows = L * budget
    if data.shape != (expected_rows, 6):
        raise SystemExit("SHAPE MISMATCH: got %r expected (%d, 6)" % (data.shape, expected_rows))
    layer_col = data[:, 0]
    token_col = data[:, 1]
    expert_ids = data[:, 2:6]  # k=4 columns

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


def main():
    if len(sys.argv) != 8:
        raise SystemExit(
            "usage: resident_sets_knee.py <route_log> <E> <L> <budget> <out_json> "
            "<K1,K2,...> <per_expert_bytes_per_layer>"
        )
    route_log, E, L, budget, out_json, k_list, per_expert = sys.argv[1:8]
    E = int(E); L = int(L); budget = int(budget)
    K_VALUES = sorted({int(x) for x in k_list.split(",")}, reverse=True)
    PER_EXPERT_BYTES_PER_LAYER = int(per_expert)

    route_log_sha256 = sha256_of(route_log)
    ids_by_layer = load_route_log(route_log, E, L, budget)

    total_per_layer = budget * 4
    hist = np.zeros((L, E), dtype=np.int64)
    for l in range(L):
        hist[l] = np.bincount(ids_by_layer[l].reshape(-1), minlength=E)
    row_sums = hist.sum(axis=1)
    if not np.all(row_sums == total_per_layer):
        raise SystemExit("HISTOGRAM SUM MISMATCH")

    resident_sets = {}
    for K in K_VALUES:
        if K == 0:
            # K=0: the pure-streaming point. Empty resident set per layer, by
            # definition -- no ranking is needed, every routed expert is
            # leased through the scratch path every time.
            per_layer = {str(l): [] for l in range(L)}
            resident_sets[str(K)] = per_layer
            continue
        if K < 0 or K > E:
            raise SystemExit("K=%d out of range 0..%d" % (K, E))
        per_layer = {}
        for l in range(L):
            counts = hist[l]
            order = sorted(range(E), key=lambda e: (-int(counts[e]), e))
            top = sorted(order[:K])
            per_layer[str(l)] = top
        resident_sets[str(K)] = per_layer

    resident_bytes_per_K = {
        str(K): K * L * PER_EXPERT_BYTES_PER_LAYER for K in K_VALUES
    }

    out = {
        "lineage": "research/ob1/resident_sets.py (same loader, same ranking rule, same tie-break)",
        "ranking_corpus": "prose (frozen at the source_route_log below; never mixed with an acceptance corpus)",
        "source_route_log": route_log,
        "source_route_log_sha256": route_log_sha256,
        "E": E,
        "L": L,
        "budget": budget,
        "tie_break": "lower expert id",
        "K_values": K_VALUES,
        "per_expert_bytes_per_layer": PER_EXPERT_BYTES_PER_LAYER,
        "resident_expert_pool_bytes_per_K": resident_bytes_per_K,
        "histogram_c_l_e": hist.astype(int).tolist(),
        "resident_sets": resident_sets,
    }
    with open(out_json, "w") as f:
        json.dump(out, f, sort_keys=True, indent=1)
        f.write("\n")

    print("ROUTE_LOG=%s SHA256=%s" % (route_log, route_log_sha256))
    print("E=%d L=%d budget=%d" % (E, L, budget))
    for K in K_VALUES:
        print("K=%d resident_expert_pool_bytes=%d" % (K, resident_bytes_per_K[str(K)]))
    print("OUT=%s" % out_json)


if __name__ == "__main__":
    main()
