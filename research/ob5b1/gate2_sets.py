#!/usr/bin/env python3
# OB-5b S1 gate 2: derive the K=16, 24 and 32 resident sets on the SAME lineage
# as the banked K=8 set, and prove the derivation by reproducing the banked set.
#
# The ranking rule is copied from the banked file's own declared lineage:
#   research/ob1/resident_sets.py (same loader, same ranking rule, same tie-break)
#   tie_break: lower expert id
# so: count descending, ties broken by lower expert id, first K, emitted ascending.
#
# The counts are the banked file's OWN histogram_c_l_e, which leg A verified
# re-derives from the source route log (OB5B-S1-RUNLOG-1 section 3.2,
# banked_k8_set_rederives_from_this_log True). No route log is re-parsed here.
#
# Analysis only: no model, no runlock, no serve contact.

import json
import sys


def rank_layer(counts, K):
    order = sorted(range(len(counts)), key=lambda e: (-counts[e], e))
    return sorted(order[:K])


def main():
    src = sys.argv[1]
    dst = sys.argv[2]
    ks = [int(x) for x in sys.argv[3].split(",")]

    d = json.load(open(src))
    L = d["L"]
    E = d["E"]
    hist = d["histogram_c_l_e"]
    per_expert = d["per_expert_bytes_per_layer"]

    if len(hist) != L or any(len(r) != E for r in hist):
        print("FATAL histogram shape %d x %d != L=%d E=%d"
              % (len(hist), len(hist[0]), L, E))
        return 2

    total_decisions = sum(sum(r) for r in hist)
    print("L %d  E %d  total_decisions %d" % (L, E, total_decisions))

    sets = {}
    for K in ks:
        sets[K] = {str(il): rank_layer(hist[il], K) for il in range(L)}

    # LIMB 1: the K=8 derivation must reproduce the banked K=8 set exactly.
    banked8 = d["resident_sets"]["8"]
    mine8 = sets.get(8)
    if mine8 is None:
        print("K8_REPRODUCES n/a (8 not requested)")
    else:
        same = all(banked8[str(il)] == mine8[str(il)] for il in range(L))
        print("K8_REPRODUCES_BANKED_SET %s" % same)
        if not same:
            for il in range(L):
                if banked8[str(il)] != mine8[str(il)]:
                    print("  layer %d banked %s mine %s"
                          % (il, banked8[str(il)], mine8[str(il)]))
            return 3

    # LIMB 2: a popularity ranking must NEST. K=8 subset of K=16 subset of ...
    ordered = sorted(ks)
    nest_ok = True
    for a, b in zip(ordered, ordered[1:]):
        for il in range(L):
            if not set(sets[a][str(il)]).issubset(set(sets[b][str(il)])):
                nest_ok = False
                print("  NEST FAIL K=%d not in K=%d at layer %d" % (a, b, il))
    print("NESTING_HOLDS %s" % nest_ok)
    if not nest_ok:
        return 4

    # LIMB 3: the mass each set captures on its own ranking corpus. These are
    # checked against OB5B-S1-RUNLOG-1 section 3.5 by the caller.
    for K in ordered:
        hit = sum(hist[il][e] for il in range(L) for e in sets[K][str(il)])
        mass = hit / total_decisions
        misses_per_token = 4 * L * (1.0 - mass)
        print("K %2d  hit %d  mass %.10f  miss %.10f  mis/token %.6f  "
              "resident_bytes %d"
              % (K, hit, mass, 1.0 - mass, misses_per_token,
                 K * L * per_expert))

    out = {
        "E": E,
        "K_values": ordered,
        "L": L,
        "budget": d["budget"],
        "histogram_c_l_e": hist,
        "lineage": ("research/ob5b1/gate2_sets.py from research/ob1b/"
                    "RESIDENT-SETS-120B-K8.json histogram_c_l_e; same ranking "
                    "rule, same tie-break; the K=8 derivation reproduces the "
                    "banked K=8 set exactly"),
        "per_expert_bytes_per_layer": per_expert,
        "ranking_corpus": d["ranking_corpus"],
        "resident_expert_pool_bytes_per_K": {
            str(K): K * L * per_expert for K in ordered},
        "resident_sets": {str(K): sets[K] for K in ordered},
        "source_route_log": d["source_route_log"],
        "source_route_log_sha256": d["source_route_log_sha256"],
        "tie_break": d["tie_break"],
    }
    with open(dst, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
        f.write("\n")
    print("WROTE %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
