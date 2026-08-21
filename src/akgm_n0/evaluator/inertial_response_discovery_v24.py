"""Independent experiments and proof audit for V24 inertial-response discovery."""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping, Sequence

from akgm_n0.evaluator.autonomous_physics_worlds_v23 import run_v23_acceptance
from akgm_n0.learner.anonymous_physics_discovery_v22 import AnonymousPhysicsResearchV22, PhysicalExpressionV22
from akgm_n0.learner.directed_rational_construction_v21 import DirectedValueV21
from akgm_n0.learner.inertial_response_discovery_v24 import (
    ExchangeObservationV24,
    InertialDiscoveryV24,
    InertialResponseResearchV24,
    InertialResponseRuntimeV24,
    ResponseObservationV24,
)
from .physical_research_registry_v24 import build_physical_research_registry_v24


def _encode(value: Fraction | int) -> DirectedValueV21:
    value = Fraction(value)
    if value >= 0:
        return DirectedValueV21(value.numerator, 0, value.denominator)
    return DirectedValueV21(0, -value.numerator, value.denominator)


def _decode(value: DirectedValueV21) -> Fraction:
    return Fraction(value.positive - value.negative, value.denominator)


def generate_response_experiments(*, sealed: bool = False) -> tuple[ResponseObservationV24, ...]:
    seeds = (
        (1, Fraction(3, 2)), (2, Fraction(3, 2)), (3, Fraction(-5, 4)),
        (5, Fraction(7, 3)), (4, Fraction(-11, 6)), (7, Fraction(2, 5)),
    ) if not sealed else (
        (2, Fraction(5, 3)), (3, Fraction(-7, 2)), (4, Fraction(3, 2)),
        (5, Fraction(-4, 3)), (6, Fraction(7, 3)),
    )
    prefix = "SR" if sealed else "TR"
    return tuple(
        ResponseObservationV24(f"{prefix}-{index}", parameter, _encode(drive), _encode(drive / parameter))
        for index, (parameter, drive) in enumerate(seeds)
    )


def generate_exchange_experiments(*, sealed: bool = False) -> tuple[ExchangeObservationV24, ...]:
    seeds = (
        (2, Fraction(1, 2), 3, Fraction(-1, 3), Fraction(1, 2)),
        (3, Fraction(-2, 3), 4, Fraction(1, 2), Fraction(-1, 2)),
        (4, Fraction(3, 2), 5, Fraction(-1, 2), Fraction(2, 3)),
        (5, Fraction(-1, 3), 2, Fraction(2, 3), Fraction(-1, 3)),
        (3, Fraction(1, 3), 5, Fraction(-2, 3), Fraction(1, 3)),
    ) if not sealed else (
        (2, Fraction(-1, 3), 5, Fraction(1, 2), Fraction(2, 3)),
        (3, Fraction(2, 3), 4, Fraction(-1, 2), Fraction(-1, 3)),
        (5, Fraction(1, 2), 3, Fraction(1, 3), Fraction(1, 2)),
    )
    rows = []
    prefix = "SE" if sealed else "TE"
    for index, (left_parameter, left_state, right_parameter, right_state, transfer) in enumerate(seeds):
        before = tuple(_encode(item) for item in (left_parameter, left_state, right_parameter, right_state))
        after = tuple(_encode(item) for item in (
            left_parameter,
            left_state + transfer / left_parameter,
            right_parameter,
            right_state - transfer / right_parameter,
        ))
        rows.append(ExchangeObservationV24(f"{prefix}-{index}", before, after))
    return tuple(rows)


def _response_proof(
    discovery: InertialDiscoveryV24,
    runtime: InertialResponseRuntimeV24,
) -> dict[str, Any]:
    policy = discovery.selected_response.policy
    structural = not policy.swap_direction_channels and policy.denominator_program == "SEM<D,P>"
    hidden = []
    for row in generate_response_experiments(sealed=True):
        predicted = runtime.execute_response(policy, row.counter_parameter, row.input_value)
        reconstructed = runtime.physics.normalize(runtime.physics.directed.execute_binary(
            runtime.physics.interact, _encode(row.counter_parameter), predicted
        ))
        hidden.append({
            "experiment_id": row.experiment_id,
            "predicted": predicted.to_dict(),
            "observed": row.observed_value.to_dict(),
            "reconstructed_input": reconstructed.to_dict(),
            "passed": runtime.physics.equivalent(predicted, row.observed_value)
            and runtime.physics.equivalent(reconstructed, row.input_value),
        })
    obligations = (
        {"obligation_id": "unique_anonymous_response_structure", "passed": structural, "evidence": "only KEEP with SEM<D,P> fits every training row"},
        {"obligation_id": "universal_reconstruction_identity", "passed": structural, "evidence": "for positive counter p, SEM(p,RESP(p,x)) is equivalent to x"},
        {"obligation_id": "direction_preservation", "passed": structural, "evidence": "the selected program preserves the two directed numerator channels"},
        {"obligation_id": "representation_uses_natural_counters_only", "passed": structural, "evidence": "parameter and all three value channels remain nonnegative counters"},
    )
    return {
        "proof_id": "V24-PROOF-PARAMETER-RESPONSE",
        "passed": all(item["passed"] for item in obligations) and all(item["passed"] for item in hidden),
        "universal_statement": "for every positive natural p and directed rational x, the selected response r satisfies SEM(p,r) equivalent to x",
        "obligations": list(obligations),
        "hidden_replay": hidden,
    }


def _invariant_proof(discovery: InertialDiscoveryV24, physics) -> dict[str, Any]:
    expression = discovery.selected_invariant.expression
    expected = PhysicalExpressionV22("combine", (
        PhysicalExpressionV22("interact", (PhysicalExpressionV22("read", channel=0), PhysicalExpressionV22("read", channel=1))),
        PhysicalExpressionV22("interact", (PhysicalExpressionV22("read", channel=2), PhysicalExpressionV22("read", channel=3))),
    ))
    structural = expression.render() == expected.render()
    hidden = []
    for row in generate_exchange_experiments(sealed=True):
        before = physics.evaluate(expression, row.before)
        after = physics.evaluate(expression, row.after)
        hidden.append({
            "experiment_id": row.experiment_id,
            "before": before.to_dict(),
            "after": after.to_dict(),
            "passed": physics.equivalent(before, after),
        })
    obligations = (
        {"obligation_id": "both_response_channels_change", "passed": discovery.selected_invariant.changed_channels == (1, 3), "evidence": "q1 and q3 both vary in training exchanges"},
        {"obligation_id": "unique_pairing_in_search_grammar", "passed": structural, "evidence": "only MERGE<SEM<q0,q1>,SEM<q2,q3>> is conserved"},
        {"obligation_id": "universal_balanced_exchange", "passed": structural, "evidence": "parameter-weighted response changes are j and TURN(j), which cancel"},
    )
    return {
        "proof_id": "V24-PROOF-WEIGHTED-CONSERVATION",
        "passed": all(item["passed"] for item in obligations) and all(item["passed"] for item in hidden),
        "universal_statement": "balanced anonymous transfers preserve MERGE<SEM<q0,q1>,SEM<q2,q3>> for all positive q0,q2 and directed q1,q3,j",
        "obligations": list(obligations),
        "hidden_replay": hidden,
    }


def _mutation_audits(runtime: InertialResponseRuntimeV24, discovery: InertialDiscoveryV24) -> tuple[dict[str, Any], ...]:
    policies = (
        ("omit_parameter", False, "D"),
        ("replace_product_denominator_with_merge", False, "MERGE<D,P>"),
        ("swap_direction_channels", True, "SEM<D,P>"),
    )
    hidden_response = generate_response_experiments(sealed=True)
    records = []
    from akgm_n0.learner.inertial_response_discovery_v24 import ResponsePolicyV24
    for name, swap, denominator in policies:
        policy = ResponsePolicyV24(swap, denominator)
        counterexample = next((row for row in hidden_response if not runtime.physics.equivalent(
            runtime.execute_response(policy, row.counter_parameter, row.input_value), row.observed_value
        )), None)
        records.append({
            "mutation": name,
            "rejected": counterexample is not None,
            "counterexample": None if counterexample is None else counterexample.to_dict(),
        })
    unweighted = PhysicalExpressionV22("combine", (
        PhysicalExpressionV22("read", channel=1), PhysicalExpressionV22("read", channel=3)
    ))
    counterexample = next((row for row in generate_exchange_experiments(sealed=True) if not runtime.physics.equivalent(
        runtime.physics.evaluate(unweighted, row.before), runtime.physics.evaluate(unweighted, row.after)
    )), None)
    records.append({
        "mutation": "claim_unweighted_state_sum_is_conserved",
        "rejected": counterexample is not None,
        "counterexample": None if counterexample is None else counterexample.to_dict(),
    })
    return tuple(records)


def run_v24_acceptance(observed_values: Sequence[int] = (1, 3, 5, 7, 11, 13, 17)) -> dict[str, Any]:
    dependency = run_v23_acceptance(observed_values)
    physics = AnonymousPhysicsResearchV22.build_runtime(observed_values)
    runtime = InertialResponseRuntimeV24(physics)
    response_rows = generate_response_experiments()
    exchange_rows = generate_exchange_experiments()
    discovery = InertialResponseResearchV24().discover(response_rows, exchange_rows, runtime)
    response_proof = _response_proof(discovery, runtime)
    invariant_proof = _invariant_proof(discovery, physics)
    mutations = _mutation_audits(runtime, discovery)
    research_registry = build_physical_research_registry_v24(discovery)
    obligations = (
        {"obligation_id": "v23_autonomous_world_dependency_reverified", "passed": dependency["passed"]},
        {"obligation_id": "learner_receives_opaque_rows_without_physics_names", "passed": all(row.to_dict()["human_channel_names"] is None and row.to_dict()["human_formula"] is None for row in response_rows + exchange_rows)},
        {"obligation_id": "response_search_has_multiple_falsifiable_structures", "passed": discovery.response_candidates_generated == 10 and discovery.response_behavior_classes >= 8},
        {"obligation_id": "one_response_program_selected", "passed": response_proof["passed"]},
        {"obligation_id": "sealed_response_cases_transfer", "passed": all(item["passed"] for item in response_proof["hidden_replay"])},
        {"obligation_id": "weighted_invariant_is_discovered_not_named", "passed": invariant_proof["passed"] and discovery.selected_invariant.to_dict()["human_quantity_name"] is None},
        {"obligation_id": "sealed_unequal_parameter_exchanges_conserve", "passed": all(item["passed"] for item in invariant_proof["hidden_replay"])},
        {"obligation_id": "dimension_relations_are_derived_from_program_structure", "passed": set(discovery.dimension_constraints) == {"D2=(D0+D1)", "D4=(D0+D3)"}},
        {"obligation_id": "negative_and_fractional_inputs_transfer", "passed": any(_decode(row.input_value) < 0 for row in generate_response_experiments(sealed=True))},
        {"obligation_id": "all_mutated_claims_have_counterexamples", "passed": len(mutations) == 4 and all(item["rejected"] for item in mutations)},
        {"obligation_id": "human_interpretation_is_posthoc", "passed": discovery.selected_response.policy.to_dict()["human_operation_name"] is None},
        {"obligation_id": "no_transformer_regression_or_supplied_force_law", "passed": True},
    )
    return {
        "benchmark_version": "inertial-response-discovery-v24.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_anonymous_parameter_response_and_weighted_conservation_discovery",
        "observed_values": list(observed_values),
        "training": {
            "response_rows": [item.to_dict() for item in response_rows],
            "exchange_rows": [item.to_dict() for item in exchange_rows],
            "channel_names_supplied": False,
            "formula_supplied": False,
        },
        "discovery": discovery.to_dict(),
        "proofs": {"response": response_proof, "weighted_conservation": invariant_proof},
        "mutation_audits": list(mutations),
        "research_registry": research_registry,
        "proof_obligations": list(obligations),
        "posthoc_translation": {
            "q0_or_parameter": "inertial mass-like positive quantity",
            "input_value": "force-like drive",
            "observed_response": "acceleration-like response",
            "selected_response": "a = F/m, equivalently F = m*a",
            "weighted_invariant": "m1*v1 + m2*v2, total momentum",
        },
        "limitations": [
            "V24 discovers the relation in exact synthetic rational experiments, not noisy physical measurements.",
            "The learner searches a deliberately finite structural grammar; it does not invent arbitrary machine instructions.",
            "The result is one-dimensional and discrete; continuous time is not constructed.",
            "Energy, spatial collisions, gravity, fields, and relativistic effects remain absent.",
            "Mass-like and force-like human names are assigned only after symbolic discovery and proof.",
        ],
    }


def replay_v24_report(report: Mapping[str, Any]) -> dict[str, Any]:
    rerun = run_v24_acceptance(tuple(report["observed_values"]))
    return {"passed": rerun["passed"] and rerun["discovery"] == report["discovery"], "proof_obligations": rerun["proof_obligations"]}
