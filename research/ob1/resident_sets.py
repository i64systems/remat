#!/usr/bin/env python3
# OB-1 stage 1, step 2: static popularity-ranked resident sets.
#
# Reads ONE route log (frozen: the RS053 20b-prose-a run only -- ranks come
# from the PROSE corpus alone, never mixed with code, per the OB-1 task's
# honesty law that ranking and acceptance corpora must differ), computes
# per-layer expert usage counts c_l(e) exactly as RS053 stage 3's M1
# (research/rs053/rs053-metrics.py compute_m1_m2: same file-order mask +
# token_index-monotonic verification, same bincount), then for each K in
# {16,8,4} freezes the top-K experts per layer by usage count, ties broken
# by LOWER EXPERT ID (same tie-break convention RS053 adopted from
# an earlier internal convention, prereg section 5.0/deviation 2).
#
# Usage: resident_sets.py <route_log> <E> <L> <budget> <out_json>

import sys, json, hashlib
import numpy as np


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_route_log(path, E, L, budget):
    # Same loader as research/rs053/rs053-metrics.py load_route_log: the
    # route log is grouped by ubatch, not one contiguous block per layer,
    # so each layer's sequence is built with a boolean mask (preserves
    # file order, which is ubatch-ascending) and verified token_index
    # comes out exactly 0..budget-1 in order before being trusted.
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
    if len(sys.argv) != 6:
        raise SystemExit("usage: resident_sets.py <route_log> <E> <L> <budget> <out_json>")
    route_log, E, L, budget, out_json = sys.argv[1:6]
    E = int(E); L = int(L); budget = int(budget)
    K_VALUES = [16, 8, 4]

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
        per_layer = {}
        for l in range(L):
            counts = hist[l]
            # rank by (-count, expert_id): descending count, ties broken by
            # lower expert id ascending
            order = sorted(range(E), key=lambda e: (-int(counts[e]), e))
            top = sorted(order[:K])  # store ascending by id for readability
            per_layer[str(l)] = top
        resident_sets[str(K)] = per_layer

    PER_EXPERT_BYTES_PER_LAYER = 13253760  # cross-checked vs research/ob1/EXPERT-MANIFEST-20B.sha256 total/(L*E)
    resident_bytes_per_K = {
        str(K): K * L * PER_EXPERT_BYTES_PER_LAYER for K in K_VALUES
    }

    out = {
        "ranking_corpus": "prose (RS053 20b-prose-a route.log ONLY; never mixed with code)",
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
