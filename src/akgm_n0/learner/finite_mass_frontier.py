"""Anonymous search for a normalized mass assignment on finite subcollections."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .foundation_kernel import FoundationRewardPolicy


NUM_EVENT = 0
NUM_COMPLEMENT = 1
NUM_WHOLE = 2
NUM_UNIT = 3
DEN_WHOLE = 0
DEN_EVENT = 1
DEN_UNIT = 2


@dataclass(frozen=True, slots=True)
class MassProgram:
    program_id: str
    numerator_mode: int
    denominator_mode: int
    normalize: bool

    def to_dict(self) -> dict[str, Any]:
        return {"program_id": self.program_id, "numerator_mode": self.numerator_mode,
                "denominator_mode": self.denominator_mode, "normalize": self.normalize}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MassProgram":
        return cls(str(value["program_id"]), int(value["numerator_mode"]),
                   int(value["denominator_mode"]), bool(value["normalize"]))


@dataclass(frozen=True, slots=True)
class MassExample:
    event_count: int
    whole_count: int
    expected_pair: tuple[int, int]


@dataclass(frozen=True, slots=True)
class MassExecution:
    halted: bool
    output_pair: tuple[int, int]
    primitive_execution_tokens: int


@dataclass(frozen=True, slots=True)
class MassCandidate:
    program: MassProgram
    exact: bool
    passed_example_count: int
    example_count: int
    execution_token_cost: int
    program_token_cost: int
    total_token_cost: int
    reward: int


@dataclass(frozen=True, slots=True)
class MassSearchReport:
    task_id: str
    candidates_evaluated: int
    selected: MassCandidate
    candidates: tuple[MassCandidate, ...]


@dataclass(frozen=True, slots=True)
class FiniteMassSemantic:
    semantic_id: str
    program: MassProgram
    dependency_semantic_ids: tuple[str, ...]
    source_task_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"semantic_id": self.semantic_id, "program": self.program.to_dict(),
                "dependency_semantic_ids": list(self.dependency_semantic_ids),
                "source_task_ids": list(self.source_task_ids)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FiniteMassSemantic":
        return cls(str(value["semantic_id"]), MassProgram.from_dict(value["program"]),
                   tuple(str(item) for item in value["dependency_semantic_ids"]),
                   tuple(str(item) for item in value["source_task_ids"]))


class MassExecutor:
    def execute(self, program: MassProgram, event_count: int, whole_count: int) -> MassExecution:
        if whole_count <= 0 or event_count < 0 or event_count > whole_count:
            return MassExecution(False, (0, 0), 1)
        numerator = {
            NUM_EVENT: event_count,
            NUM_COMPLEMENT: whole_count - event_count,
            NUM_WHOLE: whole_count,
            NUM_UNIT: 1,
        }[program.numerator_mode]
        denominator = {
            DEN_WHOLE: whole_count,
            DEN_EVENT: event_count,
            DEN_UNIT: 1,
        }[program.denominator_mode]
        if denominator == 0:
            return MassExecution(False, (0, 0), 2)
        tokens = 3 + numerator + denominator
        if program.normalize:
            common = math.gcd(numerator, denominator)
            if numerator == 0:
                pair = (0, 1)
            else:
                pair = (numerator // common, denominator // common)
            tokens += 2 + common
        else:
            pair = (numerator, denominator)
        return MassExecution(True, pair, tokens)


class FiniteMassSearch:
    def search(self, task_id: str, examples: Sequence[MassExample]) -> MassSearchReport:
        candidates = []
        for numerator_mode, denominator_mode, normalize in itertools.product(
            (NUM_EVENT, NUM_COMPLEMENT, NUM_WHOLE, NUM_UNIT),
            (DEN_WHOLE, DEN_EVENT, DEN_UNIT), (False, True),
        ):
            program = compile_mass_program(numerator_mode, denominator_mode, normalize)
            passed = 0
            tokens = 0
            for example in examples:
                result = MassExecutor().execute(program, example.event_count, example.whole_count)
                tokens += result.primitive_execution_tokens
                passed += result.halted and result.output_pair == example.expected_pair
            exact = passed == len(examples)
            total, reward = FoundationRewardPolicy().score(
                exact=exact, passed_example_count=passed,
                execution_token_cost=tokens, program_token_cost=4,
            )
            candidates.append(MassCandidate(program, exact, passed, len(examples), tokens, 4, total, reward))
        exact_candidates = [item for item in candidates if item.exact]
        if not exact_candidates:
            raise ValueError(f"no exact finite mass program for {task_id}")
        exact_candidates.sort(key=lambda item: (-item.reward, item.program.program_id))
        return MassSearchReport(task_id, len(candidates), exact_candidates[0], tuple(candidates))


class FiniteMassInducer:
    def induce(self, report: MassSearchReport, *, dependency_semantic_ids: Sequence[str]) -> FiniteMassSemantic:
        payload = {"program_id": report.selected.program.program_id,
                   "dependencies": list(dependency_semantic_ids), "source_tasks": [report.task_id]}
        semantic_id = "MSEM-" + _digest(payload)
        return FiniteMassSemantic(semantic_id, report.selected.program,
                                  tuple(dependency_semantic_ids), (report.task_id,))


def compile_mass_program(numerator_mode: int, denominator_mode: int, normalize: bool) -> MassProgram:
    payload = {"numerator_mode": numerator_mode, "denominator_mode": denominator_mode,
               "normalize": normalize}
    return MassProgram("MAP-" + _digest(payload), numerator_mode, denominator_mode, normalize)


def normalized_event_mass(event_count: int, whole_count: int) -> tuple[int, int]:
    if whole_count <= 0 or not 0 <= event_count <= whole_count:
        raise ValueError("invalid finite event cardinalities")
    if event_count == 0: return (0, 1)
    common = math.gcd(event_count, whole_count)
    return event_count // common, whole_count // common


def binomial_mass(row_size: int, marked_count: int) -> tuple[int, int]:
    if not 0 <= marked_count <= row_size:
        return (0, 1)
    return normalized_event_mass(math.comb(row_size, marked_count), 2 ** row_size)


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
