"""Order-free numeric relation discovery through executable program compression."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Callable

from .observation import NumericCollectionObservation


class InvalidRelationProgram(ValueError):
    """Raised when a relation program is malformed or numerically unsafe."""


@dataclass(frozen=True, slots=True)
class RelationNode:
    op: str
    args: tuple["RelationNode", ...] = ()
    constant: float | None = None

    @property
    def node_count(self) -> int:
        return 1 + sum(child.node_count for child in self.args)

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"op": self.op}
        if self.args:
            value["args"] = [child.to_dict() for child in self.args]
        if self.constant is not None:
            value["constant"] = self.constant
        return value


def relation_value() -> RelationNode:
    return RelationNode("r_value")


def relation_constant(value: float) -> RelationNode:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError("relation constant must be finite")
    return RelationNode("r_constant", constant=numeric)


def relation_add(left: RelationNode, right: RelationNode) -> RelationNode:
    return RelationNode("r_add", (left, right))


def relation_subtract(left: RelationNode, right: RelationNode) -> RelationNode:
    return RelationNode("r_subtract", (left, right))


def relation_key(program: RelationNode) -> str:
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))


class RelationExecutor:
    def __init__(self, *, magnitude_limit: float = 1e100) -> None:
        if not math.isfinite(magnitude_limit) or magnitude_limit <= 0:
            raise ValueError("magnitude_limit must be finite and positive")
        self.magnitude_limit = magnitude_limit

    def evaluate(self, program: RelationNode, value: float) -> float:
        if program.op == "r_value":
            if program.args or program.constant is not None:
                raise InvalidRelationProgram("r_value cannot have arguments")
            return self._checked(value)
        if program.op == "r_constant":
            if program.args or program.constant is None:
                raise InvalidRelationProgram("r_constant requires one stored value")
            return self._checked(program.constant)
        if program.op not in {"r_add", "r_subtract"} or len(program.args) != 2:
            raise InvalidRelationProgram(f"unsupported relation operation: {program.op}")
        if program.constant is not None:
            raise InvalidRelationProgram("binary relation operations cannot store constants")
        left = self.evaluate(program.args[0], value)
        right = self.evaluate(program.args[1], value)
        result = left + right if program.op == "r_add" else left - right
        return self._checked(result)

    def _checked(self, value: float) -> float:
        numeric = float(value)
        if not math.isfinite(numeric) or abs(numeric) > self.magnitude_limit:
            raise InvalidRelationProgram("relation program produced an unsafe value")
        return numeric


@dataclass(frozen=True, slots=True)
class RelationEdge:
    source: float
    target: float

    def to_dict(self) -> dict[str, float]:
        return {"source": self.source, "target": self.target}


@dataclass(frozen=True, slots=True)
class RelationBridge:
    source: float
    target: float
    steps: int
    generated_intermediates: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "steps": self.steps,
            "generated_intermediates": list(self.generated_intermediates),
        }


@dataclass(frozen=True, slots=True)
class RelationCandidate:
    candidate_id: str
    program: RelationNode
    direct_edges: tuple[RelationEdge, ...]
    best_chain: tuple[float, ...]
    bridges: tuple[RelationBridge, ...]
    generated_nodes: tuple[float, ...]

    @property
    def observed_chain_count(self) -> int:
        return len(self.best_chain)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "program": self.program.to_dict(),
            "program_nodes": self.program.node_count,
            "direct_edges": [edge.to_dict() for edge in self.direct_edges],
            "best_observed_chain": list(self.best_chain),
            "observed_chain_count": self.observed_chain_count,
            "bridges": [bridge.to_dict() for bridge in self.bridges],
            "generated_nodes": list(self.generated_nodes),
        }


@dataclass(frozen=True, slots=True)
class RelationSearchReport:
    programs_generated: int
    valid_member_count: int
    top_candidates: tuple[RelationCandidate, ...]
    evidence_constants: tuple[dict[str, Any], ...] = ()
    programs_filtered: int = 0


class RelationProgramSearch:
    """Find a short unary program that organizes an unordered collection."""

    def __init__(
        self,
        *,
        maximum_nodes: int = 7,
        maximum_composition_steps: int = 6,
        top_k: int = 20,
        maximum_evidence_constants: int = 24,
        evidence_derivation_depth: int = 2,
        maximum_semantic_states_per_size: int = 10000,
        candidate_gate: Callable[[RelationNode], bool] | None = None,
        executor: RelationExecutor | None = None,
    ) -> None:
        if maximum_nodes < 1 or maximum_nodes % 2 == 0:
            raise ValueError("maximum_nodes must be a positive odd integer")
        if maximum_composition_steps < 1 or top_k < 1:
            raise ValueError("search limits must be positive")
        if maximum_evidence_constants < 0 or evidence_derivation_depth < 0:
            raise ValueError("evidence-memory limits cannot be negative")
        if maximum_semantic_states_per_size < 1:
            raise ValueError("semantic-state limit must be positive")
        self.maximum_nodes = maximum_nodes
        self.maximum_composition_steps = maximum_composition_steps
        self.top_k = top_k
        self.maximum_evidence_constants = maximum_evidence_constants
        self.evidence_derivation_depth = evidence_derivation_depth
        self.maximum_semantic_states_per_size = maximum_semantic_states_per_size
        self.candidate_gate = candidate_gate or (lambda _program: True)
        self.executor = executor or RelationExecutor()

    def search(self, observation: NumericCollectionObservation) -> RelationSearchReport:
        values = tuple(
            value
            for value, include in zip(
                observation.numeric_values, observation.validity_mask, strict=True
            )
            if include
        )
        if len(values) < 2:
            raise ValueError("relation search requires at least two valid members")
        evidence_constants = self._derive_evidence_constants(values)
        programs = self._enumerate_programs(
            tuple(item["value"] for item in evidence_constants)
        )
        accepted_programs = [program for program in programs if self.candidate_gate(program)]
        candidates = [self._analyze(program, values) for program in accepted_programs]
        candidates = [
            candidate
            for candidate in candidates
            if candidate.program.to_dict() != relation_value().to_dict()
            and self._affine_signature(candidate.program)[0] != 0.0
        ]
        candidates.sort(
            key=lambda item: (
                -len(item.best_chain),
                -len(item.direct_edges),
                item.program.node_count,
                -len(
                    {
                        value
                        for edge in item.direct_edges
                        for value in (edge.source, edge.target)
                    }
                ),
                item.candidate_id,
            )
        )
        return RelationSearchReport(
            programs_generated=len(programs),
            valid_member_count=len(values),
            top_candidates=tuple(candidates[: self.top_k]),
            evidence_constants=evidence_constants,
            programs_filtered=len(programs) - len(accepted_programs),
        )

    def _derive_evidence_constants(
        self, values: tuple[float, ...]
    ) -> tuple[dict[str, Any], ...]:
        """Create working-memory atoms only through supplied-number subtraction."""

        known: dict[float, dict[str, Any]] = {
            float(value): {
                "value": float(value),
                "derivation_depth": 0,
                "provenance": {"op": "observed_member", "value": float(value)},
            }
            for value in sorted(set(values))
        }
        for depth in range(1, self.evidence_derivation_depth + 1):
            available = tuple(sorted(known))
            created: dict[float, dict[str, Any]] = {}
            for left in available:
                for right in available:
                    result = float(left - right)
                    if not math.isfinite(result) or result in known or result in created:
                        continue
                    created[result] = {
                        "value": result,
                        "derivation_depth": depth,
                        "provenance": {
                            "op": "subtract_workspace_atoms",
                            "left": left,
                            "right": right,
                        },
                    }
            if not created:
                break
            known.update(created)
        derived = [item for item in known.values() if item["derivation_depth"] > 0]
        derived.sort(
            key=lambda item: (
                abs(item["value"]),
                item["derivation_depth"],
                item["value"],
            )
        )
        return tuple(derived[: self.maximum_evidence_constants])

    @staticmethod
    def _affine_signature(program: RelationNode) -> tuple[float, float]:
        if program.op == "r_value":
            return (1.0, 0.0)
        if program.op == "r_constant" and program.constant is not None:
            return (0.0, float(program.constant))
        left = RelationProgramSearch._affine_signature(program.args[0])
        right = RelationProgramSearch._affine_signature(program.args[1])
        direction = 1.0 if program.op == "r_add" else -1.0
        return (left[0] + direction * right[0], left[1] + direction * right[1])

    def _trim_semantic_states(
        self, programs: dict[tuple[float, float], RelationNode]
    ) -> dict[tuple[float, float], RelationNode]:
        ordered = sorted(
            programs.items(),
            key=lambda item: (
                abs(item[0][0]) + abs(item[0][1]),
                abs(item[0][1]),
                relation_key(item[1]),
            ),
        )
        return dict(ordered[: self.maximum_semantic_states_per_size])

    def _enumerate_programs(
        self, constants: tuple[float, ...] = ()
    ) -> tuple[RelationNode, ...]:
        leaves = (relation_value(),) + tuple(
            relation_constant(value) for value in constants
        )
        by_size: dict[int, dict[tuple[float, float], RelationNode]] = {1: {}}
        for leaf in leaves:
            by_size[1].setdefault(self._affine_signature(leaf), leaf)
        for size in range(3, self.maximum_nodes + 1, 2):
            programs: dict[tuple[float, float], RelationNode] = {}
            for left_size in range(1, size - 1, 2):
                right_size = size - 1 - left_size
                for left in by_size[left_size].values():
                    for right in by_size[right_size].values():
                        ordered = sorted((left, right), key=relation_key)
                        add_program = relation_add(ordered[0], ordered[1])
                        programs.setdefault(
                            self._affine_signature(add_program), add_program
                        )
                        subtract_program = relation_subtract(left, right)
                        programs.setdefault(
                            self._affine_signature(subtract_program), subtract_program
                        )
            by_size[size] = self._trim_semantic_states(programs)
        result: list[RelationNode] = []
        for size in sorted(by_size):
            result.extend(
                sorted(by_size[size].values(), key=relation_key)
            )
        return tuple(result)

    def _analyze(
        self, program: RelationNode, values: tuple[float, ...]
    ) -> RelationCandidate:
        observed = set(values)
        direct_edges = tuple(
            RelationEdge(source, target)
            for source in sorted(observed)
            for target in (self.executor.evaluate(program, source),)
            if target in observed and target != source
        )
        best_chain: tuple[float, ...] = ()
        bridges: list[RelationBridge] = []
        generated_nodes: set[float] = set()
        for start in sorted(observed):
            current = start
            observed_chain = [start]
            pending_generated: list[float] = []
            seen = {start}
            for step in range(1, self.maximum_composition_steps + 1):
                current = self.executor.evaluate(program, current)
                if current in seen:
                    break
                seen.add(current)
                if current in observed:
                    if current not in observed_chain:
                        observed_chain.append(current)
                    if pending_generated:
                        bridges.append(
                            RelationBridge(
                                source=observed_chain[-2],
                                target=current,
                                steps=len(pending_generated) + 1,
                                generated_intermediates=tuple(pending_generated),
                            )
                        )
                        generated_nodes.update(pending_generated)
                    pending_generated = []
                else:
                    pending_generated.append(current)
            chain_tuple = tuple(observed_chain)
            if (len(chain_tuple), chain_tuple) > (len(best_chain), best_chain):
                best_chain = chain_tuple
        unique_bridges: dict[str, RelationBridge] = {}
        for bridge in bridges:
            key = json.dumps(bridge.to_dict(), sort_keys=True, separators=(",", ":"))
            unique_bridges[key] = bridge
        key = relation_key(program)
        return RelationCandidate(
            candidate_id="REL-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
            program=program,
            direct_edges=direct_edges,
            best_chain=best_chain,
            bridges=tuple(unique_bridges[key] for key in sorted(unique_bridges)),
            generated_nodes=tuple(sorted(generated_nodes)),
        )


def compose_relation(outer: RelationNode, inner: RelationNode) -> RelationNode:
    """Compile one discovered relation program around another."""

    if outer.op == "r_value":
        return inner
    if outer.op == "r_constant":
        return outer
    return RelationNode(
        outer.op,
        tuple(compose_relation(child, inner) for child in outer.args),
        constant=outer.constant,
    )


@dataclass(frozen=True, slots=True)
class PromotedRelationOperation:
    operation_id: str
    definition: RelationNode

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "definition": self.definition.to_dict(),
            "human_interpretation": None,
        }


class RelationOperationLibrary:
    def __init__(self, executor: RelationExecutor | None = None) -> None:
        self.executor = executor or RelationExecutor()
        self._entries: dict[str, PromotedRelationOperation] = {}

    def promote(self, program: RelationNode) -> PromotedRelationOperation:
        key = relation_key(program)
        operation_id = "ROP-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        entry = PromotedRelationOperation(operation_id, program)
        self._entries.setdefault(operation_id, entry)
        return self._entries[operation_id]

    def execute(self, operation_id: str, value: float) -> float:
        try:
            entry = self._entries[operation_id]
        except KeyError as exc:
            raise InvalidRelationProgram(f"unknown relation operation: {operation_id}") from exc
        return self.executor.evaluate(entry.definition, value)

    def compose(
        self, outer_operation_id: str, inner_operation_id: str
    ) -> PromotedRelationOperation:
        try:
            outer = self._entries[outer_operation_id]
            inner = self._entries[inner_operation_id]
        except KeyError as exc:
            raise InvalidRelationProgram(
                f"unknown parent operation: {exc.args[0]}"
            ) from exc
        return self.promote(compose_relation(outer.definition, inner.definition))
