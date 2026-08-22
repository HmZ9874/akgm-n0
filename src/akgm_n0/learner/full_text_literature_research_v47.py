"""V47 post-discovery open-literature research components.

The V46 semantic is frozen before this audit.  Literature may classify the
result, but it cannot modify the already discovered program or its evidence.
Only compact fingerprints of openly licensed full text enter the repository.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any


QUERY_SPECS = (
    {
        "query_id": "Q-STRUCTURE-SEARCH",
        "query": 'TITLE_ABS:"symbolic regression" AND OPEN_ACCESS:Y sort_cited:y',
        "audit_dimension": "data_driven_structure_search",
    },
    {
        "query_id": "Q-REUSABLE-SEMANTIC",
        "query": '"automatically defined functions" AND OPEN_ACCESS:Y sort_cited:y',
        "audit_dimension": "reusable_composite_semantics",
    },
    {
        "query_id": "Q-GUARDED-FORM",
        "query": '("piecewise function" AND "symbolic regression") AND OPEN_ACCESS:Y sort_cited:y',
        "audit_dimension": "guarded_or_piecewise_expression",
    },
    {
        "query_id": "Q-PARSIMONY",
        "query": '("parsimony" AND "symbolic regression") AND OPEN_ACCESS:Y sort_cited:y',
        "audit_dimension": "accuracy_complexity_tradeoff",
    },
)


SIGNATURES = {
    "structure_search": (
        "symbolic regression", "genetic programming", "program synthesis",
        "expression tree", "search space",
    ),
    "reusable_semantic": (
        "automatically defined function", "subroutine", "reusable",
        "modular", "module", "macro",
    ),
    "guarded_form": (
        "piecewise function", "conditional", "if-then", "if then", "guard",
        "branch",
    ),
    "interaction_product": (
        "interaction term", "product term", "multiplication", "multivariate",
        "epistasis",
    ),
    "parsimony": (
        "parsimony", "complexity", "program size", "description length",
        "simplification", "compression",
    ),
    "verification": (
        "holdout", "cross-validation", "cross validation", "benchmark",
        "generalization", "falsification",
    ),
}


def canonical_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class FrozenDiscoveryV47:
    semantic_id: str
    expansion_features: tuple[str, ...]
    expansion_coefficients: tuple[float, ...]
    source_report_digest: str

    def payload(self):
        return {
            "semantic_id": self.semantic_id,
            "expansion_features": list(self.expansion_features),
            "expansion_coefficients": list(self.expansion_coefficients),
            "source_report_digest": self.source_report_digest,
        }

    @property
    def commitment(self):
        return canonical_digest(self.payload())


class AutonomousLiteraturePlannerV47:
    """Select post-hoc audit dimensions from structural properties only."""

    @staticmethod
    def plan(discovery: FrozenDiscoveryV47):
        features = discovery.expansion_features
        observed = {
            "data_driven_structure_search": True,
            "reusable_composite_semantics": len(features) > 1,
            "guarded_or_piecewise_expression": any(item.startswith("GUARD(") for item in features),
            "accuracy_complexity_tradeoff": True,
        }
        selected = [dict(item) for item in QUERY_SPECS if observed[item["audit_dimension"]]]
        return {
            "selected_queries": selected,
            "query_count": len(selected),
            "selection_basis": observed,
            "host_selected_paper_ids": False,
            "literature_available_during_discovery": False,
            "discovery_commitment": discovery.commitment,
        }


class FullTextPriorArtAuditorV47:
    @staticmethod
    def _tokens(text):
        return set(re.findall(r"[a-z0-9]+", text.lower()))

    def rank_metadata(self, searches, limit=6):
        profile = {
            "symbolic", "regression", "program", "synthesis", "genetic",
            "function", "grammar", "size", "equation", "discovery",
        }
        candidates = {}
        for search in searches:
            query_id = search["query_id"]
            for rank, item in enumerate(search["records"]):
                pmcid = item.get("pmcid")
                if not pmcid or not item.get("is_open_access"):
                    continue
                title_tokens = self._tokens(item.get("title") or "")
                overlap = len(profile & title_tokens) / max(len(profile), 1)
                score = 2.5 * overlap + 0.18 * math.log1p(item.get("cited_by_count", 0)) + 1.0 / (rank + 1)
                existing = candidates.setdefault(pmcid, {
                    **item,
                    "query_ids": [],
                    "best_metadata_score": 0.0,
                    "best_query_rank": rank,
                })
                existing["query_ids"].append(query_id)
                existing["best_metadata_score"] = max(existing["best_metadata_score"], score)
                existing["best_query_rank"] = min(existing["best_query_rank"], rank)
        ranked = sorted(
            candidates.values(),
            key=lambda item: (-len(set(item["query_ids"])), -item["best_metadata_score"], item["pmcid"]),
        )
        chosen = []
        covered = set()
        for spec in QUERY_SPECS:
            options = [item for item in ranked if spec["query_id"] in item["query_ids"] and item["pmcid"] not in {x["pmcid"] for x in chosen}]
            if options:
                chosen.append(options[0])
                covered.add(spec["query_id"])
        for item in ranked:
            if len(chosen) >= limit:
                break
            if item["pmcid"] not in {x["pmcid"] for x in chosen}:
                chosen.append(item)
        return {
            "selected": chosen[:limit],
            "selection_host_selected": False,
            "selection_rule": "one highest metadata score per audit dimension, then global score",
            "covered_query_ids": sorted(covered),
        }

    def audit(self, evidence):
        documents = evidence["full_text_documents"]
        dimension_documents = {name: [] for name in SIGNATURES}
        for document in documents:
            for dimension, count in document["signature_counts"].items():
                if count > 0:
                    dimension_documents[dimension].append(document["pmcid"])
        coverage = {
            name: {
                "document_count": len(set(ids)),
                "pmcids": sorted(set(ids)),
                "detected": bool(ids),
            }
            for name, ids in dimension_documents.items()
        }
        foundational = coverage["structure_search"]["detected"] and coverage["parsimony"]["detected"]
        components = coverage["guarded_form"]["detected"] and coverage["interaction_product"]["detected"]
        reusable = coverage["reusable_semantic"]["detected"]
        exact_single_document = any(
            all(document["signature_counts"].get(name, 0) > 0 for name in (
                "structure_search", "reusable_semantic", "guarded_form", "interaction_product",
            ))
            for document in documents
        )
        if exact_single_document:
            classification = "close_structural_prior_art_detected_exact_formula_identity_not_established"
        elif foundational and (components or reusable):
            classification = "known_method_family_and_known_components_exact_composite_not_established"
        elif foundational:
            classification = "known_method_family_detected_component_relation_unresolved"
        else:
            classification = "insufficient_open_full_text_coverage"
        return {
            "audit_status": classification,
            "full_text_reviewed": bool(documents),
            "full_text_document_count": len(documents),
            "dimension_coverage": coverage,
            "foundational_prior_art_detected": foundational,
            "known_components_detected": components or reusable,
            "single_document_close_structural_match_detected": exact_single_document,
            "exact_formula_identity_established": False,
            "human_unknown_claim_allowed": False,
            "novelty_verdict": "unresolved; open-full-text evidence establishes related prior art but cannot prove global novelty or identity",
            "discovery_was_modified_by_literature": False,
        }


class ResearchCampaignV47:
    @staticmethod
    def advance(v46_campaign, audit, request_count):
        if v46_campaign["next_selected_task"] != "full_text_literature_review":
            raise ValueError("V46 did not select the literature task")
        tasks = []
        for item in v46_campaign["tasks"]:
            updated = dict(item)
            if updated["task_id"] == "full_text_literature_review":
                updated["status"] = "completed" if audit["full_text_reviewed"] else "failed"
            tasks.append(updated)
        tasks.extend((
            {
                "task_id": "semantic_transfer_counterexample_campaign",
                "status": "queued",
                "information_gain": 0.9,
                "cost": 6.0,
                "risk": 0.15,
            },
            {
                "task_id": "independent_expert_novelty_review",
                "status": "external_coordination_required",
                "information_gain": 1.0,
                "cost": 15.0,
                "risk": 0.2,
            },
        ))
        selectable = [item for item in tasks if item["status"] == "queued"]
        selected = max(
            selectable,
            key=lambda item: (item["information_gain"] / item["cost"] - item["risk"], item["task_id"]),
        ) if selectable else None
        budgets = dict(v46_campaign["budgets"])
        budgets["compute_units_remaining"] = max(0.0, float(budgets["compute_units_remaining"]) - 5.0)
        budgets["network_requests_remaining"] = max(0.0, float(budgets["network_requests_remaining"]) - request_count)
        return {
            "campaign_id": v46_campaign["campaign_id"],
            "cycle_index": int(v46_campaign["cycle_index"]) + 1,
            "resumed_from_prior_state": True,
            "completed_task": "full_text_literature_review",
            "budgets": budgets,
            "tasks": tasks,
            "next_selected_task": None if selected is None else selected["task_id"],
            "next_selection_host_selected": False,
            "checkpoint_digest": canonical_digest({"tasks": tasks, "budgets": budgets}),
        }
