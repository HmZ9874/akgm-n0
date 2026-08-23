"""Resume the persistent local V55 mathematical-semantic research campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.continuous_math_research_v55 import verify_v55_transition  # noqa: E402
from akgm_n0.evaluator.continuous_math_room_v55 import ContinuousMathSuccessRoomV55  # noqa: E402
from akgm_n0.learner.continuous_math_research_v55 import (  # noqa: E402
    ContinuousMathResearchV55,
    ContinuousResearchStateStoreV55,
)


DEFAULT_STATE = ROOT / "artifacts/research/v55/state/continuous_math_state.json"
SUCCESS_ROOM = ROOT / "artifacts/research/v55/success/discoveries.jsonl"
MISTAKE_ROOM = ROOT / "artifacts/research/v55/mistakes/rejections.jsonl"


def _digest(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _append_mistakes(records: list[dict[str, Any]]) -> int:
    existing_ids: set[str] = set()
    if MISTAKE_ROOM.exists():
        with MISTAKE_ROOM.open("r", encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    existing_ids.add(json.loads(line)["mistake_id"])
    additions = []
    for record in records:
        mistake_id = "M55-" + _digest(record)[:16]
        if mistake_id not in existing_ids:
            additions.append({"mistake_id": mistake_id, **record})
            existing_ids.add(mistake_id)
    if additions:
        MISTAKE_ROOM.parent.mkdir(parents=True, exist_ok=True)
        with MISTAKE_ROOM.open("a", encoding="utf-8", newline="\n") as stream:
            for item in additions:
                stream.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    return len(additions)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Continue the local persistent V55 mathematical-semantic research campaign."
    )
    parser.add_argument("--target-new", type=int, default=5)
    parser.add_argument("--max-rounds", type=int, default=12)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    state_path = args.state if args.state.is_absolute() else ROOT / args.state
    store = ContinuousResearchStateStoreV55(state_path)
    before = store.load()
    result = ContinuousMathResearchV55().run(
        before,
        target_new=args.target_new,
        maximum_rounds=args.max_rounds,
    )
    acceptance = verify_v55_transition(result)
    if not acceptance["passed"]:
        failed = [item for item in acceptance["proof_obligations"] if not item["passed"]]
        raise RuntimeError(f"V55 transition rejected: {failed}")

    store.save(result.after)
    success_room = ContinuousMathSuccessRoomV55(SUCCESS_ROOM)
    added_events = success_room.sync(result.after.operators)
    mistake_records = [
        {"round_index": round_.round_index, **item}
        for round_ in result.rounds
        for item in round_.rejected
    ]
    mistake_records.append({
        "reason": "mutated_certificate",
        **acceptance["mutation_audit"],
    })
    mistakes_added = _append_mistakes(mistake_records)

    now = datetime.now(timezone.utc)
    run_id = "RUN-continuous-math-v55-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    report = {
        "report_version": "continuous-math-research-v55.0",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "persistent_verified_frontier_advanced"
        if result.discoveries
        else "persistent_frontier_advanced_without_new_verified_semantic",
        "transition": result.to_dict(),
        "acceptance": acceptance,
        "campaign": {
            "state_path": state_path.relative_to(ROOT).as_posix()
            if state_path.is_relative_to(ROOT)
            else str(state_path),
            "resumed_from_run_count": before.run_count,
            "completed_run_count": result.after.run_count,
            "operator_count_before": len(before.operators),
            "operator_count_after": len(result.after.operators),
            "next_round_index": result.after.next_round_index,
            "curriculum_level": result.after.curriculum_level,
            "state_digest": result.after.state_digest,
        },
        "rooms": {
            "success": SUCCESS_ROOM.relative_to(ROOT).as_posix(),
            "success_total": len(success_room.records),
            "success_events_added": len(added_events),
            "mistakes": MISTAKE_ROOM.relative_to(ROOT).as_posix(),
            "mistakes_added": mistakes_added,
        },
        "token_accounting": {
            "cloud_model_calls": 0,
            "api_tokens": 0,
        },
        "dashboard_modified": False,
        "claim_boundary": {
            "discovered": "new exact executable natural-counter semantics not previously present in this V55 campaign",
            "not_claimed": "new-to-human mathematical formulas",
        },
    }
    report["content_digest"] = _digest(report)
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    artifact = run_dir / "continuous_math_research_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    latest = ROOT / "reports/data/continuous_math_research_v55_latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact, latest)

    summary = json.dumps({
        "run_id": run_id,
        "resumed_from_run": before.run_count,
        "completed_run": result.after.run_count,
        "new_verified_semantics": len(result.discoveries),
        "total_verified_semantics": len(result.after.operators),
        "stop_reason": result.stop_reason,
        "next_round_index": result.after.next_round_index,
        "curriculum_level": result.after.curriculum_level,
        "discoveries": [
            {
                "operator_id": item.definition.operator_id,
                "exact_signature": item.exact_semantic.exact_signature,
                "posthoc_formula": item.posthoc_formula,
            }
            for item in result.discoveries
        ],
        "acceptance": f"{sum(item['passed'] for item in acceptance['proof_obligations'])}/{len(acceptance['proof_obligations'])}",
        "api_tokens": 0,
        "state_path": str(state_path),
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
    }, ensure_ascii=False, indent=2)
    sys.stdout.buffer.write((summary + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
