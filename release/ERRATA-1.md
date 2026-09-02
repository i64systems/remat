# ERRATA-1: corrections of record to the frozen white paper
# The white paper is frozen as filed with the provisional
# application and is not edited; corrections land here. The
# receipts govern wherever they differ from a summary sentence.
# Pure ASCII.

1. K=16 p95 RANGE. Section 4's table prints 1.25-1.29x for K=16.
   The OB1 receipt also banked a K=16 cold-cache variant at
   1.5408x (research/OB1-EXPOSURE-1.md). The row should be read as
   1.25-1.54x with the cold-cache run included.

2. [TBD-A]. Section 8 references token-level tail latency measured
   in "[TBD-A]", a drafting placeholder. The measurement is the
   per-token interval series in research/OB5B-S1-1.md section 8,
   which ships here. Chunk-level p95 is what the exposure receipts
   themselves bank.

3. INTERACTIVE DECODE. Section 5 says interactive decode "is
   measured, not extrapolated, in the serving design's first
   slice." At the paper's freeze that measurement was in flight;
   it is now complete and ships here: 0.257894810 to 0.531246395
   tok/s decode across sixteen runs at four residency schedules
   (research/OB5B-S1-1.md). The composed policy-stack figure
   (3.0-4.6 tok/s) is a PROJECTION that ships nowhere in this
   tree; this sentence is its only appearance and its label.

4. COMPRESSED-VS-RAW READ COST. The comparison of 1.2072x against
   1.5139x crosses legs and thread regimes; the claims table marks
   it "a reading, not a bar" (research/claims/CLAIMS-OB5B-1.txt),
   and that caveat rides the paper's section 6 sentence wherever
   it is quoted.

5. AN OVERBROAD SENTENCE. "Compression must come from structure or
   generators, never order-0 statistics" generalizes from two
   model formats. The measured form: in both formats tested,
   entropy coding recovered under 2 percent beyond the format's
   own packing; the structural route is where the measured
   headroom lives.

6. OB5A BAR P4d. The preregistered bar text reads "decommits = 6 x
   lease_events" (164418); measured decommits were 163920, and the
   difference is exactly the 498 slices still leased at process
   exit. The receipt discloses this in its own finding F-B3-2 and
   records the bar text as defective. The accurate summary is:
   fourteen OB-5a bars pass as written; P4d passes under corrected
   accounting, disclosed in the receipt.

7. BOBMOE0 "EVERY LAYER BELOW 0.60". The result receipt and the
   training report state every layer's P_half is below the 0.60
   bar while the receipt's own table prints a maximum of
   0.616665066564260123 (layer 11, confirmed by the shipped
   route-statistics CSV). The subordinate every-layer sentence is
   FALSE; the preregistered kill evaluates the LAYER MEAN
   (0.551962400593637992), which is below the bar, so the verdict
   itself is unchanged. The receipt is not edited; this erratum is
   the correction of record.

8. "8x ADDRESSABLE CAPACITY". Summaries describe the MoE twin as
   8x. Eight is the EXPERT COUNT. The FFN parameter ratio against
   the active-matched dense twin is 4x (8 x 1,572,864 = 12,582,912
   MoE FFN parameters vs 3,145,728 dense), and the two active
   experts together equal the dense FFN. Read "8x" as expert
   count, never as a parameter or capacity multiplier.

9. SCOPE OF THE ENTROPY CONCLUSION. Erratum 5's narrowing applies
   equally to the training report's broader wording ("trained
   ternary converges to maximum entropy", "never budget order-0
   skew"): the measured basis is one scale, one corpus, two
   formats. The measured form in erratum 5 is the citable claim.

10. THE SAME K=16 BLUR INSIDE THE OB1 RECEIPT ITSELF. Erratum 1
   corrected the frozen paper's K=16 p95 row; the receipt
   research/OB1-EXPOSURE-1.md commits the identical blur in its own
   summary (its "range 1.2536-1.2907x ... including the
   cold-page-cache variant" sentence, and the headline table),
   while its own section 3 prints that variant at 1.5408x
   (24691.8 / 16025.8). The corrected reading of the receipt's
   summary is 1.2536-1.5408x. The receipt is not edited; this is
   the correction of record. No verdict moves (the bar is 3.0x).

11. BAR P4a'S DISPOSITION. The OB5A prereg defines bars P4a-P4d;
   the receipt's pass list does not name P4a separately. Per the
   prereg's own text, P4c is the mechanism that gives P4a force
   ("how P4a is prevented from being a rolling hash of nothing"):
   P4a's disposition is COVERED BY P4c's pass, recorded here so no
   bar label vanishes silently.

12. INSTRUMENT DIGESTS AFTER VOICE NORMALIZATION. Receipts and
   runlogs pin instruments at their AS-RUN digests; the shipped
   copies are voice-normalized and hash differently.
   release/DIGEST-MAP-1.md is the full declaration: 39 files, 40
   differing as-run pins, each row citing the evidence line that
   pins it. A PRIOR ISSUE OF THE MAP WAS FALSE - its generator
   paired digests with filenames across adjacent lines of
   sha256sum-format evidence, rotating most rows to neighboring
   files and omitting real divergences. The reissued map is
   line-scoped and path-matched and supersedes it entirely.

13. OB4 RECEIPT'S BUDGET SENTENCE. research/OB4-REMAT-1.md line 33
   prints "PASS, 1.62-1.38x of budget spent", which does not
   derive from the receipt's own literals: the measured spend is
   1.6878-1.8310x of baseline (its lines 78-81), leaving
   1.169-1.312x of the 3.0x budget unspent (39.0-43.7 percent,
   not "40-45"). The verdict is unaffected (bar 3.0x, worst
   1.8310x). The receipt is not edited; this is the correction of
   record.

14. THE PAPER'S PROGRAM-WIDE P95 SPAN. The frozen paper's
   "measured p95 spans 1.25x to 1.80x" understates one limb: OB4's
   own-control decode-cost reading is 1.8310x (bar 3.0x, passed).
   The corrected program-wide span is 1.25x to 1.84x.
