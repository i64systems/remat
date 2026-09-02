#!/usr/bin/env python3
# OB-5b S1 gate 0, second half: render the per-layer table and re-run C4
# section 2.3's decode arithmetic with the MEASURED top-8 hit rate substituted
# for its one unmeasured term.
#
# Every rate below is re-derived from OB5A-ALLOC-1 literals rather than taken
# from that receipt's rounded GB/s figures, and both forms are printed so the
# rounding is visible.
#
#   lease_bytes_read      363192785280   OB5A-ALLOC-1 section 6
#   measured read time       286.711586  OB5A-ALLOC-1 F-B3-1
#   measured verify time     154.163691  OB5A-ALLOC-1 F-B3-1
#   per_expert_bytes          13253760   OB5A-ALLOC-1 s6.1 / RS053 s8
#   L                               36
#   k (expert_used_count)            4
#
# Analysis only. No model, no runlock, no serve contact.

import json
import sys

LEASE_BYTES_READ = 363192785280
READ_SECONDS = 286.711586
VERIFY_SECONDS = 154.163691
PER_EXPERT_BYTES = 13253760
L = 36
K_USED = 4
C4_READ_RATE = 1267000000.0    # C4 section 2.2's rounded figure
C4_VERIFY_RATE = 2356000000.0  # C4 section 2.2's rounded figure

BASE = "/mnt/f/f32/stage/research/ob5b1/gate0/"


def rates():
    r = LEASE_BYTES_READ / READ_SECONDS
    v = LEASE_BYTES_READ / VERIFY_SECONDS
    return r, v


def decode_point(name, misses_per_token, read_rate, verify_rate):
    b = misses_per_token * PER_EXPERT_BYTES
    rs = b / read_rate
    vs = b / verify_rate
    ser = rs + vs
    return {
        "name": name,
        "misses_per_token": misses_per_token,
        "bytes_per_token": b,
        "read_seconds": rs,
        "verify_seconds": vs,
        "serialized_seconds": ser,
        "tok_s_decode_serialized": (1.0 / ser) if ser > 0 else float("inf"),
        "tok_s_decode_read_alone": (1.0 / rs) if rs > 0 else float("inf"),
    }


def main():
    rr, vr = rates()
    print("=== OB5B S1 GATE 0: DERIVED DECODE ARITHMETIC ===")
    print("")
    print("RATES, re-derived from OB5A-ALLOC-1 literals (bytes / seconds):")
    print("  read   %d / %.6f = %.6f bytes/s  (C4 s2.2 prints %.0f)"
          % (LEASE_BYTES_READ, READ_SECONDS, rr, C4_READ_RATE))
    print("  verify %d / %.6f = %.6f bytes/s  (C4 s2.2 prints %.0f)"
          % (LEASE_BYTES_READ, VERIFY_SECONDS, vr, C4_VERIFY_RATE))
    print("  read rate delta vs C4's rounded figure:   %+.6f bytes/s"
          % (rr - C4_READ_RATE))
    print("  verify rate delta vs C4's rounded figure: %+.6f bytes/s"
          % (vr - C4_VERIFY_RATE))
    print("")

    docs = {}
    for lab in ["120b-prose-a", "120b-code-a"]:
        docs[lab] = json.load(open(BASE + lab + ".json"))

    print("=== M-G0-1  PER-LAYER TOP-8 MASS, 120b-prose-a ===")
    print("the resident set under test is the BANKED K=8 prose-ranked set")
    print("(research/ob1b/RESIDENT-SETS-120B-K8.json, sha256 8053f18a...),")
    print("re-derived from this log's own counts: %s"
          % docs["120b-prose-a"]["banked_k8_set_rederives_from_this_log"])
    print("")
    print("%5s  %12s  %12s  %10s  %10s  %8s  %10s"
          % ("layer", "hit", "decisions", "mass", "miss_rate",
             "dead1pct", "mis/token"))
    for p in docs["120b-prose-a"]["per_layer"]:
        print("%5d  %12d  %12d  %10.8f  %10.8f  %8d  %10.6f"
              % (p["layer"], p["top8_decisions_hit"], p["layer_decisions"],
                 p["top8_mass"], p["miss_rate"], p["dead_experts_at_1pct"],
                 p["mean_misses_per_token"]))
    r = docs["120b-prose-a"]["run"]
    print("")
    print("  RUN LEVEL, 120b-prose-a (IN DOMAIN: the set was ranked on this log)")
    print("    top8_decisions_hit          %d of %d"
          % (r["top8_decisions_hit"], docs["120b-prose-a"]["total_decisions"]))
    print("    run top8_mass               %.10f" % r["top8_mass"])
    print("    run miss_rate               %.10f" % r["miss_rate"])
    print("    layer-mean top8_mass        %.10f" % r["layer_mean_top8_mass"])
    print("    layer-min  top8_mass        %.10f" % r["layer_min_top8_mass"])
    print("    layer-max  top8_mass        %.10f" % r["layer_max_top8_mass"])
    print("    misses/token drop-on-use    mean %.10f  min %d  p50 %.1f  p95 %.1f  max %d"
          % (r["mean_misses_per_token_drop_on_use"],
             r["min_misses_per_token_drop_on_use"],
             r["p50_misses_per_token_drop_on_use"],
             r["p95_misses_per_token_drop_on_use"],
             r["max_misses_per_token_drop_on_use"]))
    print("    misses/token keep-previous  mean %.10f  max %d  (declared EXTRA)"
          % (r["mean_misses_per_token_keep_previous"],
             r["max_misses_per_token_keep_previous"]))
    print("")

    print("=== M-G0-2  PER-LAYER TOP-8 MASS, 120b-code-a (CROSS DOMAIN) ===")
    print("the SAME prose-ranked K=8 set, applied to the code route log.")
    print("")
    print("%5s  %12s  %12s  %10s  %10s  %10s"
          % ("layer", "hit", "decisions", "mass", "miss_rate", "mis/token"))
    for p in docs["120b-code-a"]["per_layer"]:
        print("%5d  %12d  %12d  %10.8f  %10.8f  %10.6f"
              % (p["layer"], p["top8_decisions_hit"], p["layer_decisions"],
                 p["top8_mass"], p["miss_rate"], p["mean_misses_per_token"]))
    rc = docs["120b-code-a"]["run"]
    print("")
    print("  RUN LEVEL, 120b-code-a (CROSS DOMAIN)")
    print("    run top8_mass               %.10f" % rc["top8_mass"])
    print("    run miss_rate               %.10f" % rc["miss_rate"])
    print("    misses/token drop-on-use    mean %.10f  max %d"
          % (rc["mean_misses_per_token_drop_on_use"],
             rc["max_misses_per_token_drop_on_use"]))
    print("    misses/token keep-previous  mean %.10f  (declared EXTRA)"
          % rc["mean_misses_per_token_keep_previous"])
    print("")

    print("=== M-G0-3  K SWEEP, SELF-RANKED SETS (each log ranked on itself) ===")
    print("This is the IN-DOMAIN ceiling of a static popularity set at each K.")
    print("")
    print("%5s  %18s  %18s  %14s  %18s  %18s"
          % ("K", "prose mass", "prose miss", "prose mis/tok",
             "code mass (own)", "code miss (own)"))
    ks = sorted(int(x) for x in docs["120b-prose-a"]["ksweep_self_ranked"])
    for K in ks:
        a = docs["120b-prose-a"]["ksweep_self_ranked"][str(K)]
        b = docs["120b-code-a"]["ksweep_self_ranked"][str(K)]
        print("%5d  %18.10f  %18.10f  %14.6f  %18.10f  %18.10f"
              % (K, a["self_ranked_mass"], a["self_ranked_miss_rate"],
                 a["misses_per_token"], b["self_ranked_mass"],
                 b["self_ranked_miss_rate"]))
    print("")

    print("=== M-G0-4  C4 SECTION 2.3 RE-RUN WITH THE MEASURED TERM ===")
    print("Same arithmetic, same rates, only the miss term replaced.")
    print("")
    pts = []
    pts.append(decode_point("P-A  C4 pessimist, uniform K/E=0.0625 (PROJECTED)",
                            L * K_USED * (1.0 - 8.0 / 128.0), C4_READ_RATE,
                            C4_VERIFY_RATE))
    pts.append(decode_point("P-B  C4 policy point, 14.3759 pct (PROJECTED, 20b carry)",
                            L * K_USED * 0.143759, C4_READ_RATE, C4_VERIFY_RATE))
    pts.append(decode_point("G0-IN   MEASURED static K=8, in domain (prose)",
                            r["mean_misses_per_token_drop_on_use"], rr, vr))
    pts.append(decode_point("G0-IN+K MEASURED static K=8 + keep-previous, in domain",
                            r["mean_misses_per_token_keep_previous"], rr, vr))
    pts.append(decode_point("G0-X    MEASURED static K=8, cross domain (code)",
                            rc["mean_misses_per_token_drop_on_use"], rr, vr))
    pts.append(decode_point("G0-X+K  MEASURED static K=8 + keep-previous, cross domain",
                            rc["mean_misses_per_token_keep_previous"], rr, vr))
    print("%-56s %12s %16s %10s %10s %10s %10s"
          % ("point", "mis/token", "bytes/token", "read s", "verify s",
             "tok/s ser", "tok/s read"))
    for p in pts:
        print("%-56s %12.6f %16.0f %10.6f %10.6f %10.6f %10.6f"
              % (p["name"], p["misses_per_token"], p["bytes_per_token"],
                 p["read_seconds"], p["verify_seconds"],
                 p["tok_s_decode_serialized"], p["tok_s_decode_read_alone"]))
    print("")

    print("=== M-G0-5  TIME TO FIRST TOKEN, 64-TOKEN PROMPT ===")
    print("C4 section 2.3 P-C used RS053's W=64 run_mean_distinct 49.185547")
    print("and assumed the resident 8 are all inside it. That assumption is")
    print("now testable: it is only true if the top-8 are among the distinct")
    print("experts of every window, and the honest bound is computed both ways.")
    W64_DISTINCT = 49.185547   # RS053 s5, 120b-prose, W=64, non-overlapping
    opt = (W64_DISTINCT - 8.0) * L
    for nm, mis in [("P-C optimistic (all 8 resident experts inside the window)", opt),
                    ("P-C pessimistic (no resident expert inside the window)",
                     W64_DISTINCT * L)]:
        b = mis * PER_EXPERT_BYTES
        print("  %-58s misses %10.4f  bytes %14.0f  read %8.3f s  verify %8.3f s  serial %8.3f s"
              % (nm, mis, b, b / rr, b / vr, b / rr + b / vr))
    print("")
    print("  measured resident-hit share of a 64-token prefill is reported in")
    print("  M-G0-6 below and settles which of those two lines is nearer.")
    print("")

    print("=== M-G0-6  DISTINCT-EXPERT MISSES OVER A 64-TOKEN WINDOW ===")
    print("(computed directly from the route log by gate0_window.py)")
    try:
        w = json.load(open(BASE + "window64.json"))
        for lab in ["120b-prose-a", "120b-code-a"]:
            d = w[lab]
            print("  %-14s mean distinct/layer/window %10.6f   of which resident %8.6f"
                  % (lab, d["mean_distinct_per_layer_window"],
                     d["mean_resident_hits_per_layer_window"]))
            print("  %-14s mean NON-resident distinct per WINDOW (all %d layers) %12.4f"
                  % ("", L, d["mean_nonresident_distinct_per_window_all_layers"]))
            b = d["mean_nonresident_distinct_per_window_all_layers"] * PER_EXPERT_BYTES
            print("  %-14s -> bytes %14.0f  read %8.3f s  verify %8.3f s  serialized TTFT %8.3f s"
                  % ("", b, b / rr, b / vr, b / rr + b / vr))
    except FileNotFoundError:
        print("  (window64.json not present)")
    print("")
    print("=== M-G0-7  THE PRODUCT KNOB, PRICED WITH THE MEASURED MISS RATE ===")
    print("C4 section 6.1's K table gives ACCT_decode and the estimated committed")
    print("state; this adds the MEASURED in-domain miss rate at each K and the")
    print("decode rate that follows. Static popularity sets only: no policy stack.")
    print("")
    TRUNK = 2314020128            # OB5A-SCOUT-1 s4 ACCT decomposition
    PREFETCH_D2 = 106030080       # C4 s6.1, depth 2 = 8 x per_expert
    ENGINE_BUF = 941195736        # OB5A-ALLOC-1 P2c, measured at 120b load
    UNACCOUNTED = 286522920       # OB5A-ALLOC-1 P2c, run A
    MODEL_BYTES = 63387346208
    BOX_MB = 24029
    print("%5s %16s %16s %14s %12s %12s %12s %12s"
          % ("K", "resident bytes", "ACCT_decode", "exposure",
             "est cmt GB", "miss rate", "mis/token", "tok/s ser"))
    for K in ks:
        a = docs["120b-prose-a"]["ksweep_self_ranked"][str(K)]
        rb = K * L * PER_EXPERT_BYTES
        acct = TRUNK + rb + PREFETCH_D2
        cmt = acct + ENGINE_BUF + UNACCOUNTED
        pt = decode_point("", a["misses_per_token"], rr, vr)
        print("%5d %16d %16d %14.6f %12.4f %12.10f %12.6f %12.6f"
              % (K, rb, acct, MODEL_BYTES / float(acct), cmt / 1e9,
                 a["self_ranked_miss_rate"], a["misses_per_token"],
                 pt["tok_s_decode_serialized"]))
    print("")
    print("  box total %d MB = %.3f GB. The house free-RAM rule is 6 GB, and the"
          % (BOX_MB, BOX_MB * 1048576 / 1e9))
    print("  live serve (pid 654) and searxng (pid 489) sit beside the worker.")
    print("")
    print("=== END GATE 0 DERIVED ARITHMETIC ===")


if __name__ == "__main__":
    main()
