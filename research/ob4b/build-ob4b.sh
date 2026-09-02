#!/bin/sh
# OB4B-PARDEC-1 phase 1: stand up the ob4b engine build.
#
# WHY NOT A PLAIN FRESH BUILD. The reference this leg must be comparable to is
# the OB-4 engine binary in /root/ob4/llama.cpp/build. A from-scratch build in a
# different source root would differ from it in embedded __FILE__ strings even
# with identical code, leaving no way to say "the only difference is my patch".
# This script copies the OB-4 build tree into the ob4b worktree, rewrites the
# absolute source paths inside it, lets cmake regenerate its makefiles against
# the new source root with -ffile-prefix-map mapping the new root back to the
# old one for embedded paths only, and recompiles ONLY what changed.
#
# PHASE A IS THE SOUNDNESS CHECK AND IT IS NOT TAUTOLOGICAL. It recompiles
# src/ob1-lease.cpp with its CONTENT UNCHANGED (restored to the ob4b baseline
# commit, which is digest-equal to the OB-4 working tree) and relinks. The
# resulting binaries are compared by sha256 against the OB-4 binaries. A match
# proves the copied object tree plus this toolchain reproduce the OB-4 engine
# byte for byte, so that after phase B the ONLY thing separating the ob4b binary
# from the ob4 binary is the parallel-decode patch. A mismatch is reported
# literally and not worked around.
set -e

SRC=/root/ob4/llama.cpp
DST=/root/ob4b/llama.cpp
LEASE=$DST/src/ob1-lease.cpp
WT=/mnt/f/f32/openbob-wt/ob4/research/ob4b

echo "=== OB4B BUILD ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "free before:"; free -g | head -2

echo "--- restore src/ob1-lease.cpp to the ob4b baseline (the OB-4 engine) ---"
git -C $DST checkout -- src/ob1-lease.cpp
git -C $DST status --short
git -C $DST log --oneline -2
echo "baseline source digests vs the OB-4 working tree:"
for f in src/CMakeLists.txt src/ob1-lease.cpp src/ob4-remat.cpp src/ob4-remat.h; do
  A=$(sha256sum $SRC/$f | cut -d" " -f1)
  B=$(sha256sum $DST/$f | cut -d" " -f1)
  if [ "$A" = "$B" ]; then echo "  MATCH  $f  $A"; else echo "  DIFFER $f ob4=$A ob4b=$B"; exit 1; fi
done

echo "--- OB-4 binaries (the reference) ---"
sha256sum $SRC/build/bin/llama-perplexity $SRC/build/bin/libllama.so.0.3.0 \
          $SRC/build/bin/libllama-perplexity-impl.so

echo "--- copy the OB-4 build tree ---"
rm -rf $DST/build
cp -a $SRC/build $DST/build

echo "--- rewrite absolute source paths in text files only (grep -I skips binaries) ---"
echo "text files referencing the old source dir: $(grep -rlI "$SRC" $DST/build | wc -l)"
grep -rlI "$SRC" $DST/build | xargs sed -i "s|$SRC|$DST|g"
echo "remaining after rewrite: $(grep -rlI "$SRC" $DST/build | wc -l)"

echo "--- cmake reconfigure against the new source root ---"
cmake -S $DST -B $DST/build -DCMAKE_CXX_FLAGS="-ffile-prefix-map=$DST=$SRC" \
    > /root/ob4b/cmake-reconf.log 2>&1 || {
  echo "CMAKE RECONFIGURE FAILED, log verbatim:"; cat /root/ob4b/cmake-reconf.log; exit 1; }
tail -3 /root/ob4b/cmake-reconf.log

echo "--- age the checked-out sources so make does not rebuild the world ---"
find $DST -path $DST/build -prune -o -type f -print | xargs -r touch -d "2020-01-01 00:00:00"
sleep 1
find $DST/build \( -name "*.o" -o -name "*.a" -o -name "*.so" -o -name "*.so.*" \) -print | xargs -r touch
find $DST/build/bin -type f -print | xargs -r touch
sleep 1

echo "--- confirm the tree is up to date (make should have nothing to do) ---"
nice -n 10 make -C $DST/build llama-perplexity -j4 2>&1 | tail -4

echo "=== PHASE A: recompile ob1-lease.cpp UNCHANGED, must reproduce the OB-4 binaries ==="
touch $LEASE
nice -n 10 make -C $DST/build llama-perplexity -j4 2>&1 | tail -8
echo "--- phase A digests ---"
sha256sum $DST/build/bin/llama-perplexity $DST/build/bin/libllama.so.0.3.0 \
          $DST/build/bin/libllama-perplexity-impl.so
A1=$(sha256sum $SRC/build/bin/llama-perplexity   | cut -d" " -f1)
A2=$(sha256sum $DST/build/bin/llama-perplexity   | cut -d" " -f1)
B1=$(sha256sum $SRC/build/bin/libllama.so.0.3.0  | cut -d" " -f1)
B2=$(sha256sum $DST/build/bin/libllama.so.0.3.0  | cut -d" " -f1)
if [ "$A1" = "$A2" ] && [ "$B1" = "$B2" ]; then
  echo "PHASE A: MATCH (object reuse + relink reproduces the OB-4 engine byte for byte)"
else
  echo "PHASE A: DIFFER"
  echo "  llama-perplexity ob4=$A1 ob4b=$A2"
  echo "  libllama.so      ob4=$B1 ob4b=$B2"
  echo "  --- does the binary embed its own source path? (the usual benign cause) ---"
  echo "  ob4  hits: $(strings $SRC/build/bin/libllama.so.0.3.0 | grep -c "ob4/llama.cpp"  || true)"
  echo "  ob4b hits: $(strings $DST/build/bin/libllama.so.0.3.0 | grep -c "ob4b/llama.cpp" || true)"
fi

echo "=== PHASE B: the parallel-decode patch ==="
python3 $WT/apply-pardec.py $LEASE
echo "--- diff stat ---"
git -C $DST diff --stat
echo "--- patch file digest (the receipt) ---"
git -C $DST diff > /root/ob4b/pardec-regenerated.patch
sha256sum $WT/pardec.patch /root/ob4b/pardec-regenerated.patch
nice -n 10 make -C $DST/build llama-perplexity -j4 2>&1 | tail -8
echo "--- phase B digests (the binary every OB-4b run uses) ---"
sha256sum $DST/build/bin/llama-perplexity $DST/build/bin/libllama.so.0.3.0 \
          $DST/build/bin/libllama-perplexity-impl.so
C2=$(sha256sum $DST/build/bin/libllama.so.0.3.0 | cut -d" " -f1)
if [ "$B1" = "$C2" ]; then
  echo "PHASE B: libllama.so UNCHANGED after the patch -- the patch did not take, STOP"
  exit 1
else
  echo "PHASE B: libllama.so changed, as the patch requires"
fi

echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== END OB4B BUILD ==="
