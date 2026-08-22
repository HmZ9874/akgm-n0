"""Independent acceptance and replay checks for V47."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

from akgm_n0.learner.full_text_literature_research_v47 import (
    AutonomousLiteraturePlannerV47,
    FrozenDiscoveryV47,
    FullTextPriorArtAuditorV47,
    QUERY_SPECS,
    ResearchCampaignV47,
    canonical_digest,
)


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "data/network_v47/open_literature_evidence_v47_latest.json"
V46 = ROOT / "reports/data/autonomous_science_os_v46_latest.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _evidence_digest(evidence):
    return canonical_digest({key: value for key, value in evidence.items() if key != "content_digest"})


def _discovery(v46):
    semantic = v46["acceptance"]["open_language_creation"]["invented_semantic"]
    return FrozenDiscoveryV47(
        semantic["semantic_id"],
        tuple(semantic["expansion_features"]),
        tuple(map(float, semantic["expansion_coefficients"])),
        v46["content_digest"],
    )


def run_v47_acceptance(evidence_override=None):
    evidence = copy.deepcopy(evidence_override) if evidence_override is not None else _load(EVIDENCE)
    v46 = _load(V46)
    discovery = _discovery(v46)
    expected_plan = AutonomousLiteraturePlannerV47().plan(discovery)
    audit = FullTextPriorArtAuditorV47().audit(evidence)
    v46_campaign = v46["acceptance"]["long_horizon_research"]["campaign"]
    campaign = ResearchCampaignV47().advance(v46_campaign, audit, evidence["request_count"])
    registration = evidence["preregistration"]
    searches = evidence["metadata_searches"]
    documents = evidence["full_text_documents"]
    expected_queries = {item["query_id"]: item["query"] for item in QUERY_SPECS}
    actual_queries = {item["query_id"]: item["query"] for item in searches}
    receipt_digests = [
        item["receipt"]["sha256"] for item in searches + documents
    ]
    obligations = {
        "v46_dependency_verified": v46["acceptance"]["passed"],
        "evidence_content_digest_valid": _evidence_digest(evidence) == evidence["content_digest"],
        "discovery_source_digest_frozen": evidence["frozen_discovery"]["source_report_digest"] == v46["content_digest"],
        "discovery_commitment_replays": registration["discovery_commitment"] == discovery.commitment == expected_plan["discovery_commitment"],
        "commit_precedes_search_and_full_text": registration["commit_event_index"] < registration["first_search_event_index"] < registration["first_full_text_event_index"],
        "literature_unavailable_during_discovery": not evidence["autonomous_query_plan"]["literature_available_during_discovery"],
        "queries_structurally_selected": evidence["autonomous_query_plan"]["selection_basis"] == expected_plan["selection_basis"],
        "all_queries_allowlisted": actual_queries == expected_queries,
        "paper_ids_not_host_selected": not evidence["autonomous_query_plan"]["host_selected_paper_ids"] and not evidence["autonomous_document_selection"]["selection_host_selected"],
        "official_provider_and_fixed_host": evidence["provider"] == "Europe PMC REST API" and evidence["policy"]["allowlisted_root"] == "https://www.ebi.ac.uk/europepmc/webservices/rest/",
        "arbitrary_network_access_blocked": not evidence["policy"]["arbitrary_queries_allowed"] and not evidence["policy"]["arbitrary_urls_allowed"],
        "request_budget_respected": 0 < evidence["request_count"] <= v46_campaign["budgets"]["network_requests_remaining"],
        "metadata_breadth_sufficient": len(searches) == len(QUERY_SPECS) and evidence["metadata_record_count"] >= 25,
        "open_full_text_depth_sufficient": len(documents) >= 4 and all(item["body_word_count"] >= 1000 for item in documents),
        "explicit_open_licences_detected": all(item["open_licence_detected"] and item["licence_url"] for item in documents),
        "full_text_not_copied_into_repository": not evidence["policy"]["full_text_retained"] and all(not item["full_text_stored_in_repository"] for item in documents),
        "all_network_receipts_valid": len(receipt_digests) == evidence["request_count"] and all(re.fullmatch(r"[0-9a-f]{64}", item) for item in receipt_digests) and all(item["receipt"]["status"] == 200 for item in searches + documents),
        "known_prior_art_detected": audit["foundational_prior_art_detected"] and audit["known_components_detected"],
        "exact_identity_not_overclaimed": not audit["exact_formula_identity_established"],
        "human_unknown_claim_blocked": not audit["human_unknown_claim_allowed"],
        "literature_cannot_modify_discovery": not audit["discovery_was_modified_by_literature"],
        "campaign_resumed_and_task_completed": campaign["resumed_from_prior_state"] and campaign["completed_task"] == "full_text_literature_review",
        "next_task_selected_without_host": campaign["next_selected_task"] == "semantic_transfer_counterexample_campaign" and not campaign["next_selection_host_selected"],
    }
    proof_obligations = [
        {"obligation_id": key, "passed": bool(value)} for key, value in obligations.items()
    ]
    passed = all(obligations.values())
    return {
        "acceptance_version": "full-text-literature-research-v47.0",
        "passed": passed,
        "final_status": "verified" if passed else "rejected",
        "frozen_discovery": {
            **discovery.payload(),
            "commitment": discovery.commitment,
            "human_translation_post_hoc": "a three-input product-like interaction plus a predicate-gated asymmetric term",
        },
        "autonomous_research_action": {
            "selected_task": "full_text_literature_review",
            "selection_inherited_from_v46": True,
            "provider": evidence["provider"],
            "search_count": len(searches),
            "metadata_record_count": evidence["metadata_record_count"],
            "full_text_document_count": len(documents),
            "network_request_count": evidence["request_count"],
            "paper_selection_host_selected": False,
        },
        "open_full_text_evidence": {
            "documents": documents,
            "selection": evidence["autonomous_document_selection"],
            "full_text_retained": False,
            "source_snapshot_digest": evidence["content_digest"],
        },
        "prior_art_audit": audit,
        "long_horizon_research": {
            "previous_campaign_cycle": v46_campaign["cycle_index"],
            "campaign": campaign,
        },
        "proof_obligations": proof_obligations,
        "claim_state": {
            "autonomous_full_text_audit_allowed": passed,
            "known_method_family_detected": audit["foundational_prior_art_detected"],
            "exact_composite_known_claim_allowed": False,
            "human_unknown_law_allowed": False,
            "exhaustive_global_novelty_review_allowed": False,
            "fully_autonomous_scientist_allowed": False,
            "current_label": "V47_AUTONOMOUS_OPEN_FULL_TEXT_AUDIT_VERIFIED_GLOBAL_NOVELTY_AND_PHYSICAL_SCIENCE_EXTERNAL",
        },
        "limitations": [
            "Europe PMC is a large open literature corpus, not all human publications, books, patents, or unpublished knowledge.",
            "Phrase-count fingerprints support reproducible triage but are not equivalent to expert semantic identity review.",
            "The exact OPX composite was not proved new and was not proved identical to a published formula.",
            "No physical experiment, instrument fabrication, or independent laboratory replication occurred in V47.",
        ],
    }


def verify_v47_acceptance(acceptance):
    fresh = run_v47_acceptance()
    checks = {
        "reported_acceptance_passed": acceptance.get("passed") is True,
        "frozen_commitment_matches": acceptance.get("frozen_discovery", {}).get("commitment") == fresh["frozen_discovery"]["commitment"],
        "source_snapshot_digest_matches": acceptance.get("open_full_text_evidence", {}).get("source_snapshot_digest") == fresh["open_full_text_evidence"]["source_snapshot_digest"],
        "document_receipts_match": [
            item["receipt"]["sha256"] for item in acceptance.get("open_full_text_evidence", {}).get("documents", [])
        ] == [item["receipt"]["sha256"] for item in fresh["open_full_text_evidence"]["documents"]],
        "dimension_coverage_matches": acceptance.get("prior_art_audit", {}).get("dimension_coverage") == fresh["prior_art_audit"]["dimension_coverage"],
        "campaign_checkpoint_matches": acceptance.get("long_horizon_research", {}).get("campaign", {}).get("checkpoint_digest") == fresh["long_horizon_research"]["campaign"]["checkpoint_digest"],
        "claims_remain_conservative": acceptance.get("claim_state", {}).get("human_unknown_law_allowed") is False and acceptance.get("claim_state", {}).get("fully_autonomous_scientist_allowed") is False,
    }
    return {
        "verifier_version": "independent-full-text-literature-verifier-v47.0",
        "passed": all(checks.values()),
        "obligations": [
            {"obligation_id": key, "passed": bool(value)} for key, value in checks.items()
        ],
    }
