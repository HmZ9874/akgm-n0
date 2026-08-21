"""Anonymous order-canonicalization invention for unordered selections."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .autonomous_frontier import word_token
from .foundation_kernel import FoundationRewardPolicy


SEED_UNIT = 0
SEED_BASE = 1
UPDATE_KEEP = 0
UPDATE_EXPAND = 1
UPDATE_REPLACE = 2
ORDER_NONE = 0
ORDER_AFTER_LAST = 1
ORDER_BEFORE_LAST = 2
ORDER_AFTER_FIRST = 3


@dataclass(frozen=True, slots=True)
class CanonicalProgram:
    program_id: str
    controller_slot: int
    base_slot: int
    seed_mode: int
    update_mode: int
    order_mode: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "controller_slot": self.controller_slot,
            "base_slot": self.base_slot,
            "seed_mode": self.seed_mode,
            "update_mode": self.update_mode,
            "order_mode": self.order_mode,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CanonicalProgram":
        return cls(
            str(value["program_id"]), int(value["controller_slot"]),
            int(value["base_slot"]), int(value["seed_mode"]),
            int(value["update_mode"]), int(value["order_mode"]),
        )


@dataclass(frozen=True, slots=True)
class CanonicalExample:
    sources: tuple[tuple[str, ...], tuple[str, ...]]
    expected_output: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CanonicalExecution:
    halted: bool
    output: tuple[str, ...]
    primitive_execution_tokens: int
    order_comparison_tokens: int


@dataclass(frozen=True, slots=True)
class CanonicalCandidate:
    program: CanonicalProgram
    exact: bool
    passed_example_count: int
    example_count: int
    execution_token_cost: int
    program_token_cost: int
    total_token_cost: int
    reward: int


@dataclass(frozen=True, slots=True)
class CanonicalSearchReport:
    task_id: str
    candidates_evaluated: int
    selected: CanonicalCandidate
    candidates: tuple[CanonicalCandidate, ...]


@dataclass(frozen=True, slots=True)
class CanonicalFoundationSemantic:
    semantic_id: str
    opcode: int
    program: CanonicalProgram
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
    def from_dict(cls, value: Mapping[str, Any]) -> "CanonicalFoundationSemantic":
        return cls(
            str(value["semantic_id"]), int(value["opcode"]),
            CanonicalProgram.from_dict(value["program"]),
            tuple(str(item) for item in value["dependency_semantic_ids"]),
            tuple(str(item) for item in value["source_task_ids"]),
            str(value["structural_signature"]),
            str(value["invented_dependency_signature"]),
        )


class CanonicalExecutor:
    def execute(self, program: CanonicalProgram, sources: Sequence[Sequence[str]]) -> CanonicalExecution:
        if len(sources) != 2:
            raise ValueError("canonical programs require two finite collections")
        controller = tuple(sources[program.controller_slot])
        base = tuple(sources[program.base_slot])
        positions = {item: index for index, item in enumerate(base)}
        if len(positions) != len(base):
            raise ValueError("base objects must be distinct")
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
                        allowed, checked = _allows(program.order_mode, prefix, item, positions)
                        comparisons += checked
                        tokens += 2 + checked
                        if allowed:
                            expanded.append(prefix + (item,))
                state = expanded
            else:
                raise ValueError("unknown update mode")
        tokens += len(state) + 1
        return CanonicalExecution(
            True, tuple(word_token(item) for item in state), tokens, comparisons
        )


class CanonicalExpansionSearch:
    def search(self, task_id: str, examples: Sequence[CanonicalExample]) -> CanonicalSearchReport:
        candidates = []
        for controller_slot, seed_mode, update_mode, order_mode in itertools.product(
            (0, 1), (SEED_UNIT, SEED_BASE),
            (UPDATE_KEEP, UPDATE_EXPAND, UPDATE_REPLACE),
            (ORDER_NONE, ORDER_AFTER_LAST, ORDER_BEFORE_LAST, ORDER_AFTER_FIRST),
        ):
            program = compile_canonical_program(
                controller_slot, 1 - controller_slot, seed_mode, update_mode, order_mode
            )
            passed = 0
            execution_tokens = 0
            for example in examples:
                execution = CanonicalExecutor().execute(program, example.sources)
                execution_tokens += execution.primitive_execution_tokens
                passed += execution.halted and execution.output == example.expected_output
            exact = passed == len(examples)
            program_tokens = 6
            total, reward = FoundationRewardPolicy().score(
                exact=exact, passed_example_count=passed,
                execution_token_cost=execution_tokens, program_token_cost=program_tokens,
            )
            candidates.append(CanonicalCandidate(
                program, exact, passed, len(examples), execution_tokens,
                program_tokens, total, reward,
            ))
        exact_candidates = [item for item in candidates if item.exact]
        if not exact_candidates:
            raise ValueError(f"no exact order canonicalizer for {task_id}")
        exact_candidates.sort(key=lambda item: (-item.reward, item.program.program_id))
        return CanonicalSearchReport(task_id, len(candidates), exact_candidates[0], tuple(candidates))


class CanonicalSemanticInducer:
    def induce(
        self,
        report: CanonicalSearchReport,
        *,
        opcode: int,
        dependency_semantic_ids: Sequence[str],
        structural_signature: str,
        invented_dependency_signature: str,
    ) -> CanonicalFoundationSemantic:
        payload = {
            "opcode": opcode,
            "program_id": report.selected.program.program_id,
            "dependencies": list(dependency_semantic_ids),
            "source_tasks": [report.task_id],
            "structural_signature": structural_signature,
            "invented_dependency_signature": invented_dependency_signature,
        }
        semantic_id = "CSEM-" + _digest(payload)
        return CanonicalFoundationSemantic(
            semantic_id, opcode, report.selected.program,
            tuple(dependency_semantic_ids), (report.task_id,),
            structural_signature, invented_dependency_signature,
        )


def compile_canonical_program(
    controller_slot: int,
    base_slot: int,
    seed_mode: int,
    update_mode: int,
    order_mode: int,
) -> CanonicalProgram:
    payload = {
        "controller_slot": controller_slot,
        "base_slot": base_slot,
        "seed_mode": seed_mode,
        "update_mode": update_mode,
        "order_mode": order_mode,
    }
    return CanonicalProgram(
        "CAP-" + _digest(payload), controller_slot, base_slot,
        seed_mode, update_mode, order_mode,
    )


def canonical_subset_observation(base: Sequence[str], controller: Sequence[str]) -> tuple[str, ...]:
    length = len(controller)
    return tuple(word_token(items) for items in itertools.combinations(base, length))


def _allows(
    mode: int,
    prefix: tuple[str, ...],
    item: str,
    positions: Mapping[str, int],
) -> tuple[bool, int]:
    if mode == ORDER_NONE:
        return True, 0
    if not prefix:
        return True, 0
    if mode == ORDER_AFTER_LAST:
        return positions[item] > positions[prefix[-1]], 1
    if mode == ORDER_BEFORE_LAST:
        return positions[item] < positions[prefix[-1]], 1
    if mode == ORDER_AFTER_FIRST:
        return positions[item] > positions[prefix[0]], 1
    raise ValueError("unknown order mode")


def _digest(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()[:16]
