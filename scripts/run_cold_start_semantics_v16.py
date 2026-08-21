"""Run and publish the V16 cold-start runtime semantic benchmark."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.cold_start_semantics_v16 import run_v16_acceptance  # noqa: E402


def _digest(report: dict) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-cold-start-v16-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v16_acceptance(trials=20)
    if not acceptance["passed"]:
        failed = [item["obligation_id"] for item in acceptance["proof_obligations"] if not item["passed"]]
        raise RuntimeError(f"V16 acceptance failed: {failed}")

    report = {
        "report_version": "cold-start-runtime-semantics-v16.0",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "strict_cold_start_runtime_semantic_abstraction_passed",
        "acceptance": acceptance,
        "capability_change": {
            "before": "V15 macros were expanded before execution and successful programs were migrated memories",
            "after": "empty dynamic registries mine, install, dispatch, reuse, and recursively compose new parameterized runtime opcodes",
            "migrated_success_programs_used": False,
            "runtime_opcode_installation_proven": True,
            "unrestricted_mathematical_discovery_proven": False,
        },
        "claim": {
            "achieved": "cold-start runtime semantic abstraction from recurring anonymous primitive programs",
            "not_claimed": "discovery of all mathematics from raw numbers or unrestricted self-modifying control flow",
        },
    }

    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "cold_start_semantics_report.json"
    mistake_path = ROOT / "artifacts/foundation/v16/mistakes/rejected_semantics.jsonl"
    mistake_path.parent.mkdir(parents=True, exist_ok=True)
    mistakes = []
    for trial in acceptance["trials"]:
        mistakes.append({
            "schema_version": "cold-start-semantic-mistake-v16.0",
            "trial_index": trial["trial_index"],
            "kind": "mutated_certificate_counterexample",
            **trial["mutation_audit"],
        })
        for rejection in trial["sample_rejections"]:
            mistakes.append({
                "schema_version": "cold-start-semantic-mistake-v16.0",
                "trial_index": trial["trial_index"],
                "kind": "discovery_rejection",
                **rejection,
            })
    mistake_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in mistakes),
        encoding="utf-8",
    )
    report["storage"] = {
        "success_report": "artifacts/foundation/v16/success/cold_start_semantics_latest.json",
        "mistake_room": str(mistake_path.relative_to(ROOT)).replace("\\", "/"),
        "mistakes_recorded": len(mistakes),
    }
    report["content_digest"] = _digest(report)
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    destinations = (
        ROOT / "reports/data/cold_start_semantics_v16_latest.json",
        ROOT / "dashboard/data/cold_start_semantics_v16_latest.json",
        ROOT / "artifacts/foundation/v16/success/cold_start_semantics_latest.json",
    )
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)

    print(json.dumps({
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "cold_start_trials": acceptance["trial_count"],
        "installed_operators": acceptance["aggregate"]["installed_operator_count"],
        "generation_depth": acceptance["aggregate"]["minimum_generation_depth"],
        "holdout_replays": f"{acceptance['aggregate']['exact_holdout_replays']}/{acceptance['aggregate']['holdout_workloads']}",
        "holdout_token_reduction": acceptance["aggregate"]["mean_holdout_token_reduction"],
        "mutations_rejected": acceptance["aggregate"]["mutations_rejected"],
        "classification": acceptance["classification"],
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

