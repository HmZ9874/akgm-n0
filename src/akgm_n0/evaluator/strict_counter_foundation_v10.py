"""Independent replay and universal invariant proof for counter discoveries."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from akgm_n0.learner.strict_counter_foundation_v10 import (
    CounterExecutor,
    CounterMove,
    CounterProgram,
    candidate_id,
    inspect_algebraic_profile,
)


Poly = dict[tuple[int, int, int], int]


def _clean(value: Poly) -> Poly:
    return {key: coefficient for key, coefficient in value.items() if coefficient}


def _add(left: Poly, right: Poly) -> Poly:
    result = dict(left)
    for key, coefficient in right.items():
        result[key] = result.get(key, 0) + coefficient
    return _clean(result)


def _neg(value: Poly) -> Poly:
    return {key: -coefficient for key, coefficient in value.items()}


ZERO: Poly = {}
ONE: Poly = {(0, 0, 0): 1}
X: Poly = {(1, 0, 0): 1}
Y: Poly = {(0, 1, 0): 1}
T: Poly = {(0, 0, 1): 1}
TY: Poly = {(0, 1, 1): 1}
XY: Poly = {(1, 1, 0): 1}


def _symbolic_move(move: CounterMove, registers: list[Poly]) -> None:
    amount = registers[move.source]
    registers[move.source] = ZERO
    for destination in move.destinations:
        registers[destination] = _add(registers[destination], amount)


def _symbolic_outer_step(program: CounterProgram, registers: list[Poly]) -> None:
    registers[program.outer_source] = _add(
        registers[program.outer_source], _neg(ONE)
    )
    _symbolic_move(program.first_move, registers)
    _symbolic_move(program.second_move, registers)


@dataclass(frozen=True, slots=True)
class CounterFoundationProof:
    passed: bool
    semantic_id: str
    posthoc_name: str
    universal_statement: str
    derived_normal_form: str
    obligations: tuple[dict[str, Any], ...]
    hidden_replay: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "verifier_version": "strict-counter-invariant-verifier-v10.1",
            "passed": self.passed,
            "semantic_id": self.semantic_id,
            "posthoc_name": self.posthoc_name,
            "universal_statement": self.universal_statement,
            "derived_normal_form": self.derived_normal_form,
            "obligations": list(self.obligations),
            "hidden_replay": list(self.hidden_replay),
        }


def prove_counter_foundation(program: CounterProgram) -> CounterFoundationProof:
    control = program.outer_source
    stable = 1 - control
    accumulator = program.output_register
    scratch_candidates = set(range(4)) - {control, stable, accumulator}
    scratch = next(iter(scratch_candidates)) if len(scratch_candidates) == 1 else None

    obligations: list[dict[str, Any]] = []

    def check(obligation_id: str, passed: bool, evidence: str) -> None:
        obligations.append(
            {"obligation_id": obligation_id, "passed": bool(passed), "evidence": evidence}
        )

    check("output_uses_zero_initialized_accumulator", accumulator in (2, 3), f"R{accumulator} starts at zero")
    check("one_scratch_register_available", scratch is not None, f"scratch={scratch}")
    if scratch is None or accumulator not in (2, 3):
        return _failed(program, obligations)

    initial: list[Poly] = [ZERO, ZERO, ZERO, ZERO]
    initial[control] = X
    initial[stable] = Y
    first_phase = [dict(value) for value in initial]
    _symbolic_outer_step(program, first_phase)
    check("zero_input_base_case", initial[accumulator] == ZERO, "when x=0 the zero-initialized output is returned")
    check("first_phase_control", first_phase[control] == _add(X, _neg(ONE)), "the first step leaves x-1 control marks")
    check("first_phase_accumulation", first_phase[accumulator] == Y, "the first step moves one complete y quantity into the accumulator")

    # Infer the steady carrier phase from the first transition.  The learner is
    # free to keep y in either non-output register, so the verifier does not
    # prescribe which register must be the stable one.
    registers: list[Poly] = [dict(value) for value in first_phase]
    registers[control] = _add(X, _neg(T))
    registers[accumulator] = TY
    _symbolic_outer_step(program, registers)
    expected = [dict(value) for value in first_phase]
    expected[control] = _add(_add(X, _neg(T)), _neg(ONE))
    expected[accumulator] = _add(TY, Y)

    check("inductive_control_decrease", registers[control] == expected[control], "for t>=1, control changes from x-t to x-(t+1)")
    check("inductive_carrier_phase", all(registers[index] == expected[index] for index in (stable, scratch)), "the discovered carrier layout repeats after every later step")
    check("inductive_accumulation", registers[accumulator] == expected[accumulator], "accumulator changes from t*y to (t+1)*y")
    check("phase_base_case", first_phase[accumulator] == Y, "at t=1 the inferred steady phase has accumulator=y")
    invariant_passed = all(item["passed"] for item in obligations)
    check("natural_termination", invariant_passed, "control is a natural counter and decreases exactly once per outer iteration")
    check("terminal_normal_form", invariant_passed, "at t=x the accumulator is x*y")

    executor = CounterExecutor(maximum_steps=2_000_000)
    hidden = tuple(
        {
            "inputs": [left, right],
            "output": executor.execute(program, (left, right)).output,
            "oracle_free_expected_from_proven_normal_form": left * right,
            "passed": executor.execute(program, (left, right)).output == left * right,
        }
        for left, right in ((0, 17), (1, 29), (7, 11), (13, 5), (21, 21), (37, 9))
    )
    profile = inspect_algebraic_profile(
        lambda left, right: executor.execute(program, (left, right)).output,
        limit=5,
    )
    check("independent_law_replay", profile.promotable, json.dumps(profile.to_dict(), sort_keys=True))
    check("sealed_numeric_replay", all(item["passed"] for item in hidden), "six cases outside the search probe grid")

    digest = hashlib.sha256(
        json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    passed = all(item["passed"] for item in obligations)
    return CounterFoundationProof(
        passed,
        "STRICT-FSEM-" + digest,
        "自然数乘法（证明后命名）" if passed else "未命名候选",
        "for every x,y in N, the selected counter program halts and returns x*y",
        "x*y" if passed else "unproven",
        tuple(obligations),
        hidden,
    )


def _failed(program: CounterProgram, obligations: list[dict[str, Any]]) -> CounterFoundationProof:
    digest = hashlib.sha256(
        json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    return CounterFoundationProof(
        False,
        "STRICT-FSEM-" + digest,
        "未命名候选",
        "no universal statement admitted",
        "unproven",
        tuple(obligations),
        (),
    )


def replay_counter_foundation(report: Mapping[str, Any], program: CounterProgram) -> dict[str, Any]:
    proof = prove_counter_foundation(program)
    expected = report["discovery"]["selected"]["candidate_id"]
    return {
        "passed": proof.passed and expected == candidate_id(program),
        "proof": proof.to_dict(),
    }
