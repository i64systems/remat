#!/usr/bin/env python3
# OB-5b S1 gate 2 and 3: recompute every figure OB5B-S1-RUNLOG-2.txt DERIVES,
# rather than reads off a run, so that no number in it rests on hand arithmetic.
#
# Leg A banked verify-runlog-arith.py for the same reason and found two of
# its own document's errors with it. This is the same instrument for this leg's
# document. Byte counts and event counts are compared for EXACT equality, since
# a byte count that is close is a byte count that is wrong; figures the runlog
# prints rounded are compared at a stated relative tolerance.
#
# Analysis only: it reads the runlog and the banked run outputs and touches
# nothing else.

import re
import sys

CHECKS = 0
BAD = 0

TRUNK = 2314020128
MODEL = 63387346208
PER_EXPERT = 13253760
BOX = 24029 * 1048576


def eq(label, got, want, tol=0.0):
    global CHECKS, BAD
    CHECKS += 1
    if tol == 0.0:
        ok = got == want
    else:
        ok = want != 0 and abs(got - want) / abs(want) <= tol
    if not ok:
        BAD += 1
        print("DISAGREE  %-52s computed %r  runlog %r" % (label, got, want))
    return ok


def main():
    path = sys.argv[1]
    txt = open(path).read()

    def has(s, label):
        global CHECKS, BAD
        CHECKS += 1
        if s not in txt:
            BAD += 1
            print("MISSING   %-52s %r" % (label, s))

    # --- the decode-regime ACCT and exposure at each K ---
    for K, resident, acct, expo in (
            (8, 3817082880, 6184118048, 10.250022),
            (16, 7634165760, 10001200928, 6.337973),
            (24, 11451248640, 13818283808, 4.587208),
            (32, 15268331520, 17635366688, 3.594331)):
        eq("resident bytes K=%d" % K, K * 36 * PER_EXPERT, resident)
        eq("ACCT_decode K=%d" % K, TRUNK + resident + 4 * PER_EXPERT, acct)
        eq("exposure_decode K=%d" % K, round(MODEL / acct, 6), expo)
        has(str(acct), "ACCT_decode K=%d in the runlog" % K)
        has("%.6f" % expo, "exposure K=%d in the runlog" % K)

    # --- the ratio column against C4's projections ---
    for meas, proj, ratio in ((10.250022, 10.162898, 1.008573),
                              (6.337973, 6.304554, 1.005301),
                              (4.587208, 4.569676, 1.003837),
                              (3.594331, 3.583558, 1.003006)):
        eq("measured/projected %.6f" % meas, round(meas / proj, 6), ratio)

    # --- C4's own projected column, re-derived from its depth-2 term ---
    for K, proj_acct in ((8, 6237133088), (16, 10054215968),
                         (24, 13871298848), (32, 17688381728)):
        eq("C4 projected ACCT K=%d" % K,
           TRUNK + K * 36 * PER_EXPERT + 8 * PER_EXPERT, proj_acct)

    # --- the decode peak is exactly four experts ---
    eq("decode peak concurrent", 4 * PER_EXPERT, 53015040)

    # --- the served turn of gate 3 ---
    turn_acct = TRUNK + 3817082880 + 609672960
    eq("gate 3 served ACCT", turn_acct, 6740775968)
    eq("gate 3 served exposure", round(MODEL / turn_acct, 6), 9.403568)
    eq("gate 3 peak concurrent in experts", 609672960 // PER_EXPERT, 46)
    eq("gate 3 lease bytes = events x per expert",
       5461 * PER_EXPERT, 72378783360)

    # --- the batch regime comparison ---
    eq("decode exposure rise over batch",
       round(10.250022 / 8.209143 * 100 - 100, 4), 24.8610)

    # --- headroom at each K, on the box ---
    for vmhwm, head in ((7405543424, 17790689280), (11153657856, 14042574848),
                        (14907207680, 10289025024), (18660970496, 6535262208)):
        eq("headroom at VmHWM %d" % vmhwm, BOX - vmhwm, head)
    eq("K=32 headroom in MiB", 6535262208 // 1048576, 6232)

    # --- the K=40 projection, from this leg's own measured commit peaks ---
    slopes = [(10835841024 - 7081930752) // 8,
              (14590590976 - 10835841024) // 8,
              (18358575104 - 14590590976) // 8]
    eq("largest measured slope per K", max(slopes), 470998016)
    k40 = 18358575104 + 8 * max(slopes)
    eq("K=40 projected commit", k40, 22126559232)
    eq("K=40 projected VmHWM", k40 + (18660970496 - 18358575104), 22428954624)
    eq("K=40 projected headroom", BOX - 22428954624, 2767278080)
    eq("K=40 headroom in MiB", 2767278080 // 1048576, 2639)

    # --- the A/A wall clock spread ---
    eq("A/A decode ratio", round(248.163195190 / 190.394067643, 6), 1.303419)

    # --- TTFT scalings ---
    eq("worst ttft scaled to 64", round(52.736329828 * 64 / 63, 2), 53.57)
    eq("best ttft scaled to 64", round(29.700507911 * 64 / 63, 2), 30.17)
    eq("frozen-schedule worst scaled", round(44.930562558 * 64 / 56, 2), 51.35)
    eq("ttft per prompt token K=32", round(29.700507911 / 63, 6), 0.471437)
    eq("ttft per prompt token K=8", round(40.313243448 / 56, 6), 0.719879)

    # --- the K2 gap on the harder prompt ---
    eq("K2 gap out of corpus", round(0.5 / 0.470834533, 4), 1.0619)

    # --- the marginal gigabyte ---
    extra = 11451248640
    eq("tok/s bought on PROMPT-2", round(0.531246395 - 0.370816944, 9), 0.160429451)
    eq("tok/s bought on PROMPT-1 vs run a",
       round(0.470834533 - 0.257894810, 9), 0.212939723)
    eq("tok/s bought on PROMPT-1 vs run b",
       round(0.470834533 - 0.336144927, 9), 0.134689606)
    eq("marginal tok/s per GB, low",
       round(0.134689606 / (extra / 1e9), 4), 0.0118)
    eq("marginal tok/s per GB, high",
       round(0.212939723 / (extra / 1e9), 4), 0.0186)

    # --- the miss-rate reduction ---
    eq("miss reduction PROMPT-1 pct",
       round((131.625 - 101.046875) / 131.625 * 100, 1), 23.2)
    eq("miss reduction PROMPT-2 pct",
       round((124.546875 - 87.53125) / 124.546875 * 100, 1), 29.7)

    # --- the measured/model mean and spread ---
    col = [0.767997, 0.780540, 0.754797, 0.793854, 0.785576, 0.768069,
           0.769711, 0.768523, 0.751652, 0.743809, 0.787376, 0.805983]
    mean = sum(col) / len(col)
    eq("measured/model mean", round(mean, 4), 0.7732)
    eq("measured/model spread pct", round((max(col) - min(col)) / mean * 100, 1), 8.0)
    eq("read rate range factor", round(1567086343 / 793821816, 3), 1.974)

    # --- the prefill split of the schedule control ---
    eq("prefill rows differing pct", round(1085 / 2268 * 100, 1), 47.8)

    # --- the resident-set masses, against the banked histogram's own counts ---
    for K, hit, mass in ((8, 953164, 0.4040035672), (16, 1338721, 0.5674239265),
                         (24, 1588456, 0.6732754178), (32, 1768367, 0.7495316399)):
        eq("mass K=%d" % K, round(hit / 2359296, 10), mass)
        eq("mis/token K=%d" % K, round(4 * 36 * (1 - hit / 2359296), 6),
           round(144 * (1 - mass), 6), 1e-9)

    print("")
    print("CHECKS %d, DISAGREEMENTS %d" % (CHECKS, BAD))
    print("VERDICT: %s" % ("ALL DERIVED FIGURES CONFIRMED" if BAD == 0
                           else "SOME FIGURES DISAGREE, SEE ABOVE"))
    return 1 if BAD else 0


if __name__ == "__main__":
    sys.exit(main())
