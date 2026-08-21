"""Small, auditable numerical program language for Gen 0."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


EXECUTABLE_OPERATIONS = frozenset(
    {"p_read_offset", "p_add", "p_subtract", "p_scalar_parameter"}
)
_ARGUMENT_SLOT = "$argument"


class InvalidProgram(ValueError):
    """Raised when an AST is malformed or outside the declared language."""


class NumericExecutionError(ArithmeticError):
    """Raised when a valid program cannot safely execute on an observation."""


@dataclass(frozen=True, slots=True)
class ProgramNode:
    op: str
    args: tuple["ProgramNode", ...] = ()
    offset: int | None = None
    parameter_slot: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"op": self.op}
        if self.args:
            result["args"] = [child.to_dict() for child in self.args]
        if self.offset is not None:
            result["offset"] = self.offset
        if self.parameter_slot is not None:
            result["parameter_slot"] = self.parameter_slot
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProgramNode":
        if not isinstance(value, Mapping):
            raise InvalidProgram("program node must be an object")
        allowed_keys = {"op", "args", "offset", "parameter_slot"}
        unexpected = set(value) - allowed_keys
        if unexpected:
            raise InvalidProgram(f"unexpected program keys: {sorted(unexpected)}")
        op = value.get("op")
        if not isinstance(op, str) or not op:
            raise InvalidProgram("program node requires a non-empty op")
        raw_args = value.get("args", [])
        if not isinstance(raw_args, list):
            raise InvalidProgram("program args must be an array")
        args = tuple(cls.from_dict(child) for child in raw_args)
        offset = value.get("offset")
        parameter_slot = value.get("parameter_slot")
        if offset is not None and (isinstance(offset, bool) or not isinstance(offset, int)):
            raise InvalidProgram("offset must be an integer")
        if parameter_slot is not None and (
            isinstance(parameter_slot, bool)
            or not isinstance(parameter_slot, int)
            or parameter_slot < 0
        ):
            raise InvalidProgram("parameter_slot must be a non-negative integer")
        return cls(op=op, args=args, offset=offset, parameter_slot=parameter_slot)


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    sequence_values: tuple[float, ...]
    validity_mask: tuple[bool, ...]
    index: int
    parameters: Mapping[int, float]

    @classmethod
    def create(
        cls,
        sequence_values: Sequence[float],
        *,
        index: int,
        parameters: Mapping[int, float] | None = None,
        validity_mask: Sequence[bool] | None = None,
    ) -> "ExecutionContext":
        values = tuple(float(value) for value in sequence_values)
        mask = (
            tuple(True for _ in values)
            if validity_mask is None
            else tuple(bool(value) for value in validity_mask)
        )
        if len(values) != len(mask):
            raise ValueError("sequence_values and validity_mask lengths differ")
        return cls(values, mask, index, dict(parameters or {}))


class ProgramExecutor:
    """Execute a candidate with explicit resource and numeric safety limits."""

    def __init__(
        self,
        *,
        maximum_nodes: int = 64,
        maximum_depth: int = 16,
        magnitude_limit: float = 1e100,
        library: Mapping[str, ProgramNode] | None = None,
    ) -> None:
        if maximum_nodes < 1 or maximum_depth < 1 or magnitude_limit <= 0:
            raise ValueError("execution limits must be positive")
        self.maximum_nodes = maximum_nodes
        self.maximum_depth = maximum_depth
        self.magnitude_limit = magnitude_limit
        self.library = dict(library or {})
        self._validate_library()

    def evaluate(self, program: ProgramNode, context: ExecutionContext) -> float:
        self._validate_shape(program)
        result = self._evaluate_node(program, context)
        return self._checked_number(result)

    def evaluate_over_valid_indices(
        self, program: ProgramNode, context: ExecutionContext
    ) -> tuple[float | None, ...]:
        results: list[float | None] = []
        for index in range(len(context.sequence_values)):
            indexed_context = ExecutionContext(
                context.sequence_values,
                context.validity_mask,
                index,
                context.parameters,
            )
            try:
                results.append(self.evaluate(program, indexed_context))
            except NumericExecutionError:
                results.append(None)
        return tuple(results)

    def _validate_shape(self, root: ProgramNode) -> None:
        stack: list[tuple[ProgramNode, int]] = [(root, 1)]
        seen_nodes = 0
        while stack:
            node, depth = stack.pop()
            seen_nodes += 1
            if seen_nodes > self.maximum_nodes:
                raise InvalidProgram("program exceeds maximum node count")
            if depth > self.maximum_depth:
                raise InvalidProgram("program exceeds maximum depth")
            if node.op in self.library:
                if node.args or node.offset is not None or node.parameter_slot is not None:
                    raise InvalidProgram("library calls cannot carry inline arguments")
                stack.append((self.library[node.op], depth + 1))
                continue
            if node.op not in EXECUTABLE_OPERATIONS:
                raise InvalidProgram(f"operation is not executable: {node.op}")
            self._validate_node_signature(node)
            stack.extend((child, depth + 1) for child in node.args)

    @staticmethod
    def _validate_node_signature(node: ProgramNode) -> None:
        if node.op == "p_read_offset":
            if node.args or node.offset not in {-1, 0, 1} or node.parameter_slot is not None:
                raise InvalidProgram("p_read_offset requires one registered offset and no args")
        elif node.op in {"p_add", "p_subtract"}:
            if len(node.args) != 2 or node.offset is not None or node.parameter_slot is not None:
                raise InvalidProgram(f"{node.op} requires exactly two scalar args")
        elif node.op == "p_scalar_parameter":
            if node.args or node.offset is not None or node.parameter_slot is None:
                raise InvalidProgram("p_scalar_parameter requires one parameter slot")

    def _evaluate_node(self, node: ProgramNode, context: ExecutionContext) -> float:
        if node.op in self.library:
            return self._evaluate_node(self.library[node.op], context)
        if node.op == "p_read_offset":
            assert node.offset is not None
            target_index = context.index + node.offset
            if target_index < 0 or target_index >= len(context.sequence_values):
                raise NumericExecutionError("indexed read is outside the observation")
            if not context.validity_mask[target_index]:
                raise NumericExecutionError("indexed read points to an invalid observation")
            return self._checked_number(context.sequence_values[target_index])
        if node.op == "p_scalar_parameter":
            assert node.parameter_slot is not None
            try:
                value = context.parameters[node.parameter_slot]
            except KeyError as exc:
                raise NumericExecutionError(
                    f"missing scalar parameter slot {node.parameter_slot}"
                ) from exc
            return self._checked_number(value)

        left = self._evaluate_node(node.args[0], context)
        right = self._evaluate_node(node.args[1], context)
        if node.op == "p_add":
            return self._checked_number(left + right)
        if node.op == "p_subtract":
            return self._checked_number(left - right)
        raise InvalidProgram(f"unsupported operation: {node.op}")

    def _checked_number(self, value: float) -> float:
        numeric = float(value)
        if not math.isfinite(numeric):
            raise NumericExecutionError("program produced a non-finite value")
        if abs(numeric) > self.magnitude_limit:
            raise NumericExecutionError("program exceeded the magnitude limit")
        return numeric

    def _validate_library(self) -> None:
        for concept_id in self.library:
            if not concept_id.startswith("C-"):
                raise InvalidProgram("learned primitive ids must start with C-")
            if concept_id in EXECUTABLE_OPERATIONS or concept_id == _ARGUMENT_SLOT:
                raise InvalidProgram("learned primitive id conflicts with the base language")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(concept_id: str) -> None:
            if concept_id in visited:
                return
            if concept_id in visiting:
                raise InvalidProgram("learned primitive library contains a cycle")
            visiting.add(concept_id)
            stack = [self.library[concept_id]]
            dependencies: set[str] = set()
            while stack:
                node = stack.pop()
                if node.op in self.library:
                    dependencies.add(node.op)
                stack.extend(node.args)
            for dependency in dependencies:
                visit(dependency)
            visiting.remove(concept_id)
            visited.add(concept_id)

        for concept_id in self.library:
            visit(concept_id)


def read_offset(offset: int) -> ProgramNode:
    return ProgramNode("p_read_offset", offset=offset)


def parameter(slot: int) -> ProgramNode:
    return ProgramNode("p_scalar_parameter", parameter_slot=slot)


def add(left: ProgramNode, right: ProgramNode) -> ProgramNode:
    return ProgramNode("p_add", args=(left, right))


def subtract(left: ProgramNode, right: ProgramNode) -> ProgramNode:
    return ProgramNode("p_subtract", args=(left, right))


def library_call(concept_id: str) -> ProgramNode:
    if not concept_id.startswith("C-"):
        raise InvalidProgram("learned primitive ids must start with C-")
    return ProgramNode(concept_id)


def argument() -> ProgramNode:
    """Create the anonymous argument slot used only while composing programs."""

    return ProgramNode(_ARGUMENT_SLOT)


def compose(outer_template: ProgramNode, inner: ProgramNode) -> ProgramNode:
    """Apply a program template to another program without adding a runtime op."""

    replacements = 0

    def replace(node: ProgramNode) -> ProgramNode:
        nonlocal replacements
        if node.op == _ARGUMENT_SLOT:
            if node.args or node.offset is not None or node.parameter_slot is not None:
                raise InvalidProgram("argument slot cannot carry data")
            replacements += 1
            return inner
        return ProgramNode(
            op=node.op,
            args=tuple(replace(child) for child in node.args),
            offset=node.offset,
            parameter_slot=node.parameter_slot,
        )

    result = replace(outer_template)
    if replacements == 0:
        raise InvalidProgram("outer template does not contain an argument slot")
    return result
