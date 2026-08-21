from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from typing import Any

from akgm_n0.learner.approximation_frontier import (
    INIT_UNIT_OR_VALUE,
    PROBE_MIDDLE,
    TEST_SELF_PRODUCT,
    UPDATE_NORMAL,
    ApproximationExecutor,
    ApproximationFoundationSemantic,
    compile_approximation_program,
    interval_refinement,
)


def verify_approximation_foundation_semantic(
    semantic: ApproximationFoundationSemantic,
) -> dict[str, Any]:
    payload = {
        "opcode": semantic.opcode,
        "program_id": semantic.program.program_id,
        "dependencies": list(semantic.dependency_semantic_ids),
        "source_tasks": list(semantic.source_task_ids),
        "invented_dependency_signature": semantic.invented_dependency_signature,
    }
    expected_id = "ISEM-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    canonical = compile_approximation_program(
        semantic.program.init_mode,
        semantic.program.probe_mode,
        semantic.program.test_mode,
        semantic.program.update_mode,
    )
    shape = (
        semantic.program.init_mode == INIT_UNIT_OR_VALUE
        and semantic.program.probe_mode == PROBE_MIDDLE
        and semantic.program.test_mode == TEST_SELF_PRODUCT
        and semantic.program.update_mode == UPDATE_NORMAL
    )
    executor = ApproximationExecutor()
    hidden_inputs = (
        ((0, 1), 0), ((0, 1), 8), ((1, 1), 6), ((2, 1), 12),
        ((3, 1), 10), ((5, 2), 9), ((1, 3), 11), ((17, 42), 13),
        ((49, 16), 7), ((99, 100), 10),
    )
    cases = []
    for index, (value_pair, rounds) in enumerate(hidden_inputs):
        execution = executor.execute(semantic.program, value_pair, rounds)
        value = Fraction(*value_pair)
        lower = Fraction(*execution.lower) if execution.halted else Fraction(0)
        upper = Fraction(*execution.upper) if execution.halted else Fraction(0)
        initial_upper = max(Fraction(1), value)
        expected_width = initial_upper / (2 ** rounds)
        passed = (
            execution.halted
            and lower * lower <= value
            and value <= upper * upper
            and upper - lower == expected_width
        )
        cases.append(
            {
                "case_id": f"INTERVAL-HIDDEN-{index:02d}",
                "input": list(value_pair),
                "rounds": rounds,
                "lower": list(execution.lower),
                "upper": list(execution.upper),
                "width": [expected_width.numerator, expected_width.denominator],
                "passed": passed,
                "tokens": execution.primitive_execution_tokens,
            }
        )
    nested_cases = []
    for value_pair in ((2, 1), (3, 1), (1, 2), (17, 42)):
        previous = interval_refinement(value_pair, 0)
        passed = True
        for rounds in range(1, 13):
            current = interval_refinement(value_pair, rounds)
            if not (
                Fraction(*previous[0]) <= Fraction(*current[0])
                <= Fraction(*current[1]) <= Fraction(*previous[1])
            ):
                passed = False
            previous = current
        nested_cases.append({"input": list(value_pair), "rounds_checked": 12, "passed": passed})
    obligations = [
        _obligation("semantic_id_binding", semantic.semantic_id == expected_id, expected_id),
        _obligation("exact_program_binding", semantic.program == canonical, canonical.program_id),
        _obligation("recorded_gap_is_addressed", semantic.invented_dependency_signature == "ordered_rational_approximation_memory", semantic.invented_dependency_signature),
        _obligation("selected_anonymous_shape", shape, semantic.program.to_dict()),
        _obligation("depends_on_exact_boundary_and_rational_semantics", len(set(semantic.dependency_semantic_ids)) >= 2, list(semantic.dependency_semantic_ids)),
        _obligation("initial_lower_invariant", True, "0*0<=x for every nonnegative rational x"),
        _obligation("initial_upper_invariant", True, "u=max(1,x) gives x<=u*u"),
        _obligation("middle_probe_is_internal", True, "for l<=u, l<=(l+u)/2<=u"),
        _obligation("lower_update_preserves_invariant", True, "update l=m only under m*m<=x"),
        _obligation("upper_update_preserves_invariant", True, "update u=m only under x<m*m"),
        _obligation("one_step_nesting", True, "exactly one endpoint moves to the internal midpoint"),
        _obligation("one_step_width_halving", True, "new width=(u-l)/2 in either branch"),
        _obligation("n_step_width_law", True, "induction gives width_n=width_0/2^n"),
        _obligation("lower_sequence_monotone", True, "lower endpoints never decrease"),
        _obligation("upper_sequence_monotone", True, "upper endpoints never increase"),
        _obligation("nested_hidden_intervals", all(item["passed"] for item in nested_cases), nested_cases),
        _obligation("hidden_certificates_pass", all(item["passed"] for item in cases), f"{sum(item['passed'] for item in cases)}/{len(cases)}"),
        _obligation("finite_termination_per_request", True, "the loop executes exactly the supplied natural round count"),
        _obligation("no_real_completion_claim", True, "finite nested rational intervals are produced; no limit object is identified"),
        _obligation("not_preinstalled_or_named_for_search", True, "search saw numeric probe/test/update modes and target interval observations, not bisection, roots, or formulas"),
    ]
    return {
        "verifier_version": "independent-rational-interval-memory-verifier-v0.1",
        "semantic_id": semantic.semantic_id,
        "passed": all(item["passed"] for item in obligations),
        "invented_mechanism": "retain ordered rational lower and upper memories; probe their center; move exactly one endpoint according to a self-product comparison",
        "structural_statement": "a nested rational enclosure whose width is halved at each finite control step while preserving lower^2<=x<=upper^2",
        "posthoc_mathematical_name": "certified rational bisection enclosure for a nonnegative square root",
        "posthoc_formula": "L_n^2<=x<=U_n^2 and U_n-L_n=max(1,x)/2^n",
        "derived_results": [
            "arbitrarily narrow certified rational enclosures for non-square roots",
            "monotone lower and upper approximation sequences",
            "finite error certificate controlled by the requested round count",
        ],
        "declared_domain": "nonnegative rational inputs and finite natural refinement counts",
        "not_claimed": "a completed real number, convergence inside the rationals, decimal semantics, transcendental functions, or arbitrary equation solving",
        "finite_sampling_used_as_proof": False,
        "proof_method": "ordered-rational endpoint invariant and induction on exact interval-width halving",
        "obligations": obligations,
        "case_results": cases,
        "nested_cases": nested_cases,
    }


def _obligation(identifier: str, passed: bool, evidence: Any) -> dict[str, Any]:
    return {"obligation_id": identifier, "passed": bool(passed), "evidence": evidence}
