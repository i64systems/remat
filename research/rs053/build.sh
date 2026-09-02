#!/bin/sh
# RS053 instrument build, as actually run on hyde 2026-08-31.
# Script-to-file law: invoked from the Windows side as
#   wsl.exe -e sh /mnt/c/.../build.sh
# CPU wall: build runs under nice 10 with -j 10.
#
# Prerequisite handled here: hyde had no cmake on PATH. cmake is obtained as a
# pip wheel and unpacked into /root/rs053/tools; no system package is installed
# and the live /root/openbob-train venv (used by the MoE-0 collector) is not
# modified. Only its pip is borrowed, in download-only mode.

set -e

PIN=ca3d5a3e10d53f7ea672cb9b6178faca3e2807bc
CM=/root/rs053/tools/cmake/data/bin/cmake

mkdir -p /root/rs053 /root/rs053/logs /root/rs053/tools

# ---- cmake (wheel unpack, no system install) ----
if [ ! -x "$CM" ]; then
  /root/openbob-train/venv/bin/pip download --no-deps -d /tmp/rs053cm cmake
  python3 -c "import zipfile,glob; w=glob.glob('/tmp/rs053cm/cmake-*.whl')[0]; print('wheel:',w); zipfile.ZipFile(w).extractall('/root/rs053/tools')"
  chmod -R +x /root/rs053/tools/cmake/data/bin
fi
$CM --version | head -1

# ---- clone, pinned to the exact commit ----
# Shallow exact-commit fetch rather than a full clone: same content at the pin,
# far fewer bytes. The pin is the commit the house baselines build already uses.
if [ ! -d /root/rs053/llama.cpp/.git ]; then
  mkdir -p /root/rs053/llama.cpp
  cd /root/rs053/llama.cpp
  git init -q .
  git remote add origin https://github.com/ggml-org/llama.cpp
  git fetch -q --depth 1 origin $PIN
  git checkout -q FETCH_HEAD
fi
cd /root/rs053/llama.cpp
git log -1 --format='%H %ci %s'

# ---- apply the route-log patch ----
if ! grep -q ffn_moe_routelog src/llama-graph.cpp; then
  git apply /mnt/f/f32/stage/research/rs053/route-log.patch
fi
git diff --stat

# ---- configure + build (CUDA) ----
export PATH=/usr/local/cuda/bin:$PATH
export CUDACXX=/usr/local/cuda/bin/nvcc

nice -n 10 $CM -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=86 \
  -DLLAMA_CURL=OFF \
  -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_EXAMPLES=OFF \
  -DLLAMA_BUILD_TOOLS=ON \
  -DLLAMA_BUILD_SERVER=OFF

# NOTE: the run of 2026-08-31 also named llama-cli on this line, which is not a
# target under LLAMA_BUILD_EXAMPLES=OFF, so gmake returned 2 after llama-perplexity
# had already reached [100%]. llama-perplexity is the instrument; llama-cli is not
# needed. See RUNLOG-1.txt deviation D3.
nice -n 10 $CM --build build --target llama-perplexity -j 10

ls -la /root/rs053/llama.cpp/build/bin/llama-perplexity
