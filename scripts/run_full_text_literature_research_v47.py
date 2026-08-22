from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.full_text_literature_research_v47 import (
    run_v47_acceptance,
    verify_v47_acceptance,
)


def main():
    now = datetime.now(timezone.utc)
    run_id = "RUN-full-text-literature-research-v47-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v47_acceptance()
    verification = verify_v47_acceptance(acceptance)
    if not acceptance["passed"] or not verification["passed"]:
        raise RuntimeError({
            "acceptance_failures": [item for item in acceptance["proof_obligations"] if not item["passed"]],
            "verification_failures": [item for item in verification["obligations"] if not item["passed"]],
        })
    report = {
        "report_version": "full-text-literature-research-v47.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "autonomous_open_full_text_prior_art_audit_verified",
        "acceptance": acceptance,
        "independent_verification": verification,
        "research_result": {
            "discovered_this_cycle": "the internal semantic belongs to established symbolic-regression/program-search territory; reusable semantics, guarded forms, interaction terms, and parsimony all have related open prior art",
            "not_discovered": "no human-unknown operation or law was established, and exact identity of the complete OPX composite was not established",
            "next_autonomous_task": acceptance["long_horizon_research"]["campaign"]["next_selected_task"],
        },
    }
    report["content_digest"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "full_text_literature_research_v47_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    stores = {
        ROOT / "artifacts/science/v47/literature/audit_latest.json": acceptance["prior_art_audit"],
        ROOT / "artifacts/science/v47/state/campaign_latest.json": acceptance["long_horizon_research"]["campaign"],
        ROOT / "artifacts/science/v47/evidence/open_full_text_receipts_latest.json": acceptance["open_full_text_evidence"],
    }
    for destination, payload in stores.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for destination in (
        ROOT / "reports/data/full_text_literature_research_v47_latest.json",
        ROOT / "dashboard/data/full_text_literature_research_v47_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "status": acceptance["final_status"],
        "classification": acceptance["prior_art_audit"]["audit_status"],
        "metadata_records": acceptance["autonomous_research_action"]["metadata_record_count"],
        "full_text_documents": acceptance["autonomous_research_action"]["full_text_document_count"],
        "network_requests": acceptance["autonomous_research_action"]["network_request_count"],
        "remaining_network_budget": acceptance["long_horizon_research"]["campaign"]["budgets"]["network_requests_remaining"],
        "next_task": acceptance["long_horizon_research"]["campaign"]["next_selected_task"],
        "human_unknown_law": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
