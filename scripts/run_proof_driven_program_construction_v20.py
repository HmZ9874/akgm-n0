"""Run V20 program construction and publish proof evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.proof_driven_program_construction_v20 import run_v20_acceptance  # noqa: E402


def _digest(report: dict) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-proof-construction-v20-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v20_acceptance()
    if not acceptance["passed"]:
        failed = [item["obligation_id"] for item in acceptance["proof_obligations"] if not item["passed"]]
        raise RuntimeError(f"V20 acceptance failed: {failed}")
    report = {
        "report_version": "proof-driven-program-construction-v20.0",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "constructed_equation_and_rational_pair_programs_universally_proved",
        "acceptance": acceptance,
        "capability_change": {
            "before": "V19 discovered one anonymous operation, its laws, and a factor concept",
            "after": "V20 composes proven semantics into executable partition, equation, equivalence-class, and two rational-pair programs",
            "named_solution_program_supplied": False,
        },
        "claim": {
            "achieved": "verified program construction from anonymous natural-counter semantics through nonnegative rational operations",
            "not_claimed": "general symbolic algebra, signed rational field closure, or unrestricted function discovery",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "proof_driven_program_construction_report.json"
    mistakes_path = ROOT / "artifacts/foundation/v20/mistakes/rejected_program_mutations.jsonl"
    mistakes_path.parent.mkdir(parents=True, exist_ok=True)
    mistakes_path.write_text(
        "".join(json.dumps({"schema_version": "constructed-program-mistake-v20.0", **item}, ensure_ascii=False, sort_keys=True) + "\n" for item in acceptance["mutation_audits"]),
        encoding="utf-8",
    )
    report["storage"] = {
        "success_room": "artifacts/foundation/v20/success/proof_driven_programs_latest.json",
        "mistake_room": "artifacts/foundation/v20/mistakes/rejected_program_mutations.jsonl",
        "promoted_programs": len(acceptance["construction"]["promoted_pair_operations"]) + 2,
        "rejected_mutations": len(acceptance["mutation_audits"]),
    }
    report["content_digest"] = _digest(report)
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/proof_driven_program_construction_v20_latest.json",
        ROOT / "dashboard/data/proof_driven_program_construction_v20_latest.json",
        ROOT / "artifacts/foundation/v20/success/proof_driven_programs_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    summary = {
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "partition_programs_searched": acceptance["construction"]["partition_programs_generated"],
        "pair_programs_constructed": acceptance["construction"]["pair_programs_generated"],
        "pair_behavior_classes": acceptance["construction"]["pair_behavior_classes"],
        "promoted_pair_programs": len(acceptance["construction"]["promoted_pair_operations"]),
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
    }
    sys.stdout.buffer.write((json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
