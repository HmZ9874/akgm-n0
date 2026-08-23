# V52.1 preprocessing result: stopped before program search

V52.1 replaced the relative-to-block-maximum rule with “the latest cycle above 1e-6 Ah.” The dual capacity audit found one terminal bookkeeping discharge of approximately 3.42e-6 Ah in a non-sealed 0–100% 2C cell. It passed the absolute threshold and produced a normalized response near 2.37e-6, while the paired capacity counter reported only about 6.95e-8 Ah.

This is a registered preprocessing failure, not extreme battery degradation. V52.1 stops before program selection and does not access the sealed archive. Its snapshot and counterexample manifest are retained so the failure is reproducible.

V52.2 replaces the unit-dependent absolute threshold with a cell-relative diagnostic criterion: after identifying the first valid full discharge, a later candidate must have at least 10% of that initial integrated capacity. The latest qualifying cycle is selected. This rejects charge-only bookkeeping tails while remaining below the smallest assigned partial-window fraction in the registered experiment.
