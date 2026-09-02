#!/bin/sh
# OB-5b S1 gate 1: write the FROZEN PROMPT BYTES.
#
# The prompt is part of the bound state (C4 s4.3), so it is written once, here,
# by a script that is itself committed, and its digest is printed by every run
# driver. Pure ASCII, LF only, no trailing whitespace. It is deliberately plain
# continuation prose rather than an instruction or a chat turn: gpt-oss-120b is
# being driven as a base model with no chat template, and this gate measures
# byte-exactness, not answer quality.
set -e
D=/mnt/f/f32/stage/research/ob5b1
mkdir -p "$D"
printf '%s' 'The following is a plain account of how a small machine keeps a large model in a small amount of memory. It reads the weights it needs from disk, checks each one against a digest before using it, and drops it again when the layer is done. The account begins here.
' > "$D/PROMPT-1.txt"
wc -c < "$D/PROMPT-1.txt"
sha256sum "$D/PROMPT-1.txt"
od -c "$D/PROMPT-1.txt" | tail -3
