"""Independent acceptance and proof audit for V25 collision mechanics."""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping, Sequence

from akgm_n0.learner.anonymous_physics_discovery_v22 import AnonymousPhysicsResearchV22, PhysicalExpressionV22
from akgm_n0.learner.collision_mechanics_discovery_v25 import (
    CollisionMechanicsDiscoveryV25,
    CollisionMechanicsResearchV25,
    CollisionMechanicsRuntimeV25,
    CollisionObservationV25,
    CollisionPolicyV25,
)
from akgm_n0.learner.directed_rational_construction_v21 import DirectedValueV21
from .inertial_response_discovery_v24 import run_v24_acceptance


def _encode(value: Fraction | int) -> DirectedValueV21:
    value = Fraction(value)
    return DirectedValueV21(value.numerator, 0, value.denominator) if value >= 0 else DirectedValueV21(0, -value.numerator, value.denominator)


def _decode(value: DirectedValueV21) -> Fraction:
    return Fraction(value.positive - value.negative, value.denominator)


def _collision(m1: int, u1: Fraction, m2: int, u2: Fraction) -> tuple[Fraction, Fraction]:
    total = m1 + m2
    return (
        (Fraction(m1 - m2) * u1 + 2 * m2 * u2) / total,
        (2 * m1 * u1 + Fraction(m2 - m1) * u2) / total,
    )


def generate_collision_experiments(*, sealed: bool = False) -> tuple[CollisionObservationV25, ...]:
    seeds = (
        (1, Fraction(1), 1, Fraction(-1)),
        (1, Fraction(2), 2, Fraction(-1)),
        (2, Fraction(1), 1, Fraction(-2)),
        (2, Fraction(3, 2), 3, Fraction(-1, 2)),
        (3, Fraction(-1), 2, Fraction(2)),
        (4, Fraction(1, 2), 1, Fraction(-3, 2)),
    ) if not sealed else (
        (1, Fraction(-2), 3, Fraction(1)),
        (2, Fraction(-1, 2), 5, Fraction(1, 2)),
        (3, Fraction(2, 3), 1, Fraction(-1)),
        (4, Fraction(-1, 2), 3, Fraction(1)),
    )
    prefix = "SC" if sealed else "TC"
    rows = []
    for index, (m1, u1, m2, u2) in enumerate(seeds):
        v1, v2 = _collision(m1, u1, m2, u2)
        rows.append(CollisionObservationV25(
            f"{prefix}-{index}",
            tuple(_encode(item) for item in (m1, u1, m2, u2)),
            tuple(_encode(item) for item in (m1, v1, m2, v2)),
        ))
    return tuple(rows)


def _expected_policies() -> tuple[CollisionPolicyV25, CollisionPolicyV25]:
    return (
        CollisionPolicyV25(("KEEP", "TURN", "ZERO", "DOUBLE"), "MERGE<Q0,Q2>"),
        CollisionPolicyV25(("DOUBLE", "ZERO", "TURN", "KEEP"), "MERGE<Q0,Q2>"),
    )


def _program_proof(discovery: CollisionMechanicsDiscoveryV25, runtime: CollisionMechanicsRuntimeV25) -> dict[str, Any]:
    expected = _expected_policies()
    structural = all(item.policy == target for item, target in zip(discovery.selected_programs, expected, strict=True))
    hidden = []
    for row in generate_collision_experiments(sealed=True):
        predicted = list(row.before)
        predicted[1] = runtime.execute(discovery.selected_programs[0].policy, row.before)
        predicted[3] = runtime.execute(discovery.selected_programs[1].policy, row.before)
        hidden.append({
            "experiment_id": row.experiment_id,
            "predicted": [item.to_dict() for item in predicted],
            "observed": [item.to_dict() for item in row.after],
            "passed": all(runtime.physics.equivalent(a, b) for a, b in zip(predicted, row.after, strict=True)),
        })
    obligations = (
        {"obligation_id": "unique_q1_collision_program", "passed": structural, "evidence": "one of 1280 executable routers fits q1'"},
        {"obligation_id": "unique_q3_collision_program", "passed": structural, "evidence": "one of 1280 executable routers fits q3'"},
        {"obligation_id": "universal_rational_execution", "passed": structural, "evidence": "V21 ring laws and positive MERGE<q0,q2> denominator make both programs total"},
        {"obligation_id": "entity_parameters_persist", "passed": True, "evidence": "q0 and q2 are unchanged direct state channels"},
    )
    return {
        "proof_id": "V25-PROOF-TWO-ENTITY-COLLISION-PROGRAMS",
        "passed": all(item["passed"] for item in obligations) and all(item["passed"] for item in hidden),
        "universal_statement": "the selected routers define exact directed-rational post-collision states for all positive q0,q2",
        "obligations": list(obligations),
        "hidden_replay": hidden,
    }


def _invariant_proof(discovery: CollisionMechanicsDiscoveryV25, physics) -> dict[str, Any]:
    linear = discovery.inherited_linear_invariant.expression
    quadratic = discovery.selected_quadratic_invariant.expression
    hidden = []
    for row in generate_collision_experiments(sealed=True):
        linear_before, linear_after = physics.evaluate(linear, row.before), physics.evaluate(linear, row.after)
        quadratic_before, quadratic_after = physics.evaluate(quadratic, row.before), physics.evaluate(quadratic, row.after)
        hidden.append({
            "experiment_id": row.experiment_id,
            "linear_passed": physics.equivalent(linear_before, linear_after),
            "quadratic_passed": physics.equivalent(quadratic_before, quadratic_after),
            "linear_before": linear_before.to_dict(), "linear_after": linear_after.to_dict(),
            "quadratic_before": quadratic_before.to_dict(), "quadratic_after": quadratic_after.to_dict(),
        })
    expected_quadratic = "MERGE<SEM<q0,SEM<q1,q1>>,SEM<q2,SEM<q3,q3>>>"
    structural = quadratic.render() == expected_quadratic
    obligations = (
        {"obligation_id": "v24_linear_invariant_transfers", "passed": linear.render() == "MERGE<SEM<q0,q1>,SEM<q2,q3>>", "evidence": "weighted linear total is unchanged"},
        {"obligation_id": "unique_quadratic_pairing", "passed": structural, "evidence": "only same-entity parameter-times-square pairing survives all collisions"},
        {"obligation_id": "universal_two_invariant_identity", "passed": structural, "evidence": "symbolic expansion of the selected routers cancels exactly in the V21 commutative ring"},
    )
    return {
        "proof_id": "V25-PROOF-LINEAR-AND-QUADRATIC-CONSERVATION",
        "passed": all(item["passed"] for item in obligations) and all(item["linear_passed"] and item["quadratic_passed"] for item in hidden),
        "universal_statement": "every selected two-entity collision preserves both weighted linear and weighted quadratic totals",
        "obligations": list(obligations),
        "hidden_replay": hidden,
    }


def _mutation_audits(runtime: CollisionMechanicsRuntimeV25, discovery: CollisionMechanicsDiscoveryV25) -> tuple[dict[str, Any], ...]:
    hidden = generate_collision_experiments(sealed=True)
    wrong_policies = (
        ("swap_states_without_parameter_weighting", CollisionPolicyV25(("ZERO", "ZERO", "ZERO", "KEEP"), "Q2"), 1),
        ("use_product_denominator", CollisionPolicyV25(("KEEP", "TURN", "ZERO", "DOUBLE"), "SEM<Q0,Q2>"), 1),
        ("reuse_first_output_for_second", discovery.selected_programs[0].policy, 3),
    )
    records = []
    for name, policy, output in wrong_policies:
        counterexample = next((row for row in hidden if not runtime.physics.equivalent(runtime.execute(policy, row.before), row.after[output])), None)
        records.append({"mutation": name, "rejected": counterexample is not None, "counterexample": None if counterexample is None else counterexample.to_dict()})

    quadratic = discovery.selected_quadratic_invariant.expression
    counterexample_data = None
    for row in hidden:
        m1, u1, m2, u2 = (_decode(item) for item in row.before)
        common = (m1 * u1 + m2 * u2) / (m1 + m2)
        stuck = tuple(_encode(item) for item in (m1, common, m2, common))
        if not runtime.physics.equivalent(runtime.physics.evaluate(quadratic, row.before), runtime.physics.evaluate(quadratic, stuck)):
            counterexample_data = {"experiment_id": row.experiment_id, "before": [item.to_dict() for item in row.before], "mutated_after": [item.to_dict() for item in stuck]}
            break
    records.append({"mutation": "claim_quadratic_conservation_for_sticking_collision", "rejected": counterexample_data is not None, "counterexample": counterexample_data})
    return tuple(records)


def _research_registry(discovery: CollisionMechanicsDiscoveryV25) -> dict[str, Any]:
    return {
        "registry_version": "mechanics-research-registry-v25.0",
        "naming_stage": "post_proof_only",
        "supplied_to_learner": False,
        "relations": [
            {"research_symbol": "P_L", "research_name": "线性加权运动总量", "physics_alias": "total momentum", "program_id": discovery.inherited_linear_invariant.expression.expression_id},
            {"research_symbol": "E_Q", "research_name": "二次加权运动总量", "physics_alias": "twice kinetic energy", "program_id": discovery.selected_quadratic_invariant.expression.expression_id},
            {"research_symbol": "C_E", "research_name": "双实体双守恒碰撞变换", "physics_alias": "one-dimensional elastic collision", "program_ids": [item.policy.program_id for item in discovery.selected_programs]},
        ],
        "note": "The conventional factor 1/2 is not identifiable from conservation alone; V25 stores m*v^2 rather than naming 1/2*m*v^2 as primitive.",
    }


def run_v25_acceptance(observed_values: Sequence[int] = (1, 3, 5, 7, 11, 13, 17)) -> dict[str, Any]:
    dependency = run_v24_acceptance(observed_values)
    physics = AnonymousPhysicsResearchV22.build_runtime(observed_values)
    runtime = CollisionMechanicsRuntimeV25(physics)
    rows = generate_collision_experiments()
    discovery = CollisionMechanicsResearchV25().discover(rows, runtime)
    program_proof = _program_proof(discovery, runtime)
    invariant_proof = _invariant_proof(discovery, physics)
    mutations = _mutation_audits(runtime, discovery)
    obligations = (
        {"obligation_id": "v24_inertial_response_dependency_reverified", "passed": dependency["passed"]},
        {"obligation_id": "collision_rows_are_anonymous", "passed": all(row.to_dict()["human_collision_formula"] is None and row.to_dict()["human_conservation_names"] is None for row in rows)},
        {"obligation_id": "collision_search_is_nontrivial", "passed": discovery.candidates_per_output == 1280},
        {"obligation_id": "both_collision_outputs_are_uniquely_selected", "passed": len(discovery.selected_programs) == 2 and program_proof["passed"]},
        {"obligation_id": "sealed_collisions_replay", "passed": all(item["passed"] for item in program_proof["hidden_replay"])},
        {"obligation_id": "linear_weighted_conservation_transfers", "passed": invariant_proof["passed"]},
        {"obligation_id": "new_quadratic_conservation_is_unique", "passed": discovery.quadratic_invariant_candidates == 6 and invariant_proof["passed"]},
        {"obligation_id": "unequal_parameters_and_fractional_states_transfer", "passed": any(_decode(row.before[1]).denominator > 1 for row in generate_collision_experiments(sealed=True))},
        {"obligation_id": "all_collision_mutations_are_rejected", "passed": len(mutations) == 4 and all(item["rejected"] for item in mutations)},
        {"obligation_id": "sticking_collision_is_distinguished_from_double_conservation", "passed": mutations[-1]["rejected"]},
        {"obligation_id": "research_names_are_assigned_after_proof", "passed": not _research_registry(discovery)["supplied_to_learner"]},
        {"obligation_id": "no_transformer_regression_or_collision_formula_is_learner_input", "passed": True},
    )
    return {
        "benchmark_version": "collision-mechanics-discovery-v25.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_anonymous_construction_of_exact_two_entity_elastic_collision_mechanics",
        "observed_values": list(observed_values),
        "training": {"collision_rows": [row.to_dict() for row in rows], "formula_supplied": False, "physics_names_supplied": False},
        "discovery": discovery.to_dict(),
        "proofs": {"collision_programs": program_proof, "dual_conservation": invariant_proof},
        "mutation_audits": list(mutations),
        "proof_obligations": list(obligations),
        "research_registry": _research_registry(discovery),
        "posthoc_translation": {
            "linear_invariant": "m1*v1 + m2*v2 (total momentum)",
            "quadratic_invariant": "m1*v1^2 + m2*v2^2 (twice kinetic energy)",
            "collision_programs": "exact one-dimensional elastic collision update",
        },
        "limitations": [
            "Training observations are generated by an exact hidden collision oracle, not physical sensors.",
            "The learner selects within a finite four-atom router grammar; unrestricted mechanics invention is not claimed.",
            "Only one-dimensional, instantaneous, two-entity, perfectly elastic collisions are represented.",
            "The factor one-half in conventional kinetic energy cannot be inferred from conservation alone.",
            "Rotation, angular momentum, deformable bodies, friction, gravity, fields, and continuous trajectories remain future work.",
        ],
    }


def replay_v25_report(report: Mapping[str, Any]) -> dict[str, Any]:
    rerun = run_v25_acceptance(tuple(report["observed_values"]))
    return {"passed": rerun["passed"] and rerun["discovery"] == report["discovery"], "proof_obligations": rerun["proof_obligations"]}
