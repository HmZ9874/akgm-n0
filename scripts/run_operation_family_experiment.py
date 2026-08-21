"""Create and verify at least five behaviorally distinct executable formulas."""

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
from akgm_n0.learner import (
    NumericCollectionObservation,
    RelationExecutor,
    RelationOperationLibrary,
    RelationProgramSearch,
)


MINIMUM_REPORTED_FORMULAS = 5


def render_relation_formula(definition: dict) -> str:
    """Render the executable relation tree without assigning it a concept name."""

    operation = definition.get("op")
    if operation == "r_value":
        return "x"
    if operation == "r_constant":
        return str(definition.get("constant"))
    args = definition.get("args", [])
    if operation in {"r_add", "r_subtract"} and len(args) == 2:
        symbol = "+" if operation == "r_add" else "-"
        return (
            f"({render_relation_formula(args[0])} {symbol} "
            f"{render_relation_formula(args[1])})"
        )
    return json.dumps(definition, ensure_ascii=False, sort_keys=True)


def underlying_logic_signature(definition: dict) -> str:
    operations: set[str] = set()
    stack = [definition]
    while stack:
        node = stack.pop()
        operation = str(node.get("op"))
        if operation != "r_value":
            operations.add(operation)
        stack.extend(node.get("args", []))
    return json.dumps(
        {
            "substrate_family": "stateless_unary_relation_ast",
            "primitive_operations": sorted(operations),
            "control_state": False,
            "dynamic_storage": False,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def make_observation(values: tuple[float, ...]):
    return NumericCollectionObservation.create(
        opaque_session_id="USER-OPERATION-FAMILY",
        numeric_values=values,
        validity_mask=[True] * len(values),
        action_receipt="USER-UNORDERED-COLLECTION",
    )


def observed_edges(library, operation_id, values):
    members = set(values)
    return [
        {"source": source, "target": target}
        for source in sorted(members)
        for target in (library.execute(operation_id, source),)
        if target in members and target != source
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("values", nargs="+", type=float)
    arguments = parser.parse_args()
    values = tuple(arguments.values)
    if len(values) < 3:
        raise ValueError("operation-family creation requires at least three values")

    search_report = RelationProgramSearch(maximum_nodes=7, top_k=20).search(
        make_observation(values)
    )
    seed_candidate = search_report.top_candidates[0]
    executor = RelationExecutor()
    library = RelationOperationLibrary(executor)
    base = library.promote(seed_candidate.program)
    operations = [base]
    parent_operation_ids: list[list[str]] = [[]]
    while len(operations) < MINIMUM_REPORTED_FORMULAS:
        previous = operations[-1]
        created = library.compose(base.operation_id, previous.operation_id)
        operations.append(created)
        parent_operation_ids.append([base.operation_id, previous.operation_id])

    probes = (-7.0, 0.0, 3.0, 11.0)
    formula_results = []
    for index, (operation, parents) in enumerate(
        zip(operations, parent_operation_ids, strict=True), start=1
    ):
        formula_results.append(
            {
                "formula_index": index,
                "operation_id": operation.operation_id,
                "parent_operation_ids": parents,
                "machine_definition": operation.definition.to_dict(),
                "machine_formula": (
                    "seed_program"
                    if index == 1
                    else f"compose({base.operation_id}, {operations[index - 2].operation_id})"
                ),
                "post_hoc_readable_formula": (
                    f"F1(x) = {render_relation_formula(operation.definition.to_dict())}"
                    if index == 1
                    else f"F{index}(x) = F1(F{index - 1}(x))"
                ),
                "underlying_logic_signature": underlying_logic_signature(
                    operation.definition.to_dict()
                ),
                "observed_edges": observed_edges(
                    library, operation.operation_id, values
                ),
                "probe_results": [
                    {
                        "input": probe,
                        "output": library.execute(operation.operation_id, probe),
                    }
                    for probe in probes
                ],
            }
        )

    behavior_signatures = {
        tuple(item["output"] for item in formula["probe_results"])
        for formula in formula_results
    }
    logic_signatures = {
        formula["underlying_logic_signature"] for formula in formula_results
    }
    all_callable = all(
        library.execute(operation.operation_id, probe)
        == executor.evaluate(operation.definition, probe)
        for operation in operations
        for probe in probes
    )
    gates = [
        {
            "gate_id": "minimum_formula_count",
            "passed": len(formula_results) >= MINIMUM_REPORTED_FORMULAS,
            "actual": len(formula_results),
            "threshold": MINIMUM_REPORTED_FORMULAS,
        },
        {
            "gate_id": "behaviorally_distinct_formulas",
            "passed": len(behavior_signatures) == len(formula_results),
            "actual": len(behavior_signatures),
            "threshold": len(formula_results),
        },
        {
            "gate_id": "distinct_underlying_logic_families",
            "passed": len(logic_signatures) == len(formula_results),
            "actual": len(logic_signatures),
            "threshold": len(formula_results),
        },
        {
            "gate_id": "all_formulas_callable_by_operation_id",
            "passed": all_callable,
            "actual": all_callable,
            "threshold": True,
        },
        {
            "gate_id": "all_formulas_have_observed_relation",
            "passed": all(formula["observed_edges"] for formula in formula_results),
            "actual": sum(bool(formula["observed_edges"]) for formula in formula_results),
            "threshold": len(formula_results),
        },
        {
            "gate_id": "general_binary_operation",
            "passed": None,
            "actual": None,
            "threshold": True,
        },
    ]
    passed = all(gate["passed"] for gate in gates if gate["passed"] is not None)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-operation-family-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    knowledge_records = []
    for formula, operation in zip(formula_results, operations, strict=True):
        parent_ids = tuple(formula["parent_operation_ids"] or ("r_value", "r_add"))
        knowledge_id = ledger.propose(
            operation.definition,
            parent_ids=parent_ids,
            provenance={
                "run_id": run_id,
                "operation_id": operation.operation_id,
                "formula_index": formula["formula_index"],
            },
            evidence={"observed_edges": formula["observed_edges"]},
        )
        if formula["observed_edges"]:
            ledger.transition(
                knowledge_id,
                "fit_passed",
                reason="created_formula_has_observed_relation",
                evidence={"edge_count": len(formula["observed_edges"])},
            )
            ledger.transition(
                knowledge_id,
                "verified",
                reason="opaque_operation_call_matches_definition",
                evidence={"probe_count": len(probes)},
            )
            ledger.transition(
                knowledge_id,
                "bounded",
                reason="general_binary_behavior_not_claimed",
                evidence={"pending_gate": "general_binary_operation"},
            )
        else:
            ledger.transition(
                knowledge_id,
                "rejected",
                reason="created_formula_has_no_observed_relation",
                evidence={"edge_count": 0, "supplied_values": list(values)},
            )
        knowledge_records.append(
            {
                "operation_id": operation.operation_id,
                "knowledge_id": knowledge_id,
                "status": ledger.get(knowledge_id).status,
            }
        )

    success_room = FormulaSuccessRoom(
        PROJECT_ROOT
        / "artifacts"
        / "formula_rooms"
        / "success"
        / "successful_formulas.jsonl"
    )
    room_records = []
    if passed:
        for formula, operation, knowledge in zip(
            formula_results, operations, knowledge_records, strict=True
        ):
            room_record = success_room.record(
                operation.definition,
                operation_id=operation.operation_id,
                parent_operation_ids=tuple(formula["parent_operation_ids"]),
                validation_scope="five_formula_operation_family_v0.1",
                knowledge_status=knowledge["status"],
                evidence={
                    "run_id": run_id,
                    "formula_index": formula["formula_index"],
                    "underlying_logic_signature": formula[
                        "underlying_logic_signature"
                    ],
                    "observed_edges": formula["observed_edges"],
                    "probe_results": formula["probe_results"],
                },
            )
            room_records.append(room_record.to_dict())

    report = {
        "report_version": "operation-family-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "五公式可执行操作族创造实验",
        "verdict": "conditionally_passed" if passed else "failed",
        "claim_scope": "five_distinct_unary_composed_operations",
        "architecture": "opaque_operation_id_composition_not_concept_generation",
        "input": {
            "unordered_numeric_values": list(values),
            "target_formulas": False,
            "natural_language_labels": False,
            "minimum_reported_formulas": MINIMUM_REPORTED_FORMULAS,
        },
        "seed_search": {
            "programs_generated": search_report.programs_generated,
            "selected_candidate": seed_candidate.to_dict(),
        },
        "formulas": formula_results,
        "knowledge_records": knowledge_records,
        "success_formula_room": {
            "path": "artifacts/formula_rooms/success/successful_formulas.jsonl",
            "total_record_count": len(success_room.records),
            "records_for_this_run": room_records,
            "append_only_hash_chain": True,
        },
        "generated_concepts": [],
        "generated_missing_values": [],
        "gates": gates,
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "The five formulas are unary operations created by repeated composition of the first discovered operation.",
            "They may collapse to identical behavior and are not a general two-input operation.",
            "The base substrate still supplies value reading, addition, subtraction, and composition.",
            "Readable formulas are exact renderings of the executable tree; operation ids and executable definitions remain authoritative.",
        ],
    }
    artifact_path = run_directory / "operation_family_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    latest_path = PROJECT_ROOT / "reports" / "data" / "operation_family_latest.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact_path, latest_path)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": report["verdict"],
                "formula_count": len(formula_results),
                "distinct_behavior_count": len(behavior_signatures),
                "distinct_underlying_logic_count": len(logic_signatures),
                "success_room_total": len(success_room.records),
                "success_room_record_ids": [
                    item["room_record_id"] for item in room_records
                ],
                "formulas": [
                    {
                        "operation_id": item["operation_id"],
                        "formula": item["post_hoc_readable_formula"],
                        "observed_edges": item["observed_edges"],
                    }
                    for item in formula_results
                ],
                "artifact_path": artifact_path.relative_to(PROJECT_ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
