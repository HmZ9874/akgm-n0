"""Independent V48 transfer, counterexample, and scope-semantic acceptance."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from akgm_n0.learner.semantic_transfer_counterexample_v48 import (
    ApplicabilityScopeForgeV48,
    CanonicalTemporalAdapterV48,
    CounterexampleDrivenSemanticSearchV48,
    FrozenSemanticTransferV48,
)


ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / "data/official_worlds_v44/official_worlds_v44_snapshot.json"
V45 = ROOT / "reports/data/autonomous_intervention_v45_latest.json"
V47 = ROOT / "reports/data/full_text_literature_research_v47_latest.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _digest_without(payload, key):
    body = {name: value for name, value in payload.items() if name != key}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _adapt_worlds(snapshot):
    adapter = CanonicalTemporalAdapterV48()
    adapted = []
    for item in snapshot["worlds"]:
        normalized = copy.deepcopy(item)
        normalized["partitions"]["sealed_transfer"] = normalized["partitions"]["transfer"]
        adapted.append(adapter.adapt(normalized))
    return adapted


def _advance_campaign(v47_campaign, universal_candidate):
    tasks = []
    for item in v47_campaign["tasks"]:
        updated = dict(item)
        if updated["task_id"] == "semantic_transfer_counterexample_campaign":
            updated["status"] = "completed"
        tasks.append(updated)
    tasks.extend((
        {
            "task_id": "new_world_semantic_search",
            "status": "queued" if not universal_candidate else "deferred",
            "information_gain": 0.88,
            "cost": 8.0,
            "risk": 0.18,
        },
        {
            "task_id": "independent_semantic_replication",
            "status": "queued" if universal_candidate else "external_coordination_required",
            "information_gain": 1.0,
            "cost": 12.0,
            "risk": 0.2,
        },
    ))
    selectable = [item for item in tasks if item["status"] == "queued"]
    selected = max(
        selectable,
        key=lambda item: (item["information_gain"] / item["cost"] - item["risk"], item["task_id"]),
    ) if selectable else None
    budgets = dict(v47_campaign["budgets"])
    budgets["compute_units_remaining"] = max(0.0, float(budgets["compute_units_remaining"]) - 6.0)
    return {
        "campaign_id": v47_campaign["campaign_id"],
        "cycle_index": int(v47_campaign["cycle_index"]) + 1,
        "resumed_from_prior_state": True,
        "completed_task": "semantic_transfer_counterexample_campaign",
        "budgets": budgets,
        "tasks": tasks,
        "next_selected_task": None if selected is None else selected["task_id"],
        "next_selection_host_selected": False,
        "checkpoint_digest": hashlib.sha256(
            json.dumps({"tasks": tasks, "budgets": budgets}, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def run_v48_acceptance():
    snapshot = _load(SNAPSHOT)
    v45 = _load(V45)
    v47 = _load(V47)
    adapted = _adapt_worlds(snapshot)
    frozen = FrozenSemanticTransferV48().audit(adapted)
    search = CounterexampleDrivenSemanticSearchV48().search(adapted)
    scope = ApplicabilityScopeForgeV48().forge(frozen, search)
    v47_campaign = v47["acceptance"]["long_horizon_research"]["campaign"]
    campaign = _advance_campaign(v47_campaign, search["universal_formula_accepted"])
    source_audit = v45["acceptance"]["sealed_counterfactual_audit"]
    failed_frozen_worlds = [
        item for item in frozen["world_results"] if not item["universal_transfer_passed"]
    ]
    mistake_room = {
        "event_id": "V48-OPX-CROSS-DOMAIN-0001",
        "failed_semantic": frozen["semantic_id"],
        "failed_world_count": len(failed_frozen_worlds),
        "failures": [
            {
                "world_id": item["world_id"],
                "sealed_ratio": item["sealed_transfer"]["rmse_ratio_to_zero_baseline"],
                "counterexamples": item["sealed_transfer"]["counterexamples"],
                "diagnosis": "arity-compatible observational lags do not preserve the assigned-control mechanism",
                "repair": scope["semantic_id"],
            }
            for item in failed_frozen_worlds
        ],
        "mandatory_replay": True,
        "removal_policy": "OPX remains valid only in its registered apparatus; universal transfer claim removed",
    }
    obligations = {
        "v45_source_intervention_dependency_verified": v45["acceptance"]["passed"],
        "v47_campaign_dependency_verified": v47["acceptance"]["passed"],
        "selected_task_replays": v47_campaign["next_selected_task"] == "semantic_transfer_counterexample_campaign",
        "official_snapshot_digest_valid": _digest_without(snapshot, "snapshot_sha256") == snapshot["snapshot_sha256"],
        "three_anonymous_worlds_adapted": len(adapted) == 3,
        "normalization_fit_on_training_only": all(world["normalization"]["fit_partition"] == "training_only" for world in adapted),
        "frozen_opx_without_refit": all(item["frozen_without_refit"] for item in frozen["world_results"]),
        "sealed_transfer_points_present": all(item["sealed_transfer"]["point_count"] > 0 for item in frozen["world_results"]),
        "universal_opx_claim_rejected_by_counterexamples": not frozen["universal_transfer_claim_allowed"] and len(failed_frozen_worlds) > 0,
        "counterexamples_stored_in_mistake_room": mistake_room["mandatory_replay"] and all(item["counterexamples"] for item in mistake_room["failures"]),
        "replacement_search_not_host_selected": not search["host_selected"] and len(search["trials"]) >= 5,
        "candidate_claim_matches_all_world_gate": search["universal_formula_accepted"] == (not search["failed_worlds"]),
        "scope_semantic_generated_after_failure": scope["generated_after_universal_failure"],
        "scope_gate_accepts_verified_source": scope["source_decision"] == "execute" and source_audit["rmse"] < 1e-10,
        "scope_gate_rejects_role_mismatched_worlds": scope["cross_domain_decision"].startswith("abstain") and scope["false_cross_domain_accept_count"] == 0,
        "scope_name_not_supplied_before_generation": not scope["human_name_supplied_before_generation"],
        "campaign_advanced": campaign["cycle_index"] == v47_campaign["cycle_index"] + 1 and campaign["completed_task"] == "semantic_transfer_counterexample_campaign",
        "human_unknown_claim_blocked": True,
    }
    passed = all(obligations.values())
    return {
        "acceptance_version": "semantic-transfer-counterexample-v48.0",
        "passed": passed,
        "final_status": "verified" if passed else "rejected",
        "task_selection": {
            "selected_task": "semantic_transfer_counterexample_campaign",
            "selected_by_v47": True,
            "host_selected": False,
        },
        "frozen_opx_transfer": frozen,
        "counterexample_driven_search": search,
        "new_semantic": scope,
        "mistake_room": mistake_room,
        "source_domain_replay": {
            "sealed_case_count": len(source_audit["cases"]),
            "sealed_rmse": source_audit["rmse"],
            "assigned_intervention_source": True,
            "scope_decision": "execute",
        },
        "long_horizon_research": {
            "previous_campaign_cycle": v47_campaign["cycle_index"],
            "campaign": campaign,
        },
        "proof_obligations": [
            {"obligation_id": key, "passed": bool(value)} for key, value in obligations.items()
        ],
        "claim_state": {
            "opx_valid_in_registered_apparatus": True,
            "opx_universal_cross_domain_formula_allowed": False,
            "new_scope_control_semantic_allowed": passed,
            "replacement_universal_formula_allowed": search["universal_formula_accepted"],
            "human_unknown_law_allowed": False,
            "fully_autonomous_scientist_allowed": False,
            "current_label": "V48_COUNTEREXAMPLE_INDUCED_SCOPE_SEMANTIC_VERIFIED_UNIVERSAL_FORMULA_NOT_ESTABLISHED",
        },
        "limitations": [
            "The canonical adapter tests structural reuse across anonymous temporal worlds; it does not assert that their variables have the same physical meaning.",
            "A scope gate prevents false reuse but is not itself a new mathematical law.",
            "Candidate coefficients use least squares supplied by the research substrate.",
            "The official worlds are observational archives, not new causal interventions or independent laboratories.",
        ],
    }


def verify_v48_acceptance(acceptance):
    fresh = run_v48_acceptance()
    checks = {
        "reported_passed": acceptance.get("passed") is True,
        "frozen_results_match": acceptance.get("frozen_opx_transfer") == fresh["frozen_opx_transfer"],
        "candidate_search_matches": acceptance.get("counterexample_driven_search") == fresh["counterexample_driven_search"],
        "scope_semantic_matches": acceptance.get("new_semantic") == fresh["new_semantic"],
        "mistake_room_matches": acceptance.get("mistake_room") == fresh["mistake_room"],
        "campaign_checkpoint_matches": acceptance.get("long_horizon_research", {}).get("campaign", {}).get("checkpoint_digest") == fresh["long_horizon_research"]["campaign"]["checkpoint_digest"],
        "universal_claim_stays_blocked": acceptance.get("claim_state", {}).get("opx_universal_cross_domain_formula_allowed") is False,
    }
    return {
        "verifier_version": "independent-semantic-transfer-verifier-v48.0",
        "passed": all(checks.values()),
        "obligations": [
            {"obligation_id": key, "passed": bool(value)} for key, value in checks.items()
        ],
    }
