# Gen 0 Experiment Protocol v0.1

Status: **frozen before implementation**

## 1. Research claim

The learner receives anonymous numeric observations, a small declared program
language, and generic executable feedback. It is not told which reusable
structure the evaluator expects. We test whether library growth reduces the
cost of solving unseen numeric tasks while maintaining reliability.

This experiment can establish novelty relative to the learner's declared
inputs. It cannot by itself establish novelty relative to human science.

## 2. Separation of roles

### Learner process

May read only:

- `configs/learner_contract.yaml`;
- `configs/primitive_manifest.yaml`;
- anonymous observations returned by the environment interface;
- generic fit, program-cost, and reuse feedback for development tasks;
- previously admitted executable programs and their numeric evidence.

It may not read repository files, evaluator configuration, environment source,
human labels, hidden generation rules, or blind-test outcomes during search.

### Environment runner

Executes a requested anonymous numeric action and returns only the observation
fields allowed by the learner contract. It does not return source formulas,
family names, parameter semantics, or evaluator metadata.

### Evaluator process

Owns the sealed benchmark, equivalence checks, blind tasks, success gates, and
human interpretation metadata. It receives candidate programs only through a
versioned evaluation interface.

## 3. Declared initial priors

The learner is not knowledge-free in a philosophical sense. Gen 0 supplies:

- finite numeric values;
- task and sequence boundaries represented by randomized opaque identifiers;
- sequence order and bounds-aware indexed reads;
- addition, subtraction, anonymous scalar parameters, and composition;
- a search procedure over executable programs;
- generic numeric fit and description-cost feedback;
- durable storage for verified programs.

Every result must report its dependency on these supplied priors.

## 4. Prohibited learner inputs

The learner must not receive:

- natural-language task descriptions or concept names;
- target programs, formulas, family labels, or solution templates;
- pretrained language or scientific models;
- internet retrieval;
- evaluator success thresholds or blind-task identities;
- metadata correlated with hidden task families.

## 5. Knowledge admission

A candidate remains anonymous and is admitted only by executable evidence.
Human interpretation is optional metadata added after evaluation and is never
an admission criterion.

The state machine is:

`proposed -> fit_passed -> verified -> admitted | bounded | rejected`

Admitted knowledge may later be downgraded when new evidence supplies a
counterexample.

## 6. Required evidence

Each admitted or bounded program must record:

- its executable abstract syntax tree;
- all supplied and learned parent primitives;
- development, holdout, and out-of-range errors;
- stability results across seeds and numeric conditions;
- counterexamples, including failed candidates;
- a machine-readable validity domain;
- data, code, configuration, and verifier hashes;
- search cost before and after library reuse.

## 7. Baselines

The sealed evaluation compares at least:

1. fixed library with no growth;
2. growing library selected by cross-task description gain;
3. evaluator-provided ceiling primitive;
4. random reusable-fragment cache.

The learner does not receive the names or expected behavior of these baselines.

## 8. Frozen reporting rule

The dashboard must display all registered runs and all failed gates. It may not
hide seeds, remove counterexamples, or change a run's verdict. Development,
validation, and blind results are visually separated. A human-readable label
must never replace the underlying executable program.

## 9. Change control

Any change to primitives, task generation, gates, equivalence, or leakage policy
creates a new protocol version. Old results remain attached to the old version
and cannot be silently recomputed under the new rules.

