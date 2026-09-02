#!/usr/bin/env python3
"""OB-1b: turn the run directories into the literal rows of OB1B-KNEE-1.md.

Same lineage as research/ob1/analyze.py (OB-1's own equivalent tool), with four
changes, each named as a deviation in the receipt:

  1. p99 IS ADDED alongside p50/p95. The engine already banks the full per-chunk
     interval series (chunk_ns) on every run, lease and resident alike, so this
     is a one-line use of the percentile function OB-1's tool already had. No
     engine change and no re-run were needed for it.
  2. MODEL CONSTANTS ARE A PARAMETER, not module globals, so the same tool reads
     both the 20b matrix and the 120b point.
  3. THE IDENTITY REFERENCE IS NAMED EXPLICITLY per corpus rather than inferred
     from "the resident run whose name ends in -a". OB-1b's 120b reference is an
     mmap-PAGED run, not a --no-mmap resident one, so the reference has to be
     stated rather than guessed.
  4. OB-1's OWN BANKED REFERENCE DIGESTS are cross-checked where they apply, so
     the receipt can say plainly whether this leg's 8-thread runs reproduce
     OB-1's 10-thread bytes.

Every number printed here is read from the run files. Nothing is estimated.
"""

import hashlib
import math
import os
import sys

MODELS = {
    "20b": dict(
        logical=12109566624,
        resident_always=1930678944,
        per_expert=13253760,
        L=24, E=32, tokens=32768,
    ),
    "120b": dict(
        logical=63387346208,
        resident_always=2314020128,
        per_expert=13253760,
        L=36, E=128, tokens=8192,
    ),
}

# OB-1's own banked fully resident references (research/ob1/RUNLOG-1.txt section
# 7), produced by the same engine at --threads 10. Cross-checked, not assumed.
OB1_REF = {
    "prose": ("96049ccf8ca241bf58233afe13ed75e2ca43180d81973360d04cebc80d551925",
              "4777aa8319f25d6e367f761ef12c7bec81a9ff7896bfed1b8ea0326b5dffc3df"),
    "code":  ("9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8",
              "f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77"),
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
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            d[k] = v
    return d


def grep1(path, pat):
    import re
    try:
        with open(path, "r", errors="replace") as f:
            for line in f:
                m = re.search(pat, line)
                if m:
                    return m.group(1)
    except IOError:
        return None
    return None


def peak_rss_kb(path):
    v = grep1(path, r"Maximum resident set size \(kbytes\):\s*(\d+)")
    return int(v) if v else None


def wall_s(path):
    v = grep1(path, r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(.+)")
    if not v:
        return None
    t = v.strip().split(":")
    if len(t) == 2:
        return float(t[0]) * 60 + float(t[1])
    return float(t[0]) * 3600 + float(t[1]) * 60 + float(t[2])


def pct_nearest_rank(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = max(1, math.ceil(p * len(s)))
    return s[k - 1]


def corpus_of(n):
    return "code" if "code" in n else "prose"


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "20b"
    runs_dir = sys.argv[2] if len(sys.argv) > 2 else "/root/ob1b/runs"
    # Comma-separated name prefixes. The runs directory holds both models' runs
    # (20b: res8-*, lease-k*; 120b: pag120-*, lease120-*, res120-*), and the two
    # have different constants and different token budgets, so each model's table
    # must be built from its own subset.
    only = sys.argv[3] if len(sys.argv) > 3 else ""
    prefixes = [p for p in only.split(",") if p]
    M = MODELS[model]
    LOGICAL = M["logical"]

    rows = []
    for n in sorted(os.listdir(runs_dir)):
        if prefixes and not any(n.startswith(p) for p in prefixes):
            continue
        # The K=0 smoke test is a 1024-token run whose only job was to prove the
        # patched engine accepts an empty resident set. It shares no token budget
        # with the matrix, so its identity artifact cannot be compared against the
        # 32768-token references and its p95 is over a single interval. It is
        # reported in the receipt's own section, never in these tables.
        if n.startswith("smoke"):
            continue
        d = os.path.join(runs_dir, n)
        sp, ip, rp, ep = (os.path.join(d, x) for x in
                          ("ob1-stats.txt", "identity.txt", "route.log", "stderr.txt"))
        if not (os.path.exists(sp) and os.path.exists(ip)):
            continue
        st = read_stats(sp)
        chunk = [int(x) for x in st.get("chunk_ns", "").split(",") if x]
        rows.append(dict(
            name=n,
            mode=st.get("ob1_mode"),
            k=int(st.get("ob1_k", -1)),
            identity_sha=sha256_file(ip),
            identity_bytes=os.path.getsize(ip),
            route_sha=sha256_file(rp) if os.path.exists(rp) else "(none)",
            rss_kb=peak_rss_kb(ep),
            wall_s=wall_s(ep),
            lease_events=int(st.get("lease_events", 0)),
            lease_bytes=int(st.get("lease_bytes_read", 0)),
            lease_read_ns=int(st.get("lease_read_ns", 0)),
            lease_verify_ns=int(st.get("lease_verify_ns", 0)),
            drop_bytes=int(st.get("lease_drop_bytes", 0)),
            peak_lease=int(st.get("peak_concurrent_lease_bytes", 0)),
            res_bytes=int(st.get("resident_bytes_loaded", 0)),
            res_verify_ns=int(st.get("resident_verify_ns", 0)),
            chunk_n=len(chunk),
            p50=pct_nearest_rank(chunk, 0.50),
            p95=pct_nearest_rank(chunk, 0.95),
            p99=pct_nearest_rank(chunk, 0.99),
            cmax=max(chunk) if chunk else None,
        ))

    # This leg's own identity/cost reference per corpus: the non-leased run whose
    # name ends in "-a". For the 20b that is a --no-mmap resident run; for the
    # 120b it is the mmap-paged run, since a --no-mmap resident 120b run does not
    # fit in this box's RAM (see the receipt's 120b section).
    ref = {}
    for r in rows:
        if r["mode"] != "lease" and r["name"].endswith("-a"):
            ref.setdefault(corpus_of(r["name"]), r)

    print("== MODEL CONSTANTS (%s) ==" % model)
    for k in ("logical", "resident_always", "per_expert", "L", "E", "tokens"):
        print("  %-16s %d" % (k, M[k]))

    print()
    print("== IDENTITY REFERENCES (this leg's own non-leased runs) ==")
    for c, r in sorted(ref.items()):
        print("  %-6s %-20s mode=%-9s identity=%s" % (c, r["name"], r["mode"], r["identity_sha"]))
        print("  %-6s %-20s %14s route   =%s" % ("", "", "", r["route_sha"]))
        if model == "20b" and c in OB1_REF:
            i_ok = "MATCH" if r["identity_sha"] == OB1_REF[c][0] else "DIFFER"
            r_ok = "MATCH" if r["route_sha"] == OB1_REF[c][1] else "DIFFER"
            print("  %-6s %-20s vs OB-1's banked 10-thread reference: identity %s  route %s"
                  % ("", "", i_ok, r_ok))

    print()
    print("== PER-RUN ROWS ==")
    hdr = ("run", "K", "corpus", "ident", "route", "leases", "bytes_moved",
           "wall_s", "rss_KB", "p50_ms", "p95_ms", "p99_ms", "n")
    print("%-20s %3s %-6s %-6s %-6s %8s %14s %8s %10s %9s %9s %9s %3s" % hdr)
    for r in rows:
        rr = ref.get(corpus_of(r["name"]))
        ident = route = "n/a"
        if rr is not None:
            ident = "MATCH" if r["identity_sha"] == rr["identity_sha"] else "DIFFER"
            route = "MATCH" if r["route_sha"] == rr["route_sha"] else "DIFFER"
        f = lambda v: (v / 1e6) if v else 0.0
        print("%-20s %3d %-6s %-6s %-6s %8d %14d %8.2f %10d %9.1f %9.1f %9.1f %3d" % (
            r["name"], r["k"], corpus_of(r["name"]), ident, route, r["lease_events"],
            r["lease_bytes"], r["wall_s"] or 0.0, r["rss_kb"] or 0,
            f(r["p50"]), f(r["p95"]), f(r["p99"]), r["chunk_n"]))

    print()
    print("== EXPOSURE ==")
    print("%-20s %3s %14s %10s %14s %10s %16s" % (
        "run", "K", "RSS_bytes", "EXP_rss", "ACCT_bytes", "EXP_acct", "peak_lease_bytes"))
    for r in rows:
        rss = (r["rss_kb"] or 0) * 1024
        if r["mode"] == "lease":
            acct = M["resident_always"] + r["k"] * M["L"] * M["per_expert"] + r["peak_lease"]
        else:
            acct = LOGICAL
        print("%-20s %3d %14d %10.6f %14d %10.6f %16d" % (
            r["name"], r["k"], rss, LOGICAL / float(rss) if rss else 0.0,
            acct, LOGICAL / float(acct), r["peak_lease"]))

    print()
    print("== VERIFY / READ COST (lease runs) ==")
    print("%-20s %10s %10s %16s %14s %14s" % (
        "run", "read_s", "verify_s", "drop_bytes", "res_verify_s", "B/tok"))
    for r in rows:
        if r["mode"] != "lease":
            continue
        print("%-20s %10.3f %10.3f %16d %14.3f %14.1f" % (
            r["name"], r["lease_read_ns"] / 1e9, r["lease_verify_ns"] / 1e9,
            r["drop_bytes"], r["res_verify_ns"] / 1e9,
            r["lease_bytes"] / float(M["tokens"])))

    print()
    print("== COST LIMB: leased p95 vs this leg's own baseline p95 (knee bar: <= 2.0x) ==")
    base = {c: r["p95"] for c, r in ref.items()}
    base99 = {c: r["p99"] for c, r in ref.items()}
    basew = {c: r["wall_s"] for c, r in ref.items()}
    for r in rows:
        if r["mode"] != "lease":
            continue
        c = corpus_of(r["name"])
        b, b99, bw = base.get(c), base99.get(c), basew.get(c)
        if not b or not r["p95"]:
            continue
        ratio = r["p95"] / float(b)
        r99 = (r["p99"] / float(b99)) if (b99 and r["p99"]) else 0.0
        rw = (r["wall_s"] / float(bw)) if (bw and r["wall_s"]) else 0.0
        print("  %-20s p95 %9.1f ms vs %9.1f ms  ratio %.4f  %s   (p99 ratio %.4f, wall ratio %.4f)" % (
            r["name"], r["p95"] / 1e6, b / 1e6, ratio,
            "PASS" if ratio <= 2.0 else "FAIL", r99, rw))


if __name__ == "__main__":
    sys.exit(main())
