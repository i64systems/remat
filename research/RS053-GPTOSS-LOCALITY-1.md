# RS053-GPTOSS-LOCALITY-1: PRETRAINED GPT-OSS ROUTER LOCALITY, MEASURED

Lane: research (CUDA/inventor lane), venue hyde, on-machine. Branch
research-2, worktree F:\f32\openbob-wt\research-2. Builder 3 of RS053
(stats + receipt). Bound by research/RS053-GPTOSS-LOCALITY-1-PREREG.md
(commit bc240900c29fcece36c5106e0a7d253b0db7bc7e) and
research/rs053/RUNLOG-1.txt (instrument + runs, commit
4a9a4004e3670969fd65f843adf26008ad19efc2). Pure ASCII, no em dashes.
Every number below is literal command output from this leg's own script
runs, or is quoted verbatim from a cited file. Nothing here renegotiates
the prereg's frozen metric definitions; deviations from HOW they were
computed are named in section 11.

THIS IS A MEASUREMENT, NOT A VERDICT. Per prereg section 0 and section 6:
no kill bar is set anywhere in this document. MoE-0's G2 0.60 P_half
threshold, and the MoE-0 C4 leg's own measured P_half, appear only as
comparison anchors (section 9). Nobody is falsified by this receipt.

## 1. INPUTS

- Prereg: research/RS053-GPTOSS-LOCALITY-1-PREREG.md, frozen fact table
  (L, E, k) and metric definitions M1-M6, section 5.
- Route logs (Builder 2): 11 files under
  /mnt/f/f32/stage/research/rs053/runs/<label>/route.log, digests and A/A
  verdicts in RUNLOG-1.txt section 3. This leg used the "-a" run of each
  of the four prereg configs as the primary source and the "-b" run as an
  independent free check (section 3 below).
- PER_EXPERT_BYTES_PER_LAYER = 13253760 bytes, both models, from
  RUNLOG-1.txt section 5 (read off the GGUF tensor-info section, not
  inferred).

## 2. ANALYSIS METHOD

Two scripts, committed with this receipt:

- research/rs053/rs053-metrics.py: reads one route log, computes M1, M2,
  M3, M4, M6 per the frozen definitions, writes a deterministic JSON
  report (json.dump with sort_keys=True). stdlib + numpy only.
- research/rs053/rs053-cross.py: reads two rs053-metrics.py JSON reports
  for the same model (prose, code) and computes M5.

Run under /root/openbob-train/venv/bin/python, nice 10, on hyde.
Literal:

    Python 3.12.3
    numpy 2.5.2

### 2.1 File-order finding (load-bearing for correctness)

The route logs are NOT one contiguous block per layer. They are grouped
by ubatch: the 20b runs use -ub 2048 against a 65536-token budget (32
ubatches), the 120b runs use -ub 4096 against a 16384-token budget (4
ubatches). For a fixed layer, its rows appear once per ubatch, each
ubatch contributing an increasing block of token_index values, so a
naive reshape(L, budget) assuming one contiguous per-layer block is
WRONG for every run except unit-aa (single ubatch, not part of the
prereg's four configs). rs053-metrics.py builds each layer's sequence
with a boolean mask over the layer column (which preserves file order,
and file order is ubatch-ascending, so the masked token_index values come
out already monotonic), then VERIFIES token_index equals exactly
0..budget-1 in order before trusting it, raising SystemExit otherwise.
This verification passed on all 4 primary route logs and all 4 free-check
route logs (8 total): no ORDER ASSUMPTION VIOLATED, no SHAPE MISMATCH, no
EXPERT ID OUT OF RANGE.

### 2.2 Determinism check (script self-check, step 1 of the task)

rs053-metrics.py run twice on the identical input file
(runs/20b-prose-a/route.log), two separate output JSON files, byte
compared:

    DETCHECK_CMP_RC=0 IDENTICAL

### 2.3 A/B free check (step 2 of the task)

Metrics computed independently from the "-a" and "-b" route log of each
of the four prereg configs (both route logs already byte-identical per
RUNLOG-1.txt section 3, so this checks the metrics pipeline end to end
against known-identical inputs, ignoring only the label/path/sha fields
that differ by construction):

    20b-prose: METRICS_EQUAL=True
    20b-code: METRICS_EQUAL=True
    120b-prose: METRICS_EQUAL=True
    120b-code: METRICS_EQUAL=True

## 3. M1: PER-LAYER EXPERT USAGE, DEAD-EXPERT COUNT, COLLAPSE

Dead-expert threshold: c_l(e) under 1 percent of that layer's traffic
(budget * k), per prereg (E-independent, frozen).

COLLAPSE RULE, THRESHOLD NAMED (deviation D13, section 11): the prereg
states the collapse rule in words only ("P_half near 1.0 ... more than
half the experts dead"), without a numeric "near 1.0". This leg
operationalizes "near 1.0" as P_half(l) >= 0.95, using the prereg's own
quoted field reference point for trained-MoE skew (~0.95, SYNTHESIS-1
s.3, quoted in prereg 5.0) as the number. AND with dead_count(l) > E/2.

    model         collapsed layers (of L)                     max dead_count (of E)   min dead_count
    20b-prose     5 of 24 (17,20,21,22,23)                    22                      0
    20b-code      0 of 24                                     15                      1
    120b-prose    15 of 36 (18,19,20,21,22,23,24,25,26,
                  27,30,32,33,34,35)                          114                     88
    120b-code     0 of 36                                     109                     91

Full per-layer collapse_per_layer and dead_count_per_layer arrays are
banked in the JSON (section 12); recomputed here plainly: 20b-prose's
collapsed set is {17,20,21,22,23} (verified directly against
M1.collapse_per_layer = [F,F,F,F,F,F,F,F,F,F,F,F,F,F,F,F,F,T,F,F,T,T,T,T]
from research/rs053/analysis, 5 True entries at indices 17,20,21,22,23).
120b-prose's collapsed set is {18,19,20,21,22,23,24,25,26,27,30,32,33,34,35}
(15 entries, verified directly against the JSON's collapse_per_layer).
NOTE on 120b: dead_count(l) > E/2=64 is true on EVERY layer of 120b-prose
(min dead_count over all 36 layers is 88, already above 64), so on 120b
the collapse flag is gated entirely by the P_half>=0.95 half of the rule,
not by the dead-expert half -- a fact worth stating plainly since it means
the dead-expert clause is doing no discriminating work at this E and this
threshold, unlike on 20b (E/2=16) where dead_count ranges 0-22 across
layers and does discriminate.

MEASURED OBSERVATION: collapse under this threshold, when it happens,
concentrates in the LATE layers on the prose corpus for both models (20b
tail layers 17 and 20-23; 120b a long late run 18-27 plus 30,32-35). The
code corpus shows ZERO collapsed layers on either model under the same
threshold. This is a per-corpus, per-layer measurement, not a per-model
verdict; see section 10(a) for plain-language reading.

## 4. M2: P_half PER LAYER (layer mean, layer min/max)

Uniform routing = 0.50 for any E. E/2 = 16 (20b), E/2 = 64 (120b).

    config        layer-mean P_half        layer-min P_half (layer)   layer-max P_half (layer)
    20b-prose     8.51591904958089230e-01   6.59317016601562500e-01 (0)   9.75162506103515625e-01 (23)
    20b-code      8.36227258046468136e-01   6.94442749023437500e-01 (0)   9.23419952392578125e-01 (12)
    120b-prose    9.18757120768229130e-01   7.56790161132812500e-01 (0)   9.79736328125000000e-01 (34)
    120b-code     9.14716932508680580e-01   8.19854736328125000e-01 (0)   9.46838378906250000e-01 (23)

All four layer-mean values sit well above uniform (0.50) and above
MoE-0's G2 0.60 kill-threshold anchor (section 9). Every config's layer 0
is its P_half minimum; layer 0 is still 0.66-0.82, itself above uniform.

## 5. M3: WORKING-SET CURVES (W=64, 512, 4096, non-overlapping windows)

DEVIATION D14 (section 11): windows are NON-OVERLAPPING (stride = W), not
stride-1 sliding, per the prereg's own allowance in 5.3 ("stride 1, or a
stated coarser stride ... the instrument-building leg decides and records
its choice"). Chosen for tractability (stride-1 would mean up to 65536
window evaluations per layer); non-overlapping windows still answer the
locality question (bounded per-window working set) at full budget
coverage with n_windows = budget/W windows per layer (1024/128/16 for
20b, 256/32/4 for 120b).

Per-layer distinct-expert count, run-level mean/min/max, plus the layer
that is smallest/largest on average (min layer usually the deepest layer
for prose, matching the M1/M2 late-layer skew above):

    config        W     run_mean_distinct  run_min  run_max  layer_mean_min (layer)   layer_mean_max (layer)
    20b-prose     64    21.267700          6        32       13.232422 (23)           30.719727 (0)
    20b-prose     512   26.552083          13       32       19.062500 (23)           31.976562 (0)
    20b-prose     4096  30.856771          25       32       29.187500 (17)           32.000000 (0)
    20b-code      64    23.531779          9        32       19.704102 (11)           30.549805 (0)
    20b-code      512   30.122721          19       32       27.500000 (11)           31.945312 (0)
    20b-code      4096  31.895833          30       32       31.375000 (11)           32.000000 (0)
    120b-prose    64    49.185547          12       104      25.765625 (34)           80.433594 (0)
    120b-prose    512   85.975694          29       128      51.187500 (34)           123.968750 (0)
    120b-prose    4096  116.291667         94       128      102.500000 (34)          128.000000 (0)
    120b-code     64    54.387912          17       106      44.296875 (12)           78.742188 (0)
    120b-code     512   98.554688          47       128      84.875000 (12)           122.218750 (0)
    120b-code     4096  122.166667         112      128      114.500000 (11)          128.000000 (0)

E for reference: 20b E=32, 120b E=128. So 20b-prose at W=64 touches on
average 21.3 of 32 experts per layer per window (66.5 pct of the full
expert set); 120b-prose at W=64 touches 49.2 of 128 (38.4 pct).

IMPLIED RESIDENT BYTES, per-layer, at W=512 (run_mean_distinct *
13253760): 20b-prose 3.519e8 bytes/layer mean, 20b-code 3.992e8, 120b-
prose 1.140e9, 120b-code 1.306e9 (literal implied_bytes_mean fields, JSON
section 12). Pooled-across-layers (see 5.1 for the operational definition
used): 20b-prose pooled_bytes_mean 8.446e9 at W=512 (24 layers), 120b-
prose pooled_bytes_mean 4.102e10 at W=512 (36 layers).

### 5.1 "Pooled across all layers", operational definition used

Expert ids are LAYER-LOCAL (layer 0's expert 5 and layer 3's expert 5 are
different physical experts). This leg's pooled figure is therefore the
SUM, over layers, of each layer's own distinct-expert count for that
window position -- equivalent to the union of (layer, expert) pairs
touched in the window, since the per-layer id spaces are disjoint by
construction. Stated here because the prereg's wording ("the union of
that layer's or that run's touched-expert set") does not pin the exact
operation; this is the natural reading and is exact, not an
approximation, given the disjointness.

## 6. M4: PHASE STABILITY (W=512, consecutive non-overlapping window pairs)

    config        run-mean Jaccard          layer-min mean (layer)     layer-max mean (layer)
    20b-prose     8.97032519658165217e-01   0.787143 (23)              0.998524 (0)
    20b-code      9.36133793858847874e-01   0.864877 (10)              0.998024 (0)
    120b-prose    7.70133822543823343e-01   0.580005 (35)              0.946588 (0)
    120b-code     7.98622450328307698e-01   0.735260 (16)              0.929870 (0)

High J means the resident expert set barely moves between adjacent
512-token windows. Every config's layer 0 has the HIGHEST stability
(J>=0.93 in all four configs); the deepest layers are the least stable,
most sharply so on 120b-prose (layer 35, J=0.580005 -- the same late-
layer region already flagged as collapse-heavy in section 3, which is
mechanically consistent: a layer with very high usage concentration can
still reshuffle WHICH few experts are hot between windows).

## 7. M5: CROSS-SLICE DIVERGENCE (prose vs code, same model, per layer)

top_n = 32 for both models per prereg 5.5.

    model   J_top32 mean              J_top32 min    J_top32 max    L1 mean                   L1 min       L1 max
    20b     1.00000000000000000e+00  1.0 (all 24)   1.0 (all 24)   1.09297307332356763e+00   0.485619(L0) 1.470390(L21)
    120b    1.86798397125065851e-01  0.066667(L13,21) 0.361702(L0) 1.23726314968532991e+00   0.654785(L0) 1.562317(L35)

20b's J_top32=1.0 on every layer is the DEGENERATE case the prereg named
in advance (5.5): every layer's prose top-32 and code top-32 sets are the
full 32-expert set on both corpora (prose_topset_size_per_layer and
code_topset_size_per_layer are both [32]*24, i.e. every expert saw
nonzero usage on both corpora, every layer) -- J_top32=1.0 here is a
tautology of E=32 with no dead-for-a-corpus expert, NOT evidence that
prose and code route identically. The L1 distance (which does not have
this degeneracy) shows real divergence on 20b: mean 1.093, rising with
depth (min at layer 0, near-max at layer 21).

120b (E=128, top-32 a genuine 25 pct subset) shows LOW top-set overlap
(mean 0.187, as low as 0.067 at layers 13 and 21) and comparable L1
divergence to 20b (mean 1.237, also rising with depth, max at the final
layer 35). Both L1 distance ranges (0 to 2 max possible for two
probability distributions) sit in the 0.5-1.6 band across every layer of
both models -- real, layer-varying divergence between corpora, not noise
at either scale.

## 8. M6: EXPOSURE FRACTION (W=512, same windows as M4)

ALGEBRAIC NOTE: resident_bytes(l,w)/total_bytes(l) = distinct(l,w) *
13253760 / (E * 13253760) = distinct(l,w)/E exactly, because every expert
tensor in this GGUF layout is the same byte size (13253760, RUNLOG-1.txt
section 5). The byte terms cancel; fraction = working-set-fraction. Both
the count-based M3 curve and the byte-based M6 fraction are reported
because the prereg asks for both, but they carry the same information at
this fixed-expert-size scale.

    config        fraction min    fraction median   fraction max   fraction mean            min layer (frac)   max layer (frac)
    20b-prose     0.40625         0.875             1.0            8.29752604166666630e-01  23 (0.595703)      0 (0.999268)
    20b-code      0.59375         0.96875           1.0            9.41335042317708370e-01  11 (0.859375)      0 (0.998291)
    120b-prose    0.226562        0.664062          1.0            6.71685112847222210e-01  34 (0.399902)      0 (0.968506)
    120b-code     0.367188        0.78125           1.0            7.69958496093750000e-01  12 (0.663086)      0 (0.954834)

Reading: LOWER fraction is tighter locality (less of the layer touched
per window). 120b-prose is the TIGHTEST config measured (mean 67.2 pct of
each layer's expert bytes exposed per 512-token window -- even so, the
single worst window over the whole run still reaches 100 pct, i.e. all
128 experts of some layer touched inside one window). 20b-code is the
LEAKIEST (mean 94.1 pct exposed -- 20b's small E=32 leaves little room to
look concentrated in absolute fraction terms even when M2's P_half shows
real skew; see section 10's finding (b) for how to read this alongside
M3's raw counts).

## 9. COMPARISON ANCHOR: MoE-0 (trained house router)

Two anchors, cited separately per the prereg's instruction not to
conflate them:

(a) MoE-0's own G2 kill THRESHOLD (prereg 5.2, quoting BOBMOE0-PREREG-1.md
section 2): P_half < 0.60 (layer mean) is MoE-0's locality kill line. RS053
sets no such bar; the number is printed only for scale.

(b) MoE-0's C4 leg, ACTUAL MEASURED P_half, freshly complete as of this
leg's run: file
/mnt/f/f32/stage/lowint/moe0-collect-b/c4/final-run2/route-stats.csv
(read-only, cited not modified), header confirms
"arm=moe stage=2 ckpt_step=500 ... moe_layers=12 E=8 k=2", literal mean
row:

    mean,-1,4999680,9999360,4999680,5.51962400593637992e-01,2.24592257237796550e-01,9.94974377152421208e-01,0.00000000000000000e+00

i.e. layer-mean P_half = 5.51962400593637992e-01. A/A verified: this leg's
sibling run, final-run1/route-stats.csv, is byte-identical (cmp rc=0,
both sha256 a067fb18a1a6537ed710304eac3abf7e38c33360de1c28e1199d62220ac8964b,
per /mnt/f/f32/stage/lowint/moe0-collect-b/c4/cmp-final.txt, cited not
modified). This is a TRAINED, natively-ternary, 12-layer/E=8/k=2 router
on the enwik8 val split -- a different architecture scale than gpt-oss
entirely, cited as the ONLY other P_half number this house has measured
with the same G2 family of statistic, not as a like-for-like comparison.

    anchor                                    P_half (layer mean)
    MoE-0 G2 kill threshold (not a measurement) 0.60
    MoE-0 C4 leg, trained twin (E=8,k=2,L=12)   0.551962400593637992
    gpt-oss-20b-prose  (E=32,k=4,L=24)          0.851591904958089230
    gpt-oss-20b-code   (E=32,k=4,L=24)          0.836227258046468136
    gpt-oss-120b-prose (E=128,k=4,L=36)         0.918757120768229130
    gpt-oss-120b-code  (E=128,k=4,L=36)         0.914716932508680580

Every gpt-oss config's layer-mean P_half is higher than BOTH MoE-0 anchor
numbers, at roughly 4x the expert count and 2x the top-k of the trained
twin. Stated as a measured fact; section 10 reads what it does and does
not imply.

## 10. FINDINGS, PLAIN REPORT-SPEAK, MEASUREMENT LANGUAGE ONLY

(a) Is routing collapsed or spread? SPREAD, with a late-layer collapse
POCKET on the prose corpus only. Every config's layer-mean P_half
(section 4) sits between 0.836 and 0.919 -- well above uniform (0.50)
and above both MoE-0 anchors (section 9) -- so usage is concentrated on
a minority of experts, consistently. Under this leg's stated 0.95
collapse-threshold convention (section 3, deviation D13), 5 of 20b's 24
layers and 15 of 120b's 36 layers cross into the collapse zone, but ONLY
on the prose corpus (enwik8 XML-ish bytes) and ONLY in the deepest
layers of the stack; the code corpus shows zero collapsed layers on
either model. This reads as skew that is real and strong everywhere, and
in specific deep layers on repetitive/structured input, strong enough to
tip into the prereg's own collapse definition.

(b) Is there windowed locality worth leasing? YES, by the M3/M4 numbers.
At W=512 (a plausible lease-window scale), the mean working set is 26.6
of 32 experts (20b-prose) up to 98.6 of 128 (120b-code) per layer per
window -- i.e. NOT every expert is touched in a typical window, and the
gap is widest exactly where P_half is lowest (early layers) and on the
prose corpus. Phase stability (M4) reinforces this: layer-0 Jaccard
between adjacent windows is >=0.9299 on every config (range 0.9299 to
0.9985), meaning the resident
set at the first layer barely changes window to window. Depth erodes
this though -- each config's least-stable layer falls as low as
J=0.580005 (120b-prose, layer 35) to J=0.864877 (20b-code, layer 10)
across the four configs (section 6), so a fixed lease
would need to be layer-aware (tight, long-lived leases near the input;
shorter or wider ones deep in the stack) rather than one policy for the
whole network.

(c) Do prose and code light different expert sets? YES, clearly on 120b,
LESS DETECTABLY on 20b due to a measurement ceiling. 120b's top-32
overlap between corpora averages 0.187 (as low as 0.067 on two layers)
-- most of each corpus's heavily-used experts are NOT shared with the
other corpus. 20b's top-32 Jaccard reads 1.0 on every layer, but this is
the prereg's own predicted degenerate case (top-32 of a 32-expert model
is the whole set whenever no expert goes fully unused, which is what
happened here) -- it does NOT mean prose and code route identically on
20b. The L1 distance statistic, which does not have this ceiling, shows
real and comparable divergence on BOTH models (means 1.093 and 1.237,
same 0-2 scale), rising with depth on both. Read together: corpus-
sensitive routing is a real, measured property of both models; 20b's
J_top32 number alone would be misleading without the L1 figure beside
it.

(d) The measured free exposure ratio (M6). Mean fraction of a layer's
expert BYTES resident in a typical 512-token window ranges from 0.671
(120b-prose, the TIGHTEST measured config, lowest exposure) to 0.941
(20b-code, the LEAKIEST, highest exposure). Because per-expert byte size
is uniform in this GGUF layout,
this fraction is arithmetically identical to the working-set COUNT
fraction (section 8's algebraic note) -- it is not an independent
signal from M3, just M3 expressed as a share of total layer weight. The
practical reading: even in the best-measured case (120b-prose), a
window still touches roughly two-thirds of a layer's expert weight on
average, and every config has AT LEAST ONE window that touches 100
percent of some layer's experts (fraction max = 1.0 in all four rows).
Locality here is a lean toward a subset, not a hard partition -- the
"called, never loaded whole" framing (N4/A1) would need either a wider W
or a coarser leasing unit than "one gpt-oss layer, one 512-token window"
to get real headroom out of these pretrained routers, at least on these
two corpora at this scale.

## 11. DEVIATIONS, D-SERIES CONTINUED FROM RUNLOG-1.txt (D1-D12)

D13. COLLAPSE THRESHOLD NUMBER CHOSEN. The prereg's collapse rule names
    "P_half near 1.0" without a number. This leg used P_half(l) >= 0.95,
    taken from the prereg's own quoted field reference for trained-MoE
    skew (~0.95, SYNTHESIS-1 s.3, prereg 5.0). A different threshold
    would move the collapsed-layer counts in section 3; the underlying
    dead_count and P_half arrays (which do not depend on this choice) are
    banked in full in the JSON (section 12) so a reader can re-apply a
    different threshold without rerunning the instrument.

D14. M3 WINDOW STRIDE. Non-overlapping windows (stride=W), not stride-1
    sliding, chosen for tractability; explicitly allowed by prereg 5.3
    ("a stated coarser stride ... the instrument-building leg decides").
    n_windows = budget/W per layer; all three W values (64, 512, 4096)
    divide both budgets (65536, 16384) exactly, so no remainder tokens
    were dropped from any window.

D15. "POOLED ACROSS ALL LAYERS" OPERATIONAL DEFINITION. Taken as the sum,
    over layers, of each layer's own per-window distinct-expert count
    (exact, not approximate, because per-layer expert id spaces are
    disjoint by construction -- see section 5.1). The prereg's wording
    did not pin one specific operation.

D16. M6 FRACTION REDUCES TO M3's COUNT FRACTION ALGEBRAICALLY. Because
    every expert tensor in both GGUFs is the same byte size
    (PER_EXPERT_BYTES_PER_LAYER, uniform), M6's bytes-based fraction and
    M3's count-based working-set fraction are the same number by
    construction. Both are still reported (section 8) because the
    prereg specifies both, but this is named so a reader does not read
    them as two independent confirmations of the same locality claim.

D17. ANALYSIS SCOPE. M1-M6 were computed from the "-a" route log of each
    of the four prereg configs; the "-b" route log of each was ALSO run
    through the full pipeline as an end-to-end free check (section 2.3),
    not merely digest-compared. No metric in this receipt was computed
    from unit-aa or 120b-probe (both explicitly out of prereg scope per
    RUNLOG-1.txt D7/D8).

No other deviations. Nothing in the prereg or in RUNLOG-1.txt was
renegotiated by this leg.

## 12. ARTIFACT LOCATIONS

In-repo (research/rs053/):
    rs053-metrics.py       M1, M2, M3, M4, M6 for one route log -> JSON
    rs053-cross.py         M5 for a (prose, code) JSON pair -> JSON

Off-repo, /mnt/f/f32/stage/research/rs053/analysis/ (this leg's own
subdirectory under the existing rs053 out dir), sha256 literal (from
`sha256sum analysis/*.json` on hyde):

    964f5c5c164785d8391ca6a0b0c7c3b8bea60c058d89d01051a45e1aa9af4750  120b-code-a.json
    5441092ec599e1fc440d6f9465c5304087e4e7cefdd42fffc83704e609cc25a0  120b-code-b.json
    55104a59e1f1570c51e759d8782aa45a64dd8bf492c64b23a5c17c1379716320  120b-prose-a.json
    6d20b2089941b6f55f07a3a7a0e7bd7b839c1e1db9d0794e383328418e041084  120b-prose-b.json
    a5a1a44c6aca603d70ee4ba3ca28533e30c72d9ca67316434a3c88f550eb2f72  20b-code-a.json
    2af0890ce824dbe6ad2b2bb382edf461edc30cf607bc83c0398d009e9b416bf9  20b-code-b.json
    760163b29b3146004809aac9a1c63100bf21da67d93b25514ef6ebb848f3b729  20b-prose-a.json
    79d367b141a254d748d398785e431a4458e58be49bbe7de17510c0799775303f  20b-prose-b.json
    e2120ee0e34ae009bab653c0bb3341871136181be12e79b26a5abb4b31ad832b  M5-120b.json
    b786f7448662476ca4027a9ba7e576f13d7a096d4d6ac3363dd6fc45c36a874e  M5-20b.json

Each per-run JSON carries: the full L x E histogram (M1), full
per-layer P_half/dead_count/collapse arrays (M1/M2), full per-window M3
curves (all three W), the full M4 per-layer Jaccard sequence, and the
full M6 per-layer fraction means -- this receipt's tables are summaries
(layer-mean plus min/max layer) of what the JSON banks in full, per the
task's own instruction to report layer-summaries in the document while
the fuller data stays banked.

## 13. LIVE-PROCESS AND RESOURCE DISCIPLINE

This leg ran read-only analysis over already-banked route logs; no GPU
work, no new model load, no new heavy run. `nice -n 10` on every Python
invocation. Never touched pid 654, pid 489, the MoE-0 collector
(route_stats.py/c4run.sh), or any wsl.exe keepalive -- confirmed the
MoE-0 C4 final-run2 leg had already completed (END_UTC=2026-08-31T16:35:45Z,
progress.txt DONE) before this leg cited its receipt; nothing of this
leg's own work depended on or interfered with it. `free -m` at the start
of this leg's heaviest step: available 21683 MB (well above the 4 GB
floor); analysis workload is CPU-only, small arrays (largest single load
1572864 x 6 int64, well under a gigabyte resident).

END RS053-GPTOSS-LOCALITY-1
