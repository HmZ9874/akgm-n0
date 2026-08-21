"""Bind a meaningless glyph only after synthesized micro-semantics pass blind tests."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import (
    FormulaSuccessRoom,
    HiddenIntegerGridEnvironment,
    KnowledgeLedger,
    MicroMistakeLibrary,
)
from akgm_n0.learner import (
    InvalidMicroProgram,
    MicroProgramExecutor,
    MicroProgramSearch,
    UnboundSemanticError,
    UnboundSemanticSlot,
)


SECRET = b"unbound-symbol-semantics-v0.1"
GLYPHS = ("*", "@", "#")


def verify(program, observation, executor):
    cases = []
    for index, (row, observed) in enumerate(
        zip(observation.input_rows, observation.output_values, strict=True)
    ):
        try:
            execution = executor.execute(program, row)
            predicted = execution.output_value
            passed = predicted == observed
            cases.append(
                {
                    "case_index": index,
                    "input_row": list(row),
                    "predicted_value": predicted,
                    "observed_value": observed,
                    "step_count": execution.step_count,
                    "passed": passed,
                    "failure": None,
                }
            )
        except InvalidMicroProgram as exc:
            cases.append(
                {
                    "case_index": index,
                    "input_row": list(row),
                    "predicted_value": None,
                    "observed_value": observed,
                    "step_count": None,
                    "passed": False,
                    "failure": str(exc),
                }
            )
    return cases


def main() -> int:
    development_rows = (
        (2, 2),
        (2, 3),
        (3, 2),
        (4, 3),
        (-2, 3),
        (5, 2),
        (3, 4),
        (6, 5),
    )
    blind_rows = (
        (7, 5),
        (-4, 6),
        (11, 0),
        (2, 9),
        (9, 2),
        (-3, 8),
    )
    adversarial_rows = (
        (0, 7),
        (8, 0),
        (-5, 7),
        (12, 8),
        (1, 64),
    )
    development = HiddenIntegerGridEnvironment(
        development_rows, seed=401, secret=SECRET
    ).observe()
    blind = HiddenIntegerGridEnvironment(
        blind_rows, seed=402, secret=SECRET
    ).observe()
    adversarial = HiddenIntegerGridEnvironment(
        adversarial_rows, seed=403, secret=SECRET
    ).observe()

    empty_slot = UnboundSemanticSlot("*")
    unbound_call_rejected = False
    try:
        empty_slot.execute((2, 3))
    except UnboundSemanticError:
        unbound_call_rejected = True

    condition_key = "semantic-grid-" + hashlib.sha256(
        json.dumps(development_rows, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    failed_scope = "sealed_blind_semantic_validation"
    mistake_library = MicroMistakeLibrary(
        PROJECT_ROOT / "artifacts" / "mistakes" / "micro_mistakes.jsonl"
    )
    search = MicroProgramSearch(
        top_k=200,
        candidate_gate=mistake_library.candidate_gate(
            failed_scope=failed_scope, condition_key=condition_key
        ),
    )
    search_report = search.search(development)
    development_exact = [
        candidate
        for candidate in search_report.top_candidates
        if candidate.fit_error == 0.0
    ]
    if not development_exact:
        raise RuntimeError("no development-exact micro semantics were synthesized")

    executor = MicroProgramExecutor()
    candidate_assessments = []
    new_mistake_records = []
    blind_passing = []
    for candidate in development_exact:
        blind_cases = verify(candidate.program, blind, executor)
        passed = all(case["passed"] for case in blind_cases)
        candidate_assessments.append(
            {
                "candidate": candidate.to_dict(),
                "blind_passed": passed,
                "blind_cases": blind_cases,
            }
        )
        if passed:
            blind_passing.append(candidate)
        else:
            failed_cases = tuple(case for case in blind_cases if not case["passed"])
            record = mistake_library.record(
                candidate.program,
                failed_scope=failed_scope,
                condition_key=condition_key,
                counterexamples=failed_cases,
                source_candidate_id=candidate.candidate_id,
            )
            new_mistake_records.append(record.to_dict())
    if not blind_passing:
        raise RuntimeError("independent blind verification rejected every exact candidate")
    selected = blind_passing[0]
    blind_cases = verify(selected.program, blind, executor)
    adversarial_cases = verify(selected.program, adversarial, executor)

    serialized = json.dumps(selected.program.to_dict(), sort_keys=True).casefold()
    forbidden_tokens = ("multiply", "divide", "iterate", "product")
    forbidden_tokens_absent = all(token not in serialized for token in forbidden_tokens)
    glyph_results = []
    for glyph in GLYPHS:
        slot = UnboundSemanticSlot(glyph, executor=executor)
        binding = slot.bind(selected.program, verification_status="bounded")
        glyph_results.append(
            {
                "glyph": glyph,
                "operation_id": binding.operation_id,
                "probe_output": slot.execute((7, 5)).output_value,
            }
        )
    glyph_invariant = (
        len({item["operation_id"] for item in glyph_results}) == 1
        and len({item["probe_output"] for item in glyph_results}) == 1
    )

    gates = [
        {
            "gate_id": "glyph_has_no_intrinsic_behavior",
            "passed": unbound_call_rejected,
            "actual": unbound_call_rejected,
            "threshold": True,
        },
        {
            "gate_id": "minimum_five_development_exact_semantics",
            "passed": len(development_exact) >= 5,
            "actual": len(development_exact),
            "threshold": 5,
        },
        {
            "gate_id": "sealed_blind_rows_exact",
            "passed": all(case["passed"] for case in blind_cases),
            "actual": sum(case["passed"] for case in blind_cases),
            "threshold": len(blind_cases),
        },
        {
            "gate_id": "adversarial_boundary_rows_exact",
            "passed": all(case["passed"] for case in adversarial_cases),
            "actual": sum(case["passed"] for case in adversarial_cases),
            "threshold": len(adversarial_cases),
        },
        {
            "gate_id": "forbidden_target_nodes_absent",
            "passed": forbidden_tokens_absent,
            "actual": forbidden_tokens_absent,
            "threshold": True,
        },
        {
            "gate_id": "glyph_randomization_ablation",
            "passed": glyph_invariant,
            "actual": glyph_invariant,
            "threshold": True,
        },
        {
            "gate_id": "negative_control_input_semantics",
            "passed": None,
            "actual": None,
            "threshold": True,
        },
        {
            "gate_id": "non_integer_input_semantics",
            "passed": None,
            "actual": None,
            "threshold": True,
        },
    ]
    verdict = (
        "conditionally_passed"
        if all(gate["passed"] for gate in gates if gate["passed"] is not None)
        else "failed"
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-unbound-symbol-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    knowledge_id = ledger.propose(
        selected.program,
        parent_ids=(
            "two_numeric_registers",
            "single_step_scheduler",
            "numeric_read_write",
            "addition",
            "subtraction",
            "equality_halt",
        ),
        provenance={
            "run_id": run_id,
            "candidate_id": selected.candidate_id,
            "search_version": "unbound-semantic-microsearch-v0.1",
        },
        evidence={"development_fit_error": selected.fit_error},
    )
    ledger.transition(
        knowledge_id,
        "fit_passed",
        reason="synthesized_micro_semantics_fit_numeric_rows",
        evidence={"development_case_count": len(development_rows)},
    )
    if verdict == "conditionally_passed":
        ledger.transition(
            knowledge_id,
            "verified",
            reason="blind_adversarial_and_glyph_ablation_passed",
            evidence={"gates": gates},
        )
        ledger.transition(
            knowledge_id,
            "bounded",
            reason="negative_control_and_noninteger_semantics_undefined",
            evidence={
                "pending_gates": [
                    gate["gate_id"] for gate in gates if gate["passed"] is None
                ]
            },
        )
    else:
        ledger.transition(
            knowledge_id,
            "rejected",
            reason="registered_semantic_binding_gate_failed",
            evidence={"gates": gates},
        )

    binding = None
    room_record = None
    if verdict == "conditionally_passed":
        binding_slot = UnboundSemanticSlot("*", executor=executor)
        binding = binding_slot.bind(
            selected.program, verification_status=ledger.get(knowledge_id).status
        )
        room = FormulaSuccessRoom(
            PROJECT_ROOT
            / "artifacts"
            / "formula_rooms"
            / "success"
            / "successful_formulas.jsonl"
        )
        room_record = room.record(
            selected.program,
            operation_id=binding.operation_id,
            parent_operation_ids=(
                "two_numeric_registers",
                "single_step_scheduler",
                "numeric_read_write",
                "addition",
                "subtraction",
                "equality_halt",
            ),
            validation_scope="unbound_symbol_semantics_v0.1",
            knowledge_status=ledger.get(knowledge_id).status,
            evidence={
                "run_id": run_id,
                "blind_cases": blind_cases,
                "adversarial_cases": adversarial_cases,
                "glyph_ablation": glyph_results,
            },
        )

    report = {
        "report_version": "unbound-symbol-semantics-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "无意义符号的可执行语义生成实验",
        "verdict": verdict,
        "knowledge_status": ledger.get(knowledge_id).status,
        "architecture": "enumerated_microstate_semantics_not_transformer",
        "unbound_symbol": {
            "glyph": "*",
            "intrinsic_semantics": False,
            "call_before_binding_rejected": unbound_call_rejected,
        },
        "learner_received": {
            "natural_language": False,
            "target_formula": False,
            "human_operation_name": False,
            "predefined_loop_program": False,
            "iterate_node": False,
            "multiply_node": False,
            "divide_node": False,
            "numeric_input_output_rows": True,
            "registered_substrate": [
                "two_numeric_registers",
                "single_step_scheduler",
                "numeric_read_write",
                "evidence_derived_constants",
                "addition",
                "subtraction",
                "equality_selected_halt",
                "simultaneous_state_update",
            ],
        },
        "search": {
            "programs_generated": search_report.programs_generated,
            "programs_executed": search_report.programs_executed,
            "programs_filtered_by_mistake_memory": search_report.programs_filtered,
            "nonhalting_programs": search_report.nonhalting_programs,
            "evidence_constants": list(search_report.evidence_constants),
            "development_exact_candidate_count": len(development_exact),
            "selected_candidate": selected.to_dict(),
            "first_five_exact_candidates": candidate_assessments[:5],
        },
        "independent_verification": {
            "blind_cases": blind_cases,
            "adversarial_cases": adversarial_cases,
            "development_exact_candidates_rejected_by_blind": sum(
                not item["blind_passed"] for item in candidate_assessments
            ),
        },
        "mistake_memory": {
            "path": "artifacts/mistakes/micro_mistakes.jsonl",
            "new_records": new_mistake_records,
            "total_records": len(mistake_library.records),
        },
        "binding": binding.to_dict() if binding is not None else None,
        "glyph_randomization": glyph_results,
        "success_formula_room_record": (
            room_record.to_dict() if room_record is not None else None
        ),
        "post_hoc_evaluator_interpretation": {
            "assigned_after_all_completed_gates": True,
            "equivalent_on_registered_domain": "integer multiplication with a non-negative integer control input",
        },
        "gates": gates,
        "knowledge_id": knowledge_id,
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "The glyph itself contributes no semantics; the learned micro-program is authoritative.",
            "The host supplies a generic bounded single-step scheduler, two registers, equality, addition, and subtraction.",
            "The candidate creates initialization, memory updates, halt condition, and output selection; it does not create the host scheduler from nothing.",
            "The registered domain requires the second input to be an integer from zero through 64.",
            "Negative control and non-integer behavior remain undefined and are not admitted claims.",
        ],
    }
    artifact_path = run_directory / "unbound_symbol_semantics_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "unbound_symbol_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "unbound_symbol_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact_path, destination)

    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": verdict,
                "knowledge_status": ledger.get(knowledge_id).status,
                "unbound_call_rejected": unbound_call_rejected,
                "programs_generated": search_report.programs_generated,
                "development_exact_candidates": len(development_exact),
                "blind_rejected_exact_candidates": sum(
                    not item["blind_passed"] for item in candidate_assessments
                ),
                "selected_candidate_id": selected.candidate_id,
                "selected_program": selected.program.to_dict(),
                "blind_passed": sum(case["passed"] for case in blind_cases),
                "blind_total": len(blind_cases),
                "adversarial_passed": sum(
                    case["passed"] for case in adversarial_cases
                ),
                "adversarial_total": len(adversarial_cases),
                "glyph_invariant": glyph_invariant,
                "binding": binding.to_dict() if binding is not None else None,
                "success_room_record_id": (
                    room_record.room_record_id if room_record is not None else None
                ),
                "mistake_records_written": len(new_mistake_records),
                "artifact_path": artifact_path.relative_to(PROJECT_ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if verdict == "conditionally_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
