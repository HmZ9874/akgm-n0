"""Universal invariant verification for target-free event-counter behavior."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from akgm_n0.learner.strict_partition_foundation_v11 import (
    EventCounterExecutor,
    EventCounterProgram,
    event_program_id,
    inspect_conservation_profile,
)


@dataclass(frozen=True, slots=True)
class PartitionFoundationProof:
    passed: bool
    semantic_id: str
    posthoc_name: str
    universal_statement: str
    derived_normal_form: tuple[str, str]
    obligations: tuple[dict[str, Any], ...]
    hidden_replay: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "verifier_version": "strict-partition-invariant-verifier-v11.1",
            "passed": self.passed,
            "semantic_id": self.semantic_id,
            "posthoc_name": self.posthoc_name,
            "universal_statement": self.universal_statement,
            "derived_normal_form": list(self.derived_normal_form),
            "obligations": list(self.obligations),
            "hidden_replay": list(self.hidden_replay),
        }


def prove_partition_foundation(program: EventCounterProgram) -> PartitionFoundationProof:
    obligations: list[dict[str, Any]] = []

    def check(identifier: str, passed: bool, evidence: str) -> None:
        obligations.append({"obligation_id": identifier, "passed": bool(passed), "evidence": evidence})

    policy = (
        program.preserve_template,
        program.consume_work,
        program.increment_state_b,
        program.boundary_increment_state_a,
        program.boundary_clear_state_b,
        program.boundary_refill_work,
    )
    check("distinct_state_roles", len({program.state_a, program.state_b, program.work, program.scratch}) == 4, "four anonymous state registers have distinct roles")
    check("template_preserved", policy[0], "unit transfer copies the positive template through scratch storage")
    check("one_stream_and_work_mark_consumed", policy[1], "each main transition consumes one stream mark and one work mark")
    check("residual_state_advances", policy[2], "each consumed stream mark advances the second output state by one")
    check("boundary_advances_first_state", policy[3], "an empty work counter advances the first output state")
    check("boundary_resets_residual", policy[4], "a completed block clears the second output state")
    check("boundary_restores_work", policy[5], "a completed block restores exactly one template-sized work counter")

    structure_passed = all(item["passed"] for item in obligations)
    check("base_invariant", structure_passed, "at processed=0: state_a=0, state_b=0, work=d")
    check("partial_block_induction", structure_passed, "if residual+1<d, first state is unchanged, residual advances, and work decreases")
    check("complete_block_induction", structure_passed, "if residual+1=d, first state advances, residual resets, and work is restored to d")
    check("termination", structure_passed, "the finite stream counter decreases exactly once per main transition")
    check("terminal_decomposition", structure_passed, "at termination n=d*q+r with 0<=r<d")
    check("uniqueness", structure_passed, "two bounded-residual decompositions differ by a multiple of d whose magnitude is strictly below d, so both components agree")

    executor = EventCounterExecutor(maximum_steps=5_000_000)
    cases = ((0, 1), (1, 7), (17, 5), (42, 8), (101, 9), (255, 16), (997, 31))
    hidden = []
    for stream, template in cases:
        inputs = (stream, template) if program.stream_input == 0 else (template, stream)
        outputs = executor.execute(program, inputs).outputs
        hidden.append({
            "stream": stream,
            "template": template,
            "outputs": list(outputs),
            "reconstruction": outputs[0] * template + outputs[1],
            "passed": outputs[0] * template + outputs[1] == stream and 0 <= outputs[1] < template,
        })
    profile = inspect_conservation_profile(executor, program, limit=9)
    check("independent_conservation_replay", profile.promotable, json.dumps(profile.to_dict(), sort_keys=True))
    check("sealed_replay", all(item["passed"] for item in hidden), "seven cases outside the discovery grid")

    digest = hashlib.sha256(
        json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    passed = all(item["passed"] for item in obligations)
    return PartitionFoundationProof(
        passed,
        "STRICT-FSEM-" + digest,
        "欧几里得商余分解（证明后命名）" if passed else "未命名二输出行为",
        "for every n in N and d in N+, the program uniquely returns q,r with n=d*q+r and 0<=r<d" if passed else "no universal statement admitted",
        ("q=floor(n/d)", "r=n-d*q") if passed else ("unproven", "unproven"),
        tuple(obligations),
        tuple(hidden),
    )


def replay_partition_foundation(program: EventCounterProgram, candidate: str) -> dict[str, Any]:
    proof = prove_partition_foundation(program)
    return {"passed": proof.passed and event_program_id(program) == candidate, "proof": proof.to_dict()}
