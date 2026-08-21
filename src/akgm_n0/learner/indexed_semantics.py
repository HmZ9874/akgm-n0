"""Discover ordered numeric relations by reusing opaque executable semantics."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .observation import NumericObservation
from .semantic_slot import InvalidMicroProgram, MicroProgram, MicroProgramExecutor


INDEXED_OPERATIONS = frozenset(
    {"q_index", "q_constant", "q_add", "q_subtract", "q_semantic_call"}
)


class InvalidIndexedProgram(ValueError):
    """Raised when an indexed composition is malformed or cannot execute."""


@dataclass(frozen=True, slots=True)
class IndexedNode:
    op: str
    args: tuple["IndexedNode", ...] = ()
    constant: float | None = None
    operation_id: str | None = None

    @property
    def node_count(self) -> int:
        return 1 + sum(child.node_count for child in self.args)

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"op": self.op}
        if self.args:
            value["args"] = [child.to_dict() for child in self.args]
        if self.constant is not None:
            value["constant"] = self.constant
        if self.operation_id is not None:
            value["operation_id"] = self.operation_id
        return value


@dataclass(frozen=True, slots=True)
class DifferenceWorkspace:
    first_layer: tuple[float, ...]
    second_layer: tuple[float, ...]
    evidence_constants: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "construction": "generic_adjacent_subtraction",
            "first_layer": list(self.first_layer),
            "second_layer": list(self.second_layer),
            "evidence_constants": list(self.evidence_constants),
        }


class IndexedExecutor:
    """Execute compositions whose library calls are identified only by IDs."""

    def __init__(
        self,
        semantic_library: Mapping[str, MicroProgram],
        *,
        micro_executor: MicroProgramExecutor | None = None,
        magnitude_limit: float = 1e100,
    ) -> None:
        self.semantic_library = dict(semantic_library)
        self.micro_executor = micro_executor or MicroProgramExecutor(maximum_steps=256)
        self.magnitude_limit = magnitude_limit

    def execute(self, program: IndexedNode, index: float) -> float:
        self.validate(program)
        return self._evaluate(program, float(index))

    def validate(self, node: IndexedNode) -> None:
        if node.op not in INDEXED_OPERATIONS:
            raise InvalidIndexedProgram("indexed operation is not registered")
        if node.op == "q_index":
            if node.args or node.constant is not None or node.operation_id is not None:
                raise InvalidIndexedProgram("index node shape is invalid")
            return
        if node.op == "q_constant":
            if (
                node.args
                or node.constant is None
                or node.operation_id is not None
                or not math.isfinite(node.constant)
            ):
                raise InvalidIndexedProgram("constant node shape is invalid")
            return
        if len(node.args) != 2 or node.constant is not None:
            raise InvalidIndexedProgram("binary indexed node shape is invalid")
        if node.op == "q_semantic_call":
            if not node.operation_id or node.operation_id not in self.semantic_library:
                raise InvalidIndexedProgram("semantic operation is unavailable")
        elif node.operation_id is not None:
            raise InvalidIndexedProgram("arithmetic node cannot name a semantic operation")
        for child in node.args:
            self.validate(child)

    def _evaluate(self, node: IndexedNode, index: float) -> float:
        if node.op == "q_index":
            return self._checked(index)
        if node.op == "q_constant":
            assert node.constant is not None
            return self._checked(node.constant)
        left = self._evaluate(node.args[0], index)
        right = self._evaluate(node.args[1], index)
        if node.op == "q_add":
            return self._checked(left + right)
        if node.op == "q_subtract":
            return self._checked(left - right)
        assert node.operation_id is not None
        try:
            output = self.micro_executor.execute(
                self.semantic_library[node.operation_id], (left, right)
            ).output_value
        except InvalidMicroProgram as exc:
            raise InvalidIndexedProgram("opaque semantic call did not execute") from exc
        return self._checked(output)

    def _checked(self, value: float) -> float:
        numeric = float(value)
        if not math.isfinite(numeric) or abs(numeric) > self.magnitude_limit:
            raise InvalidIndexedProgram("indexed program produced unsafe magnitude")
        return numeric


@dataclass(frozen=True, slots=True)
class IndexedCandidate:
    candidate_id: str
    program: IndexedNode
    fit_mse: float
    maximum_absolute_error: float
    training_outputs: tuple[float, ...]
    probe_signature: tuple[float, ...]
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
            "exact": self.exact,
            "program_nodes": self.program.node_count,
            "training_outputs": list(self.training_outputs),
            "probe_signature": list(self.probe_signature),
            "logic_signature": self.logic_signature,
        }


@dataclass(frozen=True, slots=True)
class IndexedSearchReport:
    order_semantics_enabled: bool
    difference_workspace: DifferenceWorkspace
    semantic_operation_ids: tuple[str, ...]
    programs_generated: int
    programs_executed: int
    invalid_programs: int
    behavior_classes: int
    top_candidates: tuple[IndexedCandidate, ...]


class IndexedSemanticSearch:
    """Enumerate short index programs with optional anonymous library calls."""

    def __init__(
        self,
        semantic_library: Mapping[str, MicroProgram],
        *,
        maximum_nodes: int = 7,
        maximum_constants: int = 5,
        top_k: int = 20,
        probe_extension: int = 5,
    ) -> None:
        if maximum_nodes < 1 or maximum_nodes % 2 == 0:
            raise ValueError("maximum_nodes must be a positive odd number")
        if maximum_constants < 1 or top_k < 1 or probe_extension < 1:
            raise ValueError("indexed search limits must be positive")
        self.semantic_library = dict(semantic_library)
        self.maximum_nodes = maximum_nodes
        self.maximum_constants = maximum_constants
        self.top_k = top_k
        self.probe_extension = probe_extension
        self.executor = IndexedExecutor(self.semantic_library)

    def search(self, observation: NumericObservation) -> IndexedSearchReport:
        valid_rows = tuple(
            (index, value)
            for index, (value, valid) in enumerate(
                zip(observation.sequence_values, observation.validity_mask, strict=True)
            )
            if valid
        )
        if len(valid_rows) < 2:
            raise ValueError("indexed search requires at least two valid ordered values")
        workspace = build_difference_workspace(
            observation, maximum_constants=self.maximum_constants
        )
        constants = tuple(item["value"] for item in workspace.evidence_constants)
        probe_indexes = tuple(
            float(index)
            for index in range(len(observation.sequence_values) + self.probe_extension)
        )
        by_size: dict[int, dict[tuple[float, ...], IndexedNode]] = {}
        generated = 0
        executed = 0
        invalid = 0

        leaves = [IndexedNode("q_index")]
        leaves.extend(IndexedNode("q_constant", constant=value) for value in constants)
        by_size[1] = {}
        for node in leaves:
            generated += 1
            signature = self._signature(node, probe_indexes)
            if signature is None:
                invalid += 1
                continue
            executed += 1
            by_size[1].setdefault(signature, node)

        binary_operations = [("q_add", None), ("q_subtract", None)]
        binary_operations.extend(
            ("q_semantic_call", operation_id)
            for operation_id in sorted(self.semantic_library)
        )
        for size in range(3, self.maximum_nodes + 1, 2):
            current: dict[tuple[float, ...], IndexedNode] = {}
            for left_size in range(1, size - 1, 2):
                right_size = size - 1 - left_size
                for left in by_size.get(left_size, {}).values():
                    for right in by_size.get(right_size, {}).values():
                        for op, operation_id in binary_operations:
                            generated += 1
                            node = IndexedNode(
                                op, (left, right), operation_id=operation_id
                            )
                            signature = self._signature(node, probe_indexes)
                            if signature is None:
                                invalid += 1
                                continue
                            executed += 1
                            existing = current.get(signature)
                            if existing is None or indexed_node_key(node) < indexed_node_key(
                                existing
                            ):
                                current[signature] = node
            by_size[size] = current

        candidates: list[IndexedCandidate] = []
        seen_training_behavior: set[tuple[float, ...]] = set()
        expected = tuple(value for _, value in valid_rows)
        indexes = tuple(float(index) for index, _ in valid_rows)
        for size in sorted(by_size):
            for probe_signature, node in by_size[size].items():
                try:
                    outputs = tuple(self.executor.execute(node, index) for index in indexes)
                except InvalidIndexedProgram:
                    continue
                if outputs in seen_training_behavior:
                    continue
                seen_training_behavior.add(outputs)
                errors = tuple(actual - target for actual, target in zip(outputs, expected))
                mse = sum(error * error for error in errors) / len(errors)
                maximum_error = max(abs(error) for error in errors)
                key = indexed_node_key(node)
                candidates.append(
                    IndexedCandidate(
                        candidate_id="IC-"
                        + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
                        program=node,
                        fit_mse=mse,
                        maximum_absolute_error=maximum_error,
                        training_outputs=outputs,
                        probe_signature=probe_signature,
                        logic_signature=indexed_logic_signature(node),
                    )
                )
        candidates.sort(
            key=lambda item: (
                item.fit_mse,
                item.program.node_count,
                item.logic_signature,
                item.candidate_id,
            )
        )
        return IndexedSearchReport(
            order_semantics_enabled=True,
            difference_workspace=workspace,
            semantic_operation_ids=tuple(sorted(self.semantic_library)),
            programs_generated=generated,
            programs_executed=executed,
            invalid_programs=invalid,
            behavior_classes=sum(len(items) for items in by_size.values()),
            top_candidates=tuple(candidates[: self.top_k]),
        )

    def _signature(
        self, node: IndexedNode, probe_indexes: Sequence[float]
    ) -> tuple[float, ...] | None:
        try:
            return tuple(self.executor.execute(node, index) for index in probe_indexes)
        except InvalidIndexedProgram:
            return None


def build_difference_workspace(
    observation: NumericObservation, *, maximum_constants: int = 5
) -> DifferenceWorkspace:
    """Construct adjacent subtraction layers and provenance-carrying constants."""

    valid_values = tuple(
        value
        for value, valid in zip(
            observation.sequence_values, observation.validity_mask, strict=True
        )
        if valid
    )
    first = tuple(right - left for left, right in zip(valid_values, valid_values[1:]))
    second = tuple(right - left for left, right in zip(first, first[1:]))
    atoms = sorted(
        set(valid_values)
        | {float(index) for index in range(len(observation.sequence_values))}
        | set(first)
        | set(second)
    )
    derived: dict[float, dict[str, Any]] = {}
    for left in atoms:
        for right in atoms:
            value = float(left - right)
            derived.setdefault(
                value,
                {
                    "value": value,
                    "provenance": {
                        "op": "subtract_observed_or_derived_numeric_atoms",
                        "left": left,
                        "right": right,
                    },
                },
            )
    ordered = sorted(derived.values(), key=lambda item: (abs(item["value"]), item["value"]))
    return DifferenceWorkspace(first, second, tuple(ordered[:maximum_constants]))


def indexed_node_key(node: IndexedNode) -> str:
    return json.dumps(node.to_dict(), sort_keys=True, separators=(",", ":"))


def indexed_logic_signature(node: IndexedNode) -> str:
    """Hash topology and opaque operation identities, ignoring numeric constants."""

    def shape(value: IndexedNode) -> Any:
        return {
            "op": value.op,
            "operation_id": value.operation_id,
            "args": [shape(child) for child in value.args],
        }

    encoded = json.dumps(shape(node), sort_keys=True, separators=(",", ":"))
    return "LOGIC-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
