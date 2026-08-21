"""Discover a conditional adapter for negative second inputs."""

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
    AdaptiveBranchProgram,
    InputAdapterExecutor,
    InputAdapterSearch,
    NumericTableObservation,
    input_adapter_program_key,
)


DEVELOPMENT_CASES = (
    ((7, -3), 1),
    ((-7, -3), 2),
    ((8, -3), 2),
    ((-8, -3), 1),
    ((11, -4), 3),
    ((-12, -5), 3),
    ((17, -5), 2),
    ((-20, -6), 4),
    ((7, 3), 1),
    ((-7, 3), 2),
)
SEALED_CASES = (
    ((29, -6), 5),
    ((-29, -6), 1),
    ((31, -8), 7),
    ((-31, -8), 1),
    ((44, -9), 8),
    ((-44, -9), 1),
    ((2, -9), 2),
    ((-2, -9), 7),
)
ADVERSARIAL_CASES = (
    ((255, -32), 31),
    ((-255, -32), 1),
    ((256, -32), 0),
    ((-256, -32), 0),
    ((-1, -1), 0),
    ((0, -7), 0),
    ((-29, 6), 1),
)


def make_observation(cases) -> NumericTableObservation:
    return NumericTableObservation.create(
        opaque_session_id="anonymous-second-input-adapter",
        input_rows=tuple(row for row, _ in cases),
        output_values=tuple(output for _, output in cases),
        validity_mask=(True,) * len(cases),
        action_receipt="anonymous_mixed_sign_second_inputs",
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
                    "adapted_inputs": list(execution.adapted_inputs),
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
                    "adapted_inputs": None,
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
            == "anonymous_priority_branch_control_v0.1"
        ),
        None,
    )
    if parent_record is None:
        raise RuntimeError("signed-first-input parent controller is unavailable")
    parent_program = AdaptiveBranchProgram.from_dict(parent_record.definition)
    search = InputAdapterSearch(
        parent_program,
        parent_operation_id=parent_record.operation_id,
        top_k=100,
    ).search(make_observation(DEVELOPMENT_CASES))
    winner = search.top_candidates[0]
    executor = InputAdapterExecutor()
    sealed_results = evaluate(winner.program, SEALED_CASES, executor)
    adversarial_results = evaluate(winner.program, ADVERSARIAL_CASES, executor)
    sealed_exact = all(item["passed"] for item in sealed_results)
    adversarial_exact = all(item["passed"] for item in adversarial_results)

    selected = []
    logic_signatures = set()
    for candidate in search.top_candidates:
        if candidate.logic_signature in logic_signatures:
            continue
        selected.append((candidate, False))
        logic_signatures.add(candidate.logic_signature)
        if len(selected) == 5:
            break
    if len(selected) < 5:
        for failure in search.failed_candidates:
            if failure.logic_signature in logic_signatures:
                continue
            selected.append((failure, True))
            logic_signatures.add(failure.logic_signature)
            if len(selected) == 5:
                break
    if len(selected) < 5:
        raise RuntimeError("adapter search produced fewer than five logic structures")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-second-input-adapter-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    mistakes = AdaptiveMistakeLibrary(
        PROJECT_ROOT / "artifacts" / "mistakes" / "adaptive_mistakes.jsonl"
    )
    condition_key = "anonymous-second-input-adapter-" + hashlib.sha256(
        json.dumps(DEVELOPMENT_CASES, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    feedback = []
    for rank, (candidate, search_failure) in enumerate(selected, start=1):
        development_results = evaluate(candidate.program, DEVELOPMENT_CASES, executor)
        candidate_sealed = evaluate(candidate.program, SEALED_CASES, executor)
        counterexamples = tuple(
            item for item in development_results + candidate_sealed if not item["passed"]
        )
        mistake_record = None
        if counterexamples:
            mistake_record = mistakes.record(
                candidate.program,
                failed_scope="second_input_adapter_development_or_sealed",
                condition_key=condition_key,
                counterexamples=counterexamples,
                source_candidate_id=candidate.candidate_id,
            )
        candidate_dict = candidate.to_dict()
        feedback.append(
            {
                "rank": rank,
                **candidate_dict,
                "search_failure": search_failure,
                "development_results": list(development_results),
                "sealed_results": list(candidate_sealed),
                "sealed_exact": all(item["passed"] for item in candidate_sealed),
                "disposition": (
                    "success_room"
                    if candidate.candidate_id == winner.candidate_id
                    else (
                        "equivalent_success_not_admitted"
                        if not counterexamples
                        else "mistake_library"
                    )
                ),
                "mistake_id": mistake_record.mistake_id if mistake_record else None,
            }
        )

    serialized = json.dumps(winner.program.to_dict(), sort_keys=True).lower()
    names_absent = all(
        token not in serialized
        for token in ("absolute", "negative", "remainder", "modulo", "divide")
    )
    gates = (
        {
            "gate_id": "verified_parent_loaded",
            "passed": True,
            "actual": parent_record.operation_id,
            "threshold": "active verified parent",
        },
        {
            "gate_id": "target_names_absent",
            "passed": names_absent,
            "actual": names_absent,
            "threshold": True,
        },
        {
            "gate_id": "mixed_sign_development_exact",
            "passed": winner.exact,
            "actual": winner.fit_mse,
            "threshold": 0,
        },
        {
            "gate_id": "sealed_mixed_sign_exact",
            "passed": sealed_exact,
            "actual": sum(item["passed"] for item in sealed_results),
            "threshold": len(SEALED_CASES),
        },
        {
            "gate_id": "boundary_mixed_sign_exact",
            "passed": adversarial_exact,
            "actual": sum(item["passed"] for item in adversarial_results),
            "threshold": len(ADVERSARIAL_CASES),
        },
        {
            "gate_id": "five_distinct_adapter_structures_reported",
            "passed": len(logic_signatures) == 5,
            "actual": len(logic_signatures),
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
        reason="mixed_sign_second_input_development_evaluated",
        evidence={"adapted_second_inputs": winner.adapted_second_inputs},
    )
    room_record = None
    if winner.exact:
        ledger.transition(
            knowledge_id,
            "verified" if sealed_exact and adversarial_exact else "rejected",
            reason="sealed_and_boundary_second_input_sign_cases_evaluated",
            evidence={
                "sealed_results": sealed_results,
                "adversarial_results": adversarial_results,
            },
        )
    if winner.exact and sealed_exact and adversarial_exact:
        ledger.transition(
            knowledge_id,
            "bounded",
            reason="verified_for_nonzero_signed_second_inputs_under_registered_convention",
            evidence={"zero_second_input": "outside_scope"},
        )
        operation_id = "ADAPT-" + hashlib.sha256(
            input_adapter_program_key(winner.program).encode("utf-8")
        ).hexdigest()[:16]
        room_record = formula_room.record(
            winner.program,
            operation_id=operation_id,
            parent_operation_ids=(parent_record.operation_id,),
            validation_scope="anonymous_nonzero_signed_second_input_adapter_v0.1",
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
        "report_version": "second-input-sign-adapter-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "匿名第二输入符号适配发现实验",
        "evaluator_posthoc_convention": "nonnegative_result_using_positive_magnitude_of_nonzero_second_input",
        "verdict": verdict,
        "knowledge_status": ledger.get(knowledge_id).status,
        "architecture": "verified_signed_first_input_parent_plus_conditional_second_input_adapter",
        "learner_received": {
            "development_input_rows": [list(row) for row, _ in DEVELOPMENT_CASES],
            "development_output_values": [output for _, output in DEVELOPMENT_CASES],
            "target_concept_name": False,
            "target_formula": False,
            "sign_rule_description": False,
            "sealed_cases_visible_during_search": False,
            "parent_operation_id": parent_record.operation_id,
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
                "When the second input is a negative integer, replace it with zero minus itself; "
                "otherwise preserve it, then call the verified parent controller."
            ),
        },
        "gates": list(gates),
        "success_room_record": room_record.to_dict() if room_record else None,
        "knowledge_id": knowledge_id,
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "The adapter covers nonzero signed second inputs under one evaluator convention.",
            "A zero second input remains undefined and is rejected rather than assigned an arbitrary output.",
            "The host still supplies generic comparison sensors and conditional adapter execution.",
            "The learned adapter normalizes one input before calling its verified parent; it does not synthesize arbitrary recursive adapters.",
        ],
    }
    artifact_path = run_directory / "second_input_sign_adapter_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "second_input_adapter_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "second_input_adapter_latest.json",
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
                "programs_executed": search.programs_executed,
                "behavior_classes": search.behavior_classes,
                "winner_candidate_id": winner.candidate_id,
                "winner_guard": winner.program.adapter_guard.to_dict(),
                "winner_adapter": winner.program.adapted_second_input.to_dict(),
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
