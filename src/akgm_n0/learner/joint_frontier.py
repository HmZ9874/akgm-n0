"""Anonymous set-relation search for a blocked conditioned-mass frontier."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .foundation_kernel import FoundationRewardPolicy

REL_LEFT = 0
REL_RIGHT = 1
REL_COMMON = 2
REL_MERGED = 3
REL_LEFT_ONLY = 4
REL_RIGHT_ONLY = 5
REL_EXCLUSIVE = 6


@dataclass(frozen=True, slots=True)
class JointProgram:
    program_id: str
    left_slot: int
    right_slot: int
    relation_mode: int
    def to_dict(self) -> dict[str, Any]:
        return {"program_id": self.program_id, "left_slot": self.left_slot,
                "right_slot": self.right_slot, "relation_mode": self.relation_mode}
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "JointProgram":
        return cls(str(value["program_id"]), int(value["left_slot"]),
                   int(value["right_slot"]), int(value["relation_mode"]))


@dataclass(frozen=True, slots=True)
class JointExample:
    universe: tuple[str, ...]
    sources: tuple[tuple[str, ...], tuple[str, ...]]
    expected_output: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class JointExecution:
    halted: bool
    output: tuple[str, ...]
    primitive_execution_tokens: int
    equality_comparison_tokens: int


@dataclass(frozen=True, slots=True)
class JointCandidate:
    program: JointProgram
    exact: bool
    passed_example_count: int
    example_count: int
    execution_token_cost: int
    program_token_cost: int
    total_token_cost: int
    reward: int


@dataclass(frozen=True, slots=True)
class JointSearchReport:
    task_id: str
    candidates_evaluated: int
    selected: JointCandidate
    candidates: tuple[JointCandidate, ...]


@dataclass(frozen=True, slots=True)
class JointFoundationSemantic:
    semantic_id: str
    opcode: int
    program: JointProgram
    dependency_semantic_ids: tuple[str, ...]
    source_task_ids: tuple[str, ...]
    invented_dependency_signature: str
    def to_dict(self) -> dict[str, Any]:
        return {"semantic_id": self.semantic_id, "opcode": self.opcode,
                "program": self.program.to_dict(), "dependency_semantic_ids": list(self.dependency_semantic_ids),
                "source_task_ids": list(self.source_task_ids),
                "invented_dependency_signature": self.invented_dependency_signature}
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "JointFoundationSemantic":
        return cls(str(value["semantic_id"]), int(value["opcode"]), JointProgram.from_dict(value["program"]),
                   tuple(str(x) for x in value["dependency_semantic_ids"]),
                   tuple(str(x) for x in value["source_task_ids"]), str(value["invented_dependency_signature"]))


class JointExecutor:
    def execute(self, program: JointProgram, universe: Sequence[str], sources: Sequence[Sequence[str]]) -> JointExecution:
        left = tuple(sources[program.left_slot]); right = tuple(sources[program.right_slot])
        left_set, right_set = set(left), set(right)
        if not left_set <= set(universe) or not right_set <= set(universe):
            return JointExecution(False, (), 1, 0)
        relation = {
            REL_LEFT: left_set, REL_RIGHT: right_set,
            REL_COMMON: left_set & right_set, REL_MERGED: left_set | right_set,
            REL_LEFT_ONLY: left_set - right_set, REL_RIGHT_ONLY: right_set - left_set,
            REL_EXCLUSIVE: left_set ^ right_set,
        }[program.relation_mode]
        output = tuple(item for item in universe if item in relation)
        comparisons = len(universe) * (len(left) + len(right))
        return JointExecution(True, output, 2 + comparisons + len(output), comparisons)


class JointRelationSearch:
    def search(self, task_id: str, examples: Sequence[JointExample]) -> JointSearchReport:
        candidates = []
        for left_slot, mode in itertools.product((0, 1), range(7)):
            program = compile_joint_program(left_slot, 1-left_slot, mode)
            passed = 0; tokens = 0
            for example in examples:
                result = JointExecutor().execute(program, example.universe, example.sources)
                tokens += result.primitive_execution_tokens
                passed += result.halted and result.output == example.expected_output
            exact = passed == len(examples)
            total, reward = FoundationRewardPolicy().score(exact=exact, passed_example_count=passed,
                                                            execution_token_cost=tokens, program_token_cost=4)
            candidates.append(JointCandidate(program, exact, passed, len(examples), tokens, 4, total, reward))
        exact = [x for x in candidates if x.exact]
        if not exact: raise ValueError(f"no exact joint relation program for {task_id}")
        exact.sort(key=lambda x: (-x.reward, x.program.program_id))
        return JointSearchReport(task_id, len(candidates), exact[0], tuple(candidates))


class JointSemanticInducer:
    def induce(self, report: JointSearchReport, *, opcode: int,
               dependency_semantic_ids: Sequence[str], invented_dependency_signature: str) -> JointFoundationSemantic:
        payload = {"opcode": opcode, "program_id": report.selected.program.program_id,
                   "dependencies": list(dependency_semantic_ids), "source_tasks": [report.task_id],
                   "invented_dependency_signature": invented_dependency_signature}
        return JointFoundationSemantic("JSEM-" + _digest(payload), opcode, report.selected.program,
                                       tuple(dependency_semantic_ids), (report.task_id,), invented_dependency_signature)


def compile_joint_program(left_slot: int, right_slot: int, relation_mode: int) -> JointProgram:
    payload = {"left_slot": left_slot, "right_slot": right_slot, "relation_mode": relation_mode}
    return JointProgram("JRP-" + _digest(payload), left_slot, right_slot, relation_mode)


def common_observation(universe: Sequence[str], left: Sequence[str], right: Sequence[str]) -> tuple[str, ...]:
    common = set(left) & set(right)
    return tuple(item for item in universe if item in common)


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
