from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.formula_rejection_room import FormulaRejectionRoom  # noqa: E402
from akgm_n0.evaluator.operator_frontier_v4 import (  # noqa: E402
    run_operator_frontier,
    verify_operator_frontier_report,
)
from akgm_n0.evaluator.operator_frontier_v4_room import VerifiedOperatorRoom  # noqa: E402


def main() -> int:
    frontier = run_operator_frontier()
    verification = verify_operator_frontier_report(frontier)
    if not frontier["passed"] or not verification["passed"]:
        print(json.dumps({"frontier": frontier, "verification": verification}, ensure_ascii=False, indent=2))
        return 1
    room = VerifiedOperatorRoom(
        ROOT / "artifacts/operators/v4/success/verified_operators.jsonl"
    )
    events = [room.record(record) for record in frontier["operators"]]
    boundary_room = FormulaRejectionRoom(
        ROOT / "artifacts/operators/v4/mistakes/expression_boundaries.jsonl"
    )
    boundaries = (
        ("general_division", "mutable quotient/remainder state and divisor-controlled comparison"),
        ("general_remainder", "comparison/subtractive inner loop or equivalent modular state"),
        ("integer_root", "unbounded candidate comparison with nonlinear order predicate"),
        ("variable_base_exponentiation", "general state-by-input interaction rather than state-by-counter only"),
    )
    for name, dependency in boundaries:
        boundary_room.record(
            reason="dependency_blocked_not_promoted",
            candidate={"evaluator_only_name": name, "status": "not_an_operator_discovery"},
            evidence={"missing_structural_dependency": dependency, "finite_fit_does_not_authorize_promotion": True},
        )
    now = datetime.now(timezone.utc)
    run_id = "RUN-operator-frontier-v4-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "twelve_verified_operators_promoted",
        "frontier": frontier,
        "verification": verification,
        "rooms": {
            "success_path": "artifacts/operators/v4/success/verified_operators.jsonl",
            "boundary_path": "artifacts/operators/v4/mistakes/expression_boundaries.jsonl",
            "success_count": len(room.records),
            "boundary_count": len(boundary_room.records),
            "latest_event_hash": events[-1]["event_hash"],
        },
    }
    artifact = run_dir / "operator_frontier_v4_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/operator_frontier_v4_latest.json",
        ROOT / "dashboard/data/operator_frontier_v4_latest.json",
        ROOT / "artifacts/operators/v4/operator_frontier_v4_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "promoted": frontier["promoted_operator_count"],
        "distinct_signatures": frontier["all_behavior_signatures_distinct"],
        "boundaries": len(boundary_room.records),
        "operators": [item["posthoc_name"] for item in frontier["operators"]],
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
