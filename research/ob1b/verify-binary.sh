#!/bin/sh
# OB-1b: prove what actually separates the ob1b engine from the landed
# ob1 engine.
#
# build-ob1b.sh reported phase A (pristine source recompiled in the ob1b tree)
# as DIFFERING from the landed libllama.so by whole-file sha256. That is expected
# and benign: the linker writes the library's own search path into the file, and
# the ob1b tree lives at a different path. This script settles it properly by
# comparing the EXECUTABLE CODE rather than the whole file.
#
#   landed   = /root/rs053/llama.cpp  branch ob1,  head c087083, as landed
#   phase A  = ob1b tree, src/ob1-lease.cpp PRISTINE  -> .text must equal landed
#   phase B  = ob1b tree, src/ob1-lease.cpp PATCHED   -> .text must differ, and
#              differ only in the one comparison the guard line compiles to
set -e
SRC=/root/rs053/llama.cpp
DST=/root/ob1b/llama.cpp
LEASE=$DST/src/ob1-lease.cpp
OUT=/root/ob1b/verify
mkdir -p $OUT

echo "=== OB1B BINARY VERIFICATION ==="
echo "utc_start $(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "--- runpath, the one string that must differ ---"
readelf -d $SRC/build/bin/libllama.so.0 | grep -i runpath
readelf -d $DST/build/bin/libllama.so.0 | grep -i runpath

echo "--- rebuild phase A (pristine source) and keep it ---"
git -C $DST checkout -- src/ob1-lease.cpp
grep -n "OB1_K=%d out of range" $LEASE
touch $LEASE
nice -n 10 make -C $DST/build llama-perplexity -j4 > $OUT/makeA.log 2>&1
cp $DST/build/bin/libllama.so.0 $OUT/phaseA.so
sha256sum $OUT/phaseA.so

echo "--- rebuild phase B (patched source) and keep it ---"
python3 - "$LEASE" <<'PYEOF'
import sys
p = sys.argv[1]
old = 'if (g_K <= 0 || g_K > g_E) ob1_fatal("OB1_K=%d out of range 1..%d", g_K, g_E);'
new = 'if (g_K <  0 || g_K > g_E) ob1_fatal("OB1_K=%d out of range 0..%d", g_K, g_E);'
s = open(p).read()
assert s.count(old) == 1, "expected exactly one guard line"
open(p, "w").write(s.replace(old, new))
print("guard edit applied")
PYEOF
grep -n "OB1_K=%d out of range" $LEASE
nice -n 10 make -C $DST/build llama-perplexity -j4 > $OUT/makeB.log 2>&1
cp $DST/build/bin/libllama.so.0 $OUT/phaseB.so
sha256sum $OUT/phaseB.so

echo "--- extract .text from all three ---"
for n in landed phaseA phaseB; do
  case $n in
    landed) f=$SRC/build/bin/libllama.so.0 ;;
    phaseA) f=$OUT/phaseA.so ;;
    phaseB) f=$OUT/phaseB.so ;;
  esac
  objcopy -O binary --only-section=.text "$f" $OUT/$n.text
  printf "%-8s .text %12d bytes  %s\n" "$n" "$(stat -c %s $OUT/$n.text)" "$(sha256sum $OUT/$n.text | cut -d' ' -f1)"
done

echo "--- verdicts ---"
TL=$(sha256sum $OUT/landed.text | cut -d" " -f1)
TA=$(sha256sum $OUT/phaseA.text | cut -d" " -f1)
TB=$(sha256sum $OUT/phaseB.text | cut -d" " -f1)
if [ "$TL" = "$TA" ]; then
  echo "A) landed .text == phaseA .text : MATCH -- the ob1b tree reproduces the landed"
  echo "   engine's executable code exactly; the whole-file digest differs only in"
  echo "   metadata (the RUNPATH above)."
else
  echo "A) landed .text != phaseA .text : DIFFER"
  cmp -l $OUT/landed.text $OUT/phaseA.text | wc -l | sed "s/^/   differing bytes: /"
fi
if [ "$TB" = "$TA" ]; then
  echo "B) phaseA .text == phaseB .text : MATCH -- the guard edit did NOT reach the code, STOP"
else
  echo "B) phaseA .text != phaseB .text : DIFFER, as the guard edit requires"
  echo "   differing bytes between pristine and patched .text:"
  cmp -l $OUT/phaseA.text $OUT/phaseB.text | wc -l | sed "s/^/   /"
  echo "   first differing byte offsets:"
  cmp -l $OUT/phaseA.text $OUT/phaseB.text | head -8
fi

echo "--- the running binary is phase B (patched); confirm ---"
sha256sum $DST/build/bin/libllama.so.0 $DST/build/bin/llama-perplexity
grep -n "OB1_K=%d out of range" $LEASE
echo "utc_end $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== END VERIFICATION ==="
