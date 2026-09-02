#!/bin/sh
# House script-to-file law: every file this leg commits must be LF-only ASCII.
# Prints the CR count and any non-ASCII byte count for each committed file.
R=/mnt/f/f32/openbob-wt/research-2/research
for f in "$R/OB5B-S1-RUNLOG-1.txt" "$R"/ob5b1/*; do
  [ -f "$f" ] || continue
  CR=$(tr -dc '\r' < "$f" | wc -c)
  NA=$(tr -d '\000-\177' < "$f" | wc -c)
  printf "  CR %-4s non-ascii %-4s  %s\n" "$CR" "$NA" "$f"
done
echo "--- any em dash (U+2014) or en dash (U+2013) in the runlog? ---"
# the patterns are written as hex escapes so THIS file stays pure ASCII too
LC_ALL=C grep -c "$(printf '\xe2\x80\x94\|\xe2\x80\x93')" \
  "$R/OB5B-S1-RUNLOG-1.txt" 2>/dev/null || echo "0 (no match)"
echo "--- runlog size ---"
wc -l -c "$R/OB5B-S1-RUNLOG-1.txt"
