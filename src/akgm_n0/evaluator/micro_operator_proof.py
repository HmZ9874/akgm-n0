"""Independent replay proof for induced straight-line micro-operators."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from akgm_n0.learner.metamachine_gen2 import (
    OP_ADD_CELL,
    OP_ADD_IMMEDIATE,
    OP_ADD_INPUT,
    OP_LOAD_CELL,
    OP_LOAD_INPUT,
    OP_SET,
    OP_STORE_CELL,
    OP_SUB_CELL,
    OP_SUB_IMMEDIATE,
    OP_SUB_INPUT,
)
from akgm_n0.learner.micro_operator_mining import (
    InducedMicroOperator,
    MicroOperatorExecutor,
)


def verify_micro_operator(operator: InducedMicroOperator) -> dict[str, Any]:
    """Compare the compiled effect with a separate instruction-by-instruction VM."""
    probes = _hidden_probes()
    cases = []
    for index, (cells, inputs, immediates) in enumerate(probes):
        expected = _reference_execute(operator, cells, inputs, immediates)
        try:
            actual = MicroOperatorExecutor().execute(
                operator, cells=cells, inputs=inputs, immediates=immediates
            )
            passed = actual == expected
            error = None
        except Exception as exc:  # verifier reports malformed semantics as evidence
            actual = None
            passed = False
            error = type(exc).__name__ + ": " + str(exc)
        cases.append(
            {
                "case_id": f"PROBE-{index:02d}",
                "passed": passed,
                "expected_cells": list(expected),
                "actual_cells": None if actual is None else list(actual),
                "error": error,
            }
        )

    recomputed_signature = operator.target_token + "=" + json.dumps(
        operator.effect_ast, sort_keys=True, separators=(",", ":")
    )
    payload = {
        "opcode": operator.opcode,
        "instructions": [item.to_dict() for item in operator.normalized_instructions],
        "effect": operator.effect_ast,
        "sources": list(operator.source_record_ids),
        "occurrences": operator.supporting_occurrence_count,
    }
    recomputed_id = "SEM-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    obligations = [
        {
            "obligation_id": "effect_signature_binding",
            "passed": recomputed_signature == operator.effect_signature,
            "evidence": recomputed_signature,
        },
        {
            "obligation_id": "operator_id_binding",
            "passed": recomputed_id == operator.operator_id,
            "evidence": recomputed_id,
        },
        {
            "obligation_id": "multi_program_support",
            "passed": len(set(operator.source_record_ids)) >= 2,
            "evidence": f"{len(set(operator.source_record_ids))} independently proven source programs",
        },
        {
            "obligation_id": "repeated_occurrence_support",
            "passed": operator.supporting_occurrence_count >= 2,
            "evidence": f"{operator.supporting_occurrence_count} source occurrences",
        },
        {
            "obligation_id": "expanded_replay_equivalence",
            "passed": all(item["passed"] for item in cases),
            "evidence": f"{sum(item['passed'] for item in cases)}/{len(cases)} hidden numeric probes",
        },
    ]
    return {
        "verifier_version": "independent-micro-operator-verifier-v0.1",
        "operator_id": operator.operator_id,
        "passed": all(item["passed"] for item in obligations),
        "obligations": obligations,
        "cases": cases,
    }


def verify_micro_operator_batch(
    operators: Sequence[InducedMicroOperator], *, required_count: int = 10
) -> dict[str, Any]:
    results = [verify_micro_operator(operator) for operator in operators]
    batch_obligations = [
        {
            "obligation_id": "exact_discovery_count",
            "passed": len(operators) == required_count,
            "actual": len(operators),
            "required": required_count,
        },
        {
            "obligation_id": "unique_effects",
            "passed": len({item.effect_signature for item in operators}) == len(operators),
            "actual": len({item.effect_signature for item in operators}),
            "required": required_count,
        },
        {
            "obligation_id": "unique_fresh_opcodes",
            "passed": [item.opcode for item in operators] == list(range(18, 18 + required_count)),
            "actual": [item.opcode for item in operators],
            "required": list(range(18, 18 + required_count)),
        },
        {
            "obligation_id": "all_individual_proofs_pass",
            "passed": all(item["passed"] for item in results),
            "actual": sum(item["passed"] for item in results),
            "required": required_count,
        },
    ]
    return {
        "verifier_version": "independent-micro-operator-batch-verifier-v0.1",
        "required_count": required_count,
        "passed": all(item["passed"] for item in batch_obligations),
        "batch_obligations": batch_obligations,
        "operator_results": results,
        "probe_case_count": sum(len(item["cases"]) for item in results),
        "passed_probe_case_count": sum(
            sum(case["passed"] for case in item["cases"]) for item in results
        ),
    }


def _reference_execute(
    operator: InducedMicroOperator,
    cells: Sequence[float],
    inputs: Sequence[float],
    immediates: Sequence[float],
) -> tuple[float, ...]:
    memory = [float(value) for value in cells]
    accumulator = 0.0
    for instruction in operator.normalized_instructions:
        opcode = instruction.opcode
        token = instruction.operand_token
        kind, raw_index = token.split(":", 1)
        index = int(raw_index)
        if kind == "cell":
            value = memory[index]
        elif kind == "input":
            value = float(inputs[index])
        elif kind == "immediate":
            value = float(immediates[index])
        else:
            raise ValueError("unknown normalized operand kind")
        if opcode in (OP_LOAD_CELL, OP_LOAD_INPUT, OP_SET):
            accumulator = value
        elif opcode in (OP_ADD_CELL, OP_ADD_INPUT, OP_ADD_IMMEDIATE):
            accumulator += value
        elif opcode in (OP_SUB_CELL, OP_SUB_INPUT, OP_SUB_IMMEDIATE):
            accumulator -= value
        elif opcode == OP_STORE_CELL:
            if kind != "cell":
                raise ValueError("store target must be a cell")
            memory[index] = accumulator
        else:
            raise ValueError(f"unsupported source opcode: {opcode}")
    return tuple(memory)


def _hidden_probes() -> tuple[tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]], ...]:
    return (
        ((0, 0, 0, 0), (0, 0), (0, 0)),
        ((1, 2, 3, 4), (5, 6), (7, 8)),
        ((-1, -2, -3, -4), (-5, -6), (-7, -8)),
        ((10, -3, 8, 2), (-11, 9), (4, -12)),
        ((-2.5, 0.25, 7.75, -9.5), (1.5, -4.25), (3.125, -0.5)),
        ((101, -37, 19, -5), (23, -41), (-17, 29)),
        ((1e6, -1e6, 0.5, -0.5), (3, -3), (11, -11)),
        ((0.125, 0.25, 0.5, 1.0), (2.0, 4.0), (8.0, 16.0)),
        ((13, 13, -13, -13), (13, -13), (0, 1)),
        ((999, 1, -999, -1), (1001, -1001), (2, -2)),
        ((3.5, -7.25, 11.125, -15.0625), (-19.5, 23.75), (27.25, -31.5)),
        ((42, 17, 8, 31), (56, 23), (64, 11)),
    )

