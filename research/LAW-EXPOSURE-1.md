# LAW-EXPOSURE-1: THE EXPOSURE RUNTIME LAW
# Ratified by the owner 2026-09-01 ("canonize"), her forms verbatim.
# Canon for the one-bob program and the white paper. Pure ASCII.
#
#   "Truth is fixed; only the cost of reaching it may move."
#                                     - Harriett Little

## The hierarchy (her sentences)

  Identity decides whether computation exists.
  Latency decides whether the operating point is retained.
  Exposure is what the controller maximizes afterward.

## The objective

  max N/M   s.t.   dy = 0,   tau <= 2 * tau_0

  N   logical learned bytes bound by the ledger (on disk)
  M   peak fast-resident bytes
  dy  displacement of any committed result from its ledger-bound
      reference (the zero displacement lock)
  tau p95 latency; tau_0 the fully resident baseline's own

## Definitions (her rulings closing the open questions)

1. candidate/reference is a LEDGER RELATIONSHIP, never specifically
   output-vs-fully-resident-output. The reference is whatever the
   ledger binds the candidate to: a lease to its manifest row, a
   golden to its banked triplet, a replay to its journal, an
   acceptance run to its baseline.
2. Latency is an optimization constraint on the OPERATING POINT,
   never on the correctness of a completed answer. Exact work may
   ship.
3. assert belongs in the laboratory. The serving path voids, records
   pain, and refuses by name; it does not die silent.

## The serving form (canonical)

    // Identity is a commit invariant, never an optimization variable.

    candidate = run_verified(bound_state);

    if (!identity_holds(candidate)) {
        void_result(candidate);
        record_pain(IDENTITY_VIOLATION);
        refuse(IDENTITY_VIOLATION);
        return;
    }

    commit_result(candidate);                  // exact work may ship

    if (tau <= 2 * tau_0)
        commit_controller(lever_up(N / M));
    else
        commit_controller(back_off());

## The acceptance form (canonical, laboratory only)

    candidate = run_verified(bound_state);

    assert(candidate.digest == reference.digest);

    record_evidence(candidate);

    if (tau <= 2 * tau_0)
        accept_operating_point(N / M);
    else
        reject_operating_point(N / M);

## Status at ratification

The identity invariant has never been violated in the program's
history: OB-1 5/5, OB-2 5/5, every A/A pair byte-identical, every
lease digest-verified. The execution gate has never closed: worst
carry observed 1.6488x against the 2.0x governor. Measured exposure
to date: 3.388101 (20b, K=4); structural ceilings under the current
design: 5.142505 (20b) and 15.805342 (120b) at K=0, set by the
always-resident trunk, which is therefore the next frontier.
