#!/usr/bin/env python3
"""OB4B-PARDEC-1 phase 1: turn the run batch's stats files into the literal
numbers the runlog reports.

p95 is computed exactly the way OB-1 computed it and OB-4 reused: nearest-rank
over the run's own chunk_ns series (rank = ceil(0.95*n)), where chunk_ns holds
the wall time between successive layer-0 routing callbacks, one sample per
perplexity chunk boundary. Reported in milliseconds.

Nothing here is rounded, inferred or substituted. A missing run is reported as
missing, not filled in.
"""

import hashlib
import json
import math
import os

MINE = "/root/ob4b/runs"
OB4 = "/root/ob4/runs"
OUT = "/mnt/f/f32/openbob-wt/ob4/research/ob4b/run-analysis.json"

# the frozen bar, from research/OB4B-PARDEC-1-PREREG.md
CONTROL_P95_MS = 15640.098009          # ob4-res-code, this engine family's own K=0 run
BAR_RATIO = 1.734578198064283          # OB-4 run a: ACCEPT iff strictly less
IDENTITY_REF = "9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8"
ROUTE_REF = "f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77"


def read_stats(path):
    d = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            d[k] = v
    return d


def ints(s):
    return [int(x) for x in s.split(",") if x != ""]


def p95_ms(chunk_ns_csv):
    v = sorted(ints(chunk_ns_csv))
    if not v:
        return None, 0, 0
    rank = int(math.ceil(0.95 * len(v)))
    return v[rank - 1] / 1e6, len(v), rank


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def rss_bytes(stderr_path):
    with open(stderr_path, errors="replace") as f:
        for line in f:
            if "Maximum resident set size" in line:
                return int(line.strip().split()[-1]) * 1024
    return None


def wall_s(stderr_path):
    with open(stderr_path, errors="replace") as f:
        for line in f:
            if "Elapsed (wall clock)" in line:
                t = line.strip().split()[-1]
                parts = [float(x) for x in t.split(":")]
                if len(parts) == 3:
                    return parts[0] * 3600 + parts[1] * 60 + parts[2]
                if len(parts) == 2:
                    return parts[0] * 60 + parts[1]
                return parts[0]
    return None


def summarize(run_dir, label):
    st = read_stats(os.path.join(run_dir, "ob1-stats.txt"))
    p, n, rank = p95_ms(st.get("chunk_ns", ""))
    proc = int(st.get("process_ns_since_ob1_init", 0))
    lr = int(st.get("lease_read_ns", 0))
    lv = int(st.get("lease_verify_ns", 0))
    ld = int(st.get("ob4_lease_decode_ns", 0))
    lb = int(st.get("ob4_lease_blob_read_ns", 0))
    rd = int(st.get("ob4_resident_decode_ns", 0))
    pw = int(st.get("ob4b_pool_wall_ns", 0)) or None
    out = {
        "label": label,
        "dir": run_dir,
        "mode": st.get("ob1_mode"),
        "K": st.get("ob1_k"),
        "ob4_store": st.get("ob4_store", "off"),
        "decode_threads": int(st.get("ob4b_decode_threads", 0)) or None,
        "chunk_count": n,
        "p95_rank": rank,
        "p95_ms": p,
        "p95_over_control": (p / CONTROL_P95_MS) if p else None,
        "identity_sha256": sha(os.path.join(run_dir, "identity.txt")),
        "route_log_sha256": sha(os.path.join(run_dir, "route.log")),
        "identity_matches_reference": sha(os.path.join(run_dir, "identity.txt")) == IDENTITY_REF,
        "route_matches_reference": sha(os.path.join(run_dir, "route.log")) == ROUTE_REF,
        "peak_rss_bytes": rss_bytes(os.path.join(run_dir, "stderr.txt")),
        "wall_clock_s": wall_s(os.path.join(run_dir, "stderr.txt")),
        "process_ns": proc,
        "lease_events": int(st.get("lease_events", 0)),
        "lease_get_bytes_ns": lr,
        "lease_verify_ns": lv,
        "lease_decode_ns": ld,
        "lease_blob_read_ns": lb,
        "resident_decode_ns": rd,
        "lease_decode_share_of_lease_get_bytes": (ld / lr) if lr else None,
        "lease_blob_read_share_of_lease_get_bytes": (lb / lr) if lr else None,
        "decode_share_of_process": ((ld + rd) / proc) if proc else None,
        "pool_wall_ns": pw,
        "pool_wall_share_of_process": (pw / proc) if (pw and proc) else None,
        "serial_equivalent_lease_ns": lr + lv,
        "pool_speedup_vs_serial_equivalent": ((lr + lv) / pw) if pw else None,
        "pool_dispatches": int(st.get("ob4b_pool_dispatches", 0)) or None,
        "pool_items_total": int(st.get("ob4b_pool_items_total", 0)) or None,
        "items_by_slot": st.get("ob4b_items_by_slot"),
        "total_store_bytes_read": int(st.get("ob4_lease_store_bytes_read", 0))
        + int(st.get("ob4_resident_store_bytes_read", 0)),
        "lease_store_bytes_read": int(st.get("ob4_lease_store_bytes_read", 0)),
        "lease_bytes_materialized": int(st.get("lease_bytes_read", 0)),
    }
    return out


def main():
    runs = {}
    for label, d in [
        ("ob4b-unit-pool1", os.path.join(MINE, "unit-pool1")),
        ("ob4b-unit-pool8", os.path.join(MINE, "unit-pool8")),
        ("ob4b-k8-code-a", os.path.join(MINE, "ob4b-k8-code-a")),
        ("ob4b-k8-code-b", os.path.join(MINE, "ob4b-k8-code-b")),
        ("ob4-banked-res-code", os.path.join(OB4, "ob4-res-code")),
        ("ob4-banked-k8-code-a", os.path.join(OB4, "ob4-k8-code-a")),
        ("ob4-banked-k8-code-b", os.path.join(OB4, "ob4-k8-code-b")),
    ]:
        if os.path.isdir(d) and os.path.exists(os.path.join(d, "ob1-stats.txt")):
            runs[label] = summarize(d, label)
        else:
            runs[label] = {"label": label, "dir": d, "MISSING": True}

    verdicts = {}
    for label in ("ob4b-k8-code-a", "ob4b-k8-code-b"):
        r = runs.get(label)
        if not r or r.get("MISSING"):
            verdicts[label] = "MISSING"
            continue
        ident = r["identity_matches_reference"] and r["route_matches_reference"]
        ratio = r["p95_over_control"]
        verdicts[label] = {
            "identity_limb": "PASS" if ident else "FAIL",
            "p95_over_control": ratio,
            "bar": BAR_RATIO,
            "cost_limb": ("ACCEPT" if ratio < BAR_RATIO else "REJECT") if ratio else None,
        }

    idg, rtg = {}, {}
    for label, r in runs.items():
        if r.get("MISSING"):
            continue
        idg.setdefault(r["identity_sha256"], []).append(label)
        rtg.setdefault(r["route_log_sha256"], []).append(label)

    result = {
        "p95_method": "nearest-rank over the run's own chunk_ns series (rank = ceil(0.95*n)), milliseconds",
        "control_p95_ms": CONTROL_P95_MS,
        "control_run": "ob4-res-code (banked, OB-4's own K=0 fully resident AC-CODE run, reused by prereg)",
        "frozen_bar_ratio": BAR_RATIO,
        "identity_reference_sha256": IDENTITY_REF,
        "route_reference_sha256": ROUTE_REF,
        "runs": runs,
        "identity_groups_by_sha256": idg,
        "route_log_groups_by_sha256": rtg,
        "verdicts": verdicts,
    }
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1, sort_keys=True)
    print(json.dumps(result, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
