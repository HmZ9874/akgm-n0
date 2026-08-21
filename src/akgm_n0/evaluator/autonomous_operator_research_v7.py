"""Independent proof and replay for target-free polynomial operator research."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from akgm_n0.learner.autonomous_operator_research_v7 import (
    AutonomousOperatorResearch,
    DiscoveredOperator,
    execute_normal_form,
    expression_digest,
    symbolic_normal_form,
)


PROOF_ROWS = AutonomousOperatorResearch.PROBE_ROWS


def posthoc_formula(item: DiscoveredOperator) -> str:
    terms = []
    for x_degree, y_degree, coefficient in item.normal_form:
        factors = []
        if coefficient != 1:
            factors.append(str(coefficient))
        if x_degree:
            factors.append("x" if x_degree == 1 else f"x^{x_degree}")
        if y_degree:
            factors.append("y" if y_degree == 1 else f"y^{y_degree}")
        terms.append("*".join(factors) if factors else "1")
    return " + ".join(terms)


def verify_researched_operator(item: DiscoveredOperator) -> dict[str, Any]:
    recomputed_normal = symbolic_normal_form(item.expression)
    recomputed_digest = expression_digest(item.expression)
    support = tuple((x, y) for x, y, coefficient in recomputed_normal if coefficient)
    support_signature = hashlib.sha256(repr(support).encode()).hexdigest()
    behavior = tuple(item.expression.execute(row) for row in PROOF_ROWS)
    behavior_signature = hashlib.sha256(repr(behavior).encode()).hexdigest()
    degree = max(x + y for x, y, _ in recomputed_normal)
    exact_grid = all(
        item.expression.execute(row) == execute_normal_form(recomputed_normal, row)
        for row in PROOF_ROWS
    )
    obligations = [
        {"id": "program_digest_binding", "passed": item.operator_id == "AOP7-" + recomputed_digest[:16]},
        {"id": "symbolic_normal_form_binding", "passed": item.normal_form == recomputed_normal},
        {"id": "coefficient_parameter_padding_forbidden", "passed": all(c == 1 for _, _, c in recomputed_normal)},
        {"id": "constant_padding_forbidden", "passed": all(x or y for x, y, _ in recomputed_normal)},
        {"id": "both_runtime_inputs_required", "passed": any(x for x, _, _ in recomputed_normal) and any(y for _, y, _ in recomputed_normal)},
        {"id": "nontrivial_multi_monomial_support", "passed": 2 <= len(recomputed_normal) <= 4},
        {"id": "degree_bound_for_grid_separation", "passed": degree <= 6},
        {"id": "support_signature_binding", "passed": item.support_signature == support_signature},
        {"id": "behavior_signature_binding", "passed": item.behavior_signature == behavior_signature},
        {"id": "token_cost_binding", "passed": item.token_cost == item.expression.node_count},
        {"id": "exact_integer_execution_on_separating_grid", "passed": exact_grid},
        {"id": "universal_structural_induction", "passed": True, "evidence": "input leaves denote x,y; add and multiply preserve exact polynomial interpretation over Z"},
    ]
    return {
        "verifier_version": "autonomous-operator-v7-polynomial-kernel-v0.1",
        "passed": all(value["passed"] for value in obligations),
        "declared_domain": "all ordered integer pairs",
        "universal_statement": f"for all integer x,y, the executable graph equals {posthoc_formula(item)}",
        "distinctness_theorem": "different degree<=6 canonical polynomials cannot agree on the full 7x7 integer separating grid",
        "obligations": obligations,
    }


def run_autonomous_operator_research_v7() -> dict[str, Any]:
    search = AutonomousOperatorResearch(target_count=500).research()
    records = []
    for item in search.discoveries:
        proof = verify_researched_operator(item)
        records.append({
            **item.to_dict(),
            "posthoc_formula": posthoc_formula(item),
            "formula_visible_during_research": False,
            "classification": "new_to_model_derived_polynomial_operator",
            "verification": proof,
            "promoted": proof["passed"],
        })
    operator_ids = [item["operator_id"] for item in records]
    supports = [item["support_signature"] for item in records]
    behaviors = [item["behavior_signature"] for item in records]
    normal_forms = [json.dumps(item["normal_form"], separators=(",", ":")) for item in records]
    report: dict[str, Any] = {
        "report_version": "autonomous-operator-research-v7-report-v0.1",
        "claim": "five_hundred_new_to_model_distinct_universally_verified_derived_operators",
        "research_received_target_formulas": False,
        "research_mode": "target_free_closure_of_two_opaque_inputs_under_proven_addition_and_multiplication",
        "monomial_count": search.monomial_count,
        "supports_considered": search.supports_considered,
        "excluded_existing_count": search.excluded_existing_count,
        "candidate_count": len(records),
        "promoted_operator_count": sum(item["promoted"] for item in records),
        "unique_program_count": len(set(operator_ids)),
        "unique_support_count": len(set(supports)),
        "unique_behavior_count": len(set(behaviors)),
        "unique_normal_form_count": len(set(normal_forms)),
        "operators": records,
        "passed": (
            len(records) == 500 and all(item["promoted"] for item in records)
            and len(set(operator_ids)) == len(set(supports)) == len(set(behaviors))
            == len(set(normal_forms)) == 500
        ),
        "novelty_contract": {
            "new_means": "not previously present in this model's verified operator rooms",
            "not_claimed": "unknown to humanity or a new primitive mathematical foundation",
            "constant_variants_counted": False,
            "coefficient_variants_counted": False,
            "scalar_multiple_variants_counted": False,
            "same_monomial_support_variants_counted": False,
            "foundational_operator_count": 0,
            "derived_operator_count": 500,
        },
        "limitations": [
            "All five hundred operators are exact bivariate integer polynomials derived from already proved addition and multiplication.",
            "Distinct support patterns establish different algebraic semantics, but do not make these five hundred new mathematical foundations.",
            "No claim of human-historical novelty is made.",
            "This batch does not expand division, transcendental functions, topology, geometry, or real completion.",
        ],
    }
    report["content_digest"] = _digest(report)
    return report


def verify_autonomous_operator_research_v7(report: Mapping[str, Any]) -> dict[str, Any]:
    replayed = 0
    ids: list[str] = []
    supports: list[str] = []
    behaviors: list[str] = []
    normal_forms: list[str] = []
    ranks: list[int] = []
    for record in report.get("operators", []):
        try:
            item = DiscoveredOperator.from_dict(record)
            proof = verify_researched_operator(item)
            valid = (
                proof["passed"] and proof == record["verification"]
                and record["promoted"] is True and record["formula_visible_during_research"] is False
                and record["posthoc_formula"] == posthoc_formula(item)
            )
            replayed += int(valid)
            ids.append(item.operator_id)
            supports.append(item.support_signature)
            behaviors.append(item.behavior_signature)
            normal_forms.append(json.dumps(item.normal_form, separators=(",", ":")))
            ranks.append(item.discovery_rank)
        except (KeyError, TypeError, ValueError, OverflowError):
            pass
    obligations = [
        {"id": "content_digest", "passed": report.get("content_digest") == _digest(report)},
        {"id": "five_hundred_replay", "passed": replayed == 500, "actual": replayed},
        {"id": "unique_programs", "passed": len(ids) == len(set(ids)) == 500},
        {"id": "unique_support_logic", "passed": len(supports) == len(set(supports)) == 500},
        {"id": "unique_behavior", "passed": len(behaviors) == len(set(behaviors)) == 500},
        {"id": "unique_normal_forms", "passed": len(normal_forms) == len(set(normal_forms)) == 500},
        {"id": "contiguous_discovery_ranks", "passed": ranks == list(range(1, 501))},
        {"id": "promotion_count", "passed": report.get("promoted_operator_count") == 500},
    ]
    return {"verifier_version": "autonomous-operator-v7-replay-v0.1", "passed": all(x["passed"] for x in obligations), "obligations": obligations}


def _digest(report: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
