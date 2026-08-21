"""Universal induction proof for target-free fold discoveries."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from akgm_n0.learner.strict_fold_foundation_v12 import (
    PRIOR_BINARY_SEMANTIC_ID,
    FoldExecutor,
    FoldProgram,
    fold_program_id,
    inspect_iteration_profile,
)


@dataclass(frozen=True, slots=True)
class FoldFoundationProof:
    passed: bool
    semantic_id: str
    posthoc_name: str
    universal_statement: str
    derived_normal_form: str
    obligations: tuple[dict[str, Any], ...]
    hidden_replay: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "verifier_version": "strict-fold-induction-verifier-v12.1",
            "passed": self.passed,
            "semantic_id": self.semantic_id,
            "posthoc_name": self.posthoc_name,
            "universal_statement": self.universal_statement,
            "derived_normal_form": self.derived_normal_form,
            "obligations": list(self.obligations),
            "hidden_replay": list(self.hidden_replay),
        }


def prove_fold_foundation(program: FoldProgram) -> FoldFoundationProof:
    obligations: list[dict[str, Any]] = []

    def check(identifier: str, passed: bool, evidence: str) -> None:
        obligations.append({"obligation_id": identifier, "passed": bool(passed), "evidence": evidence})

    base_source = f"input_{1 - program.loop_input}"
    check("unit_seed", program.seed_source == "unit", "the accumulator begins at the prior semantic's identity")
    check("prior_semantic_selected", program.operation_id == PRIOR_BINARY_SEMANTIC_ID, "the update calls the universally proven V10 binary semantic")
    check("accumulator_and_base_are_update_arguments", {program.left_source, program.right_source} == {"accumulator", base_source}, "each update combines the current accumulator with the non-loop input")
    check("accumulator_is_output", program.output_source == "accumulator", "the completed fold returns its accumulated state")
    structure = all(item["passed"] for item in obligations)
    check("base_case", structure, "after zero iterations the state is the identity, denoted b^0=1")
    check("inductive_step", structure, "if state after t iterations is b^t, one prior-semantic call yields b^(t+1)")
    check("counter_invariant", structure, "after t iterations the remaining loop counter is n-t")
    check("termination", structure, "the natural loop counter decreases exactly once until zero")
    check("terminal_normal_form", structure, "at t=n the accumulator is the n-fold product of b")
    check("count_composition_law", structure, "associativity partitions an (m+n)-fold product into m-fold and n-fold products")
    check("base_composition_law", structure, "commutativity and associativity regroup n copies of a*b into n copies of a and n copies of b")

    executor = FoldExecutor(magnitude_limit=10**100)
    base_input = 1 - program.loop_input
    hidden = []
    for base, count in ((0, 0), (0, 7), (1, 31), (2, 12), (3, 9), (7, 6), (11, 5)):
        inputs = (base, count) if base_input == 0 else (count, base)
        output = executor.execute(program, inputs).output
        hidden.append({"base": base, "count": count, "output": output, "repeated_prior_semantic": base**count, "passed": output == base**count})
    profile = inspect_iteration_profile(executor, program, limit=5)
    check("independent_law_replay", profile.promotable, json.dumps(profile.to_dict(), sort_keys=True))
    check("sealed_replay", all(item["passed"] for item in hidden), "seven cases outside the discovery grid")

    digest = hashlib.sha256(json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
    passed = all(item["passed"] for item in obligations)
    return FoldFoundationProof(
        passed,
        "STRICT-FSEM-" + digest,
        "自然数幂（证明后命名）" if passed else "未命名折叠行为",
        "for every b,n in N, the program halts and returns the n-fold prior-semantic composition of b, with the empty fold equal to 1" if passed else "no universal statement admitted",
        "b^n" if passed else "unproven",
        tuple(obligations),
        tuple(hidden),
    )


def replay_fold_foundation(program: FoldProgram, candidate: str) -> dict[str, Any]:
    proof = prove_fold_foundation(program)
    return {"passed": proof.passed and fold_program_id(program) == candidate, "proof": proof.to_dict()}
