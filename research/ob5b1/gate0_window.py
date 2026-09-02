#!/usr/bin/env python3
# OB-5b S1 gate 0, TTFT limb: distinct-expert working set of a 64-token prefill
# window, split into the part the BANKED K=8 resident set already holds and the
# part that must be leased. This is the measurement that decides which of C4
# section 2.3 P-C's two readings is correct.
#
# Windows are NON-OVERLAPPING, stride W, exactly as RS053 D14 froze them, so
# the distinct counts here are directly comparable to RS053 section 5.
#
# Analysis only. No model, no runlock, no serve contact.

import json
import sys

import numpy as np

K_USED = 4
BASE = "/mnt/f/f32/stage/research/ob5b1/gate0/"
RUNS = "/mnt/f/f32/stage/research/rs053/runs/"
SETS = "/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json"
W = 64


def load_layers(path, L, T):
    with open(path, "r") as f:
        flat = np.fromstring(f.read().replace(",", " "), sep=" ", dtype=np.int64)
    rows = flat.reshape(-1, 2 + K_USED)
    out = []
    for l in range(L):
        m = rows[:, 0] == l
        idx = rows[m, 1]
        if not np.array_equal(idx, np.arange(T, dtype=np.int64)):
            sys.exit("ORDER ASSUMPTION VIOLATED at layer %d of %s" % (l, path))
        out.append(rows[m, 2:])
    return out


def main():
    sets_doc = json.load(open(SETS))
    L = int(sets_doc["L"])
    E = int(sets_doc["E"])
    T = int(sets_doc["budget"])
    banked8 = [sorted(int(x) for x in sets_doc["resident_sets"]["8"][str(l)])
               for l in range(L)]
    R = np.zeros((L, E), dtype=bool)
    for l in range(L):
        R[l, banked8[l]] = True

    result = {}
    for lab in ["120b-prose-a", "120b-code-a"]:
        per_layer = load_layers(RUNS + lab + "/route.log", L, T)
        nwin = T // W
        distinct = np.zeros((L, nwin), dtype=np.int64)
        res_hit = np.zeros((L, nwin), dtype=np.int64)
        for l in range(L):
            ids = per_layer[l]
            for w in range(nwin):
                blk = ids[w * W:(w + 1) * W].ravel()
                u = np.unique(blk)
                distinct[l, w] = u.shape[0]
                res_hit[l, w] = int(R[l][u].sum())
        nonres = distinct - res_hit
        result[lab] = {
            "W": W,
            "n_windows": nwin,
            "mean_distinct_per_layer_window": float(distinct.mean()),
            "mean_resident_hits_per_layer_window": float(res_hit.mean()),
            "mean_nonresident_per_layer_window": float(nonres.mean()),
            "mean_nonresident_distinct_per_window_all_layers":
                float(nonres.sum(axis=0).mean()),
            "max_nonresident_distinct_per_window_all_layers":
                int(nonres.sum(axis=0).max()),
            "min_nonresident_distinct_per_window_all_layers":
                int(nonres.sum(axis=0).min()),
            "layer_mean_distinct": [float(x) for x in distinct.mean(axis=1)],
            "layer_mean_resident_hits": [float(x) for x in res_hit.mean(axis=1)],
        }
        print("%s W=%d windows=%d mean_distinct/layer/window %.6f  resident %.6f  nonresident %.6f"
              % (lab, W, nwin, distinct.mean(), res_hit.mean(), nonres.mean()))
        print("    nonresident distinct per window, all %d layers: mean %.4f min %d max %d"
              % (L, nonres.sum(axis=0).mean(), nonres.sum(axis=0).min(),
                 nonres.sum(axis=0).max()))

    with open(BASE + "window64.json", "w") as f:
        json.dump(result, f, sort_keys=True, indent=1)
        f.write("\n")
    print("WROTE %swindow64.json" % BASE)


if __name__ == "__main__":
    main()
