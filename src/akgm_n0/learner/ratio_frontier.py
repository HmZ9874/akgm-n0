"""Anonymous search for a scale-invariant two-collection representation."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .foundation_kernel import FoundationRewardPolicy, unary_marks


STRATEGY_IDENTITY = 0
STRATEGY_SINGLE_CANCEL = 1
STRATEGY_DESCENDING_BLOCK = 2
STRATEGY_REPEATED_DIFFERENCE = 3
STRATEGY_REMAINDER_CHAIN = 4

ZERO_KEEP = 0
ZERO_UNIT_WHOLE = 1
ZERO_REJECT = 2


@dataclass(frozen=True, slots=True)
class RatioProgram:
    program_id: str
    part_slot: int
    whole_slot: int
    strategy_mode: int
    zero_mode: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "part_slot": self.part_slot,
            "whole_slot": self.whole_slot,
            "strategy_mode": self.strategy_mode,
            "zero_mode": self.zero_mode,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RatioProgram":
        return cls(
            str(value["program_id"]), int(value["part_slot"]),
            int(value["whole_slot"]), int(value["strategy_mode"]),
            int(value["zero_mode"]),
        )


@dataclass(frozen=True, slots=True)
class RatioExample:
    sources: tuple[tuple[str, ...], tuple[str, ...]]
    expected_part: tuple[str, ...]
    expected_whole: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RatioExecution:
    halted: bool
    output_part: tuple[str, ...]
    output_whole: tuple[str, ...]
    primitive_execution_tokens: int
    reduction_rounds: int


@dataclass(frozen=True, slots=True)
class RatioCandidate:
    program: RatioProgram
    exact: bool
    passed_example_count: int
    example_count: int
    execution_token_cost: int
    program_token_cost: int
    total_token_cost: int
    reward: int


@dataclass(frozen=True, slots=True)
class RatioSearchReport:
    task_id: str
    candidates_evaluated: int
    selected: RatioCandidate
    candidates: tuple[RatioCandidate, ...]


@dataclass(frozen=True, slots=True)
class RatioFoundationSemantic:
    semantic_id: str
    opcode: int
    program: RatioProgram
    dependency_semantic_ids: tuple[str, ...]
    source_task_ids: tuple[str, ...]
    structural_signature: str
    invented_dependency_signature: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id,
            "opcode": self.opcode,
            "program": self.program.to_dict(),
            "dependency_semantic_ids": list(self.dependency_semantic_ids),
            "source_task_ids": list(self.source_task_ids),
            "structural_signature": self.structural_signature,
            "invented_dependency_signature": self.invented_dependency_signature,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RatioFoundationSemantic":
        return cls(
            str(value["semantic_id"]), int(value["opcode"]),
            RatioProgram.from_dict(value["program"]),
            tuple(str(item) for item in value["dependency_semantic_ids"]),
            tuple(str(item) for item in value["source_task_ids"]),
            str(value["structural_signature"]),
            str(value["invented_dependency_signature"]),
        )


class RatioExecutor:
    def execute(self, program: RatioProgram, sources: Sequence[Sequence[str]]) -> RatioExecution:
        if len(sources) != 2:
            raise ValueError("ratio programs require two finite collections")
        part = len(sources[program.part_slot])
        whole = len(sources[program.whole_slot])
        if whole == 0:
            return RatioExecution(False, (), (), 1, 0)
        if part == 0:
            if program.zero_mode == ZERO_REJECT:
                return RatioExecution(False, (), (), 1, 0)
            denominator = 1 if program.zero_mode == ZERO_UNIT_WHOLE else whole
            return RatioExecution(True, (), unary_marks(denominator), 2 + denominator, 0)
        if program.strategy_mode == STRATEGY_IDENTITY:
            reduced_part, reduced_whole, tokens, rounds = part, whole, 1, 0
        elif program.strategy_mode == STRATEGY_SINGLE_CANCEL:
            common = min(part, whole)
            reduced_part, reduced_whole = part - common, whole - common
            tokens, rounds = 1 + 2 * common, 1
        elif program.strategy_mode == STRATEGY_DESCENDING_BLOCK:
            common, tokens, rounds = _descending_common_block(part, whole)
            reduced_part, reduced_whole = part // common, whole // common
        elif program.strategy_mode == STRATEGY_REPEATED_DIFFERENCE:
            common, tokens, rounds = _difference_chain(part, whole)
            reduced_part, reduced_whole = part // common, whole // common
        elif program.strategy_mode == STRATEGY_REMAINDER_CHAIN:
            common, tokens, rounds = _remainder_chain(part, whole)
            reduced_part, reduced_whole = part // common, whole // common
        else:
            raise ValueError("unknown ratio strategy")
        tokens += reduced_part + reduced_whole + 1
        return RatioExecution(
            True, unary_marks(reduced_part), unary_marks(reduced_whole), tokens, rounds
        )


class RatioSearch:
    def search(self, task_id: str, examples: Sequence[RatioExample]) -> RatioSearchReport:
        candidates = []
        for part_slot, strategy_mode, zero_mode in itertools.product(
            (0, 1),
            (STRATEGY_IDENTITY, STRATEGY_SINGLE_CANCEL, STRATEGY_DESCENDING_BLOCK,
             STRATEGY_REPEATED_DIFFERENCE, STRATEGY_REMAINDER_CHAIN),
            (ZERO_KEEP, ZERO_UNIT_WHOLE, ZERO_REJECT),
        ):
            program = compile_ratio_program(part_slot, 1 - part_slot, strategy_mode, zero_mode)
            passed = 0
            execution_tokens = 0
            for example in examples:
                execution = RatioExecutor().execute(program, example.sources)
                execution_tokens += execution.primitive_execution_tokens
                passed += (
                    execution.halted
                    and execution.output_part == example.expected_part
                    and execution.output_whole == example.expected_whole
                )
            exact = passed == len(examples)
            program_tokens = 5
            total, reward = FoundationRewardPolicy().score(
                exact=exact, passed_example_count=passed,
                execution_token_cost=execution_tokens, program_token_cost=program_tokens,
            )
            candidates.append(RatioCandidate(
                program, exact, passed, len(examples), execution_tokens,
                program_tokens, total, reward,
            ))
        exact_candidates = [item for item in candidates if item.exact]
        if not exact_candidates:
            raise ValueError(f"no exact normalized-pair program for {task_id}")
        exact_candidates.sort(key=lambda item: (-item.reward, item.program.program_id))
        return RatioSearchReport(task_id, len(candidates), exact_candidates[0], tuple(candidates))


class RatioSemanticInducer:
    def induce(
        self,
        report: RatioSearchReport,
        *,
        opcode: int,
        dependency_semantic_ids: Sequence[str],
        structural_signature: str,
        invented_dependency_signature: str,
    ) -> RatioFoundationSemantic:
        payload = {
            "opcode": opcode,
            "program_id": report.selected.program.program_id,
            "dependencies": list(dependency_semantic_ids),
            "source_tasks": [report.task_id],
            "structural_signature": structural_signature,
            "invented_dependency_signature": invented_dependency_signature,
        }
        semantic_id = "QSEM-" + _digest(payload)
        return RatioFoundationSemantic(
            semantic_id, opcode, report.selected.program,
            tuple(dependency_semantic_ids), (report.task_id,),
            structural_signature, invented_dependency_signature,
        )


def compile_ratio_program(part_slot: int, whole_slot: int, strategy_mode: int, zero_mode: int) -> RatioProgram:
    payload = {
        "part_slot": part_slot,
        "whole_slot": whole_slot,
        "strategy_mode": strategy_mode,
        "zero_mode": zero_mode,
    }
    return RatioProgram("QRP-" + _digest(payload), part_slot, whole_slot, strategy_mode, zero_mode)


def normalized_pair_observation(part: int, whole: int) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if whole <= 0:
        raise ValueError("whole cardinality must be positive")
    if part == 0:
        return (), unary_marks(1)
    common, _, _ = _remainder_chain(part, whole)
    return unary_marks(part // common), unary_marks(whole // common)


def _descending_common_block(left: int, right: int) -> tuple[int, int, int]:
    tokens = 0
    rounds = 0
    for candidate in range(min(left, right), 0, -1):
        rounds += 1
        tokens += 1 + left // candidate + right // candidate
        if left % candidate == 0 and right % candidate == 0:
            return candidate, tokens, rounds
    return 1, tokens, rounds


def _difference_chain(left: int, right: int) -> tuple[int, int, int]:
    x, y = left, right
    tokens = 0
    rounds = 0
    while x != y:
        rounds += 1
        common = min(x, y)
        tokens += 1 + common
        if x > y:
            x -= y
        else:
            y -= x
    return x, tokens, rounds


def _remainder_chain(left: int, right: int) -> tuple[int, int, int]:
    x, y = left, right
    tokens = 0
    rounds = 0
    while y:
        rounds += 1
        quotient, remainder = divmod(x, y)
        tokens += 2 + quotient + remainder
        x, y = y, remainder
    return x, tokens, rounds


def _digest(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()[:16]
