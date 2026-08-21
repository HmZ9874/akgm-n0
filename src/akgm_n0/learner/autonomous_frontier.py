"""Self-directed selection and compression of anonymous structural worlds."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .foundation_kernel import FoundationRewardPolicy


SEED_UNIT = 0
SEED_EMPTY = 1
SEED_BASE_OBJECTS = 2

UPDATE_KEEP = 0
UPDATE_EXPAND_WITH_BASE = 1
UPDATE_REPLACE_WITH_BASE = 2
UPDATE_APPEND_CONTROLLER = 3


@dataclass(frozen=True, slots=True)
class FrontierWorld:
    world_id: str
    structural_signature: str
    dependency_signatures: tuple[str, ...]
    novelty_weight: int
    compression_gain: int
    estimated_experiment_cost: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "structural_signature": self.structural_signature,
            "dependency_signatures": list(self.dependency_signatures),
            "novelty_weight": self.novelty_weight,
            "compression_gain": self.compression_gain,
            "estimated_experiment_cost": self.estimated_experiment_cost,
        }


@dataclass(frozen=True, slots=True)
class FrontierDecision:
    world: FrontierWorld
    status: str
    score: int | None
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "world": self.world.to_dict(),
            "status": self.status,
            "score": self.score,
            "reasons": list(self.reasons),
        }


class AutonomousFrontierController:
    """Choose a ready unexplained world without evaluator-side math labels."""

    def rank(
        self,
        worlds: Sequence[FrontierWorld],
        *,
        known_signatures: Sequence[str],
        failure_counts: Mapping[str, int] | None = None,
    ) -> tuple[FrontierDecision, ...]:
        known = set(known_signatures)
        failures = failure_counts or {}
        decisions = []
        for world in worlds:
            if world.structural_signature in known:
                decisions.append(FrontierDecision(world, "already_explained", None, ("signature already has a verified compressor",)))
                continue
            missing = tuple(item for item in world.dependency_signatures if item not in known)
            if missing:
                decisions.append(FrontierDecision(world, "dependency_blocked", None, tuple("missing:" + item for item in missing)))
                continue
            failure_penalty = 7 * failures.get(world.structural_signature, 0)
            score = (
                11 * world.novelty_weight
                + 5 * world.compression_gain
                - world.estimated_experiment_cost
                - failure_penalty
            )
            decisions.append(FrontierDecision(
                world,
                "ready",
                score,
                (
                    f"novelty:{world.novelty_weight}",
                    f"compression:{world.compression_gain}",
                    f"cost:{world.estimated_experiment_cost}",
                    f"failure_penalty:{failure_penalty}",
                ),
            ))
        return tuple(sorted(
            decisions,
            key=lambda item: (
                item.status != "ready",
                -(item.score if item.score is not None else -10**9),
                item.world.world_id,
            ),
        ))

    def select(self, decisions: Sequence[FrontierDecision]) -> FrontierDecision | None:
        return next((item for item in decisions if item.status == "ready"), None)


@dataclass(frozen=True, slots=True)
class RecursiveProgram:
    program_id: str
    controller_slot: int
    base_slot: int
    seed_mode: int
    update_mode: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "controller_slot": self.controller_slot,
            "base_slot": self.base_slot,
            "seed_mode": self.seed_mode,
            "update_mode": self.update_mode,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RecursiveProgram":
        return cls(
            str(value["program_id"]),
            int(value["controller_slot"]),
            int(value["base_slot"]),
            int(value["seed_mode"]),
            int(value["update_mode"]),
        )


@dataclass(frozen=True, slots=True)
class RecursiveExample:
    sources: tuple[tuple[str, ...], tuple[str, ...]]
    expected_output: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RecursiveExecution:
    halted: bool
    output: tuple[str, ...]
    primitive_execution_tokens: int


@dataclass(frozen=True, slots=True)
class RecursiveCandidate:
    program: RecursiveProgram
    exact: bool
    passed_example_count: int
    example_count: int
    execution_token_cost: int
    program_token_cost: int
    total_token_cost: int
    reward: int


@dataclass(frozen=True, slots=True)
class RecursiveSearchReport:
    task_id: str
    candidates_evaluated: int
    selected: RecursiveCandidate
    candidates: tuple[RecursiveCandidate, ...]


@dataclass(frozen=True, slots=True)
class RecursiveFoundationSemantic:
    semantic_id: str
    opcode: int
    program: RecursiveProgram
    dependency_semantic_ids: tuple[str, ...]
    source_task_ids: tuple[str, ...]
    structural_signature: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id,
            "opcode": self.opcode,
            "program": self.program.to_dict(),
            "dependency_semantic_ids": list(self.dependency_semantic_ids),
            "source_task_ids": list(self.source_task_ids),
            "structural_signature": self.structural_signature,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RecursiveFoundationSemantic":
        return cls(
            str(value["semantic_id"]),
            int(value["opcode"]),
            RecursiveProgram.from_dict(dict(value["program"])),
            tuple(str(item) for item in value["dependency_semantic_ids"]),
            tuple(str(item) for item in value["source_task_ids"]),
            str(value["structural_signature"]),
        )


class RecursiveExecutor:
    """Run an anonymous state-rewrite once for every controller object."""

    def execute(self, program: RecursiveProgram, sources: Sequence[Sequence[str]]) -> RecursiveExecution:
        if len(sources) != 2:
            raise ValueError("recursive programs require two finite collections")
        controller = tuple(sources[program.controller_slot])
        base = tuple(sources[program.base_slot])
        if program.seed_mode == SEED_UNIT:
            state: list[tuple[str, ...]] = [()]
            tokens = 1
        elif program.seed_mode == SEED_EMPTY:
            state = []
            tokens = 1
        elif program.seed_mode == SEED_BASE_OBJECTS:
            state = [(item,) for item in base]
            tokens = 1 + len(base)
        else:
            raise ValueError("unknown seed mode")
        for control_object in controller:
            tokens += 1
            if program.update_mode == UPDATE_KEEP:
                state = list(state)
                tokens += len(state)
            elif program.update_mode == UPDATE_EXPAND_WITH_BASE:
                expanded = []
                for prefix in state:
                    tokens += 1
                    for base_object in base:
                        tokens += 2
                        expanded.append(prefix + (base_object,))
                state = expanded
            elif program.update_mode == UPDATE_REPLACE_WITH_BASE:
                state = [(item,) for item in base]
                tokens += len(base)
            elif program.update_mode == UPDATE_APPEND_CONTROLLER:
                state = [prefix + (control_object,) for prefix in state]
                tokens += 2 * len(state)
            else:
                raise ValueError("unknown update mode")
        tokens += len(state) + 1
        return RecursiveExecution(True, tuple(word_token(item) for item in state), tokens)


class RecursiveExpansionSearch:
    def search(self, task_id: str, examples: Sequence[RecursiveExample]) -> RecursiveSearchReport:
        candidates = []
        for controller_slot, seed_mode, update_mode in itertools.product(
            (0, 1),
            (SEED_UNIT, SEED_EMPTY, SEED_BASE_OBJECTS),
            (UPDATE_KEEP, UPDATE_EXPAND_WITH_BASE, UPDATE_REPLACE_WITH_BASE, UPDATE_APPEND_CONTROLLER),
        ):
            program = compile_recursive_program(controller_slot, 1 - controller_slot, seed_mode, update_mode)
            passed = 0
            execution_tokens = 0
            for example in examples:
                execution = RecursiveExecutor().execute(program, example.sources)
                execution_tokens += execution.primitive_execution_tokens
                passed += execution.halted and execution.output == example.expected_output
            exact = passed == len(examples)
            program_tokens = 5
            total, reward = FoundationRewardPolicy().score(
                exact=exact,
                passed_example_count=passed,
                execution_token_cost=execution_tokens,
                program_token_cost=program_tokens,
            )
            candidates.append(RecursiveCandidate(
                program, exact, passed, len(examples), execution_tokens,
                program_tokens, total, reward,
            ))
        exact_candidates = [item for item in candidates if item.exact]
        if not exact_candidates:
            raise ValueError(f"no exact recursive compressor for {task_id}")
        exact_candidates.sort(key=lambda item: (-item.reward, item.program.program_id))
        return RecursiveSearchReport(task_id, len(candidates), exact_candidates[0], tuple(candidates))


class RecursiveSemanticInducer:
    def induce(
        self,
        report: RecursiveSearchReport,
        *,
        opcode: int,
        dependency_semantic_ids: Sequence[str],
        structural_signature: str,
    ) -> RecursiveFoundationSemantic:
        payload = {
            "opcode": opcode,
            "program_id": report.selected.program.program_id,
            "dependencies": list(dependency_semantic_ids),
            "source_tasks": [report.task_id],
            "structural_signature": structural_signature,
        }
        semantic_id = "ASEM-" + _digest(payload)
        return RecursiveFoundationSemantic(
            semantic_id, opcode, report.selected.program,
            tuple(dependency_semantic_ids), (report.task_id,), structural_signature,
        )


def compile_recursive_program(controller_slot: int, base_slot: int, seed_mode: int, update_mode: int) -> RecursiveProgram:
    payload = {
        "controller_slot": controller_slot,
        "base_slot": base_slot,
        "seed_mode": seed_mode,
        "update_mode": update_mode,
    }
    return RecursiveProgram("ARP-" + _digest(payload), controller_slot, base_slot, seed_mode, update_mode)


def word_token(items: Sequence[str]) -> str:
    return "WORD:" + json.dumps(list(items), ensure_ascii=False, separators=(",", ":"))


def recursive_word_observation(base: Sequence[str], controller: Sequence[str]) -> tuple[str, ...]:
    words: tuple[tuple[str, ...], ...] = ((),)
    for _ in controller:
        words = tuple(prefix + (item,) for prefix in words for item in base)
    return tuple(word_token(item) for item in words)


def _digest(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()[:16]
