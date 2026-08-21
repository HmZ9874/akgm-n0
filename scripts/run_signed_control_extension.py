"""Grow the anonymous controller from positive-domain to signed first inputs."""

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
    AdaptiveBranchExecutor,
    AdaptiveBranchSearch,
    AdaptiveControlProgram,
    NumericTableObservation,
    adaptive_branch_program_key,
)


DEVELOPMENT_CASES = (
    ((-7, 3), 2),
    ((-8, 3), 1),
    ((-11, 4), 1),
    ((-12, 5), 3),
    ((-17, 5), 3),
    ((-20, 6), 4),
    ((-3, 5), 2),
    ((7, 3), 1),
    ((8, 3), 2),
    ((0, 3), 0),
)
SEALED_CASES = (
    ((-29, 6), 1),
    ((-31, 8), 1),
    ((-44, 9), 1),
    ((-64, 7), 6),
    ((-2, 9), 7),
    ((-81, 10), 9),
    ((29, 6), 5),
)
ADVERSARIAL_CASES = (
    ((-255, 32), 1),
    ((-256, 32), 0),
    ((-1, 1), 0),
    ((-100, 1), 0),
    ((255, 32), 31),
    ((0, 7), 0),
)


def make_observation(cases) -> NumericTableObservation:
    return NumericTableObservation.create(
        opaque_session_id="anonymous-signed-control-development",
        input_rows=tuple(row for row, _ in cases),
        output_values=tuple(output for _, output in cases),
        validity_mask=(True,) * len(cases),
        action_receipt="anonymous_signed_rows_only",
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
    formula_room = FormulaSuccessRoom(
        PROJECT_ROOT
        / "artifacts"
        / "formula_rooms"
        / "success"
        / "successful_formulas.jsonl"
    )
    parent_record = next(
        (
            record
            for record in reversed(formula_room.records)
            if record.definition.get("substrate")
            == "anonymous_single_state_control_v0.1"
        ),
        None,
    )
    if parent_record is None:
        raise RuntimeError("verified positive-domain controller is unavailable")
    base_program = AdaptiveControlProgram.from_dict(parent_record.definition)
    search = AdaptiveBranchSearch(
        base_program,
        parent_operation_id=parent_record.operation_id,
        top_k=100,
    ).search(make_observation(DEVELOPMENT_CASES))
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
        raise RuntimeError("signed branch search produced fewer than five structures")

    winner = search.top_candidates[0]
    executor = AdaptiveBranchExecutor()
    sealed_results = evaluate(winner.program, SEALED_CASES, executor)
    adversarial_results = evaluate(winner.program, ADVERSARIAL_CASES, executor)
    sealed_exact = all(item["passed"] for item in sealed_results)
    adversarial_exact = all(item["passed"] for item in adversarial_results)
    serialized = json.dumps(winner.program.to_dict(), sort_keys=True).lower()
    names_absent = all(
        token not in serialized
        for token in ("negative", "remainder", "modulo", "divide", "quotient")
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-signed-control-extension-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    mistakes = AdaptiveMistakeLibrary(
        PROJECT_ROOT / "artifacts" / "mistakes" / "adaptive_mistakes.jsonl"
    )
    condition_key = "anonymous-signed-extension-" + hashlib.sha256(
        json.dumps(DEVELOPMENT_CASES, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    feedback = []
    for rank, candidate in enumerate(displayed, start=1):
        development_results = evaluate(candidate.program, DEVELOPMENT_CASES, executor)
        candidate_sealed = evaluate(candidate.program, SEALED_CASES, executor)
        counterexamples = tuple(
            item for item in development_results + candidate_sealed if not item["passed"]
        )
        mistake_record = None
        if counterexamples:
            mistake_record = mistakes.record(
                candidate.program,
                failed_scope="signed_branch_development_or_sealed",
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
                "mistake_id": mistake_record.mistake_id if mistake_record else None,
            }
        )

    gates = (
        {
            "gate_id": "parent_controller_loaded_from_success_room",
            "passed": True,
            "actual": parent_record.operation_id,
            "threshold": "active verified parent",
        },
        {
            "gate_id": "target_names_absent_from_learner_program",
            "passed": names_absent,
            "actual": names_absent,
            "threshold": True,
        },
        {
            "gate_id": "signed_development_rows_exact",
            "passed": winner.exact,
            "actual": winner.fit_mse,
            "threshold": 0,
        },
        {
            "gate_id": "sealed_signed_and_positive_rows_exact",
            "passed": sealed_exact,
            "actual": sum(item["passed"] for item in sealed_results),
            "threshold": len(SEALED_CASES),
        },
        {
            "gate_id": "boundary_rows_exact",
            "passed": adversarial_exact,
            "actual": sum(item["passed"] for item in adversarial_results),
            "threshold": len(ADVERSARIAL_CASES),
        },
        {
            "gate_id": "five_distinct_branch_structures_reported",
            "passed": len(signatures) == 5,
            "actual": len(signatures),
            "threshold": 5,
        },
    )
    verdict = "conditionally_passed" if all(item["passed"] for item in gates) else "failed"
    knowledge_id = ledger.propose(
        winner.program,
        parent_ids=(parent_record.operation_id,),
        provenance={"run_id": run_id, "candidate_id": winner.candidate_id},
        evidence={"development_fit_mse": winner.fit_mse},
    )
    ledger.transition(
        knowledge_id,
        "fit_passed" if winner.exact else "rejected",
        reason="anonymous_signed_development_rows_evaluated",
        evidence={"training_outputs": winner.training_outputs},
    )
    room_record = None
    if winner.exact:
        ledger.transition(
            knowledge_id,
            "verified" if sealed_exact and adversarial_exact else "rejected",
            reason="sealed_signed_and_boundary_rows_evaluated",
            evidence={
                "sealed_results": sealed_results,
                "adversarial_results": adversarial_results,
            },
        )
    if winner.exact and sealed_exact and adversarial_exact:
        ledger.transition(
            knowledge_id,
            "bounded",
            reason="verified_for_signed_first_input_and_positive_second_input",
            evidence={"maximum_registered_steps": executor.maximum_steps},
        )
        operation_id = "BRANCH-" + hashlib.sha256(
            adaptive_branch_program_key(winner.program).encode("utf-8")
        ).hexdigest()[:16]
        room_record = formula_room.record(
            winner.program,
            operation_id=operation_id,
            parent_operation_ids=(parent_record.operation_id,),
            validation_scope="anonymous_signed_first_input_positive_second_input_v0.1",
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
        "report_version": "signed-control-extension-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "匿名负输入控制分支发现实验",
        "evaluator_posthoc_convention": "nonnegative_result_for_positive_second_input",
        "verdict": verdict,
        "knowledge_status": ledger.get(knowledge_id).status,
        "architecture": "verified_parent_controller_plus_synthesized_priority_branch",
        "learner_received": {
            "development_input_rows": [list(row) for row, _ in DEVELOPMENT_CASES],
            "development_output_values": [output for _, output in DEVELOPMENT_CASES],
            "target_concept_name": False,
            "target_formula": False,
            "signed_rule_description": False,
            "sealed_cases_visible_during_search": False,
            "parent_operation_id": parent_record.operation_id,
            "generic_branch_choices": {
                "guard_sensors": ["a_equal", "a_less"],
                "trigger_polarity": [False, True],
                "updates": ["a_state", "a_add", "a_subtract"],
            },
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
                "Before the parent controller, when the integer state is below zero, "
                "add the positive second input and restart the control cycle."
            ),
        },
        "gates": list(gates),
        "success_room_record": room_record.to_dict() if room_record else None,
        "knowledge_id": knowledge_id,
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "The discovered extension defines signed first inputs only when the second input is positive.",
            "Negative or zero second inputs remain outside scope and may require a different convention.",
            "The host still provides generic equality and order sensors.",
            "The extension adds one priority branch; arbitrary nested branching is not yet synthesized.",
        ],
    }
    artifact_path = run_directory / "signed_control_extension_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "signed_control_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "signed_control_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact_path, destination)

    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": verdict,
                "knowledge_status": ledger.get(knowledge_id).status,
                "parent_operation_id": parent_record.operation_id,
                "programs_generated": search.programs_generated,
                "behavior_classes": search.behavior_classes,
                "winner_candidate_id": winner.candidate_id,
                "winner_branch": {
                    "guard": winner.program.branch_guard.to_dict(),
                    "update": winner.program.branch_update.to_dict(),
                },
                "development_exact": winner.exact,
                "sealed_exact": sealed_exact,
                "adversarial_exact": adversarial_exact,
                "success_room_record_id": room_record.room_record_id if room_record else None,
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
