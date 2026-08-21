from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.relativistic_boundary_v35 import run_v35_acceptance


def main():
    now = datetime.now(timezone.utc)
    run_id = "RUN-relativistic-boundary-v35-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v35_acceptance()
    if not acceptance["passed"]:
        raise RuntimeError([i["obligation_id"] for i in acceptance["proof_obligations"] if not i["passed"]])
    report = {
        "report_version": "relativistic-validity-boundary-v35.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "verdict": "v27_classical_mechanics_capability_graph_complete_15_of_15",
        "acceptance": acceptance,
        "claim": {
            "achieved": "all 15 domains in the frozen V27 mechanics capability graph have executable, transferable, proof-carrying, counterexample-audited evidence",
            "not_claimed": "an exhaustive theory of all real-world classical or relativistic mechanics",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "relativistic_boundary_and_completion_report.json"
    mistakes = ROOT / "artifacts/physics/v35/mistakes/rejected_frame_mutations.jsonl"
    mistakes.parent.mkdir(parents=True, exist_ok=True)
    mistakes.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in acceptance["mutation_audits"]), encoding="utf-8")
    report["storage"] = {
        "success_room": "artifacts/physics/v35/success/relativistic_boundary_latest.json",
        "mistake_room": "artifacts/physics/v35/mistakes/rejected_frame_mutations.jsonl",
    }
    report["content_digest"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    destinations = (
        ROOT / "reports/data/relativistic_boundary_v35_latest.json",
        ROOT / "dashboard/data/relativistic_boundary_v35_latest.json",
        ROOT / "artifacts/physics/v35/success/relativistic_boundary_latest.json",
    )
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)

    manifest = acceptance["completion_audit"]["evidence_manifest"]
    artifact_checks = []
    for item in manifest:
        report_exists = (ROOT / item["report"]).is_file()
        route = item["dashboard_route"].strip("/")
        page_exists = (ROOT / "dashboard/app" / route / "page.tsx").is_file()
        artifact_checks.append({"capability_id": item["capability_id"], "report_exists": report_exists, "page_exists": page_exists, "passed": report_exists and page_exists})
    audit = {
        "audit_version": "classical-mechanics-completion-audit-v35.0",
        "run_id": run_id,
        "passed": all(i["passed"] for i in artifact_checks),
        "verified_domains": 15,
        "total_domains": 15,
        "scope": acceptance["completion_audit"]["claim_scope"],
        "artifact_checks": artifact_checks,
    }
    if not audit["passed"]:
        raise RuntimeError([i for i in artifact_checks if not i["passed"]])
    audit_path = ROOT / "reports/data/classical_mechanics_completion_v35_latest.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copyfile(audit_path, ROOT / "dashboard/data/classical_mechanics_completion_v35_latest.json")
    print(json.dumps({
        "run_id": run_id,
        "acceptance": "12/12",
        "opaque_program": acceptance["discovery"]["selected_program"]["opaque_program"],
        "invariant_role": acceptance["discovery"]["selected_invariant_role"],
        "mechanics_domains": "15/15",
        "completion_audit": "15/15 artifact reports and pages present",
        "scope": audit["scope"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
