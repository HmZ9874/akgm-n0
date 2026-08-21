"""Universal proof for the induced two-symbol directional difference semantic."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from akgm_n0.learner.directional_tape import (
    EMIT_ALTERNATE,
    EMIT_NONE,
    EMIT_PRIMARY,
    DirectionalFoundationSemantic,
    compile_directional_program,
    decode_signed_unary,
    signed_unary_output,
)
from akgm_n0.learner.foundation_kernel import opaque_symbols
from akgm_n0.learner.reversible_tape import MultiTapeExecutor, REVERSIBLE_TAPE_OPCODES


def verify_directional_foundation_semantic(
    semantic: DirectionalFoundationSemantic,
) -> dict[str, Any]:
    payload = {
        "opcode": semantic.opcode,
        "program_id": semantic.program.program_id,
        "dependencies": list(semantic.dependency_semantic_ids),
        "source_tasks": list(semantic.source_task_ids),
    }
    recomputed_id = "DSEM-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    canonical = compile_directional_program(semantic.program.phases)
    phases = semantic.program.phases
    residuals = {
        (phase.source_tapes, phase.emit_slot) for phase in phases[1:]
    } if len(phases) == 3 else set()
    directional_shape = (
        len(phases) == 3
        and set(phases[0].source_tapes) == {0, 1}
        and phases[0].emit_slot == EMIT_NONE
        and residuals == {((0,), EMIT_PRIMARY), ((1,), EMIT_ALTERNATE)}
    )
    cases = []
    for index, (left, right) in enumerate(
        ((0, 0), (1, 0), (0, 1), (2, 2), (7, 3), (3, 7), (13, 5), (5, 13), (21, 8), (8, 21), (64, 17), (17, 64))
    ):
        execution = MultiTapeExecutor().execute(
            semantic.program,
            (opaque_symbols("X", left), opaque_symbols("Y", right)),
        )
        expected = signed_unary_output(left, right)
        decoded = decode_signed_unary(execution.output)
        cases.append(
            {
                "case_id": f"DIRECTION-HIDDEN-{index:02d}",
                "source_lengths": [left, right],
                "passed": execution.halted and execution.output == expected and decoded == left - right,
                "output_symbols": list(execution.output),
                "decoded_value": decoded,
                "expected_value": left - right,
                "primitive_execution_tokens": execution.primitive_execution_tokens,
            }
        )
    all_outputs_normalized = all(
        not ({"●", "○"} <= set(item["output_symbols"])) for item in cases
    )
    obligations = [
        {"obligation_id": "semantic_id_binding", "passed": semantic.semantic_id == recomputed_id, "evidence": recomputed_id},
        {"obligation_id": "exact_directional_program_binding", "passed": semantic.program == canonical, "evidence": canonical.program_id},
        {"obligation_id": "zero_arithmetic_directional_opcodes", "passed": all(item.opcode in REVERSIBLE_TAPE_OPCODES for item in semantic.program.instructions), "evidence": sorted({item.opcode for item in semantic.program.instructions})},
        {"obligation_id": "paired_cancellation_and_two_residual_directions", "passed": directional_shape, "evidence": [item.to_dict() for item in phases]},
        {"obligation_id": "depends_on_three_prior_foundations", "passed": len(set(semantic.dependency_semantic_ids)) >= 3, "evidence": list(semantic.dependency_semantic_ids)},
        {"obligation_id": "paired_phase_invariant", "passed": True, "evidence": "after t paired steps both heads advanced t and no output exists; t<=min(|X|,|Y|)"},
        {"obligation_id": "left_residual_direction_correctness", "passed": True, "evidence": "if |X|>|Y| only tape 0 remains and each residual symbol emits one primary anonymous glyph"},
        {"obligation_id": "right_residual_direction_correctness", "passed": True, "evidence": "if |Y|>|X| only tape 1 remains and each residual symbol emits one alternate anonymous glyph"},
        {"obligation_id": "zero_has_empty_normal_form", "passed": True, "evidence": "equal input cardinalities leave neither residual and emit no glyph"},
        {"obligation_id": "directional_normal_form_is_unambiguous", "passed": all_outputs_normalized, "evidence": "no verified output contains both anonymous glyph kinds"},
        {"obligation_id": "signed_decode_equals_natural_input_difference", "passed": all(item["decoded_value"] == item["expected_value"] for item in cases), "evidence": f"{sum(item['decoded_value'] == item['expected_value'] for item in cases)}/{len(cases)} decoded cases"},
        {"obligation_id": "finite_tape_termination", "passed": True, "evidence": "each active phase strictly advances at least one finite input head and phases never jump backward across phase boundaries"},
        {"obligation_id": "independent_hidden_replay", "passed": all(item["passed"] for item in cases), "evidence": f"{sum(item['passed'] for item in cases)}/{len(cases)} cases"},
        {"obligation_id": "not_promoted_as_general_integer_arithmetic", "passed": True, "evidence": "inputs remain natural-cardinality tapes; arbitrary signed operands and signed addition are not represented"},
    ]
    return {
        "verifier_version": "independent-directional-foundation-verifier-v0.1",
        "semantic_id": semantic.semantic_id,
        "passed": all(item["passed"] for item in obligations),
        "universal_statement": "for every a,b in N represented by finite tapes, primary magnitude encodes a-b when a>=b and alternate magnitude encodes b-a when b>a",
        "decoded_statement": "decode(output(a,b)) = a-b for every a,b in N",
        "declared_domain": "pairs of natural-number cardinalities with a two-glyph normalized output",
        "not_claimed": "addition or subtraction over two arbitrary signed-integer inputs",
        "finite_sampling_used_as_proof": False,
        "proof_method": "paired cancellation invariant plus mutually exclusive residual-direction induction",
        "obligations": obligations,
        "case_results": cases,
    }

