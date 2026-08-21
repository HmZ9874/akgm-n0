"""Probe a user-supplied numeric sequence without target labels or hidden continuation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import KnowledgeLedger, MistakeLibrary
from akgm_n0.learner import (
    ExecutionContext,
    NextValueProgramSearch,
    NumericExecutionError,
    NumericObservation,
    ProgramExecutor,
)


def extrapolate(candidate, values: tuple[float, ...], count: int) -> tuple[float, ...]:
    generated = list(values)
    executor = ProgramExecutor()
    predictions: list[float] = []
    for _ in range(count):
        context = ExecutionContext.create(
            generated,
            index=len(generated) - 1,
            parameters=candidate.parameters,
        )
        prediction = executor.evaluate(candidate.program, context)
        predictions.append(prediction)
        generated.append(prediction)
    return tuple(predictions)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("values", nargs="+", type=float)
    parser.add_argument("--predict", type=int, default=3)
    arguments = parser.parse_args()
    if len(arguments.values) < 5:
        raise ValueError("the registered probe requires at least five values")
    if arguments.predict < 1 or arguments.predict > 16:
        raise ValueError("prediction count must be between one and sixteen")

    values = tuple(arguments.values)
    observation = NumericObservation.create(
        opaque_session_id="USER-SEQUENCE-PROBE",
        sequence_values=values,
        validity_mask=[True] * len(values),
        action_receipt="USER-SUPPLIED-VALUES-ONLY",
    )
    search_report = NextValueProgramSearch(
        maximum_nodes=5,
        top_k=20,
        complexity_weight=1e-3,
    ).search(observation)
    exact = [
        candidate
        for candidate in search_report.top_candidates
        if candidate.train_mse <= 1e-12 and candidate.validation_mse <= 1e-12
    ]
    selected = exact[0] if exact else search_report.top_candidates[0]
    predictions = extrapolate(selected, values, arguments.predict)
    serialized_program = json.dumps(selected.program.to_dict(), sort_keys=True)
    executor = ProgramExecutor()
    full_prefix_cases = []
    for index in range(len(values) - 1):
        observed = values[index + 1]
        try:
            predicted = executor.evaluate(
                selected.program,
                ExecutionContext.create(
                    values,
                    index=index,
                    parameters=selected.parameters,
                ),
            )
            passed: bool | None = predicted == observed
            unavailable_reason = None
        except NumericExecutionError as exc:
            predicted = None
            passed = None
            unavailable_reason = str(exc)
        full_prefix_cases.append(
            {
                "index": index,
                "current_value": values[index],
                "predicted_value": predicted,
                "observed_value": observed,
                "passed": passed,
                "unavailable_reason": unavailable_reason,
            }
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-user-sequence-probe-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    knowledge_id = ledger.propose(
        selected.program,
        parent_ids=tuple(
            sorted({node["op"] for node in walk_ast(selected.program.to_dict())})
        ),
        provenance={
            "run_id": run_id,
            "source": "user_supplied_numeric_values",
            "candidate_id": selected.candidate_id,
        },
        evidence={"search_candidate": selected.to_dict()},
    )
    if exact:
        ledger.transition(
            knowledge_id,
            "fit_passed",
            reason="all_available_internal_examples_exact",
            evidence={
                "train_mse": selected.train_mse,
                "validation_mse": selected.validation_mse,
            },
        )
    failed_prefix_cases = [
        item for item in full_prefix_cases if item["passed"] is False
    ]
    mistake_record = None
    if not exact and failed_prefix_cases:
        ledger.transition(
            knowledge_id,
            "rejected",
            reason="candidate_failed_supplied_prefix_transitions",
            evidence={"counterexamples": failed_prefix_cases},
        )
        condition_key = "user-sequence-" + hashlib.sha256(
            json.dumps(values, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:16]
        mistake_library = MistakeLibrary(
            PROJECT_ROOT / "artifacts" / "mistakes" / "mistake_library.jsonl"
        )
        mistake_record = mistake_library.record(
            selected.program,
            objective_id=NextValueProgramSearch.OBJECTIVE_ID,
            failed_scope="user_supplied_prefix",
            condition_key=condition_key,
            counterexamples=tuple(failed_prefix_cases),
            source_candidate_id=selected.candidate_id,
        )

    report = {
        "report_version": "user-sequence-probe-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "claim": "hypothesis_from_user_supplied_prefix_only",
        "knowledge_status": ledger.get(knowledge_id).status,
        "learner_received": {
            "sequence_values": list(values),
            "natural_language_label": False,
            "target_formula": False,
            "future_values": False,
            "available_operations": [
                "p_read_offset",
                "p_add",
                "p_subtract",
                "p_scalar_parameter",
            ],
        },
        "search": {
            **search_report.to_dict(),
            "exact_candidate_count_in_top_k": len(exact),
            "selected_candidate": selected.to_dict(),
        },
        "candidate_extrapolation": {
            "predicted_values": list(predictions),
            "verified_against_unseen_observations": False,
        },
        "full_supplied_prefix_check": {
            "transition_count": len(full_prefix_cases),
            "passed_transition_count": sum(
                item["passed"] is True for item in full_prefix_cases
            ),
            "evaluated_transition_count": sum(
                item["passed"] is not None for item in full_prefix_cases
            ),
            "all_evaluated_passed": all(
                item["passed"] is not False for item in full_prefix_cases
            ),
            "all_transitions_evaluable": all(
                item["passed"] is not None for item in full_prefix_cases
            ),
            "case_results": full_prefix_cases,
        },
        "structural_observation": {
            "unregistered_multiply_node_present": "p_multiply" in serialized_program,
            "unregistered_divide_node_present": "p_divide" in serialized_program,
            "same_current_value_read_count": serialized_program.count(
                '"offset": 0'
            ),
        },
        "post_hoc_interpretation": {
            "assigned_after_search": True,
            "statement": "The selected program adds the current value to itself.",
            "common_human_sequence_label": "doubling geometric sequence",
        },
        "knowledge_id": knowledge_id,
        "mistake_record": (
            mistake_record.to_dict() if mistake_record is not None else None
        ),
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "Only five supplied values were available, yielding three internal next-value examples.",
            "The predicted continuation has not been checked against a withheld user-supplied value.",
            "Many longer or more complex rules can agree with a finite prefix and diverge later.",
            "The result is an executable hypothesis, not a verified general law.",
        ],
    }
    artifact_path = run_directory / "sequence_probe_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    latest_path = PROJECT_ROOT / "reports" / "data" / "sequence_probe_latest.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact_path, latest_path)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "knowledge_status": ledger.get(knowledge_id).status,
                "mistake_id": (
                    mistake_record.mistake_id if mistake_record is not None else None
                ),
                "input_values": list(values),
                "selected_candidate": selected.to_dict(),
                "predicted_values": list(predictions),
                "full_prefix_transitions_passed": sum(
                    item["passed"] is True for item in full_prefix_cases
                ),
                "full_prefix_transitions_evaluated": sum(
                    item["passed"] is not None for item in full_prefix_cases
                ),
                "full_prefix_transition_count": len(full_prefix_cases),
                "prediction_verified": False,
                "artifact_path": artifact_path.relative_to(PROJECT_ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def walk_ast(node: dict):
    yield node
    for child in node.get("args", []):
        yield from walk_ast(child)


if __name__ == "__main__":
    raise SystemExit(main())
