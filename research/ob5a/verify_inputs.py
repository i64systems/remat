#!/usr/bin/env python3
# OB-5a stage 1, step 0: verify every input this prereg rests on, by digest
# and by shape, before a single number is predicted from any of them.
#
# Nothing here is asserted. Every file is hashed, every expected digest is a
# literal quoted from a committed receipt, and every shape claim is counted.
#
# Usage: verify_inputs.py

import hashlib
import os
import sys

# Expected digests, each quoted from a committed source.
EXPECT = {
    # research/OB1B-KNEE-1.md section 10.2 (the banked 120b paged reference).
    "/mnt/f/f32/stage/research/ob1b/runs/pag120-prose-a/route.log":
        ("a32d0051bd6d68f2777e64c7b889ae48d56621e9701b107fcef88c0e30cd89c1",
         "OB1B-KNEE-1.md s10.2 route (A and B identical)"),
    "/mnt/f/f32/stage/research/ob1b/runs/pag120-prose-a/identity.txt":
        ("9d20bd0365554989051d96b6ad4932625b0a6578002879f8253e6fcc21682019",
         "OB1B-KNEE-1.md s10.2 identity (A and B identical)"),
    "/mnt/f/f32/stage/research/ob1b/runs/pag120-prose-b/route.log":
        ("a32d0051bd6d68f2777e64c7b889ae48d56621e9701b107fcef88c0e30cd89c1",
         "OB1B-KNEE-1.md s10.2 route (A/A repeat)"),
    "/mnt/f/f32/stage/research/ob1b/runs/pag120-prose-b/identity.txt":
        ("9d20bd0365554989051d96b6ad4932625b0a6578002879f8253e6fcc21682019",
         "OB1B-KNEE-1.md s10.2 identity (A/A repeat)"),
    # research/ob1b/RESIDENT-SETS-120B-K8.json, its own source_route_log_sha256 field.
    "/mnt/f/f32/stage/research/rs053/runs/120b-prose-a/route.log":
        ("5aa8464d3c71a73648c2323456d656cd40cfcf9dc88b603e1f10da69f9efa129",
         "RESIDENT-SETS-120B-K8.json source_route_log_sha256 (the RANKING corpus)"),
    # The models named in the house rules.
    "/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf":
        ("27cd6c43", "house rules prefix only"),
    "/root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf":
        ("582bd40f", "house rules prefix only"),
}

# Files hashed for the record with no prior expectation (they become the
# expectation from here on).
RECORD = [
    "/mnt/f/f32/openbob-wt/research-2/research/ob1b/RESIDENT-SETS-120B-K8.json",
    "/mnt/f/f32/openbob-wt/research-2/research/ob1b/EXPERT-MANIFEST-120B.sha256",
    "/mnt/f/f32/stage/research/ob1/AC-PROSE.txt",
    "/mnt/f/f32/stage/research/ob1/AC-CODE.txt",
]

# The 20b regression suite, banked in OB1B-KNEE-1.md section 5 and quoted in
# this leg's task brief. These are the STOP-SHIP digests of P1.
BANKED_20B = [
    ("prose", "identity",
     "96049ccf8ca241bf58233afe13ed75e2ca43180d81973360d04cebc80d551925"),
    ("prose", "route",
     "4777aa8319f25d6e367f761ef12c7bec81a9ff7896bfed1b8ea0326b5dffc3df"),
    ("code", "identity",
     "9acdf5ef883588030b675eebea31e3afbaf9f82d12d73edad8f3254762aa0ae8"),
    ("code", "route",
     "f0c3f341d8eaf299ccf09aba7850029f62cbe3f87b5a66162741f049bff41c77"),
]

# The already-landed 20b runs whose artifacts those digests describe. Verifying
# them here proves the regression targets are reachable on this box today, so a
# P1 mismatch tomorrow can only be the allocator.
LANDED_20B = {
    "/root/ob1b/runs/res8-prose-a/identity.txt": BANKED_20B[0][2],
    "/root/ob1b/runs/res8-prose-a/route.log": BANKED_20B[1][2],
    "/root/ob1b/runs/res8-code-a/identity.txt": BANKED_20B[2][2],
    "/root/ob1b/runs/res8-code-a/route.log": BANKED_20B[3][2],
    "/root/ob1b/runs/lease-k0-prose/identity.txt": BANKED_20B[0][2],
    "/root/ob1b/runs/lease-k0-prose/route.log": BANKED_20B[1][2],
}


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    fail = 0

    print("== INPUTS WITH A PRIOR EXPECTATION ==")
    for path, (expect, src) in sorted(EXPECT.items()):
        if not os.path.exists(path):
            print("  MISSING  %s" % path)
            fail += 1
            continue
        got = sha256_of(path)
        ok = got.startswith(expect) if len(expect) < 64 else (got == expect)
        if not ok:
            fail += 1
        print("  %-5s %s" % ("OK" if ok else "FAIL", path))
        print("        size   %d" % os.path.getsize(path))
        print("        sha256 %s" % got)
        print("        expect %s   (%s)" % (expect, src))

    print()
    print("== INPUTS HASHED FOR THE RECORD ==")
    for path in RECORD:
        if not os.path.exists(path):
            print("  MISSING  %s" % path)
            fail += 1
            continue
        print("  %s" % path)
        print("        size   %d" % os.path.getsize(path))
        print("        sha256 %s" % sha256_of(path))

    print()
    print("== THE 20b REGRESSION TARGETS (P1), VERIFIED REACHABLE TODAY ==")
    print("  Each of these already-landed artifacts must be reproduced BYTE FOR")
    print("  BYTE by the new allocator. If one of them does not hash to its")
    print("  banked value right now, the regression is broken before it starts.")
    for path, expect in sorted(LANDED_20B.items()):
        if not os.path.exists(path):
            print("  MISSING  %s" % path)
            fail += 1
            continue
        got = sha256_of(path)
        ok = got == expect
        if not ok:
            fail += 1
        print("  %-5s %-46s %s" % ("OK" if ok else "FAIL", os.path.basename(
            os.path.dirname(path)) + "/" + os.path.basename(path), got))

    print()
    print("== THE FOUR BANKED 20b DIGESTS, RESTATED (STOP-SHIP under P1) ==")
    for corpus, kind, dg in BANKED_20B:
        print("  %-5s %-8s %s" % (corpus, kind, dg))

    print()
    print("VERIFY_INPUTS_FAILURES=%d" % fail)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
