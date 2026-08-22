from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.autonomous_scientist_v43 import (
    run_v43_acceptance,
    verify_v43_acceptance,
)


def main():
    now = datetime.now(timezone.utc)
    run_id = "RUN-autonomous-scientist-v43-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v43_acceptance()
    independent_verification = verify_v43_acceptance(acceptance)
    if not acceptance["passed"] or not independent_verification["passed"]:
        raise RuntimeError({
            "acceptance_failures": [
                item for item in acceptance["proof_obligations"] if not item["passed"]
            ],
            "replay_failures": [
                item for item in independent_verification["obligations"]
                if not item["passed"]
            ],
        })

    report = {
        "report_version": "autonomous-scientist-kernel-v43.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "bounded_autonomous_research_language_growth_verified",
        "acceptance": acceptance,
        "independent_verification": independent_verification,
        "claim": {
            "achieved": "autonomous generic language-resource growth, score-selected agenda, semantic-saturation stop, frozen transfer, and independent replay",
            "not_achieved": "a fully autonomous scientist, unrestricted language invention, fresh external replication, live apparatus control, or a human-unknown law",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "autonomous_scientist_v43_report.json"
    semantic = ROOT / "artifacts/science/v43/semantics/autonomous_update_latest.json"
    agenda = ROOT / "artifacts/science/v43/ledger/research_language_growth_latest.json"
    semantic.parent.mkdir(parents=True, exist_ok=True)
    agenda.parent.mkdir(parents=True, exist_ok=True)
    semantic.write_text(json.dumps(
        acceptance["discovery"]["selected_program"], ensure_ascii=False, indent=2,
    ), encoding="utf-8")
    agenda.write_text(json.dumps({
        "menu_gap": acceptance["menu_gap"],
        "selected_mutations": acceptance["discovery"]["selected_mutations"],
        "rounds": acceptance["discovery"]["rounds"],
        "stop_reason": acceptance["discovery"]["stop_reason"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    report["storage"] = {
        "semantic_room": "artifacts/science/v43/semantics/autonomous_update_latest.json",
        "research_ledger": "artifacts/science/v43/ledger/research_language_growth_latest.json",
    }
    report["content_digest"] = hashlib.sha256(
        json.dumps(report, sort_keys=True).encode()
    ).hexdigest()
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for destination in (
        ROOT / "reports/data/autonomous_scientist_v43_latest.json",
        ROOT / "dashboard/data/autonomous_scientist_v43_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)

    transfer = acceptance["transfer_audit"]
    selected = acceptance["discovery"]["selected_program"]
    print(json.dumps({
        "run_id": run_id,
        "status": acceptance["final_status"],
        "program_id": selected["program_id"],
        "selected_mutations": acceptance["discovery"]["selected_mutations"],
        "final_genome": acceptance["discovery"]["final_genome"],
        "candidate_programs_evaluated": acceptance["discovery"]["candidate_programs_evaluated"],
        "stop_reason": acceptance["discovery"]["stop_reason"],
        "transfer_overall_rmse": transfer["overall"]["rmse"],
        "transfer_early_rmse": transfer["by_life_stage"]["early"]["rmse"],
        "transfer_middle_rmse": transfer["by_life_stage"]["middle"]["rmse"],
        "transfer_late_rmse": transfer["by_life_stage"]["late"]["rmse"],
        "fully_autonomous_scientist_achieved": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
