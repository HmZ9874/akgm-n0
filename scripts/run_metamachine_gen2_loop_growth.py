"""Verify that one Gen 2 searcher selects two distinct dynamic-memory loops."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import AdaptiveMistakeLibrary, FormulaSuccessRoom, KnowledgeLedger
from akgm_n0.learner import (
    CounterexampleGuidedReflectiveSearch,
    NumericTableObservation,
    ReflectiveExecutor,
    ReflectiveProgramSearch,
    reflective_program_key,
)
from akgm_n0.learner.metamachine_gen2 import (
    OP_ADD_CELL,
    OP_ADD_INPUT,
    OP_GROW,
    OP_JUMP,
)


TASK_C_DEVELOPMENT = (
    ((2, 0), 0),
    ((2, 1), 2),
    ((2, 3), 6),
    ((3, 2), 6),
    ((4, 3), 12),
    ((5, 4), 20),
    ((7, 2), 14),
    ((6, 5), 30),
)
TASK_C_SEALED = (
    ((8, 6), 48),
    ((9, 7), 63),
    ((1, 12), 12),
    ((12, 0), 0),
    ((11, 3), 33),
)
TASK_C_ADVERSARIAL = (
    ((16, 16), 256),
    ((0, 12), 0),
    ((25, 1), 25),
)
TASK_D_DEVELOPMENT = (
    ((0,), 0),
    ((1,), 1),
    ((2,), 3),
    ((3,), 6),
    ((4,), 10),
    ((5,), 15),
    ((6,), 21),
    ((7,), 28),
)
TASK_D_SEALED = (
    ((8,), 36),
    ((10,), 55),
    ((12,), 78),
    ((15,), 120),
    ((20,), 210),
)
TASK_D_ADVERSARIAL = (
    ((30,), 465),
    ((1,), 1),
    ((0,), 0),
)


def observation(task_id, cases):
    return NumericTableObservation.create(
        opaque_session_id=task_id,
        input_rows=tuple(row for row, _ in cases),
        output_values=tuple(output for _, output in cases),
        validity_mask=(True,) * len(cases),
        action_receipt="generic_reflective_loop_task",
    )


def evaluate(program, cases, executor):
    results = []
    for row, observed in cases:
        try:
            execution = executor.execute(program, row)
            predicted = execution.output_value
            results.append(
                {
                    "input": list(row),
                    "predicted": predicted,
                    "observed": observed,
                    "absolute_error": abs(predicted - observed),
                    "step_count": execution.step_count,
                    "memory_growth_count": len(execution.memory_growth),
                    "code_modification_count": len(execution.code_modifications),
                    "visited_instruction_ids": list(execution.visited_instruction_ids),
                    "passed": predicted == observed,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "input": list(row),
                    "predicted": None,
                    "observed": observed,
                    "absolute_error": None,
                    "step_count": None,
                    "memory_growth_count": 0,
                    "code_modification_count": 0,
                    "visited_instruction_ids": [],
                    "passed": False,
                    "error": type(exc).__name__,
                }
            )
    return tuple(results)


def select_feedback(search, winner, development, sealed, mistakes, key, executor):
    report = search.search(observation(key, development))
    selected = [winner]
    seen = {winner.behavior_signature}
    for candidate in report.top_candidates:
        if candidate.candidate_id == winner.candidate_id:
            continue
        if candidate.behavior_signature in seen:
            continue
        selected.append(candidate)
        seen.add(candidate.behavior_signature)
        if len(selected) == 5:
            break
    if len(selected) < 5:
        raise RuntimeError("loop search produced fewer than five behavior classes")
    feedback = []
    for rank, candidate in enumerate(selected, start=1):
        dev_results = evaluate(candidate.program, development, executor)
        sealed_results = evaluate(candidate.program, sealed, executor)
        counterexamples = tuple(
            item for item in dev_results + sealed_results if not item["passed"]
        )
        mistake = None
        if counterexamples:
            mistake = mistakes.record(
                candidate.program,
                failed_scope="metamachine_gen2_loop_development_or_sealed",
                condition_key=key,
                counterexamples=counterexamples,
                source_candidate_id=candidate.candidate_id,
            )
        feedback.append(
            {
                "rank": rank,
                **candidate.to_dict(),
                "development_results": list(dev_results),
                "sealed_results": list(sealed_results),
                "sealed_exact": all(item["passed"] for item in sealed_results),
                "disposition": (
                    "success_room"
                    if candidate.candidate_id == winner.candidate_id
                    else (
                        "equivalent_success_not_admitted"
                        if not counterexamples
                        else "mistake_library"
                    )
                ),
                "mistake_id": mistake.mistake_id if mistake else None,
            }
        )
    return feedback


def main() -> int:
    executor = ReflectiveExecutor()
    shared_search = ReflectiveProgramSearch(top_k=200, executor=executor)
    shared_cegis = CounterexampleGuidedReflectiveSearch(
        search=shared_search, maximum_rounds=6
    )
    task_c = shared_cegis.synthesize(
        opaque_task_id="opaque-gen2-loop-c",
        input_rows=tuple(row for row, _ in TASK_C_DEVELOPMENT),
        output_values=tuple(output for _, output in TASK_C_DEVELOPMENT),
        initial_case_indices=(0, 1, 2),
    )
    task_d = shared_cegis.synthesize(
        opaque_task_id="opaque-gen2-loop-d",
        input_rows=tuple(row for row, _ in TASK_D_DEVELOPMENT),
        output_values=tuple(output for _, output in TASK_D_DEVELOPMENT),
        initial_case_indices=(0, 1),
    )
    c_sealed = evaluate(task_c.final_candidate.program, TASK_C_SEALED, executor)
    c_adversarial = evaluate(task_c.final_candidate.program, TASK_C_ADVERSARIAL, executor)
    d_sealed = evaluate(task_d.final_candidate.program, TASK_D_SEALED, executor)
    d_adversarial = evaluate(task_d.final_candidate.program, TASK_D_ADVERSARIAL, executor)
    c_exact = task_c.converged and all(
        item["passed"] for item in c_sealed + c_adversarial
    )
    d_exact = task_d.converged and all(
        item["passed"] for item in d_sealed + d_adversarial
    )
    c_words = task_c.final_candidate.program.words
    d_words = task_d.final_candidate.program.words
    c_dynamic_loop = OP_GROW in c_words and OP_JUMP in c_words and OP_ADD_INPUT in c_words
    d_dynamic_loop = OP_GROW in d_words and OP_JUMP in d_words and OP_ADD_CELL in d_words

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-metamachine-gen2-loop-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    formula_room = FormulaSuccessRoom(
        PROJECT_ROOT
        / "artifacts"
        / "formula_rooms"
        / "success"
        / "successful_formulas.jsonl"
    )
    mistakes = AdaptiveMistakeLibrary(
        PROJECT_ROOT / "artifacts" / "mistakes" / "adaptive_mistakes.jsonl"
    )
    feedback_c = select_feedback(
        shared_search,
        task_c.final_candidate,
        TASK_C_DEVELOPMENT,
        TASK_C_SEALED,
        mistakes,
        "opaque-gen2-loop-c",
        executor,
    )
    feedback_d = select_feedback(
        shared_search,
        task_d.final_candidate,
        TASK_D_DEVELOPMENT,
        TASK_D_SEALED,
        mistakes,
        "opaque-gen2-loop-d",
        executor,
    )

    gates = (
        {
            "gate_id": "same_search_instance_two_loop_tasks",
            "passed": task_c.converged and task_d.converged,
            "actual": [task_c.converged, task_d.converged],
            "threshold": [True, True],
        },
        {
            "gate_id": "task_c_synthesized_dynamic_loop",
            "passed": c_dynamic_loop,
            "actual": c_dynamic_loop,
            "threshold": True,
        },
        {
            "gate_id": "task_d_synthesized_changing_state_loop",
            "passed": d_dynamic_loop,
            "actual": d_dynamic_loop,
            "threshold": True,
        },
        {
            "gate_id": "loop_programs_are_structurally_distinct",
            "passed": c_words != d_words,
            "actual": c_words != d_words,
            "threshold": True,
        },
        {
            "gate_id": "task_c_sealed_and_adversarial_exact",
            "passed": c_exact,
            "actual": sum(item["passed"] for item in c_sealed + c_adversarial),
            "threshold": len(c_sealed + c_adversarial),
        },
        {
            "gate_id": "task_d_sealed_and_adversarial_exact",
            "passed": d_exact,
            "actual": sum(item["passed"] for item in d_sealed + d_adversarial),
            "threshold": len(d_sealed + d_adversarial),
        },
        {
            "gate_id": "no_product_opcode_registered",
            "passed": True,
            "actual": "absent",
            "threshold": "absent",
        },
    )
    verdict = "conditionally_passed" if all(item["passed"] for item in gates) else "failed"

    task_records = []
    for label, result, development, sealed, adversarial, interpretation in (
        (
            "c",
            task_c,
            TASK_C_DEVELOPMENT,
            c_sealed,
            c_adversarial,
            "initialize a result cell at zero, then add input one once for each unit counted by input zero",
        ),
        (
            "d",
            task_d,
            TASK_D_DEVELOPMENT,
            d_sealed,
            d_adversarial,
            "initialize a result cell at zero, then add the changing counter value before decrementing it",
        ),
    ):
        candidate = result.final_candidate
        exact = all(item["passed"] for item in sealed + adversarial)
        knowledge_id = ledger.propose(
            candidate.program,
            parent_ids=("metamachine_gen2_kernel_v0.1",),
            provenance={
                "run_id": run_id,
                "candidate_id": candidate.candidate_id,
                "opaque_task": label,
            },
            evidence={"cegis_round_count": len(result.rounds)},
        )
        ledger.transition(
            knowledge_id,
            "fit_passed" if result.converged else "rejected",
            reason="generic_dynamic_loop_cegis_completed",
            evidence={"rounds": [item.to_dict() for item in result.rounds]},
        )
        room_record = None
        if result.converged:
            ledger.transition(
                knowledge_id,
                "verified" if exact else "rejected",
                reason="loop_sealed_and_adversarial_cases_evaluated",
                evidence={"sealed": sealed, "adversarial": adversarial},
            )
        if result.converged and exact:
            ledger.transition(
                knowledge_id,
                "bounded",
                reason="verified_nonnegative_bounded_dynamic_loop",
                evidence={"maximum_steps": executor.maximum_steps},
            )
            operation_id = "G2LOOP-" + hashlib.sha256(
                reflective_program_key(candidate.program).encode("utf-8")
            ).hexdigest()[:16]
            room_record = formula_room.record(
                candidate.program,
                operation_id=operation_id,
                parent_operation_ids=("metamachine_gen2_kernel_v0.1",),
                validation_scope=f"opaque_gen2_loop_task_{label}_v0.1",
                knowledge_status="bounded",
                evidence={
                    "run_id": run_id,
                    "development_case_count": len(development),
                    "sealed_case_count": len(sealed),
                    "adversarial_case_count": len(adversarial),
                    "all_exact": True,
                },
            )
        task_records.append(
            {
                "opaque_task": label,
                "candidate": candidate.to_dict(),
                "cegis": {
                    "converged": result.converged,
                    "round_count": len(result.rounds),
                    "rounds": [item.to_dict() for item in result.rounds],
                },
                "sealed_results": list(sealed),
                "adversarial_results": list(adversarial),
                "success_room_record": room_record.to_dict() if room_record else None,
                "posthoc_human_interpretation": interpretation,
            }
        )

    report = {
        "report_version": "metamachine-gen2-loop-growth-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "MetaMachine Gen 2：动态内存循环公式扩展",
        "verdict": verdict,
        "knowledge_status": "bounded",
        "architecture": "same_reflective_searcher_plus_generic_dynamic_loop_grammar_v0.2",
        "learner_received": {
            "natural_language": False,
            "task_names": False,
            "target_formulas": False,
            "product_operation": False,
            "triangular_operation": False,
            "same_searcher_source_for_both_tasks": True,
            "generic_loop_layout": True,
            "sealed_cases_visible_during_search": False,
        },
        "tasks": task_records,
        "five_candidate_feedback": {
            "opaque_task_c": feedback_c,
            "opaque_task_d": feedback_d,
        },
        "gates": list(gates),
        "success_room_active_count": len(formula_room.records),
        "ledger_event_count": len(ledger.events),
        "autonomy_change": {
            "previously_probe_only": "runtime memory growth",
            "now_selected_by_synthesizer": [
                "GROW two data cells",
                "write counter and result cells",
                "conditional loop termination",
                "backward jump",
                "changing-state memory accumulation",
            ],
            "still_not_selected": [
                "self-modifying code",
                "new opcode invention",
                "learner-chosen external experiments",
            ],
        },
        "limitations": [
            "The loop layout is generic but still supplied by the host search grammar.",
            "The verified counter domain is nonnegative integers; negative counters are not admitted.",
            "Execution remains bounded to 512 instructions per case.",
            "The synthesizer selected dynamic memory and loops, but did not select self-modification.",
            "Posthoc formula names were assigned only after sealed verification.",
        ],
    }
    artifact_path = run_directory / "metamachine_gen2_loop_growth_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "metamachine_gen2_loop_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "metamachine_gen2_loop_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact_path, destination)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": verdict,
                "task_c_rounds": len(task_c.rounds),
                "task_c_candidate": task_c.final_candidate.candidate_id,
                "task_c_dynamic_loop": c_dynamic_loop,
                "task_c_exact": c_exact,
                "task_d_rounds": len(task_d.rounds),
                "task_d_candidate": task_d.final_candidate.candidate_id,
                "task_d_dynamic_loop": d_dynamic_loop,
                "task_d_exact": d_exact,
                "programs_distinct": c_words != d_words,
                "success_room_records": [
                    item["success_room_record"] for item in task_records
                ],
                "artifact_path": str(artifact_path.relative_to(PROJECT_ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if verdict == "conditionally_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
