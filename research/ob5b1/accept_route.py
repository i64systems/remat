#!/usr/bin/env python3
# OB5B-S1 leg C, limb 2: re-derive every route-log figure from raw bytes,
# with an implementation written from the definitions and not from either
# builder's code. Pure python, no numpy, so the arithmetic path is different too.
import json, sys, os

PER_EXPERT = 13253760
TRUNK = 2314020128
MODEL_BYTES = 63387346208
L = 36
E = 128
KSEL = 4

def load_route(path):
    """rows: (layer, token, [4 experts]) in file order."""
    rows = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            p = line.split(',')
            rows.append((int(p[0]), int(p[1]), tuple(int(x) for x in p[2:])))
    return rows

def counts_and_order(rows):
    c = [[0]*E for _ in range(L)]
    per_layer_tokens = [[] for _ in range(L)]
    dup = 0
    for (l, t, es) in rows:
        if len(set(es)) != len(es):
            dup += 1
        for e in es:
            c[l][e] += 1
        per_layer_tokens[l].append(t)
    order_ok = True
    T = None
    for l in range(L):
        toks = per_layer_tokens[l]
        if toks != list(range(len(toks))):
            order_ok = False
        if T is None:
            T = len(toks)
        elif T != len(toks):
            order_ok = False
    return c, T, order_ok, dup

def topk_sets(c, K):
    """count descending, ties broken by LOWER expert id, first K."""
    out = []
    for l in range(L):
        idx = sorted(range(E), key=lambda e: (-c[l][e], e))
        out.append(sorted(idx[:K]))
    return out

def mass_and_miss(rows, sets, T):
    S = [set(s) for s in sets]
    hit = 0
    per_layer_hit = [0]*L
    miss_per_token = [0]*T
    for (l, t, es) in rows:
        h = sum(1 for e in es if e in S[l])
        hit += h
        per_layer_hit[l] += h
        miss_per_token[t] += (KSEL - h)
    dec = L*T*KSEL
    return hit, per_layer_hit, dec, miss_per_token

def pct(v):
    return "%.10f" % v

def gate0():
    print("=" * 74)
    print("LIMB 2A: GATE 0 RE-DERIVED FROM THE BANKED RS053 ROUTE LOGS")
    print("=" * 74)
    banked = json.load(open("/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json"))
    banked_sets = sets_for("/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json", 8)
    print("banked tie_break            %s" % banked.get("tie_break"))
    print("banked ranking_corpus       %s" % banked.get("ranking_corpus"))
    print("banked per_expert_bytes     %s" % banked.get("per_expert_bytes_per_layer"))

    base = "/mnt/f/f32/stage/research/rs053/runs"
    res = {}
    for label in ["120b-prose-a", "120b-prose-b", "120b-code-a", "120b-code-b"]:
        rows = load_route(os.path.join(base, label, "route.log"))
        c, T, order_ok, dup = counts_and_order(rows)
        res[label] = (rows, c, T)
        own8 = topk_sets(c, 8)
        rederives = (own8 == banked_sets)
        print("")
        print("%s  rows %d  T %d  order_ok %s  duplicate_expert_rows %d"
              % (label, len(rows), T, order_ok, dup))
        print("  banked_k8_set_rederives_from_this_log %s" % rederives)
        hit, plh, dec, mpt = mass_and_miss(rows, banked_sets, T)
        mass = hit / dec
        print("  BANKED K=8 SET: hit %d of %d   top8_mass %s   miss_rate %s"
              % (hit, dec, pct(mass), pct(1.0 - mass)))
        s = sorted(mpt)
        mean = sum(mpt)/len(mpt)
        print("  misses/token drop-on-use  mean %s  min %d  p50 %.1f  p95 %.1f  max %d"
              % ("%.10f" % mean, s[0], s[len(s)//2], s[int(0.95*len(s))], s[-1]))
        if label == "120b-prose-a":
            print("  per-layer mass, all 36 layers:")
            for l in range(L):
                m = plh[l] / (T*KSEL)
                print("    layer %2d  hit %6d  decisions %6d  mass %.8f  miss %.8f  mis/token %.6f"
                      % (l, plh[l], T*KSEL, m, 1.0-m, (KSEL - plh[l]/T)))
            lm = [plh[l]/(T*KSEL) for l in range(L)]
            print("  layer-mean %s  layer-min %s (layer %d)  layer-max %s (layer %d)"
                  % (pct(sum(lm)/L), pct(min(lm)), lm.index(min(lm)), pct(max(lm)), lm.index(max(lm))))
    # K sweep, self-ranked
    print("")
    print("K SWEEP, SELF-RANKED SETS (each log ranked on itself):")
    print("  K       prose mass          prose miss        prose mis/tok      code mass(own)     code miss(own)")
    for K in [8, 16, 24, 32, 48, 64]:
        line = "  %-3d" % K
        for label in ["120b-prose-a", "120b-code-a"]:
            rows, c, T = res[label]
            sets = topk_sets(c, K)
            hit, plh, dec, mpt = mass_and_miss(rows, sets, T)
            m = hit/dec
            if label == "120b-prose-a":
                line += "  %s    %s    %.6f" % (pct(m), pct(1.0-m), sum(mpt)/len(mpt))
            else:
                line += "     %s    %s" % (pct(m), pct(1.0-m))
        print(line)
    return res

def phase_split_metrics(rows, sets, n_prompt):
    """lease events under HELD-FOR-THE-UBATCH, and peak concurrent, whole run
    and decode phase. ob1_on_route releases the previous layer's leases at the
    top of each route call and then leases this call's non-resident needs, so
    `concurrent` is per (layer, ubatch-piece)."""
    S = [set(s) for s in sets]
    # group rows into route calls: consecutive rows sharing a layer form one
    # call when they belong to one llama_decode piece. The log emits one row per
    # (layer, token); a route call covers all tokens of one ubatch piece at one
    # layer. Reconstruct pieces from token_index runs per layer.
    # Build, per layer, the ordered token list; a new piece starts when the
    # token index is not previous+1 OR the previous piece is complete. We do not
    # know piece widths a priori, so recover them from the file's row order:
    # rows are emitted layer-major within a piece, so a piece boundary is where
    # the layer index returns to 0.
    # rows inside one piece are layer-major: layer 0 for every token of the
    # piece, then layer 1, and so on to layer L-1. A piece boundary is the
    # return of the layer column to 0 from a NON-zero layer.
    pieces = []
    cur = []
    last_layer = None
    for r in rows:
        if last_layer is not None and r[0] == 0 and last_layer != 0:
            pieces.append(cur)
            cur = []
        cur.append(r)
        last_layer = r[0]
    if cur:
        pieces.append(cur)
    lease_events = 0
    peak_all = 0
    peak_decode = 0
    dec_hit = 0
    dec_dec = 0
    dec_miss_per_token = {}
    for pc in pieces:
        bylayer = {}
        for (l, t, es) in pc:
            bylayer.setdefault(l, []).append((t, es))
        for l, items in bylayer.items():
            need = set()
            for (t, es) in items:
                for e in es:
                    if e not in S[l]:
                        need.add(e)
            conc = len(need) * PER_EXPERT
            lease_events += len(need)
            if conc > peak_all:
                peak_all = conc
            toks = [t for (t, es) in items]
            is_decode = all(t >= n_prompt for t in toks)
            if is_decode and conc > peak_decode:
                peak_decode = conc
        for (l, t, es) in pc:
            if t >= n_prompt:
                h = sum(1 for e in es if e in S[l])
                dec_hit += h
                dec_dec += KSEL
                dec_miss_per_token[t] = dec_miss_per_token.get(t, 0) + (KSEL - h)
    n_dec = len(dec_miss_per_token)
    return {
        "pieces": len(pieces),
        "lease_events": lease_events,
        "peak_all": peak_all,
        "peak_decode": peak_decode,
        "decode_mass": (dec_hit/dec_dec) if dec_dec else 0.0,
        "decode_mis_per_token": (sum(dec_miss_per_token.values())/n_dec) if n_dec else 0.0,
        "n_decode_tokens": n_dec,
    }

def read_stats(p):
    d = {}
    for line in open(p):
        line = line.strip()
        if '=' in line:
            k, v = line.split('=', 1)
            d[k] = v
    return d

def read_stdout_counters(p):
    d = {}
    for line in open(p):
        parts = line.split()
        if len(parts) >= 2:
            d[parts[0]] = parts[1]
    return d

def sets_for(setsfile, K):
    """resident_sets[str(K)] is a dict keyed by layer-as-string."""
    j = json.load(open(setsfile))
    block = j["resident_sets"][str(K)]
    out = []
    for l in range(L):
        out.append(sorted(int(e) for e in block[str(l)]))
    return out

def gate12(runs):
    print("")
    print("=" * 74)
    print("LIMB 2B: EVERY GENERATION RUN, DERIVED FROM ITS OWN ROUTE LOG")
    print("        AND CHECKED AGAINST THE ENGINE'S OWN COUNTERS")
    print("=" * 74)
    hdr = ("run                  K  n_pr  pieces  derivedLease  engineLease  M   "
           "derivedPeak  enginePeak  M   decodePeak  decMass       decMis/tok")
    print(hdr)
    agree = 0
    disagree = 0
    out = {}
    for (name, d, K, setsfile) in runs:
        st = read_stats(os.path.join(d, "ob1-stats.txt"))
        so = read_stdout_counters(os.path.join(d, "stdout.txt"))
        n_prompt = int(so["n_prompt_tokens"])
        rows = load_route(os.path.join(d, "route.log"))
        sets = sets_for(setsfile, K)
        m = phase_split_metrics(rows, sets, n_prompt)
        eL = int(st["lease_events"])
        eP = int(st["peak_concurrent_lease_bytes"])
        okL = (m["lease_events"] == eL)
        okP = (m["peak_all"] == eP)
        agree += int(okL) + int(okP)
        disagree += int(not okL) + int(not okP)
        print("%-20s %2d %5d %7d %13d %12d  %s %12d %11d  %s %11d  %.10f  %.7f"
              % (name, K, n_prompt, m["pieces"], m["lease_events"], eL,
                 "T" if okL else "F", m["peak_all"], eP, "T" if okP else "F",
                 m["peak_decode"], m["decode_mass"], m["decode_mis_per_token"]))
        out[name] = (m, st, so)
    print("")
    print("ROUTE-DERIVATION COMPARISONS %d  AGREE %d  DISAGREE %d"
          % (agree+disagree, agree, disagree))
    return out

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "g0"):
        gate0()
    if which in ("all", "g12"):
        B1 = "/root/ob5b1/runs"
        B2 = "/root/ob5b2/runs"
        SETS8 = "/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json"
        SETSN = "/root/ob5b2/g2/RESIDENT-SETS-120B-K8-16-24-32.json"
        runs = [
            ("gen-120b-k8-a",   B1+"/gen-120b-k8-a",    8, SETS8),
            ("gen-120b-k8-b",   B1+"/gen-120b-k8-b",    8, SETS8),
            ("gen-120b-k8-c",   B1+"/gen-120b-k8-c",    8, SETS8),
            ("gen-120b-k8-ub32",B1+"/gen-120b-k8-ub32", 8, SETS8),
            ("g2-k8-p1-a",      B2+"/g2-k8-p1-a",       8, SETS8),
            ("g2-k8-p1-b",      B2+"/g2-k8-p1-b",       8, SETS8),
            ("g2-k8-p2",        B2+"/g2-k8-p2",         8, SETS8),
            ("g2-k8-p3",        B2+"/g2-k8-p3",         8, SETS8),
            ("g2-k8-p4-narrow", B2+"/g2-k8-p4-narrow",  8, SETS8),
            ("g2-k8-p2-ub32",   B2+"/g2-k8-p2-ub32",    8, SETS8),
            ("g2-k16-p1",       B2+"/g2-k16-p1",       16, SETSN),
            ("g2-k16-p2",       B2+"/g2-k16-p2",       16, SETSN),
            ("g2-k24-p1",       B2+"/g2-k24-p1",       24, SETSN),
            ("g2-k24-p2",       B2+"/g2-k24-p2",       24, SETSN),
            ("g2-k32-p1",       B2+"/g2-k32-p1",       32, SETSN),
            ("g2-k32-p2",       B2+"/g2-k32-p2",       32, SETSN),
        ]
        gate12(runs)
