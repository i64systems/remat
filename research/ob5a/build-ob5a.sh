#!/bin/sh
# OB-5a stage 2: stand up the ob5a engine build, and prove what separates it
# from the two engines whose output this leg has to reproduce.
#
# WHY THIS IS NOT A PLAIN FRESH BUILD. The landed build tree is configured with
# GGML_CUDA=ON; a from-scratch reconfigure recompiles several hundred nvcc
# translation units for a change of one CPU-side .cpp. This script copies a
# landed build tree into the ob5a worktree, rewrites the absolute source paths
# inside it, lets cmake regenerate its makefiles against the new source root, and
# recompiles ONLY the translation units that actually changed. Same pattern as
# research/ob1b/build-ob1b.sh, and the same soundness argument.
#
# THREE PHASES, TWO OF WHICH ARE CHECKS AND NOT TAUTOLOGICAL:
#
#   PHASE A  ob5a tree, ALL FIVE touched files restored to their c087083 content.
#            .text must equal the LANDED ob1 engine (/root/rs053). This is what
#            licenses reusing the copied object tree at all.
#   PHASE B  + the D3 K=0 guard fix, and nothing else. .text must equal the OB-1b
#            engine (/root/ob1b). This is the stronger check and the one this leg
#            actually needs: the OB-1b engine is the binary that produced every
#            banked identity and route digest the P1 regression is measured
#            against, so reproducing its executable code exactly means the only
#            thing separating the P1 binary from the banked one is phase C.
#   PHASE C  + the OB-5a reserve/commit allocator. .text MUST differ, in both
#            libggml-base (the allocator) and libllama (the hooks), and the
#            differences are named rather than asserted.
#
# A mismatch in phase A or phase B is reported literally and is not worked
# around. There is no retry-until-green.
set -e

RS=/root/rs053/llama.cpp        # landed ob1
OB=/root/ob1b/llama.cpp         # ob1b, the engine that banked the digests
DST=/root/ob5a/llama.cpp        # this leg
OUT=/root/ob5a/verify
RES=/mnt/f/f32/openbob-wt/research-2/research/ob5a
mkdir -p $OUT

echo "=== OB5A BUILD ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "guard_pids: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"

echo "--- the two references ---"
sha256sum $RS/build/bin/libllama.so.0 $RS/build/bin/libggml-base.so.0 $RS/build/bin/llama-perplexity
sha256sum $OB/build/bin/libllama.so.0 $OB/build/bin/libggml-base.so.0 $OB/build/bin/llama-perplexity
echo "--- runpath, the one string that must differ between trees ---"
readelf -d $RS/build/bin/libllama.so.0 | grep -i runpath
readelf -d $OB/build/bin/libllama.so.0 | grep -i runpath

echo "--- restore pristine source in the ob5a tree (all five files this leg touches) ---"
git -C $DST checkout -- src/ob1-lease.cpp src/ob1-lease.h ggml/src/ggml-backend.cpp \
                        src/llama-model.cpp src/llama-model-loader.cpp
git -C $DST status --short
echo "guard line as checked out:"
grep -n "OB1_K=%d out of range" $DST/src/ob1-lease.cpp

echo "--- copy the ob1b build tree ---"
rm -rf $DST/build
cp -a $OB/build $DST/build

echo "--- rewrite absolute source paths in text files only (grep -I skips binaries) ---"
echo "text files referencing old source dir: $(grep -rlI "$OB" $DST/build | wc -l)"
grep -rlI "$OB" $DST/build | xargs sed -i "s|$OB|$DST|g"
echo "remaining after rewrite: $(grep -rlI "$OB" $DST/build | wc -l)"

echo "--- cmake reconfigure against the new source root ---"
# -ffile-prefix-map maps this tree's root back to rs053 for EMBEDDED paths only
# (llama.cpp puts __FILE__ in its assert macros). Without it a recompiled
# translation unit would differ from both references in that string alone, and
# phase A and phase B could not say "byte for byte". It changes no code
# generation. ob1b's build used exactly this flag with its own root, so the flag
# text in the copied flags.make is already correct after the sed above; passing
# it again keeps the cache consistent instead of silently dropping it.
cmake -S $DST -B $DST/build -DCMAKE_CXX_FLAGS="-ffile-prefix-map=$DST=$RS" \
    > /root/ob5a/cmake-reconf.log 2>&1 || {
  echo "CMAKE RECONFIGURE FAILED, log verbatim:"; cat /root/ob5a/cmake-reconf.log; exit 1; }
tail -3 /root/ob5a/cmake-reconf.log

echo "--- age the checked-out sources so make does not rebuild the world ---"
find $DST -path $DST/build -prune -o -type f -print | xargs -r touch -d "2020-01-01 00:00:00"
sleep 1
find $DST/build \( -name "*.o" -o -name "*.a" -o -name "*.so" -o -name "*.so.*" \) -print | xargs -r touch
find $DST/build/bin -type f -print | xargs -r touch
sleep 1

echo "--- confirm the tree is now fully up to date (make should have nothing to do) ---"
nice -n 10 make -C $DST/build llama-perplexity -j4 2>&1 | tail -4

snap() {   # snap <label>
  L=$1
  for n in libllama.so.0 libggml-base.so.0 libllama-perplexity-impl.so llama-perplexity; do
    f=$DST/build/bin/$n
    [ -f "$f" ] || continue
    objcopy -O binary --only-section=.text "$f" $OUT/$L.$n.text
    printf "%-8s %-28s .text %9d bytes  %s\n" "$L" "$n" \
      "$(stat -c %s $OUT/$L.$n.text)" "$(sha256sum $OUT/$L.$n.text | cut -d' ' -f1)"
  done
}
refsnap() { # refsnap <label> <tree>
  L=$1; T=$2
  for n in libllama.so.0 libggml-base.so.0 libllama-perplexity-impl.so llama-perplexity; do
    f=$T/build/bin/$n
    [ -f "$f" ] || continue
    objcopy -O binary --only-section=.text "$f" $OUT/$L.$n.text
    printf "%-8s %-28s .text %9d bytes  %s\n" "$L" "$n" \
      "$(stat -c %s $OUT/$L.$n.text)" "$(sha256sum $OUT/$L.$n.text | cut -d' ' -f1)"
  done
}

echo "=== REFERENCE .text DIGESTS ==="
refsnap landed $RS
refsnap ob1b   $OB

echo "=== PHASE A: pristine source, must reproduce the LANDED ob1 engine ==="
touch $DST/src/ob1-lease.cpp $DST/ggml/src/ggml-backend.cpp
nice -n 10 make -C $DST/build llama-perplexity -j4 > $OUT/makeA.log 2>&1 || {
  echo "PHASE A BUILD FAILED, last 40 lines verbatim:"; tail -40 $OUT/makeA.log; exit 1; }
tail -3 $OUT/makeA.log
snap phaseA

echo "=== PHASE B: + the D3 K=0 guard fix, and nothing else ==="
python3 - "$DST/src/ob1-lease.cpp" <<'PYEOF'
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
grep -n "OB1_K=%d out of range" $DST/src/ob1-lease.cpp
nice -n 10 make -C $DST/build llama-perplexity -j4 > $OUT/makeB.log 2>&1 || {
  echo "PHASE B BUILD FAILED, last 40 lines verbatim:"; tail -40 $OUT/makeB.log; exit 1; }
tail -3 $OUT/makeB.log
snap phaseB

echo "=== PHASE C: + the OB-5a reserve/commit allocator ==="
python3 $RES/apply_alloc.py
python3 $RES/apply_lease.py
echo "--- diff stat against ob1b ---"
git -C $DST diff --stat
nice -n 10 make -C $DST/build llama-perplexity -j4 > $OUT/makeC.log 2>&1 || {
  echo "PHASE C BUILD FAILED, last 60 lines verbatim:"; tail -60 $OUT/makeC.log; exit 1; }
echo "--- compiler warnings from the changed translation units ---"
grep -iE "warning|error" $OUT/makeC.log | head -30 || echo "(none)"
tail -3 $OUT/makeC.log
snap phaseC

echo "=== VERDICTS ==="
v() { # v <label> <ref> <lib> <expect: SAME|DIFFER>
  A=$(sha256sum $OUT/$2.$3.text 2>/dev/null | cut -d' ' -f1)
  B=$(sha256sum $OUT/$1.$3.text 2>/dev/null | cut -d' ' -f1)
  if [ -z "$A" ] || [ -z "$B" ]; then echo "  $1 vs $2  $3: MISSING"; return; fi
  if [ "$A" = "$B" ]; then R=SAME; else R=DIFFER; fi
  if [ "$R" = "$4" ]; then S="as required"; else S="*** NOT AS REQUIRED (expected $4) ***"; fi
  printf "  %-7s vs %-7s %-28s %-7s %s\n" "$1" "$2" "$3" "$R" "$S"
  if [ "$R" = "DIFFER" ]; then
    echo "      differing bytes: $(cmp -l $OUT/$2.$3.text $OUT/$1.$3.text 2>/dev/null | wc -l)"
  fi
}
echo "A) phase A must reproduce the LANDED ob1 engine exactly:"
v phaseA landed libllama.so.0             SAME
v phaseA landed libggml-base.so.0         SAME
v phaseA landed libllama-perplexity-impl.so SAME
v phaseA landed llama-perplexity          SAME
echo "B) phase B must reproduce the OB-1b engine exactly (the digest-banking binary):"
v phaseB ob1b   libllama.so.0             SAME
v phaseB ob1b   libggml-base.so.0         SAME
v phaseB ob1b   libllama-perplexity-impl.so SAME
v phaseB ob1b   llama-perplexity          SAME
echo "C) phase C must DIFFER from phase B, in the two libraries the patch touches:"
v phaseC phaseB libllama.so.0             DIFFER
v phaseC phaseB libggml-base.so.0         DIFFER
echo "   and the executable and the perplexity impl, which the patch does not touch:"
v phaseC phaseB libllama-perplexity-impl.so SAME
v phaseC phaseB llama-perplexity          SAME

echo "=== the new symbols must actually be exported from libggml-base ==="
nm -D --defined-only $DST/build/bin/libggml-base.so.0 | grep -E "ggml_reserve|ggml_backend_cpu_reserve" || \
  echo "*** NO OB5A SYMBOLS EXPORTED -- the allocator did not reach the library ***"
echo "=== and referenced from libllama ==="
nm -D --undefined-only $DST/build/bin/libllama.so.0 | grep -E "ggml_reserve|ggml_backend_cpu_reserve" || \
  echo "*** libllama DOES NOT REFERENCE the allocator ***"

echo "--- the running binary is phase C; final digests ---"
sha256sum $DST/build/bin/llama-perplexity $DST/build/bin/libllama.so.0 \
          $DST/build/bin/libggml-base.so.0 $DST/build/bin/libggml-cpu.so.0 \
          $DST/build/bin/libllama-perplexity-impl.so
echo "--- source digests of the five touched files ---"
sha256sum $DST/src/ob1-lease.cpp $DST/src/ob1-lease.h $DST/ggml/src/ggml-backend.cpp \
          $DST/src/llama-model.cpp $DST/src/llama-model-loader.cpp
echo "--- box state that bears on the allocator ---"
echo "vm.overcommit_memory=$(cat /proc/sys/vm/overcommit_memory)"
echo "vm.overcommit_ratio=$(cat /proc/sys/vm/overcommit_ratio)"
echo "vm.max_map_count=$(cat /proc/sys/vm/max_map_count)"
echo "page_size=$(getconf PAGESIZE)"
echo "transparent_hugepage=$(cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null || echo unavailable)"
echo "guard_pids_after: $(ps -o pid= -p 654 | wc -l) openbob, $(ps -o pid= -p 489 | wc -l) searxng"
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== END OB5A BUILD ==="
