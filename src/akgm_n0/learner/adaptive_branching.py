"""Grow a verified controller by synthesizing a higher-priority state branch."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .adaptive_control import (
    ADAPTIVE_GUARD_OPS,
    AdaptiveControlExecutor,
    AdaptiveControlProgram,
    AdaptiveExecution,
    AdaptiveGuard,
    AdaptiveValueNode,
    InvalidAdaptiveProgram,
)
from .observation import NumericTableObservation


@dataclass(frozen=True, slots=True)
class AdaptiveBranchProgram:
    parent_operation_id: str
    base_program: AdaptiveControlProgram
    branch_guard: AdaptiveGuard
    branch_update: AdaptiveValueNode

    @property
    def node_count(self) -> int:
        return (
            self.base_program.node_count
            + self.branch_guard.node_count
            + self.branch_update.node_count
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "anonymous_priority_branch_control_v0.1",
            "parent_operation_id": self.parent_operation_id,
            "base_program": self.base_program.to_dict(),
            "priority_branch": {
                "guard": self.branch_guard.to_dict(),
                "update_when_triggered": self.branch_update.to_dict(),
                "then": "restart_control_cycle",
            },
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AdaptiveBranchProgram":
        required = {
            "substrate",
            "parent_operation_id",
            "base_program",
            "priority_branch",
        }
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidAdaptiveProgram("branch program shape is invalid")
        if value["substrate"] != "anonymous_priority_branch_control_v0.1":
            raise InvalidAdaptiveProgram("branch program substrate is unavailable")
        branch = value["priority_branch"]
        if not isinstance(branch, Mapping) or set(branch) != {
            "guard",
            "update_when_triggered",
            "then",
        }:
            raise InvalidAdaptiveProgram("priority branch shape is invalid")
        if branch["then"] != "restart_control_cycle":
            raise InvalidAdaptiveProgram("priority branch continuation is invalid")
        program = cls(
            parent_operation_id=str(value["parent_operation_id"]),
            base_program=AdaptiveControlProgram.from_dict(value["base_program"]),
            branch_guard=AdaptiveGuard.from_dict(branch["guard"]),
            branch_update=AdaptiveValueNode.from_dict(
                branch["update_when_triggered"]
            ),
        )
        AdaptiveBranchExecutor().validate(program, 2)
        return program


class AdaptiveBranchExecutor:
    """Execute a candidate branch before a previously verified controller."""

    def __init__(self, *, maximum_steps: int = 256) -> None:
        self.maximum_steps = maximum_steps
        self.base_executor = AdaptiveControlExecutor(maximum_steps=maximum_steps)

    def execute(self, program: AdaptiveBranchProgram, inputs) -> AdaptiveExecution:
        numeric_inputs = tuple(float(value) for value in inputs)
        self.validate(program, len(numeric_inputs))
        state = self.base_executor._evaluate(  # noqa: SLF001 - shared substrate
            program.base_program.initial_state, numeric_inputs, None
        )
        for step in range(self.maximum_steps + 1):
            branch_predicate = self.base_executor._guard(  # noqa: SLF001
                program.branch_guard, numeric_inputs, state
            )
            if branch_predicate == program.branch_guard.halt_when:
                if step == self.maximum_steps:
                    break
                state = self.base_executor._evaluate(  # noqa: SLF001
                    program.branch_update, numeric_inputs, state
                )
                continue
            base_predicate = self.base_executor._guard(  # noqa: SLF001
                program.base_program.guard, numeric_inputs, state
            )
            if base_predicate == program.base_program.guard.halt_when:
                output = self.base_executor._evaluate(  # noqa: SLF001
                    program.base_program.output, numeric_inputs, state
                )
                return AdaptiveExecution(output, step, state)
            if step == self.maximum_steps:
                break
            state = self.base_executor._evaluate(  # noqa: SLF001
                program.base_program.update, numeric_inputs, state
            )
        raise InvalidAdaptiveProgram("branch controller did not halt within bound")

    def validate(self, program: AdaptiveBranchProgram, input_width: int) -> None:
        if not program.parent_operation_id:
            raise InvalidAdaptiveProgram("branch controller requires a parent operation")
        self.base_executor.validate(program.base_program, input_width)
        if program.branch_guard.op not in ADAPTIVE_GUARD_OPS:
            raise InvalidAdaptiveProgram("branch guard operation is unavailable")
        self.base_executor._validate_node(  # noqa: SLF001
            program.branch_guard.left, input_width, allow_state=True
        )
        self.base_executor._validate_node(  # noqa: SLF001
            program.branch_guard.right, input_width, allow_state=True
        )
        self.base_executor._validate_node(  # noqa: SLF001
            program.branch_update, input_width, allow_state=True
        )
        if not self.base_executor._uses_state(program.branch_update):  # noqa: SLF001
            raise InvalidAdaptiveProgram("branch update must depend on state")


@dataclass(frozen=True, slots=True)
class AdaptiveBranchCandidate:
    candidate_id: str
    program: AdaptiveBranchProgram
    fit_mse: float
    maximum_absolute_error: float
    maximum_steps_used: int
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
            "maximum_steps_used": self.maximum_steps_used,
            "training_outputs": list(self.training_outputs),
            "behavior_signature": list(self.behavior_signature),
            "logic_signature": self.logic_signature,
            "program_nodes": self.program.node_count,
            "exact": self.exact,
        }


@dataclass(frozen=True, slots=True)
class AdaptiveBranchSearchReport:
    programs_generated: int
    programs_executed: int
    nonhalting_programs: int
    behavior_classes: int
    evidence_constants: tuple[dict[str, Any], ...]
    top_candidates: tuple[AdaptiveBranchCandidate, ...]


class AdaptiveBranchSearch:
    """Search one generic priority branch around a verified parent controller."""

    def __init__(
        self,
        base_program: AdaptiveControlProgram,
        *,
        parent_operation_id: str,
        top_k: int = 100,
        maximum_evidence_constants: int = 3,
        executor: AdaptiveBranchExecutor | None = None,
    ) -> None:
        self.base_program = base_program
        self.parent_operation_id = parent_operation_id
        self.top_k = top_k
        self.maximum_evidence_constants = maximum_evidence_constants
        self.executor = executor or AdaptiveBranchExecutor()

    def search(self, observation: NumericTableObservation) -> AdaptiveBranchSearchReport:
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
        width = len(valid[0][0])
        constants = self._derive_constants(valid)
        inputs = tuple(AdaptiveValueNode("a_input", index=index) for index in range(width))
        constant_nodes = tuple(
            AdaptiveValueNode("a_constant", constant=item["value"])
            for item in constants
        )
        state = AdaptiveValueNode("a_state")
        immutable = inputs + constant_nodes
        guard_pairs = tuple(
            pair for source in immutable for pair in ((state, source), (source, state))
        )
        update_nodes = [state]
        for source in immutable:
            update_nodes.extend(
                (
                    AdaptiveValueNode("a_add", (state, source)),
                    AdaptiveValueNode("a_subtract", (state, source)),
                    AdaptiveValueNode("a_subtract", (source, state)),
                )
            )
        expected = tuple(output for _, output in valid)
        probe_rows = tuple(row for row, _ in valid) + (
            (-29.0, 6.0),
            (-2.0, 9.0),
            (29.0, 6.0),
        )
        generated = 0
        executed = 0
        nonhalting = 0
        by_behavior: dict[tuple[float | None, ...], AdaptiveBranchCandidate] = {}
        for left, right in guard_pairs:
            for guard_op in sorted(ADAPTIVE_GUARD_OPS):
                for trigger_when in (False, True):
                    guard = AdaptiveGuard(guard_op, left, right, trigger_when)
                    for update in update_nodes:
                        generated += 1
                        program = AdaptiveBranchProgram(
                            self.parent_operation_id,
                            self.base_program,
                            guard,
                            update,
                        )
                        outputs = []
                        steps = []
                        failed = False
                        for row, _ in valid:
                            try:
                                result = self.executor.execute(program, row)
                            except InvalidAdaptiveProgram:
                                failed = True
                                break
                            outputs.append(result.output_value)
                            steps.append(result.step_count)
                        if failed:
                            nonhalting += 1
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
                        key = adaptive_branch_program_key(program)
                        candidate = AdaptiveBranchCandidate(
                            candidate_id="AB-"
                            + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
                            program=program,
                            fit_mse=sum(error * error for error in errors) / len(errors),
                            maximum_absolute_error=max(abs(error) for error in errors),
                            maximum_steps_used=max(steps),
                            training_outputs=tuple(outputs),
                            behavior_signature=behavior_key,
                            logic_signature=adaptive_branch_logic_signature(program),
                        )
                        current = by_behavior.get(behavior_key)
                        if current is None or self._sort_key(candidate) < self._sort_key(current):
                            by_behavior[behavior_key] = candidate
        candidates = sorted(by_behavior.values(), key=self._sort_key)
        return AdaptiveBranchSearchReport(
            programs_generated=generated,
            programs_executed=executed,
            nonhalting_programs=nonhalting,
            behavior_classes=len(candidates),
            evidence_constants=constants,
            top_candidates=tuple(candidates[: self.top_k]),
        )

    @staticmethod
    def _sort_key(candidate: AdaptiveBranchCandidate) -> tuple[Any, ...]:
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


def adaptive_branch_program_key(program: AdaptiveBranchProgram) -> str:
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))


def adaptive_branch_logic_signature(program: AdaptiveBranchProgram) -> str:
    value = {
        "parent": program.parent_operation_id,
        "guard_op": program.branch_guard.op,
        "guard_left": program.branch_guard.left.op,
        "guard_right": program.branch_guard.right.op,
        "guard_right_index": program.branch_guard.right.index,
        "trigger_when": program.branch_guard.halt_when,
        "update_op": program.branch_update.op,
        "update_children": [item.op for item in program.branch_update.args],
    }
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return "ABLOGIC-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
