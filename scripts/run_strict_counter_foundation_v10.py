"""Run target-free counter exploration and publish its auditable report."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.strict_counter_foundation_v10 import prove_counter_foundation  # noqa: E402
from akgm_n0.evaluator.strict_counter_foundation_v10_room import StrictCounterFoundationRoom  # noqa: E402
from akgm_n0.learner.strict_counter_foundation_v10 import TargetFreeCounterExplorer  # noqa: E402


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-strict-counter-v10-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    discovery = TargetFreeCounterExplorer().search()
    proof = prove_counter_foundation(discovery.selected.program)
    if not proof.passed:
        raise RuntimeError("selected counter behavior failed universal proof")

    success_room = StrictCounterFoundationRoom(
        ROOT / "artifacts/foundation/v10/success/strict_counter_foundations.jsonl"
    )
    room_record = success_room.record(discovery.selected.program, proof, run_id=run_id)
    rejection_path = ROOT / "artifacts/foundation/v10/mistakes/nonpromoted_behavior_leaders.jsonl"
    rejection_path.parent.mkdir(parents=True, exist_ok=True)
    rejection_path.write_text(
        "".join(
            json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True) + "\n"
            for item in discovery.rejected_leaders
        ),
        encoding="utf-8",
    )

    report = {
        "report_version": "strict-counter-foundation-v10.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "one_target_free_counter_foundation_universally_proven",
        "discovery": {
            "information_boundary": {
                "numeric_target_rows": False,
                "named_formula_targets": False,
                "multiplication_or_division_opcode": False,
                "available_primitives": [
                    "natural input counters",
                    "unit increment",
                    "unit decrement",
                    "empty test",
                    "bounded nested loop",
                    "four registers",
                ],
                "host_supplied": [
                    "the counter/register substrate",
                    "the bounded two-level enumeration grammar",
                    "the generic algebraic-law detector",
                    "the invariant proof checker",
                ],
            },
            "programs_generated": discovery.programs_generated,
            "programs_executed": discovery.programs_executed,
            "behavior_classes": discovery.behavior_classes,
            "promotable_behavior_classes": discovery.promotable_behavior_classes,
            "selected": discovery.selected.to_dict(),
            "selection_rule": "maximize generic law count, then minimize primitive nodes, execution steps, and candidate id",
        },
        "proof": proof.to_dict(),
        "promotion": {
            "admitted": True,
            "strict_new_foundation_count": 1,
            "room_record_hash": room_record["record_hash"],
            "success_room": str(success_room.path.relative_to(ROOT)).replace("\\", "/"),
            "mistake_room": str(rejection_path.relative_to(ROOT)).replace("\\", "/"),
        },
        "classification": {
            "label": "target_free_bounded_structural_discovery",
            "autonomous_within_registered_grammar": True,
            "unrestricted_computational_semantics_invention": False,
            "human_novel_mathematics_claim": False,
            "explanation": "The learner was not given multiplication examples or a multiplication opcode. It selected one behavior from a host-bounded generic nested-counter grammar; the mathematical name was attached only after a universal loop invariant succeeded.",
        },
    }
    canonical = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    report["content_digest"] = hashlib.sha256(canonical.encode()).hexdigest()

    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "strict_counter_foundation_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/strict_counter_foundation_v10_latest.json",
        ROOT / "dashboard/data/strict_counter_foundation_v10_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "programs": discovery.programs_generated,
                "behaviors": discovery.behavior_classes,
                "promotable": discovery.promotable_behavior_classes,
                "candidate_id": discovery.selected.candidate_id,
                "proof": f"{sum(item['passed'] for item in proof.obligations)}/{len(proof.obligations)}",
                "posthoc_name": proof.posthoc_name,
                "classification": report["classification"]["label"],
                "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
            },
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
