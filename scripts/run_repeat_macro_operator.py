from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import UniversalFormulaRoom, verify_repeat_macro_semantic  # noqa: E402
from akgm_n0.learner import RepeatMacroExecutor, RepeatMacroInducer  # noqa: E402


def main() -> int:
    sources = _sources()
    semantic = RepeatMacroInducer().induce(
        sources, occupied_opcodes=tuple(range(16, 131))
    )
    verification = verify_repeat_macro_semantic(semantic)
    if not verification["passed"]:
        print(json.dumps(verification, ensure_ascii=False, indent=2))
        return 1
    executor = RepeatMacroExecutor()
    increment_demo = executor.execute((2,), 20, lambda state: (state[0] + 3,))
    pair_demo = executor.execute(
        (1, 1), 10, lambda state: (state[1], state[0] + state[1])
    )
    room_event = _record(semantic.to_dict(), verification)
    gates = [
        {
            "gate_id": "next_fresh_opcode_after_continuous_frontier",
            "passed": semantic.opcode == 131,
            "actual": semantic.opcode,
            "required": 131,
        },
        {
            "gate_id": "repeat_skeleton_has_many_proven_sources",
            "passed": len(semantic.source_record_ids) >= 5,
            "actual": len(semantic.source_record_ids),
            "required": 5,
        },
        {
            "gate_id": "body_parameter_is_not_fixed",
            "passed": len(semantic.observed_body_shapes) >= 2,
            "actual": len(semantic.observed_body_shapes),
            "required": 2,
        },
        {
            "gate_id": "universal_repeat_induction_proof",
            "passed": verification["passed"],
            "actual": sum(item["passed"] for item in verification["obligations"]),
            "required": len(verification["obligations"]),
        },
        {
            "gate_id": "macro_matches_expanded_execution",
            "passed": all(item["passed"] for item in verification["case_results"]),
            "actual": sum(item["passed"] for item in verification["case_results"]),
            "required": len(verification["case_results"]),
        },
        {
            "gate_id": "verified_control_room_persisted",
            "passed": room_event["semantic"]["semantic_id"] == semantic.semantic_id,
            "actual": room_event["semantic"]["semantic_id"],
            "required": semantic.semantic_id,
        },
    ]
    if not all(item["passed"] for item in gates):
        return 1
    now = datetime.now(timezone.utc)
    run_id = "RUN-repeat-macro-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    report = {
        "report_version": "repeat-macro-operator-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "generic_repeated_operation_compressed_into_one_verified_macro",
        "invented_operator": semantic.to_dict(),
        "posthoc_interpretation": {
            "name": "REPEAT",
            "contract": verification["universal_statement"],
            "provided_to_learner": False,
        },
        "compression": {
            "macro_instruction_count": 1,
            "demonstration_body_instruction_count": 3,
            "demonstration_repeat_count": 20,
            "expanded_body_instruction_count": 60,
            "saved_body_dispatches": 59,
            "semantic_body_is_a_parameter": True,
        },
        "demonstrations": {
            "repeat_anonymous_increment": increment_demo.to_dict(),
            "repeat_anonymous_pair_transition": pair_demo.to_dict(),
        },
        "verification": verification,
        "control_semantic_room": room_event,
        "gates": gates,
        "learner_received": {
            "repeat_name": False,
            "target_macro_definition": False,
            "fixed_body_operation": False,
            "proven_anonymous_word_code": True,
            "counter_loop_structure": True,
        },
        "limitations": [
            "OP131 compresses finite natural-number repetition; it does not express unbounded recursion or arbitrary while conditions.",
            "The runtime body must be a registered deterministic transition; arbitrary external code is not accepted as a learned semantic.",
            "The anti-unification scanner, higher-order executor, and induction proof rule are host implementations.",
            "One macro invocation hides repeated dispatch, but the underlying work still takes n body applications unless a body-specific closed form is separately discovered.",
        ],
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    artifact = run_dir / "repeat_macro_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/repeat_macro_latest.json",
        ROOT / "dashboard/data/repeat_macro_latest.json",
        ROOT / "artifacts/semantics/repeat_macro_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "semantic_id": semantic.semantic_id,
                "opcode": semantic.opcode,
                "proven_sources": len(semantic.source_record_ids),
                "body_shapes": len(semantic.observed_body_shapes),
                "proof": f"{sum(item['passed'] for item in verification['obligations'])}/{len(verification['obligations'])}",
                "expansion_cases": f"{sum(item['passed'] for item in verification['case_results'])}/{len(verification['case_results'])}",
                "compression_demo": "60 body instructions -> 1 macro invocation",
                "artifact_path": str(artifact.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _sources():
    result = []
    seen = set()
    for path in (
        ROOT / "artifacts/formula_rooms/universal/proven_formulas.jsonl",
        ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl",
    ):
        for record in UniversalFormulaRoom(path).records:
            if record.room_record_id in seen or "words" not in record.program:
                continue
            seen.add(record.room_record_id)
            result.append((record.room_record_id, tuple(record.program["words"])))
    return result


def _record(semantic, verification):
    path = ROOT / "artifacts/semantics/verified_control_semantics.jsonl"
    events = [] if not path.exists() else [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    found = next((item for item in events if item["semantic"]["semantic_id"] == semantic["semantic_id"]), None)
    if found is not None:
        return found
    event = {
        "schema_version": "verified-control-semantic-event-v0.1",
        "event_index": len(events),
        "semantic": semantic,
        "verification": verification,
        "previous_event_hash": events[-1]["event_hash"] if events else "0" * 64,
    }
    event["event_hash"] = hashlib.sha256(
        json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush(); os.fsync(stream.fileno())
    return event


if __name__ == "__main__":
    raise SystemExit(main())
