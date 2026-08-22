from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.autonomous_science_os_v46 import (
    run_v46_acceptance,
    verify_v46_acceptance,
)


def main():
    now = datetime.now(timezone.utc)
    run_id = "RUN-autonomous-science-os-v46-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    campaign_path = ROOT / "artifacts/science/v46/state/campaign_latest.json"
    previous = None
    if campaign_path.exists():
        previous = json.loads(campaign_path.read_text(encoding="utf-8"))
    acceptance = run_v46_acceptance(previous)
    verification = verify_v46_acceptance(acceptance)
    if not acceptance["passed"] or not verification["passed"]:
        raise RuntimeError({
            "acceptance_failures": [item for item in acceptance["proof_obligations"] if not item["passed"]],
            "replay_failures": [item for item in verification["obligations"] if not item["passed"]],
        })
    report = {
        "report_version": "autonomous-science-os-v46.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "unified_bounded_autonomous_science_operating_system_verified",
        "acceptance": acceptance,
        "independent_verification": verification,
        "claim": {
            "achieved": "allowlisted autonomous network collection, sandboxed language creation, causal mechanism audits, verified instrument blueprint, persistent research management, and Crossref metadata audit",
            "not_achieved": "physical fabrication, a new intervention on an unknown natural system, independent-laboratory replication, exhaustive literature review, a human-unknown law, or a fully autonomous scientist",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "autonomous_science_os_v46_report.json"
    campaign_path.parent.mkdir(parents=True, exist_ok=True)
    campaign_path.write_text(json.dumps(
        acceptance["long_horizon_research"]["campaign"], ensure_ascii=False, indent=2,
    ), encoding="utf-8")
    stores = {
        ROOT / "artifacts/science/v46/semantics/invented_opcode_latest.json": acceptance["open_language_creation"],
        ROOT / "artifacts/science/v46/causal/mechanism_audit_latest.json": acceptance["causal_and_mechanism_reasoning"],
        ROOT / "artifacts/science/v46/instruments/blueprint_latest.json": acceptance["instrument_architecture"],
        ROOT / "artifacts/science/v46/literature/audit_latest.json": acceptance["literature_and_human_knowledge_audit"],
    }
    for destination, payload in stores.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report["storage"] = {
        "campaign_state": "artifacts/science/v46/state/campaign_latest.json",
        "semantic_room": "artifacts/science/v46/semantics/invented_opcode_latest.json",
        "causal_audit": "artifacts/science/v46/causal/mechanism_audit_latest.json",
        "instrument_blueprint": "artifacts/science/v46/instruments/blueprint_latest.json",
        "literature_audit": "artifacts/science/v46/literature/audit_latest.json",
    }
    report["content_digest"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for destination in (
        ROOT / "reports/data/autonomous_science_os_v46_latest.json",
        ROOT / "dashboard/data/autonomous_science_os_v46_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "status": acceptance["final_status"],
        "network_records": acceptance["network_reality"]["collection"]["record_count"],
        "network_source": acceptance["network_reality"]["agenda"]["selected"]["source_id"],
        "invented_opcode": acceptance["open_language_creation"]["invented_semantic"]["semantic_id"],
        "instrument_blueprint": acceptance["instrument_architecture"]["blueprint"]["blueprint_id"],
        "campaign_cycle": acceptance["long_horizon_research"]["campaign"]["cycle_index"],
        "next_task": acceptance["long_horizon_research"]["campaign"]["next_selected_task"],
        "literature_status": acceptance["literature_and_human_knowledge_audit"]["audit_status"],
        "physical_fabrication_executed": False,
        "fully_autonomous_scientist": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
