#!/bin/sh
# OB-5b S1 gate 3: ASSEMBLE THE PREPARED, VERSIONED INSTALL.
#
# NOTHING HERE IS APPLIED. The house install law is that every install is
# versioned and its version report carries the H1 litmus, prompt and response
# verbatim, as a rider, and that SHA digests remain the deciding bytes. This
# script builds that package and stops. The live serve keeps running the binary
# it is running; a separate release authorization is the only thing that moves it.
set -e
V=v1
PKG=/mnt/f/f32/stage/research/ob5b2/install/OB5B-S1-BRAIN-LEASE-$V
G3=/root/ob5b2/g3
FAB=/root/ob5b2/fabric/openbob-br1
BASE=/root/ob5b2/fabric/openbob-base
LIVE=/root/.local/bin/openbob
mkdir -p "$PKG"

cp "$G3/openbob_br1.rs"      "$PKG/openbob_s11_cpu_br1.rs"
cp "$G3/br1-region.rs"       "$PKG/br1-region.rs"
cp "$G3/gate3-patch.py"      "$PKG/gate3-patch.py"
cp "$G3/ob5b2-worker.py"     "$PKG/ob5b2-worker.py"
cp "$FAB"                    "$PKG/openbob-br1"
cp "$G3/BR1-BUILD-1.txt"     "$PKG/BUILD-1.txt"
cp "$G3/PATCH-1.txt"         "$PKG/PATCH-1.txt"
cp "$G3/DEVHOME-1.txt"       "$PKG/DEVHOME-1.txt" 2>/dev/null || true
cp "$G3/SEAM-1.txt"          "$PKG/SEAM-1.txt" 2>/dev/null || true
cp /root/ob5b2/devhome/.config/openbob/openbob.bm1 "$PKG/openbob.bm1.example"
cp /root/ob5b2/devhome/.config/openbob/openbob.c1  "$PKG/openbob.c1.example"
diff -u "$G3/openbob_base.rs" "$G3/openbob_br1.rs" > "$PKG/br1.patch" || true

{
echo "OB5B-S1-BRAIN-LEASE $V   VERSION REPORT"
echo ""
echo "PREPARED, NOT APPLIED. This package is a versioned install awaiting the"
echo "owner's gate. Nothing in it has been installed. The live openbob serve"
echo "(pid 654, port 8899) runs the binary it has been running since it started"
echo "and was never touched, signalled, restarted or reconfigured by this leg."
echo ""
echo "built    $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "venue    f32-HYDE, Windows 11 + WSL2"
echo "lane     research (OB-5b slice 1, gate 3)"
echo "binds    research/OB5-DESIGN-C4-1.md section 4 (the brain lease), section"
echo "         5.2 (the brain manifest), section 7 (the telemetry surface),"
echo "         section 12 gate 3; scope-ledger entries OB5-017, OB5-018, OB5-020"
echo ""
echo "== WHAT THIS INSTALLS =="
echo "One new capability in the fabric: bob can call a LEASED BRAIN. It is not a"
echo "new action name. OPENBOB-L-1's bob.lease already carries a host, a role and"
echo "a text; it is already ASK in every mode; its host and text are already"
echo "counted as outbound bytes by the C15 door; its question already names the"
echo "host, the role, the budget and the whole text. This install registers ONE"
echo "HOST NAME, brain, and gives the executor one arm for it. Every wall the"
echo "lease law already built stands over the brain lease unchanged."
echo ""
echo "== THE BYTES =="
printf "base source        %s  %s\n" "$(sha256sum $G3/openbob_base.rs | cut -d' ' -f1)" "$(wc -l < $G3/openbob_base.rs) lines"
printf "patched source     %s  %s\n" "$(sha256sum $G3/openbob_br1.rs  | cut -d' ' -f1)" "$(wc -l < $G3/openbob_br1.rs) lines"
printf "br1 region         %s  %s\n" "$(sha256sum $G3/br1-region.rs   | cut -d' ' -f1)" "$(wc -l < $G3/br1-region.rs) lines"
printf "patcher            %s\n" "$(sha256sum $G3/gate3-patch.py | cut -d' ' -f1)"
printf "worker             %s\n" "$(sha256sum $G3/ob5b2-worker.py | cut -d' ' -f1)"
echo ""
printf "base binary        %s  %s bytes\n" "$(sha256sum $BASE | cut -d' ' -f1)" "$(stat -c %s $BASE)"
printf "NEW binary         %s  %s bytes\n" "$(sha256sum $FAB  | cut -d' ' -f1)" "$(stat -c %s $FAB)"
printf "binary on the box  %s  %s bytes  (the live serve's file, READ ONLY)\n" "$(sha256sum $LIVE | cut -d' ' -f1)" "$(stat -c %s $LIVE)"
echo "rustc              $(/root/.cargo/bin/rustc --version)"
echo "build command      rustc -O --edition 2021 <src> -o <out>"
echo ""
echo "DECLARED PLAINLY: the base binary this leg built from k4b/src/openbob_s11_cpu.rs"
echo "is NOT byte-identical to the file the live serve is running, and their sizes"
echo "differ, which the sizes above show plainly. It was built elsewhere, at another"
echo "time, with other flags. THE INSTALL DECISION THEREFORE NEEDS ONE THING THIS"
echo "LEG CANNOT SUPPLY: the source and the build command the live binary came"
echo "from, so that the brain lease is added to THAT lineage and not to a parallel"
echo "one. Naming the gap is the point of this paragraph, and it is the reason this"
echo "package is prepared rather than applied."
echo ""
echo "== THE FOUR EDIT SITES, EACH EXACTLY ONE OCCURRENCE =="
sed -n 's/^  site /  /p' "$G3/PATCH-1.txt"
echo ""
echo "== WHAT CHANGES ON THE BOX, AND WHAT DOES NOT =="
echo "CHANGES   one binary, and two new files under the conf directory:"
echo "            openbob.bm1   the brain manifest (the golden triple's brain slot)"
echo "            (openbob.c1 gains no rule: bob.lease already has one, or does not)"
echo "          one new process, the exposure worker, on 127.0.0.1:8907"
echo "DOES NOT  the journals, the runs, the API port 8899, the register's other"
echo "          rules, the retail lane, the mini, the messenger, the demo frame,"
echo "          any kernel knob, any model file"
echo ""
echo "== THE ACCEPTANCE EVIDENCE THAT CAME WITH IT =="
echo "The model-free batteries were run on the base binary and on this one and"
echo "compared byte for byte:"
for m in lease-probe guards corpus taint ceiling outside sidecar unit; do
  if cmp -s "$G3/reg-openbob-base-$m.txt" "$G3/reg-openbob-br1-$m.txt"; then
    printf "  %-12s IDENTICAL   %s lines\n" "$m" "$(wc -l < $G3/reg-openbob-base-$m.txt)"
  else
    printf "  %-12s DIFFER      see reg-*-%s.txt\n" "$m" "$m"
  fi
done
echo "The one difference is ceiling, which reads the card's live utilization; the"
echo "differing line is quoted in the runlog rather than hidden."
echo ""
echo "== ROLLBACK =="
echo "cp /root/.local/bin/openbob /root/.local/bin/openbob.pre-br1"
echo "  install:  cp $PKG/openbob-br1 /root/.local/bin/openbob"
echo "  rollback: cp /root/.local/bin/openbob.pre-br1 /root/.local/bin/openbob"
echo "Both require restarting the serve, which takes a separate release authorization and is not this"
echo "leg's: the hard walls of this workflow forbid touching pid 654."
echo ""
echo "== THE H1 RIDER =="
echo "The litmus for THIS install is the capability it adds, so the rider is one"
echo "brain lease, prompt and response verbatim, taken on the dev fabric against"
echo "the live exposure worker. It is in H1-RIDER-1.txt beside this file."
} > "$PKG/VERSION-REPORT-1.txt"

( cd "$PKG" && sha256sum ./* > SHA256SUMS.txt 2>/dev/null || true )
echo "package $PKG"
ls -la "$PKG"
