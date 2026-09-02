#!/usr/bin/env python3
# OB5B-S1 leg C, limb 7: what chunk_ns actually measures.
#
# RUNLOG-2 section 4.7 describes chunk_ns as "the wall time between layer-0
# route calls, which is one entry per llama_decode call". It is one entry per
# INTERVAL between consecutive layer-0 route calls. A run makes one prefill
# call plus n_gen decode calls, so there are n_gen intervals: the FIRST spans
# the PREFILL, and the LAST decoded token's own time is not recorded at all.
# Entry 0 is therefore not a token, and a two-piece prefill puts a second
# prefill interval at entry 1 (len(chunk_ns) is n_gen + 1 in that case).
#
# This script proves the reading by reproducing RUNLOG-2 section 4.7's own
# published cells under the include-the-prefill hypothesis, then prints the
# same table with the prefill intervals removed.
import statistics
import sys

B1 = "/root/ob5b1/runs"
B2 = "/root/ob5b2/runs"

RUNS = [
    ("g2-k8-p1-a", B2 + "/g2-k8-p1-a"),
    ("g2-k8-p1-b", B2 + "/g2-k8-p1-b"),
    ("g2-k8-p2",   B2 + "/g2-k8-p2"),
    ("g2-k8-p3",   B2 + "/g2-k8-p3"),
    ("g2-k16-p1",  B2 + "/g2-k16-p1"),
    ("g2-k24-p1",  B2 + "/g2-k24-p1"),
    ("g2-k32-p1",  B2 + "/g2-k32-p1"),
]

# RUNLOG-2 section 4.7 as published:
# (first quarter mean, last quarter mean, min, max, last/first)
PUBLISHED = {
    "g2-k8-p1-a": (4.761383, 6.748289, 2.143400, 40.302140, 1.417296),
    "g2-k8-p1-b": (6.066317, 2.641532, 2.192653, 44.919939, 0.435443),
    "g2-k8-p2":   (5.069841, 2.744875, 2.189204, 41.622151, 0.541412),
    "g2-k8-p3":   (4.453211, 2.202518, 1.874372, 36.048212, 0.494591),
    "g2-k16-p1":  (4.629770, 2.431627, 1.889135, 37.654195, 0.525216),
    "g2-k24-p1":  (4.245819, 2.352158, 1.745247, 33.988706, 0.553994),
    "g2-k32-p1":  (4.091415, 2.229538, 1.492057, 33.535756, 0.544931),
}


def stats(d):
    st = {}
    for line in open(d + "/ob1-stats.txt"):
        if "=" in line:
            k, v = line.strip().split("=", 1)
            st[k] = v
    return st


def counters(d):
    so = {}
    for line in open(d + "/stdout.txt"):
        p = line.split()
        if len(p) >= 2:
            so[p[0]] = p[1]
    return so


print("STEP 1: chunk_ns[0] IS THE PREFILL, SHOWN AGAINST ttft_seconds")
print("%-14s %6s %6s %8s %14s %14s %14s"
      % ("run", "n_gen", "len", "pieces", "chunk_ns[0]", "ttft_seconds", "difference"))
for name, d in RUNS + [("gen-120b-k8-ub32", B1 + "/gen-120b-k8-ub32"),
                       ("g2-k8-p2-ub32", B2 + "/g2-k8-p2-ub32")]:
    st = stats(d)
    so = counters(d)
    ch = [int(x) / 1e9 for x in st["chunk_ns"].split(",")]
    ng = int(so["n_generated_tokens"])
    ttft = float(so["ttft_seconds"])
    pieces = len(ch) - ng + 1
    head = ch[0] if pieces == 1 else ch[0] + ch[1]
    print("%-14s %6d %6d %8d %14.6f %14.6f %14.6f"
          % (name, ng, len(ch), pieces, head, ttft, ttft - head))
print("  len(chunk_ns) - n_gen + 1 is the number of PREFILL pieces, and the")
print("  prefill intervals sum to just under ttft. A one-piece prefill puts one")
print("  interval at entry 0; a two-piece prefill puts two, at entries 0 and 1.")
print("  The last decoded token's own time is never recorded.")

print("")
print("STEP 2: REPRODUCING RUNLOG-2 s4.7's PUBLISHED CELLS WITH THE PREFILL IN")
print("%-14s %11s %11s %11s %11s %11s %11s"
      % ("run", "pub first", "repro", "pub max", "chunk_ns[0]", "pub min", "repro min"))
ok = 0
tot = 0
for name, d in RUNS:
    st = stats(d)
    ch = [int(x) / 1e9 for x in st["chunk_ns"].split(",")]
    q = len(ch) // 4
    incl = sum(ch[:q]) / q
    p = PUBLISHED[name]
    tot += 3
    ok += (abs(incl - p[0]) < 5e-6) + (abs(max(ch) - p[3]) < 5e-6) + (abs(min(ch) - p[2]) < 5e-6)
    print("%-14s %11.6f %11.6f %11.6f %11.6f %11.6f %11.6f"
          % (name, p[0], incl, p[3], ch[0], p[2], min(ch)))
print("  CELLS REPRODUCED UNDER THE INCLUDE-PREFILL HYPOTHESIS: %d of %d" % (ok, tot))
print("  The published max is chunk_ns[0] in every row, so it is the PREFILL and")
print("  not a token, and the published first-quarter mean carries it too.")

print("")
print("STEP 3: THE SAME TABLE WITH THE PREFILL INTERVALS REMOVED")
print("%-14s %6s %13s %13s %10s %10s %9s %11s"
      % ("run", "n_dec", "first quarter", "last quarter", "min", "max", "max/min", "last/first"))
lf = []
mm = []
for name, d in RUNS:
    st = stats(d)
    ch = [int(x) / 1e9 for x in st["chunk_ns"].split(",")]
    dec = ch[1:]
    q = len(dec) // 4
    f = sum(dec[:q]) / q
    l = sum(dec[-q:]) / q
    lf.append(l / f)
    mm.append(max(dec) / min(dec))
    print("%-14s %6d %13.6f %13.6f %10.6f %10.6f %9.4f %11.6f"
          % (name, len(dec), f, l, min(dec), max(dec), max(dec) / min(dec), l / f))
print("  within-run decode spread max/min: %.4f to %.4f" % (min(mm), max(mm)))
print("  first-to-last-quarter drift:      %.6f to %.6f" % (min(lf), max(lf)))
print("  runs whose drift is within 5 percent of flat: %d of %d"
      % (sum(1 for x in lf if 0.95 <= x <= 1.05), len(lf)))

print("")
print("STEP 4: IS THERE A FIRST-TOKEN WARM-UP TO EXCLUDE AT ALL?")
print("%-14s %14s %14s %10s" % ("run", "first decode s", "median decode s", "ratio"))
for name, d in RUNS:
    st = stats(d)
    ch = [int(x) / 1e9 for x in st["chunk_ns"].split(",")]
    dec = ch[1:]
    print("%-14s %14.6f %14.6f %10.4f"
          % (name, dec[0], statistics.median(dec), dec[0] / statistics.median(dec)))
print("  The first decoded token is not systematically slower than the run")
print("  median, so tok/s decode excl first corrects for a warm-up that is not")
print("  there. See OB5B-S1-1.md finding F-C3.")
