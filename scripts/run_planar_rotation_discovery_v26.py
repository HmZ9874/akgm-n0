"""Run and publish V26 planar rotation mechanics discovery."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.planar_rotation_discovery_v26 import run_v26_acceptance  # noqa: E402


def _digest(report: dict) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-planar-rotation-v26-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v26_acceptance()
    if not acceptance["passed"]:
        failed = [item["obligation_id"] for item in acceptance["proof_obligations"] if not item["passed"]]
        raise RuntimeError(f"V26 acceptance failed: {failed}")
    report = {
        "report_version": "planar-rotation-discovery-v26.0",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "planar_oriented_operation_rotation_quantity_and_central_conservation_discovered",
        "acceptance": acceptance,
        "capability_change": {
            "before": "V25 mechanics was one-dimensional and translational",
            "after": "V26 introduces two-dimensional orientation, constructs a mass-weighted rotation quantity, and distinguishes central from noncentral actions",
            "cross_product_or_angular_momentum_formula_supplied_to_learner": False,
        },
        "claim": {
            "achieved": "exact symbolic discovery of planar angular-impulse balance and central-action angular conservation",
            "not_claimed": "three-dimensional rigid-body mechanics, continuous torque, empirical orbital mechanics, or unrestricted semantic invention",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "planar_rotation_discovery_report.json"
    mistake_path = ROOT / "artifacts/physics/v26/mistakes/rejected_planar_mutations.jsonl"
    mistake_path.parent.mkdir(parents=True, exist_ok=True)
    mistake_path.write_text("".join(json.dumps({"schema_version": "planar-mistake-v26.0", **item}, ensure_ascii=False, sort_keys=True) + "\n" for item in acceptance["mutation_audits"]), encoding="utf-8")
    report["storage"] = {
        "success_room": "artifacts/physics/v26/success/planar_rotation_latest.json",
        "mistake_room": "artifacts/physics/v26/mistakes/rejected_planar_mutations.jsonl",
        "accepted_programs": 3,
        "rejected_mutations": len(acceptance["mutation_audits"]),
    }
    report["content_digest"] = _digest(report)
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/planar_rotation_discovery_v26_latest.json",
        ROOT / "dashboard/data/planar_rotation_discovery_v26_latest.json",
        ROOT / "artifacts/physics/v26/success/planar_rotation_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    summary = {
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "oriented_program": acceptance["discovery"]["selected_bilinear"]["opaque_program"],
        "rotation_program": acceptance["discovery"]["selected_rotation_quantity"]["opaque_program"],
        "sealed_central_cases": len(acceptance["proofs"]["rotation_balance"]["central_hidden_replay"]),
        "sealed_general_cases": len(acceptance["proofs"]["rotation_balance"]["general_hidden_replay"]),
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
    }
    sys.stdout.buffer.write((json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
