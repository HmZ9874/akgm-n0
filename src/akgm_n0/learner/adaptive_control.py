"""Synthesize a bounded loop from anonymous numeric input/output rows."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .observation import NumericTableObservation


ADAPTIVE_VALUE_OPS = frozenset(
    {"a_input", "a_state", "a_constant", "a_add", "a_subtract"}
)
ADAPTIVE_GUARD_OPS = frozenset({"a_equal", "a_less"})


class InvalidAdaptiveProgram(ValueError):
    """Raised when a synthesized controller is unsafe or malformed."""


@dataclass(frozen=True, slots=True)
class AdaptiveValueNode:
    op: str
    args: tuple["AdaptiveValueNode", ...] = ()
    index: int | None = None
    constant: float | None = None

    @property
    def node_count(self) -> int:
        return 1 + sum(child.node_count for child in self.args)

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"op": self.op}
        if self.args:
            value["args"] = [child.to_dict() for child in self.args]
        if self.index is not None:
            value["index"] = self.index
        if self.constant is not None:
            value["constant"] = self.constant
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AdaptiveValueNode":
        if not isinstance(value, Mapping) or not isinstance(value.get("op"), str):
            raise InvalidAdaptiveProgram("adaptive value node must be a mapping")
        if set(value) - {"op", "args", "index", "constant"}:
            raise InvalidAdaptiveProgram("adaptive value node has unknown fields")
        raw_args = value.get("args", ())
        if not isinstance(raw_args, (list, tuple)):
            raise InvalidAdaptiveProgram("adaptive value args must be a sequence")
        raw_index = value.get("index")
        if raw_index is not None and (
            isinstance(raw_index, bool) or not isinstance(raw_index, int)
        ):
            raise InvalidAdaptiveProgram("adaptive value index must be an integer")
        raw_constant = value.get("constant")
        if raw_constant is not None and (
            isinstance(raw_constant, bool)
            or not isinstance(raw_constant, (int, float))
            or not math.isfinite(float(raw_constant))
        ):
            raise InvalidAdaptiveProgram("adaptive value constant must be finite")
        return cls(
            op=str(value["op"]),
            args=tuple(cls.from_dict(item) for item in raw_args),
            index=raw_index,
            constant=raw_constant,
        )


@dataclass(frozen=True, slots=True)
class AdaptiveGuard:
    op: str
    left: AdaptiveValueNode
    right: AdaptiveValueNode
    halt_when: bool

    @property
    def node_count(self) -> int:
        return 1 + self.left.node_count + self.right.node_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "halt_when": self.halt_when,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AdaptiveGuard":
        if not isinstance(value, Mapping) or set(value) != {
            "op",
            "left",
            "right",
            "halt_when",
        }:
            raise InvalidAdaptiveProgram("adaptive guard shape is invalid")
        if not isinstance(value["halt_when"], bool):
            raise InvalidAdaptiveProgram("adaptive guard polarity must be boolean")
        return cls(
            op=str(value["op"]),
            left=AdaptiveValueNode.from_dict(value["left"]),
            right=AdaptiveValueNode.from_dict(value["right"]),
            halt_when=value["halt_when"],
        )


@dataclass(frozen=True, slots=True)
class AdaptiveControlProgram:
    initial_state: AdaptiveValueNode
    guard: AdaptiveGuard
    update: AdaptiveValueNode
    output: AdaptiveValueNode

    @property
    def node_count(self) -> int:
        return (
            self.initial_state.node_count
            + self.guard.node_count
            + self.update.node_count
            + self.output.node_count
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "anonymous_single_state_control_v0.1",
            "initial_state": self.initial_state.to_dict(),
            "guard": self.guard.to_dict(),
            "update_when_continuing": self.update.to_dict(),
            "output": self.output.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AdaptiveControlProgram":
        required = {
            "substrate",
            "initial_state",
            "guard",
            "update_when_continuing",
            "output",
        }
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidAdaptiveProgram("adaptive program shape is invalid")
        if value["substrate"] != "anonymous_single_state_control_v0.1":
            raise InvalidAdaptiveProgram("adaptive program substrate is unavailable")
        program = cls(
            initial_state=AdaptiveValueNode.from_dict(value["initial_state"]),
            guard=AdaptiveGuard.from_dict(value["guard"]),
            update=AdaptiveValueNode.from_dict(value["update_when_continuing"]),
            output=AdaptiveValueNode.from_dict(value["output"]),
        )
        AdaptiveControlExecutor().validate(program, 2)
        return program


@dataclass(frozen=True, slots=True)
class AdaptiveExecution:
    output_value: float
    step_count: int
    final_state: float


class AdaptiveControlExecutor:
    """Run candidate-defined halt and update rules over one mutable state cell."""

    def __init__(
        self,
        *,
        maximum_steps: int = 256,
        maximum_expression_nodes: int = 3,
        magnitude_limit: float = 1e100,
    ) -> None:
        if maximum_steps < 1 or maximum_expression_nodes < 1:
            raise ValueError("adaptive execution limits must be positive")
        self.maximum_steps = maximum_steps
        self.maximum_expression_nodes = maximum_expression_nodes
        self.magnitude_limit = magnitude_limit

    def execute(
        self, program: AdaptiveControlProgram, inputs: Sequence[float]
    ) -> AdaptiveExecution:
        numeric_inputs = tuple(float(value) for value in inputs)
        if not numeric_inputs or not all(math.isfinite(value) for value in numeric_inputs):
            raise InvalidAdaptiveProgram("adaptive inputs must be finite and nonempty")
        self.validate(program, len(numeric_inputs))
        state = self._evaluate(program.initial_state, numeric_inputs, None)
        for step in range(self.maximum_steps + 1):
            predicate = self._guard(program.guard, numeric_inputs, state)
            if predicate == program.guard.halt_when:
                output = self._evaluate(program.output, numeric_inputs, state)
                return AdaptiveExecution(output, step, state)
            if step == self.maximum_steps:
                break
            state = self._evaluate(program.update, numeric_inputs, state)
        raise InvalidAdaptiveProgram("candidate did not halt within the registered bound")

    def validate(self, program: AdaptiveControlProgram, input_width: int) -> None:
        self._validate_node(program.initial_state, input_width, allow_state=False)
        self._validate_node(program.guard.left, input_width, allow_state=True)
        self._validate_node(program.guard.right, input_width, allow_state=True)
        self._validate_node(program.update, input_width, allow_state=True)
        self._validate_node(program.output, input_width, allow_state=True)
        if program.guard.op not in ADAPTIVE_GUARD_OPS:
            raise InvalidAdaptiveProgram("adaptive guard operation is unregistered")
        if not isinstance(program.guard.halt_when, bool):
            raise InvalidAdaptiveProgram("adaptive halt polarity must be boolean")
        if not self._uses_state(program.update):
            raise InvalidAdaptiveProgram("adaptive update must depend on state")

    def _validate_node(
        self, node: AdaptiveValueNode, input_width: int, *, allow_state: bool
    ) -> None:
        if node.op not in ADAPTIVE_VALUE_OPS or node.node_count > self.maximum_expression_nodes:
            raise InvalidAdaptiveProgram("adaptive expression is unregistered or too large")
        if node.op == "a_input":
            if node.args or node.index is None or node.constant is not None:
                raise InvalidAdaptiveProgram("adaptive input node shape is invalid")
            if not 0 <= node.index < input_width:
                raise InvalidAdaptiveProgram("adaptive input index is unavailable")
            return
        if node.op == "a_state":
            if not allow_state or node.args or node.index is not None or node.constant is not None:
                raise InvalidAdaptiveProgram("adaptive state node shape is invalid")
            return
        if node.op == "a_constant":
            if (
                node.args
                or node.index is not None
                or node.constant is None
                or not math.isfinite(node.constant)
            ):
                raise InvalidAdaptiveProgram("adaptive constant node shape is invalid")
            return
        if len(node.args) != 2 or node.index is not None or node.constant is not None:
            raise InvalidAdaptiveProgram("adaptive binary node shape is invalid")
        for child in node.args:
            self._validate_node(child, input_width, allow_state=allow_state)

    def _guard(
        self, guard: AdaptiveGuard, inputs: tuple[float, ...], state: float
    ) -> bool:
        left = self._evaluate(guard.left, inputs, state)
        right = self._evaluate(guard.right, inputs, state)
        return left == right if guard.op == "a_equal" else left < right

    def _evaluate(
        self,
        node: AdaptiveValueNode,
        inputs: tuple[float, ...],
        state: float | None,
    ) -> float:
        if node.op == "a_input":
            assert node.index is not None
            return self._checked(inputs[node.index])
        if node.op == "a_state":
            if state is None:
                raise InvalidAdaptiveProgram("state is unavailable during initialization")
            return self._checked(state)
        if node.op == "a_constant":
            assert node.constant is not None
            return self._checked(node.constant)
        left = self._evaluate(node.args[0], inputs, state)
        right = self._evaluate(node.args[1], inputs, state)
        return self._checked(left + right if node.op == "a_add" else left - right)

    def _checked(self, value: float) -> float:
        numeric = float(value)
        if not math.isfinite(numeric) or abs(numeric) > self.magnitude_limit:
            raise InvalidAdaptiveProgram("adaptive program produced unsafe magnitude")
        return numeric

    @staticmethod
    def _uses_state(node: AdaptiveValueNode) -> bool:
        return node.op == "a_state" or any(
            AdaptiveControlExecutor._uses_state(child) for child in node.args
        )


@dataclass(frozen=True, slots=True)
class AdaptiveCandidate:
    candidate_id: str
    program: AdaptiveControlProgram
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
class AdaptiveSearchReport:
    programs_generated: int
    programs_executed: int
    nonhalting_programs: int
    behavior_classes: int
    evidence_constants: tuple[dict[str, Any], ...]
    top_candidates: tuple[AdaptiveCandidate, ...]


class AdaptiveControlSearch:
    """Enumerate generic state, guard, update, and halt choices."""

    def __init__(
        self,
        *,
        top_k: int = 200,
        maximum_evidence_constants: int = 3,
        executor: AdaptiveControlExecutor | None = None,
    ) -> None:
        self.top_k = top_k
        self.maximum_evidence_constants = maximum_evidence_constants
        self.executor = executor or AdaptiveControlExecutor()

    def search(self, observation: NumericTableObservation) -> AdaptiveSearchReport:
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
            raise ValueError("adaptive search requires valid rows")
        width = len(valid[0][0])
        constants = self._derive_constants(valid)
        inputs = tuple(AdaptiveValueNode("a_input", index=index) for index in range(width))
        constant_nodes = tuple(
            AdaptiveValueNode("a_constant", constant=item["value"])
            for item in constants
        )
        state = AdaptiveValueNode("a_state")
        immutable = inputs + constant_nodes
        initial_nodes = immutable
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
        output_nodes = (state,) + inputs + constant_nodes

        generated = 0
        executed = 0
        nonhalting = 0
        candidates_by_behavior: dict[tuple[float | None, ...], AdaptiveCandidate] = {}
        probe_rows = tuple(row for row, _ in valid) + (
            tuple(float(index + 2) for index in range(width)),
            tuple(float((index + 2) * 3) for index in range(width)),
        )
        expected = tuple(output for _, output in valid)
        for initial in initial_nodes:
            for left, right in guard_pairs:
                for guard_op in sorted(ADAPTIVE_GUARD_OPS):
                    for halt_when in (False, True):
                        guard = AdaptiveGuard(guard_op, left, right, halt_when)
                        for update in update_nodes:
                            for output_node in output_nodes:
                                generated += 1
                                program = AdaptiveControlProgram(
                                    initial, guard, update, output_node
                                )
                                outputs = []
                                steps = []
                                failed = False
                                for row, _ in valid:
                                    try:
                                        execution = self.executor.execute(program, row)
                                    except InvalidAdaptiveProgram:
                                        failed = True
                                        break
                                    outputs.append(execution.output_value)
                                    steps.append(execution.step_count)
                                if failed:
                                    nonhalting += 1
                                    continue
                                executed += 1
                                errors = tuple(
                                    actual - target
                                    for actual, target in zip(outputs, expected, strict=True)
                                )
                                probe_signature: list[float | None] = []
                                for row in probe_rows:
                                    try:
                                        probe_signature.append(
                                            self.executor.execute(program, row).output_value
                                        )
                                    except InvalidAdaptiveProgram:
                                        probe_signature.append(None)
                                behavior = tuple(probe_signature)
                                key = adaptive_program_key(program)
                                candidate = AdaptiveCandidate(
                                    candidate_id="AC-"
                                    + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
                                    program=program,
                                    fit_mse=sum(error * error for error in errors)
                                    / len(errors),
                                    maximum_absolute_error=max(abs(error) for error in errors),
                                    maximum_steps_used=max(steps),
                                    training_outputs=tuple(outputs),
                                    behavior_signature=behavior,
                                    logic_signature=adaptive_logic_signature(program),
                                )
                                existing = candidates_by_behavior.get(behavior)
                                if existing is None or self._sort_key(candidate) < self._sort_key(
                                    existing
                                ):
                                    candidates_by_behavior[behavior] = candidate
        candidates = sorted(candidates_by_behavior.values(), key=self._sort_key)
        return AdaptiveSearchReport(
            programs_generated=generated,
            programs_executed=executed,
            nonhalting_programs=nonhalting,
            behavior_classes=len(candidates_by_behavior),
            evidence_constants=constants,
            top_candidates=tuple(candidates[: self.top_k]),
        )

    @staticmethod
    def _sort_key(candidate: AdaptiveCandidate) -> tuple[Any, ...]:
        return (
            candidate.fit_mse,
            candidate.program.node_count,
            candidate.maximum_steps_used,
            candidate.candidate_id,
        )

    def _derive_constants(
        self, valid: tuple[tuple[tuple[float, ...], float], ...]
    ) -> tuple[dict[str, Any], ...]:
        atoms = sorted({value for row, output in valid for value in (*row, output)})
        derived: dict[float, dict[str, Any]] = {}
        for left in atoms:
            for right in atoms:
                value = float(left - right)
                derived.setdefault(
                    value,
                    {
                        "value": value,
                        "provenance": {
                            "op": "subtract_observed_numeric_atoms",
                            "left": left,
                            "right": right,
                        },
                    },
                )
        return tuple(
            sorted(derived.values(), key=lambda item: (abs(item["value"]), item["value"]))[
                : self.maximum_evidence_constants
            ]
        )


def adaptive_program_key(program: AdaptiveControlProgram) -> str:
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))


def adaptive_logic_signature(program: AdaptiveControlProgram) -> str:
    def shape(node: AdaptiveValueNode) -> Any:
        return {"op": node.op, "index": node.index, "args": [shape(item) for item in node.args]}

    value = {
        "initial": shape(program.initial_state),
        "guard": {
            "op": program.guard.op,
            "left": shape(program.guard.left),
            "right": shape(program.guard.right),
            "halt_when": program.guard.halt_when,
        },
        "update": shape(program.update),
        "output": shape(program.output),
    }
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return "ALOGIC-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
