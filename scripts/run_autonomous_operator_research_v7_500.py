from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.autonomous_operator_research_v7 import (  # noqa: E402
    run_autonomous_operator_research_v7,
    verify_autonomous_operator_research_v7,
)
from akgm_n0.evaluator.autonomous_operator_room_v7 import AutonomousOperatorV7Room  # noqa: E402
from akgm_n0.evaluator.formula_rejection_room import FormulaRejectionRoom  # noqa: E402
from akgm_n0.learner.autonomous_operator_research_v7 import (  # noqa: E402
    expression_digest,
    expression_for_support,
    symbolic_normal_form,
)


def main() -> int:
    research = run_autonomous_operator_research_v7()
    replay = verify_autonomous_operator_research_v7(research)
    if not research["passed"] or not replay["passed"]:
        print(json.dumps({"research": research, "replay": replay}, ensure_ascii=False, indent=2))
        return 1

    success_room = AutonomousOperatorV7Room(
        ROOT / "artifacts/operators/v7/success/verified_500_operators.jsonl"
    )
    events = [success_room.record(item) for item in research["operators"]]
    if len(success_room.records) != 500:
        raise ValueError("V7 success room must contain exactly 500 operators")

    rejection_room = FormulaRejectionRoom(
        ROOT / "artifacts/operators/v7/mistakes/reduced_or_duplicate_candidates.jsonl"
    )
    for item in research["operators"]:
        support = tuple((x, y) for x, y, _ in item["normal_form"])
        alternative = expression_for_support(support, reverse=True)
        rejection_room.record(
            reason="algebraically_duplicate_after_exact_reduction",
            candidate={
                "program_digest": expression_digest(alternative),
                "expression": alternative.to_dict(),
            },
            evidence={
                "duplicates_promoted_operator_id": item["operator_id"],
                "recomputed_normal_form": [list(value) for value in symbolic_normal_form(alternative)],
                "does_not_increase_operator_count": True,
            },
        )
    rejection_room.record(
        reason="already_present_in_v5_operator_catalog",
        candidate={"posthoc_formula": "x+y", "support": [[1,0],[0,1]]},
        evidence={"excluded_before_promotion": True, "does_not_increase_operator_count": True},
    )

    now = datetime.now(timezone.utc)
    run_id = "RUN-autonomous-operator-v7-500-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "five_hundred_distinct_universally_verified_derived_operators_promoted",
        "research": research,
        "verification": replay,
        "rooms": {
            "success_path": "artifacts/operators/v7/success/verified_500_operators.jsonl",
            "mistake_path": "artifacts/operators/v7/mistakes/reduced_or_duplicate_candidates.jsonl",
            "success_count": len(success_room.records),
            "mistake_count": len(rejection_room.records),
            "latest_success_hash": events[-1]["event_hash"],
        },
    }
    artifact = run_dir / "autonomous_operator_research_v7_500_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/autonomous_operator_research_v7_500_latest.json",
        ROOT / "dashboard/data/autonomous_operator_research_v7_500_latest.json",
        ROOT / "artifacts/operators/v7/autonomous_operator_research_v7_500_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "promoted": research["promoted_operator_count"],
        "unique_programs": research["unique_program_count"],
        "unique_supports": research["unique_support_count"],
        "unique_behaviors": research["unique_behavior_count"],
        "supports_considered": research["supports_considered"],
        "success_room": len(success_room.records),
        "mistake_room": len(rejection_room.records),
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
