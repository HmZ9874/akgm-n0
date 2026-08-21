from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import (  # noqa: E402
    AdaptiveMistakeLibrary,
    FormulaSuccessRoom,
    UniversalFormulaRoom,
    program_digest,
)
from akgm_n0.learner import (  # noqa: E402
    CounterexampleGuidedReflectiveSearch,
    NumericTableObservation,
    ReflectiveProgram,
    SemanticExtendedExecutor,
    SemanticInventionSearch,
    SemanticOpcodeInducer,
)


DEVELOPMENT_ROWS = (
    (1, 2, 3, 4, 1, 1, 1, 1, 0),
    (4, 5, 6, 7, 2, 1, 3, 1, 0),
    (1, 2, 3, 4, 1, 1, 1, 1, 1),
    (1, 2, 3, 4, 1, 1, 1, 1, 3),
    (1, 2, 3, 4, 1, 1, 1, 1, 6),
    (2, 3, 5, 7, 2, 1, 1, 1, 4),
    (3, 1, 4, 2, 1, 2, 3, 1, 4),
    (5, 2, 1, 6, 3, 1, 2, 4, 3),
)
SEALED_ROWS = (
    (6, 9, 2, 5, 4, 2, 3, 1, 3),
    (2, 5, 8, 3, 3, 4, 2, 5, 4),
    (8, 1, 7, 4, 5, 2, 1, 3, 2),
    (9, 3, 6, 2, 2, 5, 4, 1, 5),
    (4, 8, 1, 7, 6, 1, 3, 2, 3),
)


def hidden_relation(a, b, c, d, p, q, r, s, n):
    for _ in range(n):
        a, b, c, d = b, c, d, p * d + q * c + r * b + s * a
    return a


def evaluate(program, rows, executor):
    result = []
    for row in rows:
        predicted = executor.execute(program, row).output_value
        observed = hidden_relation(*row)
        result.append(
            {"inputs": list(row), "predicted": predicted, "observed": observed,
             "passed": predicted == observed}
        )
    return result


def main() -> int:
    strict_room = UniversalFormulaRoom(
        ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl"
    )
    sources = tuple(
        (record.room_record_id, ReflectiveProgram.from_dict(dict(record.program)))
        for record in strict_room.records
        if record.program.get("substrate") == "anonymous_unified_word_machine_v0.1"
    )
    semantic = SemanticOpcodeInducer().induce(sources)
    executor = SemanticExtendedExecutor(maximum_steps=500_000)
    search = SemanticInventionSearch(semantic, executor=executor)
    discovery = CounterexampleGuidedReflectiveSearch(
        search=search, maximum_rounds=12
    ).synthesize(
        opaque_task_id="opaque-nine-column-semantic-invention",
        input_rows=DEVELOPMENT_ROWS,
        output_values=tuple(hidden_relation(*row) for row in DEVELOPMENT_ROWS),
        initial_case_indices=(0, 1),
    )
    winner = discovery.final_candidate
    sealed = evaluate(winner.program, SEALED_ROWS, executor)
    if not discovery.converged or not all(item["passed"] for item in sealed):
        raise RuntimeError("invented-semantic program failed hidden evidence")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = "RUN-semantic-invention-" + stamp
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)

    semantic_payload = {
        "schema_version": "invented-semantic-library-v0.1",
        "formula_names_used": False,
        "semantics": [semantic.to_dict()],
    }
    encoded = json.dumps(
        semantic_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    semantic_payload["library_digest"] = hashlib.sha256(encoded.encode()).hexdigest()
    semantic_library = ROOT / "artifacts/semantics/invented_semantics.json"
    semantic_library.parent.mkdir(parents=True, exist_ok=True)
    semantic_library.write_text(
        json.dumps(semantic_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    observation = NumericTableObservation.create(
        opaque_session_id="semantic-invention-feedback",
        input_rows=DEVELOPMENT_ROWS,
        output_values=tuple(hidden_relation(*row) for row in DEVELOPMENT_ROWS),
        validity_mask=(True,) * len(DEVELOPMENT_ROWS),
        action_receipt="anonymous_nine_column_feedback_v0.1",
    )
    mistake_room = AdaptiveMistakeLibrary(
        ROOT / "artifacts/mistakes/adaptive_mistakes.jsonl"
    )
    mistake_ids = []
    for candidate in search.search(observation).top_candidates:
        if candidate.candidate_id == winner.candidate_id:
            continue
        failures = [
            item
            for item in evaluate(candidate.program, DEVELOPMENT_ROWS + SEALED_ROWS, executor)
            if not item["passed"]
        ]
        if not failures:
            continue
        record = mistake_room.record(
            candidate.program,
            failed_scope="invented_semantic_cross_parameter",
            condition_key="anonymous_nine_column_relation",
            counterexamples=failures[:5],
            source_candidate_id=candidate.candidate_id,
        )
        mistake_ids.append(record.mistake_id)
        if len(mistake_ids) == 10:
            break

    success_room = FormulaSuccessRoom(
        ROOT / "artifacts/formula_rooms/success/successful_formulas.jsonl"
    )
    operation_id = "SEMANTIC-GROWN-" + program_digest(winner.program)[:16]
    success = success_room.record(
        winner.program,
        operation_id=operation_id,
        parent_operation_ids=(semantic.semantic_id,),
        validation_scope="opaque_invented_semantic_unseen_parameters",
        knowledge_status="bounded",
        evidence={
            "run_id": run_id,
            "candidate_id": winner.candidate_id,
            "cegis_rounds": len(discovery.rounds),
            "sealed_passed": sum(item["passed"] for item in sealed),
            "sealed_total": len(sealed),
            "awaiting_universal_proof": True,
        },
    )
    failed_round = next(
        item for item in discovery.rounds if item.added_counterexample_index is not None
    )
    failed_index = failed_round.added_counterexample_index
    assert failed_index is not None
    failed_row = DEVELOPMENT_ROWS[failed_index]
    expanded_instruction_count = (
        winner.program.instruction_count
        + winner.program.words[::2].count(semantic.opcode)
        * semantic.compression_saving_per_use
    )
    report = {
        "report_version": "semantic-invention-discovery-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verdict": "bounded_invented_semantic_program_awaiting_universal_proof",
        "invented_semantic": semantic.to_dict(),
        "semantic_library_path": str(semantic_library.relative_to(ROOT)),
        "candidate": winner.to_dict(),
        "program_digest": program_digest(winner.program),
        "compressed_instruction_count": winner.program.instruction_count,
        "equivalent_expanded_instruction_count": expanded_instruction_count,
        "crossed_old_instruction_limit": (
            winner.program.instruction_count <= 64 < expanded_instruction_count
        ),
        "cegis_rounds": [item.to_dict() for item in discovery.rounds],
        "first_counterexample": {
            "inputs": list(failed_row),
            "predicted": executor.execute(failed_round.candidate.program, failed_row).output_value,
            "observed": hidden_relation(*failed_row),
        },
        "sealed_results": sealed,
        "success_room_record": success.to_dict(),
        "mistake_ids": mistake_ids,
        "learner_received": {
            "formula_name": False,
            "recurrence_name": False,
            "anonymous_numeric_columns": 9,
            "multiply_divide_power_opcodes": False,
            "preassigned_opcode_16_meaning": False,
            "proven_microcode_only_for_semantic_induction": True,
        },
        "posthoc_interpretation": {
            "formula": "F(a,b,c,d,p,q,r,s,n): F0=a, F1=b, F2=c, F3=d, F(t+4)=p*F(t+3)+q*F(t+2)+r*F(t+1)+s*F(t)",
            "bottom_computation": "four uses of an induced repeated-accumulation opcode and a four-cell state shift",
        },
        "limitations": [
            "The semantic detector, descriptor encoding and extended interpreter are host-implemented.",
            "Opcode 16 was allocated and parameterized from repeated proven microcode, but the host still enforces its execution contract.",
            "Stable input-column groups remain part of the search scaffold.",
        ],
    }
    artifact = run_dir / "semantic_invention_discovery_report.json"
    artifact.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for destination in (
        ROOT / "reports/data/semantic_invention_discovery_latest.json",
        ROOT / "dashboard/data/semantic_invention_discovery_latest.json",
    ):
        shutil.copyfile(artifact, destination)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "semantic_id": semantic.semantic_id,
                "opcode": semantic.opcode,
                "supporting_occurrences": semantic.supporting_occurrence_count,
                "cegis_rounds": len(discovery.rounds),
                "sealed": f"{sum(item['passed'] for item in sealed)}/{len(sealed)}",
                "mistakes_recorded": len(mistake_ids),
                "compressed_instructions": winner.program.instruction_count,
                "expanded_instructions": expanded_instruction_count,
                "program_digest": program_digest(winner.program),
                "success_room_record_id": success.room_record_id,
                "artifact_path": str(artifact.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
