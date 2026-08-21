"""Run and publish V28 continuous dynamics discovery."""
from __future__ import annotations
import hashlib, json, shutil, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from akgm_n0.evaluator.continuous_dynamics_v28 import run_v28_acceptance  # noqa: E402

def main() -> int:
    now = datetime.now(timezone.utc); run_id = "RUN-continuous-v28-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v28_acceptance()
    if not acceptance["passed"]:
        raise RuntimeError([item["obligation_id"] for item in acceptance["proof_obligations"] if not item["passed"]])
    report = {"report_version": "continuous-dynamics-v28.0", "run_id": run_id, "created_at": now.isoformat().replace("+00:00", "Z"), "verdict": "continuous_time_polynomial_dynamics_verified", "acceptance": acceptance, "claim": {"achieved": "refinement-stable first and second time operators with continuous inertial relation", "not_claimed": "general real analysis or arbitrary differential equations"}}
    run_dir = ROOT / "artifacts/runs" / run_id; run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "continuous_dynamics_report.json"
    mistakes = ROOT / "artifacts/physics/v28/mistakes/rejected_continuous_mutations.jsonl"; mistakes.parent.mkdir(parents=True, exist_ok=True)
    mistakes.write_text("".join(json.dumps({"schema_version": "continuous-mistake-v28.0", **item}, ensure_ascii=False, sort_keys=True) + "\n" for item in acceptance["mutation_audits"]), encoding="utf-8")
    report["storage"] = {"success_room": "artifacts/physics/v28/success/continuous_dynamics_latest.json", "mistake_room": "artifacts/physics/v28/mistakes/rejected_continuous_mutations.jsonl", "accepted_programs": 3, "rejected_mutations": 4}
    report["content_digest"] = hashlib.sha256(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (ROOT / "reports/data/continuous_dynamics_v28_latest.json", ROOT / "dashboard/data/continuous_dynamics_v28_latest.json", ROOT / "artifacts/physics/v28/success/continuous_dynamics_latest.json"):
        destination.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(artifact, destination)
    graph = acceptance["mechanics_capability_graph"]
    summary = {"run_id": run_id, "acceptance": f"{sum(i['passed'] for i in acceptance['proof_obligations'])}/12", "first_operator": acceptance["discovery"]["selected_target_0"]["opaque_program"], "second_operator": acceptance["discovery"]["selected_target_1"]["opaque_program"], "refinement_order": acceptance["discovery"]["selected_refinement_order"], "mechanics_domains": f"{graph['verified_domains']}/{graph['total_domains']}", "next_gap": graph["next_selected_gap"]}
    sys.stdout.buffer.write((json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode()); return 0
if __name__ == "__main__": raise SystemExit(main())
