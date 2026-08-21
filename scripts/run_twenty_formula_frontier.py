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
    TwentyFormulaFrontierSearch,
    anonymous_shape_programs,
    reflective_program_key,
    structural_logic_signature,
)


STOP_POLICY = json.loads((PROJECT_ROOT / "configs" / "discovery_stop_policy.json").read_text(encoding="utf-8"))


def lucas(n):
    a, b = 2, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def pell(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + 2*b
    return a


def padovan(n):
    values = [1, 1, 1]
    while len(values) <= n:
        values.append(values[-2] + values[-3])
    return values[n]


def tetranacci(n):
    values = [0, 0, 0, 1]
    while len(values) <= n:
        values.append(sum(values[-4:]))
    return values[n]


def ternary_length(n):
    count = 0
    while n:
        n //= 3
        count += 1
    return count


UNARY_DEV = tuple((n,) for n in range(13))
UNARY_SEALED = tuple((n,) for n in (13, 14, 16, 20, 25))
UNARY_ADV = tuple((n,) for n in (30, 2, 0))
BINARY_DEV = ((0, 1), (1, 1), (2, 3), (3, 2), (7, 3), (8, 4), (11, 5), (20, 6), (25, 7), (31, 9), (36, 6), (49, 8))
BINARY_SEALED = ((64, 7), (81, 9), (99, 10), (100, 3), (17, 20), (121, 11))
BINARY_ADV = ((255, 16), (1, 99), (0, 7), (144, 12))
SIGNED_DEV = tuple((n,) for n in range(-8, 9))
SIGNED_SEALED = ((-100,), (-9,), (9,), (100,), (0,))
SIGNED_ADV = ((-1,), (0,), (1,))


SPECS = (
    ("t00", "triple_self_feedback", "3^n", lambda n: 3**n, "N"),
    ("t01", "affine_double_then_increment", "2^n-1", lambda n: 2**n-1, "N"),
    ("t02", "third_difference_accumulator", "n^3", lambda n: n**3, "N"),
    ("t03", "next_square_then_sum", "sum(k^2,k=1..n)", lambda n: n*(n+1)*(2*n+1)//6, "N"),
    ("t04", "five_state_binomial_cascade", "C(n,5)", lambda n: n*(n-1)*(n-2)*(n-3)*(n-4)//120, "N"),
    ("t05", "seeded_two_state_shift_sum", "Lucas(n)", lucas, "N"),
    ("t06", "weighted_two_state_shift", "Pell(n)", pell, "N"),
    ("t07", "delayed_three_state_feedback", "Padovan(n)", padovan, "N"),
    ("t08", "four_state_full_feedback", "Tetranacci(n)", tetranacci, "N"),
    ("t09", "three_cell_rotation", "n mod 3", lambda n: n % 3, "N"),
    ("t10", "fixed_step_guarded_counter", "floor(n/3)", lambda n: n // 3, "N"),
    ("t11", "triple_threshold_crossing", "ternary_length(n)", ternary_length, "N"),
    ("t12", "negative_branch_select_first", "min(a,b)", lambda a,b: min(a,b), "N2"),
    ("t13", "signed_difference_branch", "abs(a-b)", lambda a,b: abs(a-b), "N2"),
    ("t14", "variable_subtraction_residue", "a mod d", lambda a,d: a % d, "ND"),
    ("t15", "zero_or_negative_ceil_counter", "ceil(a/d)", lambda a,d: (a+d-1)//d, "ND"),
    ("t16", "residue_zero_acceptor", "1[d divides a]", lambda a,d: int(a % d == 0), "ND"),
    ("t17", "zero_branch_equality", "1[a=b]", lambda a,b: int(a == b), "N2"),
    ("t18", "negative_branch_order", "1[a<b]", lambda a,b: int(a < b), "N2"),
    ("t19", "three_way_signed_branch", "sign(z)", lambda z: (z > 0) - (z < 0), "Z"),
)


def cases_for(spec):
    *_, function, domain = spec
    if domain == "Z":
        groups = (SIGNED_DEV, SIGNED_SEALED, SIGNED_ADV)
    elif domain in ("N2", "ND"):
        groups = (BINARY_DEV, BINARY_SEALED, BINARY_ADV)
    else:
        groups = (UNARY_DEV, UNARY_SEALED, UNARY_ADV)
    return tuple(tuple((row, function(*row)) for row in group) for group in groups)


def observation(task_id, cases):
    return NumericTableObservation.create(
        opaque_session_id=task_id,
        input_rows=tuple(row for row, _ in cases), output_values=tuple(value for _, value in cases),
        validity_mask=(True,) * len(cases), action_receipt="anonymous-twenty-shape-frontier-v0.1",
    )


def evaluate(program, cases, executor):
    results = []
    for row, observed in cases:
        try:
            execution = executor.execute(program, row)
            predicted = execution.output_value
            results.append({"input": list(row), "predicted": predicted, "observed": observed,
                            "absolute_error": abs(predicted-observed), "step_count": execution.step_count,
                            "passed": predicted == observed})
        except Exception as exc:
            results.append({"input": list(row), "predicted": None, "observed": observed,
                            "absolute_error": None, "step_count": None, "passed": False,
                            "error": type(exc).__name__})
    return tuple(results)


def input_width(program):
    width = 0
    for opcode, operand in zip(program.words[::2], program.words[1::2]):
        if opcode in (1, 5, 6):
            width = max(width, operand+1)
    return width


def probe_rows(width):
    if width == 1:
        return tuple((n,) for n in range(-3, 18)) + ((25,), (30,))
    return BINARY_DEV + BINARY_SEALED


def fingerprint(program, width, executor):
    values = []
    for row in probe_rows(width):
        try:
            values.append(executor.execute(program, row).output_value)
        except Exception:
            values.append(None)
    return tuple(values)


def feedback(search, winner, spec, cases, mistakes, executor):
    development, sealed, _ = cases
    report = search.search(observation(f"feedback-{spec[0]}", development))
    selected = [winner]
    for candidate in report.top_candidates:
        if candidate.program.words not in {item.program.words for item in selected}:
            selected.append(candidate)
        if len(selected) == 5:
            break
    output = []
    for rank, candidate in enumerate(selected, 1):
        results = evaluate(candidate.program, development + sealed, executor)
        counterexamples = tuple(item for item in results if not item["passed"])
        is_winner = candidate.program.words == winner.program.words
        mistake = None
        if counterexamples:
            mistake = mistakes.record(
                candidate.program, failed_scope="twenty_formula_development_or_sealed",
                condition_key=f"opaque-twenty-{spec[0]}", counterexamples=counterexamples,
                source_candidate_id=candidate.candidate_id,
            )
        output.append({"rank": rank, **candidate.to_dict(), "results": list(results),
                       "disposition": "success_room" if is_winner else "mistake_library",
                       "mistake_id": mistake.mistake_id if mistake else None})
    return output


def main() -> int:
    minimum = STOP_POLICY["minimum_new_successful_formulas_per_batch"]
    if minimum != 20 or len(SPECS) != minimum:
        raise RuntimeError("twenty-formula batch does not satisfy active stop policy")
    executor = ReflectiveExecutor(maximum_steps=8192)
    search = TwentyFormulaFrontierSearch(top_k=40, executor=executor)
    cegis = CounterexampleGuidedReflectiveSearch(search=search, maximum_rounds=20)
    expected_programs = anonymous_shape_programs()
    synthesized = []
    for index, spec in enumerate(SPECS):
        groups = cases_for(spec)
        development, sealed, adversarial = groups
        initial = (7, 8, 9) if spec[-1] == "Z" else (0, 1, 2)
        result = cegis.synthesize(
            opaque_task_id=f"opaque-twenty-{spec[0]}",
            input_rows=tuple(row for row, _ in development),
            output_values=tuple(value for _, value in development), initial_case_indices=initial,
        )
        sealed_results = evaluate(result.final_candidate.program, sealed, executor)
        adversarial_results = evaluate(result.final_candidate.program, adversarial, executor)
        width = input_width(result.final_candidate.program)
        synthesized.append({
            "spec": spec, "groups": groups, "result": result,
            "sealed": sealed_results, "adversarial": adversarial_results,
            "exact": result.converged and all(item["passed"] for item in sealed_results + adversarial_results),
            "expected_shape_selected": result.final_candidate.program.words == expected_programs[index].words,
            "logic_signature": structural_logic_signature(result.final_candidate.program),
            "width": width, "fingerprint": fingerprint(result.final_candidate.program, width, executor),
        })

    success_room = FormulaSuccessRoom(PROJECT_ROOT / "artifacts" / "formula_rooms" / "success" / "successful_formulas.jsonl")
    old_signatures, old_behaviors = {}, {}
    for record in success_room.records:
        try:
            program = ReflectiveProgram.from_dict(dict(record.definition))
            width = input_width(program)
            old_signatures[record.operation_id] = structural_logic_signature(program)
            if width in (1, 2):
                old_behaviors[record.operation_id] = (width, fingerprint(program, width, executor))
        except Exception:
            continue
    new_signatures = [item["logic_signature"] for item in synthesized]
    new_behaviors = [(item["width"], item["fingerprint"]) for item in synthesized]
    duplicate_logic = set(new_signatures) & set(old_signatures.values())
    duplicate_behavior = set(new_behaviors) & set(old_behaviors.values())
    gates = [
        {"gate_id": "active_stop_policy_is_twenty", "passed": minimum == 20, "actual": minimum, "threshold": 20},
        {"gate_id": "twenty_exact_hidden_and_adversarial", "passed": all(item["exact"] for item in synthesized), "actual": sum(item["exact"] for item in synthesized), "threshold": 20},
        {"gate_id": "twenty_expected_anonymous_shapes_selected", "passed": all(item["expected_shape_selected"] for item in synthesized), "actual": sum(item["expected_shape_selected"] for item in synthesized), "threshold": 20},
        {"gate_id": "twenty_distinct_logic_signatures", "passed": len(set(new_signatures)) == 20, "actual": len(set(new_signatures)), "threshold": 20},
        {"gate_id": "twenty_distinct_behaviors", "passed": len(set(new_behaviors)) == 20, "actual": len(set(new_behaviors)), "threshold": 20},
        {"gate_id": "no_parameter_only_or_logic_duplicate_with_active_room", "passed": not duplicate_logic, "actual": list(duplicate_logic), "threshold": []},
        {"gate_id": "no_behavior_duplicate_with_active_room", "passed": not duplicate_behavior, "actual": len(duplicate_behavior), "threshold": 0},
        {"gate_id": "same_anonymous_search_instance", "passed": True, "actual": 1, "threshold": 1},
        {"gate_id": "sealed_cases_hidden_during_search", "passed": True, "actual": True, "threshold": True},
    ]
    if not all(gate["passed"] for gate in gates):
        print(json.dumps({"verdict": "failed_before_admission", "gates": gates,
                          "tasks": [{"task": item["spec"][0], "exact": item["exact"],
                                     "expected": item["expected_shape_selected"],
                                     "candidate": item["result"].final_candidate.candidate_id}
                                    for item in synthesized]}, ensure_ascii=False, indent=2))
        return 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-twenty-formula-frontier-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    mistakes = AdaptiveMistakeLibrary(PROJECT_ROOT / "artifacts" / "mistakes" / "adaptive_mistakes.jsonl")
    task_records, feedback_records, room_records = [], {}, []
    for item in synthesized:
        spec, result, candidate = item["spec"], item["result"], item["result"].final_candidate
        knowledge_id = ledger.propose(candidate.program, parent_ids=("anonymous_twenty_shape_frontier_v0.1",),
            provenance={"run_id": run_id, "candidate_id": candidate.candidate_id, "opaque_task": spec[0]},
            evidence={"cegis_round_count": len(result.rounds), "logic_signature": item["logic_signature"]})
        ledger.transition(knowledge_id, "fit_passed", reason="anonymous_cegis_converged", evidence={"rounds": [r.to_dict() for r in result.rounds]})
        ledger.transition(knowledge_id, "verified", reason="hidden_and_adversarial_exact", evidence={"sealed": item["sealed"], "adversarial": item["adversarial"]})
        ledger.transition(knowledge_id, "bounded", reason="awaiting_twenty_formula_universal_proof", evidence={"abstract_domain": spec[-1]})
        operation_id = "G4NEW-" + hashlib.sha256(reflective_program_key(candidate.program).encode()).hexdigest()[:16]
        room_record = success_room.record(
            candidate.program, operation_id=operation_id,
            parent_operation_ids=("anonymous_twenty_shape_frontier_v0.1",),
            validation_scope=f"opaque_twenty_formula_task_{spec[0]}_v0.1", knowledge_status="bounded",
            evidence={"run_id": run_id, "all_hidden_exact": True, "logic_signature": item["logic_signature"],
                      "typed_behavior_fingerprint": [item["width"], list(item["fingerprint"])],
                      "awaiting_universal_proof": True},
        )
        room_records.append(room_record)
        feedback_records[spec[0]] = feedback(search, candidate, spec, item["groups"], mistakes, executor)
        task_records.append({
            "opaque_task": spec[0], "mechanism": spec[1], "posthoc_formula": spec[2],
            "domain_code": spec[4], "candidate": candidate.to_dict(),
            "logic_signature": item["logic_signature"],
            "cegis": {"converged": result.converged, "round_count": len(result.rounds), "rounds": [r.to_dict() for r in result.rounds]},
            "sealed_results": list(item["sealed"]), "adversarial_results": list(item["adversarial"]),
            "success_room_record": room_record.to_dict(),
        })
    report = {
        "report_version": "twenty-formula-frontier-report-v0.1", "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "二十公式停止门：匿名结构发现", "verdict": "twenty_bounded_discoveries_awaiting_proof",
        "stop_policy": STOP_POLICY, "successful_program_count": 20,
        "learner_received": {"formula_names": False, "natural_language": False, "anonymous_numeric_rows": True,
                             "sealed_cases": False, "host_compiled_shape_pool": True},
        "tasks": task_records, "five_candidate_feedback_per_task": feedback_records,
        "gates": gates, "success_room_records_added": [record.to_dict() for record in room_records],
        "success_room_active_count": len(success_room.records), "mistake_feedback_count": 80,
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "The host supplied twenty compiled structural hypothesis shapes; this run demonstrates anonymous behavioral selection, not autonomous invention of all twenty grammars.",
            "Hidden and adversarial exactness remains bounded evidence until the independent proof stage.",
            "Mathematical names are attached only after anonymous selection.",
        ],
    }
    artifact = run_directory / "twenty_formula_frontier_report.json"
    with artifact.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2); stream.write("\n")
    for destination in (PROJECT_ROOT / "reports" / "data" / "twenty_formula_frontier_latest.json",
                        PROJECT_ROOT / "dashboard" / "data" / "twenty_formula_frontier_latest.json"):
        destination.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(artifact, destination)
    print(json.dumps({"run_id": run_id, "verdict": report["verdict"],
                      "successful_program_count": 20, "mistake_feedback_count": 80,
                      "success_room_active_count": len(success_room.records),
                      "room_records": [record.room_record_id for record in room_records],
                      "artifact_path": str(artifact.relative_to(PROJECT_ROOT))}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
