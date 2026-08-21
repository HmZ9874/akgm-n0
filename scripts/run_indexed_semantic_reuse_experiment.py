"""Test whether an ordered relation can reuse an anonymous learned operation."""

from __future__ import annotations

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
    IndexedMistakeLibrary,
    KnowledgeLedger,
)
from akgm_n0.learner import (
    IndexedExecutor,
    IndexedSemanticSearch,
    MicroProgram,
    NumericObservation,
    indexed_node_key,
)


SUPPLIED_VALUES = (2, 6, 12, 20, 30, 42, 56)
# Evaluator-only extension. It is never passed to either search.
SEALED_EXTENSION = ((7, 72), (8, 90), (9, 110), (10, 132), (11, 156))


def _five_distinct_logic_candidates(report):
    selected = []
    signatures = set()
    for candidate in report.top_candidates:
        if candidate.logic_signature in signatures:
            continue
        selected.append(candidate)
        signatures.add(candidate.logic_signature)
        if len(selected) == 5:
            break
    return tuple(selected)


def main() -> int:
    success_path = (
        PROJECT_ROOT
        / "artifacts"
        / "formula_rooms"
        / "success"
        / "successful_formulas.jsonl"
    )
    success_room = FormulaSuccessRoom(success_path)
    semantic_records = tuple(
        record
        for record in success_room.records
        if record.definition.get("substrate") == "anonymous_microstate_v0.1"
    )
    semantic_library = {
        record.operation_id: MicroProgram.from_dict(record.definition)
        for record in semantic_records
    }
    if not semantic_library:
        raise RuntimeError("success room contains no verified anonymous microstate semantic")

    observation = NumericObservation.create(
        opaque_session_id="ordered-relation-opaque",
        sequence_values=SUPPLIED_VALUES,
        validity_mask=(True,) * len(SUPPLIED_VALUES),
        action_receipt="ordered_numeric_relation",
    )
    without_library = IndexedSemanticSearch({}, top_k=100).search(observation)
    with_library = IndexedSemanticSearch(semantic_library, top_k=100).search(
        observation
    )
    displayed = _five_distinct_logic_candidates(with_library)
    if len(displayed) < 5:
        raise RuntimeError("search did not produce five distinct logic structures")
    winner = with_library.top_candidates[0]
    executor = IndexedExecutor(semantic_library)
    blind_results = tuple(
        {
            "index": index,
            "predicted": executor.execute(winner.program, index),
            "observed": expected,
        }
        for index, expected in SEALED_EXTENSION
    )
    blind_exact = all(
        item["predicted"] == item["observed"] for item in blind_results
    )
    serialized_winner = json.dumps(
        winner.program.to_dict(), ensure_ascii=False, sort_keys=True
    ).lower()
    no_intrinsic_forbidden_nodes = all(
        token not in serialized_winner
        for token in ("multiply", "division", "divide", "product")
    )
    exact_without = any(candidate.exact for candidate in without_library.top_candidates)
    exact_with = winner.exact
    parent_ids = tuple(
        operation_id
        for operation_id in with_library.semantic_operation_ids
        if operation_id.lower() in serialized_winner
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-indexed-semantic-reuse-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    condition_key = "ordered-relation-" + hashlib.sha256(
        json.dumps(SUPPLIED_VALUES, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    mistakes = IndexedMistakeLibrary(
        PROJECT_ROOT / "artifacts" / "mistakes" / "indexed_mistakes.jsonl"
    )
    rejected_records = []
    for candidate in displayed:
        if candidate.exact:
            continue
        counterexamples = tuple(
            {
                "index": index,
                "predicted": predicted,
                "observed": observed,
                "absolute_error": abs(predicted - observed),
            }
            for index, (predicted, observed) in enumerate(
                zip(candidate.training_outputs, SUPPLIED_VALUES, strict=True)
            )
            if predicted != observed
        )
        record = mistakes.record(
            candidate.program,
            failed_scope="supplied_ordered_relation_fit",
            condition_key=condition_key,
            counterexamples=counterexamples,
            source_candidate_id=candidate.candidate_id,
        )
        rejected_records.append(record.mistake_id)

    gates = (
        {
            "gate_id": "ordered_position_available_without_next_value_target",
            "passed": with_library.order_semantics_enabled,
            "actual": with_library.order_semantics_enabled,
            "threshold": True,
        },
        {
            "gate_id": "generic_adjacent_subtraction_workspace_built",
            "passed": with_library.difference_workspace.second_layer
            == (2.0, 2.0, 2.0, 2.0, 2.0),
            "actual": list(with_library.difference_workspace.second_layer),
            "threshold": "constant derived layer",
        },
        {
            "gate_id": "add_subtract_only_control_has_no_exact_program",
            "passed": not exact_without,
            "actual": exact_without,
            "threshold": False,
        },
        {
            "gate_id": "anonymous_success_room_operation_enables_exact_fit",
            "passed": exact_with and bool(parent_ids),
            "actual": {"exact": exact_with, "parents": list(parent_ids)},
            "threshold": "exact with at least one opaque parent operation",
        },
        {
            "gate_id": "sealed_extension_exact",
            "passed": blind_exact,
            "actual": blind_results,
            "threshold": "5/5 exact",
        },
        {
            "gate_id": "no_intrinsic_multiply_or_divide_node",
            "passed": no_intrinsic_forbidden_nodes,
            "actual": no_intrinsic_forbidden_nodes,
            "threshold": True,
        },
        {
            "gate_id": "five_distinct_logic_structures_reported",
            "passed": len({item.logic_signature for item in displayed}) == 5,
            "actual": len({item.logic_signature for item in displayed}),
            "threshold": 5,
        },
    )
    verdict = "conditionally_passed" if all(gate["passed"] for gate in gates) else "failed"

    knowledge_id = ledger.propose(
        winner.program,
        parent_ids=parent_ids,
        provenance={
            "run_id": run_id,
            "candidate_id": winner.candidate_id,
            "search": "indexed_semantic_reuse_v0.1",
        },
        evidence={"training_fit_mse": winner.fit_mse},
    )
    ledger.transition(
        knowledge_id,
        "fit_passed" if winner.exact else "rejected",
        reason="supplied_ordered_relation_evaluated",
        evidence={"candidate": winner.to_dict()},
    )
    room_record = None
    if winner.exact:
        ledger.transition(
            knowledge_id,
            "verified" if blind_exact else "rejected",
            reason="sealed_index_extension_evaluated",
            evidence={"blind_results": blind_results},
        )
    if winner.exact and blind_exact and verdict == "conditionally_passed":
        ledger.transition(
            knowledge_id,
            "bounded",
            reason="verified_on_supplied_relation_and_five_sealed_indices",
            evidence={"verified_index_domain": [0, 11]},
        )
        operation_id = "IDX-" + hashlib.sha256(
            indexed_node_key(winner.program).encode("utf-8")
        ).hexdigest()[:16]
        room_record = success_room.record(
            winner.program,
            operation_id=operation_id,
            parent_operation_ids=parent_ids,
            validation_scope="indexed_semantic_reuse_v0.1_indices_0_through_11",
            knowledge_status="bounded",
            evidence={
                "run_id": run_id,
                "training_case_count": len(SUPPLIED_VALUES),
                "sealed_case_count": len(SEALED_EXTENSION),
                "sealed_exact": blind_exact,
                "control_without_library_exact": exact_without,
            },
        )

    candidate_feedback = [
        {
            "rank": rank,
            **candidate.to_dict(),
            "disposition": "success_room" if candidate.exact else "mistake_library",
        }
        for rank, candidate in enumerate(displayed, start=1)
    ]
    report = {
        "report_version": "indexed-semantic-reuse-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "有序关系与匿名计算语义复用实验",
        "verdict": verdict,
        "knowledge_status": ledger.get(knowledge_id).status,
        "architecture": "ordered_index_plus_difference_workspace_plus_opaque_semantic_composition",
        "learner_received": {
            "numeric_values": list(SUPPLIED_VALUES),
            "order_semantics": True,
            "next_value_question": False,
            "natural_language_math_concepts": False,
            "target_formula": False,
            "intrinsic_multiply_node": False,
            "intrinsic_divide_node": False,
            "opaque_success_room_operation_ids": list(semantic_library),
            "sealed_extension_visible_during_search": False,
        },
        "derived_workspace": with_library.difference_workspace.to_dict(),
        "control_without_success_room": {
            "semantic_operation_count": 0,
            "programs_generated": without_library.programs_generated,
            "behavior_classes": without_library.behavior_classes,
            "best_candidate": without_library.top_candidates[0].to_dict(),
            "exact_candidate_found": exact_without,
        },
        "search_with_success_room": {
            "semantic_operation_ids": list(with_library.semantic_operation_ids),
            "programs_generated": with_library.programs_generated,
            "programs_executed": with_library.programs_executed,
            "invalid_programs": with_library.invalid_programs,
            "behavior_classes": with_library.behavior_classes,
            "exact_candidate_found": exact_with,
        },
        "five_candidate_feedback": candidate_feedback,
        "winner": {
            **winner.to_dict(),
            "parent_operation_ids": list(parent_ids),
            "sealed_extension": list(blind_results),
        },
        "gates": list(gates),
        "success_room_record": room_record.to_dict() if room_record else None,
        "mistake_record_ids": rejected_records,
        "knowledge_id": knowledge_id,
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "The ordered position token is host-provided metadata, not a learned semantic.",
            "The winning relation is bounded to supplied and sealed indices 0 through 11.",
            "The opaque parent semantic was previously verified only over a bounded integer domain.",
            "A second unrelated ordered task is still required to establish broad transfer.",
        ],
    }
    artifact_path = run_directory / "indexed_semantic_reuse_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "indexed_semantic_reuse_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "indexed_semantic_reuse_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact_path, destination)

    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": verdict,
                "knowledge_status": ledger.get(knowledge_id).status,
                "derived_first_layer": list(with_library.difference_workspace.first_layer),
                "derived_second_layer": list(with_library.difference_workspace.second_layer),
                "control_without_library_exact": exact_without,
                "with_library_exact": exact_with,
                "sealed_extension_exact": blind_exact,
                "winner_candidate_id": winner.candidate_id,
                "winner_program": winner.program.to_dict(),
                "success_room_record_id": (
                    room_record.room_record_id if room_record else None
                ),
                "five_formula_count": len(candidate_feedback),
                "mistake_records_written": len(rejected_records),
                "artifact_path": artifact_path.relative_to(PROJECT_ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if verdict == "conditionally_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
