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
    NumericTableObservation,
    ReflectiveExecutor,
    ReflectiveProgram,
    RewriteGrowthSearch,
    RewriteRuleInducer,
    reflective_program_key,
)


DEVELOPMENT_ROWS = (
    (1, 2, 3, 1, 1, 1, 0),
    (4, 5, 6, 2, 1, 3, 0),
    (1, 2, 3, 1, 1, 1, 1),
    (1, 2, 3, 1, 1, 1, 2),
    (1, 2, 3, 1, 1, 1, 5),
    (2, 3, 5, 2, 1, 1, 3),
    (3, 1, 4, 1, 2, 3, 4),
    (5, 2, 1, 3, 1, 2, 3),
    (2, 7, 4, 2, 3, 1, 4),
)
SEALED_ROWS = (
    (6, 9, 2, 4, 2, 3, 3),
    (2, 5, 8, 3, 4, 2, 4),
    (8, 1, 7, 5, 2, 1, 2),
    (9, 3, 6, 2, 5, 4, 5),
    (4, 8, 1, 6, 1, 3, 3),
)


def hidden_relation(a, b, c, p, q, r, n):
    for _ in range(n):
        a, b, c = b, c, p * c + q * b + r * a
    return a


def reflective_sources(room):
    return tuple(
        (record.room_record_id, ReflectiveProgram.from_dict(dict(record.program)))
        for record in room.records
        if record.program.get("substrate") == "anonymous_unified_word_machine_v0.1"
    )


def evaluate(program, rows, executor):
    result = []
    for row in rows:
        predicted = executor.execute(program, row).output_value
        observed = hidden_relation(*row)
        result.append(
            {
                "inputs": list(row),
                "predicted": predicted,
                "observed": observed,
                "passed": predicted == observed,
            }
        )
    return result


def main() -> int:
    universal_room = UniversalFormulaRoom(
        ROOT / "artifacts/formula_rooms/universal/proven_formulas.jsonl"
    )
    strict_room = UniversalFormulaRoom(
        ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl"
    )
    universal_sources = reflective_sources(universal_room)
    strict_sources = reflective_sources(strict_room)
    motifs = MotifExtractor().extract(strict_sources)
    weighted_source = next(
        item
        for item in strict_sources
        if item[0]
        == json.loads(
            (ROOT / "reports/data/motif_growth_proof_latest.json").read_text(
                encoding="utf-8"
            )
        )["strict_room_record"]["room_record_id"]
    )
    rule = RewriteRuleInducer().induce(
        universal_sources, weighted_source, motifs
    )
    executor = ReflectiveExecutor(maximum_steps=300_000)
    search = RewriteGrowthSearch(rule, executor=executor)
    discovery = CounterexampleGuidedReflectiveSearch(
        search=search, maximum_rounds=12
    ).synthesize(
        opaque_task_id="opaque-seven-column-rewrite-growth",
        input_rows=DEVELOPMENT_ROWS,
        output_values=tuple(hidden_relation(*row) for row in DEVELOPMENT_ROWS),
        initial_case_indices=(0, 1),
    )
    winner = discovery.final_candidate
    sealed = evaluate(winner.program, SEALED_ROWS, executor)
    if not discovery.converged or not all(item["passed"] for item in sealed):
        raise RuntimeError("rewrite-grown program failed hidden evidence")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = "RUN-rewrite-growth-" + stamp
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)

    rule_payload = {
        "schema_version": "learned-program-rewrite-library-v0.1",
        "formula_names_used": False,
        "rules": [rule.to_dict()],
    }
    encoded = json.dumps(
        rule_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    rule_payload["library_digest"] = hashlib.sha256(encoded.encode()).hexdigest()
    rule_library = ROOT / "artifacts/rewrite_rules/learned_rewrite_rules.json"
    rule_library.parent.mkdir(parents=True, exist_ok=True)
    rule_library.write_text(
        json.dumps(rule_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    observation = NumericTableObservation.create(
        opaque_session_id="rewrite-growth-feedback",
        input_rows=DEVELOPMENT_ROWS,
        output_values=tuple(hidden_relation(*row) for row in DEVELOPMENT_ROWS),
        validity_mask=(True,) * len(DEVELOPMENT_ROWS),
        action_receipt="anonymous_seven_column_feedback_v0.1",
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
            failed_scope="rewrite_growth_cross_parameter",
            condition_key="anonymous_seven_column_relation",
            counterexamples=failures[:5],
            source_candidate_id=candidate.candidate_id,
        )
        mistake_ids.append(record.mistake_id)
        if len(mistake_ids) == 10:
            break

    success_room = FormulaSuccessRoom(
        ROOT / "artifacts/formula_rooms/success/successful_formulas.jsonl"
    )
    operation_id = "REWRITE-GROWN-" + hashlib.sha256(
        reflective_program_key(winner.program).encode()
    ).hexdigest()[:16]
    success = success_room.record(
        winner.program,
        operation_id=operation_id,
        parent_operation_ids=(rule.rule_id,),
        validation_scope="opaque_rewrite_growth_unseen_parameters",
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
    first_failed_round = next(
        item for item in discovery.rounds if item.added_counterexample_index is not None
    )
    failed_index = first_failed_round.added_counterexample_index
    assert failed_index is not None
    failed_row = DEVELOPMENT_ROWS[failed_index]
    report = {
        "report_version": "rewrite-growth-discovery-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verdict": "bounded_rewrite_grown_program_awaiting_universal_proof",
        "rewrite_rule": rule.to_dict(),
        "rewrite_rule_library_path": str(rule_library.relative_to(ROOT)),
        "candidate": winner.to_dict(),
        "program_digest": program_digest(winner.program),
        "cegis_rounds": [item.to_dict() for item in discovery.rounds],
        "first_counterexample": {
            "inputs": list(failed_row),
            "predicted": executor.execute(
                first_failed_round.candidate.program, failed_row
            ).output_value,
            "observed": hidden_relation(*failed_row),
        },
        "sealed_results": sealed,
        "success_room_record": success.to_dict(),
        "mistake_ids": mistake_ids,
        "learner_received": {
            "formula_name": False,
            "recurrence_name": False,
            "anonymous_numeric_columns": 7,
            "multiply_divide_power_opcodes": False,
            "theorem_labels_for_rule_induction": False,
            "learned_rewrite_rule": rule.rule_id,
        },
        "posthoc_interpretation": {
            "formula": "F(a,b,c,p,q,r,n): F0=a, F1=b, F2=c, F(t+3)=p*F(t+2)+q*F(t+1)+r*F(t)",
            "bottom_computation": "three repeated-addition terms, one shared accumulator, and a three-cell state shift",
        },
        "limitations": [
            "The rewrite-rule detector and symbolic assembler remain host-implemented.",
            "The rule was induced from structural progression in prior proven programs; it is not yet a self-authored VM opcode.",
            "Input columns retain stable positions even though their meanings and formula are hidden.",
        ],
    }
    artifact = run_dir / "rewrite_growth_discovery_report.json"
    artifact.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for destination in (
        ROOT / "reports/data/rewrite_growth_discovery_latest.json",
        ROOT / "dashboard/data/rewrite_growth_discovery_latest.json",
    ):
        shutil.copyfile(artifact, destination)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "rewrite_rule": rule.rule_id,
                "cegis_rounds": len(discovery.rounds),
                "sealed": f"{sum(item['passed'] for item in sealed)}/{len(sealed)}",
                "mistakes_recorded": len(mistake_ids),
                "candidate_id": winner.candidate_id,
                "instruction_count": winner.program.instruction_count,
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
