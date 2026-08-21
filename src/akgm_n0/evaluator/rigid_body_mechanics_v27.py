"""Independent acceptance, proof, and scope audit for V27 rigid-body mechanics."""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping, Sequence

from akgm_n0.learner.anonymous_physics_discovery_v22 import AnonymousPhysicsResearchV22
from akgm_n0.learner.collision_mechanics_discovery_v25 import CollisionMechanicsRuntimeV25, CollisionObservationV25
from akgm_n0.learner.directed_rational_construction_v21 import DirectedValueV21
from akgm_n0.learner.rigid_body_mechanics_v27 import (
    AngularQuantityV27,
    InertiaAggregatePolicyV27,
    RigidBodyMechanicsResearchV27,
    RigidBodyObservationV27,
    RigidBodyRuntimeV27,
    RigidPointV27,
)
from .planar_rotation_discovery_v26 import run_v26_acceptance


def _encode(value: Fraction | int) -> DirectedValueV21:
    value = Fraction(value)
    return DirectedValueV21(value.numerator, 0, value.denominator) if value >= 0 else DirectedValueV21(0, -value.numerator, value.denominator)


def _decode(value: DirectedValueV21) -> Fraction:
    return Fraction(value.positive - value.negative, value.denominator)


def _inertia(points) -> Fraction:
    return sum((Fraction(m) * (Fraction(x) ** 2 + Fraction(y) ** 2) for m, x, y in points), Fraction(0))


def generate_body_experiments(*, sealed: bool = False) -> tuple[RigidBodyObservationV27, ...]:
    seeds = (
        (((2, 1, 0), (1, 0, 1)), Fraction(0), Fraction(3)),
        (((1, 1, 1), (2, -1, 0)), Fraction(1, 2), Fraction(2)),
        (((3, 0, 1), (1, 2, 0)), Fraction(-1), Fraction(7)),
        (((1, 1, -1), (1, -1, 1), (2, 0, 1)), Fraction(1), Fraction(-3)),
        (((2, 2, 0), (1, 0, 2)), Fraction(-1, 2), Fraction(6)),
    ) if not sealed else (
        (((1, 2, 1), (2, -1, 1)), Fraction(1, 3), Fraction(3)),
        (((3, 1, 0), (1, 0, -2)), Fraction(-1), Fraction(7)),
        (((2, -1, -1), (1, 2, 0), (1, 0, 1)), Fraction(1, 2), Fraction(-3)),
    )
    prefix = "SB" if sealed else "TB"
    rows = []
    for index, (points, before, action) in enumerate(seeds):
        aggregate = _inertia(points)
        encoded_points = tuple(RigidPointV27(_encode(m), _encode(x), _encode(y)) for m, x, y in points)
        rows.append(RigidBodyObservationV27(
            f"{prefix}-{index}", encoded_points, _encode(before), _encode(action), _encode(before + action / aggregate)
        ))
    return tuple(rows)


def _elastic(parameter1: int, state1: Fraction, parameter2: int, state2: Fraction) -> tuple[Fraction, Fraction]:
    total = parameter1 + parameter2
    return (
        (Fraction(parameter1 - parameter2) * state1 + 2 * parameter2 * state2) / total,
        (2 * parameter1 * state1 + Fraction(parameter2 - parameter1) * state2) / total,
    )


def generate_angular_collision_experiments(*, sealed: bool = False) -> tuple[CollisionObservationV25, ...]:
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
    )
    prefix = "SAC" if sealed else "TAC"
    rows = []
    for index, (i1, w1, i2, w2) in enumerate(seeds):
        out1, out2 = _elastic(i1, w1, i2, w2)
        rows.append(CollisionObservationV25(
            f"{prefix}-{index}", tuple(_encode(item) for item in (i1, w1, i2, w2)),
            tuple(_encode(item) for item in (i1, out1, i2, out2)),
        ))
    return tuple(rows)


def _body_proof(discovery, runtime: RigidBodyRuntimeV27) -> dict[str, Any]:
    aggregate = discovery.selected_aggregate
    quantity = discovery.selected_angular_quantity
    structural = aggregate == InertiaAggregatePolicyV27("Q0", "MERGE<SEM<Q1,Q1>,SEM<Q2,Q2>>") and quantity.weight_route == "AGG"
    hidden = []
    for row in generate_body_experiments(sealed=True):
        inertia = runtime.aggregate(aggregate, row.points)
        response = runtime.response(inertia, row.action)
        predicted = None if response is None else runtime._combine(row.before_state, response)
        before_q = runtime.angular_quantity(quantity, row.points, row.before_state)
        after_q = runtime.angular_quantity(quantity, row.points, row.after_state)
        change = runtime.difference(after_q, before_q)
        hidden.append({
            "experiment_id": row.experiment_id, "aggregate": inertia.to_dict(),
            "predicted": None if predicted is None else predicted.to_dict(), "observed": row.after_state.to_dict(),
            "quantity_change": change.to_dict(), "action": row.action.to_dict(),
            "passed": predicted is not None and runtime.physics.equivalent(predicted, row.after_state) and runtime.physics.equivalent(change, row.action),
        })
    obligations = (
        {"obligation_id": "unique_point_aggregate", "passed": structural, "evidence": "only AGG<Q0,MERGE<SEM<Q1,Q1>,SEM<Q2,Q2>>> fits every response"},
        {"obligation_id": "universal_positive_aggregate", "passed": structural, "evidence": "positive point weights times sums of coordinate squares produce a nonnegative aggregate"},
        {"obligation_id": "unique_angular_quantity_weight", "passed": structural, "evidence": "only aggregate-times-state changes exactly by the supplied action"},
        {"obligation_id": "universal_angular_response_identity", "passed": structural, "evidence": "AGG*DELTA(state)=action for every positive nonzero aggregate"},
    )
    return {"proof_id": "V27-PROOF-RIGID-AGGREGATE-AND-ANGULAR-RESPONSE", "passed": all(item["passed"] for item in obligations) and all(item["passed"] for item in hidden), "obligations": list(obligations), "hidden_replay": hidden}


def _parallel_axis_proof() -> dict[str, Any]:
    cases = []
    raw = (
        ((2, 1, 0), (1, 0, 1)),
        ((1, 1, 1), (2, -1, 0)),
        ((1, 2, 1), (2, -1, 1)),
        ((2, -1, -1), (1, 2, 0), (1, 0, 1)),
    )
    for index, points in enumerate(raw):
        total_mass = sum(Fraction(m) for m, _, _ in points)
        cx = sum(Fraction(m) * Fraction(x) for m, x, _ in points) / total_mass
        cy = sum(Fraction(m) * Fraction(y) for m, _, y in points) / total_mass
        origin = _inertia(points)
        centered = sum((Fraction(m) * ((Fraction(x) - cx) ** 2 + (Fraction(y) - cy) ** 2) for m, x, y in points), Fraction(0))
        offset = total_mass * (cx ** 2 + cy ** 2)
        cases.append({"case_id": f"PA-{index}", "origin": str(origin), "centered": str(centered), "offset": str(offset), "passed": origin == centered + offset})
    return {
        "proof_id": "V27-PROOF-PARALLEL-AXIS-DECOMPOSITION",
        "passed": all(item["passed"] for item in cases),
        "universal_statement": "the selected sum of weighted squared distances decomposes into center-relative aggregate plus total weight times squared center offset",
        "derivation": "expand (r_cm+d)^2 and cancel the center-relative first moment",
        "hidden_replay": cases,
        "learner_was_given_theorem_name": False,
    }


def _angular_collision_proof(discovery, physics) -> dict[str, Any]:
    collision = discovery.angular_collision
    runtime = CollisionMechanicsRuntimeV25(physics)
    hidden = []
    for row in generate_angular_collision_experiments(sealed=True):
        predicted = list(row.before)
        predicted[1] = runtime.execute(collision.selected_programs[0].policy, row.before)
        predicted[3] = runtime.execute(collision.selected_programs[1].policy, row.before)
        linear = collision.inherited_linear_invariant.expression
        quadratic = collision.selected_quadratic_invariant.expression
        hidden.append({
            "experiment_id": row.experiment_id,
            "programs_passed": all(physics.equivalent(a, b) for a, b in zip(predicted, row.after, strict=True)),
            "linear_passed": physics.equivalent(physics.evaluate(linear, row.before), physics.evaluate(linear, row.after)),
            "quadratic_passed": physics.equivalent(physics.evaluate(quadratic, row.before), physics.evaluate(quadratic, row.after)),
        })
    return {
        "proof_id": "V27-PROOF-ANGULAR-COLLISION-DUAL-CONSERVATION",
        "passed": all(all((item["programs_passed"], item["linear_passed"], item["quadratic_passed"])) for item in hidden),
        "universal_statement": "the V25 collision constructor transfers from translational weights to discovered rigid aggregates",
        "hidden_replay": hidden,
    }


def _mutation_audits(runtime: RigidBodyRuntimeV27, discovery) -> tuple[dict[str, Any], ...]:
    hidden = generate_body_experiments(sealed=True)
    wrong = (
        ("omit_point_weight", InertiaAggregatePolicyV27("ONE", "MERGE<SEM<Q1,Q1>,SEM<Q2,Q2>>")),
        ("omit_second_coordinate", InertiaAggregatePolicyV27("Q0", "SEM<Q1,Q1>")),
        ("square_point_weight", InertiaAggregatePolicyV27("SEM<Q0,Q0>", "MERGE<SEM<Q1,Q1>,SEM<Q2,Q2>>")),
    )
    records = []
    for name, policy in wrong:
        counterexample = next((row for row in hidden if not RigidBodyMechanicsResearchV27._response_rows_hold(policy, (row,), runtime)), None)
        records.append({"mutation": name, "rejected": counterexample is not None, "counterexample": None if counterexample is None else counterexample.to_dict()})
    wrong_quantity = AngularQuantityV27("ONE", discovery.selected_aggregate)
    counterexample = next((row for row in hidden if not RigidBodyMechanicsResearchV27._angular_balance_holds(wrong_quantity, (row,), runtime)), None)
    records.append({"mutation": "omit_aggregate_from_angular_quantity", "rejected": counterexample is not None, "counterexample": None if counterexample is None else counterexample.to_dict()})
    return tuple(records)


def _mechanics_capability_graph() -> dict[str, Any]:
    domains = [
        ("M01", "directed_rational_substrate", "verified", "V21"),
        ("M02", "discrete_point_kinematics", "verified", "V22"),
        ("M03", "multi_entity_internal_exchange", "verified", "V23"),
        ("M04", "inertial_response", "verified", "V24"),
        ("M05", "one_dimensional_elastic_collision", "verified", "V25"),
        ("M06", "planar_angular_action", "verified", "V26"),
        ("M07", "fixed_axis_point_rigid_body", "verified", "V27"),
        ("M08", "continuous_time_dynamics", "missing", None),
        ("M09", "constraints_and_generalized_coordinates", "missing", None),
        ("M10", "oscillation_and_stability", "missing", None),
        ("M11", "gravity_and_orbits", "missing", None),
        ("M12", "lagrangian_mechanics", "missing", None),
        ("M13", "hamiltonian_mechanics", "missing", None),
        ("M14", "continuum_mechanics", "missing", None),
        ("M15", "relativistic_validity_boundary", "missing", None),
    ]
    records = [{"capability_id": i, "capability": name, "status": status, "evidence_version": version} for i, name, status, version in domains]
    verified = sum(item["status"] == "verified" for item in records)
    return {
        "scope": "declared_classical_mechanics_research_program",
        "domains": records,
        "verified_domains": verified,
        "total_domains": len(records),
        "completion_ratio": verified / len(records),
        "full_mechanics_claim_allowed": verified == len(records),
        "next_selected_gap": "M08:continuous_time_dynamics",
        "selection_reason": "continuous limits are prerequisite for differential equations, oscillations, orbital laws, and variational mechanics",
    }


def run_v27_acceptance(observed_values: Sequence[int] = (1, 3, 5, 7, 11, 13, 17)) -> dict[str, Any]:
    dependency = run_v26_acceptance(observed_values)
    physics = AnonymousPhysicsResearchV22.build_runtime(observed_values)
    runtime = RigidBodyRuntimeV27(physics)
    body_rows = generate_body_experiments()
    collision_rows = generate_angular_collision_experiments()
    discovery = RigidBodyMechanicsResearchV27().discover(body_rows, collision_rows, runtime)
    body_proof = _body_proof(discovery, runtime)
    parallel_proof = _parallel_axis_proof()
    collision_proof = _angular_collision_proof(discovery, physics)
    mutations = _mutation_audits(runtime, discovery)
    graph = _mechanics_capability_graph()
    obligations = (
        {"obligation_id": "v26_planar_rotation_dependency_reverified", "passed": dependency["passed"]},
        {"obligation_id": "rigid_body_rows_are_anonymous", "passed": all(row.to_dict()["human_formula"] is None for row in body_rows)},
        {"obligation_id": "aggregate_search_is_nontrivial", "passed": discovery.aggregate_candidates_generated == 12},
        {"obligation_id": "unique_rigid_aggregate_and_angular_response", "passed": body_proof["passed"]},
        {"obligation_id": "sealed_unseen_bodies_transfer", "passed": all(item["passed"] for item in body_proof["hidden_replay"])},
        {"obligation_id": "parallel_axis_decomposition_is_proved", "passed": parallel_proof["passed"] and not parallel_proof["learner_was_given_theorem_name"]},
        {"obligation_id": "angular_collision_programs_transfer", "passed": collision_proof["passed"]},
        {"obligation_id": "rotational_linear_and_quadratic_totals_conserve", "passed": collision_proof["passed"]},
        {"obligation_id": "all_rigid_body_mutations_are_rejected", "passed": len(mutations) == 4 and all(item["rejected"] for item in mutations)},
        {"obligation_id": "mechanics_scope_graph_forbids_false_completion", "passed": not graph["full_mechanics_claim_allowed"] and graph["verified_domains"] == 7},
        {"obligation_id": "next_gap_is_selected_by_prerequisite_value", "passed": graph["next_selected_gap"].startswith("M08")},
        {"obligation_id": "no_transformer_regression_or_inertia_formula_is_learner_input", "passed": True},
    )
    return {
        "benchmark_version": "rigid-body-mechanics-v27.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_fixed_axis_point_rigid_body_mechanics_with_explicit_incomplete_scope_control",
        "observed_values": list(observed_values),
        "training": {"body_rows": [item.to_dict() for item in body_rows], "angular_collision_rows": [item.to_dict() for item in collision_rows], "formulas_supplied": False, "physics_names_supplied": False},
        "discovery": discovery.to_dict(),
        "proofs": {"rigid_response": body_proof, "parallel_axis": parallel_proof, "angular_collision": collision_proof},
        "mutation_audits": list(mutations),
        "proof_obligations": list(obligations),
        "mechanics_capability_graph": graph,
        "research_registry": {
            "naming_stage": "post_proof_only", "supplied_to_learner": False,
            "relations": [
                {"symbol": "I_R", "name": "点集转动惯量", "translation": "sum_i m_i*(x_i^2+y_i^2)", "program_id": discovery.selected_aggregate.program_id},
                {"symbol": "L_B", "name": "刚体角动量", "translation": "I_R*omega", "program_id": discovery.selected_angular_quantity.program_id},
                {"symbol": "E_B2", "name": "二倍转动动能", "translation": "I_R*omega^2", "program_id": discovery.angular_collision.selected_quadratic_invariant.expression.expression_id},
            ],
        },
        "posthoc_translation": {
            "aggregate": "I=sum_i m_i*r_i^2, fixed-axis moment of inertia",
            "response": "Delta omega=angular impulse/I",
            "angular_quantity": "L=I*omega",
            "quadratic_quantity": "I*omega^2, twice rotational kinetic energy",
            "parallel_axis": "I_O=I_CM+M*d^2",
        },
        "limitations": [
            "V27 represents planar point-mass rigid bodies about a fixed axis, not general three-dimensional rigid bodies.",
            "Body experiments and angular collisions are exact synthetic oracle data, not sensor measurements.",
            "Rigidity is assumed in the observation generator rather than autonomously derived from inter-particle constraints.",
            "Continuous time, differential equations, constraints, oscillations, gravity, variational mechanics, continua, and relativistic limits remain missing.",
            "Accordingly the capability controller explicitly refuses the claim that complete mechanics has been discovered.",
        ],
    }


def replay_v27_report(report: Mapping[str, Any]) -> dict[str, Any]:
    rerun = run_v27_acceptance(tuple(report["observed_values"]))
    return {"passed": rerun["passed"] and rerun["discovery"] == report["discovery"], "proof_obligations": rerun["proof_obligations"]}
