"""Supplementary: in-process (library, no subprocess/pipe) decode cost using
python-zstandard bindings against libzstd, to separate true decompression
work from CLI subprocess+pipe overhead measured in sweep.py's C1/C2/C4
decode timings. Single-threaded, sequential, on the same eval C1 artifacts.
"""
import hashlib
import json
import os
import time

import zstandard as zstd

RESULTS_DIR = "/mnt/f/f32/stage/research/ob4/results"
GGUF_PATH = "/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf"

with open(os.path.join(RESULTS_DIR, "encode-results.json")) as f:
    results = json.load(f)
with open(os.path.join(RESULTS_DIR, "extract-manifest.json")) as f:
    em = json.load(f)
eval_by_key = {(r["layer"], r["expert"], r["tensor"]): r for r in em["rows"] if r["set"] == "eval"}

dctx = zstd.ZstdDecompressor()
gguf_fd = os.open(GGUF_PATH, os.O_RDONLY)

by_kind = {}
for r in results:
    by_kind.setdefault(r["tensor"], []).append(r)

out = {}
try:
    for kind, rows in by_kind.items():
        baseline_times = []
        lib_c1_times = []
        for r in rows:
            key = (r["layer"], r["expert"], r["tensor"])
            row = eval_by_key[key]

            t0 = time.perf_counter()
            raw = os.pread(gguf_fd, row["nbytes"], row["offset"])
            _ = hashlib.sha256(raw).hexdigest()
            baseline_times.append(time.perf_counter() - t0)

            with open(r["c1_file"], "rb") as f:
                comp = f.read()
            t0 = time.perf_counter()
            dec = dctx.decompress(comp, max_output_size=row["nbytes"])
            lib_c1_times.append(time.perf_counter() - t0)
            assert hashlib.sha256(dec).hexdigest() == row["sha256"]

        avg_base = sum(baseline_times) / len(baseline_times)
        avg_lib = sum(lib_c1_times) / len(lib_c1_times)
        out[kind] = {
            "n": len(rows),
            "avg_baseline_pread_sha256_sec": avg_base,
            "avg_lib_zstd_decompress_sec": avg_lib,
            "lib_decode_over_baseline_x": avg_lib / avg_base,
        }
        print(kind, out[kind])
finally:
    os.close(gguf_fd)

with open(os.path.join(RESULTS_DIR, "lib-decode-bench.json"), "w") as f:
    json.dump(out, f, indent=2)
