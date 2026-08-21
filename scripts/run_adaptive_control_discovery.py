"""Hidden-evaluator experiment for discovery of a new anonymous loop behavior."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import AdaptiveMistakeLibrary, FormulaSuccessRoom, KnowledgeLedger
from akgm_n0.learner import (
    AdaptiveControlExecutor,
    AdaptiveControlSearch,
    NumericTableObservation,
    adaptive_program_key,
)


DEVELOPMENT_CASES = (
    ((5, 2), 1),
    ((7, 3), 1),
    ((8, 3), 2),
    ((11, 4), 3),
    ((12, 5), 2),
    ((17, 5), 2),
    ((20, 6), 2),
    ((23, 7), 2),
    ((6, 3), 0),
    ((3, 5), 3),
)
SEALED_CASES = (
    ((29, 6), 5),
    ((31, 8), 7),
    ((44, 9), 8),
    ((64, 7), 1),
    ((2, 9), 2),
    ((81, 10), 1),
)
ADVERSARIAL_CASES = (
    ((0, 3), 0),
    ((1, 1), 0),
    ((100, 1), 0),
    ((127, 16), 15),
    ((255, 32), 31),
)


def observation_from(cases):
    return NumericTableObservation.create(
        opaque_session_id="anonymous-control-development",
        input_rows=tuple(row for row, _ in cases),
        output_values=tuple(output for _, output in cases),
        validity_mask=(True,) * len(cases),
        action_receipt="anonymous_numeric_rows_only",
    )


def evaluate(program, cases, executor):
    results = []
    for row, observed in cases:
        try:
            execution = executor.execute(program, row)
            predicted = execution.output_value
            results.append(
                {
                    "input": list(row),
                    "predicted": predicted,
                    "observed": observed,
                    "absolute_error": abs(predicted - observed),
                    "step_count": execution.step_count,
                    "passed": predicted == observed,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "input": list(row),
                    "predicted": None,
                    "observed": observed,
                    "absolute_error": None,
                    "step_count": None,
                    "passed": False,
                    "error": type(exc).__name__,
                }
            )
    return tuple(results)


def main() -> int:
    development = observation_from(DEVELOPMENT_CASES)
    search = AdaptiveControlSearch(top_k=200).search(development)
    displayed = []
    signatures = set()
    for candidate in search.top_candidates:
        if candidate.logic_signature in signatures:
            continue
        displayed.append(candidate)
        signatures.add(candidate.logic_signature)
        if len(displayed) == 5:
            break
    if len(displayed) < 5:
        raise RuntimeError("adaptive search produced fewer than five logic structures")

    executor = AdaptiveControlExecutor()
    winner = search.top_candidates[0]
    sealed_results = evaluate(winner.program, SEALED_CASES, executor)
    adversarial_results = evaluate(winner.program, ADVERSARIAL_CASES, executor)
    sealed_exact = all(item["passed"] for item in sealed_results)
    adversarial_exact = all(item["passed"] for item in adversarial_results)
    serialized = json.dumps(winner.program.to_dict(), sort_keys=True).lower()
    forbidden_names_absent = all(
        token not in serialized
        for token in ("remainder", "modulo", "mod", "divide", "division", "quotient")
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-adaptive-control-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    mistakes = AdaptiveMistakeLibrary(
        PROJECT_ROOT / "artifacts" / "mistakes" / "adaptive_mistakes.jsonl"
    )
    condition_key = "anonymous-control-cases-" + hashlib.sha256(
        json.dumps(DEVELOPMENT_CASES, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]

    feedback = []
    for rank, candidate in enumerate(displayed, start=1):
        development_results = evaluate(candidate.program, DEVELOPMENT_CASES, executor)
        candidate_sealed = evaluate(candidate.program, SEALED_CASES, executor)
        all_results = development_results + candidate_sealed
        counterexamples = tuple(item for item in all_results if not item["passed"])
        mistake_record = None
        if counterexamples:
            mistake_record = mistakes.record(
                candidate.program,
                failed_scope=(
                    "development_fit"
                    if any(not item["passed"] for item in development_results)
                    else "sealed_generalization"
                ),
                condition_key=condition_key,
                counterexamples=counterexamples,
                source_candidate_id=candidate.candidate_id,
            )
        feedback.append(
            {
                "rank": rank,
                **candidate.to_dict(),
                "sealed_results": list(candidate_sealed),
                "sealed_exact": all(item["passed"] for item in candidate_sealed),
                "disposition": (
                    "success_room" if not counterexamples else "mistake_library"
                ),
                "mistake_id": (
                    mistake_record.mistake_id if mistake_record is not None else None
                ),
            }
        )

    gates = (
        {
            "gate_id": "learner_program_contains_no_target_operation_name",
            "passed": forbidden_names_absent,
            "actual": forbidden_names_absent,
            "threshold": True,
        },
        {
            "gate_id": "development_rows_exact",
            "passed": winner.exact,
            "actual": winner.fit_mse,
            "threshold": 0,
        },
        {
            "gate_id": "sealed_rows_exact",
            "passed": sealed_exact,
            "actual": sum(item["passed"] for item in sealed_results),
            "threshold": len(SEALED_CASES),
        },
        {
            "gate_id": "boundary_and_adversarial_rows_exact",
            "passed": adversarial_exact,
            "actual": sum(item["passed"] for item in adversarial_results),
            "threshold": len(ADVERSARIAL_CASES),
        },
        {
            "gate_id": "candidate_created_nonzero_loop_depth",
            "passed": winner.maximum_steps_used > 0,
            "actual": winner.maximum_steps_used,
            "threshold": 1,
        },
        {
            "gate_id": "five_distinct_logic_structures_reported",
            "passed": len(signatures) == 5,
            "actual": len(signatures),
            "threshold": 5,
        },
    )
    verdict = "conditionally_passed" if all(item["passed"] for item in gates) else "failed"
    knowledge_id = ledger.propose(
        winner.program,
        parent_ids=("anonymous_single_state_control_v0.1",),
        provenance={"run_id": run_id, "candidate_id": winner.candidate_id},
        evidence={"development_fit_mse": winner.fit_mse},
    )
    ledger.transition(
        knowledge_id,
        "fit_passed" if winner.exact else "rejected",
        reason="anonymous_development_rows_evaluated",
        evidence={"training_outputs": winner.training_outputs},
    )
    room_record = None
    if winner.exact:
        ledger.transition(
            knowledge_id,
            "verified" if sealed_exact and adversarial_exact else "rejected",
            reason="sealed_and_boundary_rows_evaluated",
            evidence={
                "sealed_results": sealed_results,
                "adversarial_results": adversarial_results,
            },
        )
    if winner.exact and sealed_exact and adversarial_exact:
        ledger.transition(
            knowledge_id,
            "bounded",
            reason="verified_for_nonnegative_first_input_positive_second_input_with_step_bound",
            evidence={"maximum_registered_steps": executor.maximum_steps},
        )
        operation_id = "CTRL-" + hashlib.sha256(
            adaptive_program_key(winner.program).encode("utf-8")
        ).hexdigest()[:16]
        formula_room = FormulaSuccessRoom(
            PROJECT_ROOT
            / "artifacts"
            / "formula_rooms"
            / "success"
            / "successful_formulas.jsonl"
        )
        room_record = formula_room.record(
            winner.program,
            operation_id=operation_id,
            parent_operation_ids=("anonymous_single_state_control_v0.1",),
            validation_scope="anonymous_two_input_control_nonnegative_positive_domain_v0.1",
            knowledge_status="bounded",
            evidence={
                "run_id": run_id,
                "development_case_count": len(DEVELOPMENT_CASES),
                "sealed_case_count": len(SEALED_CASES),
                "adversarial_case_count": len(ADVERSARIAL_CASES),
                "all_exact": True,
            },
        )

    report = {
        "report_version": "adaptive-control-discovery-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "匿名自适应控制语义发现实验",
        "evaluator_posthoc_task_name": "remainder_behavior_probe",
        "verdict": verdict,
        "knowledge_status": ledger.get(knowledge_id).status,
        "architecture": "candidate_defined_state_initialization_guard_halt_polarity_update_and_output",
        "learner_received": {
            "development_input_rows": [list(row) for row, _ in DEVELOPMENT_CASES],
            "development_output_values": [output for _, output in DEVELOPMENT_CASES],
            "natural_language": False,
            "target_concept_name": False,
            "target_symbol": False,
            "target_formula": False,
            "sealed_cases_visible_during_search": False,
            "available_value_operations": [
                "a_input",
                "a_state",
                "a_constant",
                "a_add",
                "a_subtract",
            ],
            "available_guard_sensors": ["a_equal", "a_less"],
        },
        "search": {
            "programs_generated": search.programs_generated,
            "programs_executed": search.programs_executed,
            "nonhalting_programs": search.nonhalting_programs,
            "behavior_classes": search.behavior_classes,
            "evidence_constants": list(search.evidence_constants),
        },
        "five_candidate_feedback": feedback,
        "winner": {
            **winner.to_dict(),
            "sealed_results": list(sealed_results),
            "adversarial_results": list(adversarial_results),
            "posthoc_human_interpretation": (
                "Initialize state from input 0; stop when state is below input 1; "
                "otherwise subtract input 1 and repeat; output state."
            ),
        },
        "gates": list(gates),
        "success_room_record": room_record.to_dict() if room_record else None,
        "knowledge_id": knowledge_id,
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "The host provides generic equality and order sensors; the candidate chooses how to use them.",
            "The synthesized controller has one mutable state cell and no nested or branching subprograms.",
            "Validation is bounded to nonnegative first inputs, positive second inputs, and 256 steps.",
            "Zero or negative second inputs are outside the admitted scope.",
        ],
    }
    artifact_path = run_directory / "adaptive_control_discovery_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "adaptive_control_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "adaptive_control_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact_path, destination)

    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": verdict,
                "knowledge_status": ledger.get(knowledge_id).status,
                "programs_generated": search.programs_generated,
                "behavior_classes": search.behavior_classes,
                "winner_candidate_id": winner.candidate_id,
                "winner_program": winner.program.to_dict(),
                "development_exact": winner.exact,
                "sealed_exact": sealed_exact,
                "adversarial_exact": adversarial_exact,
                "success_room_record_id": (
                    room_record.room_record_id if room_record else None
                ),
                "mistake_records_written": sum(
                    item["mistake_id"] is not None for item in feedback
                ),
                "artifact_path": artifact_path.relative_to(PROJECT_ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if verdict == "conditionally_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
