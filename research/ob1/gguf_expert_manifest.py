#!/usr/bin/env python3
# OB-1 stage 1, step 1: expert digest manifest.
#
# Parses the GGUF header + tensor-info section (no full-file load up front),
# locates the six per-layer fused expert tensors that gpt-oss packs per
# projection (ffn_gate_exps.{weight,bias}, ffn_up_exps.{weight,bias},
# ffn_down_exps.{weight,bias} -- each one tensor per layer holding ALL E
# experts' data, not one tensor per expert), computes each expert's absolute
# byte range within that tensor, and sha256's each expert's slice by reading
# directly from the on-disk file (no torch/gguf third-party dep, stdlib
# only).
#
# PACKING ASSUMPTION, STATED: the expert axis is the tensor's outermost
# (slowest-varying) GGUF dimension (dims listed as (n_embd, n_ff, n_expert)
# for the weight tensors), so expert e's bytes are the contiguous slice
# [e * (bytes_span/E), (e+1) * (bytes_span/E)) of the tensor's byte span.
# This is the same per-expert division RS053 stage 3 used
# (research/rs053/gguf-expert-bytes.py, RUNLOG-1.txt section 5,
# PER_EXPERT_BYTES_PER_LAYER=13253760) to get a size; this tool checks the
# division is exact (bytes_span % E == 0) for every tensor before trusting
# it and additionally verifies its own PER_EXPERT_BYTES_PER_LAYER total
# against that prior, independently-banked number (see the manifest
# footer / stage report).
#
# GGUF header/tensor-info reader follows the method in
# research/rs053/gguf-expert-bytes.py (RS053 stage 3's already-validated
# reader: magic+version+kv section, then tensor-info list of name/dims/
# type/offset, data_start = end-of-tensor-info rounded up to
# general.alignment); this tool extends it to per-expert byte ranges +
# sha256, which gguf-expert-bytes.py did not compute (it stopped at
# per-tensor and per-layer totals).
#
# Usage: gguf_expert_manifest.py <model.gguf> <out_manifest.sha256>
# Writes <out_manifest.sha256> (CSV-ish, one row per layer,expert,tensor)
# and prints a short literal summary to stdout.

import struct, sys, os, hashlib, time


def rd(f, fmt):
    n = struct.calcsize(fmt)
    b = f.read(n)
    if len(b) != n:
        raise EOFError("short read")
    return struct.unpack(fmt, b)


def rstr(f):
    (n,) = rd(f, "<Q")
    return f.read(n).decode("utf-8", "replace")


# gguf value type enum (subset used by kv values we care about)
VT = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}


def rval(f, t):
    if t == 8:
        return rstr(f)
    if t == 9:
        (et,) = rd(f, "<I")
        (n,) = rd(f, "<Q")
        return [rval(f, et) for _ in range(n)]
    return rd(f, VT[t])[0]


def parse_header(path):
    sz = os.path.getsize(path)
    f = open(path, "rb")
    magic = f.read(4)
    assert magic == b"GGUF", magic
    (ver,) = rd(f, "<I")
    (ntensor,) = rd(f, "<Q")
    (nkv,) = rd(f, "<Q")
    kv = {}
    for _ in range(nkv):
        k = rstr(f)
        (t,) = rd(f, "<I")
        kv[k] = rval(f, t)
    tensors = []
    for _ in range(ntensor):
        name = rstr(f)
        (nd,) = rd(f, "<I")
        dims = [rd(f, "<Q")[0] for _ in range(nd)]
        (tt,) = rd(f, "<I")
        (off,) = rd(f, "<Q")
        tensors.append({"name": name, "dims": dims, "type": tt, "offset": off})
    align = kv.get("general.alignment", 32)
    pos = f.tell()
    data_start = pos + (-pos) % align
    f.close()
    return {"path": path, "file_size": sz, "version": ver, "n_tensor": ntensor,
            "align": align, "data_start": data_start, "kv": kv, "tensors": tensors}


SUFFIXES = [
    "ffn_gate_exps.weight", "ffn_up_exps.weight", "ffn_down_exps.weight",
    "ffn_gate_exps.bias", "ffn_up_exps.bias", "ffn_down_exps.bias",
]


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: gguf_expert_manifest.py <model.gguf> <out_manifest.sha256>")
    model_path, out_path = sys.argv[1], sys.argv[2]
    t0 = time.time()
    g = parse_header(model_path)
    E = g["kv"].get("gpt-oss.expert_count")
    L = g["kv"].get("gpt-oss.block_count")
    if E is None or L is None:
        raise SystemExit("MISSING KV: gpt-oss.expert_count/block_count not found")

    ts = sorted(g["tensors"], key=lambda t: t["offset"])
    for i, t in enumerate(ts):
        nxt = ts[i + 1]["offset"] if i + 1 < len(ts) else (g["file_size"] - g["data_start"])
        t["bytes_span"] = nxt - t["offset"]
    by_name = {t["name"]: t for t in ts}

    rows = []
    total_expert_bytes = 0
    per_layer_total_bytes = None  # bytes for ALL E experts of one layer, summed over the 6 suffixes
    f = open(model_path, "rb")
    for l in range(L):
        layer_bytes = 0
        for suf in SUFFIXES:
            name = "blk.%d.%s" % (l, suf)
            t = by_name.get(name)
            if t is None:
                raise SystemExit("MISSING TENSOR %s" % name)
            span = t["bytes_span"]
            if span % E != 0:
                raise SystemExit("NOT UNIFORM: %s span=%d not divisible by E=%d" % (name, span, E))
            per_expert = span // E
            abs_tensor_off = g["data_start"] + t["offset"]
            f.seek(abs_tensor_off)
            buf = f.read(span)
            if len(buf) != span:
                raise SystemExit("SHORT READ on %s: got %d expected %d" % (name, len(buf), span))
            for e in range(E):
                lo = e * per_expert
                sl = buf[lo:lo + per_expert]
                h = hashlib.sha256(sl).hexdigest()
                abs_off = abs_tensor_off + lo
                rows.append((l, e, suf, abs_off, per_expert, h))
                total_expert_bytes += per_expert
                layer_bytes += per_expert
        if per_layer_total_bytes is None:
            per_layer_total_bytes = layer_bytes
        elif layer_bytes != per_layer_total_bytes:
            raise SystemExit("PER-LAYER BYTES NOT UNIFORM: layer %d has %d, layer 0 had %d" % (
                l, layer_bytes, per_layer_total_bytes))
    f.close()

    rows.sort(key=lambda r: (r[0], SUFFIXES.index(r[2]), r[1]))  # layer, tensor(suffix order), expert

    if per_layer_total_bytes % E != 0:
        raise SystemExit("per_layer_total_bytes %d not divisible by E=%d" % (per_layer_total_bytes, E))
    per_expert_bytes_per_layer = per_layer_total_bytes // E  # sum of all 6 suffixes' one-expert slices

    elapsed = time.time() - t0
    with open(out_path, "w", newline="\n") as out:
        out.write("# OB-1 EXPERT DIGEST MANIFEST -- %s\n" % g["kv"].get("general.name", "?"))
        out.write("# model_path=%s\n" % model_path)
        out.write("# model_file_size_bytes=%d\n" % g["file_size"])
        out.write("# gguf_data_start=%d gguf_align=%d gguf_version=%d n_tensor=%d\n" % (
            g["data_start"], g["align"], g["version"], g["n_tensor"]))
        out.write("# expert_count=%d block_count=%d\n" % (E, L))
        out.write("# per_expert_bytes_per_layer=%d (one expert's share of all 6 suffix tensors combined)\n" % per_expert_bytes_per_layer)
        out.write("# per_layer_total_expert_bytes=%d (all %d experts, one layer)\n" % (per_layer_total_bytes, E))
        out.write("# columns: layer,expert,tensor,offset,nbytes,sha256\n")
        for l, e, suf, off, nbytes, h in rows:
            out.write("%d,%d,%s,%d,%d,%s\n" % (l, e, suf, off, nbytes, h))
        out.write("# TOTAL_EXPERT_BYTES=%d\n" % total_expert_bytes)
        out.write("# TOTAL_MODEL_BYTES=%d\n" % g["file_size"])
        out.write("# ROW_COUNT=%d\n" % len(rows))
        out.write("# ELAPSED_SECONDS=%.3f\n" % elapsed)

    print("MODEL=%s" % g["kv"].get("general.name", "?"))
    print("E=%d L=%d" % (E, L))
    print("PER_EXPERT_BYTES_PER_LAYER=%d" % per_expert_bytes_per_layer)
    print("PER_LAYER_TOTAL_EXPERT_BYTES=%d" % per_layer_total_bytes)
    print("TOTAL_EXPERT_BYTES=%d" % total_expert_bytes)
    print("TOTAL_MODEL_BYTES=%d" % g["file_size"])
    print("ROW_COUNT=%d" % len(rows))
    print("ELAPSED_SECONDS=%.3f" % elapsed)
    print("OUT=%s" % out_path)


if __name__ == "__main__":
    main()
