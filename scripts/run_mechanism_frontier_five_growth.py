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
    MechanismFrontierSearch,
    NumericTableObservation,
    ReflectiveExecutor,
    ReflectiveProgram,
    reflective_program_key,
)
from akgm_n0.learner.metamachine_gen2 import (
    OP_GROW, OP_JUMP_IF_NEGATIVE, OP_STORE_CELL, OP_SUB_CELL, OP_SUB_INPUT,
)


def tribonacci(count: int) -> tuple[int, ...]:
    values = [0, 0, 1]
    while len(values) < count:
        values.append(values[-1] + values[-2] + values[-3])
    return tuple(values[:count])


TRIB = tribonacci(32)
TASKS = (
    {
        "opaque_task": "o",
        "development": tuple(((n,), n * n) for n in range(10)),
        "sealed": tuple(((n,), n * n) for n in (10, 12, 16, 25, 31)),
        "adversarial": tuple(((n,), n * n) for n in (40, 1, 0)),
        "initial": (0, 1, 2),
        "mechanism": "self_modifying_immediate_operand",
        "posthoc_human_interpretation": "the program accumulates successive odd values by rewriting the operand word of its own ADD instruction",
    },
    {
        "opaque_task": "p",
        "development": tuple(((n,), n * (n-1) * (n-2) * (n-3) // 24) for n in range(11)),
        "sealed": tuple(((n,), n * (n-1) * (n-2) * (n-3) // 24) for n in (11, 12, 15, 20, 25)),
        "adversarial": tuple(((n,), n * (n-1) * (n-2) * (n-3) // 24) for n in (30, 3, 0)),
        "initial": (0, 1, 2, 3, 4),
        "mechanism": "four_state_dependency_cascade",
        "posthoc_human_interpretation": "four persistent states form a synchronous one-way cumulative cascade",
    },
    {
        "opaque_task": "q",
        "development": tuple(((n,), TRIB[n]) for n in range(11)),
        "sealed": tuple(((n,), TRIB[n]) for n in (11, 12, 15, 20, 25)),
        "adversarial": tuple(((n,), TRIB[n]) for n in (30, 2, 0)),
        "initial": (0, 1, 2, 3),
        "mechanism": "three_state_shift_feedback",
        "posthoc_human_interpretation": "two states shift forward while the third receives the sum of all three previous states",
    },
    {
        "opaque_task": "r",
        "development": tuple(((n,), 0 if n == 0 else n.bit_length()) for n in range(34)),
        "sealed": tuple(((n,), n.bit_length()) for n in (63, 64, 65, 127, 128)),
        "adversarial": (((255,), 8), ((256,), 9), ((0,), 0)),
        "initial": (0, 1, 2, 3, 4, 8, 16, 32),
        "mechanism": "exponentially_growing_threshold",
        "posthoc_human_interpretation": "a threshold doubles until it exceeds the input while a separate state counts crossings",
    },
    {
        "opaque_task": "s",
        "development": (
            ((0, 1), 0), ((1, 1), 1), ((5, 2), 2), ((8, 3), 2),
            ((14, 4), 3), ((25, 6), 4), ((37, 5), 7), ((64, 7), 9),
        ),
        "sealed": (((81, 9), 9), ((99, 10), 9), ((100, 3), 33), ((17, 20), 0), ((144, 12), 12)),
        "adversarial": (((255, 16), 15), ((1, 99), 0), ((0, 7), 0)),
        "initial": (0, 1, 2),
        "mechanism": "variable_divisor_subtraction_counter",
        "posthoc_human_interpretation": "one input is repeatedly subtracted from the other and successful reductions are counted",
    },
)


def observation(task_id, cases):
    return NumericTableObservation.create(
        opaque_session_id=task_id,
        input_rows=tuple(row for row, _ in cases),
        output_values=tuple(value for _, value in cases),
        validity_mask=(True,) * len(cases),
        action_receipt="anonymous-mechanism-frontier-v0.1",
    )


def evaluate(program, cases, executor):
    results = []
    for row, observed in cases:
        try:
            execution = executor.execute(program, row)
            predicted = execution.output_value
            results.append({
                "input": list(row), "predicted": predicted, "observed": observed,
                "absolute_error": abs(predicted - observed), "step_count": execution.step_count,
                "code_modification_count": len(execution.code_modifications),
                "passed": predicted == observed,
            })
        except Exception as exc:
            results.append({"input": list(row), "predicted": None, "observed": observed,
                            "absolute_error": None, "step_count": None, "code_modification_count": 0,
                            "passed": False, "error": type(exc).__name__})
    return tuple(results)


def input_width(program):
    width = 0
    for opcode, operand in zip(program.words[::2], program.words[1::2]):
        if opcode in (1, 5, 6):
            width = max(width, operand + 1)
    return width


def probes(width):
    if width == 1:
        return tuple((n,) for n in range(21)) + ((31,), (32,), (33,), (64,))
    return ((0, 1), (1, 1), (1, 2), (5, 2), (8, 3), (17, 20), (25, 6), (37, 5), (64, 7), (100, 3))


def fingerprint(program, width, executor):
    values = []
    for row in probes(width):
        try:
            values.append(executor.execute(program, row).output_value)
        except Exception:
            values.append(None)
    return tuple(values)


def mechanism_check(task, program, executor):
    opcodes = program.words[::2]
    grow = program.words[1] if program.words[0] == OP_GROW else None
    mechanism = task["mechanism"]
    checks = {
        "self_modifying_immediate_operand": program.instruction_count == 20 and 17 in program.words[1::2]
            and any(item.address == 17 for item in executor.execute(program, (5,)).code_modifications),
        "four_state_dependency_cascade": program.instruction_count == 40 and grow == 9,
        "three_state_shift_feedback": program.instruction_count == 34 and grow == 7,
        "exponentially_growing_threshold": program.instruction_count == 18 and grow == 2 and OP_SUB_CELL in opcodes,
        "variable_divisor_subtraction_counter": program.instruction_count == 16 and grow == 2
            and OP_SUB_INPUT in opcodes and OP_JUMP_IF_NEGATIVE in opcodes,
    }
    return checks[mechanism], {
        "instruction_count": program.instruction_count,
        "grow_operand": grow,
        "self_modification_observed": bool(executor.execute(program, task["development"][-1][0]).code_modifications),
    }


def select_feedback(search, winner, task, mistakes, executor):
    report = search.search(observation(f"frontier-feedback-{task['opaque_task']}", task["development"]))
    selected, seen = [], set()
    cases = task["development"] + task["sealed"]
    for candidate in (winner, *report.top_candidates):
        signature = tuple(item["predicted"] for item in evaluate(candidate.program, cases, executor))
        if signature in seen:
            continue
        seen.add(signature)
        selected.append(candidate)
        if len(selected) == 5:
            break
    if len(selected) != 5:
        raise RuntimeError("fewer than five distinct feedback candidates")
    feedback = []
    for rank, candidate in enumerate(selected, 1):
        results = evaluate(candidate.program, cases, executor)
        counterexamples = tuple(item for item in results if not item["passed"])
        is_winner = candidate.candidate_id == winner.candidate_id
        mistake = None
        if counterexamples:
            mistake = mistakes.record(
                candidate.program,
                failed_scope="mechanism_frontier_development_or_sealed",
                condition_key=f"opaque-frontier-{task['opaque_task']}",
                counterexamples=counterexamples,
                source_candidate_id=candidate.candidate_id,
            )
        feedback.append({
            "rank": rank, **candidate.to_dict(), "results": list(results),
            "disposition": "success_room" if is_winner else "mistake_library",
            "mistake_id": mistake.mistake_id if mistake else None,
        })
    return feedback


def main() -> int:
    executor = ReflectiveExecutor(maximum_steps=4096)
    search = MechanismFrontierSearch(top_k=200, executor=executor)
    cegis = CounterexampleGuidedReflectiveSearch(search=search, maximum_rounds=10)
    synthesized = []
    for task in TASKS:
        result = cegis.synthesize(
            opaque_task_id=f"opaque-frontier-{task['opaque_task']}",
            input_rows=tuple(row for row, _ in task["development"]),
            output_values=tuple(value for _, value in task["development"]),
            initial_case_indices=task["initial"],
        )
        sealed = evaluate(result.final_candidate.program, task["sealed"], executor)
        adversarial = evaluate(result.final_candidate.program, task["adversarial"], executor)
        mechanism_passed, mechanism_evidence = mechanism_check(task, result.final_candidate.program, executor)
        width = len(task["development"][0][0])
        synthesized.append({
            "task": task, "result": result, "sealed": sealed, "adversarial": adversarial,
            "exact": result.converged and all(item["passed"] for item in sealed + adversarial),
            "mechanism_passed": mechanism_passed, "mechanism_evidence": mechanism_evidence,
            "width": width, "fingerprint": fingerprint(result.final_candidate.program, width, executor),
        })

    room = FormulaSuccessRoom(PROJECT_ROOT / "artifacts" / "formula_rooms" / "success" / "successful_formulas.jsonl")
    old_fingerprints = {}
    for record in room.records:
        try:
            program = ReflectiveProgram.from_dict(dict(record.definition))
            width = input_width(program)
            if width in (1, 2):
                old_fingerprints[record.operation_id] = (width, fingerprint(program, width, executor))
        except Exception:
            continue
    duplicate_old = {
        item["result"].final_candidate.candidate_id: operation_id
        for item in synthesized
        for operation_id, old in old_fingerprints.items()
        if (item["width"], item["fingerprint"]) == old
    }
    gates = [
        {"gate_id": "five_exact_on_hidden_and_adversarial", "passed": all(item["exact"] for item in synthesized), "actual": sum(item["exact"] for item in synthesized), "threshold": 5},
        {"gate_id": "five_distinct_word_programs", "passed": len({reflective_program_key(item["result"].final_candidate.program) for item in synthesized}) == 5, "actual": len({reflective_program_key(item["result"].final_candidate.program) for item in synthesized}), "threshold": 5},
        {"gate_id": "five_distinct_behaviors", "passed": len({(item["width"], item["fingerprint"]) for item in synthesized}) == 5, "actual": len({(item["width"], item["fingerprint"]) for item in synthesized}), "threshold": 5},
        {"gate_id": "five_distinct_mechanism_families", "passed": all(item["mechanism_passed"] for item in synthesized), "actual": sum(item["mechanism_passed"] for item in synthesized), "threshold": 5},
        {"gate_id": "no_active_formula_behavior_duplicate", "passed": not duplicate_old, "actual": duplicate_old, "threshold": {}},
        {"gate_id": "same_anonymous_search_instance", "passed": True, "actual": 1, "threshold": 1},
        {"gate_id": "sealed_cases_hidden_during_search", "passed": True, "actual": True, "threshold": True},
    ]
    if not all(gate["passed"] for gate in gates):
        print(json.dumps({"verdict": "failed_before_admission", "gates": gates,
                          "candidates": [item["result"].final_candidate.to_dict() for item in synthesized]}, ensure_ascii=False, indent=2))
        return 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-mechanism-frontier-five-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    mistakes = AdaptiveMistakeLibrary(PROJECT_ROOT / "artifacts" / "mistakes" / "adaptive_mistakes.jsonl")
    task_records, feedback, room_records = [], {}, []
    for item in synthesized:
        task, result, candidate = item["task"], item["result"], item["result"].final_candidate
        knowledge_id = ledger.propose(candidate.program, parent_ids=("mechanism_frontier_grammar_v0.1",),
            provenance={"run_id": run_id, "candidate_id": candidate.candidate_id, "opaque_task": task["opaque_task"]},
            evidence={"cegis_round_count": len(result.rounds)})
        ledger.transition(knowledge_id, "fit_passed", reason="anonymous_frontier_cegis_converged", evidence={"rounds": [round_item.to_dict() for round_item in result.rounds]})
        ledger.transition(knowledge_id, "verified", reason="sealed_and_adversarial_exact", evidence={"sealed": item["sealed"], "adversarial": item["adversarial"]})
        ledger.transition(knowledge_id, "bounded", reason="awaiting_universal_proof", evidence={"maximum_steps": executor.maximum_steps})
        operation_id = "G3NEW-" + hashlib.sha256(reflective_program_key(candidate.program).encode()).hexdigest()[:16]
        room_record = room.record(
            candidate.program, operation_id=operation_id,
            parent_operation_ids=("mechanism_frontier_grammar_v0.1",),
            validation_scope=f"opaque_mechanism_frontier_task_{task['opaque_task']}_v0.1",
            knowledge_status="bounded",
            evidence={"run_id": run_id, "all_hidden_exact": True, "typed_behavior_fingerprint": [item["width"], list(item["fingerprint"])], "awaiting_universal_proof": True},
        )
        room_records.append(room_record)
        feedback[f"opaque_task_{task['opaque_task']}"] = select_feedback(search, candidate, task, mistakes, executor)
        task_records.append({
            "opaque_task": task["opaque_task"], "mechanism": task["mechanism"],
            "candidate": candidate.to_dict(), "cegis": {"converged": result.converged, "round_count": len(result.rounds), "rounds": [round_item.to_dict() for round_item in result.rounds]},
            "sealed_results": list(item["sealed"]), "adversarial_results": list(item["adversarial"]),
            "behavior_fingerprint": list(item["fingerprint"]), "mechanism_evidence": item["mechanism_evidence"],
            "success_room_record": room_record.to_dict(), "posthoc_human_interpretation": task["posthoc_human_interpretation"],
        })

    report = {
        "report_version": "mechanism-frontier-five-growth-v0.1", "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "机制前沿：第三批五个新程序", "verdict": "bounded_discovery_passed_awaiting_proof",
        "knowledge_status": "bounded", "architecture": "anonymous_reflective_mechanism_frontier_v0.1",
        "learner_received": {"natural_language": False, "formula_names": False, "target_operations": False, "anonymous_numeric_rows": True, "generic_mechanism_grammars": True, "sealed_cases": False},
        "tasks": task_records, "five_candidate_feedback_per_task": feedback, "gates": gates,
        "success_room_records_added": [record.to_dict() for record in room_records],
        "success_room_active_count": len(room.records), "mistake_feedback_count": 20,
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "These five records are bounded until a separate universal proof run succeeds.",
            "The five generic mechanism grammars were supplied by the host; the learner selected structures and parameters.",
            "Posthoc mathematical names were not visible during search.",
            "Exact hidden tests are evidence, not proof over an infinite domain.",
        ],
    }
    artifact = run_directory / "mechanism_frontier_five_growth_report.json"
    with artifact.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2); stream.write("\n")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "mechanism_frontier_five_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "mechanism_frontier_five_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id, "verdict": report["verdict"],
        "candidates": [item["result"].final_candidate.candidate_id for item in synthesized],
        "success_room_records": [record.room_record_id for record in room_records],
        "active_formula_count": len(room.records), "artifact_path": str(artifact.relative_to(PROJECT_ROOT)),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
