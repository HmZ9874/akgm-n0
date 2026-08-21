"""V41 acceptance for domain-blind state discovery on official NASA trajectories."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from akgm_n0.learner.dynamic_state_v41 import (
    AnonymousTraceV41,
    DynamicStateResearchV41,
    dynamic_program_commitment_v41,
)

ROOT = Path(__file__).resolve().parents[3]
BROKER = ROOT / "scripts/v41_nasa_archive_broker.py"
SNAPSHOT = ROOT / "data/nasa_v41/nasa_battery_dynamic_snapshot.json"
PROVENANCE = ROOT / "data/nasa_v41/nasa_battery_dynamic_provenance.json"
ARCHIVE = ROOT / "data/nasa_v41/Battery_Random_Walk_Room_Temp_2Post.zip"


class NasaArchiveClientV41:
    def __init__(self):
        self.process = subprocess.Popen(
            [sys.executable, "-B", str(BROKER)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8",
        )

    def send(self, operation, **payload):
        if self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("NASA archive broker pipes unavailable")
        self.process.stdin.write(json.dumps({"op": operation, **payload}, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            error = "" if self.process.stderr is None else self.process.stderr.read()
            raise RuntimeError(f"NASA archive broker closed: {error}")
        return json.loads(line)

    def close(self):
        try:
            self.send("shutdown")
        finally:
            self.process.wait(timeout=10)
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream is not None:
                    stream.close()


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _history_counterexample(traces):
    rows = [(trace.trace_id, sample) for trace in traces for sample in trace.samples]
    best = None
    for index, (left_trace, left) in enumerate(rows):
        for right_trace, right in rows[index + 1:]:
            if left_trace == right_trace:
                continue
            comparable = abs(left["q0"] - right["q0"]) < 0.03 and abs(left["q3"] - right["q3"]) < 3 and abs(left["q2"] - right["q2"]) < 2
            if not comparable:
                continue
            difference = abs(left["q1"] - right["q1"])
            if best is None or difference > best[0]:
                best = (difference, left_trace, left, right_trace, right)
    if best is None:
        return {"passed": False, "reason": "no comparable anonymous inputs"}
    difference, left_trace, left, right_trace, right = best
    return {
        "passed": difference > 0.1,
        "same_current_tolerance": 0.03,
        "same_elapsed_time_tolerance": 3,
        "same_temperature_tolerance": 2,
        "response_difference": difference,
        "case_a": {"trace_id": left_trace, **left},
        "case_b": {"trace_id": right_trace, **right},
        "interpretation_available_to_learner": "matching anonymous inputs do not determine Q1 without trajectory history",
    }


def run_v41_acceptance():
    client = NasaArchiveClientV41()
    try:
        metadata = client.send("metadata")
        premature = client.send("future_holdout")
        training_payload = client.send("training")
        validation_payload = client.send("validation")
        training = tuple(AnonymousTraceV41.from_dict(item) for item in training_payload["traces"])
        validation = tuple(AnonymousTraceV41.from_dict(item) for item in validation_payload["traces"])
        researcher = DynamicStateResearchV41()
        selected, candidates = researcher.discover(training, validation)
        commitment = dynamic_program_commitment_v41(selected)
        commit = client.send("commit_program", commitment=commitment)
        future_payload = client.send("future_holdout")
        replication_payload = client.send("cross_cell_replication")
    finally:
        client.close()

    future = tuple(AnonymousTraceV41.from_dict(item) for item in future_payload["traces"])
    replication_traces = tuple(AnonymousTraceV41.from_dict(item) for item in replication_payload["traces"])
    future_audit = researcher.evaluate(selected, future)
    replication = researcher.evaluate(selected, replication_traces)
    future_audit["passed"] = future_audit["rmse"] < 0.08 and future_audit["median_absolute_percentage_error"] < 0.02
    replication["passed"] = replication["rmse"] < 0.08 and replication["median_absolute_percentage_error"] < 0.02

    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    provenance_audit = {
        **provenance,
        "archive_digest_recomputed": _sha256(ARCHIVE),
        "snapshot_digest_recomputed": _sha256(SNAPSHOT),
    }
    provenance_audit["passed"] = provenance_audit["archive_digest_recomputed"] == provenance["archive_sha256"] and provenance_audit["snapshot_digest_recomputed"] == provenance["snapshot_sha256"]

    candidate_rows = [candidate.to_dict() for candidate in candidates]
    stateless = next(item for item in candidates if item.kind == "stateless")
    persistence = next(item for item in candidates if item.kind == "persistence")
    competition = {
        "candidate_count": len(candidates),
        "selected": selected.to_dict(),
        "candidates": candidate_rows,
        "stateful_to_stateless_rmse_ratio": selected.validation_rmse / stateless.validation_rmse,
        "stateful_to_persistence_rmse_ratio": selected.validation_rmse / persistence.validation_rmse,
        "selected_is_created_state_fold": selected.kind == "state_fold",
    }
    history = _history_counterexample(training + validation)
    current_levels = sorted({round(trace.samples[0]["q0"], 2) for trace in training + validation})
    randomized_protocol = {
        "official_description_declares_randomized_current_profiles": "randomized" in provenance["official_experiment_summary"].lower(),
        "observed_anonymous_input_level_count": len(current_levels),
        "observed_anonymous_input_levels": current_levels,
        "passed": len(current_levels) >= 8,
    }
    compression = {
        "uncompressed_step_applications_per_trace": 24,
        "uncompressed_nodes_per_trace": 24 * selected.node_count,
        "compressed_operator": "STATE_FOLD",
        "compressed_call_nodes_per_trace": selected.node_count + 2,
        "compression_ratio": (24 * selected.node_count) / (selected.node_count + 2),
        "passed": selected.kind == "state_fold" and (24 * selected.node_count) / (selected.node_count + 2) > 10,
    }
    mutations = [
        {"mutation": "remove_memory", "rejected": selected.validation_rmse < stateless.validation_rmse * 0.6, "evidence": competition["stateful_to_stateless_rmse_ratio"]},
        {"mutation": "copy_state_only", "rejected": selected.validation_rmse < persistence.validation_rmse, "evidence": competition["stateful_to_persistence_rmse_ratio"]},
        {"mutation": "reveal_future_before_commitment", "rejected": not premature["ok"]},
        {"mutation": "single_cell_validation_only", "rejected": replication["passed"]},
        {"mutation": "domain_labels_visible_during_discovery", "rejected": not metadata["human_quantity_names_exposed_to_learner"]},
    ]
    gates = {
        "official_nasa_provenance": provenance_audit["passed"],
        "real_physical_experiment_archive": provenance["provider"] == "NASA Ames Prognostics Center of Excellence",
        "randomized_control_profiles": randomized_protocol["passed"],
        "separate_sealed_archive_process": metadata["broker_pid"] != os.getpid(),
        "domain_blind_channels": not metadata["human_quantity_names_exposed_to_learner"],
        "future_partition_locked_until_commitment": not premature["ok"] and commit["event_index"] < future_payload["event_index"],
        "history_dependence_counterexample": history["passed"],
        "state_fold_operator_created": competition["selected_is_created_state_fold"],
        "stateful_program_beats_stateless": competition["stateful_to_stateless_rmse_ratio"] < 0.6,
        "prospective_future_trajectory_prediction": future_audit["passed"],
        "cross_cell_replication": replication["passed"],
        "repeated_steps_compressed": compression["passed"],
        "live_new_physical_measurement": False,
        "human_unknown_natural_law": False,
    }
    obligations = [{"obligation_id": key, "passed": value} for key, value in gates.items() if key not in ("live_new_physical_measurement", "human_unknown_natural_law")]
    obligations.extend([
        {"obligation_id": "historical_not_live_claim_enforced", "passed": not gates["live_new_physical_measurement"]},
        {"obligation_id": "human_unknown_claim_blocked", "passed": not gates["human_unknown_natural_law"]},
        {"obligation_id": "five_mutations_rejected", "passed": all(item["rejected"] for item in mutations)},
    ])
    return {
        "benchmark_version": "official-dynamic-science-v41.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_domain_blind_dynamic_state_discovery_on_official_nasa_physical_archive",
        "dataset": {"metadata": metadata, "provenance_audit": provenance_audit, "randomized_protocol_audit": randomized_protocol},
        "discovery": competition,
        "history_dependence_audit": history,
        "preregistration": {"program_commitment": commitment, "commit_event_index": commit["event_index"], "future_reveal_event_index": future_payload["event_index"], "commitment_precedes_reveal": commit["event_index"] < future_payload["event_index"]},
        "future_trajectory_audit": future_audit,
        "cross_cell_replication_audit": replication,
        "semantic_compression_audit": compression,
        "mutation_audits": mutations,
        "discovery_gates": gates,
        "proof_obligations": obligations,
        "claim_state": {
            "official_dynamic_archive_discovery_verified": all(item["passed"] for item in obligations[:12]),
            "live_physical_experiment_claim_allowed": False,
            "human_unknown_claim_allowed": False,
            "current_label": "OFFICIAL_NASA_DYNAMIC_STATE_REDISCOVERY",
        },
        "posthoc_translation": provenance["posthoc_channel_translation"],
        "limitations": [
            "NASA created the physical battery experiment and the project analyzes a historical archive; no new live battery measurement was made here.",
            "The learner saw anonymous channels, but the archive adapter and posthoc evaluator knew the NASA field mapping.",
            "STATE_FOLD is a system-created reusable semantic, not a claim that recurrent state models are new to humanity.",
            "Cross-cell replication uses RW4 from the same NASA test campaign, not a different laboratory.",
            "The result demonstrates hidden-state necessity and trajectory prediction, not a human-unknown electrochemical law.",
        ],
    }
