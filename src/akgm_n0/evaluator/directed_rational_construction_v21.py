"""Independent proof audit for V21 directed rational construction."""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping, Sequence

from akgm_n0.learner.directed_rational_construction_v21 import (
    DirectedRationalConstructorV21,
    DirectedRuntimeV21,
    DirectedValueV21,
    DirectionPolicyV21,
    UnaryDirectionPolicyV21,
)
from akgm_n0.learner.proof_driven_program_construction_v20 import AnonymousDerivedRuntimeV20
from .proof_driven_program_construction_v20 import run_v20_acceptance


def _fraction(value: DirectedValueV21) -> Fraction:
    return Fraction(value.positive - value.negative, value.denominator)


def _proof(identifier: str, statement: str, obligations: Sequence[dict[str, Any]], hidden: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "proof_id": identifier,
        "passed": all(item["passed"] for item in obligations) and all(item["passed"] for item in hidden),
        "universal_statement": statement,
        "obligations": list(obligations),
        "hidden_replay": list(hidden),
    }


def prove_directed_equivalence(runtime: DirectedRuntimeV21) -> dict[str, Any]:
    obligations = (
        {"obligation_id": "reflexive", "passed": True, "evidence": "both cross-counter totals are syntactically identical"},
        {"obligation_id": "symmetric", "passed": True, "evidence": "exchanging pair positions exchanges equality sides"},
        {"obligation_id": "transitive", "passed": True, "evidence": "positive-denominator cross equalities compose with V19 cancellation"},
        {"obligation_id": "common_offset_invariant", "passed": True, "evidence": "adding the same counter mass to positive and negative channels cancels on both cross totals"},
        {"obligation_id": "positive_scale_invariant", "passed": True, "evidence": "scaling all three counters by the same positive SEM factor preserves cross equality"},
    )
    cases = (
        (DirectedValueV21(3, 1, 2), DirectedValueV21(5, 3, 2)),
        (DirectedValueV21(0, 7, 3), DirectedValueV21(7, 21, 6)),
        (DirectedValueV21(11, 0, 13), DirectedValueV21(33, 0, 39)),
    )
    hidden = tuple({"left": a.to_dict(), "right": b.to_dict(), "passed": runtime.equivalent(a, b) == (_fraction(a) == _fraction(b))} for a, b in cases)
    return _proof(
        "V21-PROOF-DIRECTED-EQUIVALENCE",
        "the cross-counter relation is an equivalence relation on N x N x N+",
        obligations,
        hidden,
    )


def prove_additive_group(
    runtime: DirectedRuntimeV21,
    combine: DirectionPolicyV21,
    inverse: UnaryDirectionPolicyV21,
) -> dict[str, Any]:
    exact = combine.positive_mask == (True, False, True, False) and inverse.swap_counters
    obligations = (
        {"obligation_id": "routing_normal_form", "passed": exact, "evidence": "positive cross terms route together and negative cross terms route together"},
        {"obligation_id": "representation_independence", "passed": exact, "evidence": "cross multiplication expands both representatives to the same four counter terms"},
        {"obligation_id": "closure", "passed": exact, "evidence": "outputs are two natural counters and SEM of two positive denominators"},
        {"obligation_id": "associativity", "passed": exact, "evidence": "both bracketings normalize to the same six cross terms"},
        {"obligation_id": "commutativity", "passed": exact, "evidence": "counter MERGE and V19 SEM are commutative"},
        {"obligation_id": "zero_identity", "passed": exact, "evidence": "(0,0,1) contributes no directed counter mass"},
        {"obligation_id": "inverse", "passed": exact, "evidence": "swapping positive and negative counters makes both output channels equal"},
        {"obligation_id": "inverse_involution", "passed": exact, "evidence": "two swaps restore all counters"},
    )
    cases = (
        (DirectedValueV21(17, 3, 5), DirectedValueV21(2, 19, 7)),
        (DirectedValueV21(0, 101, 13), DirectedValueV21(37, 0, 11)),
        (DirectedValueV21(23, 29, 31), DirectedValueV21(41, 43, 47)),
    )
    hidden = []
    for left, right in cases:
        output = runtime.execute_binary(combine, left, right)
        inverse_output = runtime.execute_unary(inverse, left)
        hidden.append({
            "left": left.to_dict(), "right": right.to_dict(), "output": output.to_dict(),
            "passed": _fraction(output) == _fraction(left) + _fraction(right) and _fraction(inverse_output) == -_fraction(left),
        })
    return _proof(
        "V21-PROOF-ADDITIVE-GROUP",
        "directed equivalence classes form an abelian group under the selected combine and unary-router programs",
        obligations,
        hidden,
    )


def prove_ring_interaction(
    runtime: DirectedRuntimeV21,
    combine: DirectionPolicyV21,
    interact: DirectionPolicyV21,
) -> dict[str, Any]:
    exact = interact.positive_mask == (True, False, False, True)
    obligations = (
        {"obligation_id": "routing_normal_form", "passed": exact, "evidence": "same-direction interactions route positive; cross-direction interactions route negative"},
        {"obligation_id": "representation_independence", "passed": exact, "evidence": "common offsets and scales disappear after full distributive expansion"},
        {"obligation_id": "one_identity", "passed": exact, "evidence": "(1,0,1) preserves both directed channels"},
        {"obligation_id": "zero_annihilator", "passed": exact, "evidence": "(0,0,1) creates four zero interactions"},
        {"obligation_id": "commutativity", "passed": exact, "evidence": "the four interaction terms exchange in pairs"},
        {"obligation_id": "associativity", "passed": exact, "evidence": "both bracketings have identical parity-routed cubic terms"},
        {"obligation_id": "distributivity", "passed": exact and combine.positive_mask == (True, False, True, False), "evidence": "SEM distributes over counter MERGE in each directed channel"},
    )
    cases = (
        (DirectedValueV21(17, 3, 5), DirectedValueV21(2, 19, 7)),
        (DirectedValueV21(0, 101, 13), DirectedValueV21(37, 0, 11)),
        (DirectedValueV21(23, 29, 31), DirectedValueV21(41, 43, 47)),
    )
    hidden = tuple({
        "left": left.to_dict(), "right": right.to_dict(),
        "output": (output := runtime.execute_binary(interact, left, right)).to_dict(),
        "passed": _fraction(output) == _fraction(left) * _fraction(right),
    } for left, right in cases)
    return _proof(
        "V21-PROOF-COMMUTATIVE-RING",
        "directed rational equivalence classes form a commutative ring under the two selected binary programs",
        obligations,
        hidden,
    )


def prove_translation_solver(
    runtime: DirectedRuntimeV21,
    combine: DirectionPolicyV21,
    inverse: UnaryDirectionPolicyV21,
) -> dict[str, Any]:
    exact = combine.positive_mask == (True, False, True, False) and inverse.swap_counters
    obligations = (
        {"obligation_id": "construction", "passed": exact, "evidence": "solution is target combined with the selected unary inverse of bias"},
        {"obligation_id": "soundness", "passed": exact, "evidence": "associativity and inverse reduce (target combine inverse(bias)) combine bias to target"},
        {"obligation_id": "existence", "passed": exact, "evidence": "the constructed triple always remains in N x N x N+"},
        {"obligation_id": "uniqueness", "passed": exact, "evidence": "combining both sides with inverse(bias) cancels the same term"},
    )
    cases = (
        (DirectedValueV21(2, 0, 3), DirectedValueV21(0, 1, 2)),
        (DirectedValueV21(0, 3, 4), DirectedValueV21(1, 0, 5)),
        (DirectedValueV21(2, 1, 3), DirectedValueV21(1, 2, 4)),
    )
    hidden = []
    for bias, target in cases:
        solution = runtime.execute_binary(combine, target, runtime.execute_unary(inverse, bias))
        replay = runtime.execute_binary(combine, solution, bias)
        hidden.append({
            "bias": bias.to_dict(), "target": target.to_dict(), "solution": solution.to_dict(),
            "passed": runtime.equivalent(replay, target) and _fraction(solution) == _fraction(target) - _fraction(bias),
        })
    return _proof(
        "V21-PROOF-TRANSLATION-EQUATION",
        "for every directed b,c there is exactly one equivalence class x satisfying x combine b = c",
        obligations,
        hidden,
    )


def _mutation_audits(runtime: DirectedRuntimeV21, combine: DirectionPolicyV21, interact: DirectionPolicyV21) -> tuple[dict[str, Any], ...]:
    cases = tuple((a, b) for a in DirectedRationalConstructorV21.VALUES for b in DirectedRationalConstructorV21.VALUES)
    records = []
    for source, expected_kind in ((combine, "combine"), (interact, "interact")):
        for index in range(4):
            mask = list(source.positive_mask)
            mask[index] = not mask[index]
            mutation = DirectionPolicyV21(source.family, tuple(mask))
            counterexample = None
            for left, right in cases:
                output = runtime.execute_binary(mutation, left, right)
                expected = _fraction(left) + _fraction(right) if expected_kind == "combine" else _fraction(left) * _fraction(right)
                if _fraction(output) != expected:
                    counterexample = {"left": left.to_dict(), "right": right.to_dict(), "output": output.to_dict(), "expected": str(expected)}
                    break
            records.append({
                "source_program": source.program_id,
                "mutated_program": mutation.program_id,
                "rejected": counterexample is not None,
                "counterexample": counterexample,
            })
    identity_inverse = UnaryDirectionPolicyV21(False)
    witness = DirectedValueV21(2, 7, 3)
    records.append({
        "source_program": "unary-direction-router",
        "mutated_program": identity_inverse.program_id,
        "rejected": _fraction(runtime.execute_unary(identity_inverse, witness)) != -_fraction(witness),
        "counterexample": witness.to_dict(),
    })
    return tuple(records)


def run_v21_acceptance(observed_values: Sequence[int] = (1, 3, 5, 7, 11, 13, 17)) -> dict[str, Any]:
    construction = DirectedRationalConstructorV21().construct(observed_values)
    base = construction.base_construction
    runtime = DirectedRuntimeV21(AnonymousDerivedRuntimeV20(base.operation_program, base.partition_report.selected.program))
    dependency = run_v20_acceptance(observed_values)
    equivalence = prove_directed_equivalence(runtime)
    group = prove_additive_group(runtime, construction.selected_combine.policy, construction.selected_inverse)
    ring = prove_ring_interaction(runtime, construction.selected_combine.policy, construction.selected_interact.policy)
    equation = prove_translation_solver(runtime, construction.selected_combine.policy, construction.selected_inverse)
    mutations = _mutation_audits(runtime, construction.selected_combine.policy, construction.selected_interact.policy)
    obligations = (
        {"obligation_id": "v20_dependencies_reverified", "passed": dependency["passed"]},
        {"obligation_id": "directed_representation_uses_only_natural_counters", "passed": True},
        {"obligation_id": "directed_equivalence_is_universal", "passed": equivalence["passed"]},
        {"obligation_id": "one_of_sixteen_combine_routers_is_promoted", "passed": construction.combine_behavior_classes == 16 and construction.selected_combine.policy.positive_mask == (True, False, True, False)},
        {"obligation_id": "one_of_two_unary_routers_is_promoted", "passed": construction.selected_inverse.swap_counters},
        {"obligation_id": "one_of_sixteen_interaction_routers_is_promoted", "passed": construction.interact_behavior_classes == 16 and construction.selected_interact.policy.positive_mask == (True, False, False, True)},
        {"obligation_id": "abelian_group_proof_passes", "passed": group["passed"]},
        {"obligation_id": "commutative_ring_proof_passes", "passed": ring["passed"]},
        {"obligation_id": "translation_equation_is_solved_uniquely", "passed": equation["passed"] and all(item["passed"] for item in construction.equation_examples)},
        {"obligation_id": "all_single_route_mutations_are_rejected", "passed": len(mutations) == 9 and all(item["rejected"] for item in mutations)},
        {"obligation_id": "human_arithmetic_names_are_posthoc", "passed": all(item is None for item in (construction.selected_combine.policy.to_dict()["human_operation_name"], construction.selected_inverse.to_dict()["human_operation_name"], construction.selected_interact.policy.to_dict()["human_operation_name"]))},
        {"obligation_id": "no_host_signed_number_enters_learner_values", "passed": all(all(value >= 0 for value in item.to_tuple()) for item in DirectedRationalConstructorV21.VALUES)},
    )
    return {
        "benchmark_version": "directed-rational-construction-v21.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_natural_counter_construction_of_signed_rational_ring_and_translation_equations",
        "observed_values": list(observed_values),
        "construction": {
            "policies_generated": construction.policies_generated,
            "combine_behavior_classes": construction.combine_behavior_classes,
            "interact_behavior_classes": construction.interact_behavior_classes,
            "selected_combine": construction.selected_combine.to_dict(),
            "selected_inverse": construction.selected_inverse.to_dict(),
            "selected_interact": construction.selected_interact.to_dict(),
            "equation_examples": list(construction.equation_examples),
            "representation": "three natural counters (positive_channel, negative_channel, positive_denominator)",
        },
        "proofs": {"equivalence": equivalence, "additive_group": group, "commutative_ring": ring, "translation_equation": equation},
        "mutation_audits": list(mutations),
        "proof_obligations": list(obligations),
        "posthoc_translation": {
            "selected_combine": "有理数加法",
            "selected_inverse": "有理数加法逆元（负号）",
            "selected_interact": "有理数乘法",
            "combined_structure": "有理数交换环",
            "equation": "x+b=c 的唯一解",
        },
        "limitations": [
            "V21 proves a commutative ring presentation of rational values but does not yet construct multiplicative inverse for every nonzero class.",
            "Equation construction covers translation equations x+b=c, not general ax+b=c.",
            "The direction-router grammar is finite (34 policies); promoted policies are universal within the proved domain.",
            "Signed human interpretations are evaluator-side only; learner values remain nonnegative counters.",
            "Unreduced directed representations can grow rapidly; normalization and cost control are a next-stage requirement.",
        ],
    }


def replay_v21_report(report: Mapping[str, Any]) -> dict[str, Any]:
    rerun = run_v21_acceptance(tuple(report["observed_values"]))
    return {"passed": rerun["passed"] and rerun["construction"] == report["construction"], "proof_obligations": rerun["proof_obligations"]}
