#!/usr/bin/env python3
"""OB-1b: predict lease_events and peak_concurrent_lease_bytes exactly,
from an already-banked route log, before the runs are made.

WHY THIS EXISTS. The prereg predicts the peak-concurrent term with the
rule peak(K) = (E-K) * PER_EXPERT, reasoning that in the worst micro-batch every
non-resident expert of some layer gets routed. That is a plausible argument, and
it reproduces OB-1's three measured points, but it is still an argument. The
route logs are already banked, and the lease engine's behaviour is a pure
function of them: it leases, at each (layer, micro-batch) callback, exactly the
DISTINCT routed experts of that layer's micro-batch that are not resident, and
drops them at the next layer. So both counters can be computed exactly in
advance and then checked against the engine's own measurement.

  lease_events(K)   = sum over (layer, chunk) of |routed(layer,chunk) \\ resident(layer,K)|
  peak_concurrent(K)= max over (layer, chunk) of |routed(layer,chunk) \\ resident(layer,K)|
                      * PER_EXPERT_BYTES_PER_LAYER

VALIDATION FIRST: the same computation is run against OB-1's own K in {16,8,4}
and must reproduce its published lease_events and peak_concurrent_lease_bytes
before any new K is trusted.

Usage: predict_leases.py <route_log> <E> <L> <budget> <chunk_tokens> <sets.json> <K,..>
"""

import json
import sys

import numpy as np

PER_EXPERT = 13253760


def load_route_log(path, E, L, budget):
    # Identical loader/verification to research/ob1b/sim_miss.py.
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


def predict(ids_by_layer, resident, E, L, budget, chunk_tokens):
    """resident: dict layer -> set of resident expert ids."""
    nchunks = budget // chunk_tokens
    events = 0
    peak_experts = 0
    for l in range(L):
        res = resident.get(l, set())
        for c in range(nchunks):
            block = ids_by_layer[l, c * chunk_tokens:(c + 1) * chunk_tokens, :]
            routed = np.unique(block)
            n = sum(1 for e in routed.tolist() if e not in res)
            events += n
            if n > peak_experts:
                peak_experts = n
    return events, peak_experts, peak_experts * PER_EXPERT


def main():
    if len(sys.argv) != 8:
        raise SystemExit(__doc__)
    route_log, E, L, budget, chunk_tokens, sets_json, klist = sys.argv[1:8]
    E, L, budget, chunk_tokens = int(E), int(L), int(budget), int(chunk_tokens)
    Ks = sorted({int(x) for x in klist.split(",")}, reverse=True)

    ids = load_route_log(route_log, E, L, budget)
    doc = json.load(open(sets_json))
    sets = doc["resident_sets"]

    print("route_log      %s" % route_log)
    print("E=%d L=%d budget=%d chunk_tokens=%d chunks=%d" % (
        E, L, budget, chunk_tokens, budget // chunk_tokens))
    print("sets           %s" % sets_json)
    print()
    print("%-4s %14s %16s %20s %18s" % (
        "K", "lease_events", "peak_experts", "peak_concurrent_B", "rule (E-K)*per_exp"))
    for K in Ks:
        key = str(K)
        if key not in sets:
            print("%-4d  (K=%d not present in this resident-sets file)" % (K, K))
            continue
        resident = {int(l): set(v) for l, v in sets[key].items()}
        ev, pe, pb = predict(ids, resident, E, L, budget, chunk_tokens)
        rule = (E - K) * PER_EXPERT
        print("%-4d %14d %16d %20d %18d %s" % (
            K, ev, pe, pb, rule, "MATCHES RULE" if pb == rule else "DIFFERS FROM RULE"))


if __name__ == "__main__":
    main()
