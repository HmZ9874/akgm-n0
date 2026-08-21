"""Run and publish V21 directed rational construction evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.directed_rational_construction_v21 import run_v21_acceptance  # noqa: E402


def _digest(report: dict) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-directed-rational-v21-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v21_acceptance()
    if not acceptance["passed"]:
        failed = [item["obligation_id"] for item in acceptance["proof_obligations"] if not item["passed"]]
        raise RuntimeError(f"V21 acceptance failed: {failed}")
    report = {
        "report_version": "directed-rational-construction-v21.0",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "natural_counter_signed_rational_ring_construction_passed",
        "acceptance": acceptance,
        "capability_change": {
            "before": "V20 represented nonnegative rationals and solved natural multiplicative equations",
            "after": "V21 constructs direction, additive inverse, signed rational ring operations, and unique translation-equation solutions using natural counters only",
            "host_negative_values_given_to_learner": False,
        },
        "claim": {
            "achieved": "verified construction of a signed rational commutative ring presentation and x+b=c solver",
            "not_claimed": "multiplicative inverses, general ax+b=c solving, or unrestricted symbolic algebra",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "directed_rational_construction_report.json"
    mistake_path = ROOT / "artifacts/foundation/v21/mistakes/rejected_direction_routes.jsonl"
    mistake_path.parent.mkdir(parents=True, exist_ok=True)
    mistake_path.write_text(
        "".join(json.dumps({"schema_version": "direction-route-mistake-v21.0", **item}, ensure_ascii=False, sort_keys=True) + "\n" for item in acceptance["mutation_audits"]),
        encoding="utf-8",
    )
    report["storage"] = {
        "success_room": "artifacts/foundation/v21/success/directed_rational_latest.json",
        "mistake_room": "artifacts/foundation/v21/mistakes/rejected_direction_routes.jsonl",
        "promoted_programs": 3,
        "rejected_mutations": len(acceptance["mutation_audits"]),
    }
    report["content_digest"] = _digest(report)
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/directed_rational_construction_v21_latest.json",
        ROOT / "dashboard/data/directed_rational_construction_v21_latest.json",
        ROOT / "artifacts/foundation/v21/success/directed_rational_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    summary = {
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "policies_generated": acceptance["construction"]["policies_generated"],
        "promoted_programs": 3,
        "mutations_rejected": sum(item["rejected"] for item in acceptance["mutation_audits"]),
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
    }
    sys.stdout.buffer.write((json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
