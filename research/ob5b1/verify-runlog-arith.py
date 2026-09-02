#!/usr/bin/env python3
# OB-5b S1: recompute every figure research/OB5B-S1-RUNLOG-1.txt DERIVES, so no
# number in that document rests on hand arithmetic. Prints the literal value and
# the value the runlog states, and flags any disagreement.
#
# Analysis only. No model, no runlock, no serve contact.

CHECKS = []


def _show(name, value, stated, ok):
    CHECKS.append(ok)
    print("  %-56s computed %-22s runlog %-22s %s"
          % (name, ("%.9f" % value).rstrip("0").rstrip("."),
             ("%.9f" % stated).rstrip("0").rstrip("."),
             "OK" if ok else "*** DISAGREES ***"))


def chk(name, value, stated, tol=5e-7):
    """Relative agreement, for figures the runlog prints rounded."""
    _show(name, value, stated, abs(value - stated) <= tol * abs(stated))


def chk_i(name, value, stated):
    """EXACT equality, for byte counts and event counts. No tolerance at all:
    a byte count that is close is a byte count that is wrong."""
    _show(name, value, stated, value == stated)


print("=== OB5B-S1-RUNLOG-1 DERIVED-FIGURE VERIFICATION ===")

READ_RATE = 363192785280 / 286.711586
VERIFY_RATE = 363192785280 / 154.163691
PER_EXPERT = 13253760

print("\n-- section 1, the re-derived rates --")
chk("read rate bytes/s", READ_RATE, 1266753082.242027, 1e-9)
chk("verify rate bytes/s", VERIFY_RATE, 2355890566.216399, 1e-9)

print("\n-- section 3, mass against uniform K/E = 8/128 = 0.0625 --")
chk("in-domain mass / uniform", 0.4040035672 / 0.0625, 6.4641, 1e-4)
chk("cross-domain mass / uniform", 0.0793007745 / 0.0625, 1.2688, 1e-4)
chk("gate1 decode mass / uniform", 0.0861545139 / 0.0625, 1.3785, 1e-4)
chk("P-B miss 0.143759 x L x k", 36 * 4 * 0.143759, 20.701296, 1e-6)
chk("box bytes from 24029 MB, in GB", 24029 * 1048576 / 1e9, 25.196, 1e-4)

print("\n-- section 4/5, lease events and bytes --")
chk_i("6049 x per_expert_bytes", 6049 * PER_EXPERT, 80171994240)
chk("peak concurrent in experts", 954270720 / PER_EXPERT, 72.0, 1e-9)
chk("ubatch32 peak in experts", 742210560 / PER_EXPERT, 56.0, 1e-9)
chk("batch-regime peak in experts", 1590451200 / PER_EXPERT, 120.0, 1e-9)
chk("decode peak / batch peak", 954270720 / 1590451200, 0.6, 1e-12)

print("\n-- section 5, ACCT and exposure --")
acct = 2314020128 + 3817082880 + 954270720
chk_i("ACCT measured", acct, 7085373728)
chk("EXPOSURE_acct", 63387346208 / acct, 8.946225, 1e-6)
chk("exposure rise vs 8.209143, pct",
    (63387346208 / acct / 8.209143 - 1.0) * 100.0, 8.9787, 1e-4)

print("\n-- section 5, the serialization tax --")
rd, vf, dr = 60.554869168, 33.543769913, 4.563211333
tot = 130.607581700
chk("read + verify seconds", rd + vf, 94.098639081, 1e-8)
chk("read + verify + drop seconds", rd + vf + dr, 98.661850414, 1e-8)
chk("read+verify share of process", (rd + vf) / tot, 0.720468, 1e-6)
chk("read+verify+drop share of process", (rd + vf + dr) / tot, 0.755407, 1e-6)
chk("measured read rate", 80171994240 / rd, 1323956196.116539, 1e-9)
chk("measured verify rate", 80171994240 / vf, 2390071075.729895, 1e-9)
chk("measured read rate vs batch, pct",
    (80171994240 / rd / READ_RATE - 1.0) * 100.0, 4.5157, 1e-4)
chk("measured verify rate vs batch, pct",
    (80171994240 / vf / VERIFY_RATE - 1.0) * 100.0, 1.4509, 1e-4)

print("\n-- section 5, decode against the arithmetic --")
mis = 131.59375
b = mis * PER_EXPERT
chk_i("decode bytes per token", b, 1744111980.0)
chk("decode read seconds", b / READ_RATE, 1.376837, 1e-5)
chk("decode verify seconds", b / VERIFY_RATE, 0.740320, 1e-5)
chk("decode serialized seconds", b / READ_RATE + b / VERIFY_RATE, 2.117156, 1e-5)
chk("decode projected tok/s", 1.0 / (b / READ_RATE + b / VERIFY_RATE), 0.472332, 1e-5)
tps = (0.415512616 + 0.443048277 + 0.438939230) / 3
chk("measured tok/s decode, mean of 3", tps, 0.432500041, 1e-8)
chk("measured / projected", tps / (1.0 / (b / READ_RATE + b / VERIFY_RATE)),
    0.915670, 1e-5)

print("\n-- section 5, time to first token --")
ttft = (40.421992879 + 37.165344090 + 36.840228521) / 3
chk("measured ttft mean, seconds", ttft, 38.142521830, 1e-8)
pb = 1838 * PER_EXPERT
chk_i("prefill distinct bytes", pb, 24360410880)
chk("prefill read seconds", pb / READ_RATE, 19.2306, 1e-4)
chk("prefill verify seconds", pb / VERIFY_RATE, 10.3402, 1e-4)
chk("prefill serialized seconds", pb / READ_RATE + pb / VERIFY_RATE, 29.5708, 1e-4)
chk("lease share of measured prefill",
    (pb / READ_RATE + pb / VERIFY_RATE) / ttft, 0.775271, 1e-5)
chk("C4 P-C seconds per prompt token", 23.851 / 64, 0.372672, 1e-5)
chk("measured seconds per prompt token", ttft / 56, 0.681116, 1e-5)
chk("ratio to P-C", (ttft / 56) / (23.851 / 64), 1.827657, 1e-5)
chk("ttft scaled to 64 prompt tokens", ttft * 64 / 56, 43.591, 1e-4)

print("\n-- section 3.8, the K=48 row that does not fit --")
acct48 = 2314020128 + 48 * 36 * PER_EXPERT + 106030080
chk_i("K=48 resident bytes", 48 * 36 * PER_EXPERT, 22902497280)
chk_i("K=48 ACCT_decode", acct48, 25322547488)
chk("K=48 est committed GB", (acct48 + 941195736 + 286522920) / 1e9, 26.5503, 1e-3)
acct24 = 2314020128 + 24 * 36 * PER_EXPERT + 106030080
chk("K=24 est committed GB", (acct24 + 941195736 + 286522920) / 1e9, 15.0990, 1e-3)
chk("headroom at K=24, GB",
    24029 * 1048576 / 1e9 - (acct24 + 941195736 + 286522920) / 1e9, 10.10, 1e-2)
acct32 = 2314020128 + 32 * 36 * PER_EXPERT + 106030080
chk("headroom at K=32, GB",
    24029 * 1048576 / 1e9 - (acct32 + 941195736 + 286522920) / 1e9, 6.28, 1e-2)

print("\n-- section 3.7, the TTFT window projections --")
chk_i("prose nonresident bytes per 64-token window",
      1507.90625 * PER_EXPERT, 19985427540.0)
chk_i("code nonresident bytes per 64-token window",
      1805.75390625 * PER_EXPERT, 23933028892.5)

print("\n-- section 4.1, the allocator's single-request reduction --")
chk("63374323968 / 615333888", 63374323968 / 615333888, 102.9918, 1e-4)

print("")
bad = CHECKS.count(False)
print("CHECKS %d, DISAGREEMENTS %d" % (len(CHECKS), bad))
print("VERDICT: %s" % ("ALL DERIVED FIGURES CONFIRMED" if bad == 0
                       else "*** RUNLOG MUST BE CORRECTED ***"))
raise SystemExit(1 if bad else 0)
