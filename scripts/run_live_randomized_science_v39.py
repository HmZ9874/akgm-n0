from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.live_randomized_science_v39 import run_v39_acceptance


def main():
    dependency = json.loads((ROOT / "reports/data/interventional_science_v38_latest.json").read_text(encoding="utf-8"))
    if not dependency["acceptance"]["passed"]:
        raise RuntimeError("V38 interventional science dependency is not accepted")
    now = datetime.now(timezone.utc)
    run_id = "RUN-live-randomized-science-v39-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v39_acceptance()
    if not acceptance["passed"]:
        raise RuntimeError([item for item in acceptance["proof_obligations"] if not item["passed"]])
    report = {
        "report_version": "live-randomized-science-v39.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "live_randomized_adaptive_computational_experiment_loop_verified",
        "acceptance": acceptance,
        "dependency": {"v38_run_id": dependency["run_id"], "v38_passed": True},
        "claim": {
            "achieved": "live measurement, randomized intervention order, adaptive next-experiment choice, prospective holdout and new-process replication",
            "not_achieved": "natural-science discovery, an external laboratory result, or a human-unknown law",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "live_randomized_science_report.json"
    mistakes = ROOT / "artifacts/science/v39/mistakes/rejected_protocol_mutations.jsonl"
    mistakes.parent.mkdir(parents=True, exist_ok=True)
    mistakes.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in acceptance["mutation_audits"]), encoding="utf-8")
    report["storage"] = {
        "calibration_room": "artifacts/science/v39/calibrations/live_scale_latest.json",
        "mistake_room": "artifacts/science/v39/mistakes/rejected_protocol_mutations.jsonl",
        "human_discovery_room": None,
    }
    report["content_digest"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    destinations = (
        ROOT / "reports/data/live_randomized_science_v39_latest.json",
        ROOT / "dashboard/data/live_randomized_science_v39_latest.json",
        ROOT / "artifacts/science/v39/calibrations/live_scale_latest.json",
    )
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    model = acceptance["model_competition"]["selected"]
    print(json.dumps({
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "live_measurements": len(acceptance["measurements"]),
        "adaptive_rounds": acceptance["adaptive_experiment_audit"]["round_count"],
        "selected_exponent": model["exponent_quarters"] / 4,
        "holdout_error": acceptance["prospective_holdout_audit"]["absolute_percentage_error"],
        "replication_error": acceptance["new_process_replication_audit"]["median_absolute_percentage_error"],
        "label": acceptance["claim_state"]["current_label"],
        "human_unknown_claim_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
