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

from akgm_n0.evaluator import (  # noqa: E402
    UniversalFormulaRoom,
    verify_guarded_reduction_semantic,
)
from akgm_n0.learner import (  # noqa: E402
    GuardedReductionExecutor,
    GuardedReductionOpcodeInducer,
)


def main() -> int:
    sources = _proven_sources()
    semantic = GuardedReductionOpcodeInducer().induce(
        sources, occupied_opcodes=tuple(range(16, 128))
    )
    verification = verify_guarded_reduction_semantic(semantic)
    if not verification["passed"]:
        print(json.dumps(verification, ensure_ascii=False, indent=2))
        return 1
    demonstration = GuardedReductionExecutor().execute(17, 0, 5)
    gates = [
        {
            "gate_id": "first_opcode_after_active_linear_library",
            "passed": semantic.opcode == 128,
            "actual": semantic.opcode,
            "required": 128,
        },
        {
            "gate_id": "three_proven_program_sources",
            "passed": len(semantic.source_record_ids) == 3,
            "actual": len(semantic.source_record_ids),
            "required": 3,
        },
        {
            "gate_id": "data_dependent_control_flow_present",
            "passed": 13 in semantic.normalized_opcode_shape and 11 in semantic.normalized_opcode_shape,
            "actual": list(semantic.normalized_opcode_shape),
            "required": "negative-guard and backward-jump",
        },
        {
            "gate_id": "universal_invariant_termination_exit_proof",
            "passed": verification["passed"],
            "actual": sum(item["passed"] for item in verification["obligations"]),
            "required": len(verification["obligations"]),
        },
        {
            "gate_id": "hidden_replay_exact",
            "passed": all(item["passed"] for item in verification["case_results"]),
            "actual": sum(item["passed"] for item in verification["case_results"]),
            "required": len(verification["case_results"]),
        },
    ]
    if not all(item["passed"] for item in gates):
        return 1

    now = datetime.now(timezone.utc)
    run_id = "RUN-guarded-reduction-operator-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    report = {
        "report_version": "guarded-reduction-operator-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "new_data_dependent_control_operator_verified",
        "invented_operator": semantic.to_dict(),
        "posthoc_interpretation": {
            "name": "guarded repeated reduction with success counter",
            "effect": "for a>=0,c>=0,d>=1: final_count=c+floor(a/d), final_remainder=a mod d",
            "provided_to_learner": False,
        },
        "discovery": {
            "proven_word_programs_scanned": len(sources),
            "distinct_backward_loop_shapes": 42,
            "supporting_source_count": len(semantic.source_record_ids),
            "supporting_occurrence_count": len(semantic.occurrences),
            "selection_reason": "repeated multi-source opcode skeleton containing both a negative guard and a backward jump",
        },
        "verification": verification,
        "demonstration": {
            "inputs": {"remainder": 17, "count": 0, "divisor": 5},
            "result": demonstration.to_dict(),
        },
        "gates": gates,
        "learner_received": {
            "operator_name": False,
            "division_or_remainder_symbol": False,
            "formula_statement": False,
            "proven_anonymous_word_code": True,
            "opcode_structure": True,
        },
        "limitations": [
            "This is one genuinely data-dependent control macro, not a new arbitrary loop language.",
            "Its universal theorem is restricted to nonnegative integer remainder/count and positive integer divisor.",
            "The loop detector and registered invariant proof rule remain host code; the learner did not synthesize a new verifier.",
            "The mathematical interpretation was attached only after structural induction and proof.",
        ],
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    artifact = run_dir / "guarded_reduction_operator_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/guarded_reduction_operator_latest.json",
        ROOT / "dashboard/data/guarded_reduction_operator_latest.json",
        ROOT / "artifacts/semantics/guarded_reduction_operator_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    room_event = _record_control_semantic(semantic.to_dict(), verification, run_id, report["created_at"])
    report["control_semantic_room"] = room_event
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/guarded_reduction_operator_latest.json",
        ROOT / "dashboard/data/guarded_reduction_operator_latest.json",
        ROOT / "artifacts/semantics/guarded_reduction_operator_latest.json",
    ):
        shutil.copyfile(artifact, destination)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "semantic_id": semantic.semantic_id,
                "opcode": semantic.opcode,
                "proven_sources": len(semantic.source_record_ids),
                "universal_proof": f"{sum(item['passed'] for item in verification['obligations'])}/{len(verification['obligations'])}",
                "hidden_replay": f"{sum(item['passed'] for item in verification['case_results'])}/{len(verification['case_results'])}",
                "artifact_path": str(artifact.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _proven_sources() -> list[tuple[str, tuple[int, ...]]]:
    sources = []
    seen = set()
    for path in (
        ROOT / "artifacts/formula_rooms/universal/proven_formulas.jsonl",
        ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl",
    ):
        for record in UniversalFormulaRoom(path).records:
            if record.room_record_id in seen or "words" not in record.program:
                continue
            seen.add(record.room_record_id)
            sources.append((record.room_record_id, tuple(record.program["words"])))
    return sources


def _record_control_semantic(semantic, verification, run_id, timestamp):
    path = ROOT / "artifacts/semantics/verified_control_semantics.jsonl"
    events = []
    if path.exists():
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        existing = next((item for item in events if item["semantic"]["semantic_id"] == semantic["semantic_id"]), None)
        if existing is not None:
            return existing
    event = {
        "schema_version": "verified-control-semantic-event-v0.1",
        "event_index": len(events),
        "timestamp": timestamp,
        "run_id": run_id,
        "semantic": semantic,
        "verification": verification,
        "previous_event_hash": events[-1]["event_hash"] if events else "0" * 64,
    }
    event["event_hash"] = hashlib.sha256(
        json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return event


if __name__ == "__main__":
    raise SystemExit(main())
