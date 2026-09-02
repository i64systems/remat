#!/usr/bin/env python3
"""OB4-REMAT-1 Phase 1: manifest-driven expert slice extraction.

Reads EXPERT-MANIFEST-20B.sha256, pread's the byte ranges named in it
directly from the gguf, verifies each slice against the manifest's own
sha256, and writes the raw bytes out as per-row files under an eval/
and train/ tree for the codec sweep to consume.

No weight downloads, no model run: this is a plain pread + hash.
"""
import hashlib
import json
import os
import sys
import time

GGUF_PATH = "/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf"
MANIFEST_PATH = "/mnt/f/f32/openbob-wt/ob4/research/ob1/EXPERT-MANIFEST-20B.sha256"
OUT_DIR = "/mnt/f/f32/stage/research/ob4"

EVAL_EXPERTS = [0, 10, 20, 31]
TRAIN_EXPERTS = [4, 5]  # disjoint from EVAL_EXPERTS, used only for dictionary training

TENSOR_KINDS = [
    "ffn_gate_exps.weight",
    "ffn_up_exps.weight",
    "ffn_down_exps.weight",
    "ffn_gate_exps.bias",
    "ffn_up_exps.bias",
    "ffn_down_exps.bias",
]


def parse_manifest(path):
    rows = []
    header = []
    with open(path, "r") as f:
        for line in f:
            if line.startswith("#"):
                header.append(line.rstrip("\n"))
                continue
            line = line.strip()
            if not line:
                continue
            layer, expert, tensor, offset, nbytes, sha = line.split(",")
            rows.append({
                "layer": int(layer),
                "expert": int(expert),
                "tensor": tensor,
                "offset": int(offset),
                "nbytes": int(nbytes),
                "sha256": sha,
            })
    return header, rows


def slice_name(row):
    t = row["tensor"].replace(".", "_")
    return "L%02d_E%02d_%s.bin" % (row["layer"], row["expert"], t)


def extract_one(gguf_fd, row, out_path):
    os.pread  # sanity: ensure available (py3.3+)
    data = os.pread(gguf_fd, row["nbytes"], row["offset"])
    if len(data) != row["nbytes"]:
        return False, "short read: got %d want %d" % (len(data), row["nbytes"])
    got = hashlib.sha256(data).hexdigest()
    if got != row["sha256"]:
        return False, "DIGEST MISMATCH got=%s want=%s" % (got, row["sha256"])
    with open(out_path, "wb") as f:
        f.write(data)
    return True, len(data)


def main():
    t0 = time.time()
    header, rows = parse_manifest(MANIFEST_PATH)
    print("manifest rows:", len(rows))
    print("manifest header:")
    for h in header:
        print(" ", h)

    by_key = {(r["layer"], r["expert"], r["tensor"]): r for r in rows}
    all_layers = sorted(set(r["layer"] for r in rows))
    print("layers found:", len(all_layers), all_layers[:3], "...", all_layers[-3:])

    eval_rows = []
    for layer in all_layers:
        for expert in EVAL_EXPERTS:
            for tk in TENSOR_KINDS:
                key = (layer, expert, tk)
                if key not in by_key:
                    print("MISSING ROW", key)
                    sys.exit(1)
                eval_rows.append(by_key[key])

    train_rows = []
    for layer in all_layers:
        for expert in TRAIN_EXPERTS:
            for tk in TENSOR_KINDS:
                key = (layer, expert, tk)
                if key not in by_key:
                    print("MISSING TRAIN ROW", key)
                    sys.exit(1)
                train_rows.append(by_key[key])

    assert set(EVAL_EXPERTS).isdisjoint(set(TRAIN_EXPERTS)), "eval/train expert leakage"

    print("eval rows:", len(eval_rows), "train rows:", len(train_rows))

    eval_dir = os.path.join(OUT_DIR, "slices", "eval")
    train_dir = os.path.join(OUT_DIR, "slices", "train")
    os.makedirs(eval_dir, exist_ok=True)
    os.makedirs(train_dir, exist_ok=True)

    gguf_fd = os.open(GGUF_PATH, os.O_RDONLY)
    try:
        fails = []
        manifest_out = []
        for tag, rowlist, outdir in (("eval", eval_rows, eval_dir), ("train", train_rows, train_dir)):
            n_ok = 0
            n_bytes = 0
            for row in rowlist:
                fn = slice_name(row)
                out_path = os.path.join(outdir, fn)
                ok, info = extract_one(gguf_fd, row, out_path)
                if not ok:
                    fails.append((tag, row, info))
                    print("FAIL", tag, row, info)
                    continue
                n_ok += 1
                n_bytes += info
                manifest_out.append({
                    "set": tag,
                    "layer": row["layer"],
                    "expert": row["expert"],
                    "tensor": row["tensor"],
                    "offset": row["offset"],
                    "nbytes": row["nbytes"],
                    "sha256": row["sha256"],
                    "file": os.path.join(outdir, fn),
                })
            print(tag, "extracted ok:", n_ok, "bytes:", n_bytes)
    finally:
        os.close(gguf_fd)

    results_dir = os.path.join(OUT_DIR, "results")
    os.makedirs(results_dir, exist_ok=True)
    with open(os.path.join(results_dir, "extract-manifest.json"), "w") as f:
        json.dump({
            "gguf_path": GGUF_PATH,
            "manifest_path": MANIFEST_PATH,
            "eval_experts": EVAL_EXPERTS,
            "train_experts": TRAIN_EXPERTS,
            "n_eval_rows": len(eval_rows),
            "n_train_rows": len(train_rows),
            "fails": len(fails),
            "rows": manifest_out,
        }, f)

    print("fails:", len(fails))
    print("elapsed sec:", round(time.time() - t0, 2))
    if fails:
        sys.exit(2)


if __name__ == "__main__":
    main()
