from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.external_physical_science_v40 import run_v40_acceptance


def main():
    dependency = json.loads((ROOT / "reports/data/live_randomized_science_v39_latest.json").read_text(encoding="utf-8"))
    if not dependency["acceptance"]["passed"]:
        raise RuntimeError("V39 live randomized science dependency is not accepted")
    now = datetime.now(timezone.utc)
    run_id = "RUN-external-physical-science-v40-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v40_acceptance()
    report = {
        "report_version": "external-physical-science-v40.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "external_physical_experiment_verified" if acceptance["passed"] else "external_physical_experiment_blocked",
        "acceptance": acceptance,
        "dependency": {"v39_run_id": dependency["run_id"], "v39_passed": True},
        "claim": {
            "achieved": "domain-blind control of an external optical sensor, adaptive interventions, prospective prediction and new-process replication",
            "not_achieved": "a human-unknown natural law or multi-site independent replication",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "external_physical_science_report.json"
    receipt_path = ROOT / "artifacts/science/v40/receipts/physical_receipts.jsonl"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text("".join(json.dumps(receipt, ensure_ascii=False) + "\n" for receipt in acceptance["physical_receipt_audit"]["receipts"]), encoding="utf-8")
    mistakes = ROOT / "artifacts/science/v40/mistakes/rejected_protocol_mutations.jsonl"
    mistakes.parent.mkdir(parents=True, exist_ok=True)
    mistakes.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in acceptance["mutation_audits"]), encoding="utf-8")
    report["storage"] = {
        "physical_calibration_room": "artifacts/science/v40/calibrations/external_optical_latest.json",
        "receipt_room": "artifacts/science/v40/receipts/physical_receipts.jsonl",
        "mistake_room": "artifacts/science/v40/mistakes/rejected_protocol_mutations.jsonl",
        "raw_image_room": None,
        "human_discovery_room": None,
    }
    report["content_digest"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    destinations = (
        ROOT / "reports/data/external_physical_science_v40_latest.json",
        ROOT / "dashboard/data/external_physical_science_v40_latest.json",
        ROOT / "artifacts/science/v40/calibrations/external_optical_latest.json",
    )
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    summary = {
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "passed": acceptance["passed"],
        "physical_receipts": acceptance["physical_receipt_audit"]["receipt_count"],
        "unique_raw_digests": acceptance["physical_receipt_audit"]["unique_raw_digest_count"],
        "response_range": acceptance["physical_receipt_audit"]["response_range"],
        "holdout_error": acceptance["prospective_holdout_audit"]["absolute_percentage_error"],
        "replication_error": acceptance["new_process_replication_audit"]["median_absolute_percentage_error"],
        "label": acceptance["claim_state"]["current_label"],
        "human_unknown_claim_allowed": False,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not acceptance["passed"]:
        print(json.dumps([item for item in acceptance["proof_obligations"] if not item["passed"]], ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
