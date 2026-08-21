from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.formula_rejection_room import FormulaRejectionRoom  # noqa: E402
from akgm_n0.evaluator.meta_autonomy_v4_benchmark import (  # noqa: E402
    run_deep_research_benchmark,
    verify_deep_research_report,
)
from akgm_n0.evaluator.meta_autonomy_v4_room import MetaAutonomyV4Room  # noqa: E402


def main() -> int:
    benchmark = run_deep_research_benchmark()
    verification = verify_deep_research_report(benchmark)
    if not benchmark["passed"] or not verification["passed"]:
        print(json.dumps({"benchmark": benchmark, "verification": verification}, ensure_ascii=False, indent=2))
        return 1
    success_room = MetaAutonomyV4Room(
        ROOT / "artifacts/meta_autonomy/v4/success/deep_research.jsonl"
    )
    event = success_room.record(benchmark)
    mistake_room = FormulaRejectionRoom(
        ROOT / "artifacts/meta_autonomy/v4/mistakes/research_antipatterns.jsonl"
    )
    antipatterns = (
        (
            "forcing_maximum_state_width_discards_smaller_reachable_programs",
            {"policy": "state_width_equals_capacity"},
            {"repair": "enumerate_all_widths_up_to_capacity", "regression_case": "AW-v4-7f"},
        ),
        (
            "fixed_point_only_polynomial_kernel_rejects_inductive_zero_sets",
            {"proof_rule": "P(next)=P(now) only"},
            {"repair": "admit P(next)=lambda*P with exact coefficient checking"},
        ),
        (
            "single_best_solution_can_hide_reusable_substructure",
            {"library_policy": "compress_one_carried_solution_per_world"},
            {"repair": "retain independent minimal-genome solutions", "macro_count": benchmark["library_learning"]["macro_count"]},
        ),
    )
    for reason, candidate, evidence in antipatterns:
        mistake_room.record(reason=reason, candidate=candidate, evidence=evidence)

    now = datetime.now(timezone.utc)
    run_id = "RUN-deep-meta-research-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "expanded_symbolic_research_passed",
        "benchmark": benchmark,
        "verification": verification,
        "research_basis": [
            {
                "title": "Algebra-based Synthesis of Loops and their Invariants",
                "url": "https://arxiv.org/abs/2103.03599",
                "adopted_idea": "constant-coefficient recurrence proof portfolio",
            },
            {
                "title": "Counterexample-Guided Polynomial Loop Invariant Generation",
                "url": "https://arxiv.org/abs/1502.04280",
                "adopted_idea": "counterexample-refined exact invariant constraints",
            },
            {
                "title": "DreamCoder: Bootstrapping Inductive Program Synthesis with Wake-Sleep Library Learning",
                "url": "https://people.csail.mit.edu/asolar/papers/EllisWNSMHCST21.pdf",
                "adopted_idea": "retain multiple solutions and compress recurring executable components",
                "neural_policy_adopted": False,
            },
        ],
        "rooms": {
            "success_path": "artifacts/meta_autonomy/v4/success/deep_research.jsonl",
            "mistake_path": "artifacts/meta_autonomy/v4/mistakes/research_antipatterns.jsonl",
            "success_count": len(success_room.records),
            "mistake_count": len(mistake_room.records),
            "event_hash": event["event_hash"],
        },
    }
    artifact = run_dir / "deep_meta_research_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/deep_meta_research_latest.json",
        ROOT / "dashboard/data/deep_meta_research_latest.json",
        ROOT / "artifacts/meta_autonomy/v4/deep_meta_research_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "overall_score": benchmark["overall_score"],
        "dimension_scores": benchmark["dimension_scores"],
        "sealed_worlds": f"{sum(item['passed'] for item in benchmark['sealed_results'])}/{len(benchmark['sealed_results'])}",
        "proved_loops": f"{sum(item['passed'] for item in benchmark['proof_results'])}/{len(benchmark['proof_results'])}",
        "macro_transfer_candidates": benchmark["library_learning"]["macro_candidates"],
        "primitive_baseline_candidates": benchmark["library_learning"]["primitive_baseline_candidates"],
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
