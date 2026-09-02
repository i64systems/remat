#!/usr/bin/env python3
# OB-1 stage 1, step 3: acceptance corpora extraction.
#
# AC-PROSE: enwik8 bytes [96000000, 96262144) -- a DIFFERENT byte range than
# RS053's own prose corpus ([95000000, 95262144)), which was itself the
# source of the ranking route log used in step 2 (20b-prose-a). Using a
# disjoint slice of the same underlying enwik8 file keeps the acceptance
# text prose-like/comparable while guaranteeing it is not the literal text
# the resident sets were ranked on (the honesty law: ranking corpus and
# acceptance corpora must differ).
#
# AC-CODE: copied byte-exact from the RS053 code corpus (never used for
# ranking; RS053's ranking route log was prose-only per step 2).
#
# Usage: extract_corpora.py <enwik8_path> <rs053_code_corpus_path> <out_prose> <out_code>

import sys, hashlib, shutil

PROSE_START = 96000000
PROSE_END = 96262144  # 262144 bytes


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if len(sys.argv) != 5:
        raise SystemExit("usage: extract_corpora.py <enwik8> <rs053_code_corpus> <out_prose> <out_code>")
    enwik8_path, code_src_path, out_prose, out_code = sys.argv[1:5]

    with open(enwik8_path, "rb") as f:
        f.seek(PROSE_START)
        prose_bytes = f.read(PROSE_END - PROSE_START)
    if len(prose_bytes) != (PROSE_END - PROSE_START):
        raise SystemExit("SHORT READ on enwik8 slice: got %d expected %d" % (
            len(prose_bytes), PROSE_END - PROSE_START))
    with open(out_prose, "wb") as f:
        f.write(prose_bytes)

    shutil.copyfile(code_src_path, out_code)

    prose_sha = sha256_bytes(prose_bytes)
    code_sha = sha256_file(out_code)
    import os
    code_bytes = os.path.getsize(out_code)

    print("AC-PROSE path=%s bytes=%d sha256=%s range=[%d,%d)" % (
        out_prose, len(prose_bytes), prose_sha, PROSE_START, PROSE_END))
    print("AC-CODE  path=%s bytes=%d sha256=%s source=%s" % (
        out_code, code_bytes, code_sha, code_src_path))


if __name__ == "__main__":
    main()
