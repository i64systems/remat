#!/usr/bin/env python3
# OB5B-S1 leg C, limb 2A-bis: parse leg A's OWN printed gate 0 tables
# out of RUNLOG-1 and compare them, cell by cell, against this leg's
# independent recomputation from the raw route logs.
import json, re

PER_EXPERT = 13253760
L, E, KSEL = 36, 128, 4
RUNLOG = "/mnt/f/f32/openbob-wt/research-2/research/OB5B-S1-RUNLOG-1.txt"
SETSF = "/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json"
BASE = "/mnt/f/f32/stage/research/rs053/runs"

def load(p):
    rows = []
    for line in open(p):
        line = line.strip()
        if line:
            f = line.split(',')
            rows.append((int(f[0]), int(f[1]), tuple(int(x) for x in f[2:])))
    return rows

def counts(rows):
    c = [[0]*E for _ in range(L)]
    T = 0
    for (l, t, es) in rows:
        for e in es:
            c[l][e] += 1
        if l == 0:
            T += 1
    return c, T

def topk(c, K):
    return [sorted(sorted(range(E), key=lambda e: (-c[l][e], e))[:K]) for l in range(L)]

def evaluate(rows, sets, T):
    S = [set(s) for s in sets]
    plh = [0]*L
    mpt = [0]*T
    hit = 0
    for (l, t, es) in rows:
        h = sum(1 for e in es if e in S[l])
        hit += h
        plh[l] += h
        mpt[t] += (KSEL - h)
    return hit, plh, mpt

sets8 = None
j = json.load(open(SETSF))["resident_sets"]["8"]
sets8 = [sorted(int(e) for e in j[str(l)]) for l in range(L)]

txt = open(RUNLOG).read()
CHECKS = 0
BAD = 0
def chk(label, got, claim):
    global CHECKS, BAD
    CHECKS += 1
    if got != claim:
        BAD += 1
        print("  *** DISAGREE %-44s got %s  runlog %s" % (label, got, claim))

# ---- section 3.3, the per-layer table, all 36 rows x 5 printed columns ----
rows = load(BASE + "/120b-prose-a/route.log")
c, T = counts(rows)
hit, plh, mpt = evaluate(rows, sets8, T)
blk = txt.split("3.3 M-G0-1")[1].split("RUN LEVEL")[0]
n = 0
for line in blk.splitlines():
    m = re.match(r"\s*(\d+)\s+(\d+)\s+(\d+)\s+([0-9.]+)\s+([0-9.]+)\s+(\d+)\s+([0-9.]+)\s*$", line)
    if not m:
        continue
    l = int(m.group(1))
    n += 1
    chk("layer %d hit" % l, plh[l], int(m.group(2)))
    chk("layer %d decisions" % l, T*KSEL, int(m.group(3)))
    chk("layer %d mass" % l, "%.8f" % (plh[l]/(T*KSEL)), m.group(4))
    chk("layer %d miss" % l, "%.8f" % (1 - plh[l]/(T*KSEL)), m.group(5))
    chk("layer %d mis/token" % l, "%.6f" % (KSEL - plh[l]/T), m.group(7))
print("  per-layer rows parsed from the runlog and re-derived: %d" % n)

# ---- run level, in domain ----
chk("prose top8_decisions_hit", hit, 953164)
chk("prose top8_mass", "%.10f" % (hit/(L*T*KSEL)), "0.4040035672")
chk("prose miss_rate", "%.10f" % (1 - hit/(L*T*KSEL)), "0.5959964328")
s = sorted(mpt)
chk("prose mis/token mean", "%.10f" % (sum(mpt)/len(mpt)), "85.8234863281")
chk("prose mis/token min", s[0], 40)
chk("prose mis/token p50", "%.1f" % s[len(s)//2], "85.0")
chk("prose mis/token p95", "%.1f" % s[int(0.95*len(s))], "115.0")
chk("prose mis/token max", s[-1], 141)
lm = [plh[l]/(T*KSEL) for l in range(L)]
chk("prose layer-mean", "%.10f" % (sum(lm)/L), "0.4040035672")
chk("prose layer-min", "%.10f" % min(lm), "0.2023162842")
chk("prose layer-max", "%.10f" % max(lm), "0.7522735596")
chk("prose banked set re-derives", topk(c, 8) == sets8, True)

# ---- cross domain ----
rowsc = load(BASE + "/120b-code-a/route.log")
cc, Tc = counts(rowsc)
hitc, plhc, mptc = evaluate(rowsc, sets8, Tc)
chk("code top8_mass", "%.10f" % (hitc/(L*Tc*KSEL)), "0.0793007745")
chk("code miss_rate", "%.10f" % (1 - hitc/(L*Tc*KSEL)), "0.9206992255")
chk("code mis/token mean", "%.10f" % (sum(mptc)/len(mptc)), "132.5806884766")
chk("code mis/token max", max(mptc), 144)
chk("code banked set re-derives", topk(cc, 8) == sets8, False)

# ---- section 3.5, the K sweep, both corpora ----
SWEEP = {8: ("0.4040035672", "0.5959964328", "85.823486", "0.3554954529", "0.6445045471"),
         16: ("0.5674239265", "0.4325760735", "62.290955", "0.5288352966", "0.4711647034"),
         24: ("0.6732754178", "0.3267245822", "47.048340", "0.6435796950", "0.3564203050"),
         32: ("0.7495316399", "0.2504683601", "36.067444", "0.7274055481", "0.2725944519"),
         48: ("0.8533664280", "0.1466335720", "21.115234", "0.8436071608", "0.1563928392"),
         64: ("0.9187571208", "0.0812428792", "11.698975", "0.9147169325", "0.0852830675")}
for K, (pm, pmi, pmt, cm, cmi) in SWEEP.items():
    sp = topk(c, K)
    h, _, m = evaluate(rows, sp, T)
    chk("K=%d prose mass" % K, "%.10f" % (h/(L*T*KSEL)), pm)
    chk("K=%d prose miss" % K, "%.10f" % (1 - h/(L*T*KSEL)), pmi)
    chk("K=%d prose mis/token" % K, "%.6f" % (sum(m)/len(m)), pmt)
    sc = topk(cc, K)
    h2, _, m2 = evaluate(rowsc, sc, Tc)
    chk("K=%d code mass" % K, "%.10f" % (h2/(L*Tc*KSEL)), cm)
    chk("K=%d code miss" % K, "%.10f" % (1 - h2/(L*Tc*KSEL)), cmi)

# ---- the free cross-check against RS053's own P_half ----
sp64 = topk(c, 64)
h64, _, _ = evaluate(rows, sp64, T)
chk("K=64 prose mass == RS053 layer-mean P_half 9.18757120768229130e-01",
    "%.17e" % (h64/(L*T*KSEL)), "9.18757120768229130e-01".replace("e-01", "e-01"))

print("")
print("GATE 0 CELL CHECKS %d   DISAGREEMENTS %d" % (CHECKS, BAD))
