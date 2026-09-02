#!/usr/bin/env python3
"""OB-1 stage 2: build the doctored manifests used by the negative controls.

A digest check that never fires proves nothing, so three deliberately wrong
manifests are written and the engine is run against each. Each must ABORT, and
the abort message must name the right failure. Nothing here touches the real
manifest: the doctored copies are written to the leg's own stage directory.

  C1  wrong digest on a NON-resident expert  -> must abort at lease time
  C2  wrong digest on a RESIDENT expert      -> must abort at model-load time
  C3  wrong offset on a resident expert      -> must abort in the loader's
                                                manifest-vs-loader geometry check
"""

import os
import sys

SRC = "/mnt/f/f32/openbob-wt/research-2/research/ob1/EXPERT-MANIFEST-20B.sha256"
OUT = "/mnt/f/f32/stage/research/ob1/controls"

# layer 0, K=16 resident set is [1,2,3,5,6,9,10,11,16,17,21,22,24,25,30,31]
NONRESIDENT_EXPERT = 0
RESIDENT_EXPERT = 1
TENSOR = "ffn_gate_exps.weight"
BAD_SHA = "0" * 64


def load(path):
    with open(path, "r") as f:
        return f.readlines()


def write(path, lines):
    with open(path, "w", newline="\n") as f:
        f.writelines(lines)


def doctor(lines, layer, expert, tensor, mode):
    out = []
    hits = 0
    for line in lines:
        if line.startswith("#"):
            out.append(line)
            continue
        p = line.rstrip("\n").split(",")
        if len(p) == 6 and int(p[0]) == layer and int(p[1]) == expert and p[2] == tensor:
            hits += 1
            if mode == "sha":
                p[5] = BAD_SHA
            elif mode == "offset":
                p[3] = str(int(p[3]) + 32)
            out.append(",".join(p) + "\n")
        else:
            out.append(line)
    if hits != 1:
        print("FAIL: doctored %d rows, expected 1" % hits)
        sys.exit(1)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    lines = load(SRC)
    write(os.path.join(OUT, "C1-bad-sha-nonresident.sha256"),
          doctor(lines, 0, NONRESIDENT_EXPERT, TENSOR, "sha"))
    write(os.path.join(OUT, "C2-bad-sha-resident.sha256"),
          doctor(lines, 0, RESIDENT_EXPERT, TENSOR, "sha"))
    write(os.path.join(OUT, "C3-bad-offset-resident.sha256"),
          doctor(lines, 0, RESIDENT_EXPERT, TENSOR, "offset"))
    print("wrote 3 doctored manifests to %s" % OUT)


if __name__ == "__main__":
    sys.exit(main())
