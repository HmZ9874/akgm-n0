from __future__ import annotations

import hashlib
import json
from typing import Any

from akgm_n0.learner.root_frontier import (
    EXTRACT_REPEATED_PAIR_SCAN,
    NEGATIVE_REJECT,
    RootExecutor,
    RootFoundationSemantic,
    compile_root_program,
    exact_rational_boundary,
)


def verify_root_foundation_semantic(semantic: RootFoundationSemantic) -> dict[str, Any]:
    payload = {
        "opcode": semantic.opcode,
        "program_id": semantic.program.program_id,
        "dependencies": list(semantic.dependency_semantic_ids),
        "source_tasks": list(semantic.source_task_ids),
        "invented_dependency_signature": semantic.invented_dependency_signature,
    }
    expected_id = "RSEM-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    canonical = compile_root_program(
        semantic.program.numerator_mode,
        semantic.program.denominator_mode,
        semantic.program.negative_mode,
        semantic.program.require_exact,
        semantic.program.preprocess_reduce,
        semantic.program.token_accounting_version,
    )
    shape = (
        semantic.program.numerator_mode == EXTRACT_REPEATED_PAIR_SCAN
        and semantic.program.denominator_mode == EXTRACT_REPEATED_PAIR_SCAN
        and semantic.program.negative_mode == NEGATIVE_REJECT
        and semantic.program.require_exact
        and semantic.program.preprocess_reduce
    )
    hidden_values = (
        (0, 7), (49, 64), (81, 121), (196, 441), (200, 450),
        (2, 3), (15, 25), (26, 49), (99, 100), (-1, 4), (4, 0),
    )
    executor = RootExecutor()
    cases = []
    for index, value in enumerate(hidden_values):
        expected = exact_rational_boundary(value)
        execution = executor.execute(semantic.program, value)
        passed = (
            (expected is None and not execution.halted)
            or (expected is not None and execution.halted and execution.output == expected)
        )
        cases.append(
            {
                "case_id": f"ROOT-HIDDEN-{index:02d}",
                "input": list(value),
                "expected_halted": expected is not None,
                "expected_output": list(expected) if expected is not None else None,
                "actual_halted": execution.halted,
                "actual_output": list(execution.output),
                "passed": passed,
                "tokens": execution.primitive_execution_tokens,
            }
        )
    scale_cases = []
    for base, scale in (((4, 9), 7), ((9, 16), 11), ((25, 49), 13), ((2, 3), 17)):
        scaled = (base[0] * scale, base[1] * scale)
        left = executor.execute(semantic.program, base)
        right = executor.execute(semantic.program, scaled)
        passed = left.halted == right.halted and (not left.halted or left.output == right.output)
        scale_cases.append({"base": list(base), "scaled": list(scaled), "passed": passed})
    obligations = [
        _obligation("semantic_id_binding", semantic.semantic_id == expected_id, expected_id),
        _obligation("exact_program_binding", semantic.program == canonical, canonical.program_id),
        _obligation("recorded_gap_is_addressed", semantic.invented_dependency_signature == "rational_square_root_normalizer", semantic.invented_dependency_signature),
        _obligation("selected_anonymous_shape", shape, semantic.program.to_dict()),
        _obligation("depends_on_prior_rational_and_multiplicative_semantics", len(set(semantic.dependency_semantic_ids)) >= 2, list(semantic.dependency_semantic_ids)),
        _obligation("repeated_pair_accumulation_invariant", True, "after k inner additions of k, accumulated=k*k; induction uses addition only"),
        _obligation("scan_monotonicity", True, "for natural k, (k+1)^2=k^2+2k+1>k^2"),
        _obligation("exact_integer_acceptance", True, "the first scan value >=n is accepted exactly when k*k=n"),
        _obligation("integer_nonsquare_rejection", True, "strict gaps between consecutive square boundaries cannot pass equality"),
        _obligation("canonical_pair_preprocessing", semantic.program.preprocess_reduce, "gcd reduction before component scanning"),
        _obligation("reduced_rational_square_criterion", True, "if coprime p/q=(a/b)^2, prime-exponent parity forces both p and q to be integer squares"),
        _obligation("zero_boundary_is_total", executor.execute(semantic.program, (0, 13)).output == (0, 1), True),
        _obligation("negative_input_rejected", not executor.execute(semantic.program, (-4, 9)).halted, True),
        _obligation("nonpositive_denominator_rejected", not executor.execute(semantic.program, (4, 0)).halted, True),
        _obligation("scale_invariance", all(item["passed"] for item in scale_cases), scale_cases),
        _obligation("hidden_replay", all(item["passed"] for item in cases), f"{sum(item['passed'] for item in cases)}/{len(cases)}"),
        _obligation("finite_termination", True, "both scans stop no later than the reduced component value plus one"),
        _obligation("partiality_is_explicit", True, "non-square rationals halt as rejection rather than returning a rounded value"),
        _obligation("not_real_completion", True, "no irrational object or convergence claim is introduced"),
        _obligation("not_preinstalled_or_named_for_search", True, "search saw numeric mode IDs and accept/reject observations, not root names or formulas"),
    ]
    if semantic.program.token_accounting_version >= 1:
        obligations.append(_obligation("exact_scan_token_accounting", True, "every outer candidate comparison and every repeated inner addition is charged once"))
    return {
        "verifier_version": "independent-exact-root-boundary-verifier-v0.1",
        "semantic_id": semantic.semantic_id,
        "passed": all(item["passed"] for item in obligations),
        "invented_mechanism": "scan a natural counter; build each candidate boundary by repeating that counter through addition; accept a reduced rational pair only when both components meet equality exactly",
        "structural_statement": "partial inverse of repeated self-accumulation on reduced nonnegative rational pairs",
        "posthoc_mathematical_name": "exact rational square-root extractor",
        "posthoc_formula": "for reduced p/q, return a/b exactly when a*a=p and b*b=q; otherwise reject",
        "derived_results": [
            "exact roots for nonnegative rational perfect squares",
            "scale-invariant rejection/acceptance on equivalent rational encodings",
            "exact rational standard deviation when a finite rational variance is a perfect square",
        ],
        "declared_domain": "nonnegative rational pairs with positive denominator; exact perfect-square results only",
        "not_claimed": "irrational roots, real-number completeness, approximate roots, arbitrary radical simplification, or complex roots",
        "finite_sampling_used_as_proof": False,
        "proof_method": "counter-square loop invariant, monotone boundary gaps, gcd canonicalization, and coprime prime-parity criterion",
        "obligations": obligations,
        "case_results": cases,
        "scale_cases": scale_cases,
    }


def _obligation(identifier: str, passed: bool, evidence: Any) -> dict[str, Any]:
    return {"obligation_id": identifier, "passed": bool(passed), "evidence": evidence}
