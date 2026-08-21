"""Run V22 anonymous physics discovery and publish proof evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.anonymous_physics_discovery_v22 import run_v22_acceptance  # noqa: E402


def _digest(report: dict) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-anonymous-physics-v22-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v22_acceptance()
    if not acceptance["passed"]:
        failed = [item["obligation_id"] for item in acceptance["proof_obligations"] if not item["passed"]]
        raise RuntimeError(f"V22 acceptance failed: {failed}")
    report = {
        "report_version": "anonymous-physics-discovery-v22.0",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "anonymous_discrete_kinematics_dimensions_and_conservation_passed",
        "acceptance": acceptance,
        "capability_change": {
            "before": "V21 constructed a signed rational ring and translation-equation solver",
            "after": "V22 learns executable state-transition laws, dimension constraints, normalization, and an additive conservation law from anonymous experiments",
            "physics_formula_names_supplied": False,
        },
        "claim": {
            "achieved": "verified first physics layer: discrete rational kinematics, relational dimensions, and closed additive exchange conservation",
            "not_claimed": "continuous mechanics, force/mass dynamics, real-world sensor science, or stochastic physics",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "anonymous_physics_discovery_report.json"
    mistake_path = ROOT / "artifacts/physics/v22/mistakes/rejected_physics_claims.jsonl"
    mistake_path.parent.mkdir(parents=True, exist_ok=True)
    mistake_path.write_text(
        "".join(json.dumps({"schema_version": "physics-mistake-v22.0", **item}, ensure_ascii=False, sort_keys=True) + "\n" for item in acceptance["mutation_audits"]),
        encoding="utf-8",
    )
    report["storage"] = {
        "success_room": "artifacts/physics/v22/success/anonymous_physics_latest.json",
        "mistake_room": "artifacts/physics/v22/mistakes/rejected_physics_claims.jsonl",
        "promoted_transition_programs": len(acceptance["discovery"]["channel_programs"]),
        "promoted_invariants": 1,
        "rejected_claims": len(acceptance["mutation_audits"]),
    }
    report["content_digest"] = _digest(report)
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/anonymous_physics_discovery_v22_latest.json",
        ROOT / "dashboard/data/anonymous_physics_discovery_v22_latest.json",
        ROOT / "artifacts/physics/v22/success/anonymous_physics_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    summary = {
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "expressions_searched": acceptance["discovery"]["expressions_generated"],
        "transition_programs": len(acceptance["discovery"]["channel_programs"]),
        "conservation_programs": 1,
        "mutations_rejected": sum(item["rejected"] for item in acceptance["mutation_audits"]),
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
    }
    sys.stdout.buffer.write((json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
