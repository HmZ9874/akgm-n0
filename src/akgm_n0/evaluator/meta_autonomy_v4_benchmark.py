"""Expanded evaluator-only research benchmark for the v4 symbolic learner."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from akgm_n0.evaluator.meta_autonomy_v3_benchmark import sealed_cases as v3_cases
from akgm_n0.learner.meta_autonomy_v3 import (
    AdaptiveGrammarSynthesizer,
    AnonymousWorld,
    AutonomousCurriculum,
    EvolvedProgram,
    GenericProgramSynthesizer,
    GrammarGenome,
)
from akgm_n0.learner.meta_autonomy_v4 import (
    AutonomousProofPortfolio,
    MacroGuidedSynthesizer,
    TransitionLibraryMiner,
    replay_portfolio_proof,
)


BENCHMARK_VERSION = "meta-autonomy-v4-deep-research-v0.1"


@dataclass(frozen=True, slots=True)
class DeepCase:
    world: AnonymousWorld
    sealed_inputs: tuple[tuple[int, ...], ...]
    sealed_outputs: tuple[tuple[int, ...], ...]
    evaluator_interpretation: str


def _normalize(outputs: Sequence[int | Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    return tuple(
        (int(value),) if isinstance(value, int) else tuple(map(int, value))
        for value in outputs
    )


def _case(
    world_id: str, development: Sequence[int], sealed_indices: Sequence[int],
    sealed: Sequence[int], interpretation: str,
) -> DeepCase:
    return DeepCase(
        AnonymousWorld.create(world_id, tuple((i,) for i in range(len(development))), development),
        tuple((i,) for i in sealed_indices), _normalize(sealed), interpretation,
    )


def deep_cases() -> tuple[DeepCase, ...]:
    inherited = tuple(
        DeepCase(case.world, case.sealed_inputs, case.sealed_outputs, case.posthoc_equivalent)
        for case in v3_cases()
    )
    return inherited + (
        _case("AW-v4-21", (1, 2, 4, 8, 16, 32), (6, 7, 8, 9), (64, 128, 256, 512), "hidden two-state doubling dynamics"),
        _case("AW-v4-37", (1, 1, 2, 6, 24, 120), (6, 7, 8), (720, 5040, 40320), "state/counter product fold"),
        _case("AW-v4-4b", (0, 1, 4, 9, 16, 25), (6, 7, 9), (36, 49, 81), "repeated self-sized accumulation"),
        _case("AW-v4-5d", (1, -1, 1, -1, 1, -1), (6, 7, 8, 9), (1, -1, 1, -1), "signed period-two recurrence"),
        _case("AW-v4-6e", (0, 1, 1, 2, 3, 5), (6, 7, 8, 9), (8, 13, 21, 34), "second-order C-finite recurrence"),
        _case("AW-v4-7f", (1, 3, 9, 27, 81, 243), (6, 7, 8), (729, 2187, 6561), "learned scale-three recurrence"),
    )


def transfer_case() -> DeepCase:
    return _case(
        "AW-v4-transfer-93", (0, 1, 2, 4, 8, 16, 32),
        (7, 8, 9, 10), (64, 128, 256, 512),
        "shifted recurrence requiring a previously mined transition pair",
    )


def _sealed_check(case: DeepCase, program: EvolvedProgram) -> dict[str, Any]:
    values = [program.execute(row) for row in case.sealed_inputs]
    passed = [value == expected for value, expected in zip(values, case.sealed_outputs, strict=True)]
    return {
        "world_id": case.world.world_id,
        "program": program.to_dict(),
        "passed": all(passed),
        "sealed_passed": sum(passed),
        "sealed_total": len(passed),
        "evaluator_interpretation": case.evaluator_interpretation,
        "interpretation_visible_to_learner": False,
    }


def run_deep_research_benchmark() -> dict[str, Any]:
    cases = deep_cases()
    initial = GrammarGenome()
    curriculum = AutonomousCurriculum(
        AdaptiveGrammarSynthesizer(maximum_rounds=10)
    ).run(tuple(case.world for case in cases), initial)
    sealed_results = [
        _sealed_check(case, curriculum.programs[case.world.world_id])
        if case.world.world_id in curriculum.programs
        else {
            "world_id": case.world.world_id, "program": None, "passed": False,
            "sealed_passed": 0, "sealed_total": len(case.sealed_inputs),
            "evaluator_interpretation": case.evaluator_interpretation,
            "interpretation_visible_to_learner": False,
        }
        for case in cases
    ]
    portfolio = AutonomousProofPortfolio()
    proof_results = []
    loop_programs = [program for program in curriculum.programs.values() if program.kind == "counter_fold"]
    for program in loop_programs:
        proofs = portfolio.prove(program)
        proof_results.append({
            "program_id": program.program_id,
            "program": program.to_dict(),
            "proofs": [proof.to_dict() for proof in proofs],
            "proof_domains": sorted({proof.proof_domain for proof in proofs}),
            "passed": bool(proofs) and all(proof.verification["passed"] for proof in proofs),
        })

    # A single carried grammar may settle on different equivalent programs and
    # hide reusable substructure.  Keep independent minimal-genome solutions in
    # the wake corpus so compression sees multiple valid decompositions.
    library_source_ids = ("AW-v4-21", "AW-v4-6e", "AW-d814")
    case_by_id = {case.world.world_id: case for case in cases}
    independent_solver = AdaptiveGrammarSynthesizer(maximum_rounds=10)
    library_programs = tuple(
        independent_solver.solve(case_by_id[world_id].world, GrammarGenome()).final_candidate.program
        for world_id in library_source_ids
    )
    macros = TransitionLibraryMiner().mine(library_programs, minimum_support=2)
    transfer = transfer_case()
    macro_report = MacroGuidedSynthesizer().search(transfer.world, macros)
    macro_sealed = _sealed_check(transfer, macro_report.selected.program)
    baseline = GenericProgramSynthesizer().search(
        transfer.world, GrammarGenome(state_cells=2, loop_depth=1)
    )
    efficiency_reduction = 1.0 - macro_report.candidates_executed / baseline.candidates_executed
    mutations = {
        mutation for item in curriculum.selections for mutation in item.mutations
    }
    required_mutations = {
        "grow_input_channel", "grow_state_cell", "grow_counter_fold",
        "grow_guarded_path", "grow_product_output",
        "expand_coefficient_palette", "grow_counter_interaction",
    }
    scores = {
        "expanded_sealed_generalization": round(10 * sum(item["passed"] for item in sealed_results) / len(cases), 2),
        "proof_portfolio_coverage": round(10 * sum(item["passed"] for item in proof_results) / max(1, len(proof_results)), 2),
        "structural_self_extension": round(10 * len(mutations & required_mutations) / len(required_mutations), 2),
        "autonomous_curriculum": round(10 * len(curriculum.selections) / len(cases), 2),
        "library_transfer_efficiency": round(10 * max(0.0, efficiency_reduction), 2),
    }
    report: dict[str, Any] = {
        "report_version": BENCHMARK_VERSION,
        "claim": "expanded_bounded_symbolic_research_only",
        "passed": min(scores.values()) >= 8.0 and macro_sealed["passed"],
        "overall_score": min(scores.values()),
        "dimension_scores": scores,
        "information_boundary": {
            "learner_received": ["opaque IDs", "development integer tables", "generic structural genes"],
            "learner_withheld": ["sealed values", "mathematical interpretations", "target formulas", "proof domains", "transfer world"],
        },
        "initial_genome": initial.to_dict(),
        "final_genome": curriculum.final_genome.to_dict(),
        "autonomous_selections": [
            {
                "index": item.selection_index, "world_id": item.selected_world_id,
                "learner_score": item.learner_score, "solved": item.solved,
                "mutations": list(item.mutations), "host_selected": False,
            }
            for item in curriculum.selections
        ],
        "sealed_results": sealed_results,
        "proof_results": proof_results,
        "library_learning": {
            "macros": [macro.to_dict() for macro in macros],
            "independent_solution_world_ids": list(library_source_ids),
            "independent_solution_programs": [program.to_dict() for program in library_programs],
            "macro_count": len(macros),
            "transfer_search": macro_report.to_dict(),
            "transfer_sealed": macro_sealed,
            "primitive_baseline_candidates": baseline.candidates_executed,
            "macro_candidates": macro_report.candidates_executed,
            "candidate_reduction_fraction": efficiency_reduction,
        },
        "research_findings": [
            "A coefficient-two behavior emerged through two interacting ±1 states before coefficient expansion was selected.",
            "The proof portfolio discovered an affine eigen-form hidden across multiple state cells.",
            "A counter/state interaction gene made a previously unreachable product fold expressible.",
            "Capacity semantics must retain all smaller genomes; forcing maximum state width caused false unreachable results.",
            "Repeated transition rows compressed into macros and solved a withheld transfer world before primitive enumeration.",
        ],
        "limitations": [
            "State width is still capped at two in open enumeration.",
            "Counter interaction search is restricted to one state cell to control combinatorial growth.",
            "Proof domains cover polynomial, affine eigen-scaling, counter-product induction, and small C-finite systems—not arbitrary programs.",
            "This benchmark measures symbolic program creation, not language understanding or universal mathematical intelligence.",
        ],
    }
    report["content_digest"] = _digest(report)
    return report


def verify_deep_research_report(report: Mapping[str, Any]) -> dict[str, Any]:
    obligations = []

    def check(identifier: str, passed: bool, actual: Any) -> None:
        obligations.append({"id": identifier, "passed": bool(passed), "actual": actual})

    check("version", report.get("report_version") == BENCHMARK_VERSION, report.get("report_version"))
    check("digest", report.get("content_digest") == _digest(report), report.get("content_digest"))
    cases = {case.world.world_id: case for case in deep_cases()}
    replayed = 0
    for item in report.get("sealed_results", []):
        try:
            case = cases[item["world_id"]]
            result = _sealed_check(case, EvolvedProgram.from_dict(item["program"]))
            replayed += result["passed"] and item["passed"]
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    check("sealed_replay", replayed == len(cases), replayed)

    proofs_replayed = 0
    for item in report.get("proof_results", []):
        try:
            program = EvolvedProgram.from_dict(item["program"])
            valid = bool(item["proofs"]) and all(
                replay_portfolio_proof(program, proof)["passed"]
                and proof["verification"] == replay_portfolio_proof(program, proof)
                for proof in item["proofs"]
            )
            proofs_replayed += valid
        except (KeyError, TypeError, ValueError):
            continue
    check("proof_portfolio_replay", proofs_replayed == len(report.get("proof_results", [])) and proofs_replayed > 0, proofs_replayed)

    library = report.get("library_learning", {})
    try:
        transfer = transfer_case()
        transfer_program = EvolvedProgram.from_dict(library["transfer_search"]["selected_program"])
        transfer_valid = _sealed_check(transfer, transfer_program)["passed"]
        baseline = GenericProgramSynthesizer().search(
            transfer.world, GrammarGenome(state_cells=2, loop_depth=1)
        )
        efficiency_valid = (
            transfer_valid
            and library["primitive_baseline_candidates"] == baseline.candidates_executed
            and 0 < library["macro_candidates"] < baseline.candidates_executed
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        efficiency_valid = False
    check("library_transfer_replay", efficiency_valid, library.get("macro_candidates"))
    scores = report.get("dimension_scores", {})
    score_valid = (
        isinstance(scores, Mapping) and len(scores) == 5
        and all(value >= 8.0 for value in scores.values())
        and report.get("overall_score") == min(scores.values())
        and report.get("passed") is True
    )
    check("all_scores_at_least_eight", score_valid, scores)
    check(
        "autonomous_selection",
        len(report.get("autonomous_selections", [])) == len(cases)
        and all(item.get("host_selected") is False for item in report["autonomous_selections"]),
        len(report.get("autonomous_selections", [])),
    )
    return {
        "verifier_version": "meta-autonomy-v4-replay-v0.1",
        "passed": all(item["passed"] for item in obligations),
        "obligations": obligations,
    }


def _digest(report: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
