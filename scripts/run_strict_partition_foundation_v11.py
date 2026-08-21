"""Explore and publish a strict two-output counter foundation."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.strict_partition_foundation_v11 import prove_partition_foundation  # noqa: E402
from akgm_n0.evaluator.strict_partition_foundation_v11_room import StrictPartitionFoundationRoom  # noqa: E402
from akgm_n0.learner.strict_partition_foundation_v11 import TargetFreePartitionExplorer  # noqa: E402


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-strict-partition-v11-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    discovery = TargetFreePartitionExplorer().search()
    proof = prove_partition_foundation(discovery.selected.program)
    if not proof.passed:
        raise RuntimeError("selected partition behavior failed universal proof")
    room = StrictPartitionFoundationRoom(ROOT / "artifacts/foundation/v11/success/strict_partition_foundations.jsonl")
    record = room.record(discovery.selected.program, proof, run_id=run_id)
    mistakes = ROOT / "artifacts/foundation/v11/mistakes/nonpromoted_behavior_leaders.jsonl"
    mistakes.parent.mkdir(parents=True, exist_ok=True)
    mistakes.write_text("".join(json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True) + "\n" for item in discovery.rejected_leaders), encoding="utf-8")
    report = {
        "report_version": "strict-partition-foundation-v11.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "one_target_free_two_output_foundation_universally_proven",
        "dependency": {
            "semantic_id": "STRICT-FSEM-82df58ba4ce6f41c",
            "normal_form": "x*y",
            "role": "previously proven binary semantic used only by the post-execution conservation checker",
        },
        "discovery": {
            "information_boundary": {
                "target_output_rows": False,
                "division_or_remainder_opcode": False,
                "named_formula_target": False,
                "available_primitives": ["unit increment", "unit decrement", "empty event", "conditional policy bits", "six natural counters"],
                "host_supplied": ["event-controller grammar", "bounded enumeration", "conservation-law detector", "invariant checker"],
            },
            "programs_generated": discovery.programs_generated,
            "programs_executed": discovery.programs_executed,
            "behavior_classes": discovery.behavior_classes,
            "promotable_behavior_classes": discovery.promotable_behavior_classes,
            "selected": discovery.selected.to_dict(),
        },
        "proof": proof.to_dict(),
        "promotion": {
            "admitted": True,
            "strict_new_foundation_count": 1,
            "strict_foundations_in_v10_v11": 2,
            "room_record_hash": record["record_hash"],
            "success_room": str(room.path.relative_to(ROOT)).replace("\\", "/"),
            "mistake_room": str(mistakes.relative_to(ROOT)).replace("\\", "/"),
        },
        "classification": {
            "label": "target_free_bounded_structural_discovery",
            "autonomous_within_registered_grammar": True,
            "unrestricted_semantics_invention": False,
            "human_novel_mathematics_claim": False,
        },
    }
    report["content_digest"] = hashlib.sha256(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "strict_partition_foundation_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (ROOT / "reports/data/strict_partition_foundation_v11_latest.json", ROOT / "dashboard/data/strict_partition_foundation_v11_latest.json"):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "programs": discovery.programs_generated,
        "behaviors": discovery.behavior_classes,
        "promotable": discovery.promotable_behavior_classes,
        "candidate_id": discovery.selected.candidate_id,
        "proof": f"{sum(item['passed'] for item in proof.obligations)}/{len(proof.obligations)}",
        "posthoc_name": proof.posthoc_name,
        "normal_form": list(proof.derived_normal_form),
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
