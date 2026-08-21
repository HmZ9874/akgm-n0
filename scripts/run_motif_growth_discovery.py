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
    MotifExtractor,
    MotifGrowthSearch,
    NumericTableObservation,
    ReflectiveExecutor,
    ReflectiveProgram,
    reflective_program_key,
)


DEVELOPMENT_ROWS = (
    (1, 2, 1, 1, 0),
    (3, 4, 2, 1, 0),
    (1, 2, 1, 1, 1),
    (1, 2, 1, 1, 5),
    (2, 3, 2, 1, 2),
    (2, 3, 2, 1, 4),
    (3, 1, 1, 2, 3),
    (4, 2, 3, 1, 3),
    (5, 3, 2, 2, 4),
    (7, 1, 1, 3, 5),
)
SEALED_ROWS = (
    (6, 9, 4, 2, 3),
    (2, 5, 3, 4, 4),
    (8, 1, 5, 2, 2),
    (9, 7, 2, 5, 3),
    (4, 6, 6, 1, 4),
)


def hidden_relation(a: int, b: int, p: int, q: int, n: int) -> int:
    for _ in range(n):
        a, b = b, p * b + q * a
    return a


def evaluate(program, rows, executor):
    results = []
    for row in rows:
        predicted = executor.execute(program, row).output_value
        observed = hidden_relation(*row)
        results.append(
            {
                "inputs": list(row),
                "predicted": predicted,
                "observed": observed,
                "passed": predicted == observed,
            }
        )
    return results


def main() -> int:
    strict_room = UniversalFormulaRoom(
        ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl"
    )
    sources = tuple(
        (record.room_record_id, ReflectiveProgram.from_dict(dict(record.program)))
        for record in strict_room.records
        if record.program.get("substrate") == "anonymous_unified_word_machine_v0.1"
    )
    motifs = MotifExtractor().extract(sources)
    motif_kinds = {item.kind for item in motifs}
    if not MotifGrowthSearch.REQUIRED_MOTIFS.issubset(motif_kinds):
        raise RuntimeError("prior proof programs did not support required growth motifs")

    executor = ReflectiveExecutor(maximum_steps=200_000)
    search = MotifGrowthSearch(motifs, executor=executor)
    cegis = CounterexampleGuidedReflectiveSearch(search=search, maximum_rounds=12)
    discovery = cegis.synthesize(
        opaque_task_id="opaque-five-column-motif-growth",
        input_rows=DEVELOPMENT_ROWS,
        output_values=tuple(hidden_relation(*row) for row in DEVELOPMENT_ROWS),
        initial_case_indices=(0, 1),
    )
    winner = discovery.final_candidate
    sealed = evaluate(winner.program, SEALED_ROWS, executor)
    if not discovery.converged or not all(item["passed"] for item in sealed):
        raise RuntimeError("motif-grown program failed its hidden evidence")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = "RUN-motif-growth-" + stamp
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)

    motif_payload = {
        "schema_version": "learned-word-motif-library-v0.1",
        "source_strict_record_count": len(sources),
        "input_metadata_used": ["room_record_id", "program"],
        "formula_names_used": False,
        "motifs": [item.to_dict() for item in motifs],
    }
    motif_encoded = json.dumps(
        motif_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    motif_payload["library_digest"] = hashlib.sha256(motif_encoded.encode()).hexdigest()
    motif_library = ROOT / "artifacts/motifs/learned_word_motifs.json"
    motif_library.parent.mkdir(parents=True, exist_ok=True)
    motif_library.write_text(
        json.dumps(motif_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    observation = NumericTableObservation.create(
        opaque_session_id="motif-growth-feedback",
        input_rows=DEVELOPMENT_ROWS,
        output_values=tuple(hidden_relation(*row) for row in DEVELOPMENT_ROWS),
        validity_mask=(True,) * len(DEVELOPMENT_ROWS),
        action_receipt="anonymous_five_column_feedback_v0.1",
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
            failed_scope="motif_growth_cross_parameter",
            condition_key="anonymous_five_column_relation",
            counterexamples=failures[:5],
            source_candidate_id=candidate.candidate_id,
        )
        mistake_ids.append(record.mistake_id)
        if len(mistake_ids) == 10:
            break

    success_room = FormulaSuccessRoom(
        ROOT / "artifacts/formula_rooms/success/successful_formulas.jsonl"
    )
    operation_id = "MOTIF-GROWN-" + hashlib.sha256(
        reflective_program_key(winner.program).encode()
    ).hexdigest()[:16]
    success = success_room.record(
        winner.program,
        operation_id=operation_id,
        parent_operation_ids=tuple(item.motif_id for item in motifs),
        validation_scope="opaque_motif_growth_unseen_parameters",
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

    first_counterexample_round = next(
        item for item in discovery.rounds if item.added_counterexample_index is not None
    )
    counterexample_index = first_counterexample_round.added_counterexample_index
    assert counterexample_index is not None
    counterexample_row = DEVELOPMENT_ROWS[counterexample_index]
    first_counterexample = {
        "inputs": list(counterexample_row),
        "predicted": executor.execute(
            first_counterexample_round.candidate.program, counterexample_row
        ).output_value,
        "observed": hidden_relation(*counterexample_row),
    }
    report = {
        "report_version": "motif-growth-discovery-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verdict": "bounded_motif_grown_program_awaiting_universal_proof",
        "candidate": winner.to_dict(),
        "program_digest": program_digest(winner.program),
        "cegis_rounds": [item.to_dict() for item in discovery.rounds],
        "first_counterexample": first_counterexample,
        "sealed_results": sealed,
        "learned_motifs": [item.to_dict() for item in motifs],
        "motif_library_path": str(motif_library.relative_to(ROOT)),
        "success_room_record": success.to_dict(),
        "mistake_ids": mistake_ids,
        "learner_received": {
            "formula_name": False,
            "recurrence_name": False,
            "anonymous_numeric_columns": 5,
            "multiply_divide_power_opcodes": False,
            "prior_proven_word_programs": len(sources),
            "prior_formula_labels": False,
        },
        "posthoc_interpretation": {
            "formula": "F(a,b,p,q,n): F0=a, F1=b, F(t+2)=p*F(t+1)+q*F(t)",
            "bottom_computation": "two repeated-addition loops plus synchronous state update",
        },
        "limitations": [
            "The motif predicates and structural mutation slots are still host-implemented.",
            "The learner grew input/state routing from motifs extracted from proven code; it did not invent a new VM opcode.",
            "Sealed finite evidence is bounded until the independent all-domain proof is recorded.",
        ],
    }
    artifact = run_dir / "motif_growth_discovery_report.json"
    artifact.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for destination in (
        ROOT / "reports/data/motif_growth_discovery_latest.json",
        ROOT / "dashboard/data/motif_growth_discovery_latest.json",
    ):
        shutil.copyfile(artifact, destination)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "motifs": len(motifs),
                "cegis_rounds": len(discovery.rounds),
                "sealed": f"{sum(item['passed'] for item in sealed)}/{len(sealed)}",
                "mistakes_recorded": len(mistake_ids),
                "candidate_id": winner.candidate_id,
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
