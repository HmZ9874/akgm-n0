"""V38 acceptance for controlled-intervention causal calibration."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from akgm_n0.learner.interventional_calibration_v38 import (
    InterventionRowV38,
    InterventionalMechanismResearchV38,
    prediction_commitment_v38,
)

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / "data/nist_pontius_v38_snapshot.csv"
PROVENANCE = ROOT / "data/nist_pontius_v38_provenance.json"
BROKER = ROOT / "scripts/v38_intervention_broker.py"


class SubprocessInterventionBrokerV38:
    def __init__(self):
        self.process = subprocess.Popen(
            [sys.executable, "-B", str(BROKER), str(SNAPSHOT)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8",
        )

    def send(self, operation, **payload):
        if self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("broker pipes unavailable")
        self.process.stdin.write(json.dumps({"op": operation, **payload}, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            error = "" if self.process.stderr is None else self.process.stderr.read()
            raise RuntimeError(f"intervention broker closed: {error}")
        return json.loads(line)

    def close(self):
        try:
            self.send("shutdown")
        finally:
            self.process.wait(timeout=10)
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream is not None:
                    stream.close()


def _provenance_audit(metadata):
    source = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    digest = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()
    return {
        "passed": digest == source["snapshot_sha256"] and metadata["rows"] == source["row_count"],
        "provider": source["provider"],
        "dataset": source["dataset"],
        "source_url": source["source_url"],
        "reference_dataset_url": source["reference_dataset_url"],
        "doi": source["doi"],
        "snapshot_sha256": digest,
        "row_count": source["row_count"],
        "experimental_design": source["design"],
        "units": source["units"],
        "known_risk": source["known_risk"],
    }


def _future_audit(program, inputs, outputs):
    observed = {row["row_id"]: float(row["target"]) for row in outputs}
    cases = []
    for row in inputs:
        predicted = program.predict(row)
        target = observed[row.row_id]
        cases.append({
            "row_id": row.row_id,
            "normalized_intervention": row.q0,
            "unseen_intervention_level": row.unseen_intervention_level,
            "predicted": predicted,
            "observed": target,
            "absolute_error": abs(predicted - target),
            "absolute_percentage_error": abs(predicted - target) / target,
        })
    unseen = [item for item in cases if item["unseen_intervention_level"]]
    return {
        "passed": statistics.median(item["absolute_percentage_error"] for item in cases) < 0.002,
        "case_count": len(cases),
        "unseen_intervention_count": len(unseen),
        "median_absolute_percentage_error": statistics.median(item["absolute_percentage_error"] for item in cases),
        "unseen_intervention_mape": statistics.median(item["absolute_percentage_error"] for item in unseen),
        "root_mean_square_error": math.sqrt(sum(item["absolute_error"] ** 2 for item in cases) / len(cases)),
        "cases": cases,
    }


def _repeatability_audit():
    with SNAPSHOT.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_level: dict[int, dict[int, float]] = {}
    for row in rows:
        by_level.setdefault(int(row["within_run_index"]), {})[int(row["run_index"])] = float(row["deflection"])
    differences = [pair[2] - pair[1] for pair in by_level.values()]
    mean = statistics.mean(differences)
    return {
        "paired_levels": len(differences),
        "mean_signed_batch_difference": mean,
        "mean_absolute_batch_difference": statistics.mean(abs(value) for value in differences),
        "repeatability_standard_deviation": statistics.stdev(differences),
        "systematic_order_in_both_batches": True,
        "randomized_order": False,
        "drift_separable_from_response": False,
    }


def _direction_audit(discovery):
    reverse = min(discovery.reverse_candidates, key=lambda item: item.bic)
    no_link = next(item for item in discovery.forward_candidates if item.degree == 0)
    return {
        "selected_graph": "Q0_TO_Q1",
        "controlled_slot": discovery.controlled_slot,
        "response_slot": discovery.response_slot,
        "forward_best": discovery.selected.to_dict(),
        "reverse_best": reverse.to_dict(),
        "no_link": no_link.to_dict(),
        "observational_fit_alone_determines_direction": False,
        "intervention_role_selects_direction": discovery.controlled_slot == "Q0" and discovery.response_slot == "Q1",
        "reverse_graph_rejected_reason": "Q1 was not assigned by the experiment; it was observed after do(Q0)",
    }


def _shape_certificate(program):
    c0, c1, c2 = program.coefficients
    derivative_left = c1 + 2 * c2 * 0.05
    derivative_right = c1 + 2 * c2 * 1.0
    return {
        "proof_id": "V38-PROOF-MONOTONE-INTERVENTION-RESPONSE",
        "domain": "0.05 <= Q0 <= 1.0",
        "derivative": f"{c1:.12g}+2*({c2:.12g})*Q0",
        "endpoint_derivatives": [derivative_left, derivative_right],
        "passed": min(derivative_left, derivative_right) > 0,
    }


def run_v38_acceptance():
    client = SubprocessInterventionBrokerV38()
    try:
        metadata = client.send("metadata")
        premature = client.send("future_outputs")
        training_payload = client.send("training")
        future_inputs_payload = client.send("future_inputs")
        training = tuple(InterventionRowV38.from_dict(row) for row in training_payload["rows"])
        future_inputs = tuple(InterventionRowV38.from_dict(row) for row in future_inputs_payload["rows"])
        researcher = InterventionalMechanismResearchV38()
        discovery = researcher.discover(training, controlled_slot=metadata["controlled_slot"], response_slot=metadata["response_slot"])
        commitment, predictions = prediction_commitment_v38(discovery.selected, future_inputs)
        commit = client.send("commit", commitment=commitment)
        reveal = client.send("future_outputs")
    finally:
        client.close()

    provenance = _provenance_audit(metadata)
    future = _future_audit(discovery.selected, future_inputs, reveal["rows"])
    repeatability = _repeatability_audit()
    direction = _direction_audit(discovery)
    shape = _shape_certificate(discovery.selected)
    known = {
        "catalog_id": "NIST-PONTIUS-QUADRATIC-CALIBRATION",
        "matched": discovery.selected.degree == 2,
        "human_novelty": False,
    }
    mutations = [
        {"mutation": "no_link", "rejected": direction["no_link"]["bic"] > direction["forward_best"]["bic"], "evidence": direction["no_link"]},
        {"mutation": "linear_only", "rejected": next(item for item in discovery.forward_candidates if item.degree == 1).bic > discovery.selected.bic, "evidence": next(item for item in discovery.forward_candidates if item.degree == 1).to_dict()},
        {"mutation": "reverse_arrow", "rejected": direction["intervention_role_selects_direction"], "evidence": direction["reverse_graph_rejected_reason"]},
        {"mutation": "decreasing_response", "rejected": shape["passed"], "evidence": shape},
    ]
    gates = {
        "real_controlled_experiment": provenance["passed"] and metadata["controlled_slot"] == "Q0",
        "separate_data_process": metadata["broker_pid"] != os.getpid(),
        "commit_before_second_batch": not premature["ok"] and commit["event_index"] < reveal["event_index"],
        "causal_direction_from_intervention": direction["intervention_role_selects_direction"],
        "mechanism_complexity_selected": discovery.selected.degree == 2,
        "unseen_intervention_prediction": future["passed"] and future["unseen_intervention_count"] >= 10,
        "repeatability_noise_measured": repeatability["paired_levels"] == 20,
        "monotone_shape_certificate": shape["passed"],
        "alternative_graphs_falsified": all(item["rejected"] for item in mutations),
        "known_calibration_match": known["matched"],
        "randomized_intervention_order": metadata["randomized_order"],
        "drift_separated": repeatability["drift_separable_from_response"],
        "live_new_intervention": False,
        "human_novelty": False,
    }
    obligations = (
        {"obligation_id": "nist_intervention_provenance", "passed": provenance["passed"]},
        {"obligation_id": "data_process_isolated", "passed": gates["separate_data_process"]},
        {"obligation_id": "future_batch_locked_until_commit", "passed": gates["commit_before_second_batch"]},
        {"obligation_id": "three_causal_graphs_compete", "passed": len(discovery.to_dict()["graph_candidates"]) == 3},
        {"obligation_id": "intervention_role_selects_direction", "passed": gates["causal_direction_from_intervention"]},
        {"obligation_id": "quadratic_complexity_selected_by_bic", "passed": gates["mechanism_complexity_selected"]},
        {"obligation_id": "quadratic_beats_runner_up", "passed": discovery.to_dict()["bic_margin"] > 0},
        {"obligation_id": "second_batch_prediction", "passed": future["passed"]},
        {"obligation_id": "unseen_intervention_levels_predicted", "passed": future["unseen_intervention_count"] >= 10},
        {"obligation_id": "repeatability_noise_quantified", "passed": gates["repeatability_noise_measured"]},
        {"obligation_id": "monotone_response_proved", "passed": shape["passed"]},
        {"obligation_id": "alternative_mechanisms_rejected", "passed": gates["alternative_graphs_falsified"]},
        {"obligation_id": "known_nist_model_not_called_novel", "passed": known["matched"] and not known["human_novelty"]},
        {"obligation_id": "nonrandomized_drift_risk_blocks_clean_effect_claim", "passed": not gates["randomized_intervention_order"] and not gates["drift_separated"]},
        {"obligation_id": "live_discovery_claim_remains_blocked", "passed": not gates["live_new_intervention"] and not gates["human_novelty"]},
    )
    return {
        "benchmark_version": "interventional-science-v38.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_real_controlled_intervention_direction_and_known_quadratic_calibration_with_drift_gate",
        "dataset": {"metadata": metadata, "provenance_audit": provenance},
        "discovery": discovery.to_dict(),
        "direction_audit": direction,
        "preregistration": {"commitment": commitment, "prediction_count": len(predictions), "commitment_precedes_reveal": commit["event_index"] < reveal["event_index"]},
        "future_batch_audit": future,
        "repeatability_audit": repeatability,
        "shape_certificate": shape,
        "mutation_audits": mutations,
        "known_law_audit": known,
        "discovery_gates": gates,
        "claim_state": {
            "interventional_pipeline_verified": all(value for key, value in gates.items() if key not in ("randomized_intervention_order", "drift_separated", "live_new_intervention", "human_novelty")),
            "clean_causal_effect_claim_allowed": False,
            "human_unknown_claim_allowed": False,
            "current_label": "CONTROLLED_INTERVENTION_KNOWN_CALIBRATION_REDISCOVERY",
        },
        "proof_obligations": list(obligations),
        "posthoc_translation": {
            "Q0": "applied load divided by 3,000,000",
            "Q1": "load-cell deflection",
            "mechanism": "quadratic calibration response",
        },
        "limitations": [
            "The data are a historical NIST calibration experiment and the quadratic model is human-known.",
            "The intervention order increased systematically in both batches, so temporal drift is not separable from load response.",
            "The second batch is sealed computationally now but was not prospectively collected for this project.",
            "Causal direction uses supplied anonymous intervention-role metadata; observational fit alone does not orient the edge.",
            "No live apparatus, randomized intervention schedule, adaptive next experiment, or human-novel mechanism is present.",
        ],
    }


def replay_v38_report(report: Mapping[str, Any]):
    replay = run_v38_acceptance()
    return {"passed": replay["passed"] and replay["discovery"] == report["discovery"]}
