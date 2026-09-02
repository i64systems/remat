#!/usr/bin/env python3
"""OB-1b: decompose the added cost of leasing per byte and per lease
event, across every K this program has measured.

THE QUESTION THIS ANSWERS. The prereg section 3 says the knee is
predicted to sit below K=4 "UNLESS an unmeasured cost floor (fixed per-lease-
event overhead, not just bytes moved) dominates at very small K". That is a
real possibility and it is testable: if the cost were purely proportional to
bytes moved, then read seconds per byte and verify seconds per byte would be
FLAT across K. If instead there is a fixed charge per lease event, the per-BYTE
figures would climb as K falls, because smaller K means more events for a given
volume... except that in this design every lease event moves exactly the same
13253760 bytes, so per-event and per-byte cost carry the same information and a
per-event floor cannot be separated from a per-byte one by arithmetic alone.
What CAN be separated is whether the observed rate degrades at all as K falls.

Reads the engine's own ob1-stats.txt from OB-1's run directories and this leg's,
so every figure is literal file content, not a transcription from a document.
"""

import os
import sys

PER_EXPERT = 13253760
DIRS = ["/root/ob1/runs", "/root/ob1b/runs"]


def read_stats(path):
    d = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                k, v = line.split("=", 1)
                d[k] = v
    return d


def main():
    rows = []
    for base in DIRS:
        if not os.path.isdir(base):
            continue
        for n in sorted(os.listdir(base)):
            sp = os.path.join(base, n, "ob1-stats.txt")
            if not os.path.exists(sp) or n.startswith("smoke"):
                continue
            st = read_stats(sp)
            if st.get("ob1_mode") != "lease":
                continue
            ev = int(st.get("lease_events", 0))
            by = int(st.get("lease_bytes_read", 0))
            if not ev or not by:
                continue
            rows.append(dict(
                src=os.path.basename(base), name=n, k=int(st.get("ob1_k", -1)),
                events=ev, bytes=by,
                fadv=int(st.get("ob1_fadvise", 0)),
                read_s=int(st.get("lease_read_ns", 0)) / 1e9,
                ver_s=int(st.get("lease_verify_ns", 0)) / 1e9,
                drop_s=int(st.get("lease_drop_ns", 0)) / 1e9,
            ))

    if not rows:
        print("(no leased runs with stats found yet)")
        return

    print("== BYTES PER LEASE EVENT (must be exactly one expert's share, %d) ==" % PER_EXPERT)
    bad = 0
    for r in rows:
        q = r["bytes"] / float(r["events"])
        if abs(q - PER_EXPERT) > 0.5:
            bad += 1
            print("  %-22s %.1f  DIFFERS" % (r["name"], q))
    print("  %d of %d runs move exactly %d bytes per lease event" % (
        len(rows) - bad, len(rows), PER_EXPERT))

    print()
    print("== READ AND VERIFY RATE VERSUS K ==")
    print("  A fixed per-event overhead that dominates at small K would show up as")
    print("  these GB/s columns FALLING sharply as K falls. Flat columns mean cost")
    print("  tracks bytes moved, which is the case builder 1's prediction assumed.")
    print()
    print("  %-6s %-22s %3s %10s %16s %10s %10s %10s %10s %5s" % (
        "leg", "run", "K", "events", "bytes", "read_GB/s", "ver_GB/s",
        "read_ms/ev", "ver_ms/ev", "fadv"))
    for r in sorted(rows, key=lambda x: (-x["k"], x["name"])):
        rg = (r["bytes"] / r["read_s"] / 1e9) if r["read_s"] else 0.0
        vg = (r["bytes"] / r["ver_s"] / 1e9) if r["ver_s"] else 0.0
        print("  %-6s %-22s %3d %10d %16d %10.4f %10.4f %10.4f %10.4f %5d" % (
            r["src"], r["name"], r["k"], r["events"], r["bytes"], rg, vg,
            r["read_s"] * 1e3 / r["events"], r["ver_s"] * 1e3 / r["events"], r["fadv"]))

    print()
    print("== RATE AT THE EXTREMES (the floor question, stated as a ratio) ==")
    # The page-cache-dropping run (fadv=1) is excluded from these aggregates: it
    # deliberately reads from cold storage, so its 1.04 GB/s read rate measures
    # the NVMe path, not a per-event overhead, and averaging it into the K=16
    # figure would manufacture a false decline.
    warm = [r for r in rows if not r["fadv"]]
    print("  (page-cache-dropping runs excluded: %d of %d rows)" % (
        len(rows) - len(warm), len(rows)))
    rows_agg = warm
    ks = sorted({r["k"] for r in rows_agg})
    if len(ks) >= 2:
        hi = [r for r in rows_agg if r["k"] == max(ks)]
        lo = [r for r in rows_agg if r["k"] == min(ks)]
        def mean(rs, f):
            return sum(f(r) for r in rs) / float(len(rs))
        rh = mean(hi, lambda r: r["bytes"] / r["read_s"] / 1e9)
        rl = mean(lo, lambda r: r["bytes"] / r["read_s"] / 1e9)
        vh = mean(hi, lambda r: r["bytes"] / r["ver_s"] / 1e9)
        vl = mean(lo, lambda r: r["bytes"] / r["ver_s"] / 1e9)
        print("  highest K measured = %d : read %.4f GB/s, verify %.4f GB/s" % (max(ks), rh, vh))
        print("  lowest  K measured = %d : read %.4f GB/s, verify %.4f GB/s" % (min(ks), rl, vl))
        print("  read rate at lowest K is %.4f x the rate at highest K" % (rl / rh if rh else 0))
        print("  verify rate at lowest K is %.4f x the rate at highest K" % (vl / vh if vh else 0))
        print("  NOTE: runs from different legs used different thread counts and ran")
        print("  under different sibling load, so treat cross-leg rows as indicative.")


if __name__ == "__main__":
    sys.exit(main())
