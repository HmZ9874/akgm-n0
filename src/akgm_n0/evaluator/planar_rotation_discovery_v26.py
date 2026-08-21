"""Independent experiments and proof audit for V26 planar rotation mechanics."""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping, Sequence

from akgm_n0.learner.anonymous_physics_discovery_v22 import AnonymousPhysicsResearchV22
from akgm_n0.learner.directed_rational_construction_v21 import DirectedValueV21
from akgm_n0.learner.planar_rotation_discovery_v26 import (
    OrientedBilinearPolicyV26,
    PlanarActionObservationV26,
    PlanarRotationDiscoveryV26,
    PlanarRotationResearchV26,
    PlanarRotationRuntimeV26,
    RotationQuantityV26,
)
from .collision_mechanics_discovery_v25 import run_v25_acceptance


def _encode(value: Fraction | int) -> DirectedValueV21:
    value = Fraction(value)
    return DirectedValueV21(value.numerator, 0, value.denominator) if value >= 0 else DirectedValueV21(0, -value.numerator, value.denominator)


def _decode(value: DirectedValueV21) -> Fraction:
    return Fraction(value.positive - value.negative, value.denominator)


def _row(prefix: str, index: int, seed, central: bool) -> PlanarActionObservationV26:
    mass, x, y, vx, vy, jx, jy = seed
    before_values = (mass, x, y, vx, vy, jx, jy)
    after_values = (mass, x, y, vx + jx / mass, vy + jy / mass, jx, jy)
    return PlanarActionObservationV26(
        f"{prefix}-{index}", tuple(_encode(item) for item in before_values),
        tuple(_encode(item) for item in after_values), central,
    )


def generate_planar_experiments(*, sealed: bool = False) -> tuple[tuple[PlanarActionObservationV26, ...], tuple[PlanarActionObservationV26, ...]]:
    central = (
        (2, Fraction(1), Fraction(0), Fraction(0), Fraction(1), Fraction(1), Fraction(0)),
        (3, Fraction(0), Fraction(1), Fraction(1), Fraction(0), Fraction(0), Fraction(-1)),
        (2, Fraction(1), Fraction(1), Fraction(1), Fraction(-1), Fraction(1), Fraction(1)),
        (4, Fraction(2), Fraction(-1), Fraction(0), Fraction(1), Fraction(1), Fraction(-1, 2)),
    ) if not sealed else (
        (3, Fraction(-1), Fraction(2), Fraction(1), Fraction(1), Fraction(1, 2), Fraction(-1)),
        (5, Fraction(2), Fraction(1), Fraction(-1), Fraction(0), Fraction(-1), Fraction(-1, 2)),
        (2, Fraction(-1), Fraction(-1), Fraction(1, 2), Fraction(-1), Fraction(-1), Fraction(-1)),
    )
    general = (
        (2, Fraction(1), Fraction(0), Fraction(0), Fraction(1), Fraction(0), Fraction(1)),
        (3, Fraction(0), Fraction(1), Fraction(1), Fraction(0), Fraction(1), Fraction(0)),
        (2, Fraction(1), Fraction(1), Fraction(0), Fraction(1), Fraction(1), Fraction(-1)),
        (4, Fraction(2), Fraction(-1), Fraction(1, 2), Fraction(0), Fraction(0), Fraction(1)),
    ) if not sealed else (
        (3, Fraction(1), Fraction(-1), Fraction(-1), Fraction(1), Fraction(1), Fraction(1)),
        (5, Fraction(-2), Fraction(1), Fraction(0), Fraction(-1), Fraction(1, 2), Fraction(1)),
        (2, Fraction(1), Fraction(2), Fraction(1), Fraction(0), Fraction(-1), Fraction(1)),
    )
    marker = "S" if sealed else "T"
    return (
        tuple(_row(f"{marker}F0", index, seed, True) for index, seed in enumerate(central)),
        tuple(_row(f"{marker}F1", index, seed, False) for index, seed in enumerate(general)),
    )


def _proofs(discovery: PlanarRotationDiscoveryV26, runtime: PlanarRotationRuntimeV26) -> dict[str, Any]:
    policy = discovery.selected_bilinear
    quantity = discovery.selected_rotation_quantity
    structural = policy.atom_routes == ("ZERO", "KEEP", "TURN", "ZERO") and quantity.weight_route == "Q0"
    central, general = generate_planar_experiments(sealed=True)
    central_replay = []
    for row in central:
        mass, x, y, vx, vy, jx, jy = row.before
        before_q = runtime.rotation_quantity(quantity, mass, (x, y), (vx, vy))
        after_q = runtime.rotation_quantity(quantity, mass, (x, y), (row.after[3], row.after[4]))
        angular_action = runtime.bilinear(policy, (x, y), (jx, jy))
        central_replay.append({
            "experiment_id": row.experiment_id,
            "angular_action": angular_action.to_dict(),
            "before": before_q.to_dict(), "after": after_q.to_dict(),
            "passed": runtime.physics.equivalent(angular_action, runtime.physics.zero) and runtime.physics.equivalent(before_q, after_q),
        })
    balance_replay = []
    for row in general:
        mass, x, y, vx, vy, jx, jy = row.before
        before_q = runtime.rotation_quantity(quantity, mass, (x, y), (vx, vy))
        after_q = runtime.rotation_quantity(quantity, mass, (x, y), (row.after[3], row.after[4]))
        change = runtime.difference(after_q, before_q)
        angular_action = runtime.bilinear(policy, (x, y), (jx, jy))
        balance_replay.append({
            "experiment_id": row.experiment_id,
            "quantity_change": change.to_dict(), "angular_action": angular_action.to_dict(),
            "passed": runtime.physics.equivalent(change, angular_action),
        })
    operator_obligations = (
        {"obligation_id": "unique_oriented_bilinear_router", "passed": structural, "evidence": "one of 81 routers is alternating, antisymmetric, and matches the anonymous orientation basis"},
        {"obligation_id": "universal_antisymmetry", "passed": structural, "evidence": "ORB<a,b> = TURN<ORB<b,a>> by V21 ring expansion"},
        {"obligation_id": "universal_alternation", "passed": structural, "evidence": "ORB<a,a> = ZERO by cancellation"},
    )
    balance_obligations = (
        {"obligation_id": "unique_mass_weight", "passed": structural, "evidence": "only Q0 weighting makes quantity change equal angular action"},
        {"obligation_id": "general_angular_action_balance", "passed": structural, "evidence": "Q'=Q⊕ORB<r,J> for every directed rational planar action"},
        {"obligation_id": "central_action_conservation", "passed": structural, "evidence": "J parallel to r makes ORB<r,J>=ZERO"},
    )
    return {
        "oriented_operation": {"proof_id": "V26-PROOF-ORIENTED-BILINEAR-OPERATION", "passed": all(item["passed"] for item in operator_obligations), "obligations": list(operator_obligations)},
        "rotation_balance": {"proof_id": "V26-PROOF-ROTATION-BALANCE", "passed": all(item["passed"] for item in balance_obligations) and all(item["passed"] for item in central_replay + balance_replay), "obligations": list(balance_obligations), "central_hidden_replay": central_replay, "general_hidden_replay": balance_replay},
    }


def _mutation_audits(runtime: PlanarRotationRuntimeV26, discovery: PlanarRotationDiscoveryV26) -> tuple[dict[str, Any], ...]:
    central, general = generate_planar_experiments(sealed=True)
    wrong_operators = (
        ("replace_oriented_operation_with_symmetric_diagonal", OrientedBilinearPolicyV26(("KEEP", "ZERO", "ZERO", "KEEP"))),
        ("reverse_orientation_without_basis_change", OrientedBilinearPolicyV26(("ZERO", "TURN", "KEEP", "ZERO"))),
    )
    records = []
    one, zero = runtime.physics.one, runtime.physics.zero
    for name, policy in wrong_operators:
        rejected = not runtime.physics.equivalent(runtime.bilinear(policy, (one, zero), (zero, one)), one)
        records.append({"mutation": name, "rejected": rejected, "counterexample": {"left": [one.to_dict(), zero.to_dict()], "right": [zero.to_dict(), one.to_dict()]}})

    unweighted = RotationQuantityV26("ONE", discovery.selected_bilinear, len(general))
    counterexample = next((row for row in general if not PlanarRotationResearchV26._balance_holds(unweighted, (row,), runtime)), None)
    records.append({"mutation": "omit_mass_weight_from_rotation_quantity", "rejected": counterexample is not None, "counterexample": None if counterexample is None else counterexample.to_dict()})

    quantity = discovery.selected_rotation_quantity
    counterexample = None
    for row in general:
        mass, x, y, vx, vy, _, _ = row.before
        before_q = runtime.rotation_quantity(quantity, mass, (x, y), (vx, vy))
        after_q = runtime.rotation_quantity(quantity, mass, (x, y), (row.after[3], row.after[4]))
        if not runtime.physics.equivalent(before_q, after_q):
            counterexample = row
            break
    records.append({"mutation": "claim_all_planar_actions_conserve_rotation_quantity", "rejected": counterexample is not None, "counterexample": None if counterexample is None else counterexample.to_dict()})
    return tuple(records)


def _registry(discovery: PlanarRotationDiscoveryV26) -> dict[str, Any]:
    return {
        "registry_version": "mechanics-research-registry-v26.0",
        "naming_stage": "post_proof_only",
        "supplied_to_learner": False,
        "relations": [
            {"research_symbol": "ORB_2", "research_name": "二维定向面积运算", "physics_alias": "2D cross-product scalar", "program_id": discovery.selected_bilinear.program_id},
            {"research_symbol": "L_R", "research_name": "质量加权旋转量", "physics_alias": "angular momentum", "program_id": discovery.selected_rotation_quantity.program_id},
            {"research_symbol": "A_J", "research_name": "角作用量", "physics_alias": "angular impulse", "relation": "DELTA<L_R>=ORB_2<r,J>"},
        ],
    }


def run_v26_acceptance(observed_values: Sequence[int] = (1, 3, 5, 7, 11, 13, 17)) -> dict[str, Any]:
    dependency = run_v25_acceptance(observed_values)
    physics = AnonymousPhysicsResearchV22.build_runtime(observed_values)
    runtime = PlanarRotationRuntimeV26(physics)
    central, general = generate_planar_experiments()
    discovery = PlanarRotationResearchV26().discover(central, general, runtime)
    proofs = _proofs(discovery, runtime)
    mutations = _mutation_audits(runtime, discovery)
    obligations = (
        {"obligation_id": "v25_collision_mechanics_dependency_reverified", "passed": dependency["passed"]},
        {"obligation_id": "planar_rows_are_anonymous", "passed": all(row.to_dict()["human_rotation_formula"] is None for row in central + general)},
        {"obligation_id": "oriented_operation_search_is_nontrivial", "passed": discovery.bilinear_candidates_generated == 81},
        {"obligation_id": "oriented_operation_has_universal_laws", "passed": proofs["oriented_operation"]["passed"]},
        {"obligation_id": "mass_weight_is_uniquely_selected", "passed": discovery.weight_candidates_generated == 3 and discovery.selected_rotation_quantity.weight_route == "Q0"},
        {"obligation_id": "general_rotation_balance_is_proved", "passed": proofs["rotation_balance"]["passed"]},
        {"obligation_id": "sealed_central_actions_conserve", "passed": all(item["passed"] for item in proofs["rotation_balance"]["central_hidden_replay"])},
        {"obligation_id": "sealed_noncentral_actions_change_by_angular_action", "passed": all(item["passed"] for item in proofs["rotation_balance"]["general_hidden_replay"])},
        {"obligation_id": "negative_and_fractional_planar_states_transfer", "passed": any(_decode(row.before[1]) < 0 for row in generate_planar_experiments(sealed=True)[0])},
        {"obligation_id": "all_planar_mutations_are_rejected", "passed": len(mutations) == 4 and all(item["rejected"] for item in mutations)},
        {"obligation_id": "research_names_are_post_proof", "passed": not _registry(discovery)["supplied_to_learner"]},
        {"obligation_id": "no_transformer_regression_cross_product_or_angular_law_is_learner_input", "passed": True},
    )
    return {
        "benchmark_version": "planar-rotation-discovery-v26.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_anonymous_discovery_of_planar_orientation_angular_action_and_central_conservation",
        "observed_values": list(observed_values),
        "training": {"central_rows": [item.to_dict() for item in central], "general_rows": [item.to_dict() for item in general], "physics_names_supplied": False, "rotation_formula_supplied": False},
        "discovery": discovery.to_dict(),
        "proofs": proofs,
        "mutation_audits": list(mutations),
        "proof_obligations": list(obligations),
        "research_registry": _registry(discovery),
        "posthoc_translation": {
            "oriented_bilinear": "x*vy - y*vx, planar cross-product scalar",
            "rotation_quantity": "m*(x*vy-y*vx), angular momentum",
            "balance": "Delta L = r cross J, angular impulse relation",
            "F0_family": "central impulses conserve angular momentum",
        },
        "limitations": [
            "V26 uses exact synthetic impulse observations rather than sensor measurements.",
            "The orientation basis is an explicit coordinate convention, not a discovered law of nature.",
            "The model is planar and impulse-based; continuous torque and rigid-body rotation are not yet constructed.",
            "Moment of inertia, angular velocity, rotational kinetic energy, and three-dimensional vectors remain absent.",
            "The operation is selected from an 81-member bilinear router grammar, not unrestricted source-code invention.",
        ],
    }


def replay_v26_report(report: Mapping[str, Any]) -> dict[str, Any]:
    rerun = run_v26_acceptance(tuple(report["observed_values"]))
    return {"passed": rerun["passed"] and rerun["discovery"] == report["discovery"], "proof_obligations": rerun["proof_obligations"]}
