from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.event_world_semantic_search_v49 import (
    run_v49_acceptance,
    verify_v49_acceptance,
)


def main():
    now = datetime.now(timezone.utc)
    run_id = "RUN-event-world-semantic-search-v49-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v49_acceptance()
    verification = verify_v49_acceptance(acceptance)
    if not acceptance["passed"] or not verification["passed"]:
        raise RuntimeError({
            "acceptance_failures": [item for item in acceptance["proof_obligations"] if not item["passed"]],
            "verification_failures": [item for item in verification["obligations"] if not item["passed"]],
        })
    program = acceptance["autonomous_language_search"]
    gap_payload = {
        "failed_world_id": acceptance["task_selection"]["target_world_id"],
        "candidate_count": program["candidate_programs_evaluated"],
        "validation_ratio": program["validation"]["rmse_ratio_to_zero_baseline"],
        "sealed_ratio": acceptance["sealed_transfer"]["rmse_ratio_to_zero_baseline"],
        "action": "invent_new_observables_or_language_resources",
    }
    gap_semantic = {
        "semantic_id": "GAPSEM-" + hashlib.sha256(
            json.dumps(gap_payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16],
        "kind": "verified_evidence_gap_state",
        **gap_payload,
        "formula_promotion_blocked": True,
        "meaning": "the registered observables and current finite language do not support a stable predictive semantic",
    }
    report = {
        "report_version": "event-world-semantic-search-v49.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "verified_negative_discovery_and_evidence_gap",
        "acceptance": acceptance,
        "independent_verification": verification,
        "new_gap_semantic": gap_semantic,
        "research_result": {
            "candidate_programs_evaluated": program["candidate_programs_evaluated"],
            "best_program": program["program_id"],
            "best_program_features": program["features"],
            "local_formula_accepted": acceptance["local_formula_accepted"],
            "finding": "no supplied observable, lag, delta, self-coupling, pair interaction, or guarded path produced stable predictive gain on the anonymous event world",
            "posthoc_interpretation": "the current USGS catalog channels do not support a validated magnitude predictor in this finite search language",
            "next_autonomous_task": acceptance["long_horizon_research"]["campaign"]["next_selected_task"],
        },
    }
    report["content_digest"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "event_world_semantic_search_v49_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    stores = {
        ROOT / "artifacts/science/v49/mistakes/event_world_latest.json": acceptance["mistake_room"],
        ROOT / "artifacts/science/v49/gaps/evidence_gap_latest.json": gap_semantic,
        ROOT / "artifacts/science/v49/state/campaign_latest.json": acceptance["long_horizon_research"]["campaign"],
    }
    for destination, payload in stores.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for destination in (
        ROOT / "reports/data/event_world_semantic_search_v49_latest.json",
        ROOT / "dashboard/data/event_world_semantic_search_v49_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "status": acceptance["final_status"],
        "programs_evaluated": program["candidate_programs_evaluated"],
        "best_program": program["program_id"],
        "validation_ratio": program["validation"]["rmse_ratio_to_zero_baseline"],
        "sealed_ratio": acceptance["sealed_transfer"]["rmse_ratio_to_zero_baseline"],
        "local_formula_accepted": acceptance["local_formula_accepted"],
        "gap_semantic": gap_semantic["semantic_id"],
        "next_task": acceptance["long_horizon_research"]["campaign"]["next_selected_task"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
