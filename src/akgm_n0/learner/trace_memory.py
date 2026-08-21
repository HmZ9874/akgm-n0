"""Synthesize a second memory cell over a verified controller's transition trace."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .adaptive_control import (
    AdaptiveControlExecutor,
    AdaptiveValueNode,
    InvalidAdaptiveProgram,
)
from .input_adapter import InputAdapterExecutor, InputAdapterProgram
from .observation import NumericTableObservation


@dataclass(frozen=True, slots=True)
class TraceMemoryProgram:
    """Attach candidate-defined memory updates to two anonymous transition classes."""

    parent_operation_id: str
    parent_program: InputAdapterProgram
    initial_memory: AdaptiveValueNode
    priority_memory_update: AdaptiveValueNode
    base_memory_update: AdaptiveValueNode
    output: AdaptiveValueNode

    @property
    def node_count(self) -> int:
        return (
            self.parent_program.node_count
            + self.initial_memory.node_count
            + self.priority_memory_update.node_count
            + self.base_memory_update.node_count
            + self.output.node_count
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "anonymous_dual_state_trace_memory_v0.1",
            "parent_operation_id": self.parent_operation_id,
            "parent_program": self.parent_program.to_dict(),
            "memory": {
                "initial": self.initial_memory.to_dict(),
                "update_on_priority_transition": self.priority_memory_update.to_dict(),
                "update_on_base_transition": self.base_memory_update.to_dict(),
                "output": self.output.to_dict(),
            },
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TraceMemoryProgram":
        required = {"substrate", "parent_operation_id", "parent_program", "memory"}
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidAdaptiveProgram("trace memory program shape is invalid")
        if value["substrate"] != "anonymous_dual_state_trace_memory_v0.1":
            raise InvalidAdaptiveProgram("trace memory substrate is unavailable")
        memory = value["memory"]
        if not isinstance(memory, Mapping) or set(memory) != {
            "initial",
            "update_on_priority_transition",
            "update_on_base_transition",
            "output",
        }:
            raise InvalidAdaptiveProgram("trace memory definition is invalid")
        program = cls(
            parent_operation_id=str(value["parent_operation_id"]),
            parent_program=InputAdapterProgram.from_dict(value["parent_program"]),
            initial_memory=AdaptiveValueNode.from_dict(memory["initial"]),
            priority_memory_update=AdaptiveValueNode.from_dict(
                memory["update_on_priority_transition"]
            ),
            base_memory_update=AdaptiveValueNode.from_dict(
                memory["update_on_base_transition"]
            ),
            output=AdaptiveValueNode.from_dict(memory["output"]),
        )
        TraceMemoryExecutor().validate(program)
        return program


@dataclass(frozen=True, slots=True)
class TraceMemoryExecution:
    output_value: float
    final_memory: float
    parent_output_value: float
    final_parent_state: float
    transition_count: int
    priority_transition_count: int
    base_transition_count: int
    adapted_inputs: tuple[float, float]


class TraceMemoryExecutor:
    """Run parent state transitions while a candidate controls a separate memory cell."""

    def __init__(self, *, maximum_steps: int = 256) -> None:
        self.maximum_steps = maximum_steps
        self.parent_executor = InputAdapterExecutor(maximum_steps=maximum_steps)
        self.memory_executor = AdaptiveControlExecutor(maximum_steps=maximum_steps)

    def validate(self, program: TraceMemoryProgram) -> None:
        if not program.parent_operation_id:
            raise InvalidAdaptiveProgram("trace memory requires a parent operation")
        self.parent_executor.validate(program.parent_program)
        self.memory_executor._validate_node(  # noqa: SLF001
            program.initial_memory, 2, allow_state=False
        )
        for update in (program.priority_memory_update, program.base_memory_update):
            self.memory_executor._validate_node(update, 2, allow_state=True)  # noqa: SLF001
            if not self.memory_executor._uses_state(update):  # noqa: SLF001
                raise InvalidAdaptiveProgram("memory update must depend on memory state")
        self.memory_executor._validate_node(program.output, 2, allow_state=True)  # noqa: SLF001

    def execute(self, program: TraceMemoryProgram, inputs) -> TraceMemoryExecution:
        numeric_inputs = tuple(float(value) for value in inputs)
        if len(numeric_inputs) != 2:
            raise InvalidAdaptiveProgram("trace memory requires exactly two inputs")
        self.validate(program)

        adapter = program.parent_program
        predicate = self.parent_executor.value_executor._guard(  # noqa: SLF001
            adapter.adapter_guard, numeric_inputs, 0.0
        )
        if predicate == adapter.adapter_guard.halt_when:
            adapted_second = self.parent_executor.value_executor._evaluate(  # noqa: SLF001
                adapter.adapted_second_input, numeric_inputs, None
            )
        else:
            adapted_second = numeric_inputs[1]
        adapted_inputs = (numeric_inputs[0], adapted_second)

        branch_program = adapter.parent_program
        base_executor = self.parent_executor.parent_executor.base_executor
        parent_state = base_executor._evaluate(  # noqa: SLF001
            branch_program.base_program.initial_state, adapted_inputs, None
        )
        memory = self.memory_executor._evaluate(  # noqa: SLF001
            program.initial_memory, numeric_inputs, None
        )
        priority_count = 0
        base_count = 0

        for step in range(self.maximum_steps + 1):
            branch_predicate = base_executor._guard(  # noqa: SLF001
                branch_program.branch_guard, adapted_inputs, parent_state
            )
            if branch_predicate == branch_program.branch_guard.halt_when:
                if step == self.maximum_steps:
                    break
                parent_state = base_executor._evaluate(  # noqa: SLF001
                    branch_program.branch_update, adapted_inputs, parent_state
                )
                memory = self.memory_executor._evaluate(  # noqa: SLF001
                    program.priority_memory_update, numeric_inputs, memory
                )
                priority_count += 1
                continue

            base_predicate = base_executor._guard(  # noqa: SLF001
                branch_program.base_program.guard, adapted_inputs, parent_state
            )
            if base_predicate == branch_program.base_program.guard.halt_when:
                parent_output = base_executor._evaluate(  # noqa: SLF001
                    branch_program.base_program.output, adapted_inputs, parent_state
                )
                output = self.memory_executor._evaluate(  # noqa: SLF001
                    program.output, numeric_inputs, memory
                )
                return TraceMemoryExecution(
                    output_value=output,
                    final_memory=memory,
                    parent_output_value=parent_output,
                    final_parent_state=parent_state,
                    transition_count=step,
                    priority_transition_count=priority_count,
                    base_transition_count=base_count,
                    adapted_inputs=adapted_inputs,
                )
            if step == self.maximum_steps:
                break
            parent_state = base_executor._evaluate(  # noqa: SLF001
                branch_program.base_program.update, adapted_inputs, parent_state
            )
            memory = self.memory_executor._evaluate(  # noqa: SLF001
                program.base_memory_update, numeric_inputs, memory
            )
            base_count += 1
        raise InvalidAdaptiveProgram("trace memory parent did not halt within bound")


@dataclass(frozen=True, slots=True)
class TraceMemoryCandidate:
    candidate_id: str
    program: TraceMemoryProgram
    fit_mse: float
    maximum_absolute_error: float
    maximum_transitions_used: int
    training_outputs: tuple[float, ...]
    behavior_signature: tuple[float | None, ...]
    logic_signature: str

    @property
    def exact(self) -> bool:
        return self.maximum_absolute_error == 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "program": self.program.to_dict(),
            "fit_mse": self.fit_mse,
            "maximum_absolute_error": self.maximum_absolute_error,
            "maximum_transitions_used": self.maximum_transitions_used,
            "training_outputs": list(self.training_outputs),
            "behavior_signature": list(self.behavior_signature),
            "logic_signature": self.logic_signature,
            "program_nodes": self.program.node_count,
            "exact": self.exact,
        }


@dataclass(frozen=True, slots=True)
class TraceMemorySearchReport:
    programs_generated: int
    programs_executed: int
    programs_rejected: int
    behavior_classes: int
    evidence_constants: tuple[dict[str, Any], ...]
    top_candidates: tuple[TraceMemoryCandidate, ...]


class TraceMemorySearch:
    """Enumerate memory initialization, event updates, and final read choices."""

    def __init__(
        self,
        parent_program: InputAdapterProgram,
        *,
        parent_operation_id: str,
        top_k: int = 500,
        maximum_evidence_constants: int = 3,
        executor: TraceMemoryExecutor | None = None,
    ) -> None:
        self.parent_program = parent_program
        self.parent_operation_id = parent_operation_id
        self.top_k = top_k
        self.maximum_evidence_constants = maximum_evidence_constants
        self.executor = executor or TraceMemoryExecutor()

    def search(self, observation: NumericTableObservation) -> TraceMemorySearchReport:
        valid = tuple(
            (row, output)
            for row, output, include in zip(
                observation.input_rows,
                observation.output_values,
                observation.validity_mask,
                strict=True,
            )
            if include
        )
        if not valid:
            raise ValueError("trace memory search requires valid rows")
        constants = self._derive_constants(valid)
        inputs = tuple(AdaptiveValueNode("a_input", index=index) for index in range(2))
        constant_nodes = tuple(
            AdaptiveValueNode("a_constant", constant=item["value"])
            for item in constants
        )
        immutable = inputs + constant_nodes
        memory = AdaptiveValueNode("a_state")
        updates = [memory]
        for source in immutable:
            updates.extend(
                (
                    AdaptiveValueNode("a_add", (memory, source)),
                    AdaptiveValueNode("a_subtract", (memory, source)),
                    AdaptiveValueNode("a_subtract", (source, memory)),
                )
            )
        outputs = (memory,) + immutable
        expected = tuple(output for _, output in valid)
        probe_rows = tuple(row for row, _ in valid) + (
            (29.0, -6.0),
            (-29.0, -6.0),
            (31.0, 8.0),
            (-31.0, -8.0),
        )
        generated = 0
        executed = 0
        rejected = 0
        behavior_keys: set[tuple[float | None, ...]] = set()
        by_logic_behavior: dict[
            tuple[tuple[float | None, ...], str], TraceMemoryCandidate
        ] = {}

        for initial in immutable:
            for priority_update in updates:
                for base_update in updates:
                    for output in outputs:
                        generated += 1
                        program = TraceMemoryProgram(
                            self.parent_operation_id,
                            self.parent_program,
                            initial,
                            priority_update,
                            base_update,
                            output,
                        )
                        values: list[float] = []
                        transitions: list[int] = []
                        failed = False
                        for row, _ in valid:
                            try:
                                result = self.executor.execute(program, row)
                            except InvalidAdaptiveProgram:
                                failed = True
                                break
                            values.append(result.output_value)
                            transitions.append(result.transition_count)
                        if failed:
                            rejected += 1
                            continue
                        executed += 1
                        errors = tuple(
                            actual - target
                            for actual, target in zip(values, expected, strict=True)
                        )
                        behavior: list[float | None] = []
                        for row in probe_rows:
                            try:
                                behavior.append(self.executor.execute(program, row).output_value)
                            except InvalidAdaptiveProgram:
                                behavior.append(None)
                        behavior_key = tuple(behavior)
                        logic_signature = trace_memory_logic_signature(program)
                        key = trace_memory_program_key(program)
                        candidate = TraceMemoryCandidate(
                            candidate_id="TM-"
                            + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
                            program=program,
                            fit_mse=sum(error * error for error in errors) / len(errors),
                            maximum_absolute_error=max(abs(error) for error in errors),
                            maximum_transitions_used=max(transitions),
                            training_outputs=tuple(values),
                            behavior_signature=behavior_key,
                            logic_signature=logic_signature,
                        )
                        behavior_keys.add(behavior_key)
                        dedupe_key = (behavior_key, logic_signature)
                        current = by_logic_behavior.get(dedupe_key)
                        if current is None or self._sort_key(candidate) < self._sort_key(current):
                            by_logic_behavior[dedupe_key] = candidate
        candidates = sorted(by_logic_behavior.values(), key=self._sort_key)
        return TraceMemorySearchReport(
            programs_generated=generated,
            programs_executed=executed,
            programs_rejected=rejected,
            behavior_classes=len(behavior_keys),
            evidence_constants=constants,
            top_candidates=tuple(candidates[: self.top_k]),
        )

    @staticmethod
    def _sort_key(candidate: TraceMemoryCandidate) -> tuple[Any, ...]:
        return (
            candidate.fit_mse,
            candidate.program.node_count,
            candidate.maximum_transitions_used,
            candidate.candidate_id,
        )

    def _derive_constants(self, valid) -> tuple[dict[str, Any], ...]:
        atoms = sorted({value for row, output in valid for value in (*row, output)})
        values: dict[float, dict[str, Any]] = {}
        for left in atoms:
            for right in atoms:
                result = float(left - right)
                values.setdefault(
                    result,
                    {
                        "value": result,
                        "provenance": {
                            "op": "subtract_observed_numeric_atoms",
                            "left": left,
                            "right": right,
                        },
                    },
                )
        return tuple(
            sorted(values.values(), key=lambda item: (abs(item["value"]), item["value"]))[
                : self.maximum_evidence_constants
            ]
        )


def trace_memory_program_key(program: TraceMemoryProgram) -> str:
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))


def trace_memory_logic_signature(program: TraceMemoryProgram) -> str:
    def node_shape(node: AdaptiveValueNode) -> dict[str, Any]:
        return {
            "op": node.op,
            "index": node.index,
            "constant": node.constant,
            "children": [node_shape(item) for item in node.args],
        }

    value = {
        "parent": program.parent_operation_id,
        "initial": node_shape(program.initial_memory),
        "priority_update": node_shape(program.priority_memory_update),
        "base_update": node_shape(program.base_memory_update),
        "output": node_shape(program.output),
    }
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return "TMLOGIC-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
