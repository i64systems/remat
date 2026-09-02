# EVIDENCE-NOTE-1: the evidence layer, what ships and what does
# not. Pure ASCII.

The receipts do not stand alone: the byte layer underneath them
ships beside them. Roughly 280 files, including:

- Every project's RUNLOG (research/ob1 .. ob5b2, rs053): the
  literal command output the receipts quote.
- The checksum inventories and expert/trunk manifests
  (EXPERT-MANIFEST-20B/120B.sha256, TRUNK-MANIFEST-*.sha256,
  SHA256SUMS-1/2/3, MANIFEST-DATA.sha256).
- The acceptance and analysis instruments (accept_*.py,
  analyze_*.py, verify_*.py, sim_*.py, *_arith.py,
  decode_replay.py, route checkers). BE PRECISE ABOUT SCOPE: the
  instruments that run COLD against shipped bytes are
  research/ob5b1/verify-runlog-arith.py and
  verify-runlog2-arith.py. Precisely: verify-runlog2-arith.py READS
  the shipped OB5B-S1-RUNLOG-2.txt (70 checks);
  verify-runlog-arith.py recomputes RUNLOG-1's arithmetic from
  literals transcribed into the instrument itself (49 checks) -
  faithful to the shipped runlog, but a tampered RUNLOG-1 is caught
  by the digest manifest, not by that instrument. The remaining instruments read the raw run
  trees, which do not ship (class 6 below); they are provided for
  method transparency - what was computed and how - and will abort
  on their missing inputs rather than run cold. Two instruments
  report their verdict in printed counters, not exit codes
  (accept_hash.py and analyze_alloc.py exit 0 regardless): read
  the counters.
- The run drivers (run-*.sh, gate*-*.sh, build scripts) for METHOD
  transparency.
- The complete BOBMOE0 training evidence: the frozen
  preregistration (BOBMOE0-PREREG-1.md), stage plans and launches,
  metrics, route-statistics CSVs, environment freezes, and the
  trainer itself (lowint/moe0/train/) - a reader can reproduce the
  stage-1 bit-exactness claim on their own CPU per the prereg.
- The first-leased-answer receipt (research/OB5B-S1-1.md) with
  both runlogs, and the decode-shape probe receipt with its
  prereg - the source of the 10.25 decode-shape exposure and the
  0.26-0.53 tok/s decode band.

WHAT DOES NOT SHIP, DECLARED (nothing is silently absent):

1. THE ENGINE LAYER: the lease/allocator/region/policy engine
   patches and source, the scripts that apply them, and the C
   probe sources (mprotect_cost.c, reserve_probe.c). Receipts
   publish WHAT was measured; the engine is HOW. Consequence,
   stated plainly: the run drivers reference these and will not
   run cold. The cold-verifiable path is the instruments over the
   shipped runlogs, not re-running the engine.
2. POLICY CONSTANTS: the frozen residency-set files and the OB3
   byte-detector. Their derivation scripts ship and their digests
   are pinned in the shipped runlogs and manifests.
3. MODEL WEIGHTS: never redistributed; the expert manifests pin
   every slice digest so a reader with the same public GGUF files
   can verify byte identity themselves.
4. THREE COLLECTION LOGS, withheld for a local account-name leak
   in ls -l output (a privacy scrub, declared not silent). Their
   digests, so they can be checked if later shipped:
   4c65fe2aa70e02c62b7777ee35c2bd782cd936eb5fbddd73c7531ae1f614af8c  lowint/moe0/evidence/leg-launch.txt
   db3f01a4a27a2a02c25dbc6f07ceb65cea084fe60ad09f39c144cf4ac21d0bfb  lowint/moe0/evidence/leg-g1card.txt
   c8359cd49ba1b503d3b1c2c11e9ea05faf5714daaab01673b701fe4d92010c56  lowint/moe0/evidence/leg2.txt
5. INTERNAL COMMIT HASHES cited inside receipts refer to the
   private research repository and do not resolve here. The public
   integrity anchor for this tree is MANIFEST-SHA256.txt.
6. THE RAW RUN TREES: /root/ob1, /root/ob1b, /root/ob5a,
   /root/ob5b1, /root/ob5b2 and the /mnt/f staging areas - route
   logs, identity files, gate-0 JSONs, allocation journals, worker
   logs, the PROMPT-1..4 texts, the acceptance corpora
   (AC-PROSE/AC-CODE/AC-CODE2 and the corpus-*.txt ranking texts,
   digest-pinned in the shipped runlogs), and the final BOBMOE0
   checkpoint and evaluation bytes. The receipts quote them and
   the shipped runlogs digest them; the raw trees themselves stay
   on the lab machines. Anything a shipped receipt or instrument
   references that is not in this tree falls in classes 1-6.

ON THE PRONOUNS IN THE LAB RECORDS: the receipts, runlogs and
evidence legs are the laboratory record verbatim. References in
them to "the owner", "her" and "she" denote the inventor, Harriett
Little, directing the research program.
No other person appears in this repository.

ON INSTRUMENT COMMENTS AND THE DIGEST MAP: the shipped instruments
were normalized for release voice after acceptance - internal
staffing labels removed ("builder 1/2/3", "builder A/B/C" were
internal work-parallelization labels, not people's names) and
comments and presentation strings rewritten to a single
first-person-plural voice with no third-person authorities. The
measurement code is unchanged. Where shipped evidence pins an
instrument's AS-RUN digest, the normalized copy hashes
differently: release/DIGEST-MAP-1.md declares every such pair
(as-run digest as pinned -> shipped digest). Receipts and runlogs
themselves are the lab record verbatim, always. Citations of
private planning documents by filename remain in some comments;
the rule content each citation points at is restated in the
instrument itself.

ON CHRONOLOGY, STATED PLAINLY: this history is fresh by design
(release commits only), so repository history proves nothing about
when preregistrations were written relative to runs. A USPTO
acknowledgement receipt exists for the provisional application
(filed 2026) carrying SHA-512 digests of the filed
document bundle; it is a government record held by the applicant,
it binds the FILED bundle (not this repository's individual
files), and it is not published here. A cold reader should
therefore treat preregistration chronology as UNVERIFIABLE-COLD
and judge the receipts on their internal consistency.
