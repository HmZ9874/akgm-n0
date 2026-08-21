"""Anonymous interval-memory search over nonnegative rational observations."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Mapping, Sequence

from .foundation_kernel import FoundationRewardPolicy


INIT_UNIT_OR_VALUE = 0
INIT_VALUE_PLUS_UNIT = 1
INIT_DOUBLE_PLUS_UNIT = 2

PROBE_MIDDLE = 0
PROBE_LOWER_THIRD = 1
PROBE_UPPER_THIRD = 2

TEST_SELF_PRODUCT = 0
TEST_DIRECT_VALUE = 1
TEST_DOUBLE_VALUE = 2

UPDATE_NORMAL = 0
UPDATE_REVERSED = 1


@dataclass(frozen=True, slots=True)
class ApproximationProgram:
    program_id: str
    init_mode: int
    probe_mode: int
    test_mode: int
    update_mode: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "init_mode": self.init_mode,
            "probe_mode": self.probe_mode,
            "test_mode": self.test_mode,
            "update_mode": self.update_mode,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ApproximationProgram":
        return cls(
            str(value["program_id"]), int(value["init_mode"]),
            int(value["probe_mode"]), int(value["test_mode"]),
            int(value["update_mode"]),
        )


@dataclass(frozen=True, slots=True)
class ApproximationExample:
    value_pair: tuple[int, int]
    rounds: int
    expected_lower: tuple[int, int]
    expected_upper: tuple[int, int]


@dataclass(frozen=True, slots=True)
class ApproximationExecution:
    halted: bool
    lower: tuple[int, int]
    upper: tuple[int, int]
    primitive_execution_tokens: int
    rounds_completed: int


@dataclass(frozen=True, slots=True)
class ApproximationCandidate:
    program: ApproximationProgram
    exact: bool
    passed_example_count: int
    example_count: int
    execution_token_cost: int
    program_token_cost: int
    total_token_cost: int
    reward: int


@dataclass(frozen=True, slots=True)
class ApproximationSearchReport:
    task_id: str
    candidates_evaluated: int
    selected: ApproximationCandidate
    candidates: tuple[ApproximationCandidate, ...]


@dataclass(frozen=True, slots=True)
class ApproximationFoundationSemantic:
    semantic_id: str
    opcode: int
    program: ApproximationProgram
    dependency_semantic_ids: tuple[str, ...]
    source_task_ids: tuple[str, ...]
    invented_dependency_signature: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id,
            "opcode": self.opcode,
            "program": self.program.to_dict(),
            "dependency_semantic_ids": list(self.dependency_semantic_ids),
            "source_task_ids": list(self.source_task_ids),
            "invented_dependency_signature": self.invented_dependency_signature,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ApproximationFoundationSemantic":
        return cls(
            str(value["semantic_id"]), int(value["opcode"]),
            ApproximationProgram.from_dict(value["program"]),
            tuple(map(str, value["dependency_semantic_ids"])),
            tuple(map(str, value["source_task_ids"])),
            str(value["invented_dependency_signature"]),
        )


class ApproximationExecutor:
    def execute(
        self, program: ApproximationProgram, value_pair: tuple[int, int], rounds: int
    ) -> ApproximationExecution:
        if value_pair[1] <= 0 or value_pair[0] < 0 or rounds < 0:
            return ApproximationExecution(False, (0, 0), (0, 0), 1, 0)
        value = Fraction(*value_pair)
        lower = Fraction(0)
        upper = {
            INIT_UNIT_OR_VALUE: max(Fraction(1), value),
            INIT_VALUE_PLUS_UNIT: value + 1,
            INIT_DOUBLE_PLUS_UNIT: 2 * value + 1,
        }[program.init_mode]
        tokens = 4 + abs(value.numerator) + value.denominator
        for _ in range(rounds):
            probe = {
                PROBE_MIDDLE: (lower + upper) / 2,
                PROBE_LOWER_THIRD: (2 * lower + upper) / 3,
                PROBE_UPPER_THIRD: (lower + 2 * upper) / 3,
            }[program.probe_mode]
            accepted = {
                TEST_SELF_PRODUCT: probe * probe <= value,
                TEST_DIRECT_VALUE: probe <= value,
                TEST_DOUBLE_VALUE: probe + probe <= value,
            }[program.test_mode]
            if program.update_mode == UPDATE_REVERSED:
                accepted = not accepted
            if accepted:
                lower = probe
            else:
                upper = probe
            tokens += 8 + abs(probe.numerator) + probe.denominator
        return ApproximationExecution(
            True,
            (lower.numerator, lower.denominator),
            (upper.numerator, upper.denominator),
            tokens,
            rounds,
        )


class ApproximationMemorySearch:
    def search(
        self, task_id: str, examples: Sequence[ApproximationExample]
    ) -> ApproximationSearchReport:
        candidates = []
        for init_mode, probe_mode, test_mode, update_mode in itertools.product(
            range(3), range(3), range(3), range(2)
        ):
            program = compile_approximation_program(init_mode, probe_mode, test_mode, update_mode)
            passed = 0
            execution_tokens = 0
            for example in examples:
                execution = ApproximationExecutor().execute(
                    program, example.value_pair, example.rounds
                )
                execution_tokens += execution.primitive_execution_tokens
                passed += (
                    execution.halted
                    and execution.lower == example.expected_lower
                    and execution.upper == example.expected_upper
                )
            exact = passed == len(examples)
            program_tokens = 5
            total, reward = FoundationRewardPolicy().score(
                exact=exact,
                passed_example_count=passed,
                execution_token_cost=execution_tokens,
                program_token_cost=program_tokens,
            )
            candidates.append(
                ApproximationCandidate(
                    program, exact, passed, len(examples), execution_tokens,
                    program_tokens, total, reward,
                )
            )
        exact = [candidate for candidate in candidates if candidate.exact]
        if not exact:
            raise ValueError(f"no exact interval-memory program for {task_id}")
        exact.sort(key=lambda candidate: (-candidate.reward, candidate.program.program_id))
        return ApproximationSearchReport(task_id, len(candidates), exact[0], tuple(candidates))


class ApproximationSemanticInducer:
    def induce(
        self,
        report: ApproximationSearchReport,
        *,
        opcode: int,
        dependency_semantic_ids: Sequence[str],
        invented_dependency_signature: str,
    ) -> ApproximationFoundationSemantic:
        payload = {
            "opcode": opcode,
            "program_id": report.selected.program.program_id,
            "dependencies": list(dependency_semantic_ids),
            "source_tasks": [report.task_id],
            "invented_dependency_signature": invented_dependency_signature,
        }
        return ApproximationFoundationSemantic(
            "ISEM-" + _digest(payload), opcode, report.selected.program,
            tuple(dependency_semantic_ids), (report.task_id,), invented_dependency_signature,
        )


def compile_approximation_program(
    init_mode: int, probe_mode: int, test_mode: int, update_mode: int
) -> ApproximationProgram:
    payload = {
        "init_mode": init_mode,
        "probe_mode": probe_mode,
        "test_mode": test_mode,
        "update_mode": update_mode,
    }
    return ApproximationProgram(
        "IAP-" + _digest(payload), init_mode, probe_mode, test_mode, update_mode
    )


def interval_refinement(
    value_pair: tuple[int, int], rounds: int
) -> tuple[tuple[int, int], tuple[int, int]]:
    program = compile_approximation_program(
        INIT_UNIT_OR_VALUE, PROBE_MIDDLE, TEST_SELF_PRODUCT, UPDATE_NORMAL
    )
    result = ApproximationExecutor().execute(program, value_pair, rounds)
    if not result.halted:
        raise ValueError("invalid refinement input")
    return result.lower, result.upper


def _digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
