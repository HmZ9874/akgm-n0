"""Run and publish V27 rigid-body mechanics and completeness audit."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from akgm_n0.evaluator.rigid_body_mechanics_v27 import run_v27_acceptance  # noqa: E402


def _digest(report: dict) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-rigid-body-v27-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v27_acceptance()
    if not acceptance["passed"]:
        failed = [item["obligation_id"] for item in acceptance["proof_obligations"] if not item["passed"]]
        raise RuntimeError(f"V27 acceptance failed: {failed}")
    report = {
        "report_version": "rigid-body-mechanics-v27.0", "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "fixed_axis_rigid_body_mechanics_discovered_but_complete_mechanics_not_yet_achieved",
        "acceptance": acceptance,
        "capability_change": {
            "before": "V26 had planar point rotation but no composite-body inertia",
            "after": "V27 discovers point-set rotational inertia, angular response, angular collision invariants, and a strict mechanics completion controller",
            "inertia_formula_supplied_to_learner": False,
        },
        "claim": {
            "achieved": "verified fixed-axis point-rigid-body mechanics and explicit selection of continuous-time dynamics as the next prerequisite gap",
            "not_claimed": "complete mechanics; eight declared mechanics domains remain unverified",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "rigid_body_mechanics_report.json"
    mistake_path = ROOT / "artifacts/physics/v27/mistakes/rejected_rigid_mutations.jsonl"
    mistake_path.parent.mkdir(parents=True, exist_ok=True)
    mistake_path.write_text("".join(json.dumps({"schema_version": "rigid-mistake-v27.0", **item}, ensure_ascii=False, sort_keys=True) + "\n" for item in acceptance["mutation_audits"]), encoding="utf-8")
    report["storage"] = {"success_room": "artifacts/physics/v27/success/rigid_body_latest.json", "mistake_room": "artifacts/physics/v27/mistakes/rejected_rigid_mutations.jsonl", "accepted_programs": 5, "rejected_mutations": len(acceptance["mutation_audits"])}
    report["content_digest"] = _digest(report)
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (ROOT / "reports/data/rigid_body_mechanics_v27_latest.json", ROOT / "dashboard/data/rigid_body_mechanics_v27_latest.json", ROOT / "artifacts/physics/v27/success/rigid_body_latest.json"):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    graph = acceptance["mechanics_capability_graph"]
    summary = {
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "aggregate_program": acceptance["discovery"]["selected_aggregate"]["opaque_program"],
        "angular_quantity": acceptance["discovery"]["selected_angular_quantity"]["opaque_program"],
        "mechanics_domains": f"{graph['verified_domains']}/{graph['total_domains']}",
        "complete_mechanics_claim_allowed": graph["full_mechanics_claim_allowed"],
        "next_gap": graph["next_selected_gap"],
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
    }
    sys.stdout.buffer.write((json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
