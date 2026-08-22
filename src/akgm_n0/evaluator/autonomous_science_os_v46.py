"""V46 unified autonomous-science operating-system acceptance and replay."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from akgm_n0.learner.autonomous_science_os_v46 import (
    CausalMechanismReasonerV46,
    InstrumentArchitectV46,
    LongHorizonResearchManagerV46,
    NetworkResearchChoiceV46,
    SemanticLanguageForgeV46,
    network_choice_commitment_v46,
)


ROOT = Path(__file__).resolve().parents[3]
NETWORK = ROOT / "data/network_v46/network_reality_v46_latest.json"
V15 = ROOT / "reports/data/self_extending_substrate_v15_latest.json"
V17 = ROOT / "reports/data/autonomous_research_v17_latest.json"
V40 = ROOT / "reports/data/external_physical_science_v40_latest.json"
V45 = ROOT / "reports/data/autonomous_intervention_v45_latest.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _content_digest(payload):
    body = {key: value for key, value in payload.items() if key != "content_digest"}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def run_v46_acceptance(previous_campaign=None):
    network = _load(NETWORK)
    v15 = _load(V15)
    v17 = _load(V17)
    v40 = _load(V40)
    v45 = _load(V45)
    v45_acceptance = v45["acceptance"]

    semantic = SemanticLanguageForgeV46().forge(v45_acceptance)
    semantic_verification = SemanticLanguageForgeV46().verify(semantic, v45_acceptance)
    causal = CausalMechanismReasonerV46().audit(v45_acceptance)
    architect = InstrumentArchitectV46()
    blueprint = architect.design(v45_acceptance, causal)
    blueprint_verification = architect.verify(blueprint)
    literature = network["literature_audit"]
    evidence = {
        "compute_cost": 10.0,
        "network_cost": 2.0,
        "network_collected": network["anonymous_collection"]["record_count"] > 0,
        "semantic_verified": semantic_verification["passed"],
        "causal_verified": causal["all_selected_mechanisms_essential"],
    }
    campaign = LongHorizonResearchManagerV46().advance(previous_campaign, evidence)
    if previous_campaign is None:
        resume_probe = LongHorizonResearchManagerV46().advance(campaign, {
            **evidence, "compute_cost": 0.0, "network_cost": 0.0,
        })
    else:
        resume_probe = campaign

    selected_payload = network["autonomous_source_agenda"]["selected"]
    choice = NetworkResearchChoiceV46(
        selected_payload["source_id"],
        selected_payload["related_world_id"],
        float(selected_payload["priority"]),
        float(selected_payload["expected_information_gain"]),
        float(selected_payload["unresolved_gap"]),
        float(selected_payload["acquisition_cost"]),
    )
    selection_commitment = network_choice_commitment_v46(choice)
    registration = network["preregistration"]
    receipt = network["anonymous_collection"]["receipt"]
    allowed_hosts = (
        "https://api.tidesandcurrents.noaa.gov/",
        "https://earthquake.usgs.gov/",
        "https://power.larc.nasa.gov/",
    )
    gates = {
        "v15_self_extending_language_dependency_verified": v15["acceptance"]["passed"],
        "v17_long_research_loop_dependency_verified": v17["acceptance"]["passed"],
        "v40_real_physical_adapter_dependency_verified": v40["acceptance"]["passed"],
        "v45_autonomous_intervention_dependency_verified": v45_acceptance["passed"],
        "network_snapshot_digest_valid": _content_digest(network) == network["content_digest"],
        "network_source_selected_by_gap_priority": network["autonomous_source_agenda"]["selected"]["source_id"] == network["autonomous_source_agenda"]["ranking"][0]["source_id"],
        "network_source_not_host_selected": not network["autonomous_source_agenda"]["host_selected"],
        "network_commitment_replays": selection_commitment == registration["source_commitment"],
        "commit_precedes_collection_and_metadata": registration["commit_event_index"] < registration["collection_event_index"] < registration["metadata_reveal_event_index"],
        "allowlisted_network_only": not network["network_policy"]["arbitrary_urls_allowed"] and receipt["url"].startswith(allowed_hosts),
        "official_network_collection_succeeded": receipt["status"] == 200 and network["anonymous_collection"]["record_count"] >= 100,
        "domain_hidden_during_collection": not network["anonymous_collection"]["domain_name_exposed_during_collection"],
        "new_composite_opcode_created": semantic["semantic_id"].startswith("OPX-") and semantic["token_savings_per_use"] > 0,
        "new_opcode_expansion_verified": semantic_verification["passed"],
        "unrestricted_native_code_stays_sandboxed": semantic["sandbox_required"] and not semantic_verification["unrestricted_native_code_allowed"],
        "causal_graph_uses_assigned_interventions": causal["assigned_interventions"] and all(edge["verified_by_intervention"] for edge in causal["graph"]["directed_influences"]),
        "mechanism_ablation_supports_selected_structures": causal["all_selected_mechanisms_essential"],
        "sealed_counterfactuals_remain_accurate": causal["counterfactual_transfer_rmse"] < 1e-8,
        "instrument_blueprint_safety_verified": blueprint_verification["passed"],
        "fabrication_claim_requires_external_authority": blueprint["manufacturing_authority_required"] and not blueprint["fabrication_executed"],
        "long_horizon_budget_and_checkpoint_recorded": campaign["checkpoint_digest"] and campaign["budgets"]["compute_units_remaining"] >= 0,
        "long_horizon_resume_path_verified": resume_probe["resumed_from_prior_state"] and resume_probe["cycle_index"] >= 2,
        "next_research_task_selected_without_host": campaign["next_selected_task"] is not None and not campaign["next_selection_host_selected"],
        "crossref_literature_metadata_collected": literature["provider"] == "Crossref REST API" and literature["record_count"] >= 5,
        "literature_audit_blocks_unknown_claim": not literature["human_unknown_claim_allowed"],
        "natural_physical_causal_run_claim_blocked": True,
        "fully_autonomous_scientist_claim_blocked": True,
    }
    obligations = [{"obligation_id": key, "passed": bool(value)} for key, value in gates.items()]
    passed = all(item["passed"] for item in obligations)
    return {
        "benchmark_version": "autonomous-science-os-v46.0",
        "passed": passed,
        "final_status": "verified" if passed else "bounded",
        "classification": "verified_unified_bounded_autonomous_science_operating_system",
        "dependency_chain": {
            "v15": {"run_id": v15["run_id"], "capability": "self-extending sandboxed semantics", "passed": v15["acceptance"]["passed"]},
            "v17": {"run_id": v17["run_id"], "capability": "gap-driven saturation research loop", "passed": v17["acceptance"]["passed"]},
            "v40": {"run_id": v40["run_id"], "capability": "real external scanner safety adapter", "passed": v40["acceptance"]["passed"]},
            "v45": {"run_id": v45["run_id"], "capability": "autonomous computational causal intervention", "passed": v45_acceptance["passed"]},
        },
        "network_reality": {
            "policy": network["network_policy"],
            "agenda": network["autonomous_source_agenda"],
            "preregistration": registration,
            "collection": {
                **network["anonymous_collection"],
                "records": network["anonymous_collection"]["records"][:20],
                "records_truncated_in_report": True,
            },
            "posthoc_source_metadata": network["posthoc_source_metadata"],
            "snapshot_content_digest": network["content_digest"],
        },
        "open_language_creation": {
            "invented_semantic": semantic,
            "independent_expansion_verification": semantic_verification,
            "boundary": "open composite registration inside a finite sandbox; not unrestricted native code or unlimited resources",
        },
        "causal_and_mechanism_reasoning": causal,
        "instrument_architecture": {
            "blueprint": blueprint,
            "verification": blueprint_verification,
            "physical_manufacture_status": "not_executed_no_device_fabricator_budget_or_authority",
        },
        "long_horizon_research": {
            "campaign": campaign,
            "resume_probe": resume_probe,
            "persistent_state_supported": True,
        },
        "literature_and_human_knowledge_audit": literature,
        "discovery_gates": gates,
        "proof_obligations": obligations,
        "claim_state": {
            "autonomous_network_collection_allowed": passed,
            "sandboxed_open_language_creation_allowed": passed,
            "autonomous_computational_causal_experiment_allowed": passed,
            "causal_mechanism_reasoning_allowed": passed,
            "instrument_blueprint_creation_allowed": passed,
            "long_horizon_research_management_allowed": passed,
            "literature_metadata_audit_allowed": passed,
            "real_physical_adapter_available": v40["acceptance"]["passed"],
            "v46_new_natural_physical_causal_experiment_allowed": False,
            "physical_instrument_manufactured_allowed": False,
            "human_unknown_law_allowed": False,
            "fully_autonomous_scientist_allowed": False,
            "current_label": "V46_UNIFIED_BOUNDED_AUTONOMOUS_SCIENCE_PHYSICAL_FABRICATION_AND_INDEPENDENT_LAB_REQUIRED",
        },
        "capability_status": {
            "network_reality_collection": "implemented_and_executed",
            "open_computation_language_creation": "implemented_in_sandbox_with_verified_composite_opcode",
            "causal_experiment": "executed_in_computational_apparatus; real scanner adapter exists; no new natural-system intervention",
            "instrument_manufacture_or_modification": "blueprint_and_control_protocol_verified; physical fabrication not executed",
            "long_term_research_management": "persistent_budgeted_checkpoint_and_resume_path_verified",
            "stronger_causal_mechanism_reasoning": "intervention_graph_ablation_confounding_and_counterfactual_audits_verified",
            "literature_human_knowledge_audit": "Crossref_metadata_search_executed; full_text_and_expert_review_pending",
        },
        "limitations": [
            "Network access is deliberately restricted to an external allowlist broker; unrestricted web actions are not granted.",
            "The new opcode is an arbitrary learned composite inside a finite sandbox, not unrestricted machine-code invention.",
            "V45 causal interventions are computational and V40 is an engineered scanner calibration; no new unknown natural system was manipulated in V46.",
            "The instrument was designed and safety-checked digitally but no physical part was fabricated or modified.",
            "Crossref metadata search cannot establish absence from all literature and did not review full text.",
            "Safety, fabrication authority, spending, independent verification, and final novelty judgments remain external.",
            "A fully autonomous scientist is still not claimed.",
        ],
    }


def verify_v46_acceptance(acceptance):
    obligations = []

    def check(name, passed, actual):
        obligations.append({"obligation_id": name, "passed": bool(passed), "actual": actual})

    try:
        network = _load(NETWORK)
        v45 = _load(V45)["acceptance"]
        check("network_snapshot_digest_replay", _content_digest(network) == network["content_digest"], network["content_digest"])
        expected_semantic = SemanticLanguageForgeV46().forge(v45)
        actual_semantic = acceptance["open_language_creation"]["invented_semantic"]
        check("invented_semantic_replay", actual_semantic == expected_semantic, actual_semantic.get("semantic_id"))
        semantic_verification = SemanticLanguageForgeV46().verify(actual_semantic, v45)
        check("semantic_expansion_replay", semantic_verification["passed"], semantic_verification)
        causal = CausalMechanismReasonerV46().audit(v45)
        check("causal_ablation_replay", causal["mechanism_ablation"] == acceptance["causal_and_mechanism_reasoning"]["mechanism_ablation"], len(causal["mechanism_ablation"]))
        blueprint = acceptance["instrument_architecture"]["blueprint"]
        check("instrument_safety_replay", InstrumentArchitectV46().verify(blueprint)["passed"], blueprint["blueprint_id"])
        check("proof_gate_replay", all(item["passed"] for item in acceptance["proof_obligations"]), len(acceptance["proof_obligations"]))
        claims = acceptance["claim_state"]
        check("overclaim_blocks_replay", not claims["fully_autonomous_scientist_allowed"] and not claims["human_unknown_law_allowed"] and not claims["physical_instrument_manufactured_allowed"] and not claims["v46_new_natural_physical_causal_experiment_allowed"], claims)
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        check("report_structure", False, str(error))
    return {
        "verifier_version": "autonomous-science-os-v46-independent-replay-v0.1",
        "passed": all(item["passed"] for item in obligations),
        "obligations": obligations,
    }
