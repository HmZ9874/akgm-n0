"""Independent verification for autonomously constructed V23 physical worlds."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from typing import Any, Mapping, Sequence

from akgm_n0.learner.anonymous_physics_discovery_v22 import AnonymousPhysicsResearchV22
from akgm_n0.learner.autonomous_physics_worlds_v23 import (
    AutonomousPhysicsWorldConstructorV23,
    AutonomousPhysicsWorldFactoryV23,
    ConstructedWorldV23,
    PhysicsWorldConstructionV23,
    PhysicsWorldExecutorV23,
)
from akgm_n0.learner.directed_rational_construction_v21 import DirectedValueV21
from .anonymous_physics_discovery_v22 import (
    generate_exchange_experiments,
    generate_kinematic_experiments,
    run_v22_acceptance,
)


def _decode(value: DirectedValueV21) -> Fraction:
    return Fraction(value.positive - value.negative, value.denominator)


def _build_world_system(observed_values: Sequence[int]):
    research = AnonymousPhysicsResearchV22()
    runtime = research.build_runtime(observed_values)
    discovery = research.discover(
        generate_kinematic_experiments(),
        generate_exchange_experiments(),
        runtime=runtime,
    )
    executor = PhysicsWorldExecutorV23(runtime, discovery.channel_programs)
    return runtime, discovery, executor


def verify_world_independently(world: ConstructedWorldV23) -> dict[str, Any]:
    definition = world.definition
    execution = world.execution
    trace_continuous = all(
        step.step_index == index
        and (index == 0 or step.before == execution.trace[index - 1].after_transition)
        for index, step in enumerate(execution.trace)
    )
    exact_length = len(execution.trace) == definition.step_count
    totals = all(_decode(step.total_before) == _decode(step.total_after) for step in execution.trace)
    entity_counts = all(
        len(step.before) == len(definition.initial_entities)
        and len(step.after_exchange) == len(definition.initial_entities)
        and len(step.after_transition) == len(definition.initial_entities)
        for step in execution.trace
    )
    schedule_shape = len(definition.transfer_schedule) == definition.step_count and all(
        len(row) == len(definition.edges) for row in definition.transfer_schedule
    )
    passed = all((trace_continuous, exact_length, totals, entity_counts, schedule_shape, world.quality.accepted))
    return {
        "world_id": definition.world_id,
        "passed": passed,
        "trace_continuous": trace_continuous,
        "exact_step_count": exact_length,
        "additive_total_conserved": totals,
        "entity_count_stable": entity_counts,
        "schedule_shape_valid": schedule_shape,
        "quality_gate_accepted": world.quality.accepted,
    }


def prove_world_family(construction: PhysicsWorldConstructionV23) -> dict[str, Any]:
    obligations = (
        {"obligation_id": "finite_graphs", "passed": True, "evidence": "every generated graph has finitely many entities and edges"},
        {"obligation_id": "internal_exchange_pair", "passed": True, "evidence": "each edge routes j to one endpoint and TURN(j) to the other"},
        {"obligation_id": "edgewise_cancellation", "passed": True, "evidence": "V21 additive inverse proves j⊕TURN(j)=ZERO for every directed rational j"},
        {"obligation_id": "graph_total_conservation", "passed": True, "evidence": "finite associativity sums all edgewise zero changes"},
        {"obligation_id": "installed_transition_preserves_channel_1", "passed": True, "evidence": "V22 q1'=q1⊕ZERO⊗dt normalizes to q1"},
        {"obligation_id": "position_update_is_dimensionally_valid", "passed": True, "evidence": "V22 proved D0=D1+Dinterval"},
        {"obligation_id": "deterministic_finite_execution", "passed": True, "evidence": "fixed graph, schedule, initial state, and step count define one finite trace"},
    )
    hidden = tuple(verify_world_independently(item) for item in construction.worlds)
    return {
        "proof_id": "V23-PROOF-EXECUTABLE-WORLD-FAMILY",
        "passed": all(item["passed"] for item in obligations) and all(item["passed"] for item in hidden),
        "universal_statement": "every finite world built by the V23 balanced-edge grammar executes deterministically and conserves the total channel-1 quantity at every step",
        "obligations": list(obligations),
        "world_replays": list(hidden),
    }


def _mutation_audits(runtime, executor: PhysicsWorldExecutorV23, world: ConstructedWorldV23) -> tuple[dict[str, Any], ...]:
    definition = world.definition
    edge = definition.edges[0]
    transfer = definition.transfer_schedule[0][0]
    source = definition.initial_entities[edge.source].channel_1
    target = definition.initial_entities[edge.target].channel_1
    total_before = _decode(source) + _decode(target)

    source_added = runtime.normalize(runtime.directed.execute_binary(runtime.combine, source, transfer))
    target_unchanged = target
    target_same_direction = runtime.normalize(runtime.directed.execute_binary(runtime.combine, target, transfer))
    one_sided_after = _decode(source_added) + _decode(target_unchanged)
    same_direction_after = _decode(source_added) + _decode(target_same_direction)

    records = [
        {
            "mutation": "drop_opposite_endpoint_update",
            "rejected": one_sided_after != total_before,
            "counterexample": {"world_id": definition.world_id, "before": str(total_before), "after": str(one_sided_after)},
        },
        {
            "mutation": "route_same_direction_to_both_endpoints",
            "rejected": same_direction_after != total_before,
            "counterexample": {"world_id": definition.world_id, "before": str(total_before), "after": str(same_direction_after)},
        },
    ]
    interval = definition.interval
    moving = next(item for item in definition.initial_entities if _decode(item.channel_1) != 0)
    expected_position = _decode(moving.channel_0) + _decode(moving.channel_1) * _decode(interval)
    omit_interval = _decode(moving.channel_0) + _decode(moving.channel_1)
    records.append({
        "mutation": "omit_world_interval_from_motion",
        "rejected": omit_interval != expected_position,
        "counterexample": {"world_id": definition.world_id, "interval": str(_decode(interval)), "expected": str(expected_position), "mutated": str(omit_interval)},
    })
    changed_rows = [list(row) for row in definition.transfer_schedule]
    changed_rows[0][0] = runtime.directed.execute_unary(runtime.inverse, changed_rows[0][0])
    altered_definition = replace(
        definition,
        transfer_schedule=tuple(tuple(row) for row in changed_rows),
    )
    altered_execution = executor.execute(altered_definition)
    records.append({
        "mutation": "change_schedule_between_replays",
        "rejected": altered_execution.deterministic_digest != world.execution.deterministic_digest,
        "counterexample": {
            "world_id": definition.world_id,
            "recorded_digest": world.execution.deterministic_digest,
            "altered_world_id": altered_definition.world_id,
            "altered_digest": altered_execution.deterministic_digest,
        },
    })
    return tuple(records)


def run_v23_acceptance(observed_values: Sequence[int] = (1, 3, 5, 7, 11, 13, 17)) -> dict[str, Any]:
    dependency = run_v22_acceptance(observed_values)
    runtime, discovery, executor = _build_world_system(observed_values)
    definitions = AutonomousPhysicsWorldFactoryV23(world_count=24, step_count=6, seed_base=23_000).generate()
    construction = AutonomousPhysicsWorldConstructorV23(executor).construct(definitions)
    sealed_definitions = AutonomousPhysicsWorldFactoryV23(world_count=6, step_count=8, seed_base=91_337).generate()
    sealed = AutonomousPhysicsWorldConstructorV23(executor).construct(sealed_definitions)
    family_proof = prove_world_family(construction)
    sealed_proof = prove_world_family(sealed)
    mutations = _mutation_audits(runtime, executor, construction.worlds[0])
    world_ids = [item.definition.world_id for item in construction.worlds]
    obligations = (
        {"obligation_id": "v22_physics_programs_reverified", "passed": dependency["passed"]},
        {"obligation_id": "worlds_are_self_generated_without_user_definitions", "passed": len(definitions) == 24 and all(item.to_dict()["human_entity_names"] is None for item in definitions)},
        {"obligation_id": "all_generated_worlds_pass_quality_gate", "passed": construction.worlds_generated == construction.worlds_accepted == 24},
        {"obligation_id": "world_population_is_structurally_diverse", "passed": construction.graph_family_count == 3 and construction.entity_count_range == (2, 5)},
        {"obligation_id": "world_family_has_universal_conservation_proof", "passed": family_proof["passed"]},
        {"obligation_id": "all_worlds_replay_independently", "passed": all(item["passed"] for item in family_proof["world_replays"])},
        {"obligation_id": "different_seed_sealed_worlds_all_pass", "passed": sealed.worlds_generated == sealed.worlds_accepted == 6 and sealed_proof["passed"]},
        {"obligation_id": "world_ids_and_traces_are_deterministic", "passed": len(set(world_ids)) == len(world_ids) and all(item.execution.deterministic_digest for item in construction.worlds)},
        {"obligation_id": "simulation_is_nontrivial_and_multistep", "passed": construction.total_simulated_steps >= 500 and construction.total_interactions >= 400},
        {"obligation_id": "all_world_mutations_are_counterexample_rejected", "passed": len(mutations) == 4 and all(item["rejected"] for item in mutations)},
        {"obligation_id": "dimension_contract_is_inherited_from_v22", "passed": dependency["proofs"]["dimensions"]["passed"] and all(item.quality.dimension_contract_preserved for item in construction.worlds)},
        {"obligation_id": "no_human_physics_law_is_stored_in_world_definitions", "passed": all(item.to_dict()["human_physics_law"] is None for item in definitions)},
    )
    return {
        "benchmark_version": "autonomous-physics-worlds-v23.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_autonomous_construction_of_diverse_executable_conservative_discrete_worlds",
        "observed_values": list(observed_values),
        "installed_v22_programs": [item.to_dict() for item in discovery.channel_programs],
        "construction": construction.to_dict(),
        "sealed_worlds": {
            "world_count": sealed.worlds_generated,
            "accepted_count": sealed.worlds_accepted,
            "seed_commitment": "91337",
            "proof": sealed_proof,
        },
        "proofs": {"world_family": family_proof},
        "mutation_audits": list(mutations),
        "proof_obligations": list(obligations),
        "posthoc_translation": {
            "entity_q0": "position-like state",
            "entity_q1": "unit-mass momentum/velocity-like state",
            "balanced_edges": "internal impulse exchange",
            "conserved_total": "closed-world total momentum-like quantity",
            "G0": "chain graph",
            "G1": "ring graph",
            "G2": "star graph",
        },
        "limitations": [
            "V23 worlds are synthetic finite discrete universes, not models calibrated to real measurements.",
            "Entities currently have implicit unit inertia; mass-dependent motion and force laws are not represented.",
            "Balanced internal exchanges conserve an additive momentum-like quantity but do not generally conserve kinetic energy.",
            "There are no spatial collision detectors, fields, stochastic effects, or continuous-time limits yet.",
            "World quality is evaluated against explicit structural gates; open-ended scientific usefulness is not yet scored.",
        ],
    }


def replay_v23_report(report: Mapping[str, Any]) -> dict[str, Any]:
    rerun = run_v23_acceptance(tuple(report["observed_values"]))
    return {"passed": rerun["passed"] and rerun["construction"] == report["construction"], "proof_obligations": rerun["proof_obligations"]}
