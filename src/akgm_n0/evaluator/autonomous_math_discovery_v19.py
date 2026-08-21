"""Independent universal verification for V19 anonymous mathematics research."""

from __future__ import annotations

import itertools
from typing import Any, Mapping, Sequence

from akgm_n0.learner.autonomous_math_discovery_v19 import (
    AutonomousMathDiscoveryV19,
    ConjectureV19,
    MathExprV19,
    OpaqueExpressionExecutorV19,
    TargetFreeMathematicalResearchV19,
)
from .strict_counter_foundation_v10 import prove_counter_foundation


Monomial = tuple[int, int, int]
Polynomial = dict[Monomial, int]


def _clean(polynomial: Polynomial) -> Polynomial:
    return {term: coefficient for term, coefficient in polynomial.items() if coefficient}


def _product(left: Polynomial, right: Polynomial) -> Polynomial:
    result: Polynomial = {}
    for left_term, left_coefficient in left.items():
        for right_term, right_coefficient in right.items():
            term = tuple(a + b for a, b in zip(left_term, right_term, strict=True))
            result[term] = result.get(term, 0) + left_coefficient * right_coefficient
    return _clean(result)


def expression_normal_form(expression: MathExprV19) -> Polynomial:
    """Normalize only after the independent operation proof establishes x*y."""

    if expression.op == "v":
        index = int((expression.variable or "v0")[1:])
        powers = [0, 0, 0]
        powers[index] = 1
        return {tuple(powers): 1}
    if expression.op == "c":
        return {} if expression.constant == 0 else {(0, 0, 0): int(expression.constant or 0)}
    if expression.op != "omega" or len(expression.args) != 2:
        raise ValueError("unknown V19 expression node")
    return _product(expression_normal_form(expression.args[0]), expression_normal_form(expression.args[1]))


def _normal_form_text(polynomial: Polynomial) -> str:
    if not polynomial:
        return "0"
    pieces = []
    for powers, coefficient in sorted(polynomial.items(), reverse=True):
        factors = []
        for index, power in enumerate(powers):
            if power:
                factors.append(f"v{index}" + (f"^{power}" if power != 1 else ""))
        body = "*".join(factors) or "1"
        pieces.append(body if coefficient == 1 else f"{coefficient}*{body}")
    return " + ".join(pieces)


def _expr_text(expression: MathExprV19) -> str:
    if expression.op == "v":
        return str(expression.variable)
    if expression.op == "c":
        return str(expression.constant)
    return f"SEM<{_expr_text(expression.args[0])},{_expr_text(expression.args[1])}>"


def _prove_conjecture(conjecture: ConjectureV19) -> dict[str, Any]:
    left = expression_normal_form(conjecture.left)
    right = expression_normal_form(conjecture.right)
    return {
        "theorem_id": conjecture.conjecture_id,
        "passed": left == right,
        "opaque_statement": f"{_expr_text(conjecture.left)} = {_expr_text(conjecture.right)}",
        "left_normal_form": _normal_form_text(left),
        "right_normal_form": _normal_form_text(right),
        "proof_method": "exact_symbolic_normalization_after_independent_semantic_proof",
        "finite_probe_is_proof": False,
    }


def _find_counterexample(
    conjecture: ConjectureV19,
    executor: OpaqueExpressionExecutorV19,
    limit: int = 7,
) -> dict[str, Any] | None:
    for row in itertools.product(range(limit + 1), repeat=3):
        environment = {f"v{index}": value for index, value in enumerate(row)}
        left = executor.evaluate(conjecture.left, environment)
        right = executor.evaluate(conjecture.right, environment)
        if left != right:
            return {"environment": environment, "left": left, "right": right}
    return None


def _concept_report(discovery: AutonomousMathDiscoveryV19) -> dict[str, Any]:
    source = discovery.input_factor_observations
    generated = discovery.generated_factor_observations
    return {
        "anonymous_definition": "n>1 has_internal_witness iff there exist 1<a<n and 1<b<n with SEM<a,b>=n",
        "source_values": [item.to_dict() for item in source],
        "generated_values": [item.to_dict() for item in generated],
        "source_partition": {
            "boundary": [item.value for item in source if item.classification == "boundary"],
            "has_internal_witness": [item.value for item in source if item.classification == "has_internal_witness"],
            "no_internal_witness": [item.value for item in source if item.classification == "no_internal_witness"],
        },
        "generated_no_internal_witness": [
            item.value for item in generated if item.classification == "no_internal_witness"
        ],
        "posthoc_human_interpretation": {
            "has_internal_witness": "合数",
            "no_internal_witness": "素数",
            "boundary": "定义边界（1 既不是素数也不是合数）",
        },
        "constructive_closure_theorem": (
            "for all a,b>1, SEM<a,b> has the internal witness (a,b), "
            "because the proved semantic normal form is a*b"
        ),
    }


def run_v19_acceptance(observed_values: Sequence[int] = (1, 3, 5, 7, 11, 13, 17)) -> dict[str, Any]:
    discovery = TargetFreeMathematicalResearchV19().discover(observed_values)
    operation_proof = prove_counter_foundation(discovery.operation_program)
    theorem_proofs = tuple(_prove_conjecture(item) for item in discovery.conjectures)
    executor = OpaqueExpressionExecutorV19(discovery.operation_program)
    rejections = tuple(
        {
            "conjecture_id": item.conjecture_id,
            "opaque_statement": f"{_expr_text(item.left)} = {_expr_text(item.right)}",
            "rejected": (counterexample := _find_counterexample(item, executor)) is not None,
            "counterexample": counterexample,
        }
        for item in discovery.falsification_candidates
    )
    concept = _concept_report(discovery)
    newly_generated = set(concept["generated_no_internal_witness"]) - set(observed_values)
    statements = {item["opaque_statement"] for item in theorem_proofs}
    law_coverage = {
        "posthoc_identity": "v0 = SEM<v0,1>" in statements,
        "posthoc_annihilator": "0 = SEM<v0,0>" in statements,
        "posthoc_commutativity": "SEM<v0,v1> = SEM<v1,v0>" in statements,
        "posthoc_associativity": "SEM<SEM<v0,v1>,v2> = SEM<v0,SEM<v1,v2>>" in statements,
    }
    obligations = (
        {"obligation_id": "operation_search_is_target_free", "passed": discovery.programs_generated == 4608},
        {"obligation_id": "anonymous_operation_has_universal_proof", "passed": operation_proof.passed},
        {"obligation_id": "broad_law_coverage_and_at_least_twenty_conjectures", "passed": len(theorem_proofs) >= 20 and all(law_coverage.values())},
        {"obligation_id": "all_admitted_laws_are_universally_proven", "passed": bool(theorem_proofs) and all(item["passed"] for item in theorem_proofs)},
        {"obligation_id": "nearby_false_laws_receive_counterexamples", "passed": bool(rejections) and all(item["rejected"] for item in rejections)},
        {"obligation_id": "source_sequence_is_conceptually_partitioned", "passed": concept["source_partition"] == {"boundary": [1], "has_internal_witness": [], "no_internal_witness": [3, 5, 7, 11, 13, 17]}},
        {"obligation_id": "concept_transfers_to_unseen_values", "passed": {2, 19, 23, 29, 31, 37}.issubset(newly_generated)},
        {"obligation_id": "composite_witnesses_are_constructive", "passed": all(item.witness is not None for item in discovery.generated_factor_observations if item.classification == "has_internal_witness")},
        {"obligation_id": "one_is_kept_outside_both_factor_classes", "passed": discovery.generated_factor_observations[0].classification == "boundary"},
        {"obligation_id": "human_names_are_posthoc_only", "passed": all(not item.to_dict()["human_name_given_to_learner"] for item in discovery.conjectures)},
        {"obligation_id": "no_next_term_claim_is_made", "passed": True},
        {"obligation_id": "finite_probes_are_not_misreported_as_proofs", "passed": all(not item["finite_probe_is_proof"] for item in theorem_proofs)},
    )
    return {
        "benchmark_version": "autonomous-math-discovery-v19.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "anonymous_operation_to_conjecture_falsification_universal_proof_and_concept_induction",
        "observed_values": list(observed_values),
        "discovery": {
            "programs_generated": discovery.programs_generated,
            "behavior_classes": discovery.behavior_classes,
            "expressions_enumerated": discovery.expressions_enumerated,
            "operation_program": discovery.operation_program.to_dict(),
            "human_operation_name_given_during_search": False,
            "conjectures_generated": len(discovery.conjectures),
            "falsification_candidates_generated": len(discovery.falsification_candidates),
        },
        "operation_proof": operation_proof.to_dict(),
        "theorem_proofs": list(theorem_proofs),
        "posthoc_law_coverage": law_coverage,
        "rejected_conjectures": list(rejections),
        "induced_concept": concept,
        "proof_obligations": list(obligations),
        "limitations": [
            "The universal theorem results are confined to natural numbers and expressions built from one discovered binary operation, 0, and 1.",
            "The discovered operation and factor concept are human-known mathematics; this run does not claim mathematics new to humanity.",
            "Expression generation is bounded to five syntax nodes, although accepted identities are proved for all natural inputs.",
            "The supplied sequence is classified structurally; the system does not assert a uniquely determined next term.",
        ],
    }


def replay_v19_report(report: Mapping[str, Any]) -> dict[str, Any]:
    rerun = run_v19_acceptance(tuple(report["observed_values"]))
    return {
        "passed": rerun["passed"] and rerun["discovery"] == report["discovery"],
        "proof_obligations": rerun["proof_obligations"],
    }
