#!/usr/bin/env python3
# RS053-GPTOSS-LOCALITY-1 : Stage 3 (stats + receipt)
# Computes M1, M2, M3, M4, M6 for ONE route log, per the frozen definitions
# in research/RS053-GPTOSS-LOCALITY-1-PREREG.md section 5. Pure stdlib +
# numpy. Deterministic: no parallel reductions, no dict iteration order
# dependence (json.dumps sort_keys=True), no wall-clock or PID in output.
#
# Usage:
#   rs053-metrics.py <route_log> <E> <L> <budget> <label> <out_json>
#
# Writes <out_json>. Also prints a short literal summary to stdout.

import sys, os, json, hashlib
import numpy as np

PER_EXPERT_BYTES_PER_LAYER = 13253760  # RUNLOG-1.txt section 5, both models
WINDOW_SIZES = [64, 512, 4096]
COLLAPSE_PHALF_THRESHOLD = 0.95   # named convention, see report section "M1 collapse rule"
DEAD_FRACTION_THRESHOLD = 0.01    # frozen in prereg (E-independent)
TOP_N_FOR_M5 = 32                 # frozen in prereg 5.5


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_route_log(path, E, L, budget):
    # NOTE ON FILE ORDER: the route log is NOT one contiguous block per layer.
    # It is grouped by ubatch (the model is run with -ub < budget on the 20b
    # and 120b configs, e.g. 32 ubatches of 2048 tokens for the 20b runs), so
    # for a fixed layer l, its rows appear once per ubatch, at file offsets
    # spaced L*ubatch_size apart, each contributing an increasing block of
    # token_index values. Only the unit-aa runs (single ubatch, tokens <=
    # ubatch size) happen to be one contiguous block per layer. This loader
    # therefore builds each layer's token-ordered sequence with a boolean
    # mask (which preserves file order, and file order is ubatch-ascending,
    # so the masked token_index values come out already monotonic) rather
    # than assuming a fixed reshape, and then VERIFIES token_index covers
    # 0..budget-1 exactly once per layer, in order, before trusting it.
    data = np.loadtxt(path, delimiter=",", dtype=np.int64)
    expected_rows = L * budget
    if data.shape != (expected_rows, 6):
        raise SystemExit("SHAPE MISMATCH: got %r expected (%d, 6)" % (data.shape, expected_rows))
    layer_col = data[:, 0]
    token_col = data[:, 1]
    expert_ids = data[:, 2:6]  # k=4 columns, id0..id3

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
            raise SystemExit("ORDER ASSUMPTION VIOLATED: layer %d token_index sequence "
                              "(in file-encounter order) is not exactly 0..budget-1 in order" % l)
        ids_by_layer[l] = expert_ids[mask]
    return ids_by_layer


def compute_m1_m2(ids_by_layer, E, L, budget):
    total_per_layer = budget * 4  # k=4 fixed
    hist = np.zeros((L, E), dtype=np.int64)
    for l in range(L):
        flat = ids_by_layer[l].reshape(-1)
        hist[l] = np.bincount(flat, minlength=E)
    # sanity: every layer's histogram sums to total_per_layer
    row_sums = hist.sum(axis=1)
    if not np.all(row_sums == total_per_layer):
        raise SystemExit("M1 HISTOGRAM SUM MISMATCH")

    dead_threshold = DEAD_FRACTION_THRESHOLD * total_per_layer
    dead_count = (hist < dead_threshold).sum(axis=1)  # per layer

    half = E // 2
    sorted_desc = np.sort(hist, axis=1)[:, ::-1]
    p_half = sorted_desc[:, :half].sum(axis=1).astype(np.float64) / row_sums.astype(np.float64)

    collapse = (p_half >= COLLAPSE_PHALF_THRESHOLD) & (dead_count > half)

    m1 = {
        "total_per_layer": int(total_per_layer),
        "dead_fraction_threshold": DEAD_FRACTION_THRESHOLD,
        "dead_count_per_layer": dead_count.astype(int).tolist(),
        "histogram": hist.astype(int).tolist(),  # L x E, c_l(e)
        "collapse_phalf_threshold": COLLAPSE_PHALF_THRESHOLD,
        "collapse_per_layer": collapse.tolist(),
        "collapse_any": bool(collapse.any()),
    }
    m2 = {
        "half": int(half),
        "p_half_per_layer": p_half.tolist(),
        "p_half_mean": float(p_half.mean()),
        "p_half_min": float(p_half.min()),
        "p_half_max": float(p_half.max()),
        "p_half_argmin_layer": int(p_half.argmin()),
        "p_half_argmax_layer": int(p_half.argmax()),
    }
    return m1, m2, hist


def onehot_windows(ids_by_layer, l, E, budget, W):
    n_windows = budget // W
    used = n_windows * W
    ids = ids_by_layer[l, :used, :].reshape(n_windows, W * 4)
    onehot = np.zeros((n_windows, E), dtype=bool)
    rows = np.repeat(np.arange(n_windows), W * 4)
    onehot[rows, ids.reshape(-1)] = True
    return onehot, n_windows


def compute_m3_m6(ids_by_layer, E, L, budget):
    m3 = {}
    m6_all_fractions = []  # collect across W=512 windows, all layers, for the M6 run-level distribution
    m4 = None
    for W in WINDOW_SIZES:
        if budget % W != 0:
            raise SystemExit("M3: budget %d not divisible by window %d" % (budget, W))
        per_layer_distinct = []  # L x n_windows
        onehots = []
        for l in range(L):
            oh, n_windows = onehot_windows(ids_by_layer, l, E, budget, W)
            distinct = oh.sum(axis=1)  # per window
            per_layer_distinct.append(distinct.astype(int).tolist())
            onehots.append(oh)
        per_layer_distinct_arr = np.array(per_layer_distinct, dtype=np.int64)  # L x n_windows
        implied_bytes = per_layer_distinct_arr * PER_EXPERT_BYTES_PER_LAYER
        pooled_distinct = per_layer_distinct_arr.sum(axis=0)  # sum over layers (disjoint per-layer namespaces)
        pooled_bytes = pooled_distinct * PER_EXPERT_BYTES_PER_LAYER

        m3[str(W)] = {
            "n_windows": int(n_windows),
            "per_layer_distinct_mean": per_layer_distinct_arr.mean(axis=1).tolist(),
            "per_layer_distinct_min": per_layer_distinct_arr.min(axis=1).tolist(),
            "per_layer_distinct_max": per_layer_distinct_arr.max(axis=1).tolist(),
            "run_mean_distinct": float(per_layer_distinct_arr.mean()),
            "run_min_distinct": int(per_layer_distinct_arr.min()),
            "run_max_distinct": int(per_layer_distinct_arr.max()),
            "implied_bytes_mean": float(implied_bytes.mean()),
            "implied_bytes_min": int(implied_bytes.min()),
            "implied_bytes_max": int(implied_bytes.max()),
            "pooled_distinct_mean": float(pooled_distinct.mean()),
            "pooled_distinct_min": int(pooled_distinct.min()),
            "pooled_distinct_max": int(pooled_distinct.max()),
            "pooled_bytes_mean": float(pooled_bytes.mean()),
            "pooled_bytes_min": int(pooled_bytes.min()),
            "pooled_bytes_max": int(pooled_bytes.max()),
        }

        if W == 512:
            # M4: consecutive non-overlapping window pairs, Jaccard per layer
            per_layer_jacc_mean = []
            per_layer_jacc_seq = []
            for l in range(L):
                oh = onehots[l]
                a = oh[:-1]
                b = oh[1:]
                inter = (a & b).sum(axis=1).astype(np.float64)
                union = (a | b).sum(axis=1).astype(np.float64)
                jacc = inter / union
                per_layer_jacc_seq.append(jacc.tolist())
                per_layer_jacc_mean.append(float(jacc.mean()))
            run_mean_jacc = float(np.mean(per_layer_jacc_mean))
            m4 = {
                "window": 512,
                "per_layer_jaccard_mean": per_layer_jacc_mean,
                "run_mean_jaccard": run_mean_jacc,
                "per_layer_jaccard_seq": per_layer_jacc_seq,
            }

            # M6: exposure fraction using the SAME W=512 windows.
            # resident_bytes(l,w) = distinct(l,w) * PER_EXPERT_BYTES_PER_LAYER
            # total_bytes(l)      = E * PER_EXPERT_BYTES_PER_LAYER
            # fraction = resident/total = distinct(l,w) / E   (byte term cancels
            # exactly because every expert in this GGUF layout is the same
            # byte size; recorded here as a stated algebraic fact, not assumed
            # before the division is shown to cancel it).
            fractions = per_layer_distinct_arr.astype(np.float64) / float(E)
            m6_all_fractions = fractions.reshape(-1)
            per_layer_fraction_mean = fractions.mean(axis=1).tolist()

    m6 = {
        "window": 512,
        "e_used_for_division": None,  # filled by caller (E), kept here for clarity in JSON
        "fraction_min": float(m6_all_fractions.min()),
        "fraction_median": float(np.median(m6_all_fractions)),
        "fraction_max": float(m6_all_fractions.max()),
        "fraction_mean": float(m6_all_fractions.mean()),
        "per_layer_fraction_mean": per_layer_fraction_mean,
    }
    return m3, m4, m6


def main():
    if len(sys.argv) != 7:
        raise SystemExit("usage: rs053-metrics.py <route_log> <E> <L> <budget> <label> <out_json>")
    route_log, E, L, budget, label, out_json = sys.argv[1:7]
    E = int(E); L = int(L); budget = int(budget)

    route_log_sha256 = sha256_of(route_log)
    ids_by_layer = load_route_log(route_log, E, L, budget)
    m1, m2, hist = compute_m1_m2(ids_by_layer, E, L, budget)
    m3, m4, m6 = compute_m3_m6(ids_by_layer, E, L, budget)
    m6["e_used_for_division"] = E

    report = {
        "label": label,
        "route_log": route_log,
        "route_log_sha256": route_log_sha256,
        "E": E,
        "L": L,
        "budget": budget,
        "per_expert_bytes_per_layer": PER_EXPERT_BYTES_PER_LAYER,
        "M1": m1,
        "M2": m2,
        "M3": m3,
        "M4": m4,
        "M6": m6,
    }

    with open(out_json, "w") as f:
        json.dump(report, f, sort_keys=True, indent=1)
        f.write("\n")

    print("LABEL=%s" % label)
    print("ROUTE_LOG=%s SHA256=%s" % (route_log, route_log_sha256))
    print("E=%d L=%d budget=%d" % (E, L, budget))
    print("M2 p_half_mean=%.17e p_half_min=%.17e (layer %d) p_half_max=%.17e (layer %d)" % (
        m2["p_half_mean"], m2["p_half_min"], m2["p_half_argmin_layer"],
        m2["p_half_max"], m2["p_half_argmax_layer"]))
    print("M1 collapse_any=%s max_dead_count=%d of E=%d" % (
        m1["collapse_any"], max(m1["dead_count_per_layer"]), E))
    for W in WINDOW_SIZES:
        d = m3[str(W)]
        print("M3 W=%d run_mean_distinct=%.6f run_min=%d run_max=%d pooled_distinct_mean=%.6f" % (
            W, d["run_mean_distinct"], d["run_min_distinct"], d["run_max_distinct"], d["pooled_distinct_mean"]))
    print("M4 W=512 run_mean_jaccard=%.17e" % m4["run_mean_jaccard"])
    print("M6 W=512 fraction_min=%.17e fraction_median=%.17e fraction_max=%.17e fraction_mean=%.17e" % (
        m6["fraction_min"], m6["fraction_median"], m6["fraction_max"], m6["fraction_mean"]))
    print("OUT_JSON=%s" % out_json)


if __name__ == "__main__":
    main()
