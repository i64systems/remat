#!/usr/bin/env python3
"""OB-1b: recompute every byte figure this leg quotes, from first
principles, rather than copying stage 1's or OB-1's arithmetic forward.

Two things are checked here:
  1. THE ACCOUNTING IDENTITIES. resident_always is derived as
     TOTAL_MODEL_BYTES - L*E*PER_EXPERT_BYTES_PER_LAYER for both models and must
     equal the value the prereg and OB-1's RUNLOG state.
  2. THE PREDICTION RULE. peak_concurrent_lease_bytes(K) = (E-K)*PER_EXPERT is
     checked against OB-1's THREE MEASURED points before it is used to predict
     anything, so the extrapolation rests on a rule that reproduced measurements
     rather than on an assertion.

Measured peaks from research/ob1/RUNLOG-1.txt section 9 are hard-coded here as
the check's input; they are OB-1's literal output, cited not recomputed.
"""

M20 = dict(name="gpt-oss-20b", total=12109566624, per_expert=13253760, L=24, E=32)
M120 = dict(name="gpt-oss-120b", total=63387346208, per_expert=13253760, L=36, E=128)

# OB-1 RUNLOG-1.txt section 9, literal.
OB1_MEASURED_PEAK = {16: 212060160, 8: 318090240, 4: 371105280}
OB1_MEASURED_ACCT = {16: 7232182944, 8: 4793491104, 4: 3574145184}
OB1_MEASURED_EXP = {16: 1.674400, 8: 2.526252, 4: 3.388101}


def resident_always(m):
    return m["total"] - m["L"] * m["E"] * m["per_expert"]


def acct(m, K, peak):
    return resident_always(m) + K * m["L"] * m["per_expert"] + peak


def main():
    print("== ACCOUNTING IDENTITIES ==")
    for m in (M20, M120):
        ra = resident_always(m)
        print("  %-13s total=%d  L=%d E=%d per_expert=%d" % (
            m["name"], m["total"], m["L"], m["E"], m["per_expert"]))
        print("  %-13s total_expert_bytes = %d x %d x %d = %d" % (
            "", m["L"], m["E"], m["per_expert"], m["L"] * m["E"] * m["per_expert"]))
        print("  %-13s resident_always    = %d - %d = %d  (%.2f pct of the model)" % (
            "", m["total"], m["L"] * m["E"] * m["per_expert"], ra,
            100.0 * ra / m["total"]))
    print("  CHECK resident_always(20b)  == 1930678944 : %s" % (resident_always(M20) == 1930678944))
    print("  CHECK resident_always(120b) == 2314020128 : %s" % (resident_always(M120) == 2314020128))

    print()
    print("== THE PREDICTION RULE, CHECKED AGAINST OB-1'S THREE MEASURED POINTS ==")
    print("  rule: peak_concurrent_lease_bytes(K) = (E - K) * PER_EXPERT_BYTES_PER_LAYER")
    ok = True
    for K in (16, 8, 4):
        pred = (M20["E"] - K) * M20["per_expert"]
        meas = OB1_MEASURED_PEAK[K]
        a = acct(M20, K, meas)
        e = M20["total"] / float(a)
        good = (pred == meas and a == OB1_MEASURED_ACCT[K]
                and abs(e - OB1_MEASURED_EXP[K]) < 5e-7)
        ok = ok and good
        print("  K=%-3d predicted %d  measured %d  %s | ACCT %d (OB-1 %d) EXP %.6f (OB-1 %.6f) %s" % (
            K, pred, meas, "MATCH" if pred == meas else "DIFFER",
            a, OB1_MEASURED_ACCT[K], e, OB1_MEASURED_EXP[K], "OK" if good else "MISMATCH"))
    print("  RULE REPRODUCES ALL THREE MEASURED POINTS EXACTLY: %s" % ok)

    print()
    print("== 20b PREDICTED CURVE, K in {2,1,0} (peak term PREDICTED, not measured) ==")
    print("  %-3s %14s %14s %14s %12s" % ("K", "pool_bytes", "peak_pred", "ACCT_pred", "EXP_pred"))
    for K in (2, 1, 0):
        pool = K * M20["L"] * M20["per_expert"]
        peak = (M20["E"] - K) * M20["per_expert"]
        a = acct(M20, K, peak)
        print("  %-3d %14d %14d %14d %12.6f" % (K, pool, peak, a, M20["total"] / float(a)))

    print()
    print("== 120b PREDICTED POINT, K=8 of 128 ==")
    K = 8
    pool = K * M120["L"] * M120["per_expert"]
    peak = (M120["E"] - K) * M120["per_expert"]
    a = acct(M120, K, peak)
    print("  pool_bytes  = %d x %d x %d = %d" % (K, M120["L"], M120["per_expert"], pool))
    print("  peak_pred   = (%d - %d) x %d = %d" % (M120["E"], K, M120["per_expert"], peak))
    print("  ACCT_pred   = %d + %d + %d = %d" % (resident_always(M120), pool, peak, a))
    print("  EXP_pred    = %d / %d = %.6f" % (M120["total"], a, M120["total"] / float(a)))

    print()
    print("== THE FLOOR OF THIS DESIGN (why K=0 is the end of the curve) ==")
    for m in (M20, M120):
        ra = resident_always(m)
        peak0 = m["E"] * m["per_expert"]
        a0 = ra + peak0
        print("  %-13s K=0 ACCT = resident_always %d + peak %d = %d" % (m["name"], ra, peak0, a0))
        print("  %-13s     max exposure at K=0 = %.6f ; resident_always is %.1f pct of that floor" % (
            "", m["total"] / float(a0), 100.0 * ra / a0))


if __name__ == "__main__":
    main()
