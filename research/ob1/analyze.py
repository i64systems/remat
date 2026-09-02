#!/usr/bin/env python3
"""OB-1 stage 2: turn the run directories into the literal rows of RUNLOG-1.txt.

Reads, for every run directory under /root/ob1/runs/:
  ob1-stats.txt  the lease engine's own counters and per-chunk wall times
  identity.txt   the identity artifact (prereg section 5)
  route.log      the MoE route-id log
  stderr.txt     /usr/bin/time -v output, for peak resident set size

Every number printed here is read from those files. Nothing is estimated.

Definitions used below, all from research/OB1-EXPOSURE-1-PREREG.md section 7:
  LOGICAL               12109566624  bytes of the GGUF on disk
  resident_always       1930678944   LOGICAL minus all fused expert tensors
  PER_EXPERT_PER_LAYER  13253760     one expert's bytes across the 6 suffixes
  RESIDENT_accounted(K) = resident_always + K*24*PER_EXPERT_PER_LAYER
                          + peak_concurrent_lease_bytes   (measured, not assumed)
  CAPACITY EXPOSURE     = LOGICAL / RESIDENT

p95 is the nearest-rank percentile over the per-chunk wall times the engine
timestamps between successive layer-0 routing callbacks. A 32-chunk run yields
31 such intervals (the last chunk has no following layer-0 callback to close
it), so p95 is the 30th smallest of 31 samples.
"""

import hashlib
import os
import re
import sys

RUNS = "/root/ob1/runs"
LOGICAL = 12109566624
RESIDENT_ALWAYS = 1930678944
PER_EXPERT_PER_LAYER = 13253760
L = 24
TOKENS = 32768


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
    import math
    k = max(1, math.ceil(p * len(s)))
    return s[k - 1]


def main():
    names = sorted(os.listdir(RUNS))
    rows = []
    for n in names:
        d = os.path.join(RUNS, n)
        sp = os.path.join(d, "ob1-stats.txt")
        ip = os.path.join(d, "identity.txt")
        rp = os.path.join(d, "route.log")
        ep = os.path.join(d, "stderr.txt")
        if not (os.path.exists(sp) and os.path.exists(ip) and os.path.exists(rp)):
            continue
        st = read_stats(sp)
        chunk = [int(x) for x in st.get("chunk_ns", "").split(",") if x]
        r = {
            "name": n,
            "mode": st.get("ob1_mode"),
            "k": int(st.get("ob1_k", -1)),
            "fadv": int(st.get("ob1_fadvise", 0)),
            "identity_sha": sha256_file(ip),
            "route_sha": sha256_file(rp),
            "rss_kb": peak_rss_kb(ep),
            "wall_s": wall_s(ep),
            "lease_events": int(st.get("lease_events", 0)),
            "lease_bytes": int(st.get("lease_bytes_read", 0)),
            "lease_read_ns": int(st.get("lease_read_ns", 0)),
            "lease_verify_ns": int(st.get("lease_verify_ns", 0)),
            "drop_bytes": int(st.get("lease_drop_bytes", 0)),
            "peak_lease": int(st.get("peak_concurrent_lease_bytes", 0)),
            "res_bytes": int(st.get("resident_bytes_loaded", 0)),
            "res_verify_ns": int(st.get("resident_verify_ns", 0)),
            "route_calls": int(st.get("route_calls", 0)),
            "chunk_n": len(chunk),
            "chunk_p50": pct_nearest_rank(chunk, 0.50),
            "chunk_p95": pct_nearest_rank(chunk, 0.95),
            "chunk_max": max(chunk) if chunk else None,
            "chunk_sum": sum(chunk) if chunk else 0,
        }
        rows.append(r)

    def corpus_of(n):
        return "code" if "code" in n else "prose"

    ref = {}
    for r in rows:
        if r["mode"] == "resident" and r["name"].endswith("-a"):
            ref[corpus_of(r["name"])] = r

    print("== IDENTITY REFERENCES (this leg's fully resident CPU runs) ==")
    for c, r in sorted(ref.items()):
        print("  %-6s %-22s identity=%s" % (c, r["name"], r["identity_sha"]))
        print("  %-6s %-22s route   =%s" % ("", "", r["route_sha"]))

    print()
    print("== PER-RUN ROWS ==")
    hdr = ("run", "K", "corpus", "tok", "ident", "route", "leases", "bytes_moved",
           "B/tok", "wall_s", "rss_KB", "p50_ms", "p95_ms", "p95/tok_us")
    print("%-22s %3s %-6s %6s %-6s %-6s %8s %14s %8s %8s %10s %8s %8s %10s" % hdr)
    for r in rows:
        c = corpus_of(r["name"])
        rr = ref.get(c)
        if rr is None:
            ident = "n/a"
            route = "n/a"
        else:
            ident = "MATCH" if r["identity_sha"] == rr["identity_sha"] else "DIFFER"
            route = "MATCH" if r["route_sha"] == rr["route_sha"] else "DIFFER"
        bpt = r["lease_bytes"] / float(TOKENS)
        p50 = r["chunk_p50"] / 1e6 if r["chunk_p50"] else 0.0
        p95 = r["chunk_p95"] / 1e6 if r["chunk_p95"] else 0.0
        p95tok = (r["chunk_p95"] / 1024.0 / 1e3) if r["chunk_p95"] else 0.0
        print("%-22s %3d %-6s %6d %-6s %-6s %8d %14d %8.1f %8.2f %10d %8.1f %8.1f %10.1f" % (
            r["name"], r["k"], c, TOKENS, ident, route, r["lease_events"],
            r["lease_bytes"], bpt, r["wall_s"] or 0.0, r["rss_kb"] or 0,
            p50, p95, p95tok))

    print()
    print("== EXPOSURE ==")
    print("%-22s %3s %14s %10s %14s %10s %16s" % (
        "run", "K", "RSS_bytes", "EXP_rss", "ACCT_bytes", "EXP_acct", "peak_lease_bytes"))
    for r in rows:
        rss = (r["rss_kb"] or 0) * 1024
        if r["mode"] == "lease":
            acct = RESIDENT_ALWAYS + r["k"] * L * PER_EXPERT_PER_LAYER + r["peak_lease"]
        else:
            acct = LOGICAL
        print("%-22s %3d %14d %10.6f %14d %10.6f %16d" % (
            r["name"], r["k"], rss, LOGICAL / float(rss) if rss else 0.0,
            acct, LOGICAL / float(acct), r["peak_lease"]))

    print()
    print("== VERIFY / READ COST (lease runs) ==")
    print("%-22s %14s %14s %14s %14s" % (
        "run", "read_s", "verify_s", "drop_bytes", "res_verify_s"))
    for r in rows:
        if r["mode"] != "lease":
            continue
        print("%-22s %14.3f %14.3f %14d %14.3f" % (
            r["name"], r["lease_read_ns"] / 1e9, r["lease_verify_ns"] / 1e9,
            r["drop_bytes"], r["res_verify_ns"] / 1e9))

    print()
    print("== COST LIMB (prereg section 8: leased p95 <= 3.0x baseline p95 at K=16) ==")
    base = {}
    for r in rows:
        if r["mode"] == "resident" and r["name"].endswith("-a"):
            base[corpus_of(r["name"])] = r["chunk_p95"]
    for r in rows:
        if r["mode"] != "lease":
            continue
        b = base.get(corpus_of(r["name"]))
        if not b or not r["chunk_p95"]:
            continue
        ratio = r["chunk_p95"] / float(b)
        print("  %-22s p95 %8.1f ms vs baseline %8.1f ms  ratio %.4f  %s" % (
            r["name"], r["chunk_p95"] / 1e6, b / 1e6, ratio,
            "PASS" if ratio <= 3.0 else "FAIL"))


if __name__ == "__main__":
    sys.exit(main())
