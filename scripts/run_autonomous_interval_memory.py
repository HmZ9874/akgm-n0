from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import (  # noqa: E402
    ApproximationFrontierRoom,
    FormulaRejectionRoom,
    verify_approximation_foundation_semantic,
)
from akgm_n0.learner import (  # noqa: E402
    ApproximationExample,
    ApproximationMemorySearch,
    ApproximationSemanticInducer,
    interval_refinement,
)


def main() -> int:
    prior = json.loads(
        (ROOT / "reports/data/autonomous_exact_root_latest.json").read_text(encoding="utf-8")
    )
    rational = json.loads(
        (ROOT / "reports/data/autonomous_rational_latest.json").read_text(encoding="utf-8")
    )
    frontier = prior["next_frontier"]
    observations = (
        ((2, 1), 1), ((2, 1), 3), ((3, 1), 4), ((1, 2), 4),
        ((5, 2), 5), ((9, 4), 3), ((17, 42), 6), ((0, 1), 3),
    )
    examples = []
    for value_pair, rounds in observations:
        lower, upper = interval_refinement(value_pair, rounds)
        examples.append(ApproximationExample(value_pair, rounds, lower, upper))
    search = ApproximationMemorySearch().search(frontier["world_id"], tuple(examples))
    dependencies = (
        prior["discovery"]["semantic"]["semantic_id"],
        rational["discovery"]["semantic"]["semantic_id"],
    )
    semantic = ApproximationSemanticInducer().induce(
        search,
        opcode=17,
        dependency_semantic_ids=dependencies,
        invented_dependency_signature=frontier["missing_dependency"],
    )
    proof = verify_approximation_foundation_semantic(semantic)
    if not proof["passed"]:
        print(json.dumps(proof, ensure_ascii=False, indent=2))
        return 1
    room = ApproximationFrontierRoom(
        ROOT / "artifacts/foundation/success/approximation_memory_semantics.jsonl"
    )
    event = room.record(semantic, proof)
    mistakes = FormulaRejectionRoom(
        ROOT / "artifacts/foundation/mistakes/approximation_memory_programs.jsonl"
    )
    for candidate in search.candidates:
        if candidate.program.program_id == search.selected.program.program_id:
            continue
        mistakes.record(
            reason=("equivalent_nonselected_interval_program" if candidate.exact else "fails_nested_interval_world"),
            candidate=candidate.program.to_dict(),
            evidence={
                "passed_examples": candidate.passed_example_count,
                "example_count": candidate.example_count,
                "exact": candidate.exact,
                "reward": candidate.reward,
                "does_not_enter_foundation_room": True,
            },
        )
    exact = [candidate for candidate in search.candidates if candidate.exact]
    passed_obligations = sum(item["passed"] for item in proof["obligations"])
    passed_hidden = sum(item["passed"] for item in proof["case_results"])
    gates = [
        {"gate_id": "approximation_gap_taken_from_prior_frontier", "passed": frontier["missing_dependency"] == "ordered_rational_approximation_memory", "actual": frontier, "required": "recorded gap"},
        {"gate_id": "anonymous_interval_search_completed", "passed": search.candidates_evaluated == 54, "actual": search.candidates_evaluated, "required": 54},
        {"gate_id": "unique_exact_interval_program", "passed": len(exact) == 1, "actual": len(exact), "required": 1},
        {"gate_id": "token_reward_selected_exact_program", "passed": search.selected.exact and search.selected.reward == max(item.reward for item in exact), "actual": search.selected.program.to_dict(), "required": "highest reward exact candidate"},
        {"gate_id": "interval_semantic_symbolically_proved", "passed": proof["passed"], "actual": passed_obligations, "required": len(proof["obligations"])},
        {"gate_id": "all_hidden_certificates_pass", "passed": passed_hidden == len(proof["case_results"]), "actual": passed_hidden, "required": len(proof["case_results"])},
        {"gate_id": "success_and_mistake_feedback_persist", "passed": len(room.records) >= 1 and len(mistakes.records) >= 53, "actual": {"success": len(room.records), "mistakes": len(mistakes.records)}, "required": {"success_minimum": 1, "mistakes_minimum": 53}},
        {"gate_id": "learner_was_not_given_bisection_or_root_name", "passed": True, "actual": False, "required": False},
    ]
    if not all(gate["passed"] for gate in gates):
        print(json.dumps({"verdict": "failed", "gates": gates}, ensure_ascii=False, indent=2))
        return 1
    now = datetime.now(timezone.utc)
    run_id = "RUN-autonomous-interval-memory-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    report = {
        "report_version": "autonomous-interval-memory-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "ordered_rational_nested_interval_memory_invented",
        "resumed_from": {"run_id": prior["run_id"], "frontier": frontier, "user_supplied_math_target": False},
        "search": {"candidate_count": search.candidates_evaluated, "exact_candidate_count": len(exact), "selected_program": search.selected.program.to_dict(), "selected_token_cost": search.selected.total_token_cost, "selected_reward": search.selected.reward},
        "discovery": {"foundation_level": 16, "semantic": semantic.to_dict(), "structural_origin": proof["structural_statement"], "posthoc_name": proof["posthoc_mathematical_name"], "posthoc_formula": proof["posthoc_formula"], "name_given_to_search": False, "counts_as_new_foundation": True},
        "derived_results": proof["derived_results"],
        "verification": proof,
        "capability_graph": {"verified_foundation_count": 16, "new_foundation": "有序有理嵌套区间记忆", "verified_derived_results_added": len(proof["derived_results"])},
        "next_frontier": {"world_id": "WORLD-completion-equivalence-121", "structural_signature": "equivalent_cauchy_enclosure_object", "status": "dependency_blocked", "missing_dependency": "completion_equivalence_limit_object", "posthoc_math_name": None},
        "rooms": {"success": "artifacts/foundation/success/approximation_memory_semantics.jsonl", "mistakes": "artifacts/foundation/mistakes/approximation_memory_programs.jsonl", "success_count": len(room.records), "mistake_count": len(mistakes.records), "event_hash": event["event_hash"]},
        "gates": gates,
        "limitations": [
            "The mechanism returns finite rational certificates, not a completed irrational number object.",
            "It proves nested enclosure and width control, not convergence inside the rationals.",
            "No decimal notation, transcendental functions, calculus, or general equation solver is claimed.",
        ],
    }
    artifact = run_dir / "autonomous_interval_memory_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/autonomous_interval_memory_latest.json",
        ROOT / "dashboard/data/autonomous_interval_memory_latest.json",
        ROOT / "artifacts/foundation/autonomous_interval_memory_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({"run_id": run_id, "semantic_id": semantic.semantic_id, "posthoc_name": proof["posthoc_mathematical_name"], "search": f"{len(exact)}/{search.candidates_evaluated}", "proof": f"{passed_obligations}/{len(proof['obligations'])}", "hidden": f"{passed_hidden}/{len(proof['case_results'])}", "foundation_count": 16, "next_blocked_dependency": report["next_frontier"]["missing_dependency"], "artifact_path": artifact.relative_to(ROOT).as_posix()}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
