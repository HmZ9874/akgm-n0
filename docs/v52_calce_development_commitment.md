# V52 development-stage commitment

The V52 learner has not accessed the sealed `G20_80_2C` archive. This document records the development-stage data contract and selected executable program before validation evaluation or sealed access.

## Audited data contract

- Seven official non-sealed CALCE archives were verified by SHA-256 before parsing.
- MATLAB v5 MCOS tables are decoded with `mat-io` in raw-property mode; the learner receives only anonymous numeric controls, time coordinates, and normalized capacity.
- A diagnostic observation is the latest measurable full-discharge cycle in each recorded operation block. The extractor uses within-cycle discharge-capacity range, which is invariant to whether the Arbin counter accumulates across an operation or resets each cycle.
- Charge-only terminal bookkeeping cycles and explicitly missing operations are rejected and retained in the manifest as counterexamples.
- All 14 non-sealed cells satisfy the preregistered minimum of eight diagnostic observations after parser auditing. The anonymous snapshot contains 296 observations.

## Frozen development result

The search enumerated 7,175 behaviorally distinct executable programs from 35 anonymous atoms, with leave-one-protocol-group-out evaluation and an explicit program-size penalty. The selected program and fitted parameters are frozen in `experiments/v52_calce_program_commitment.json`.

The program is a bounded predictive representation, not a battery law. It cannot identify electrochemical mediation, separate assigned rate from unmeasured internal heating, establish cross-chemistry universality, or support a claim of human-unknown science.

Validation must run with the committed program and parameters unchanged. The sealed archive remains inaccessible until the validation result is recorded and this commitment is present in Git history.
