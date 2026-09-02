---
license: apache-2.0
tags:
- mixture-of-experts
- inference
- memory-efficiency
- nvme
- deterministic
- reproducibility
- byte-exact
- low-bit
- systems
---

# Memory Remat from NVMe to Resident "Fast Memory": byte-exact inference from digest-verified, demand-rematerialized model memory

## What this is

A runtime that runs a 63 GB mixture-of-experts model on a 24 GB
machine by leasing expert slices from disk on demand, every slice
verified against a sha256 manifest before use, with byte-identical
output to the fully resident reference on every run. Capacity
exposure - logical bytes on disk over peak fast-resident bytes -
is measured from 1.67 to 10.25 across two open-weight models. This
repository holds the white paper, the lab records as appended to
the provisional filing, and the evidence layer beneath them.

## What bob is

bob is the assistant this runtime exists for: local, on your own
hardware, deterministic end to end. The same memory and the same
words produce the same bytes, every time, and the conversation
still moves. No cloud, no drift.

## Reproduce

    sha256sum -c MANIFEST-SHA256.txt
    cd research/claims && sh run-checks.sh
    python3 research/ob5b1/verify-runlog-arith.py
    python3 research/ob5b1/verify-runlog2-arith.py research/OB5B-S1-RUNLOG-2.txt

The first proves the tree is what the manifest pins. The second
accepts the claims table and refuses the malformed fixtures by
name. The third recomputes the serving receipt's arithmetic (49
checks) from literals transcribed out of RUNLOG-1; the fourth reads
the shipped RUNLOG-2 itself (70 checks). Beyond that, every number
in every receipt is printed beside the literal command output it
came from - pick any and re-derive it by hand. The litmus protocol
(release/LITMUS-PROTOCOL-1.md) tests a live instance in your own
words.

What ships, what stays private, and exactly what a cold reader can
and cannot verify from here: release/EVIDENCE-NOTE-1.md.
Corrections of record: release/ERRATA-1.md.

>Patent pending - U.S. provisional filed 2026 - contact: i64systems@proton.me
>(c) 2026 i64. House code licensed Apache-2.0
