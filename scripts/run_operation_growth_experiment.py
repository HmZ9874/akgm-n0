"""Run the isolated bounded-iteration operation-growth experiment."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import HiddenIntegerGridEnvironment, KnowledgeLedger
from akgm_n0.learner import IterationExecutor, IterationProgramSearch


SECRET = b"local-operation-growth-experiment-v0.1"


def main() -> int:
    development_rows = (
        (0, 0),
        (0, 3),
        (1, 0),
        (1, 1),
        (2, 3),
        (3, 2),
        (4, 1),
        (-2, 3),
        (5, 4),
    )
    blind_rows = (
        (7, 5),
        (-4, 6),
        (11, 0),
        (2, 9),
        (9, 2),
        (-3, 8),
    )
    development = HiddenIntegerGridEnvironment(
        development_rows, seed=104729, secret=SECRET
    ).observe()
    blind = HiddenIntegerGridEnvironment(
        blind_rows, seed=130363, secret=SECRET
    ).observe()

    search_report = IterationProgramSearch(top_k=20).search(development)
    exact = [item for item in search_report.top_candidates if item.fit_error == 0.0]
    if not exact:
        raise RuntimeError("development search produced no exact candidate")
    selected = exact[0]
    executor = IterationExecutor()
    predictions = tuple(
        executor.evaluate(selected.program, row) for row in blind.input_rows
    )
    case_results = [
        {
            "case_index": index,
            "input_row": list(row),
            "predicted_value": prediction,
            "observed_value": observed,
            "passed": prediction == observed,
        }
        for index, (row, prediction, observed) in enumerate(
            zip(blind.input_rows, predictions, blind.output_values, strict=True)
        )
    ]
    blind_passed = all(item["passed"] for item in case_results)
    serialized_program = json.dumps(selected.program.to_dict(), sort_keys=True)
    forbidden_runtime_nodes_absent = all(
        token not in serialized_program for token in ("p_multiply", "p_divide")
    )
    gates = [
        {
            "gate_id": "development_exact_fit",
            "passed": selected.fit_error == 0.0,
            "actual": selected.fit_error,
            "threshold": 0.0,
        },
        {
            "gate_id": "blind_unseen_rows_exact",
            "passed": blind_passed,
            "actual": sum(item["passed"] for item in case_results),
            "threshold": len(case_results),
        },
        {
            "gate_id": "unregistered_nodes_absent",
            "passed": forbidden_runtime_nodes_absent,
            "actual": forbidden_runtime_nodes_absent,
            "threshold": True,
        },
        {
            "gate_id": "negative_control_values",
            "passed": None,
            "actual": None,
            "threshold": True,
        },
        {
            "gate_id": "non_integer_inputs",
            "passed": None,
            "actual": None,
            "threshold": True,
        },
    ]
    completed = [gate for gate in gates if gate["passed"] is not None]
    verdict = "conditionally_passed" if all(gate["passed"] for gate in completed) else "failed"

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-operation-growth-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    knowledge_id = ledger.propose(
        selected.program,
        parent_ids=("p_input", "p_accumulator", "p_add", "p_subtract", "p_iterate"),
        provenance={
            "run_id": run_id,
            "search_version": "anonymous-transition-search-v0.1",
            "candidate_id": selected.candidate_id,
        },
        evidence={"development_fit_error": selected.fit_error},
    )
    ledger.transition(
        knowledge_id,
        "fit_passed",
        reason="anonymous_development_rows_exact",
        evidence={"valid_row_count": search_report.valid_row_count},
    )
    if blind_passed:
        ledger.transition(
            knowledge_id,
            "verified",
            reason="sealed_unseen_rows_exact",
            evidence={"case_count": len(case_results)},
        )
        ledger.transition(
            knowledge_id,
            "bounded",
            reason="registered_non_negative_control_domain_only",
            evidence={
                "maximum_control_steps": executor.maximum_control_steps,
                "pending_gates": [
                    gate["gate_id"] for gate in gates if gate["passed"] is None
                ],
            },
        )
    else:
        ledger.transition(
            knowledge_id,
            "rejected",
            reason="sealed_unseen_rows_failed",
            evidence={
                "failed_cases": [
                    item for item in case_results if not item["passed"]
                ]
            },
        )

    report = {
        "report_version": "operation-growth-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "匿名运算生长实验：有限重复执行",
        "verdict": verdict,
        "knowledge_status": ledger.get(knowledge_id).status,
        "claim_scope": "integer_value_and_non_negative_integer_control_up_to_64",
        "architecture": "enumerative_state_transition_search_not_transformer",
        "learner_received": {
            "natural_language": False,
            "human_formula": False,
            "human_operation_name": False,
            "anonymous_numeric_rows": True,
            "available_nodes": [
                "p_input",
                "p_accumulator",
                "p_add",
                "p_subtract",
                "p_iterate",
            ],
            "supplied_computational_prior": "bounded_state_transition_repetition",
        },
        "development": {
            "row_count": len(development_rows),
            "programs_generated": search_report.programs_generated,
            "valid_row_count": search_report.valid_row_count,
            "selected_candidate": selected.to_dict(),
        },
        "blind_verification": {
            "case_count": len(case_results),
            "passed_case_count": sum(item["passed"] for item in case_results),
            "failed_case_count": sum(not item["passed"] for item in case_results),
            "case_results": case_results,
        },
        "post_hoc_evaluator_interpretation": {
            "assigned_after_blind_verification": True,
            "statement": "The learned transition repeatedly accumulates one input, with the other input controlling the bounded repetition count.",
            "equivalent_on_registered_domain": "integer multiplication",
        },
        "gates": gates,
        "knowledge_id": knowledge_id,
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "The repetition mechanism itself is a supplied generic computational prior.",
            "The control input is restricted to integers from 0 through 64.",
            "The current result does not define behavior for negative control values or non-integer inputs.",
            "This demonstrates an independently assembled executable procedure, not a claim of new mathematics.",
        ],
    }
    artifact_path = run_directory / "operation_growth_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    latest_path = PROJECT_ROOT / "reports" / "data" / "operation_growth_latest.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact_path, latest_path)
    dashboard_path = PROJECT_ROOT / "dashboard" / "data" / "operation_growth_latest.json"
    if dashboard_path.parent.parent.exists():
        dashboard_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact_path, dashboard_path)

    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": verdict,
                "knowledge_status": ledger.get(knowledge_id).status,
                "candidate_id": selected.candidate_id,
                "programs_generated": search_report.programs_generated,
                "blind_passed": sum(item["passed"] for item in case_results),
                "blind_total": len(case_results),
                "artifact_path": artifact_path.relative_to(PROJECT_ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if blind_passed and forbidden_runtime_nodes_absent else 1


if __name__ == "__main__":
    raise SystemExit(main())
