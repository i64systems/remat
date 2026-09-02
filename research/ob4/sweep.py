#!/usr/bin/env python3
"""OB4-REMAT-1 Phase 1: codec sweep C0-C4 over the extracted eval slices.

All codecs are deterministic (zstd, order-0 entropy counting). Operates
only on files already extracted+digest-verified by extract.py under
/mnt/f/f32/stage/research/ob4/slices/{eval,train}.
"""
import hashlib
import json
import math
import multiprocessing
import os
import subprocess
import sys
import time

import numpy as np

OUT_DIR = "/mnt/f/f32/stage/research/ob4"
RESULTS_DIR = os.path.join(OUT_DIR, "results")
WORK_DIR = os.path.join(OUT_DIR, "work")
DICT_DIR = os.path.join(OUT_DIR, "dicts")
GGUF_PATH = "/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf"

BLOCK_SIZE = 17  # 1 byte E8M0 scale + 16 bytes packed 4-bit mantissa (32 values), ggml block_mxfp4
WEIGHT_SUFFIX = ".weight"
BIAS_SUFFIX = ".bias"
TENSOR_KINDS = [
    "ffn_gate_exps.weight",
    "ffn_up_exps.weight",
    "ffn_down_exps.weight",
    "ffn_gate_exps.bias",
    "ffn_up_exps.bias",
    "ffn_down_exps.bias",
]
NPROC = 6  # RUNLOCK cap for non-model compute


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def load_extract_manifest():
    with open(os.path.join(RESULTS_DIR, "extract-manifest.json")) as f:
        return json.load(f)


def order0_entropy_bits(symbols_u8, alphabet):
    counts = np.bincount(symbols_u8, minlength=alphabet).astype(np.float64)
    n = counts.sum()
    p = counts[counts > 0] / n
    h = -np.sum(p * np.log2(p))  # bits/symbol
    return float(h), int(n)


def layout_facts(eval_rows):
    facts = {}
    w = next(r for r in eval_rows if r["tensor"].endswith(WEIGHT_SUFFIX))
    assert w["nbytes"] % BLOCK_SIZE == 0, "weight slice not block-aligned to %d" % BLOCK_SIZE
    nblocks = w["nbytes"] // BLOCK_SIZE
    n_elems = nblocks * 32
    side = int(round(math.sqrt(n_elems)))
    facts["weight_example"] = w["tensor"]
    facts["weight_nbytes"] = w["nbytes"]
    facts["weight_block_size_bytes"] = BLOCK_SIZE
    facts["weight_nblocks"] = nblocks
    facts["weight_n_elements"] = n_elems
    facts["weight_square_side_if_2d"] = side
    facts["weight_side_check"] = side * side == n_elems

    b = next(r for r in eval_rows if r["tensor"].endswith(BIAS_SUFFIX))
    facts["bias_example"] = b["tensor"]
    facts["bias_nbytes"] = b["nbytes"]
    facts["bias_elems_if_f32"] = b["nbytes"] / 4.0
    facts["bias_elems_if_f16"] = b["nbytes"] / 2.0
    with open(b["file"], "rb") as f:
        raw = f.read()
    arr_f32 = np.frombuffer(raw, dtype="<f4")
    facts["bias_f32_min"] = float(arr_f32.min())
    facts["bias_f32_max"] = float(arr_f32.max())
    facts["bias_f32_mean"] = float(arr_f32.mean())
    facts["bias_f32_n"] = int(arr_f32.size)
    return facts


def split_streams(raw):
    arr = np.frombuffer(raw, dtype=np.uint8).reshape(-1, BLOCK_SIZE)
    scale = arr[:, 0].tobytes()
    mantissa = arr[:, 1:].tobytes()
    return scale, mantissa


def interleave_streams(scale, mantissa, nblocks):
    s = np.frombuffer(scale, dtype=np.uint8).reshape(nblocks, 1)
    m = np.frombuffer(mantissa, dtype=np.uint8).reshape(nblocks, BLOCK_SIZE - 1)
    out = np.concatenate([s, m], axis=1)
    return out.tobytes()


def zstd_compress_file(src_path, dst_path, dict_path=None, level=19):
    cmd = ["zstd", "-q", "-f", "-%d" % level, "-T1"]
    if dict_path:
        cmd += ["-D", dict_path]
    cmd += ["-o", dst_path, src_path]
    sh(cmd)
    return os.path.getsize(dst_path)


def zstd_decompress_to_bytes(src_path, dict_path=None):
    cmd = ["zstd", "-q", "-d", "-c", "-T1"]
    if dict_path:
        cmd += ["-D", dict_path]
    cmd += [src_path]
    p = subprocess.run(cmd, check=True, stdout=subprocess.PIPE)
    return p.stdout


def build_dicts(train_rows_by_kind):
    os.makedirs(DICT_DIR, exist_ok=True)
    dicts = {}
    for kind, rows in train_rows_by_kind.items():
        files = [r["file"] for r in rows]
        dict_path = os.path.join(DICT_DIR, kind.replace(".", "_") + ".dict")
        cmd = ["zstd", "--train-fastcover", "-q", "-f",
               "--maxdict=112640", "-o", dict_path] + files
        t0 = time.time()
        sh(cmd)
        dt = time.time() - t0
        train_bytes = sum(os.path.getsize(fp) for fp in files)
        dicts[kind] = {
            "path": dict_path,
            "size_bytes": os.path.getsize(dict_path),
            "n_train_files": len(files),
            "train_bytes": train_bytes,
            "train_seconds": round(dt, 3),
        }
        print("dict[%s] size=%d trained on %d files (%d bytes) in %.2fs" % (
            kind, dicts[kind]["size_bytes"], len(files), train_bytes, dt))
    return dicts


def process_eval_row(args):
    row, dict_path = args
    kind = row["tensor"]
    is_weight = kind.endswith(WEIGHT_SUFFIX)
    with open(row["file"], "rb") as f:
        raw = f.read()
    assert hashlib.sha256(raw).hexdigest() == row["sha256"]

    base = row["file"]
    c1_path = base + ".c1.zst"
    c1_size = zstd_compress_file(base, c1_path, dict_path=None)

    out = {
        "layer": row["layer"], "expert": row["expert"], "tensor": kind,
        "raw_bytes": row["nbytes"],
        "c0_bytes": row["nbytes"],
        "c1_bytes": c1_size,
        "file": base, "c1_file": c1_path,
    }

    if is_weight:
        scale, mantissa = split_streams(raw)
        nblocks = len(scale)
        scale_path = base + ".scale.bin"
        mant_path = base + ".mant.bin"
        with open(scale_path, "wb") as f:
            f.write(scale)
        with open(mant_path, "wb") as f:
            f.write(mantissa)
        scale_c = scale_path + ".zst"
        mant_c = mant_path + ".zst"
        scale_c_size = zstd_compress_file(scale_path, scale_c)
        mant_c_size = zstd_compress_file(mant_path, mant_c)
        out["c2_scale_bytes"] = scale_c_size
        out["c2_mant_bytes"] = mant_c_size
        out["c2_bytes"] = scale_c_size + mant_c_size
        out["scale_c_file"] = scale_c
        out["mant_c_file"] = mant_c
        out["scale_raw_file"] = scale_path
        out["mant_raw_file"] = mant_path

        # round-trip verify C2
        rt_scale = zstd_decompress_to_bytes(scale_c)
        rt_mant = zstd_decompress_to_bytes(mant_c)
        rebuilt = interleave_streams(rt_scale, rt_mant, nblocks)
        out["c2_roundtrip_ok"] = (hashlib.sha256(rebuilt).hexdigest() == row["sha256"])

        # C3 order-0 entropy
        h_scale, n_scale = order0_entropy_bits(np.frombuffer(scale, dtype=np.uint8), 256)
        mant_bytes = np.frombuffer(mantissa, dtype=np.uint8)
        lo = mant_bytes & 0x0F
        hi = mant_bytes >> 4
        nib = np.concatenate([lo, hi])
        h_mant, n_mant = order0_entropy_bits(nib, 16)
        floor_scale_bytes = math.ceil(h_scale * n_scale / 8.0)
        floor_mant_bytes = math.ceil(h_mant * n_mant / 8.0)
        out["c3_scale_entropy_bits_per_symbol"] = h_scale
        out["c3_mant_entropy_bits_per_nibble"] = h_mant
        out["c3_floor_bytes"] = floor_scale_bytes + floor_mant_bytes
    else:
        out["c2_bytes"] = c1_size  # no block structure to split; C2 == C1 for bias
        out["c2_roundtrip_ok"] = None
        h, n = order0_entropy_bits(np.frombuffer(raw, dtype=np.uint8), 256)
        out["c3_scale_entropy_bits_per_symbol"] = None
        out["c3_mant_entropy_bits_per_nibble"] = None
        out["c3_floor_bytes"] = math.ceil(h * n / 8.0)

    # C4 dictionary-assisted
    c4_path = base + ".c4.zst"
    c4_size = zstd_compress_file(base, c4_path, dict_path=dict_path)
    out["c4_bytes"] = c4_size
    out["c4_file"] = c4_path
    rt4 = zstd_decompress_to_bytes(c4_path, dict_path=dict_path)
    out["c4_roundtrip_ok"] = (hashlib.sha256(rt4).hexdigest() == row["sha256"])

    return out


def encode_phase(eval_rows, dicts):
    args = []
    for r in eval_rows:
        dpath = dicts[r["tensor"]]["path"]
        args.append((r, dpath))
    with multiprocessing.Pool(processes=NPROC) as pool:
        results = pool.map(process_eval_row, args, chunksize=4)
    return results


def decode_timing_with_offsets(eval_rows_by_key, results):
    os.nice(0)
    gguf_fd = os.open(GGUF_PATH, os.O_RDONLY)
    timing = []
    try:
        for r in results:
            key = (r["layer"], r["expert"], r["tensor"])
            row = eval_rows_by_key[key]

            t0 = time.perf_counter()
            raw = os.pread(gguf_fd, row["nbytes"], row["offset"])
            _ = hashlib.sha256(raw).hexdigest()
            t_baseline = time.perf_counter() - t0

            t0 = time.perf_counter()
            d1 = zstd_decompress_to_bytes(r["c1_file"])
            t_c1 = time.perf_counter() - t0
            assert hashlib.sha256(d1).hexdigest() == row["sha256"]

            t_c2 = None
            if "scale_c_file" in r:
                t0 = time.perf_counter()
                sc = zstd_decompress_to_bytes(r["scale_c_file"])
                mc = zstd_decompress_to_bytes(r["mant_c_file"])
                rebuilt = interleave_streams(sc, mc, len(sc))
                t_c2 = time.perf_counter() - t0
                assert hashlib.sha256(rebuilt).hexdigest() == row["sha256"]

            t0 = time.perf_counter()
            d4 = zstd_decompress_to_bytes(r["c4_file"], dict_path=DICTS_GLOBAL[row["tensor"]]["path"])
            t_c4 = time.perf_counter() - t0
            assert hashlib.sha256(d4).hexdigest() == row["sha256"]

            timing.append({
                "layer": row["layer"], "expert": row["expert"], "tensor": row["tensor"],
                "baseline_pread_sha256_sec": t_baseline,
                "c1_decode_sec": t_c1,
                "c2_decode_sec": t_c2,
                "c4_decode_sec": t_c4,
            })
    finally:
        os.close(gguf_fd)
    return timing


DICTS_GLOBAL = {}


def summarize(results, timing):
    by_kind = {}
    for r in results:
        by_kind.setdefault(r["tensor"], []).append(r)

    timing_by_kind = {}
    for t in timing:
        timing_by_kind.setdefault(t["tensor"], []).append(t)

    def pool_ratio(rows, key):
        raw = sum(x["raw_bytes"] for x in rows)
        comp = sum(x[key] for x in rows)
        return comp / raw, raw, comp

    lines = []
    grand = {"raw": 0, "c0": 0, "c1": 0, "c2": 0, "c4": 0, "c3floor": 0}
    for kind in TENSOR_KINDS:
        rows = by_kind.get(kind, [])
        if not rows:
            continue
        r1, raw, c1 = pool_ratio(rows, "c1_bytes")
        r2, _, c2 = pool_ratio(rows, "c2_bytes")
        r4, _, c4 = pool_ratio(rows, "c4_bytes")
        c3floor = sum(x["c3_floor_bytes"] for x in rows)
        r3 = c3floor / raw
        grand["raw"] += raw
        grand["c0"] += raw
        grand["c1"] += c1
        grand["c2"] += c2
        grand["c4"] += c4
        grand["c3floor"] += c3floor

        trows = timing_by_kind.get(kind, [])
        avg_baseline = sum(x["baseline_pread_sha256_sec"] for x in trows) / len(trows) if trows else None
        avg_c1 = sum(x["c1_decode_sec"] for x in trows) / len(trows) if trows else None
        c2t = [x["c2_decode_sec"] for x in trows if x["c2_decode_sec"] is not None]
        avg_c2 = sum(c2t) / len(c2t) if c2t else None
        avg_c4 = sum(x["c4_decode_sec"] for x in trows) / len(trows) if trows else None

        rt_ok_c2 = all(x.get("c2_roundtrip_ok") in (True, None) for x in rows)
        rt_ok_c4 = all(x.get("c4_roundtrip_ok") is True for x in rows)

        lines.append({
            "tensor_kind": kind, "n_slices": len(rows), "raw_bytes_total": raw,
            "ratio_C0": 1.0,
            "ratio_C1_zstd19": r1,
            "ratio_C2_split_stream": r2,
            "ratio_C3_entropy_floor": r3,
            "ratio_C4_dict": r4,
            "decode_sec_avg_baseline_pread_sha256": avg_baseline,
            "decode_sec_avg_C1": avg_c1,
            "decode_sec_avg_C2": avg_c2,
            "decode_sec_avg_C4": avg_c4,
            "c1_over_baseline_x": (avg_c1 / avg_baseline) if (avg_c1 and avg_baseline) else None,
            "c4_over_baseline_x": (avg_c4 / avg_baseline) if (avg_c4 and avg_baseline) else None,
            "c2_roundtrip_all_ok": rt_ok_c2,
            "c4_roundtrip_all_ok": rt_ok_c4,
        })

    pooled = {
        "raw_bytes_total": grand["raw"],
        "ratio_C0": 1.0,
        "ratio_C1_zstd19": grand["c1"] / grand["raw"],
        "ratio_C2_split_stream": grand["c2"] / grand["raw"],
        "ratio_C3_entropy_floor": grand["c3floor"] / grand["raw"],
        "ratio_C4_dict_no_amortization": grand["c4"] / grand["raw"],
    }
    return lines, pooled


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    em = load_extract_manifest()
    eval_rows = [r for r in em["rows"] if r["set"] == "eval"]
    train_rows = [r for r in em["rows"] if r["set"] == "train"]
    eval_by_key = {(r["layer"], r["expert"], r["tensor"]): r for r in eval_rows}

    os.makedirs(WORK_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    facts = layout_facts(eval_rows)
    print("LAYOUT FACTS:")
    print(json.dumps(facts, indent=2))
    with open(os.path.join(RESULTS_DIR, "layout-facts.json"), "w") as f:
        json.dump(facts, f, indent=2)

    train_by_kind = {}
    for r in train_rows:
        train_by_kind.setdefault(r["tensor"], []).append(r)

    print("BUILDING DICTIONARIES...")
    dicts = build_dicts(train_by_kind)
    global DICTS_GLOBAL
    DICTS_GLOBAL = dicts
    with open(os.path.join(RESULTS_DIR, "dicts.json"), "w") as f:
        json.dump(dicts, f, indent=2)

    print("ENCODE PHASE (pool=%d)..." % NPROC)
    t0 = time.time()
    results = encode_phase(eval_rows, dicts)
    print("encode phase elapsed sec:", round(time.time() - t0, 2))
    with open(os.path.join(RESULTS_DIR, "encode-results.json"), "w") as f:
        json.dump(results, f)

    print("DECODE TIMING PHASE (single-thread, sequential)...")
    t0 = time.time()
    timing = decode_timing_with_offsets(eval_by_key, results)
    print("decode timing phase elapsed sec:", round(time.time() - t0, 2))
    with open(os.path.join(RESULTS_DIR, "decode-timing.json"), "w") as f:
        json.dump(timing, f)

    lines, pooled = summarize(results, timing)
    with open(os.path.join(RESULTS_DIR, "sweep-summary.json"), "w") as f:
        json.dump({"by_tensor_kind": lines, "pooled": pooled}, f, indent=2)

    print("\n=== PER TENSOR KIND ===")
    for l in lines:
        print(json.dumps(l, indent=2))
    print("\n=== POOLED ===")
    print(json.dumps(pooled, indent=2))


if __name__ == "__main__":
    main()
