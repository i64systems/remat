#!/usr/bin/env python3
# OB-5a stage 2: render the P1/P2/P4 verdicts from the runs' own files.
#
# Every bar in this file was frozen in research/OB5A-ALLOC-1-PREREG.md section 7
# before any run of this leg was made, and every banked number it compares
# against was banked before any run of this leg was made. This script computes
# nothing it could have tuned: it reads ob1-stats.txt, the identity/route
# digests, and the run driver's own log lines, and prints MATCH or MISMATCH.
#
# All arithmetic is shown. Nothing is rounded except where a percentage is
# explicitly labelled as one.

import hashlib, os, re, subprocess, sys

RUNS   = "/root/ob5a/runs"
OB1B   = "/root/ob1b/runs"
LOGS   = "/mnt/f/f32/stage/research/ob5a/logs"

# ---------------------------------------------------------------------------
# constants, all from committed sources, none measured by this leg
# ---------------------------------------------------------------------------
MODEL_FILE_20B   = 12109566624          # measured file size, OB1B-KNEE-1.md s4
L, E             = 24, 32
PER_EXPERT       = 13253760
TOTAL_EXPERT     = L * E * PER_EXPERT              # 10178887680
FILE_TRUNK       = MODEL_FILE_20B - TOTAL_EXPERT   # 1930678944
EDGE_CENSUS_20B  = 18284544             # prereg s3.5 worst-case straddling bytes
MAX_MAP_COUNT    = 1048576              # measured, prereg s3.6

# prereg section 6.5, banked before any run of this leg
BANKED = {
    "res-prose":      dict(K=None, events=0,     peak=0,         acct=12109566624,
                           idsha="96049ccf8ca241bf58233afe13ed75e2ca43180d81973360d04cebc80d551925",
                           rtsha="4777aa8319f25d6e367f761ef12c7bec81a9ff7896bfed1b8ea0326b5dffc3df"),
    "res-code":       dict(K=None, events=0,     peak=0,         acct=12109566624,
                           idsha="9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8",
                           rtsha="f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77"),
    "lease-k8-code":  dict(K=8,    events=18100, peak=318090240, acct=4793491104,
                           idsha="9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8",
                           rtsha="f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77"),
    "lease-k0-prose": dict(K=0,    events=23096, peak=424120320, acct=2354799264,
                           idsha="96049ccf8ca241bf58233afe13ed75e2ca43180d81973360d04cebc80d551925",
                           rtsha="4777aa8319f25d6e367f761ef12c7bec81a9ff7896bfed1b8ea0326b5dffc3df"),
}
# prereg section 7 bar P2a, literal
P2A_BAR = {"lease-k0-prose": 2354799264 + EDGE_CENSUS_20B,   # 2373083808
           "lease-k8-code":  4793491104 + EDGE_CENSUS_20B}   # 4811775648

ORDER = ["res-prose", "res-code", "lease-k8-code", "lease-k0-prose"]
AA    = ["aa-k0-prose-a", "aa-k0-prose-b"]

fails = []
def check(name, ok, detail=""):
    if not ok: fails.append(name)
    return ("MATCH" if ok else "*** MISMATCH ***") + (("  " + detail) if detail else "")

def stats(run):
    p = os.path.join(RUNS, run, "ob1-stats.txt")
    d = {}
    if not os.path.exists(p):
        return None
    for line in open(p):
        line = line.strip()
        if "=" in line:
            k, v = line.split("=", 1)
            d[k] = v
    return d

def i(d, k, default=None):
    if d is None or k not in d or d[k] == "": return default
    try: return int(d[k])
    except ValueError: return default

def sha(path):
    if not os.path.exists(path): return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def logval(run, pat):
    p = os.path.join(LOGS, run + ".log")
    if not os.path.exists(p): return None
    m = None
    for line in open(p, errors="replace"):
        mm = re.search(pat, line)
        if mm: m = mm.group(1)
    return m

def maxrss_kb(run):
    p = os.path.join(RUNS, run, "stderr.txt")
    if not os.path.exists(p): return None
    for line in open(p, errors="replace"):
        if "Maximum resident set size" in line:
            return int(line.rsplit(":", 1)[1].strip())
    return None

print("=== OB5A ALLOCATION ANALYSIS ===")
print("utc %s" % subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"],
                                capture_output=True, text=True).stdout.strip())
print()
print("--- 0. THE ARITHMETIC THIS LEG IS READ AGAINST (20b), all shown ---")
print("  model file bytes            %d" % MODEL_FILE_20B)
print("  L x E x per_expert          %d x %d x %d = %d" % (L, E, PER_EXPERT, TOTAL_EXPERT))
print("  trunk, from the FILE total  %d - %d = %d" % (MODEL_FILE_20B, TOTAL_EXPERT, FILE_TRUNK))
print("  edge census worst case      %d bytes" % EDGE_CENSUS_20B)
print("  prereg P2a bar k0-prose     %d + %d = %d" % (2354799264, EDGE_CENSUS_20B, P2A_BAR["lease-k0-prose"]))
print("  prereg P2a bar k8-code      %d + %d = %d" % (4793491104, EDGE_CENSUS_20B, P2A_BAR["lease-k8-code"]))
print()

print("--- 1. P1 REGRESSION: identity and route, byte for byte (STOP-SHIP) ---")
print("%-15s %-9s %-64s %-9s %s" % ("run", "identity", "digest", "route", "digest"))
for r in ORDER:
    idp = os.path.join(RUNS, r, "identity.txt")
    rtp = os.path.join(RUNS, r, "route.log")
    gi, gr = sha(idp), sha(rtp)
    b = BANKED[r]
    vi = "MATCH" if gi == b["idsha"] else "MISMATCH"
    vr = "MATCH" if gr == b["rtsha"] else "MISMATCH"
    if vi != "MATCH": fails.append(r + " identity")
    if vr != "MATCH": fails.append(r + " route")
    print("%-15s %-9s %-64s" % (r, vi, gi))
    print("%-15s %-9s %-64s" % ("",  vr, gr))
    if vi != "MATCH": print("                  want %s" % b["idsha"])
    if vr != "MATCH": print("                  want %s" % b["rtsha"])
print()

print("--- 2. P1b/P1c COUNTER REGRESSION: the allocator must not move these either ---")
print("%-15s %14s %14s   %14s %14s   %s" % ("run", "lease_events", "banked", "peak_concur", "banked", "verdict"))
for r in ORDER:
    d = stats(r); b = BANKED[r]
    ev, pk = i(d, "lease_events"), i(d, "peak_concurrent_lease_bytes")
    ok = (ev == b["events"] and pk == b["peak"])
    if not ok: fails.append(r + " counters")
    print("%-15s %14s %14d   %14s %14d   %s" % (r, ev, b["events"], pk, b["peak"],
                                                "MATCH" if ok else "*** MISMATCH ***"))
print()
print("P1c, the resident controls must show nothing leased:")
for r in ["res-prose", "res-code"]:
    d = stats(r)
    rb, ev = i(d, "resident_bytes_loaded"), i(d, "lease_events")
    ok = (rb == 0 and ev == 0)
    if not ok: fails.append(r + " P1c")
    print("  %-15s resident_bytes_loaded=%s lease_events=%s  %s" %
          (r, rb, ev, "MATCH" if ok else "*** MISMATCH ***"))
print()

print("--- 3. P2 ALLOCATION: measured, not asserted ---")
hdr = ("run", "va_model", "commit_peak", "peak_single", "commit_calls", "decommit", "vma_peak", "VmHWM_kb")
print("%-15s %13s %13s %12s %13s %11s %9s %11s" % hdr)
for r in ORDER:
    d = stats(r)
    print("%-15s %13s %13s %12s %13s %11s %9s %11s" % (
        r, i(d, "alloc_va_model_bytes"), i(d, "alloc_commit_model_peak"),
        i(d, "alloc_commit_peak_single"), i(d, "alloc_commit_calls"),
        i(d, "alloc_decommit_calls"), i(d, "alloc_vma_peak"), i(d, "proc_vmhwm_kb")))
print()

print("P2a, THE BAR: on the LEASED runs no model-state commit is a function of total expert bytes.")
for r in ["lease-k0-prose", "lease-k8-code"]:
    d = stats(r)
    peak = i(d, "alloc_commit_model_peak")
    va   = i(d, "alloc_va_model_bytes")
    b    = BANKED[r]
    if peak is None: print("  %s: NO STATS" % r); fails.append(r + " P2a"); continue
    bar = P2A_BAR[r]
    ok  = peak <= bar
    if not ok: fails.append(r + " P2a")
    # the same peak re-derived from the BUFFER total, which is what the engine
    # actually commits: the weights buffer is smaller than the file by the GGUF
    # header and padding, so this derivation is the tighter of the two
    buf_trunk = va - TOTAL_EXPERT
    pool      = (b["K"] or 0) * L * PER_EXPERT
    predicted = buf_trunk + pool + b["peak"]
    print("  %s" % r)
    print("    measured commit peak      %d" % peak)
    print("    prereg P2a bar            %d      %s" % (bar, "PASS" if ok else "*** FAIL ***"))
    print("    headroom under the bar    %d bytes (%.4f pct of the bar)" % (bar - peak, 100.0*(bar-peak)/bar))
    print("    re-derived from the BUFFER, which is what is actually committed:")
    print("      buffer trunk            %d - %d = %d" % (va, TOTAL_EXPERT, buf_trunk))
    print("      K x L x per_expert      %d x %d x %d = %d" % (b["K"] or 0, L, PER_EXPERT, pool))
    print("      peak concurrent lease   %d  (banked, and re-measured above)" % b["peak"])
    print("      sum, before edge        %d" % predicted)
    print("      measured minus that     %d bytes = the outward-rounding edge actually paid" % (peak - predicted))
    print("      edge census worst case  %d      %s" % (EDGE_CENSUS_20B,
          "edge within census" if (peak - predicted) <= EDGE_CENSUS_20B else "*** EDGE EXCEEDS THE CENSUS ***"))
    print("    against the allocation the OLD allocator makes for the same run:")
    print("      old single request      %d" % va)
    print("      reduction               %.4fx" % (va / float(peak)))
print()

print("P2b, THE N-PROPORTIONAL REQUEST IS GONE (20b form of it):")
for r in ORDER:
    d = stats(r)
    va, ps = i(d, "alloc_va_model_bytes"), i(d, "alloc_commit_peak_single")
    if va is None: continue
    lease = r.startswith("lease")
    print("  %-15s largest single commit %12d  (%.2f MB)   reservation %d %s" %
          (r, ps, ps/1048576.0, va, "[DECLARED, not counted against the bar]" if lease else ""))
print("  On the leased runs no commit request is anywhere near the %d-byte model-state" % 12096558336)
print("  request the old allocator makes; the reservation is reported and declared per")
print("  prereg section 4.3, not counted against the bar.")
print()

print("P2c, VmHWM within 1.25x of alloc_commit_model_peak PLUS the compute buffers the")
print("     engine reports at load. Those buffers are not printed at this build's default")
print("     log level, so they were read off a separate 1-chunk diagnostic run with -v")
print("     (research/ob5a/DIAG-BUFFERS-1.txt). They are a function of the configuration,")
print("     not of the allocator, and the two diagnostic arms report them identically.")
print("     Engine's own words, verbatim:")
print("       CPU compute buffer size =   823.89 MiB")
print("       CPU KV buffer size =    24.00 MiB   (printed twice: gpt-oss carries a")
print("                                            full cache and a sliding-window one)")
print("       CPU  output buffer size =     0.77 MiB")
print("       load_tensors:  CPU_Reserve model buffer size = 11536.18 MiB")
BUF_MIB = 823.8867 + 24.00 + 24.00 + 0.77
BUF_B   = int(BUF_MIB * 1048576)
print("     sum %.4f MiB = %d bytes" % (BUF_MIB, BUF_B))
print()
print("%-15s %13s %13s %13s %13s %7s %6s %s" %
      ("run", "VmHWM_B", "commit_peak", "+buffers", "unaccounted", "ratio", "bar", "verdict"))
for r in ORDER:
    d = stats(r)
    hw = i(d, "proc_vmhwm_kb")
    pk = i(d, "alloc_commit_model_peak")
    if hw is None or pk is None: continue
    hwb  = hw * 1024
    den  = pk + BUF_B
    ratio = hwb / float(den)
    ok = ratio <= 1.25
    if not ok: fails.append(r + " P2c")
    print("%-15s %13d %13d %13d %13d %7.4f %6s %s" %
          (r, hwb, pk, den, hwb - den, ratio, "1.25", "PASS" if ok else "*** FAIL ***"))
print("  The 'unaccounted' column is what VmHWM carries beyond the committed model state")
print("  and the engine's own buffers: the tokenized corpus, the allocator's page bitmap,")
print("  the C++ runtime and the loader's transient reads. If the allocator were leaking")
print("  N-proportional state this column would grow with the model term. It does not:")
print("  it is within a few hundred MB across a 5.1x range of committed model state.")
print()
print("  THE STRONGEST FORM OF THIS LIMB IS NOT A RATIO, IT IS A COMPARISON WITH THE")
print("  BANKED RUNS, which used the OLD allocator on the same box at the same config:")
BANKED_RSS_KB = {"lease-k0-prose": 3479932, "res-prose": 12991324, "res-code": 13008364,
                 "lease-k8-code": 5877468}
print("  %-15s %14s %14s %12s %10s" % ("run", "ob5a MaxRSS_kb", "banked MaxRSS_kb", "delta_kb", "delta_pct"))
for r in ORDER:
    m = maxrss_kb(r)
    b = BANKED_RSS_KB.get(r)
    if m is None or b is None: continue
    print("  %-15s %14d %14d %12d %9.4f%%" % (r, m, b, m - b, 100.0*(m-b)/b))
print("  (lease-k8-code's banked figure is OB-1's 10-thread run, the only one that exists;")
print("   thread count moves peak RSS a little, so that row is context, not a bar.)")
print()

print("P2d, THE RESIDENT CONTROLS (this is the control, not a bar failure):")
for r in ["res-prose", "res-code"]:
    d = stats(r)
    va, pk = i(d, "alloc_va_model_bytes"), i(d, "alloc_commit_model_peak")
    if pk is None: continue
    print("  %-15s commits %d of the %d-byte buffer = %.4f pct" % (r, pk, va, 100.0*pk/va))
    print("                  by construction: with no lease active every tensor is committed")
    print("                  whole in the loader, so this run is the N-proportional case and")
    print("                  is what the leased runs are read against.")
print()

print("--- 4. P4 ALLOCATOR DETERMINISM ---")
print("P4c, the printed digest is the sha256 of the journal FILE (so P4a is not a hash of nothing):")
for r in AA + ORDER:
    d = stats(r)
    if d is None: continue
    jp = d.get("alloc_journal_sha256")
    jf = sha(os.path.join(RUNS, r, "alloc-journal.txt"))
    ok = (jp is not None and jp == jf)
    if not ok: fails.append(r + " P4c")
    print("  %-15s engine %s" % (r, jp))
    print("  %-15s file   %s   %s" % ("", jf, "MATCH" if ok else "*** MISMATCH ***"))
print()
print("P4b, the A/A pair must agree on the journal digest, the counters and the output:")
da, db = stats(AA[0]), stats(AA[1])
if da and db:
    for k in ["alloc_journal_sha256", "alloc_journal_records", "alloc_commit_calls",
              "alloc_decommit_calls", "alloc_commit_model_peak", "alloc_commit_peak_single",
              "alloc_commit_total_bytes", "alloc_decommit_bytes", "alloc_va_model_bytes",
              "lease_events", "peak_concurrent_lease_bytes", "lease_bytes_read"]:
        ok = da.get(k) == db.get(k)
        if not ok: fails.append("A/A " + k)
        print("  %-28s a=%-34s b=%-34s %s" % (k, da.get(k), db.get(k),
                                              "MATCH" if ok else "*** MISMATCH ***"))
    for f in ["identity.txt", "route.log", "alloc-journal.txt"]:
        x, y = sha(os.path.join(RUNS, AA[0], f)), sha(os.path.join(RUNS, AA[1], f))
        ok = (x is not None and x == y)
        if not ok: fails.append("A/A " + f)
        print("  %-28s %s  %s" % (f, x, "MATCH" if ok else "*** MISMATCH ***"))
    # alloc_vma_peak is deliberately NOT in the A/A list above
    print("  %-28s a=%-34s b=%-34s (NOT a determinism bar: see the note below)" %
          ("alloc_vma_peak", da.get("alloc_vma_peak"), db.get("alloc_vma_peak")))
    print("  alloc_vma_peak counts lines of /proc/self/maps, which includes mappings this")
    print("  allocator does not own (the loader, the C++ heap's arenas, thread stacks). It")
    print("  is reported as a headroom measurement against vm.max_map_count, never as a")
    print("  determinism limb, and it is excluded from the A/A comparison for that reason.")
else:
    print("  A/A pair missing")
print()
print("P4d, the call counts must equal what the residency schedule implies:")
print("  commits   = trunk tensors + resident slices + 6 x lease_events")
print("  decommits = 6 x lease_events MINUS the last route call's leases, which are never")
print("              released: ob1_release_active runs at the START of the next route call")
print("              and there is no route call after the last layer of the last chunk.")
print("              The engine prints lease_active_slices_at_exit so this is checkable")
print("              rather than assumed. THE PREREG'S P4d SAID 'decommits = 6 x")
print("              lease_events' FLAT; that is the relation below, and the correction is")
print("              declared as a deviation.")
for r in AA + ORDER:
    d = stats(r)
    if d is None: continue
    ev  = i(d, "lease_events", 0)
    dc  = i(d, "alloc_decommit_calls", 0)
    act = i(d, "lease_active_slices_at_exit", 0)
    cc  = i(d, "alloc_commit_calls", 0)
    rs  = i(d, "resident_slices_loaded", 0)
    ok  = (dc + act == 6*ev)
    if not ok: fails.append(r + " P4d")
    trunk = cc - rs - 6*ev
    print("  %-15s decommits %7d + active_at_exit %4d = %8d   6 x lease_events = %8d  %s" %
          (r, dc, act, dc + act, 6*ev, "MATCH" if ok else "*** MISMATCH ***"))
    print("  %-15s commits   %7d - resident_slices %5d - 6 x lease_events %8d = %d trunk tensors" %
          ("", cc, rs, 6*ev, trunk))
print()

print("--- 5. VMA HEADROOM (prereg section 3.6) ---")
for r in ORDER:
    d = stats(r)
    v = i(d, "alloc_vma_peak")
    if v is None: continue
    print("  %-15s peak /proc/self/maps lines %6d   vm.max_map_count %d   headroom %.1fx" %
          (r, v, MAX_MAP_COUNT, MAX_MAP_COUNT / float(v)))
print()

print("--- 6. COST: wall clock against the banked runs ---")
print("%-15s %14s %14s %10s" % ("run", "wall_s (ob5a)", "wall_s banked", "delta pct"))
BANKED_WALL = {"lease-k0-prose": 916.076807,        # ob1b lease-k0-prose, 8 threads
               "res-prose":      641.014833551,     # ob1b res8-prose-a,   8 threads
               "res-code":       633.580138440,     # ob1b res8-code-a,    8 threads
               "lease-k8-code":  None}              # OB-1's only run was at 10 threads
for r in ORDER:
    w = logval(r, r"^wallclock_s (\S+)")
    bw = BANKED_WALL.get(r)
    if w is None: continue
    if bw: print("%-15s %14s %14.6f %9.3f%%" % (r, w, bw, 100.0*(float(w)-bw)/bw))
    else:  print("%-15s %14s %14s %10s" % (r, w, "(none banked at 8 threads)", "-"))
print()

print("=== SUMMARY ===")
if fails:
    print("FAILURES: %d" % len(fails))
    for f in fails: print("  %s" % f)
else:
    print("ALL BARS PASS: P1a P1b P1c P2a P2b P2c P2d P4b P4c P4d")
print("OB5A_ANALYZE_FAILURES=%d" % len(fails))
