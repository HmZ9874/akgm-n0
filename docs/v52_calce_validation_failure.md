# V52 validation result: registered failure

V52 failed its preregistered non-sealed validation criterion. The frozen forged program produced RMSE 0.223456491831, while the best registered baseline (last observed normalized capacity) produced RMSE 0.187639918360. The error ratio was 1.19087928509, above the required maximum of 0.80.

The failure remains valid even though the post-result audit found a preprocessing defect. In the 0–100% 2C files, the first cycle of several multi-cycle operation blocks contains approximately twice the ordinary discharge capacity. The V52 extractor selected the latest cycle above half of the block maximum; when the doubled first cycle made ordinary later cycles fall just below that threshold, it selected the first cycle and created nonphysical normalized capacity increases up to about 1.75.

Independent current–time integration reproduced the doubled first-cycle value, showing that this is a cycle-boundary/operation-layout issue rather than only a corrupted capacity column. The auditable invariant is simpler: choose the latest cycle with measurable discharge, because CALCE partial-cycle blocks end in a full diagnostic discharge and full-cycle blocks may end in a charge-only bookkeeping cycle.

V52 is not rerun or relabeled as successful. Its program commitment remains in Git commit `a714db2`, its failure report is retained, and the sealed `G20_80_2C` archive remains unaccessed. The parser correction is treated as a new V52.1 experiment with a new commitment.
