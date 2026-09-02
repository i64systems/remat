import hashlib
import json
import os
import time

import numpy as np
import zstandard as zstd

RESULTS_DIR = "/mnt/f/f32/stage/research/ob4/results"
BLOCK_SIZE = 17

with open(os.path.join(RESULTS_DIR, "encode-results.json")) as f:
    results = json.load(f)
with open(os.path.join(RESULTS_DIR, "extract-manifest.json")) as f:
    em = json.load(f)
eval_by_key = {(r["layer"], r["expert"], r["tensor"]): r for r in em["rows"] if r["set"] == "eval"}

dctx = zstd.ZstdDecompressor()

by_kind = {}
for r in results:
    if "scale_c_file" in r:
        by_kind.setdefault(r["tensor"], []).append(r)

out = {}
for kind, rows in by_kind.items():
    times = []
    for r in rows:
        key = (r["layer"], r["expert"], r["tensor"])
        row = eval_by_key[key]
        with open(r["scale_c_file"], "rb") as f:
            sc = f.read()
        with open(r["mant_c_file"], "rb") as f:
            mc = f.read()
        nblocks = row["nbytes"] // BLOCK_SIZE
        scale_raw_bytes = nblocks
        mant_raw_bytes = nblocks * (BLOCK_SIZE - 1)

        t0 = time.perf_counter()
        s = dctx.decompress(sc, max_output_size=scale_raw_bytes)
        m = dctx.decompress(mc, max_output_size=mant_raw_bytes)
        sarr = np.frombuffer(s, dtype=np.uint8).reshape(nblocks, 1)
        marr = np.frombuffer(m, dtype=np.uint8).reshape(nblocks, BLOCK_SIZE - 1)
        rebuilt = np.concatenate([sarr, marr], axis=1).tobytes()
        times.append(time.perf_counter() - t0)
        assert hashlib.sha256(rebuilt).hexdigest() == row["sha256"]
    out[kind] = {"n": len(rows), "avg_lib_c2_decode_sec": sum(times) / len(times)}
    print(kind, out[kind])

with open(os.path.join(RESULTS_DIR, "lib-decode-c2.json"), "w") as f:
    json.dump(out, f, indent=2)
