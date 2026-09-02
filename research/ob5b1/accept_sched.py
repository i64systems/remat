#!/usr/bin/env python3
# OB5B-S1 leg C, limb 5: THE SCHEDULE CONTROL, read as a set of routing
# decisions rather than as a file. Both runlogs compared the two route logs
# POSITIONALLY. The emission order of the log depends on the ubatch schedule,
# so a positional compare of two schedules compares different rows to each
# other. This limb settles it three ways.
import hashlib, collections

def rows(p):
    out = []
    for line in open(p):
        line = line.strip()
        if line:
            f = line.split(',')
            out.append((int(f[0]), int(f[1]), tuple(int(x) for x in f[2:])))
    return out

def sha_lines(rs):
    s = "".join("%d,%d,%s\n" % (l, t, ",".join(str(e) for e in es)) for (l, t, es) in rs)
    return hashlib.sha256(s.encode()).hexdigest()

CASES = [
 ("GATE 1 CONTROL (R1 s4.6, F-A5)", 56,
  "/root/ob5b1/runs/gen-120b-k8-a/route.log",
  "/root/ob5b1/runs/gen-120b-k8-ub32/route.log"),
 ("GATE 2 CONTROL (R2 s4.8, F-B9)", 63,
  "/root/ob5b2/runs/g2-k8-p2/route.log",
  "/root/ob5b2/runs/g2-k8-p2-ub32/route.log"),
]

for (label, n_prompt, pa, pb) in CASES:
    A = rows(pa); B = rows(pb)
    print("=" * 78)
    print(label)
    print("=" * 78)
    print("  rows            %d vs %d" % (len(A), len(B)))
    print("  FILE ORDER identical                     %s" % (A == B))

    # 1. as a multiset of whole rows
    ca = collections.Counter(A); cb = collections.Counter(B)
    print("  MULTISET of (layer, token, experts) equal %s" % (ca == cb))

    # 2. as a map (layer, token) -> experts, which is the routing decision
    ma = {(l, t): es for (l, t, es) in A}
    mb = {(l, t): es for (l, t, es) in B}
    print("  keys equal                               %s" % (set(ma) == set(mb)))
    diffs = [k for k in ma if ma[k] != mb.get(k)]
    print("  ROUTING DECISIONS that differ            %d of %d" % (len(diffs), len(ma)))
    pre = [k for k in diffs if k[1] < n_prompt]
    dec = [k for k in diffs if k[1] >= n_prompt]
    print("    of which prefill %d, decode %d" % (len(pre), len(dec)))

    # 3. canonical-order digest: identical iff every decision is identical
    A2 = sorted(A, key=lambda r: (r[0], r[1]))
    B2 = sorted(B, key=lambda r: (r[0], r[1]))
    print("  CANONICAL (layer,token) digest ub64      %s" % sha_lines(A2))
    print("  CANONICAL (layer,token) digest ub32      %s" % sha_lines(B2))
    print("  CANONICAL digests equal                  %s" % (sha_lines(A2) == sha_lines(B2)))

    # what the positional compare reports, so the artifact is visible
    posdiff = sum(1 for x, y in zip(A, B) if x != y)
    pa_pre = [r for r in A if r[1] < n_prompt]
    pb_pre = [r for r in B if r[1] < n_prompt]
    posdiff_pre = sum(1 for x, y in zip(pa_pre, pb_pre) if x != y)
    print("  positional compare, whole file           %d rows differ" % posdiff)
    print("  positional compare, prefill rows only    %d of %d differ (%.1f pct)"
          % (posdiff_pre, len(pa_pre), 100.0*posdiff_pre/len(pa_pre)))
    print("  -> the positional figure is an EMISSION-ORDER artifact.")
    # show the artifact concretely
    print("  ub64 file line 33: %s" % (A[32],))
    print("  ub32 file line 33: %s" % (B[32],))
    print("")

print("=" * 78)
print("LIMB 5B: WHAT tok_s_decode_excl_first ACTUALLY DIVIDES BY")
print("=" * 78)
import os
for name, d in [("gen-120b-k8-a", "/root/ob5b1/runs/gen-120b-k8-a"),
                ("gen-120b-k8-b", "/root/ob5b1/runs/gen-120b-k8-b"),
                ("g2-k8-p1-a", "/root/ob5b2/runs/g2-k8-p1-a"),
                ("g2-k32-p2", "/root/ob5b2/runs/g2-k32-p2")]:
    so = {}
    for line in open(d+"/stdout.txt"):
        p = line.split()
        if len(p) >= 2: so[p[0]] = p[1]
    n = int(so["n_generated_tokens"]); ds = float(so["decode_seconds"])
    ex = float(so["tok_s_decode_excl_first"]); tk = float(so["tok_s_decode"])
    implied = (n-1)/ex
    print("%-16s n %d  decode_s %.9f  tok/s %.9f  excl1 %.9f" % (name, n, ds, tk, ex))
    print("                 implied denominator (n-1)/excl1 = %.9f   decode_s - implied = %.9f"
          % (implied, ds - implied))
    print("                 (n-1)/decode_s = %.9f   ratio to printed = %.9f"
          % ((n-1)/ds, ((n-1)/ds)/ex))
