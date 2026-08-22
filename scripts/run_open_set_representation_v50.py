from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.open_set_representation_v50 import (
    run_v50_acceptance,
    verify_v50_acceptance,
)


def main():
    now = datetime.now(timezone.utc)
    run_id = "RUN-open-set-representation-v50-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v50_acceptance()
    verification = verify_v50_acceptance(acceptance)
    if not acceptance["passed"] or not verification["passed"]:
        raise RuntimeError({
            "acceptance_failures": [item for item in acceptance["proof_obligations"] if not item["passed"]],
            "verification_failures": [item for item in verification["obligations"] if not item["passed"]],
        })
    selected = acceptance["representation_discovery"]["selected"]
    report = {
        "report_version": "open-set-representation-v50.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "meaningful_bounded_set_relation_rediscovered",
        "acceptance": acceptance,
        "independent_verification": verification,
        "posthoc_human_knowledge_audit": {
            "status": "known_human_law_rediscovered",
            "human_family": "Gutenberg-Richter frequency-magnitude relation",
            "official_reference": "https://www.usgs.gov/publications/calculating-california-seismicity-rates",
            "historical_reference": "https://pubmed.ncbi.nlm.nih.gov/17770563/",
            "literature_available_during_discovery": False,
            "human_unknown_claim_allowed": False,
        },
        "research_result": {
            "semantic_id": acceptance["representation_discovery"]["semantic_id"],
            "internal_ast": selected["ast"],
            "constant": selected["constant"],
            "threshold_step": acceptance["anonymous_set_world"]["grid"]["step"],
            "validation_prediction_ratio": selected["validation"]["prediction_rmse_ratio"],
            "sealed_prediction_ratio": acceptance["sealed_transfer"]["prediction_rmse_ratio"],
            "sealed_constant_shift": acceptance["sealed_transfer"]["constant_relative_shift"],
            "bounded_relation_registered": acceptance["success_room"]["registered"],
            "human_equivalent": acceptance["posthoc_translation"]["human_equivalent"],
            "next_autonomous_task": acceptance["long_horizon_research"]["campaign"]["next_selected_task"],
        },
    }
    report["content_digest"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "open_set_representation_v50_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    stores = {
        ROOT / "artifacts/science/v50/success/set_relation_latest.json": acceptance["success_room"],
        ROOT / "artifacts/science/v50/mistakes/set_relation_latest.json": acceptance["mistake_room"],
        ROOT / "artifacts/science/v50/state/campaign_latest.json": acceptance["long_horizon_research"]["campaign"],
    }
    for destination, payload in stores.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for destination in (
        ROOT / "reports/data/open_set_representation_v50_latest.json",
        ROOT / "dashboard/data/open_set_representation_v50_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "status": acceptance["final_status"],
        "semantic_id": acceptance["representation_discovery"]["semantic_id"],
        "ast": selected["ast"],
        "constant": selected["constant"],
        "validation_prediction_ratio": selected["validation"]["prediction_rmse_ratio"],
        "sealed_prediction_ratio": acceptance["sealed_transfer"]["prediction_rmse_ratio"],
        "known_human_equivalent": "Gutenberg-Richter frequency-magnitude relation",
        "next_task": acceptance["long_horizon_research"]["campaign"]["next_selected_task"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
