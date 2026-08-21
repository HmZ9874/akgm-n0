"""Independent acceptance audit for the V17 autonomous research loop."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import Any, Sequence

from akgm_n0.learner.autonomous_research_loop_v17 import (
    AutonomousResearchLoopV17,
    AutonomousResearchResultV17,
    AutonomousWorldFactoryV17,
    KnowledgeGapAnalyzerV17,
)
from akgm_n0.learner.cold_start_semantics_v16 import (
    DATA_OPS,
    OperatorDefinitionV16,
    SelfExtendingCounterVM,
    operator_surface_audit,
)
from .cold_start_semantics_v16 import IndependentSemanticVerifierV16


def _verify_operator_chain(definitions: Sequence[OperatorDefinitionV16]) -> dict[str, Any]:
    vm = SelfExtendingCounterVM()
    verifier = IndependentSemanticVerifierV16()
    reports = []
    for definition in definitions:
        vm.install_operator(definition)
        reports.append(verifier.verify(definition, vm).to_dict())
    return {
        "passed": all(item["passed"] for item in reports),
        "operator_count": len(reports),
        "exhaustive_cases": sum(item["exhaustive_cases"] for item in reports),
        "reports": reports,
    }


def _audit_research_causality(result: AutonomousResearchResultV17, *, seed: int) -> dict[str, Any]:
    analyzer = KnowledgeGapAnalyzerV17()
    factory = AutonomousWorldFactoryV17()
    prefix: list[OperatorDefinitionV16] = []
    rounds = []
    for round_ in result.rounds:
        recomputed_gap = analyzer.inspect(prefix)
        gap_matches = recomputed_gap == round_.gap
        plan_matches = (
            round_.experiment.gap_id == round_.gap.gap_id
            and round_.experiment.focus_transition == round_.gap.focus_transition
            and round_.experiment.target_arity == round_.gap.target_arity
        )
        worlds = factory.generate(round_.experiment, seed=seed)
        digest = hashlib.sha256(
            json.dumps([item.to_dict() for item in worlds], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        world_matches = digest == round_.world_digest
        count_matches = round_.operator_count_before == len(prefix)
        prefix.extend(round_.discovered_operators)
        rounds.append({
            "round_index": round_.round_index,
            "gap_recomputed": gap_matches,
            "experiment_responds_to_gap": plan_matches,
            "world_regenerated": world_matches,
            "knowledge_count_matches": count_matches,
        })
    return {"passed": all(all(value for key, value in item.items() if key != "round_index") for item in rounds), "rounds": rounds}


def _mutated_certificate_audit(definition: OperatorDefinitionV16) -> dict[str, Any]:
    body = list(definition.body)
    mutation_index = next(index for index, item in enumerate(body) if item.op in DATA_OPS)
    item = body[mutation_index]
    body[mutation_index] = replace(item, op="u_zero" if item.op != "u_zero" else "u_inc")
    mutated = replace(definition, body=tuple(body))
    vm = SelfExtendingCounterVM()
    vm.install_operator(mutated)
    report = IndependentSemanticVerifierV16().verify(mutated, vm)
    return {
        "candidate_id": mutated.operator_id,
        "rejected": not report.passed,
        "counterexample": report.counterexample,
    }


def run_v17_acceptance(*, independent_runs: int = 5) -> dict[str, Any]:
    if independent_runs < 1:
        raise ValueError("at least one autonomous research run is required")
    run_reports = []
    raw_results = []
    for run_index in range(independent_runs):
        seed = 17_001 + run_index * 997
        result = AutonomousResearchLoopV17(seed=seed).run()
        raw_results.append(result)
        verification = _verify_operator_chain(result.operators)
        causality = _audit_research_causality(result, seed=seed)
        mutation = _mutated_certificate_audit(result.operators[0])
        surface = operator_surface_audit(result.operators)
        payload = result.to_dict()
        payload.update({
            "operator_verification": verification,
            "causality_audit": causality,
            "mutation_audit": mutation,
            "surface_audit": surface,
            "distinct_gap_count": len({round_.gap.gap_id for round_ in result.rounds}),
            "total_rejected_candidates": sum(round_.rejected_candidate_count for round_ in result.rounds),
        })
        run_reports.append(payload)

    obligations = (
        {"obligation_id": "five_independent_autonomous_research_runs", "passed": independent_runs >= 5},
        {"obligation_id": "every_run_starts_with_empty_dynamic_registry", "passed": all(result.initial_dynamic_operator_count == 0 for result in raw_results)},
        {"obligation_id": "worlds_are_generated_inside_the_research_loop", "passed": all(report["self_generated_world_count"] > 0 and report["causality_audit"]["passed"] for report in run_reports)},
        {"obligation_id": "knowledge_gap_is_recomputed_before_every_experiment", "passed": all(all(item["gap_recomputed"] for item in report["causality_audit"]["rounds"]) for report in run_reports)},
        {"obligation_id": "experiment_selection_responds_to_current_gap", "passed": all(all(item["experiment_responds_to_gap"] for item in report["causality_audit"]["rounds"]) for report in run_reports)},
        {"obligation_id": "research_direction_changes_with_acquired_knowledge", "passed": all(report["distinct_gap_count"] >= 4 for report in run_reports)},
        {"obligation_id": "new_runtime_semantics_are_discovered", "passed": all(report["operator_count"] >= 30 for report in run_reports)},
        {"obligation_id": "learned_semantics_are_reused_recursively", "passed": all(report["generation_depth"] >= 2 for report in run_reports)},
        {"obligation_id": "all_semantics_have_independent_certificates", "passed": all(report["operator_verification"]["passed"] for report in run_reports)},
        {"obligation_id": "mutated_semantics_are_rejected", "passed": all(report["mutation_audit"]["rejected"] for report in run_reports)},
        {"obligation_id": "loop_stops_only_after_consecutive_sterile_rounds", "passed": all(
            result.stop_reason == "semantic_saturation"
            and len(result.rounds) < result.maximum_rounds
            and len(result.rounds) >= result.patience
            and all(len(round_.discovered_operators) == 0 for round_ in result.rounds[-result.patience:])
            for result in raw_results
        )},
        {"obligation_id": "no_named_high_level_target_leakage", "passed": all(report["surface_audit"]["passed"] for report in run_reports)},
    )
    return {
        "benchmark_version": "autonomous-research-loop-v17.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_bounded_autonomous_research_saturation",
        "independent_run_count": independent_runs,
        "runs": run_reports,
        "aggregate": {
            "operators_discovered": sum(report["operator_count"] for report in run_reports),
            "minimum_operators_per_run": min(report["operator_count"] for report in run_reports),
            "self_generated_worlds": sum(report["self_generated_world_count"] for report in run_reports),
            "research_rounds": sum(report["round_count"] for report in run_reports),
            "minimum_generation_depth": min(report["generation_depth"] for report in run_reports),
            "certificate_cases": sum(report["operator_verification"]["exhaustive_cases"] for report in run_reports),
            "mutations_rejected": sum(report["mutation_audit"]["rejected"] for report in run_reports),
            "saturation_stops": sum(report["stop_reason"] == "semantic_saturation" for report in run_reports),
        },
        "proof_obligations": list(obligations),
        "limitations": [
            "Saturation is proven only inside the declared charter: primitive span at most three, arity at most two, and generation at most three.",
            "The system autonomously chooses experiments within that charter; the eight primitives, MDL reward, and safety boundaries remain externally supplied.",
            "The generated worlds are program-behavior experiments, not unrestricted physical or mathematical universes.",
            "A safety maximum of 32 rounds exists, but successful runs must stop earlier through four consecutive sterile rounds.",
        ],
    }

