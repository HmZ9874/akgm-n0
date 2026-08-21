"""Autonomous gap -> world -> experiment -> learn -> saturation loop."""

from __future__ import annotations

import hashlib
import itertools
import json
import random
from collections import Counter
from dataclasses import dataclass
from typing import Any, Sequence

from .cold_start_semantics_v16 import (
    DATA_OPS,
    ColdStartSemanticResearcherV16,
    OperatorDefinitionV16,
    PrimitiveWorkload,
    RuntimeInstruction,
)


@dataclass(frozen=True, slots=True)
class KnowledgeGapV17:
    gap_id: str
    focus_transition: tuple[str, str]
    target_arity: int
    current_operator_count: int
    current_generation_depth: int
    transition_evidence: int
    arity_evidence: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "focus_transition": list(self.focus_transition),
            "target_arity": self.target_arity,
            "current_operator_count": self.current_operator_count,
            "current_generation_depth": self.current_generation_depth,
            "transition_evidence": self.transition_evidence,
            "arity_evidence": self.arity_evidence,
        }


@dataclass(frozen=True, slots=True)
class ExperimentPlanV17:
    experiment_id: str
    round_index: int
    gap_id: str
    focus_transition: tuple[str, str]
    target_arity: int
    family_count: int
    workloads_per_family: int
    instruction_count: int
    recurrence_probability: float
    seed_commitment: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "round_index": self.round_index,
            "gap_id": self.gap_id,
            "focus_transition": list(self.focus_transition),
            "target_arity": self.target_arity,
            "family_count": self.family_count,
            "workloads_per_family": self.workloads_per_family,
            "instruction_count": self.instruction_count,
            "recurrence_probability": self.recurrence_probability,
            "seed_commitment": self.seed_commitment,
        }


@dataclass(frozen=True, slots=True)
class ResearchRoundV17:
    round_index: int
    gap: KnowledgeGapV17
    experiment: ExperimentPlanV17
    world_digest: str
    operator_count_before: int
    discovered_operators: tuple[OperatorDefinitionV16, ...]
    rejected_candidate_count: int
    training_token_reduction: float
    consecutive_sterile_rounds: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_index": self.round_index,
            "gap": self.gap.to_dict(),
            "experiment": self.experiment.to_dict(),
            "world_digest": self.world_digest,
            "operator_count_before": self.operator_count_before,
            "new_operator_count": len(self.discovered_operators),
            "new_operator_ids": [item.operator_id for item in self.discovered_operators],
            "rejected_candidate_count": self.rejected_candidate_count,
            "training_token_reduction": self.training_token_reduction,
            "consecutive_sterile_rounds": self.consecutive_sterile_rounds,
        }


@dataclass(frozen=True, slots=True)
class AutonomousResearchResultV17:
    seed_commitment: str
    initial_dynamic_operator_count: int
    operators: tuple[OperatorDefinitionV16, ...]
    rounds: tuple[ResearchRoundV17, ...]
    stop_reason: str
    patience: int
    maximum_rounds: int
    self_generated_world_count: int

    @property
    def generation_depth(self) -> int:
        return max((item.generation for item in self.operators), default=0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed_commitment": self.seed_commitment,
            "initial_dynamic_operator_count": self.initial_dynamic_operator_count,
            "operator_count": len(self.operators),
            "generation_depth": self.generation_depth,
            "round_count": len(self.rounds),
            "stop_reason": self.stop_reason,
            "patience": self.patience,
            "maximum_rounds": self.maximum_rounds,
            "self_generated_world_count": self.self_generated_world_count,
            "operators": [item.to_dict() for item in self.operators],
            "rounds": [item.to_dict() for item in self.rounds],
        }


class KnowledgeGapAnalyzerV17:
    """Select the least evidenced primitive transition and operand arity."""

    def inspect(self, definitions: Sequence[OperatorDefinitionV16]) -> KnowledgeGapV17:
        transitions: Counter[tuple[str, str]] = Counter()
        arities: Counter[int] = Counter()
        for definition in definitions:
            arities[definition.arity] += 1
            ops = tuple(item.op for item in definition.primitive_body)
            transitions.update(zip(ops, ops[1:], strict=False))
        transition_space = tuple(itertools.product(sorted(DATA_OPS), repeat=2))
        focus = min(transition_space, key=lambda pair: (transitions[pair], pair))
        target_arity = min((1, 2), key=lambda arity: (arities[arity], arity))
        depth = max((item.generation for item in definitions), default=0)
        payload = {
            "focus": focus,
            "arity": target_arity,
            "count": len(definitions),
            "depth": depth,
            "transition_evidence": transitions[focus],
            "arity_evidence": arities[target_arity],
        }
        gap_id = "GAP-" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16]
        return KnowledgeGapV17(
            gap_id, focus, target_arity, len(definitions), depth,
            transitions[focus], arities[target_arity],
        )


class AutonomousWorldFactoryV17:
    """Generate anonymous primitive experiments from the selected gap only."""

    def plan(self, gap: KnowledgeGapV17, *, round_index: int, seed: int) -> ExperimentPlanV17:
        experiment_seed = int(hashlib.sha256(f"{seed}:{round_index}:{gap.gap_id}".encode()).hexdigest()[:16], 16)
        payload = {
            "round": round_index,
            "gap": gap.gap_id,
            "focus": gap.focus_transition,
            "arity": gap.target_arity,
            "seed": experiment_seed,
        }
        experiment_id = "EXP-" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16]
        return ExperimentPlanV17(
            experiment_id=experiment_id,
            round_index=round_index,
            gap_id=gap.gap_id,
            focus_transition=gap.focus_transition,
            target_arity=gap.target_arity,
            family_count=4,
            workloads_per_family=48,
            instruction_count=36,
            recurrence_probability=min(0.72, 0.46 + 0.03 * (round_index % 7)),
            seed_commitment=hashlib.sha256(str(experiment_seed).encode()).hexdigest(),
        )

    def generate(self, plan: ExperimentPlanV17, *, seed: int) -> tuple[PrimitiveWorkload, ...]:
        mixed = int(hashlib.sha256(f"{seed}:{plan.experiment_id}:world".encode()).hexdigest()[:16], 16)
        rng = random.Random(mixed)
        workloads = []
        base_choices = tuple(sorted(DATA_OPS))
        for family_index in range(plan.family_count):
            family_id = f"R{plan.round_index:02d}-F{family_index:02d}"
            register_count = max(3, plan.target_arity + family_index % 2)
            for workload_index in range(plan.workloads_per_family):
                initial = [rng.randrange(0, 6) for _ in range(register_count)]
                state = list(initial)
                stream: list[RuntimeInstruction] = []
                previous_op: str | None = None
                previous_register: int | None = None
                for _ in range(plan.instruction_count):
                    draw = rng.random()
                    if previous_op == plan.focus_transition[0] and draw < plan.recurrence_probability:
                        op = plan.focus_transition[1]
                    elif draw < 0.34:
                        op = plan.focus_transition[rng.randrange(2)]
                    else:
                        op = rng.choice(base_choices)
                    if previous_register is not None and rng.random() < (0.68 if plan.target_arity == 1 else 0.38):
                        register = previous_register
                    else:
                        register = rng.randrange(register_count)
                    if op == "u_dec" and state[register] == 0:
                        op = "u_inc"
                    if op == "u_zero":
                        state[register] = 0
                    elif op == "u_unit":
                        state[register] = 1
                    elif op == "u_inc":
                        state[register] += 1
                    elif op == "u_dec":
                        state[register] -= 1
                    stream.append(RuntimeInstruction(op, (register,)))
                    previous_op = op
                    previous_register = register
                payload = {
                    "experiment": plan.experiment_id,
                    "family": family_id,
                    "index": workload_index,
                    "stream": [item.to_dict() for item in stream],
                }
                workload_id = "RW-" + hashlib.sha256(
                    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()[:16]
                workloads.append(PrimitiveWorkload(
                    family_id, workload_id, register_count, tuple(initial), tuple(stream),
                ))
        return tuple(workloads)


class AutonomousResearchLoopV17:
    def __init__(
        self,
        *,
        seed: int,
        patience: int = 4,
        maximum_rounds: int = 32,
        maximum_new_operators_per_round: int = 8,
    ) -> None:
        if patience < 2:
            raise ValueError("saturation patience must be at least two rounds")
        self.seed = seed
        self.patience = patience
        self.maximum_rounds = maximum_rounds
        self.maximum_new_operators_per_round = maximum_new_operators_per_round
        self.researcher = ColdStartSemanticResearcherV16()
        self.gaps = KnowledgeGapAnalyzerV17()
        self.worlds = AutonomousWorldFactoryV17()

    def run(self) -> AutonomousResearchResultV17:
        rounds = []
        sterile = 0
        world_count = 0
        stop_reason = "maximum_round_boundary"
        for round_index in range(self.maximum_rounds):
            before_definitions = self.researcher.vm.operators
            gap = self.gaps.inspect(before_definitions)
            experiment = self.worlds.plan(gap, round_index=round_index, seed=self.seed)
            workloads = self.worlds.generate(experiment, seed=self.seed)
            world_count += len(workloads)
            discovery = self.researcher.extend(
                workloads,
                maximum_new_operators=self.maximum_new_operators_per_round,
                maximum_primitive_span=3,
                maximum_arity=2,
                maximum_generation=3,
            )
            if discovery.operators:
                sterile = 0
            else:
                sterile += 1
            rounds.append(ResearchRoundV17(
                round_index,
                gap,
                experiment,
                discovery.manifest["workload_digest"],
                len(before_definitions),
                discovery.operators,
                len(discovery.rejected),
                discovery.training_reduction,
                sterile,
            ))
            if sterile >= self.patience:
                stop_reason = "semantic_saturation"
                break
        return AutonomousResearchResultV17(
            seed_commitment=hashlib.sha256(str(self.seed).encode()).hexdigest(),
            initial_dynamic_operator_count=0,
            operators=self.researcher.vm.operators,
            rounds=tuple(rounds),
            stop_reason=stop_reason,
            patience=self.patience,
            maximum_rounds=self.maximum_rounds,
            self_generated_world_count=world_count,
        )

