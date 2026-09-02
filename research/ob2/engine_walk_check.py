#!/usr/bin/env python3
"""OB-2 stage 2: a paper model of the LIVE ENGINE's walk, checked against the
committed simulator before any model process is started.

Why this exists. The committed simulator (research/ob2/sim_residency.py) walks
one layer at a time over all 32768 tokens. The live engine cannot: llama.cpp
hands it one ubatch of 1024 tokens per layer, in graph order (all 24 layers of
ubatch 0, then all 24 of ubatch 1, ...), and every policy boundary inside that
ubatch has to be handled from state the engine carries across callbacks. That is
a different loop shape over the same policy, and a different loop shape is
exactly where a boundary off-by-one or a state-carry bug lives.

So this script re-expresses the ENGINE's loop -- ubatch-major, per-layer carried
state, windows split at H boundaries inside a ubatch -- in Python, and checks
that it lands on the same miss count and the same resident-set schedule as the
committed simulator. It is a cheap dry run of src/ob1-lease.cpp's ob2_on_route()
that costs no runlock, no GPU, and no 15-minute model run.

It also reports the quantity the simulator has no notion of: how many experts
per layer must be in RAM SIMULTANEOUSLY for one ubatch. The kernel computes all
1024 tokens of a ubatch in a single mul_mat_id call, so the physical set is the
union over that ubatch's 4 policy windows of their resident sets, plus every
expert the router actually picked in it. That union, not K, is the honest memory
bound at this batch size.

Usage:
  engine_walk_check.py <route_log> <E> <L> <budget> <K> <H> <ubatch> [out_trace] [max_token]
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_residency  # noqa: E402


def engine_walk(ids_by_layer, L, E, K, H, budget, ubatch, add=65536, shift=1,
                max_token=None):
    cnt = [[0] * E for _ in range(L)]
    res = [set(range(K)) for _ in range(L)]
    phys = [set(range(K)) for _ in range(L)]
    tok = [0] * L

    lines = []
    misses = 0
    picks = 0
    churn = 0
    boundaries = 0
    lease_events = 0
    evict_events = 0
    promote_events = 0
    trans_events = 0
    physneed_max = 0
    physneed_sum = 0
    physneed_n = 0

    n_ub = (budget + ubatch - 1) // ubatch
    for ub in range(n_ub):
        lo = ub * ubatch
        hi = min(budget, lo + ubatch)
        for il in range(L):
            ids = ids_by_layer[il][lo:hi]           # (n_tokens, 4)
            n_tokens = ids.shape[0]
            runion = set()
            need = set()

            t = 0
            while t < n_tokens:
                abs_t = tok[il] + t
                span = min(H - (abs_t % H), n_tokens - t)

                if abs_t % H == 0:
                    if abs_t > 0:
                        cnt[il] = [c >> shift for c in cnt[il]]
                        new_res = set(sim_residency.top_k(cnt[il], K, E))
                        churn += len(res[il].symmetric_difference(new_res))
                    else:
                        new_res = set(range(K))
                    res[il] = new_res
                    boundaries += 1
                    if max_token is None or abs_t < max_token:
                        lines.append((il, abs_t, sorted(new_res)))

                runion |= res[il]

                seg = ids[t:t + span].reshape(-1)
                rl = sorted(res[il])
                misses += int(np.sum(~np.isin(seg, rl)))
                picks += int(seg.size)
                need |= set(int(x) for x in np.unique(seg))
                bc = np.bincount(seg, minlength=E)
                for e in range(E):
                    cnt[il][e] += add * int(bc[e])
                t += span

            pneed = runion | need
            physneed_sum += len(pneed)
            physneed_n += 1
            physneed_max = max(physneed_max, len(pneed))

            ev = phys[il] - pneed                    # evict
            evict_events += len(ev)
            phys[il] -= ev

            li = pneed - phys[il]                    # lease in
            lease_events += len(li)
            promote_events += len(li & res[il])
            phys[il] |= li

            tr = phys[il] - res[il]                  # transient, dropped after the layer
            trans_events += len(tr)
            phys[il] -= tr

            tok[il] += n_tokens

    return {
        "misses": misses, "picks": picks, "churn": churn, "boundaries": boundaries,
        "lease_events": lease_events, "evict_events": evict_events,
        "promote_events": promote_events, "trans_events": trans_events,
        "physneed_max": physneed_max,
        "physneed_mean": physneed_sum / float(physneed_n) if physneed_n else 0.0,
        "lines": lines,
    }


def main():
    if len(sys.argv) < 8:
        raise SystemExit("usage: engine_walk_check.py <route_log> <E> <L> <budget> <K> <H> <ubatch> [out_trace] [max_token]")
    route_log = sys.argv[1]
    E = int(sys.argv[2]); L = int(sys.argv[3]); budget = int(sys.argv[4])
    K = int(sys.argv[5]); H = int(sys.argv[6]); ubatch = int(sys.argv[7])
    out_trace = sys.argv[8] if len(sys.argv) > 8 else None
    max_token = int(sys.argv[9]) if len(sys.argv) > 9 else None

    print("ROUTE_LOG=%s" % route_log)
    print("ROUTE_LOG_SHA256=%s" % sim_residency.sha256_of(route_log))
    print("K=%d H=%d ubatch=%d E=%d L=%d budget=%d" % (K, H, ubatch, E, L, budget))

    ids_by_layer = sim_residency.load_route_log(route_log, E, L, budget)

    r = engine_walk(ids_by_layer, L, E, K, H, budget, ubatch, max_token=max_token)

    # the committed simulator's own answer for the same policy/corpus/K
    sim_misses = 0
    sim_picks = 0
    sim_churn = 0
    for il in range(L):
        m, p, c = sim_residency.sim_p2_decay(ids_by_layer[il], K, E, H)
        sim_misses += m; sim_picks += p; sim_churn += c

    print()
    print("ENGINE-SHAPED WALK   misses=%d picks=%d miss_pct=%.10f churn=%d boundaries=%d" % (
        r["misses"], r["picks"], 100.0 * r["misses"] / r["picks"], r["churn"], r["boundaries"]))
    print("COMMITTED SIMULATOR  misses=%d picks=%d miss_pct=%.10f churn=%d" % (
        sim_misses, sim_picks, 100.0 * sim_misses / sim_picks, sim_churn))
    ok = (r["misses"] == sim_misses and r["picks"] == sim_picks and r["churn"] == sim_churn)
    print("AGREE=%s" % ("PASS (exact)" if ok else "FAIL"))

    print()
    print("BYTE MOVEMENT THE SIMULATOR CANNOT SEE (ubatch=%d granularity):" % ubatch)
    print("  lease_events   = %d   (expert-loads from the GGUF, all digest-verified)" % r["lease_events"])
    print("  evict_events   = %d   (residency drops: policy no longer keeps them)" % r["evict_events"])
    print("  promote_events = %d   (loads that the new residency KEEPS)" % r["promote_events"])
    print("  trans_events   = %d   (loads dropped as soon as the layer is computed)" % r["trans_events"])
    print("  physneed_max   = %d experts per layer simultaneously (K=%d)" % (r["physneed_max"], K))
    print("  physneed_mean  = %.4f experts per layer per ubatch" % r["physneed_mean"])

    if out_trace:
        r["lines"].sort(key=lambda x: (x[0], x[1]))
        with open(out_trace, "w") as f:
            for (il, tk, rs) in r["lines"]:
                f.write("%d,%d,%s\n" % (il, tk, ",".join(str(e) for e in rs)))
        print("WROTE %s (%d lines)" % (out_trace, len(r["lines"])))

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
