#!/usr/bin/env python3
"""OB-5b P05 (C8-S8-2): THE DECODE-SHAPE REPLAY HARNESS OF RECORD.

Replays a banked route log at an arbitrary micro-batch shape (ubatch U)
through a deterministic integer residency/lease simulator and reports the
counters the live engine reports, so that a decode-shape (U=1) figure can
be produced for a model that has only ever been measured at U=1024.

LINEAGE. The policy bodies (P0-STATIC, P1-SLIDING, P2-DECAY) are carried
unmodified in behaviour from research/ob2/sim_residency.py, which has an
AGREE=PASS record against the live engine's own walk
(research/ob2/engine_walk_check.py, OB2-PREDICTIVE-1.md section 5). What
is NEW here is the LEASE accounting layer: sim_residency.py counted
pick-level misses only, which is a decode-shape quantity by accident
(at U=1 a pick-level miss is a lease event) and says nothing at U=1024.
This harness counts LEASE EVENTS at an arbitrary U, which is what the
engine's ob1-stats.txt reports, and is therefore the first replay in this
house that can be CALIBRATED against a live counter.

DETERMINISM WALL. Every counter below is a Python int. The only floats
are rates printed for humans and never fed back into a decision. The
resident set for any decision is a pure function of the route history
strictly before the governing recompute boundary and of fixed integer
policy constants; it never depends on timing, cache state, or the
current token's own routing.

THE ENGINE MODEL, stated so it can be falsified. The lease engine takes
one route call per (layer, micro-batch): it computes routing for the
whole micro-batch, leases every routed expert that is not resident, and
drops those leases before the next layer's routing (OB2-PREDICTIVE-1.md
section 7; OB1B-KNEE-1.md section 8). So:

  lease_events(layer, window) = |{experts routed in window} \\ {resident}|
  lease_bytes_read            = lease_events * per_expert
  peak_concurrent_lease_bytes = max over (layer, window) of
                                lease_events(layer, window) * per_expert

There is no prefetch term: the measured batch-shape peak_concurrent is
exactly ONE layer's non-resident set, (E-K) x per_expert (OB5A-ALLOC-1.md
section 6.2, measured twice). That fact is what pins prefetch depth d=1
for the engine of record, and it is the whole of this harness's
reconciliation of the two banked decode-shape ACCT literals.

WHEN THE POLICY BOUNDARY IS FINER THAN THE MICRO-BATCH (H < U) the model
above is ambiguous and the harness reports BOTH readings rather than
choosing:
  window-start  the resident set current at the first token of the
                micro-batch governs the whole route call
  sub-window    the micro-batch is split at policy boundaries and each
                piece is counted against its own resident set
For a static policy, and for any U <= H, the two are identical by
construction.

usage: see main()'s argument list; every run writes one literal row block.
"""

import sys
import json
import hashlib
import argparse
import numpy as np


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_route_log(path, E, L, budget, k):
    """research/ob1's frozen route-log format: layer,token_index,e0..e{k-1};
    one row per (layer, token), file order ubatch-ascending. Carried from
    sim_residency.py's loader, generalized from k=4 to any k."""
    data = np.loadtxt(path, delimiter=",", dtype=np.int64)
    expected_rows = L * budget
    if data.shape != (expected_rows, 2 + k):
        raise SystemExit("SHAPE MISMATCH: got %r expected (%d, %d)"
                         % (data.shape, expected_rows, 2 + k))
    layer_col = data[:, 0]
    token_col = data[:, 1]
    expert_ids = data[:, 2:2 + k]
    if int((expert_ids < 0).sum()) != 0 or int((expert_ids >= E).sum()) != 0:
        raise SystemExit("EXPERT ID OUT OF RANGE")
    expected_tok = np.arange(budget)
    ids_by_layer = np.empty((L, budget, k), dtype=np.int64)
    for l in range(L):
        mask = layer_col == l
        n = int(mask.sum())
        if n != budget:
            raise SystemExit("LAYER %d: got %d rows, expected budget=%d" % (l, n, budget))
        tok_l = token_col[mask]
        if not np.array_equal(tok_l, expected_tok):
            raise SystemExit("ORDER ASSUMPTION VIOLATED: layer %d" % l)
        ids_by_layer[l] = expert_ids[mask]
    return ids_by_layer


def top_k(counts, K, E):
    """Descending count, ties by lower expert id. Integer only."""
    order = sorted(range(E), key=lambda e: (-int(counts[e]), e))
    return sorted(order[:K])


# ---------------------------------------------------------------------
# RESIDENCY SCHEDULES. Each returns (boundaries, sets) where boundaries
# is the ascending list of token indices at which the resident set
# changes and sets[i] is the frozen set in force from boundaries[i]
# until boundaries[i+1]. Behaviour is carried from
# research/ob2/sim_residency.py; only the return shape differs (that
# file folded the miss count into the policy body, this one separates
# the schedule from the accounting so the accounting can be done at any
# micro-batch shape).
# ---------------------------------------------------------------------

def sched_p0_static(ids_layer, K, E, frozen_set, H):
    return [0], [frozenset(frozen_set)]


def sched_p1_sliding(ids_layer, K, E, W_tokens, H):
    budget = ids_layer.shape[0]
    bounds = []
    sets = []
    t = 0
    while t < budget:
        if t == 0:
            new_resident = frozenset(range(K))
        else:
            lo = max(0, t - W_tokens)
            window = ids_layer[lo:t].reshape(-1)
            counts = np.bincount(window, minlength=E)
            new_resident = frozenset(top_k(counts, K, E))
        bounds.append(t)
        sets.append(new_resident)
        t = min(budget, t + H)
    return bounds, sets


def sched_p2_decay(ids_layer, K, E, H, add=65536, shift=1):
    budget = ids_layer.shape[0]
    counters = [0] * E
    bounds = []
    sets = []
    t = 0
    first = True
    while t < budget:
        if not first:
            counters = [c >> shift for c in counters]
        new_resident = frozenset(range(K)) if first else frozenset(top_k(counters, K, E))
        bounds.append(t)
        sets.append(new_resident)
        first = False
        hi = min(budget, t + H)
        flat = ids_layer[t:hi].reshape(-1)
        bc = np.bincount(flat, minlength=E)
        for e in range(E):
            counters[e] += add * int(bc[e])
        t = hi
    return bounds, sets


# ---------------------------------------------------------------------
# LEASE ACCOUNTING AT MICRO-BATCH SHAPE U.
# ---------------------------------------------------------------------

def resident_at(bounds, sets, t):
    """The resident set in force at token t. bounds is ascending."""
    lo, hi = 0, len(bounds) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if bounds[mid] <= t:
            lo = mid
        else:
            hi = mid - 1
    return sets[lo]


def lease_counts_layer(ids_layer, bounds, sets, U, mode):
    """Returns (events, peak_events_in_one_window, picks, pick_misses).

    mode 'window-start': one route call per U-token window, resident set
      taken at the window's first token.
    mode 'sub-window': the window is split at every policy boundary
      inside it and each piece counted against its own resident set.
    """
    budget = ids_layer.shape[0]
    events = 0
    peak = 0
    pick_misses = 0
    picks = budget * ids_layer.shape[1]
    bset = set(bounds)
    t = 0
    while t < budget:
        hi = min(budget, t + U)
        if mode == "window-start":
            cuts = [t, hi]
        else:
            cuts = [t] + sorted(b for b in bounds if t < b < hi) + [hi]
        win_events = 0
        for i in range(len(cuts) - 1):
            a, b = cuts[i], cuts[i + 1]
            res = resident_at(bounds, sets, a)
            seg = ids_layer[a:b].reshape(-1)
            uniq = np.unique(seg)
            miss = [int(e) for e in uniq if int(e) not in res]
            win_events += len(miss)
            pick_misses += int(np.sum(~np.isin(seg, list(res)))) if res else int(seg.size)
        events += win_events
        if win_events > peak:
            peak = win_events
        t = hi
    return events, peak, picks, pick_misses


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", required=True)
    ap.add_argument("--E", type=int, required=True)
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--budget", type=int, required=True)
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--per-expert", type=int, required=True)
    ap.add_argument("--trunk", type=int, required=True)
    ap.add_argument("--logical", type=int, required=True)
    ap.add_argument("--read-rate", type=int, required=True,
                    help="bytes per second, integer, cited to a receipt")
    ap.add_argument("--ubatch", type=int, action="append", required=True)
    ap.add_argument("--K", type=int, action="append", required=True)
    ap.add_argument("--policy", action="append", required=True,
                    help="P0-STATIC | P1-SLIDING-W<n> | P2-DECAY")
    ap.add_argument("--sets", default=None, help="RESIDENT-SETS json for P0-STATIC")
    ap.add_argument("--H", type=int, default=256)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    route_sha = sha256_of(args.route)
    ids = load_route_log(args.route, args.E, args.L, args.budget, args.k)

    sets_json = None
    sets_sha = "-"
    if args.sets:
        sets_sha = sha256_of(args.sets)
        with open(args.sets, "r") as f:
            sets_json = json.load(f)

    out = open(args.out, "w", newline="\n")

    def w(s=""):
        out.write(s + "\n")
        print(s)

    w("LABEL=%s" % args.label)
    w("ROUTE_LOG=%s" % args.route)
    w("ROUTE_LOG_SHA256=%s" % route_sha)
    w("RESIDENT_SETS_JSON=%s" % (args.sets or "-"))
    w("RESIDENT_SETS_SHA256=%s" % sets_sha)
    w("E=%d L=%d budget=%d k=%d per_expert=%d H=%d" %
      (args.E, args.L, args.budget, args.k, args.per_expert, args.H))
    w("TRUNK_BYTES=%d LOGICAL_BYTES=%d READ_RATE_BYTES_PER_S=%d" %
      (args.trunk, args.logical, args.read_rate))
    w()

    for K in args.K:
        for pol in args.policy:
            # build the schedule once per (K, policy); it does not depend on U
            scheds = []
            for l in range(args.L):
                if pol == "P0-STATIC":
                    if sets_json is None:
                        raise SystemExit("P0-STATIC needs --sets")
                    frozen = sets_json["resident_sets"][str(K)][str(l)]
                    scheds.append(sched_p0_static(ids[l], K, args.E, frozen, args.H))
                elif pol == "P0-EMPTY":
                    # pure streaming: no expert is ever resident (OB-1b's K=0
                    # point). Not a policy so much as the floor every policy is
                    # measured against.
                    scheds.append(sched_p0_static(ids[l], 0, args.E, [], args.H))
                elif pol.startswith("P1-SLIDING-W"):
                    W = int(pol[len("P1-SLIDING-W"):])
                    scheds.append(sched_p1_sliding(ids[l], K, args.E, W, args.H))
                elif pol == "P2-DECAY":
                    scheds.append(sched_p2_decay(ids[l], K, args.E, args.H))
                else:
                    raise SystemExit("unknown policy %s" % pol)

            for U in args.ubatch:
                modes = ["window-start"]
                if len(scheds[0][0]) > 1 and U > args.H:
                    modes.append("sub-window")
                for mode in modes:
                    tot_events = 0
                    peak_events = 0
                    tot_picks = 0
                    tot_pick_misses = 0
                    per_layer = []
                    for l in range(args.L):
                        b, s = scheds[l]
                        e, pk, pc, pm = lease_counts_layer(ids[l], b, s, U, mode)
                        tot_events += e
                        tot_picks += pc
                        tot_pick_misses += pm
                        per_layer.append(e)
                        if pk > peak_events:
                            peak_events = pk
                    lease_bytes = tot_events * args.per_expert
                    peak_conc = peak_events * args.per_expert
                    resident_bytes = K * args.L * args.per_expert
                    acct = args.trunk + resident_bytes + peak_conc
                    bytes_per_token_num = lease_bytes          # integer numerator
                    bytes_per_token_den = args.budget          # integer denominator
                    # read-bound ceiling, tokens per second, at the cited rate:
                    #   ceiling = read_rate / (lease_bytes / budget)
                    w("ROW policy=%s K=%d ubatch=%d mode=%s" % (pol, K, U, mode))
                    w("  route_calls              %d" % (args.L * ((args.budget + U - 1) // U)))
                    w("  lease_events             %d" % tot_events)
                    w("  lease_bytes_read         %d" % lease_bytes)
                    w("  peak_events_one_window   %d" % peak_events)
                    w("  peak_concurrent_bytes    %d" % peak_conc)
                    w("  per_layer_lease_events   %s" % ",".join(str(x) for x in per_layer))
                    w("  picks                    %d" % tot_picks)
                    w("  pick_misses              %d" % tot_pick_misses)
                    w("  pick_miss_pct            %.10f" % (100.0 * tot_pick_misses / tot_picks))
                    w("  resident_expert_bytes    %d" % resident_bytes)
                    w("  ACCT_bytes               %d" % acct)
                    w("  exposure                 %.6f" % (args.logical / acct))
                    w("  bytes_per_token          %.4f   (%d / %d)" %
                      (bytes_per_token_num / bytes_per_token_den,
                       bytes_per_token_num, bytes_per_token_den))
                    w("  read_ms_per_token        %.4f" %
                      (1000.0 * bytes_per_token_num / bytes_per_token_den / args.read_rate))
                    w("  read_bound_tok_s_ceiling %.6f" %
                      (args.read_rate * bytes_per_token_den / bytes_per_token_num))
                    w()

    out.close()


if __name__ == "__main__":
    main()
