#!/bin/sh
# RS053: the exact run set executed on hyde 2026-08-31, in order.
# 8 prereg executions (4 runs x 2 for A/A) plus 2 unit-A/A executions and
# 1 sizing probe. Every invocation is byte-for-byte what was run.
D=$(dirname "$0")
M20=/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf
M120=/root/openbob-baselines/models/gpt-oss-120b-MXFP4.gguf
CP=/mnt/f/f32/stage/research/rs053/corpus-prose.txt
CC=/mnt/f/f32/stage/research/rs053/corpus-code.txt

# ---- step 2: unit A/A, 20b, first 512 prose tokens, twice ----
sh $D/run.sh unit-aa-a    $M20  $CP  512  1  512  512  -ngl 99
sh $D/run.sh unit-aa-b    $M20  $CP  512  1  512  512  -ngl 99
cmp /root/rs053/runs/unit-aa-a/route.log /root/rs053/runs/unit-aa-b/route.log \
  && echo "AA_VERDICT unit-aa=IDENTICAL" || echo "AA_VERDICT unit-aa=DIFFER"

# ---- R1 20b-prose, 65536 tokens (ctx 4096 x 16 chunks) ----
sh $D/run.sh 20b-prose-a  $M20  $CP  4096 16 2048 2048 -ngl 99
sh $D/run.sh 20b-prose-b  $M20  $CP  4096 16 2048 2048 -ngl 99
cmp /root/rs053/runs/20b-prose-a/route.log /root/rs053/runs/20b-prose-b/route.log \
  && echo "AA_VERDICT 20b-prose=IDENTICAL" || echo "AA_VERDICT 20b-prose=DIFFER"

# ---- R2 20b-code, 65536 tokens ----
sh $D/run.sh 20b-code-a   $M20  $CC  4096 16 2048 2048 -ngl 99
sh $D/run.sh 20b-code-b   $M20  $CC  4096 16 2048 2048 -ngl 99
cmp /root/rs053/runs/20b-code-a/route.log /root/rs053/runs/20b-code-b/route.log \
  && echo "AA_VERDICT 20b-code=IDENTICAL" || echo "AA_VERDICT 20b-code=DIFFER"

# ---- sizing probe for the 120b, not one of the 8 ----
sh $D/run.sh 120b-probe   $M120 $CP  2048 1  2048 2048 -ngl 99 -ncmoe 36

# ---- R3 120b-prose, 16384 tokens (ctx 4096 x 4 chunks) ----
# -ncmoe 36: all 36 layers of expert weights stay CPU-resident (mmap of the
# 63 GB GGUF); everything else on the GPU. -ub 4096 makes each chunk one ubatch,
# which halves the number of full expert-weight sweeps versus -ub 2048.
sh $D/run.sh 120b-prose-a $M120 $CP  4096 4  4096 4096 -ngl 99 -ncmoe 36
sh $D/run.sh 120b-prose-b $M120 $CP  4096 4  4096 4096 -ngl 99 -ncmoe 36
cmp /root/rs053/runs/120b-prose-a/route.log /root/rs053/runs/120b-prose-b/route.log \
  && echo "AA_VERDICT 120b-prose=IDENTICAL" || echo "AA_VERDICT 120b-prose=DIFFER"

# ---- R4 120b-code, 16384 tokens ----
sh $D/run.sh 120b-code-a  $M120 $CC  4096 4  4096 4096 -ngl 99 -ncmoe 36
sh $D/run.sh 120b-code-b  $M120 $CC  4096 4  4096 4096 -ngl 99 -ncmoe 36
cmp /root/rs053/runs/120b-code-a/route.log /root/rs053/runs/120b-code-b/route.log \
  && echo "AA_VERDICT 120b-code=IDENTICAL" || echo "AA_VERDICT 120b-code=DIFFER"
