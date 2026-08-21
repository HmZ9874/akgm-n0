from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.interventional_science_v38 import run_v38_acceptance


def main():
    dependency = json.loads((ROOT / "reports/data/empirical_science_v37_latest.json").read_text(encoding="utf-8"))
    if not dependency["acceptance"]["passed"]:
        raise RuntimeError("V37 empirical science dependency is not accepted")
    now = datetime.now(timezone.utc)
    run_id = "RUN-interventional-science-v38-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v38_acceptance()
    if not acceptance["passed"]:
        raise RuntimeError([item for item in acceptance["proof_obligations"] if not item["passed"]])
    report = {
        "report_version": "interventional-science-v38.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "controlled_intervention_direction_and_known_calibration_mechanism_verified_with_drift_block",
        "acceptance": acceptance,
        "dependency": {"v37_run_id": dependency["run_id"], "v37_passed": True},
        "claim": {
            "achieved": "controlled-variable causal direction, mechanism complexity selection, sealed second-batch prediction, repeatability noise and drift-risk audit",
            "not_achieved": "a randomized drift-free live causal discovery or a human-novel mechanism",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "interventional_science_report.json"
    mistakes = ROOT / "artifacts/science/v38/mistakes/rejected_causal_graphs.jsonl"
    mistakes.parent.mkdir(parents=True, exist_ok=True)
    mistakes.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in acceptance["mutation_audits"]), encoding="utf-8")
    report["storage"] = {
        "rediscovery_room": "artifacts/science/v38/rediscoveries/nist_quadratic_calibration_latest.json",
        "mistake_room": "artifacts/science/v38/mistakes/rejected_causal_graphs.jsonl",
        "human_discovery_room": None,
    }
    report["content_digest"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    destinations = (
        ROOT / "reports/data/interventional_science_v38_latest.json",
        ROOT / "dashboard/data/interventional_science_v38_latest.json",
        ROOT / "artifacts/science/v38/rediscoveries/nist_quadratic_calibration_latest.json",
    )
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    selected = acceptance["discovery"]["selected_mechanism"]
    print(json.dumps({
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "rows": acceptance["dataset"]["metadata"]["rows"],
        "graph": selected["direction"],
        "degree": selected["degree"],
        "unseen_interventions": acceptance["future_batch_audit"]["unseen_intervention_count"],
        "future_mape": acceptance["future_batch_audit"]["median_absolute_percentage_error"],
        "label": acceptance["claim_state"]["current_label"],
        "clean_causal_effect_claim_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
