"""Discover a second batch of five distinct verified Gen 2 control programs."""

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
    ReflectiveProgram,
    ReflectiveProgramSearch,
    reflective_program_key,
)
from akgm_n0.learner.metamachine_gen2 import (
    OP_ADD_INPUT,
    OP_GROW,
    OP_JUMP,
    OP_JUMP_IF_NEGATIVE,
    OP_JUMP_IF_ZERO,
    OP_LOAD_INPUT,
    OP_SUB_CELL,
    OP_SUB_INPUT,
)


TASKS = (
    {
        "opaque_task": "j",
        "development": tuple(((n,), (0, 1, 1, 0, -1, -1)[n % 6]) for n in range(10)),
        "sealed": tuple(((n,), (0, 1, 1, 0, -1, -1)[n % 6]) for n in (10, 11, 12, 13, 14)),
        "adversarial": tuple(((n,), (0, 1, 1, 0, -1, -1)[n % 6]) for n in (20, 1, 0)),
        "initial": (0, 1, 2),
        "mechanism": "subtractive_two_state_oscillator",
        "posthoc_human_interpretation": "two synchronous states update as next A equals A plus B and next B equals one minus A, producing a signed six-step oscillator",
    },
    {
        "opaque_task": "k",
        "development": tuple(((n,), value) for n, value in enumerate((0, 0, 0, 1, 4, 10, 20, 35, 56))),
        "sealed": (((9,), 84), ((10,), 120), ((12,), 220), ((15,), 455), ((20,), 1140)),
        "adversarial": (((25,), 2300), ((1,), 0), ((0,), 0)),
        "initial": (0, 1, 2, 3),
        "mechanism": "three_state_dependency_cascade",
        "posthoc_human_interpretation": "three synchronous states form a one-way accumulation cascade with a unit source",
    },
    {
        "opaque_task": "l",
        "development": tuple(((n,), n % 4) for n in range(13)),
        "sealed": (((13,), 1), ((14,), 2), ((15,), 3), ((20,), 0), ((31,), 3)),
        "adversarial": (((40,), 0), ((1,), 1), ((0,), 0)),
        "initial": (0, 1, 2, 3, 4),
        "mechanism": "threshold_wrap_control",
        "posthoc_human_interpretation": "a tentative state is compared with an evidence threshold and conditionally wrapped",
    },
    {
        "opaque_task": "m",
        "development": (
            ((6, 4), 2), ((15, 10), 5), ((21, 14), 7), ((17, 5), 1),
            ((9, 3), 3), ((8, 12), 4), ((27, 18), 9), ((25, 15), 5),
        ),
        "sealed": (((48, 18), 6), ((81, 57), 3), ((100, 35), 5), ((121, 44), 11), ((144, 60), 12)),
        "adversarial": (((233, 144), 1), ((7, 7), 7), ((1, 99), 1)),
        "initial": (0, 1, 2),
        "mechanism": "two_input_comparison_rewrite",
        "posthoc_human_interpretation": "two positive states repeatedly rewrite the larger by their difference until equality",
    },
    {
        "opaque_task": "n",
        "development": tuple(((n,), int(n ** 0.5)) for n in range(25)),
        "sealed": (((25,), 5), ((35,), 5), ((36,), 6), ((48,), 6), ((64,), 8)),
        "adversarial": (((99,), 9), ((1,), 1), ((0,), 0)),
        "initial": (0, 1, 4, 9),
        "mechanism": "guarded_changing_step_accumulator",
        "posthoc_human_interpretation": "a remainder is reduced by an increasing odd state until the next reduction would cross zero",
    },
)


def observation(task_id, cases):
    return NumericTableObservation.create(
        opaque_session_id=task_id,
        input_rows=tuple(row for row, _ in cases),
        output_values=tuple(output for _, output in cases),
        validity_mask=(True,) * len(cases),
        action_receipt="generic_reflective_control_task",
    )


def evaluate(program, cases, executor):
    results = []
    for row, observed in cases:
        try:
            execution = executor.execute(program, row)
            predicted = execution.output_value
            results.append(
                {
                    "input": list(row), "predicted": predicted, "observed": observed,
                    "absolute_error": abs(predicted - observed), "step_count": execution.step_count,
                    "memory_growth_count": len(execution.memory_growth),
                    "code_modification_count": len(execution.code_modifications), "passed": predicted == observed,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "input": list(row), "predicted": None, "observed": observed,
                    "absolute_error": None, "step_count": None, "memory_growth_count": 0,
                    "code_modification_count": 0, "passed": False, "error": type(exc).__name__,
                }
            )
    return tuple(results)


def program_input_width(program):
    width = 0
    for offset in range(0, len(program.words), 2):
        if program.words[offset] in (OP_LOAD_INPUT, OP_ADD_INPUT, OP_SUB_INPUT):
            width = max(width, program.words[offset + 1] + 1)
    return width


def probe_rows(width):
    if width == 1:
        return tuple((value,) for value in range(17))
    if width == 2:
        return ((1, 1), (2, 1), (1, 2), (6, 4), (8, 12), (17, 5), (21, 14), (25, 15), (48, 18), (81, 57))
    return ()


def behavior_fingerprint(program, width, executor):
    values = []
    for row in probe_rows(width):
        try:
            values.append(executor.execute(program, row).output_value)
        except Exception:
            values.append(None)
    return tuple(values)


def mechanism_check(task, program):
    opcodes = program.words[::2]
    grow = next(program.words[offset + 1] for offset in range(0, len(program.words), 2) if program.words[offset] == OP_GROW)
    jumps = opcodes.count(OP_JUMP)
    mechanism = task["mechanism"]
    checks = {
        "subtractive_two_state_oscillator": grow == 5 and OP_SUB_CELL in opcodes,
        "three_state_dependency_cascade": grow == 7 and jumps == 1,
        "threshold_wrap_control": grow == 3 and jumps >= 2 and OP_JUMP_IF_NEGATIVE in opcodes,
        "two_input_comparison_rewrite": grow == 2 and jumps >= 2 and OP_JUMP_IF_ZERO in opcodes and OP_JUMP_IF_NEGATIVE in opcodes,
        "guarded_changing_step_accumulator": grow == 3 and jumps == 1 and OP_JUMP_IF_NEGATIVE in opcodes,
    }
    return checks[mechanism], {"grow_operand": grow, "jump_count": jumps, "input_width": program_input_width(program)}


def select_feedback(search, winner, task, mistakes, executor):
    report = search.search(observation(f"opaque-control-{task['opaque_task']}-feedback", task["development"]))
    selected, seen = [], set()
    probe_cases = task["development"] + task["sealed"]
    for candidate in (winner, *report.top_candidates):
        signature = tuple(item["predicted"] for item in evaluate(candidate.program, probe_cases, executor))
        if signature in seen:
            continue
        selected.append(candidate)
        seen.add(signature)
        if len(selected) == 5:
            break
    if len(selected) != 5:
        raise RuntimeError("fewer than five candidate behaviors")
    feedback = []
    for rank, candidate in enumerate(selected, start=1):
        development = evaluate(candidate.program, task["development"], executor)
        sealed = evaluate(candidate.program, task["sealed"], executor)
        counterexamples = tuple(item for item in development + sealed if not item["passed"])
        is_winner = candidate.candidate_id == winner.candidate_id
        mistake = None
        if counterexamples:
            mistake = mistakes.record(
                candidate.program, failed_scope="metamachine_gen2_five_control_development_or_sealed",
                condition_key=f"opaque-gen2-control-{task['opaque_task']}", counterexamples=counterexamples,
                source_candidate_id=candidate.candidate_id,
            )
        feedback.append(
            {
                "rank": rank, **candidate.to_dict(), "development_results": list(development),
                "sealed_results": list(sealed), "sealed_exact": all(item["passed"] for item in sealed),
                "disposition": "success_room" if is_winner else "mistake_library",
                "mistake_id": mistake.mistake_id if mistake else None,
            }
        )
    return feedback


def main() -> int:
    executor = ReflectiveExecutor(maximum_steps=4096)
    shared_search = ReflectiveProgramSearch(top_k=200, executor=executor)
    shared_cegis = CounterexampleGuidedReflectiveSearch(search=shared_search, maximum_rounds=8)
    synthesized = []
    for task in TASKS:
        result = shared_cegis.synthesize(
            opaque_task_id=f"opaque-gen2-control-{task['opaque_task']}",
            input_rows=tuple(row for row, _ in task["development"]),
            output_values=tuple(value for _, value in task["development"]),
            initial_case_indices=task["initial"],
        )
        sealed = evaluate(result.final_candidate.program, task["sealed"], executor)
        adversarial = evaluate(result.final_candidate.program, task["adversarial"], executor)
        mechanism_passed, mechanism_evidence = mechanism_check(task, result.final_candidate.program)
        width = len(task["development"][0][0])
        synthesized.append(
            {
                "task": task, "result": result, "sealed": sealed, "adversarial": adversarial,
                "exact": result.converged and all(item["passed"] for item in sealed + adversarial),
                "mechanism_passed": mechanism_passed, "mechanism_evidence": mechanism_evidence,
                "input_width": width,
                "fingerprint": behavior_fingerprint(result.final_candidate.program, width, executor),
            }
        )

    program_keys = [reflective_program_key(item["result"].final_candidate.program) for item in synthesized]
    typed_fingerprints = [(item["input_width"], item["fingerprint"]) for item in synthesized]
    formula_room = FormulaSuccessRoom(PROJECT_ROOT / "artifacts" / "formula_rooms" / "success" / "successful_formulas.jsonl")
    old_fingerprints = {}
    for record in formula_room.records:
        definition = dict(record.definition)
        if definition.get("substrate") != "anonymous_unified_word_machine_v0.1":
            continue
        try:
            program = ReflectiveProgram.from_dict(definition)
            width = program_input_width(program)
            if width in (1, 2):
                old_fingerprints[record.operation_id] = (width, behavior_fingerprint(program, width, executor))
        except Exception:
            continue
    duplicate_old = {
        item["result"].final_candidate.candidate_id: operation_id
        for item in synthesized
        for operation_id, old in old_fingerprints.items()
        if (item["input_width"], item["fingerprint"]) == old
    }
    gates = [
        {"gate_id": "second_batch_five_exact", "passed": all(item["exact"] for item in synthesized), "actual": sum(item["exact"] for item in synthesized), "threshold": 5},
        {"gate_id": "five_new_structures", "passed": len(set(program_keys)) == 5, "actual": len(set(program_keys)), "threshold": 5},
        {"gate_id": "five_new_typed_behaviors", "passed": len(set(typed_fingerprints)) == 5, "actual": len(set(typed_fingerprints)), "threshold": 5},
        {"gate_id": "five_control_mechanisms_selected", "passed": all(item["mechanism_passed"] for item in synthesized), "actual": sum(item["mechanism_passed"] for item in synthesized), "threshold": 5},
        {"gate_id": "no_duplicate_among_18_old_successes", "passed": not duplicate_old, "actual": duplicate_old, "threshold": {}},
        {"gate_id": "same_search_instance_all_five", "passed": True, "actual": 1, "threshold": 1},
        {"gate_id": "sealed_hidden_during_search", "passed": True, "actual": True, "threshold": True},
    ]
    if not all(gate["passed"] for gate in gates):
        print(json.dumps({"verdict": "failed_before_admission", "gates": gates, "candidates": [{"task": item["task"]["opaque_task"], "candidate": item["result"].final_candidate.candidate_id, "mechanism": item["mechanism_evidence"], "mechanism_passed": item["mechanism_passed"]} for item in synthesized]}, ensure_ascii=False, indent=2))
        return 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-metamachine-gen2-control-five-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    mistakes = AdaptiveMistakeLibrary(PROJECT_ROOT / "artifacts" / "mistakes" / "adaptive_mistakes.jsonl")
    task_records, feedback_records, room_records = [], {}, []
    for item in synthesized:
        task, result = item["task"], item["result"]
        candidate = result.final_candidate
        knowledge_id = ledger.propose(
            candidate.program, parent_ids=("metamachine_gen2_control_grammar_v0.4",),
            provenance={"run_id": run_id, "candidate_id": candidate.candidate_id, "opaque_task": task["opaque_task"]},
            evidence={"cegis_round_count": len(result.rounds)},
        )
        ledger.transition(knowledge_id, "fit_passed", reason="generic_control_cegis_converged", evidence={"rounds": [round_item.to_dict() for round_item in result.rounds]})
        ledger.transition(knowledge_id, "verified", reason="sealed_and_adversarial_exact", evidence={"sealed": item["sealed"], "adversarial": item["adversarial"]})
        ledger.transition(knowledge_id, "bounded", reason="verified_bounded_control_program", evidence={"maximum_steps": executor.maximum_steps})
        operation_id = "G2CTRL-" + hashlib.sha256(reflective_program_key(candidate.program).encode("utf-8")).hexdigest()[:16]
        room_record = formula_room.record(
            candidate.program, operation_id=operation_id,
            parent_operation_ids=("metamachine_gen2_control_grammar_v0.4",),
            validation_scope=f"opaque_gen2_control_task_{task['opaque_task']}_v0.1", knowledge_status="bounded",
            evidence={"run_id": run_id, "development_case_count": len(task["development"]), "sealed_case_count": len(task["sealed"]), "adversarial_case_count": len(task["adversarial"]), "typed_behavior_fingerprint": [item["input_width"], list(item["fingerprint"])], "all_exact": True},
        )
        room_records.append(room_record)
        feedback_records[f"opaque_task_{task['opaque_task']}"] = select_feedback(shared_search, candidate, task, mistakes, executor)
        task_records.append(
            {
                "opaque_task": task["opaque_task"], "mechanism": task["mechanism"], "candidate": candidate.to_dict(),
                "cegis": {"converged": result.converged, "round_count": len(result.rounds), "rounds": [round_item.to_dict() for round_item in result.rounds]},
                "sealed_results": list(item["sealed"]), "adversarial_results": list(item["adversarial"]),
                "input_width": item["input_width"], "behavior_fingerprint": list(item["fingerprint"]),
                "mechanism_evidence": item["mechanism_evidence"], "success_room_record": room_record.to_dict(),
                "posthoc_human_interpretation": task["posthoc_human_interpretation"],
            }
        )

    report = {
        "report_version": "metamachine-gen2-five-control-growth-v0.1", "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "MetaMachine Gen 2：第二批五个成功控制公式", "verdict": "conditionally_passed",
        "knowledge_status": "bounded", "architecture": "same_reflective_searcher_plus_generic_control_grammars_v0.4",
        "stop_rule": {"minimum_new_successful_formulas": 5, "actual": 5, "satisfied": True},
        "learner_received": {"natural_language": False, "task_names": False, "target_formulas": False, "remainder_sqrt_gcd_or_combinatorial_opcode": False, "generic_control_grammars": True, "sealed_cases_visible_during_search": False},
        "tasks": task_records, "five_candidate_feedback_per_task": feedback_records, "gates": gates,
        "success_room_records_added": [record.to_dict() for record in room_records],
        "success_room_active_count": len(formula_room.records), "mistake_feedback_count": 20,
        "ledger_event_count": len(ledger.events),
        "autonomy_accounting": {
            "host_supplied": ["16 primitive opcodes", "generic control layouts", "anonymous numeric evidence", "resource bounds", "counterexample protocol"],
            "learner_selected": ["state count", "state initialization", "copy/add/subtract dependencies", "comparison branch", "threshold", "data-driven halt", "output state"],
            "posthoc_only": ["human formula names and mathematical interpretations"],
        },
        "limitations": [
            "The control layouts remain host-supplied generic search grammars.",
            "The comparison-rewrite result is verified only for positive integer input pairs.",
            "Other unary results are bounded to the registered integer domains and 4096 instructions.",
            "The learner still did not invent a new opcode or choose external experiments.",
            "Enumeration remains expensive; exact search time is not evidence of efficient reasoning.",
        ],
    }
    artifact_path = run_directory / "metamachine_gen2_five_control_growth_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "metamachine_gen2_five_control_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "metamachine_gen2_five_control_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact_path, destination)
    print(json.dumps({"run_id": run_id, "verdict": report["verdict"], "successful_formula_count": 5, "candidates": [item["result"].final_candidate.candidate_id for item in synthesized], "cegis_rounds": {record["opaque_task"]: record["cegis"]["round_count"] for record in task_records}, "success_room_records": [record.room_record_id for record in room_records], "success_room_active_count": len(formula_room.records), "artifact_path": str(artifact_path.relative_to(PROJECT_ROOT))}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
