#!/bin/sh
# OB-1b: after the 120b leg, pick up whatever 20b rows are still
# missing (the K=0 A/A repeat, then K=1 and K=2).
#
# Sequential on purpose. Both legs take the house runlock per run, so running
# them at once would only make this leg compete with itself in a queue already
# shared with four sibling workflows.
echo "### chain-resume: waiting for the 120b leg to finish, $(date -u +%Y-%m-%dT%H:%M:%SZ)"
while pgrep -f "ob1b/runs-120b.sh" > /dev/null 2>&1; do
  sleep 60
done
echo "### chain-resume: 120b leg is gone at $(date -u +%Y-%m-%dT%H:%M:%SZ); resuming the 20b matrix"
sh /mnt/f/f32/openbob-wt/research-2/research/ob1b/runs-knee-resume.sh
echo "### chain-resume: resume returned $? at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
