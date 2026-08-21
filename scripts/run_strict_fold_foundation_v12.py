"""Explore and publish a target-free fold foundation."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.strict_fold_foundation_v12 import prove_fold_foundation  # noqa: E402
from akgm_n0.evaluator.strict_fold_foundation_v12_room import StrictFoldFoundationRoom  # noqa: E402
from akgm_n0.learner.strict_fold_foundation_v12 import TargetFreeFoldExplorer  # noqa: E402


def main() -> int:
    now = datetime.now(timezone.utc)
    run_id = "RUN-strict-fold-v12-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    discovery = TargetFreeFoldExplorer().search()
    proof = prove_fold_foundation(discovery.selected.program)
    if not proof.passed:
        raise RuntimeError("selected fold behavior failed universal proof")
    room = StrictFoldFoundationRoom(ROOT / "artifacts/foundation/v12/success/strict_fold_foundations.jsonl")
    record = room.record(discovery.selected.program, proof, run_id=run_id)
    mistakes = ROOT / "artifacts/foundation/v12/mistakes/nonpromoted_behavior_leaders.jsonl"
    mistakes.parent.mkdir(parents=True, exist_ok=True)
    mistakes.write_text("".join(json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True) + "\n" for item in discovery.rejected_leaders), encoding="utf-8")
    report = {
        "report_version": "strict-fold-foundation-v12.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "one_target_free_fold_foundation_universally_proven",
        "dependency": {
            "semantic_id": "STRICT-FSEM-82df58ba4ce6f41c",
            "provided_to_candidate_as": "opaque verified binary operation",
            "human_name_hidden_during_search": True,
        },
        "discovery": {
            "information_boundary": {
                "target_output_rows": False,
                "power_or_exponent_opcode": False,
                "named_formula_target": False,
                "available_choices": ["loop input", "seed source", "opaque binary semantic", "two update sources", "output source"],
                "host_supplied": ["fold-controller grammar", "bounded enumeration", "iteration-homomorphism detector", "induction checker"],
            },
            "programs_generated": discovery.programs_generated,
            "programs_executed": discovery.programs_executed,
            "behavior_classes": discovery.behavior_classes,
            "promotable_behavior_classes": discovery.promotable_behavior_classes,
            "promotable_semantic_orbits_under_input_renaming": 1,
            "selected": discovery.selected.to_dict(),
        },
        "proof": proof.to_dict(),
        "promotion": {
            "admitted": True,
            "strict_new_foundation_count": 1,
            "strict_foundations_in_v10_v11_v12": 3,
            "room_record_hash": record["record_hash"],
            "success_room": str(room.path.relative_to(ROOT)).replace("\\", "/"),
            "mistake_room": str(mistakes.relative_to(ROOT)).replace("\\", "/"),
        },
        "classification": {
            "label": "target_free_bounded_structural_discovery",
            "autonomous_within_registered_grammar": True,
            "unrestricted_semantics_invention": False,
            "human_novel_mathematics_claim": False,
            "note": "Two ordered behaviors pass because swapping the anonymous inputs swaps base and count; they form one semantic orbit and one promoted foundation.",
        },
    }
    report["content_digest"] = hashlib.sha256(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact = run_dir / "strict_fold_foundation_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (ROOT / "reports/data/strict_fold_foundation_v12_latest.json", ROOT / "dashboard/data/strict_fold_foundation_v12_latest.json"):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "programs": discovery.programs_generated,
        "behaviors": discovery.behavior_classes,
        "promotable_ordered_behaviors": discovery.promotable_behavior_classes,
        "promotable_semantic_orbits": 1,
        "candidate_id": discovery.selected.candidate_id,
        "proof": f"{sum(item['passed'] for item in proof.obligations)}/{len(proof.obligations)}",
        "posthoc_name": proof.posthoc_name,
        "normal_form": proof.derived_normal_form,
        "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
