#!/usr/bin/env python3
"""OB-2 analysis step: turn the run directories into the literal rows of RUNLOG-1.txt.

Reads, for every run directory under /root/ob2/runs/:
  ob2-stats.txt  the engine's own counters, policy series, and per-chunk wall times
  identity.txt   the identity artifact (the per-chunk PPL line, same as OB-1)
  route.log      the MoE route-id log
  stderr.txt     /usr/bin/time -v output, for peak resident set size

Every number printed here is read from those files or from committed artifacts.
Nothing is estimated.

The three bars, exactly as research/OB2-PREDICTIVE-1-PREREG.md section 9 froze
them:

  IDENTITY (stop-ship): identity artifact AND route log must be byte-identical
    to OB-1's banked fully-resident reference for that corpus. The reference
    digests are computed here from the banked files themselves, not copied from
    a document, so a silently edited reference would show up as a changed digest
    rather than as a pass.

  MISS RATE (report-only): the engine's measured per-pick miss rate must fall
    within 2.0 percentage points of the committed simulator's prediction for the
    same policy/corpus/K. The predictions are parsed out of the committed
    research/ob2/SIM-{PROSE,CODE}-TABLE-1.txt rather than retyped. Because both
    sides consume the same route ids and implement the same integer policy, this
    script also reports whether the two agree EXACTLY (the stronger claim the
    2.0-point bar was set to catch failures of).

  COST: leased p95 <= 3.0x OB-1's own per-corpus fully-resident baseline p95.
    p95 is the nearest-rank percentile over the per-chunk wall times the engine
    timestamps between successive layer-0 routing callbacks. A 32-chunk run
    yields 31 such intervals, so p95 is the 30th smallest of 31 samples --
    identical method and identical baselines to OB-1 (prereg deviation D3).
"""

import hashlib
import math
import os
import re
import sys

RUNS = "/root/ob2/runs"
OB1_STAGE = "/mnt/f/f32/stage/research/ob1/runs"
WT_OB2 = "/mnt/f/f32/openbob-wt/research-2/research/ob2"

LOGICAL = 12109566624
RESIDENT_ALWAYS = 1930678944
PER_EXPERT_PER_LAYER = 13253760
L = 24
TOKENS = 32768

# OB-1's own fully-resident baseline p95, per corpus, from research/ob1/RUNLOG-1.txt
BASELINE_P95_MS = {"prose": 16025.8, "code": 16073.7}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def read_stats(path):
    d = {}
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            d[k] = v
    return d


def peak_rss_kb(path):
    with open(path, "r", errors="replace") as f:
        for line in f:
            m = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", line)
            if m:
                return int(m.group(1))
    return None


def wall_s(path):
    with open(path, "r", errors="replace") as f:
        for line in f:
            m = re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(.+)", line)
            if m:
                t = m.group(1).strip().split(":")
                if len(t) == 2:
                    return float(t[0]) * 60 + float(t[1])
                return float(t[0]) * 3600 + float(t[1]) * 60 + float(t[2])
    return None


def pct_nearest_rank(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = max(1, math.ceil(p * len(s)))
    return s[k - 1]


def load_sim_predictions():
    """Parse the P2-DECAY rows out of the committed simulator tables."""
    pred = {}
    for corpus, fn in (("prose", "SIM-PROSE-TABLE-1.txt"), ("code", "SIM-CODE-TABLE-1.txt")):
        path = os.path.join(WT_OB2, fn)
        with open(path, "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 7 or parts[0] != "P2-DECAY":
                    continue
                # policy corpus K variant total_picks misses miss_pct churn
                K = int(parts[2])
                total_picks = int(parts[-4])
                misses = int(parts[-3])
                pred[(corpus, K)] = (misses, total_picks, 100.0 * misses / total_picks)
    return pred


def corpus_of(n):
    return "code" if "code" in n else "prose"


def main():
    pred = load_sim_predictions()

    ref = {}
    for corpus, name in (("prose", "res-prose-a"), ("code", "res-code-a")):
        d = os.path.join(OB1_STAGE, name)
        ref[corpus] = {
            "name": name,
            "identity_sha": sha256_file(os.path.join(d, "identity.txt")),
            "route_sha": sha256_file(os.path.join(d, "route.log")),
        }

    # Only the acceptance matrix (prereg section 8) is tabulated here. The
    # "unit-*" directory is the 4-chunk schedule/identity unit from step 2: it
    # covers 4096 tokens, not 32768, so its miss rate is a cold-start figure and
    # its 3-sample p95 is not a latency measurement. It is reported in the unit
    # section of RUNLOG-1.txt on its own terms instead of being averaged in here.
    names = [n for n in sorted(os.listdir(RUNS)) if n.startswith("dyn-")]
    rows = []
    for n in names:
        d = os.path.join(RUNS, n)
        sp = os.path.join(d, "ob2-stats.txt")
        ip = os.path.join(d, "identity.txt")
        rp = os.path.join(d, "route.log")
        ep = os.path.join(d, "stderr.txt")
        if not (os.path.exists(sp) and os.path.exists(ip) and os.path.exists(rp)):
            continue
        st = read_stats(sp)
        chunk = [int(x) for x in st.get("chunk_ns", "").split(",") if x]
        rows.append({
            "name": n,
            "k": int(st.get("ob2_k", -1)),
            "policy": st.get("ob2_policy", "none"),
            "identity_sha": sha256_file(ip),
            "route_sha": sha256_file(rp),
            "rss_kb": peak_rss_kb(ep),
            "wall_s": wall_s(ep),
            "picks": int(st.get("ob2_picks", 0)),
            "misses": int(st.get("ob2_misses", 0)),
            "miss_pct": float(st.get("ob2_miss_pct", 0.0)),
            "boundaries": int(st.get("ob2_boundaries", 0)),
            "churn": int(st.get("ob2_churn_symdiff", 0)),
            "promote_events": int(st.get("ob2_promote_events", 0)),
            "evict_events": int(st.get("ob2_evict_events", 0)),
            "evict_bytes": int(st.get("ob2_evict_bytes", 0)),
            "trans_events": int(st.get("ob2_transient_events", 0)),
            "physneed_max": int(st.get("ob2_physneed_max_experts", 0)),
            "physneed_mean": float(st.get("ob2_physneed_mean_experts", 0.0)),
            "lease_events": int(st.get("lease_events", 0)),
            "lease_bytes": int(st.get("lease_bytes_read", 0)),
            "lease_read_ns": int(st.get("lease_read_ns", 0)),
            "lease_verify_ns": int(st.get("lease_verify_ns", 0)),
            "drop_bytes": int(st.get("lease_drop_bytes", 0)),
            "peak_lease": int(st.get("peak_concurrent_lease_bytes", 0)),
            "res_bytes": int(st.get("resident_bytes_loaded", 0)),
            "route_calls": int(st.get("route_calls", 0)),
            "chunk_n": len(chunk),
            "chunk_p50": pct_nearest_rank(chunk, 0.50),
            "chunk_p95": pct_nearest_rank(chunk, 0.95),
            "chunk_max": max(chunk) if chunk else None,
        })

    print("== IDENTITY REFERENCES (OB-1's banked fully-resident runs, re-digested here) ==")
    for c in sorted(ref):
        print("  %-6s %-14s identity=%s" % (c, ref[c]["name"], ref[c]["identity_sha"]))
        print("  %-6s %-14s route   =%s" % ("", "", ref[c]["route_sha"]))

    print()
    print("== PER-RUN ROWS ==")
    hdr = ("run", "K", "corpus", "ident", "route", "misses", "miss_pct",
           "sim_pct", "delta_pp", "leases", "bytes_moved", "B/tok", "wall_s",
           "rss_KB", "p95_ms")
    print("%-24s %3s %-6s %-6s %-6s %10s %9s %9s %9s %8s %14s %9s %8s %10s %9s" % hdr)
    for r in rows:
        c = corpus_of(r["name"])
        ident = "MATCH" if r["identity_sha"] == ref[c]["identity_sha"] else "DIFFER"
        route = "MATCH" if r["route_sha"] == ref[c]["route_sha"] else "DIFFER"
        p = pred.get((c, r["k"]))
        sim_pct = p[2] if p else float("nan")
        delta = r["miss_pct"] - sim_pct if p else float("nan")
        bpt = r["lease_bytes"] / float(TOKENS)
        p95 = r["chunk_p95"] / 1e6 if r["chunk_p95"] else 0.0
        print("%-24s %3d %-6s %-6s %-6s %10d %8.4f%% %8.4f%% %+9.4f %8d %14d %9.1f %8.2f %10d %9.1f" % (
            r["name"], r["k"], c, ident, route, r["misses"], r["miss_pct"],
            sim_pct, delta, r["lease_events"], r["lease_bytes"], bpt,
            r["wall_s"] or 0.0, r["rss_kb"] or 0, p95))

    print()
    print("== MISS-RATE LIMB (prereg section 9: within 2.0 percentage points of the sim) ==")
    for r in rows:
        c = corpus_of(r["name"])
        p = pred.get((c, r["k"]))
        if not p:
            print("  %-24s no simulator prediction for (%s, K=%d)" % (r["name"], c, r["k"]))
            continue
        sim_misses, sim_picks, sim_pct = p
        delta = abs(r["miss_pct"] - sim_pct)
        exact = (r["misses"] == sim_misses and r["picks"] == sim_picks)
        print("  %-24s engine %d/%d = %.6f%%   sim %d/%d = %.6f%%   |delta| %.6f pp  %s  exact_match=%s" % (
            r["name"], r["misses"], r["picks"], r["miss_pct"],
            sim_misses, sim_picks, sim_pct, delta,
            "PASS" if delta <= 2.0 else "FAIL", "YES" if exact else "NO"))

    print()
    print("== POLICY WORK (what the dynamic set actually cost in movement) ==")
    print("%-24s %3s %11s %10s %12s %12s %12s %10s %10s" % (
        "run", "K", "boundaries", "churn", "promotions", "evictions", "transient",
        "phys_max", "phys_mean"))
    for r in rows:
        print("%-24s %3d %11d %10d %12d %12d %12d %10d %10.3f" % (
            r["name"], r["k"], r["boundaries"], r["churn"], r["promote_events"],
            r["evict_events"], r["trans_events"], r["physneed_max"], r["physneed_mean"]))

    print()
    print("== EXPOSURE ==")
    print("%-24s %3s %14s %10s %14s %10s %16s" % (
        "run", "K", "RSS_bytes", "EXP_rss", "ACCT_bytes", "EXP_acct", "peak_lease_bytes"))
    for r in rows:
        rss = (r["rss_kb"] or 0) * 1024
        acct = RESIDENT_ALWAYS + r["k"] * L * PER_EXPERT_PER_LAYER + r["peak_lease"]
        print("%-24s %3d %14d %10.6f %14d %10.6f %16d" % (
            r["name"], r["k"], rss, LOGICAL / float(rss) if rss else 0.0,
            acct, LOGICAL / float(acct), r["peak_lease"]))

    print()
    print("== VERIFY / READ COST ==")
    print("%-24s %14s %14s %16s %16s" % ("run", "read_s", "verify_s", "drop_bytes", "evict_bytes"))
    for r in rows:
        print("%-24s %14.3f %14.3f %16d %16d" % (
            r["name"], r["lease_read_ns"] / 1e9, r["lease_verify_ns"] / 1e9,
            r["drop_bytes"], r["evict_bytes"]))

    print()
    print("== COST LIMB (prereg section 9: leased p95 <= 3.0x OB-1's per-corpus baseline) ==")
    for r in rows:
        c = corpus_of(r["name"])
        b = BASELINE_P95_MS[c]
        if not r["chunk_p95"]:
            continue
        p95 = r["chunk_p95"] / 1e6
        ratio = p95 / b
        print("  %-24s p95 %8.1f ms vs baseline %8.1f ms  ratio %.4f  %s" % (
            r["name"], p95, b, ratio, "PASS" if ratio <= 3.0 else "FAIL"))

    print()
    print("== A/A LIMB (the dynamic policy must be reproducible run to run) ==")
    groups = {}
    for r in rows:
        base = re.sub(r"-(a|b)$", "", r["name"])
        groups.setdefault(base, []).append(r)
    for base, g in sorted(groups.items()):
        if len(g) < 2:
            continue
        first = g[0]
        for other in g[1:]:
            same = (first["identity_sha"] == other["identity_sha"] and
                    first["route_sha"] == other["route_sha"] and
                    first["misses"] == other["misses"])
            print("  %-24s vs %-24s identity+route+misses %s" % (
                first["name"], other["name"], "IDENTICAL" if same else "DIFFER"))


if __name__ == "__main__":
    sys.exit(main())
