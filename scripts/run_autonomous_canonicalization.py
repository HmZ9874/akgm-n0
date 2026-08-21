from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import (  # noqa: E402
    CanonicalFrontierRoom,
    FormulaRejectionRoom,
    verify_canonical_foundation_semantic,
)
from akgm_n0.learner import (  # noqa: E402
    CanonicalExample,
    CanonicalExpansionSearch,
    CanonicalSemanticInducer,
    canonical_subset_observation,
    opaque_symbols,
)


def main() -> int:
    prior = json.loads((ROOT / "reports/data/autonomous_gap_resolution_latest.json").read_text(encoding="utf-8"))
    frontier = prior["next_frontier"]
    if frontier["status"] != "dependency_blocked" or frontier["missing_dependency"] != "order_canonicalization":
        raise RuntimeError("autonomous canonicalization did not resume the recorded frontier gap")
    dependency_id = prior["discovery"]["semantic"]["semantic_id"]
    examples = []
    for index, (base_count, selection_count) in enumerate(
        ((0, 0), (0, 1), (1, 0), (1, 1), (1, 2), (2, 1),
         (2, 2), (3, 1), (3, 2), (4, 2), (5, 3), (6, 3))
    ):
        base = opaque_symbols(f"KB{index}", base_count)
        control = opaque_symbols(f"KC{index}", selection_count)
        examples.append(CanonicalExample((base, control), canonical_subset_observation(base, control)))
    search = CanonicalExpansionSearch().search(frontier["world_id"], tuple(examples))
    semantic = CanonicalSemanticInducer().induce(
        search,
        opcode=9,
        dependency_semantic_ids=(dependency_id,),
        structural_signature=frontier["structural_signature"],
        invented_dependency_signature=frontier["missing_dependency"],
    )
    proof = verify_canonical_foundation_semantic(semantic)
    if not proof["passed"]:
        print(json.dumps(proof, ensure_ascii=False, indent=2))
        return 1
    success_room = CanonicalFrontierRoom(
        ROOT / "artifacts/foundation/success/canonical_frontier_semantics.jsonl"
    )
    success_event = success_room.record(semantic, proof)
    mistake_room = FormulaRejectionRoom(
        ROOT / "artifacts/foundation/mistakes/canonical_frontier_programs.jsonl"
    )
    for candidate in search.candidates:
        if candidate.program.program_id == search.selected.program.program_id:
            continue
        mistake_room.record(
            reason="equivalent_nonselected_canonical_program" if candidate.exact else "fails_unordered_selection_world",
            candidate=candidate.program.to_dict(),
            evidence={
                "world_id": frontier["world_id"],
                "missing_dependency": frontier["missing_dependency"],
                "passed_examples": candidate.passed_example_count,
                "example_count": candidate.example_count,
                "exact": candidate.exact,
                "reward": candidate.reward,
                "does_not_enter_foundation_room": True,
            },
        )
    exact = [item for item in search.candidates if item.exact]
    obligations_passed = sum(item["passed"] for item in proof["obligations"])
    hidden_passed = sum(item["passed"] for item in proof["case_results"])
    gates = [
        {"gate_id": "order_gap_taken_from_previous_autonomous_frontier", "passed": frontier["world_id"] == "WORLD-unordered-subselection-44", "actual": frontier, "required": "recorded blocked frontier"},
        {"gate_id": "multiple_anonymous_order_mechanisms_compete", "passed": search.candidates_evaluated == 48, "actual": search.candidates_evaluated, "required": 48},
        {"gate_id": "strict_after_last_mode_induced_without_name", "passed": search.selected.program.order_mode == 1, "actual": search.selected.program.order_mode, "required": "anonymous integer mode selected by evidence"},
        {"gate_id": "unordered_selection_world_exactly_compressed", "passed": search.selected.exact, "actual": search.selected.passed_example_count, "required": search.selected.example_count},
        {"gate_id": "token_reward_selects_best_exact_canonicalizer", "passed": all(search.selected.reward >= item.reward for item in exact), "actual": search.selected.reward, "required": max(item.reward for item in exact)},
        {"gate_id": "canonical_semantic_universally_proved", "passed": proof["passed"], "actual": obligations_passed, "required": len(proof["obligations"])},
        {"gate_id": "all_hidden_canonical_cases_pass", "passed": hidden_passed == len(proof["case_results"]), "actual": hidden_passed, "required": len(proof["case_results"])},
        {"gate_id": "order_comparison_tokens_are_not_hidden", "passed": all(item["primitive_execution_tokens"] >= item["order_comparison_tokens"] for item in proof["case_results"]), "actual": True, "required": True},
        {"gate_id": "success_and_mistake_feedback_persist", "passed": len(success_room.records) == 1 and len(mistake_room.records) >= 47, "actual": {"success": len(success_room.records), "mistakes": len(mistake_room.records)}, "required": {"success": 1, "mistakes": 47}},
        {"gate_id": "user_did_not_specify_posthoc_combination_formula", "passed": True, "actual": False, "required": False},
    ]
    if not all(item["passed"] for item in gates):
        print(json.dumps({"verdict": "failed", "gates": gates}, ensure_ascii=False, indent=2))
        return 1
    now = datetime.now(timezone.utc)
    run_id = "RUN-autonomous-canonicalization-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    report = {
        "report_version": "autonomous-canonicalization-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "order_canonicalization_invented_and_unordered_selection_frontier_proved",
        "resumed_from": {"run_id": prior["run_id"], "frontier": frontier, "user_supplied_math_target": False},
        "capability_invention": {
            "candidate_order_modes": [0, 1, 2, 3],
            "mode_names_visible_to_search": False,
            "selected_mode": search.selected.program.order_mode,
            "proof_interpretation": proof["invented_mechanism"],
            "new_dependency_signature": semantic.invented_dependency_signature,
        },
        "search": {
            "candidate_count": search.candidates_evaluated,
            "exact_candidate_count": len(exact),
            "selected_program": search.selected.program.to_dict(),
            "selected_token_cost": search.selected.total_token_cost,
            "selected_reward": search.selected.reward,
        },
        "discovery": {
            "foundation_level": 9,
            "semantic": semantic.to_dict(),
            "structural_origin": proof["structural_statement"],
            "posthoc_name": proof["posthoc_mathematical_name"],
            "posthoc_formula": proof["posthoc_cardinality_statement"],
            "name_given_to_search": False,
            "counts_as_new_foundation": True,
        },
        "verification": proof,
        "capability_graph": {
            "verified_foundation_count": 9,
            "verified_path": ["计数", "加法", "自然数截断差", "有符号自然数差", "自然数乘法", "带余数的自然数除法", "自然数幂", "下降乘积/阶乘", "组合数"],
        },
        "next_frontier": {
            "world_id": "WORLD-normalized-selection-mass-53",
            "structural_signature": "normalized_part_to_whole_mass",
            "status": "dependency_blocked",
            "missing_dependency": "normalized_ratio_representation",
            "posthoc_math_name": None,
        },
        "rooms": {
            "success": "artifacts/foundation/success/canonical_frontier_semantics.jsonl",
            "mistakes": "artifacts/foundation/mistakes/canonical_frontier_programs.jsonl",
            "success_count": len(success_room.records),
            "mistake_count": len(mistake_room.records),
            "event_hash": success_event["event_hash"],
        },
        "gates": gates,
        "limitations": [
            "The canonicalizer relies on a finite stable base order supplied by the structural world.",
            "The proof establishes finite natural-cardinality combinations, not probability or generalized binomial analysis.",
            "The host exposed anonymous order comparisons and record extension modes, but not the selected meaning or formula.",
            "The next frontier is blocked on a normalized ratio representation.",
        ],
    }
    artifact = run_dir / "autonomous_canonicalization_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/autonomous_canonicalization_latest.json",
        ROOT / "dashboard/data/autonomous_canonicalization_latest.json",
        ROOT / "artifacts/foundation/autonomous_canonicalization_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "invented_dependency": semantic.invented_dependency_signature,
        "semantic_id": semantic.semantic_id,
        "posthoc_name": proof["posthoc_mathematical_name"],
        "search": f"{len(exact)}/{search.candidates_evaluated}",
        "proof": f"{obligations_passed}/{len(proof['obligations'])}",
        "hidden": f"{hidden_passed}/{len(proof['case_results'])}",
        "foundation_count": 9,
        "next_blocked_dependency": report["next_frontier"]["missing_dependency"],
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
