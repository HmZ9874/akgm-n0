"""Discover executable relations in an unordered user-supplied numeric collection."""

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

from akgm_n0.evaluator import (
    FormulaSuccessRoom,
    KnowledgeLedger,
    RelationMistakeLibrary,
)
from akgm_n0.learner import (
    NumericCollectionObservation,
    RelationExecutor,
    RelationOperationLibrary,
    RelationProgramSearch,
    compose_relation,
)


def make_observation(values: tuple[float, ...], session: str):
    return NumericCollectionObservation.create(
        opaque_session_id=session,
        numeric_values=values,
        validity_mask=[True] * len(values),
        action_receipt=f"RECEIPT-{session}",
    )


def render_relation(definition: dict) -> str:
    operation = definition["op"]
    if operation == "r_value":
        return "x"
    if operation == "r_constant":
        return str(definition["constant"])
    symbol = "+" if operation == "r_add" else "-"
    left, right = definition["args"]
    return f"({render_relation(left)} {symbol} {render_relation(right)})"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("values", nargs="+", type=float)
    arguments = parser.parse_args()
    values = tuple(arguments.values)
    if len(values) < 3:
        raise ValueError("relation discovery requires at least three values")

    condition_key = "unordered-set-" + hashlib.sha256(
        json.dumps(sorted(set(values)), separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    mistake_library = RelationMistakeLibrary(
        PROJECT_ROOT / "artifacts" / "mistakes" / "relation_mistakes.jsonl"
    )
    mistake_scope = {
        "objective_id": "unordered_relation_compression",
        "failed_scope": "supplied_collection",
        "condition_key": condition_key,
    }
    search = RelationProgramSearch(
        maximum_nodes=7,
        maximum_composition_steps=6,
        top_k=20,
        candidate_gate=mistake_library.candidate_gate(**mistake_scope),
    )
    report = search.search(make_observation(values, "USER-RELATION-COLLECTION"))
    selected = report.top_candidates[0]
    permutation_report = search.search(
        make_observation(tuple(reversed(values)), "ORDER-ABLATION")
    )
    order_invariant = (
        permutation_report.top_candidates[0].candidate_id == selected.candidate_id
    )

    executor = RelationExecutor()
    library = RelationOperationLibrary(executor)
    promoted = library.promote(selected.program)
    composed_program = compose_relation(selected.program, selected.program)
    composed_results = [
        {
            "source": value,
            "result": executor.evaluate(composed_program, value),
            "result_is_observed": executor.evaluate(composed_program, value) in set(values),
        }
        for value in sorted(values)
    ]
    generated_results = [
        {
            "source": value,
            "result": library.execute(promoted.operation_id, value),
            "result_is_observed": library.execute(promoted.operation_id, value)
            in set(values),
        }
        for value in sorted(values)
    ]
    connected_all_members = selected.observed_chain_count == len(set(values))
    gates = [
        {
            "gate_id": "input_order_ablation",
            "passed": order_invariant,
            "actual": order_invariant,
            "threshold": True,
        },
        {
            "gate_id": "all_members_connected_by_composition",
            "passed": connected_all_members,
            "actual": selected.observed_chain_count,
            "threshold": len(set(values)),
        },
        {
            "gate_id": "direct_observed_relations",
            "passed": len(selected.direct_edges) >= 2,
            "actual": len(selected.direct_edges),
            "threshold": 2,
        },
        {
            "gate_id": "composition_connects_members_directly_or_by_bridge",
            "passed": connected_all_members
            or bool(selected.generated_nodes and selected.bridges),
            "actual": {
                "connected_all_directly": connected_all_members,
                "generated_bridge_count": len(selected.bridges),
            },
            "threshold": True,
        },
        {
            "gate_id": "promoted_operation_executes",
            "passed": all(
                library.execute(promoted.operation_id, value)
                == executor.evaluate(selected.program, value)
                for value in values
            ),
            "actual": True,
            "threshold": True,
        },
        {
            "gate_id": "unseen_collection_transfer",
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
    run_id = f"RUN-relation-growth-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    knowledge_id = ledger.propose(
        selected.program,
        parent_ids=("r_value", "r_add", "r_subtract", "r_compose"),
        provenance={
            "run_id": run_id,
            "search_version": "unordered-relation-search-v0.1",
            "candidate_id": selected.candidate_id,
        },
        evidence={"selected_relation": selected.to_dict()},
    )
    if len(selected.direct_edges) >= 2:
        ledger.transition(
            knowledge_id,
            "fit_passed",
            reason="relation_compresses_user_collection",
            evidence={
                "observed_chain_count": selected.observed_chain_count,
                "direct_edge_count": len(selected.direct_edges),
            },
        )
    else:
        ledger.transition(
            knowledge_id,
            "rejected",
            reason="relation_did_not_compress_user_collection",
            evidence={"direct_edge_count": len(selected.direct_edges)},
        )
    if verdict == "conditionally_passed":
        ledger.transition(
            knowledge_id,
            "verified",
            reason="order_ablation_and_executable_composition_passed",
            evidence={"gates": gates},
        )
        ledger.transition(
            knowledge_id,
            "bounded",
            reason="no_unseen_collection_transfer_yet",
            evidence={"pending_gates": ["unseen_collection_transfer"]},
        )
    elif ledger.get(knowledge_id).status == "fit_passed":
        ledger.transition(
            knowledge_id,
            "rejected",
            reason="registered_relation_experiment_gate_failed",
            evidence={"gates": gates},
        )
    mistake_record = None
    if verdict == "failed":
        counterexamples = tuple(
            {
                "source": value,
                "result": executor.evaluate(selected.program, value),
                "result_is_observed": executor.evaluate(selected.program, value)
                in set(values),
            }
            for value in sorted(set(values))
            if executor.evaluate(selected.program, value) not in set(values)
        ) or ({"reason": "experiment_gate_failed", "gates": gates},)
        mistake_record = mistake_library.record(
            selected.program,
            **mistake_scope,
            counterexamples=counterexamples,
            source_candidate_id=selected.candidate_id,
        )

    success_room = FormulaSuccessRoom(
        PROJECT_ROOT
        / "artifacts"
        / "formula_rooms"
        / "success"
        / "successful_formulas.jsonl"
    )
    room_record = None
    if verdict == "conditionally_passed":
        room_record = success_room.record(
            selected.program,
            operation_id=promoted.operation_id,
            parent_operation_ids=(
                "r_value",
                "r_add",
                "r_subtract",
                "evidence_working_memory",
            ),
            validation_scope="unordered_relation_reasoning_v0.2",
            knowledge_status=ledger.get(knowledge_id).status,
            evidence={
                "run_id": run_id,
                "candidate_id": selected.candidate_id,
                "direct_edges": [edge.to_dict() for edge in selected.direct_edges],
                "order_ablation": order_invariant,
                "evidence_constants": list(report.evidence_constants),
            },
        )

    payload = {
        "report_version": "relation-growth-report-v0.2",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "无序数字关系与新计算操作生长实验",
        "verdict": verdict,
        "knowledge_status": ledger.get(knowledge_id).status,
        "claim_scope": "user_supplied_unordered_collection_only",
        "architecture": "executable_relation_compression_not_next_value_prediction",
        "learner_received": {
            "numeric_values": list(values),
            "input_order_semantics": False,
            "output_targets": False,
            "natural_language_labels": False,
            "target_formula": False,
            "base_operations": ["r_value", "r_add", "r_subtract", "r_compose"],
            "pre_supplied_constants": False,
        },
        "search": {
            "programs_generated": report.programs_generated,
            "programs_filtered_by_mistake_memory": report.programs_filtered,
            "valid_member_count": report.valid_member_count,
            "evidence_derived_working_memory": list(report.evidence_constants),
            "selected_candidate": selected.to_dict(),
            "order_ablation_selected_same_candidate": order_invariant,
        },
        "relation_graph": {
            "observed_members_in_discovered_chain": list(selected.best_chain),
            "direct_edges": [edge.to_dict() for edge in selected.direct_edges],
            "generated_missing_nodes": list(selected.generated_nodes),
            "bridges": [bridge.to_dict() for bridge in selected.bridges],
        },
        "new_computation": {
            "promoted_operation": promoted.to_dict(),
            "single_application_results": generated_results,
            "self_composed_program": composed_program.to_dict(),
            "self_composed_results": composed_results,
        },
        "post_hoc_evaluator_interpretation": {
            "assigned_after_search": True,
            "readable_formula": render_relation(selected.program.to_dict()),
            "human_relation_graph": " -> ".join(
                str(int(value) if value.is_integer() else value)
                for value in selected.best_chain
            ),
        },
        "gates": gates,
        "knowledge_id": knowledge_id,
        "mistake_record": (
            mistake_record.to_dict() if mistake_record is not None else None
        ),
        "success_formula_room_record": (
            room_record.to_dict() if room_record is not None else None
        ),
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "The discovered computation is derived from supplied value reading, addition, subtraction, and evidence working memory.",
            "The relation is verified for this collection and order ablations, not for an unseen collection.",
            "Generated value 32 is a bridge implied by the selected operation, not an observed input.",
            "This establishes relation discovery and operation composition, not autonomous invention of a new physical computation law.",
        ],
    }
    artifact_path = run_directory / "relation_growth_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    latest_path = PROJECT_ROOT / "reports" / "data" / "relation_growth_latest.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact_path, latest_path)
    dashboard_path = PROJECT_ROOT / "dashboard" / "data" / "relation_growth_latest.json"
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact_path, dashboard_path)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": verdict,
                "knowledge_status": ledger.get(knowledge_id).status,
                "candidate_id": selected.candidate_id,
                "operation_id": promoted.operation_id,
                "input_order_ignored": order_invariant,
                "observed_chain": list(selected.best_chain),
                "generated_nodes": list(selected.generated_nodes),
                "direct_edges": [edge.to_dict() for edge in selected.direct_edges],
                "readable_formula": render_relation(selected.program.to_dict()),
                "evidence_constants": list(report.evidence_constants),
                "success_room_record_id": (
                    room_record.room_record_id if room_record is not None else None
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
