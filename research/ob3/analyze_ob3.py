#!/usr/bin/env python3
"""OB-3 analysis step: turn this leg's run directories into the literal rows of RUNLOG-1.txt.

Reads, for every run directory named on the command line:
  ob1-stats.txt  the lease engine's own counters, the OB-3 detector's own
                 recorded classification, and the per-chunk wall times
  identity.txt   the identity artifact (OB-1 prereg section 5: the '[1]' line)
  route.log      the MoE route-id log
  stderr.txt     /usr/bin/time -v output, for peak resident set size

Every number printed here is read from those files. Nothing is estimated.

Definitions are OB-1's, unchanged (research/ob1/analyze.py):
  p95 is the nearest-rank percentile over the per-chunk wall times the engine
  timestamps between successive layer-0 routing callbacks. A 32-chunk run
  yields 31 such intervals, so p95 is the 30th smallest of 31 samples.
  bytes/token = lease_bytes_read / 32768.

The MEASURED miss rate is computed by replaying each run's OWN route log
against the set the detector actually selected, at that run's K, using
research/ob3/sim_predict.py's own loader and comparison (same lineage as the
prereg's simulated table, so measured and simulated are the same statistic).
"""

import hashlib
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_predict  # noqa: E402

TOKENS = 32768

WT = "/mnt/f/f32/openbob-wt/ob3"
SETS = {
    "PROSE": WT + "/research/ob1/RESIDENT-SETS.json",
    "CODE": WT + "/research/ob3/RESIDENT-SETS-CODE.json",
    "MIX": WT + "/research/ob3/RESIDENT-SETS-MIX.json",
}

# OB-1's banked fully-resident references (rs053 binary, 10 threads).
BANK = "/mnt/f/f32/stage/research/ob1/runs"
REF_IDENTITY = {
    "AC-CODE.txt": BANK + "/res-code-a/identity.txt",
    "AC-PROSE.txt": BANK + "/res-prose-a/identity.txt",
}
REF_STATS = {
    "AC-CODE.txt": BANK + "/res-code-a/ob1-stats.txt",
    "AC-PROSE.txt": BANK + "/res-prose-a/ob1-stats.txt",
}

# Sim predictions frozen in OB3-REGION-1-PREREG section 4, keyed
# (selected_set, corpus_basename, K). AC-CODE2 has no sim prediction by
# construction (no route log for it existed before this leg ran).
SIM = {
    ("CODE", "AC-CODE.txt", 16): 14.4536,
    ("CODE", "AC-CODE.txt", 8): 36.9441,
    ("PROSE", "AC-PROSE.txt", 16): 18.8048,
    ("PROSE", "AC-PROSE.txt", 8): 42.3153,
    ("CODE", "AC-PROSE.txt", 16): 54.2367,
    ("PROSE", "AC-CODE.txt", 16): 60.5733,
}


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
            line = line.rstrip("\n")
            if "=" not in line:
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


def load_run(d):
    st = read_stats(os.path.join(d, "ob1-stats.txt"))
    chunk = [int(x) for x in st.get("chunk_ns", "").split(",") if x]
    # The corpus: from the driver's own run-metadata file when present (it is
    # written for every run, leased or resident), else from the detector's
    # recorded input path (leased runs only).
    meta_path = os.path.join(d, "ob3-run.txt")
    meta = read_stats(meta_path) if os.path.exists(meta_path) else {}
    corpus = os.path.basename(meta.get("corpus", "")) or \
        os.path.basename(st.get("ob3_detect_path", "")) or None
    return {
        "corpus_of_run": corpus,
        "name": os.path.basename(d.rstrip("/")),
        "dir": d,
        "mode": st.get("ob1_mode"),
        "k": int(st.get("ob1_k", -1)),
        "detect_on": st.get("ob3_detect") == "1",
        "corpus": corpus,
        "det_class": st.get("ob3_detect_class"),
        "det_score": st.get("ob3_detect_score"),
        "det_PDNL": (st.get("ob3_detect_P"), st.get("ob3_detect_D"),
                     st.get("ob3_detect_N"), st.get("ob3_detect_L")),
        "sets_selected": st.get("ob3_sets_selected"),
        "identity_sha": sha256_file(os.path.join(d, "identity.txt")),
        "route_sha": sha256_file(os.path.join(d, "route.log")),
        "route_lines": sum(1 for _ in open(os.path.join(d, "route.log"), "rb")),
        "rss_kb": peak_rss_kb(os.path.join(d, "stderr.txt")),
        "wall_s": wall_s(os.path.join(d, "stderr.txt")),
        "lease_events": int(st.get("lease_events", 0)),
        "lease_bytes": int(st.get("lease_bytes_read", 0)),
        "peak_lease": int(st.get("peak_concurrent_lease_bytes", 0)),
        "chunk_n": len(chunk),
        "chunk_p50": pct_nearest_rank(chunk, 0.50),
        "chunk_p95": pct_nearest_rank(chunk, 0.95),
        "stats": st,
    }


def set_label(path):
    if not path:
        return None
    for lab, p in SETS.items():
        if os.path.abspath(p) == os.path.abspath(path):
            return lab
    return os.path.basename(path)


def main():
    dirs = sys.argv[1:]
    if not dirs:
        raise SystemExit("usage: analyze_ob3.py <rundir> [rundir ...]")
    runs = [load_run(d) for d in dirs]

    print("== DETECTOR, AS RECORDED BY THE ENGINE ITSELF ==")
    print("%-20s %-14s %5s %4s %4s %4s %5s %7s  %s" % (
        "run", "corpus", "P", "D", "N", "L", "SCORE", "CLASS", "set selected"))
    for r in runs:
        if not r["detect_on"]:
            print("%-20s %-14s %s" % (r["name"], r["corpus"] or "-", "(detector off: resident baseline)"))
            continue
        P, D, N, L = r["det_PDNL"]
        print("%-20s %-14s %5s %4s %4s %4s %5s %7s  %s" % (
            r["name"], r["corpus"], P, D, N, L, r["det_score"], r["det_class"],
            set_label(r["sets_selected"])))

    print()
    print("== IDENTITY ==")
    print("%-20s %-14s %-64s %s" % ("run", "corpus", "identity_sha256", "vs reference"))
    ref_sha = {}
    ref_name = {c: "OB-1 banked res-%s-a" % ("code" if "CODE.txt" in c else "prose")
                for c in REF_IDENTITY}
    # AC-CODE2 has no OB-1 banked reference (OB-1 never ran it), so this leg's
    # own fully-resident r0-res-code2 run IS the reference for that corpus.
    for r in runs:
        if r["mode"] == "resident" and r["corpus_of_run"]:
            if r["corpus_of_run"] not in REF_IDENTITY:
                REF_IDENTITY[r["corpus_of_run"]] = os.path.join(r["dir"], "identity.txt")
                ref_name[r["corpus_of_run"]] = "this leg's own %s" % r["name"]
    for r in runs:
        c = r["corpus"]
        v = "n/a"
        if c in REF_IDENTITY:
            if c not in ref_sha:
                ref_sha[c] = sha256_file(REF_IDENTITY[c])
            v = "%s (%s)" % ("MATCH" if r["identity_sha"] == ref_sha[c] else "DIFFER",
                             ref_name[c])
        print("%-20s %-14s %-64s %s" % (r["name"], c or "-", r["identity_sha"], v))

    print()
    print("== MEASURED MISS RATE (each run's OWN route log vs the set the detector chose) ==")
    print("%-20s %-14s %3s %-6s %11s %10s %10s %9s %9s" % (
        "run", "corpus", "K", "set", "total_picks", "misses", "measured%", "sim%", "delta_pp"))
    measured = {}
    for r in runs:
        if not r["detect_on"]:
            continue
        lab = set_label(r["sets_selected"])
        total, misses, rate = sim_predict.miss_rate(
            r["sets_selected"], os.path.join(r["dir"], "route.log"), r["k"])
        measured[r["name"]] = rate
        key = (lab, r["corpus"], r["k"])
        sim = SIM.get(key)
        simstr = "%.4f" % sim if sim is not None else "none"
        dstr = "%+.4f" % (rate - sim) if sim is not None else "-"
        print("%-20s %-14s %3d %-6s %11d %10d %9.4f%% %9s %9s" % (
            r["name"], r["corpus"], r["k"], lab, total, misses, rate, simstr, dstr))

    print()
    print("== COST ==")
    print("%-20s %3s %-14s %10s %10s %12s %10s %14s %10s" % (
        "run", "K", "corpus", "p50_ms", "p95_ms", "bytes/token", "wall_s", "rss_KB", "leases"))
    for r in runs:
        p50 = (r["chunk_p50"] or 0) / 1e6
        p95 = (r["chunk_p95"] or 0) / 1e6
        bpt = r["lease_bytes"] / float(TOKENS)
        print("%-20s %3d %-14s %10.1f %10.1f %12.1f %10.2f %14d %10d" % (
            r["name"], r["k"], r["corpus"] or "-", p50, p95, bpt,
            r["wall_s"] or 0.0, r["rss_kb"] or 0, r["lease_events"]))

    print()
    print("== COST LIMB (leased p95 / resident p95) ==")
    for c, p in REF_STATS.items():
        st = read_stats(p)
        ch = [int(x) for x in st.get("chunk_ns", "").split(",") if x]
        b = pct_nearest_rank(ch, 0.95)
        print("  OB-1 banked resident baseline %-14s p95=%.1f ms (n=%d, 10 threads)" % (c, b / 1e6, len(ch)))
    local_res = {r["name"]: r for r in runs if r["mode"] == "resident"}
    for n, r in local_res.items():
        print("  this leg's resident baseline  %-14s p95=%.1f ms (n=%d, 8 threads, run %s)" % (
            "AC-CODE2.txt", (r["chunk_p95"] or 0) / 1e6, r["chunk_n"], n))
    print()
    for r in runs:
        if r["mode"] != "lease":
            continue
        c = r["corpus"]
        if c in REF_STATS:
            st = read_stats(REF_STATS[c])
            ch = [int(x) for x in st.get("chunk_ns", "").split(",") if x]
            b = pct_nearest_rank(ch, 0.95)
            ratio = r["chunk_p95"] / float(b)
            print("  %-20s p95 %.1f / %.1f = %.4fx   (vs OB-1 banked 10-thread resident; bar 3.0x at K=16)" % (
                r["name"], r["chunk_p95"] / 1e6, b / 1e6, ratio))
        else:
            for n, rr in local_res.items():
                ratio = r["chunk_p95"] / float(rr["chunk_p95"])
                print("  %-20s p95 %.1f / %.1f = %.4fx   (vs THIS leg's own 8-thread resident %s; report-only)" % (
                    r["name"], r["chunk_p95"] / 1e6, rr["chunk_p95"] / 1e6, ratio, n))

    print()
    print("== A/A ==")
    for a in runs:
        for b in runs:
            if a["name"] >= b["name"]:
                continue
            if a["corpus"] == b["corpus"] and a["k"] == b["k"] and a["mode"] == b["mode"] == "lease":
                print("  %s vs %s: identity %s, route.log %s" % (
                    a["name"], b["name"],
                    "MATCH" if a["identity_sha"] == b["identity_sha"] else "DIFFER",
                    "MATCH" if a["route_sha"] == b["route_sha"] else "DIFFER"))

    print()
    print("== ROUTE LOGS ==")
    for r in runs:
        print("  %-20s lines=%d sha256=%s" % (r["name"], r["route_lines"], r["route_sha"]))


if __name__ == "__main__":
    main()
