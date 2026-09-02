#!/usr/bin/env python3
"""OB4-REMAT-1 phase 3 (acceptance), independent re-verification leg.

Written fresh for this acceptance leg, NOT a copy of build_store.py or
verify_store.py -- reads the frozen container/index format directly from
OB4-REMAT-1-PREREG.md section 4 and independently re-implements the decode
+ digest check on a random sample, to catch anything a shared bug in the
builder-2 scripts might have hidden from a full-but-same-code run.

Method: seed a PRNG from a fixed, disclosed seed (so this run is itself
reproducible), draw 256 distinct row indices out of 4608 without
replacement, decode each via ctypes-linked libzstd (matching the live
engine's linked-library path, not a CLI subprocess), and sha256-compare
against the EXISTING manifest digest (identity authority, unchanged).

Usage: verify_sample256.py [container_path] [seed]
"""

import ctypes
import hashlib
import json
import os
import random
import struct
import sys
import time

ZSTD_SO = "/usr/lib/x86_64-linux-gnu/libzstd.so.1"
MANIFEST = "/mnt/f/f32/openbob-wt/ob4/research/ob1/EXPERT-MANIFEST-20B.sha256"
DEFAULT_STORE = "/root/ob4/EXPERT-STORE-20B.ob4"
RECEIPT = "/mnt/f/f32/openbob-wt/ob4/research/ob4/verify-sample256.json"
SAMPLE_N = 256
BLOCK = 17
IDX_REC = struct.Struct("<HHB QQ 32s QQ")

SUFFIX = [
    "ffn_gate_exps.weight",
    "ffn_up_exps.weight",
    "ffn_down_exps.weight",
    "ffn_gate_exps.bias",
    "ffn_up_exps.bias",
    "ffn_down_exps.bias",
]
SUFFIX_IDX = {s: i for i, s in enumerate(SUFFIX)}


def zdec(dctx, z, src, expect):
    out = ctypes.create_string_buffer(expect)
    n = z.ZSTD_decompressDCtx(dctx, out, expect, src, len(src))
    if z.ZSTD_isError(n):
        raise RuntimeError("ZSTD_decompressDCtx error code %d" % n)
    if n != expect:
        raise RuntimeError("decompressed %d bytes, expected %d" % (n, expect))
    return out.raw[:n]


def load_manifest_map():
    m = {}
    with open(MANIFEST) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            il, e, tname, off, nb, sha = line.strip().split(",")
            m[(int(il), int(e), SUFFIX_IDX[tname])] = (int(off), int(nb), sha)
    return m


def main():
    store_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_STORE
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20260901
    index_path = store_path + ".idx"
    t0 = time.time()

    z = ctypes.CDLL(ZSTD_SO)
    z.ZSTD_createDCtx.restype = ctypes.c_void_p
    z.ZSTD_decompressDCtx.restype = ctypes.c_size_t
    z.ZSTD_decompressDCtx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                      ctypes.c_void_p, ctypes.c_size_t]
    z.ZSTD_isError.restype = ctypes.c_uint
    z.ZSTD_isError.argtypes = [ctypes.c_size_t]
    dctx = z.ZSTD_createDCtx()

    store_size = os.path.getsize(store_path)
    with open(index_path, "rb") as f:
        ihdr = f.read(64)
        idx_body = f.read()
    if ihdr[:8] != b"OB4INDX1":
        raise RuntimeError("index magic is %r, not OB4INDX1" % ihdr[:8])
    nrows = struct.unpack_from("<Q", ihdr, 12)[0]
    hdr_store_size = struct.unpack_from("<Q", ihdr, 20)[0]
    hdr_store_sha = ihdr[28:60].hex()
    if hdr_store_size != store_size:
        raise RuntimeError("index says container is %d bytes, file is %d"
                           % (hdr_store_size, store_size))

    manifest = load_manifest_map()
    if nrows != len(manifest):
        raise RuntimeError("index has %d rows, manifest has %d" % (nrows, len(manifest)))

    rng = random.Random(seed)
    sample = sorted(rng.sample(range(nrows), SAMPLE_N))

    fd = os.open(store_path, os.O_RDONLY)
    results = []
    ok = 0
    fails = []
    for ci in sample:
        il, e, t, moff, mnb, msha, boff, blen = IDX_REC.unpack_from(idx_body, ci * IDX_REC.size)
        msha_hex = msha.hex()
        key = (il, e, t)
        m_off, m_nb, m_sha = manifest[key]
        if (moff, mnb, msha_hex) != (m_off, m_nb, m_sha):
            fails.append({"ci": ci, "why": "index disagrees with manifest"})
            continue
        blob = os.pread(fd, blen, boff)
        if len(blob) != blen:
            fails.append({"ci": ci, "why": "short blob read %d of %d" % (len(blob), blen)})
            continue
        scale_len = struct.unpack_from("<I", blob, 0)[0]
        mant_len = blen - 4 - scale_len
        if mant_len == 0:
            data = zdec(dctx, z, blob[4:4 + scale_len], mnb)
        else:
            if mnb % BLOCK != 0:
                fails.append({"ci": ci, "why": "nbytes %d not multiple of %d" % (mnb, BLOCK)})
                continue
            nblk = mnb // BLOCK
            s = zdec(dctx, z, blob[4:4 + scale_len], nblk)
            m = zdec(dctx, z, blob[4 + scale_len:], nblk * (BLOCK - 1))
            # interleave without numpy: scale byte then 16 mantissa bytes per block
            buf = bytearray(mnb)
            for k in range(nblk):
                buf[k * BLOCK] = s[k]
                buf[k * BLOCK + 1: k * BLOCK + BLOCK] = m[k * (BLOCK - 1):(k + 1) * (BLOCK - 1)]
            data = bytes(buf)
        got = hashlib.sha256(data).hexdigest()
        rec = {"ci": ci, "layer": il, "expert": e, "tensor": SUFFIX[t],
               "raw_bytes": mnb, "blob_bytes": blen, "split": mant_len != 0,
               "ok": got == msha_hex}
        results.append(rec)
        if rec["ok"]:
            ok += 1
        else:
            rec["got"] = got
            rec["want"] = msha_hex
            fails.append(rec)
    os.close(fd)

    dt = time.time() - t0
    verdict = "PASS" if (ok == SAMPLE_N and not fails) else "FAIL"
    receipt = {
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "leg": "builder3-acceptance-independent-sample",
        "container_path": store_path,
        "container_bytes": store_size,
        "container_sha256_from_index_header": hdr_store_sha,
        "index_rows_total": nrows,
        "sample_seed": seed,
        "sample_n": SAMPLE_N,
        "sample_row_indices_first10": sample[:10],
        "rows_ok": ok,
        "rows_failed": len(fails),
        "failures": fails,
        "verdict": verdict,
        "wall_seconds": dt,
    }
    with open(RECEIPT, "w") as f:
        json.dump(receipt, f, indent=1, sort_keys=True)
    print(json.dumps({k: v for k, v in receipt.items() if k != "failures"},
                     indent=1, sort_keys=True))
    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    main()
