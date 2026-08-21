"""Deterministic Gen 0 program enumeration and generic numeric scoring."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from statistics import fmean
from typing import Any, Callable, Iterable, Mapping, Sequence

from .dsl import (
    ExecutionContext,
    NumericExecutionError,
    ProgramExecutor,
    ProgramNode,
    add,
    library_call,
    parameter,
    read_offset,
    subtract,
)
from .observation import NumericObservation


def program_node_count(program: ProgramNode) -> int:
    return 1 + sum(program_node_count(child) for child in program.args)


def program_depth(program: ProgramNode) -> int:
    if not program.args:
        return 1
    return 1 + max(program_depth(child) for child in program.args)


def program_key(program: ProgramNode) -> str:
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))


def program_id(program: ProgramNode) -> str:
    return hashlib.sha256(program_key(program).encode("utf-8")).hexdigest()[:16]


class ProgramEnumerator:
    """Enumerate expression trees from the declared primitive surface."""

    def __init__(
        self,
        *,
        readable_offsets: Sequence[int] = (-1, 0),
        parameter_slots: Sequence[int] = (0,),
        library_operation_ids: Sequence[str] = (),
    ) -> None:
        offsets = tuple(sorted(set(readable_offsets)))
        slots = tuple(sorted(set(parameter_slots)))
        if not offsets:
            raise ValueError("at least one readable offset is required")
        if any(offset not in {-1, 0, 1} for offset in offsets):
            raise ValueError("readable offset is outside the primitive manifest")
        if any(slot < 0 for slot in slots):
            raise ValueError("parameter slots must be non-negative")
        self.readable_offsets = offsets
        self.parameter_slots = slots
        self.library_operation_ids = tuple(sorted(set(library_operation_ids)))
        if any(not concept_id.startswith("C-") for concept_id in self.library_operation_ids):
            raise ValueError("learned primitive ids must start with C-")

    def enumerate(self, maximum_nodes: int) -> tuple[ProgramNode, ...]:
        if maximum_nodes < 1:
            raise ValueError("maximum_nodes must be positive")

        by_size: dict[int, dict[str, ProgramNode]] = {1: {}}
        for offset in self.readable_offsets:
            self._insert(by_size[1], read_offset(offset))
        for slot in self.parameter_slots:
            self._insert(by_size[1], parameter(slot))
        for concept_id in self.library_operation_ids:
            self._insert(by_size[1], library_call(concept_id))

        for size in range(3, maximum_nodes + 1, 2):
            programs: dict[str, ProgramNode] = {}
            remaining = size - 1
            for left_size in range(1, remaining, 2):
                right_size = remaining - left_size
                if left_size not in by_size or right_size not in by_size:
                    continue
                left_programs = tuple(by_size[left_size].values())
                right_programs = tuple(by_size[right_size].values())
                for left in left_programs:
                    for right in right_programs:
                        ordered_left, ordered_right = self._canonical_add_args(left, right)
                        self._insert(programs, add(ordered_left, ordered_right))
                        if left != right:
                            self._insert(programs, subtract(left, right))
            by_size[size] = programs

        result: list[ProgramNode] = []
        for size in sorted(by_size):
            result.extend(by_size[size][key] for key in sorted(by_size[size]))
        return tuple(result)

    @staticmethod
    def _canonical_add_args(
        left: ProgramNode, right: ProgramNode
    ) -> tuple[ProgramNode, ProgramNode]:
        if program_key(left) <= program_key(right):
            return left, right
        return right, left

    @staticmethod
    def _insert(destination: dict[str, ProgramNode], program: ProgramNode) -> None:
        destination.setdefault(program_key(program), program)


@dataclass(frozen=True, slots=True)
class CandidateScore:
    candidate_id: str
    program: ProgramNode
    parameters: Mapping[int, float]
    train_mse: float
    validation_mse: float
    normalized_validation_mse: float
    program_nodes: int
    program_depth: int
    objective_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "program_ast": self.program.to_dict(),
            "parameters": {str(key): value for key, value in self.parameters.items()},
            "train_mse": self.train_mse,
            "validation_mse": self.validation_mse,
            "normalized_validation_mse": self.normalized_validation_mse,
            "program_nodes": self.program_nodes,
            "program_depth": self.program_depth,
            "objective_score": self.objective_score,
        }


@dataclass(frozen=True, slots=True)
class SearchReport:
    objective_id: str
    observation_id: str
    readable_offsets: tuple[int, ...]
    target_offset: int
    train_example_count: int
    validation_example_count: int
    programs_generated: int
    programs_scored: int
    programs_rejected: int
    programs_filtered: int
    top_candidates: tuple[CandidateScore, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "observation_id": self.observation_id,
            "information_boundary": {
                "readable_offsets": list(self.readable_offsets),
                "target_offset": self.target_offset,
            },
            "train_example_count": self.train_example_count,
            "validation_example_count": self.validation_example_count,
            "programs_generated": self.programs_generated,
            "programs_scored": self.programs_scored,
            "programs_rejected": self.programs_rejected,
            "programs_filtered": self.programs_filtered,
            "top_candidates": [candidate.to_dict() for candidate in self.top_candidates],
        }


class NextValueProgramSearch:
    """Search programs that predict a future numeric value from past values.

    The objective is generic. Candidate programs are structurally prevented from
    reading the target offset.
    """

    OBJECTIVE_ID = "predict_next_numeric_value_v0.1"

    def __init__(
        self,
        *,
        maximum_nodes: int = 5,
        top_k: int = 10,
        validation_fraction: float = 0.4,
        complexity_weight: float = 1e-3,
        executor: ProgramExecutor | None = None,
        concept_library: Mapping[str, ProgramNode] | None = None,
        candidate_gate: Callable[[ProgramNode], bool] | None = None,
    ) -> None:
        if maximum_nodes < 1 or maximum_nodes % 2 == 0:
            raise ValueError("maximum_nodes must be a positive odd integer")
        if top_k < 1:
            raise ValueError("top_k must be positive")
        if not 0 < validation_fraction < 1:
            raise ValueError("validation_fraction must be between zero and one")
        if complexity_weight < 0:
            raise ValueError("complexity_weight must be non-negative")
        self.maximum_nodes = maximum_nodes
        self.top_k = top_k
        self.validation_fraction = validation_fraction
        self.complexity_weight = complexity_weight
        self.concept_library = dict(concept_library or {})
        self.executor = executor or ProgramExecutor(library=self.concept_library)
        self.candidate_gate = candidate_gate
        self.enumerator = ProgramEnumerator(
            readable_offsets=(-1, 0),
            library_operation_ids=tuple(self.concept_library),
        )

    def search(self, observation: NumericObservation) -> SearchReport:
        examples = self._valid_example_indices(observation)
        if len(examples) < 3:
            raise ValueError("at least three valid prediction examples are required")
        train_indices, validation_indices = self._split_examples(examples)
        scale = self._target_scale(observation, examples)
        programs = self.enumerator.enumerate(self.maximum_nodes)
        scores: list[CandidateScore] = []
        rejected = 0
        filtered = 0
        for program in programs:
            if self.candidate_gate is not None and not self.candidate_gate(program):
                filtered += 1
                continue
            try:
                score = self._score_program(
                    program,
                    observation,
                    train_indices,
                    validation_indices,
                    scale,
                )
            except NumericExecutionError:
                rejected += 1
                continue
            scores.append(score)

        scores.sort(
            key=lambda item: (
                item.objective_score,
                item.validation_mse,
                item.program_nodes,
                item.candidate_id,
            )
        )
        return SearchReport(
            objective_id=self.OBJECTIVE_ID,
            observation_id=observation.opaque_session_id,
            readable_offsets=self.enumerator.readable_offsets,
            target_offset=1,
            train_example_count=len(train_indices),
            validation_example_count=len(validation_indices),
            programs_generated=len(programs),
            programs_scored=len(scores),
            programs_rejected=rejected,
            programs_filtered=filtered,
            top_candidates=tuple(scores[: self.top_k]),
        )

    @staticmethod
    def _valid_example_indices(observation: NumericObservation) -> tuple[int, ...]:
        indices: list[int] = []
        for index in range(1, len(observation.sequence_values) - 1):
            if all(
                observation.validity_mask[candidate_index]
                for candidate_index in (index - 1, index, index + 1)
            ):
                indices.append(index)
        return tuple(indices)

    def _split_examples(
        self, examples: Sequence[int]
    ) -> tuple[tuple[int, ...], tuple[int, ...]]:
        validation_count = max(1, round(len(examples) * self.validation_fraction))
        validation_count = min(validation_count, len(examples) - 1)
        split_index = len(examples) - validation_count
        return tuple(examples[:split_index]), tuple(examples[split_index:])

    @staticmethod
    def _target_scale(observation: NumericObservation, examples: Sequence[int]) -> float:
        targets = [observation.sequence_values[index + 1] for index in examples]
        mean = fmean(targets)
        variance = fmean((target - mean) ** 2 for target in targets)
        return max(variance, 1e-12)

    def _score_program(
        self,
        program: ProgramNode,
        observation: NumericObservation,
        train_indices: Sequence[int],
        validation_indices: Sequence[int],
        target_scale: float,
    ) -> CandidateScore:
        parameters = self._fit_parameters(program, observation, train_indices)
        train_mse = self._mse(program, parameters, observation, train_indices)
        validation_mse = self._mse(
            program, parameters, observation, validation_indices
        )
        normalized = validation_mse / target_scale
        nodes = program_node_count(program)
        depth = program_depth(program)
        objective_score = normalized + self.complexity_weight * nodes
        if not all(
            math.isfinite(value)
            for value in (train_mse, validation_mse, normalized, objective_score)
        ):
            raise NumericExecutionError("candidate score is non-finite")
        return CandidateScore(
            candidate_id=f"CAND-{program_id(program)}",
            program=program,
            parameters=parameters,
            train_mse=train_mse,
            validation_mse=validation_mse,
            normalized_validation_mse=normalized,
            program_nodes=nodes,
            program_depth=depth,
            objective_score=objective_score,
        )

    def _fit_parameters(
        self,
        program: ProgramNode,
        observation: NumericObservation,
        train_indices: Sequence[int],
    ) -> dict[int, float]:
        slots = sorted(_parameter_slots(program))
        if not slots:
            return {}
        if slots != [0]:
            raise NumericExecutionError("Gen 0 fitter supports exactly parameter slot zero")

        numerator = 0.0
        denominator = 0.0
        for index in train_indices:
            prediction_zero = self._evaluate(
                program, observation, index, parameters={0: 0.0}
            )
            prediction_one = self._evaluate(
                program, observation, index, parameters={0: 1.0}
            )
            coefficient = prediction_one - prediction_zero
            target = observation.sequence_values[index + 1]
            numerator += coefficient * (target - prediction_zero)
            denominator += coefficient * coefficient
        if denominator <= 1e-15:
            return {0: 0.0}
        fitted = numerator / denominator
        if not math.isfinite(fitted):
            raise NumericExecutionError("parameter fit is non-finite")
        return {0: fitted}

    def _mse(
        self,
        program: ProgramNode,
        parameters: Mapping[int, float],
        observation: NumericObservation,
        indices: Sequence[int],
    ) -> float:
        squared_errors: list[float] = []
        for index in indices:
            prediction = self._evaluate(program, observation, index, parameters)
            target = observation.sequence_values[index + 1]
            squared_errors.append((prediction - target) ** 2)
        return fmean(squared_errors)

    def _evaluate(
        self,
        program: ProgramNode,
        observation: NumericObservation,
        index: int,
        parameters: Mapping[int, float],
    ) -> float:
        context = ExecutionContext.create(
            observation.sequence_values,
            index=index,
            parameters=parameters,
            validity_mask=observation.validity_mask,
        )
        return self.executor.evaluate(program, context)


def _parameter_slots(program: ProgramNode) -> set[int]:
    slots: set[int] = set()
    stack = [program]
    while stack:
        node = stack.pop()
        if node.op == "p_scalar_parameter" and node.parameter_slot is not None:
            slots.add(node.parameter_slot)
        stack.extend(node.args)
    return slots


def iter_read_offsets(
    program: ProgramNode, library: Mapping[str, ProgramNode] | None = None
) -> Iterable[int]:
    definitions = library or {}
    stack = [program]
    expanded: set[str] = set()
    while stack:
        node = stack.pop()
        if node.op in definitions and node.op not in expanded:
            expanded.add(node.op)
            stack.append(definitions[node.op])
            continue
        if node.op == "p_read_offset" and node.offset is not None:
            yield node.offset
        stack.extend(node.args)
