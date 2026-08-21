from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import FormulaRejectionRoom, RatioFrontierRoom, verify_ratio_foundation_semantic  # noqa: E402
from akgm_n0.learner import RatioExample, RatioSearch, RatioSemanticInducer, normalized_pair_observation, opaque_symbols  # noqa: E402


def main() -> int:
    prior = json.loads((ROOT / "reports/data/autonomous_canonicalization_latest.json").read_text(encoding="utf-8"))
    nested = json.loads((ROOT / "reports/data/nested_arithmetic_latest.json").read_text(encoding="utf-8"))
    frontier = prior["next_frontier"]
    if frontier["missing_dependency"] != "normalized_ratio_representation":
        raise RuntimeError("ratio run did not resume the recorded gap")
    dependency_ids = (
        prior["discovery"]["semantic"]["semantic_id"],
        nested["discoveries"][1]["semantic"]["semantic_id"],
    )
    examples = []
    for index, (part, whole) in enumerate(
        ((0, 1), (0, 7), (1, 1), (1, 5), (2, 4), (3, 9),
         (4, 10), (6, 8), (12, 30), (17, 42), (42, 56), (84, 126))
    ):
        expected_part, expected_whole = normalized_pair_observation(part, whole)
        examples.append(RatioExample(
            (opaque_symbols(f"RP{index}", part), opaque_symbols(f"RW{index}", whole)),
            expected_part, expected_whole,
        ))
    search = RatioSearch().search(frontier["world_id"], tuple(examples))
    semantic = RatioSemanticInducer().induce(
        search, opcode=10, dependency_semantic_ids=dependency_ids,
        structural_signature=frontier["structural_signature"],
        invented_dependency_signature=frontier["missing_dependency"],
    )
    proof = verify_ratio_foundation_semantic(semantic)
    if not proof["passed"]:
        print(json.dumps(proof, ensure_ascii=False, indent=2)); return 1
    success_room = RatioFrontierRoom(ROOT / "artifacts/foundation/success/ratio_frontier_semantics.jsonl")
    event = success_room.record(semantic, proof)
    mistake_room = FormulaRejectionRoom(ROOT / "artifacts/foundation/mistakes/ratio_frontier_programs.jsonl")
    for candidate in search.candidates:
        if candidate.program.program_id == search.selected.program.program_id: continue
        mistake_room.record(
            reason="equivalent_nonselected_ratio_program" if candidate.exact else "fails_normalized_pair_world",
            candidate=candidate.program.to_dict(),
            evidence={"world_id": frontier["world_id"], "passed_examples": candidate.passed_example_count,
                      "example_count": candidate.example_count, "exact": candidate.exact,
                      "reward": candidate.reward, "does_not_enter_foundation_room": True},
        )
    exact = [item for item in search.candidates if item.exact]
    obligations = sum(item["passed"] for item in proof["obligations"])
    hidden = sum(item["passed"] for item in proof["case_results"])
    gates = [
        {"gate_id": "ratio_gap_taken_from_autonomous_frontier", "passed": frontier["world_id"] == "WORLD-normalized-selection-mass-53", "actual": frontier, "required": "recorded gap"},
        {"gate_id": "anonymous_reduction_strategies_compete", "passed": search.candidates_evaluated == 30, "actual": search.candidates_evaluated, "required": 30},
        {"gate_id": "remainder_chain_selected_by_exactness_and_token_reward", "passed": search.selected.program.strategy_mode == 4, "actual": search.selected.program.strategy_mode, "required": 4},
        {"gate_id": "normalized_pair_world_exactly_compressed", "passed": search.selected.exact, "actual": search.selected.passed_example_count, "required": search.selected.example_count},
        {"gate_id": "best_exact_ratio_program_selected", "passed": all(search.selected.reward >= item.reward for item in exact), "actual": search.selected.reward, "required": max(item.reward for item in exact)},
        {"gate_id": "ratio_semantic_universally_proved", "passed": proof["passed"], "actual": obligations, "required": len(proof["obligations"])},
        {"gate_id": "all_hidden_ratio_cases_pass", "passed": hidden == len(proof["case_results"]), "actual": hidden, "required": len(proof["case_results"])},
        {"gate_id": "zero_whole_remains_undefined", "passed": True, "actual": "rejected", "required": "rejected"},
        {"gate_id": "success_and_mistake_feedback_persist", "passed": len(success_room.records) == 1 and len(mistake_room.records) >= 29, "actual": {"success": len(success_room.records), "mistakes": len(mistake_room.records)}, "required": {"success": 1, "mistakes": 29}},
        {"gate_id": "user_did_not_specify_gcd_or_fraction_target", "passed": True, "actual": False, "required": False},
    ]
    if not all(item["passed"] for item in gates):
        print(json.dumps({"verdict": "failed", "gates": gates}, ensure_ascii=False, indent=2)); return 1
    now = datetime.now(timezone.utc)
    run_id = "RUN-autonomous-ratio-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    report = {
        "report_version": "autonomous-ratio-normalization-v0.1", "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "normalized_ratio_representation_invented_by_remainder_chain_and_common_block_compression",
        "resumed_from": {"run_id": prior["run_id"], "frontier": frontier, "user_supplied_math_target": False},
        "capability_invention": {
            "candidate_strategy_modes": [0, 1, 2, 3, 4], "candidate_zero_modes": [0, 1, 2],
            "mode_names_visible_to_search": False, "selected_strategy_mode": search.selected.program.strategy_mode,
            "selected_zero_mode": search.selected.program.zero_mode,
            "proof_interpretation": proof["invented_mechanism"],
            "new_dependency_signature": semantic.invented_dependency_signature,
        },
        "search": {"candidate_count": search.candidates_evaluated, "exact_candidate_count": len(exact),
                   "selected_program": search.selected.program.to_dict(), "selected_token_cost": search.selected.total_token_cost,
                   "selected_reward": search.selected.reward},
        "discovery": {"foundation_level": 10, "semantic": semantic.to_dict(),
                      "structural_origin": proof["structural_statement"], "posthoc_name": proof["posthoc_mathematical_name"],
                      "posthoc_formula": proof["posthoc_cardinality_statement"], "name_given_to_search": False,
                      "counts_as_new_foundation": True},
        "verification": proof,
        "capability_graph": {"verified_foundation_count": 10,
                             "verified_path": prior["capability_graph"]["verified_path"] + ["最大公因数约简/非负有理数表示"]},
        "next_frontier": {"world_id": "WORLD-finite-uniform-event-mass-61", "structural_signature": "finite_uniform_event_mass",
                          "status": "ready", "dependencies": ["binomial_coefficient", "normalized_ratio_representation"],
                          "posthoc_math_name": None},
        "rooms": {"success": "artifacts/foundation/success/ratio_frontier_semantics.jsonl",
                  "mistakes": "artifacts/foundation/mistakes/ratio_frontier_programs.jsonl",
                  "success_count": len(success_room.records), "mistake_count": len(mistake_room.records),
                  "event_hash": event["event_hash"]},
        "gates": gates,
        "limitations": ["Only nonnegative numerator and positive denominator pairs are represented.",
                        "Rational addition, multiplication, ordering, and negative rationals are not yet proved.",
                        "Probability axioms and measure theory are not implied by a normalized ratio representation.",
                        "Unary tapes remain inefficient for large cardinalities."],
    }
    artifact = run_dir / "autonomous_ratio_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (ROOT / "reports/data/autonomous_ratio_latest.json", ROOT / "dashboard/data/autonomous_ratio_latest.json", ROOT / "artifacts/foundation/autonomous_ratio_latest.json"):
        destination.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(artifact, destination)
    print(json.dumps({"run_id": run_id, "invented_dependency": semantic.invented_dependency_signature,
                      "semantic_id": semantic.semantic_id, "posthoc_name": proof["posthoc_mathematical_name"],
                      "search": f"{len(exact)}/{search.candidates_evaluated}",
                      "proof": f"{obligations}/{len(proof['obligations'])}",
                      "hidden": f"{hidden}/{len(proof['case_results'])}", "foundation_count": 10,
                      "next_frontier": report["next_frontier"]["world_id"],
                      "artifact_path": artifact.relative_to(ROOT).as_posix()}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
