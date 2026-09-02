#!/bin/sh
# OB-1 stage 1, step 4: the four baseline (fully-resident) runs, each run
# TWICE for an A/A byte-identity check on both the route log and the
# identity artifact (stdout). CTX=1024 CHUNKS=32 NB=1024 NUB=1024 gives
# n_seq=1 in llama-perplexity's batching arithmetic (n_batch==n_ctx), the
# same safe shape RS053's own runs used (ctx>=batch, n_batch%n_ctx==0);
# 1024*32=32768 = the OB-1 token budget exactly.
set -e
MODEL=/root/openbob-baselines/models/gpt-oss-20b-MXFP4.gguf
AC_PROSE=/mnt/f/f32/stage/research/ob1/AC-PROSE.txt
AC_CODE=/mnt/f/f32/stage/research/ob1/AC-CODE.txt
SH=/mnt/f/f32/openbob-wt/research-2/research/ob1/run.sh

sh "$SH" prose-a "$MODEL" "$AC_PROSE" 1024 32 1024 1024 -ngl 99
sh "$SH" prose-b "$MODEL" "$AC_PROSE" 1024 32 1024 1024 -ngl 99
sh "$SH" code-a  "$MODEL" "$AC_CODE"  1024 32 1024 1024 -ngl 99
sh "$SH" code-b  "$MODEL" "$AC_CODE"  1024 32 1024 1024 -ngl 99
