"""Independent structural and replay proof for generation-two operators."""

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
from akgm_n0.learner.operator_evolution import (
    EvolvedMicroOperator,
    EvolvedMicroOperatorExecutor,
)


def verify_evolved_operator(operator: EvolvedMicroOperator) -> dict[str, Any]:
    instruction_vector = _instruction_vector(operator)
    ast_vector = _ast_vector(operator.effect_ast, operator.operand_tokens)
    recomputed_signature = operator.target_token + "=" + ",".join(
        f"{token}:{coefficient}"
        for token, coefficient in zip(
            operator.operand_tokens, operator.coefficient_vector, strict=True
        )
    )
    payload = {
        "opcode": operator.opcode,
        "instructions": [item.to_dict() for item in operator.normalized_instructions],
        "target": operator.target_token,
        "operands": list(operator.operand_tokens),
        "coefficients": list(operator.coefficient_vector),
        "seed_library_digest": operator.seed_library_digest,
        "generation": operator.generation,
    }
    recomputed_id = "ESEM-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]

    cases = []
    for index, (cells, inputs, immediates) in enumerate(_hidden_probes()):
        expected = _reference_execute(operator, cells, inputs, immediates)
        try:
            actual = EvolvedMicroOperatorExecutor().execute(
                operator, cells=cells, inputs=inputs, immediates=immediates
            )
            passed = actual == expected
            error = None
        except Exception as exc:
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

    obligations = [
        {
            "obligation_id": "instruction_symbolic_vector_binding",
            "passed": instruction_vector == operator.coefficient_vector,
            "evidence": list(instruction_vector),
        },
        {
            "obligation_id": "effect_ast_symbolic_vector_binding",
            "passed": ast_vector == operator.coefficient_vector,
            "evidence": list(ast_vector),
        },
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
            "obligation_id": "nontrivial_multi_operand_effect",
            "passed": sum(value != 0 for value in operator.coefficient_vector) >= 2,
            "evidence": list(operator.coefficient_vector),
        },
        {
            "obligation_id": "compressed_expansion_is_shorter",
            "passed": len(operator.normalized_instructions) > 1,
            "evidence": f"{len(operator.normalized_instructions)} source instructions -> 1 opcode",
        },
        {
            "obligation_id": "independent_numeric_replay",
            "passed": all(case["passed"] for case in cases),
            "evidence": f"{sum(case['passed'] for case in cases)}/{len(cases)} probes",
        },
    ]
    return {
        "verifier_version": "independent-evolved-operator-verifier-v0.1",
        "operator_id": operator.operator_id,
        "passed": all(item["passed"] for item in obligations),
        "obligations": obligations,
        "cases": cases,
    }


def verify_evolved_operator_batch(
    operators: Sequence[EvolvedMicroOperator],
    *,
    required_count: int = 100,
    first_opcode: int = 28,
) -> dict[str, Any]:
    results = [verify_evolved_operator(operator) for operator in operators]
    obligations = [
        {
            "obligation_id": "exact_hundred_stop_count",
            "passed": len(operators) == required_count,
            "actual": len(operators),
            "required": required_count,
        },
        {
            "obligation_id": "hundred_unique_algebraic_effects",
            "passed": len({item.coefficient_vector for item in operators}) == required_count,
            "actual": len({item.coefficient_vector for item in operators}),
            "required": required_count,
        },
        {
            "obligation_id": "fresh_opcode_range",
            "passed": [item.opcode for item in operators]
            == list(range(first_opcode, first_opcode + required_count)),
            "actual": [item.opcode for item in operators],
            "required": list(range(first_opcode, first_opcode + required_count)),
        },
        {
            "obligation_id": "all_structural_and_replay_proofs_pass",
            "passed": all(item["passed"] for item in results),
            "actual": sum(item["passed"] for item in results),
            "required": required_count,
        },
    ]
    return {
        "verifier_version": "independent-evolved-operator-batch-verifier-v0.1",
        "required_count": required_count,
        "passed": all(item["passed"] for item in obligations),
        "batch_obligations": obligations,
        "operator_results": results,
        "probe_case_count": sum(len(item["cases"]) for item in results),
        "passed_probe_case_count": sum(
            sum(case["passed"] for case in item["cases"]) for item in results
        ),
    }


def _instruction_vector(operator: EvolvedMicroOperator) -> tuple[int, ...]:
    coefficients = {token: 0 for token in operator.operand_tokens}
    started = False
    for index, instruction in enumerate(operator.normalized_instructions):
        opcode, token = instruction.opcode, instruction.operand_token
        if opcode in (OP_LOAD_CELL, OP_LOAD_INPUT, OP_SET):
            if index != 0 or token not in coefficients:
                return ()
            coefficients = {item: 0 for item in operator.operand_tokens}
            coefficients[token] = 1
            started = True
        elif opcode in (OP_ADD_CELL, OP_ADD_INPUT, OP_ADD_IMMEDIATE):
            if not started or token not in coefficients:
                return ()
            coefficients[token] += 1
        elif opcode in (OP_SUB_CELL, OP_SUB_INPUT, OP_SUB_IMMEDIATE):
            if not started or token not in coefficients:
                return ()
            coefficients[token] -= 1
        elif opcode == OP_STORE_CELL:
            if index != len(operator.normalized_instructions) - 1:
                return ()
            if token != operator.target_token:
                return ()
        else:
            return ()
    return tuple(coefficients[token] for token in operator.operand_tokens)


def _ast_vector(
    node: Mapping[str, Any], tokens: Sequence[str]
) -> tuple[int, ...]:
    coefficients = {token: 0 for token in tokens}

    def walk(current: Mapping[str, Any], sign: int = 1) -> None:
        if current.get("op") == "token":
            token = str(current.get("token"))
            if token not in coefficients:
                raise ValueError("effect AST uses an undeclared operand token")
            coefficients[token] += sign
            return
        left, right = current["args"]
        walk(left, sign)
        walk(right, sign if current["op"] == "add" else -sign)

    try:
        walk(node)
    except (KeyError, TypeError, ValueError):
        return ()
    return tuple(coefficients[token] for token in tokens)


def _reference_execute(
    operator: EvolvedMicroOperator,
    cells: Sequence[float],
    inputs: Sequence[float],
    immediates: Sequence[float],
) -> tuple[float, ...]:
    memory = [float(value) for value in cells]
    accumulator = 0.0
    for instruction in operator.normalized_instructions:
        kind, raw = instruction.operand_token.split(":", 1)
        index = int(raw)
        value = {
            "cell": memory,
            "input": inputs,
            "immediate": immediates,
        }[kind][index]
        opcode = instruction.opcode
        if opcode in (OP_LOAD_CELL, OP_LOAD_INPUT, OP_SET):
            accumulator = float(value)
        elif opcode in (OP_ADD_CELL, OP_ADD_INPUT, OP_ADD_IMMEDIATE):
            accumulator += float(value)
        elif opcode in (OP_SUB_CELL, OP_SUB_INPUT, OP_SUB_IMMEDIATE):
            accumulator -= float(value)
        elif opcode == OP_STORE_CELL:
            memory[index] = accumulator
        else:
            raise ValueError("unsupported expansion opcode")
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
