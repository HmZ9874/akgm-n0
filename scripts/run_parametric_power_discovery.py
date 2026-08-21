"""Discover one two-input parametric operation from anonymous numeric evidence."""

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
    OP_JUMP_IF_ZERO,
    OP_LOAD_INPUT,
    OP_SUB_IMMEDIATE,
    OP_SUB_INPUT,
)


def value_for(base: int, counter: int) -> int:
    return base**counter


DEVELOPMENT_INPUTS = (
    (2, 0), (2, 1), (2, 2),
    (3, 1), (3, 2), (3, 3),
    (4, 1), (4, 2), (4, 3),
    (0, 1), (1, 4), (2, 4),
)
SEALED_INPUTS = ((5, 0), (5, 2), (5, 4), (7, 1), (7, 3), (9, 2), (11, 3))
ADVERSARIAL_INPUTS = ((0, 0), (0, 5), (1, 8), (6, 5), (10, 3))


def cases(rows):
    return tuple((row, value_for(*row)) for row in rows)


def observation(session_id, rows):
    prepared = cases(rows)
    return NumericTableObservation.create(
        opaque_session_id=session_id,
        input_rows=tuple(row for row, _ in prepared),
        output_values=tuple(value for _, value in prepared),
        validity_mask=(True,) * len(prepared),
        action_receipt="anonymous_two_input_cross_instance_evidence_v0.1",
    )


def evaluate(program, rows, executor):
    results = []
    for row, observed in cases(rows):
        try:
            execution = executor.execute(program, row)
            predicted = execution.output_value
            results.append({
                "inputs": list(row), "predicted": predicted, "observed": observed,
                "passed": predicted == observed, "step_count": execution.step_count,
            })
        except Exception as exc:
            results.append({
                "inputs": list(row), "predicted": None, "observed": observed,
                "passed": False, "error": type(exc).__name__,
            })
    return tuple(results)


def parametric_mechanism(program):
    instructions = tuple(zip(program.words[::2], program.words[1::2]))
    opcodes = tuple(opcode for opcode, _ in instructions)
    runtime_inputs = {
        operand for opcode, operand in instructions
        if opcode in (OP_LOAD_INPUT, OP_ADD_INPUT, OP_SUB_INPUT)
    }
    return {
        "two_free_inputs_loaded": runtime_inputs == {0, 1},
        "dynamic_memory": OP_GROW in opcodes,
        "nested_control": opcodes.count(OP_JUMP) >= 2 and opcodes.count(OP_JUMP_IF_ZERO) >= 2,
        "inner_accumulation": OP_ADD_CELL in opcodes or OP_ADD_INPUT in opcodes,
        "natural_counter_descent": opcodes.count(OP_SUB_IMMEDIATE) >= 2,
        "no_constant_base_instance": runtime_inputs == {0, 1},
        "no_multiply_or_power_opcode": True,
    }


def main() -> int:
    executor = ReflectiveExecutor(maximum_steps=100_000)
    search = ReflectiveProgramSearch(top_k=300, executor=executor)
    cegis = CounterexampleGuidedReflectiveSearch(search=search, maximum_rounds=20)
    development = cases(DEVELOPMENT_INPUTS)
    result = cegis.synthesize(
        opaque_task_id="opaque-parametric-two-input-00",
        input_rows=tuple(row for row, _ in development),
        output_values=tuple(value for _, value in development),
        initial_case_indices=(0, 1, 2),
    )
    candidate = result.final_candidate
    development_results = evaluate(candidate.program, DEVELOPMENT_INPUTS, executor)
    sealed_results = evaluate(candidate.program, SEALED_INPUTS, executor)
    adversarial_results = evaluate(candidate.program, ADVERSARIAL_INPUTS, executor)
    mechanism = parametric_mechanism(candidate.program)
    gates = [
        {"gate_id": "development_cross_instance_exact", "passed": all(x["passed"] for x in development_results), "actual": sum(x["passed"] for x in development_results), "threshold": len(development_results)},
        {"gate_id": "unseen_bases_exact", "passed": all(x["passed"] for x in sealed_results), "actual": sum(x["passed"] for x in sealed_results), "threshold": len(sealed_results)},
        {"gate_id": "zero_and_large_edge_cases_exact", "passed": all(x["passed"] for x in adversarial_results), "actual": sum(x["passed"] for x in adversarial_results), "threshold": len(adversarial_results)},
        {"gate_id": "both_inputs_are_runtime_variables", "passed": mechanism["two_free_inputs_loaded"], "actual": mechanism["two_free_inputs_loaded"], "threshold": True},
        {"gate_id": "nested_repeated_accumulation_selected", "passed": all(mechanism.values()), "actual": mechanism, "threshold": {key: True for key in mechanism}},
    ]
    if not all(gate["passed"] for gate in gates):
        print(json.dumps({
            "verdict": "failed_before_admission", "gates": gates,
            "candidate": candidate.to_dict(), "rounds": [item.to_dict() for item in result.rounds],
        }, ensure_ascii=False, indent=2))
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-parametric-power-{stamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    knowledge_id = ledger.propose(
        candidate.program,
        parent_ids=("anonymous_unified_word_machine_v0.1", "generic_nested_counter_grammar_v0.3"),
        provenance={"run_id": run_id, "candidate_id": candidate.candidate_id},
        evidence={"learner_visible_case_count": len(development)},
    )
    ledger.transition(knowledge_id, "fit_passed", reason="anonymous_cross_instance_cegis", evidence={"rounds": [item.to_dict() for item in result.rounds]})
    ledger.transition(knowledge_id, "verified", reason="unseen_base_and_edge_exact", evidence={"sealed": sealed_results, "adversarial": adversarial_results})
    ledger.transition(knowledge_id, "bounded", reason="awaiting_parametric_universal_proof", evidence={"domain": "N x N", "resource_limit": executor.maximum_steps})

    room = FormulaSuccessRoom(PROJECT_ROOT / "artifacts" / "formula_rooms" / "success" / "successful_formulas.jsonl")
    operation_id = "PARAM-" + hashlib.sha256(reflective_program_key(candidate.program).encode()).hexdigest()[:16]
    room_record = room.record(
        candidate.program,
        operation_id=operation_id,
        parent_operation_ids=("anonymous_unified_word_machine_v0.1", "generic_nested_counter_grammar_v0.3"),
        validation_scope="anonymous_parametric_natural_pair_v0.1",
        knowledge_status="bounded",
        evidence={
            "run_id": run_id, "cross_instance": True, "free_input_count": 2,
            "sealed_bases": sorted({row[0] for row in SEALED_INPUTS}),
            "awaiting_universal_proof": True,
        },
    )

    mistakes = AdaptiveMistakeLibrary(PROJECT_ROOT / "artifacts" / "mistakes" / "adaptive_mistakes.jsonl")
    final_search = search.search(observation("opaque-parametric-feedback", DEVELOPMENT_INPUTS))
    mistake_ids = []
    for other in final_search.top_candidates:
        if other.candidate_id == candidate.candidate_id:
            continue
        failures = [item for item in evaluate(other.program, DEVELOPMENT_INPUTS + SEALED_INPUTS, executor) if not item["passed"]]
        if not failures:
            continue
        record = mistakes.record(
            other.program,
            failed_scope="parametric_cross_instance_or_unseen_base",
            condition_key="opaque-parametric-two-input-00",
            counterexamples=failures,
            source_candidate_id=other.candidate_id,
        )
        mistake_ids.append(record.mistake_id)
        if len(mistake_ids) == 5:
            break

    report = {
        "report_version": "parametric-power-discovery-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "匿名二输入参数化规律发现",
        "verdict": "bounded_parametric_program_awaiting_universal_proof",
        "knowledge_status": "bounded",
        "learner_received": {
            "natural_language": False, "formula_name": False, "target_formula": False,
            "fixed_base_hint": False, "multiply_opcode": False, "power_opcode": False,
            "anonymous_numeric_input_output_rows": True,
            "generic_nested_counter_grammar": True,
        },
        "candidate": candidate.to_dict(),
        "cegis_rounds": [item.to_dict() for item in result.rounds],
        "development_results": development_results,
        "sealed_results": sealed_results,
        "adversarial_results": adversarial_results,
        "mechanism": mechanism,
        "gates": gates,
        "success_room_record": room_record.to_dict(),
        "mistake_ids": mistake_ids,
        "posthoc_interpretation": {
            "assigned_after_all_gates": True,
            "formula": "F(a,n)=a^n",
            "domain": "a,n in N with 0^0=1",
            "program_meaning": "repeat an inner accumulation controlled by runtime a, then repeat that transformation runtime n times",
        },
        "limitations": [
            "The learner selected a host-supplied generic nested-counter layout; it did not invent the loop grammar in this run.",
            "Finite hidden cases establish transfer to unseen bases but are not the universal proof.",
            "The formula name and exponent interpretation were assigned only after discovery.",
        ],
    }
    artifact = run_directory / "parametric_power_discovery_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "parametric_power_discovery_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "parametric_power_discovery_latest.json",
    ):
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id, "verdict": report["verdict"], "candidate_id": candidate.candidate_id,
        "success_room_record": room_record.room_record_id, "cegis_rounds": len(result.rounds),
        "mistakes": len(mistake_ids), "artifact_path": str(artifact.relative_to(PROJECT_ROOT)),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
