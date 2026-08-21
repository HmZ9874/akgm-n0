"""Synthesize a conditional input adapter around a verified controller."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .adaptive_branching import (
    AdaptiveBranchExecutor,
    AdaptiveBranchProgram,
)
from .adaptive_control import (
    ADAPTIVE_GUARD_OPS,
    AdaptiveControlExecutor,
    AdaptiveGuard,
    AdaptiveValueNode,
    InvalidAdaptiveProgram,
)
from .observation import NumericTableObservation


@dataclass(frozen=True, slots=True)
class InputAdapterProgram:
    parent_operation_id: str
    parent_program: AdaptiveBranchProgram
    adapter_guard: AdaptiveGuard
    adapted_second_input: AdaptiveValueNode

    @property
    def node_count(self) -> int:
        return (
            self.parent_program.node_count
            + self.adapter_guard.node_count
            + self.adapted_second_input.node_count
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "anonymous_conditional_input_adapter_v0.1",
            "parent_operation_id": self.parent_operation_id,
            "parent_program": self.parent_program.to_dict(),
            "adapter": {
                "guard": self.adapter_guard.to_dict(),
                "second_input_when_triggered": self.adapted_second_input.to_dict(),
                "second_input_otherwise": {"op": "a_input", "index": 1},
            },
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InputAdapterProgram":
        required = {
            "substrate",
            "parent_operation_id",
            "parent_program",
            "adapter",
        }
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidAdaptiveProgram("input adapter program shape is invalid")
        if value["substrate"] != "anonymous_conditional_input_adapter_v0.1":
            raise InvalidAdaptiveProgram("input adapter substrate is unavailable")
        adapter = value["adapter"]
        if not isinstance(adapter, Mapping) or set(adapter) != {
            "guard",
            "second_input_when_triggered",
            "second_input_otherwise",
        }:
            raise InvalidAdaptiveProgram("input adapter definition is invalid")
        if adapter["second_input_otherwise"] != {"op": "a_input", "index": 1}:
            raise InvalidAdaptiveProgram("input adapter fallback is invalid")
        program = cls(
            parent_operation_id=str(value["parent_operation_id"]),
            parent_program=AdaptiveBranchProgram.from_dict(value["parent_program"]),
            adapter_guard=AdaptiveGuard.from_dict(adapter["guard"]),
            adapted_second_input=AdaptiveValueNode.from_dict(
                adapter["second_input_when_triggered"]
            ),
        )
        InputAdapterExecutor().validate(program)
        return program


@dataclass(frozen=True, slots=True)
class InputAdapterExecution:
    output_value: float
    step_count: int
    adapted_inputs: tuple[float, float]


class InputAdapterExecutor:
    def __init__(self, *, maximum_steps: int = 256) -> None:
        self.value_executor = AdaptiveControlExecutor(maximum_steps=maximum_steps)
        self.parent_executor = AdaptiveBranchExecutor(maximum_steps=maximum_steps)

    def execute(self, program: InputAdapterProgram, inputs) -> InputAdapterExecution:
        numeric_inputs = tuple(float(value) for value in inputs)
        if len(numeric_inputs) != 2:
            raise InvalidAdaptiveProgram("input adapter requires exactly two inputs")
        self.validate(program)
        predicate = self.value_executor._guard(  # noqa: SLF001
            program.adapter_guard, numeric_inputs, 0.0
        )
        if predicate == program.adapter_guard.halt_when:
            second = self.value_executor._evaluate(  # noqa: SLF001
                program.adapted_second_input, numeric_inputs, None
            )
        else:
            second = numeric_inputs[1]
        adapted = (numeric_inputs[0], second)
        result = self.parent_executor.execute(program.parent_program, adapted)
        return InputAdapterExecution(result.output_value, result.step_count, adapted)

    def validate(self, program: InputAdapterProgram) -> None:
        if not program.parent_operation_id:
            raise InvalidAdaptiveProgram("input adapter requires a parent operation")
        self.parent_executor.validate(program.parent_program, 2)
        if program.adapter_guard.op not in ADAPTIVE_GUARD_OPS:
            raise InvalidAdaptiveProgram("input adapter guard is unavailable")
        self.value_executor._validate_node(  # noqa: SLF001
            program.adapter_guard.left, 2, allow_state=False
        )
        self.value_executor._validate_node(  # noqa: SLF001
            program.adapter_guard.right, 2, allow_state=False
        )
        self.value_executor._validate_node(  # noqa: SLF001
            program.adapted_second_input, 2, allow_state=False
        )
        if not _uses_second_input(program.adapted_second_input):
            raise InvalidAdaptiveProgram("adapter expression must depend on second input")


@dataclass(frozen=True, slots=True)
class InputAdapterCandidate:
    candidate_id: str
    program: InputAdapterProgram
    fit_mse: float
    maximum_absolute_error: float
    maximum_steps_used: int
    training_outputs: tuple[float, ...]
    adapted_second_inputs: tuple[float, ...]
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
            "maximum_steps_used": self.maximum_steps_used,
            "training_outputs": list(self.training_outputs),
            "adapted_second_inputs": list(self.adapted_second_inputs),
            "behavior_signature": list(self.behavior_signature),
            "logic_signature": self.logic_signature,
            "program_nodes": self.program.node_count,
            "exact": self.exact,
        }


@dataclass(frozen=True, slots=True)
class InputAdapterSearchReport:
    programs_generated: int
    programs_executed: int
    nonhalting_programs: int
    behavior_classes: int
    evidence_constants: tuple[dict[str, Any], ...]
    top_candidates: tuple[InputAdapterCandidate, ...]
    failed_candidates: tuple["InputAdapterFailure", ...]


@dataclass(frozen=True, slots=True)
class InputAdapterFailure:
    candidate_id: str
    program: InputAdapterProgram
    logic_signature: str
    failed_row: tuple[float, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "program": self.program.to_dict(),
            "logic_signature": self.logic_signature,
            "failed_row": list(self.failed_row),
            "reason": self.reason,
            "exact": False,
        }


class InputAdapterSearch:
    def __init__(
        self,
        parent_program: AdaptiveBranchProgram,
        *,
        parent_operation_id: str,
        top_k: int = 100,
        maximum_evidence_constants: int = 3,
        executor: InputAdapterExecutor | None = None,
    ) -> None:
        self.parent_program = parent_program
        self.parent_operation_id = parent_operation_id
        self.top_k = top_k
        self.maximum_evidence_constants = maximum_evidence_constants
        self.executor = executor or InputAdapterExecutor()

    def search(self, observation: NumericTableObservation) -> InputAdapterSearchReport:
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
        constants = self._derive_constants(valid)
        input_0 = AdaptiveValueNode("a_input", index=0)
        input_1 = AdaptiveValueNode("a_input", index=1)
        constant_nodes = tuple(
            AdaptiveValueNode("a_constant", constant=item["value"])
            for item in constants
        )
        immutable = (input_0, input_1) + constant_nodes
        guard_pairs = tuple(
            pair for source in immutable for pair in ((input_1, source), (source, input_1))
        )
        adapters = [input_1]
        for source in immutable:
            adapters.extend(
                (
                    AdaptiveValueNode("a_add", (input_1, source)),
                    AdaptiveValueNode("a_subtract", (input_1, source)),
                    AdaptiveValueNode("a_subtract", (source, input_1)),
                )
            )
        expected = tuple(output for _, output in valid)
        probe_rows = tuple(row for row, _ in valid) + (
            (-29.0, -6.0),
            (29.0, -6.0),
            (-29.0, 6.0),
        )
        generated = 0
        executed = 0
        nonhalting = 0
        by_logic_behavior: dict[
            tuple[tuple[float | None, ...], str], InputAdapterCandidate
        ] = {}
        behavior_keys: set[tuple[float | None, ...]] = set()
        failures_by_logic: dict[str, InputAdapterFailure] = {}
        for left, right in guard_pairs:
            for guard_op in sorted(ADAPTIVE_GUARD_OPS):
                for trigger_when in (False, True):
                    guard = AdaptiveGuard(guard_op, left, right, trigger_when)
                    for adapter in adapters:
                        generated += 1
                        program = InputAdapterProgram(
                            self.parent_operation_id,
                            self.parent_program,
                            guard,
                            adapter,
                        )
                        outputs = []
                        steps = []
                        adapted_seconds = []
                        failed = False
                        failed_row: tuple[float, ...] | None = None
                        for row, _ in valid:
                            try:
                                result = self.executor.execute(program, row)
                            except InvalidAdaptiveProgram:
                                failed = True
                                failed_row = tuple(row)
                                break
                            outputs.append(result.output_value)
                            steps.append(result.step_count)
                            adapted_seconds.append(result.adapted_inputs[1])
                        if failed:
                            nonhalting += 1
                            logic_signature = input_adapter_logic_signature(program)
                            key = input_adapter_program_key(program)
                            failures_by_logic.setdefault(
                                logic_signature,
                                InputAdapterFailure(
                                    candidate_id="IF-"
                                    + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
                                    program=program,
                                    logic_signature=logic_signature,
                                    failed_row=failed_row or tuple(valid[0][0]),
                                    reason="did_not_halt_within_registered_bound",
                                ),
                            )
                            continue
                        executed += 1
                        errors = tuple(
                            actual - target
                            for actual, target in zip(outputs, expected, strict=True)
                        )
                        behavior: list[float | None] = []
                        for row in probe_rows:
                            try:
                                behavior.append(self.executor.execute(program, row).output_value)
                            except InvalidAdaptiveProgram:
                                behavior.append(None)
                        behavior_key = tuple(behavior)
                        key = input_adapter_program_key(program)
                        logic_signature = input_adapter_logic_signature(program)
                        candidate = InputAdapterCandidate(
                            candidate_id="IA-"
                            + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
                            program=program,
                            fit_mse=sum(error * error for error in errors) / len(errors),
                            maximum_absolute_error=max(abs(error) for error in errors),
                            maximum_steps_used=max(steps),
                            training_outputs=tuple(outputs),
                            adapted_second_inputs=tuple(adapted_seconds),
                            behavior_signature=behavior_key,
                            logic_signature=logic_signature,
                        )
                        behavior_keys.add(behavior_key)
                        dedupe_key = (behavior_key, logic_signature)
                        current = by_logic_behavior.get(dedupe_key)
                        if current is None or self._sort_key(candidate) < self._sort_key(current):
                            by_logic_behavior[dedupe_key] = candidate
        candidates = sorted(by_logic_behavior.values(), key=self._sort_key)
        return InputAdapterSearchReport(
            programs_generated=generated,
            programs_executed=executed,
            nonhalting_programs=nonhalting,
            behavior_classes=len(behavior_keys),
            evidence_constants=constants,
            top_candidates=tuple(candidates[: self.top_k]),
            failed_candidates=tuple(
                failures_by_logic[key] for key in sorted(failures_by_logic)
            ),
        )

    @staticmethod
    def _sort_key(candidate: InputAdapterCandidate) -> tuple[Any, ...]:
        return (
            candidate.fit_mse,
            candidate.program.node_count,
            candidate.maximum_steps_used,
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


def _uses_second_input(node: AdaptiveValueNode) -> bool:
    return (node.op == "a_input" and node.index == 1) or any(
        _uses_second_input(item) for item in node.args
    )


def input_adapter_program_key(program: InputAdapterProgram) -> str:
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))


def input_adapter_logic_signature(program: InputAdapterProgram) -> str:
    value = {
        "parent": program.parent_operation_id,
        "guard_op": program.adapter_guard.op,
        "guard_left": program.adapter_guard.left.op,
        "guard_left_index": program.adapter_guard.left.index,
        "guard_right": program.adapter_guard.right.op,
        "guard_right_index": program.adapter_guard.right.index,
        "trigger_when": program.adapter_guard.halt_when,
        "adapter_op": program.adapted_second_input.op,
        "adapter_children": [item.op for item in program.adapted_second_input.args],
    }
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return "IALOGIC-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
