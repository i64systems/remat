#!/usr/bin/env python3
# OB-3 Stage 1, step 2: SIM PREDICTIONS.
#
# For a given resident-sets JSON (SET-PROSE from OB-1, or this leg's
# SET-CODE / SET-MIX) and a given banked route log, replay every individual
# router pick against the frozen resident set for its layer and report the
# per-decision miss rate -- same method OB1-EXPOSURE-1.md section 3 used
# (a miss is a pick whose expert id is NOT in that layer's resident set).
#
# total_picks = L * budget * 4 (4 router picks per token per layer).
#
# Usage: sim_predict.py <resident_sets.json> <route_log> <K> [label]
# Prints: label K total_picks misses miss_rate_pct

import sys, json
import numpy as np


def load_route_log(path, E, L, budget):
    data = np.loadtxt(path, delimiter=",", dtype=np.int64)
    expected_rows = L * budget
    if data.shape != (expected_rows, 6):
        raise SystemExit("SHAPE MISMATCH %s: got %r expected (%d, 6)" % (path, data.shape, expected_rows))
    layer_col = data[:, 0]
    token_col = data[:, 1]
    expert_ids = data[:, 2:6]
    if int((expert_ids < 0).sum()) != 0 or int((expert_ids >= E).sum()) != 0:
        raise SystemExit("EXPERT ID OUT OF RANGE in %s" % path)
    expected_tok = np.arange(budget)
    ids_by_layer = np.empty((L, budget, 4), dtype=np.int64)
    for l in range(L):
        mask = layer_col == l
        n = int(mask.sum())
        if n != budget:
            raise SystemExit("%s LAYER %d: got %d rows, expected budget=%d" % (path, l, n, budget))
        tok_l = token_col[mask]
        if not np.array_equal(tok_l, expected_tok):
            raise SystemExit("ORDER ASSUMPTION VIOLATED: %s layer %d" % (path, l))
        ids_by_layer[l] = expert_ids[mask]
    return ids_by_layer


def miss_rate(resident_json_path, route_log_path, K, E=32, L=24, budget=32768):
    with open(resident_json_path) as f:
        rs = json.load(f)
    if rs["E"] != E or rs["L"] != L:
        raise SystemExit("E/L mismatch in %s" % resident_json_path)
    sets_for_K = rs["resident_sets"][str(K)]
    resident_mask = np.zeros((L, E), dtype=bool)
    for l in range(L):
        for e in sets_for_K[str(l)]:
            resident_mask[l, e] = True

    ids_by_layer = load_route_log(route_log_path, E, L, budget)
    total_picks = L * budget * 4
    misses = 0
    for l in range(L):
        picks = ids_by_layer[l].reshape(-1)
        hit = resident_mask[l][picks]
        misses += int((~hit).sum())
    rate = 100.0 * misses / total_picks
    return total_picks, misses, rate


def main():
    if len(sys.argv) < 4:
        raise SystemExit("usage: sim_predict.py <resident_sets.json> <route_log> <K> [label]")
    rs_path, route_log, K = sys.argv[1], sys.argv[2], int(sys.argv[3])
    label = sys.argv[4] if len(sys.argv) > 4 else rs_path
    total, misses, rate = miss_rate(rs_path, route_log, K)
    print("%-30s K=%-3d total_picks=%-10d misses=%-10d miss_rate=%.4f%%" % (
        label, K, total, misses, rate))


if __name__ == "__main__":
    main()
