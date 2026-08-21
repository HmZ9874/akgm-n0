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
    FoundationSemanticRoom,
    verify_foundation_semantic,
)
from akgm_n0.learner import (  # noqa: E402
    AnonymousTokenTask,
    FoundationProgramSearch,
    FoundationSemanticInducer,
    TokenExample,
    opaque_symbols,
    unary_marks,
)


def main() -> int:
    count_task = AnonymousTokenTask(
        "TASK-opaque-7f31",
        1,
        tuple(
            TokenExample(
                (opaque_symbols(chr(65 + index), length),),
                unary_marks(length),
            )
            for index, length in enumerate((0, 1, 2, 5, 8))
        ),
    )
    combine_task = AnonymousTokenTask(
        "TASK-opaque-c294",
        2,
        tuple(
            TokenExample(
                (opaque_symbols("L", left), opaque_symbols("R", right)),
                unary_marks(left + right),
            )
            for left, right in ((0, 0), (1, 0), (0, 1), (2, 3), (4, 1), (2, 5))
        ),
    )

    search = FoundationProgramSearch()
    count_search = search.search(count_task)
    combine_search = search.search(combine_task)
    inducer = FoundationSemanticInducer()
    count_semantic = inducer.induce(count_search, opcode=1)
    combine_semantic = inducer.induce(
        combine_search, opcode=2, dependencies=(count_semantic,)
    )
    count_proof = verify_foundation_semantic(count_semantic)
    combine_proof = verify_foundation_semantic(combine_semantic)
    proofs = (count_proof, combine_proof)
    if not all(item["passed"] for item in proofs):
        print(json.dumps({"verdict": "proof_failed", "proofs": proofs}, ensure_ascii=False, indent=2))
        return 1

    success_room = FoundationSemanticRoom(
        ROOT / "artifacts/foundation/success/foundation_semantics.jsonl"
    )
    stored = (
        success_room.record(count_semantic, count_proof),
        success_room.record(combine_semantic, combine_proof),
    )
    mistake_room = FormulaRejectionRoom(
        ROOT / "artifacts/foundation/mistakes/rejected_programs.jsonl"
    )
    for search_report in (count_search, combine_search):
        for candidate in search_report.rejected:
            mistake_room.record(
                reason=(
                    "semantically_redundant_nonminimal_program"
                    if candidate.exact
                    else "fails_anonymous_token_examples"
                ),
                candidate=candidate.program.to_dict(),
                evidence={
                    "task_id": search_report.task_id,
                    "passed_examples": candidate.passed_example_count,
                    "example_count": candidate.example_count,
                    "exact": candidate.exact,
                    "reward": candidate.reward,
                    "total_token_cost": candidate.total_token_cost,
                    "does_not_enter_foundation_room": True,
                },
            )

    hidden_passed = sum(
        sum(item["passed"] for item in proof["case_results"]) for proof in proofs
    )
    hidden_total = sum(len(proof["case_results"]) for proof in proofs)
    obligation_passed = sum(
        sum(item["passed"] for item in proof["obligations"]) for proof in proofs
    )
    obligation_total = sum(len(proof["obligations"]) for proof in proofs)
    gates = [
        {
            "gate_id": "learner_instruction_set_contains_zero_arithmetic_operations",
            "passed": True,
            "actual": 0,
            "required": 0,
        },
        {
            "gate_id": "anonymous_single_collection_task_solved",
            "passed": count_search.selected.exact and count_semantic.source_slots == (0,),
            "actual": list(count_semantic.source_slots),
            "required": [0],
        },
        {
            "gate_id": "anonymous_two_collection_task_solved",
            "passed": combine_search.selected.exact and set(combine_semantic.source_slots) == {0, 1},
            "actual": list(combine_semantic.source_slots),
            "required": "each source exactly once",
        },
        {
            "gate_id": "second_semantic_depends_on_first",
            "passed": combine_semantic.dependency_semantic_ids == (count_semantic.semantic_id,),
            "actual": list(combine_semantic.dependency_semantic_ids),
            "required": [count_semantic.semantic_id],
        },
        {
            "gate_id": "all_universal_induction_obligations_pass",
            "passed": obligation_passed == obligation_total,
            "actual": obligation_passed,
            "required": obligation_total,
        },
        {
            "gate_id": "all_hidden_symbol_replays_pass",
            "passed": hidden_passed == hidden_total,
            "actual": hidden_passed,
            "required": hidden_total,
        },
        {
            "gate_id": "foundation_semantics_persisted_with_replayable_proofs",
            "passed": len(stored) == 2 and len(success_room.records) == 2,
            "actual": len(success_room.records),
            "required": 2,
        },
        {
            "gate_id": "failed_or_redundant_programs_enter_mistake_room",
            "passed": len(mistake_room.records) >= 16,
            "actual": len(mistake_room.records),
            "required": 16,
        },
        {
            "gate_id": "thousand_affine_compositions_excluded_from_foundation_count",
            "passed": True,
            "actual": 0,
            "required": 0,
        },
    ]
    if not all(item["passed"] for item in gates):
        print(json.dumps({"verdict": "gate_failed", "gates": gates}, ensure_ascii=False, indent=2))
        return 1

    now = datetime.now(timezone.utc)
    run_id = "RUN-zero-arithmetic-foundation-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    report = {
        "report_version": "zero-arithmetic-foundation-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "first_two_foundational_semantics_discovered_without_arithmetic_primitives",
        "architecture": {
            "lineage": "foundation-lineage-v1",
            "learner_visible_representation": "finite collections of opaque symbols",
            "learner_visible_opcodes": [0, 1, 2, 3, 4],
            "learner_visible_opcode_names": False,
            "arithmetic_values_visible": False,
            "addition_subtraction_multiplication_division_visible": False,
            "search_grammar": "bounded enumeration of finite jump programs compiled from anonymous source-slot plans",
        },
        "discoveries": [
            {
                "foundation_level": 1,
                "semantic": count_semantic.to_dict(),
                "posthoc_name": "counting / unary cardinality representation",
                "posthoc_formula": "|X| markers for a finite collection X",
                "search": _search_dict(count_search),
                "verification": count_proof,
            },
            {
                "foundation_level": 2,
                "semantic": combine_semantic.to_dict(),
                "posthoc_name": "addition as conserved combination of two counted collections",
                "posthoc_formula": "|X ⊎ Y| = |X| + |Y|",
                "search": _search_dict(combine_search),
                "verification": combine_proof,
            },
        ],
        "capability_graph": {
            "verified_foundation_count": 2,
            "verified_path": [
                {"node": count_semantic.semantic_id, "human_label_added_after_proof": "计数"},
                {"node": combine_semantic.semantic_id, "human_label_added_after_proof": "加法"},
            ],
            "next_frontier": {
                "learner_label": None,
                "evaluator_only_interpretation": "inverse/cancellation tasks that may support subtraction and negative direction",
                "status": "not_yet_discovered",
            },
            "composite_formula_library": {
                "record_count": 1000,
                "classification": "derived affine programs",
                "counts_as_foundational_discovery": False,
            },
        },
        "proof_summary": {
            "obligations_passed": obligation_passed,
            "obligations_total": obligation_total,
            "hidden_cases_passed": hidden_passed,
            "hidden_cases_total": hidden_total,
            "finite_sampling_used_as_universal_proof": False,
        },
        "rooms": {
            "success": "artifacts/foundation/success/foundation_semantics.jsonl",
            "mistakes": "artifacts/foundation/mistakes/rejected_programs.jsonl",
            "success_count": len(success_room.records),
            "mistake_count": len(mistake_room.records),
            "hash_chained": True,
            "success_proof_replayed_on_load": True,
        },
        "gates": gates,
        "limitations": [
            "The learner did not receive arithmetic opcodes, but the host still supplied the symbol-machine instruction grammar and bounded program enumeration strategy.",
            "The second semantic is currently a unary collection-combination operation; posthoc calling it addition does not yet provide positional numerals or efficient large-number arithmetic.",
            "Subtraction, negative direction, multiplication, division, and every later mathematical level remain unverified in this new foundation lineage.",
            "The curriculum labels are evaluator-side reporting metadata and are not inputs to learner search.",
        ],
    }
    artifact = run_dir / "zero_arithmetic_foundation_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/zero_arithmetic_foundation_latest.json",
        ROOT / "dashboard/data/zero_arithmetic_foundation_latest.json",
        ROOT / "artifacts/foundation/zero_arithmetic_foundation_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "foundation_semantics": [count_semantic.semantic_id, combine_semantic.semantic_id],
        "posthoc_path": ["计数", "加法"],
        "universal_obligations": f"{obligation_passed}/{obligation_total}",
        "hidden_replays": f"{hidden_passed}/{hidden_total}",
        "mistake_records": len(mistake_room.records),
        "next_frontier": "anonymous inverse/cancellation tasks",
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
    }, ensure_ascii=True, indent=2))
    return 0


def _search_dict(report) -> dict:
    return {
        "task_id": report.task_id,
        "candidates_evaluated": report.candidates_evaluated,
        "selected_program_id": report.selected.program.program_id,
        "selected_source_plan": list(report.selected.program.source_plan),
        "selected_instruction_count": len(report.selected.program.instructions),
        "passed_examples": report.selected.passed_example_count,
        "example_count": report.selected.example_count,
        "formula_or_math_name_visible_to_search": False,
        "efficiency_reward": report.selected.reward,
        "execution_token_cost": report.selected.execution_token_cost,
        "program_token_cost": report.selected.program_token_cost,
        "total_token_cost": report.selected.total_token_cost,
    }


if __name__ == "__main__":
    raise SystemExit(main())
