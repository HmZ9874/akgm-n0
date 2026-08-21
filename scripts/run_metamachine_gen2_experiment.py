"""Run MetaMachine Gen 2 reflective-kernel and generic CEGIS milestone tests."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import AdaptiveMistakeLibrary, FormulaSuccessRoom, KnowledgeLedger
from akgm_n0.learner import (
    CounterexampleGuidedReflectiveSearch,
    NumericTableObservation,
    ReflectiveExecutor,
    ReflectiveProgram,
    ReflectiveProgramSearch,
    reflective_program_key,
)
from akgm_n0.learner.metamachine_gen2 import (
    OP_EMIT,
    OP_GROW,
    OP_HALT,
    OP_JUMP,
    OP_JUMP_IF_NEGATIVE,
    OP_LOAD_CELL,
    OP_SET,
    OP_STORE_CELL,
)


TASK_A_DEVELOPMENT = (
    ((0, 0), 0),
    ((1, 2), 3),
    ((-2, 4), 2),
    ((5, -3), 2),
    ((-7, -2), -9),
    ((9, 1), 10),
    ((3, 3), 6),
)
TASK_A_SEALED = (
    ((12, -5), 7),
    ((-11, 8), -3),
    ((20, 20), 40),
    ((-4, -9), -13),
    ((0, 17), 17),
)
TASK_B_DEVELOPMENT = (
    ((0,), 0),
    ((2,), 2),
    ((7,), 7),
    ((-2,), 2),
    ((-5,), 5),
    ((3,), 3),
    ((-7,), 7),
)
TASK_B_SEALED = (
    ((-11,), 11),
    ((9,), 9),
    ((-1,), 1),
    ((0,), 0),
    ((25,), 25),
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
                    "visited_instruction_ids": list(execution.visited_instruction_ids),
                    "code_modification_count": len(execution.code_modifications),
                    "memory_growth_count": len(execution.memory_growth),
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
                    "visited_instruction_ids": [],
                    "code_modification_count": 0,
                    "memory_growth_count": 0,
                    "passed": False,
                    "error": type(exc).__name__,
                }
            )
    return tuple(results)


def observation(task_id, cases):
    return NumericTableObservation.create(
        opaque_session_id=task_id,
        input_rows=tuple(row for row, _ in cases),
        output_values=tuple(output for _, output in cases),
        validity_mask=(True,) * len(cases),
        action_receipt="generic_reflective_word_task",
    )


def five_feedback(search, cases, sealed, winner, mistakes, condition_key, executor):
    report = search.search(observation(condition_key, cases))
    selected = [winner]
    seen_behaviors = {winner.behavior_signature}
    for candidate in report.top_candidates:
        if candidate.candidate_id == winner.candidate_id:
            continue
        if candidate.behavior_signature in seen_behaviors:
            continue
        selected.append(candidate)
        seen_behaviors.add(candidate.behavior_signature)
        if len(selected) == 5:
            break
    if len(selected) < 5:
        raise RuntimeError("Gen 2 search produced fewer than five behavior classes")
    feedback = []
    for rank, candidate in enumerate(selected, start=1):
        development_results = evaluate(candidate.program, cases, executor)
        sealed_results = evaluate(candidate.program, sealed, executor)
        counterexamples = tuple(
            item for item in development_results + sealed_results if not item["passed"]
        )
        mistake = None
        if counterexamples:
            mistake = mistakes.record(
                candidate.program,
                failed_scope="metamachine_gen2_development_or_sealed",
                condition_key=condition_key,
                counterexamples=counterexamples,
                source_candidate_id=candidate.candidate_id,
            )
        feedback.append(
            {
                "rank": rank,
                **candidate.to_dict(),
                "development_results": list(development_results),
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
    self_modifying_probe = ReflectiveProgram(
        (
            OP_SET,
            7,
            OP_STORE_CELL,
            7,
            OP_JUMP,
            3,
            OP_SET,
            0,
            OP_EMIT,
            0,
            OP_HALT,
            0,
        )
    )
    self_modifying_result = executor.execute(self_modifying_probe, ())
    growth_probe = ReflectiveProgram(
        (
            OP_GROW,
            2,
            OP_SET,
            5,
            OP_STORE_CELL,
            12,
            OP_LOAD_CELL,
            12,
            OP_EMIT,
            0,
            OP_HALT,
            0,
        )
    )
    growth_result = executor.execute(growth_probe, ())

    shared_search = ReflectiveProgramSearch(top_k=200, executor=executor)
    shared_cegis = CounterexampleGuidedReflectiveSearch(
        search=shared_search, maximum_rounds=6
    )
    task_a = shared_cegis.synthesize(
        opaque_task_id="opaque-gen2-a",
        input_rows=tuple(row for row, _ in TASK_A_DEVELOPMENT),
        output_values=tuple(output for _, output in TASK_A_DEVELOPMENT),
        initial_case_indices=(0, 1, 2),
    )
    task_b = shared_cegis.synthesize(
        opaque_task_id="opaque-gen2-b",
        input_rows=tuple(row for row, _ in TASK_B_DEVELOPMENT),
        output_values=tuple(output for _, output in TASK_B_DEVELOPMENT),
        initial_case_indices=(0, 1, 2),
    )
    task_a_sealed = evaluate(task_a.final_candidate.program, TASK_A_SEALED, executor)
    task_b_sealed = evaluate(task_b.final_candidate.program, TASK_B_SEALED, executor)
    task_a_exact = task_a.converged and all(item["passed"] for item in task_a_sealed)
    task_b_exact = task_b.converged and all(item["passed"] for item in task_b_sealed)
    task_b_created_branch = OP_JUMP_IF_NEGATIVE in task_b.final_candidate.program.words

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-metamachine-gen2-{timestamp}"
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
    feedback_a = five_feedback(
        shared_search,
        TASK_A_DEVELOPMENT,
        TASK_A_SEALED,
        task_a.final_candidate,
        mistakes,
        "opaque-gen2-a",
        executor,
    )
    feedback_b = five_feedback(
        shared_search,
        TASK_B_DEVELOPMENT,
        TASK_B_SEALED,
        task_b.final_candidate,
        mistakes,
        "opaque-gen2-b",
        executor,
    )

    gates = (
        {
            "gate_id": "unified_code_and_data_memory",
            "passed": len(self_modifying_result.code_modifications) == 1,
            "actual": len(self_modifying_result.code_modifications),
            "threshold": 1,
        },
        {
            "gate_id": "runtime_memory_growth",
            "passed": len(growth_result.memory_growth) == 1,
            "actual": len(growth_result.memory_growth),
            "threshold": 1,
        },
        {
            "gate_id": "same_search_instance_two_tasks",
            "passed": task_a.converged and task_b.converged,
            "actual": [task_a.converged, task_b.converged],
            "threshold": [True, True],
        },
        {
            "gate_id": "counterexample_caused_control_revision",
            "passed": len(task_b.rounds) >= 2 and task_b_created_branch,
            "actual": {
                "rounds": len(task_b.rounds),
                "created_branch": task_b_created_branch,
            },
            "threshold": {"rounds": 2, "created_branch": True},
        },
        {
            "gate_id": "task_a_sealed_exact",
            "passed": task_a_exact,
            "actual": sum(item["passed"] for item in task_a_sealed),
            "threshold": len(TASK_A_SEALED),
        },
        {
            "gate_id": "task_b_sealed_exact",
            "passed": task_b_exact,
            "actual": sum(item["passed"] for item in task_b_sealed),
            "threshold": len(TASK_B_SEALED),
        },
    )
    verdict = "conditionally_passed" if all(item["passed"] for item in gates) else "failed"

    task_records = []
    for label, result, sealed_results in (
        ("a", task_a, task_a_sealed),
        ("b", task_b, task_b_sealed),
    ):
        candidate = result.final_candidate
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
            reason="generic_word_code_cegis_completed",
            evidence={"rounds": [item.to_dict() for item in result.rounds]},
        )
        sealed_exact = all(item["passed"] for item in sealed_results)
        room_record = None
        if result.converged:
            ledger.transition(
                knowledge_id,
                "verified" if sealed_exact else "rejected",
                reason="opaque_sealed_cases_evaluated",
                evidence={"sealed_results": sealed_results},
            )
        if result.converged and sealed_exact:
            ledger.transition(
                knowledge_id,
                "bounded",
                reason="verified_under_gen2_bounded_word_search",
                evidence={"kernel_version": "v0.1"},
            )
            operation_id = "G2OP-" + hashlib.sha256(
                reflective_program_key(candidate.program).encode("utf-8")
            ).hexdigest()[:16]
            room_record = formula_room.record(
                candidate.program,
                operation_id=operation_id,
                parent_operation_ids=("metamachine_gen2_kernel_v0.1",),
                validation_scope=f"opaque_gen2_task_{label}_v0.1",
                knowledge_status="bounded",
                evidence={
                    "run_id": run_id,
                    "development_case_count": (
                        len(TASK_A_DEVELOPMENT) if label == "a" else len(TASK_B_DEVELOPMENT)
                    ),
                    "sealed_case_count": len(sealed_results),
                    "all_exact": True,
                },
            )
        task_records.append(
            {
                "opaque_task": label,
                "knowledge_id": knowledge_id,
                "candidate": candidate.to_dict(),
                "cegis": {
                    "converged": result.converged,
                    "round_count": len(result.rounds),
                    "rounds": [item.to_dict() for item in result.rounds],
                },
                "sealed_results": list(sealed_results),
                "success_room_record": room_record.to_dict() if room_record else None,
                "posthoc_human_interpretation": (
                    "combine the two input values"
                    if label == "a"
                    else "preserve nonnegative input and reverse the sign of negative input"
                ),
            }
        )

    report = {
        "report_version": "metamachine-gen2-milestone-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "MetaMachine Gen 2：统一内存与反例驱动字程序",
        "verdict": verdict,
        "knowledge_status": "bounded",
        "architecture": "reflective_unified_word_vm_plus_task_agnostic_cegis_v0.1",
        "kernel": {
            "word_width": 2,
            "opcode_count": 16,
            "unified_code_data_memory": True,
            "candidate_controlled_halt": True,
            "self_modification_probe": {
                "program": self_modifying_probe.to_dict(),
                "output": self_modifying_result.output_value,
                "modifications": [asdict(item) for item in self_modifying_result.code_modifications],
                "passed": len(self_modifying_result.code_modifications) == 1,
            },
            "dynamic_growth_probe": {
                "program": growth_probe.to_dict(),
                "output": growth_result.output_value,
                "growth": [asdict(item) for item in growth_result.memory_growth],
                "passed": len(growth_result.memory_growth) == 1,
            },
        },
        "learner_received": {
            "natural_language": False,
            "task_names": False,
            "target_formulas": False,
            "same_searcher_source_for_both_tasks": True,
            "initial_case_indices": [0, 1, 2],
            "counterexample_feedback": "first failing row only",
            "sealed_cases_visible_during_search": False,
        },
        "tasks": task_records,
        "five_candidate_feedback": {
            "opaque_task_a": feedback_a,
            "opaque_task_b": feedback_b,
        },
        "gates": list(gates),
        "success_room_active_count": len(formula_room.records),
        "ledger_event_count": len(ledger.events),
        "autonomy_accounting": {
            "human_supplied": [
                "sixteen primitive opcode meanings",
                "resource bounds",
                "generic straight-line and conditional code grammar",
                "initial examples and evaluator counterexample pool",
            ],
            "system_generated": [
                "candidate word sequences",
                "choice between straight-line and conditional control",
                "revision after one revealed counterexample",
                "final program selection and replay",
            ],
            "capability_only_not_yet_autonomously_selected": [
                "writing into future code cells",
                "growing memory during a synthesized task",
                "inventing a brand-new opcode meaning",
                "choosing its own external experiment",
            ],
        },
        "limitations": [
            "The kernel can self-modify and grow memory, but those two capabilities are demonstrated by probes rather than selected by the current synthesizer.",
            "The generic search grammar currently covers bounded straight-line code and one conditional split; arbitrary loops are executable but not yet synthesized.",
            "Counterexamples are selected by the evaluator, not proposed as external experiments by the learner.",
            "Opcode meanings remain host-defined; autonomous creation of new primitive meanings is not yet verified.",
            "The two promoted programs are bounded evidence that one searcher can create different word-code structures, not evidence of general intelligence.",
        ],
    }
    artifact_path = run_directory / "metamachine_gen2_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "metamachine_gen2_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "metamachine_gen2_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact_path, destination)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": verdict,
                "self_modification_passed": len(self_modifying_result.code_modifications) == 1,
                "memory_growth_passed": len(growth_result.memory_growth) == 1,
                "task_a_rounds": len(task_a.rounds),
                "task_a_candidate": task_a.final_candidate.candidate_id,
                "task_a_sealed_exact": task_a_exact,
                "task_b_rounds": len(task_b.rounds),
                "task_b_candidate": task_b.final_candidate.candidate_id,
                "task_b_created_branch": task_b_created_branch,
                "task_b_sealed_exact": task_b_exact,
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
