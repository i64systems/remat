#!/usr/bin/env python3
# OB-5b S1 gate 0: THE TOP-8 MASS READ.
#
# Analysis only. Reads BANKED RS053 route logs and the BANKED OB-1b resident
# set file. Loads no model, takes no runlock, contacts no serve, writes nothing
# outside its own --out path.
#
# What it answers, per OB5-DESIGN-C4-1.md section 12 gate 0:
#   (1) the routing mass captured by the top-8 popularity-ranked experts per
#       layer, per layer and run-level;
#   (2) the per-token hit rate a K=8 resident set would achieve on a
#       SINGLE-TOKEN DECODE schedule, which is the one UNMEASURED term in every
#       projection of C4 section 2.3.
#
# Frozen definitions used here, stated so a reader can re-apply them:
#   A DECISION is one (layer, token, slot) routing selection. A run of budget T
#   tokens over L layers with k selections per (token, layer) has L*T*k
#   decisions. gpt-oss.expert_used_count = 4, so k = 4.
#   MASS(R, l) = sum over e in R_l of c_l(e), divided by T*k. Because every
#   expert tensor in this GGUF layout is the same byte size (13253760,
#   RS053 RUNLOG-1 section 5), mass is simultaneously the decision hit rate and
#   the byte hit rate. It is NOT the same as a per-token hit rate when the k
#   selections of one token are not distinct; section VERIFY below proves they
#   are distinct in these logs, so mass == mean per-token hit rate exactly.
#   MISSES_PER_TOKEN = sum over layers of (k - |ids(t,l) INTERSECT R_l|).
#   DROP-ON-USE is the residency model of C4 projection P-A: a leased expert is
#   released after the token that needed it, so every non-resident selection is
#   a fresh lease.
#   KEEP-PREVIOUS is a declared EXTRA beyond the gate bar (C4 section 2.2: "A
#   lease taken for token t helps token t+1 only if the runtime KEEPS it"): the
#   experts of token t-1 at that layer are still held, so a selection misses
#   only when it is neither resident nor used by the previous token.
#
# Ranking rule, copied from the banked lineage (RESIDENT-SETS-120B-K8.json:
# lineage "research/ob1/resident_sets.py (same loader, same ranking rule, same
# tie-break)", tie_break "lower expert id"): sort by count descending, ties
# broken by lower expert id, take the first K.
#
# Output is a deterministic JSON document (sort_keys, fixed float repr) so two
# runs on the same inputs are byte-identical.

import argparse
import hashlib
import json
import os
import sys

import numpy as np

K_USED = 4  # gpt-oss.expert_used_count, frozen fact (RS053 prereg fact table)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def load_route_log(path):
    """Return (layers, rows) as int64 arrays. Row = layer, token_index, e0..e3."""
    with open(path, "r") as f:
        txt = f.read()
    flat = np.fromstring(txt.replace(",", " "), sep=" ", dtype=np.int64)
    if flat.size % (2 + K_USED) != 0:
        sys.exit("ROUTE LOG SHAPE: %d numbers is not a multiple of %d"
                 % (flat.size, 2 + K_USED))
    return flat.reshape(-1, 2 + K_USED)


def rank_topk(counts, K):
    """Popularity rank: count descending, tie-break lower expert id. First K."""
    ids = np.arange(counts.shape[0], dtype=np.int64)
    order = np.lexsort((ids, -counts))
    return np.sort(order[:K])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--sets", required=True,
                    help="banked resident-set JSON (the K=8 prose-ranked sets)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ksweep", default="8,16,24,32,48,64")
    args = ap.parse_args()

    rows = load_route_log(args.route)
    layers = rows[:, 0]
    L = int(layers.max()) + 1
    experts_all = rows[:, 2:]
    E = int(experts_all.max()) + 1
    # E is the observed maximum; take the declared E from the sets file below and
    # cross-check, never the other way round.

    with open(args.sets, "r") as f:
        sets_doc = json.load(f)
    E_decl = int(sets_doc["E"])
    L_decl = int(sets_doc["L"])
    budget_decl = int(sets_doc["budget"])
    per_expert_bytes = int(sets_doc["per_expert_bytes_per_layer"])
    # resident_sets is {K_str: {layer_str: [expert ids]}}
    banked_sets = {}
    for k_str, by_layer in sets_doc["resident_sets"].items():
        banked_sets[int(k_str)] = [
            sorted(int(x) for x in by_layer[str(l)])
            for l in range(L_decl)
        ]

    if E > E_decl:
        sys.exit("EXPERT ID OUT OF RANGE: observed max id %d, declared E %d"
                 % (E - 1, E_decl))
    E = E_decl
    if L != L_decl:
        sys.exit("SHAPE MISMATCH: route log has %d layers, sets file declares %d"
                 % (L, L_decl))

    # --- per-layer split, file-order preserving, with the RS053 order check ---
    per_layer_ids = []
    T = None
    for l in range(L):
        m = layers == l
        idx = rows[m, 1]
        ids = experts_all[m]
        if T is None:
            T = idx.shape[0]
        elif idx.shape[0] != T:
            sys.exit("SHAPE MISMATCH: layer %d has %d rows, layer 0 has %d"
                     % (l, idx.shape[0], T))
        if not np.array_equal(idx, np.arange(T, dtype=np.int64)):
            sys.exit("ORDER ASSUMPTION VIOLATED at layer %d" % l)
        per_layer_ids.append(ids)
    if T != budget_decl:
        sys.exit("BUDGET MISMATCH: route log budget %d, sets file %d"
                 % (T, budget_decl))

    # --- k selections per (token, layer) must be DISTINCT for mass == hit rate ---
    dup_rows = 0
    for l in range(L):
        ids = per_layer_ids[l]
        s = np.sort(ids, axis=1)
        dup_rows += int((s[:, 1:] == s[:, :-1]).any(axis=1).sum())
    if dup_rows != 0:
        sys.exit("DUPLICATE EXPERT IN A TOKEN'S TOP-k: %d rows" % dup_rows)

    counts = np.zeros((L, E), dtype=np.int64)
    for l in range(L):
        counts[l] = np.bincount(per_layer_ids[l].ravel(), minlength=E)

    total_decisions_per_layer = T * K_USED
    total_decisions = L * total_decisions_per_layer

    # --- the resident set under test: the BANKED K=8 set, verified re-derivable
    banked8 = banked_sets[8]
    rederived8 = [rank_topk(counts[l], 8).tolist() for l in range(L)]
    banked_match = (rederived8 == banked8)

    R8 = np.zeros((L, E), dtype=bool)
    for l in range(L):
        R8[l, banked8[l]] = True

    per_layer = []
    misses_tok = np.zeros(T, dtype=np.int64)
    misses_tok_keep = np.zeros(T, dtype=np.int64)
    for l in range(L):
        ids = per_layer_ids[l]
        hit = R8[l][ids]                      # (T, k) bool
        hits_layer = int(hit.sum())
        mass = hits_layer / float(total_decisions_per_layer)
        misses_tok += (K_USED - hit.sum(axis=1))

        # keep-previous (declared extra)
        prev_hit = np.zeros_like(hit)
        prev_hit[1:] = (ids[1:, :, None] == ids[:-1, None, :]).any(axis=2)
        keep_hit = hit | prev_hit
        misses_tok_keep += (K_USED - keep_hit.sum(axis=1))

        top8_counts = counts[l][banked8[l]]
        per_layer.append({
            "layer": l,
            "resident_ids": banked8[l],
            "resident_counts": [int(x) for x in top8_counts],
            "top8_decisions_hit": hits_layer,
            "layer_decisions": total_decisions_per_layer,
            "top8_mass": mass,
            "miss_rate": 1.0 - mass,
            "mean_misses_per_token": float((K_USED - hit.sum(axis=1)).mean()),
            "dead_experts_at_1pct": int(
                (counts[l] < 0.01 * total_decisions_per_layer).sum()),
            "rank1_count": int(counts[l].max()),
            "rank1_share": float(counts[l].max()) / total_decisions_per_layer,
        })

    hits_total = sum(p["top8_decisions_hit"] for p in per_layer)
    run_mass = hits_total / float(total_decisions)
    run_miss = 1.0 - run_mass

    # --- K sweep on the SAME popularity ranking derived from THIS log's counts
    ksweep = {}
    for K in [int(x) for x in args.ksweep.split(",")]:
        if K > E:
            continue
        hitK = 0
        for l in range(L):
            RK = np.zeros(E, dtype=bool)
            RK[rank_topk(counts[l], K)] = True
            hitK += int(RK[per_layer_ids[l]].sum())
        m = hitK / float(total_decisions)
        ksweep[str(K)] = {
            "K": K,
            "self_ranked_mass": m,
            "self_ranked_miss_rate": 1.0 - m,
            "misses_per_token": (1.0 - m) * L * K_USED,
        }

    # --- K sweep using the BANKED prose-ranked sets is only possible at K=8
    # (the banked file holds K=8 alone), so it is not attempted here.

    doc = {
        "gate": "OB5B-S1-GATE0",
        "label": args.label,
        "route_log": os.path.abspath(args.route),
        "route_log_sha256": sha256_file(args.route),
        "sets_file": os.path.abspath(args.sets),
        "sets_file_sha256": sha256_file(args.sets),
        "sets_source_route_log": sets_doc.get("source_route_log"),
        "sets_ranking_corpus": sets_doc.get("ranking_corpus"),
        "L": L,
        "E": E,
        "budget_tokens": T,
        "k_used": K_USED,
        "per_expert_bytes_per_layer": per_expert_bytes,
        "total_decisions": total_decisions,
        "banked_k8_set_rederives_from_this_log": bool(banked_match),
        "duplicate_expert_rows": dup_rows,
        "run": {
            "top8_decisions_hit": hits_total,
            "top8_mass": run_mass,
            "miss_rate": run_miss,
            "mean_misses_per_token_drop_on_use": float(misses_tok.mean()),
            "min_misses_per_token_drop_on_use": int(misses_tok.min()),
            "max_misses_per_token_drop_on_use": int(misses_tok.max()),
            "p50_misses_per_token_drop_on_use": float(np.percentile(
                misses_tok, 50, method="nearest")),
            "p95_misses_per_token_drop_on_use": float(np.percentile(
                misses_tok, 95, method="nearest")),
            "mean_misses_per_token_keep_previous": float(misses_tok_keep.mean()),
            "max_misses_per_token_keep_previous": int(misses_tok_keep.max()),
            "layer_mean_top8_mass": float(
                np.mean([p["top8_mass"] for p in per_layer])),
            "layer_min_top8_mass": float(
                min(p["top8_mass"] for p in per_layer)),
            "layer_max_top8_mass": float(
                max(p["top8_mass"] for p in per_layer)),
        },
        "ksweep_self_ranked": ksweep,
        "per_layer": per_layer,
    }

    with open(args.out, "w") as f:
        json.dump(doc, f, sort_keys=True, indent=1)
        f.write("\n")
    print("WROTE %s" % args.out)
    print("label %s  L %d  E %d  budget %d  decisions %d"
          % (args.label, L, E, T, total_decisions))
    print("banked_k8_set_rederives_from_this_log %s" % banked_match)
    print("run top8_mass %.10f  miss_rate %.10f" % (run_mass, run_miss))
    print("mean misses/token drop-on-use %.10f  keep-previous %.10f"
          % (misses_tok.mean(), misses_tok_keep.mean()))


if __name__ == "__main__":
    main()
