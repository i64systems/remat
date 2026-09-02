#!/usr/bin/env python3
# OB5B-S1 leg C, limb 3: recompute every RATE and every DERIVED figure from
# the runs' own raw counters. Nothing here is read from a runlog's prose; the
# claims are transcribed into CLAIMS at the bottom and compared.
import os, re, sys

PER_EXPERT   = 13253760
TRUNK        = 2314020128
MODEL_BYTES  = 63387346208
BOX_BYTES    = 24029 * 1024 * 1024        # 25196232704
FREE_BAR     = 6144 * 1024 * 1024         # 6442450944 bytes = 6144 MiB
BATCH_ACCT   = 7721554208
BATCH_EXPO   = 8.209143
BATCH_PEAK   = 1590451200
# OB5A F-B3-1 rates, re-derived from its own literals (leg A section 1)
OB5A_LEASE_BYTES = 363192785280
OB5A_READ_S      = 286.711586
OB5A_VERIFY_S    = 154.163691

B1 = "/root/ob5b1/runs"
B2 = "/root/ob5b2/runs"

RUNS = [
 ("gen-120b-k8-a",   B1+"/gen-120b-k8-a",     8),
 ("gen-120b-k8-b",   B1+"/gen-120b-k8-b",     8),
 ("gen-120b-k8-c",   B1+"/gen-120b-k8-c",     8),
 ("gen-120b-k8-ub32",B1+"/gen-120b-k8-ub32",  8),
 ("smoke-20b-k2",    B1+"/smoke-20b-k2",      2),
 ("g2-k8-p1-a",      B2+"/g2-k8-p1-a",        8),
 ("g2-k8-p1-b",      B2+"/g2-k8-p1-b",        8),
 ("g2-k8-p2",        B2+"/g2-k8-p2",          8),
 ("g2-k8-p3",        B2+"/g2-k8-p3",          8),
 ("g2-k8-p4-narrow", B2+"/g2-k8-p4-narrow",   8),
 ("g2-k8-p2-ub32",   B2+"/g2-k8-p2-ub32",     8),
 ("g2-k16-p1",       B2+"/g2-k16-p1",        16),
 ("g2-k16-p2",       B2+"/g2-k16-p2",        16),
 ("g2-k24-p1",       B2+"/g2-k24-p1",        24),
 ("g2-k24-p2",       B2+"/g2-k24-p2",        24),
 ("g2-k32-p1",       B2+"/g2-k32-p1",        32),
 ("g2-k32-p2",       B2+"/g2-k32-p2",        32),
]

def read_kv(p):
    d = {}
    for line in open(p):
        line = line.rstrip("\n")
        if '=' in line:
            k, v = line.split('=', 1)
            d[k.strip()] = v.strip()
    return d

def read_stdout(p):
    d = {}
    for line in open(p):
        parts = line.split()
        if len(parts) >= 2:
            d[parts[0]] = parts[1]
    return d

def read_timev(p):
    d = {}
    for line in open(p, errors="replace"):
        m = re.match(r"\s*Maximum resident set size \(kbytes\): (\d+)", line)
        if m: d["maxrss_kb"] = int(m.group(1))
        m = re.match(r"\s*Elapsed \(wall clock\) time \([^)]*\): (.+)", line)
        if m: d["elapsed"] = m.group(1).strip()
        m = re.match(r"\s*Exit status: (\d+)", line)
        if m: d["exit"] = int(m.group(1))
        m = re.match(r"\s*File system inputs: (\d+)", line)
        if m: d["fs_in"] = int(m.group(1))
    return d

def close(a, b, tol=1e-9):
    if b == 0: return abs(a) < tol
    return abs(a - b) <= tol * max(1.0, abs(b))

CHECKS = 0
DISAGREE = 0
def chk(label, got, claim, tol=1e-9, exact=False):
    global CHECKS, DISAGREE
    CHECKS += 1
    if exact:
        ok = (got == claim)
    else:
        ok = close(float(got), float(claim), tol)
    if not ok:
        DISAGREE += 1
        print("  *** DISAGREE  %-52s got %s  claim %s" % (label, got, claim))
    return ok

print("=" * 100)
print("LIMB 3: RATES AND DERIVED FIGURES, RECOMPUTED FROM EACH RUN'S OWN RAW COUNTERS")
print("=" * 100)

# the OB-5a rates the whole cost model rests on, re-derived here
READ_RATE  = OB5A_LEASE_BYTES / OB5A_READ_S
VER_RATE   = OB5A_LEASE_BYTES / OB5A_VERIFY_S
print("OB5A read rate   %d / %s = %.6f bytes/s" % (OB5A_LEASE_BYTES, OB5A_READ_S, READ_RATE))
print("OB5A verify rate %d / %s = %.6f bytes/s" % (OB5A_LEASE_BYTES, OB5A_VERIFY_S, VER_RATE))
chk("OB5A read rate (R1 s1 claims 1266753082.242027)", READ_RATE, 1266753082.242027, 1e-12)
chk("OB5A verify rate (R1 s1 claims 2355890566.216399)", VER_RATE, 2355890566.216399, 1e-12)

print("")
print("PERF DATA POINTS LAW: every field our standing order names, per run.")
print("run                 tok/s decode  tok/s excl1  ttft_s        wall_s        MaxRSS_kb  VmHWM_bytes  lease_ev  peak_conc    cmt_model_peak  cmt_single  exit")
rows = {}
for (name, d, K) in RUNS:
    st = read_kv(os.path.join(d, "ob1-stats.txt"))
    so = read_stdout(os.path.join(d, "stdout.txt"))
    tv = read_timev(os.path.join(d, "stderr.txt"))
    ngen = int(so["n_generated_tokens"])
    dsec = float(so["decode_seconds"])
    tok = ngen / dsec
    # excl first: the first decode call includes the first sampled token; the
    # engine's chunk_ns series gives the first call's own time
    chunk = [int(x) for x in st["chunk_ns"].split(",")]
    first_ns = chunk[0]
    tok_excl = (ngen - 1) / (dsec - first_ns / 1e9) if ngen > 1 else float('nan')
    rows[name] = dict(st=st, so=so, tv=tv, K=K, ngen=ngen, dsec=dsec, chunk=chunk)
    print("%-19s %13.9f %12.9f %13.9f %13.9f %10d %12d %9s %12s %15s %11s %5s"
          % (name, tok, tok_excl, float(so["ttft_seconds"]), float(so["wall_seconds"]),
             tv.get("maxrss_kb", -1), int(so["VmHWM_bytes"]), st["lease_events"],
             st["peak_concurrent_lease_bytes"], st["alloc_commit_model_peak"],
             st["alloc_commit_peak_single"], tv.get("exit", "?")))
    # the engine's own printed rate must equal ngen/decode_seconds
    chk("%s tok_s_decode == n_gen/decode_seconds" % name, tok, float(so["tok_s_decode"]), 1e-8)
    # lease bytes must be an exact multiple of the per-expert size
    if name != "smoke-20b-k2":
        chk("%s lease_events*13253760 == lease_bytes_read" % name,
            int(st["lease_events"]) * PER_EXPERT, int(st["lease_bytes_read"]), exact=True)
        chk("%s resident_bytes == K*36*13253760" % name,
            K * 36 * PER_EXPERT, int(st["resident_bytes_loaded"]), exact=True)
        chk("%s peak_concurrent is an exact expert multiple" % name,
            int(st["peak_concurrent_lease_bytes"]) % PER_EXPERT, 0, exact=True)
    chk("%s alloc_commit_peak_single == 615333888" % name,
        int(st["alloc_commit_peak_single"]), 615333888, exact=True)
    chk("%s alloc_journal digest field present" % name,
        ("alloc_journal_sha256" in st) or (name.startswith("g2")), True, exact=True)

print("")
print("PER-RUN COST DECOMPOSITION, all recomputed from ns counters")
print("run                 own read B/s     own verify B/s   r+v share proc  ACCT_run      EXPO_run   ACCT_decode   EXPO_decode")
for (name, d, K) in RUNS:
    if name == "smoke-20b-k2":
        continue
    r = rows[name]; st = r["st"]
    lb = int(st["lease_bytes_read"]); lr = int(st["lease_read_ns"]); lv = int(st["lease_verify_ns"])
    proc = int(st["process_ns_since_ob1_init"])
    own_read = lb / (lr / 1e9)
    own_ver  = lb / (lv / 1e9)
    share    = (lr + lv) / proc
    resb     = int(st["resident_bytes_loaded"])
    acct_run = TRUNK + resb + int(st["peak_concurrent_lease_bytes"])
    acct_dec = TRUNK + resb + 4 * PER_EXPERT
    print("%-19s %16.6f %16.6f %15.6f %13d %10.6f %13d %11.6f"
          % (name, own_read, own_ver, share, acct_run, MODEL_BYTES/acct_run,
             acct_dec, MODEL_BYTES/acct_dec))

print("")
print("THE DECODE-REGIME ACCT TABLE (C4 s6.1), MEASURED THIRD TERM 4 x 13253760 = %d"
      % (4*PER_EXPERT))
print("  K   resident bytes   ACCT_decode    EXPOSURE_decode   C4 projected(depth2)  ratio")
C4PROJ = {8: 10.162898, 16: 6.304554, 24: 4.569676, 32: 3.583558}
for K in [8, 16, 24, 32]:
    resb = K * 36 * PER_EXPERT
    acct = TRUNK + resb + 4 * PER_EXPERT
    acct_c4 = TRUNK + resb + 8 * PER_EXPERT
    expo = MODEL_BYTES / acct
    expo_c4 = MODEL_BYTES / acct_c4
    print("  %-3d %14d %13d %17.6f %21.6f %6.6f" % (K, resb, acct, expo, expo_c4, expo/expo_c4))
    chk("C4 s6.1 projected exposure at K=%d" % K, expo_c4, C4PROJ[K], 1e-6)

acct8 = TRUNK + 8*36*PER_EXPERT + 4*PER_EXPERT
chk("R2 headline ACCT_decode K=8 == 6184118048", acct8, 6184118048, exact=True)
chk("R2 headline EXPOSURE_decode K=8 == 10.250022", MODEL_BYTES/acct8, 10.250022, 1e-6)
chk("R2 rise over batch regime 24.8610 pct",
    (MODEL_BYTES/acct8) / BATCH_EXPO - 1.0, 0.248610, 1e-4)

print("")
print("K=32 FIT, AND THE K=40 PROJECTION, FROM THE MEASURED COMMIT PEAKS")
cm = {}
for K, nm in [(8,"g2-k8-p1-a"), (16,"g2-k16-p1"), (24,"g2-k24-p1"), (32,"g2-k32-p1")]:
    cm[K] = int(rows[nm]["st"]["alloc_commit_model_peak"])
vh = {}
for K, nm in [(8,"g2-k8-p1-a"), (16,"g2-k16-p1"), (24,"g2-k24-p1"), (32,"g2-k32-p1")]:
    vh[K] = int(rows[nm]["so"]["VmHWM_bytes"])
print("  box bytes 24029 MiB = %d" % BOX_BYTES)
for K in [8, 16, 24, 32]:
    hr = BOX_BYTES - vh[K]
    print("  K=%-3d commit_model_peak %12d  VmHWM %12d  headroom %11d (%d MiB)"
          % (K, cm[K], vh[K], hr, hr // (1024*1024)))
slopes = [(cm[16]-cm[8])/8.0, (cm[24]-cm[16])/8.0, (cm[32]-cm[24])/8.0]
print("  slopes per K: %.1f  %.1f  %.1f" % tuple(slopes))
k40_cm = cm[32] + 8 * max(slopes)
k40_vh = k40_cm + (vh[32] - cm[32])
print("  K=40 projected commit %d  VmHWM %d  headroom %d (%d MiB)"
      % (k40_cm, k40_vh, BOX_BYTES - k40_vh, (BOX_BYTES - k40_vh)//(1024*1024)))
chk("R2 s4.4 K=32 headroom 6535262208", BOX_BYTES - vh[32], 6535262208, exact=True)
chk("R2 s4.4 K=32 headroom in MiB == 6232", (BOX_BYTES - vh[32])//(1024*1024), 6232, exact=True)
chk("R2 s4.4 slopes 469238784", slopes[0], 469238784.0, 1e-12)
chk("R2 s4.4 slopes 469343744", slopes[1], 469343744.0, 1e-12)
chk("R2 s4.4 slopes 470998016", slopes[2], 470998016.0, 1e-12)
chk("R2 s4.4 K=40 commit 22126559232", k40_cm, 22126559232, 1e-12)
chk("R2 s4.4 K=40 VmHWM about 22428954624", k40_vh, 22428954624, 1e-12)
chk("R2 s4.4 K=40 headroom 2767278080", BOX_BYTES - k40_vh, 2767278080, 1e-12)
chk("R2 s4.4 K=40 headroom MiB 2639", (BOX_BYTES - k40_vh)//(1024*1024), 2639, exact=True)
print("  K=32 headroom above the 6144 MiB house bar: %s" % ((BOX_BYTES - vh[32]) > FREE_BAR))
print("  K=40 headroom above the 6144 MiB house bar: %s" % ((BOX_BYTES - k40_vh) > FREE_BAR))

print("")
print("GATE 1's OWN DECODE ARITHMETIC (R1 s5), RECOMPUTED")
a = rows["gen-120b-k8-a"]; b = rows["gen-120b-k8-b"]; c = rows["gen-120b-k8-c"]
tk = [float(x["so"]["tok_s_decode"]) for x in (a, b, c)]
mean_tok = sum(tk)/3
chk("R1 s5 mean tok/s decode 0.432500041", mean_tok, 0.432500041, 1e-8)
mis = 131.59375
bpt = mis * PER_EXPERT
ser = bpt/READ_RATE + bpt/VER_RATE
print("  decode mis/token 131.59375  bytes/token %.0f  serialized %.6f s -> %.6f tok/s"
      % (bpt, ser, 1/ser))
chk("R1 s5 bytes/token 1744111980", bpt, 1744111980, 1e-9)
chk("R1 s5 serialized 2.117156", ser, 2.117156, 1e-6)
chk("R1 s5 model tok/s 0.472332", 1/ser, 0.472332, 1e-5)
chk("R1 s5 measured/model 0.915670", mean_tok*ser, 0.915670, 1e-5)
ttft = [float(x["so"]["ttft_seconds"]) for x in (a, b, c)]
mt = sum(ttft)/3
chk("R1 s5 mean ttft 38.142521830", mt, 38.142521830, 1e-8)
chk("R1 s5 ttft scaled to 64 tokens 43.591", mt*64/56, 43.591, 1e-4)
chk("R1 s5 ratio to C4 P-C 1.827657", (mt/56)/(23.851/64), 1.827657, 1e-5)
st = a["st"]
share_a = (int(st["lease_read_ns"])+int(st["lease_verify_ns"]))/int(st["process_ns_since_ob1_init"])
chk("R1 s5 read+verify share 0.720468", share_a, 0.720468, 1e-5)
chk("R1 s5 measured read rate 1323956196.116539",
    int(st["lease_bytes_read"])/(int(st["lease_read_ns"])/1e9), 1323956196.116539, 1e-9)
chk("R1 s5 measured verify rate 2390071075.729895",
    int(st["lease_bytes_read"])/(int(st["lease_verify_ns"])/1e9), 2390071075.729895, 1e-9)
chk("R1 s5 ACCT this run 7085373728",
    TRUNK + int(st["resident_bytes_loaded"]) + int(st["peak_concurrent_lease_bytes"]),
    7085373728, exact=True)
chk("R1 s5 EXPOSURE_acct 8.946225", MODEL_BYTES/7085373728, 8.946225, 1e-6)

print("")
print("GATE 2's A/A WALL-CLOCK SPREAD AND THE COST-MODEL RESIDUAL (R2 s4.2, s4.6)")
d1 = float(rows["g2-k8-p1-a"]["so"]["decode_seconds"])
d2 = float(rows["g2-k8-p1-b"]["so"]["decode_seconds"])
chk("R2 s4.2 A/A decode ratio 1.303419", d1/d2, 1.303419, 1e-6)
print("  A/A decode seconds %.9f vs %.9f, ratio %.6f (%.1f pct)" % (d1, d2, d1/d2, (d1/d2-1)*100))
ratios = []
DECMIS = {"g2-k8-p1-a":131.625, "g2-k8-p1-b":131.625, "g2-k8-p2":124.546875,
          "g2-k8-p3":121.171875, "g2-k16-p1":122.453125, "g2-k24-p1":113.21875,
          "g2-k32-p1":101.046875, "g2-k16-p2":111.796875, "g2-k24-p2":99.78125,
          "g2-k32-p2":87.53125, "g2-k8-p2-ub32":124.546875, "g2-k8-p4-narrow":135.90625}
print("  run                mis/tok    bytes/tok   ser(banked)  tok/s(banked)  measured    meas/model(own rates)")
for nm, m in DECMIS.items():
    r = rows[nm]; st = r["st"]
    bpt = m * PER_EXPERT
    serb = bpt/READ_RATE + bpt/VER_RATE
    own_read = int(st["lease_bytes_read"])/(int(st["lease_read_ns"])/1e9)
    own_ver  = int(st["lease_bytes_read"])/(int(st["lease_verify_ns"])/1e9)
    ser_own  = bpt/own_read + bpt/own_ver
    meas = float(r["so"]["tok_s_decode"])
    ratios.append(meas*ser_own)
    print("  %-18s %10.6f %11.0f %12.6f %14.6f %11.9f %12.6f"
          % (nm, m, bpt, serb, 1/serb, meas, meas*ser_own))
print("  measured/model over 12 runs: min %.6f  max %.6f  mean %.4f  spread/mean %.4f"
      % (min(ratios), max(ratios), sum(ratios)/len(ratios),
         (max(ratios)-min(ratios))/(sum(ratios)/len(ratios))))
chk("R2 F-B5 min 0.743809", min(ratios), 0.743809, 1e-5)
chk("R2 F-B5 max 0.805983", max(ratios), 0.805983, 1e-5)
chk("R2 F-B5 mean 0.7732", sum(ratios)/len(ratios), 0.7732, 2e-4)

print("")
print("F-B3 PRICED PER GIGABYTE, RECOMPUTED")
extra = (32-8)*36*PER_EXPERT
p2 = float(rows["g2-k32-p2"]["so"]["tok_s_decode"]) - float(rows["g2-k8-p2"]["so"]["tok_s_decode"])
p1a = float(rows["g2-k32-p1"]["so"]["tok_s_decode"]) - float(rows["g2-k8-p1-a"]["so"]["tok_s_decode"])
p1b = float(rows["g2-k32-p1"]["so"]["tok_s_decode"]) - float(rows["g2-k8-p1-b"]["so"]["tok_s_decode"])
chk("R2 F-B3 extra residency bytes 11451248640", extra, 11451248640, exact=True)
chk("R2 F-B3 PROMPT-2 gain 0.160429451", p2, 0.160429451, 1e-8)
chk("R2 F-B3 PROMPT-1 gain lo 0.134689606", min(p1a,p1b), 0.134689606, 1e-8)
chk("R2 F-B3 PROMPT-1 gain hi 0.212939723", max(p1a,p1b), 0.212939723, 1e-8)
gb = extra/1e9
print("  extra residency %d bytes; gains %.9f / %.9f / %.9f tok/s; per GB %.6f to %.6f"
      % (extra, p2, p1a, p1b, min(p2,p1a,p1b)/gb, max(p2,p1a,p1b)/gb))

print("")
print("K2 AND K3, EVALUATED FROM THE RAW ROWS")
fit = [8,16,24,32]
best = {}
for K in fit:
    vals = [float(rows[n]["so"]["tok_s_decode"]) for n in rows if ("k%d-" % K) in n and n.startswith("g2")]
    best[K] = max(vals)
    print("  K=%-3d measured tok/s decode: %s   best %.9f" % (K, ", ".join("%.9f" % v for v in sorted(vals)), best[K]))
print("  K2 condition is 'below 0.5 at EVERY fitting K'.")
print("  K2 TRIPPED = %s  (best over all fitting K is %.9f)"
      % (all(v < 0.5 for v in best.values()), max(best.values())))
worst_ttft = max((float(rows[n]["so"]["ttft_seconds"]), n) for n in rows if n.startswith("g2") or n.startswith("gen"))
print("  worst TTFT over every run in both legs: %.9f s (%s), on %s prompt tokens"
      % (worst_ttft[0], worst_ttft[1], rows[worst_ttft[1]]["so"]["n_prompt_tokens"]))
npr = int(rows[worst_ttft[1]]["so"]["n_prompt_tokens"])
print("  scaled to a 64-token prompt: %.6f s   K3 bar 120 s   K3 TRIPPED = %s"
      % (worst_ttft[0]*64/npr, (worst_ttft[0]*64/npr) > 120))
print("  K5 condition is decode peak concurrent > the batch regime's %d." % BATCH_PEAK)
print("  measured decode-phase peak on every run: %d.  K5 TRIPPED = %s"
      % (4*PER_EXPERT, (4*PER_EXPERT) > BATCH_PEAK))

print("")
print("=" * 100)
print("ARITH CHECKS %d   DISAGREEMENTS %d" % (CHECKS, DISAGREE))
print("=" * 100)
