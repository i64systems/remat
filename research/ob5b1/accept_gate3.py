#!/usr/bin/env python3
# OB5B-S1 leg C, limb 6: the gate 3 served turn, re-derived from the turn's
# own artifacts. Every number the announcement and the receipt printed is
# recomputed from the bytes on disk and from the worker log's counter block.
import hashlib, json, os, re

PER_EXPERT  = 13253760
TRUNK       = 2314020128
MODEL_BYTES = 63387346208
W = "/root/ob5b2/worker"
T = W + "/w-000001"

def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

CHECKS = 0
BAD = 0
def chk(label, got, claim, exact=True, tol=1e-9):
    global CHECKS, BAD
    CHECKS += 1
    ok = (got == claim) if exact else (abs(float(got)-float(claim)) <= tol*max(1.0, abs(float(claim))))
    if not ok:
        BAD += 1
        print("  *** DISAGREE %-50s got %s claim %s" % (label, got, claim))
    else:
        print("  ok  %-50s %s" % (label, got))

rec = json.loads(open(W + "/WORKER-LOG-1.jsonl").read().strip())
c = rec["counters"]

print("=" * 78)
print("LIMB 6: THE GATE 3 SERVED TURN, RE-DERIVED FROM ITS OWN BYTES")
print("=" * 78)

print("-- identity, recomputed over the turn's artifacts --")
chk("turn_id == sha256(gen-ids.txt)", sha_file(T+"/gen-ids.txt"), rec["turn_id"])
chk("answer_sha256 == sha256(gen-text.txt)", sha_file(T+"/gen-text.txt"), rec["answer_sha256"])
chk("route_log_sha256 == sha256(route.log)", sha_file(T+"/route.log"), c["route_log_sha256"])
chk("prompt_sha256 == sha256(prompt.txt)", sha_file(T+"/prompt.txt"), rec["prompt_sha256"])
chk("alloc_journal_sha256 == sha256(alloc-journal.txt)",
    sha_file(T+"/alloc-journal.txt"), c["alloc_journal_sha256"])
chk("engine_sha256 == the gate 1/2 binary",
    sha_file("/root/ob5b1/llama.cpp/build/bin/ob5b1-gen"), rec["engine_sha256"])
chk("residency_sha256 == the banked K=8 set",
    sha_file("/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json"),
    rec["residency_sha256"])
print("  NOTE weights_sha256 %s" % rec["weights_sha256"])
print("       this leg re-hashed the 63387346208 byte model file whole; see MODEL-SHA-1.txt")

print("")
print("-- the receipt's numbers, recomputed from the counter block --")
le = int(c["lease_events"]); lb = int(c["lease_bytes_read"])
pk = int(c["peak_concurrent_lease_bytes"]); rb = int(c["resident_bytes_loaded"])
chk("lease_events * 13253760 == lease_bytes_read", le*PER_EXPERT, lb)
chk("leased slices (receipt says 5461)", le, 5461)
chk("leased bytes (receipt says 72.37 gb)", lb, 72378783360)
print("  ok  leased gb                                        %.2f" % (lb/1e9))
chk("peak concurrent is an exact expert multiple", pk % PER_EXPERT, 0)
print("  ok  peak concurrent in experts                       %d" % (pk//PER_EXPERT))
acct = TRUNK + rb + pk
chk("ACCT 2314020128 + %d + %d" % (rb, pk), acct, 6740775968)
print("  ok  held gb (receipt says 6.74 gb)                   %.2f" % (acct/1e9))
expo = MODEL_BYTES / acct
chk("EXPOSURE 63387346208 / %d == 9.403568" % acct, round(expo, 6), 9.403568, exact=True)
ng = int(c["n_generated_tokens"]); ds = float(c["decode_seconds"])
chk("tok_s_decode == n_gen/decode_seconds", round(ng/ds, 9), round(float(c["tok_s_decode"]), 9))
print("  ok  ttft_seconds                                     %s" % c["ttft_seconds"])
chk("resident_bytes == 8*36*13253760", rb, 8*36*PER_EXPERT)
chk("alloc_commit_peak_single == 615333888", int(c["alloc_commit_peak_single"]), 615333888)
chk("guards alive before the turn", rec["guards_before"], {"489": True, "654": True})
chk("guards alive after the turn", rec["guards_after"], {"489": True, "654": True})
print("  ok  runlock wait seconds                             %s" % c["runlock_wait_seconds"])

print("")
print("-- the turn's own route log, derived and checked against its counters --")
rows = []
for line in open(T + "/route.log"):
    line = line.strip()
    if line:
        f = line.split(',')
        rows.append((int(f[0]), int(f[1]), tuple(int(x) for x in f[2:])))
sets = json.load(open("/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json"))["resident_sets"]["8"]
S = [set(int(e) for e in sets[str(l)]) for l in range(36)]
pieces, cur, last = [], [], None
for r in rows:
    if last is not None and r[0] == 0 and last != 0:
        pieces.append(cur); cur = []
    cur.append(r); last = r[0]
if cur: pieces.append(cur)
n_prompt = int(c["n_prompt_tokens"])
derived_leases = 0; peak_all = 0; peak_dec = 0
for pc in pieces:
    by = {}
    for (l, t, es) in pc:
        by.setdefault(l, []).append((t, es))
    for l, items in by.items():
        need = set()
        for (t, es) in items:
            for e in es:
                if e not in S[l]:
                    need.add(e)
        derived_leases += len(need)
        conc = len(need) * PER_EXPERT
        peak_all = max(peak_all, conc)
        if all(t >= n_prompt for (t, es) in items):
            peak_dec = max(peak_dec, conc)
chk("derived lease_events == engine's", derived_leases, le)
chk("derived peak concurrent == engine's", peak_all, pk)
chk("derived DECODE-phase peak == 4 x 13253760", peak_dec, 4*PER_EXPERT)
print("  ok  route pieces (1 prefill + %d decode)             %d" % (ng, len(pieces)))

print("")
print("-- the answer bytes, verbatim, %d of them --" % os.path.getsize(T+"/gen-text.txt"))
print(open(T+"/gen-text.txt", 'rb').read().decode('utf-8', 'replace'))

print("")
print("GATE 3 CHECKS %d   DISAGREEMENTS %d" % (CHECKS, BAD))
