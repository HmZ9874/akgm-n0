"""V42 acceptance for counterexample-guided transfer on the reused NASA archive."""
from __future__ import annotations

import json
from pathlib import Path

from akgm_n0.learner.counterexample_transfer_v42 import (
    CounterexampleTransferResearchV42,
    transfer_program_commitment_v42,
)
from akgm_n0.learner.dynamic_state_v41 import (
    AnonymousTraceV41,
    DynamicProgramV41,
    DynamicStateResearchV41,
)

ROOT = Path(__file__).resolve().parents[3]
CHALLENGE = ROOT / "data/nasa_v41/nasa_battery_v41_blind_challenge.json"
V41_REPORT = ROOT / "reports/data/official_dynamic_science_v41_latest.json"
V41_CHALLENGE = ROOT / "reports/data/nasa_v41_blind_challenge_latest.json"


def _anonymous_trace(payload):
    """Remove source object, life stage, and archive indices before discovery."""
    return AnonymousTraceV41.from_dict({
        "trace_id": payload["trace_id"],
        "samples": payload["samples"],
    })


class SealedTransferArchiveV42:
    """Expose object A for discovery and object B only after a program commitment."""

    def __init__(self, payload):
        self._payload = payload
        self._commitment = None
        self._event_index = 0

    def discovery(self):
        if self._commitment is not None:
            raise RuntimeError("discovery partition cannot be reopened after commitment")
        source = [item for item in self._payload["traces"] if item["source_cell"] == "RW5"]
        self._event_index += 1
        return {
            "training": tuple(_anonymous_trace(item) for item in source[::2]),
            "validation": tuple(_anonymous_trace(item) for item in source[1::2]),
            "event_index": self._event_index,
            "labels_exposed": False,
        }

    def commit(self, commitment):
        if self._commitment is not None:
            raise RuntimeError("only one frozen commitment is allowed")
        self._commitment = commitment
        self._event_index += 1
        return {"commitment": commitment, "event_index": self._event_index}

    def reveal_transfer(self, commitment):
        if commitment != self._commitment or self._commitment is None:
            raise RuntimeError("transfer object is sealed until the selected program is committed")
        source = [item for item in self._payload["traces"] if item["source_cell"] == "RW6"]
        self._event_index += 1
        return {
            "traces": tuple(_anonymous_trace(item) for item in source),
            "stage_by_trace": {item["trace_id"]: item["life_stage"] for item in source},
            "event_index": self._event_index,
            "labels_exposed_to_program": False,
        }


def _v41_program(payload):
    return DynamicProgramV41(
        payload["kind"],
        tuple(payload["coefficients"]),
        payload["validation_rmse"],
        payload["validation_mape"],
        payload["node_count"],
    )


def run_v42_acceptance():
    snapshot = json.loads(CHALLENGE.read_text(encoding="utf-8"))
    v41 = json.loads(V41_REPORT.read_text(encoding="utf-8"))
    v41_challenge = json.loads(V41_CHALLENGE.read_text(encoding="utf-8"))
    previous_failure = v41_challenge["challenge"]["counterexample"]

    archive = SealedTransferArchiveV42(snapshot)
    discovery = archive.discovery()
    researcher = CounterexampleTransferResearchV42()
    selected, candidates = researcher.discover(
        discovery["training"], discovery["validation"],
    )
    commitment = transfer_program_commitment_v42(selected)
    commit = archive.commit(commitment)
    transfer = archive.reveal_transfer(commitment)

    overall = researcher.evaluate(selected, transfer["traces"])
    by_stage = {}
    for stage in ("early", "middle", "late"):
        traces = tuple(
            trace for trace in transfer["traces"]
            if transfer["stage_by_trace"][trace.trace_id] == stage
        )
        by_stage[stage] = researcher.evaluate(selected, traces)

    candidate_rows = [candidate.to_dict() for candidate in candidates]
    candidate_validation = {
        candidate.kind: {
            "validation_rmse": candidate.validation_rmse,
            "validation_mape": candidate.validation_mape,
            "node_count": candidate.node_count,
        }
        for candidate in candidates
    }
    parent_candidate = next(item for item in candidates if item.kind == "state_fold")

    frozen_v41_payload = v41["acceptance"]["discovery"]["selected"]
    frozen_v41 = _v41_program(frozen_v41_payload)
    v41_researcher = DynamicStateResearchV41()
    frozen_v41_overall = v41_researcher.evaluate(frozen_v41, transfer["traces"])
    frozen_v41_late = v41_researcher.evaluate(
        frozen_v41,
        tuple(
            trace for trace in transfer["traces"]
            if transfer["stage_by_trace"][trace.trace_id] == "late"
        ),
    )

    stages_pass = {
        "early": by_stage["early"]["rmse"] < 0.10,
        "middle": by_stage["middle"]["rmse"] < 0.10,
        "late": by_stage["late"]["rmse"] < 0.10,
    }
    counterexample_feedback = {
        "consumed_failure_id": previous_failure["failure_id"],
        "previous_observed_rmse": previous_failure["observed_rmse"],
        "previous_threshold": previous_failure["expected_max_rmse"],
        "previous_scope_restriction_preserved": previous_failure["universal_formula_removed"],
        "created_response": selected.kind,
        "new_transfer_late_rmse": by_stage["late"]["rmse"],
        "late_rmse_ratio_to_v41": by_stage["late"]["rmse"] / frozen_v41_late["rmse"],
        "resolved_on_reused_archive": stages_pass["late"],
        "fresh_external_replication_still_required": True,
    }
    gates = {
        "v41_counterexample_consumed": previous_failure["failure_id"] == "V41-CHALLENGE-LATE-LIFE-EXTRAPOLATION",
        "source_and_stage_labels_hidden_during_discovery": not discovery["labels_exposed"],
        "candidate_selected_before_transfer_reveal": commit["event_index"] < transfer["event_index"],
        "program_frozen_without_transfer_refit": commitment == transfer_program_commitment_v42(selected),
        "interaction_semantic_created": selected.kind == "interaction_fold",
        "created_semantic_beats_parent_on_validation": selected.validation_rmse < parent_candidate.validation_rmse,
        "transfer_object_has_sixty_trajectories": overall["trace_count"] == 60,
        "early_transfer_below_threshold": stages_pass["early"],
        "middle_transfer_below_threshold": stages_pass["middle"],
        "late_transfer_below_threshold": stages_pass["late"],
        "late_transfer_improves_frozen_v41": by_stage["late"]["rmse"] < frozen_v41_late["rmse"],
        "fresh_human_blind_claim_blocked": True,
        "human_unknown_law_claim_blocked": True,
    }
    proof_obligations = [
        {"obligation_id": key, "passed": value} for key, value in gates.items()
    ]
    passed = all(item["passed"] for item in proof_obligations)
    return {
        "benchmark_version": "counterexample-transfer-v42.0",
        "passed": passed,
        "final_status": "verified" if passed else "bounded",
        "classification": "programmatically_sealed_reused_archive_cross_object_transfer",
        "protocol": {
            "discovery_object": "anonymous_object_A",
            "transfer_object": "anonymous_object_B",
            "discovery_training_trace_count": len(discovery["training"]),
            "discovery_validation_trace_count": len(discovery["validation"]),
            "transfer_trace_count": len(transfer["traces"]),
            "human_quantity_names_exposed_to_learner": False,
            "source_identity_exposed_to_learner": False,
            "life_stage_exposed_to_learner": False,
            "developer_had_prior_access_to_archive": True,
            "fresh_human_blind_replication": False,
        },
        "discovery": {
            "selected": selected.to_dict(),
            "candidates": candidate_rows,
            "candidate_validation": candidate_validation,
            "selection_score": selected.validation_rmse + selected.node_count * 1e-5,
            "complexity_penalty_per_node": 1e-5,
        },
        "preregistration": {
            "program_commitment": commitment,
            "discovery_event_index": discovery["event_index"],
            "commit_event_index": commit["event_index"],
            "transfer_reveal_event_index": transfer["event_index"],
            "commitment_precedes_programmatic_reveal": commit["event_index"] < transfer["event_index"],
        },
        "transfer_audit": {
            "overall": overall,
            "by_life_stage": by_stage,
            "stage_passes": stages_pass,
            "threshold_rmse": 0.10,
            "frozen_v41_overall": frozen_v41_overall,
            "frozen_v41_late": frozen_v41_late,
        },
        "counterexample_feedback": counterexample_feedback,
        "discovery_gates": gates,
        "proof_obligations": proof_obligations,
        "claim_state": {
            "reused_archive_cross_object_transfer_allowed": passed,
            "fresh_external_replication_claim_allowed": False,
            "universal_all_life_model_allowed": False,
            "human_unknown_claim_allowed": False,
            "current_label": "V42_REUSED_ARCHIVE_TRANSFER_VERIFIED_EXTERNAL_REPLICATION_REQUIRED",
        },
        "limitations": [
            "RW6 was sealed from the learner until program commitment, but developers had prior access to this reused archive.",
            "The result is a reproducible engineering transfer test, not a fresh human-blind preregistration.",
            "INTERACTION_FOLD is a system-composed reusable computation, not a human-unknown electrochemical law.",
            "Passing one additional object does not establish a universal all-life battery model.",
            "Independent data from a different campaign or laboratory is required next.",
        ],
    }
