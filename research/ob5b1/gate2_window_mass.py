#!/usr/bin/env python3
# OB-5b S1 gate 2: WHAT DOES GATE 0's 0.4040035672 LOOK LIKE ON A PROMPT-SIZED
# SLICE?
#
# Gate 2's in-sample prompt (PROMPT-3, cut from inside the corpus the K=8 set
# was ranked on) scored a prefill top-8 mass of 0.1922080979, less than half
# gate 0's run-level 0.4040035672 on that same corpus. Two explanations were
# available and they have different consequences: SMALL SAMPLE (a 59 token
# slice is not a 16384 token run and the spread is wide) or SCHEDULE (gate 0's
# route logs were produced at -ub 4096 and a served prefill runs at -ub 64,
# which leg A's control 2 proved can move the routing).
#
# This script settles the first one by measuring the spread directly: it slices
# the BANKED 120b-prose-a route log into consecutive windows the size of gate
# 2's prompts and reports the distribution of top-8 mass across them. If a 59
# token window routinely scores 0.19, the small-sample explanation stands on
# its own; if the windows cluster near 0.40, it does not.
#
# Analysis only. No model, no runlock, no serve contact.

import json
import sys

K_USED = 4


def main():
    log = sys.argv[1]
    sets_path = sys.argv[2]
    K = int(sys.argv[3])
    W = int(sys.argv[4])

    d = json.load(open(sets_path))
    L, E = int(d["L"]), int(d["E"])
    sets = d["resident_sets"][str(K)]
    resident = [set(int(x) for x in sets[str(l)]) for l in range(L)]

    hits = {}
    dec = {}
    T = 0
    for line in open(log):
        line = line.strip()
        if not line:
            continue
        r = [int(x) for x in line.split(",")]
        l, t, ids = r[0], r[1], set(r[2:2 + K_USED])
        T = max(T, t + 1)
        w = t // W
        hits[w] = hits.get(w, 0) + len(ids & resident[l])
        dec[w] = dec.get(w, 0) + len(ids)

    ms = sorted(hits[w] / dec[w] for w in hits if dec[w] > 0)
    n = len(ms)

    def q(p):
        return ms[min(n - 1, max(0, int(p * (n - 1))))]

    print("log      %s" % log)
    print("K %d  L %d  E %d  tokens %d  window %d  windows %d" % (K, L, E, T, W, n))
    print("run-level mass  %.10f" % (sum(hits.values()) / sum(dec.values())))
    print("window mass     min %.10f  p05 %.10f  p50 %.10f  p95 %.10f  max %.10f"
          % (ms[0], q(0.05), q(0.50), q(0.95), ms[-1]))
    print("windows at or below 0.20   %d of %d" % (sum(1 for m in ms if m <= 0.20), n))
    print("windows at or below 0.25   %d of %d" % (sum(1 for m in ms if m <= 0.25), n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
