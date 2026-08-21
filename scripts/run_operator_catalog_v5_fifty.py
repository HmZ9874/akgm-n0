from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.formula_rejection_room import FormulaRejectionRoom  # noqa: E402
from akgm_n0.evaluator.operator_catalog_v5 import (  # noqa: E402
    run_operator_catalog_v5,
    verify_operator_catalog_v5_report,
)
from akgm_n0.evaluator.operator_catalog_v5_room import VerifiedOperatorCatalogRoom  # noqa: E402


def main() -> int:
    catalog = run_operator_catalog_v5()
    verification = verify_operator_catalog_v5_report(catalog)
    if not catalog["passed"] or not verification["passed"]:
        print(json.dumps({"catalog": catalog, "verification": verification}, ensure_ascii=False, indent=2))
        return 1

    room = VerifiedOperatorCatalogRoom(
        ROOT / "artifacts/operators/v5/success/verified_operator_catalog.jsonl"
    )
    events = [room.record(record) for record in catalog["operators"]]
    if len(room.records) != 50:
        raise ValueError(f"verified room must contain exactly 50 records, got {len(room.records)}")

    boundary_room = FormulaRejectionRoom(
        ROOT / "artifacts/operators/v5/mistakes/unresolved_operator_boundaries.jsonl"
    )
    boundaries = (
        ("general_division", "nested quotient/remainder control with divisor-dependent comparison"),
        ("general_remainder", "subtractive or equivalent modular loop with zero-divisor contract"),
        ("integer_root", "unbounded candidate comparison and nonlinear order predicate"),
        ("logarithm", "inverse search over generic parametric power with explicit domain failures"),
        ("rational_field", "canonical numerator/denominator storage and normalization"),
    )
    for name, dependency in boundaries:
        boundary_room.record(
            reason="dependency_blocked_not_promoted",
            candidate={"evaluator_only_name": name, "status": "not_counted"},
            evidence={
                "missing_structural_dependency": dependency,
                "finite_fit_does_not_authorize_promotion": True,
            },
        )

    now = datetime.now(timezone.utc)
    run_id = "RUN-operator-catalog-v5-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "fifty_distinct_verified_operator_semantics_promoted",
        "catalog": catalog,
        "verification": verification,
        "rooms": {
            "success_path": "artifacts/operators/v5/success/verified_operator_catalog.jsonl",
            "boundary_path": "artifacts/operators/v5/mistakes/unresolved_operator_boundaries.jsonl",
            "success_count": len(room.records),
            "boundary_count": len(boundary_room.records),
            "latest_event_hash": events[-1]["event_hash"],
        },
    }
    artifact = run_dir / "operator_catalog_v5_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/operator_catalog_v5_latest.json",
        ROOT / "dashboard/data/operator_catalog_v5_latest.json",
        ROOT / "artifacts/operators/v5/operator_catalog_v5_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "promoted": catalog["promoted_operator_count"],
        "unique_programs": catalog["unique_program_count"],
        "unique_signatures": catalog["unique_behavior_signature_count"],
        "success_room_count": len(room.records),
        "boundaries": len(boundary_room.records),
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
