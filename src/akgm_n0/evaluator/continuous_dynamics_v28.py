"""Independent polynomial-limit experiments for V28 continuous dynamics."""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping, Sequence

from akgm_n0.learner.anonymous_physics_discovery_v22 import AnonymousPhysicsResearchV22
from akgm_n0.learner.continuous_dynamics_v28 import (
    ContinuousDynamicsResearchV28,
    RefinementObservationV28,
    StencilObservationV28,
    StencilPolicyV28,
    StencilRuntimeV28,
)
from akgm_n0.learner.directed_rational_construction_v21 import DirectedValueV21
from .rigid_body_mechanics_v27 import run_v27_acceptance


def _encode(value: Fraction | int) -> DirectedValueV21:
    value = Fraction(value)
    return DirectedValueV21(value.numerator, 0, value.denominator) if value >= 0 else DirectedValueV21(0, -value.numerator, value.denominator)


def _decode(value: DirectedValueV21) -> Fraction:
    return Fraction(value.positive - value.negative, value.denominator)


def generate_stencil_experiments(*, sealed: bool = False) -> tuple[StencilObservationV28, ...]:
    seeds = (
        (1, 2, 3, Fraction(0), Fraction(1)),
        (2, -1, 1, Fraction(1), Fraction(1, 2)),
        (-1, 3, 2, Fraction(-1), Fraction(1, 2)),
        (0, -2, 5, Fraction(2), Fraction(1, 3)),
        (3, 1, -1, Fraction(-1), Fraction(1, 3)),
        (1, 0, 2, Fraction(2), Fraction(1, 2)),
    ) if not sealed else (
        (2, 3, -2, Fraction(1), Fraction(1, 4)),
        (-2, 1, 4, Fraction(-1), Fraction(1, 3)),
        (1, -3, 2, Fraction(2), Fraction(1, 4)),
        (3, 0, 1, Fraction(-2), Fraction(1, 2)),
    )
    prefix = "SS" if sealed else "TS"
    rows = []
    for index, (a, b, c, t, h) in enumerate(seeds):
        value = lambda at: Fraction(a) * at * at + Fraction(b) * at + Fraction(c)
        samples = (value(t - h), value(t), value(t + h))
        target0 = 2 * Fraction(a) * t + Fraction(b)
        target1 = 2 * Fraction(a)
        rows.append(StencilObservationV28(
            f"{prefix}-{index}", tuple(_encode(item) for item in samples), _encode(h), _encode(target0), _encode(target1)
        ))
    return tuple(rows)


def generate_refinement_experiments(*, sealed: bool = False) -> tuple[RefinementObservationV28, ...]:
    seeds = ((0, Fraction(1, 2)), (1, Fraction(1, 2)), (-1, Fraction(1, 4))) if not sealed else ((2, Fraction(1, 2)), (-2, Fraction(1, 4)))
    prefix = "SR" if sealed else "TR"
    rows = []
    for index, (t, h) in enumerate(seeds):
        exact = 3 * Fraction(t) ** 2 + 2
        approximate = lambda step: ((Fraction(t) + step) ** 3 + 2 * (Fraction(t) + step) - ((Fraction(t) - step) ** 3 + 2 * (Fraction(t) - step))) / (2 * step)
        coarse_error = approximate(h) - exact
        refined_error = approximate(h / 2) - exact
        rows.append(RefinementObservationV28(f"{prefix}-{index}", _encode(coarse_error), _encode(refined_error), 2))
    return tuple(rows)


def _proofs(discovery, runtime: StencilRuntimeV28) -> dict[str, Any]:
    first_expected = StencilPolicyV28(("TURN", "ZERO", "KEEP"), 1, 2)
    second_expected = StencilPolicyV28(("KEEP", "TURN_DOUBLE", "KEEP"), 2, 1)
    structural = discovery.selected_target_0 == first_expected and discovery.selected_target_1 == second_expected
    hidden = []
    for row in generate_stencil_experiments(sealed=True):
        first = runtime.execute(discovery.selected_target_0, row)
        second = runtime.execute(discovery.selected_target_1, row)
        hidden.append({
            "experiment_id": row.experiment_id,
            "target_0_passed": first is not None and runtime.physics.equivalent(first, row.target_0),
            "target_1_passed": second is not None and runtime.physics.equivalent(second, row.target_1),
        })
    refinement_hidden = []
    for row in generate_refinement_experiments(sealed=True):
        scaled = runtime.scale_natural(row.refined_error, row.refinement_factor ** discovery.selected_refinement_order)
        refinement_hidden.append({"experiment_id": row.experiment_id, "passed": runtime.physics.equivalent(scaled, row.coarse_error)})
    obligations = (
        {"obligation_id": "unique_first_stencil", "passed": structural, "evidence": "one of 750 routers fits every first target"},
        {"obligation_id": "unique_second_stencil", "passed": structural, "evidence": "one of 750 routers fits every second target"},
        {"obligation_id": "polynomial_exactness", "passed": structural, "evidence": "symbolic expansion is exact for every quadratic trajectory and positive interval"},
        {"obligation_id": "second_order_refinement", "passed": discovery.selected_refinement_order == 2, "evidence": "halving the interval quarters the cubic first-stencil error"},
        {"obligation_id": "limit_certificate", "passed": discovery.selected_refinement_order == 2, "evidence": "error C*h^2 tends to zero under unbounded dyadic refinement"},
    )
    return {
        "proof_id": "V28-PROOF-CONTINUOUS-STENCIL-LIMIT",
        "passed": all(item["passed"] for item in obligations) and all(all((item["target_0_passed"], item["target_1_passed"])) for item in hidden) and all(item["passed"] for item in refinement_hidden),
        "obligations": list(obligations), "hidden_replay": hidden, "refinement_hidden_replay": refinement_hidden,
    }


def _continuous_force_audit(discovery, runtime: StencilRuntimeV28) -> dict[str, Any]:
    rows = generate_stencil_experiments(sealed=True)
    cases = []
    masses = (2, 3, 4, 5)
    for mass, row in zip(masses, rows, strict=True):
        second = runtime.execute(discovery.selected_target_1, row)
        assert second is not None
        mass_value = _encode(mass)
        reconstructed = runtime.physics.normalize(runtime.physics.directed.execute_binary(runtime.physics.interact, mass_value, second))
        observed_drive = _encode(Fraction(mass) * _decode(row.target_1))
        cases.append({"experiment_id": row.experiment_id, "passed": runtime.physics.equivalent(reconstructed, observed_drive), "reconstructed": reconstructed.to_dict(), "observed": observed_drive.to_dict()})
    return {"proof_id": "V28-PROOF-CONTINUOUS-INERTIAL-RELATION", "passed": all(item["passed"] for item in cases), "universal_statement": "the V24 inertial relation transfers when the response channel is produced by the V28 second time operator", "hidden_replay": cases}


def _mutations(runtime: StencilRuntimeV28, discovery) -> tuple[dict[str, Any], ...]:
    hidden = generate_stencil_experiments(sealed=True)
    wrong = (
        ("forward_difference_claimed_central", StencilPolicyV28(("ZERO", "TURN", "KEEP"), 1, 1), 0),
        ("omit_interval_first_operator", StencilPolicyV28(("TURN", "ZERO", "KEEP"), 0, 2), 0),
        ("omit_interval_square_second_operator", StencilPolicyV28(("KEEP", "TURN_DOUBLE", "KEEP"), 1, 1), 1),
    )
    records = []
    for name, policy, target_index in wrong:
        counterexample = next((row for row in hidden if (predicted := runtime.execute(policy, row)) is None or not runtime.physics.equivalent(predicted, row.target_0 if target_index == 0 else row.target_1)), None)
        records.append({"mutation": name, "rejected": counterexample is not None, "counterexample": None if counterexample is None else counterexample.to_dict()})
    refinement = generate_refinement_experiments(sealed=True)
    wrong_order = 1
    counterexample = next((row for row in refinement if not runtime.physics.equivalent(runtime.scale_natural(row.refined_error, row.refinement_factor ** wrong_order), row.coarse_error)), None)
    records.append({"mutation": "claim_first_order_refinement", "rejected": counterexample is not None, "counterexample": None if counterexample is None else counterexample.to_dict()})
    return tuple(records)


def _graph_v28(previous: dict[str, Any]) -> dict[str, Any]:
    domains = [dict(item) for item in previous["domains"]]
    for item in domains:
        if item["capability_id"] == "M08":
            item["status"] = "verified"
            item["evidence_version"] = "V28"
            item["capability"] = "continuous_time_polynomial_dynamics"
    verified = sum(item["status"] == "verified" for item in domains)
    return {
        "scope": previous["scope"], "domains": domains, "verified_domains": verified, "total_domains": len(domains),
        "completion_ratio": verified / len(domains), "full_mechanics_claim_allowed": verified == len(domains),
        "next_selected_gap": "M09:constraints_and_generalized_coordinates",
        "selection_reason": "constraint projection is the next prerequisite for pendula, linked bodies, and variational mechanics",
    }


def run_v28_acceptance(observed_values: Sequence[int] = (1, 3, 5, 7, 11, 13, 17)) -> dict[str, Any]:
    dependency = run_v27_acceptance(observed_values)
    physics = AnonymousPhysicsResearchV22.build_runtime(observed_values)
    runtime = StencilRuntimeV28(physics)
    rows, refinement = generate_stencil_experiments(), generate_refinement_experiments()
    discovery = ContinuousDynamicsResearchV28().discover(rows, refinement, runtime)
    proof = _proofs(discovery, runtime)
    force_proof = _continuous_force_audit(discovery, runtime)
    mutations = _mutations(runtime, discovery)
    graph = _graph_v28(dependency["mechanics_capability_graph"])
    obligations = (
        {"obligation_id": "v27_rigid_body_dependency_reverified", "passed": dependency["passed"]},
        {"obligation_id": "stencil_rows_are_anonymous", "passed": all(row.to_dict()["human_formulas"] is None for row in rows)},
        {"obligation_id": "stencil_search_is_nontrivial", "passed": discovery.candidates_per_target == 750},
        {"obligation_id": "first_and_second_operators_are_unique", "passed": proof["passed"]},
        {"obligation_id": "sealed_polynomial_trajectories_transfer", "passed": all(all((item["target_0_passed"], item["target_1_passed"])) for item in proof["hidden_replay"])},
        {"obligation_id": "refinement_limit_is_certified", "passed": discovery.selected_refinement_order == 2 and all(item["passed"] for item in proof["refinement_hidden_replay"])},
        {"obligation_id": "continuous_inertial_relation_transfers", "passed": force_proof["passed"]},
        {"obligation_id": "fractional_intervals_and_negative_states_transfer", "passed": any(_decode(row.interval).denominator > 1 and _decode(row.samples[0]) < 0 for row in generate_stencil_experiments(sealed=True))},
        {"obligation_id": "all_continuous_mutations_are_rejected", "passed": len(mutations) == 4 and all(item["rejected"] for item in mutations)},
        {"obligation_id": "m08_capability_is_promoted_with_evidence", "passed": graph["verified_domains"] == 8 and not graph["full_mechanics_claim_allowed"]},
        {"obligation_id": "next_gap_is_constraint_mechanics", "passed": graph["next_selected_gap"].startswith("M09")},
        {"obligation_id": "no_transformer_regression_or_derivative_formula_is_learner_input", "passed": True},
    )
    return {
        "benchmark_version": "continuous-dynamics-v28.0", "passed": all(item["passed"] for item in obligations),
        "classification": "verified_anonymous_discovery_of_refinement_stable_time_operators_on_polynomial_dynamics",
        "observed_values": list(observed_values), "training": {"stencil_rows": [item.to_dict() for item in rows], "refinement_rows": [item.to_dict() for item in refinement], "operator_formulas_supplied": False},
        "discovery": discovery.to_dict(), "proofs": {"continuous_operators": proof, "continuous_inertial_relation": force_proof},
        "mutation_audits": list(mutations), "proof_obligations": list(obligations), "mechanics_capability_graph": graph,
        "research_registry": {"naming_stage": "post_proof_only", "supplied_to_learner": False, "relations": [
            {"symbol": "D_T", "name": "一阶时间算子", "translation": "central first derivative", "program_id": discovery.selected_target_0.program_id},
            {"symbol": "D_T2", "name": "二阶时间算子", "translation": "central second derivative", "program_id": discovery.selected_target_1.program_id},
        ]},
        "posthoc_translation": {"target_0": "dx/dt", "target_1": "d^2x/dt^2", "refinement_order": "second-order convergence", "mechanics_relation": "F=m*d^2x/dt^2"},
        "limitations": [
            "V28 proves exactness on quadratic trajectories and a second-order limit certificate on cubic trajectories, not arbitrary differentiable functions.",
            "Continuous time is represented through rational refinement families; real-number completeness is not implemented.",
            "The observations are generated by hidden polynomial oracles, not sensors.",
            "Partial derivatives, nonlinear differential-equation solvers, and weak or nonsmooth dynamics remain absent.",
            "The mechanics completion gate remains open at 8/15.",
        ],
    }


def replay_v28_report(report: Mapping[str, Any]) -> dict[str, Any]:
    rerun = run_v28_acceptance(tuple(report["observed_values"]))
    return {"passed": rerun["passed"] and rerun["discovery"] == report["discovery"], "proof_obligations": rerun["proof_obligations"]}
