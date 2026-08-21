"""Run and publish the V24 anonymous inertial-response discovery."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.inertial_response_discovery_v24 import run_v24_acceptance  # noqa: E402


def _digest(report: dict) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-inertial-response-v24-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v24_acceptance()
    if not acceptance["passed"]:
        failed = [item["obligation_id"] for item in acceptance["proof_obligations"] if not item["passed"]]
        raise RuntimeError(f"V24 acceptance failed: {failed}")
    report = {
        "report_version": "inertial-response-discovery-v24.0",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "anonymous_inertial_response_and_weighted_conservation_discovered",
        "acceptance": acceptance,
        "capability_change": {
            "before": "V23 entities had implicit unit inertia and conserved an unweighted additive state",
            "after": "V24 varies an anonymous positive entity parameter, discovers inverse response scaling, and constructs the uniquely conserved parameter-weighted total",
            "mass_force_acceleration_formula_supplied_to_learner": False,
        },
        "claim": {
            "achieved": "exact symbolic discovery and universal proof of a mass-force-acceleration-like relation plus momentum-like conservation",
            "not_claimed": "empirical Newtonian mechanics, energy conservation, continuous dynamics, or unrestricted semantic invention",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "inertial_response_discovery_report.json"
    mistake_path = ROOT / "artifacts/physics/v24/mistakes/rejected_inertial_mutations.jsonl"
    mistake_path.parent.mkdir(parents=True, exist_ok=True)
    mistake_path.write_text("".join(
        json.dumps({"schema_version": "inertial-mistake-v24.0", **item}, ensure_ascii=False, sort_keys=True) + "\n"
        for item in acceptance["mutation_audits"]
    ), encoding="utf-8")
    report["storage"] = {
        "success_room": "artifacts/physics/v24/success/inertial_response_latest.json",
        "mistake_room": "artifacts/physics/v24/mistakes/rejected_inertial_mutations.jsonl",
        "accepted_programs": 2,
        "rejected_mutations": len(acceptance["mutation_audits"]),
    }
    report["content_digest"] = _digest(report)
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/inertial_response_discovery_v24_latest.json",
        ROOT / "dashboard/data/inertial_response_discovery_v24_latest.json",
        ROOT / "artifacts/physics/v24/success/inertial_response_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    summary = {
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "response_program": acceptance["discovery"]["selected_response"]["opaque_program"],
        "weighted_invariant": acceptance["discovery"]["selected_invariant"]["opaque_program"],
        "sealed_response_cases": len(acceptance["proofs"]["response"]["hidden_replay"]),
        "sealed_exchange_cases": len(acceptance["proofs"]["weighted_conservation"]["hidden_replay"]),
        "rejected_mutations": len(acceptance["mutation_audits"]),
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
    }
    sys.stdout.buffer.write((json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
