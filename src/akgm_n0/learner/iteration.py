"""Bounded anonymous state-transition programs for operation growth."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Sequence

from .observation import NumericTableObservation


VALUE_OPERATIONS = frozenset({"p_input", "p_accumulator", "p_add", "p_subtract"})


class InvalidIterationProgram(ValueError):
    """Raised when a state-transition program exceeds its public contract."""


@dataclass(frozen=True, slots=True)
class ValueNode:
    op: str
    args: tuple["ValueNode", ...] = ()
    column_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"op": self.op}
        if self.args:
            value["args"] = [child.to_dict() for child in self.args]
        if self.column_index is not None:
            value["column_index"] = self.column_index
        return value

    @property
    def node_count(self) -> int:
        return 1 + sum(child.node_count for child in self.args)

    @property
    def uses_accumulator(self) -> bool:
        return self.op == "p_accumulator" or any(
            child.uses_accumulator for child in self.args
        )


@dataclass(frozen=True, slots=True)
class IterationProgram:
    count_column: int
    initial: ValueNode
    update: ValueNode

    def to_dict(self) -> dict[str, Any]:
        return {
            "op": "p_iterate",
            "count_source": {"op": "p_input", "column_index": self.count_column},
            "initial_program": self.initial.to_dict(),
            "update_program": self.update.to_dict(),
        }

    @property
    def node_count(self) -> int:
        return 2 + self.initial.node_count + self.update.node_count


class IterationExecutor:
    """Execute one program with strict step, expression, and magnitude limits."""

    def __init__(
        self,
        *,
        maximum_control_steps: int = 64,
        maximum_expression_nodes: int = 3,
        magnitude_limit: float = 1e100,
    ) -> None:
        if maximum_control_steps < 0 or maximum_expression_nodes < 1:
            raise ValueError("execution limits are invalid")
        if not math.isfinite(magnitude_limit) or magnitude_limit <= 0:
            raise ValueError("magnitude_limit must be finite and positive")
        self.maximum_control_steps = maximum_control_steps
        self.maximum_expression_nodes = maximum_expression_nodes
        self.magnitude_limit = magnitude_limit

    def evaluate(self, program: IterationProgram, row: Sequence[float]) -> float:
        inputs = tuple(float(value) for value in row)
        self._validate_program(program, len(inputs))
        if not all(math.isfinite(value) for value in inputs):
            raise InvalidIterationProgram("input row contains a non-finite value")
        raw_count = inputs[program.count_column]
        if raw_count < 0 or not raw_count.is_integer():
            raise InvalidIterationProgram("control count must be a non-negative integer")
        count = int(raw_count)
        if count > self.maximum_control_steps:
            raise InvalidIterationProgram("control count exceeds the registered bound")
        accumulator = self._evaluate_node(program.initial, inputs, None)
        for _ in range(count):
            accumulator = self._evaluate_node(program.update, inputs, accumulator)
        return accumulator

    def _validate_program(self, program: IterationProgram, width: int) -> None:
        if isinstance(program.count_column, bool) or not isinstance(program.count_column, int):
            raise InvalidIterationProgram("count column must be an integer")
        if program.count_column < 0 or program.count_column >= width:
            raise InvalidIterationProgram("count column is outside the input row")
        for node, allow_accumulator in ((program.initial, False), (program.update, True)):
            if node.node_count > self.maximum_expression_nodes:
                raise InvalidIterationProgram("expression exceeds the registered node bound")
            self._validate_node(node, width, allow_accumulator)
        if not program.update.uses_accumulator:
            raise InvalidIterationProgram("update program must depend on its state")

    def _validate_node(self, node: ValueNode, width: int, allow_accumulator: bool) -> None:
        if node.op not in VALUE_OPERATIONS:
            raise InvalidIterationProgram(f"operation is not executable: {node.op}")
        if node.op == "p_input":
            if node.args or node.column_index is None:
                raise InvalidIterationProgram("p_input requires one column index")
            if node.column_index < 0 or node.column_index >= width:
                raise InvalidIterationProgram("input column is outside the row")
            return
        if node.op == "p_accumulator":
            if node.args or node.column_index is not None or not allow_accumulator:
                raise InvalidIterationProgram("state terminal is unavailable here")
            return
        if len(node.args) != 2 or node.column_index is not None:
            raise InvalidIterationProgram(f"{node.op} requires two scalar args")
        for child in node.args:
            self._validate_node(child, width, allow_accumulator)

    def _evaluate_node(
        self, node: ValueNode, inputs: tuple[float, ...], accumulator: float | None
    ) -> float:
        if node.op == "p_input":
            assert node.column_index is not None
            return self._checked(inputs[node.column_index])
        if node.op == "p_accumulator":
            if accumulator is None:
                raise InvalidIterationProgram("state terminal has no current value")
            return self._checked(accumulator)
        left = self._evaluate_node(node.args[0], inputs, accumulator)
        right = self._evaluate_node(node.args[1], inputs, accumulator)
        if node.op == "p_add":
            return self._checked(left + right)
        return self._checked(left - right)

    def _checked(self, value: float) -> float:
        if not math.isfinite(value) or abs(value) > self.magnitude_limit:
            raise InvalidIterationProgram("program produced an unsafe numeric value")
        return float(value)


@dataclass(frozen=True, slots=True)
class IterationCandidate:
    candidate_id: str
    program: IterationProgram
    fit_error: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "program_ast": self.program.to_dict(),
            "fit_error": self.fit_error,
            "program_nodes": self.program.node_count,
        }


@dataclass(frozen=True, slots=True)
class IterationSearchReport:
    programs_generated: int
    valid_row_count: int
    top_candidates: tuple[IterationCandidate, ...]


class IterationProgramSearch:
    """Enumerate small anonymous transition programs using development data only."""

    def __init__(self, *, top_k: int = 20, executor: IterationExecutor | None = None):
        if top_k < 1:
            raise ValueError("top_k must be positive")
        self.top_k = top_k
        self.executor = executor or IterationExecutor()

    def search(self, observation: NumericTableObservation) -> IterationSearchReport:
        valid = [
            (row, output)
            for row, output, include in zip(
                observation.input_rows,
                observation.output_values,
                observation.validity_mask,
                strict=True,
            )
            if include
        ]
        if not valid:
            raise ValueError("search requires at least one valid row")
        width = len(observation.input_rows[0])
        initial_nodes = self._expressions(width, include_accumulator=False)
        update_nodes = tuple(
            node
            for node in self._expressions(width, include_accumulator=True)
            if node.uses_accumulator
        )
        candidates: list[IterationCandidate] = []
        generated = 0
        for count_column in range(width):
            for initial in initial_nodes:
                for update in update_nodes:
                    program = IterationProgram(count_column, initial, update)
                    generated += 1
                    try:
                        errors = [
                            self.executor.evaluate(program, row) - output
                            for row, output in valid
                        ]
                    except InvalidIterationProgram:
                        continue
                    fit_error = sum(error * error for error in errors) / len(errors)
                    payload = json.dumps(
                        program.to_dict(), sort_keys=True, separators=(",", ":")
                    ).encode("utf-8")
                    candidate_id = "CAND-" + hashlib.sha256(payload).hexdigest()[:16]
                    candidates.append(IterationCandidate(candidate_id, program, fit_error))
        candidates.sort(
            key=lambda item: (item.fit_error, item.program.node_count, item.candidate_id)
        )
        return IterationSearchReport(generated, len(valid), tuple(candidates[: self.top_k]))

    @staticmethod
    def _expressions(width: int, *, include_accumulator: bool) -> tuple[ValueNode, ...]:
        terminals = [ValueNode("p_input", column_index=index) for index in range(width)]
        if include_accumulator:
            terminals.append(ValueNode("p_accumulator"))
        nodes = list(terminals)
        for op in ("p_add", "p_subtract"):
            for left in terminals:
                for right in terminals:
                    nodes.append(ValueNode(op, args=(left, right)))
        unique: dict[str, ValueNode] = {}
        for node in nodes:
            key = json.dumps(node.to_dict(), sort_keys=True, separators=(",", ":"))
            unique[key] = node
        return tuple(unique[key] for key in sorted(unique))
