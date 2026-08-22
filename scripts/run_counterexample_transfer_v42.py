from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.counterexample_transfer_v42 import run_v42_acceptance


def main():
    now = datetime.now(timezone.utc)
    run_id = "RUN-counterexample-transfer-v42-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v42_acceptance()
    if not acceptance["passed"]:
        failed = [item for item in acceptance["proof_obligations"] if not item["passed"]]
        raise RuntimeError(failed)

    report = {
        "report_version": "counterexample-transfer-v42.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "reused_archive_cross_object_transfer_verified_external_replication_required",
        "acceptance": acceptance,
        "claim": {
            "achieved": "counterexample consumption, anonymous semantic competition, programmatic freeze, and cross-object transfer below the registered threshold",
            "not_achieved": "fresh human-blind replication, independent-laboratory replication, a universal battery model, or a human-unknown law",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "counterexample_transfer_v42_report.json"

    semantic = ROOT / "artifacts/science/v42/semantics/interaction_fold_latest.json"
    resolution = ROOT / "artifacts/science/v42/mistakes/v41_counterexample_retest.json"
    semantic.parent.mkdir(parents=True, exist_ok=True)
    resolution.parent.mkdir(parents=True, exist_ok=True)
    semantic.write_text(
        json.dumps(acceptance["discovery"]["selected"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    resolution.write_text(
        json.dumps(acceptance["counterexample_feedback"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report["storage"] = {
        "verified_semantic_room": "artifacts/science/v42/semantics/interaction_fold_latest.json",
        "counterexample_retest_room": "artifacts/science/v42/mistakes/v41_counterexample_retest.json",
    }
    report["content_digest"] = hashlib.sha256(
        json.dumps(report, sort_keys=True).encode()
    ).hexdigest()
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for destination in (
        ROOT / "reports/data/counterexample_transfer_v42_latest.json",
        ROOT / "dashboard/data/counterexample_transfer_v42_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)

    audit = acceptance["transfer_audit"]
    print(json.dumps({
        "run_id": run_id,
        "status": acceptance["final_status"],
        "selected_program": acceptance["discovery"]["selected"]["program_id"],
        "created_operator": acceptance["discovery"]["selected"]["created_operator"],
        "validation_rmse": acceptance["discovery"]["selected"]["validation_rmse"],
        "transfer_overall_rmse": audit["overall"]["rmse"],
        "transfer_early_rmse": audit["by_life_stage"]["early"]["rmse"],
        "transfer_middle_rmse": audit["by_life_stage"]["middle"]["rmse"],
        "transfer_late_rmse": audit["by_life_stage"]["late"]["rmse"],
        "fresh_human_blind_replication": False,
        "universal_model_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
