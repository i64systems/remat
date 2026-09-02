#!/usr/bin/env python3
# OB-5b C3-T2: THE TRUNK MANIFEST AND THE CLOSED-FORM BANK.
#
# Extends research/ob1/gguf_expert_manifest.py's reader (itself following
# research/rs053/gguf-expert-bytes.py's already-validated GGUF header
# reader) from expert tensors to TRUNK (non-expert) tensors.
#
# This tool performs, as an unavoidable precondition of building a correct
# manifest, the same header-parse census that the design note's slice T1
# specifies (component names, dims, types, byte spans, the tie question).
# P08/T2 is fired without a separately-landed P03/T1 receipt in this
# worktree; this tool's census output is offered AS the T1-equivalent
# measurement, cross-checked byte-for-byte against RS053 section 5's
# already-published NON_EXPERT_BYTES totals (the only independent prior
# reading of the same quantity), and is reported honestly as such rather
# than silently assumed.
#
# No model process, no runlock (matches T1/T2's own venue notes: "no model
# run, no runlock, no weights downloaded" -- weights are READ here, once,
# directly off disk by pread, exactly as T2's venue note describes: "one
# full read of 2300997888 B, 1.8 s cold").
#
# Usage:
#   trunk_manifest.py <model.gguf> <label> <out_dir>
# Writes:
#   <out_dir>/TRUNK-CENSUS-<label>.txt
#   <out_dir>/TRUNK-MANIFEST-<label>.sha256
# and prints a literal summary to stdout.

import struct, sys, os, hashlib, time

PAGE = 4096

# RS053 section 5 literals, the only independent prior reading of this
# quantity. Used as a cross-check, never as an input to the arithmetic
# below.
RS053_NON_EXPERT_BYTES = {"20B": 1917670656, "120B": 2300997888}
RS053_DATA_START = {"20B": 13008288, "120B": 13022240}
OB1B_RESIDENT_ALWAYS = {"20B": 1930678944, "120B": 2314020128}

EXPERT_SUFFIXES = [
    "ffn_gate_exps.weight", "ffn_up_exps.weight", "ffn_down_exps.weight",
    "ffn_gate_exps.bias", "ffn_up_exps.bias", "ffn_down_exps.bias",
]


def rd(f, fmt):
    n = struct.calcsize(fmt)
    b = f.read(n)
    if len(b) != n:
        raise EOFError("short read")
    return struct.unpack(fmt, b)


def rstr(f):
    (n,) = rd(f, "<Q")
    return f.read(n).decode("utf-8", "replace")


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


def is_expert(name):
    return name.startswith("blk.") and any(name.endswith(s) for s in EXPERT_SUFFIXES)


def sha256_range(f, abs_off, nbytes):
    f.seek(abs_off)
    buf = f.read(nbytes)
    if len(buf) != nbytes:
        raise SystemExit("SHORT READ at %d: got %d expected %d" % (abs_off, len(buf), nbytes))
    return hashlib.sha256(buf).hexdigest()


def build(model_path, label, out_dir):
    t0 = time.time()
    g = parse_header(model_path)
    E = g["kv"].get("gpt-oss.expert_count")
    L = g["kv"].get("gpt-oss.block_count")
    n_embd = g["kv"].get("gpt-oss.embedding_length")
    if E is None or L is None or n_embd is None:
        raise SystemExit("MISSING KV")

    ts = sorted(g["tensors"], key=lambda t: t["offset"])
    for i, t in enumerate(ts):
        nxt = ts[i + 1]["offset"] if i + 1 < len(ts) else (g["file_size"] - g["data_start"])
        t["bytes_span"] = nxt - t["offset"]
        t["abs_offset"] = g["data_start"] + t["offset"]
    by_name = {t["name"]: t for t in ts}

    trunk = [t for t in ts if not is_expert(t["name"])]
    expert = [t for t in ts if is_expert(t["name"])]
    glob = [t for t in trunk if not t["name"].startswith("blk.")]
    perlayer = [t for t in trunk if t["name"].startswith("blk.")]

    sum_trunk_bytes = sum(t["bytes_span"] for t in trunk)
    sum_expert_bytes = sum(t["bytes_span"] for t in expert)

    # ---- B1-1 / B1-2 reconciliation against RS053 and OB-1b (report-only bars, asserted) ----
    assert sum_trunk_bytes == RS053_NON_EXPERT_BYTES[label], (sum_trunk_bytes, RS053_NON_EXPERT_BYTES[label])
    assert g["data_start"] == RS053_DATA_START[label], (g["data_start"], RS053_DATA_START[label])
    assert sum_trunk_bytes + g["data_start"] == OB1B_RESIDENT_ALWAYS[label], \
        (sum_trunk_bytes, g["data_start"], OB1B_RESIDENT_ALWAYS[label])

    # ---- B1-3: structure, 3 global + 13 per layer ----
    per_layer_suffixes = sorted(set(t["name"].split(".", 2)[2] for t in perlayer))
    assert len(glob) == 3, len(glob)
    assert len(per_layer_suffixes) == 13, len(per_layer_suffixes)
    per_layer_names = ["blk.0." + s for s in per_layer_suffixes]

    # ---- K-T1: the tie question ----
    tw = by_name["token_embd.weight"]
    ow = by_name["output.weight"]
    tied = (tw["offset"] == ow["offset"])
    same_shape = (tw["dims"] == ow["dims"] and tw["type"] == ow["type"] and tw["bytes_span"] == ow["bytes_span"])

    # ---- per-component exact byte totals (replaces the T-A/T-B bracket) ----
    Gb = sum(t["bytes_span"] for t in glob)
    Pb_per_layer = sum(t["bytes_span"] for t in ts if t["name"].startswith("blk.0.") and not is_expert(t["name"]))
    Pb_total = Pb_per_layer * L
    Hb = g["data_start"]
    assert Gb + Pb_total + Hb == OB1B_RESIDENT_ALWAYS[label]

    # router + norms: the resident trunk floor (ruling C3-R1)
    floor_names = {"attn_norm.weight", "post_attention_norm.weight", "ffn_gate_inp.weight", "ffn_gate_inp.bias"}
    floor_per_layer = sum(t["bytes_span"] for t in ts if t["name"].startswith("blk.0.")
                           and t["name"].split(".", 2)[2] in floor_names)
    floor_total = floor_per_layer * L

    # attention-only per-layer bytes (what the K_t sweep actually leases)
    attn_per_layer = Pb_per_layer - floor_per_layer
    attn_total = attn_per_layer * L

    # embedding / head row geometry
    vocab = tw["dims"][-1]
    row_elems = tw["dims"][0]
    assert tw["dims"] == [n_embd, vocab]
    row_bytes = tw["bytes_span"] // vocab
    assert row_bytes * vocab == tw["bytes_span"], "row size does not divide evenly"
    assert ow["dims"] == [n_embd, vocab] and ow["bytes_span"] == tw["bytes_span"]

    # ---- manifest rows ----
    f = open(model_path, "rb")
    rows = []  # (kind, key, abs_off, nbytes, ggml_type, sha256)

    # per-layer trunk tensors, whole-tensor rows (attention + router + norms), all L layers
    for l in range(L):
        for suf in per_layer_suffixes:
            name = "blk.%d.%s" % (l, suf)
            t = by_name.get(name)
            if t is None:
                raise SystemExit("MISSING TENSOR %s" % name)
            h = sha256_range(f, t["abs_offset"], t["bytes_span"])
            rows.append(("PERLAYER", "%d,%s" % (l, suf), t["abs_offset"], t["bytes_span"], t["type"], h))

    # output_norm.weight: one whole-tensor row (part of the resident floor)
    onw = by_name["output_norm.weight"]
    h = sha256_range(f, onw["abs_offset"], onw["bytes_span"])
    rows.append(("NORM", "output_norm.weight", onw["abs_offset"], onw["bytes_span"], onw["type"], h))

    # embedding blocks, canonical b=8 rows/block (matches the design note's
    # section 6.1's own worked arithmetic to the byte -- see receipt).
    EB = 8
    assert vocab % EB == 0, "vocab not a multiple of EB, ragged tail needs handling"
    n_eblocks = vocab // EB
    embed_rows = []
    for bi in range(n_eblocks):
        off = tw["abs_offset"] + bi * EB * row_bytes
        nb = EB * row_bytes
        embed_rows.append((bi, off, nb))
    # A/A cost note only: hashing all 25136 (20b/120b identical vocab) blocks
    # of the full table is the same total bytes as hashing token_embd.weight
    # whole; we do it block-wise so the manifest carries a digest PER LEASE
    # UNIT (section 8.1), which a whole-tensor hash would not.
    for bi, off, nb in embed_rows:
        h = sha256_range(f, off, nb)
        rows.append(("EMBED", str(bi), off, nb, tw["type"], h))

    # head tiles, canonical 32 tiles (evenly divides vocab: 201088 / 32 = 6284)
    HT = 32
    assert vocab % HT == 0, "vocab not evenly divisible by head tile count"
    tile_rows = vocab // HT
    tile_bytes = tile_rows * row_bytes
    head_rows_list = []
    for ti in range(HT):
        off = ow["abs_offset"] + ti * tile_bytes
        head_rows_list.append((ti, off, tile_bytes))
    for ti, off, nb in head_rows_list:
        h = sha256_range(f, off, nb)
        rows.append(("HEAD", str(ti), off, nb, ow["type"], h))

    f.close()

    manifest_covered_bytes = sum(r[3] for r in rows)
    # cross-check: PERLAYER rows cover Pb_total, NORM covers onw bytes,
    # EMBED covers tw bytes, HEAD covers ow bytes -- together they must
    # equal the full trunk sum (B2-1).
    assert manifest_covered_bytes == sum_trunk_bytes, (manifest_covered_bytes, sum_trunk_bytes)

    elapsed = time.time() - t0

    os.makedirs(out_dir, exist_ok=True)
    census_path = os.path.join(out_dir, "TRUNK-CENSUS-%s.txt" % label)
    manifest_path = os.path.join(out_dir, "TRUNK-MANIFEST-%s.sha256" % label)

    with open(census_path, "w", newline="\n") as out:
        out.write("# OB-5b C3-T2 TRUNK CENSUS -- %s (%s)\n" % (label, g["kv"].get("general.name", "?")))
        out.write("model_path=%s\n" % model_path)
        out.write("file_size=%d data_start=%d align=%d n_tensor=%d gguf_version=%d\n" % (
            g["file_size"], g["data_start"], g["align"], g["n_tensor"], g["version"]))
        out.write("expert_count(E)=%d block_count(L)=%d embedding_length(n_embd)=%d vocab=%d\n" % (
            E, L, n_embd, vocab))
        out.write("n_trunk_tensors=%d n_expert_tensors=%d n_global=%d n_perlayer_suffixes=%d\n" % (
            len(trunk), len(expert), len(glob), len(per_layer_suffixes)))
        out.write("SUM_TRUNK_BYTES=%d (RS053 NON_EXPERT_BYTES=%d) MATCH=%s\n" % (
            sum_trunk_bytes, RS053_NON_EXPERT_BYTES[label], sum_trunk_bytes == RS053_NON_EXPERT_BYTES[label]))
        out.write("resident_always_check: SUM_TRUNK_BYTES+data_start=%d OB1B_resident_always=%d MATCH=%s\n" % (
            sum_trunk_bytes + g["data_start"], OB1B_RESIDENT_ALWAYS[label],
            sum_trunk_bytes + g["data_start"] == OB1B_RESIDENT_ALWAYS[label]))
        out.write("\n--- GLOBAL TENSORS (%d) ---\n" % len(glob))
        for t in glob:
            out.write("%s dims=%s type=%d abs_offset=%d bytes=%d page_aligned=%s\n" % (
                t["name"], t["dims"], t["type"], t["abs_offset"], t["bytes_span"],
                t["abs_offset"] % PAGE == 0))
        out.write("Gb (sum of global trunk bytes) = %d\n" % Gb)
        out.write("\n--- K-T1 THE TIE QUESTION ---\n")
        out.write("token_embd.weight: offset=%d dims=%s type=%d bytes=%d\n" % (
            tw["offset"], tw["dims"], tw["type"], tw["bytes_span"]))
        out.write("output.weight:     offset=%d dims=%s type=%d bytes=%d\n" % (
            ow["offset"], ow["dims"], ow["type"], ow["bytes_span"]))
        out.write("TIED (same on-disk tensor, same offset) = %s\n" % tied)
        out.write("SAME_SHAPE_DIFFERENT_TENSOR (equal dims/type/bytes, distinct offsets) = %s\n" % same_shape)
        out.write("VERDICT: K-T1 %s (embedding and output projection are %s on disk)\n" % (
            "DOES NOT FIRE" if not tied else "FIRES",
            "two distinct tensors" if not tied else "one tied tensor"))
        out.write("\n--- PER-LAYER STRUCTURE (13 tensors x %d layers) ---\n" % L)
        out.write("suffixes=%s\n" % per_layer_suffixes)
        for name in per_layer_names:
            t = by_name[name]
            out.write("%s dims=%s type=%d bytes=%d\n" % (t["name"], t["dims"], t["type"], t["bytes_span"]))
        out.write("Pb_per_layer (13 tensors, exact) = %d\n" % Pb_per_layer)
        out.write("Pb_total (x%d layers) = %d\n" % (L, Pb_total))
        out.write("floor_per_layer (2 norms + router weight+bias, ruling C3-R1) = %d\n" % floor_per_layer)
        out.write("floor_total (x%d layers) = %d\n" % (L, floor_total))
        out.write("attn_per_layer (Pb_per_layer - floor_per_layer, what K_t actually leases) = %d\n" % attn_per_layer)
        out.write("attn_total (x%d layers) = %d\n" % (L, attn_total))
        out.write("\n--- TRUNK-H ---\n")
        out.write("TRUNK-H (gguf header+tensor-info, data_start) = %d\n" % Hb)
        out.write("\n--- RECONCILIATION: Gb + Pb_total + Hb = resident_always ---\n")
        out.write("%d + %d + %d = %d (want %d) MATCH=%s\n" % (
            Gb, Pb_total, Hb, Gb + Pb_total + Hb, OB1B_RESIDENT_ALWAYS[label],
            Gb + Pb_total + Hb == OB1B_RESIDENT_ALWAYS[label]))
        out.write("\n--- EMBEDDING / HEAD ROW GEOMETRY ---\n")
        out.write("vocab=%d n_embd=%d row_bytes(Q8_0? type=%d)=%d\n" % (vocab, n_embd, tw["type"], row_bytes))
        out.write("\n--- MANIFEST LEASE-UNIT SCHEME (canonical, matches section 6.1/6.2 worked numbers) ---\n")
        out.write("EMBED: b=%d rows/block, n_blocks=%d, raw_block_bytes=%d, committed(page-outward)=%d, edge=%d B/block (%.4f pct)\n" % (
            EB, n_eblocks, EB * row_bytes, -(-(EB * row_bytes) // PAGE) * PAGE,
            (-(-(EB * row_bytes) // PAGE) * PAGE) - EB * row_bytes,
            100.0 * ((-(-(EB * row_bytes) // PAGE) * PAGE) - EB * row_bytes) / (EB * row_bytes)))
        out.write("HEAD: %d tiles, tile_rows=%d, raw_tile_bytes=%d, committed(page-outward)=%d, edge=%d B/tile (%.4f pct)\n" % (
            HT, tile_rows, tile_bytes, -(-tile_bytes // PAGE) * PAGE,
            (-(-tile_bytes // PAGE) * PAGE) - tile_bytes,
            100.0 * ((-(-tile_bytes // PAGE) * PAGE) - tile_bytes) / tile_bytes))
        out.write("\nMANIFEST_ROW_COUNT=%d MANIFEST_COVERED_BYTES=%d SUM_TRUNK_BYTES=%d MATCH=%s\n" % (
            len(rows), manifest_covered_bytes, sum_trunk_bytes, manifest_covered_bytes == sum_trunk_bytes))
        out.write("ELAPSED_SECONDS=%.3f\n" % elapsed)

    with open(manifest_path, "w", newline="\n") as out:
        out.write("# OB-5b C3-T2 TRUNK LEASE MANIFEST -- %s (%s)\n" % (label, g["kv"].get("general.name", "?")))
        out.write("# model_path=%s\n" % model_path)
        out.write("# model_file_size_bytes=%d\n" % g["file_size"])
        out.write("# gguf_data_start=%d gguf_align=%d gguf_version=%d n_tensor=%d\n" % (
            g["data_start"], g["align"], g["version"], g["n_tensor"]))
        out.write("# expert_count=%d block_count=%d vocab=%d row_bytes=%d\n" % (E, L, vocab, row_bytes))
        out.write("# EMBED block: b=%d rows, n_blocks=%d ; HEAD tile: %d tiles, %d rows/tile\n" % (
            EB, n_eblocks, HT, tile_rows))
        out.write("# columns: kind,key,abs_offset,nbytes,ggml_type,sha256\n")
        for kind, key, off, nb, typ, h in rows:
            out.write("%s,%s,%d,%d,%d,%s\n" % (kind, key, off, nb, typ, h))
        out.write("# MANIFEST_ROW_COUNT=%d\n" % len(rows))
        out.write("# MANIFEST_COVERED_BYTES=%d\n" % manifest_covered_bytes)
        out.write("# SUM_TRUNK_BYTES=%d\n" % sum_trunk_bytes)
        out.write("# ELAPSED_SECONDS=%.3f\n" % elapsed)

    summary = {
        "label": label, "E": E, "L": L, "vocab": vocab, "row_bytes": row_bytes,
        "Gb": Gb, "Pb_per_layer": Pb_per_layer, "Pb_total": Pb_total, "Hb": Hb,
        "floor_per_layer": floor_per_layer, "floor_total": floor_total,
        "attn_per_layer": attn_per_layer, "attn_total": attn_total,
        "tied": tied, "row_count": len(rows), "covered_bytes": manifest_covered_bytes,
        "elapsed": elapsed, "EB": EB, "n_eblocks": n_eblocks, "HT": HT, "tile_rows": tile_rows,
        "tile_bytes": tile_bytes,
    }
    print("=== %s ===" % label)
    for k, v in summary.items():
        print("%s=%s" % (k, v))
    return summary, census_path, manifest_path


if __name__ == "__main__":
    model_path, label, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    build(model_path, label, out_dir)
