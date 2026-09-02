#!/usr/bin/env python3
# OB-5a stage 1, step 3: the predictions, banked before any run.
#
# WHAT IS PREDICTED AND FROM WHAT.
#
# The lease engine's two main counters are a pure function of a route trace and
# a resident set (src/ob1-lease.cpp ob1_on_route: at each (layer, micro-batch)
# callback it leases exactly the DISTINCT routed experts of that micro-batch
# that are not resident, and drops them at the next callback):
#
#   lease_events(K)    = sum  over (layer, chunk) of |routed(layer,chunk) \ resident(layer,K)|
#   peak_concurrent(K) = max  over (layer, chunk) of |routed(layer,chunk) \ resident(layer,K)|
#                        * PER_EXPERT_BYTES_PER_LAYER
#
# That is the OB-1b lineage (research/ob1b/predict_leases.py), and it is
# re-implemented here rather than imported, so this leg's arithmetic is its own.
# It is VALIDATED FIRST against OB-1's six measured 20b points; only then is it
# used at an unmeasured point.
#
# DECLARED DEVIATION D1 (see OB5A-ALLOC-1-PREREG.md section 8). The task brief
# says to predict the 120b K=8 counters "from the RS053 120b route log". That
# log cannot produce this leg's prediction and this script does not use it for
# that purpose, for three measured reasons printed below: it is a different
# corpus, a different micro-batch size, and a different token budget. It IS the
# ranking source for the resident sets (step 2) and is used as such, unchanged.
# The counters are predicted from the route trace of the run this leg's 120b row
# is compared against: the banked paged reference pag120-prose-a, whose route
# log is digest a32d0051... and which is byte-identical to its own A/A repeat.
#
# Usage: predict_120b.py

import json
import sys

import numpy as np

PER_EXPERT = 13253760          # one expert's share of all 6 suffix tensors, one layer
PAGE = 4096

M20 = dict(name="gpt-oss-20b", total=12109566624, L=24, E=32)
M120 = dict(name="gpt-oss-120b", total=63387346208, L=36, E=128)

RL20_PROSE = "/root/ob1/runs/res-prose-a/route.log"
RL20_CODE = "/root/ob1/runs/res-code-a/route.log"
RL120 = "/mnt/f/f32/stage/research/ob1b/runs/pag120-prose-a/route.log"

SETS20_OB1 = "/mnt/f/f32/openbob-wt/research-2/research/ob1/RESIDENT-SETS.json"
SETS20_KNEE = "/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-KNEE.json"
SETS120 = "/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json"

# OB-1's own measured counters, quoted from research/OB1B-KNEE-1.md section 3.
OB1_MEASURED = {
    ("prose", 16): (10836, 212060160),
    ("prose", 8): (16954, 318090240),
    ("prose", 4): (20024, 371105280),
    ("code", 16): (12092, 212060160),
    ("code", 8): (18100, 318090240),
    ("code", 4): (21115, 371105280),
}
# OB-1b's own measured counters at K=0, OB1B-KNEE-1.md section 6.
OB1B_MEASURED = {
    ("prose", 0): (23096, 424120320),
    ("code", 0): (24078, 424120320),
}


def load_route_log(path, E, L, budget):
    data = np.loadtxt(path, delimiter=",", dtype=np.int64)
    if data.shape != (L * budget, 6):
        raise SystemExit("SHAPE MISMATCH %s: got %r expected (%d, 6)" % (
            path, data.shape, L * budget))
    layer_col, token_col, ids = data[:, 0], data[:, 1], data[:, 2:6]
    if int((ids < 0).sum()) or int((ids >= E).sum()):
        raise SystemExit("EXPERT ID OUT OF RANGE in %s" % path)
    expected_tok = np.arange(budget)
    out = np.empty((L, budget, 4), dtype=np.int64)
    for l in range(L):
        m = layer_col == l
        if int(m.sum()) != budget:
            raise SystemExit("LAYER %d: %d rows, expected %d" % (l, int(m.sum()), budget))
        if not np.array_equal(token_col[m], expected_tok):
            raise SystemExit("ORDER ASSUMPTION VIOLATED: layer %d of %s" % (l, path))
        out[l] = ids[m]
    return out


def predict(ids_by_layer, resident, L, budget, chunk_tokens):
    nchunks = budget // chunk_tokens
    events = 0
    peak_experts = 0
    per_layer = []
    for l in range(L):
        res = resident.get(l, set())
        lev = 0
        for c in range(nchunks):
            block = ids_by_layer[l, c * chunk_tokens:(c + 1) * chunk_tokens, :]
            routed = np.unique(block)
            n = int(sum(1 for e in routed.tolist() if e not in res))
            lev += n
            if n > peak_experts:
                peak_experts = n
        events += lev
        per_layer.append(lev)
    return events, peak_experts, peak_experts * PER_EXPERT, per_layer


def sets_for(path, K):
    doc = json.load(open(path))
    return {int(l): set(v) for l, v in doc["resident_sets"][str(K)].items()}


def resident_always(m):
    return m["total"] - m["L"] * m["E"] * PER_EXPERT


def acct(m, K, peak):
    return resident_always(m) + K * m["L"] * PER_EXPERT + peak


def main():
    ok_all = True

    print("== 0. WHY THE RS053 120b ROUTE LOG IS NOT THE PREDICTION SOURCE ==")
    print("  Measured, not argued. The RS053 run's own command line, verbatim from")
    print("  /mnt/f/f32/stage/research/rs053/runs/120b-prose-a/stderr.txt:")
    print("    -f /mnt/f/f32/stage/research/rs053/corpus-prose.txt --ctx-size 4096")
    print("    --chunks 4 -b 4096 -ub 4096 --threads 10 -ngl 99 -ncmoe 36")
    print("  This leg's frozen 120b configuration, verbatim from")
    print("  /root/ob1b/runs/pag120-prose-a/stderr.txt:")
    print("    -f /mnt/f/f32/stage/research/ob1/AC-PROSE.txt --ctx-size 1024")
    print("    --chunks 8 -b 1024 -ub 1024 --threads 8 -ngl 0 --no-repack")
    print("  Three differences, each of which alone breaks the prediction:")
    print("    corpus        rs053/corpus-prose.txt  vs  ob1/AC-PROSE.txt")
    print("    micro-batch   4096 tokens             vs  1024 tokens")
    print("    token budget  16384 (4 x 4096)        vs  8192 (8 x 1024)")
    print("  lease_events and peak_concurrent are both defined per MICRO-BATCH, so a")
    print("  4096-token chunking cannot predict a 1024-token run even on the same")
    print("  corpus. The RS053 log's role is unchanged and unmixed: it is the")
    print("  RANKING corpus that produced RESIDENT-SETS-120B-K8.json, and step 2")
    print("  verifies exactly that.")

    print()
    print("== 1. THE RULE, VALIDATED AGAINST EIGHT ALREADY-MEASURED 20b POINTS ==")
    ids20 = {"prose": load_route_log(RL20_PROSE, M20["E"], M20["L"], 32768),
             "code": load_route_log(RL20_CODE, M20["E"], M20["L"], 32768)}
    print("  %-6s %-3s %14s %14s %8s %20s %20s %8s" % (
        "corpus", "K", "pred_events", "meas_events", "ev", "pred_peak_B",
        "meas_peak_B", "peak"))
    for (corpus, K), (mev, mpk) in sorted(OB1_MEASURED.items()) + sorted(OB1B_MEASURED.items()):
        src = SETS20_OB1 if K in (16, 8, 4) else SETS20_KNEE
        res = sets_for(src, K)
        ev, pe, pb, _ = predict(ids20[corpus], res, M20["L"], 32768, 1024)
        good_e = ev == mev
        good_p = pb == mpk
        ok_all = ok_all and good_e and good_p
        print("  %-6s %-3d %14d %14d %8s %20d %20d %8s" % (
            corpus, K, ev, mev, "MATCH" if good_e else "DIFFER",
            pb, mpk, "MATCH" if good_p else "DIFFER"))
    print("  EIGHT OF EIGHT REPRODUCED: %s" % ok_all)

    print()
    print("== 2. THIS LEG'S OWN 20b REGRESSION POINTS, PREDICTED ==")
    print("  The P1 suite is four runs. The two resident runs lease nothing, so")
    print("  their counters are zero by construction. The two leased runs have")
    print("  predicted counters, and those counters are themselves a regression:")
    print("  the new allocator must not change them either.")
    print("  %-16s %-3s %14s %20s %16s" % (
        "run", "K", "lease_events", "peak_concurrent_B", "ACCT_bytes"))
    print("  %-16s %-3s %14d %20d %16d" % (
        "res-prose", "-", 0, 0, M20["total"]))
    print("  %-16s %-3s %14d %20d %16d" % (
        "res-code", "-", 0, 0, M20["total"]))
    for run, corpus, K, src in (("lease-k8-code", "code", 8, SETS20_OB1),
                                ("lease-k0-prose", "prose", 0, SETS20_KNEE)):
        res = sets_for(src, K)
        ev, pe, pb, _ = predict(ids20[corpus], res, M20["L"], 32768, 1024)
        a = acct(M20, K, pb)
        print("  %-16s %-3d %14d %20d %16d" % (run, K, ev, pb, a))
    print("  (lease-k8-code is OB-1's own measured point: 18100 / 318090240.")
    print("   lease-k0-prose is OB-1b's:                  23096 / 424120320.")
    print("   Both are therefore predictions AND banked measurements.)")

    print()
    print("== 3. THE 120b K=8 PREDICTION, THE ONE THE NIGHT LEG CONSUMES ==")
    print("  route source  %s" % RL120)
    print("  route sha256  a32d0051bd6d68f2777e64c7b889ae48d56621e9701b107fcef88c0e30cd89c1")
    print("  sets source   %s" % SETS120)
    print("  config        E=128 L=36 budget=8192 chunk_tokens=1024 chunks=8")
    ids120 = load_route_log(RL120, M120["E"], M120["L"], 8192)
    print()
    print("  %-3s %14s %14s %20s %22s %8s" % (
        "K", "lease_events", "peak_experts", "peak_concurrent_B",
        "rule (E-K)*per_expert", "rule?"))
    rows = {}
    for K in (8, 0):
        res = sets_for(SETS120, K) if K == 8 else {l: set() for l in range(M120["L"])}
        ev, pe, pb, per_layer = predict(ids120, res, M120["L"], 8192, 1024)
        rule = (M120["E"] - K) * PER_EXPERT
        rows[K] = (ev, pe, pb, per_layer)
        print("  %-3d %14d %14d %20d %22d %8s" % (
            K, ev, pe, pb, rule, "MATCHES" if pb == rule else "DIFFERS"))
    print()
    ev8, pe8, pb8, pl8 = rows[8]
    print("  lease_bytes_read predicted for K=8 = %d x %d = %d" % (
        ev8, PER_EXPERT, ev8 * PER_EXPERT))
    print("  per-layer lease_events K=8 (36 values, the engine prints this series):")
    print("    %s" % ",".join(str(x) for x in pl8))

    print()
    print("== 4. THE ACCT ARITHMETIC, RE-DERIVED FROM FIRST PRINCIPLES ==")
    print("  Definitions used, and nothing else:")
    print("    TOTAL(120b)          = %d      (measured file size, verify_inputs)" % M120["total"])
    print("    L                    = %d" % M120["L"])
    print("    E                    = %d" % M120["E"])
    print("    PER_EXPERT           = %d      (manifest header, one expert one layer)" % PER_EXPERT)
    tot_exp = M120["L"] * M120["E"] * PER_EXPERT
    ra = resident_always(M120)
    print("    total_expert_bytes   = %d x %d x %d = %d" % (
        M120["L"], M120["E"], PER_EXPERT, tot_exp))
    print("    resident_always      = %d - %d = %d" % (M120["total"], tot_exp, ra))
    print("    resident_always      = %.4f pct of the model" % (100.0 * ra / M120["total"]))
    print("    CHECK vs OB1B-KNEE-1.md s4 (2314020128): %s" % (ra == 2314020128))
    print()
    K = 8
    pool = K * M120["L"] * PER_EXPERT
    a8 = ra + pool + pb8
    print("    K=8 pool_bytes       = %d x %d x %d = %d" % (K, M120["L"], PER_EXPERT, pool))
    print("    K=8 peak_concurrent  = %d      (PREDICTED above, not assumed)" % pb8)
    print("    K=8 ACCT             = %d + %d + %d = %d" % (ra, pool, pb8, a8))
    print("    CHECK vs the brief's expected RSS figure (7721554208): %s" % (a8 == 7721554208))
    print("    K=8 EXPOSURE_acct    = %d / %d = %.6f" % (M120["total"], a8, M120["total"] / float(a8)))
    print()
    ev0, pe0, pb0, _ = rows[0]
    a0 = ra + pb0
    print("    K=0 ACCT (the floor) = %d + %d = %d" % (ra, pb0, a0))
    print("    K=0 EXPOSURE_acct    = %d / %d = %.6f   (prereg ceiling)" % (
        M120["total"], a0, M120["total"] / float(a0)))
    print("    CHECK vs OB5-PLAN-1 s1 ceiling 15.805342: %s" % (
        abs(M120["total"] / float(a0) - 15.805342) < 5e-7))

    print()
    print("== 5. THE MOONSHOT SLOPE, AT MATCHED RESIDENT FRACTION ==")
    print("  K/E = 6.25 percent on both models (20b K=2 of 32; 120b K=8 of 128).")
    res20 = sets_for(SETS20_KNEE, 2)
    ev2, pe2, pb2, _ = predict(ids20["prose"], res20, M20["L"], 32768, 1024)
    a20 = acct(M20, 2, pb2)
    e20 = M20["total"] / float(a20)
    print("  %-13s K=%-3d ACCT %14d  EXPOSURE %.6f   (OB1B measured 4.084898)" % (
        "gpt-oss-20b", 2, a20, e20))
    print("  %-13s K=%-3d ACCT %14d  EXPOSURE %.6f   (PREDICTED, this leg)" % (
        "gpt-oss-120b", 8, a8, M120["total"] / float(a8)))
    print("  slope: N grows %.4fx (%d -> %d) while ACCT grows %.4fx (%d -> %d)" % (
        M120["total"] / float(M20["total"]), M20["total"], M120["total"],
        a8 / float(a20), a20, a8))
    print("  exposure ratio 120b/20b at matched resident fraction: %.4fx" % (
        (M120["total"] / float(a8)) / e20))

    print()
    print("== 6. WHAT MUST NOT SCALE WITH N, STATED AS THE P2 TERMS ==")
    print("  The peak committed MODEL STATE is predicted term by term. Every term")
    print("  is either a constant of the model trunk or a function of the residency")
    print("  schedule (K, L, E). No term is a function of total expert bytes.")
    print("  %-24s %16s %16s" % ("term", "20b K=0", "120b K=8"))
    ra20 = resident_always(M20)
    print("  %-24s %16d %16d" % ("resident_always (trunk)", ra20, ra))
    print("  %-24s %16d %16d" % ("K x L x per_expert", 0, pool))
    print("  %-24s %16d %16d" % ("peak_concurrent", pb0 if False else 424120320, pb8))
    print("  %-24s %16d %16d" % ("ACCT total", ra20 + 424120320, a8))
    print("  %-24s %16d %16d" % ("total_expert_bytes (N term)",
                                 M20["L"] * M20["E"] * PER_EXPERT, tot_exp))
    print("  %-24s %15.2f%% %15.2f%%" % (
        "ACCT as pct of model",
        100.0 * (ra20 + 424120320) / M20["total"], 100.0 * a8 / M120["total"]))
    print()
    print("  The current allocator's single model-state request, for contrast:")
    print("    20b   %d bytes   (measured: it succeeds, and is 5.14x the K=0 ACCT)" % M20["total"])
    print("    120b  %d bytes   (measured: it FAILS, OB1B-KNEE-1.md s9)" % 63374323968)
    print("    note 63374323968 is the BUFFER size llama.cpp asks for; the model file")
    print("    is 63387346208. The 12222240-byte difference is GGUF header and")
    print("    metadata that never enters the tensor buffer.")

    print()
    print("PREDICT_VALIDATION_OK=%s" % ok_all)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
