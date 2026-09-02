#!/bin/sh
# Digest every artifact this leg banks, in-repo and off-repo, in one place.
R=/mnt/f/f32/openbob-wt/research-2/research
S=/mnt/f/f32/stage/research/ob5b1
echo "=== IN REPO: research/ob5b1/ (as committed, CRLF-free by construction) ==="
sha256sum $R/ob5b1/*.sh $R/ob5b1/*.py $R/ob5b1/*.cpp 2>/dev/null | sort -k2
echo ""
echo "=== OFF REPO: gate 0 analysis outputs ==="
sha256sum $S/gate0/*.json 2>/dev/null
echo ""
echo "=== OFF REPO: the frozen prompt ==="
sha256sum $S/PROMPT-1.txt 2>/dev/null
echo ""
echo "=== OFF REPO: gate 1 run trees ==="
for d in $S/runs/*/; do
  echo "--- $d"
  sha256sum "$d"gen-ids.txt "$d"gen-text.txt "$d"prompt-ids.txt "$d"route.log 2>/dev/null
done
echo ""
echo "=== the ob5b1 engine, whole-file and .text ==="
D=/root/ob5b1/llama.cpp
sha256sum $D/build/bin/ob5b1-gen $D/build/bin/libllama.so.0 \
          $D/build/bin/libggml-base.so.0 $D/build/bin/libggml-cpu.so.0 \
          $D/build/bin/libggml.so.0 2>/dev/null
for n in libllama.so.0 libggml-base.so.0 libggml-cpu.so.0 libggml.so.0; do
  objcopy -O binary --only-section=.text $D/build/bin/$n /tmp/ob5b1.$n.text
  printf "  .text %-22s %s\n" "$n" "$(sha256sum /tmp/ob5b1.$n.text | cut -d' ' -f1)"
  rm -f /tmp/ob5b1.$n.text
done
echo ""
echo "=== the five allocator sources in the ob5b1 worktree ==="
sha256sum $D/src/ob1-lease.cpp $D/src/ob1-lease.h $D/ggml/src/ggml-backend.cpp \
          $D/src/llama-model.cpp $D/src/llama-model-loader.cpp
