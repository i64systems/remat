import struct, sys, os, json

def rd(f, fmt):
    n = struct.calcsize(fmt)
    b = f.read(n)
    if len(b) != n:
        raise EOFError("short read")
    return struct.unpack(fmt, b)

def rstr(f):
    (n,) = rd(f, "<Q")
    return f.read(n).decode("utf-8", "replace")

# gguf value type enum
VT = {0:"<B",1:"<b",2:"<H",3:"<h",4:"<I",5:"<i",6:"<f",7:"<?",10:"<Q",11:"<q",12:"<d"}

def rval(f, t):
    if t == 8:
        return rstr(f)
    if t == 9:
        (et,) = rd(f, "<I")
        (n,) = rd(f, "<Q")
        return [rval(f, et) for _ in range(n)]
    return rd(f, VT[t])[0]

def parse(path):
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

def report(path):
    g = parse(path)
    ts = sorted(g["tensors"], key=lambda t: t["offset"])
    for i, t in enumerate(ts):
        nxt = ts[i+1]["offset"] if i+1 < len(ts) else (g["file_size"] - g["data_start"])
        t["bytes_span"] = nxt - t["offset"]
    E = g["kv"].get("gpt-oss.expert_count")
    L = g["kv"].get("gpt-oss.block_count")
    print("FILE %s" % g["path"])
    print("  file_size=%d data_start=%d align=%d n_tensor=%d gguf_version=%d" % (
        g["file_size"], g["data_start"], g["align"], g["n_tensor"], g["version"]))
    print("  expert_count=%s block_count=%s expert_used=%s" % (
        E, L, g["kv"].get("gpt-oss.expert_used_count")))
    exps = [t for t in ts if "_exps" in t["name"]]
    print("  n_expert_tensors=%d" % len(exps))
    # group by suffix
    from collections import defaultdict
    bysuf = defaultdict(list)
    for t in exps:
        suf = t["name"].split(".", 2)[-1]
        bysuf[suf].append(t)
    tot = 0
    for suf in sorted(bysuf):
        lst = bysuf[suf]
        sizes = sorted(set(t["bytes_span"] for t in lst))
        dims = sorted(set(tuple(t["dims"]) for t in lst))
        types = sorted(set(t["type"] for t in lst))
        s0 = lst[0]["bytes_span"]
        print("  suffix=%-16s count=%d type=%s dims=%s bytes_per_tensor=%s per_expert=%s" % (
            suf, len(lst), types, dims, sizes,
            [s // E for s in sizes] if E else "n/a"))
        tot += sum(t["bytes_span"] for t in lst)
    print("  TOTAL_EXPERT_TENSOR_BYTES=%d" % tot)
    if E and L:
        # per-layer totals
        perlayer = defaultdict(int)
        for t in exps:
            lid = t["name"].split(".")[1]
            perlayer[lid] += t["bytes_span"]
        vals = sorted(set(perlayer.values()))
        print("  per_layer_expert_bytes_distinct=%s (n_layers_with_experts=%d)" % (vals, len(perlayer)))
        print("  PER_EXPERT_BYTES_PER_LAYER=%s" % [v // E for v in vals])
    # non-expert total
    nonexp = g["file_size"] - g["data_start"] - tot
    print("  NON_EXPERT_BYTES=%d" % nonexp)
    print("")

for p in sys.argv[1:]:
    report(p)
