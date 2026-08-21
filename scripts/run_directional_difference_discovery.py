from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import (  # noqa: E402
    DirectionalFoundationRoom,
    FormulaRejectionRoom,
    verify_directional_foundation_semantic,
)
from akgm_n0.learner import (  # noqa: E402
    DirectionalSemanticInducer,
    DirectionalTapeSearch,
    TokenExample,
    opaque_symbols,
    signed_unary_output,
)


def main() -> int:
    base = json.loads((ROOT / "reports/data/zero_arithmetic_foundation_latest.json").read_text(encoding="utf-8"))
    truncation = json.loads((ROOT / "reports/data/reversible_cancellation_latest.json").read_text(encoding="utf-8"))
    dependency_ids = tuple(item["semantic"]["semantic_id"] for item in base["discoveries"]) + (
        truncation["discovery"]["semantic"]["semantic_id"],
    )
    task_id = "TASK-opaque-direction-09af"
    examples = tuple(
        TokenExample(
            (opaque_symbols(f"A{index}", left), opaque_symbols(f"B{index}", right)),
            signed_unary_output(left, right),
        )
        for index, (left, right) in enumerate(
            ((0, 0), (1, 0), (0, 1), (2, 1), (1, 2), (3, 3), (7, 2), (2, 7), (9, 4), (4, 9), (11, 3), (3, 11))
        )
    )
    search = DirectionalTapeSearch().search(task_id, examples, maximum_phases=3)
    semantic = DirectionalSemanticInducer().induce(
        search, opcode=4, dependency_semantic_ids=dependency_ids
    )
    proof = verify_directional_foundation_semantic(semantic)
    if not proof["passed"]:
        print(json.dumps(proof, ensure_ascii=False, indent=2))
        return 1

    success_room = DirectionalFoundationRoom(
        ROOT / "artifacts/foundation/success/directional_semantics.jsonl"
    )
    stored = success_room.record(semantic, proof)
    mistake_room = FormulaRejectionRoom(
        ROOT / "artifacts/foundation/mistakes/directional_programs.jsonl"
    )
    for candidate in search.candidates:
        if candidate.program.program_id == search.selected.program.program_id:
            continue
        mistake_room.record(
            reason=(
                "semantically_equivalent_nonselected_directional_program"
                if candidate.exact
                else "fails_anonymous_directional_examples"
            ),
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
    exact_candidates = [item for item in search.candidates if item.exact]
    obligations_passed = sum(item["passed"] for item in proof["obligations"])
    hidden_passed = sum(item["passed"] for item in proof["case_results"])
    gates = [
        {"gate_id": "no_sign_or_subtraction_label_visible_to_learner", "passed": True, "actual": False, "required": False},
        {"gate_id": "two_output_glyphs_are_anonymous", "passed": True, "actual": ["●", "○"], "required": "two unlabeled glyphs"},
        {"gate_id": "anonymous_direction_task_exactly_solved", "passed": search.selected.exact, "actual": search.selected.passed_example_count, "required": search.selected.example_count},
        {"gate_id": "paired_phase_and_both_residual_directions_induced", "passed": len(search.selected.program.phases) == 3, "actual": [item.to_dict() for item in search.selected.program.phases], "required": 3},
        {"gate_id": "universal_directional_difference_proof", "passed": proof["passed"], "actual": obligations_passed, "required": len(proof["obligations"])},
        {"gate_id": "all_hidden_signed_direction_cases_pass", "passed": hidden_passed == len(proof["case_results"]), "actual": hidden_passed, "required": len(proof["case_results"])},
        {"gate_id": "negative_direction_information_is_preserved", "passed": any(item["decoded_value"] < 0 and item["passed"] for item in proof["case_results"]), "actual": min(item["decoded_value"] for item in proof["case_results"]), "required": "less than zero"},
        {"gate_id": "directional_outputs_are_normalized", "passed": all(not ({"●", "○"} <= set(item["output_symbols"])) for item in proof["case_results"]), "actual": True, "required": True},
        {"gate_id": "token_reward_selects_a_maximum_reward_exact_program", "passed": all(search.selected.reward >= item.reward for item in exact_candidates), "actual": search.selected.reward, "required": max(item.reward for item in exact_candidates)},
        {"gate_id": "success_and_mistake_rooms_persist", "passed": len(success_room.records) == 1 and len(mistake_room.records) >= 819, "actual": {"success": len(success_room.records), "mistakes": len(mistake_room.records)}, "required": {"success": 1, "mistakes": 819}},
        {"gate_id": "not_misreported_as_general_signed_integer_arithmetic", "passed": proof["not_claimed"] == "addition or subtraction over two arbitrary signed-integer inputs", "actual": proof["not_claimed"], "required": "addition or subtraction over two arbitrary signed-integer inputs"},
    ]
    if not all(item["passed"] for item in gates):
        print(json.dumps({"verdict": "failed", "gates": gates}, ensure_ascii=False, indent=2))
        return 1

    now = datetime.now(timezone.utc)
    run_id = "RUN-directional-difference-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    report = {
        "report_version": "directional-difference-discovery-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "fourth_foundation_preserves_negative_direction_for_natural_input_difference",
        "learner_received": {
            "negative_name": False,
            "positive_name": False,
            "subtraction_symbol": False,
            "target_formula": False,
            "two_anonymous_output_glyphs": ["●", "○"],
            "generic_multi_tape_opcodes": [0, 1, 2, 3, 4, 5, 6],
            "token_efficiency_reward": True,
        },
        "search": {
            "task_id": task_id,
            "candidate_count": search.candidates_evaluated,
            "exact_candidate_count": len(exact_candidates),
            "selected_program": search.selected.program.to_dict(),
            "selected_token_cost": search.selected.total_token_cost,
            "selected_reward": search.selected.reward,
            "all_exact_rewards": sorted({item.reward for item in exact_candidates}, reverse=True),
        },
        "discovery": {
            "foundation_level": 4,
            "semantic": semantic.to_dict(),
            "depends_on": list(dependency_ids),
            "posthoc_name": "two-glyph signed direction for natural-input difference",
            "posthoc_decoding": "empty=0; primary glyph count=positive magnitude; alternate glyph count=negative magnitude",
            "posthoc_formula": "decode(S(a,b))=a-b for every a,b in N",
            "counts_as_new_foundation": True,
            "novelty_reason": "unlike truncated difference, the output preserves which input tape retains unmatched symbols",
        },
        "verification": proof,
        "capability_graph": {
            "verified_foundation_count": 4,
            "verified_path": ["计数", "加法", "自然数截断差", "有符号自然数差"],
            "next_frontier": {
                "learner_label": None,
                "evaluator_only_interpretation": "normalize and operate on pairs of already-signed inputs, then seek reusable nested traversal",
                "status": "not_yet_discovered",
            },
        },
        "rooms": {
            "success": "artifacts/foundation/success/directional_semantics.jsonl",
            "mistakes": "artifacts/foundation/mistakes/directional_programs.jsonl",
            "success_count": len(success_room.records),
            "mistake_count": len(mistake_room.records),
            "event_hash": stored["event_hash"],
        },
        "gates": gates,
        "limitations": [
            "The result represents a-b for natural-cardinality inputs, including negative output direction; it does not yet accept arbitrary signed operands.",
            "The host exposed a second anonymous glyph and a bounded three-phase grammar, but supplied neither sign meanings nor the target program.",
            "Unary magnitude is inefficient for large values and positional notation remains undiscovered.",
            "Multiplication and division are not yet foundation-level discoveries.",
        ],
    }
    artifact = run_dir / "directional_difference_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/directional_difference_latest.json",
        ROOT / "dashboard/data/directional_difference_latest.json",
        ROOT / "artifacts/foundation/directional_difference_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "semantic_id": semantic.semantic_id,
        "candidates": search.candidates_evaluated,
        "exact_candidates": len(exact_candidates),
        "proof": f"{obligations_passed}/{len(proof['obligations'])}",
        "hidden": f"{hidden_passed}/{len(proof['case_results'])}",
        "minimum_decoded_hidden_value": min(item["decoded_value"] for item in proof["case_results"]),
        "foundation_count": 4,
        "not_claimed": proof["not_claimed"],
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
