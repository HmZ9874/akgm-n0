"""Run and publish the local-only V54 learning-efficiency benchmark."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.self_bootstrap_efficiency_v54 import run_v54_acceptance  # noqa: E402


def _digest(report: dict) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-self-bootstrap-efficiency-v54-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v54_acceptance()
    if not acceptance["passed"]:
        failed = [item for item in acceptance["proof_obligations"] if not item["passed"]]
        raise RuntimeError(f"V54 acceptance failed: {failed}")
    report = {
        "report_version": "self-bootstrap-efficiency-v54.0",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "local_autonomous_learning_efficiency_upgrade_passed",
        "acceptance": acceptance,
        "token_accounting": {
            "cloud_model_calls": 0,
            "api_tokens_consumed_by_research_runtime": 0,
            "local_resources": ["CPU", "memory", "wall-clock time", "electricity"],
        },
        "storage": {
            "success_room": "artifacts/foundation/v54/success/efficiency_latest.json",
            "mistake_room": "artifacts/foundation/v54/mistakes/mutated_certificates.jsonl",
            "design_mistake_room": "artifacts/foundation/v54/mistakes/design_failures.jsonl",
            "dashboard_modified": False,
        },
    }
    report["content_digest"] = _digest(report)
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    artifact = run_dir / "self_bootstrap_efficiency_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mistake = ROOT / report["storage"]["mistake_room"]
    mistake.parent.mkdir(parents=True, exist_ok=True)
    mistake.write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in acceptance["mutation_audits"]),
        encoding="utf-8",
    )
    design_mistake = ROOT / report["storage"]["design_mistake_room"]
    design_mistake.parent.mkdir(parents=True, exist_ok=True)
    design_mistake.write_text(
        json.dumps(
            {
                "schema_version": "research-design-mistake-v54.0",
                "reason": "four_short_term_sterile_rounds_stopped_the_frozen_twenty_round_benchmark_early",
                "failed_gate": "operator_noninferiority_at_ninety_percent",
                "failed_result": {"candidate": 78, "baseline": 90, "retention_ratio": 0.8666666666666667},
                "repair": "complete_all_twenty_preregistered_rounds; use short-term sterility for budget adaptation only",
                "acceptance_threshold_changed": False
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    for destination in (
        ROOT / "reports/data/self_bootstrap_efficiency_v54_latest.json",
        ROOT / report["storage"]["success_room"],
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    aggregate = acceptance["aggregate"]
    print(json.dumps({
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "operator_retention_ratio": aggregate["operator_retention_ratio"],
        "behavior_execution_reduction": aggregate["behavior_execution_reduction"],
        "window_normalization_reduction": aggregate["window_normalization_reduction"],
        "verified_operator_efficiency_gain": aggregate["verified_operator_per_window_execution_gain"],
        "wall_clock_speedup_observed": aggregate["wall_clock_speedup_observed"],
        "api_tokens": 0,
        "dashboard_modified": False,
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
