#!/usr/bin/env python3
"""OB-2 stage 2: resident-set SCHEDULE trace, emitted from the COMMITTED simulator.

The live lease engine, run with OB2_TRACE=<path>, writes one line per
(layer, recompute boundary):

    <layer>,<token_index>,<e0>,<e1>,...,<e{K-1}>        expert ids ascending

This script emits the identical format from the simulator that
research/OB2-PREDICTIVE-1-PREREG.md froze, so the two schedules can be
byte-compared (prereg section 9's engine-matches-model check, taken to its
strongest form: not "the miss rates are within 2.0 points" but "the engine made
the same residency decision at every boundary").

The policy is NOT re-derived here. This script imports the committed
research/ob2/sim_residency.py and, for every layer, cross-checks its own traced
walk's miss count against that module's own sim_p2_decay() BEFORE writing any
trace line for that layer. A mismatch is fatal. So the trace cannot silently
drift from the frozen policy even though the walk has to be re-expressed here
(sim_p2_decay returns totals and cannot report the intermediate sets).

Determinism: plain-integer counters throughout, same as the simulator. The
resident set at any boundary is a pure function of the route history strictly
before it plus the fixed constants (H, add, shift, K).

Usage:
  sim_trace.py <route_log> <E> <L> <budget> <K> <H> <out_trace> [max_token]

  max_token   optional: emit only boundaries with token_index < max_token
              (used for the short unit run, which covers fewer tokens than the
              banked reference route log the policy is replayed against)

Output is written sorted by (layer, token_index). The engine emits in graph
order (all layers of ubatch 0, then all layers of ubatch 1, ...) rather than
layer-major, so both sides are sorted the same way before comparison; the
comparison is then a byte-for-byte cmp of two identically-ordered files.
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_residency  # noqa: E402  (committed, digest pinned in the prereg)


def trace_p2_decay(ids_layer, il, K, E, H, lines, add=65536, shift=1, max_token=None):
    """Walk one layer under P2 DECAY-COUNTER, appending a trace line at every
    recompute boundary. Mirrors sim_residency.sim_p2_decay step for step; the
    returned miss count is cross-checked against it by the caller."""
    budget = ids_layer.shape[0]
    counters = [0] * E
    misses = 0
    t = 0
    first = True
    while t < budget:
        boundary = t
        if boundary > 0:
            # decay strictly-prior state, then recompute residency from it
            counters = [c >> shift for c in counters]
        resident = sorted(sim_residency.top_k(counters, K, E)) if not first else list(range(K))
        first = False

        if max_token is None or boundary < max_token:
            lines.append((il, boundary, resident))

        hi = min(budget, t + H)
        flat = ids_layer[t:hi].reshape(-1)
        misses += int(np.sum(~np.isin(flat, resident)))

        bc = np.bincount(flat, minlength=E)
        for e in range(E):
            counters[e] += add * int(bc[e])
        t = hi
    return misses


def main():
    if len(sys.argv) not in (8, 9):
        raise SystemExit("usage: sim_trace.py <route_log> <E> <L> <budget> <K> <H> <out_trace> [max_token]")
    route_log = sys.argv[1]
    E = int(sys.argv[2]); L = int(sys.argv[3]); budget = int(sys.argv[4])
    K = int(sys.argv[5]); H = int(sys.argv[6])
    out_trace = sys.argv[7]
    max_token = int(sys.argv[8]) if len(sys.argv) == 9 else None

    route_sha = sim_residency.sha256_of(route_log)
    ids_by_layer = sim_residency.load_route_log(route_log, E, L, budget)

    lines = []
    tot_misses = 0
    tot_picks = 0
    for il in range(L):
        m_trace = trace_p2_decay(ids_by_layer[il], il, K, E, H, lines, max_token=max_token)
        m_ref, picks, _churn = sim_residency.sim_p2_decay(ids_by_layer[il], K, E, H)
        if m_trace != m_ref:
            raise SystemExit(
                "FATAL: traced walk disagrees with committed sim_p2_decay at layer %d: "
                "%d vs %d misses" % (il, m_trace, m_ref))
        tot_misses += m_ref
        tot_picks += picks

    lines.sort(key=lambda r: (r[0], r[1]))
    with open(out_trace, "w") as f:
        for (il, tok, resident) in lines:
            f.write("%d,%d,%s\n" % (il, tok, ",".join(str(e) for e in resident)))

    print("ROUTE_LOG=%s" % route_log)
    print("ROUTE_LOG_SHA256=%s" % route_sha)
    print("K=%d H=%d E=%d L=%d budget=%d max_token=%s" % (K, H, E, L, budget, max_token))
    print("CROSSCHECK_VS_COMMITTED_SIM=PASS (all %d layers)" % L)
    print("TOTAL_PICKS=%d" % tot_picks)
    print("TOTAL_MISSES=%d" % tot_misses)
    print("MISS_PCT=%.10f" % (100.0 * tot_misses / tot_picks))
    print("TRACE_LINES=%d" % len(lines))
    print("WROTE %s" % out_trace)


if __name__ == "__main__":
    main()
