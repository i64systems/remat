#!/usr/bin/env python3
# OB-5b S1: cross-check gate 0's projection against gate 1's OWN routing trace.
#
# Gate 0 read the BANKED RS053 route logs, which were produced by a perplexity
# harness at -ub 4096 on an enwik8-derived prose corpus. Gate 1's runs produce
# their own route log on a different prompt, at n_ubatch 64, with a genuine
# decode tail. This script re-applies gate 0's exact definitions to that trace
# and reports where the two agree and where they do not.
#
# It also predicts lease_events from the routing alone and compares the
# prediction to the engine's measured counter, which is the check that says
# whether the residency model in the projection matches the engine's behaviour.
#
# Analysis only. No model, no runlock, no serve contact.

import json
import sys

import numpy as np

K_USED = 4
SETS = "/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json"
PER_EXPERT_BYTES = 13253760
READ_RATE = 363192785280 / 286.711586     # OB5A-ALLOC-1 F-B3-1, re-derived
VERIFY_RATE = 363192785280 / 154.163691   # OB5A-ALLOC-1 F-B3-1, re-derived


def main():
    if len(sys.argv) < 4:
        sys.exit("usage: gate1_route_check.py <route.log> <n_prompt> <n_gen> [ob1-stats.txt]")
    path = sys.argv[1]
    n_prompt = int(sys.argv[2])
    n_gen = int(sys.argv[3])
    stats_path = sys.argv[4] if len(sys.argv) > 4 else None

    sets_doc = json.load(open(SETS))
    L = int(sets_doc["L"])
    E = int(sets_doc["E"])
    banked8 = [sorted(int(x) for x in sets_doc["resident_sets"]["8"][str(l)])
               for l in range(L)]
    R = np.zeros((L, E), dtype=bool)
    for l in range(L):
        R[l, banked8[l]] = True

    with open(path, "r") as f:
        flat = np.fromstring(f.read().replace(",", " "), sep=" ", dtype=np.int64)
    rows = flat.reshape(-1, 2 + K_USED)
    T = n_prompt + n_gen

    per_layer = []
    for l in range(L):
        m = rows[:, 0] == l
        idx = rows[m, 1]
        ids = rows[m, 2:]
        if idx.shape[0] != T:
            sys.exit("SHAPE: layer %d has %d rows, expected %d" % (l, idx.shape[0], T))
        if not np.array_equal(idx, np.arange(T, dtype=np.int64)):
            sys.exit("ORDER ASSUMPTION VIOLATED at layer %d" % l)
        per_layer.append(ids)

    print("=== GATE 1 ROUTE TRACE, RE-READ WITH GATE 0's DEFINITIONS ===")
    print("route_log     %s" % path)
    print("L %d  E %d  k %d  n_prompt %d  n_gen %d  total tokens %d"
          % (L, E, K_USED, n_prompt, n_gen, T))
    print("")

    # --- phase split ---
    for name, lo, hi in [("PREFILL", 0, n_prompt), ("DECODE", n_prompt, T)]:
        hits = 0
        dec = 0
        mis_tok = np.zeros(hi - lo, dtype=np.int64)
        mis_tok_keep = np.zeros(hi - lo, dtype=np.int64)
        distinct_nonres_window = 0
        for l in range(L):
            ids = per_layer[l][lo:hi]
            hit = R[l][ids]
            hits += int(hit.sum())
            dec += hit.size
            mis_tok += (K_USED - hit.sum(axis=1))
            prev_hit = np.zeros_like(hit)
            if hi - lo > 1:
                # for DECODE the token before the first one is the last prompt token
                prevblk = per_layer[l][lo - 1:hi - 1] if lo > 0 else per_layer[l][lo:hi - 1]
                if lo > 0:
                    prev_hit = (ids[:, :, None] == prevblk[:, None, :]).any(axis=2)
                else:
                    prev_hit[1:] = (ids[1:, :, None] == per_layer[l][lo:hi - 1][:, None, :]).any(axis=2)
            keep_hit = hit | prev_hit
            mis_tok_keep += (K_USED - keep_hit.sum(axis=1))
            u = np.unique(per_layer[l][lo:hi])
            distinct_nonres_window += int((~R[l][u]).sum())
        mass = hits / float(dec)
        print("  %s PHASE (tokens %d..%d)" % (name, lo, hi - 1))
        print("    decisions                    %d" % dec)
        print("    top8 hits                    %d" % hits)
        print("    top8 mass                    %.10f" % mass)
        print("    miss rate                    %.10f" % (1.0 - mass))
        print("    misses/token drop-on-use     mean %.10f  min %d  max %d"
              % (mis_tok.mean(), mis_tok.min(), mis_tok.max()))
        print("    misses/token keep-previous   mean %.10f" % mis_tok_keep.mean())
        print("    DISTINCT non-resident (layer,expert) pairs over the whole phase  %d"
              % distinct_nonres_window)
        b = mis_tok.mean() * PER_EXPERT_BYTES
        print("    drop-on-use lease bytes/token %.0f  read %.6f s  verify %.6f s  serialized %.6f s -> %.6f tok/s decode"
              % (b, b / READ_RATE, b / VERIFY_RATE,
                 b / READ_RATE + b / VERIFY_RATE,
                 1.0 / (b / READ_RATE + b / VERIFY_RATE)))
        print("")
        if name == "PREFILL":
            pf_distinct = distinct_nonres_window
            pf_dropuse = int(mis_tok.sum())
        else:
            dec_dropuse = int(mis_tok.sum())
            dec_mean = float(mis_tok.mean())

    print("=== LEASE-EVENT PREDICTION vs THE ENGINE'S OWN COUNTER ===")
    print("  Two residency models, both computed from the trace alone:")
    print("    A) DROP ON USE, every non-resident selection is a fresh lease")
    print("       prefill %d + decode %d = %d" % (pf_dropuse, dec_dropuse,
                                                  pf_dropuse + dec_dropuse))
    print("    B) HELD FOR THE UBATCH, one lease per distinct non-resident")
    print("       (layer, expert) per llama_decode call:")
    print("       prefill %d + decode %d = %d" % (pf_distinct, dec_dropuse,
                                                  pf_distinct + dec_dropuse))
    if stats_path:
        meas = {}
        for line in open(stats_path):
            if "=" in line:
                k, v = line.strip().split("=", 1)
                meas[k] = v
        le = int(meas.get("lease_events", "-1"))
        print("    MEASURED lease_events                      %d" % le)
        print("    model A error  %+d" % (pf_dropuse + dec_dropuse - le))
        print("    model B error  %+d" % (pf_distinct + dec_dropuse - le))
        print("    measured lease_bytes_read                  %s" % meas.get("lease_bytes_read"))
        print("    lease_events x per_expert_bytes            %d" % (le * PER_EXPERT_BYTES))
        print("    measured peak_concurrent_lease_bytes       %s"
              % meas.get("peak_concurrent_lease_bytes"))
        pc = int(meas.get("peak_concurrent_lease_bytes", "0"))
        print("    peak concurrent, in experts                %.6f"
              % (pc / float(PER_EXPERT_BYTES)))
        print("    batch-regime peak (OB5A-ALLOC-1)           1590451200 (120 experts)")
        print("    decode-regime peak / batch-regime peak     %.10f" % (pc / 1590451200.0))
        trunk = 2314020128
        resident = int(meas.get("resident_bytes_loaded", "0"))
        acct = trunk + resident + pc
        print("")
        print("=== ACCT AND EXPOSURE, MEASURED ON THIS RUN ===")
        print("    resident_always trunk (OB5A-SCOUT-1 s4)    %d" % trunk)
        print("    resident_bytes_loaded (measured)           %d" % resident)
        print("    peak_concurrent_lease_bytes (measured)     %d" % pc)
        print("    ACCT_decode                                %d" % acct)
        print("    model bytes                                63387346208")
        print("    EXPOSURE_acct                              %.6f" % (63387346208 / float(acct)))
        print("    C4 s6.1 PROJECTED ACCT_decode at depth 2   6237133088")
        print("    C4 s6.1 PROJECTED exposure                 10.162898")
        print("    OB5A batch-regime measured ACCT            7721554208")
        print("    OB5A batch-regime measured exposure        8.209143")
        rd = int(meas.get("lease_read_ns", "0")) / 1e9
        vf = int(meas.get("lease_verify_ns", "0")) / 1e9
        dr = int(meas.get("lease_drop_ns", "0")) / 1e9
        tot = int(meas.get("process_ns_since_ob1_init", "0")) / 1e9
        lb = int(meas.get("lease_bytes_read", "0"))
        print("")
        print("=== THE SERIALIZATION TAX, MEASURED ON THIS RUN ===")
        print("    lease_read_seconds                         %.9f" % rd)
        print("    lease_verify_seconds                       %.9f" % vf)
        print("    lease_drop_seconds                         %.9f" % dr)
        print("    process_seconds_since_ob1_init             %.9f" % tot)
        print("    read+verify+drop as a share of process     %.6f" % ((rd + vf + dr) / tot))
        print("    measured read rate                         %.6f bytes/s" % (lb / rd))
        print("    measured verify rate                       %.6f bytes/s" % (lb / vf))
        print("    OB5A batch-regime read rate                %.6f bytes/s" % READ_RATE)
        print("    OB5A batch-regime verify rate              %.6f bytes/s" % VERIFY_RATE)


if __name__ == "__main__":
    main()
