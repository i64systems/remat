#!/usr/bin/env python3
"""OB-5b P05: compare two route logs by (layer, token) rather than by file
order.

The engine emits route rows in the order it computes them, so a run at
ubatch=1024 emits all tokens of layer 0, then layer 1, while a run at
ubatch=1 emits layer 0..23 for token 0, then token 1. The file digests
therefore differ even if every routing decision is identical, and a
digest comparison alone cannot tell an ORDERING difference from a
ROUTING difference. This tool separates them.

usage: route_compare.py A.route.log B.route.log
"""
import sys
import hashlib


def load(path):
    d = {}
    order = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = [int(x) for x in line.split(",")]
            key = (parts[0], parts[1])
            d[key] = tuple(parts[2:])
            order.append(key)
    return d, order


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    pa, pb = sys.argv[1], sys.argv[2]
    a, oa = load(pa)
    b, ob = load(pb)
    print("A %s  rows %d  sha256 %s" % (pa, len(oa), sha(pa)))
    print("B %s  rows %d  sha256 %s" % (pb, len(ob), sha(pb)))
    print("EMISSION ORDER IDENTICAL: %s" % (oa == ob))
    ka, kb = set(a), set(b)
    print("KEY SETS IDENTICAL: %s  (A only %d, B only %d)"
          % (ka == kb, len(ka - kb), len(kb - ka)))
    common = sorted(ka & kb)
    diff = [k for k in common if a[k] != b[k]]
    print("ROWS COMPARED BY (layer,token): %d" % len(common))
    print("ROWS WITH A DIFFERENT PICK SET: %d" % len(diff))
    if diff:
        k = diff[0]
        print("FIRST DIVERGENCE: layer %d token %d  A%s  B%s"
              % (k[0], k[1], list(a[k]), list(b[k])))
    # pick-level agreement, as sets (order within a row is router rank order)
    same_picks = 0
    tot = 0
    for k in common:
        sa, sb = set(a[k]), set(b[k])
        same_picks += len(sa & sb)
        tot += len(sa)
    print("PICK-LEVEL AGREEMENT: %d of %d = %.6f pct"
          % (same_picks, tot, 100.0 * same_picks / tot))
    # per-layer divergent row counts
    per = {}
    for k in diff:
        per[k[0]] = per.get(k[0], 0) + 1
    print("DIVERGENT ROWS PER LAYER: %s"
          % ",".join("%d:%d" % (l, per.get(l, 0))
                     for l in sorted(set(k[0] for k in common))))
    # the sorted-canonical digest, which is order-independent
    for name, d in (("A", a), ("B", b)):
        h = hashlib.sha256()
        for k in sorted(d):
            h.update(("%d,%d,%s\n" % (k[0], k[1],
                                      ",".join(str(x) for x in d[k]))).encode())
        print("CANONICAL (layer,token)-SORTED DIGEST %s: %s" % (name, h.hexdigest()))


if __name__ == "__main__":
    main()
