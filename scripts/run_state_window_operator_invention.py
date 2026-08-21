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
    UniversalFormulaRoom,
    verify_state_window_semantic,
)
from akgm_n0.learner import (
    AutonomousExperimentLoop,
    DisagreementExperimentPlanner,
    NumericTableObservation,
    StateWindowGrowthSearch,
    StateWindowOpcodeInducer,
    state_window_program_key,
)


def hidden_relation(row: tuple[float, ...]) -> float:
    # Evaluator-only order: (c,n,a,e,b,d).
    c, n, a, e, b, d = (int(value) for value in row)
    state = [a, b, c, d, e]
    for _ in range(n):
        state = state[1:] + [sum(state)]
    return float(state[0])


def main() -> int:
    strict = UniversalFormulaRoom(
        ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl"
    )
    word_sources = [
        (record.room_record_id, tuple(int(item) for item in record.program["words"]))
        for record in strict.records
        if "words" in record.program
    ]
    semantic = StateWindowOpcodeInducer().induce(word_sources, occupied_opcodes=(16,))
    semantic_verification = verify_state_window_semantic(semantic)
    if not semantic_verification["passed"]:
        print(json.dumps(semantic_verification, ensure_ascii=False, indent=2))
        return 1

    search = StateWindowGrowthSearch(semantic, top_k=5000)
    seed_rows = (
        (3.0, 0.0, 1.0, 5.0, 2.0, 4.0),
        (8.0, 0.0, 6.0, 10.0, 7.0, 9.0),
    )
    active = AutonomousExperimentLoop(
        search,
        planner=DisagreementExperimentPlanner(maximum_candidates=100),
        maximum_rounds=10,
    ).run(
        opaque_task_id="anonymous-state-window-operator",
        initial_rows=seed_rows,
        initial_outputs=tuple(hidden_relation(row) for row in seed_rows),
        oracle=hidden_relation,
        value_pool=(0, 1, 2, 3),
    )
    candidate = active.final_candidate
    sealed_rows = (
        (3.0, 5.0, 1.0, 5.0, 2.0, 4.0),
        (2.0, 6.0, 1.0, 4.0, 1.0, 3.0),
        (5.0, 7.0, 2.0, 6.0, 3.0, 4.0),
        (0.0, 8.0, 1.0, 1.0, 0.0, 2.0),
        (7.0, 4.0, 9.0, 3.0, 8.0, 6.0),
        (4.0, 0.0, 7.0, 2.0, 5.0, 3.0),
    )
    sealed_results = []
    for row in sealed_rows:
        predicted = search.executor.execute(candidate.program, row).output_value
        observed = hidden_relation(row)
        sealed_results.append(
            {
                "inputs": list(row), "predicted": predicted,
                "observed": observed, "passed": predicted == observed,
            }
        )

    final_observation = NumericTableObservation.create(
        opaque_session_id="state-window-final-evidence",
        input_rows=active.input_rows,
        output_values=active.output_values,
        validity_mask=(True,) * len(active.input_rows),
        action_receipt="autonomous_state_window_evidence",
    )
    final_search = search.search(final_observation)
    mistake_library = AdaptiveMistakeLibrary(
        ROOT / "artifacts/mistakes/adaptive_mistakes.jsonl"
    )
    mistake_ids = []
    all_rows = active.input_rows + sealed_rows
    all_outputs = active.output_values + tuple(hidden_relation(row) for row in sealed_rows)
    for wrong in final_search.top_candidates:
        if state_window_program_key(wrong.program) == state_window_program_key(candidate.program):
            continue
        counterexamples = []
        for row, observed in zip(all_rows, all_outputs, strict=True):
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
        record = mistake_library.record(
            wrong.program,
            failed_scope="state_window_operator_sealed",
            condition_key="anonymous-six-column-v0.1",
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
    digest = hashlib.sha256(state_window_program_key(candidate.program).encode()).hexdigest()
    success = FormulaSuccessRoom(
        ROOT / "artifacts/formula_rooms/success/successful_formulas.jsonl"
    )
    success_record = success.record(
        candidate.program,
        operation_id="SWNEW-" + digest[:16],
        parent_operation_ids=(),
        validation_scope="verified_state_window_width5",
        knowledge_status="verified",
        evidence={
            "semantic_id": semantic.semantic_id,
            "semantic_verifier": semantic_verification["verifier_version"],
            "unseen_width": 5,
            "sealed_exact": all(item["passed"] for item in sealed_results),
        },
    )

    gates = [
        {"gate_id": "next_unused_opcode_allocated", "passed": semantic.opcode == 17, "actual": semantic.opcode, "threshold": 17},
        {"gate_id": "copy_chains_mined_from_proven_code", "passed": {2, 3, 4}.issubset(semantic.observed_widths), "actual": list(semantic.observed_widths), "threshold": [2, 3, 4]},
        {"gate_id": "independent_semantic_equivalence", "passed": semantic_verification["passed"], "actual": sum(item["passed"] for item in semantic_verification["obligations"]), "threshold": len(semantic_verification["obligations"])},
        {"gate_id": "unseen_width_five_executes", "passed": all(item["passed"] for item in sealed_results), "actual": sum(item["passed"] for item in sealed_results), "threshold": len(sealed_results)},
        {"gate_id": "self_selected_experiment_exists", "passed": bool(active_queries), "actual": len(active_queries), "threshold": 1},
        {"gate_id": "wrong_routes_enter_mistake_room", "passed": len(mistake_ids) == 10, "actual": len(mistake_ids), "threshold": 10},
    ]
    if not all(gate["passed"] for gate in gates):
        print(json.dumps({"verdict": "failed", "gates": gates}, ensure_ascii=False, indent=2))
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = "RUN-state-window-operator-" + stamp
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    report = {
        "report_version": "state-window-operator-invention-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verdict": "new_memory_operator_verified",
        "invented_operator": semantic.to_dict(),
        "posthoc_symbol": "OP17 / WINDOW_SHIFT",
        "induction_evidence": {
            "uses_formula_names": False,
            "observed_copy_chain_widths": list(semantic.observed_widths),
            "supporting_proven_program_count": len(semantic.source_record_ids),
            "supporting_occurrence_count": semantic.supporting_occurrence_count,
        },
        "semantic_verification": semantic_verification,
        "demonstration": {
            "candidate": candidate.to_dict(),
            "unseen_window_width": 5,
            "compressed_instruction_count": candidate.program.instruction_count,
            "expanded_instruction_count": candidate.program.instruction_count - 1 + 10,
            "posthoc_formula": "F0=a,F1=b,F2=c,F3=d,F4=e,F(t+5)=sum(F(t)..F(t+4))",
            "success_room_record": success_record.to_dict(),
        },
        "experiment": {
            "host_seed_count": len(seed_rows),
            "self_selected_query_count": len(active_queries),
            "total_observation_count": len(active.input_rows),
            "self_selected_queries": active_queries,
            "rounds": [round_.to_dict() for round_ in active.rounds],
        },
        "sealed_results": sealed_results,
        "mistake_ids": mistake_ids,
        "gates": gates,
        "learner_received": {
            "operator_name_or_symbol": False,
            "formula_names": False,
            "copy_chain_width_labels": False,
            "proven_word_code": True,
            "anonymous_numeric_rows": True,
        },
        "limitations": [
            "The detector, descriptor encoding, and extended interpreter are host code; this is constrained semantic induction.",
            "The operator copies a contiguous window and one append source; arbitrary graph-shaped memory movement is not yet supported.",
            "The width-generalization proof is symbolic plus bounded executable probes, not self-generated machine code for a new interpreter.",
        ],
    }
    artifact = run_dir / "state_window_operator_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/state_window_operator_latest.json",
        ROOT / "dashboard/data/state_window_operator_latest.json",
    ):
        shutil.copyfile(artifact, destination)
    registry = ROOT / "artifacts/semantics/state_window_operator_latest.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact, registry)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "semantic_id": semantic.semantic_id,
                "opcode": semantic.opcode,
                "observed_widths": list(semantic.observed_widths),
                "unseen_width": 5,
                "self_selected_queries": len(active_queries),
                "sealed": f"{sum(item['passed'] for item in sealed_results)}/{len(sealed_results)}",
                "semantic_proof": f"{sum(item['passed'] for item in semantic_verification['obligations'])}/{len(semantic_verification['obligations'])}",
                "mistakes_recorded": len(mistake_ids),
                "artifact_path": str(artifact.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
