#!/usr/bin/env python3
"""OB4-REMAT-1 phase 2, step 1: build the EXPERT-STORE-20B container.

Encodes all 4608 rows of research/ob1/EXPERT-MANIFEST-20B.sha256 with the codec
frozen in research/OB4-REMAT-1-PREREG.md section 3 (C2, split-stream zstd -19)
into the container format frozen in section 4.

Every row is pread from the GGUF by its manifest byte range and sha256-verified
against the manifest BEFORE it is encoded, so a bad read can never be baked into
the store. The manifest remains the identity authority: the container carries no
independent identity claim.

CONTAINER (EXPERT-STORE-20B.ob4)
  bytes 0..7    magic  "OB4STOR1"
  bytes 8..11   uint32 le  format version (1)
  bytes 12..19  uint64 le  row count
  bytes 20..27  uint64 le  offset of the first blob (64)
  bytes 28..63  zero padding
  bytes 64..    blobs, concatenated, in canonical row order

BLOB
  bytes 0..3    uint32 le  scale_frame_len
  bytes 4..     scale zstd frame (scale_frame_len bytes)
  then          mantissa zstd frame (blob_len - 4 - scale_frame_len bytes)
  For a bias row there is no block structure to split: the single zstd frame of
  the whole slice is stored as the "scale" frame, scale_frame_len is the entire
  payload length (blob_len - 4), and the mantissa frame is empty. The reader
  therefore has one code path with one branch on mantissa_len == 0.

INDEX (EXPERT-STORE-20B.ob4.idx)
  bytes 0..7    magic  "OB4INDX1"
  bytes 8..11   uint32 le  format version (1)
  bytes 12..19  uint64 le  row count
  bytes 20..27  uint64 le  container file size in bytes
  bytes 28..59  container sha256 (32 raw bytes)
  bytes 60..63  zero padding
  bytes 64..    row_count fixed records of 69 bytes, canonical order:
     uint16 le layer
     uint16 le expert
     uint8     tensor kind index (0..5, the OB1_SUFFIX order below)
     uint64 le manifest offset
     uint64 le manifest nbytes
     32 bytes  manifest sha256
     uint64 le blob offset (absolute, in the container file)
     uint64 le blob length

CANONICAL ROW ORDER is ((layer*E + expert)*6 + tensor_kind_index), identical to
idx_m() in the fork's src/ob1-lease.cpp, so the engine indexes the store directly
with the index it already computes.

Compression uses libzstd through ctypes at /usr/lib/x86_64-linux-gnu/libzstd.so.1
-- the SAME shared object the patched engine links and decodes with, so encode
and decode are the same library build (1.5.5) end to end.
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
GGUF = "/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf"
GGUF_SHA = "27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901"
MANIFEST = "/mnt/f/f32/openbob-wt/ob4/research/ob1/EXPERT-MANIFEST-20B.sha256"
OUT_DIR = "/root/ob4"
RECEIPT = "/mnt/f/f32/openbob-wt/ob4/research/ob4/store-build.json"

BLOCK = 17          # ggml block_mxfp4: 1 scale byte + 16 mantissa bytes
LEVEL = 19
NWORKERS = 6        # worker cap for non-model analysis work
TOTAL_EXPERT_BYTES = 10178887680

SUFFIX = [
    "ffn_gate_exps.weight",
    "ffn_up_exps.weight",
    "ffn_down_exps.weight",
    "ffn_gate_exps.bias",
    "ffn_up_exps.bias",
    "ffn_down_exps.bias",
]
SUFFIX_IDX = {s: i for i, s in enumerate(SUFFIX)}

IDX_REC = struct.Struct("<HHB QQ 32s QQ")
assert IDX_REC.size == 69, IDX_REC.size


# --------------------------------------------------------------------------
# libzstd through ctypes
# --------------------------------------------------------------------------

def open_zstd():
    z = ctypes.CDLL(ZSTD_SO)
    z.ZSTD_versionString.restype = ctypes.c_char_p
    z.ZSTD_compressBound.restype = ctypes.c_size_t
    z.ZSTD_compressBound.argtypes = [ctypes.c_size_t]
    z.ZSTD_compress.restype = ctypes.c_size_t
    z.ZSTD_compress.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    z.ZSTD_isError.restype = ctypes.c_uint
    z.ZSTD_isError.argtypes = [ctypes.c_size_t]
    return z


_W = {}


def worker_init():
    _W["z"] = open_zstd()
    _W["fd"] = os.open(GGUF, os.O_RDONLY)


def zcomp(buf):
    z = _W["z"]
    bound = z.ZSTD_compressBound(len(buf))
    out = ctypes.create_string_buffer(bound)
    n = z.ZSTD_compress(out, bound, buf, len(buf), LEVEL)
    if z.ZSTD_isError(n):
        raise RuntimeError("ZSTD_compress error code %d" % n)
    return out.raw[:n]


def encode_row(row):
    """(canonical_index, layer, expert, kind_index, offset, nbytes, sha_hex)
    -> (canonical_index, blob_bytes, scale_frame_len, split_used)"""
    ci, il, e, t, off, nb, shahex = row
    raw = os.pread(_W["fd"], nb, off)
    if len(raw) != nb:
        raise RuntimeError("short pread row %d: %d of %d" % (ci, len(raw), nb))
    got = hashlib.sha256(raw).hexdigest()
    if got != shahex:
        raise RuntimeError("PREREAD DIGEST MISMATCH row %d l=%d e=%d %s: got %s want %s"
                           % (ci, il, e, SUFFIX[t], got, shahex))

    split = SUFFIX[t].endswith(".weight")
    if split:
        if nb % BLOCK != 0:
            raise RuntimeError("row %d nbytes %d not a multiple of block size %d"
                               % (ci, nb, BLOCK))
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(-1, BLOCK)
        cs = zcomp(arr[:, 0].tobytes())
        cm = zcomp(arr[:, 1:].tobytes())
        blob = struct.pack("<I", len(cs)) + cs + cm
        return (ci, blob, len(cs), True)

    cs = zcomp(raw)
    blob = struct.pack("<I", len(cs)) + cs
    return (ci, blob, len(cs), False)


# --------------------------------------------------------------------------

def load_manifest():
    rows = []
    maxl = maxe = -1
    with open(MANIFEST) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split(",")
            if len(parts) != 6:
                raise RuntimeError("manifest line not parseable: %r" % line)
            il, e, tname, off, nb, sha = parts
            il, e, off, nb = int(il), int(e), int(off), int(nb)
            if tname not in SUFFIX_IDX:
                raise RuntimeError("unknown tensor suffix %r" % tname)
            if len(sha) != 64:
                raise RuntimeError("sha field not 64 hex chars: %r" % sha)
            rows.append((il, e, SUFFIX_IDX[tname], off, nb, sha))
            maxl, maxe = max(maxl, il), max(maxe, e)
    L, E = maxl + 1, maxe + 1
    if len(rows) != L * E * 6:
        raise RuntimeError("row count %d != L*E*6 = %d" % (len(rows), L * E * 6))
    ordered = [None] * len(rows)
    for (il, e, t, off, nb, sha) in rows:
        ci = (il * E + e) * 6 + t
        if ordered[ci] is not None:
            raise RuntimeError("duplicate manifest row at canonical index %d" % ci)
        ordered[ci] = (ci, il, e, t, off, nb, sha)
    if any(r is None for r in ordered):
        raise RuntimeError("manifest has a hole in canonical order")
    return L, E, ordered


def sha256_file(path, bufsize=8 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(bufsize)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    t_start = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)
    store_path = os.path.join(OUT_DIR, "EXPERT-STORE-20B.ob4")
    index_path = store_path + ".idx"

    z0 = open_zstd()
    zver = z0.ZSTD_versionString().decode()
    print("libzstd %s (%s)" % (zver, ZSTD_SO), flush=True)

    L, E, rows = load_manifest()
    print("manifest: L=%d E=%d rows=%d" % (L, E, len(rows)), flush=True)
    raw_total = sum(r[5] for r in rows)
    print("manifest raw byte total: %d (TOTAL_EXPERT_BYTES %d, match=%s)"
          % (raw_total, TOTAL_EXPERT_BYTES, raw_total == TOTAL_EXPERT_BYTES), flush=True)

    header = (b"OB4STOR1" + struct.pack("<I", 1) + struct.pack("<Q", len(rows))
              + struct.pack("<Q", 64))
    header = header + b"\x00" * (64 - len(header))
    assert len(header) == 64

    index_rows = [None] * len(rows)
    per_kind = {s: {"n": 0, "raw": 0, "stored": 0} for s in SUFFIX}
    n_split = 0
    off = 64
    done = 0

    with open(store_path, "wb") as out:
        out.write(header)
        with mp.Pool(NWORKERS, initializer=worker_init) as pool:
            for (ci, blob, scale_len, split) in pool.imap(encode_row, rows, chunksize=4):
                _, il, e, t, moff, mnb, msha = rows[ci]
                out.write(blob)
                index_rows[ci] = IDX_REC.pack(il, e, t, moff, mnb,
                                              bytes.fromhex(msha), off, len(blob))
                k = SUFFIX[t]
                per_kind[k]["n"] += 1
                per_kind[k]["raw"] += mnb
                per_kind[k]["stored"] += len(blob)
                n_split += 1 if split else 0
                off += len(blob)
                done += 1
                if done % 500 == 0:
                    el = time.time() - t_start
                    print("  encoded %d/%d rows  %.1f s  %.2f MB/s"
                          % (done, len(rows), el,
                             sum(v["raw"] for v in per_kind.values()) / el / 1e6),
                          flush=True)

    store_size = os.path.getsize(store_path)
    if store_size != off:
        raise RuntimeError("container size %d != expected %d" % (store_size, off))
    t_enc = time.time() - t_start
    print("container written: %d bytes in %.1f s" % (store_size, t_enc), flush=True)

    store_sha = sha256_file(store_path)
    print("container sha256: %s" % store_sha, flush=True)

    ihdr = (b"OB4INDX1" + struct.pack("<I", 1) + struct.pack("<Q", len(rows))
            + struct.pack("<Q", store_size) + bytes.fromhex(store_sha))
    ihdr = ihdr + b"\x00" * (64 - len(ihdr))
    assert len(ihdr) == 64
    with open(index_path, "wb") as f:
        f.write(ihdr)
        for rec in index_rows:
            f.write(rec)
    index_size = os.path.getsize(index_path)
    index_sha = sha256_file(index_path)
    print("index written: %d bytes  sha256 %s" % (index_size, index_sha), flush=True)

    stored_total = store_size + index_size
    receipt = {
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "codec": "C2 split-stream zstd -19 (frozen, OB4-REMAT-1-PREREG.md section 3)",
        "zstd_library": ZSTD_SO,
        "zstd_version": zver,
        "zstd_level": LEVEL,
        "workers": NWORKERS,
        "gguf": GGUF,
        "gguf_sha256_pinned": GGUF_SHA,
        "manifest": MANIFEST,
        "manifest_sha256": sha256_file(MANIFEST),
        "layers": L,
        "experts": E,
        "rows": len(rows),
        "rows_split_stream": n_split,
        "rows_single_frame": len(rows) - n_split,
        "raw_bytes_total": raw_total,
        "TOTAL_EXPERT_BYTES": TOTAL_EXPERT_BYTES,
        "container_path": store_path,
        "container_bytes": store_size,
        "container_sha256": store_sha,
        "index_path": index_path,
        "index_bytes": index_size,
        "index_sha256": index_sha,
        "index_record_bytes": IDX_REC.size,
        "stored_bytes_total": stored_total,
        "ratio_container_only": store_size / raw_total,
        "ratio_with_index": stored_total / raw_total,
        "bytes_saved": raw_total - stored_total,
        "encode_wall_seconds": t_enc,
        "by_tensor_kind": {
            k: {"n": v["n"], "raw_bytes": v["raw"], "stored_bytes": v["stored"],
                "ratio": v["stored"] / v["raw"]}
            for k, v in per_kind.items()
        },
    }
    with open(RECEIPT, "w") as f:
        json.dump(receipt, f, indent=1, sort_keys=True)
    print(json.dumps(receipt, indent=1, sort_keys=True), flush=True)
    print("OK build_store total %.1f s" % (time.time() - t_start), flush=True)


if __name__ == "__main__":
    main()
