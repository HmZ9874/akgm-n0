"""Anonymous finite-state graph programs for MetaMachine Gen 1."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .observation import SymbolTraceObservation


class InvalidStateGraph(ValueError):
    """Raised when a candidate exceeds the frozen substrate contract."""


@dataclass(frozen=True, slots=True)
class StateGraphProgram:
    state_count: int
    initial_state_id: int
    transition_table: tuple[tuple[int, ...], ...]
    output_table: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_count": self.state_count,
            "initial_state_id": self.initial_state_id,
            "transition_table": [list(row) for row in self.transition_table],
            "output_table": list(self.output_table),
        }


@dataclass(frozen=True, slots=True)
class StateGraphExecution:
    output_value: int
    visited_state_ids: tuple[int, ...]
    step_count: int


class StateGraphExecutor:
    """Apply one selected transition-table entry per supplied symbol."""

    def __init__(
        self,
        *,
        symbol_cardinality: int = 2,
        output_cardinality: int = 2,
        maximum_state_count: int = 3,
        maximum_trace_steps: int = 64,
    ) -> None:
        if min(
            symbol_cardinality,
            output_cardinality,
            maximum_state_count,
            maximum_trace_steps,
        ) < 1:
            raise ValueError("substrate limits must be positive")
        self.symbol_cardinality = symbol_cardinality
        self.output_cardinality = output_cardinality
        self.maximum_state_count = maximum_state_count
        self.maximum_trace_steps = maximum_trace_steps

    def execute(
        self, program: StateGraphProgram, trace: Sequence[int]
    ) -> StateGraphExecution:
        self.validate(program)
        if len(trace) > self.maximum_trace_steps:
            raise InvalidStateGraph("trace exceeds the registered step bound")
        state = program.initial_state_id
        visited = [state]
        for symbol in trace:
            if isinstance(symbol, bool) or not isinstance(symbol, int):
                raise InvalidStateGraph("trace symbol must be an integer")
            if symbol < 0 or symbol >= self.symbol_cardinality:
                raise InvalidStateGraph("trace symbol is outside the registered alphabet")
            state = program.transition_table[state][symbol]
            visited.append(state)
        return StateGraphExecution(
            output_value=program.output_table[state],
            visited_state_ids=tuple(visited),
            step_count=len(trace),
        )

    def validate(self, program: StateGraphProgram) -> None:
        if isinstance(program.state_count, bool) or not isinstance(program.state_count, int):
            raise InvalidStateGraph("state_count must be an integer")
        if program.state_count < 1 or program.state_count > self.maximum_state_count:
            raise InvalidStateGraph("state_count is outside the registered bound")
        if program.initial_state_id < 0 or program.initial_state_id >= program.state_count:
            raise InvalidStateGraph("initial state is outside the graph")
        if len(program.transition_table) != program.state_count:
            raise InvalidStateGraph("transition table height does not match state_count")
        if len(program.output_table) != program.state_count:
            raise InvalidStateGraph("output table length does not match state_count")
        for row in program.transition_table:
            if len(row) != self.symbol_cardinality:
                raise InvalidStateGraph("transition table width is invalid")
            if any(
                isinstance(state, bool)
                or not isinstance(state, int)
                or state < 0
                or state >= program.state_count
                for state in row
            ):
                raise InvalidStateGraph("transition target is outside the graph")
        if any(
            isinstance(output, bool)
            or not isinstance(output, int)
            or output < 0
            or output >= self.output_cardinality
            for output in program.output_table
        ):
            raise InvalidStateGraph("output table value is outside the registered range")


@dataclass(frozen=True, slots=True)
class StateGraphCandidate:
    candidate_id: str
    program: StateGraphProgram
    fit_error: float
    reachable_state_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "program": self.program.to_dict(),
            "fit_error": self.fit_error,
            "reachable_state_count": self.reachable_state_count,
        }


@dataclass(frozen=True, slots=True)
class StateGraphSearchReport:
    programs_generated: int
    programs_scored: int
    valid_trace_count: int
    top_candidates: tuple[StateGraphCandidate, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "programs_generated": self.programs_generated,
            "programs_scored": self.programs_scored,
            "valid_trace_count": self.valid_trace_count,
            "top_candidates": [item.to_dict() for item in self.top_candidates],
        }


class StateGraphSearch:
    """Deterministically enumerate small anonymous state graphs."""

    def __init__(
        self,
        *,
        maximum_state_count: int = 3,
        top_k: int = 20,
        executor: StateGraphExecutor | None = None,
    ) -> None:
        if maximum_state_count < 1 or maximum_state_count > 3:
            raise ValueError("current search supports one through three states")
        if top_k < 1:
            raise ValueError("top_k must be positive")
        self.maximum_state_count = maximum_state_count
        self.top_k = top_k
        self.executor = executor or StateGraphExecutor(
            maximum_state_count=maximum_state_count
        )

    def search(self, observation: SymbolTraceObservation) -> StateGraphSearchReport:
        valid = [
            (trace, output)
            for trace, output, include in zip(
                observation.symbol_traces,
                observation.output_values,
                observation.validity_mask,
                strict=True,
            )
            if include
        ]
        if not valid:
            raise ValueError("search requires at least one valid trace")
        candidates: list[StateGraphCandidate] = []
        generated = 0
        scored = 0
        seen: set[str] = set()
        for program in self._enumerate_programs():
            generated += 1
            canonical = canonicalize_state_graph(program)
            key = state_graph_key(canonical)
            if key in seen:
                continue
            seen.add(key)
            mismatches = sum(
                self.executor.execute(canonical, trace).output_value != expected
                for trace, expected in valid
            )
            scored += 1
            fit_error = mismatches / len(valid)
            candidate_id = "SG-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
            candidates.append(
                StateGraphCandidate(
                    candidate_id,
                    canonical,
                    fit_error,
                    len(reachable_states(canonical)),
                )
            )
        candidates.sort(
            key=lambda item: (
                item.fit_error,
                item.reachable_state_count,
                item.program.state_count,
                item.candidate_id,
            )
        )
        return StateGraphSearchReport(
            programs_generated=generated,
            programs_scored=scored,
            valid_trace_count=len(valid),
            top_candidates=tuple(candidates[: self.top_k]),
        )

    def _enumerate_programs(self) -> Iterable[StateGraphProgram]:
        symbol_count = self.executor.symbol_cardinality
        output_count = self.executor.output_cardinality
        for state_count in range(1, self.maximum_state_count + 1):
            transition_slots = state_count * symbol_count
            for flat_transitions in itertools.product(
                range(state_count), repeat=transition_slots
            ):
                transitions = tuple(
                    tuple(
                        flat_transitions[row * symbol_count + column]
                        for column in range(symbol_count)
                    )
                    for row in range(state_count)
                )
                for outputs in itertools.product(
                    range(output_count), repeat=state_count
                ):
                    yield StateGraphProgram(
                        state_count=state_count,
                        initial_state_id=0,
                        transition_table=transitions,
                        output_table=tuple(outputs),
                    )


@dataclass(frozen=True, slots=True)
class StateGraphSemantic:
    operation_id: str
    definition: StateGraphProgram

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "definition": self.definition.to_dict(),
            "human_interpretation": None,
        }


class StateGraphLibrary:
    """Runtime library of promoted anonymous state-graph semantics."""

    def __init__(self, executor: StateGraphExecutor | None = None) -> None:
        self.executor = executor or StateGraphExecutor()
        self._entries: dict[str, StateGraphSemantic] = {}

    @property
    def entries(self) -> tuple[StateGraphSemantic, ...]:
        return tuple(self._entries[key] for key in sorted(self._entries))

    def promote(self, program: StateGraphProgram) -> StateGraphSemantic:
        canonical = canonicalize_state_graph(program)
        self.executor.validate(canonical)
        operation_id = "OP-" + hashlib.sha256(
            state_graph_key(canonical).encode("utf-8")
        ).hexdigest()[:16]
        semantic = StateGraphSemantic(operation_id, canonical)
        self._entries.setdefault(operation_id, semantic)
        return self._entries[operation_id]

    def execute(self, operation_id: str, trace: Sequence[int]) -> StateGraphExecution:
        try:
            semantic = self._entries[operation_id]
        except KeyError as exc:
            raise InvalidStateGraph(f"unknown promoted operation: {operation_id}") from exc
        return self.executor.execute(semantic.definition, trace)


def state_graph_key(program: StateGraphProgram) -> str:
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))


def reachable_states(program: StateGraphProgram) -> frozenset[int]:
    pending = [program.initial_state_id]
    reached: set[int] = set()
    while pending:
        state = pending.pop()
        if state in reached:
            continue
        reached.add(state)
        pending.extend(program.transition_table[state])
    return frozenset(reached)


def canonicalize_state_graph(program: StateGraphProgram) -> StateGraphProgram:
    """Rename reachable states by discovery order and discard unreachable states."""

    order: list[int] = []
    mapping: dict[int, int] = {}
    pending = [program.initial_state_id]
    while pending:
        state = pending.pop(0)
        if state in mapping:
            continue
        mapping[state] = len(order)
        order.append(state)
        for target in program.transition_table[state]:
            if target not in mapping and target not in pending:
                pending.append(target)
    transitions = tuple(
        tuple(mapping[target] for target in program.transition_table[state])
        for state in order
    )
    outputs = tuple(program.output_table[state] for state in order)
    return StateGraphProgram(len(order), 0, transitions, outputs)
