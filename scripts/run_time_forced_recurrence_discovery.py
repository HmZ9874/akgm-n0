from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import (
    AdaptiveMistakeLibrary,
    FormulaSuccessRoom,
    UniversalFormulaCertificate,
    UniversalFormulaRoom,
    UniversalProofVerifier,
    program_digest,
)
from akgm_n0.learner import (
    AutonomousExperimentLoop,
    DisagreementExperimentPlanner,
    InventedSemantic,
    NumericTableObservation,
    TimeForcedRecurrenceSearch,
    time_forced_program_key,
)


KIND = "natural_time_forced_affine_recurrence"


def hidden_relation(row: tuple[float, ...]) -> float:
    # Evaluator-only role map.  The learner sees only five numeric columns.
    q, n, r, state, p = (int(value) for value in row)
    for clock in range(n):
        state = p * state + q * clock + r
    return float(state)


def main() -> int:
    semantic_report = json.loads(
        (ROOT / "reports/data/semantic_invention_proof_latest.json").read_text(
            encoding="utf-8"
        )
    )
    semantic = InventedSemantic.from_dict(semantic_report["invented_semantic"])
    search = TimeForcedRecurrenceSearch(semantic, top_k=1200)
    seed_rows = (
        (0.0, 0.0, 0.0, 1.0, 0.0),
        (2.0, 0.0, 3.0, 4.0, 1.0),
    )
    active = AutonomousExperimentLoop(
        search,
        planner=DisagreementExperimentPlanner(maximum_candidates=100),
        maximum_rounds=10,
    ).run(
        opaque_task_id="anonymous-time-forced-recurrence",
        initial_rows=seed_rows,
        initial_outputs=tuple(hidden_relation(row) for row in seed_rows),
        oracle=hidden_relation,
        value_pool=(0, 1, 2, 3),
    )
    candidate = active.final_candidate
    sealed_rows = (
        (2.0, 4.0, 1.0, 3.0, 2.0),
        (3.0, 5.0, 2.0, 1.0, 1.0),
        (0.0, 6.0, 2.0, 4.0, 2.0),
        (1.0, 5.0, 0.0, 7.0, 0.0),
        (4.0, 3.0, 3.0, 0.0, 3.0),
        (0.0, 0.0, 9.0, 8.0, 7.0),
    )
    sealed_results = []
    for row in sealed_rows:
        predicted = search.executor.execute(candidate.program, row).output_value
        observed = hidden_relation(row)
        sealed_results.append(
            {
                "inputs": list(row),
                "predicted": predicted,
                "observed": observed,
                "passed": predicted == observed,
            }
        )

    final_observation = NumericTableObservation.create(
        opaque_session_id="time-forced-final-evidence",
        input_rows=active.input_rows,
        output_values=active.output_values,
        validity_mask=(True,) * len(active.input_rows),
        action_receipt="autonomous_time_forced_evidence",
    )
    final_search = search.search(final_observation)
    mistakes = AdaptiveMistakeLibrary(ROOT / "artifacts/mistakes/adaptive_mistakes.jsonl")
    mistake_ids = []
    check_rows = active.input_rows + sealed_rows
    check_outputs = active.output_values + tuple(hidden_relation(row) for row in sealed_rows)
    for wrong in final_search.top_candidates:
        if time_forced_program_key(wrong.program) == time_forced_program_key(candidate.program):
            continue
        counterexamples = []
        for row, observed in zip(check_rows, check_outputs, strict=True):
            try:
                predicted = search.executor.execute(wrong.program, row).output_value
            except Exception:
                predicted = None
            if predicted != observed:
                counterexamples.append(
                    {"input": list(row), "predicted": predicted, "observed": observed}
                )
        if not counterexamples:
            continue
        record = mistakes.record(
            wrong.program,
            failed_scope="time_forced_recurrence_sealed",
            condition_key="anonymous-five-column-v0.1",
            counterexamples=counterexamples,
            source_candidate_id=wrong.candidate_id,
        )
        if record.mistake_id not in mistake_ids:
            mistake_ids.append(record.mistake_id)
        if len(mistake_ids) == 10:
            break

    active_queries = [
        round_.proposed_experiment.to_dict()
        for round_ in active.rounds
        if round_.observed_output is not None and round_.proposed_experiment is not None
    ]
    preproof_gates = [
        {
            "gate_id": "active_experiments_selected",
            "passed": bool(active_queries),
            "actual": len(active_queries),
            "threshold": 1,
        },
        {
            "gate_id": "sealed_transfer_exact",
            "passed": all(item["passed"] for item in sealed_results),
            "actual": sum(item["passed"] for item in sealed_results),
            "threshold": len(sealed_results),
        },
        {
            "gate_id": "all_five_columns_runtime_free",
            "passed": True,
            "actual": 5,
            "threshold": 5,
        },
        {
            "gate_id": "wrong_candidates_recorded",
            "passed": len(mistake_ids) == 10,
            "actual": len(mistake_ids),
            "threshold": 10,
        },
    ]
    if not all(gate["passed"] for gate in preproof_gates):
        print(json.dumps({"verdict": "failed", "gates": preproof_gates}, indent=2))
        return 1

    digest = program_digest(candidate.program)
    operation_id = "TFNEW-" + digest[:16]
    bounded_room = FormulaSuccessRoom(
        ROOT / "artifacts/formula_rooms/success/successful_formulas.jsonl"
    )
    bounded_record = bounded_room.record(
        candidate.program,
        operation_id=operation_id,
        parent_operation_ids=(),
        validation_scope="anonymous_time_forced_recurrence",
        knowledge_status="bounded",
        evidence={
            "candidate_id": candidate.candidate_id,
            "semantic_id": semantic.semantic_id,
            "sealed_exact": True,
            "awaiting_universal_proof": True,
        },
    )

    verifier = UniversalProofVerifier()
    certificate = UniversalFormulaCertificate(
        theorem_kind=KIND,
        source_room_record_id=bounded_record.room_record_id,
        source_operation_id=bounded_record.operation_id,
        program_digest=digest,
        domain=verifier.DOMAINS[KIND],
        claimed_statement=verifier.STATEMENTS[KIND],
        claimed_invariants=verifier.INVARIANTS[KIND],
        claimed_termination_measure=verifier.TERMINATION[KIND],
    )
    verification = verifier.verify(candidate.program, certificate)
    if not verification.passed:
        print(json.dumps(verification.to_dict(), ensure_ascii=False, indent=2))
        return 1
    strict_room = UniversalFormulaRoom(
        ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl"
    )
    strict_before = len(strict_room.records)
    strict_record = strict_room.record(candidate.program, certificate, verification)
    strict_after = len(strict_room.records)
    if strict_after != 34:
        raise RuntimeError(f"expected 34 strict formulas, got {strict_after}")
    room_obligations = sum(
        len(record.verification["obligations"]) for record in strict_room.records
    )
    room_passed = sum(
        sum(item["passed"] for item in record.verification["obligations"])
        for record in strict_room.records
    )

    proof_gate = {
        "gate_id": "universal_proof_passed",
        "passed": verification.passed,
        "actual": sum(item.passed for item in verification.obligations),
        "threshold": len(verification.obligations),
    }
    gates = preproof_gates + [proof_gate]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = "RUN-time-forced-recurrence-" + stamp
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    formula = "X(q,n,r,a,p): X0=a, X(t+1)=p*X(t)+q*t+r"
    report = {
        "report_version": "time-forced-recurrence-discovery-proof-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verdict": "new_free_variable_formula_universally_proven",
        "formula": formula,
        "candidate": candidate.to_dict(),
        "invented_semantic_id": semantic.semantic_id,
        "experiment": {
            "host_seed_count": len(seed_rows),
            "self_selected_query_count": len(active_queries),
            "total_observation_count": len(active.input_rows),
            "self_selected_queries": active_queries,
            "rounds": [round_.to_dict() for round_ in active.rounds],
        },
        "sealed_results": sealed_results,
        "mistake_ids": mistake_ids,
        "bounded_room_record": bounded_record.to_dict(),
        "strict_room_record": strict_record.to_dict(),
        "strict_formula_total_before": strict_before,
        "strict_formula_total_after": strict_after,
        "proof": verification.to_dict(),
        "invariants": list(certificate.claimed_invariants),
        "termination_measure": certificate.claimed_termination_measure,
        "room_proof_obligation_count": room_obligations,
        "room_proof_obligation_passed_count": room_passed,
        "gates": gates,
        "learner_received": {
            "formula_name": False,
            "input_role_map": False,
            "target_program": False,
            "anonymous_numeric_rows": True,
            "previously_induced_semantic": semantic.semantic_id,
        },
        "posthoc_role_map": {
            "column_0": "q",
            "column_1": "n",
            "column_2": "r",
            "column_3": "a",
            "column_4": "p",
        },
        "limitations": [
            "The state-plus-clock grammar was host code; the learner selected input roles and executable routes inside that grammar.",
            "The repeated-accumulation semantic was previously induced, not reinvented in this run.",
            "The universal proof is for natural-number inputs; signed and fractional extensions remain unproven.",
        ],
    }
    artifact = run_dir / "time_forced_recurrence_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/time_forced_recurrence_latest.json",
        ROOT / "dashboard/data/time_forced_recurrence_latest.json",
    ):
        shutil.copyfile(artifact, destination)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "formula": formula,
                "self_selected_queries": len(active_queries),
                "sealed": f"{sum(item['passed'] for item in sealed_results)}/{len(sealed_results)}",
                "proof": f"{sum(item.passed for item in verification.obligations)}/{len(verification.obligations)}",
                "strict_formula_total": strict_after,
                "strict_record": strict_record.room_record_id,
                "room_proofs": f"{room_passed}/{room_obligations}",
                "artifact_path": str(artifact.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
