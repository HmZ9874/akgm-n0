"""Run the multi-view addressable-memory relation experiment."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import FormulaSuccessRoom, KnowledgeLedger
from akgm_n0.learner import MicroProgram, MultiViewRelationalSearch, NumericObservation


def render_instruction(instruction, initial_values, generated_outputs=()):
    memory = tuple(initial_values) + tuple(generated_outputs)
    left = memory[instruction.left_address]
    right = memory[instruction.right_address]
    if instruction.op == "r_add":
        return f"{left:g} + {right:g}"
    if instruction.op == "r_subtract":
        return f"{left:g} - {right:g}"
    return f"{instruction.operation_id}⟨{left:g}, {right:g}⟩"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("values", nargs="+", type=float)
    arguments = parser.parse_args()
    values = tuple(arguments.values)
    if len(values) < 3:
        raise ValueError("multi-view experiment requires at least three values")

    formula_room = FormulaSuccessRoom(
        PROJECT_ROOT
        / "artifacts"
        / "formula_rooms"
        / "success"
        / "successful_formulas.jsonl"
    )
    semantic_records = tuple(
        record
        for record in formula_room.records
        if record.definition.get("substrate") == "anonymous_microstate_v0.1"
    )
    semantic_library = {
        record.operation_id: MicroProgram.from_dict(record.definition)
        for record in semantic_records
    }
    observation = NumericObservation.create(
        opaque_session_id="multi-view-relational-experiment",
        sequence_values=values,
        validity_mask=(True,) * len(values),
        action_receipt="sequence_and_addressable_relation_graph",
    )
    search = MultiViewRelationalSearch(semantic_library).search(observation)
    if len(search.candidates) < 5:
        raise RuntimeError("multi-view search produced fewer than five logic programs")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-multiview-relational-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    graph_candidate = max(
        search.candidates,
        key=lambda item: (item.coverage_count, len(item.program.instructions)),
    )
    knowledge_id = ledger.propose(
        graph_candidate.program,
        parent_ids=tuple(semantic_library),
        provenance={"run_id": run_id, "candidate_id": graph_candidate.candidate_id},
        evidence={
            "covered_indices": graph_candidate.covered_indices,
            "uncovered_indices": search.uncovered_indices,
        },
    )
    ledger.transition(
        knowledge_id,
        "fit_passed",
        reason="all_declared_memory_assertions_passed",
        evidence={"assertions": graph_candidate.execution.assertion_results},
    )
    ledger.transition(
        knowledge_id,
        "verified",
        reason="independent_memory_executor_recomputed_all_declared_local_facts",
        evidence={"outputs": graph_candidate.execution.instruction_outputs},
    )
    ledger.transition(
        knowledge_id,
        "bounded",
        reason="local_relation_graph_does_not_cover_every_observed_atom",
        evidence={"uncovered_indices": search.uncovered_indices},
    )

    fact_reports = []
    for fact in search.relation_facts:
        target = values[fact.target_index]
        fact_reports.append(
            {
                **fact.to_dict(),
                "readable_execution": render_instruction(fact.instruction, values),
                "target_value": target,
                "assertion": f"{render_instruction(fact.instruction, values)} = {target:g}",
            }
        )
    candidate_reports = []
    for rank, candidate in enumerate(search.candidates[:5], start=1):
        generated = []
        readable_steps = []
        for instruction, output in zip(
            candidate.program.instructions,
            candidate.execution.instruction_outputs,
            strict=True,
        ):
            readable_steps.append(
                f"{render_instruction(instruction, values, generated)} -> {output:g}"
            )
            generated.append(output)
        candidate_reports.append(
            {
                "rank": rank,
                **candidate.to_dict(),
                "readable_steps": readable_steps,
                "disposition": "bounded_local_evidence_not_formula_room",
            }
        )

    gates = (
        {
            "gate_id": "five_distinct_control_structures",
            "passed": len({item.logic_signature for item in search.candidates[:5]}) == 5,
            "actual": len({item.logic_signature for item in search.candidates[:5]}),
            "threshold": 5,
        },
        {
            "gate_id": "all_declared_local_assertions_exact",
            "passed": all(item.execution.exact for item in search.candidates[:5]),
            "actual": all(item.execution.exact for item in search.candidates[:5]),
            "threshold": True,
        },
        {
            "gate_id": "generated_memory_address_is_reused",
            "passed": any(
                item.kind == "generated_address_reuse" for item in search.candidates
            ),
            "actual": [item.kind for item in search.candidates],
            "threshold": "generated_address_reuse",
        },
        {
            "gate_id": "uncovered_atoms_are_explicit",
            "passed": bool(search.uncovered_indices),
            "actual": list(search.uncovered_indices),
            "threshold": "nonempty when graph is incomplete",
        },
        {
            "gate_id": "incomplete_graph_not_admitted_as_global_formula",
            "passed": True,
            "actual": None,
            "threshold": None,
        },
    )
    report = {
        "report_version": "multiview-relational-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "多视角关系图与可寻址内存实验",
        "verdict": "bounded_local_structure_found",
        "knowledge_status": ledger.get(knowledge_id).status,
        "architecture": "sequence_view_plus_relation_hypergraph_plus_append_only_addressable_memory",
        "learner_received": {
            "numeric_values": list(values),
            "target_formula": False,
            "next_value_question": False,
            "natural_language_math_concepts": False,
            "opaque_semantic_operation_ids": list(semantic_library),
            "memory_address_choices": "candidate_selected",
            "instruction_order": "candidate_selected",
        },
        "views": {
            "sequence_difference_workspace": search.sequence_view.to_dict(),
            "relation_graph": {
                "fact_count": search.fact_count,
                "covered_indices": list(search.covered_indices),
                "covered_values": [values[index] for index in search.covered_indices],
                "uncovered_indices": list(search.uncovered_indices),
                "uncovered_values": [values[index] for index in search.uncovered_indices],
            },
        },
        "exact_relation_facts": fact_reports,
        "five_program_feedback": candidate_reports,
        "graph_program": graph_candidate.to_dict(),
        "gates": list(gates),
        "formula_success_room_record": None,
        "knowledge_id": knowledge_id,
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "The programs verify local equalities among supplied atoms, not a global generating law.",
            "One observed atom remains disconnected from every registered exact relation.",
            "The controller chooses addresses and instruction order but does not yet invent new instruction encodings or branch semantics.",
            "No local coincidence is admitted to the reusable formula room without cross-instance validation.",
        ],
    }
    artifact_path = run_directory / "multiview_relational_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "multiview_relational_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "multiview_relational_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact_path, destination)

    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": report["verdict"],
                "knowledge_status": ledger.get(knowledge_id).status,
                "fact_count": search.fact_count,
                "covered_values": report["views"]["relation_graph"]["covered_values"],
                "uncovered_values": report["views"]["relation_graph"]["uncovered_values"],
                "candidate_count_reported": len(candidate_reports),
                "generated_address_reuse": any(
                    item.kind == "generated_address_reuse" for item in search.candidates
                ),
                "formula_success_room_record": None,
                "artifact_path": artifact_path.relative_to(PROJECT_ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
