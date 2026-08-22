from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.autonomous_intervention_v45 import (
    run_v45_acceptance,
    verify_v45_acceptance,
)


def main():
    now = datetime.now(timezone.utc)
    run_id = "RUN-autonomous-intervention-v45-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v45_acceptance()
    verification = verify_v45_acceptance(acceptance)
    if not acceptance["passed"] or not verification["passed"]:
        raise RuntimeError({
            "acceptance_failures": [item for item in acceptance["proof_obligations"] if not item["passed"]],
            "replay_failures": [item for item in verification["obligations"] if not item["passed"]],
            "selected_program": acceptance["language_growth"]["selected_program"],
            "selected_mutations": acceptance["language_growth"]["selected_mutations"],
            "transfer": acceptance["sealed_counterfactual_audit"],
        })
    report = {
        "report_version": "autonomous-intervention-v45.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "bounded_autonomous_live_computational_intervention_verified",
        "acceptance": acceptance,
        "independent_verification": verification,
        "claim": {
            "achieved": "autonomous multi-control intervention design, safe live execution, language growth, causal effect audit, preregistered sealed counterfactual transfer, and fresh-process replay",
            "not_achieved": "intervention on an unknown natural physical system, independent-laboratory replication, a human-unknown law, or a fully autonomous scientist",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "autonomous_intervention_v45_report.json"
    destinations = {
        ROOT / "artifacts/science/v45/semantics/causal_program_latest.json": acceptance["language_growth"]["selected_program"],
        ROOT / "artifacts/science/v45/ledger/experiment_agenda_latest.json": acceptance["autonomous_experiment_design"],
        ROOT / "artifacts/science/v45/mistakes/rejected_mechanisms_latest.json": acceptance["mistake_room"],
    }
    for destination, payload in destinations.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report["storage"] = {
        "semantic_room": "artifacts/science/v45/semantics/causal_program_latest.json",
        "research_ledger": "artifacts/science/v45/ledger/experiment_agenda_latest.json",
        "mistake_room": "artifacts/science/v45/mistakes/rejected_mechanisms_latest.json",
    }
    report["content_digest"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for destination in (
        ROOT / "reports/data/autonomous_intervention_v45_latest.json",
        ROOT / "dashboard/data/autonomous_intervention_v45_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "status": acceptance["final_status"],
        "experiment_count": acceptance["autonomous_experiment_design"]["experiment_count"],
        "selected_mutations": acceptance["language_growth"]["selected_mutations"],
        "program_id": acceptance["language_growth"]["selected_program"]["program_id"],
        "transfer_rmse": acceptance["sealed_counterfactual_audit"]["rmse"],
        "stop_reason": acceptance["autonomous_experiment_design"]["stop_reason"],
        "natural_physical_system": False,
        "fully_autonomous_scientist": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
