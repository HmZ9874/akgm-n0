"""Anonymous memory-mechanism invention for a blocked structural frontier."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .foundation_kernel import FoundationRewardPolicy
from .autonomous_frontier import word_token


SEED_UNIT = 0
SEED_BASE = 1

UPDATE_KEEP = 0
UPDATE_EXPAND = 1
UPDATE_REPLACE = 2

FILTER_NONE = 0
FILTER_DIFFERENT_FROM_LAST = 1
FILTER_DIFFERENT_FROM_FIRST = 2
FILTER_NOT_IN_RECORD = 3


@dataclass(frozen=True, slots=True)
class DistinctProgram:
    program_id: str
    controller_slot: int
    base_slot: int
    seed_mode: int
    update_mode: int
    filter_mode: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "controller_slot": self.controller_slot,
            "base_slot": self.base_slot,
            "seed_mode": self.seed_mode,
            "update_mode": self.update_mode,
            "filter_mode": self.filter_mode,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DistinctProgram":
        return cls(
            str(value["program_id"]), int(value["controller_slot"]),
            int(value["base_slot"]), int(value["seed_mode"]),
            int(value["update_mode"]), int(value["filter_mode"]),
        )


@dataclass(frozen=True, slots=True)
class DistinctExample:
    sources: tuple[tuple[str, ...], tuple[str, ...]]
    expected_output: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DistinctExecution:
    halted: bool
    output: tuple[str, ...]
    primitive_execution_tokens: int
    equality_comparison_tokens: int


@dataclass(frozen=True, slots=True)
class DistinctCandidate:
    program: DistinctProgram
    exact: bool
    passed_example_count: int
    example_count: int
    execution_token_cost: int
    program_token_cost: int
    total_token_cost: int
    reward: int


@dataclass(frozen=True, slots=True)
class DistinctSearchReport:
    task_id: str
    candidates_evaluated: int
    selected: DistinctCandidate
    candidates: tuple[DistinctCandidate, ...]


@dataclass(frozen=True, slots=True)
class DistinctFoundationSemantic:
    semantic_id: str
    opcode: int
    program: DistinctProgram
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
    def from_dict(cls, value: Mapping[str, Any]) -> "DistinctFoundationSemantic":
        return cls(
            str(value["semantic_id"]), int(value["opcode"]),
            DistinctProgram.from_dict(value["program"]),
            tuple(str(item) for item in value["dependency_semantic_ids"]),
            tuple(str(item) for item in value["source_task_ids"]),
            str(value["structural_signature"]),
            str(value["invented_dependency_signature"]),
        )


class DistinctExecutor:
    def execute(self, program: DistinctProgram, sources: Sequence[Sequence[str]]) -> DistinctExecution:
        if len(sources) != 2:
            raise ValueError("distinct programs require two finite collections")
        controller = tuple(sources[program.controller_slot])
        base = tuple(sources[program.base_slot])
        if program.seed_mode == SEED_UNIT:
            state: list[tuple[str, ...]] = [()]
            tokens = 1
        elif program.seed_mode == SEED_BASE:
            state = [(item,) for item in base]
            tokens = 1 + len(base)
        else:
            raise ValueError("unknown seed mode")
        comparisons = 0
        for _ in controller:
            tokens += 1
            if program.update_mode == UPDATE_KEEP:
                tokens += len(state)
            elif program.update_mode == UPDATE_REPLACE:
                state = [(item,) for item in base]
                tokens += len(base)
            elif program.update_mode == UPDATE_EXPAND:
                expanded = []
                for prefix in state:
                    tokens += 1
                    for item in base:
                        allowed, checked = _allows(program.filter_mode, prefix, item)
                        comparisons += checked
                        tokens += 2 + checked
                        if allowed:
                            expanded.append(prefix + (item,))
                state = expanded
            else:
                raise ValueError("unknown update mode")
        tokens += len(state) + 1
        return DistinctExecution(
            True, tuple(word_token(item) for item in state), tokens, comparisons
        )


class DistinctExpansionSearch:
    def search(self, task_id: str, examples: Sequence[DistinctExample]) -> DistinctSearchReport:
        candidates = []
        for controller_slot, seed_mode, update_mode, filter_mode in itertools.product(
            (0, 1), (SEED_UNIT, SEED_BASE),
            (UPDATE_KEEP, UPDATE_EXPAND, UPDATE_REPLACE),
            (FILTER_NONE, FILTER_DIFFERENT_FROM_LAST, FILTER_DIFFERENT_FROM_FIRST, FILTER_NOT_IN_RECORD),
        ):
            program = compile_distinct_program(
                controller_slot, 1 - controller_slot, seed_mode, update_mode, filter_mode
            )
            passed = 0
            execution_tokens = 0
            for example in examples:
                execution = DistinctExecutor().execute(program, example.sources)
                execution_tokens += execution.primitive_execution_tokens
                passed += execution.halted and execution.output == example.expected_output
            exact = passed == len(examples)
            program_tokens = 6
            total, reward = FoundationRewardPolicy().score(
                exact=exact, passed_example_count=passed,
                execution_token_cost=execution_tokens, program_token_cost=program_tokens,
            )
            candidates.append(DistinctCandidate(
                program, exact, passed, len(examples), execution_tokens,
                program_tokens, total, reward,
            ))
        exact_candidates = [item for item in candidates if item.exact]
        if not exact_candidates:
            raise ValueError(f"no exact memory mechanism for {task_id}")
        exact_candidates.sort(key=lambda item: (-item.reward, item.program.program_id))
        return DistinctSearchReport(task_id, len(candidates), exact_candidates[0], tuple(candidates))


class DistinctSemanticInducer:
    def induce(
        self,
        report: DistinctSearchReport,
        *,
        opcode: int,
        dependency_semantic_ids: Sequence[str],
        structural_signature: str,
        invented_dependency_signature: str,
    ) -> DistinctFoundationSemantic:
        payload = {
            "opcode": opcode,
            "program_id": report.selected.program.program_id,
            "dependencies": list(dependency_semantic_ids),
            "source_tasks": [report.task_id],
            "structural_signature": structural_signature,
            "invented_dependency_signature": invented_dependency_signature,
        }
        semantic_id = "XSEM-" + _digest(payload)
        return DistinctFoundationSemantic(
            semantic_id, opcode, report.selected.program,
            tuple(dependency_semantic_ids), (report.task_id,),
            structural_signature, invented_dependency_signature,
        )


def compile_distinct_program(
    controller_slot: int,
    base_slot: int,
    seed_mode: int,
    update_mode: int,
    filter_mode: int,
) -> DistinctProgram:
    payload = {
        "controller_slot": controller_slot,
        "base_slot": base_slot,
        "seed_mode": seed_mode,
        "update_mode": update_mode,
        "filter_mode": filter_mode,
    }
    return DistinctProgram(
        "DXP-" + _digest(payload), controller_slot, base_slot,
        seed_mode, update_mode, filter_mode,
    )


def distinct_word_observation(base: Sequence[str], controller: Sequence[str]) -> tuple[str, ...]:
    words: tuple[tuple[str, ...], ...] = ((),)
    for _ in controller:
        words = tuple(
            prefix + (item,)
            for prefix in words
            for item in base
            if item not in prefix
        )
    return tuple(word_token(item) for item in words)


def _allows(mode: int, prefix: tuple[str, ...], item: str) -> tuple[bool, int]:
    if mode == FILTER_NONE:
        return True, 0
    if mode == FILTER_DIFFERENT_FROM_LAST:
        return (not prefix or prefix[-1] != item), int(bool(prefix))
    if mode == FILTER_DIFFERENT_FROM_FIRST:
        return (not prefix or prefix[0] != item), int(bool(prefix))
    if mode == FILTER_NOT_IN_RECORD:
        for checked, existing in enumerate(prefix, 1):
            if existing == item:
                return False, checked
        return True, len(prefix)
    raise ValueError("unknown filter mode")


def _digest(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()[:16]
