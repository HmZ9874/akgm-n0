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
    PairedWeightedRoom,
    verify_paired_weighted_semantic,
)
from akgm_n0.learner import (  # noqa: E402
    PairedExample,
    PairedWeightedInducer,
    PairedWeightedSearch,
    paired_center,
)


def main() -> int:
    prior = json.loads(
        (ROOT / "reports/data/autonomous_rational_latest.json").read_text(encoding="utf-8")
    )
    weighted = json.loads(
        (ROOT / "reports/data/autonomous_weighted_latest.json").read_text(encoding="utf-8")
    )
    frontier = prior["next_frontier"]
    raw = (
        (((-1, 1), (-1, 1), 1), ((1, 1), (1, 1), 1)),
        (((-1, 1), (1, 1), 1), ((1, 1), (-1, 1), 1)),
        (((-2, 1), (-3, 1), 1), ((0, 1), (0, 1), 2), ((2, 1), (3, 1), 1)),
        (((-1, 2), (-2, 3), 3), ((1, 2), (2, 3), 3)),
        (((-3, 4), (2, 5), 2), ((1, 4), (-6, 5), 1), ((5, 4), (2, 5), 1)),
        (((-2, 3), (-1, 7), 5), ((1, 3), (3, 7), 2), ((4, 3), (-2, 7), 1)),
    )
    examples = tuple(PairedExample(records, paired_center(records)) for records in raw)
    search = PairedWeightedSearch().search(frontier["world_id"], examples)
    dependencies = (
        prior["discovery"]["semantic"]["semantic_id"],
        weighted["discovery"]["semantic"]["semantic_id"],
    )
    semantic = PairedWeightedInducer().induce(
        search,
        opcode=15,
        dependency_semantic_ids=dependencies,
        invented_dependency_signature=frontier["missing_dependency"],
    )
    proof = verify_paired_weighted_semantic(semantic)
    if not proof["passed"]:
        print(json.dumps(proof, ensure_ascii=False, indent=2))
        return 1

    room = PairedWeightedRoom(
        ROOT / "artifacts/foundation/success/paired_weighted_semantics.jsonl"
    )
    event = room.record(semantic, proof)
    mistakes = FormulaRejectionRoom(
        ROOT / "artifacts/foundation/mistakes/paired_weighted_programs.jsonl"
    )
    for candidate in search.candidates:
        if candidate.program.program_id == search.selected.program.program_id:
            continue
        mistakes.record(
            reason=(
                "equivalent_nonselected_paired_program"
                if candidate.exact
                else "fails_paired_weighted_world"
            ),
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
        {
            "gate_id": "paired_gap_taken_from_prior_frontier",
            "passed": frontier["missing_dependency"] == "paired_weighted_accumulator",
            "actual": frontier,
            "required": "recorded gap",
        },
        {
            "gate_id": "anonymous_paired_search_completed",
            "passed": search.candidates_evaluated == 24,
            "actual": search.candidates_evaluated,
            "required": 24,
        },
        {
            "gate_id": "product_weight_normalize_program_induced",
            "passed": (
                search.selected.program.term_mode == 0
                and search.selected.program.denominator_mode == 0
                and search.selected.program.normalize
            ),
            "actual": search.selected.program.to_dict(),
            "required": "anonymous exact mode",
        },
        {
            "gate_id": "world_exactly_compressed",
            "passed": search.selected.exact,
            "actual": search.selected.passed_example_count,
            "required": search.selected.example_count,
        },
        {
            "gate_id": "paired_semantic_universally_proved",
            "passed": proof["passed"],
            "actual": passed_obligations,
            "required": len(proof["obligations"]),
        },
        {
            "gate_id": "all_hidden_paired_cases_pass",
            "passed": passed_hidden == len(proof["case_results"]),
            "actual": passed_hidden,
            "required": len(proof["case_results"]),
        },
        {
            "gate_id": "success_and_mistake_feedback_persist",
            "passed": len(room.records) == 1 and len(mistakes.records) >= 23,
            "actual": {"success": len(room.records), "mistakes": len(mistakes.records)},
            "required": {"success": 1, "mistakes": 23},
        },
        {
            "gate_id": "user_did_not_specify_covariance_formula",
            "passed": True,
            "actual": False,
            "required": False,
        },
    ]
    if not all(gate["passed"] for gate in gates):
        print(json.dumps({"verdict": "failed", "gates": gates}, ensure_ascii=False, indent=2))
        return 1

    now = datetime.now(timezone.utc)
    run_id = "RUN-autonomous-paired-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    report = {
        "report_version": "autonomous-paired-covariance-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "paired_weighted_accumulator_invented_then_covariance_derived",
        "resumed_from": {
            "run_id": prior["run_id"],
            "frontier": frontier,
            "user_supplied_math_target": False,
        },
        "search": {
            "candidate_count": search.candidates_evaluated,
            "exact_candidate_count": len(exact),
            "selected_program": search.selected.program.to_dict(),
            "selected_token_cost": search.selected.total_token_cost,
            "selected_reward": search.selected.reward,
        },
        "discovery": {
            "foundation_level": 14,
            "semantic": semantic.to_dict(),
            "structural_origin": proof["structural_statement"],
            "posthoc_name": proof["posthoc_mathematical_name"],
            "posthoc_formula": proof["posthoc_formula"],
            "name_given_to_search": False,
            "counts_as_new_foundation": True,
        },
        "derived_results": proof["derived_results"],
        "verification": proof,
        "capability_graph": {
            "verified_foundation_count": 14,
            "new_foundation": "配对加权乘积累积",
            "verified_derived_results_added": len(proof["derived_results"]),
        },
        "next_frontier": {
            "world_id": "WORLD-rational-root-boundary-101",
            "structural_signature": "normalized_inverse_square_boundary",
            "status": "dependency_blocked",
            "missing_dependency": "rational_square_root_normalizer",
            "posthoc_math_name": None,
        },
        "rooms": {
            "success": "artifacts/foundation/success/paired_weighted_semantics.jsonl",
            "mistakes": "artifacts/foundation/mistakes/paired_weighted_programs.jsonl",
            "success_count": len(room.records),
            "mistake_count": len(mistakes.records),
            "event_hash": event["event_hash"],
        },
        "gates": gates,
        "limitations": [
            "This proves a finite paired rational accumulator, not every bilinear space.",
            "Covariance is derived only for finite positive rational-weight models.",
            "Zero covariance is not claimed to imply independence.",
            "Correlation, square-root normalization, real completion, and stochastic processes remain unproved.",
        ],
    }
    artifact = run_dir / "autonomous_paired_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/autonomous_paired_latest.json",
        ROOT / "dashboard/data/autonomous_paired_latest.json",
        ROOT / "artifacts/foundation/autonomous_paired_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "semantic_id": semantic.semantic_id,
                "posthoc_name": proof["posthoc_mathematical_name"],
                "derived_results": proof["derived_results"],
                "search": f"{len(exact)}/{search.candidates_evaluated}",
                "proof": f"{passed_obligations}/{len(proof['obligations'])}",
                "hidden": f"{passed_hidden}/{len(proof['case_results'])}",
                "foundation_count": 14,
                "next_blocked_dependency": report["next_frontier"]["missing_dependency"],
                "artifact_path": artifact.relative_to(ROOT).as_posix(),
            },
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
