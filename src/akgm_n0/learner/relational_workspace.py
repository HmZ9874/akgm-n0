"""Multi-view relation graph with candidate-written addressable memory programs."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping

from .indexed_semantics import DifferenceWorkspace, build_difference_workspace
from .observation import NumericObservation
from .semantic_slot import InvalidMicroProgram, MicroProgram, MicroProgramExecutor


RELATIONAL_INSTRUCTIONS = frozenset({"r_add", "r_subtract", "r_semantic_call"})


class InvalidRelationalProgram(ValueError):
    """Raised when a relational memory program is malformed or unsafe."""


@dataclass(frozen=True, slots=True)
class MemoryInstruction:
    op: str
    left_address: int
    right_address: int
    operation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "op": self.op,
            "left_address": self.left_address,
            "right_address": self.right_address,
            "write": "append_next_address",
        }
        if self.operation_id is not None:
            result["operation_id"] = self.operation_id
        return result


@dataclass(frozen=True, slots=True)
class MemoryAssertion:
    result_address: int
    observed_address: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "op": "r_assert_equal",
            "result_address": self.result_address,
            "observed_address": self.observed_address,
        }


@dataclass(frozen=True, slots=True)
class RelationalProgram:
    input_width: int
    instructions: tuple[MemoryInstruction, ...]
    assertions: tuple[MemoryAssertion, ...]

    @property
    def node_count(self) -> int:
        return len(self.instructions) + len(self.assertions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "addressable_relational_memory_v0.1",
            "input_width": self.input_width,
            "initial_memory": "ordered_observed_numeric_atoms",
            "instructions": [item.to_dict() for item in self.instructions],
            "assertions": [item.to_dict() for item in self.assertions],
        }


@dataclass(frozen=True, slots=True)
class RelationalExecution:
    final_memory: tuple[float, ...]
    instruction_outputs: tuple[float, ...]
    assertion_results: tuple[bool, ...]

    @property
    def exact(self) -> bool:
        return bool(self.assertion_results) and all(self.assertion_results)


class RelationalMemoryExecutor:
    """Execute candidate-selected reads and append-only writes."""

    def __init__(
        self,
        semantic_library: Mapping[str, MicroProgram],
        *,
        maximum_instructions: int = 16,
        magnitude_limit: float = 1e100,
    ) -> None:
        self.semantic_library = dict(semantic_library)
        self.maximum_instructions = maximum_instructions
        self.magnitude_limit = magnitude_limit
        self.micro_executor = MicroProgramExecutor(maximum_steps=256)

    def execute(
        self, program: RelationalProgram, observed_values: tuple[float, ...]
    ) -> RelationalExecution:
        self.validate(program, len(observed_values))
        memory = [self._checked(value) for value in observed_values]
        outputs = []
        for instruction in program.instructions:
            left = memory[instruction.left_address]
            right = memory[instruction.right_address]
            if instruction.op == "r_add":
                output = left + right
            elif instruction.op == "r_subtract":
                output = left - right
            else:
                assert instruction.operation_id is not None
                try:
                    output = self.micro_executor.execute(
                        self.semantic_library[instruction.operation_id], (left, right)
                    ).output_value
                except InvalidMicroProgram as exc:
                    raise InvalidRelationalProgram(
                        "opaque semantic call did not execute"
                    ) from exc
            output = self._checked(output)
            memory.append(output)
            outputs.append(output)
        assertion_results = tuple(
            memory[item.result_address] == memory[item.observed_address]
            for item in program.assertions
        )
        return RelationalExecution(tuple(memory), tuple(outputs), assertion_results)

    def validate(self, program: RelationalProgram, observed_width: int) -> None:
        if program.input_width != observed_width or observed_width < 1:
            raise InvalidRelationalProgram("relational input width mismatch")
        if not program.instructions or len(program.instructions) > self.maximum_instructions:
            raise InvalidRelationalProgram("relational instruction bound violated")
        available = observed_width
        for instruction in program.instructions:
            if instruction.op not in RELATIONAL_INSTRUCTIONS:
                raise InvalidRelationalProgram("unregistered relational instruction")
            if not (0 <= instruction.left_address < available) or not (
                0 <= instruction.right_address < available
            ):
                raise InvalidRelationalProgram("instruction reads unavailable memory")
            if instruction.op == "r_semantic_call":
                if (
                    not instruction.operation_id
                    or instruction.operation_id not in self.semantic_library
                ):
                    raise InvalidRelationalProgram("semantic operation is unavailable")
            elif instruction.operation_id is not None:
                raise InvalidRelationalProgram("basic instruction cannot name semantics")
            available += 1
        if not program.assertions:
            raise InvalidRelationalProgram("program must declare verification assertions")
        for assertion in program.assertions:
            if not (0 <= assertion.result_address < available) or not (
                0 <= assertion.observed_address < observed_width
            ):
                raise InvalidRelationalProgram("assertion address is unavailable")

    def _checked(self, value: float) -> float:
        numeric = float(value)
        if not math.isfinite(numeric) or abs(numeric) > self.magnitude_limit:
            raise InvalidRelationalProgram("relational program produced unsafe magnitude")
        return numeric


@dataclass(frozen=True, slots=True)
class RelationFact:
    fact_id: str
    instruction: MemoryInstruction
    source_indices: tuple[int, int]
    target_index: int
    output_value: float

    @property
    def covered_indices(self) -> frozenset[int]:
        return frozenset((*self.source_indices, self.target_index))

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "instruction": self.instruction.to_dict(),
            "source_indices": list(self.source_indices),
            "target_index": self.target_index,
            "output_value": self.output_value,
            "exact_on_observed_atoms": True,
        }


@dataclass(frozen=True, slots=True)
class RelationalCandidate:
    candidate_id: str
    kind: str
    program: RelationalProgram
    logic_signature: str
    covered_indices: tuple[int, ...]
    execution: RelationalExecution

    @property
    def coverage_count(self) -> int:
        return len(self.covered_indices)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "kind": self.kind,
            "program": self.program.to_dict(),
            "logic_signature": self.logic_signature,
            "covered_indices": list(self.covered_indices),
            "coverage_count": self.coverage_count,
            "instruction_outputs": list(self.execution.instruction_outputs),
            "assertion_results": list(self.execution.assertion_results),
            "exact": self.execution.exact,
        }


@dataclass(frozen=True, slots=True)
class MultiViewRelationReport:
    sequence_view: DifferenceWorkspace
    fact_count: int
    relation_facts: tuple[RelationFact, ...]
    candidates: tuple[RelationalCandidate, ...]
    covered_indices: tuple[int, ...]
    uncovered_indices: tuple[int, ...]


class MultiViewRelationalSearch:
    """Search exact local graph edges and candidate-written control sequences."""

    def __init__(self, semantic_library: Mapping[str, MicroProgram]) -> None:
        self.semantic_library = dict(semantic_library)
        self.executor = RelationalMemoryExecutor(self.semantic_library)

    def search(self, observation: NumericObservation) -> MultiViewRelationReport:
        values = tuple(observation.sequence_values)
        if not all(observation.validity_mask):
            raise ValueError("multi-view relation search requires all atoms to be valid")
        facts = self._discover_facts(values)
        candidates = self._build_candidates(values, facts)
        covered = tuple(sorted({index for fact in facts for index in fact.covered_indices}))
        uncovered = tuple(index for index in range(len(values)) if index not in covered)
        return MultiViewRelationReport(
            sequence_view=build_difference_workspace(observation),
            fact_count=len(facts),
            relation_facts=facts,
            candidates=candidates,
            covered_indices=covered,
            uncovered_indices=uncovered,
        )

    def _discover_facts(self, values: tuple[float, ...]) -> tuple[RelationFact, ...]:
        facts: dict[str, RelationFact] = {}
        operations = [("r_add", None), ("r_subtract", None)] + [
            ("r_semantic_call", operation_id)
            for operation_id in sorted(self.semantic_library)
        ]
        for left_index, left in enumerate(values):
            for right_index, right in enumerate(values):
                for op, operation_id in operations:
                    if op == "r_add" and right_index < left_index:
                        continue
                    instruction = MemoryInstruction(
                        op, left_index, right_index, operation_id
                    )
                    program = RelationalProgram(
                        len(values),
                        (instruction,),
                        (MemoryAssertion(len(values), 0),),
                    )
                    try:
                        execution = self.executor.execute(program, values)
                    except InvalidRelationalProgram:
                        continue
                    output = execution.instruction_outputs[0]
                    for target_index, target in enumerate(values):
                        if target_index in {left_index, right_index} or output != target:
                            continue
                        key = json.dumps(
                            {
                                "op": op,
                                "operation_id": operation_id,
                                "sources": [left_index, right_index],
                                "target": target_index,
                            },
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                        fact_id = "RF-" + hashlib.sha256(
                            key.encode("utf-8")
                        ).hexdigest()[:16]
                        facts[key] = RelationFact(
                            fact_id,
                            instruction,
                            (left_index, right_index),
                            target_index,
                            output,
                        )
        return tuple(
            sorted(
                facts.values(),
                key=lambda item: (
                    item.instruction.op,
                    item.target_index,
                    item.source_indices,
                    item.fact_id,
                ),
            )
        )

    def _build_candidates(
        self, values: tuple[float, ...], facts: tuple[RelationFact, ...]
    ) -> tuple[RelationalCandidate, ...]:
        candidates: list[RelationalCandidate] = []
        for operation in ("r_add", "r_subtract", "r_semantic_call"):
            fact = next((item for item in facts if item.instruction.op == operation), None)
            if fact is not None:
                candidates.append(self._candidate_from_facts(values, (fact,), "direct"))

        chain = self._find_reuse_chain(facts)
        if chain is not None:
            candidates.append(self._reuse_chain_candidate(values, chain))

        graph_facts = self._greedy_cover(facts)
        if len(graph_facts) >= 2:
            candidates.append(
                self._candidate_from_facts(values, graph_facts, "graph_control")
            )

        unique: dict[str, RelationalCandidate] = {}
        for candidate in candidates:
            unique.setdefault(candidate.logic_signature, candidate)
        return tuple(
            sorted(
                unique.values(),
                key=lambda item: (
                    -item.coverage_count,
                    len(item.program.instructions),
                    item.kind,
                    item.candidate_id,
                ),
            )
        )

    def _candidate_from_facts(
        self,
        values: tuple[float, ...],
        facts: tuple[RelationFact, ...],
        kind: str,
    ) -> RelationalCandidate:
        width = len(values)
        program = RelationalProgram(
            width,
            tuple(fact.instruction for fact in facts),
            tuple(
                MemoryAssertion(width + offset, fact.target_index)
                for offset, fact in enumerate(facts)
            ),
        )
        covered = tuple(sorted({index for fact in facts for index in fact.covered_indices}))
        return self._make_candidate(kind, program, covered, values)

    def _reuse_chain_candidate(
        self, values: tuple[float, ...], chain: tuple[RelationFact, RelationFact]
    ) -> RelationalCandidate:
        first, second = chain
        width = len(values)
        sources = list(second.source_indices)
        sources[sources.index(first.target_index)] = width
        second_instruction = MemoryInstruction(
            second.instruction.op,
            sources[0],
            sources[1],
            second.instruction.operation_id,
        )
        program = RelationalProgram(
            width,
            (first.instruction, second_instruction),
            (
                MemoryAssertion(width, first.target_index),
                MemoryAssertion(width + 1, second.target_index),
            ),
        )
        covered = tuple(sorted(first.covered_indices | second.covered_indices))
        return self._make_candidate("generated_address_reuse", program, covered, values)

    def _make_candidate(
        self,
        kind: str,
        program: RelationalProgram,
        covered: tuple[int, ...],
        values: tuple[float, ...],
    ) -> RelationalCandidate:
        execution = self.executor.execute(program, values)
        key = relational_program_key(program)
        return RelationalCandidate(
            candidate_id="RC-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
            kind=kind,
            program=program,
            logic_signature=relational_logic_signature(program),
            covered_indices=covered,
            execution=execution,
        )

    @staticmethod
    def _find_reuse_chain(
        facts: tuple[RelationFact, ...]
    ) -> tuple[RelationFact, RelationFact] | None:
        choices = [
            (first, second)
            for first in facts
            for second in facts
            if first.fact_id != second.fact_id
            and first.target_index in second.source_indices
            and second.target_index not in first.covered_indices
        ]
        if not choices:
            return None
        return max(
            choices,
            key=lambda pair: (
                len(pair[0].covered_indices | pair[1].covered_indices),
                pair[0].instruction.op != pair[1].instruction.op,
                pair[0].fact_id,
                pair[1].fact_id,
            ),
        )

    @staticmethod
    def _greedy_cover(facts: tuple[RelationFact, ...]) -> tuple[RelationFact, ...]:
        selected: list[RelationFact] = []
        covered: frozenset[int] = frozenset()
        remaining = list(facts)
        while remaining:
            best = max(
                remaining,
                key=lambda item: (
                    len(item.covered_indices - covered),
                    item.instruction.op not in {
                        fact.instruction.op for fact in selected
                    },
                    item.fact_id,
                ),
            )
            gain = best.covered_indices - covered
            if not gain:
                break
            selected.append(best)
            covered = covered | best.covered_indices
            remaining = [item for item in remaining if item.fact_id != best.fact_id]
        return tuple(selected)


def relational_program_key(program: RelationalProgram) -> str:
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))


def relational_logic_signature(program: RelationalProgram) -> str:
    width = program.input_width

    def address_kind(address: int) -> str:
        return "input" if address < width else f"generated_{address - width}"

    shape = {
        "instructions": [
            {
                "op": item.op,
                "left": address_kind(item.left_address),
                "right": address_kind(item.right_address),
                "operation_id": item.operation_id,
            }
            for item in program.instructions
        ],
        "assertion_count": len(program.assertions),
    }
    encoded = json.dumps(shape, sort_keys=True, separators=(",", ":"))
    return "RLOGIC-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
