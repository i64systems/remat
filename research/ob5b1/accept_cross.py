#!/usr/bin/env python3
# OB5B-S1 leg C, limb 4: the cross-run identity limbs, the schedule
# control's phase split, and the "excl first" definition, all from raw bytes.
import hashlib, os

def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()

def rd(p):
    return open(p, 'rb').read()

B1 = "/root/ob5b1/runs"
B2 = "/root/ob5b2/runs"

print("=" * 78)
print("LIMB 4A: GATE 1's IDENTITY EXTENDS INTO GATE 2 (the n_predict cross limb)")
print("=" * 78)
g1 = rd(B1 + "/gen-120b-k8-a/gen-ids.txt").decode().split()
g2 = rd(B2 + "/g2-k8-p1-a/gen-ids.txt").decode().split()
print("gate 1 ids %d tokens, gate 2 ids %d tokens" % (len(g1), len(g2)))
print("GATE1_PREFIX_MATCHES_GATE2 %s" % (g2[:len(g1)] == g1))
print("gate 1 ids, in order: %s" % " ".join(g1))
print("gate 2 tokens 33..64:  %s" % " ".join(g2[32:]))

print("")
print("=" * 78)
print("LIMB 4B: THE SCHEDULE CONTROL, PHASE-SPLIT BY HAND (R2 s4.8)")
print("=" * 78)
for (label, a, b, n_prompt) in [
    ("gate1 ctl  ub64 vs ub32", B1+"/gen-120b-k8-a", B1+"/gen-120b-k8-ub32", 56),
    ("gate2 ctl  ub64 vs ub32", B2+"/g2-k8-p2",      B2+"/g2-k8-p2-ub32",    63),
]:
    ra = [l.strip() for l in open(a+"/route.log") if l.strip()]
    rb = [l.strip() for l in open(b+"/route.log") if l.strip()]
    print("")
    print(label)
    print("  rows %d vs %d" % (len(ra), len(rb)))
    print("  whole route.log identical: %s" % (ra == rb))
    ida = rd(a+"/gen-ids.txt"); idb = rd(b+"/gen-ids.txt")
    txa = rd(a+"/gen-text.txt"); txb = rd(b+"/gen-text.txt")
    print("  gen-ids.txt  identical: %s   sha %s" % (ida == idb, sha_bytes(ida)))
    print("  gen-text.txt identical: %s   sha %s" % (txa == txb, sha_bytes(txa)))
    pa = [l for l in ra if int(l.split(',')[1]) < n_prompt]
    pb = [l for l in rb if int(l.split(',')[1]) < n_prompt]
    da = [l for l in ra if int(l.split(',')[1]) >= n_prompt]
    db = [l for l in rb if int(l.split(',')[1]) >= n_prompt]
    # compare prefill rows in the canonical (layer, token) order so the two
    # schedules' different emission orders do not fake a difference
    ka = sorted(pa, key=lambda l: (int(l.split(',')[0]), int(l.split(',')[1])))
    kb = sorted(pb, key=lambda l: (int(l.split(',')[0]), int(l.split(',')[1])))
    diff = sum(1 for x, y in zip(ka, kb) if x != y)
    print("  PREFILL rows %d, differing %d (%.1f pct)" % (len(ka), diff, 100.0*diff/len(ka)))
    print("    ub64 prefill sha %s" % sha_bytes(("\n".join(ka)+"\n").encode()))
    print("    ub32 prefill sha %s" % sha_bytes(("\n".join(kb)+"\n").encode()))
    kda = sorted(da, key=lambda l: (int(l.split(',')[0]), int(l.split(',')[1])))
    kdb = sorted(db, key=lambda l: (int(l.split(',')[0]), int(l.split(',')[1])))
    ddiff = sum(1 for x, y in zip(kda, kdb) if x != y)
    print("  DECODE  rows %d, differing %d" % (len(kda), ddiff))
    print("    both decode sha %s / %s" % (sha_bytes(("\n".join(kda)+"\n").encode()),
                                            sha_bytes(("\n".join(kdb)+"\n").encode())))
    # first differing byte of the raw files, as cmp would report it
    ba, bb = rd(a+"/route.log"), rd(b+"/route.log")
    fb = next((i for i in range(min(len(ba), len(bb))) if ba[i] != bb[i]), None)
    if fb is not None:
        line = ba[:fb].count(b"\n") + 1
        print("  first differing byte %d, line %d -> %r" % (fb+1, line, ra[line-1]))

print("")
print("=" * 78)
print("LIMB 4C: WHAT 'tok/s DECODE excl first' ACTUALLY IS")
print("=" * 78)
print("run                 printed excl1   (n-1)/decode_s   (n-1)/(decode_s - chunk_ns[0])")
RUNS = [("gen-120b-k8-a", B1+"/gen-120b-k8-a"), ("gen-120b-k8-b", B1+"/gen-120b-k8-b"),
        ("gen-120b-k8-c", B1+"/gen-120b-k8-c"), ("g2-k8-p1-a", B2+"/g2-k8-p1-a"),
        ("g2-k32-p2", B2+"/g2-k32-p2")]
agree = 0
for name, d in RUNS:
    so = {}
    for line in open(d+"/stdout.txt"):
        p = line.split()
        if len(p) >= 2: so[p[0]] = p[1]
    st = {}
    for line in open(d+"/ob1-stats.txt"):
        if '=' in line:
            k, v = line.strip().split('=', 1); st[k] = v
    n = int(so["n_generated_tokens"]); ds = float(so["decode_seconds"])
    c0 = int(st["chunk_ns"].split(",")[0]) / 1e9
    a = (n-1)/ds
    b = (n-1)/(ds - c0)
    pr = float(so["tok_s_decode_excl_first"])
    ok = abs(a - pr) < 1e-8
    agree += int(ok)
    print("%-19s %14.9f %16.9f %20.9f   defn (n-1)/decode_s matches: %s"
          % (name, pr, a, b, ok))
print("")
print("The field removes the first TOKEN from the numerator and keeps the whole")
print("decode window in the denominator. It is a conservative lower bound on the")
print("decode rate, NOT a post-warmup steady-state rate. %d of %d runs confirm the"
      % (agree, len(RUNS)))
print("definition. chunk_ns[0] spans the PREFILL, so it cannot be used to strip a")
print("warm-up token, which is why no steady-state figure exists in either leg.")
