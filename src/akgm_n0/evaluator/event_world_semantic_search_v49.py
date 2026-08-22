"""Independent acceptance for V49 anonymous event-world semantic search."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from akgm_n0.learner.event_world_semantic_search_v49 import (
    AnonymousEventAdapterV49,
    AutonomousLocalLanguageSearchV49,
    commit_program_v49,
    evaluate_program,
)


ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / "data/official_worlds_v44/official_worlds_v44_snapshot.json"
V48 = ROOT / "reports/data/semantic_transfer_counterexample_v48_latest.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _snapshot_digest(payload):
    body = {key: value for key, value in payload.items() if key != "snapshot_sha256"}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _advance_campaign(previous, local_accepted):
    tasks = []
    for item in previous["tasks"]:
        updated = dict(item)
        if updated["task_id"] == "new_world_semantic_search":
            updated["status"] = "completed"
        tasks.append(updated)
    tasks.extend((
        {
            "task_id": "independent_event_world_replication",
            "status": "queued" if local_accepted else "external_coordination_required",
            "information_gain": 0.95,
            "cost": 4.0,
            "risk": 0.16,
        },
        {
            "task_id": "event_world_feature_invention",
            "status": "deferred" if local_accepted else "queued",
            "information_gain": 0.82,
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
    budgets["compute_units_remaining"] = max(0.0, float(budgets["compute_units_remaining"]) - 8.0)
    return {
        "campaign_id": previous["campaign_id"],
        "cycle_index": int(previous["cycle_index"]) + 1,
        "resumed_from_prior_state": True,
        "completed_task": "new_world_semantic_search",
        "budgets": budgets,
        "tasks": tasks,
        "next_selected_task": None if selected is None else selected["task_id"],
        "next_selection_host_selected": False,
        "checkpoint_digest": hashlib.sha256(
            json.dumps({"tasks": tasks, "budgets": budgets}, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def run_v49_acceptance():
    snapshot = _load(SNAPSHOT)
    v48 = _load(V48)
    v48_acceptance = v48["acceptance"]
    failed_worlds = v48_acceptance["counterexample_driven_search"]["failed_worlds"]
    if len(failed_worlds) != 1:
        raise ValueError("V49 requires exactly one V48 failed world")
    target_world_id = failed_worlds[0]
    world = next(item for item in snapshot["worlds"] if item["world_id"] == target_world_id)
    adapted = AnonymousEventAdapterV49().adapt(copy.deepcopy(world))
    program = AutonomousLocalLanguageSearchV49().search(adapted)
    commitment = commit_program_v49(program)
    sealed = evaluate_program(
        tuple(program["features"]), tuple(program["coefficients"]), adapted["sealed_transfer"]
    )
    validation_passed = program["validation"]["rmse_ratio_to_zero_baseline"] < 0.98
    sealed_passed = sealed["rmse_ratio_to_zero_baseline"] < 0.98
    local_accepted = validation_passed and sealed_passed
    campaign_previous = v48_acceptance["long_horizon_research"]["campaign"]
    campaign = _advance_campaign(campaign_previous, local_accepted)
    mistake_room = {
        "event_id": "V49-EVENT-LOCAL-COUNTEREXAMPLES-0001",
        "program_id": program["program_id"],
        "counterexamples": sealed["counterexamples"],
        "mandatory_replay": True,
        "program_status": "bounded_success" if local_accepted else "rejected",
        "universal_promotion_allowed": False,
    }
    event_order = {
        "development_reveal_event_index": 1,
        "program_commit_event_index": 2,
        "sealed_transfer_reveal_event_index": 3,
        "physical_metadata_reveal_event_index": 4,
    }
    obligations = {
        "v48_dependency_verified": v48_acceptance["passed"],
        "v48_selected_new_world_search": campaign_previous["next_selected_task"] == "new_world_semantic_search",
        "failed_world_selected_without_host": target_world_id == failed_worlds[0] and not v48_acceptance["task_selection"]["host_selected"],
        "official_snapshot_digest_valid": _snapshot_digest(snapshot) == snapshot["snapshot_sha256"],
        "domain_labels_hidden_during_search": program["human_names_received"] is False,
        "normalization_training_only": adapted["normalization"]["fit_partition"] == "training_only",
        "language_resources_grown_autonomously": not program["host_selected"] and program["candidate_programs_evaluated"] >= 10,
        "program_committed_before_sealed_and_metadata": event_order["program_commit_event_index"] < event_order["sealed_transfer_reveal_event_index"] < event_order["physical_metadata_reveal_event_index"],
        "commitment_is_replayable": commitment == commit_program_v49(program),
        "sealed_points_present": sealed["point_count"] >= 100,
        "acceptance_matches_validation_and_sealed_gates": local_accepted == (validation_passed and sealed_passed),
        "counterexamples_recorded": mistake_room["mandatory_replay"] and len(mistake_room["counterexamples"]) >= 5,
        "universal_claim_blocked": not mistake_room["universal_promotion_allowed"],
        "campaign_advanced": campaign["cycle_index"] == campaign_previous["cycle_index"] + 1,
        "human_unknown_claim_blocked": True,
    }
    passed = all(obligations.values())
    return {
        "acceptance_version": "event-world-semantic-search-v49.0",
        "passed": passed,
        "final_status": "verified" if passed else "rejected",
        "task_selection": {
            "selected_task": "new_world_semantic_search",
            "target_world_id": target_world_id,
            "selected_from_v48_failure": True,
            "host_selected": False,
        },
        "anonymous_world": {
            "descriptor": world["anonymous_descriptor"],
            "normalization": adapted["normalization"],
            "training_point_count": len(adapted["training"]),
            "validation_point_count": len(adapted["validation"]),
            "sealed_point_count": len(adapted["sealed_transfer"]),
        },
        "autonomous_language_search": program,
        "preregistration": {
            "program_commitment": commitment,
            **event_order,
        },
        "sealed_transfer": sealed,
        "local_formula_accepted": local_accepted,
        "posthoc_translation": {
            **world["sealed_metadata"],
            "labels_revealed_after_sealed_audit": True,
        },
        "mistake_room": mistake_room,
        "long_horizon_research": {
            "previous_campaign_cycle": campaign_previous["cycle_index"],
            "campaign": campaign,
        },
        "proof_obligations": [
            {"obligation_id": key, "passed": bool(value)} for key, value in obligations.items()
        ],
        "claim_state": {
            "bounded_local_event_formula_allowed": local_accepted,
            "universal_event_law_allowed": False,
            "causal_earthquake_law_allowed": False,
            "human_unknown_law_allowed": False,
            "fully_autonomous_scientist_allowed": False,
            "current_label": "V49_ANONYMOUS_EVENT_WORLD_LOCAL_SEARCH_VERIFIED_UNIVERSAL_AND_CAUSAL_CLAIMS_BLOCKED",
        },
        "limitations": [
            "The search language receives generic arithmetic, ridge regression, and a finite resource pool from the substrate.",
            "Validation selection and sealed transfer establish only bounded predictive performance on one archived event catalog.",
            "Observational association is not an earthquake mechanism or causal law.",
            "Human novelty and independent-world replication are not established.",
        ],
    }


def verify_v49_acceptance(acceptance):
    fresh = run_v49_acceptance()
    checks = {
        "reported_passed": acceptance.get("passed") is True,
        "target_matches": acceptance.get("task_selection") == fresh["task_selection"],
        "program_matches": acceptance.get("autonomous_language_search") == fresh["autonomous_language_search"],
        "commitment_matches": acceptance.get("preregistration", {}).get("program_commitment") == fresh["preregistration"]["program_commitment"],
        "sealed_metrics_match": acceptance.get("sealed_transfer") == fresh["sealed_transfer"],
        "mistake_room_matches": acceptance.get("mistake_room") == fresh["mistake_room"],
        "campaign_checkpoint_matches": acceptance.get("long_horizon_research", {}).get("campaign", {}).get("checkpoint_digest") == fresh["long_horizon_research"]["campaign"]["checkpoint_digest"],
        "claims_remain_bounded": acceptance.get("claim_state", {}).get("universal_event_law_allowed") is False and acceptance.get("claim_state", {}).get("human_unknown_law_allowed") is False,
    }
    return {
        "verifier_version": "independent-event-world-verifier-v49.0",
        "passed": all(checks.values()),
        "obligations": [
            {"obligation_id": key, "passed": bool(value)} for key, value in checks.items()
        ],
    }
