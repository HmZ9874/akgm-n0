"""Anonymous cross-task concept mining using description-length gain."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .dsl import ProgramNode
from .search import iter_read_offsets, program_key, program_node_count


@dataclass(frozen=True, slots=True)
class ConceptCandidate:
    concept_id: str
    definition: ProgramNode
    support_task_ids: tuple[str, ...]
    occurrence_count: int
    definition_nodes: int
    description_gain: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "definition_ast": self.definition.to_dict(),
            "support_task_ids": list(self.support_task_ids),
            "support_task_count": len(self.support_task_ids),
            "occurrence_count": self.occurrence_count,
            "definition_nodes": self.definition_nodes,
            "description_gain": self.description_gain,
            "human_interpretation": None,
        }


@dataclass(frozen=True, slots=True)
class ConceptLibrary:
    entries: tuple[ConceptCandidate, ...] = ()

    def definitions(self) -> dict[str, ProgramNode]:
        return {entry.concept_id: entry.definition for entry in self.entries}

    def to_dict(self) -> dict[str, Any]:
        return {
            "library_version": "concept-library-v0.1",
            "entry_count": len(self.entries),
            "entries": [entry.to_dict() for entry in self.entries],
        }


class CrossTaskConceptMiner:
    """Find reusable parameter-free subtrees without semantic target labels."""

    def __init__(
        self,
        *,
        minimum_support_tasks: int = 3,
        minimum_definition_nodes: int = 3,
        maximum_definition_nodes: int = 7,
        registration_cost: int = 1,
    ) -> None:
        if minimum_support_tasks < 2:
            raise ValueError("minimum_support_tasks must be at least two")
        if minimum_definition_nodes < 2:
            raise ValueError("minimum_definition_nodes must be at least two")
        if maximum_definition_nodes < minimum_definition_nodes:
            raise ValueError("maximum_definition_nodes is below the minimum")
        if registration_cost < 0:
            raise ValueError("registration_cost must be non-negative")
        self.minimum_support_tasks = minimum_support_tasks
        self.minimum_definition_nodes = minimum_definition_nodes
        self.maximum_definition_nodes = maximum_definition_nodes
        self.registration_cost = registration_cost

    def mine(
        self, task_programs: Mapping[str, ProgramNode]
    ) -> tuple[ConceptCandidate, ...]:
        occurrences: dict[str, list[tuple[str, ProgramNode]]] = {}
        for task_id, program in sorted(task_programs.items()):
            for subtree in _walk_subtrees(program):
                if not self._eligible(subtree):
                    continue
                occurrences.setdefault(program_key(subtree), []).append((task_id, subtree))

        candidates: list[ConceptCandidate] = []
        for key, matches in occurrences.items():
            support_task_ids = tuple(sorted({task_id for task_id, _ in matches}))
            if len(support_task_ids) < self.minimum_support_tasks:
                continue
            definition = matches[0][1]
            nodes = program_node_count(definition)
            occurrence_count = len(matches)
            raw_cost = occurrence_count * nodes
            library_cost = nodes + self.registration_cost + occurrence_count
            gain = raw_cost - library_cost
            if gain <= 0:
                continue
            concept_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
            candidates.append(
                ConceptCandidate(
                    concept_id=f"C-{concept_hash}",
                    definition=definition,
                    support_task_ids=support_task_ids,
                    occurrence_count=occurrence_count,
                    definition_nodes=nodes,
                    description_gain=gain,
                )
            )

        candidates.sort(
            key=lambda item: (
                -item.description_gain,
                -len(item.support_task_ids),
                item.definition_nodes,
                item.concept_id,
            )
        )
        return tuple(candidates)

    def promote(
        self, candidates: Sequence[ConceptCandidate], *, maximum_entries: int = 1
    ) -> ConceptLibrary:
        if maximum_entries < 1:
            raise ValueError("maximum_entries must be positive")
        return ConceptLibrary(entries=tuple(candidates[:maximum_entries]))

    def _eligible(self, program: ProgramNode) -> bool:
        nodes = program_node_count(program)
        if not self.minimum_definition_nodes <= nodes <= self.maximum_definition_nodes:
            return False
        if _contains_parameter(program):
            return False
        offsets = set(iter_read_offsets(program))
        return len(offsets) >= 2


def _walk_subtrees(program: ProgramNode):
    yield program
    for child in program.args:
        yield from _walk_subtrees(child)


def _contains_parameter(program: ProgramNode) -> bool:
    stack = [program]
    while stack:
        node = stack.pop()
        if node.op == "p_scalar_parameter":
            return True
        stack.extend(node.args)
    return False

