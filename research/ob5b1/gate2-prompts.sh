#!/bin/sh
# OB-5b S1 gate 2: the three prompts of the operating envelope.
#
# Leg A's item (c): "AN IN-CORPUS AND AN OUT-OF-CORPUS PROMPT, BOTH
# MEASURED". This leg makes it three points, because "in corpus" hides a
# distinction that matters: the K=8 resident set was RANKED on the first 16384
# tokens of corpus-prose.txt, so a prompt drawn from those tokens is IN SAMPLE
# and a prompt drawn from later in the same file is in the same corpus and OUT
# OF SAMPLE. A product only ever sees the second and third cases.
#
#   PROMPT-1.txt  out of corpus   leg A's gate 1 prompt, carried unchanged
#                                 so gate 2's K=8 row is comparable to gate 1's
#   PROMPT-2.txt  in corpus, out of sample   from byte 196608 of corpus-prose.txt
#   PROMPT-3.txt  in corpus, in sample       from byte 16384 of corpus-prose.txt
#
# THE DRAW RULE, stated so a reader can re-cut them: from the given byte offset,
# advance to the first byte after the next newline, then take exactly 264 bytes,
# which is PROMPT-1's own size. No editing, no selection, no looking at what the
# text says. 16384 tokens of a 262144 byte file is roughly its first quarter at
# this tokenizer's byte rate, so 16384 is inside the ranking sample and 196608
# is far outside it.
set -e
CORPUS=/mnt/f/f32/stage/research/rs053/corpus-prose.txt
OUT=/mnt/f/f32/stage/research/ob5b1
N=264

cut_at() {  # cut_at <offset> <dest>
  python3 - "$CORPUS" "$1" "$2" "$N" <<'PY'
import sys
src, off, dst, n = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
b = open(src, "rb").read()
i = b.index(b"\n", off) + 1
open(dst, "wb").write(b[i:i+n])
print("%s offset_requested %d line_start %d bytes %d" % (dst, off, i, n))
PY
}

echo "corpus        $CORPUS"
echo "corpus_bytes  $(stat -c %s $CORPUS)"
echo "corpus_sha256 $(sha256sum $CORPUS | cut -d' ' -f1)"
cut_at 196608 "$OUT/PROMPT-2.txt"
cut_at 16384  "$OUT/PROMPT-3.txt"
printf 'the' > "$OUT/PROMPT-4.txt"
echo "$OUT/PROMPT-4.txt one word, for the narrow-prefill control"
echo ""
for f in PROMPT-1.txt PROMPT-2.txt PROMPT-3.txt PROMPT-4.txt; do
  echo "--- $f  $(stat -c %s $OUT/$f) bytes  $(sha256sum $OUT/$f | cut -d' ' -f1)"
  cat "$OUT/$f"; echo ""
done
