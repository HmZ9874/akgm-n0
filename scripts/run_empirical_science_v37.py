from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.empirical_science_v37 import run_v37_acceptance


def main():
    dependency = json.loads((ROOT / "reports/data/scientific_discovery_v36_latest.json").read_text(encoding="utf-8"))
    if not dependency["acceptance"]["passed"]:
        raise RuntimeError("V36 scientific workflow dependency is not accepted")
    now = datetime.now(timezone.utc)
    run_id = "RUN-empirical-science-v37-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v37_acceptance()
    if not acceptance["passed"]:
        raise RuntimeError([item for item in acceptance["proof_obligations"] if not item["passed"]])
    report = {
        "report_version": "empirical-science-v37.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "real_archive_known_law_rediscovery_pipeline_verified",
        "acceptance": acceptance,
        "dependency": {"v36_run_id": dependency["run_id"], "v36_passed": True},
        "claim": {
            "achieved": "real public archive ingestion, subprocess sealing, anonymous robust law selection, preregistered holdout prediction, uncertainty and null audits",
            "not_achieved": "independent confirmation of a new law of nature",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "empirical_science_report.json"
    report["storage"] = {
        "rediscovery_room": "artifacts/science/v37/rediscoveries/kepler_like_relation_latest.json",
        "human_discovery_room": None,
        "data_snapshot": "data/nasa_exoplanet_v37_snapshot.csv",
        "provenance": "data/nasa_exoplanet_v37_provenance.json",
    }
    report["content_digest"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    destinations = (
        ROOT / "reports/data/empirical_science_v37_latest.json",
        ROOT / "dashboard/data/empirical_science_v37_latest.json",
        ROOT / "artifacts/science/v37/rediscoveries/kepler_like_relation_latest.json",
    )
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    selected = acceptance["discovery"]["selected_program"]
    print(json.dumps({
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "real_rows": acceptance["dataset"]["metadata"]["rows"],
        "train_holdout": f"{acceptance['dataset']['metadata']['train_rows']}/{acceptance['dataset']['metadata']['holdout_rows']}",
        "opaque_program": selected["opaque_program"],
        "bootstrap_stability": acceptance["discovery"]["bootstrap_selection_rate"],
        "holdout_mape": acceptance["holdout_audit"]["median_absolute_percentage_error"],
        "label": acceptance["claim_state"]["current_label"],
        "human_unknown_claim_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
