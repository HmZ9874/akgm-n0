"""Discover a new output computation by attaching memory to parent transitions."""

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
    InputAdapterProgram,
    NumericTableObservation,
    TraceMemoryExecutor,
    TraceMemorySearch,
    trace_memory_program_key,
)


DEVELOPMENT_CASES = (
    ((7, 3), 2),
    ((-7, 3), -3),
    ((8, -3), 2),
    ((-8, -3), -3),
    ((11, 4), 2),
    ((-12, -5), -3),
    ((17, -5), 3),
    ((-20, -6), -4),
    ((2, 9), 0),
    ((0, -7), 0),
)
SEALED_CASES = (
    ((29, -6), 4),
    ((-29, -6), -5),
    ((31, 8), 3),
    ((-31, -8), -4),
    ((44, -9), 4),
    ((-44, 9), -5),
    ((63, -7), 9),
    ((-63, -7), -9),
)
ADVERSARIAL_CASES = (
    ((255, -32), 7),
    ((-255, -32), -8),
    ((256, -32), 8),
    ((-256, -32), -8),
    ((-1, -1), -1),
    ((1, -1), 1),
    ((0, 7), 0),
)


def make_observation(cases) -> NumericTableObservation:
    return NumericTableObservation.create(
        opaque_session_id="anonymous-trace-memory-output",
        input_rows=tuple(row for row, _ in cases),
        output_values=tuple(output for _, output in cases),
        validity_mask=(True,) * len(cases),
        action_receipt="anonymous_transition_memory_rows",
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
                    "parent_output": execution.parent_output_value,
                    "final_memory": execution.final_memory,
                    "priority_transitions": execution.priority_transition_count,
                    "base_transitions": execution.base_transition_count,
                    "transition_count": execution.transition_count,
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
                    "parent_output": None,
                    "final_memory": None,
                    "priority_transitions": None,
                    "base_transitions": None,
                    "transition_count": None,
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
            == "anonymous_conditional_input_adapter_v0.1"
        ),
        None,
    )
    if parent_record is None:
        raise RuntimeError("verified input adapter parent is unavailable")
    parent_program = InputAdapterProgram.from_dict(parent_record.definition)
    search = TraceMemorySearch(
        parent_program,
        parent_operation_id=parent_record.operation_id,
        top_k=500,
    ).search(make_observation(DEVELOPMENT_CASES))
    winner = search.top_candidates[0]
    executor = TraceMemoryExecutor()
    development_results = evaluate(winner.program, DEVELOPMENT_CASES, executor)
    sealed_results = evaluate(winner.program, SEALED_CASES, executor)
    adversarial_results = evaluate(winner.program, ADVERSARIAL_CASES, executor)
    sealed_exact = all(item["passed"] for item in sealed_results)
    adversarial_exact = all(item["passed"] for item in adversarial_results)

    selected = [winner]
    logic_signatures = {winner.logic_signature}
    exact_equivalent = next(
        (
            candidate
            for candidate in search.top_candidates[1:]
            if candidate.exact and candidate.logic_signature not in logic_signatures
        ),
        None,
    )
    if exact_equivalent is not None:
        selected.append(exact_equivalent)
        logic_signatures.add(exact_equivalent.logic_signature)
    for candidate in search.top_candidates:
        if candidate.exact or candidate.logic_signature in logic_signatures:
            continue
        selected.append(candidate)
        logic_signatures.add(candidate.logic_signature)
        if len(selected) == 5:
            break
    if len(selected) < 5:
        for candidate in search.top_candidates:
            if candidate.logic_signature in logic_signatures:
                continue
            selected.append(candidate)
            logic_signatures.add(candidate.logic_signature)
            if len(selected) == 5:
                break
    if len(selected) < 5:
        raise RuntimeError("trace memory search produced fewer than five logic structures")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-trace-memory-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    mistakes = AdaptiveMistakeLibrary(
        PROJECT_ROOT / "artifacts" / "mistakes" / "adaptive_mistakes.jsonl"
    )
    condition_key = "anonymous-trace-memory-" + hashlib.sha256(
        json.dumps(DEVELOPMENT_CASES, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    feedback = []
    for rank, candidate in enumerate(selected, start=1):
        candidate_development = evaluate(candidate.program, DEVELOPMENT_CASES, executor)
        candidate_sealed = evaluate(candidate.program, SEALED_CASES, executor)
        counterexamples = tuple(
            item for item in candidate_development + candidate_sealed if not item["passed"]
        )
        mistake_record = None
        if counterexamples:
            mistake_record = mistakes.record(
                candidate.program,
                failed_scope="trace_memory_development_or_sealed",
                condition_key=condition_key,
                counterexamples=counterexamples,
                source_candidate_id=candidate.candidate_id,
            )
        feedback.append(
            {
                "rank": rank,
                **candidate.to_dict(),
                "development_results": list(candidate_development),
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
    target_names_absent = all(
        token not in serialized
        for token in ("multiply", "divide", "quotient", "remainder", "modulo")
    )
    gates = (
        {
            "gate_id": "verified_parent_loaded",
            "passed": True,
            "actual": parent_record.operation_id,
            "threshold": "active verified parent",
        },
        {
            "gate_id": "target_names_and_operations_absent",
            "passed": target_names_absent,
            "actual": target_names_absent,
            "threshold": True,
        },
        {
            "gate_id": "development_exact",
            "passed": winner.exact,
            "actual": winner.fit_mse,
            "threshold": 0,
        },
        {
            "gate_id": "sealed_exact",
            "passed": sealed_exact,
            "actual": sum(item["passed"] for item in sealed_results),
            "threshold": len(SEALED_CASES),
        },
        {
            "gate_id": "adversarial_exact",
            "passed": adversarial_exact,
            "actual": sum(item["passed"] for item in adversarial_results),
            "threshold": len(ADVERSARIAL_CASES),
        },
        {
            "gate_id": "five_distinct_memory_structures_reported",
            "passed": len(logic_signatures) == 5,
            "actual": len(logic_signatures),
            "threshold": 5,
        },
        {
            "gate_id": "second_memory_is_executable_not_host_step_read",
            "passed": winner.program.output.op == "a_state",
            "actual": winner.program.output.op,
            "threshold": "a_state",
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
        reason="anonymous_trace_memory_development_evaluated",
        evidence={"training_outputs": winner.training_outputs},
    )
    room_record = None
    if winner.exact:
        ledger.transition(
            knowledge_id,
            "verified" if sealed_exact and adversarial_exact else "rejected",
            reason="sealed_and_adversarial_trace_memory_cases_evaluated",
            evidence={
                "sealed_results": sealed_results,
                "adversarial_results": adversarial_results,
            },
        )
    if winner.exact and sealed_exact and adversarial_exact:
        ledger.transition(
            knowledge_id,
            "bounded",
            reason="verified_dual_state_memory_under_registered_integer_scope",
            evidence={"zero_second_input": "outside_scope"},
        )
        operation_id = "TRACE-" + hashlib.sha256(
            trace_memory_program_key(winner.program).encode("utf-8")
        ).hexdigest()[:16]
        room_record = formula_room.record(
            winner.program,
            operation_id=operation_id,
            parent_operation_ids=(parent_record.operation_id,),
            validation_scope="anonymous_signed_integer_trace_memory_v0.1",
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
        "report_version": "trace-memory-discovery-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "匿名转移轨迹第二记忆发现实验",
        "verdict": verdict,
        "knowledge_status": ledger.get(knowledge_id).status,
        "architecture": "verified_parent_plus_candidate_defined_second_memory_cell",
        "learner_received": {
            "development_input_rows": [list(row) for row, _ in DEVELOPMENT_CASES],
            "development_output_values": [output for _, output in DEVELOPMENT_CASES],
            "transition_classes": ["priority_transition", "base_transition"],
            "target_concept_name": False,
            "target_formula": False,
            "multiply_operation": False,
            "divide_operation": False,
            "host_step_count_as_output": False,
            "sealed_cases_visible_during_search": False,
            "parent_operation_id": parent_record.operation_id,
        },
        "search": {
            "programs_generated": search.programs_generated,
            "programs_executed": search.programs_executed,
            "programs_rejected": search.programs_rejected,
            "behavior_classes": search.behavior_classes,
            "evidence_constants": list(search.evidence_constants),
        },
        "five_candidate_feedback": feedback,
        "winner": {
            **winner.to_dict(),
            "development_results": list(development_results),
            "sealed_results": list(sealed_results),
            "adversarial_results": list(adversarial_results),
            "posthoc_human_interpretation": (
                "Initialize a second memory cell at zero. On the parent's priority transition, "
                "change that memory by negative one; on the parent's base transition, change it "
                "by positive one; return the second memory instead of the parent's final state."
            ),
        },
        "gates": list(gates),
        "success_room_record": room_record.to_dict() if room_record else None,
        "success_room_active_count": len(formula_room.records),
        "knowledge_id": knowledge_id,
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "The new memory program is bounded to registered integer inputs with a nonzero second input.",
            "The host exposes two anonymous transition events and supplies the generic second memory substrate.",
            "The candidate creates and updates memory itself; it is not given the host step counter as an output.",
            "The posthoc quotient-like interpretation is an evaluator description, not a learner input.",
        ],
    }
    artifact_path = run_directory / "trace_memory_discovery_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "trace_memory_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "trace_memory_latest.json",
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
                "winner": winner.candidate_id,
                "winner_memory": winner.program.to_dict()["memory"],
                "development_exact": winner.exact,
                "sealed_exact": sealed_exact,
                "adversarial_exact": adversarial_exact,
                "five_feedback_ids": [item["candidate_id"] for item in feedback],
                "success_room_record": room_record.to_dict() if room_record else None,
                "artifact_path": str(artifact_path.relative_to(PROJECT_ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if verdict == "conditionally_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
