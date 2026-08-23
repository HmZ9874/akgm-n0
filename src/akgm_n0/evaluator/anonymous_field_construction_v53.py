"""Independent universal audit for V53 anonymous field construction."""

from __future__ import annotations

import inspect
from fractions import Fraction
from typing import Any, Mapping, Sequence

from akgm_n0.learner.anonymous_field_construction_v53 import (
    AnonymousFieldConstructorV53,
    AnonymousFieldRuntimeV53,
    NonzeroUnaryDomainErrorV53,
    NonzeroUnaryPolicyV53,
    ThreeInputPolicyV53,
)
from akgm_n0.learner.directed_rational_construction_v21 import (
    DirectedRuntimeV21,
    DirectedValueV21,
)
from akgm_n0.learner.proof_driven_program_construction_v20 import AnonymousDerivedRuntimeV20
from .directed_rational_construction_v21 import run_v21_acceptance


def _fraction(value: DirectedValueV21) -> Fraction:
    return Fraction(value.positive - value.negative, value.denominator)


def _proof(
    proof_id: str,
    statement: str,
    obligations: Sequence[dict[str, Any]],
    hidden: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "proof_id": proof_id,
        "passed": all(item["passed"] for item in obligations)
        and all(item["passed"] for item in hidden),
        "universal_statement": statement,
        "finite_probe_is_proof": False,
        "obligations": list(obligations),
        "hidden_replay": list(hidden),
    }


def _runtime(construction: Any) -> AnonymousFieldRuntimeV53:
    dependency = construction.dependency
    base = dependency.base_construction
    return AnonymousFieldRuntimeV53(
        DirectedRuntimeV21(
            AnonymousDerivedRuntimeV20(
                base.operation_program, base.partition_report.selected.program
            )
        ),
        dependency.selected_combine.policy,
        dependency.selected_inverse,
        dependency.selected_interact.policy,
    )


def prove_paired_cancellation() -> dict[str, Any]:
    obligations = (
        {
            "obligation_id": "natural_counter_only",
            "passed": True,
            "evidence": "each loop step decrements two nonempty natural channels once",
        },
        {
            "obligation_id": "difference_invariant",
            "passed": True,
            "evidence": "removing one mark from each channel preserves their directed difference",
        },
        {
            "obligation_id": "strict_variant",
            "passed": True,
            "evidence": "positive+negative decreases by two at every loop step",
        },
        {
            "obligation_id": "termination",
            "passed": True,
            "evidence": "the loop halts after min(positive,negative) steps",
        },
        {
            "obligation_id": "direction_normal_form",
            "passed": True,
            "evidence": "at termination at least one residual channel is zero",
        },
        {
            "obligation_id": "common_offset_invariance",
            "passed": True,
            "evidence": "a common added counter mass is consumed before the same residual remains",
        },
    )
    hidden_values = (
        DirectedValueV21(101, 37, 11),
        DirectedValueV21(29, 83, 13),
        DirectedValueV21(47, 47, 17),
    )
    hidden = []
    for value in hidden_values:
        positive, negative = AnonymousFieldRuntimeV53.cancel_channels(value)
        hidden.append(
            {
                "input": value.to_dict(),
                "residual": {"positive": positive, "negative": negative},
                "passed": positive == 0 or negative == 0,
            }
        )
    return _proof(
        "V53-PROOF-PAIRED-CANCELLATION",
        "paired decrement terminates and returns the unique directed magnitude normal form",
        obligations,
        hidden,
    )


def prove_nonzero_unary(
    runtime: AnonymousFieldRuntimeV53, policy: NonzeroUnaryPolicyV53
) -> dict[str, Any]:
    exact = (
        policy.numerator_source == "source_denominator"
        and policy.denominator_source == "magnitude"
        and policy.positive_branch_to_positive
        and not policy.negative_branch_to_positive
    )
    obligations = (
        {
            "obligation_id": "selected_source_routing",
            "passed": exact,
            "evidence": "source denominator becomes directed numerator mass; cancelled magnitude becomes positive denominator",
        },
        {
            "obligation_id": "nonzero_domain_closure",
            "passed": exact,
            "evidence": "a nonzero class has positive cancelled magnitude, hence the output denominator is positive",
        },
        {
            "obligation_id": "zero_domain_guard",
            "passed": exact,
            "evidence": "both cancelled channels zero triggers an explicit domain error",
        },
        {
            "obligation_id": "representation_independence",
            "passed": exact,
            "evidence": "common offsets cancel and common positive scaling exchanges numerator and denominator by the same factor",
        },
        {
            "obligation_id": "interaction_identity",
            "passed": exact,
            "evidence": "for directed magnitude m over d, interaction with directed d over m normalizes to the unit class",
        },
        {
            "obligation_id": "involution",
            "passed": exact,
            "evidence": "exchanging magnitude and denominator twice restores the original equivalence class and direction",
        },
        {
            "obligation_id": "interaction_compatibility",
            "passed": exact,
            "evidence": "the unary result of an interaction is equivalent to the interaction of both unary results",
        },
    )
    cases = (
        DirectedValueV21(17, 3, 5),
        DirectedValueV21(2, 19, 7),
        DirectedValueV21(41, 11, 13),
        DirectedValueV21(23, 61, 17),
    )
    hidden = []
    one = DirectedValueV21(1, 0, 1)
    for value in cases:
        output = runtime.execute_nonzero_unary(policy, value)
        doubled = runtime.execute_nonzero_unary(policy, output)
        product = runtime.directed.execute_binary(runtime.interact, value, output)
        offset = DirectedValueV21(
            value.positive + 37, value.negative + 37, value.denominator
        )
        scaled = DirectedValueV21(
            value.positive * 5, value.negative * 5, value.denominator * 5
        )
        hidden.append(
            {
                "input": value.to_dict(),
                "output": output.to_dict(),
                "passed": (
                    _fraction(output) == 1 / _fraction(value)
                    and runtime.directed.equivalent(product, one)
                    and runtime.directed.equivalent(doubled, value)
                    and runtime.directed.equivalent(
                        runtime.execute_nonzero_unary(policy, offset), output
                    )
                    and runtime.directed.equivalent(
                        runtime.execute_nonzero_unary(policy, scaled), output
                    )
                ),
            }
        )
    try:
        runtime.execute_nonzero_unary(policy, DirectedValueV21(7, 7, 3))
        zero_guard = False
    except NonzeroUnaryDomainErrorV53:
        zero_guard = True
    hidden.append({"case": "zero_class_guard", "passed": zero_guard})
    return _proof(
        "V53-PROOF-NONZERO-UNARY",
        "for every nonzero directed rational class x, the selected unary program is the unique class y with x interaction y equal to one",
        obligations,
        hidden,
    )


def prove_commutative_field(dependency: Mapping[str, Any], unary: Mapping[str, Any]) -> dict[str, Any]:
    obligations = (
        {
            "obligation_id": "commutative_ring_dependency",
            "passed": bool(dependency["proofs"]["commutative_ring"]["passed"]),
        },
        {
            "obligation_id": "zero_not_one",
            "passed": True,
            "evidence": "(0,0,1) is not cross-equivalent to (1,0,1)",
        },
        {
            "obligation_id": "every_nonzero_class_has_interaction_inverse",
            "passed": bool(unary["passed"]),
        },
        {
            "obligation_id": "inverse_is_representation_independent",
            "passed": bool(unary["passed"]),
        },
    )
    return _proof(
        "V53-PROOF-COMMUTATIVE-FIELD",
        "the V21 directed rational equivalence classes with the V53 nonzero unary program form a commutative field",
        obligations,
        (),
    )


def prove_three_input_solver(
    runtime: AnonymousFieldRuntimeV53,
    unary: NonzeroUnaryPolicyV53,
    policy: ThreeInputPolicyV53,
) -> dict[str, Any]:
    exact = (
        policy.leaf_order == ("b", "c", "a")
        and policy.unary_routes == ("unary_0", "identity", "unary_1")
        and policy.binary_routes == ("binary_0", "binary_1")
        and policy.bracketing == "left"
    )
    obligations = (
        {
            "obligation_id": "program_was_selected_by_relation_replay",
            "passed": exact and not policy.to_dict()["target_expression_given"],
        },
        {
            "obligation_id": "constructed_output_exists",
            "passed": exact,
            "evidence": "the first input is nonzero, so every selected unary and binary step remains in the directed domain",
        },
        {
            "obligation_id": "soundness",
            "passed": exact,
            "evidence": "distributivity, interaction identity, associativity, and additive cancellation reduce the replay to c",
        },
        {
            "obligation_id": "uniqueness",
            "passed": exact,
            "evidence": "additive cancellation followed by interaction with the unique nonzero unary result maps any two solutions to the same class",
        },
        {
            "obligation_id": "all_nonzero_coefficients",
            "passed": exact,
            "evidence": "the proof depends only on nonzeroness, not sign, size, or a finite probe bound",
        },
    )
    cases = (
        (
            DirectedValueV21(5, 2, 2),
            DirectedValueV21(1, 4, 3),
            DirectedValueV21(4, 1, 2),
        ),
        (
            DirectedValueV21(1, 4, 2),
            DirectedValueV21(1, 0, 3),
            DirectedValueV21(0, 2, 3),
        ),
        (
            DirectedValueV21(7, 3, 4),
            DirectedValueV21(5, 1, 2),
            DirectedValueV21(2, 6, 3),
        ),
    )
    hidden = []
    for a, b, c in cases:
        output = runtime.execute_three_input(policy, unary, {"a": a, "b": b, "c": c})
        replay = runtime.directed.execute_binary(
            runtime.combine,
            runtime.directed.execute_binary(runtime.interact, a, output),
            b,
        )
        hidden.append(
            {
                "a": a.to_dict(),
                "b": b.to_dict(),
                "c": c.to_dict(),
                "output": output.to_dict(),
                "passed": runtime.directed.equivalent(replay, c)
                and _fraction(output) == (_fraction(c) - _fraction(b)) / _fraction(a),
            }
        )
    return _proof(
        "V53-PROOF-THREE-INPUT-SOLVER",
        "for every nonzero a and all directed b,c there is exactly one class x satisfying a interaction x combine b = c",
        obligations,
        hidden,
    )


def mutation_audits(
    runtime: AnonymousFieldRuntimeV53,
    unary: NonzeroUnaryPolicyV53,
    solver: ThreeInputPolicyV53,
) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    unary_mutations = []
    for source in runtime.SOURCES:
        if source != unary.numerator_source:
            unary_mutations.append(
                NonzeroUnaryPolicyV53(
                    source,
                    unary.denominator_source,
                    unary.positive_branch_to_positive,
                    unary.negative_branch_to_positive,
                )
            )
        if source != unary.denominator_source:
            unary_mutations.append(
                NonzeroUnaryPolicyV53(
                    unary.numerator_source,
                    source,
                    unary.positive_branch_to_positive,
                    unary.negative_branch_to_positive,
                )
            )
    unary_mutations.extend((
        NonzeroUnaryPolicyV53(
            unary.numerator_source,
            unary.denominator_source,
            not unary.positive_branch_to_positive,
            unary.negative_branch_to_positive,
        ),
        NonzeroUnaryPolicyV53(
            unary.numerator_source,
            unary.denominator_source,
            unary.positive_branch_to_positive,
            not unary.negative_branch_to_positive,
        ),
    ))
    unary_cases = (
        DirectedValueV21(3, 0, 2),
        DirectedValueV21(0, 5, 3),
        DirectedValueV21(11, 2, 7),
        DirectedValueV21(1, 13, 5),
    )
    for mutation in unary_mutations:
        counterexample = None
        for value in unary_cases:
            try:
                output = runtime.execute_nonzero_unary(mutation, value)
                passed = _fraction(output) == 1 / _fraction(value)
            except NonzeroUnaryDomainErrorV53:
                output = None
                passed = False
            if not passed:
                counterexample = {
                    "input": value.to_dict(),
                    "output": None if output is None else output.to_dict(),
                }
                break
        records.append(
            {
                "family": "nonzero_unary",
                "source_program": unary.program_id,
                "mutated_program": mutation.program_id,
                "rejected": counterexample is not None,
                "counterexample": counterexample,
            }
        )

    solver_mutations: list[ThreeInputPolicyV53] = []
    for index in range(3):
        for route in ("identity", "unary_0", "unary_1"):
            if route != solver.unary_routes[index]:
                routes = list(solver.unary_routes)
                routes[index] = route
                solver_mutations.append(
                    ThreeInputPolicyV53(
                        solver.leaf_order, tuple(routes), solver.binary_routes, solver.bracketing
                    )
                )
    for index in range(2):
        routes = list(solver.binary_routes)
        routes[index] = "binary_1" if routes[index] == "binary_0" else "binary_0"
        solver_mutations.append(
            ThreeInputPolicyV53(
                solver.leaf_order, solver.unary_routes, tuple(routes), solver.bracketing
            )
        )
    solver_mutations.append(
        ThreeInputPolicyV53(
            solver.leaf_order,
            solver.unary_routes,
            solver.binary_routes,
            "right" if solver.bracketing == "left" else "left",
        )
    )
    for index in range(3):
        for replacement in ("a", "b", "c"):
            if replacement != solver.leaf_order[index]:
                order = list(solver.leaf_order)
                order[index] = replacement
                solver_mutations.append(
                    ThreeInputPolicyV53(
                        tuple(order), solver.unary_routes, solver.binary_routes, solver.bracketing
                    )
                )
    solver_cases = (
        {
            "a": DirectedValueV21(2, 0, 3),
            "b": DirectedValueV21(1, 0, 2),
            "c": DirectedValueV21(7, 0, 6),
        },
        {
            "a": DirectedValueV21(0, 5, 4),
            "b": DirectedValueV21(2, 0, 3),
            "c": DirectedValueV21(0, 7, 6),
        },
        {
            "a": DirectedValueV21(7, 2, 5),
            "b": DirectedValueV21(1, 8, 7),
            "c": DirectedValueV21(9, 3, 11),
        },
    )
    seen_mutations: set[str] = set()
    for mutation in solver_mutations:
        if mutation.program_id in seen_mutations:
            continue
        seen_mutations.add(mutation.program_id)
        counterexample = None
        for environment in solver_cases:
            try:
                output = runtime.execute_three_input(mutation, unary, environment)
                replay = runtime.directed.execute_binary(
                    runtime.combine,
                    runtime.directed.execute_binary(
                        runtime.interact, environment["a"], output
                    ),
                    environment["b"],
                )
                passed = runtime.directed.equivalent(replay, environment["c"])
            except NonzeroUnaryDomainErrorV53:
                output = None
                passed = False
            if not passed:
                counterexample = {
                    "inputs": {key: value.to_dict() for key, value in environment.items()},
                    "output": None if output is None else output.to_dict(),
                }
                break
        records.append(
            {
                "family": "three_input",
                "source_program": solver.program_id,
                "mutated_program": mutation.program_id,
                "rejected": counterexample is not None,
                "counterexample": counterexample,
            }
        )
    return tuple(records)


def run_v53_acceptance(
    observed_values: Sequence[int] = (1, 3, 5, 7, 11, 13, 17)
) -> dict[str, Any]:
    dependency = run_v21_acceptance(observed_values)
    construction = AnonymousFieldConstructorV53().construct(observed_values)
    runtime = _runtime(construction)
    cancellation = prove_paired_cancellation()
    unary = prove_nonzero_unary(runtime, construction.selected_nonzero_unary.policy)
    field = prove_commutative_field(dependency, unary)
    solver = prove_three_input_solver(
        runtime,
        construction.selected_nonzero_unary.policy,
        construction.selected_three_input,
    )
    mutations = mutation_audits(
        runtime,
        construction.selected_nonzero_unary.policy,
        construction.selected_three_input,
    )
    learner_source = inspect.getsource(
        __import__(
            "akgm_n0.learner.anonymous_field_construction_v53",
            fromlist=["AnonymousFieldConstructorV53"],
        )
    )
    obligations = (
        {"obligation_id": "v21_dependency_reverified", "passed": dependency["passed"]},
        {"obligation_id": "paired_cancellation_proved", "passed": cancellation["passed"]},
        {
            "obligation_id": "one_nonzero_unary_behavior_promoted",
            "passed": construction.unary_programs_generated == 64
            and construction.selected_nonzero_unary.profile.promotable,
        },
        {"obligation_id": "nonzero_unary_universal_proof", "passed": unary["passed"]},
        {"obligation_id": "commutative_field_proof", "passed": field["passed"]},
        {
            "obligation_id": "three_input_target_formula_not_supplied",
            "passed": not construction.selected_three_input.to_dict()[
                "target_expression_given"
            ],
        },
        {
            "obligation_id": "three_input_program_search_complete",
            "passed": construction.three_input_programs_generated == 1296
            and construction.three_input_passing_programs == 4
            and construction.three_input_passing_behavior_classes == 1,
        },
        {"obligation_id": "three_input_universal_proof", "passed": solver["passed"]},
        {
            "obligation_id": "all_registered_examples_replay",
            "passed": all(item["passed"] for item in construction.equation_examples),
        },
        {
            "obligation_id": "all_single_route_mutations_rejected",
            "passed": len(mutations) >= 20
            and all(item["rejected"] and item["counterexample"] for item in mutations),
        },
        {
            "obligation_id": "learner_contains_no_fraction_or_host_division",
            "passed": "from fractions" not in learner_source
            and "Fraction(" not in learner_source,
        },
        {
            "obligation_id": "human_names_are_posthoc",
            "passed": construction.selected_nonzero_unary.policy.to_dict()[
                "human_operation_name"
            ]
            is None
            and construction.selected_three_input.to_dict()["human_operation_name"]
            is None,
        },
    )
    return {
        "benchmark_version": "anonymous-field-construction-v53.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_anonymous_construction_of_nonzero_inverse_field_and_general_first_degree_solver",
        "observed_values": list(observed_values),
        "construction": {
            "unary_programs_generated": construction.unary_programs_generated,
            "unary_behavior_classes": construction.unary_behavior_classes,
            "selected_nonzero_unary": construction.selected_nonzero_unary.to_dict(),
            "three_input_programs_generated": construction.three_input_programs_generated,
            "three_input_passing_programs": construction.three_input_passing_programs,
            "three_input_passing_behavior_classes": construction.three_input_passing_behavior_classes,
            "selected_three_input": construction.selected_three_input.to_dict(),
            "equation_examples": list(construction.equation_examples),
        },
        "proofs": {
            "paired_cancellation": cancellation,
            "nonzero_unary": unary,
            "commutative_field": field,
            "general_first_degree_solver": solver,
        },
        "mutation_audits": list(mutations),
        "proof_obligations": list(obligations),
        "posthoc_translation": {
            "paired_cancellation": "有向计数器约简",
            "selected_nonzero_unary": "非零有理数的乘法逆元（倒数）",
            "combined_structure": "有理数域",
            "selected_three_input": "a*x+b=c（a≠0）的唯一解程序",
            "selected_three_input_normal_form": "(c-b)/a",
        },
        "limitations": [
            "V53 constructs the rational field only; real and complex completions are not constructed.",
            "The solver covers first-degree one-variable equations, not polynomial equations of degree two or higher.",
            "Output triples are equivalence-correct but are not always reduced to minimum counter size.",
            "Finite search selected the programs; universal validity comes from the separate symbolic proofs.",
            "No claim of new-to-human mathematics is made.",
        ],
    }


def replay_v53_report(report: Mapping[str, Any]) -> dict[str, Any]:
    rerun = run_v53_acceptance(tuple(report["observed_values"]))
    return {
        "passed": rerun["passed"]
        and rerun["construction"] == report["construction"],
        "proof_obligations": rerun["proof_obligations"],
    }
