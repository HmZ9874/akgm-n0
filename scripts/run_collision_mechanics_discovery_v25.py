"""Run and publish V25 collision mechanics discovery."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.collision_mechanics_discovery_v25 import run_v25_acceptance  # noqa: E402


def _digest(report: dict) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-collision-mechanics-v25-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v25_acceptance()
    if not acceptance["passed"]:
        failed = [item["obligation_id"] for item in acceptance["proof_obligations"] if not item["passed"]]
        raise RuntimeError(f"V25 acceptance failed: {failed}")
    report = {
        "report_version": "collision-mechanics-discovery-v25.0",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "anonymous_collision_programs_and_dual_conservation_discovered",
        "acceptance": acceptance,
        "capability_change": {
            "before": "V24 represented parameter-dependent response and one weighted linear invariant",
            "after": "V25 constructs both post-collision entity programs and proves simultaneous linear and quadratic weighted conservation",
            "collision_formula_supplied_to_learner": False,
        },
        "claim": {
            "achieved": "exact symbolic reconstruction of one-dimensional elastic two-body collision mechanics inside the V21-V24 substrate",
            "not_claimed": "sensor-derived mechanics, arbitrary collision geometry, rotation, friction, deformation, or unrestricted law invention",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "collision_mechanics_discovery_report.json"
    mistake_path = ROOT / "artifacts/physics/v25/mistakes/rejected_collision_mutations.jsonl"
    mistake_path.parent.mkdir(parents=True, exist_ok=True)
    mistake_path.write_text("".join(json.dumps({"schema_version": "collision-mistake-v25.0", **item}, ensure_ascii=False, sort_keys=True) + "\n" for item in acceptance["mutation_audits"]), encoding="utf-8")
    report["storage"] = {
        "success_room": "artifacts/physics/v25/success/collision_mechanics_latest.json",
        "mistake_room": "artifacts/physics/v25/mistakes/rejected_collision_mutations.jsonl",
        "accepted_programs": 4,
        "rejected_mutations": len(acceptance["mutation_audits"]),
    }
    report["content_digest"] = _digest(report)
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/collision_mechanics_discovery_v25_latest.json",
        ROOT / "dashboard/data/collision_mechanics_discovery_v25_latest.json",
        ROOT / "artifacts/physics/v25/success/collision_mechanics_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    summary = {
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "candidates_per_output": acceptance["discovery"]["candidates_per_output"],
        "collision_programs": [item["opaque_program"] for item in acceptance["discovery"]["selected_programs"]],
        "linear_invariant": acceptance["discovery"]["inherited_linear_invariant"]["opaque_program"],
        "quadratic_invariant": acceptance["discovery"]["selected_quadratic_invariant"]["opaque_program"],
        "sealed_collisions": len(acceptance["proofs"]["collision_programs"]["hidden_replay"]),
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
    }
    sys.stdout.buffer.write((json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
