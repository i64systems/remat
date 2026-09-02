#!/usr/bin/env python3
# OB-3 step 1 (held-out probe): AC-CODE2 extraction.
#
# AC-CODE2 = the next 32768 tokens of the SAME source file as OB-1's
# AC-CODE.txt (corpus-code.txt / openbob_s11_cpu.rs), starting immediately
# after the point where AC-CODE's own frozen acceptance-run invocation
# (llama-perplexity --chunks 32 --ctx-size 1024, i.e. 32768 tokens) stops
# consuming it. AC-CODE was never sliced at extraction time (OB-1 copied
# the whole file verbatim and let --chunks 32 do the clipping at run
# time), so this leg locates that same 32768-token clip point by
# tokenization, then continues from there.
#
# METHOD: vocab-only tokenization (llama-tokenize, model_params.vocab_only
# = true, no weights loaded) with --no-bos --no-escape, binary search
# restricted to NEWLINE-SAFE cut points. A cut placed immediately after a
# '\n' cannot fall inside a token: BPE merges never cross a
# pre-tokenizer chunk boundary, and a newline always starts a fresh
# chunk. This means a prefix tokenized ALONE, cut at a newline, reproduces
# EXACTLY the corresponding prefix of the whole-file tokenization -- no
# continuation-context uncertainty, and (for the same reason) the
# resulting AC-CODE2 file will tokenize identically whether read as a
# continuation of the source or, as it actually will be, as its own
# standalone corpus file in the live run.
#
# Step A: find X, the first newline-safe byte offset in AC-CODE.txt whose
#         standalone token count is >= 32768 (this is where AC-CODE's own
#         cut effectively lands; the exact overshoot past 32768, forced
#         by the newline-safety constraint, is reported literally).
# Step B: within the remaining bytes [X:], find Y, the first newline-safe
#         length whose STANDALONE (fresh) token count is >= 32768.
# AC-CODE2 = bytes[X : X+Y], written to
#   /mnt/f/f32/stage/research/ob3/AC-CODE2.txt   (off-repo per house rule,
#   same as every other corpus file in this program).
#
# Requires a CPU-only llama-tokenize build in this leg's own worktree
# (FORK DISCIPLINE: /root/ob3/llama.cpp, branch ob3, off c087083 --
# never built inside /root/rs053/llama.cpp directly):
#   git -C /root/rs053/llama.cpp worktree add /root/ob3/llama.cpp -b ob3 c087083
#   cmake -S /root/ob3/llama.cpp -B /root/ob3/llama.cpp/build \
#       -DGGML_CUDA=OFF -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF
#   cmake --build /root/ob3/llama.cpp/build --target llama-tokenize -j24
#
# This tool loads the model in vocab_only mode (no expert weights touched)
# but still runs it under the box-wide RUNLOCK per house law, since it is
# a gpt-oss model process; each call is sub-second (pure vocab lookup, no
# forward pass), so the whole binary search holds the lock only briefly.

import subprocess, sys, tempfile, os, hashlib, json

BIN = "/root/ob3/llama.cpp/build/bin/llama-tokenize"
MODEL = "/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf"
SRC = "/mnt/f/f32/stage/research/ob1/AC-CODE.txt"
OUT_PATH = "/mnt/f/f32/stage/research/ob3/AC-CODE2.txt"
RESULT_PATH = "/root/ob3/ac-code2-extraction-result.json"
TARGET = 32768


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def tok_count(data: bytes) -> int:
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(data)
        path = f.name
    try:
        out = subprocess.run(
            [BIN, "-m", MODEL, "-f", path, "--no-bos", "--no-escape", "--show-count"],
            capture_output=True, text=True, check=True,
        ).stdout
        for line in out.splitlines():
            if line.startswith("Total number of tokens:"):
                return int(line.split(":")[1].strip())
        raise SystemExit("no count line in output: %r" % out)
    finally:
        os.unlink(path)


def newline_safe_candidates(buf: bytes):
    cands = [i + 1 for i, b in enumerate(buf) if b == 0x0A]
    if not cands or cands[-1] != len(buf):
        cands.append(len(buf))
    return cands


def find_min_offset_reaching(buf: bytes, candidates, target):
    lo, hi = 0, len(candidates) - 1
    calls = 0
    while lo < hi:
        mid = (lo + hi) // 2
        c = tok_count(buf[:candidates[mid]])
        calls += 1
        if c >= target:
            hi = mid
        else:
            lo = mid + 1
    off = candidates[lo]
    count = tok_count(buf[:off])
    calls += 1
    return off, count, calls


def main():
    with open(SRC, "rb") as f:
        data = f.read()
    print("SRC=%s bytes=%d sha256=%s" % (SRC, len(data), sha256_bytes(data)))

    candidates = newline_safe_candidates(data)
    print("newline_safe_candidates=%d file_bytes=%d" % (len(candidates), len(data)))

    whole_count = tok_count(data)
    print("WHOLE_FILE_TOKEN_COUNT(no_bos)=%d" % whole_count)
    if whole_count < 2 * TARGET:
        print("WARNING: whole file has fewer than 2*TARGET tokens; AC-CODE2 may not "
              "reach the full 32768-token budget")

    X, countX, calls_a = find_min_offset_reaching(data, candidates, TARGET)
    print("STEP_A calls=%d X=%d count_at_X=%d overshoot=%d" % (
        calls_a, X, countX, countX - TARGET))
    if countX < TARGET:
        raise SystemExit("STEP A FAILED: could not reach target token count within file")

    remaining = data[X:]
    rel_candidates = newline_safe_candidates(remaining)
    print("remaining_bytes=%d remaining_newline_safe_candidates=%d" % (
        len(remaining), len(rel_candidates)))

    Y, countY, calls_b = find_min_offset_reaching(remaining, rel_candidates, TARGET)
    print("STEP_B calls=%d Y=%d count_at_Y=%d overshoot=%d" % (
        calls_b, Y, countY, countY - TARGET))
    if countY < TARGET:
        raise SystemExit("STEP B FAILED: source file exhausted before reaching a second "
                          "32768-token window; AC-CODE2 cannot be built as specified")

    ac_code2 = remaining[:Y]
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "wb") as f:
        f.write(ac_code2)

    result = {
        "source_file": SRC,
        "source_sha256": sha256_bytes(data),
        "source_bytes": len(data),
        "whole_file_token_count_no_bos": whole_count,
        "target_tokens": TARGET,
        "cut_X_byte_offset": X,
        "cut_X_token_count_no_bos": countX,
        "cut_X_overshoot_tokens": countX - TARGET,
        "ac_code2_byte_length": len(ac_code2),
        "ac_code2_token_count_no_bos": countY,
        "ac_code2_overshoot_tokens": countY - TARGET,
        "ac_code2_path": OUT_PATH,
        "ac_code2_sha256": sha256_bytes(ac_code2),
        "method": "newline-safe binary search on standalone llama-tokenize --no-bos --no-escape counts",
    }
    print("RESULT_JSON=" + json.dumps(result, sort_keys=True))
    with open(RESULT_PATH, "w") as f:
        json.dump(result, f, sort_keys=True, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
