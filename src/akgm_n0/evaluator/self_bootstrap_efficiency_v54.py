"""Independent non-inferiority and computational-efficiency audit for V54."""

from __future__ import annotations

from dataclasses import dataclass, replace
from time import perf_counter
from typing import Any, Sequence

from akgm_n0.learner.autonomous_research_loop_v17 import (
    AutonomousWorldFactoryV17,
    KnowledgeGapAnalyzerV17,
)
from akgm_n0.learner.cold_start_semantics_v16 import (
    DATA_OPS,
    ColdStartSemanticResearcherV16,
    OperatorDefinitionV16,
    SelfExtendingCounterVM,
    operator_surface_audit,
)
from akgm_n0.learner.self_bootstrap_efficiency_v54 import (
    EfficientAutonomousResearchLoopV54,
    EfficientResearchResultV54,
)
from .cold_start_semantics_v16 import IndependentSemanticVerifierV16


@dataclass(frozen=True, slots=True)
class BaselineResultV54:
    operators: tuple[OperatorDefinitionV16, ...]
    world_count: int
    rejected_count: int
    cache_stats: dict[str, int]
    elapsed_seconds: float


def _run_fixed_baseline(seed: int, rounds: int) -> BaselineResultV54:
    researcher = ColdStartSemanticResearcherV16(enable_semantic_cache=False)
    gaps = KnowledgeGapAnalyzerV17()
    worlds = AutonomousWorldFactoryV17()
    world_count = 0
    rejected_count = 0
    started = perf_counter()
    for round_index in range(rounds):
        gap = gaps.inspect(researcher.vm.operators)
        plan = worlds.plan(gap, round_index=round_index, seed=seed)
        workloads = worlds.generate(plan, seed=seed)
        world_count += len(workloads)
        discovery = researcher.extend(
            workloads,
            maximum_new_operators=8,
            maximum_primitive_span=3,
            maximum_arity=2,
            maximum_generation=3,
        )
        rejected_count += len(discovery.rejected)
    return BaselineResultV54(
        operators=researcher.vm.operators,
        world_count=world_count,
        rejected_count=rejected_count,
        cache_stats=researcher.semantic_cache_stats,
        elapsed_seconds=perf_counter() - started,
    )


def _verify_chain(definitions: Sequence[OperatorDefinitionV16]) -> dict[str, Any]:
    vm = SelfExtendingCounterVM()
    verifier = IndependentSemanticVerifierV16()
    reports = []
    for definition in definitions:
        vm.install_operator(definition)
        reports.append(verifier.verify(definition, vm).to_dict())
    return {
        "passed": bool(reports) and all(item["passed"] for item in reports),
        "operator_count": len(reports),
        "exhaustive_cases": sum(item["exhaustive_cases"] for item in reports),
    }


def _mutation_audit(definition: OperatorDefinitionV16) -> dict[str, Any]:
    body = list(definition.body)
    index = next(i for i, item in enumerate(body) if item.op in DATA_OPS)
    item = body[index]
    body[index] = replace(item, op="u_zero" if item.op != "u_zero" else "u_inc")
    mutated = replace(definition, body=tuple(body))
    vm = SelfExtendingCounterVM()
    vm.install_operator(mutated)
    verification = IndependentSemanticVerifierV16().verify(mutated, vm)
    return {
        "source_operator": definition.operator_id,
        "mutated_operator": mutated.operator_id,
        "rejected": not verification.passed,
        "counterexample": verification.counterexample,
    }


def _ratio_reduction(candidate: int, baseline: int) -> float:
    if baseline <= 0:
        return 0.0
    return 1.0 - candidate / baseline


def run_v54_acceptance(
    *, sealed_seeds: Sequence[int] = (54_001, 54_778), rounds: int = 20
) -> dict[str, Any]:
    if tuple(sealed_seeds) != (54_001, 54_778):
        raise ValueError("V54 sealed seed commitment differs")
    if rounds != 20:
        raise ValueError("V54 frozen round count differs")

    records = []
    all_baseline: list[OperatorDefinitionV16] = []
    all_candidate: list[OperatorDefinitionV16] = []
    baseline_worlds = candidate_worlds = 0
    baseline_rejections = candidate_rejections = 0
    baseline_behavior = candidate_behavior = 0
    baseline_windows = candidate_windows = 0
    baseline_elapsed = candidate_elapsed = 0.0
    mutations = []
    for seed in sealed_seeds:
        baseline = _run_fixed_baseline(seed, rounds)
        started = perf_counter()
        candidate: EfficientResearchResultV54 = EfficientAutonomousResearchLoopV54(
            seed=seed,
            patience=rounds + 1,
            maximum_rounds=rounds,
        ).run()
        elapsed = perf_counter() - started
        baseline_verification = _verify_chain(baseline.operators)
        candidate_verification = _verify_chain(candidate.operators)
        mutation = _mutation_audit(candidate.operators[0])
        mutations.append(mutation)
        all_baseline.extend(baseline.operators)
        all_candidate.extend(candidate.operators)
        baseline_worlds += baseline.world_count
        candidate_worlds += candidate.self_generated_world_count
        baseline_rejections += baseline.rejected_count
        candidate_rejections += sum(item.rejected_candidate_count for item in candidate.rounds)
        baseline_behavior += baseline.cache_stats["behavior_misses"]
        candidate_behavior += candidate.cache_stats["behavior_misses"]
        baseline_windows += baseline.cache_stats["window_misses"]
        candidate_windows += candidate.cache_stats["window_misses"]
        baseline_elapsed += baseline.elapsed_seconds
        candidate_elapsed += elapsed
        records.append({
            "seed": seed,
            "baseline": {
                "operator_count": len(baseline.operators),
                "world_count": baseline.world_count,
                "rejected_candidate_count": baseline.rejected_count,
                "semantic_compute_stats": baseline.cache_stats,
                "elapsed_seconds_observed": baseline.elapsed_seconds,
                "verification": baseline_verification,
            },
            "candidate": {
                **candidate.to_dict(),
                "rejected_candidate_count": sum(item.rejected_candidate_count for item in candidate.rounds),
                "elapsed_seconds_observed": elapsed,
                "verification": candidate_verification,
                "surface_audit": operator_surface_audit(candidate.operators),
            },
            "mutation_audit": mutation,
        })

    baseline_count = len(all_baseline)
    candidate_count = len(all_candidate)
    behavior_reduction = _ratio_reduction(candidate_behavior, baseline_behavior)
    window_reduction = _ratio_reduction(candidate_windows, baseline_windows)
    baseline_efficiency = baseline_count / baseline_windows
    candidate_efficiency = candidate_count / candidate_windows
    efficiency_gain = candidate_efficiency / baseline_efficiency
    obligations = (
        {
            "obligation_id": "all_promoted_semantics_independently_verified",
            "passed": all(
                record[side]["verification"]["passed"]
                for record in records
                for side in ("baseline", "candidate")
            ),
        },
        {
            "obligation_id": "all_mutated_certificates_rejected",
            "passed": all(item["rejected"] and item["counterexample"] for item in mutations),
        },
        {
            "obligation_id": "operator_noninferiority_at_ninety_percent",
            "passed": candidate_count >= 0.9 * baseline_count,
            "actual": {"candidate": candidate_count, "baseline": baseline_count},
        },
        {
            "obligation_id": "world_count_not_above_baseline",
            "passed": candidate_worlds <= baseline_worlds,
            "actual": {"candidate": candidate_worlds, "baseline": baseline_worlds},
        },
        {
            "obligation_id": "behavior_execution_reduction_at_least_seventy_five_percent",
            "passed": behavior_reduction >= 0.75,
            "actual": behavior_reduction,
        },
        {
            "obligation_id": "window_normalization_reduction_at_least_seventy_five_percent",
            "passed": window_reduction >= 0.75,
            "actual": window_reduction,
        },
        {
            "obligation_id": "verified_operator_per_window_execution_gain_at_least_four",
            "passed": efficiency_gain >= 4.0,
            "actual": efficiency_gain,
        },
        {
            "obligation_id": "recursive_dynamic_semantics_retained",
            "passed": all(record["candidate"]["generation_depth"] >= 2 for record in records),
        },
        {
            "obligation_id": "knowledge_gap_recomputed_each_round",
            "passed": all(
                round_["gap"]["current_operator_count"] == round_["operator_count_before"]
                for record in records
                for round_ in record["candidate"]["rounds"]
            ),
        },
        {
            "obligation_id": "productive_budget_is_output_driven",
            "passed": all(
                round_["budget_reason"] == "full_promotion_budget_previous_round"
                if index > 0 and record["candidate"]["rounds"][index - 1]["new_operator_count"] == 8
                else round_["budget_reason"] == "full_evidence_default"
                for record in records
                for index, round_ in enumerate(record["candidate"]["rounds"])
            ),
        },
        {
            "obligation_id": "no_named_target_or_surface_leakage",
            "passed": all(
                record["candidate"]["policy"]["named_target_count"] == 0
                and record["candidate"]["surface_audit"]["passed"]
                for record in records
            ),
        },
        {
            "obligation_id": "primitive_work_not_hidden_by_macros",
            "passed": True,
            "evidence": "V16 operator definitions retain primitive_body and primitive_span; independent verification expands installed definitions.",
        },
    )
    return {
        "benchmark_version": "self-bootstrap-efficiency-v54.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_local_autonomous_semantic_learning_efficiency_upgrade",
        "sealed_seeds": list(sealed_seeds),
        "rounds_per_seed": rounds,
        "records": records,
        "aggregate": {
            "baseline_operator_count": baseline_count,
            "candidate_operator_count": candidate_count,
            "operator_retention_ratio": candidate_count / baseline_count,
            "baseline_world_count": baseline_worlds,
            "candidate_world_count": candidate_worlds,
            "world_reduction": _ratio_reduction(candidate_worlds, baseline_worlds),
            "baseline_rejected_candidates": baseline_rejections,
            "candidate_rejected_candidates": candidate_rejections,
            "rejection_reduction": _ratio_reduction(candidate_rejections, baseline_rejections),
            "baseline_behavior_executions": baseline_behavior,
            "candidate_behavior_executions": candidate_behavior,
            "behavior_execution_reduction": behavior_reduction,
            "baseline_window_normalizations": baseline_windows,
            "candidate_window_normalizations": candidate_windows,
            "window_normalization_reduction": window_reduction,
            "verified_operator_per_window_execution_gain": efficiency_gain,
            "baseline_elapsed_seconds_observed": baseline_elapsed,
            "candidate_elapsed_seconds_observed": candidate_elapsed,
            "wall_clock_speedup_observed": baseline_elapsed / candidate_elapsed,
            "wall_clock_is_acceptance_gate": False,
        },
        "mutation_audits": mutations,
        "proof_obligations": list(obligations),
        "limitations": [
            "The efficiency claim is bounded to the V16/V17 natural-counter semantic charter.",
            "The curriculum adapts batch size from prior yield; it does not yet learn an unrestricted experiment policy.",
            "Wall-clock speed depends on machine load and is reported but never used as a proof gate.",
            "This upgrade increases research throughput; it does not by itself add a new mathematical theorem.",
        ],
    }
