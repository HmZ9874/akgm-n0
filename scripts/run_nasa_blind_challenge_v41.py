from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.nasa_blind_challenge_v41 import run_v41_blind_challenge


def main():
    now = datetime.now(timezone.utc)
    run_id = "RUN-nasa-v41-blind-challenge-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    challenge = run_v41_blind_challenge()
    if not challenge["challenge_complete"]:
        raise RuntimeError("V41 challenge protocol integrity failed")
    report = {
        "report_version": "nasa-v41-blind-challenge.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "frozen_program_bounded_by_late_life_counterexample",
        "challenge": challenge,
        "claim": {
            "achieved": "post-commit RW5/RW6 transfer test across early, middle and late life without parameter refit",
            "not_achieved": "late-life trajectory accuracy or a universal all-life state model",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "nasa_v41_blind_challenge_report.json"
    mistake = ROOT / "artifacts/science/v41/mistakes/late_life_extrapolation_counterexample.json"
    mistake.parent.mkdir(parents=True, exist_ok=True)
    mistake.write_text(json.dumps(challenge["counterexample"], ensure_ascii=False, indent=2), encoding="utf-8")
    report["storage"] = {
        "bounded_semantic_room": "artifacts/science/v41/semantics/nasa_state_fold_latest.json",
        "counterexample_room": "artifacts/science/v41/mistakes/late_life_extrapolation_counterexample.json",
    }
    report["content_digest"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for destination in (
        ROOT / "reports/data/nasa_v41_blind_challenge_latest.json",
        ROOT / "dashboard/data/nasa_v41_blind_challenge_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    audit = challenge["performance_audit"]
    print(json.dumps({
        "run_id": run_id,
        "status": challenge["final_status"],
        "challenge_traces": challenge["provenance_audit"]["trace_count"],
        "overall_rmse": audit["overall"]["rmse"],
        "overall_median_percentage_error": audit["overall"]["median_absolute_percentage_error"],
        "early_rmse": audit["by_life_stage"]["early"]["rmse"],
        "middle_rmse": audit["by_life_stage"]["middle"]["rmse"],
        "late_rmse": audit["by_life_stage"]["late"]["rmse"],
        "state_corruption_ratio": audit["state_corruption_rmse_ratio"],
        "universal_all_life_model_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
