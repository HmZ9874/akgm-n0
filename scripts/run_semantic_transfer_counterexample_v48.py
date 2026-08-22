from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.semantic_transfer_counterexample_v48 import (
    run_v48_acceptance,
    verify_v48_acceptance,
)


def main():
    now = datetime.now(timezone.utc)
    run_id = "RUN-semantic-transfer-counterexample-v48-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v48_acceptance()
    verification = verify_v48_acceptance(acceptance)
    if not acceptance["passed"] or not verification["passed"]:
        raise RuntimeError({
            "acceptance_failures": [item for item in acceptance["proof_obligations"] if not item["passed"]],
            "verification_failures": [item for item in verification["obligations"] if not item["passed"]],
        })
    snapshot = json.loads(
        (ROOT / "data/official_worlds_v44/official_worlds_v44_snapshot.json").read_text(encoding="utf-8")
    )
    translations = {
        item["world_id"]: item["sealed_metadata"] for item in snapshot["worlds"]
    }
    search = acceptance["counterexample_driven_search"]
    report = {
        "report_version": "semantic-transfer-counterexample-v48.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "counterexample_induced_scope_semantic_verified",
        "acceptance": acceptance,
        "independent_verification": verification,
        "posthoc_world_translation": translations,
        "research_result": {
            "opx_result": "failed all three anonymous cross-domain transfers and remains valid only in its registered intervention apparatus",
            "best_replacement_candidate": {
                "program_id": search["candidate_program_id"],
                "internal_formula": "0.927335736393*PREV + -0.446960122953*DELTA",
                "human_translation": "z_t = 0.927335736393 z_(t-1) - 0.446960122953 (z_(t-1)-z_(t-2))",
                "passed_worlds": search["passed_worlds"],
                "failed_worlds": search["failed_worlds"],
                "universal_formula_accepted": search["universal_formula_accepted"],
            },
            "new_verified_semantic": acceptance["new_semantic"],
            "next_autonomous_task": acceptance["long_horizon_research"]["campaign"]["next_selected_task"],
        },
    }
    report["content_digest"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "semantic_transfer_counterexample_v48_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    stores = {
        ROOT / "artifacts/science/v48/mistakes/opx_cross_domain_latest.json": acceptance["mistake_room"],
        ROOT / "artifacts/science/v48/semantics/scope_semantic_latest.json": acceptance["new_semantic"],
        ROOT / "artifacts/science/v48/state/campaign_latest.json": acceptance["long_horizon_research"]["campaign"],
    }
    for destination, payload in stores.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for destination in (
        ROOT / "reports/data/semantic_transfer_counterexample_v48_latest.json",
        ROOT / "dashboard/data/semantic_transfer_counterexample_v48_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "status": acceptance["final_status"],
        "opx_passed_worlds": acceptance["frozen_opx_transfer"]["passed_world_count"],
        "opx_world_count": acceptance["frozen_opx_transfer"]["world_count"],
        "replacement_program": search["candidate_program_id"],
        "replacement_passed_worlds": len(search["passed_worlds"]),
        "replacement_universal": search["universal_formula_accepted"],
        "new_scope_semantic": acceptance["new_semantic"]["semantic_id"],
        "next_task": acceptance["long_horizon_research"]["campaign"]["next_selected_task"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
