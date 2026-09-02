import sys, os

def validate(path, E, L, budget):
    layers = {}
    kset = set()
    idmin = 10**9
    idmax = -1
    dup_lines = 0
    bad = 0
    n = 0
    with open(path, "r") as f:
        for line in f:
            n += 1
            p = line.rstrip("\n").split(",")
            il = int(p[0]); ti = int(p[1])
            ids = [int(x) for x in p[2:]]
            kset.add(len(ids))
            if len(set(ids)) != len(ids):
                dup_lines += 1
            for e in ids:
                if e < idmin: idmin = e
                if e > idmax: idmax = e
                if e < 0 or e >= E: bad += 1
            d = layers.setdefault(il, [ti, ti, 0])
            if ti < d[0]: d[0] = ti
            if ti > d[1]: d[1] = ti
            d[2] += 1
    tokmins = sorted(set(d[0] for d in layers.values()))
    tokmaxs = sorted(set(d[1] for d in layers.values()))
    counts  = sorted(set(d[2] for d in layers.values()))
    print("FILE %s" % path)
    print("  lines=%d bytes=%d" % (n, os.path.getsize(path)))
    print("  distinct_layers=%d layer_ids=[%d..%d] expected_L=%d %s" % (
        len(layers), min(layers), max(layers), L,
        "OK" if len(layers) == L and min(layers) == 0 and max(layers) == L-1 else "MISMATCH"))
    print("  k_per_line=%s expected_k=4 %s" % (sorted(kset), "OK" if kset == {4} else "MISMATCH"))
    print("  token_index_min_per_layer=%s token_index_max_per_layer=%s" % (tokmins, tokmaxs))
    print("  tokens_per_layer=%s expected_budget=%d %s" % (
        counts, budget, "OK" if counts == [budget] and tokmaxs == [budget-1] else "MISMATCH"))
    print("  expert_id_range=[%d..%d] expected=[0..%d] out_of_range=%d %s" % (
        idmin, idmax, E-1, bad, "OK" if bad == 0 else "MISMATCH"))
    print("  lines_with_duplicate_expert_ids=%d" % dup_lines)
    print("  total_lines_check=%d expected=%d %s" % (n, L*budget, "OK" if n == L*budget else "MISMATCH"))
    print("")

specs = [
    ("/root/rs053/runs/unit-aa-a/route.log",   32, 24,   512),
    ("/root/rs053/runs/unit-aa-b/route.log",   32, 24,   512),
    ("/root/rs053/runs/20b-prose-a/route.log", 32, 24, 65536),
    ("/root/rs053/runs/20b-prose-b/route.log", 32, 24, 65536),
    ("/root/rs053/runs/20b-code-a/route.log",  32, 24, 65536),
    ("/root/rs053/runs/20b-code-b/route.log",  32, 24, 65536),
    ("/root/rs053/runs/120b-prose-a/route.log",128, 36, 16384),
    ("/root/rs053/runs/120b-prose-b/route.log",128, 36, 16384),
    ("/root/rs053/runs/120b-code-a/route.log", 128, 36, 16384),
    ("/root/rs053/runs/120b-code-b/route.log", 128, 36, 16384),
]
for p, E, L, b in specs:
    validate(p, E, L, b)
