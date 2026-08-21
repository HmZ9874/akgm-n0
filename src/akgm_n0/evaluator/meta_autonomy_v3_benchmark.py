"""Evaluator-owned sealed benchmark for the meta-autonomy v3 learner.

The learner receives only the development tables and opaque world IDs.  The
sealed rows, post-hoc mathematical descriptions, scoring thresholds, and
boundary cases stay in this evaluator module.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from akgm_n0.learner.meta_autonomy_v3 import (
    AffineExpression,
    AnonymousWorld,
    AutonomousCurriculum,
    EvolvedProgram,
    GeneralizedMistakeMemory,
    GrammarGenome,
    PolynomialInvariantKernel,
    PolynomialInvariantMiner,
    InvariantCertificate,
    compile_affine_program,
    compile_fold_program,
)


BENCHMARK_VERSION = "meta-autonomy-v3-benchmark-v0.1"
REQUIRED_SCORE = 8.0


@dataclass(frozen=True, slots=True)
class SealedCase:
    world: AnonymousWorld
    sealed_inputs: tuple[tuple[int, ...], ...]
    sealed_outputs: tuple[tuple[int, ...], ...]
    posthoc_equivalent: str


def _case(
    world_id: str,
    development_inputs: Sequence[Sequence[int]],
    development_outputs: Sequence[int | Sequence[int]],
    sealed_inputs: Sequence[Sequence[int]],
    sealed_outputs: Sequence[int | Sequence[int]],
    posthoc_equivalent: str,
) -> SealedCase:
    world = AnonymousWorld.create(world_id, development_inputs, development_outputs)
    normalized_outputs = tuple(
        (int(output),) if isinstance(output, int) else tuple(map(int, output))
        for output in sealed_outputs
    )
    return SealedCase(
        world,
        tuple(tuple(map(int, row)) for row in sealed_inputs),
        normalized_outputs,
        posthoc_equivalent,
    )


def sealed_cases() -> tuple[SealedCase, ...]:
    """Return evaluator data.  Callers must not pass sealed fields to learners."""

    return (
        _case(
            "AW-7fa1", ((-2, 3), (0, 4), (1, -1), (3, 2)),
            (-6, -3, 4, 5), ((-5, -2), (4, 9), (8, -3)),
            (-7, 0, 20), "two-input affine relation",
        ),
        _case(
            "AW-91bc", ((-4,), (-2,), (0,), (3,), (5,)),
            (4, 2, 0, 3, 5), ((-9,), (1,), (12,)),
            (9, 1, 12), "sign-guarded magnitude",
        ),
        _case(
            "AW-c203", ((2, 0), (2, 1), (2, 3), (3, 4), (5, 2)),
            (0, 2, 6, 12, 10), ((7, 6), (9, 3), (0, 11), (4, 8)),
            (42, 27, 0, 32), "repeated accumulation; equivalent to natural multiplication",
        ),
        _case(
            "AW-d814", ((0,), (1,), (2,), (3,), (5,)),
            (0, 1, 3, 6, 15), ((6,), (7,), (9,)),
            (21, 28, 45), "two-state triangular accumulation",
        ),
        _case(
            "AW-e52a", ((-1,), (0,), (2,), (5,)),
            ((-1, 0), (0, 1), (2, 3), (5, 6)), ((-5,), (8,), (13,)),
            ((-5, -4), (8, 9), (13, 14)), "two-output product construction",
        ),
    )


def _formal_programs() -> tuple[tuple[str, EvolvedProgram, bool], ...]:
    zero1 = AffineExpression((0,), 0)
    one1 = AffineExpression((0,), 1)
    zero2 = AffineExpression((0, 0), 0)
    return (
        (
            "FP-01",
            compile_fold_program(
                input_width=2, counter_input=1, initial_registers=(zero2,),
                update_matrix=((1, 1, 0),), update_bias=(0,),
            ),
            True,
        ),
        (
            "FP-02",
            compile_fold_program(
                input_width=1, counter_input=0, initial_registers=(zero1, one1),
                update_matrix=((1, 1, 0), (0, 1, 0)), update_bias=(0, 1),
            ),
            True,
        ),
        (
            "FP-03",
            compile_fold_program(
                input_width=2, counter_input=1,
                initial_registers=(AffineExpression((1, 0), 0),),
                update_matrix=((1, 0, 0),), update_bias=(3,),
            ),
            True,
        ),
        (
            "FP-04",
            compile_fold_program(
                input_width=1, counter_input=0, initial_registers=(zero1, one1),
                update_matrix=((1, 1, 0), (0, 1, 0)), update_bias=(0, 2),
            ),
            True,
        ),
        (
            "FP-05",
            compile_fold_program(
                input_width=1, counter_input=0, initial_registers=(one1,),
                update_matrix=((2, 0),), update_bias=(0,),
            ),
            False,
        ),
    )


def _mistake_transfer() -> dict[str, Any]:
    memory = GeneralizedMistakeMemory(minimum_support=2)
    context = "shape:2>1"
    training = (
        compile_affine_program((1, 0), 0),
        compile_affine_program((2, 0), 1),
    )
    for index, program in enumerate(training):
        memory.observe(context, program, {"sealed_counterexample": index})
    unseen = tuple(
        compile_affine_program((coefficient, 0), bias)
        for coefficient, bias in ((-2, -2), (-2, 1), (-1, 2), (1, -2), (1, 2), (2, -2), (2, 2), (-1, -1))
    )
    correct = compile_affine_program((2, -1), 1)
    rejected = tuple(program.program_id for program in unseen if memory.rejects(context, program))
    clause = memory.clause(context)
    return {
        "context": context,
        "training_programs": [program.to_dict() for program in training],
        "unseen_programs": [program.to_dict() for program in unseen],
        "correct_program": correct.to_dict(),
        "clause": clause.to_dict() if clause else None,
        "unseen_rejected": list(rejected),
        "unseen_count": len(unseen),
        "false_positive_on_correct": memory.rejects(context, correct),
    }


def _proof_results() -> list[dict[str, Any]]:
    miner = PolynomialInvariantMiner(maximum_degree=2)
    results = []
    for case_id, program, invariant_expected in _formal_programs():
        certificates = miner.mine(program)
        verifications = [miner.kernel.verify(program, item) for item in certificates]
        results.append(
            {
                "case_id": case_id,
                "program": program.to_dict(),
                "degree_bound": 2,
                "invariant_expected": invariant_expected,
                "certificate_count": len(certificates),
                "certificates": [item.to_dict() for item in certificates],
                "kernel_results": verifications,
                "passed": bool(certificates) == invariant_expected
                and all(item["passed"] for item in verifications),
            }
        )
    return results


def _sealed_result(case: SealedCase, program: EvolvedProgram) -> dict[str, Any]:
    actual = [program.execute(row) for row in case.sealed_inputs]
    checks = [value == expected for value, expected in zip(actual, case.sealed_outputs, strict=True)]
    return {
        "world_id": case.world.world_id,
        "program": program.to_dict(),
        "sealed_case_count": len(checks),
        "sealed_passed_count": sum(checks),
        "passed": all(checks),
        "posthoc_equivalent": case.posthoc_equivalent,
        "target_name_seen_by_learner": False,
    }


def _score_report(
    sealed_results: Sequence[Mapping[str, Any]],
    mistake: Mapping[str, Any],
    proof_results: Sequence[Mapping[str, Any]],
    mutation_names: set[str],
    selection_count: int,
) -> dict[str, float]:
    world_count = len(sealed_results)
    sealed_passes = sum(bool(item["passed"]) for item in sealed_results)
    transfer = len(mistake["unseen_rejected"]) / max(1, int(mistake["unseen_count"]))
    mistake_score = 0.0 if mistake["false_positive_on_correct"] else 10.0 * transfer
    certified_count = sum(
        bool(item["invariant_expected"])
        and int(item["certificate_count"]) > 0
        and all(result["passed"] for result in item["kernel_results"])
        for item in proof_results
    )
    proof_score = 10.0 * certified_count / max(1, len(proof_results))
    return {
        "mistake_family_transfer": round(mistake_score, 2),
        "autonomous_frontier_choice": round(10.0 * selection_count / world_count, 2),
        "grammar_self_extension": round(10.0 * min(len(mutation_names), 5) / 5, 2),
        "formal_proof_autonomy": round(proof_score, 2),
        "sealed_open_ended_generalization": round(10.0 * sealed_passes / world_count, 2),
    }


def run_meta_autonomy_benchmark() -> dict[str, Any]:
    cases = sealed_cases()
    learner_worlds = tuple(case.world for case in cases)
    initial_genome = GrammarGenome()
    curriculum = AutonomousCurriculum().run(learner_worlds, initial_genome)
    sealed_results = [
        _sealed_result(case, curriculum.programs[case.world.world_id])
        if case.world.world_id in curriculum.programs
        else {
            "world_id": case.world.world_id, "program": None,
            "sealed_case_count": len(case.sealed_inputs), "sealed_passed_count": 0,
            "passed": False, "posthoc_equivalent": case.posthoc_equivalent,
            "target_name_seen_by_learner": False,
        }
        for case in cases
    ]
    mistake = _mistake_transfer()
    proofs = _proof_results()
    mutation_names = {
        mutation
        for selection in curriculum.selections
        for mutation in selection.mutations
    }
    scores = _score_report(
        sealed_results, mistake, proofs, mutation_names, len(curriculum.selections)
    )
    minimum_score = min(scores.values())
    report: dict[str, Any] = {
        "report_version": BENCHMARK_VERSION,
        "claim": "bounded_meta_autonomy_benchmark_only",
        "required_score_per_dimension": REQUIRED_SCORE,
        "overall_score": minimum_score,
        "passed": minimum_score >= REQUIRED_SCORE,
        "learner_information_boundary": {
            "received": ["opaque world id", "integer input rows", "integer output rows", "generic grammar mutations"],
            "withheld": ["sealed rows", "mathematical names", "target formulas", "benchmark scoring", "proof boundary expectation"],
        },
        "initial_genome": initial_genome.to_dict(),
        "final_genome": curriculum.final_genome.to_dict(),
        "autonomous_selections": [
            {
                "selection_index": item.selection_index,
                "selected_world_id": item.selected_world_id,
                "learner_score": item.learner_score,
                "solved": item.solved,
                "grammar_before": item.grammar_before.to_dict(),
                "grammar_after": item.grammar_after.to_dict(),
                "mutations": list(item.mutations),
                "host_selected": False,
            }
            for item in curriculum.selections
        ],
        "sealed_results": sealed_results,
        "mistake_transfer": mistake,
        "formal_proof_results": proofs,
        "dimension_scores": scores,
        "limitations": [
            "The score is for five declared capabilities on this sealed finite benchmark, not a universal intelligence score.",
            "Program synthesis is restricted to integer affine, guarded, bounded counter-fold, and product-output genomes.",
            "The proof miner is complete only for polynomial invariants up to degree two in its supported transition language.",
            "The geometric-growth boundary is intentionally not certified by the degree-two invariant kernel.",
        ],
    }
    report["content_digest"] = _content_digest(report)
    return report


def verify_meta_autonomy_report(report: Mapping[str, Any]) -> dict[str, Any]:
    obligations: list[dict[str, Any]] = []

    def check(identifier: str, passed: bool, actual: Any = None) -> None:
        obligations.append({"id": identifier, "passed": bool(passed), "actual": actual})

    check("report_version", report.get("report_version") == BENCHMARK_VERSION, report.get("report_version"))
    digest = report.get("content_digest")
    check("content_digest", isinstance(digest, str) and digest == _content_digest(report), digest)
    learner_boundary = report.get("learner_information_boundary", {})
    check("targets_withheld", "target formulas" in learner_boundary.get("withheld", []), learner_boundary)

    cases = {case.world.world_id: case for case in sealed_cases()}
    sealed_valid = 0
    for item in report.get("sealed_results", []):
        case = cases.get(item.get("world_id"))
        if case is None or not item.get("program"):
            continue
        try:
            program = EvolvedProgram.from_dict(item["program"])
            replay = _sealed_result(case, program)
            if replay["passed"] and item.get("passed") is True and item.get("sealed_passed_count") == replay["sealed_passed_count"]:
                sealed_valid += 1
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    check("all_sealed_programs_replay", sealed_valid == len(cases), sealed_valid)

    mistake = report.get("mistake_transfer", {})
    try:
        memory = GeneralizedMistakeMemory(minimum_support=2)
        context = str(mistake["context"])
        for index, value in enumerate(mistake["training_programs"]):
            memory.observe(context, EvolvedProgram.from_dict(value), {"replay": index})
        unseen = [EvolvedProgram.from_dict(value) for value in mistake["unseen_programs"]]
        correct = EvolvedProgram.from_dict(mistake["correct_program"])
        replay_rejected = [item.program_id for item in unseen if memory.rejects(context, item)]
        mistake_valid = (
            replay_rejected == mistake["unseen_rejected"]
            and not memory.rejects(context, correct)
            and memory.clause(context) is not None
            and memory.clause(context).to_dict() == mistake["clause"]
        )
    except (KeyError, TypeError, ValueError):
        mistake_valid = False
    check("mistake_family_replays", mistake_valid, mistake.get("clause"))

    proof_valid = 0
    kernel = PolynomialInvariantKernel()
    for item in report.get("formal_proof_results", []):
        try:
            program = EvolvedProgram.from_dict(item["program"])
            certs = [
                InvariantCertificate(
                    str(value["certificate_id"]), str(value["program_id"]),
                    int(value["variable_count"]), int(value["degree"]),
                    tuple(map(int, value["coefficients"])),
                    tuple(tuple(map(int, monomial)) for monomial in value["monomials"]),
                    int(value["ranking_variable"]),
                )
                for value in item["certificates"]
            ]
            boundary = not item["invariant_expected"] and not certs
            certified = item["invariant_expected"] and bool(certs) and all(kernel.verify(program, cert)["passed"] for cert in certs)
            proof_valid += bool(boundary or certified)
        except (KeyError, TypeError, ValueError):
            continue
    check("formal_proofs_replay", proof_valid == 5, proof_valid)

    scores = report.get("dimension_scores", {})
    score_valid = (
        isinstance(scores, Mapping) and len(scores) == 5
        and all(isinstance(value, (int, float)) and value >= REQUIRED_SCORE for value in scores.values())
        and report.get("overall_score") == min(scores.values())
        and report.get("passed") is True
    )
    check("every_dimension_at_least_eight", score_valid, scores)
    selections = report.get("autonomous_selections", [])
    check(
        "learner_selected_every_frontier",
        len(selections) == 5 and all(item.get("host_selected") is False for item in selections),
        len(selections),
    )
    return {
        "verifier_version": "meta-autonomy-v3-independent-replay-v0.1",
        "passed": all(item["passed"] for item in obligations),
        "obligations": obligations,
    }


def _content_digest(report: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
