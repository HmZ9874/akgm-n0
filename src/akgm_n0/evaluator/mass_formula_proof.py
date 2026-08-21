"""Independent exact proof gates for a large parametric formula batch."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Sequence

from akgm_n0.learner.operator_evolution import EvolvedMicroOperator

from .evolved_operator_proof import verify_evolved_operator_batch


FORMULA_COUNT = 1000
FIRST_OPCODE = 132


def semantic_normal_form(operator: EvolvedMicroOperator) -> str:
    """Return the role-sensitive algebraic meaning, not the program spelling."""

    return json.dumps(
        {
            "target": operator.target_token,
            "operands": list(operator.operand_tokens),
            "integer_coefficients": list(operator.coefficient_vector),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def formula_id(operator: EvolvedMicroOperator) -> str:
    return "PF-" + hashlib.sha256(semantic_normal_form(operator).encode()).hexdigest()[:16]


def structural_logic_signature(operator: EvolvedMicroOperator) -> str:
    return json.dumps(
        [item.to_dict() for item in operator.normalized_instructions],
        sort_keys=True,
        separators=(",", ":"),
    )


def verify_mass_formula_batch(
    operators: Sequence[EvolvedMicroOperator],
    *,
    prior_coefficient_vectors: Sequence[Sequence[int]],
    required_count: int = FORMULA_COUNT,
    first_opcode: int = FIRST_OPCODE,
) -> dict[str, Any]:
    """Prove exact semantics and enforce novelty/parameterization gates."""

    exact = verify_evolved_operator_batch(
        operators,
        required_count=required_count,
        first_opcode=first_opcode,
    )
    prior = {tuple(int(value) for value in item) for item in prior_coefficient_vectors}
    normal_forms = [semantic_normal_form(item) for item in operators]
    structural_signatures = [structural_logic_signature(item) for item in operators]
    batch_vectors = [item.coefficient_vector for item in operators]
    all_tokens_are_runtime_roles = all(
        all(token.startswith(("cell:", "input:", "immediate:")) for token in item.operand_tokens)
        for item in operators
    )
    all_multi_variable = all(
        sum(coefficient != 0 for coefficient in item.coefficient_vector) >= 2
        for item in operators
    )
    obligations = [
        {
            "obligation_id": "exact_thousand_stop_count",
            "passed": len(operators) == required_count,
            "actual": len(operators),
            "required": required_count,
        },
        {
            "obligation_id": "unique_semantic_normal_forms",
            "passed": len(set(normal_forms)) == required_count,
            "actual": len(set(normal_forms)),
            "required": required_count,
        },
        {
            "obligation_id": "unique_minimal_program_structures",
            "passed": len(set(structural_signatures)) == required_count,
            "actual": len(set(structural_signatures)),
            "required": required_count,
        },
        {
            "obligation_id": "cross_generation_novelty",
            "passed": not any(tuple(item) in prior for item in batch_vectors),
            "actual": sum(tuple(item) in prior for item in batch_vectors),
            "required": 0,
        },
        {
            "obligation_id": "all_symbols_are_free_runtime_variables",
            "passed": all_tokens_are_runtime_roles,
            "actual": all_tokens_are_runtime_roles,
            "required": True,
        },
        {
            "obligation_id": "all_formulas_depend_on_multiple_variables",
            "passed": all_multi_variable,
            "actual": sum(
                sum(value != 0 for value in item.coefficient_vector) >= 2
                for item in operators
            ),
            "required": required_count,
        },
        {
            "obligation_id": "generation_three_binding",
            "passed": all(item.generation == 3 for item in operators),
            "actual": sorted({item.generation for item in operators}),
            "required": [3],
        },
        {
            "obligation_id": "all_exact_symbolic_proofs_and_replays_pass",
            "passed": exact["passed"],
            "actual": sum(item["passed"] for item in exact["operator_results"]),
            "required": required_count,
        },
    ]
    return {
        "verifier_version": "independent-mass-parametric-formula-verifier-v0.1",
        "passed": all(item["passed"] for item in obligations),
        "formal_domain": "all assignments of the free roles in any additive abelian group; numeric executor probes use finite real values",
        "proof_method": "structural induction over load/add/subtract/store plus exact integer coefficient normalization",
        "finite_sampling_used_as_universal_proof": False,
        "obligations": obligations,
        "formula_proof_count": sum(item["passed"] for item in exact["operator_results"]),
        "formula_count": len(exact["operator_results"]),
        "hidden_replay_passed_count": exact["passed_probe_case_count"],
        "hidden_replay_count": exact["probe_case_count"],
        "operator_results": exact["operator_results"],
    }

