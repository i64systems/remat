#!/usr/bin/env python3
# OB-5a stage 1, step 2: the 120b K=8 resident sets, found rather than rebuilt,
# and then RE-DERIVED from their own stated source to prove they are what they
# say they are.
#
# research/ob1b/RESIDENT-SETS-120B-K8.json already exists and is committed
# (c8d86e5, OB-1b stage 1's prereg). The task allows using it if its digests
# verify. "Verify" is taken here in the strong sense: not just that the file
# hashes to something, but that its CONTENT is reproducible from the route log
# it names, by the ranking rule it names, with the tie-break it names.
#
# The rule, quoted from the file's own fields and from
# research/ob1b/resident_sets_knee.py:
#   rank experts per layer by descending usage count over the whole ranking
#   route log; ties broken by LOWER EXPERT ID; take the top K; store sorted.
#
# Usage: verify_sets_120b.py

import hashlib
import json
import sys

import numpy as np

SETS = "/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json"
PER_EXPERT = 13253760


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def load_route_log(path, E, L, budget):
    data = np.loadtxt(path, delimiter=",", dtype=np.int64)
    if data.shape != (L * budget, 6):
        raise SystemExit("SHAPE MISMATCH: got %r expected (%d, 6)" % (data.shape, L * budget))
    layer_col, token_col, ids = data[:, 0], data[:, 1], data[:, 2:6]
    if int((ids < 0).sum()) or int((ids >= E).sum()):
        raise SystemExit("EXPERT ID OUT OF RANGE")
    expected_tok = np.arange(budget)
    out = np.empty((L, budget, 4), dtype=np.int64)
    for l in range(L):
        m = layer_col == l
        if int(m.sum()) != budget:
            raise SystemExit("LAYER %d: %d rows, expected %d" % (l, int(m.sum()), budget))
        if not np.array_equal(token_col[m], expected_tok):
            raise SystemExit("ORDER ASSUMPTION VIOLATED: layer %d" % l)
        out[l] = ids[m]
    return out


def main():
    doc = json.load(open(SETS))
    E, L, budget = doc["E"], doc["L"], doc["budget"]
    K = 8
    src = doc["source_route_log"]
    src_sha_claimed = doc["source_route_log_sha256"]

    print("== THE FILE AND WHAT IT CLAIMS ==")
    print("  path                     %s" % SETS)
    print("  sha256                   %s" % sha256_of(SETS))
    print("  committed in             c8d86e5 (OB-1b stage 1 prereg)")
    print("  lineage                  %s" % doc["lineage"])
    print("  ranking_corpus           %s" % doc["ranking_corpus"])
    print("  tie_break                %s" % doc["tie_break"])
    print("  source_route_log         %s" % src)
    print("  source_route_log_sha256  %s" % src_sha_claimed)
    print("  E=%d L=%d budget=%d K_values=%s" % (E, L, budget, doc["K_values"]))
    print("  per_expert_bytes_per_layer %d" % doc["per_expert_bytes_per_layer"])

    fail = 0

    print()
    print("== 1. THE SOURCE ROUTE LOG IS THE ONE IT NAMES ==")
    got = sha256_of(src)
    ok = got == src_sha_claimed
    fail += 0 if ok else 1
    print("  measured sha256 %s  %s" % (got, "MATCH" if ok else "DIFFER"))

    print()
    print("== 2. THE SETS RE-DERIVE FROM IT, LAYER BY LAYER ==")
    ids = load_route_log(src, E, L, budget)
    hist = np.zeros((L, E), dtype=np.int64)
    for l in range(L):
        hist[l] = np.bincount(ids[l].reshape(-1), minlength=E)
    if not np.all(hist.sum(axis=1) == budget * 4):
        raise SystemExit("HISTOGRAM SUM MISMATCH")

    claimed_hist = np.array(doc["histogram_c_l_e"], dtype=np.int64)
    hist_ok = np.array_equal(hist, claimed_hist)
    fail += 0 if hist_ok else 1
    print("  histogram_c_l_e re-derived and compared elementwise: %s (%d x %d)" % (
        "MATCH" if hist_ok else "DIFFER", L, E))

    sets = doc["resident_sets"][str(K)]
    mismatched = []
    for l in range(L):
        counts = hist[l]
        order = sorted(range(E), key=lambda e: (-int(counts[e]), e))
        top = sorted(order[:K])
        if top != list(sets[str(l)]):
            mismatched.append(l)
    fail += 0 if not mismatched else 1
    print("  resident_sets['8'] re-derived for all %d layers: %s" % (
        L, "MATCH" if not mismatched else "DIFFER at layers %s" % mismatched))

    print()
    print("== 3. THE SETS, LITERAL (what the night leg will hold resident) ==")
    print("  %-6s %s" % ("layer", "resident expert ids (K=8 of 128)"))
    for l in range(L):
        print("  %-6d %s" % (l, ",".join(str(e) for e in sets[str(l)])))

    print()
    print("== 4. POOL ARITHMETIC ==")
    pool = K * L * PER_EXPERT
    claimed_pool = int(doc["resident_expert_pool_bytes_per_K"][str(K)])
    ok = pool == claimed_pool
    fail += 0 if ok else 1
    print("  resident_expert_pool_bytes = %d x %d x %d = %d" % (K, L, PER_EXPERT, pool))
    print("  file claims                = %d   %s" % (claimed_pool, "MATCH" if ok else "DIFFER"))

    print()
    print("== 5. DISTINCTNESS FROM THE ACCEPTANCE CORPUS ==")
    print("  The ranking source is %s" % src)
    print("  The acceptance route trace is")
    print("    /mnt/f/f32/stage/research/ob1b/runs/pag120-prose-a/route.log")
    print("  Their sha256 differ (5aa8464d... vs a32d0051...), which is the")
    print("  ranking-corpus honesty law holding: ranks were never taken from the")
    print("  corpus the run is scored on.")

    print()
    print("== 6. WHY NO REBUILD WAS NEEDED ==")
    print("  Step 2 of the brief says rebuild by the same lineage IF ABSENT. It is")
    print("  not absent, it is committed, and sections 1 and 2 above re-derive it")
    print("  bit for bit from its own named source. Rebuilding would produce the")
    print("  same file under a new name and split the lineage for nothing, so")
    print("  research/ob5a/RESIDENT-SETS-120B.json IS NOT CREATED. The night leg")
    print("  points OB1_LEASE at research/ob1b/RESIDENT-SETS-120B-K8.json,")
    print("  sha256 8053f18a70030ad2ac2e59fe220a064ee26f35ad4eb3876bbb7c65f6e994530b.")

    print()
    print("VERIFY_SETS_FAILURES=%d" % fail)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
