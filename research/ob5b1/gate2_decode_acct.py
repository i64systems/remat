#!/usr/bin/env python3
# OB-5b S1 gate 2: THE DECODE-REGIME ACCOUNTING, derived from each run's own
# route log and checked against that run's own engine counters.
#
# WHAT THIS ANSWERS, and why it is a derivation rather than a new counter.
# Leg A's finding F-A4: peak_concurrent_lease_bytes in a served turn is set
# by the PREFILL ubatch, not by the decode tail, so the decode-regime ACCT that
# C4 section 6.1 and scope-ledger entry OB5-023 are about had not been measured.
# Leg A named two ways to get it and called either acceptable. Adding a
# per-phase counter to ob1-lease.cpp would change libllama's .text and void the
# engine-lineage proof gate 1 rests on, so this leg does not. Instead:
#
#   1. The engine computes peak_concurrent as the maximum, over route calls, of
#      the bytes leased AT THAT CALL for that layer (ob1_on_route: the previous
#      layer's leases are released at the top, then `concurrent` sums the
#      non-resident needed experts of this layer). That quantity is a pure
#      function of the route log, the resident set and the batch schedule.
#   2. So this script recomputes it from the route log, and PROVES the
#      recomputation against the engine's own counter on the whole run. When
#      the whole-run maximum matches the engine to the byte, the DECODE-PHASE
#      maximum from the same computation is a measurement of the same kind.
#   3. And a narrow-prefill control run (a three byte prompt, so the prefill
#      route call is as narrow as a decode route call) has the engine itself
#      print a decode-width peak, which is the third, independent check.
#
# Analysis only. No model, no runlock, no serve contact.

import json
import re
import sys

PER_EXPERT = 13253760
TRUNK = 2314020128          # OB5A-SCOUT-1 s4, the 120b resident_always
MODEL_BYTES = 63387346208
K_USED = 4
# OB5A-ALLOC-1 F-B3-1, re-derived from the literals exactly as leg A did.
READ_RATE = 363192785280 / 286.711586
VERIFY_RATE = 363192785280 / 154.163691


def load_stats(p):
    out = {}
    for line in open(p):
        line = line.strip()
        if "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


def stdout_num(so, key):
    m = re.search(r"^%s\s+(\S+)$" % re.escape(key), so, re.M)
    return m.group(1) if m else None


def main():
    run = sys.argv[1]
    sets_path = sys.argv[2]
    K = int(sys.argv[3])

    so = open(run + "/stdout.txt").read()
    st = load_stats(run + "/ob1-stats.txt")
    n_prompt = int(stdout_num(so, "n_prompt_tokens"))
    n_gen = int(stdout_num(so, "n_generated_tokens"))
    ub = int(re.search(r"^n_ubatch\s+(\d+)$", so, re.M).group(1))
    L = int(st["layers"])
    E = int(st["experts"])

    sets = json.load(open(sets_path))["resident_sets"][str(K)]
    resident = [set(int(x) for x in sets[str(l)]) for l in range(L)]

    rows = []
    for line in open(run + "/route.log"):
        line = line.strip()
        if line:
            rows.append([int(x) for x in line.split(",")])

    T = n_prompt + n_gen
    # THE CALL EACH TOKEN BELONGS TO. The prefill is submitted in ceil(n_prompt
    # / n_ubatch) pieces of exactly n_ubatch tokens; decode submits exactly one
    # token per llama_decode. That is the frozen schedule ob5b1-gen prints, so
    # the mapping is a fact of the bound state and not a guess.
    def call_of(t):
        return t // ub if t < n_prompt else (n_prompt + ub - 1) // ub + (t - n_prompt)

    # per (call, layer) -> set of non-resident experts
    need = {}
    per_token_miss = [0] * T
    hits = [0, 0]     # prefill, decode
    dec = [0, 0]
    for r in rows:
        l, t, ids = r[0], r[1], r[2:2 + K_USED]
        if t >= T:
            sys.exit("route log token_index %d beyond T=%d" % (t, T))
        phase = 0 if t < n_prompt else 1
        distinct = set(ids)
        h = len(distinct & resident[l])
        hits[phase] += h
        dec[phase] += len(distinct)
        per_token_miss[t] += len(distinct) - h
        key = (call_of(t), l)
        need.setdefault(key, set()).update(e for e in distinct if e not in resident[l])

    whole_peak = 0
    decode_peak = 0
    decode_vals = []
    prefill_calls = (n_prompt + ub - 1) // ub
    lease_pred = 0
    lease_pred_prefill = 0
    lease_pred_decode = 0
    for (c, l), s in need.items():
        b = len(s) * PER_EXPERT
        lease_pred += len(s)
        whole_peak = max(whole_peak, b)
        if c >= prefill_calls:
            decode_peak = max(decode_peak, b)
            decode_vals.append(b)
            lease_pred_decode += len(s)
        else:
            lease_pred_prefill += len(s)

    meas_peak = int(st["peak_concurrent_lease_bytes"])
    meas_lease = int(st["lease_events"])
    print("run                        %s" % run)
    print("K %d  L %d  E %d  n_prompt %d  n_gen %d  n_ubatch %d  prefill_pieces %d"
          % (K, L, E, n_prompt, n_gen, ub, prefill_calls))
    print("")
    print("-- THE DERIVATION, CHECKED AGAINST THE ENGINE ON THE WHOLE RUN --")
    print("derived whole-run peak concurrent   %d  = %.6f experts"
          % (whole_peak, whole_peak / PER_EXPERT))
    print("engine  peak_concurrent_lease_bytes %d" % meas_peak)
    print("PEAK_DERIVATION_MATCHES_ENGINE      %s" % (whole_peak == meas_peak))
    print("derived lease_events (model B)      %d" % lease_pred)
    print("engine  lease_events                %d" % meas_lease)
    print("LEASE_DERIVATION_MATCHES_ENGINE     %s" % (lease_pred == meas_lease))
    print("derived lease_events prefill        %d" % lease_pred_prefill)
    print("derived lease_events decode         %d" % lease_pred_decode)
    print("")
    print("-- THE DECODE-REGIME FIGURE THE DERIVATION THEREFORE LICENSES --")
    print("decode-phase peak concurrent        %d  = %.6f experts"
          % (decode_peak, decode_peak / PER_EXPERT))
    if decode_vals:
        print("decode-phase mean concurrent        %.4f  over %d (call,layer) pairs"
              % (sum(decode_vals) / len(decode_vals), len(decode_vals)))
    rb = int(st["resident_bytes_loaded"])
    acct_run = TRUNK + rb + meas_peak
    acct_dec = TRUNK + rb + decode_peak
    print("ACCT whole run   %d + %d + %d = %d   exposure %.6f"
          % (TRUNK, rb, meas_peak, acct_run, MODEL_BYTES / acct_run))
    print("ACCT decode only %d + %d + %d = %d   exposure %.6f"
          % (TRUNK, rb, decode_peak, acct_dec, MODEL_BYTES / acct_dec))
    print("")
    print("-- ROUTING, BY PHASE (gate 0's definitions, this run's own trace) --")
    for i, nm, toks in ((0, "prefill", n_prompt), (1, "decode ", n_gen)):
        d = dec[i]
        if d == 0:
            continue
        mass = hits[i] / d
        mt = [per_token_miss[t] for t in
              (range(n_prompt) if i == 0 else range(n_prompt, T))]
        print("%s decisions %6d  topK mass %.10f  miss %.10f  mis/token mean %.6f "
              "min %d max %d"
              % (nm, d, mass, 1 - mass, sum(mt) / len(mt), min(mt), max(mt)))
    mtd = [per_token_miss[t] for t in range(n_prompt, T)]
    mpt = sum(mtd) / len(mtd)
    bpt = mpt * PER_EXPERT
    ser = bpt / READ_RATE + bpt / VERIFY_RATE
    print("")
    print("-- THE LEASE-ONLY COST MODEL AGAINST THE MEASURED DECODE --")
    print("decode mis/token           %.10f" % mpt)
    print("bytes/token                %.4f" % bpt)
    print("read s/token               %.6f   verify s/token %.6f"
          % (bpt / READ_RATE, bpt / VERIFY_RATE))
    print("serialized s/token         %.6f -> %.6f tok/s" % (ser, 1 / ser))
    tps = float(stdout_num(so, "tok_s_decode"))
    print("measured tok/s DECODE      %.9f" % tps)
    print("measured / lease-only      %.6f" % (tps * ser))
    lr = int(st["lease_read_ns"]) / 1e9
    lv = int(st["lease_verify_ns"]) / 1e9
    ld = int(st["lease_drop_ns"]) / 1e9
    pr = int(st["process_ns_since_ob1_init"]) / 1e9
    lb = int(st["lease_bytes_read"])
    # THE SAME MODEL AT THIS RUN'S OWN MEASURED RATES. The banked rates above
    # were taken in the batch regime on a warm 63 GB working set; a long decode
    # on this box reads colder as it goes, so the constant is the thing that
    # moves and this line separates the constant from the structure.
    own_r = lb / lr
    own_v = lb / lv
    ser2 = bpt / own_r + bpt / own_v
    print("at THIS run's own rates    %.6f s/token -> %.6f tok/s   measured/model %.6f"
          % (ser2, 1 / ser2, tps * ser2))
    print("")
    print("-- THE SERIALIZATION TAX ON THIS RUN --")
    print("lease_read_s %.9f  lease_verify_s %.9f  lease_drop_s %.9f  process_s %.9f"
          % (lr, lv, ld, pr))
    print("read+verify share of process time   %.6f" % ((lr + lv) / pr))
    print("read+verify+drop share              %.6f" % ((lr + lv + ld) / pr))
    print("measured read rate   %.6f bytes/s" % (lb / lr))
    print("measured verify rate %.6f bytes/s" % (lb / lv))
    print("")
    print("-- HAS THE DECODE RATE STOPPED MOVING? (chunk_ns, one entry per")
    print("   llama_decode call after the first) --")
    ch = [int(x) for x in st["chunk_ns"].split(",") if x]
    dchunks = ch[-n_gen:] if len(ch) >= n_gen else ch
    if dchunks:
        q = max(1, len(dchunks) // 4)
        print("decode calls timed %d  first quarter mean %.6f s  last quarter mean %.6f s"
              % (len(dchunks), sum(dchunks[:q]) / q / 1e9, sum(dchunks[-q:]) / q / 1e9))
        print("min %.6f s  max %.6f s  last/first %.6f"
              % (min(dchunks) / 1e9, max(dchunks) / 1e9,
                 (sum(dchunks[-q:]) / q) / (sum(dchunks[:q]) / q)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
