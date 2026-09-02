#!/usr/bin/env python3
"""OB4-REMAT-1 phase 2, step 4 analysis: turn the run batch's stats files into
the literal numbers the receipt reports.

p95 is computed exactly the way OB-1 computed it (research/ob1/RUNLOG-1.txt
deviation D2): nearest-rank over the run's own chunk_ns series, which holds the
wall time between successive layer-0 routing callbacks, i.e. one sample per
perplexity chunk boundary (31 samples for a 32-chunk run). Reported in
milliseconds, as OB-1 reported them.
"""

import hashlib
import json
import math
import os
import sys

MINE = "/root/ob4/runs"
BANKED = "/mnt/f/f32/stage/research/ob1/runs"
OUT = "/mnt/f/f32/openbob-wt/ob4/research/ob4/run-analysis.json"

# OB-1's own figures for the same run class, quoted from its banked stats file
OB1_LEASE_K8_CODE = "lease-k8-code"
OB1_RES_CODE = "res-code-a"


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
        return None
    rank = int(math.ceil(0.95 * len(v)))   # nearest-rank, 1-based
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


def summarize(run_dir, label):
    st = read_stats(os.path.join(run_dir, "ob1-stats.txt"))
    p, n, rank = p95_ms(st.get("chunk_ns", ""))
    out = {
        "label": label,
        "dir": run_dir,
        "mode": st.get("ob1_mode"),
        "K": st.get("ob1_k"),
        "sha_impl": st.get("ob1_sha_impl"),
        "ob4_store": st.get("ob4_store", "off"),
        "chunk_count": n,
        "p95_rank": rank,
        "p95_ms": p,
        "chunk_ns_sum_ms": sum(ints(st.get("chunk_ns", ""))) / 1e6,
        "identity_sha256": sha(os.path.join(run_dir, "identity.txt")),
        "route_log_sha256": sha(os.path.join(run_dir, "route.log")),
        "peak_rss_bytes": rss_bytes(os.path.join(run_dir, "stderr.txt")),
        "stats": st,
    }
    return out


def main():
    runs = {}
    for label, d in [
        ("ob4-res-code", os.path.join(MINE, "ob4-res-code")),
        ("ob4-k8-code-a", os.path.join(MINE, "ob4-k8-code-a")),
        ("ob4-k8-code-b", os.path.join(MINE, "ob4-k8-code-b")),
        ("ob1-banked-res-code-a", os.path.join(BANKED, OB1_RES_CODE)),
        ("ob1-banked-lease-k8-code", os.path.join(BANKED, OB1_LEASE_K8_CODE)),
    ]:
        if os.path.isdir(d):
            runs[label] = summarize(d, label)

    base = runs.get("ob4-res-code")
    banked_base = runs.get("ob1-banked-res-code-a")
    ob1_lease = runs.get("ob1-banked-lease-k8-code")

    rows = []
    for label in ("ob4-k8-code-a", "ob4-k8-code-b"):
        r = runs.get(label)
        if not r:
            continue
        st = r["stats"]
        proc_ns = int(st.get("process_ns_since_ob1_init", 0))
        lease_dec = int(st.get("ob4_lease_decode_ns", 0))
        res_dec = int(st.get("ob4_resident_decode_ns", 0))
        lease_blob = int(st.get("ob4_lease_blob_read_ns", 0))
        res_blob = int(st.get("ob4_resident_blob_read_ns", 0))
        lease_read_ns = int(st.get("lease_read_ns", 0))
        lease_ver_ns = int(st.get("lease_verify_ns", 0))
        lease_store_b = int(st.get("ob4_lease_store_bytes_read", 0))
        res_store_b = int(st.get("ob4_resident_store_bytes_read", 0))
        lease_raw_b = int(st.get("lease_bytes_read", 0))
        res_raw_b = int(st.get("resident_bytes_loaded", 0))
        row = {
            "run": label,
            "identity_sha256": r["identity_sha256"],
            "route_log_sha256": r["route_log_sha256"],
            "p95_ms": r["p95_ms"],
            "p95_over_own_resident_baseline": (r["p95_ms"] / base["p95_ms"]) if base else None,
            "p95_over_banked_resident_baseline": (r["p95_ms"] / banked_base["p95_ms"]) if banked_base else None,
            "p95_of_ob1_banked_lease_k8_code_ms": ob1_lease["p95_ms"] if ob1_lease else None,
            "peak_rss_bytes": r["peak_rss_bytes"],
            "lease_events": int(st.get("lease_events", 0)),
            "decodes_total": int(st.get("ob4_decodes_total", 0)),
            "decodes_split_stream": int(st.get("ob4_decodes_split_stream", 0)),
            "decoded_bytes_total": int(st.get("ob4_decoded_bytes_total", 0)),
            # bytes actually moved off disk, store vs OB-1's raw GGUF reads
            "lease_store_bytes_read": lease_store_b,
            "lease_expert_bytes_materialized": lease_raw_b,
            "lease_store_over_raw_ratio": (lease_store_b / lease_raw_b) if lease_raw_b else None,
            "ob1_banked_lease_bytes_read": int(ob1_lease["stats"].get("lease_bytes_read", 0)) if ob1_lease else None,
            "resident_store_bytes_read": res_store_b,
            "resident_expert_bytes_materialized": res_raw_b,
            "total_store_bytes_read": lease_store_b + res_store_b,
            "total_expert_bytes_materialized": lease_raw_b + res_raw_b,
            # where the time went
            "process_ns": proc_ns,
            "lease_decode_ns": lease_dec,
            "resident_decode_ns": res_dec,
            "lease_blob_read_ns": lease_blob,
            "resident_blob_read_ns": res_blob,
            "lease_verify_ns": lease_ver_ns,
            "lease_get_bytes_ns": lease_read_ns,
            "decode_share_of_process": (lease_dec + res_dec) / proc_ns if proc_ns else None,
            "lease_decode_share_of_process": lease_dec / proc_ns if proc_ns else None,
            "lease_decode_share_of_lease_get_bytes": (lease_dec / lease_read_ns) if lease_read_ns else None,
            "lease_blob_read_share_of_lease_get_bytes": (lease_blob / lease_read_ns) if lease_read_ns else None,
        }
        rows.append(row)

    identity_group = {}
    for label, r in runs.items():
        identity_group.setdefault(r["identity_sha256"], []).append(label)
    route_group = {}
    for label, r in runs.items():
        route_group.setdefault(r["route_log_sha256"], []).append(label)

    result = {
        "p95_method": "nearest-rank over the run's own chunk_ns series (rank = ceil(0.95*n)), milliseconds",
        "runs": {k: {kk: vv for kk, vv in v.items() if kk != "stats"} for k, v in runs.items()},
        "cost_limb_denominator_ms": base["p95_ms"] if base else None,
        "cost_limb_denominator_run": "ob4-res-code (this binary's own fully resident AC-CODE run)",
        "banked_ob1_resident_p95_ms": banked_base["p95_ms"] if banked_base else None,
        "identity_groups_by_sha256": identity_group,
        "route_log_groups_by_sha256": route_group,
        "ob4_rows": rows,
    }
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1, sort_keys=True)
    print(json.dumps(result, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
