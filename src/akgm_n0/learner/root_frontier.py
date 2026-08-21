"""Anonymous search for an exact boundary extractor over signed rational pairs."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .foundation_kernel import FoundationRewardPolicy


EXTRACT_IDENTITY = 0
EXTRACT_UNIT = 1
EXTRACT_SUCCESSIVE_BOUNDARY = 2
EXTRACT_REPEATED_PAIR_SCAN = 3
EXTRACT_HALF = 4

NEGATIVE_REJECT = 0
NEGATIVE_ABSOLUTE = 1


@dataclass(frozen=True, slots=True)
class RootProgram:
    program_id: str
    numerator_mode: int
    denominator_mode: int
    negative_mode: int
    require_exact: bool
    preprocess_reduce: bool
    token_accounting_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        result = {
            "program_id": self.program_id,
            "numerator_mode": self.numerator_mode,
            "denominator_mode": self.denominator_mode,
            "negative_mode": self.negative_mode,
            "require_exact": self.require_exact,
            "preprocess_reduce": self.preprocess_reduce,
        }
        if self.token_accounting_version != 0:
            result["token_accounting_version"] = self.token_accounting_version
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RootProgram":
        return cls(
            str(value["program_id"]),
            int(value["numerator_mode"]),
            int(value["denominator_mode"]),
            int(value["negative_mode"]),
            bool(value["require_exact"]),
            bool(value["preprocess_reduce"]),
            int(value.get("token_accounting_version", 0)),
        )


@dataclass(frozen=True, slots=True)
class RootExample:
    value_pair: tuple[int, int]
    expect_halted: bool
    expected_output: tuple[int, int]


@dataclass(frozen=True, slots=True)
class RootExecution:
    halted: bool
    output: tuple[int, int]
    primitive_execution_tokens: int
    numerator_rounds: int
    denominator_rounds: int


@dataclass(frozen=True, slots=True)
class RootCandidate:
    program: RootProgram
    exact: bool
    passed_example_count: int
    example_count: int
    execution_token_cost: int
    program_token_cost: int
    total_token_cost: int
    reward: int


@dataclass(frozen=True, slots=True)
class RootSearchReport:
    task_id: str
    candidates_evaluated: int
    selected: RootCandidate
    candidates: tuple[RootCandidate, ...]


@dataclass(frozen=True, slots=True)
class RootFoundationSemantic:
    semantic_id: str
    opcode: int
    program: RootProgram
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
    def from_dict(cls, value: Mapping[str, Any]) -> "RootFoundationSemantic":
        return cls(
            str(value["semantic_id"]),
            int(value["opcode"]),
            RootProgram.from_dict(value["program"]),
            tuple(map(str, value["dependency_semantic_ids"])),
            tuple(map(str, value["source_task_ids"])),
            str(value["invented_dependency_signature"]),
        )


class RootExecutor:
    def execute(self, program: RootProgram, value_pair: tuple[int, int]) -> RootExecution:
        numerator, denominator = value_pair
        if denominator <= 0:
            return RootExecution(False, (0, 0), 1, 0, 0)
        if numerator < 0:
            if program.negative_mode == NEGATIVE_REJECT:
                return RootExecution(False, (0, 0), 1, 0, 0)
            numerator = abs(numerator)
        tokens = 2
        if program.preprocess_reduce:
            common = math.gcd(abs(numerator), denominator)
            numerator //= common
            denominator //= common
            tokens += common + 2
        left, left_exact, left_tokens, left_rounds = _extract(program.numerator_mode, numerator, program.token_accounting_version)
        right, right_exact, right_tokens, right_rounds = _extract(program.denominator_mode, denominator, program.token_accounting_version)
        tokens += left_tokens + right_tokens
        if program.require_exact and not (left_exact and right_exact):
            return RootExecution(False, (0, 0), tokens + 1, left_rounds, right_rounds)
        if right == 0:
            return RootExecution(False, (0, 0), tokens + 1, left_rounds, right_rounds)
        common = math.gcd(left, right)
        output = (0, 1) if left == 0 else (left // common, right // common)
        return RootExecution(True, output, tokens + common + 2, left_rounds, right_rounds)


class RootBoundarySearch:
    def search(self, task_id: str, examples: Sequence[RootExample]) -> RootSearchReport:
        candidates = []
        for numerator_mode, denominator_mode, negative_mode, require_exact, preprocess_reduce in itertools.product(
            range(5), range(5), range(2), (False, True), (False, True)
        ):
            program = compile_root_program(
                numerator_mode, denominator_mode, negative_mode, require_exact, preprocess_reduce
            )
            passed = 0
            execution_tokens = 0
            for example in examples:
                execution = RootExecutor().execute(program, example.value_pair)
                execution_tokens += execution.primitive_execution_tokens
                passed += (
                    execution.halted == example.expect_halted
                    and (not example.expect_halted or execution.output == example.expected_output)
                )
            exact = passed == len(examples)
            program_tokens = 6
            total, reward = FoundationRewardPolicy().score(
                exact=exact,
                passed_example_count=passed,
                execution_token_cost=execution_tokens,
                program_token_cost=program_tokens,
            )
            candidates.append(
                RootCandidate(
                    program, exact, passed, len(examples), execution_tokens,
                    program_tokens, total, reward,
                )
            )
        exact = [candidate for candidate in candidates if candidate.exact]
        if not exact:
            raise ValueError(f"no exact boundary extractor for {task_id}")
        exact.sort(key=lambda candidate: (-candidate.reward, candidate.program.program_id))
        return RootSearchReport(task_id, len(candidates), exact[0], tuple(candidates))


class RootSemanticInducer:
    def induce(
        self,
        report: RootSearchReport,
        *,
        opcode: int,
        dependency_semantic_ids: Sequence[str],
        invented_dependency_signature: str,
    ) -> RootFoundationSemantic:
        payload = {
            "opcode": opcode,
            "program_id": report.selected.program.program_id,
            "dependencies": list(dependency_semantic_ids),
            "source_tasks": [report.task_id],
            "invented_dependency_signature": invented_dependency_signature,
        }
        return RootFoundationSemantic(
            "RSEM-" + _digest(payload), opcode, report.selected.program,
            tuple(dependency_semantic_ids), (report.task_id,), invented_dependency_signature,
        )


def compile_root_program(
    numerator_mode: int,
    denominator_mode: int,
    negative_mode: int,
    require_exact: bool,
    preprocess_reduce: bool,
    token_accounting_version: int = 1,
) -> RootProgram:
    payload = {
        "numerator_mode": numerator_mode,
        "denominator_mode": denominator_mode,
        "negative_mode": negative_mode,
        "require_exact": require_exact,
        "preprocess_reduce": preprocess_reduce,
    }
    if token_accounting_version != 0:
        payload["token_accounting_version"] = token_accounting_version
    return RootProgram(
        "RBP-" + _digest(payload), numerator_mode, denominator_mode,
        negative_mode, require_exact, preprocess_reduce,
        token_accounting_version,
    )


def exact_rational_boundary(value_pair: tuple[int, int]) -> tuple[int, int] | None:
    numerator, denominator = value_pair
    if numerator < 0 or denominator <= 0:
        return None
    common = math.gcd(numerator, denominator)
    numerator //= common
    denominator //= common
    left, right = math.isqrt(numerator), math.isqrt(denominator)
    if left * left != numerator or right * right != denominator:
        return None
    return (0, 1) if left == 0 else (left, right)


def _extract(mode: int, value: int, token_accounting_version: int = 1) -> tuple[int, bool, int, int]:
    if mode == EXTRACT_IDENTITY:
        return value, True, 1, 0
    if mode == EXTRACT_UNIT:
        return 1, value in (0, 1), 1, 0
    if mode == EXTRACT_HALF:
        return value // 2, value % 2 == 0, 2 + value // 2, value // 2
    if mode == EXTRACT_SUCCESSIVE_BOUNDARY:
        remainder, boundary, count, tokens = value, 1, 0, 1
        while remainder > 0:
            remainder -= boundary
            boundary += 2
            count += 1
            tokens += 3 + count
        return count, remainder == 0, tokens, count
    if mode == EXTRACT_REPEATED_PAIR_SCAN:
        tokens = 1
        for count in range(value + 1):
            accumulated = 0
            for _ in range(count):
                accumulated += count
                tokens += 1
            tokens += 1
            if accumulated >= value:
                charged = tokens if token_accounting_version >= 1 else 3 + count * count
                rounds = count + 1 if token_accounting_version >= 1 else count
                return count, accumulated == value, charged, rounds
        return value, False, tokens, value + 1
    raise ValueError("unknown extraction mode")


def _digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
