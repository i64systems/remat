#!/usr/bin/env python3
# OB-1b, step 2: SIM PREDICTIONS -- per-decision miss rate for a
# resident-set size K against an ALREADY-BANKED route log, with no model run.
#
# A DECISION is one entry in the router's top-4 selection for one token at
# one layer: the route log has one row per (layer, token) holding all 4
# chosen expert ids, so one row contributes 4 decisions. A decision MISSES
# when its expert id is not in that layer's resident set for K. This is a
# pure lookup against the already-banked route log; it does not run the
# model and does not touch OB1_LEASE/the lease engine. K=0 is not computed by
# lookup -- an empty resident set misses on every decision by definition, so
# the miss rate is stated as exactly 1.0 (100 pct).
#
# Usage: sim_miss.py <route_log> <E> <L> <budget> <resident_sets.json> <K1,K2,...>

import sys, json
import numpy as np


def load_route_log(path, E, L, budget):
    # Identical loader to research/ob1/resident_sets.py / resident_sets_knee.py.
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


def main():
    if len(sys.argv) != 7:
        raise SystemExit(
            "usage: sim_miss.py <route_log> <E> <L> <budget> <resident_sets.json> <K1,K2,...>"
        )
    route_log, E, L, budget, sets_json, k_list = sys.argv[1:7]
    E = int(E); L = int(L); budget = int(budget)
    K_VALUES = sorted({int(x) for x in k_list.split(",")}, reverse=True)

    ids_by_layer = load_route_log(route_log, E, L, budget)
    total_decisions = L * budget * 4

    with open(sets_json) as f:
        sets_doc = json.load(f)
    resident_sets = sets_doc["resident_sets"]

    print("ROUTE_LOG=%s" % route_log)
    print("E=%d L=%d budget=%d total_decisions=%d" % (E, L, budget, total_decisions))

    results = {}
    for K in K_VALUES:
        if K == 0:
            miss = total_decisions
            print("K=0 miss_decisions=%d total_decisions=%d miss_rate=1.000000 "
                  "(BY DEFINITION: empty resident set, every decision misses)" % (miss, total_decisions))
            results["0"] = {"miss_decisions": miss, "total_decisions": total_decisions, "miss_rate": 1.0}
            continue
        per_layer = resident_sets[str(K)]
        # resident mask per layer: E-length boolean
        miss_total = 0
        for l in range(L):
            resident = np.zeros(E, dtype=bool)
            resident[np.array(per_layer[str(l)], dtype=np.int64)] = True
            sel = ids_by_layer[l]  # (budget, 4)
            hit = resident[sel]
            miss_total += int((~hit).sum())
        rate = miss_total / total_decisions
        print("K=%d miss_decisions=%d total_decisions=%d miss_rate=%.6f" % (K, miss_total, total_decisions, rate))
        results[str(K)] = {"miss_decisions": miss_total, "total_decisions": total_decisions, "miss_rate": rate}

    return results


if __name__ == "__main__":
    main()
