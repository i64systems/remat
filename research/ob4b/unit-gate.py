#!/usr/bin/env python3
"""OB4B-PARDEC-1 unit gate: the identity check that stands between the unit runs
and any full run.

Three assertions:
  1. pool 1 and pool 8 produce byte-identical identity artifacts
  2. pool 1 and pool 8 produce byte-identical route logs
  3. both are exact prefixes of the banked OB-4 32-chunk artifacts

DEFECT FIXED HERE, RECORDED RATHER THAN HIDDEN. The first version of this gate
compared the raw bytes of the 4-chunk identity.txt against the banked 32-chunk
identity.txt with str.startswith and reported FAIL. The cause was in the gate,
not the engine: identity.txt is produced by `grep '^\\[1\\]' stdout.txt`, so it
ends in a newline. The 4-chunk file is therefore

    [1]24.5827,[2]9.4037,[3]5.8070,[4]4.6785,\\n

while the banked file continues '[5]...' at that offset. The 41 bytes before the
newline are byte-identical; the newline is a line terminator, not a measurement.
The gate now strips the trailing newline from the shorter artifact before the
prefix test, and prints both forms so the reader can check the claim.

usage: unit-gate.py POOL1_DIR POOL8_DIR BANKED_DIR
"""

import hashlib
import sys


def rd(p):
    return open(p, "rb").read()


def sha(x):
    return hashlib.sha256(x).hexdigest()


def main():
    a, b, banked = sys.argv[1], sys.argv[2], sys.argv[3]

    ia, ib = rd(a + "/identity.txt"), rd(b + "/identity.txt")
    ra, rb = rd(a + "/route.log"), rd(b + "/route.log")
    ibank = rd(banked + "/identity.txt")
    rbank = rd(banked + "/route.log")

    print("pool1 identity sha256 %s (%d B)" % (sha(ia), len(ia)))
    print("pool8 identity sha256 %s (%d B)" % (sha(ib), len(ib)))
    print("pool1 route    sha256 %s (%d B)" % (sha(ra), len(ra)))
    print("pool8 route    sha256 %s (%d B)" % (sha(rb), len(rb)))
    print("pool1 identity bytes  %r" % ia)
    print("banked identity head  %r" % ibank[: len(ia) + 8])

    fail = 0

    if ia != ib:
        print("FAIL: pool1 and pool8 identity artifacts differ")
        fail = 1
    else:
        print("PASS: pool1 == pool8 identity, byte identical")

    if ra != rb:
        print("FAIL: pool1 and pool8 route logs differ")
        fail = 1
    else:
        print("PASS: pool1 == pool8 route log, byte identical")

    ia_body = ia.rstrip(b"\n")
    if not ibank.startswith(ia_body):
        print("FAIL: unit identity is not a prefix of the banked OB-4 identity")
        fail = 1
    else:
        print("PASS: unit identity (%d B, trailing newline stripped) is an exact "
              "prefix of the banked OB-4 identity" % len(ia_body))

    if not rbank.startswith(ra):
        print("FAIL: unit route log is not a prefix of the banked OB-4 route log")
        fail = 1
    else:
        print("PASS: unit route log is an exact prefix of the banked OB-4 route log")
        print("      unit lines %d, banked lines %d"
              % (ra.count(b"\n"), rbank.count(b"\n")))

    sys.exit(fail)


if __name__ == "__main__":
    main()
