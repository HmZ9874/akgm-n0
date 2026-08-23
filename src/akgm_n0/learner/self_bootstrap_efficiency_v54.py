"""Yield-aware autonomous curriculum over an exact memoized semantic miner."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .autonomous_research_loop_v17 import (
    AutonomousWorldFactoryV17,
    ExperimentPlanV17,
    KnowledgeGapAnalyzerV17,
    KnowledgeGapV17,
)
from .cold_start_semantics_v16 import (
    ColdStartSemanticResearcherV16,
    OperatorDefinitionV16,
)


@dataclass(frozen=True, slots=True)
class EfficiencyPolicyV54:
    initial_workloads_per_family: int = 48
    productive_workloads_per_family: int = 36
    instructions_per_workload: int = 36
    maximum_new_operators_per_round: int = 8
    maximum_primitive_span: int = 3
    maximum_arity: int = 2
    maximum_generation: int = 3

    def workload_budget(self, previous_yield: int | None) -> tuple[int, str]:
        if previous_yield == self.maximum_new_operators_per_round:
            return self.productive_workloads_per_family, "full_promotion_budget_previous_round"
        return self.initial_workloads_per_family, "full_evidence_default"


@dataclass(frozen=True, slots=True)
class EfficiencyRoundV54:
    round_index: int
    gap: KnowledgeGapV17
    experiment: ExperimentPlanV17
    budget_reason: str
    operator_count_before: int
    discovered_operators: tuple[OperatorDefinitionV16, ...]
    rejected_candidate_count: int
    training_token_reduction: float
    cache_delta: dict[str, int]
    consecutive_sterile_rounds: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_index": self.round_index,
            "gap": self.gap.to_dict(),
            "experiment": self.experiment.to_dict(),
            "budget_reason": self.budget_reason,
            "operator_count_before": self.operator_count_before,
            "new_operator_count": len(self.discovered_operators),
            "new_operator_ids": [item.operator_id for item in self.discovered_operators],
            "rejected_candidate_count": self.rejected_candidate_count,
            "training_token_reduction": self.training_token_reduction,
            "cache_delta": self.cache_delta,
            "consecutive_sterile_rounds": self.consecutive_sterile_rounds,
        }


@dataclass(frozen=True, slots=True)
class EfficientResearchResultV54:
    seed: int
    policy: EfficiencyPolicyV54
    operators: tuple[OperatorDefinitionV16, ...]
    rounds: tuple[EfficiencyRoundV54, ...]
    self_generated_world_count: int
    stop_reason: str
    patience: int
    maximum_rounds: int
    cache_stats: dict[str, int]

    @property
    def generation_depth(self) -> int:
        return max((item.generation for item in self.operators), default=0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "operator_count": len(self.operators),
            "generation_depth": self.generation_depth,
            "round_count": len(self.rounds),
            "self_generated_world_count": self.self_generated_world_count,
            "stop_reason": self.stop_reason,
            "patience": self.patience,
            "maximum_rounds": self.maximum_rounds,
            "cache_stats": self.cache_stats,
            "policy": {
                "initial_workloads_per_family": self.policy.initial_workloads_per_family,
                "productive_workloads_per_family": self.policy.productive_workloads_per_family,
                "instructions_per_workload": self.policy.instructions_per_workload,
                "maximum_new_operators_per_round": self.policy.maximum_new_operators_per_round,
                "named_target_count": 0,
            },
            "operators": [item.to_dict() for item in self.operators],
            "rounds": [item.to_dict() for item in self.rounds],
        }


class EfficientAutonomousResearchLoopV54:
    def __init__(
        self,
        *,
        seed: int,
        policy: EfficiencyPolicyV54 | None = None,
        patience: int = 4,
        maximum_rounds: int = 20,
    ) -> None:
        if patience < 2:
            raise ValueError("saturation patience must be at least two rounds")
        if maximum_rounds < 1:
            raise ValueError("research round budget is empty")
        self.seed = seed
        self.policy = policy or EfficiencyPolicyV54()
        self.patience = patience
        self.maximum_rounds = maximum_rounds
        self.researcher = ColdStartSemanticResearcherV16(enable_semantic_cache=True)
        self.gaps = KnowledgeGapAnalyzerV17()
        self.worlds = AutonomousWorldFactoryV17()

    def run(self) -> EfficientResearchResultV54:
        rounds: list[EfficiencyRoundV54] = []
        sterile = 0
        world_count = 0
        previous_yield: int | None = None
        stop_reason = "maximum_round_boundary"
        for round_index in range(self.maximum_rounds):
            definitions_before = self.researcher.vm.operators
            gap = self.gaps.inspect(definitions_before)
            plan = self.worlds.plan(gap, round_index=round_index, seed=self.seed)
            workload_budget, budget_reason = self.policy.workload_budget(previous_yield)
            plan = replace(
                plan,
                workloads_per_family=workload_budget,
                instruction_count=self.policy.instructions_per_workload,
            )
            workloads = self.worlds.generate(plan, seed=self.seed)
            world_count += len(workloads)
            cache_before = self.researcher.semantic_cache_stats
            discovery = self.researcher.extend(
                workloads,
                maximum_new_operators=self.policy.maximum_new_operators_per_round,
                maximum_primitive_span=self.policy.maximum_primitive_span,
                maximum_arity=self.policy.maximum_arity,
                maximum_generation=self.policy.maximum_generation,
            )
            cache_after = self.researcher.semantic_cache_stats
            cache_delta = {
                key: cache_after[key] - cache_before[key]
                for key in cache_after
            }
            previous_yield = len(discovery.operators)
            sterile = 0 if discovery.operators else sterile + 1
            rounds.append(
                EfficiencyRoundV54(
                    round_index=round_index,
                    gap=gap,
                    experiment=plan,
                    budget_reason=budget_reason,
                    operator_count_before=len(definitions_before),
                    discovered_operators=discovery.operators,
                    rejected_candidate_count=len(discovery.rejected),
                    training_token_reduction=discovery.training_reduction,
                    cache_delta=cache_delta,
                    consecutive_sterile_rounds=sterile,
                )
            )
            if sterile >= self.patience:
                stop_reason = "semantic_saturation"
                break
        return EfficientResearchResultV54(
            seed=self.seed,
            policy=self.policy,
            operators=self.researcher.vm.operators,
            rounds=tuple(rounds),
            self_generated_world_count=world_count,
            stop_reason=stop_reason,
            patience=self.patience,
            maximum_rounds=self.maximum_rounds,
            cache_stats=self.researcher.semantic_cache_stats,
        )
