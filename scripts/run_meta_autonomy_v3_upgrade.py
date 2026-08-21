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
    MetaAutonomyV3Room,
    run_meta_autonomy_benchmark,
    verify_meta_autonomy_report,
)


def main() -> int:
    benchmark = run_meta_autonomy_benchmark()
    verification = verify_meta_autonomy_report(benchmark)
    if not benchmark["passed"] or not verification["passed"]:
        print(json.dumps({"benchmark": benchmark, "verification": verification}, ensure_ascii=False, indent=2))
        return 1

    success_room = MetaAutonomyV3Room(
        ROOT / "artifacts/meta_autonomy/v3/success/benchmarks.jsonl"
    )
    success_event = success_room.record(benchmark)
    mistake_room = FormulaRejectionRoom(
        ROOT / "artifacts/meta_autonomy/v3/mistakes/generalized_failure_families.jsonl"
    )
    mistake = benchmark["mistake_transfer"]
    for candidate in mistake["training_programs"] + mistake["unseen_programs"]:
        mistake_room.record(
            reason="generalized_failure_family_rejected_before_execution",
            candidate=candidate,
            evidence={
                "failure_clause": mistake["clause"],
                "context": mistake["context"],
                "does_not_enter_success_room": True,
            },
        )

    now = datetime.now(timezone.utc)
    run_id = "RUN-meta-autonomy-v3-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "bounded_threshold_reached",
        "benchmark": benchmark,
        "verification": verification,
        "rooms": {
            "success_path": "artifacts/meta_autonomy/v3/success/benchmarks.jsonl",
            "mistake_path": "artifacts/meta_autonomy/v3/mistakes/generalized_failure_families.jsonl",
            "success_count": len(success_room.records),
            "mistake_count": len(mistake_room.records),
            "success_event_hash": success_event["event_hash"],
            "hash_chained": True,
            "proof_replayed_on_load": True,
        },
    }
    artifact = run_dir / "meta_autonomy_v3_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/meta_autonomy_v3_latest.json",
        ROOT / "dashboard/data/meta_autonomy_v3_latest.json",
        ROOT / "artifacts/meta_autonomy/v3/meta_autonomy_v3_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)

    print(json.dumps({
        "run_id": run_id,
        "verdict": report["verdict"],
        "overall_score": benchmark["overall_score"],
        "dimension_scores": benchmark["dimension_scores"],
        "sealed_worlds": f"{sum(item['passed'] for item in benchmark['sealed_results'])}/{len(benchmark['sealed_results'])}",
        "formal_certificates": f"{sum(item['certificate_count'] > 0 for item in benchmark['formal_proof_results'])}/{len(benchmark['formal_proof_results'])}",
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
