"""Run and publish the V17 autonomous research-loop benchmark."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.autonomous_research_loop_v17 import run_v17_acceptance  # noqa: E402


def _digest(report: dict) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-autonomous-research-v17-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v17_acceptance(independent_runs=5)
    if not acceptance["passed"]:
        failed = [item["obligation_id"] for item in acceptance["proof_obligations"] if not item["passed"]]
        raise RuntimeError(f"V17 acceptance failed: {failed}")

    report = {
        "report_version": "autonomous-research-loop-v17.0",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "bounded_autonomous_research_and_semantic_saturation_passed",
        "acceptance": acceptance,
        "capability_change": {
            "before": "V16 required an external script to supply each anonymous workload corpus",
            "after": "the loop diagnoses its current semantic gap, selects an experiment, generates worlds, learns, verifies, and stops at measured saturation",
            "external_per_round_world_selection_required": False,
            "external_per_round_stop_decision_required": False,
            "unbounded_research_saturation_proven": False,
        },
        "claim": {
            "achieved": "autonomous experiment selection and semantic saturation inside a finite declared research charter",
            "not_claimed": "saturation of mathematics as a whole or removal of all externally supplied safety boundaries",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "autonomous_research_report.json"
    mistake_path = ROOT / "artifacts/foundation/v17/mistakes/autonomous_research_rejections.jsonl"
    mistake_path.parent.mkdir(parents=True, exist_ok=True)
    mistakes = []
    for run_index, run in enumerate(acceptance["runs"]):
        mistakes.append({
            "schema_version": "autonomous-research-mistake-v17.0",
            "run_index": run_index,
            "kind": "mutated_semantic_counterexample",
            **run["mutation_audit"],
        })
        for round_ in run["rounds"]:
            if round_["rejected_candidate_count"]:
                mistakes.append({
                    "schema_version": "autonomous-research-mistake-v17.0",
                    "run_index": run_index,
                    "kind": "round_rejection_summary",
                    "round_index": round_["round_index"],
                    "gap_id": round_["gap"]["gap_id"],
                    "rejected_candidate_count": round_["rejected_candidate_count"],
                })
    mistake_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in mistakes),
        encoding="utf-8",
    )
    report["storage"] = {
        "success_report": "artifacts/foundation/v17/success/autonomous_research_latest.json",
        "mistake_room": str(mistake_path.relative_to(ROOT)).replace("\\", "/"),
        "mistake_records": len(mistakes),
    }
    report["content_digest"] = _digest(report)
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/autonomous_research_v17_latest.json",
        ROOT / "dashboard/data/autonomous_research_v17_latest.json",
        ROOT / "artifacts/foundation/v17/success/autonomous_research_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)

    print(json.dumps({
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "autonomous_runs": acceptance["independent_run_count"],
        "research_rounds": acceptance["aggregate"]["research_rounds"],
        "self_generated_worlds": acceptance["aggregate"]["self_generated_worlds"],
        "operators_discovered": acceptance["aggregate"]["operators_discovered"],
        "saturation_stops": acceptance["aggregate"]["saturation_stops"],
        "certificate_cases": acceptance["aggregate"]["certificate_cases"],
        "classification": acceptance["classification"],
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

