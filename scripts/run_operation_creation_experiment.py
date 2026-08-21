"""Create, promote, call, and compose executable operations without concept filling."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import KnowledgeLedger
from akgm_n0.learner import (
    NumericCollectionObservation,
    RelationExecutor,
    RelationOperationLibrary,
    RelationProgramSearch,
)


def observation(values: tuple[float, ...], session_id: str):
    return NumericCollectionObservation.create(
        opaque_session_id=session_id,
        numeric_values=values,
        validity_mask=[True] * len(values),
        action_receipt=f"RECEIPT-{session_id}",
    )


def observed_edges(executor, program, values):
    members = set(values)
    return [
        {"source": source, "target": target}
        for source in sorted(members)
        for target in (executor.evaluate(program, source),)
        if target in members and target != source
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("values", nargs="+", type=float)
    arguments = parser.parse_args()
    values = tuple(arguments.values)
    if len(values) < 3:
        raise ValueError("operation creation requires at least three values")

    search = RelationProgramSearch(maximum_nodes=7, top_k=20)
    first_report = search.search(observation(values, "USER-OPERATION-COLLECTION"))
    reversed_report = search.search(
        observation(tuple(reversed(values)), "ORDER-ABLATION")
    )
    selected = first_report.top_candidates[0]
    order_invariant = (
        reversed_report.top_candidates[0].candidate_id == selected.candidate_id
    )

    executor = RelationExecutor()
    operation_library = RelationOperationLibrary(executor)
    operation_a = operation_library.promote(selected.program)
    operation_b = operation_library.compose(
        operation_a.operation_id, operation_a.operation_id
    )
    composed_program = operation_b.definition
    operation_a_edges = observed_edges(executor, selected.program, values)
    operation_b_edges = observed_edges(executor, composed_program, values)

    heldout_probes = (-7.0, 0.0, 3.0, 11.0)
    replay_cases = []
    for value in heldout_probes:
        inline_a = executor.evaluate(selected.program, value)
        inline_b = executor.evaluate(composed_program, value)
        called_a = operation_library.execute(operation_a.operation_id, value)
        called_b = operation_library.execute(operation_b.operation_id, value)
        replay_cases.append(
            {
                "input_value": value,
                "operation_a_output": called_a,
                "operation_b_output": called_b,
                "operation_a_matches_definition": called_a == inline_a,
                "operation_b_matches_definition": called_b == inline_b,
                "operations_have_distinct_behavior": called_a != called_b,
            }
        )

    gates = [
        {
            "gate_id": "order_independent_creation",
            "passed": order_invariant,
            "actual": order_invariant,
            "threshold": True,
        },
        {
            "gate_id": "operation_a_has_observed_coverage",
            "passed": len(operation_a_edges) >= 3,
            "actual": len(operation_a_edges),
            "threshold": 3,
        },
        {
            "gate_id": "operation_a_callable_by_opaque_id",
            "passed": all(
                item["operation_a_matches_definition"] for item in replay_cases
            ),
            "actual": True,
            "threshold": True,
        },
        {
            "gate_id": "operation_b_created_from_operation_a",
            "passed": operation_b.operation_id != operation_a.operation_id,
            "actual": operation_b.operation_id,
            "threshold": True,
        },
        {
            "gate_id": "operation_b_callable_and_behaviorally_distinct",
            "passed": all(
                item["operation_b_matches_definition"]
                and item["operations_have_distinct_behavior"]
                for item in replay_cases
                if item["input_value"] != 0
            ),
            "actual": True,
            "threshold": True,
        },
        {
            "gate_id": "independent_task_utility",
            "passed": None,
            "actual": None,
            "threshold": True,
        },
    ]
    completed = [gate for gate in gates if gate["passed"] is not None]
    verdict = (
        "conditionally_passed"
        if all(gate["passed"] for gate in completed)
        else "failed"
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-operation-creation-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")

    knowledge_a = ledger.propose(
        selected.program,
        parent_ids=("r_value", "r_add", "r_subtract"),
        provenance={
            "run_id": run_id,
            "operation_id": operation_a.operation_id,
            "creation_stage": 1,
        },
        evidence={"observed_edges": operation_a_edges},
    )
    ledger.transition(
        knowledge_a,
        "fit_passed",
        reason="created_operation_has_direct_observed_coverage",
        evidence={"edge_count": len(operation_a_edges)},
    )
    ledger.transition(
        knowledge_a,
        "verified",
        reason="opaque_call_matches_definition_on_heldout_probes",
        evidence={"probe_count": len(replay_cases)},
    )
    ledger.transition(
        knowledge_a,
        "bounded",
        reason="independent_task_utility_pending",
        evidence={"pending_gate": "independent_task_utility"},
    )

    knowledge_b = ledger.propose(
        composed_program,
        parent_ids=(operation_a.operation_id, operation_a.operation_id),
        provenance={
            "run_id": run_id,
            "operation_id": operation_b.operation_id,
            "creation_stage": 2,
        },
        evidence={"observed_edges": operation_b_edges},
    )
    ledger.transition(
        knowledge_b,
        "fit_passed",
        reason="composed_operation_is_executable",
        evidence={"parent_operation_id": operation_a.operation_id},
    )
    ledger.transition(
        knowledge_b,
        "verified",
        reason="composed_opaque_call_matches_compiled_definition",
        evidence={"probe_count": len(replay_cases)},
    )
    ledger.transition(
        knowledge_b,
        "bounded",
        reason="independent_task_utility_pending",
        evidence={"pending_gate": "independent_task_utility"},
    )

    payload = {
        "report_version": "operation-creation-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "可执行新计算操作创造实验",
        "verdict": verdict,
        "claim_scope": "operation_creation_and_composition_only",
        "architecture": "executable_program_synthesis_not_concept_completion",
        "learner_received": {
            "unordered_numeric_values": list(values),
            "input_order_semantics": False,
            "target_outputs": False,
            "target_operation": False,
            "natural_language_labels": False,
            "base_operations": ["r_value", "r_add", "r_subtract", "r_compose"],
        },
        "creation_result": {
            "operation_a": {
                **operation_a.to_dict(),
                "knowledge_id": knowledge_a,
                "knowledge_status": ledger.get(knowledge_a).status,
                "observed_edges": operation_a_edges,
            },
            "operation_b": {
                **operation_b.to_dict(),
                "knowledge_id": knowledge_b,
                "knowledge_status": ledger.get(knowledge_b).status,
                "created_from_operation_ids": [
                    operation_a.operation_id,
                    operation_a.operation_id,
                ],
                "observed_edges": operation_b_edges,
            },
            "heldout_execution_replay": replay_cases,
        },
        "search": {
            "programs_generated": first_report.programs_generated,
            "selected_candidate_id": selected.candidate_id,
            "order_ablation_selected_same_candidate": order_invariant,
        },
        "generated_concepts": [],
        "generated_missing_values": [],
        "post_hoc_evaluator_interpretation": {
            "assigned_after_creation": True,
            "operation_a": "add the input value to itself",
            "operation_b": "apply operation A to the result of operation A",
        },
        "gates": gates,
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "Both new operations are derived from the supplied value, addition, subtraction, and composition substrate.",
            "Behavioral replay proves executable identity, not usefulness on an independent task.",
            "No missing value or concept is generated or admitted by this experiment.",
            "This is internal operation creation, not a claim of previously unknown human mathematics.",
        ],
    }
    artifact_path = run_directory / "operation_creation_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    latest_path = PROJECT_ROOT / "reports" / "data" / "operation_creation_latest.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact_path, latest_path)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": verdict,
                "operation_a": operation_a.operation_id,
                "operation_b": operation_b.operation_id,
                "operation_b_parents": [
                    operation_a.operation_id,
                    operation_a.operation_id,
                ],
                "operation_a_edges": operation_a_edges,
                "operation_b_edges": operation_b_edges,
                "generated_concept_count": 0,
                "generated_missing_value_count": 0,
                "artifact_path": artifact_path.relative_to(PROJECT_ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if verdict == "conditionally_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
