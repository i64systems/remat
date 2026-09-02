import json, os
RESULTS_DIR = "/mnt/f/f32/stage/research/ob4/results"
with open(os.path.join(RESULTS_DIR, "encode-results.json")) as f:
    results = json.load(f)
with open(os.path.join(RESULTS_DIR, "dicts.json")) as f:
    dicts = json.load(f)

by_kind = {}
for r in results:
    by_kind.setdefault(r["tensor"], []).append(r)

grand_raw = 0
grand_c4_amort = 0
out = {}
for kind, rows in by_kind.items():
    raw = sum(r["raw_bytes"] for r in rows)
    c4 = sum(r["c4_bytes"] for r in rows)
    dsize = dicts[kind]["size_bytes"]
    c4_amort = c4 + dsize
    ratio_amort = c4_amort / raw
    ratio_bare = c4 / raw
    out[kind] = {
        "n_slices": len(rows), "raw": raw, "c4_bare": c4, "dict_bytes": dsize,
        "c4_amortized_total": c4_amort,
        "ratio_C4_bare": ratio_bare,
        "ratio_C4_amortized": ratio_amort,
    }
    grand_raw += raw
    grand_c4_amort += c4_amort
    print(kind, out[kind])

print("POOLED ratio_C4_amortized:", grand_c4_amort / grand_raw)
out["_pooled"] = {"raw": grand_raw, "c4_amortized_total": grand_c4_amort, "ratio_C4_amortized": grand_c4_amort/grand_raw}
with open(os.path.join(RESULTS_DIR, "c4-amortized.json"), "w") as f:
    json.dump(out, f, indent=2)
