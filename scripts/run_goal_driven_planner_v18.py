"""Run and publish V18 goal-driven planning acceptance evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.goal_driven_planner_v18 import run_v18_acceptance  # noqa: E402


def _digest(report: dict) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-goal-planner-v18-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v18_acceptance(independent_runs=3, problems_per_run=36)
    if not acceptance["passed"]:
        failed = [item["obligation_id"] for item in acceptance["proof_obligations"] if not item["passed"]]
        raise RuntimeError(f"V18 acceptance failed: {failed}")
    report = {
        "report_version": "goal-driven-program-planner-v18.0",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "goal_driven_use_of_invented_runtime_semantics_passed",
        "acceptance": acceptance,
        "capability_change": {
            "before": "V17 invented and verified tools without selecting them to reach a supplied goal",
            "after": "uniform-cost planning composes invented runtime semantics into independently replayable solutions for unseen bounded goals",
            "solution_witness_supplied_to_planner": False,
            "invented_operators_used_in_every_accepted_problem": True,
            "natural_language_problem_solving_proven": False,
        },
        "claim": {
            "achieved": "verified goal-driven program synthesis over unseen bounded counter-state problems",
            "not_claimed": "natural-language understanding, unrestricted symbolic mathematics, or theorem proving",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "goal_driven_planner_report.json"
    mistake_path = ROOT / "artifacts/foundation/v18/mistakes/rejected_goal_plans.jsonl"
    mistake_path.parent.mkdir(parents=True, exist_ok=True)
    mistakes = [
        {
            "schema_version": "goal-plan-mistake-v18.0",
            "run_index": run["run_index"],
            "kind": "truncated_plan_counterexample",
            **run["mutation_audit"],
        }
        for run in acceptance["runs"]
    ]
    mistake_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in mistakes),
        encoding="utf-8",
    )
    report["storage"] = {
        "success_report": "artifacts/foundation/v18/success/goal_driven_planner_latest.json",
        "mistake_room": str(mistake_path.relative_to(ROOT)).replace("\\", "/"),
        "wrong_plan_records": len(mistakes),
    }
    report["content_digest"] = _digest(report)
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/goal_driven_planner_v18_latest.json",
        ROOT / "dashboard/data/goal_driven_planner_v18_latest.json",
        ROOT / "artifacts/foundation/v18/success/goal_driven_planner_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    aggregate = acceptance["aggregate"]
    print(json.dumps({
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "problems": aggregate["problem_count"],
        "solved_and_verified": f"{aggregate['verified_count']}/{aggregate['problem_count']}",
        "dynamic_use": aggregate["dynamic_use_problem_count"],
        "improved": aggregate["improved_problem_count"],
        "baseline_tokens": aggregate["baseline_tokens"],
        "learned_tokens": aggregate["learned_tokens"],
        "token_reduction": aggregate["token_reduction"],
        "classification": acceptance["classification"],
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

