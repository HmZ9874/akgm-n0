"""Construct and publish V23 autonomous executable physical worlds."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.autonomous_physics_worlds_v23 import run_v23_acceptance  # noqa: E402


def _digest(report: dict) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-physics-worlds-v23-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v23_acceptance()
    if not acceptance["passed"]:
        failed = [item["obligation_id"] for item in acceptance["proof_obligations"] if not item["passed"]]
        raise RuntimeError(f"V23 acceptance failed: {failed}")
    report = {
        "report_version": "autonomous-physics-worlds-v23.0",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "autonomous_executable_conservative_world_construction_passed",
        "acceptance": acceptance,
        "capability_change": {
            "before": "V22 inferred physical transition and conservation programs from supplied anonymous experiments",
            "after": "V23 generates diverse multi-entity worlds, executes installed laws, applies internal interactions, scores world quality, and independently replays every trace",
            "per_world_human_definition_supplied": False,
        },
        "claim": {
            "achieved": "verified autonomous construction of finite multi-entity discrete worlds with balanced internal exchanges and conserved additive totals",
            "not_claimed": "real-world fidelity, mass-force mechanics, energy conservation, fields, or continuous spacetime",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "autonomous_physics_worlds_report.json"
    mistake_path = ROOT / "artifacts/physics/v23/mistakes/rejected_world_mutations.jsonl"
    mistake_path.parent.mkdir(parents=True, exist_ok=True)
    mistake_path.write_text(
        "".join(json.dumps({"schema_version": "physics-world-mistake-v23.0", **item}, ensure_ascii=False, sort_keys=True) + "\n" for item in acceptance["mutation_audits"]),
        encoding="utf-8",
    )
    report["storage"] = {
        "success_room": "artifacts/physics/v23/success/autonomous_worlds_latest.json",
        "mistake_room": "artifacts/physics/v23/mistakes/rejected_world_mutations.jsonl",
        "accepted_worlds": acceptance["construction"]["worlds_accepted"],
        "rejected_mutations": len(acceptance["mutation_audits"]),
    }
    report["content_digest"] = _digest(report)
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/autonomous_physics_worlds_v23_latest.json",
        ROOT / "dashboard/data/autonomous_physics_worlds_v23_latest.json",
        ROOT / "artifacts/physics/v23/success/autonomous_worlds_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    construction = acceptance["construction"]
    summary = {
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "worlds": f"{construction['worlds_accepted']}/{construction['worlds_generated']}",
        "graph_families": construction["graph_family_count"],
        "entity_count_range": construction["entity_count_range"],
        "simulated_entity_steps": construction["total_simulated_steps"],
        "internal_interactions": construction["total_interactions"],
        "sealed_worlds": acceptance["sealed_worlds"]["accepted_count"],
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
    }
    sys.stdout.buffer.write((json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
