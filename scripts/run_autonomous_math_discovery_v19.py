"""Run V19 anonymous mathematical discovery and publish replayable evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.autonomous_math_discovery_v19 import run_v19_acceptance  # noqa: E402


def _digest(report: dict) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-autonomous-math-v19-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    acceptance = run_v19_acceptance((1, 3, 5, 7, 11, 13, 17))
    if not acceptance["passed"]:
        failed = [item["obligation_id"] for item in acceptance["proof_obligations"] if not item["passed"]]
        raise RuntimeError(f"V19 acceptance failed: {failed}")
    report = {
        "report_version": "autonomous-math-discovery-v19.0",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "anonymous_math_discovery_with_universal_proofs_passed",
        "acceptance": acceptance,
        "capability_change": {
            "before": "V18 planned executable programs for externally supplied bounded goals",
            "after": "V19 autonomously discovers an anonymous operation, generates equations, falsifies wrong equations, universally proves surviving identities, and induces a reusable factor concept",
            "next_term_prediction_used": False,
            "human_math_name_supplied_to_learner": False,
        },
        "claim": {
            "achieved": "verified autonomous conjecture-falsification-proof-concept loop over a discovered natural-number operation",
            "not_claimed": "mathematics new to humanity, unrestricted theorem proving, or modern-mathematics mastery",
        },
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "autonomous_math_discovery_report.json"
    mistakes_path = ROOT / "artifacts/foundation/v19/mistakes/rejected_conjectures.jsonl"
    mistakes_path.parent.mkdir(parents=True, exist_ok=True)
    mistakes_path.write_text(
        "".join(
            json.dumps(
                {"schema_version": "math-conjecture-mistake-v19.0", **item},
                ensure_ascii=False,
                sort_keys=True,
            ) + "\n"
            for item in acceptance["rejected_conjectures"]
        ),
        encoding="utf-8",
    )
    report["storage"] = {
        "success_room": "artifacts/foundation/v19/success/autonomous_math_latest.json",
        "mistake_room": "artifacts/foundation/v19/mistakes/rejected_conjectures.jsonl",
        "proven_formula_records": len(acceptance["theorem_proofs"]),
        "rejected_formula_records": len(acceptance["rejected_conjectures"]),
    }
    report["content_digest"] = _digest(report)
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/autonomous_math_discovery_v19_latest.json",
        ROOT / "dashboard/data/autonomous_math_discovery_v19_latest.json",
        ROOT / "artifacts/foundation/v19/success/autonomous_math_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "programs_searched": acceptance["discovery"]["programs_generated"],
        "expressions_enumerated": acceptance["discovery"]["expressions_enumerated"],
        "universally_proven_formulas": len(acceptance["theorem_proofs"]),
        "wrong_formulas_rejected": len(acceptance["rejected_conjectures"]),
        "generated_no_internal_witness": acceptance["induced_concept"]["generated_no_internal_witness"],
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
