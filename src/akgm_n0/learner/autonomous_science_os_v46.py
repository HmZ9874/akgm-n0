"""V46 research operating-system components.

This module coordinates allowlisted network acquisition, learned semantic
registration, causal mechanism audits, instrument blueprint generation,
long-horizon agenda management, and conservative literature checks.  Safety,
network allowlists, manufacturing authority, and final novelty claims remain
outside the learner.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any

import numpy as np

from akgm_n0.learner.autonomous_intervention_v45 import (
    InterventionActionV45,
    InterventionProgramV45,
    _feature_value,
)


@dataclass(frozen=True, slots=True)
class NetworkResearchChoiceV46:
    source_id: str
    related_world_id: str
    priority: float
    expected_information_gain: float
    unresolved_gap: float
    acquisition_cost: float

    def to_dict(self):
        return {
            "source_id": self.source_id,
            "related_world_id": self.related_world_id,
            "priority": self.priority,
            "expected_information_gain": self.expected_information_gain,
            "unresolved_gap": self.unresolved_gap,
            "acquisition_cost": self.acquisition_cost,
            "host_selected": False,
            "domain_name_received": False,
        }


class AutonomousNetworkScoutV46:
    def choose(self, queue, catalog):
        gaps = {item["world_id"]: item for item in queue}
        candidates = []
        for source in catalog:
            gap = gaps.get(source["related_world_id"])
            if gap is None:
                continue
            information = float(gap["expected_information_gain"])
            unresolved = float(gap["knowledge_gap"])
            cost = float(source["acquisition_cost"])
            provenance = 1.0 if source["provenance_verifiable"] else 0.0
            priority = (
                0.55 * min(1.0, information)
                + 0.25 * min(1.0, unresolved)
                + 0.15 * provenance
                - 0.05 * cost
            )
            candidates.append(NetworkResearchChoiceV46(
                source["source_id"], source["related_world_id"], priority,
                information, unresolved, cost,
            ))
        if not candidates:
            raise ValueError("no allowlisted source addresses an autonomous knowledge gap")
        ranked = tuple(sorted(candidates, key=lambda item: (-item.priority, item.source_id)))
        return {"selected": ranked[0], "ranked": ranked, "host_selected": False}


def network_choice_commitment_v46(choice):
    payload = choice.to_dict()
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class SemanticLanguageForgeV46:
    """Register a discovered composite program as a new sandboxed opcode."""

    @staticmethod
    def forge(v45_acceptance):
        program = v45_acceptance["language_growth"]["selected_program"]
        expansion = tuple(program["features"])
        coefficients = tuple(map(float, program["coefficients"]))
        payload = {"expansion": expansion, "coefficients": coefficients, "arity": 3}
        semantic_id = "OPX-" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16]
        primitive_cost = len(expansion) + len(coefficients)
        return {
            "semantic_id": semantic_id,
            "kind": "learned_composite_opcode",
            "arity": 3,
            "expansion_features": list(expansion),
            "expansion_coefficients": list(coefficients),
            "primitive_token_cost": primitive_cost,
            "macro_token_cost": 1,
            "token_savings_per_use": primitive_cost - 1,
            "memory_slots_created": 0,
            "control_paths_created": sum(feature.startswith("GUARD(") for feature in expansion),
            "supplied_target_name": False,
            "sandbox_required": True,
        }

    @staticmethod
    def verify(semantic, v45_acceptance):
        program_payload = v45_acceptance["language_growth"]["selected_program"]
        program = InterventionProgramV45(
            tuple(program_payload["features"]),
            tuple(map(float, program_payload["coefficients"])),
            float(program_payload["cross_validated_rmse"]),
            float(program_payload["score"]),
        )
        cases = v45_acceptance["sealed_counterfactual_audit"]["cases"]
        errors = []
        for case in cases:
            action = InterventionActionV45(tuple(map(float, case["action"]["values"])))
            expanded = program.predict(action)
            macro = sum(
                coefficient * _feature_value(feature, action.values)
                for coefficient, feature in zip(
                    semantic["expansion_coefficients"], semantic["expansion_features"], strict=True,
                )
            )
            errors.append(abs(expanded - macro))
        return {
            "passed": bool(errors) and max(errors) < 1e-12,
            "case_count": len(errors),
            "maximum_expansion_error": max(errors) if errors else math.inf,
            "token_compression_verified": semantic["token_savings_per_use"] > 0,
            "unrestricted_native_code_allowed": False,
        }


class CausalMechanismReasonerV46:
    @staticmethod
    def _fit(features, measurements):
        design = np.asarray([
            [_feature_value(feature, row["action"]["values"]) for feature in features]
            for row in measurements
        ], dtype=float)
        target = np.asarray([row["response"] for row in measurements], dtype=float)
        coefficients, *_ = np.linalg.lstsq(design, target, rcond=None)
        return tuple(float(value) for value in coefficients)

    @staticmethod
    def _rmse(features, coefficients, cases):
        errors = []
        for case in cases:
            values = case["action"]["values"]
            prediction = sum(
                coefficient * _feature_value(feature, values)
                for coefficient, feature in zip(coefficients, features, strict=True)
            )
            errors.append(prediction - float(case["observed"]))
        return math.sqrt(sum(value * value for value in errors) / len(errors))

    def audit(self, v45_acceptance):
        program = v45_acceptance["language_growth"]["selected_program"]
        features = tuple(program["features"])
        measurements = v45_acceptance["autonomous_experiment_design"]["development_measurements"]
        cases = v45_acceptance["sealed_counterfactual_audit"]["cases"]
        full_rmse = float(v45_acceptance["sealed_counterfactual_audit"]["rmse"])
        ablations = []
        for feature in features:
            if feature == "ONE":
                continue
            remaining = tuple(item for item in features if item != feature)
            coefficients = self._fit(remaining, measurements)
            ablated_rmse = self._rmse(remaining, coefficients, cases)
            ablations.append({
                "removed_feature": feature,
                "sealed_rmse": ablated_rmse,
                "rmse_ratio_to_full": ablated_rmse / max(full_rmse, 1e-15),
                "mechanistically_essential": ablated_rmse > 1e-6,
            })
        randomized = v45_acceptance["discovery_gates"]["multi_action_order_randomized"]
        assigned = v45_acceptance["causal_effect_audit"]["essential_controls"]
        return {
            "graph": {
                "nodes": ["Q0", "Q1", "Q2", "Y"],
                "directed_influences": [
                    {"from": item["control_slot"], "to": "Y", "verified_by_intervention": item["essential_effect_observed"]}
                    for item in assigned
                ],
                "interaction_hyperedges": [
                    {"inputs": ["Q0", "Q1", "Q2"], "to": "Y", "internal_feature": "COUPLE(0,1,2)"},
                    {"condition": "Q0>Q1", "payload": "Q0", "to": "Y", "internal_feature": "GUARD(0,1,0)"},
                ],
            },
            "mechanism_ablation": ablations,
            "all_selected_mechanisms_essential": all(item["mechanistically_essential"] for item in ablations),
            "counterfactual_transfer_rmse": full_rmse,
            "assigned_interventions": True,
            "randomized_execution_order": randomized,
            "confounding_assessment": "control-to-response total effects are identified inside this apparatus because controls were assigned; unique internal mediation is not proved",
            "unique_universal_causal_graph_claim_allowed": False,
        }


class InstrumentArchitectV46:
    def design(self, v45_acceptance, causal_audit):
        safe_ranges = v45_acceptance["apparatus_boundary"]["safe_ranges"]
        blueprint = {
            "blueprint_version": "instrument-blueprint-v46.0",
            "research_gap": "replace local computational controls with three isolated physical actuator channels and one measured response",
            "actuator_channels": [
                {"slot": f"Q{index}", "safe_envelope": envelope, "command_mode": "bounded_setpoint"}
                for index, envelope in enumerate(safe_ranges)
            ],
            "sensor_channels": [{"slot": "Y", "requirements": ["timestamp", "value", "unit", "uncertainty", "calibration_digest"]}],
            "controller_protocol": {
                "transport": "JSON-lines isolated broker",
                "required_operations": ["metadata", "commit_batch", "run_batch", "commit_program", "emergency_stop"],
                "model_has_direct_hardware_access": False,
            },
            "mandatory_interlocks": [
                "hard_range_limit", "rate_limit", "energy_budget", "command_timeout",
                "watchdog", "manual_emergency_stop", "power_isolation", "calibration_expiry",
            ],
            "calibration_plan": [
                "zero_reference", "three_point_span", "repeatability_batch",
                "randomized_order_drift_check", "sealed_reference_standard",
            ],
            "digital_acceptance_tests": [
                "reject_out_of_range", "reject_uncommitted_batch", "stop_on_timeout",
                "record_receipt_digest", "holdout_prediction_before_measurement",
            ],
            "causal_channels_required": len(causal_audit["graph"]["directed_influences"]),
            "manufacturing_authority_required": True,
            "fabrication_executed": False,
            "current_status": "verified_design_waiting_for_human_approved_fabrication_and_device",
        }
        blueprint["blueprint_id"] = "INST-" + hashlib.sha256(
            json.dumps(blueprint, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16]
        return blueprint

    @staticmethod
    def verify(blueprint):
        required = {
            "hard_range_limit", "rate_limit", "energy_budget", "command_timeout",
            "watchdog", "manual_emergency_stop", "power_isolation", "calibration_expiry",
        }
        return {
            "passed": (
                len(blueprint["actuator_channels"]) == blueprint["causal_channels_required"]
                and required.issubset(blueprint["mandatory_interlocks"])
                and not blueprint["controller_protocol"]["model_has_direct_hardware_access"]
                and blueprint["manufacturing_authority_required"]
                and not blueprint["fabrication_executed"]
            ),
            "required_interlock_count": len(required),
            "present_interlock_count": len(required & set(blueprint["mandatory_interlocks"])),
            "fabrication_claim_blocked": not blueprint["fabrication_executed"],
        }


class LongHorizonResearchManagerV46:
    def advance(self, previous, evidence):
        cycle = 1 if previous is None else int(previous["cycle_index"]) + 1
        remaining_compute = 100.0 if previous is None else float(previous["budgets"]["compute_units_remaining"])
        remaining_network = 20.0 if previous is None else float(previous["budgets"]["network_requests_remaining"])
        remaining_compute = max(0.0, remaining_compute - float(evidence["compute_cost"]))
        remaining_network = max(0.0, remaining_network - float(evidence["network_cost"]))
        tasks = [
            {"task_id": "network_gap_acquisition", "status": "completed" if evidence["network_collected"] else "queued", "information_gain": 0.8, "cost": 1.0, "risk": 0.1},
            {"task_id": "semantic_language_forge", "status": "completed" if evidence["semantic_verified"] else "queued", "information_gain": 0.7, "cost": 2.0, "risk": 0.2},
            {"task_id": "causal_mechanism_audit", "status": "completed" if evidence["causal_verified"] else "queued", "information_gain": 0.9, "cost": 2.0, "risk": 0.2},
            {"task_id": "physical_instrument_fabrication", "status": "approval_required", "information_gain": 1.0, "cost": 20.0, "risk": 0.9},
            {"task_id": "independent_laboratory_replication", "status": "external_coordination_required", "information_gain": 1.0, "cost": 30.0, "risk": 0.4},
            {"task_id": "full_text_literature_review", "status": "queued", "information_gain": 0.6, "cost": 5.0, "risk": 0.1},
        ]
        selectable = [item for item in tasks if item["status"] == "queued"]
        selected = max(
            selectable,
            key=lambda item: (item["information_gain"] / item["cost"] - item["risk"], item["task_id"]),
        ) if selectable else None
        return {
            "campaign_id": "CAMPAIGN-AKGM-N0-AUTONOMOUS-SCIENCE",
            "cycle_index": cycle,
            "resumed_from_prior_state": previous is not None,
            "budgets": {
                "compute_units_remaining": remaining_compute,
                "network_requests_remaining": remaining_network,
                "physical_energy_authorized": 0.0,
                "fabrication_spend_authorized": 0.0,
            },
            "tasks": tasks,
            "next_selected_task": None if selected is None else selected["task_id"],
            "next_selection_host_selected": False,
            "pause_reason": "external_authority_required" if selected is None else None,
            "checkpoint_digest": hashlib.sha256(
                json.dumps(tasks, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }


class LiteratureKnowledgeAuditorV46:
    @staticmethod
    def _tokens(text):
        return set(re.findall(r"[a-z0-9]+", text.lower())) - {
            "the", "and", "of", "a", "to", "in", "for", "with", "on",
        }

    def audit(self, query, response):
        query_tokens = self._tokens(query)
        records = []
        for item in response["records"]:
            title = item.get("title") or ""
            overlap = len(query_tokens & self._tokens(title)) / max(len(query_tokens), 1)
            records.append({**item, "query_token_overlap": overlap})
        ranked = sorted(records, key=lambda item: (-item["query_token_overlap"], -item["is_referenced_by_count"], item.get("doi") or ""))
        related = [item for item in ranked if item["query_token_overlap"] > 0]
        return {
            "provider": response["provider"],
            "query": query,
            "record_count": len(records),
            "related_title_count": len(related),
            "top_records": ranked[:10],
            "metadata_receipt": response["receipt"],
            "full_text_reviewed": response["full_text_reviewed"],
            "audit_status": "prior_art_or_related_human_knowledge_detected" if related else "novelty_unresolved_metadata_search_only",
            "human_unknown_claim_allowed": False,
            "reason": "metadata search cannot prove absence from literature; full-text and independent expert review remain required",
        }
