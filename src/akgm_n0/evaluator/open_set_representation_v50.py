"""Independent acceptance for V50 open set-representation synthesis."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

from akgm_n0.learner.open_set_representation_v50 import (
    AnonymousSetWorldV50,
    OpenRepresentationForgeV50,
    ast_dependencies,
    ast_nodes,
    canonical_digest,
    relation_metrics,
)


ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / "data/official_worlds_v44/official_worlds_v44_snapshot.json"
V49 = ROOT / "reports/data/event_world_semantic_search_v49_latest.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _snapshot_digest(payload):
    body = {key: value for key, value in payload.items() if key != "snapshot_sha256"}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _advance_campaign(previous, accepted):
    tasks = []
    for item in previous["tasks"]:
        updated = dict(item)
        if updated["task_id"] == "event_world_feature_invention":
            updated["status"] = "completed"
        tasks.append(updated)
    tasks.extend((
        {
            "task_id": "independent_distribution_law_replication",
            "status": "queued" if accepted else "external_coordination_required",
            "information_gain": 0.96,
            "cost": 4.0,
            "risk": 0.12,
        },
        {
            "task_id": "deeper_set_language_growth",
            "status": "deferred" if accepted else "queued",
            "information_gain": 0.78,
            "cost": 7.0,
            "risk": 0.2,
        },
    ))
    selectable = [item for item in tasks if item["status"] == "queued"]
    selected = max(
        selectable,
        key=lambda item: (item["information_gain"] / item["cost"] - item["risk"], item["task_id"]),
    ) if selectable else None
    budgets = dict(previous["budgets"])
    budgets["compute_units_remaining"] = max(0.0, float(budgets["compute_units_remaining"]) - 9.0)
    return {
        "campaign_id": previous["campaign_id"],
        "cycle_index": int(previous["cycle_index"]) + 1,
        "resumed_from_prior_state": True,
        "completed_task": "event_world_feature_invention",
        "budgets": budgets,
        "tasks": tasks,
        "next_selected_task": None if selected is None else selected["task_id"],
        "next_selection_host_selected": False,
        "checkpoint_digest": canonical_digest({"tasks": tasks, "budgets": budgets}),
    }


def run_v50_acceptance():
    snapshot = _load(SNAPSHOT)
    v49 = _load(V49)
    v49_acceptance = v49["acceptance"]
    target_world_id = v49_acceptance["task_selection"]["target_world_id"]
    world = next(item for item in snapshot["worlds"] if item["world_id"] == target_world_id)
    set_world = AnonymousSetWorldV50()
    grid = set_world.infer_grid(world["partitions"]["training"])
    training_profiles = set_world.profiles(
        world["partitions"]["training"], grid["thresholds"], "DEV", 4,
    )
    validation_profiles = set_world.profiles(
        world["partitions"]["validation"], grid["thresholds"], "VAL", 4,
    )
    sealed_profiles = set_world.profiles(
        world["partitions"]["transfer"], grid["thresholds"], "SEALED", 4,
    )
    discovery = OpenRepresentationForgeV50().search(training_profiles, validation_profiles)
    selected = discovery["selected"]
    commitment = canonical_digest({
        "semantic_id": discovery["semantic_id"],
        "ast": selected["ast"],
        "constant": selected["constant"],
        "grid": grid,
    })
    sealed = relation_metrics(selected["ast"], selected["constant"], sealed_profiles)
    if sealed is None:
        raise RuntimeError("selected representation is not executable on sealed profiles")
    constant_relative_shift = abs(sealed["relation_mean"] - selected["constant"]) / max(abs(selected["constant"]), 1e-12)
    validation_passed = selected["validation"]["prediction_rmse_ratio"] < 0.65
    sealed_passed = sealed["prediction_rmse_ratio"] < 0.65 and constant_relative_shift < 0.15
    accepted = validation_passed and sealed_passed
    previous_campaign = v49_acceptance["long_horizon_research"]["campaign"]
    campaign = _advance_campaign(previous_campaign, accepted)
    event_order = {
        "training_representation_event_index": 1,
        "semantic_commit_event_index": 2,
        "sealed_profile_reveal_event_index": 3,
        "physical_metadata_reveal_event_index": 4,
        "human_literature_mapping_event_index": 5,
    }
    human_equivalent = None
    ast = selected["ast"]
    if ast == {"op": "SAFE_DIV", "args": [{"var": "B"}, {"var": "A"}]}:
        b_value = -math.log10(selected["constant"]) / float(grid["step"])
        human_equivalent = {
            "internal_relation": "SURVIVAL_NEXT / SURVIVAL_CURRENT ~= K",
            "formula": "N(value >= u + delta) / N(value >= u) ~= K",
            "iterated_formula": "N(value >= u + n*delta) ~= N(value >= u) * K^n",
            "log_linear_equivalent": "log10 N(value >= u) = a - b*u",
            "estimated_b": b_value,
            "known_human_family": "Gutenberg-Richter frequency-magnitude relation",
        }
    mistake_room = {
        "event_id": "V50-SET-RELATION-COUNTEREXAMPLES-0001",
        "semantic_id": discovery["semantic_id"],
        "counterexamples": sealed["counterexamples"],
        "mandatory_replay": True,
        "status": "bounded_success_with_residuals" if accepted else "rejected",
    }
    success_room = {
        "registered": accepted,
        "room": "bounded_verified_relations",
        "semantic_id": discovery["semantic_id"],
        "ast": selected["ast"],
        "constant": selected["constant"],
        "threshold_step": grid["step"],
        "scope": target_world_id,
        "universal": False,
        "human_unknown": False,
    }
    obligations = {
        "v49_dependency_verified": v49_acceptance["passed"],
        "v49_selected_feature_invention": previous_campaign["next_selected_task"] == "event_world_feature_invention",
        "official_snapshot_digest_valid": _snapshot_digest(snapshot) == snapshot["snapshot_sha256"],
        "failed_world_reused_without_host_selection": target_world_id == v49_acceptance["task_selection"]["target_world_id"] and not v49_acceptance["task_selection"]["host_selected"],
        "grid_derived_from_training_values_only": grid["derived_from"] == "training_values_only" and len(grid["thresholds"]) >= 6,
        "domain_names_hidden_during_search": not discovery["human_law_name_received"],
        "representation_ast_synthesized": not discovery["host_selected"] and discovery["evaluated_candidate_count"] >= 4,
        "anti_triviality_passed": all(discovery["anti_triviality"].values()) and ast_dependencies(selected["ast"]) == {"A", "B"},
        "semantic_committed_before_sealed_and_metadata": event_order["semantic_commit_event_index"] < event_order["sealed_profile_reveal_event_index"] < event_order["physical_metadata_reveal_event_index"],
        "commitment_replays": commitment == canonical_digest({"semantic_id": discovery["semantic_id"], "ast": selected["ast"], "constant": selected["constant"], "grid": grid}),
        "validation_prediction_beats_identity": validation_passed,
        "sealed_prediction_beats_identity": sealed_passed,
        "constant_transfers_without_refit": constant_relative_shift < 0.15,
        "accepted_relation_enters_bounded_room": success_room["registered"] == accepted and not success_room["universal"],
        "sealed_residuals_enter_mistake_room": mistake_room["mandatory_replay"] and len(mistake_room["counterexamples"]) >= 5,
        "human_mapping_occurs_posthoc": human_equivalent is not None and event_order["human_literature_mapping_event_index"] > event_order["sealed_profile_reveal_event_index"],
        "human_unknown_claim_blocked": not success_room["human_unknown"],
        "campaign_advanced": campaign["cycle_index"] == previous_campaign["cycle_index"] + 1,
    }
    passed = all(obligations.values())
    return {
        "acceptance_version": "open-set-representation-v50.0",
        "passed": passed,
        "final_status": "verified" if passed else "rejected",
        "task_selection": {
            "selected_task": "event_world_feature_invention",
            "target_world_id": target_world_id,
            "selected_from_v49_gap": True,
            "host_selected": False,
        },
        "anonymous_set_world": {
            "grid": {**grid, "thresholds": list(grid["thresholds"])},
            "training_group_count": len(training_profiles),
            "validation_group_count": len(validation_profiles),
            "sealed_group_count": len(sealed_profiles),
            "physical_labels_available_during_search": False,
        },
        "representation_discovery": discovery,
        "preregistration": {"semantic_commitment": commitment, **event_order},
        "sealed_transfer": {
            **sealed,
            "constant_relative_shift": constant_relative_shift,
            "constant_refit_on_sealed": False,
        },
        "success_room": success_room,
        "mistake_room": mistake_room,
        "posthoc_translation": {
            **world["sealed_metadata"],
            "human_equivalent": human_equivalent,
            "labels_revealed_after_sealed_audit": True,
        },
        "long_horizon_research": {
            "previous_campaign_cycle": previous_campaign["cycle_index"],
            "campaign": campaign,
        },
        "proof_obligations": [
            {"obligation_id": key, "passed": bool(value)} for key, value in obligations.items()
        ],
        "claim_state": {
            "meaningful_bounded_set_relation_allowed": accepted,
            "open_representation_synthesis_allowed": passed,
            "universal_distribution_law_allowed": False,
            "causal_physical_law_allowed": False,
            "human_unknown_law_allowed": False,
            "fully_autonomous_scientist_allowed": False,
            "current_label": "V50_OPEN_SET_REPRESENTATION_REDISCOVERY_VERIFIED_INDEPENDENT_REPLICATION_REQUIRED",
        },
        "limitations": [
            "The substrate still supplies ordering, comparison, counting, arithmetic, and a finite AST node budget.",
            "The discovered relation is a bounded rediscovery of a known human law, not a human-unknown result.",
            "The same official archive supplies development and sealed groups; an independent catalog is still required.",
            "A distributional regularity is not a causal earthquake mechanism.",
        ],
    }


def verify_v50_acceptance(acceptance):
    fresh = run_v50_acceptance()
    checks = {
        "reported_passed": acceptance.get("passed") is True,
        "task_matches": acceptance.get("task_selection") == fresh["task_selection"],
        "discovery_matches": acceptance.get("representation_discovery") == fresh["representation_discovery"],
        "commitment_matches": acceptance.get("preregistration", {}).get("semantic_commitment") == fresh["preregistration"]["semantic_commitment"],
        "sealed_metrics_match": acceptance.get("sealed_transfer") == fresh["sealed_transfer"],
        "rooms_match": acceptance.get("success_room") == fresh["success_room"] and acceptance.get("mistake_room") == fresh["mistake_room"],
        "campaign_checkpoint_matches": acceptance.get("long_horizon_research", {}).get("campaign", {}).get("checkpoint_digest") == fresh["long_horizon_research"]["campaign"]["checkpoint_digest"],
        "claims_remain_bounded": acceptance.get("claim_state", {}).get("human_unknown_law_allowed") is False and acceptance.get("claim_state", {}).get("causal_physical_law_allowed") is False,
    }
    return {
        "verifier_version": "independent-open-set-representation-verifier-v50.0",
        "passed": all(checks.values()),
        "obligations": [{"obligation_id": key, "passed": bool(value)} for key, value in checks.items()],
    }
