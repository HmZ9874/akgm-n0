"""Run an anonymous multi-stage residual-memory discovery experiment."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import AdaptiveMistakeLibrary, FormulaSuccessRoom, KnowledgeLedger
from akgm_n0.learner import (
    NumericTableObservation,
    RadixMemoryExecutor,
    RadixMemorySearch,
    TraceMemoryProgram,
    radix_memory_program_key,
)


DEVELOPMENT_CASES = (
    ((1, 10), "0.1"),
    ((1, 100), "0.01"),
    ((1, 1000), "0.001"),
    ((1, 2), "0.5"),
    ((3, 4), "0.75"),
    ((1, 8), "0.125"),
    ((7, 20), "0.35"),
    ((9, 25), "0.36"),
    ((13, 40), "0.325"),
    ((-1, 8), "-0.125"),
    ((-7, 20), "-0.35"),
    ((23, -10), "2.3"),
)
SEALED_CASES = (
    ((17, 8), "2.125"),
    ((-17, -8), "-2.125"),
    ((19, 20), "0.95"),
    ((-19, 20), "-0.95"),
    ((37, 40), "0.925"),
    ((99, 100), "0.99"),
    ((1, 125), "0.008"),
    ((-1, 125), "-0.008"),
    ((123, 100), "1.23"),
)
ADVERSARIAL_CASES = (
    ((999, 1000), "0.999"),
    ((-999, 1000), "-0.999"),
    ((1001, 1000), "1.001"),
    ((-1001, -1000), "-1.001"),
    ((255, 8), "31.875"),
    ((-255, 8), "-31.875"),
    ((5, 2), "2.5"),
    ((0, 125), "0"),
)


def make_observation(cases) -> NumericTableObservation:
    return NumericTableObservation.create(
        opaque_session_id="anonymous-multistage-residual-output",
        input_rows=tuple(row for row, _ in cases),
        output_values=tuple(float(output) for _, output in cases),
        validity_mask=(True,) * len(cases),
        action_receipt="anonymous-noninteger-output-rows",
    )


def evaluate(program, cases, executor):
    results = []
    for row, observed_text in cases:
        observed = Decimal(observed_text)
        try:
            execution = executor.execute(program, row)
            predicted = execution.output_decimal
            results.append(
                {
                    "input": list(row),
                    "predicted": str(predicted),
                    "observed": observed_text,
                    "absolute_error": str(abs(predicted - observed)),
                    "integer_memory": execution.integer_memory,
                    "initial_residual": str(execution.initial_residual),
                    "adapted_inputs": list(execution.adapted_inputs),
                    "stages": [item.to_dict() for item in execution.stages],
                    "passed": predicted == observed,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "input": list(row),
                    "predicted": None,
                    "observed": observed_text,
                    "absolute_error": None,
                    "integer_memory": None,
                    "initial_residual": None,
                    "adapted_inputs": None,
                    "stages": [],
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
            == "anonymous_dual_state_trace_memory_v0.1"
        ),
        None,
    )
    if parent_record is None:
        raise RuntimeError("verified trace-memory parent is unavailable")
    parent_program = TraceMemoryProgram.from_dict(parent_record.definition)
    search = RadixMemorySearch(
        parent_program,
        parent_operation_id=parent_record.operation_id,
        top_k=500,
    ).search(make_observation(DEVELOPMENT_CASES))
    winner = search.top_candidates[0]
    executor = RadixMemoryExecutor()
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
        raise RuntimeError("multistage residual search produced fewer than five structures")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-multistage-residual-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    mistakes = AdaptiveMistakeLibrary(
        PROJECT_ROOT / "artifacts" / "mistakes" / "adaptive_mistakes.jsonl"
    )
    condition_key = "anonymous-multistage-residual-" + hashlib.sha256(
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
                failed_scope="multistage_residual_development_or_sealed",
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
        for token in ("decimal", "multiply", "divide", "quotient", "fraction", "base_10")
    )
    weights = tuple(Decimal(item) for item in winner.program.stage_weights)
    coherent = all(
        sum((weights[index + 1] for _ in range(winner.program.cycle_width)), Decimal(0))
        == weights[index]
        for index in range(len(weights) - 1)
    )
    gates = (
        {
            "gate_id": "verified_trace_memory_parent_loaded",
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
            "gate_id": "internal_stage_weights_are_coherent",
            "passed": coherent and winner.coherence_error == 0,
            "actual": {
                "cycle_width": winner.program.cycle_width,
                "stage_weights": list(winner.program.stage_weights),
            },
            "threshold": "each later weight repeated cycle_width times equals prior weight",
        },
        {
            "gate_id": "sealed_noninteger_outputs_exact",
            "passed": sealed_exact,
            "actual": sum(item["passed"] for item in sealed_results),
            "threshold": len(SEALED_CASES),
        },
        {
            "gate_id": "adversarial_thousandths_exact",
            "passed": adversarial_exact,
            "actual": sum(item["passed"] for item in adversarial_results),
            "threshold": len(ADVERSARIAL_CASES),
        },
        {
            "gate_id": "five_distinct_program_structures_reported",
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
        reason="anonymous_noninteger_output_development_evaluated",
        evidence={"training_outputs": winner.training_outputs},
    )
    room_record = None
    if winner.exact:
        ledger.transition(
            knowledge_id,
            "verified" if sealed_exact and adversarial_exact else "rejected",
            reason="sealed_and_adversarial_multistage_residual_cases_evaluated",
            evidence={
                "sealed_results": sealed_results,
                "adversarial_results": adversarial_results,
            },
        )
    if winner.exact and sealed_exact and adversarial_exact:
        ledger.transition(
            knowledge_id,
            "bounded",
            reason="verified_for_three_anonymous_output_stages",
            evidence={"maximum_stage_count": len(winner.program.stage_weights)},
        )
        operation_id = "STAGE-" + hashlib.sha256(
            radix_memory_program_key(winner.program).encode("utf-8")
        ).hexdigest()[:16]
        room_record = formula_room.record(
            winner.program,
            operation_id=operation_id,
            parent_operation_ids=(parent_record.operation_id,),
            validation_scope="anonymous_noninteger_output_three_stage_v0.1",
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
        "report_version": "multistage-residual-discovery-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "匿名非整数输出多级余量发现实验",
        "verdict": verdict,
        "knowledge_status": ledger.get(knowledge_id).status,
        "architecture": "verified_trace_parent_plus_candidate_multistage_residual_memory",
        "learner_received": {
            "development_input_rows": [list(row) for row, _ in DEVELOPMENT_CASES],
            "development_output_values": [output for _, output in DEVELOPMENT_CASES],
            "cycle_width_candidates": list(search.cycle_width_candidates),
            "evidence_weights": list(search.evidence_weights),
            "target_concept_name": False,
            "target_formula": False,
            "named_radix": False,
            "multiply_operation": False,
            "divide_operation": False,
            "sealed_cases_visible_during_search": False,
            "parent_operation_id": parent_record.operation_id,
        },
        "search": {
            "programs_generated": search.programs_generated,
            "programs_executed": search.programs_executed,
            "programs_rejected": search.programs_rejected,
            "behavior_classes": search.behavior_classes,
        },
        "five_candidate_feedback": feedback,
        "winner": {
            **winner.to_dict(),
            "development_results": list(development_results),
            "sealed_results": list(sealed_results),
            "adversarial_results": list(adversarial_results),
            "posthoc_human_interpretation": (
                "The candidate selected a cycle width of ten and coherent stage weights "
                "0.1, 0.01, and 0.001, then generated successive output positions through "
                "repeated addition and verified parent calls."
            ),
        },
        "gates": list(gates),
        "success_room_record": room_record.to_dict() if room_record else None,
        "success_room_active_count": len(formula_room.records),
        "knowledge_id": knowledge_id,
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "The result is bounded to at most three generated output stages.",
            "The registered evidence covers terminating noninteger outputs, not recurring expansions.",
            "Inputs remain integer pairs and the second input must be nonzero.",
            "The host enumerates anonymous cycle widths 2 through 12 and exposes observed output magnitudes as candidate weights.",
            "The evaluator uses exact Decimal arithmetic after the learner selects its program.",
        ],
    }
    artifact_path = run_directory / "multistage_residual_discovery_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "radix_memory_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "radix_memory_latest.json",
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
                "winner_cycle_width": winner.program.cycle_width,
                "winner_stage_weights": list(winner.program.stage_weights),
                "coherence_error": winner.coherence_error,
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
