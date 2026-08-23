"""Run V53 anonymous mathematical construction without touching the dashboard."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.anonymous_field_construction_v53 import run_v53_acceptance  # noqa: E402


def _digest(report: dict) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-anonymous-field-v53-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v53_acceptance()
    if not acceptance["passed"]:
        failed = [
            item["obligation_id"]
            for item in acceptance["proof_obligations"]
            if not item["passed"]
        ]
        raise RuntimeError(f"V53 acceptance failed: {failed}")

    report = {
        "report_version": "anonymous-field-construction-v53.0",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "anonymous_rational_field_and_general_first_degree_solver_passed",
        "acceptance": acceptance,
        "capability_change": {
            "before": "V21 constructed a signed rational commutative ring and solved x+b=c.",
            "after": "V53 constructs the nonzero multiplicative inverse, the rational field, and a unique solver for a*x+b=c when a is nonzero.",
            "target_formula_given_to_learner": False,
            "host_division_available_to_learner": False,
        },
        "claim": {
            "achieved": "verified reconstruction of known rational-field mathematics from anonymous natural-counter programs",
            "not_claimed": "real or complex completion, higher polynomial solving, calculus, or mathematics unknown to humans",
        },
    }

    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "anonymous_field_construction_report.json"
    mistake_path = ROOT / "artifacts/foundation/v53/mistakes/rejected_program_mutations.jsonl"
    mistake_path.parent.mkdir(parents=True, exist_ok=True)
    mistake_path.write_text(
        "".join(
            json.dumps(
                {"schema_version": "anonymous-program-mistake-v53.0", **item},
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
            for item in acceptance["mutation_audits"]
        ),
        encoding="utf-8",
    )
    report["storage"] = {
        "success_room": "artifacts/foundation/v53/success/anonymous_field_latest.json",
        "mistake_room": "artifacts/foundation/v53/mistakes/rejected_program_mutations.jsonl",
        "promoted_behavior_classes": 2,
        "rejected_mutations": len(acceptance["mutation_audits"]),
        "dashboard_modified": False,
    }
    report["content_digest"] = _digest(report)
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/anonymous_field_construction_v53_latest.json",
        ROOT / "artifacts/foundation/v53/success/anonymous_field_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)

    construction = acceptance["construction"]
    summary = {
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "unary_search": {
            "programs": construction["unary_programs_generated"],
            "behavior_classes": construction["unary_behavior_classes"],
        },
        "three_input_search": {
            "programs": construction["three_input_programs_generated"],
            "passing_programs": construction["three_input_passing_programs"],
            "passing_behavior_classes": construction["three_input_passing_behavior_classes"],
        },
        "mutations_rejected": sum(item["rejected"] for item in acceptance["mutation_audits"]),
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
        "dashboard_modified": False,
    }
    sys.stdout.buffer.write((json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
