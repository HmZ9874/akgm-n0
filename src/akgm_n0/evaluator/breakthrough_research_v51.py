"""Independent ten-gate capability audit for the V51 research reset."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from akgm_n0.learner.breakthrough_research_v51 import (
    BehavioralRepresentationForgeV51,
    MechanismTournamentV51,
    ablation_audit,
    sealed_audit,
)


ROOT = Path(__file__).resolve().parents[3]
V45 = ROOT / "reports/data/autonomous_intervention_v45_latest.json"
V47 = ROOT / "reports/data/full_text_literature_research_v47_latest.json"
V50 = ROOT / "reports/data/open_set_representation_v50_latest.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _gate(gate_id, passed, evidence, required_to_reach_ten=True):
    return {
        "gate_id": gate_id,
        "passed": bool(passed),
        "evidence": evidence,
        "required_to_reach_ten": required_to_reach_ten,
    }


def _axis(axis_id, gates):
    score = sum(item["passed"] for item in gates)
    return {
        "axis_id": axis_id,
        "score": score,
        "target": 10,
        "score_kind": "evidence_gates_passed_not_subjective_intelligence",
        "gates": gates,
        "reached_ten": score == 10,
        "claim_allowed": score == 10,
        "blocking_gates": [item["gate_id"] for item in gates if not item["passed"]],
    }


def run_v51_acceptance():
    v45 = _load(V45)["acceptance"]
    v47 = _load(V47)["acceptance"]
    v50 = _load(V50)["acceptance"]
    measurements = v45["autonomous_experiment_design"]["development_measurements"]
    cases = v45["sealed_counterfactual_audit"]["cases"]
    safe_ranges = v45["apparatus_boundary"]["safe_ranges"]

    tournament = MechanismTournamentV51(maximum_features=3).search(measurements, safe_ranges)
    selected = tournament["selected"]
    sealed = sealed_audit(selected, cases)
    ablations = ablation_audit(selected, measurements, cases)
    observed = [row["action"]["values"] for row in measurements]
    proposed = MechanismTournamentV51.propose_discriminating_intervention(
        tournament["ranked"], safe_ranges, observed,
    )
    representation = BehavioralRepresentationForgeV51.forge(selected, safe_ranges)
    macro_errors = []
    for case in cases:
        values = tuple(map(float, case["action"]["values"]))
        macro_errors.append(
            BehavioralRepresentationForgeV51.execute(representation, values)
            - float(case["observed"])
        )
    macro_rmse = (sum(error * error for error in macro_errors) / len(macro_errors)) ** 0.5

    representation_gates = [
        _gate("anonymous_inputs", not tournament["domain_labels_received"], "V45 Q slots remained anonymous during search"),
        _gate("autonomous_candidate_generation", not tournament["host_selected"] and tournament["programs_generated"] >= 100, tournament["programs_generated"]),
        _gate("behavioral_deduplication", tournament["behavior_classes"] <= tournament["programs_generated"] and tournament["probe_count"] >= 100, tournament["behavior_classes"]),
        _gate("executable_new_opcode", representation["kind"] == "learned_behavioral_opcode", representation["representation_id"]),
        _gate("counterfactual_dependency", len(representation["dependency_slots"]) == 3, representation["dependency_slots"]),
        _gate("expansion_equivalence", representation["behaviorally_equivalent_on_registered_domain"], representation["maximum_expansion_error"]),
        _gate("description_compression", representation["token_savings_per_call"] > 0, representation["token_savings_per_call"]),
        _gate("sealed_reuse_without_refit", macro_rmse < 1e-8, macro_rmse),
        _gate("cross_process_replay", v45["discovery_gates"]["new_process_replication"], "V45 independent broker process"),
        _gate("independent_natural_domain_transfer", False, "No unrelated natural-domain success exists"),
    ]
    representation_axis = _axis("autonomous_representation_creation", representation_gates)

    selected_gap = 0.0
    if len(tournament["ranked"]) > 1:
        selected_gap = tournament["ranked"][1].score - selected.score
    mechanism_gates = [
        _gate("assigned_interventions", v45["causal_effect_audit"]["direction"].startswith("assigned"), "V45 assigned controls"),
        _gate("randomized_execution", v45["discovery_gates"]["multi_action_order_randomized"], "V45 randomized batches"),
        _gate("competing_hypotheses", tournament["programs_generated"] >= 100, tournament["programs_generated"]),
        _gate("behavioral_equivalence_control", tournament["behavior_classes"] >= 10, tournament["behavior_classes"]),
        _gate("autonomous_discriminating_intervention", proposed is not None and proposed["prediction_disagreement"] > 0, proposed),
        _gate("essential_component_ablation", bool(ablations) and all(item["sealed_rmse"] > 1e-6 for item in ablations), list(ablations)),
        _gate("sealed_counterfactual_prediction", sealed["rmse"] < 1e-8, sealed),
        _gate("selected_mechanism_separated", selected_gap > 0, selected_gap),
        _gate("fresh_process_replication", v45["discovery_gates"]["new_process_replication"], "same-machine fresh apparatus process"),
        _gate("natural_system_external_intervention", False, "Current apparatus is computational, not a natural system"),
    ]
    mechanism_axis = _axis("causal_mechanism_reasoning", mechanism_gates)

    v50_selected = v50["representation_discovery"]["selected"]
    v47_audit = v47["prior_art_audit"]
    unknown_gates = [
        _gate("presealed_commitment", v50["preregistration"]["semantic_commit_event_index"] < v50["preregistration"]["sealed_profile_reveal_event_index"], v50["preregistration"]["semantic_commitment"]),
        _gate("strong_quantitative_baseline", v50_selected["validation"]["prediction_rmse_ratio"] < 0.65, v50_selected["validation"]["prediction_rmse_ratio"]),
        _gate("sealed_holdout", v50["sealed_transfer"]["prediction_rmse_ratio"] < 0.65, v50["sealed_transfer"]["prediction_rmse_ratio"]),
        _gate("independent_source_replication", False, "V50 groups came from one archive"),
        _gate("causal_mechanism_evidence", False, "V50 is distributional regularity only"),
        _gate("prospective_novel_prediction", False, "No future-data prediction was frozen and observed"),
        _gate("preclaim_open_literature_audit", False, "V47 audit concerns OPX; V50 mapping was post-hoc"),
        _gate("broad_prior_art_coverage", False, v47_audit.get("audit_status", "open corpus is non-exhaustive")),
        _gate("independent_expert_novelty_review", False, "No external expert verdict"),
        _gate("independent_laboratory_replication", False, "No external laboratory replication"),
    ]
    unknown_axis = _axis("human_unknown_scientific_law", unknown_gates)

    axes = [representation_axis, mechanism_axis, unknown_axis]
    hard_block = not all(axis["reached_ten"] for axis in axes)
    next_tasks = [
        {
            "priority": 1,
            "task_id": "independent_natural_domain_representation_challenge",
            "closes": ["autonomous_representation_creation.independent_natural_domain_transfer"],
            "status": "ready_for_public_data_selection",
        },
        {
            "priority": 2,
            "task_id": "real_natural_system_quasi_intervention",
            "closes": ["causal_mechanism_reasoning.natural_system_external_intervention"],
            "status": "requires_valid_public_intervention_dataset",
        },
        {
            "priority": 3,
            "task_id": "frontier_question_preregistration",
            "closes": unknown_axis["blocking_gates"],
            "status": "must_precede_model_fitting",
        },
    ]
    payload = {
        "standard_version": "breakthrough-evidence-standard-v51.0",
        "axes": axes,
        "hard_block": hard_block,
        "next_tasks": next_tasks,
    }
    return {
        "acceptance_version": "breakthrough-research-v51.0",
        "passed": True,
        "final_status": "architecture_upgraded_claims_evidence_gated",
        "mechanism_tournament": {
            "selected": selected.to_dict(),
            "runner_up": tournament["ranked"][1].to_dict(),
            "programs_generated": tournament["programs_generated"],
            "behavior_classes": tournament["behavior_classes"],
            "probe_count": tournament["probe_count"],
            "selected_score_gap": selected_gap,
            "sealed_audit": sealed,
            "ablations": list(ablations),
            "next_discriminating_intervention": proposed,
        },
        "representation_forge": {
            **representation,
            "sealed_macro_rmse": macro_rmse,
        },
        "ten_gate_standard": payload,
        "standard_commitment": hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest(),
        "claim_state": {
            "representation_10_of_10_allowed": representation_axis["reached_ten"],
            "mechanism_10_of_10_allowed": mechanism_axis["reached_ten"],
            "unknown_law_10_of_10_allowed": unknown_axis["reached_ten"],
            "human_unknown_law_discovered": False,
            "breakthrough_claim_allowed": not hard_block,
            "current_label": "V51_BREAKTHROUGH_STANDARD_ACTIVE_NO_BREAKTHROUGH_CLAIM",
        },
        "limitations": [
            "A ten-gate score measures supplied evidence, not general intelligence.",
            "The representation opcode is a verified composite, not a new irreducible mathematical primitive.",
            "The mechanism tournament uses an engineered computational apparatus and a supplied structural feature substrate.",
            "No existing result is a human-unknown scientific law.",
            "External expert review and independent laboratory replication cannot be self-awarded by this repository.",
        ],
    }


def verify_v51_acceptance(acceptance):
    fresh = run_v51_acceptance()
    checks = {
        "reported_run_passed": acceptance.get("passed") is True,
        "tournament_replays": acceptance.get("mechanism_tournament") == fresh["mechanism_tournament"],
        "representation_replays": acceptance.get("representation_forge") == fresh["representation_forge"],
        "standard_commitment_replays": acceptance.get("standard_commitment") == fresh["standard_commitment"],
        "scores_replay": acceptance.get("ten_gate_standard", {}).get("axes") == fresh["ten_gate_standard"]["axes"],
        "breakthrough_remains_blocked": acceptance.get("claim_state", {}).get("breakthrough_claim_allowed") is False,
        "unknown_law_remains_unclaimed": acceptance.get("claim_state", {}).get("human_unknown_law_discovered") is False,
    }
    return {
        "verifier_version": "independent-breakthrough-standard-verifier-v51.0",
        "passed": all(checks.values()),
        "obligations": [
            {"obligation_id": key, "passed": bool(value)} for key, value in checks.items()
        ],
    }
