# RS053-GPTOSS-LOCALITY-1-PREREG: PRETRAINED GPT-OSS ROUTER LOCALITY,
# FROZEN BEFORE ANY INSTRUMENT EXISTS

Lane: research (CUDA/inventor lane), venue hyde, on-machine. Branch
research-2, worktree F:\f32\openbob-wt\research-2. Builder 1 of RS053
(prereg only; no instrument written or run by this leg). Pure ASCII, no
em dashes. Committed BEFORE any measurement code exists; nothing below
this line is renegotiated mid-run. Deviations are named, not silently
absorbed.

Substrate at prereg time: worktree HEAD c1eadb175e595afebd36c1f98cf8f5700befa39d,
branch research-2, `git status --porcelain` empty (clean).

## 0. THE QUESTION (measurement, not falsifier)

Do the PRETRAINED, already-shipped routers inside gpt-oss-20b and
gpt-oss-120b (MXFP4 GGUF, top-k softmax routers, NOT the house's own
frozen-BitNet router from BOBMOE0-PREREG-1.md) show leaseable locality:
expert-usage skew and bounded per-window working sets, on the same
instrument family the MoE-0 C4 leg used? This decides whether pretrained
MoE routers already carry the locality structure the called-never-loaded
thesis (N4/A1) needs, or whether that structure only shows up in a
natively-trained ternary router (the separate low-int/BOBMOE0 question).

STATED PLAINLY PER THE OWNER'S PROBE FRAMING: this is a measurement. No
kill bar is set here. MoE-0's G2 0.60 P_half bar is carried forward only
as a COMPARISON ANCHOR (see M2), never as a pass/fail gate for this
instrument. Nobody is falsified by this run; a number is banked.

## 1. ARCHITECTURE FACTS, SOURCED AND CROSS-VERIFIED

Two independent sources per fact: (a) the house's own registered
documents (v11 prompt doc for 20b, F-3 census card for 120b), (b) a
direct GGUF metadata read of the on-disk artifact by this leg (script
below), done because "convenient" per the task and because it costs
nothing beyond a header parse (no full-file read, no llama.cpp build
needed).

Independent GGUF read: research/gen (this leg) wrote a minimal GGUF
metadata-only parser (magic + version + kv section, stdlib struct only,
no third-party deps) and ran it under `nice -n 10 python3` on hyde
against both on-disk files. Full output, literal:

  gpt-oss-20b-MXFP4.gguf:
    general.architecture = gpt-oss
    general.name = gpt-oss-20b
    gpt-oss.block_count = 24
    gpt-oss.context_length = 131072
    gpt-oss.embedding_length = 2880
    gpt-oss.feed_forward_length = 2880
    gpt-oss.attention.head_count = 64
    gpt-oss.attention.head_count_kv = 8
    gpt-oss.rope.scaling.original_context_length = 4096
    gpt-oss.expert_count = 32
    gpt-oss.expert_used_count = 4
    gpt-oss.expert_feed_forward_length = 2880
    _gguf_version = 3
    _tensor_count = 459
    _kv_count = 36

  gpt-oss-120b-MXFP4.gguf:
    general.architecture = gpt-oss
    general.name = gpt-oss-120b
    gpt-oss.block_count = 36
    gpt-oss.context_length = 131072
    gpt-oss.embedding_length = 2880
    gpt-oss.feed_forward_length = 2880
    gpt-oss.attention.head_count = 64
    gpt-oss.attention.head_count_kv = 8
    gpt-oss.rope.scaling.original_context_length = 4096
    gpt-oss.expert_count = 128
    gpt-oss.expert_used_count = 4
    gpt-oss.expert_feed_forward_length = 2880
    _gguf_version = 3
    _tensor_count = 687
    _kv_count = 36

FROZEN FACT TABLE (both sources agree, MATCH on every row; L = layers,
E = experts/layer, k = top-k active, h = d_model/embedding_length,
heads/kv = attention head counts, expert_ffn = expert_feed_forward_length):

  model         L    E    k    h     heads  kv   expert_ffn  source(doc)          source(gguf)  verdict
  gpt-oss-20b   24   32   4    2880  64     8    2880        v11/PROMPT-GPT-OSS-20B.md L20-22    gguf read     MATCH
  gpt-oss-120b  36   128  4    2880  64     8    2880        h1-work/h110 census card, "geometry" line  gguf read  MATCH

Doc-source quotes, literal:
  20b: "Facts   21B total / 3.6B active, 24 layers, 32 experts top-4, 2880
  hidden, 64 heads / 8 KV heads, ..." (F:\f32\openbob-wt\research-2\v11\PROMPT-GPT-OSS-20B.md
  line 20-22).
  120b: "geometry  h 2880, nh 64, nkv 8, hd 64, inter 2880, v 201088, l 36,
  nexperts 128, topk 4" (/root/h1-work/h110/F3-CENSUS-CARD-gpt-oss-120b.md
  section 1, sourced there to research/src/h1_f2_forward.rs line 1078).

No mismatch found; no deviation to name on architecture facts.

## 2. ARTIFACT DIGEST VERIFICATION

Both files verified by this leg with `nice -n 10 sha256sum` on hyde,
2026-08-31, against the registry JSON LFS oid at
/root/openbob-baselines/reg/hf-ggml-org_gpt-oss-{20b,120b}-GGUF.json.
Literal command output:

  START 2026-08-31T15:46:29Z
  27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901  gpt-oss-20b-MXFP4.gguf
  MID 2026-08-31T15:46:48Z
  582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d  gpt-oss-120b-MXFP4.gguf
  END 2026-08-31T15:47:50Z

Expected (from reg JSON siblings[].lfs.sha256, and cross-checked against
/root/openbob-baselines/reg/HYDE-MODEL-MANIFEST.sha256, a prior baselines-1
leg's own independent verification from 2026-08-28T07:16:18Z):
  gpt-oss-20b-MXFP4.gguf   expected 27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901
  gpt-oss-120b-MXFP4.gguf  expected 582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d

VERDICT:
  gpt-oss-20b-MXFP4.gguf   MATCH
  gpt-oss-120b-MXFP4.gguf  MATCH

Byte sizes on disk (literal, from the models directory listing at
verification time): gpt-oss-20b-MXFP4.gguf 12109566624 bytes;
gpt-oss-120b-MXFP4.gguf 63387346208 bytes. Both equal the reg JSON's
lfs.size and siblings[].size fields.

## 3. CORPORA, PINNED

PROSE: enwik8 bytes [95000000, 95262144) (262144 bytes), extracted from
/mnt/f/f32/stage/lowint/data/enwik8/enwik8 (a read-only staged asset of
the low-int lane; this leg only reads it) by a stdlib-only Python
extraction (offset seek + fixed-length read, no transform). Written to
F:\f32\stage\research\rs053\corpus-prose.txt (off-repo per house rule).

  bytes: 262144 (literal, matches the slice length by construction)
  sha256: 3da39fce307af7a85b91c2f4372942f4a77f83e9c44fe70294c67cbb392d3c55

CODE: the single file F:\f32\openbob-wt\retail-m0\k4b\src\openbob_s11_cpu.rs
(the PRIMARY path named in the task; it exists, so the named fallback
F:\f32\openbob\k4b\src\openbob_s11_cpu.rs was NOT used). Copied byte-exact
to F:\f32\stage\research\rs053\corpus-code.txt.

  bytes: 1576144 (literal, from the source file's own size)
  sha256: d2db5c682d5f52a4383d188fee9d25f592a15d69763dbf886b5614c953e7f3fc

Both files confirmed present at F:\f32\stage\research\rs053\ post-write
(directory listing: corpus-code.txt 1576144 bytes, corpus-prose.txt
262144 bytes, both dated 2026-08-31 11:46 local).

DEVIATION NAMED: the task's fallback clause for the code corpus was not
triggered (primary path existed); recorded here only because the task
asked that the choice be recorded either way.

## 4. THE FOUR RUNS, EACH TWICE

Runs (model x corpus), 4 total, each executed TWICE from clean processes
for an A/A byte-identity check on the emitted route-id logs (same law as
G1 in BOBMOE0-PREREG-1.md: same box, same weights, same corpus slice,
byte-identical route-id log both times, digest quoted in the eventual
receipt):

  R1  20b-prose   gpt-oss-20b-MXFP4.gguf  x  corpus-prose.txt
  R2  20b-code    gpt-oss-20b-MXFP4.gguf  x  corpus-code.txt
  R3  120b-prose  gpt-oss-120b-MXFP4.gguf x  corpus-prose.txt
  R4  120b-code   gpt-oss-120b-MXFP4.gguf x  corpus-code.txt

8 executions total (4 runs x 2 for A/A). The router is deterministic by
construction (top-k over logits from a fixed forward on fixed weights,
no sampling, no dropout at inference); the A/A check exists to catch
nondeterminism in the INSTRUMENT (thread races, uninitialized reads,
nonassociative float reduction order) rather than in the model, exactly
as G1 exists to catch instrument nondeterminism on the trained twins.

TOKEN BUDGETS, FROZEN NOW:
  20b slices:  65536 tokens per (run, corpus) pair.
  120b slices: 16384 tokens per (run, corpus) pair.
TRUNCATION RULE: the corpus is tokenized by the model's own tokenizer
(o200k_harmony per the 20b prompt doc; same tokenizer family for 120b)
and truncated to the frozen budget above. IF a corpus tokenizes SHORTER
than its budget (fewer tokens than the frozen number), the full
tokenized length is used instead and the actual token count is recorded
literally in the run receipt; this is not a deviation, it is the
pre-agreed fallback for that case, stated here so a builder never
renegotiates it mid-run. Prose and code corpora are sized (262144 and
1576144 bytes respectively) to comfortably clear both budgets at any
plausible bytes-per-token ratio for a byte/BPE-class tokenizer, but the
actual token count is an instrument-time fact, not assumed here.

## 5. METRIC DEFINITIONS M1-M6, PARAMETERIZED BY (L, E, k)

### 5.0 G2 LIFTED VERBATIM (source: BOBMOE0-PREREG-1.md section 2, the
MoE0 stage-1/2 house router locality instrument), then mapped onto this
instrument's parameters.

Verbatim (MoE0's own frozen text, E=8, k=2 in that document):
  "G2 LOCALITY ... STAT DEFINITIONS FROZEN NOW. Over the frozen eval
  split, deterministic forward, for each MoE layer l with selection sets
  S(l,t) (the k=2 experts, tie-break as frozen):
    c_l(e)   = count of positions t with e in S(l,t)
    P_half(l)= (sum of the E/2=4 largest c_l) / (sum of all c_l)
               [uniform routing gives 0.50; the field's measured skew on
               trained MoEs is ~0.95 through half - SYNTHESIS-1 s.3]
    ...
  Banked per layer and as layer means, plus dead-expert count (experts
  under 1 percent of a layer's traffic). COLLAPSE NAMED AS ITS OWN
  OUTCOME: P_half near 1.0 with more than half the experts dead is
  reported as routing collapse, never as locality."

DECLARED PARAMETER MAPPING for RS053 (this instrument, both models have
k=4 by the GATE JSON facts of section 1; E differs per model):
  gpt-oss-20b:   E=32, so E/2=16 (P_half sums the 16 largest c_l).
  gpt-oss-120b:  E=128, so E/2=64 (P_half sums the 64 largest c_l).
  k=4 for both (S(l,t) is the 4 experts gpt-oss's own trained router
  selects at layer l, position t; this is a top-4 softmax router, NOT
  the frozen top-2 deterministic BitNet router BOBMOE0 measures).
  Dead-expert threshold is UNCHANGED (E-independent): under 1 percent of
  a layer's traffic, same rule, same 1 percent, for both models.
  Collapse rule is UNCHANGED IN FORM: P_half near 1.0 with more than
  half the experts (E/2, per model) dead is reported as collapse, never
  as locality.

DEVIATION NAMED (tie-break): BOBMOE0's tie-break law ("ties in router
logits resolve to the lower expert index") is a law for a router THIS
HOUSE TRAINS from scratch. gpt-oss's router is pretrained and its
top-4 selection is read off float logits already baked into the
weights; exact float ties at inference are measure-zero in practice.
RS053 adopts the SAME tie-break convention (lower expert index) purely
as a measurement-time bookkeeping rule in case the instrument ever
observes an exact tie, and will record in the receipt whether any tie
was ever observed (expected count: 0).

G2's C_3 (co-activation pair concentration) and H_l (normalized routing
entropy) are NOT carried into M1-M6 below. RS053 supersedes them with
the richer M3-M5 window/Jaccard/divergence family, which was designed
for a full-scale pretrained router reading real corpora rather than a
tiny CPU twin on a synthetic split, and answers the same underlying
locality question (is usage concentrated, and does the concentrated set
change slowly) with instruments matched to this scale. This is a named
scope choice, not an oversight: if a future leg wants C_3/H_l for direct
MoE0 comparison, they are cheap additions given c_l(e) and p_l(e,f) are
already computed for M1/M2.

### 5.1 M1: per-layer expert usage histogram + G2 collapse rule

For each layer l in [0, L), each expert e in [0, E): c_l(e) = count of
token positions t in the run's token budget with e in S(l,t) (the k=4
selected experts at that position). Banked as the full L x E histogram
plus, per layer, the dead-expert count (experts with c_l(e) under 1
percent of sum_e c_l(e)) and the collapse flag (P_half(l) near 1.0 AND
more than E/2 experts dead at that layer), per the G2 collapse rule
lifted in 5.0.

### 5.2 M2: P_half analog per layer

P_half(l) = (sum of the E/2 largest c_l(e) values) / (sum of all c_l(e)
values), per layer, per the mapping in 5.0 (E/2=16 for 20b, E/2=64 for
120b). Uniform routing gives 0.50 for any E. MoE-0's G2 kill threshold,
0.60, is carried forward here ONLY as a COMPARISON ANCHOR printed beside
the measured value; RS053 sets no kill bar (section 0). Banked per layer
and as the layer mean.

### 5.3 M3: working-set curves

For sliding windows of W tokens, W in {64, 512, 4096}: the number of
DISTINCT experts touched by ANY position in the window, per layer and
also pooled across all layers (the union of that layer's or that run's
touched-expert set over the window). Reported as a curve over all window
positions in the run (stride 1, or a stated coarser stride if the full
stride-1 curve is too large to bank; the instrument-building leg decides
and records its choice). IMPLIED RESIDENT BYTES: the working-set expert
count at each window position, multiplied by the per-expert byte size
(from M6's gguf-tensor-derived expert byte size), giving a working-set
byte curve alongside the count curve.

### 5.4 M4: phase stability

For W=512 windows only, at consecutive non-overlapping window pairs
(window i, window i+1) per layer: Jaccard overlap of the two windows'
distinct-expert sets, J = |A intersect B| / |A union B|. Banked per
layer as a sequence over the run and as the layer mean. High J means the
resident set barely moves between adjacent windows (a leasable, phase-
stable set); low J means it is being reshuffled continuously.

### 5.5 M5: cross-slice divergence

Per layer, comparing the SAME model's prose run against its code run
(20b-prose vs 20b-code; 120b-prose vs 120b-code):
  (a) Jaccard overlap of the top-32-by-usage expert sets (the 32 experts
  with the largest c_l(e) in that layer, ranked by usage, for each
  corpus), J_top32 = |top32_prose intersect top32_code| / |top32_prose
  union top32_code|.
  (b) L1 distance of the two corpora's normalized usage distributions:
  sum_e |c_l_prose(e)/sum(c_l_prose) - c_l_code(e)/sum(c_l_code)|.
NOTED PROPERTY, NOT A DEVIATION (the "top-32" count is the task's own
fixed number, not E-parameterized): for gpt-oss-20b, E=32, so
"top-32-by-usage" is the FULL expert set for that model, and J_top32 is
DEGENERATE (equals 1.0 by construction, both sets are all 32 experts,
provided every expert has nonzero usage; if any expert has zero usage in
one corpus it drops from that corpus's set and J_top32 can fall below
1.0, which is itself informative - a dead-for-this-corpus expert). For
gpt-oss-120b, E=128, top-32 is a genuine 25-percent-of-experts subset
and J_top32 is a real selectivity measure. Both are computed and banked
as specified; the 20b number is reported with this note attached so a
reader does not mistake "1.0" for evidence of high overlap when it may
be a tautology of the corpus size relative to E.

### 5.6 M6: exposure implication

Per layer, per window position (same W=512 windows as M4): measured
resident expert bytes (the M3 working-set expert count at that window,
times per-expert byte size) versus TOTAL expert bytes for that layer (E
times per-expert byte size). Reported as a fraction (resident / total)
per window, and as a run-level distribution (min, median, max, mean over
all windows and layers).
PER-EXPERT BYTE SIZE, SOURCE NAMED: read from the GGUF tensor byte sizes
at instrument-build time (each layer's ffn_gate_exps/ffn_up_exps/
ffn_down_exps tensors in the MXFP4 GGUF, per-expert slice = tensor byte
size / E for a tensor holding all E experts' weights, or read directly
per-expert if the format splits per-expert; the instrument-building leg
names which GGUF tensor layout it found and records the exact byte
count per expert per layer, since gpt-oss's GGUF may pack all experts of
a layer into one multi-expert tensor rather than E separate tensors).
This leg (prereg only) did NOT read the tensor-info section of the GGUF
(only the KV-metadata section, section 1); the per-expert byte size is
therefore a DEFERRED fact, named here so the instrument-building leg
knows it owes that number before M6 can be computed, not assumed from
this document.

## 6. WHAT THIS IS, STATED PLAINLY (repeat of section 0)

This is a measurement of ALREADY-TRAINED, ALREADY-SHIPPED pretrained
routers. No kill bar. No pass/fail verdict is defined anywhere in this
document. MoE-0's P_half 0.60 threshold appears exactly once, in M2, as
a comparison anchor and nowhere else. Whatever M1-M6 measure, they are
reported as facts about gpt-oss's routers, feeding the one-bob/capacity-
exposure program's locality question, not adjudicating it alone.

## 7. WALLS AND SCOPE FOR THIS AND FOLLOWING RS053 LEGS

Per the house rules handed to this builder (RS053 task brief, not
BOBMOE0's stage-1 walls, which bind a different lane): CPU budget at
most 10 threads under nice 10 for any heavy run; at least 4 GB WSL RAM
free at all times; GPU IS available for RS053's use (unlike BOBMOE0
stage-1's CPU-only wall), leaving the approximately 1.2 GB already
resident on the card alone. Never touch, signal, renice, or kill pid
654 (openbob serve, the 120B serve), searxng pid 489, any
route_stats.py/c4run.sh/c5run.sh process (the MoE-0 C4 collector legs),
or any wsl.exe keepalive; a stalled collector is reported, never
"fixed." Every wsl.exe invocation in this and following legs runs a
script file written to the Windows filesystem first (script-to-file
law); python.exe (never python3) on the Windows host, python3 on the
WSL/hyde side. Read-never: ~/.config/openbob/, journal blobs, tokens,
pins, and the sealed corpus lowint/fixtures/LI-S5-ROUTES-1.txt (never
opened by this or any RS053 leg). Stage dirs under /mnt/f/f32/stage/ are
read-only except this leg's own out dir
/mnt/f/f32/stage/research/rs053/, created by this leg. No weight
downloads (none needed; both artifacts were already on disk). git work
happens only in F:\f32\openbob-wt\research-2 on branch research-2;
master is never touched, nothing is pushed; the architect merges.
Receipts are pure ASCII, no em dashes, every number literal command
output, large bytes off-repo with sha256 recorded in-repo (this
document).

## 8. DEVIATIONS, COLLECTED

  1. Code corpus fallback path was not needed (primary path existed);
     recorded per task instruction regardless.
  2. G2's tie-break law is reapplied as a measurement convention only
     (pretrained router, not a house-trained one); no tie is expected,
     will be recorded if observed.
  3. G2's C_3 and H_l are not carried into M1-M6 (superseded by M3-M5,
     named as a scope choice in 5.0, not an omission).
  4. M5's "top-32" is degenerate (equals the full expert set) for
     gpt-oss-20b specifically, because E=32 there; noted in 5.5, not
     altered, since the task named the number literally.
  5. M6's per-expert byte size was NOT computed by this leg (KV-metadata
     read only, no tensor-info-section read); named as a fact the
     instrument-building leg owes before M6 can run (5.6).
  6. This leg did not build or run the measurement instrument itself
     (out of scope for Builder 1 / prereg, per the task).

No other deviations. Nothing above was renegotiated after this document
was committed.

END RS053-GPTOSS-LOCALITY-1-PREREG
