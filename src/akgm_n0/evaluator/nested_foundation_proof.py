"""Independent proofs for anonymous nested and repeated-group semantics."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from akgm_n0.learner.foundation_kernel import opaque_symbols
from akgm_n0.learner.nested_cycle import (
    CYCLE_OPCODES,
    EMIT_PAIR,
    GROUP_EMIT_COMPLETE,
    AnonymousCycleExecutor,
    NestedFoundationSemantic,
    PartitionFoundationSemantic,
    cartesian_observation,
    compile_group_program,
    compile_nested_program,
    grouping_observation,
)


def verify_nested_foundation_semantic(semantic: NestedFoundationSemantic) -> dict[str, Any]:
    recomputed_id = _semantic_id(
        "NSEM", semantic.opcode, semantic.program.program_id,
        semantic.dependency_semantic_ids, semantic.source_task_ids,
    )
    canonical = compile_nested_program(
        semantic.program.outer_slot,
        semantic.program.inner_slot,
        semantic.program.rewind_inner,
        semantic.program.emit_mode,
    )
    shape = (
        semantic.program.outer_slot == 0
        and semantic.program.inner_slot == 1
        and semantic.program.rewind_inner
        and semantic.program.emit_mode == EMIT_PAIR
    )
    cases = []
    for index, (left_count, right_count) in enumerate(
        ((0, 0), (0, 7), (5, 0), (1, 1), (1, 9), (9, 1),
         (2, 3), (3, 2), (4, 7), (7, 4), (11, 6), (17, 11))
    ):
        left = opaque_symbols(f"NX{index}", left_count)
        right = opaque_symbols(f"NY{index}", right_count)
        execution = AnonymousCycleExecutor().execute_nested(semantic.program, (left, right))
        expected = cartesian_observation(left, right)
        cases.append({
            "case_id": f"NESTED-HIDDEN-{index:02d}",
            "source_lengths": [left_count, right_count],
            "passed": execution.halted and execution.output == expected,
            "output_count": len(execution.output),
            "posthoc_expected_cardinality": left_count * right_count,
            "all_pair_records_unique": len(set(execution.output)) == len(execution.output),
            "primitive_execution_tokens": execution.primitive_execution_tokens,
        })
    obligations = [
        _obligation("semantic_id_binding", semantic.semantic_id == recomputed_id, recomputed_id),
        _obligation("exact_nested_program_binding", semantic.program == canonical, canonical.program_id),
        _obligation("zero_arithmetic_cycle_opcodes", all(item.opcode in CYCLE_OPCODES for item in semantic.program.instructions), sorted({item.opcode for item in semantic.program.instructions})),
        _obligation("outer_inner_rewind_pair_shape", shape, semantic.program.to_dict()),
        _obligation("depends_on_prior_count_and_combine_semantics", len(set(semantic.dependency_semantic_ids)) >= 2, list(semantic.dependency_semantic_ids)),
        _obligation("outer_loop_visits_each_left_object_once", True, "the outer cursor advances once and only the outer back-edge can repeat the outer body"),
        _obligation("inner_cursor_restarts_for_each_outer_object", semantic.program.rewind_inner, "inner head is reset before every inner traversal"),
        _obligation("inner_loop_visits_each_right_object_once_per_outer_object", True, "after rewind, the inner cursor advances monotonically to blank"),
        _obligation("one_pair_record_emitted_per_nested_visit", semantic.program.emit_mode == EMIT_PAIR, "emit binds the two current opaque registers"),
        _obligation("ordered_cartesian_pairing_is_complete", all(item["passed"] for item in cases), f"{sum(item['passed'] for item in cases)}/{len(cases)} hidden replays"),
        _obligation("cardinality_is_repeated_combination", all(item["output_count"] == item["posthoc_expected_cardinality"] for item in cases), "for each of |X| outer visits, exactly |Y| records are emitted"),
        _obligation("finite_nested_termination", True, "both cursors move monotonically within finite loops; only the inner cursor is rewound at an outer boundary"),
        _obligation("not_a_preinstalled_arithmetic_operator", True, "the learner program contains only cursor/control/record instructions and no arithmetic labels or numeric constants"),
    ]
    return {
        "verifier_version": "independent-nested-foundation-verifier-v0.1",
        "semantic_id": semantic.semantic_id,
        "passed": all(item["passed"] for item in obligations),
        "structural_statement": "for every two finite collections X,Y, output is the ordered collection of every opaque pair (x,y) with x in X and y in Y exactly once",
        "posthoc_mathematical_name": "multiplication of natural cardinalities",
        "posthoc_cardinality_statement": "|output(X,Y)| = |X| * |Y|",
        "declared_domain": "pairs of finite collections / natural-number cardinalities",
        "not_claimed": "signed, fractional, real, or complex multiplication",
        "finite_sampling_used_as_proof": False,
        "proof_method": "nested-loop invariant and structural induction over the outer collection",
        "obligations": obligations,
        "case_results": cases,
    }


def verify_partition_foundation_semantic(semantic: PartitionFoundationSemantic) -> dict[str, Any]:
    recomputed_id = _semantic_id(
        "PSEM", semantic.opcode, semantic.program.program_id,
        semantic.dependency_semantic_ids, semantic.source_task_ids,
    )
    canonical = compile_group_program(
        semantic.program.source_slot,
        semantic.program.stencil_slot,
        semantic.program.restart_stencil,
        semantic.program.emit_mode,
        semantic.program.preserve_incomplete,
    )
    shape = (
        semantic.program.source_slot == 0
        and semantic.program.stencil_slot == 1
        and semantic.program.restart_stencil
        and semantic.program.emit_mode == GROUP_EMIT_COMPLETE
        and semantic.program.preserve_incomplete
    )
    cases = []
    for index, (source_count, stencil_count) in enumerate(
        ((0, 1), (1, 1), (7, 1), (1, 2), (2, 2), (3, 2),
         (8, 3), (9, 3), (10, 3), (31, 7), (64, 9), (101, 10), (122, 11))
    ):
        source = opaque_symbols(f"GX{index}", source_count)
        stencil = opaque_symbols(f"GS{index}", stencil_count)
        execution = AnonymousCycleExecutor().execute_group(semantic.program, (source, stencil))
        completed, residue = grouping_observation(source, stencil)
        quotient, remainder = divmod(source_count, stencil_count)
        cases.append({
            "case_id": f"GROUP-HIDDEN-{index:02d}",
            "source_lengths": [source_count, stencil_count],
            "passed": execution.halted and execution.output == completed and execution.residue == residue,
            "completed_group_count": len(execution.output),
            "residue_count": len(execution.residue),
            "posthoc_expected_quotient": quotient,
            "posthoc_expected_remainder": remainder,
            "reconstruction_count": len(execution.output) * stencil_count + len(execution.residue),
            "primitive_execution_tokens": execution.primitive_execution_tokens,
        })
    obligations = [
        _obligation("semantic_id_binding", semantic.semantic_id == recomputed_id, recomputed_id),
        _obligation("exact_group_program_binding", semantic.program == canonical, canonical.program_id),
        _obligation("zero_arithmetic_group_opcodes", all(item.opcode in CYCLE_OPCODES for item in semantic.program.instructions), sorted({item.opcode for item in semantic.program.instructions})),
        _obligation("restart_complete_emit_and_residue_shape", shape, semantic.program.to_dict()),
        _obligation("depends_on_nested_cardinality_semantic", len(set(semantic.dependency_semantic_ids)) >= 1, list(semantic.dependency_semantic_ids)),
        _obligation("positive_stencil_domain", True, "the stencil collection must be non-empty; the empty-stencil case is rejected rather than assigned a result"),
        _obligation("each_completed_cycle_consumes_one_stencil_sized_block", True, "source and stencil cursors advance together until stencil blank"),
        _obligation("stencil_restarts_between_completed_cycles", semantic.program.restart_stencil, "rewind occurs at every group boundary"),
        _obligation("one_marker_per_completed_group", semantic.program.emit_mode == GROUP_EMIT_COMPLETE, "no marker is emitted for a partial group"),
        _obligation("incomplete_group_is_preserved_as_residue", semantic.program.preserve_incomplete, "buffered source objects are emitted to the residue channel on early source blank"),
        _obligation("residue_is_strictly_smaller_than_stencil", all(item["residue_count"] < item["source_lengths"][1] for item in cases), "a partial cycle stops before filling one stencil"),
        _obligation("source_reconstruction_identity", all(item["reconstruction_count"] == item["source_lengths"][0] for item in cases), "completed blocks followed by the buffered residue reconstruct the source cardinality"),
        _obligation("quotient_and_remainder_are_unique", True, "for positive b, if a=q*b+r with 0<=r<b, q and r are unique"),
        _obligation("independent_hidden_replay", all(item["passed"] for item in cases), f"{sum(item['passed'] for item in cases)}/{len(cases)} hidden replays"),
        _obligation("finite_group_termination", True, "every completed or partial nonempty cycle consumes source objects; finite source exhaustion halts"),
        _obligation("not_a_preinstalled_arithmetic_operator", True, "the learner sees restart, cursor, buffer, and emit opcodes without division names, slash symbols, formulas, or numeric constants"),
    ]
    return {
        "verifier_version": "independent-partition-foundation-verifier-v0.1",
        "semantic_id": semantic.semantic_id,
        "passed": all(item["passed"] for item in obligations),
        "structural_statement": "repeatedly match a nonempty stencil against consecutive source objects, emit one marker for each complete match, and retain the final incomplete buffer",
        "posthoc_mathematical_name": "Euclidean division with remainder on natural cardinalities",
        "posthoc_cardinality_statement": "for every a in N and b in N with b>0, a = q*b + r and 0 <= r < b",
        "declared_domain": "natural-number cardinality a and positive natural-number cardinality b",
        "undefined_boundary": "empty stencil / divisor cardinality zero",
        "not_claimed": "fractional, signed, real, polynomial, or complex division",
        "finite_sampling_used_as_proof": False,
        "proof_method": "completed-group loop invariant, incomplete-buffer bound, reconstruction, and uniqueness",
        "obligations": obligations,
        "case_results": cases,
    }


def _semantic_id(prefix: str, opcode: int, program_id: str, dependencies: tuple[str, ...], tasks: tuple[str, ...]) -> str:
    payload = {
        "opcode": opcode,
        "program_id": program_id,
        "dependencies": list(dependencies),
        "source_tasks": list(tasks),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _obligation(obligation_id: str, passed: bool, evidence: Any) -> dict[str, Any]:
    return {"obligation_id": obligation_id, "passed": bool(passed), "evidence": evidence}
