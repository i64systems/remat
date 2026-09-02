#!/usr/bin/env python3
# RS053-GPTOSS-LOCALITY-1 : Stage 3, M5 cross-slice divergence.
# Reads two per-run JSON reports from rs053-metrics.py (same model, prose vs
# code corpus) and computes M5 per prereg 5.5. Deterministic, stdlib json only.
#
# Usage: rs053-cross.py <prose_json> <code_json> <model_label> <top_n> <out_json>

import sys, json


def top_set(counts, n):
    nz = [(i, c) for i, c in enumerate(counts) if c > 0]
    nz.sort(key=lambda p: (-p[1], p[0]))  # largest usage first, lower index breaks ties
    return set(i for i, c in nz[:n])


def main():
    if len(sys.argv) != 6:
        raise SystemExit("usage: rs053-cross.py <prose_json> <code_json> <model_label> <top_n> <out_json>")
    prose_path, code_path, model_label, top_n, out_json = sys.argv[1:6]
    top_n = int(top_n)

    with open(prose_path) as f:
        prose = json.load(f)
    with open(code_path) as f:
        code = json.load(f)

    if prose["E"] != code["E"] or prose["L"] != code["L"]:
        raise SystemExit("M5: prose/code E or L mismatch, not the same model")
    E = prose["E"]
    L = prose["L"]

    hist_prose = prose["M1"]["histogram"]  # L x E
    hist_code = code["M1"]["histogram"]

    j_top_per_layer = []
    l1_per_layer = []
    prose_topset_sizes = []
    code_topset_sizes = []
    for l in range(L):
        cp = hist_prose[l]
        cc = hist_code[l]
        tp = top_set(cp, top_n)
        tc = top_set(cc, top_n)
        prose_topset_sizes.append(len(tp))
        code_topset_sizes.append(len(tc))
        inter = len(tp & tc)
        union = len(tp | tc)
        j = (inter / union) if union > 0 else 1.0
        j_top_per_layer.append(j)

        sp = sum(cp)
        sc = sum(cc)
        l1 = 0.0
        for e in range(E):
            l1 += abs((cp[e] / sp) - (cc[e] / sc))
        l1_per_layer.append(l1)

    report = {
        "model_label": model_label,
        "prose_json": prose_path,
        "code_json": code_path,
        "E": E,
        "L": L,
        "top_n": top_n,
        "j_top_per_layer": j_top_per_layer,
        "j_top_mean": sum(j_top_per_layer) / L,
        "j_top_min": min(j_top_per_layer),
        "j_top_max": max(j_top_per_layer),
        "prose_topset_size_per_layer": prose_topset_sizes,
        "code_topset_size_per_layer": code_topset_sizes,
        "l1_per_layer": l1_per_layer,
        "l1_mean": sum(l1_per_layer) / L,
        "l1_min": min(l1_per_layer),
        "l1_max": max(l1_per_layer),
        "degenerate_top_n_equals_E": (top_n >= E),
    }

    with open(out_json, "w") as f:
        json.dump(report, f, sort_keys=True, indent=1)
        f.write("\n")

    print("MODEL=%s top_n=%d E=%d L=%d degenerate=%s" % (model_label, top_n, E, L, report["degenerate_top_n_equals_E"]))
    print("M5 j_top_mean=%.17e j_top_min=%.17e j_top_max=%.17e" % (report["j_top_mean"], report["j_top_min"], report["j_top_max"]))
    print("M5 l1_mean=%.17e l1_min=%.17e l1_max=%.17e" % (report["l1_mean"], report["l1_min"], report["l1_max"]))
    print("OUT_JSON=%s" % out_json)


if __name__ == "__main__":
    main()
