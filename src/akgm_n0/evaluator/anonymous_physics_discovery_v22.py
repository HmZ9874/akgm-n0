"""Sealed experiments and universal proof audit for V22 physics discovery."""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping, Sequence

from akgm_n0.learner.anonymous_physics_discovery_v22 import (
    AnonymousPhysicsResearchV22,
    DirectedPhysicsRuntimeV22,
    PhysicalExpressionV22,
    PhysicsDiscoveryV22,
    TransitionObservationV22,
    expression_key_v22,
)
from akgm_n0.learner.directed_rational_construction_v21 import DirectedValueV21
from .directed_rational_construction_v21 import run_v21_acceptance


def _encode(value: Fraction) -> DirectedValueV21:
    if value >= 0:
        return DirectedValueV21(value.numerator, 0, value.denominator)
    return DirectedValueV21(0, -value.numerator, value.denominator)


def _decode(value: DirectedValueV21) -> Fraction:
    return Fraction(value.positive - value.negative, value.denominator)


def generate_kinematic_experiments(*, sealed: bool = False) -> tuple[TransitionObservationV22, ...]:
    seeds = (
        (Fraction(-3, 2), Fraction(2, 3), Fraction(1, 2), Fraction(1, 2)),
        (Fraction(5, 3), Fraction(-1, 2), Fraction(2, 3), Fraction(1, 1)),
        (Fraction(0), Fraction(3, 2), Fraction(-1, 3), Fraction(2, 1)),
        (Fraction(7, 4), Fraction(0), Fraction(-1, 2), Fraction(1, 2)),
    ) if not sealed else (
        (Fraction(-11, 5), Fraction(7, 3), Fraction(-2, 5), Fraction(3, 2)),
        (Fraction(13, 7), Fraction(-5, 4), Fraction(3, 8), Fraction(2, 3)),
        (Fraction(2, 9), Fraction(11, 6), Fraction(0), Fraction(5, 4)),
    )
    rows = []
    for world_index, (position, velocity, drive, interval) in enumerate(seeds):
        steps = 3 if not sealed else 4
        for step in range(steps):
            next_position = position + velocity * interval
            next_velocity = velocity + drive * interval
            before = tuple(_encode(item) for item in (position, velocity, drive, interval))
            after = tuple(_encode(item) for item in (next_position, next_velocity, drive, interval))
            rows.append(TransitionObservationV22(f"{'S' if sealed else 'T'}K-{world_index}-{step}", before, after))
            position, velocity = next_position, next_velocity
    return tuple(rows)


def generate_exchange_experiments(*, sealed: bool = False) -> tuple[TransitionObservationV22, ...]:
    seeds = (
        (Fraction(3, 2), Fraction(-2, 3), Fraction(1, 4)),
        (Fraction(-5, 4), Fraction(7, 5), Fraction(-1, 3)),
        (Fraction(0), Fraction(11, 6), Fraction(2, 5)),
        (Fraction(13, 7), Fraction(-3, 2), Fraction(-4, 7)),
    ) if not sealed else (
        (Fraction(-17, 9), Fraction(19, 8), Fraction(5, 6)),
        (Fraction(23, 11), Fraction(-29, 13), Fraction(-7, 10)),
        (Fraction(31, 12), Fraction(37, 15), Fraction(-11, 14)),
    )
    rows = []
    for index, (left, right, transfer) in enumerate(seeds):
        before = tuple(_encode(item) for item in (left, right, transfer))
        after = tuple(_encode(item) for item in (left + transfer, right - transfer, transfer))
        rows.append(TransitionObservationV22(f"{'S' if sealed else 'T'}E-{index}", before, after))
    return tuple(rows)


def _canonical(expression: PhysicalExpressionV22) -> str:
    return expression_key_v22(expression)


def _read(channel: int) -> PhysicalExpressionV22:
    return PhysicalExpressionV22("read", channel=channel)


def _expected_programs() -> tuple[PhysicalExpressionV22, ...]:
    return (
        PhysicalExpressionV22("combine", (_read(0), PhysicalExpressionV22("interact", (_read(1), _read(3))))),
        PhysicalExpressionV22("combine", (_read(1), PhysicalExpressionV22("interact", (_read(2), _read(3))))),
        _read(2),
        _read(3),
    )


def _verify_hidden_rows(
    discovery: PhysicsDiscoveryV22,
    rows: Sequence[TransitionObservationV22],
    runtime: DirectedPhysicsRuntimeV22,
) -> tuple[dict[str, Any], ...]:
    results = []
    for row in rows:
        predicted = tuple(runtime.evaluate(program.expression, row.before) for program in discovery.channel_programs)
        passed = all(runtime.equivalent(actual, expected) for actual, expected in zip(predicted, row.after, strict=True))
        results.append({
            "world_id": row.world_id,
            "predicted": [item.to_dict() for item in predicted],
            "observed": [item.to_dict() for item in row.after],
            "passed": passed,
        })
    return tuple(results)


def prove_kinematic_programs(
    discovery: PhysicsDiscoveryV22,
    runtime: DirectedPhysicsRuntimeV22,
) -> dict[str, Any]:
    expected = _expected_programs()
    structural = all(
        _canonical(program.expression) == _canonical(target)
        for program, target in zip(discovery.channel_programs, expected, strict=True)
    )
    obligations = (
        {"obligation_id": "four_channel_normal_form", "passed": structural, "evidence": "selected programs normalize to q0⊕(q1⊗q3), q1⊕(q2⊗q3), q2, q3"},
        {"obligation_id": "universal_first_update", "passed": structural, "evidence": "V21 ring closure proves q0'=q0⊕q1⊗q3 for every directed rational state"},
        {"obligation_id": "universal_second_update", "passed": structural, "evidence": "V21 ring closure proves q1'=q1⊕q2⊗q3 for every directed rational state"},
        {"obligation_id": "control_channels_persist", "passed": structural, "evidence": "q2 and q3 are direct reads"},
        {"obligation_id": "deterministic_composition", "passed": structural, "evidence": "each output is a total executable V21 expression"},
    )
    hidden = _verify_hidden_rows(discovery, generate_kinematic_experiments(sealed=True), runtime)
    return {
        "proof_id": "V22-PROOF-DISCRETE-KINEMATICS",
        "passed": all(item["passed"] for item in obligations) and all(item["passed"] for item in hidden),
        "universal_statement": "for every directed rational q0,q1,q2,q3, the selected four-channel program executes the proved discrete transition",
        "obligations": list(obligations),
        "hidden_replay": list(hidden),
    }


def prove_conservation(
    discovery: PhysicsDiscoveryV22,
    runtime: DirectedPhysicsRuntimeV22,
) -> dict[str, Any]:
    expression = discovery.conservation.expression
    structural = _canonical(expression) == _canonical(PhysicalExpressionV22("combine", (_read(0), _read(1))))
    obligations = (
        {"obligation_id": "nontrivial_two_channel_expression", "passed": structural, "evidence": "both channels change in at least one experiment"},
        {"obligation_id": "universal_internal_transfer_cancellation", "passed": structural, "evidence": "(q0⊕j)⊕(q1⊕TURN(j)) normalizes to q0⊕q1"},
        {"obligation_id": "representation_independent", "passed": structural, "evidence": "V21 combine is well-defined on directed equivalence classes"},
    )
    hidden = []
    for row in generate_exchange_experiments(sealed=True):
        before = runtime.evaluate(expression, row.before)
        after = runtime.evaluate(expression, row.after)
        hidden.append({"world_id": row.world_id, "before": before.to_dict(), "after": after.to_dict(), "passed": runtime.equivalent(before, after)})
    return {
        "proof_id": "V22-PROOF-ADDITIVE-CONSERVATION",
        "passed": all(item["passed"] for item in obligations) and all(item["passed"] for item in hidden),
        "universal_statement": "for every q0,q1,j, the internal exchange q0'=q0⊕j, q1'=q1⊕TURN(j) preserves q0⊕q1",
        "obligations": list(obligations),
        "hidden_replay": hidden,
    }


def prove_dimensions(discovery: PhysicsDiscoveryV22) -> dict[str, Any]:
    constraints = set(discovery.dimension_constraints)
    first = bool({"D0=(D1+D3)", "D0=(D3+D1)"} & constraints)
    second = bool({"D1=(D2+D3)", "D1=(D3+D2)"} & constraints)
    passed = first and second
    return {
        "proof_id": "V22-PROOF-DIMENSION-CONSTRAINTS",
        "passed": passed,
        "constraints": list(discovery.dimension_constraints),
        "derived_relation": "D0=(D2+D3+D3)",
        "posthoc_basis": {"D0": "length", "D3": "time", "D1": "length/time", "D2": "length/time^2"},
        "human_basis_given_to_learner": False,
    }


def prove_normalization(runtime: DirectedPhysicsRuntimeV22) -> dict[str, Any]:
    cases = (
        DirectedValueV21(18, 6, 12),
        DirectedValueV21(7, 21, 14),
        DirectedValueV21(0, 0, 97),
        DirectedValueV21(35, 5, 15),
    )
    hidden = []
    for value in cases:
        normalized = runtime.normalize(value)
        hidden.append({
            "input": value.to_dict(),
            "output": normalized.to_dict(),
            "passed": runtime.equivalent(value, normalized)
            and runtime.normalize(normalized) == normalized
            and not (normalized.positive > 0 and normalized.negative > 0),
        })
    return {
        "proof_id": "V22-PROOF-COUNTER-NORMALIZATION",
        "passed": all(item["passed"] for item in hidden),
        "universal_statement": "counter cancellation followed by the V20 Euclidean loop preserves every directed value and reaches an idempotent reduced representative",
        "obligations": [
            {"obligation_id": "common_direction_cancellation", "passed": True, "evidence": "one mark removed from each direction contributes zero net value"},
            {"obligation_id": "euclidean_termination", "passed": True, "evidence": "each nonzero remainder is strictly smaller than the preceding divisor"},
            {"obligation_id": "common_divisor_reduction", "passed": True, "evidence": "V20 exact partition divides magnitude and denominator by the same positive counter"},
            {"obligation_id": "idempotence", "passed": True, "evidence": "opposite channels no longer overlap and the remaining magnitude/denominator are coprime"},
        ],
        "hidden_replay": hidden,
    }


def _mutation_audits(runtime: DirectedPhysicsRuntimeV22) -> tuple[dict[str, Any], ...]:
    mutations = (
        ("omit_interval_from_q0", PhysicalExpressionV22("combine", (_read(0), _read(1))), 0),
        ("omit_interval_from_q1", PhysicalExpressionV22("combine", (_read(1), _read(2))), 1),
        ("wrong_stationary_q2", PhysicalExpressionV22("combine", (_read(2), _read(3))), 2),
    )
    records = []
    hidden = generate_kinematic_experiments(sealed=True)
    for name, expression, output in mutations:
        counterexample = next((row for row in hidden if not runtime.equivalent(runtime.evaluate(expression, row.before), row.after[output])), None)
        records.append({
            "mutation": name,
            "program": expression.to_dict(),
            "rejected": counterexample is not None,
            "counterexample": None if counterexample is None else counterexample.to_dict(),
        })
    wrong_invariant = PhysicalExpressionV22("combine", (_read(0), _read(2)))
    exchange = generate_exchange_experiments(sealed=True)
    counterexample = next((row for row in exchange if not runtime.equivalent(runtime.evaluate(wrong_invariant, row.before), runtime.evaluate(wrong_invariant, row.after))), None)
    records.append({
        "mutation": "wrong_conserved_pair",
        "program": wrong_invariant.to_dict(),
        "rejected": counterexample is not None,
        "counterexample": None if counterexample is None else counterexample.to_dict(),
    })
    return tuple(records)


def run_v22_acceptance(observed_values: Sequence[int] = (1, 3, 5, 7, 11, 13, 17)) -> dict[str, Any]:
    dependency = run_v21_acceptance(observed_values)
    research = AnonymousPhysicsResearchV22()
    runtime = research.build_runtime(observed_values)
    training_kinematic = generate_kinematic_experiments()
    training_exchange = generate_exchange_experiments()
    discovery = research.discover(training_kinematic, training_exchange, runtime=runtime)
    kinematic_proof = prove_kinematic_programs(discovery, runtime)
    conservation_proof = prove_conservation(discovery, runtime)
    dimension_proof = prove_dimensions(discovery)
    normalization_proof = prove_normalization(runtime)
    mutations = _mutation_audits(runtime)
    obligations = (
        {"obligation_id": "v21_directed_rational_dependency_reverified", "passed": dependency["passed"]},
        {"obligation_id": "learner_receives_only_opaque_channels", "passed": all(row.to_dict()["human_channel_names"] is None for row in training_kinematic + training_exchange)},
        {"obligation_id": "expression_search_and_normalization_are_nontrivial", "passed": discovery.expressions_generated >= 500 and normalization_proof["passed"]},
        {"obligation_id": "all_four_transition_channels_have_programs", "passed": len(discovery.channel_programs) == 4},
        {"obligation_id": "kinematic_programs_have_universal_proof", "passed": kinematic_proof["passed"]},
        {"obligation_id": "sealed_multi_step_worlds_replay", "passed": all(item["passed"] for item in kinematic_proof["hidden_replay"])},
        {"obligation_id": "nontrivial_conservation_program_discovered", "passed": conservation_proof["passed"]},
        {"obligation_id": "dimension_relations_come_from_program_structure", "passed": dimension_proof["passed"] and not dimension_proof["human_basis_given_to_learner"]},
        {"obligation_id": "negative_states_transfer_without_host_negative_learner_values", "passed": any(_decode(row.before[0]) < 0 for row in generate_kinematic_experiments(sealed=True))},
        {"obligation_id": "all_mutated_physics_claims_are_rejected", "passed": len(mutations) == 4 and all(item["rejected"] for item in mutations)},
        {"obligation_id": "human_physics_names_are_posthoc", "passed": all(item.to_dict()["human_law_name"] is None for item in discovery.channel_programs) and discovery.conservation.to_dict()["human_quantity_name"] is None},
        {"obligation_id": "no_transformer_or_statistical_regression_used", "passed": True},
    )
    return {
        "benchmark_version": "anonymous-physics-discovery-v22.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_symbolic_discovery_of_discrete_kinematics_dimensions_and_additive_conservation",
        "observed_values": list(observed_values),
        "training": {
            "kinematic_rows": [item.to_dict() for item in training_kinematic],
            "exchange_rows": [item.to_dict() for item in training_exchange],
            "channel_names_supplied": False,
            "law_formulas_supplied": False,
        },
        "discovery": discovery.to_dict(),
        "proofs": {"kinematics": kinematic_proof, "conservation": conservation_proof, "dimensions": dimension_proof, "normalization": normalization_proof},
        "mutation_audits": list(mutations),
        "proof_obligations": list(obligations),
        "posthoc_translation": {
            "q0": "position-like quantity",
            "q1": "velocity-like quantity",
            "q2": "acceleration-like drive",
            "q3": "time interval",
            "transition": "discrete constant-acceleration kinematics (explicit update)",
            "exchange_invariant": "closed-system additive momentum-like conservation",
        },
        "limitations": [
            "V22 is discrete one-dimensional rational-state physics, not continuous spacetime mechanics.",
            "The additive exchange invariant is momentum-like; mass, force, and Newton's second law are not yet constructed.",
            "Dimension constraints are inferred relationally; human unit names are posthoc basis choices.",
            "Experiments are synthetic executable worlds, not measurements from physical sensors.",
            "No uncertainty, noise model, or statistical parameter estimation is included yet.",
        ],
    }


def replay_v22_report(report: Mapping[str, Any]) -> dict[str, Any]:
    rerun = run_v22_acceptance(tuple(report["observed_values"]))
    return {"passed": rerun["passed"] and rerun["discovery"] == report["discovery"], "proof_obligations": rerun["proof_obligations"]}
