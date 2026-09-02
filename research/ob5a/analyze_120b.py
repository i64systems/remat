#!/usr/bin/env python3
# OB-5a builder 2b: the P3 verdicts for the 120b row, computed from the runs.
#
# Every expectation in EXPECT below is a literal from OB5A-ALLOC-1-PREREG.md,
# committed at f7a96a0 BEFORE any run of this leg existed. Nothing here is
# fitted: this script can only confirm or refute.
#
# usage: analyze_120b.py RUN_A RUN_B [BUFFERS_BYTES]
import sys, os, re, hashlib, math

RUNS = "/root/ob5a/runs"
REF_A = "/root/ob1b/runs/pag120-prose-a"
REF_B = "/root/ob1b/runs/pag120-prose-b"

# ---- BANKED BEFORE THE RUNS (OB5A-ALLOC-1-PREREG.md) -----------------------
TOTAL            = 63387346208     # s6.3 measured file size
NLAYER, NEXPERT  = 36, 128
PER_EXPERT       = 13253760
RESIDENT_ALWAYS  = 2314020128      # s6.3
K                = 8
POOL_K8          = 3817082880      # s6.3  8 x 36 x 13253760
PRED_PEAKCONC    = 1590451200      # s6.2  (E-K) x per_expert
PRED_ACCT        = 7721554208      # s6.3
PRED_EXPOSURE    = 8.209143        # s6.3
PRED_EVENTS      = 27403           # s6.2
PRED_BYTES_READ  = 363192785280    # s6.2
P2A_BAR          = 7833915680      # s7 P2a  ACCT + edge census
EDGE_BOUND       = 112361472       # s3.5 120b worst-case edge
P2B_CEIL         = 1073741824      # s7 P2b  1 GB
VA_EXPECT        = 63374323968     # s1 the request that used to fail
OLD_REQUEST      = 63374323968     # the single allocation the old allocator makes
P95_REF_MS       = 49619.8         # s7 P3d tau_0, pag120-prose-a
P95_BAR_MS       = 99239.6         # s7 P3d 2.0x
P95_REF_B_MS     = 46732.3         # s7 P3d the A/A partner, recorded so the
                                   # friendlier one cannot be chosen after the fact
BANK_ID = "9d20bd0365554989051d96b6ad4932625b0a6578002879f8253e6fcc21682019"
BANK_RT = "a32d0051bd6d68f2777e64c7b889ae48d56621e9701b107fcef88c0e30cd89c1"
PRED_PER_LAYER = "957,918,863,812,811,822,862,837,781,727,666,642,643,656,760,763,706,740,749,776,751,715,703,718,740,770,750,762,783,760,784,848,776,726,682,644"

FAIL = 0
def verdict(ok, label, detail=""):
    global FAIL
    tag = "PASS" if ok else "*** FAIL ***"
    if not ok: FAIL += 1
    print("  %-58s %s %s" % (label, tag, detail))

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def stats(run):
    d = {}
    with open(os.path.join(run, "ob1-stats.txt")) as f:
        for line in f:
            if "=" in line:
                k, v = line.rstrip("\n").split("=", 1)
                d[k] = v
    return d

def maxrss_kb(run):
    with open(os.path.join(run, "stderr.txt"), errors="replace") as f:
        for line in f:
            m = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", line)
            if m: return int(m.group(1))
    return None

def chunk_ms(d):
    return [int(x) / 1e6 for x in d["chunk_ns"].split(",") if x]

def p95(vals):
    # nearest-rank, the method OB-1b's tau_0 was computed with: the
    # ceil(0.95 n)-th smallest. For n=7 that is the 7th, the maximum.
    s = sorted(vals)
    return s[math.ceil(0.95 * len(s)) - 1]

a_name, b_name = sys.argv[1], sys.argv[2]
BUFFERS = int(sys.argv[3]) if len(sys.argv) > 3 else None
A, B = os.path.join(RUNS, a_name), os.path.join(RUNS, b_name)
sa, sb = stats(A), stats(B)
ra, rb = maxrss_kb(A), maxrss_kb(B)

print("=" * 78)
print("OB5A P3: THE 120b K=8 LEASED ROW ON THE RESERVE/COMMIT ALLOCATOR")
print("=" * 78)
print("run A %s" % A)
print("run B %s" % B)
print("all expectations below are literals of OB5A-ALLOC-1-PREREG.md at f7a96a0")
print()

print("--- P3a IDENTITY AND ROUTE vs THE BANKED PAGED REFERENCE PAIR ---")
ida, idb = sha256(A + "/identity.txt"), sha256(B + "/identity.txt")
rta, rtb = sha256(A + "/route.log"), sha256(B + "/route.log")
print("  banked identity %s" % BANK_ID)
print("  banked route    %s" % BANK_RT)
print("  run A identity  %s" % ida)
print("  run A route     %s" % rta)
print("  run B identity  %s" % idb)
print("  run B route     %s" % rtb)
verdict(ida == BANK_ID, "A identity == banked paged reference")
verdict(rta == BANK_RT, "A route    == banked paged reference")
verdict(idb == BANK_ID, "B identity == banked paged reference")
verdict(rtb == BANK_RT, "B route    == banked paged reference")
print("  identity line, verbatim:")
print("    A: %s" % open(A + "/identity.txt").read().strip())
print("    B: %s" % open(B + "/identity.txt").read().strip())
print("    ref: %s" % open(REF_A + "/identity.txt").read().strip())
print()

print("--- P3e A/A: THE TWO RUNS AGAINST EACH OTHER ---")
verdict(ida == idb, "A/A identity byte-identical")
verdict(rta == rtb, "A/A route byte-identical")
for k in ("lease_events", "peak_concurrent_lease_bytes", "lease_bytes_read",
          "lease_drop_bytes", "route_calls", "per_layer_lease_events",
          "alloc_journal_sha256", "alloc_commit_calls", "alloc_decommit_calls",
          "alloc_commit_model_peak", "alloc_commit_peak_single",
          "alloc_commit_total_bytes", "alloc_va_model_bytes"):
    if k in sa or k in sb:
        va, vb = sa.get(k), sb.get(k)
        short = (va[:24] + "...") if va and len(va) > 27 else va
        verdict(va == vb, "A/A %s" % k, str(short))
print()

print("--- P3b COUNTERS vs THE BANKED PREDICTIONS ---")
ev = int(sa["lease_events"]); pc = int(sa["peak_concurrent_lease_bytes"])
br = int(sa["lease_bytes_read"])
verdict(ev == PRED_EVENTS, "lease_events", "%d  predicted %d" % (ev, PRED_EVENTS))
verdict(pc == PRED_PEAKCONC, "peak_concurrent_lease_bytes", "%d  predicted %d" % (pc, PRED_PEAKCONC))
verdict(br == PRED_BYTES_READ, "lease_bytes_read", "%d  predicted %d" % (br, PRED_BYTES_READ))
verdict(sa.get("per_layer_lease_events") == PRED_PER_LAYER,
        "per_layer_lease_events (36 layers)", "vs the banked series")
print()

print("--- P2b THE N-PROPORTIONAL REQUEST ---")
va = int(sa["alloc_va_model_bytes"]); ps = int(sa["alloc_commit_peak_single"])
print("  alloc_va_model_bytes      %d   (the reservation: DECLARED, not charged, prereg s4.3)" % va)
print("  alloc_commit_peak_single  %d   (%.2f MB)" % (ps, ps / 1048576.0))
verdict(ps <= P2B_CEIL, "peak single commit <= 1 GB ceiling", "%d <= %d" % (ps, P2B_CEIL))
verdict(ps != OLD_REQUEST, "no commit request of %d bytes" % OLD_REQUEST)
print("  reduction of the peak single request vs the old allocator's one call:")
print("    %d / %d = %.4fx" % (OLD_REQUEST, ps, OLD_REQUEST / float(ps)))
print()

print("--- P2a THE ALLOCATION BAR (peak SIMULTANEOUSLY COMMITTED model state) ---")
cp = int(sa["alloc_commit_model_peak"])
trunk = va - NLAYER * NEXPERT * PER_EXPERT
sum_before_edge = trunk + K * NLAYER * PER_EXPERT + pc
edge = cp - sum_before_edge
print("  measured alloc_commit_model_peak   %d" % cp)
print("  prereg P2a bar (ACCT + edge)       %d" % P2A_BAR)
print("  re-derived from the buffer:")
print("    buffer trunk      %d - %d = %d" % (va, NLAYER * NEXPERT * PER_EXPERT, trunk))
print("    K x L x per_expert  %d x %d x %d = %d" % (K, NLAYER, PER_EXPERT, K * NLAYER * PER_EXPERT))
print("    peak concurrent     %d" % pc)
print("    sum before edge     %d" % sum_before_edge)
print("    edge actually paid  %d   (census bound %d)" % (edge, EDGE_BOUND))
verdict(cp <= P2A_BAR, "commit peak <= P2a bar", "%d <= %d, headroom %d" % (cp, P2A_BAR, P2A_BAR - cp))
verdict(0 <= edge <= EDGE_BOUND, "edge within the page census", "%d of %d (%.2f pct)" % (edge, EDGE_BOUND, 100.0 * edge / EDGE_BOUND))
print("  against the model-state request the OLD allocator makes for this run:")
print("    %d / %d = %.4fx smaller" % (OLD_REQUEST, cp, OLD_REQUEST / float(cp)))
print("    commit peak as pct of the model: %.4f pct" % (100.0 * cp / TOTAL))
print()

print("--- P3c EXPOSURE ---")
acct = RESIDENT_ALWAYS + POOL_K8 + pc
print("  ACCT = resident_always + K x L x per_expert + peak_concurrent")
print("       = %d + %d + %d" % (RESIDENT_ALWAYS, POOL_K8, pc))
print("       = %d      (predicted %d)" % (acct, PRED_ACCT))
verdict(acct == PRED_ACCT, "ACCT == the banked prediction")
exp_acct = TOTAL / float(acct)
print("  EXPOSURE_acct = %d / %d = %.6f      (predicted %.6f)" % (TOTAL, acct, exp_acct, PRED_EXPOSURE))
verdict(abs(exp_acct - PRED_EXPOSURE) < 5e-6, "EXPOSURE_acct == the banked prediction",
        "%.6f" % exp_acct)
print("  ACCT as pct of the model: %.4f pct" % (100.0 * acct / TOTAL))
for nm, rss in (("A", ra), ("B", rb)):
    if rss:
        rb_ = rss * 1024
        print("  run %s VmHWM %d kbytes = %d bytes" % (nm, rss, rb_))
        print("    EXPOSURE_rss = %d / %d = %.6f" % (TOTAL, rb_, TOTAL / float(rb_)))
print()

print("--- P2c VmHWM vs COMMITTED MODEL STATE PLUS THE ENGINE'S BUFFERS ---")
if BUFFERS is None:
    print("  NOT COMPUTED: the 120b buffer sizes were not supplied. The 20b figure")
    print("  915046871 from DIAG-BUFFERS-1.txt is NOT carried across; the buffers")
    print("  are a function of the model as well as the configuration.")
else:
    print("  engine buffers at load (measured on the 120b): %d bytes" % BUFFERS)
    for nm, rss in (("A", ra), ("B", rb)):
        if rss:
            hw = rss * 1024
            den = cp + BUFFERS
            print("  run %s  VmHWM %d   commit_peak+buffers %d   unaccounted %d   ratio %.4f  bar 1.25"
                  % (nm, hw, den, hw - den, hw / float(den)))
            verdict(hw / float(den) <= 1.25, "P2c run %s VmHWM within 1.25x" % nm, "%.4f" % (hw / float(den)))
print()

print("--- P3d LATENCY: p95 PER CHUNK vs THE PAGED REFERENCE ---")
print("  tau_0 is the PAGED pair. A fully resident 120b baseline is UNMEASURABLE")
print("  on this 24029 MB box and is named as such, never substituted.")
for nm, run, s in (("A", A, sa), ("B", B, sb)):
    ms = chunk_ms(s)
    print("  run %s chunk_ms (%d chunks): %s" % (nm, len(ms), ", ".join("%.1f" % v for v in ms)))
    print("    p95 (nearest-rank) %.1f ms   mean %.1f ms   max %.1f ms" % (p95(ms), sum(ms) / len(ms), max(ms)))
try:
    refs = chunk_ms(stats(REF_A))
    print("  paged reference pag120-prose-a chunk_ms: %s" % ", ".join("%.1f" % v for v in refs))
    print("    its p95 (nearest-rank) %.1f ms   prereg tau_0 %.1f ms" % (p95(refs), P95_REF_MS))
except Exception as e:
    print("  (paged reference chunk_ns unreadable: %s)" % e)
pa = p95(chunk_ms(sa))
print("  RATIO run A p95 / paged reference p95 = %.1f / %.1f = %.4fx" % (pa, P95_REF_MS, pa / P95_REF_MS))
print("  bar: 2.0x = %.1f ms" % P95_BAR_MS)
print("  (the friendlier partner pag120-prose-b was %.1f ms, implying %.1f ms;" % (P95_REF_B_MS, 2 * P95_REF_B_MS))
print("   the prereg fixed the binding number at %.1f ms before any run)" % P95_BAR_MS)
verdict(pa <= P95_BAR_MS, "P3d p95 <= 2.0x the paged reference", "%.1f <= %.1f ms" % (pa, P95_BAR_MS))
print()

print("--- P4b/P4d ALLOCATOR DETERMINISM ---")
verdict(sa.get("alloc_journal_sha256") == sb.get("alloc_journal_sha256"),
        "P4b alloc_journal_sha256 A == B", str(sa.get("alloc_journal_sha256")))
for nm, s in (("A", sa), ("B", sb)):
    dc = int(s["alloc_decommit_calls"]); ae = int(s.get("lease_active_slices_at_exit", -1))
    lhs = dc + ae; rhs = 6 * int(s["lease_events"])
    verdict(lhs == rhs, "P4d %s decommits + active_at_exit == 6 x lease_events" % nm,
            "%d + %d = %d vs %d" % (dc, ae, lhs, rhs))
    cc = int(s["alloc_commit_calls"])
    resident_slices = K * NLAYER * 6
    implied_trunk = cc - resident_slices - 6 * int(s["lease_events"])
    print("      %s commits %d - resident slices %d - 6 x lease_events %d = %d trunk tensors"
          % (nm, cc, resident_slices, 6 * int(s["lease_events"]), implied_trunk))
print()

print("=" * 78)
print("OB5A_120B_ANALYZE_FAILURES=%d" % FAIL)
print("=" * 78)
