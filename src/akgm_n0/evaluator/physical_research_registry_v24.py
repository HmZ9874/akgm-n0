"""Post-proof research names for anonymous V24 quantities and constant candidates."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from akgm_n0.learner.inertial_response_discovery_v24 import InertialDiscoveryV24


def _stable_id(prefix: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return prefix + "-" + hashlib.sha256(encoded.encode()).hexdigest()[:12].upper()


def build_physical_research_registry_v24(discovery: InertialDiscoveryV24) -> dict[str, Any]:
    """Assign names only after discovery; these records are never learner inputs."""
    response_program = discovery.selected_response.policy.program_id
    invariant_program = discovery.selected_invariant.expression.expression_id
    quantities = (
        {
            "machine_symbol": "P_IR",
            "research_name": "惯性参数",
            "posthoc_physics_alias": "m",
            "role": "positive_entity_parameter",
            "source_program_id": response_program,
        },
        {
            "machine_symbol": "X_IR",
            "research_name": "外部作用量",
            "posthoc_physics_alias": "F",
            "role": "directed_input_quantity",
            "source_program_id": response_program,
        },
        {
            "machine_symbol": "R_IR",
            "research_name": "惯性响应量",
            "posthoc_physics_alias": "a",
            "role": "directed_response_quantity",
            "source_program_id": response_program,
        },
        {
            "machine_symbol": "J_IR",
            "research_name": "加权运动总量",
            "posthoc_physics_alias": "p_total",
            "role": "conserved_weighted_quantity",
            "source_program_id": invariant_program,
        },
    )
    named_quantities = [
        {"quantity_id": _stable_id("QIR", item), **item, "assigned_after_proof": True}
        for item in quantities
    ]
    constant_payload = {
        "machine_symbol": "K_IR",
        "research_name": "惯性响应比例系数",
        "display_symbol": "κ_IR",
        "exact_value": {"positive": 1, "negative": 0, "denominator": 1},
        "defining_relation": "X_IR = K_IR SEM<P_IR,R_IR>",
        "source_program_id": response_program,
    }
    constant = {
        "constant_id": _stable_id("KIR", constant_payload),
        **constant_payload,
        "status": "unit_normalized_constant_candidate",
        "evidence_level": "proved_inside_v24_synthetic_world_family",
        "scope": "V24 exact one-dimensional rational worlds",
        "universal_nature_constant_claimed": False,
        "warning": "K_IR=1 may follow from the chosen unit convention; cross-world and unit-change invariance is not yet established.",
        "assigned_after_proof": True,
    }
    return {
        "registry_version": "physical-research-registry-v24.1",
        "naming_stage": "post_proof_only",
        "supplied_to_learner": False,
        "quantities": named_quantities,
        "constant_candidates": [constant],
        "promotion_rule": {
            "target_status": "cross_world_physical_constant",
            "requirements": [
                "same dimensionless relation in independently generated world families",
                "stable under permitted representation and unit changes",
                "sealed experimental transfer",
                "independent counterexample search finds no varying coefficient",
            ],
        },
    }
