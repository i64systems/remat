#!/usr/bin/env python3
# OB-3 Stage 1, step 1: task-selected region sets.
#
# Same loader/ranking lineage as research/ob1/resident_sets.py (per-layer
# usage counts c_l(e), top-K by count with ties broken by LOWER expert id),
# but ranked from OB-1's own acceptance route logs (res-code-a / res-prose-a,
# budget=32768) rather than RS053's separate 65536-budget ranking log.
#
# HONESTY SPLIT (stated in the prereg too): these sets rank on the SAME
# corpora the live runs will replay against (res-code-a for SET-CODE, both
# logs for SET-MIX), unlike OB-1's design where the ranking log (RS053
# 20b-prose-a, budget 65536) was disjoint from every acceptance corpus.
# This makes SET-CODE and SET-MIX's own-corpus miss rates an IN-DOMAIN
# UPPER BOUND on what a real deterministic detector+region-lease design
# could achieve, not a held-out generalization measurement. The one
# genuinely held-out row in this leg is the AC-CODE2 transfer probe
# (extract_ac_code2.py), which SET-CODE has never seen at all.
#
# Usage:
#   resident_sets_ob3.py set-code  <code_route_log> <E> <L> <budget> <out_json>
#   resident_sets_ob3.py set-mix   <code_route_log> <prose_route_log> <E> <L> <budget> <out_json>

import sys, json, hashlib
import numpy as np

K_VALUES = [16, 8]
PER_EXPERT_BYTES_PER_LAYER = 13253760


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_route_log(path, E, L, budget):
    # Identical loader/verification to research/ob1/resident_sets.py: the
    # route log is grouped by ubatch (file order is ubatch-ascending, not
    # one contiguous block per layer), so each layer's sequence is built
    # with a boolean mask and verified token_index comes out 0..budget-1
    # in order before being trusted.
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


def histogram(ids_by_layer, E, L, budget):
    total_per_layer = budget * 4
    hist = np.zeros((L, E), dtype=np.int64)
    for l in range(L):
        hist[l] = np.bincount(ids_by_layer[l].reshape(-1), minlength=E)
    row_sums = hist.sum(axis=1)
    if not np.all(row_sums == total_per_layer):
        raise SystemExit("HISTOGRAM SUM MISMATCH")
    return hist


def rank_sets(hist, E, L):
    resident_sets = {}
    for K in K_VALUES:
        per_layer = {}
        for l in range(L):
            counts = hist[l]
            order = sorted(range(E), key=lambda e: (-int(counts[e]), e))
            top = sorted(order[:K])
            per_layer[str(l)] = top
        resident_sets[str(K)] = per_layer
    return resident_sets


def write_out(out_json, ranking_corpus, source_logs, E, L, budget, hist, resident_sets):
    resident_bytes_per_K = {
        str(K): K * L * PER_EXPERT_BYTES_PER_LAYER for K in K_VALUES
    }
    out = {
        "ranking_corpus": ranking_corpus,
        "source_route_logs": source_logs,
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
    print("OUT=%s" % out_json)
    for K in K_VALUES:
        print("K=%d resident_expert_pool_bytes=%d" % (K, resident_bytes_per_K[str(K)]))


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    mode = sys.argv[1]

    if mode == "set-code":
        if len(sys.argv) != 7:
            raise SystemExit("usage: resident_sets_ob3.py set-code <code_route_log> <E> <L> <budget> <out_json>")
        route_log, E, L, budget, out_json = sys.argv[2:7]
        E = int(E); L = int(L); budget = int(budget)
        sha = sha256_of(route_log)
        print("ROUTE_LOG=%s SHA256=%s" % (route_log, sha))
        ids = load_route_log(route_log, E, L, budget)
        hist = histogram(ids, E, L, budget)
        sets = rank_sets(hist, E, L)
        write_out(out_json,
                   "code (res-code-a ONLY; the live run's own corpus -- in-domain upper bound, see file header)",
                   [{"path": route_log, "sha256": sha}],
                   E, L, budget, hist, sets)

    elif mode == "set-mix":
        if len(sys.argv) != 8:
            raise SystemExit("usage: resident_sets_ob3.py set-mix <code_route_log> <prose_route_log> <E> <L> <budget> <out_json>")
        code_log, prose_log, E, L, budget, out_json = sys.argv[2:8]
        E = int(E); L = int(L); budget = int(budget)
        sha_c = sha256_of(code_log)
        sha_p = sha256_of(prose_log)
        print("CODE_ROUTE_LOG=%s SHA256=%s" % (code_log, sha_c))
        print("PROSE_ROUTE_LOG=%s SHA256=%s" % (prose_log, sha_p))
        ids_c = load_route_log(code_log, E, L, budget)
        ids_p = load_route_log(prose_log, E, L, budget)
        hist_c = histogram(ids_c, E, L, budget)
        hist_p = histogram(ids_p, E, L, budget)
        hist = hist_c + hist_p  # concatenated ranking: sum of both corpora's usage counts
        sets = rank_sets(hist, E, L)
        write_out(out_json,
                   "mix (res-code-a + res-prose-a concatenated counts; in-domain upper bound for both)",
                   [{"path": code_log, "sha256": sha_c}, {"path": prose_log, "sha256": sha_p}],
                   E, L, budget, hist, sets)
    else:
        raise SystemExit("unknown mode %r" % mode)


if __name__ == "__main__":
    main()
