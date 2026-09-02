#!/usr/bin/env python3
"""OB4-REMAT-1 phase 2, step 2: full decode verification of the container.

Decodes ALL rows of EXPERT-STORE-20B.ob4 through the container/index format
frozen in research/OB4-REMAT-1-PREREG.md section 4 and checks every decoded
slice's sha256 against the row's manifest digest -- the verification law of
section 5. This reader is deliberately written the same way the C++ engine
reads (header parse, index record parse, one blob pread, one or two zstd frames,
interleave, sha256), so it doubles as an executable spec for the engine.

Stop-ship bar (prereg section 7, DIGEST limb): 4608/4608 must match.

Usage: verify_store.py [container_path]
"""

import ctypes
import hashlib
import json
import multiprocessing as mp
import os
import struct
import sys
import time

import numpy as np

ZSTD_SO = "/usr/lib/x86_64-linux-gnu/libzstd.so.1"
MANIFEST = "/mnt/f/f32/openbob-wt/ob4/research/ob1/EXPERT-MANIFEST-20B.sha256"
DEFAULT_STORE = "/root/ob4/EXPERT-STORE-20B.ob4"
RECEIPT = "/mnt/f/f32/openbob-wt/ob4/research/ob4/store-verify.json"

BLOCK = 17
NWORKERS = 6
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

_W = {}
_STORE_PATH = DEFAULT_STORE


def worker_init(store_path):
    z = ctypes.CDLL(ZSTD_SO)
    z.ZSTD_createDCtx.restype = ctypes.c_void_p
    z.ZSTD_freeDCtx.restype = ctypes.c_size_t
    z.ZSTD_freeDCtx.argtypes = [ctypes.c_void_p]
    z.ZSTD_decompressDCtx.restype = ctypes.c_size_t
    z.ZSTD_decompressDCtx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                      ctypes.c_void_p, ctypes.c_size_t]
    z.ZSTD_isError.restype = ctypes.c_uint
    z.ZSTD_isError.argtypes = [ctypes.c_size_t]
    _W["z"] = z
    _W["dctx"] = z.ZSTD_createDCtx()
    _W["fd"] = os.open(store_path, os.O_RDONLY)


def zdec(src, expect):
    z = _W["z"]
    out = ctypes.create_string_buffer(expect)
    n = z.ZSTD_decompressDCtx(_W["dctx"], out, expect, src, len(src))
    if z.ZSTD_isError(n):
        raise RuntimeError("ZSTD_decompressDCtx error code %d" % n)
    if n != expect:
        raise RuntimeError("decompressed %d bytes, expected %d" % (n, expect))
    return out.raw[:n]


def verify_row(rec):
    """(ci, il, e, t, moff, mnb, msha_hex, blob_off, blob_len) -> result dict"""
    ci, il, e, t, moff, mnb, msha, boff, blen = rec
    blob = os.pread(_W["fd"], blen, boff)
    if len(blob) != blen:
        return {"ci": ci, "ok": False, "why": "short blob read %d of %d" % (len(blob), blen)}
    scale_len = struct.unpack_from("<I", blob, 0)[0]
    mant_len = blen - 4 - scale_len
    if scale_len < 0 or mant_len < 0:
        return {"ci": ci, "ok": False, "why": "bad frame lengths %d/%d" % (scale_len, mant_len)}

    if mant_len == 0:
        data = zdec(blob[4:4 + scale_len], mnb)
    else:
        if mnb % BLOCK != 0:
            return {"ci": ci, "ok": False, "why": "split row nbytes %d not multiple of %d" % (mnb, BLOCK)}
        nblk = mnb // BLOCK
        s = zdec(blob[4:4 + scale_len], nblk)
        m = zdec(blob[4 + scale_len:], nblk * (BLOCK - 1))
        data = np.concatenate(
            [np.frombuffer(s, dtype=np.uint8).reshape(nblk, 1),
             np.frombuffer(m, dtype=np.uint8).reshape(nblk, BLOCK - 1)], axis=1).tobytes()

    got = hashlib.sha256(data).hexdigest()
    return {"ci": ci, "ok": got == msha, "got": got, "want": msha,
            "layer": il, "expert": e, "tensor": SUFFIX[t],
            "raw_bytes": mnb, "blob_bytes": blen, "split": mant_len != 0}


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
    index_path = store_path + ".idx"
    t0 = time.time()

    store_size = os.path.getsize(store_path)
    with open(index_path, "rb") as f:
        ihdr = f.read(64)
        idx_body = f.read()
    if ihdr[:8] != b"OB4INDX1":
        raise RuntimeError("index magic is %r, not OB4INDX1" % ihdr[:8])
    iver = struct.unpack_from("<I", ihdr, 8)[0]
    nrows = struct.unpack_from("<Q", ihdr, 12)[0]
    hdr_store_size = struct.unpack_from("<Q", ihdr, 20)[0]
    hdr_store_sha = ihdr[28:60].hex()
    print("index: version=%d rows=%d container_size=%d container_sha256=%s"
          % (iver, nrows, hdr_store_size, hdr_store_sha), flush=True)
    if hdr_store_size != store_size:
        raise RuntimeError("index says container is %d bytes, file is %d"
                           % (hdr_store_size, store_size))
    if len(idx_body) != nrows * IDX_REC.size:
        raise RuntimeError("index body %d bytes != rows*%d = %d"
                           % (len(idx_body), IDX_REC.size, nrows * IDX_REC.size))

    with open(store_path, "rb") as f:
        shdr = f.read(64)
    if shdr[:8] != b"OB4STOR1":
        raise RuntimeError("container magic is %r, not OB4STOR1" % shdr[:8])
    if struct.unpack_from("<Q", shdr, 12)[0] != nrows:
        raise RuntimeError("container header row count disagrees with index")

    manifest = load_manifest_map()
    print("manifest rows loaded: %d" % len(manifest), flush=True)

    recs = []
    covered = 0
    prev_end = 64
    for ci in range(nrows):
        il, e, t, moff, mnb, msha, boff, blen = IDX_REC.unpack_from(idx_body, ci * IDX_REC.size)
        key = (il, e, t)
        if key not in manifest:
            raise RuntimeError("index row %d (l=%d e=%d t=%d) has no manifest row" % (ci, il, e, t))
        m_off, m_nb, m_sha = manifest[key]
        # the manifest is the identity authority: the index must agree with it
        if (moff, mnb, msha.hex()) != (m_off, m_nb, m_sha):
            raise RuntimeError("index row %d disagrees with manifest: %s vs %s"
                               % (ci, (moff, mnb, msha.hex()), (m_off, m_nb, m_sha)))
        if ci != (il * 32 + e) * 6 + t:
            raise RuntimeError("index row %d is out of canonical order" % ci)
        if boff != prev_end:
            raise RuntimeError("index row %d blob offset %d leaves a gap after %d"
                               % (ci, boff, prev_end))
        prev_end = boff + blen
        covered += blen
        recs.append((ci, il, e, t, moff, mnb, msha.hex(), boff, blen))
    if prev_end != store_size:
        raise RuntimeError("blobs cover %d bytes, container is %d" % (prev_end, store_size))
    print("index structural checks PASS: canonical order, no gaps, "
          "covers %d of %d container bytes (64-byte header is the remainder)"
          % (covered, store_size), flush=True)

    ok = 0
    fails = []
    raw_total = blob_total = 0
    with mp.Pool(NWORKERS, initializer=worker_init, initargs=(store_path,)) as pool:
        for i, r in enumerate(pool.imap_unordered(verify_row, recs, chunksize=8), 1):
            if r["ok"]:
                ok += 1
                raw_total += r["raw_bytes"]
                blob_total += r["blob_bytes"]
            else:
                fails.append(r)
            if i % 1000 == 0:
                print("  verified %d/%d  (%d ok, %d fail)  %.1f s"
                      % (i, len(recs), ok, len(fails), time.time() - t0), flush=True)

    dt = time.time() - t0
    verdict = "PASS" if (ok == nrows and not fails) else "FAIL"
    print("DIGEST LIMB %s: %d/%d rows decoded and sha256-matched the manifest"
          % (verdict, ok, nrows), flush=True)
    for f in fails[:20]:
        print("  FAIL row %d l=%s e=%s %s: %s"
              % (f["ci"], f.get("layer"), f.get("expert"), f.get("tensor"),
                 f.get("why", "digest %s != %s" % (f.get("got"), f.get("want")))), flush=True)

    receipt = {
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "container_path": store_path,
        "container_bytes": store_size,
        "container_sha256_from_index_header": hdr_store_sha,
        "index_path": index_path,
        "index_bytes": os.path.getsize(index_path),
        "rows": nrows,
        "rows_ok": ok,
        "rows_failed": len(fails),
        "failures": fails[:100],
        "verdict": verdict,
        "raw_bytes_verified": raw_total,
        "blob_bytes_read": blob_total,
        "wall_seconds": dt,
        "workers": NWORKERS,
        "zstd_library": ZSTD_SO,
    }
    with open(RECEIPT, "w") as f:
        json.dump(receipt, f, indent=1, sort_keys=True)
    print(json.dumps({k: v for k, v in receipt.items() if k != "failures"},
                     indent=1, sort_keys=True), flush=True)
    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    main()
