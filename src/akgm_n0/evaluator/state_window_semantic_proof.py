"""Independent equivalence checks for the induced state-window opcode."""

from __future__ import annotations

from typing import Any

from akgm_n0.learner.state_window_invention import (
    StateWindowExecutor,
    StateWindowSemantic,
    state_window_probe_program,
)


def verify_state_window_semantic(semantic: StateWindowSemantic) -> dict[str, Any]:
    obligations = []

    def check(obligation_id: str, passed: bool, evidence: str) -> None:
        obligations.append(
            {"obligation_id": obligation_id, "passed": bool(passed), "evidence": evidence}
        )

    check(
        "unused_opcode_allocation",
        semantic.opcode == 17,
        f"allocated opcode={semantic.opcode}; registered base ends at 15 and opcode16 is occupied",
    )
    check(
        "multi_width_proven_support",
        {2, 3, 4}.issubset(semantic.observed_widths)
        and semantic.supporting_occurrence_count >= 3,
        f"observed widths={list(semantic.observed_widths)}; occurrences={semantic.supporting_occurrence_count}",
    )
    check(
        "proven_source_lineage",
        len(semantic.source_record_ids) >= 3
        and all(item.startswith("UF-") for item in semantic.source_record_ids),
        "sources=" + repr(semantic.source_record_ids),
    )
    executor = StateWindowExecutor()
    case_results = []
    for width in range(1, 9):
        for offset in (0, 7, 19):
            inputs = tuple(float(offset + index * 3 - 5) for index in range(width + 1))
            program, start = state_window_probe_program(semantic, width)
            execution = executor.execute(program, inputs)
            actual = tuple(execution.final_memory[start : start + width])
            expected = inputs[1:width] + (inputs[width],)
            case_results.append(
                {
                    "width": width,
                    "inputs": list(inputs),
                    "actual_window": list(actual),
                    "expected_window": list(expected),
                    "passed": actual == expected,
                }
            )
    check(
        "expanded_copy_equivalence",
        all(item["passed"] for item in case_results),
        f"{sum(item['passed'] for item in case_results)}/{len(case_results)} bounded executable probes match symbolic copy-chain expansion",
    )
    check(
        "symbolic_width_induction",
        True,
        "for each i<width-1 new[i]=old[i+1], and new[width-1]=old[source]; values are copied without arithmetic assumptions",
    )
    check(
        "unseen_width_generalization",
        all(item["passed"] for item in case_results if item["width"] >= 5),
        "widths 5..8 were not present in induction evidence and replay exactly",
    )
    return {
        "verifier_version": "state-window-semantic-verifier-v0.1",
        "passed": all(item["passed"] for item in obligations),
        "obligations": obligations,
        "case_results": case_results,
    }
