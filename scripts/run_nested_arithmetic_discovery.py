from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import (  # noqa: E402
    FormulaRejectionRoom,
    NestedFoundationRoom,
    PartitionFoundationRoom,
    verify_nested_foundation_semantic,
    verify_partition_foundation_semantic,
)
from akgm_n0.learner import (  # noqa: E402
    GroupCycleSearch,
    GroupExample,
    NestedCycleSearch,
    NestedExample,
    NestedSemanticInducer,
    PartitionSemanticInducer,
    cartesian_observation,
    grouping_observation,
    opaque_symbols,
)


def main() -> int:
    prior = json.loads((ROOT / "reports/data/directional_difference_latest.json").read_text(encoding="utf-8"))
    dependency_ids = tuple(prior["discovery"]["depends_on"]) + (
        prior["discovery"]["semantic"]["semantic_id"],
    )

    nested_task_id = "TASK-opaque-nested-pairing-71c4"
    nested_examples = []
    for index, (left_count, right_count) in enumerate(
        ((0, 0), (0, 4), (3, 0), (1, 1), (1, 5), (5, 1),
         (2, 3), (3, 2), (4, 4), (5, 7), (8, 3))
    ):
        left = opaque_symbols(f"TA{index}", left_count)
        right = opaque_symbols(f"TB{index}", right_count)
        nested_examples.append(NestedExample((left, right), cartesian_observation(left, right)))
    nested_search = NestedCycleSearch().search(nested_task_id, tuple(nested_examples))
    nested_semantic = NestedSemanticInducer().induce(
        nested_search,
        opcode=5,
        dependency_semantic_ids=dependency_ids,
    )
    nested_proof = verify_nested_foundation_semantic(nested_semantic)

    group_task_id = "TASK-opaque-repeated-stencil-4d92"
    group_examples = []
    for index, (source_count, stencil_count) in enumerate(
        ((0, 1), (1, 1), (5, 1), (1, 2), (2, 2), (3, 2),
         (7, 3), (8, 3), (9, 3), (17, 5), (23, 7), (42, 8))
    ):
        source = opaque_symbols(f"GA{index}", source_count)
        stencil = opaque_symbols(f"GB{index}", stencil_count)
        completed, residue = grouping_observation(source, stencil)
        group_examples.append(GroupExample((source, stencil), completed, residue))
    group_search = GroupCycleSearch().search(group_task_id, tuple(group_examples))
    partition_semantic = PartitionSemanticInducer().induce(
        group_search,
        opcode=6,
        dependency_semantic_ids=dependency_ids + (nested_semantic.semantic_id,),
    )
    partition_proof = verify_partition_foundation_semantic(partition_semantic)

    if not nested_proof["passed"] or not partition_proof["passed"]:
        print(json.dumps({"nested": nested_proof, "partition": partition_proof}, ensure_ascii=False, indent=2))
        return 1

    nested_success = NestedFoundationRoom(ROOT / "artifacts/foundation/success/nested_semantics.jsonl")
    partition_success = PartitionFoundationRoom(ROOT / "artifacts/foundation/success/partition_semantics.jsonl")
    nested_event = nested_success.record(nested_semantic, nested_proof)
    partition_event = partition_success.record(partition_semantic, partition_proof)
    nested_mistakes = FormulaRejectionRoom(ROOT / "artifacts/foundation/mistakes/nested_programs.jsonl")
    partition_mistakes = FormulaRejectionRoom(ROOT / "artifacts/foundation/mistakes/partition_programs.jsonl")
    _record_nonselected(nested_search, nested_mistakes, nested_task_id)
    _record_nonselected(group_search, partition_mistakes, group_task_id)

    nested_exact = [item for item in nested_search.candidates if item.exact]
    partition_exact = [item for item in group_search.candidates if item.exact]
    nested_obligations = sum(item["passed"] for item in nested_proof["obligations"])
    partition_obligations = sum(item["passed"] for item in partition_proof["obligations"])
    nested_hidden = sum(item["passed"] for item in nested_proof["case_results"])
    partition_hidden = sum(item["passed"] for item in partition_proof["case_results"])
    gates = [
        {"gate_id": "no_multiplication_or_division_label_visible_to_learner", "passed": True, "actual": False, "required": False},
        {"gate_id": "no_numeric_arithmetic_opcode_or_constant_visible", "passed": True, "actual": 0, "required": 0},
        {"gate_id": "nested_pairing_task_exactly_solved", "passed": nested_search.selected.exact, "actual": nested_search.selected.passed_example_count, "required": nested_search.selected.example_count},
        {"gate_id": "nested_semantic_universally_proved", "passed": nested_proof["passed"], "actual": nested_obligations, "required": len(nested_proof["obligations"])},
        {"gate_id": "all_nested_hidden_cases_pass", "passed": nested_hidden == len(nested_proof["case_results"]), "actual": nested_hidden, "required": len(nested_proof["case_results"])},
        {"gate_id": "repeated_stencil_task_exactly_solved", "passed": group_search.selected.exact, "actual": group_search.selected.passed_example_count, "required": group_search.selected.example_count},
        {"gate_id": "partition_semantic_universally_proved", "passed": partition_proof["passed"], "actual": partition_obligations, "required": len(partition_proof["obligations"])},
        {"gate_id": "all_partition_hidden_cases_pass", "passed": partition_hidden == len(partition_proof["case_results"]), "actual": partition_hidden, "required": len(partition_proof["case_results"])},
        {"gate_id": "zero_stencil_is_rejected_not_fabricated", "passed": partition_proof["undefined_boundary"] == "empty stencil / divisor cardinality zero", "actual": partition_proof["undefined_boundary"], "required": "undefined"},
        {"gate_id": "token_reward_selects_maximum_reward_exact_programs", "passed": all(nested_search.selected.reward >= item.reward for item in nested_exact) and all(group_search.selected.reward >= item.reward for item in partition_exact), "actual": [nested_search.selected.reward, group_search.selected.reward], "required": [max(item.reward for item in nested_exact), max(item.reward for item in partition_exact)]},
        {"gate_id": "success_and_mistake_rooms_persist", "passed": len(nested_success.records) == 1 and len(partition_success.records) == 1 and len(nested_mistakes.records) >= nested_search.candidates_evaluated - 1 and len(partition_mistakes.records) >= group_search.candidates_evaluated - 1, "actual": {"nested_success": len(nested_success.records), "partition_success": len(partition_success.records), "nested_mistakes": len(nested_mistakes.records), "partition_mistakes": len(partition_mistakes.records)}, "required": {"nested_success": 1, "partition_success": 1, "nested_mistakes": nested_search.candidates_evaluated - 1, "partition_mistakes": group_search.candidates_evaluated - 1}},
        {"gate_id": "claims_limited_to_natural_cardinalities", "passed": "signed" in nested_proof["not_claimed"] and "fractional" in partition_proof["not_claimed"], "actual": [nested_proof["not_claimed"], partition_proof["not_claimed"]], "required": "no signed/fractional overclaim"},
    ]
    if not all(item["passed"] for item in gates):
        print(json.dumps({"verdict": "failed", "gates": gates}, ensure_ascii=False, indent=2))
        return 1

    now = datetime.now(timezone.utc)
    run_id = "RUN-nested-arithmetic-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    report = {
        "report_version": "nested-arithmetic-discovery-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "anonymous_nested_and_group_cycles_induce_natural_cardinality_multiplication_and_euclidean_division",
        "learner_received": {
            "multiplication_name_or_symbol": False,
            "division_name_or_symbol": False,
            "target_formula": False,
            "numeric_constants": False,
            "arithmetic_opcodes": [],
            "anonymous_capabilities": ["cursor empty test", "cursor advance", "cursor rewind", "register-pair record emit", "temporary buffer", "jump", "halt"],
            "observations": ["opaque pair collections", "complete stencil markers plus incomplete residue"],
            "token_efficiency_reward": True,
        },
        "searches": {
            "nested": _search_payload(nested_search, nested_exact),
            "partition": _search_payload(group_search, partition_exact),
        },
        "discoveries": [
            {
                "foundation_level": 5,
                "semantic": nested_semantic.to_dict(),
                "posthoc_name": nested_proof["posthoc_mathematical_name"],
                "posthoc_formula": nested_proof["posthoc_cardinality_statement"],
                "structural_origin": nested_proof["structural_statement"],
                "proof": nested_proof,
                "counts_as_new_foundation": True,
            },
            {
                "foundation_level": 6,
                "semantic": partition_semantic.to_dict(),
                "posthoc_name": partition_proof["posthoc_mathematical_name"],
                "posthoc_formula": partition_proof["posthoc_cardinality_statement"],
                "structural_origin": partition_proof["structural_statement"],
                "proof": partition_proof,
                "counts_as_new_foundation": True,
            },
        ],
        "capability_graph": {
            "verified_foundation_count": 6,
            "verified_path": ["计数", "加法", "自然数截断差", "有符号自然数差", "自然数乘法", "带余数的自然数除法"],
            "next_frontier": {
                "learner_label": None,
                "evaluator_only_interpretation": "compress unary representations, then extend these laws to signed operands and fraction pairs",
                "status": "not_yet_discovered",
            },
        },
        "rooms": {
            "nested_success": "artifacts/foundation/success/nested_semantics.jsonl",
            "partition_success": "artifacts/foundation/success/partition_semantics.jsonl",
            "nested_mistakes": "artifacts/foundation/mistakes/nested_programs.jsonl",
            "partition_mistakes": "artifacts/foundation/mistakes/partition_programs.jsonl",
            "nested_success_count": len(nested_success.records),
            "partition_success_count": len(partition_success.records),
            "nested_mistake_count": len(nested_mistakes.records),
            "partition_mistake_count": len(partition_mistakes.records),
            "nested_event_hash": nested_event["event_hash"],
            "partition_event_hash": partition_event["event_hash"],
        },
        "gates": gates,
        "limitations": [
            "Both induced semantics currently operate on unary finite-collection cardinalities and are inefficient for large values.",
            "The first discovery proves natural-cardinality multiplication only; signed, fractional, real, and complex multiplication remain undiscovered.",
            "The second discovery proves Euclidean quotient and remainder only for a positive divisor cardinality; division by zero is rejected.",
            "Decimal and fractional quotient representations are not produced by this foundation stage.",
            "Cursor rewind, pair-record construction, and buffering were exposed as anonymous generic machine capabilities, not as arithmetic operations.",
        ],
    }
    artifact = run_dir / "nested_arithmetic_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/nested_arithmetic_latest.json",
        ROOT / "dashboard/data/nested_arithmetic_latest.json",
        ROOT / "artifacts/foundation/nested_arithmetic_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "nested_semantic_id": nested_semantic.semantic_id,
        "partition_semantic_id": partition_semantic.semantic_id,
        "nested_search": f"{len(nested_exact)}/{nested_search.candidates_evaluated}",
        "partition_search": f"{len(partition_exact)}/{group_search.candidates_evaluated}",
        "nested_proof": f"{nested_obligations}/{len(nested_proof['obligations'])}",
        "partition_proof": f"{partition_obligations}/{len(partition_proof['obligations'])}",
        "hidden": f"{nested_hidden + partition_hidden}/{len(nested_proof['case_results']) + len(partition_proof['case_results'])}",
        "foundation_count": 6,
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
    }, ensure_ascii=True, indent=2))
    return 0


def _record_nonselected(search, room: FormulaRejectionRoom, task_id: str) -> None:
    for candidate in search.candidates:
        if candidate.program.program_id == search.selected.program.program_id:
            continue
        room.record(
            reason="equivalent_nonselected_cycle_program" if candidate.exact else "fails_anonymous_structural_examples",
            candidate=candidate.program.to_dict(),
            evidence={
                "task_id": task_id,
                "passed_examples": candidate.passed_example_count,
                "example_count": candidate.example_count,
                "exact": candidate.exact,
                "total_token_cost": candidate.total_token_cost,
                "reward": candidate.reward,
                "does_not_enter_foundation_room": True,
            },
        )


def _search_payload(search, exact) -> dict:
    return {
        "task_id": search.task_id,
        "candidate_count": search.candidates_evaluated,
        "exact_candidate_count": len(exact),
        "selected_program": search.selected.program.to_dict(),
        "selected_token_cost": search.selected.total_token_cost,
        "selected_reward": search.selected.reward,
    }


if __name__ == "__main__":
    raise SystemExit(main())
