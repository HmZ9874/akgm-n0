from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.scientific_discovery_machine_v36 import run_v36_acceptance


def main():
    mechanics_report = json.loads((ROOT / "reports/data/relativistic_boundary_v35_latest.json").read_text(encoding="utf-8"))
    if not mechanics_report["acceptance"]["passed"]:
        raise RuntimeError("V35 mechanics foundation is not accepted")
    now = datetime.now(timezone.utc)
    run_id = "RUN-scientific-discovery-v36-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v36_acceptance()
    if not acceptance["passed"]:
        raise RuntimeError([item for item in acceptance["proof_obligations"] if not item["passed"]])
    report = {
        "report_version": "scientific-discovery-machine-v36.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "scientific_discovery_workflow_verified_human_novelty_claim_blocked",
        "acceptance": acceptance,
        "dependency": {
            "v35_run_id": mechanics_report["run_id"],
            "v35_passed": True,
            "mechanics_domains": "15/15",
        },
        "claim": {
            "achieved": "blind active hypothesis discrimination, preregistered prediction, sealed reveal, local novelty triage, falsification, and independent synthetic replication",
            "not_achieved": "a discovery new to humanity or a validated law of nature",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "scientific_discovery_report.json"
    mistakes = ROOT / "artifacts/science/v36/mistakes/rejected_hypotheses.jsonl"
    mistakes.parent.mkdir(parents=True, exist_ok=True)
    mistakes.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in acceptance["mutation_audits"]), encoding="utf-8")
    report["storage"] = {
        "candidate_room": "artifacts/science/v36/candidates/local_novel_candidate_latest.json",
        "mistake_room": "artifacts/science/v36/mistakes/rejected_hypotheses.jsonl",
        "human_discovery_room": None,
    }
    report["content_digest"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    destinations = (
        ROOT / "reports/data/scientific_discovery_v36_latest.json",
        ROOT / "dashboard/data/scientific_discovery_v36_latest.json",
        ROOT / "artifacts/science/v36/candidates/local_novel_candidate_latest.json",
    )
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    discovery = acceptance["frontier_world"]["discovery"]
    print(json.dumps({
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "candidate_program": discovery["selected_program"]["opaque_program"],
        "competing_models": discovery["initial_candidate_count"],
        "active_rounds": len(discovery["active_experiments"]),
        "sealed_prediction": acceptance["frontier_world"]["preregistration"]["passed"],
        "replication": acceptance["independent_replication"]["passed"],
        "label": acceptance["claim_state"]["current_label"],
        "human_unknown_claim_allowed": acceptance["claim_state"]["human_unknown_claim_allowed"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
