#!/bin/sh
# OB-1b: stand up the ob1b engine build.
#
# WHY THIS IS NOT A PLAIN FRESH BUILD. The landed OB-1 build
# (/root/rs053/llama.cpp/build, branch ob1 head c087083) is configured with
# GGML_CUDA=ON, so a from-scratch reconfigure recompiles several hundred nvcc
# translation units (measured: still grinding through
# ggml-cuda/template-instances after 3 minutes at -j4) for a change of ONE
# character in one CPU-side source file. This script instead copies the landed
# build tree into the ob1b worktree, rewrites the absolute source paths inside
# it, lets cmake regenerate its makefiles against the new source root, and then
# recompiles ONLY the translation units that actually changed.
#
# THE SOUNDNESS CHECK IS PHASE A, AND IT IS NOT TAUTOLOGICAL. Phase A touches
# src/ob1-lease.cpp with its CONTENT UNCHANGED and runs make. That genuinely
# recompiles that translation unit in the new tree and relinks libllama.so and
# llama-perplexity. The results are then compared by sha256 against the landed
# binaries. A match proves the copied object tree plus this toolchain reproduce
# the landed engine byte for byte, so that after phase B the ONLY thing
# separating the ob1b binary from the ob1 binary is the one-line guard change.
# A mismatch is reported literally, not worked around.
set -e

SRC=/root/rs053/llama.cpp
DST=/root/ob1b/llama.cpp
LEASE=$DST/src/ob1-lease.cpp

echo "=== OB1B BUILD ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# This script must be re-runnable. Restore src/ob1-lease.cpp to its pristine
# c087083 content first, so that phase A always compiles UNPATCHED source no
# matter how many times the script has run before. (Found the hard way: a second
# invocation reused the already-patched file left by the first, which would have
# made phase A compare the patched build against the landed one and call the
# guard change a build-system artefact.)
echo "--- restore pristine source ---"
git -C $DST checkout -- src/ob1-lease.cpp
git -C $DST status --short
echo "guard line as checked out:"
grep -n "OB1_K=%d out of range" $LEASE

echo "--- landed binaries (the reference) ---"
sha256sum $SRC/build/bin/llama-perplexity $SRC/build/bin/libllama.so

echo "--- copy build tree ---"
rm -rf $DST/build
cp -a $SRC/build $DST/build

echo "--- rewrite absolute source paths in text files only (grep -I skips binaries) ---"
echo "text files referencing old source dir: $(grep -rlI "$SRC" $DST/build | wc -l)"
grep -rlI "$SRC" $DST/build | xargs sed -i "s|$SRC|$DST|g"
echo "remaining after rewrite: $(grep -rlI "$SRC" $DST/build | wc -l)"

echo "--- cmake reconfigure against the new source root ---"
# -ffile-prefix-map is what makes phase A an EXACT check rather than an
# approximate one. Source files embed their own path through __FILE__ (llama.cpp
# uses it in its assert macros), so a translation unit recompiled under
# /root/ob1b/... would differ from the landed /root/rs053/... object in that
# string alone -- a benign difference, but one that would leave phase A unable
# to say "byte for byte". Measured on the first attempt of this script, without
# the flag: landed libllama.so carried 151 occurrences of "rs053/llama.cpp" and
# the rebuilt one carried 150 plus 1 occurrence of "ob1b/llama.cpp", exactly the
# one recompiled translation unit. The flag maps the new root back to the old
# one for embedded paths only; it changes no code generation.
cmake -S $DST -B $DST/build -DCMAKE_CXX_FLAGS="-ffile-prefix-map=$DST=$SRC" \
    > /root/ob1b/cmake-reconf.log 2>&1 || {
  echo "CMAKE RECONFIGURE FAILED, log verbatim:"; cat /root/ob1b/cmake-reconf.log; exit 1; }
tail -3 /root/ob1b/cmake-reconf.log

echo "--- age the checked-out sources so make does not rebuild all 392 objects ---"
# git worktree add stamped every checked-out file with the checkout time, which
# is newer than every copied .o; and the sed above bumped every makefile. Both
# would make make rebuild the world. The objects were compiled from byte-
# identical sources at the same commit, so reusing them is sound -- and phase A
# is the check that proves it rather than assuming it.
find $DST -path $DST/build -prune -o -type f -print | xargs -r touch -d "2020-01-01 00:00:00"
sleep 1
find $DST/build \( -name "*.o" -o -name "*.a" -o -name "*.so" -o -name "*.so.*" \) -print | xargs -r touch
find $DST/build/bin -type f -print | xargs -r touch
sleep 1

echo "--- confirm the tree is now fully up to date (make should have nothing to do) ---"
nice -n 10 make -C $DST/build llama-perplexity -j4 2>&1 | tail -5

echo "=== PHASE A: recompile ob1-lease.cpp UNCHANGED, must reproduce the landed binaries ==="
touch $LEASE
nice -n 10 make -C $DST/build llama-perplexity -j4 2>&1 | tail -12
echo "--- phase A digests ---"
sha256sum $DST/build/bin/llama-perplexity $DST/build/bin/libllama.so
A1=$(sha256sum $SRC/build/bin/llama-perplexity | cut -d" " -f1)
A2=$(sha256sum $DST/build/bin/llama-perplexity | cut -d" " -f1)
B1=$(sha256sum $SRC/build/bin/libllama.so | cut -d" " -f1)
B2=$(sha256sum $DST/build/bin/libllama.so | cut -d" " -f1)
if [ "$A1" = "$A2" ] && [ "$B1" = "$B2" ]; then
  echo "PHASE A: MATCH (object reuse + relink reproduces the landed engine byte for byte)"
else
  echo "PHASE A: DIFFER"
  echo "  llama-perplexity landed=$A1 ob1b=$A2"
  echo "  libllama.so      landed=$B1 ob1b=$B2"
  echo "  sizes:"; ls -l $SRC/build/bin/libllama.so $DST/build/bin/libllama.so
  echo "  --- does the binary embed its own source path? (the usual benign cause) ---"
  echo "  landed hits: $(strings $SRC/build/bin/libllama.so | grep -c "rs053/llama.cpp" || true)"
  echo "  ob1b   hits: $(strings $DST/build/bin/libllama.so | grep -c "ob1b/llama.cpp" || true)"
fi

echo "=== PHASE B: the one-line K=0 guard fix ==="
echo "--- before ---"
grep -n "OB1_K=%d out of range" $LEASE
# Exact literal replacement with a count assertion. Not sed: the line contains
# "||", and every convenient sed delimiter collides with something in it.
python3 - "$LEASE" <<'PYEOF'
import sys
p = sys.argv[1]
old = 'if (g_K <= 0 || g_K > g_E) ob1_fatal("OB1_K=%d out of range 1..%d", g_K, g_E);'
new = 'if (g_K <  0 || g_K > g_E) ob1_fatal("OB1_K=%d out of range 0..%d", g_K, g_E);'
s = open(p).read()
n = s.count(old)
if n != 1:
    sys.exit("GUARD EDIT ABORTED: expected exactly 1 occurrence, found %d" % n)
open(p, "w").write(s.replace(old, new))
print("guard edit applied: 1 occurrence replaced")
PYEOF
echo "--- after ---"
grep -n "OB1_K=%d out of range" $LEASE
echo "--- diff ---"
cd $DST && git diff --stat && git diff

nice -n 10 make -C $DST/build llama-perplexity -j4 2>&1 | tail -12
echo "--- phase B digests (the binary every OB-1b run uses) ---"
sha256sum $DST/build/bin/llama-perplexity $DST/build/bin/libllama.so
C2=$(sha256sum $DST/build/bin/libllama.so | cut -d" " -f1)
if [ "$B1" = "$C2" ]; then
  echo "PHASE B: libllama.so UNCHANGED after the edit -- the edit did not take, STOP"
else
  echo "PHASE B: libllama.so changed, as the one-line edit requires"
fi

echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== END OB1B BUILD ==="
