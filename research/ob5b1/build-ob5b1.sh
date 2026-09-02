#!/bin/sh
# OB-5b S1 gate 1: stand up the ob5b1 engine and the generation entry point.
#
# LINEAGE, STATED SO THE REUSE IS AUDITABLE. The prompt binds this leg to the
# OB-5a allocator worktree lineage. The ob5a BRANCH head is c087083; the
# allocator itself lives as UNCOMMITTED working-tree state in /root/ob5a/
# llama.cpp (OB5A-ALLOC-1 section 9.5, finding F-B3-4: "pinned is not the same
# as committed"). A worktree taken from ob5a head therefore does NOT carry the
# allocator, and this script reproduces it the only way that is byte-provable:
# it COPIES the five modified source files out of /root/ob5a/llama.cpp and
# verifies each against the digest OB5A's own research/ob5a/BUILD-1.txt banked.
# It never writes into a sibling worktree.
#
# It then reuses the ob5a build tree by the same argument research/ob5a/
# build-ob5a.sh makes for reusing the ob1b tree, and PROVES the reuse by
# comparing .text sections against /root/ob5a's own binaries. .text and not the
# whole file, because RUNPATH carries the build tree's absolute path and must
# differ between two trees; that is the one difference this comparison is
# designed to tolerate and it is printed rather than hidden.
#
# Finally it compiles ob5b1-gen against the public llama.h C API only. It does
# NOT touch any CMakeLists.txt, so the engine build this leg verifies is the
# engine build this leg runs.
set -e

OB5A=/root/ob5a/llama.cpp
RS=/root/rs053/llama.cpp
DST=/root/ob5b1/llama.cpp
SRC=/mnt/f/f32/openbob-wt/research-2/research/ob5b1
OUT=/root/ob5b1/verify
mkdir -p "$OUT"

echo "=== OB5B1 BUILD ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
free -m
echo ""
echo "--- the ob5a tree this leg descends from (read only) ---"
git -C "$OB5A" branch --show-current
git -C "$OB5A" log --oneline -1
git -C "$OB5A" status --porcelain
echo ""

echo "--- create the ob5b1 worktree at ob5a head ---"
if [ -d "$DST" ]; then
  echo "(worktree already present; reusing)"
else
  git -C "$OB5A" worktree add "$DST" -b ob5b1 ob5a
fi
git -C "$DST" branch --show-current
git -C "$DST" log --oneline -1
echo ""

echo "--- copy the five allocator source files out of ob5a and verify each ---"
for f in src/ob1-lease.cpp src/ob1-lease.h ggml/src/ggml-backend.cpp \
         src/llama-model.cpp src/llama-model-loader.cpp; do
  cp "$OB5A/$f" "$DST/$f"
done
sha256sum "$DST/src/ob1-lease.cpp" "$DST/src/ob1-lease.h" \
          "$DST/ggml/src/ggml-backend.cpp" "$DST/src/llama-model.cpp" \
          "$DST/src/llama-model-loader.cpp"
echo "the digests research/ob5a/BUILD-1.txt banked for these five files:"
grep -A6 "source digests of the five touched files" \
  /mnt/f/f32/openbob-wt/research-2/research/ob5a/BUILD-1.txt | tail -5
echo ""
echo "--- verdict on the five source files ---"
FAIL=0
verify_src() {  # verify_src <path-in-dst> <expected-sha256>
  G=$(sha256sum "$DST/$1" | cut -d' ' -f1)
  if [ "$G" = "$2" ]; then
    printf "  %-32s MATCH  %s\n" "$1" "$G"
  else
    printf "  %-32s *** MISMATCH ***\n    got  %s\n    want %s\n" "$1" "$G" "$2"
    FAIL=1
  fi
}
verify_src src/ob1-lease.cpp          ab1ee51d5905bf1a949bda0cca4ef63926493159338af314045b1fb566676018
verify_src src/ob1-lease.h            087a045dddc35a4618b6580c406b2b35b32b93dd46e71e2a3573fe3ed9b34172
verify_src ggml/src/ggml-backend.cpp  be278cef9427d165ce2632683d99ee006b504f7795948eabe8d2de3779655141
verify_src src/llama-model.cpp        9f9dcdaec300c3c87a07de8cac359cf0b5ff6ca33c53445f612245bb5dc16efb
verify_src src/llama-model-loader.cpp 28ea244454bb29ac66b39074d534034f7fa655878570729f00fdff09e596ad76
if [ "$FAIL" != "0" ]; then
  echo "SOURCE LINEAGE BROKEN -- STOPPING. The ob5b1 engine would not be the ob5a engine."
  exit 20
fi
echo "  five of five MATCH"
echo ""
echo "--- diffstat of the ob5b1 worktree against its own base commit ---"
git -C "$DST" diff --stat
echo ""

echo "--- copy the ob5a build tree and rewrite its absolute source paths ---"
rm -rf "$DST/build"
cp -a "$OB5A/build" "$DST/build"
echo "text files referencing the ob5a source dir: $(grep -rlI "$OB5A" "$DST/build" | wc -l)"
grep -rlI "$OB5A" "$DST/build" | xargs -r sed -i "s|$OB5A|$DST|g"
echo "remaining after rewrite: $(grep -rlI "$OB5A" "$DST/build" | wc -l)"
echo ""

echo "--- cmake reconfigure against the new source root ---"
# Same -ffile-prefix-map argument research/ob5a/build-ob5a.sh makes: llama.cpp
# puts __FILE__ into its assert macros, so without mapping this tree's root back
# to the rs053 root a recompiled translation unit would differ from the ob5a
# reference in that string alone and the .text comparison below could not say
# "byte for byte". It changes no code generation.
cmake -S "$DST" -B "$DST/build" -DCMAKE_CXX_FLAGS="-ffile-prefix-map=$DST=$RS" \
  > /root/ob5b1/cmake-reconf.log 2>&1 || {
    echo "CMAKE RECONFIGURE FAILED, log verbatim:"; cat /root/ob5b1/cmake-reconf.log; exit 21; }
tail -3 /root/ob5b1/cmake-reconf.log
echo ""

echo "--- age the sources so make does not rebuild the world ---"
find "$DST" -path "$DST/build" -prune -o -type f -print | xargs -r touch -d "2020-01-01 00:00:00"
sleep 1
find "$DST/build" \( -name "*.o" -o -name "*.a" -o -name "*.so" -o -name "*.so.*" \) -print | xargs -r touch
find "$DST/build/bin" -type f -print | xargs -r touch
sleep 1
echo ""

echo "--- make llama-perplexity (should have nothing to do) ---"
nice -n 10 make -C "$DST/build" llama-perplexity -j4 > "$OUT/make.log" 2>&1 || {
  echo "BUILD FAILED, last 40 lines verbatim:"; tail -40 "$OUT/make.log"; exit 22; }
tail -6 "$OUT/make.log"
echo ""

snap() {  # snap <label> <tree>
  L=$1; T=$2
  for n in libllama.so.0 libggml-base.so.0 libggml-cpu.so.0 libggml.so.0 \
           libllama-perplexity-impl.so llama-perplexity; do
    f=$T/build/bin/$n
    [ -f "$f" ] || continue
    objcopy -O binary --only-section=.text "$f" "$OUT/$L.$n.text"
    printf "  %-8s %-30s .text %9d bytes  %s\n" "$L" "$n" \
      "$(stat -c %s "$OUT/$L.$n.text")" "$(sha256sum "$OUT/$L.$n.text" | cut -d' ' -f1)"
  done
}
echo "=== .text DIGESTS ==="
snap ob5a  "$OB5A"
snap ob5b1 "$DST"
echo ""
echo "=== VERDICT: ob5b1 must reproduce the ob5a engine .text EXACTLY ==="
V=0
v() {
  A=$(sha256sum "$OUT/ob5a.$1.text" 2>/dev/null | cut -d' ' -f1)
  B=$(sha256sum "$OUT/ob5b1.$1.text" 2>/dev/null | cut -d' ' -f1)
  if [ -z "$A" ] || [ -z "$B" ]; then printf "  %-30s MISSING\n" "$1"; V=1; return; fi
  if [ "$A" = "$B" ]; then printf "  %-30s SAME    as required\n" "$1";
  else printf "  %-30s *** DIFFER -- NOT AS REQUIRED ***\n" "$1"; V=1;
       echo "      differing bytes: $(cmp -l "$OUT/ob5a.$1.text" "$OUT/ob5b1.$1.text" 2>/dev/null | wc -l)"; fi
}
v libllama.so.0
v libggml-base.so.0
v libggml-cpu.so.0
v libggml.so.0
v libllama-perplexity-impl.so
v llama-perplexity
if [ "$V" != "0" ]; then
  echo "ENGINE LINEAGE NOT REPRODUCED -- STOPPING."
  exit 23
fi
echo ""

echo "=== whole-file digests, ob5a reference then ob5b1 ==="
echo "(RUNPATH carries the build tree's absolute path, so whole-file digests are"
echo " expected to differ for anything relinked in this tree; .text above is the"
echo " comparison that decides, and it passed.)"
sha256sum "$OB5A/build/bin/llama-perplexity" "$OB5A/build/bin/libllama.so.0" \
          "$OB5A/build/bin/libggml-base.so.0" "$OB5A/build/bin/libggml-cpu.so.0"
sha256sum "$DST/build/bin/llama-perplexity" "$DST/build/bin/libllama.so.0" \
          "$DST/build/bin/libggml-base.so.0" "$DST/build/bin/libggml-cpu.so.0"
echo "--- RUNPATH of each ---"
readelf -d "$OB5A/build/bin/libllama.so.0" | grep -i runpath || echo "(none)"
readelf -d "$DST/build/bin/libllama.so.0"  | grep -i runpath || echo "(none)"
echo ""

echo "=== the allocator symbols must be present in THIS tree's libggml-base ==="
nm -D --defined-only "$DST/build/bin/libggml-base.so.0" | grep -E "ggml_reserve|ggml_backend_cpu_reserve" || {
  echo "*** NO OB5A SYMBOLS EXPORTED ***"; exit 24; }
echo "--- and referenced from THIS tree's libllama ---"
nm -D --undefined-only "$DST/build/bin/libllama.so.0" | grep -E "ggml_reserve|ggml_backend_cpu_reserve" || {
  echo "*** libllama DOES NOT REFERENCE the allocator ***"; exit 25; }
echo ""

echo "=== compile the generation entry point (no CMakeLists touched) ==="
tr -d '\r' < "$SRC/ob5b1-gen.cpp" > "$DST/ob5b1-gen.cpp"
sha256sum "$DST/ob5b1-gen.cpp"
g++ --version | head -1
set -x
nice -n 10 g++ -O2 -std=c++17 -Wall -Wextra \
  -I "$DST/include" -I "$DST/ggml/include" \
  -o "$DST/build/bin/ob5b1-gen" "$DST/ob5b1-gen.cpp" \
  -L "$DST/build/bin" -lllama -lggml-base \
  -Wl,-rpath,"$DST/build/bin"
set +x
sha256sum "$DST/build/bin/ob5b1-gen"
echo "--- ldd: which library files this binary actually loads ---"
LD_LIBRARY_PATH="$DST/build/bin" ldd "$DST/build/bin/ob5b1-gen"
echo ""

echo "--- box state that bears on the allocator ---"
echo "vm.overcommit_memory=$(cat /proc/sys/vm/overcommit_memory)"
echo "vm.overcommit_ratio=$(cat /proc/sys/vm/overcommit_ratio)"
echo "vm.max_map_count=$(cat /proc/sys/vm/max_map_count)"
echo "page_size=$(getconf PAGESIZE)"
echo "transparent_hugepage=$(cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null || echo unavailable)"
echo "guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== END OB5B1 BUILD ==="
