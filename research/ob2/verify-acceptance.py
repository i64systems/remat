#!/usr/bin/env python3
"""OB-2 stage 3: independent acceptance re-verification.

Re-derives every number the acceptance bars depend on directly from the
off-repo run artifacts, without importing or trusting analyze_ob2.py's own
arithmetic (a separate implementation checking the same claims). Nothing
here is copied from RUNLOG-1.txt; every figure is recomputed from the
underlying files.

Adds one thing analyze_ob2.py does not compute: a whole-model PEAK and MEAN
pool-bytes figure and their exposure bases, side by side with the existing
ACCT and RSS bases. See section "POOL BYTES (peak and mean)" in the output
and OB2-PREDICTIVE-1.md section 7 for the derivation and why a naive
sum-of-physneed-over-24-layers is NOT used (it double-counts: the engine
drops a layer's transient leases before the next layer's routing, so at
most one layer's transient pool is concurrently resident with the 24
layers' worth of ALWAYS-resident K-sized sets, never 24 layers' worth of
transient pools at once).

Usage: verify-acceptance.py [--runs-dir DIR] [--ob1-dir DIR]
Defaults match the off-repo layout named in RUNLOG-1.txt section 10.
"""
import argparse
import hashlib
import math
import os
import re

LOGICAL = 12109566624
RESIDENT_ALWAYS = 1930678944
PER_EXPERT = 13253760
L = 24
TOKENS = 32768
BASELINE_P95_MS = {"prose": 16025.8, "code": 16073.7}
COST_BAR = 3.0
MISSRATE_BAR_PP = 2.0

DYN_RUNS = ["dyn-k16-code-a", "dyn-k16-code-b", "dyn-k16-prose",
            "dyn-k8-code", "dyn-k8-prose"]

# P2-DECAY predictions, parsed fresh from the committed simulator tables
# (not retyped), same method as analyze_ob2.py.
def load_sim_predictions(ob2_wt_dir):
    pred = {}
    for corpus, fn in (("prose", "SIM-PROSE-TABLE-1.txt"), ("code", "SIM-CODE-TABLE-1.txt")):
        path = os.path.join(ob2_wt_dir, fn)
        with open(path) as f:
            for line in f:
                parts = line.split()
                if len(parts) < 7 or parts[0] != "P2-DECAY":
                    continue
                K = int(parts[2])
                total_picks = int(parts[-4])
                misses = int(parts[-3])
                pred[(corpus, K)] = (misses, total_picks, 100.0 * misses / total_picks)
    return pred


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def read_stats(path):
    d = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            d[k] = v
    return d


def pct_nearest_rank(vals, p):
    s = sorted(vals)
    k = max(1, math.ceil(p * len(s)))
    return s[k - 1]


def corpus_of(name):
    return "code" if "code" in name else "prose"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", default="/mnt/f/f32/stage/research/ob2/runs")
    ap.add_argument("--ob1-runs-dir", default="/mnt/f/f32/stage/research/ob1/runs")
    ap.add_argument("--ob2-wt-dir", default="/mnt/f/f32/openbob-wt/research-2/research/ob2")
    args = ap.parse_args()

    pred = load_sim_predictions(args.ob2_wt_dir)

    ref = {}
    for corpus, name in (("prose", "res-prose-a"), ("code", "res-code-a")):
        d = os.path.join(args.ob1_runs_dir, name)
        ref[corpus] = {
            "identity_sha": sha256_file(os.path.join(d, "identity.txt")),
            "route_sha": sha256_file(os.path.join(d, "route.log")),
        }

    print("== IDENTITY REFERENCES (re-hashed from OB-1 banked runs) ==")
    for c in sorted(ref):
        print("  %-6s identity=%s route=%s" % (c, ref[c]["identity_sha"], ref[c]["route_sha"]))

    print()
    print("== PER-RUN INDEPENDENT RE-VERIFICATION ==")
    hdr = ("run", "K", "corpus", "ident", "route", "miss_pct", "sim_pct",
           "delta_pp", "exact", "p95_ms", "cost_ratio", "cost")
    print("%-16s %3s %-6s %-6s %-6s %10s %10s %9s %6s %10s %10s %-5s" % hdr)
    rows = []
    all_pass = True
    for name in DYN_RUNS:
        d = os.path.join(args.runs_dir, name)
        st = read_stats(os.path.join(d, "ob2-stats.txt"))
        identity_sha = sha256_file(os.path.join(d, "identity.txt"))
        route_sha = sha256_file(os.path.join(d, "route.log"))
        c = corpus_of(name)
        k = int(st["ob2_k"])
        ident_ok = identity_sha == ref[c]["identity_sha"]
        route_ok = route_sha == ref[c]["route_sha"]
        misses = int(st["ob2_misses"])
        picks = int(st["ob2_picks"])
        miss_pct = 100.0 * misses / picks
        sim_misses, sim_picks, sim_pct = pred[(c, k)]
        delta = miss_pct - sim_pct
        exact = (misses == sim_misses and picks == sim_picks)
        chunk = [int(x) for x in st["chunk_ns"].split(",")]
        p95_ms = pct_nearest_rank(chunk, 0.95) / 1e6
        ratio = p95_ms / BASELINE_P95_MS[c]
        cost_ok = ratio <= COST_BAR
        ok = ident_ok and route_ok and exact and cost_ok
        all_pass = all_pass and ok
        print("%-16s %3d %-6s %-6s %-6s %9.4f%% %9.4f%% %+9.4f %6s %10.1f %9.4fx %-5s" % (
            name, k, c, "MATCH" if ident_ok else "DIFFER",
            "MATCH" if route_ok else "DIFFER", miss_pct, sim_pct, delta,
            "YES" if exact else "NO", p95_ms, ratio,
            "PASS" if cost_ok else "FAIL"))
        rows.append({
            "name": name, "k": k, "corpus": c, "miss_pct": miss_pct,
            "misses": misses, "picks": picks, "peak_lease": int(st["peak_concurrent_lease_bytes"]),
            "physneed_max": int(st["ob2_physneed_max_experts"]),
            "physneed_mean": float(st["ob2_physneed_mean_experts"]),
            "rss_source": None,
        })

    print()
    print("== A/A LIMB (dyn-k16-code-a vs dyn-k16-code-b) ==")
    a = read_stats(os.path.join(args.runs_dir, "dyn-k16-code-a", "ob2-stats.txt"))
    b = read_stats(os.path.join(args.runs_dir, "dyn-k16-code-b", "ob2-stats.txt"))
    ida = sha256_file(os.path.join(args.runs_dir, "dyn-k16-code-a", "identity.txt"))
    idb = sha256_file(os.path.join(args.runs_dir, "dyn-k16-code-b", "identity.txt"))
    rta = sha256_file(os.path.join(args.runs_dir, "dyn-k16-code-a", "route.log"))
    rtb = sha256_file(os.path.join(args.runs_dir, "dyn-k16-code-b", "route.log"))
    aa_ok = (ida == idb and rta == rtb and a["ob2_misses"] == b["ob2_misses"])

    print("  identity match: %s   route match: %s   misses match: %s -> %s" % (
        ida == idb, rta == rtb, a["ob2_misses"] == b["ob2_misses"],
        "IDENTICAL" if aa_ok else "DIFFER"))

    print()
    print("== POOL BYTES (peak and mean, whole model, two independent derivations) ==")
    print("Peak: RESIDENT_ALWAYS + K*L*PER_EXPERT + peak_concurrent_lease_bytes")
    print("      (the engine's own measured peak simultaneous transient-lease bytes")
    print("      for whichever ONE layer is currently being computed, added to the")
    print("      K-per-layer resident sets which ARE concurrent across all L layers).")
    print("Mean: RESIDENT_ALWAYS + K*L*PER_EXPERT + (physneed_mean_experts - K)*PER_EXPERT")
    print("      (physneed_mean_experts is the engine's per-layer, per-ubatch mean of")
    print("      the union of resident+transient experts needed; subtracting K isolates")
    print("      the transient portion, applied to one active layer at a time, matching")
    print("      the same single-active-layer model as the peak formula above -- NOT")
    print("      multiplied by L again, which would double-count the resident term.)")
    print()
    print("%-16s %3s %13s %9s   %13s %9s   %13s %9s" % (
        "run", "K", "peak_pool", "EXP_peak", "mean_pool", "EXP_mean", "RSS_peak", "EXP_rss"))
    for r in rows:
        d = os.path.join(args.runs_dir, r["name"])
        rss_kb = None
        with open(os.path.join(d, "stderr.txt"), errors="replace") as f:
            for line in f:
                m = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", line)
                if m:
                    rss_kb = int(m.group(1))
        rss_bytes = rss_kb * 1024
        resident_expert_pool = r["k"] * L * PER_EXPERT
        peak_pool = RESIDENT_ALWAYS + resident_expert_pool + r["peak_lease"]
        transient_mean_bytes = (r["physneed_mean"] - r["k"]) * PER_EXPERT
        mean_pool = RESIDENT_ALWAYS + resident_expert_pool + transient_mean_bytes
        print("%-16s %3d %13.0f %9.6f   %13.1f %9.6f   %13d %9.6f" % (
            r["name"], r["k"], peak_pool, LOGICAL / peak_pool,
            mean_pool, LOGICAL / mean_pool, rss_bytes, LOGICAL / rss_bytes))

    print()
    print("ALL_LIMBS_PASS=%s" % all_pass)


if __name__ == "__main__":
    main()
