from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.breakthrough_research_v51 import (
    run_v51_acceptance,
    verify_v51_acceptance,
)


def main():
    now = datetime.now(timezone.utc)
    run_id = "RUN-breakthrough-research-v51-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v51_acceptance()
    verification = verify_v51_acceptance(acceptance)
    if not acceptance["passed"] or not verification["passed"]:
        raise RuntimeError("V51 independent verification failed")
    report = {
        "report_version": "breakthrough-research-v51.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "architecture_upgraded_breakthrough_not_established",
        "acceptance": acceptance,
        "independent_verification": verification,
    }
    report["content_digest"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "breakthrough_research_v51_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for destination in (
        ROOT / "reports/data/breakthrough_research_v51_latest.json",
        ROOT / "dashboard/data/breakthrough_research_v51_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    axes = acceptance["ten_gate_standard"]["axes"]
    print(json.dumps({
        "run_id": run_id,
        "status": acceptance["final_status"],
        "scores": {axis["axis_id"]: f'{axis["score"]}/10' for axis in axes},
        "representation_id": acceptance["representation_forge"]["representation_id"],
        "mechanism_id": acceptance["mechanism_tournament"]["selected"]["mechanism_id"],
        "breakthrough_claim_allowed": acceptance["claim_state"]["breakthrough_claim_allowed"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
