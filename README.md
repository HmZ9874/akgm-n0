# AKGM-N0

AKGM-N0 is a local research prototype for discovering executable, reusable
numeric programs without exposing domain labels, target formulas, or language
corpora to the learner.

The first milestone is the Gen 0 contract layer. It freezes:

- what the learner can observe;
- which computational primitives are supplied;
- which information is evaluator-only;
- how a discovery is recorded and judged;
- how public configuration is audited for target leakage.

The files ending in `.yaml` deliberately use the JSON-compatible subset of
YAML 1.2. They can be loaded with Python's standard `json` module, so the
contract audit has no third-party dependency.

## Current commands

Run the contract and leakage audit:

```powershell
python scripts/audit_contracts.py
```

Run the test suite:

```powershell
python -m unittest discover -s tests -v
```

Run the evaluator-side numeric core smoke demo:

```powershell
python scripts/demo_numeric_core.py
```

Run the first autonomous program-search smoke test:

```powershell
python scripts/run_search_smoke.py
```

Run search, independent verification, counterexample capture, and ledgering:

```powershell
python scripts/run_verification_smoke.py
```

Run the multi-task anonymous concept and transfer comparison:

```powershell
python scripts/run_concept_experiment.py
```

## Trust boundary

`configs/` contains learner-visible configuration. `evaluator/` contains sealed
benchmark information and must never be mounted into a learner process. The
current milestone validates the file-level boundary; process-level sandboxing
will be added with the experiment runner.

## Executable core

The next layer is represented by two packages:

- `akgm_n0.learner` contains the public observation type and the small executable
  program language;
- `akgm_n0.evaluator` contains hidden numeric world generation and must remain
  outside the learner filesystem bundle.

The DSL is an expression-tree interpreter, not a Transformer architecture. It
enforces registered operations, sequence bounds, validity masks, program size,
program depth, finite values, and magnitude limits.
