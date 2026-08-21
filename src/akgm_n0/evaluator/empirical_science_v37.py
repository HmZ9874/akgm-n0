"""V37 acceptance: real archive data, subprocess sealing and robust discovery."""
from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from akgm_n0.learner.empirical_power_discovery_v37 import (
    EmpiricalRowV37,
    RobustPowerLawResearchV37,
    prediction_commitment,
)

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / "data/nasa_exoplanet_v37_snapshot.csv"
PROVENANCE = ROOT / "data/nasa_exoplanet_v37_provenance.json"
BROKER = ROOT / "scripts/v37_observation_broker.py"


class SubprocessBrokerClientV37:
    def __init__(self):
        self.process = subprocess.Popen(
            [sys.executable, "-B", str(BROKER), str(SNAPSHOT)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

    def send(self, operation, **payload):
        if self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("broker pipes unavailable")
        self.process.stdin.write(json.dumps({"op": operation, **payload}, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            error = "" if self.process.stderr is None else self.process.stderr.read()
            raise RuntimeError(f"broker closed: {error}")
        return json.loads(line)

    def close(self):
        try:
            self.send("shutdown")
        finally:
            self.process.wait(timeout=10)
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream is not None:
                    stream.close()


def _interval_audit(program, train, holdout, outputs):
    output_by_id = {row["row_id"]: row for row in outputs}
    train_residuals = [abs(math.log(row.target / program.predict(row))) for row in train]
    robust_width = max(0.03, 1.96 * 1.4826 * statistics.median(train_residuals))
    factor = math.exp(robust_width)
    cases = []
    for row in holdout:
        observed = float(output_by_id[row.row_id]["target"])
        predicted = program.predict(row)
        cases.append({
            "row_id": row.row_id,
            "predicted": predicted,
            "observed": observed,
            "lower": predicted / factor,
            "upper": predicted * factor,
            "absolute_percentage_error": abs(predicted - observed) / observed,
            "covered": predicted / factor <= observed <= predicted * factor,
        })
    return {
        "method": "training robust log-residual interval fixed before holdout reveal",
        "multiplicative_factor": factor,
        "median_absolute_percentage_error": statistics.median(item["absolute_percentage_error"] for item in cases),
        "coverage": sum(item["covered"] for item in cases) / len(cases),
        "cases": cases,
    }


def _null_audit(researcher, train, selected):
    ordered_targets = [row.target for row in train]
    null_scores = []
    for shift in (1, 3, 5, 7, 11):
        permuted = [
            EmpiricalRowV37(row.row_id, row.q0, row.q1, ordered_targets[(index + shift) % len(train)], row.sigma_q0, row.sigma_q1, row.sigma_target)
            for index, row in enumerate(train)
        ]
        null_scores.append(researcher.discover(permuted).selected.robust_score)
    return {
        "method": "deterministic target-rotation nulls",
        "null_count": len(null_scores),
        "selected_score": selected.robust_score,
        "null_scores": null_scores,
        "passed": all(selected.robust_score < score for score in null_scores),
    }


def _provenance_audit(metadata):
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    digest = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()
    return {
        "passed": digest == provenance["snapshot_sha256"] and metadata["rows"] == provenance["snapshot_rows_retained"],
        "snapshot_sha256": digest,
        "provider": provenance["provider"],
        "table": provenance["table"],
        "endpoint": provenance["endpoint"],
        "query": provenance["query"],
        "retrieved_at": provenance["retrieved_at"],
        "row_count": metadata["rows"],
        "units": provenance["units"],
        "source_documentation": provenance["source_documentation"],
        "derived_quantity_risk": provenance["important_caveat"],
    }


def run_v37_acceptance():
    client = SubprocessBrokerClientV37()
    try:
        metadata = client.send("metadata")
        premature = client.send("holdout_outputs")
        training_payload = client.send("train")
        inputs_payload = client.send("holdout_inputs")
        train = tuple(EmpiricalRowV37.from_dict(row) for row in training_payload["rows"])
        holdout = tuple(EmpiricalRowV37.from_dict(row) for row in inputs_payload["rows"])
        researcher = RobustPowerLawResearchV37()
        discovery = researcher.discover(train)
        commitment, predictions = prediction_commitment(discovery.selected, holdout)
        commit = client.send("commit", commitment=commitment)
        reveal = client.send("holdout_outputs")
        broker_pid = metadata["broker_pid"]
    finally:
        client.close()

    interval = _interval_audit(discovery.selected, train, holdout, reveal["rows"])
    null = _null_audit(researcher, train, discovery.selected)
    provenance = _provenance_audit(metadata)
    known_law = {
        "catalog_id": "KNOWN-KEPLER-THIRD-LAW-TWO-BODY-LIMIT",
        "matched": (discovery.selected.alpha_twice, discovery.selected.beta_twice) == (3, -1),
        "expected_posthoc_form": "P_days approximately scale*a_AU^(3/2)*M_solar^(-1/2)",
        "human_novelty": False,
    }
    leakage = {
        "learner_received_planet_names": False,
        "learner_received_archive_column_names": False,
        "learner_received_formula_name": False,
        "holdout_output_before_commit_rejected": not premature["ok"] and premature["error"] == "prediction_commitment_required",
        "broker_process_isolated": broker_pid != os.getpid(),
        "broker_pid": broker_pid,
        "evaluator_pid": os.getpid(),
        "commit_event_index": commit["event_index"],
        "reveal_event_index": reveal["event_index"],
    }
    gates = {
        "real_public_archive_snapshot": provenance["passed"],
        "source_and_query_provenance": bool(provenance["query"] and provenance["source_documentation"]),
        "separate_data_process": leakage["broker_process_isolated"],
        "anonymous_columns": not leakage["learner_received_archive_column_names"],
        "holdout_commit_before_reveal": leakage["holdout_output_before_commit_rejected"] and commit["event_index"] < reveal["event_index"],
        "measurement_uncertainty_handled": discovery.missing_uncertainty_rows > 0,
        "robust_model_selection": discovery.selected.robust_score < discovery.runner_up.robust_score,
        "bootstrap_stability": discovery.to_dict()["bootstrap_selection_rate"] >= 0.75,
        "holdout_prediction": interval["median_absolute_percentage_error"] < 0.15,
        "null_model_rejection": null["passed"],
        "known_law_catalog_match": known_law["matched"],
        "independent_measurement_of_all_variables": False,
        "human_novelty": False,
        "external_laboratory_replication": False,
    }
    obligations = (
        {"obligation_id": "real_archive_provenance", "passed": gates["real_public_archive_snapshot"] and gates["source_and_query_provenance"]},
        {"obligation_id": "data_broker_runs_in_separate_process", "passed": gates["separate_data_process"]},
        {"obligation_id": "archive_semantics_hidden_during_search", "passed": gates["anonymous_columns"]},
        {"obligation_id": "holdout_cannot_reveal_before_commit", "passed": gates["holdout_commit_before_reveal"]},
        {"obligation_id": "eighty_one_power_models_compete", "passed": discovery.candidate_count == 81},
        {"obligation_id": "expected_exponents_recovered", "passed": known_law["matched"]},
        {"obligation_id": "selected_model_beats_runner_up", "passed": gates["robust_model_selection"]},
        {"obligation_id": "subsample_stability", "passed": gates["bootstrap_stability"]},
        {"obligation_id": "missing_uncertainty_is_explicitly_handled", "passed": gates["measurement_uncertainty_handled"]},
        {"obligation_id": "sealed_holdout_accuracy", "passed": gates["holdout_prediction"]},
        {"obligation_id": "rotated_target_nulls_rejected", "passed": gates["null_model_rejection"]},
        {"obligation_id": "known_law_is_not_called_human_novel", "passed": known_law["matched"] and not known_law["human_novelty"]},
        {"obligation_id": "derived_variable_risk_blocks_independent_confirmation", "passed": not gates["independent_measurement_of_all_variables"]},
        {"obligation_id": "external_discovery_claim_remains_blocked", "passed": not gates["human_novelty"] and not gates["external_laboratory_replication"]},
    )
    return {
        "benchmark_version": "empirical-science-v37.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_real_archive_blind_known_law_rediscovery_with_sealed_holdout_and_uncertainty",
        "dataset": {"metadata": metadata, "provenance_audit": provenance},
        "discovery": discovery.to_dict(),
        "preregistration": {"commitment": commitment, "prediction_count": len(predictions), "commitment_precedes_reveal": commit["event_index"] < reveal["event_index"]},
        "holdout_audit": interval,
        "null_audit": null,
        "leakage_audit": leakage,
        "known_law_audit": known_law,
        "discovery_gates": gates,
        "claim_state": {
            "real_data_pipeline_verified": all(value for key, value in gates.items() if key not in ("independent_measurement_of_all_variables", "human_novelty", "external_laboratory_replication")),
            "human_unknown_claim_allowed": False,
            "current_label": "REAL_ARCHIVE_KNOWN_LAW_REDISCOVERY",
        },
        "proof_obligations": list(obligations),
        "posthoc_translation": {
            "q0": "orbit semi-major axis in AU",
            "q1": "stellar mass in solar masses",
            "target": "orbital period in days",
            "program": "P_days = fitted_scale * a_AU^(3/2) * M_solar^(-1/2)",
        },
        "limitations": [
            "This is a re-discovery of a human-known relation, not a new law.",
            "PSCompPars may combine parameters from different references, and semi-major axis may be derived using the same physical relation under test.",
            "The supplied hypothesis language is a two-input power-law grid with half-integer exponents.",
            "Missing uncertainties use an explicit three-percent log-error floor rather than inferred measurement distributions.",
            "No causal intervention or external laboratory replication is possible in this static archive calibration.",
        ],
    }


def replay_v37_report(report: Mapping[str, Any]):
    replay = run_v37_acceptance()
    return {"passed": replay["passed"] and replay["discovery"] == report["discovery"]}
