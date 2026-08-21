from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.official_dynamic_science_v41 import run_v41_acceptance


def main():
    dependency = json.loads((ROOT / "reports/data/external_physical_science_v40_latest.json").read_text(encoding="utf-8"))
    if not dependency["acceptance"]["passed"]:
        raise RuntimeError("V40 external physical science dependency is not accepted")
    now = datetime.now(timezone.utc)
    run_id = "RUN-official-dynamic-science-v41-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v41_acceptance()
    if not acceptance["passed"]:
        raise RuntimeError([item for item in acceptance["proof_obligations"] if not item["passed"]])
    report = {
        "report_version": "official-dynamic-science-v41.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "official_nasa_dynamic_hidden_state_and_state_fold_semantic_verified",
        "acceptance": acceptance,
        "dependency": {"v40_run_id": dependency["run_id"], "v40_passed": True},
        "claim": {
            "achieved": "official physical-archive provenance, anonymous hidden-state counterexample, recurrent semantic synthesis, future trajectory prediction and cross-cell replication",
            "not_achieved": "a new live battery experiment, independent-laboratory replication, or a human-unknown electrochemical law",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "official_dynamic_science_report.json"
    mistakes = ROOT / "artifacts/science/v41/mistakes/rejected_dynamic_mutations.jsonl"
    mistakes.parent.mkdir(parents=True, exist_ok=True)
    mistakes.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in acceptance["mutation_audits"]), encoding="utf-8")
    report["storage"] = {
        "semantic_room": "artifacts/science/v41/semantics/nasa_state_fold_latest.json",
        "mistake_room": "artifacts/science/v41/mistakes/rejected_dynamic_mutations.jsonl",
        "official_archive": "data/nasa_v41/Battery_Random_Walk_Room_Temp_2Post.zip",
        "human_discovery_room": None,
    }
    report["content_digest"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    destinations = (
        ROOT / "reports/data/official_dynamic_science_v41_latest.json",
        ROOT / "dashboard/data/official_dynamic_science_v41_latest.json",
        ROOT / "artifacts/science/v41/semantics/nasa_state_fold_latest.json",
    )
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "official_traces": acceptance["dataset"]["provenance_audit"]["trace_count"],
        "created_operator": acceptance["discovery"]["selected"]["created_operator"],
        "stateful_to_stateless_rmse_ratio": acceptance["discovery"]["stateful_to_stateless_rmse_ratio"],
        "history_counterexample_delta": acceptance["history_dependence_audit"]["response_difference"],
        "future_trajectory_rmse": acceptance["future_trajectory_audit"]["rmse"],
        "cross_cell_rmse": acceptance["cross_cell_replication_audit"]["rmse"],
        "label": acceptance["claim_state"]["current_label"],
        "live_measurement_claim_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
