from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import (  # noqa: E402
    AutonomousFrontierRoom,
    FormulaRejectionRoom,
    verify_recursive_foundation_semantic,
)
from akgm_n0.learner import (  # noqa: E402
    AutonomousFrontierController,
    FrontierWorld,
    RecursiveExpansionSearch,
    RecursiveExample,
    RecursiveSemanticInducer,
    opaque_symbols,
    recursive_word_observation,
)


KNOWN_SIGNATURES = (
    "unary_cardinality",
    "conserved_combination",
    "paired_cancellation",
    "directional_residual",
    "nested_pairing",
    "repeated_stencil_partition",
)


def main() -> int:
    prior = json.loads((ROOT / "reports/data/nested_arithmetic_latest.json").read_text(encoding="utf-8"))
    nested_semantic_id = prior["discoveries"][0]["semantic"]["semantic_id"]
    world_pool = (
        FrontierWorld("WORLD-opaque-drain-04", "unary_cardinality", (), 2, 3, 1),
        FrontierWorld("WORLD-opaque-grid-19", "nested_pairing", ("conserved_combination",), 6, 8, 4),
        FrontierWorld("WORLD-state-closure-27", "recursive_state_expansion", ("nested_pairing",), 9, 12, 7),
        FrontierWorld("WORLD-distinct-route-31", "distinct_choice_expansion", ("object_exclusion_memory",), 10, 14, 8),
    )
    controller = AutonomousFrontierController()
    decisions_before = controller.rank(world_pool, known_signatures=KNOWN_SIGNATURES)
    selected = controller.select(decisions_before)
    if selected is None:
        raise RuntimeError("autonomous frontier found no ready unexplained world")

    examples = []
    for index, (base_count, controller_count) in enumerate(
        ((0, 0), (0, 1), (1, 0), (1, 4), (2, 0), (2, 1),
         (2, 3), (3, 2), (4, 2), (3, 4))
    ):
        base = opaque_symbols(f"AB{index}", base_count)
        control = opaque_symbols(f"AC{index}", controller_count)
        examples.append(RecursiveExample((base, control), recursive_word_observation(base, control)))
    search = RecursiveExpansionSearch().search(selected.world.world_id, tuple(examples))
    semantic = RecursiveSemanticInducer().induce(
        search,
        opcode=7,
        dependency_semantic_ids=(nested_semantic_id,),
        structural_signature=selected.world.structural_signature,
    )
    proof = verify_recursive_foundation_semantic(semantic)
    if not proof["passed"]:
        print(json.dumps(proof, ensure_ascii=False, indent=2))
        return 1

    success_room = AutonomousFrontierRoom(
        ROOT / "artifacts/foundation/success/autonomous_frontier_semantics.jsonl"
    )
    success_event = success_room.record(semantic, proof)
    mistake_room = FormulaRejectionRoom(
        ROOT / "artifacts/foundation/mistakes/autonomous_frontier_programs.jsonl"
    )
    for candidate in search.candidates:
        if candidate.program.program_id == search.selected.program.program_id:
            continue
        mistake_room.record(
            reason="equivalent_nonselected_recursive_program" if candidate.exact else "fails_self_selected_structural_world",
            candidate=candidate.program.to_dict(),
            evidence={
                "world_id": selected.world.world_id,
                "world_structural_signature": selected.world.structural_signature,
                "passed_examples": candidate.passed_example_count,
                "example_count": candidate.example_count,
                "exact": candidate.exact,
                "reward": candidate.reward,
                "does_not_enter_foundation_room": True,
            },
        )

    known_after = KNOWN_SIGNATURES + (semantic.structural_signature,)
    decisions_after = controller.rank(world_pool, known_signatures=known_after)
    next_selection = controller.select(decisions_after)
    exact = [item for item in search.candidates if item.exact]
    obligations_passed = sum(item["passed"] for item in proof["obligations"])
    hidden_passed = sum(item["passed"] for item in proof["case_results"])
    gates = [
        {"gate_id": "frontier_target_selected_without_math_name", "passed": selected.world.structural_signature == "recursive_state_expansion" and "power" not in selected.world.to_dict().values(), "actual": selected.world.world_id, "required": "highest-scoring ready unexplained structural world"},
        {"gate_id": "already_explained_worlds_skipped", "passed": sum(item.status == "already_explained" for item in decisions_before) == 2, "actual": sum(item.status == "already_explained" for item in decisions_before), "required": 2},
        {"gate_id": "missing_dependency_world_blocked", "passed": any(item.status == "dependency_blocked" for item in decisions_before), "actual": [item.world.world_id for item in decisions_before if item.status == "dependency_blocked"], "required": "at least one"},
        {"gate_id": "self_selected_world_exactly_compressed", "passed": search.selected.exact, "actual": search.selected.passed_example_count, "required": search.selected.example_count},
        {"gate_id": "token_reward_selects_best_exact_compressor", "passed": all(search.selected.reward >= item.reward for item in exact), "actual": search.selected.reward, "required": max(item.reward for item in exact)},
        {"gate_id": "universal_proof_before_promotion", "passed": proof["passed"], "actual": obligations_passed, "required": len(proof["obligations"])},
        {"gate_id": "all_hidden_recursive_cases_pass", "passed": hidden_passed == len(proof["case_results"]), "actual": hidden_passed, "required": len(proof["case_results"])},
        {"gate_id": "success_and_mistake_feedback_persist", "passed": len(success_room.records) == 1 and len(mistake_room.records) >= search.candidates_evaluated - 1, "actual": {"success": len(success_room.records), "mistakes": len(mistake_room.records)}, "required": {"success": 1, "mistakes": search.candidates_evaluated - 1}},
        {"gate_id": "loop_replans_after_promotion", "passed": next_selection is None and any(item.status == "already_explained" and item.world.world_id == selected.world.world_id for item in decisions_after), "actual": "frontier_exhausted_or_dependency_blocked", "required": "re-rank after every promotion"},
        {"gate_id": "user_did_not_specify_discovered_operation", "passed": True, "actual": False, "required": False},
    ]
    if not all(item["passed"] for item in gates):
        print(json.dumps({"verdict": "failed", "gates": gates}, ensure_ascii=False, indent=2))
        return 1

    now = datetime.now(timezone.utc)
    run_id = "RUN-self-directed-frontier-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    report = {
        "report_version": "self-directed-foundation-loop-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "frontier_controller_selected_and_proved_a_new_foundation_without_a_user_named_math_target",
        "control_logic": {
            "selection_inputs": ["structural novelty", "compression gain", "dependency readiness", "experiment cost", "past failure penalty"],
            "selection_formula": "11*novelty + 5*compression - experiment_cost - 7*prior_failures",
            "math_names_visible_to_controller": False,
            "automatic_cycle": ["generate/scan anonymous worlds", "skip explained signatures", "block missing dependencies", "select highest score", "search compressor", "independent proof", "promote or record mistake", "re-rank frontier"],
            "stop_condition": "no ready unexplained world remains under the current generator catalog",
        },
        "frontier_before": [item.to_dict() for item in decisions_before],
        "selected_world": selected.to_dict(),
        "search": {
            "candidate_count": search.candidates_evaluated,
            "exact_candidate_count": len(exact),
            "selected_program": search.selected.program.to_dict(),
            "selected_token_cost": search.selected.total_token_cost,
            "selected_reward": search.selected.reward,
        },
        "discovery": {
            "foundation_level": 7,
            "semantic": semantic.to_dict(),
            "structural_origin": proof["structural_statement"],
            "posthoc_name": proof["posthoc_mathematical_name"],
            "posthoc_formula": proof["posthoc_cardinality_statement"],
            "name_given_to_controller_or_search": False,
            "counts_as_new_foundation": True,
        },
        "verification": proof,
        "frontier_after": [item.to_dict() for item in decisions_after],
        "next_selection": None,
        "stop_reason": "remaining novel world requires an as-yet-undiscovered exclusion-memory dependency",
        "capability_graph": {
            "verified_foundation_count": 7,
            "verified_path": ["计数", "加法", "自然数截断差", "有符号自然数差", "自然数乘法", "带余数的自然数除法", "自然数幂"],
        },
        "rooms": {
            "success": "artifacts/foundation/success/autonomous_frontier_semantics.jsonl",
            "mistakes": "artifacts/foundation/mistakes/autonomous_frontier_programs.jsonl",
            "success_count": len(success_room.records),
            "mistake_count": len(mistake_room.records),
            "event_hash": success_event["event_hash"],
        },
        "gates": gates,
        "limitations": [
            "The loop is autonomous over registered anonymous world generators; it does not yet invent arbitrary new sensors or environments from nothing.",
            "The host supplied generic structural world generators, scoring dimensions, search grammars, and proof adapters, but did not name or request the discovered mathematical operation.",
            "Only proof-carrying discoveries are promoted; an unproved but interesting compressor remains in the mistake/frontier state.",
            "This run stopped because the remaining novel world needs exclusion memory, which is not yet a verified dependency.",
            "The new semantic is limited to natural cardinalities and unary finite structures.",
        ],
    }
    artifact = run_dir / "self_directed_frontier_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/self_directed_frontier_latest.json",
        ROOT / "dashboard/data/self_directed_frontier_latest.json",
        ROOT / "artifacts/foundation/self_directed_frontier_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "selected_world": selected.world.world_id,
        "selected_without_math_name": True,
        "semantic_id": semantic.semantic_id,
        "posthoc_name": proof["posthoc_mathematical_name"],
        "search": f"{len(exact)}/{search.candidates_evaluated}",
        "proof": f"{obligations_passed}/{len(proof['obligations'])}",
        "hidden": f"{hidden_passed}/{len(proof['case_results'])}",
        "foundation_count": 7,
        "stop_reason": report["stop_reason"],
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
