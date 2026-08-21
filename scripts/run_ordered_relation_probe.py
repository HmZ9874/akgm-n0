"""Run a bounded ordered-relation probe and preserve honest failures."""

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

from akgm_n0.evaluator import FormulaSuccessRoom, IndexedMistakeLibrary, KnowledgeLedger
from akgm_n0.learner import IndexedSemanticSearch, MicroProgram, NumericObservation


def five_distinct_logic(report):
    chosen = []
    signatures = set()
    for candidate in report.top_candidates:
        if candidate.logic_signature in signatures:
            continue
        chosen.append(candidate)
        signatures.add(candidate.logic_signature)
        if len(chosen) == 5:
            break
    return tuple(chosen)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("values", nargs="+", type=float)
    arguments = parser.parse_args()
    values = tuple(arguments.values)
    if len(values) < 3:
        raise ValueError("ordered relation probe requires at least three numbers")

    success_room = FormulaSuccessRoom(
        PROJECT_ROOT
        / "artifacts"
        / "formula_rooms"
        / "success"
        / "successful_formulas.jsonl"
    )
    semantic_records = tuple(
        record
        for record in success_room.records
        if record.definition.get("substrate") == "anonymous_microstate_v0.1"
    )
    semantic_library = {
        record.operation_id: MicroProgram.from_dict(record.definition)
        for record in semantic_records
    }
    observation = NumericObservation.create(
        opaque_session_id="ordered-relation-probe",
        sequence_values=values,
        validity_mask=(True,) * len(values),
        action_receipt="ordered_relation_only_not_next_value",
    )
    control = IndexedSemanticSearch({}, top_k=100).search(observation)
    search = IndexedSemanticSearch(semantic_library, top_k=100).search(observation)
    candidates = five_distinct_logic(search)
    if len(candidates) < 5:
        raise RuntimeError("fewer than five distinct logic candidates were generated")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-ordered-relation-probe-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    condition_key = "ordered-probe-" + hashlib.sha256(
        json.dumps(values, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    mistake_library = IndexedMistakeLibrary(
        PROJECT_ROOT / "artifacts" / "mistakes" / "indexed_mistakes.jsonl"
    )
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    feedback = []
    for rank, candidate in enumerate(candidates, start=1):
        counterexamples = tuple(
            {
                "index": index,
                "predicted": predicted,
                "observed": observed,
                "absolute_error": abs(predicted - observed),
            }
            for index, (predicted, observed) in enumerate(
                zip(candidate.training_outputs, values, strict=True)
            )
            if predicted != observed
        )
        mistake_record = None
        if counterexamples:
            mistake_record = mistake_library.record(
                candidate.program,
                failed_scope="supplied_ordered_relation_fit",
                condition_key=condition_key,
                counterexamples=counterexamples,
                source_candidate_id=candidate.candidate_id,
            )
        feedback.append(
            {
                "rank": rank,
                **candidate.to_dict(),
                "counterexamples": list(counterexamples),
                "disposition": (
                    "fit_only_unverified" if candidate.exact else "mistake_library"
                ),
                "mistake_id": (
                    mistake_record.mistake_id if mistake_record is not None else None
                ),
            }
        )

    winner = candidates[0]
    knowledge_id = ledger.propose(
        winner.program,
        parent_ids=tuple(search.semantic_operation_ids),
        provenance={"run_id": run_id, "candidate_id": winner.candidate_id},
        evidence={"supplied_fit_mse": winner.fit_mse},
    )
    if winner.exact:
        ledger.transition(
            knowledge_id,
            "fit_passed",
            reason="all_supplied_positions_fit_but_no_independent_extension_available",
            evidence={"independent_verification": False},
        )
        verdict = "fit_only"
    else:
        ledger.transition(
            knowledge_id,
            "rejected",
            reason="best_candidate_failed_supplied_positions",
            evidence={"counterexamples": feedback[0]["counterexamples"]},
        )
        verdict = "no_relation_discovered"

    report = {
        "report_version": "ordered-relation-probe-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "有序数字关系探测",
        "verdict": verdict,
        "knowledge_status": ledger.get(knowledge_id).status,
        "learner_received": {
            "numeric_values": list(values),
            "order_semantics": True,
            "next_value_question": False,
            "target_formula": False,
            "natural_language_math_concepts": False,
            "intrinsic_multiply_node": False,
            "intrinsic_divide_node": False,
            "opaque_semantic_operation_ids": list(search.semantic_operation_ids),
        },
        "derived_workspace": search.difference_workspace.to_dict(),
        "control_without_library": {
            "programs_generated": control.programs_generated,
            "behavior_classes": control.behavior_classes,
            "best_fit_mse": control.top_candidates[0].fit_mse,
            "exact": control.top_candidates[0].exact,
        },
        "search_with_library": {
            "programs_generated": search.programs_generated,
            "programs_executed": search.programs_executed,
            "behavior_classes": search.behavior_classes,
            "best_fit_mse": winner.fit_mse,
            "best_maximum_absolute_error": winner.maximum_absolute_error,
            "exact": winner.exact,
        },
        "five_candidate_feedback": feedback,
        "success_room_record": None,
        "knowledge_id": knowledge_id,
        "ledger_event_count": len(ledger.events),
        "conclusion": (
            "No candidate in the registered bounded search exactly relates all supplied positions."
            if not winner.exact
            else "An exact supplied-data fit exists but lacks independent validation."
        ),
        "limitations": [
            "Failure is relative to the registered seven-node grammar and loaded semantic library.",
            "It does not prove that no relation exists in a larger computation space.",
            "No next value is predicted and no successful formula is admitted without exact fit and independent evidence.",
        ],
    }
    artifact_path = run_directory / "ordered_relation_probe_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "ordered_relation_probe_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "ordered_relation_probe_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact_path, destination)

    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": verdict,
                "knowledge_status": ledger.get(knowledge_id).status,
                "values": values,
                "first_layer": search.difference_workspace.first_layer,
                "second_layer": search.difference_workspace.second_layer,
                "control_best_mse": control.top_candidates[0].fit_mse,
                "library_best_mse": winner.fit_mse,
                "library_best_maximum_absolute_error": winner.maximum_absolute_error,
                "exact": winner.exact,
                "candidate_count_reported": len(feedback),
                "mistake_count_written": sum(
                    item["mistake_id"] is not None for item in feedback
                ),
                "success_room_record": None,
                "artifact_path": artifact_path.relative_to(PROJECT_ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
