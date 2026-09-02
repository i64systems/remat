# FIGURES
# Provisional Patent Application: Byte-Exact Inference From
# Digest-Verified, Demand-Rematerialized Model Memory With
# Deterministic Residency Control
# Inventor: Harriett Ione Little
# Applicant: Lauren Nicole Miedel

FIG. 1  THE VERIFIED LEASE PATH (the core method, statement A)

  +------------------+     +---------------------------------------+
  |  BACKING STORE   |     |  MANIFEST (the identity ledger)       |
  |  (NVMe, cold)    |     |  tensor id | offset | length | digest |
  |  model bytes N   |     |  one row per leasable weight region   |
  +--------+---------+     +-------------------+-------------------+
           |                                   |
           |  (1) routing decision names       |
           |      the regions required         |
           v                                   v
  +--------+-----------------------------------+-------------------+
  |  LEASE:  read by byte-range  ->  VERIFY digest (sha256)        |
  |          against the manifest BEFORE use                       |
  |          FAIL -> void_result, record_pain, refuse by name      |
  |          PASS -> place DETERMINISTICALLY (keyed by region id,  |
  |                  never by i/o completion order)                |
  +--------------------------------+-------------------------------+
                                   |
                                   v
  +--------------------------------+-------------------------------+
  |  COMPUTE (kernels unchanged)  ->  use  ->  discard             |
  |  OUTPUT: byte-identical to the fully resident computation      |
  +----------------------------------------------------------------+

  Fast-resident bytes M << logical model bytes N.
  CAPACITY EXPOSURE = N / M, measured never claimed.


FIG. 2  THE CONTROLLER (statement E): result commitment and
        operating point commitment are SEPARATED

  verified result ----------------------> ALWAYS SHIPS
       |                                  (latency never voids
       |                                   correct completed work)
       v
  p95 <= c * baseline ?   yes -> commit lever_up   (grow N/M)
        (c = 2 in the      no -> commit back_off
         reference)
       |
       v
  every controller commit is JOURNALED, REPLAYABLE state;
  identity violation -> void_result + record_pain + named refusal


FIG. 3  MEASURED EXPOSURE (reduction to practice; receipts attached)

  exposure (N/M, accounted), latency multiple vs resident baseline

  12 GB model (32 experts/layer), resident fraction K/32:
    K=16  1.674400   p95 1.25-1.29x     identity byte-exact
    K=8   2.526252   p95 1.41-1.51x     identity byte-exact
    K=4   3.388101   p95 1.52-1.54x     identity byte-exact
    K=2   4.084898   p95 1.52-1.58x     identity byte-exact
    K=1   4.553092   p95 1.58-1.60x     identity byte-exact
    K=0   5.142505   p95 1.48-1.77x     identity byte-exact
          (empty resident set: every region leased on every use)

  63 GB model (128 experts/layer), K=8, resident-proportional
  allocator, no operating-system overcommit setting:
          8.209143   p95 1.7971x        identity byte-exact
          largest single model-state allocation: 586.83 MB
          (the N-proportional allocation is designed out)


FIG. 4  DETERMINISTIC RESIDENCY POLICIES (statements B, B1, C)

  input bytes --> [ frozen integer byte-classifier ] --> region set
                     (statement C: task-region           chosen at
                      selection by fixed thresholds,     startup
                      compiled)
                                |
                                v
  routing history --> [ integer decay-counter per region ]
                       +constant on selection; >> at fixed
                       decision-count boundaries; top-K at
                       boundaries only   (statement B/B1)
                                |
                                v
        resident set = pure function of (input bytes,
        routing history, fixed constants) -> REPRODUCIBLE
        by an independent simulator to exact counts
        (measured: engine == simulator to the integer)
