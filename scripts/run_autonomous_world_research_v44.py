from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.autonomous_world_research_v44 import (
    run_v44_acceptance,
    verify_v44_acceptance,
)


def main():
    now = datetime.now(timezone.utc)
    run_id = "RUN-autonomous-world-research-v44-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v44_acceptance()
    verification = verify_v44_acceptance(acceptance)
    if not acceptance["passed"] or not verification["passed"]:
        raise RuntimeError({
            "acceptance_failures": [item for item in acceptance["proof_obligations"] if not item["passed"]],
            "replay_failures": [item for item in verification["obligations"] if not item["passed"]],
        })
    report = {
        "report_version": "autonomous-world-research-v44.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "bounded_autonomous_official_world_selection_verified",
        "acceptance": acceptance,
        "independent_verification": verification,
        "claim": {
            "achieved": "anonymous multi-world ranking, autonomous agenda selection, preregistration, source-group-isolated transfer, failure memory, and independent replay",
            "not_achieved": "unrestricted language invention, causal intervention, live apparatus control, independent-laboratory replication, a human-unknown law, or a fully autonomous scientist",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "autonomous_world_research_v44_report.json"
    semantic = ROOT / "artifacts/science/v44/semantics/selected_world_program_latest.json"
    agenda = ROOT / "artifacts/science/v44/ledger/autonomous_agenda_latest.json"
    mistakes = ROOT / "artifacts/science/v44/mistakes/mistake_room_latest.json"
    for destination, payload in (
        (semantic, acceptance["discovery"]["selected_program"]),
        (agenda, acceptance["autonomous_agenda"]),
        (mistakes, acceptance["mistake_room"]),
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report["storage"] = {
        "semantic_room": "artifacts/science/v44/semantics/selected_world_program_latest.json",
        "research_ledger": "artifacts/science/v44/ledger/autonomous_agenda_latest.json",
        "mistake_room": "artifacts/science/v44/mistakes/mistake_room_latest.json",
    }
    report["content_digest"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for destination in (
        ROOT / "reports/data/autonomous_world_research_v44_latest.json",
        ROOT / "dashboard/data/autonomous_world_research_v44_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "status": acceptance["final_status"],
        "selected_world_id": acceptance["autonomous_agenda"]["selected_world_id"],
        "program_id": acceptance["discovery"]["selected_program"]["program_id"],
        "selected_mutations": acceptance["discovery"]["selected_mutations"],
        "validation_normalized_error": acceptance["discovery"]["validation_normalized_error"],
        "transfer_normalized_rmse": acceptance["sealed_transfer_audit"]["normalized_rmse"],
        "posthoc_domain": acceptance["posthoc_translation"]["domain"],
        "queued_worlds": len(acceptance["autonomous_agenda"]["next_research_queue"]),
        "fully_autonomous_scientist_achieved": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
