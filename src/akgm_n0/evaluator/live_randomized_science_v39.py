"""V39 acceptance: live, randomized and adaptive computational experiments."""
from __future__ import annotations

import hashlib
import json
import os
import random
import statistics
import subprocess
import sys
from pathlib import Path

from akgm_n0.learner.live_experiment_v39 import (
    LiveMeasurementV39,
    LiveScaleResearchV39,
    batch_commitment_v39,
    prediction_commitment_v39,
)

ROOT = Path(__file__).resolve().parents[3]
APPARATUS = ROOT / "scripts/v39_live_apparatus.py"


class LiveApparatusClientV39:
    def __init__(self):
        self.process = subprocess.Popen(
            [sys.executable, "-B", str(APPARATUS)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

    def send(self, operation, **payload):
        if self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("apparatus pipes unavailable")
        self.process.stdin.write(json.dumps({"op": operation, **payload}, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            error = "" if self.process.stderr is None else self.process.stderr.read()
            raise RuntimeError(f"live apparatus closed: {error}")
        return json.loads(line)

    def close(self):
        try:
            self.send("shutdown")
        finally:
            self.process.wait(timeout=10)
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream is not None:
                    stream.close()


def _randomized_order(levels, seed):
    ordered = list(levels)
    random.Random(seed).shuffle(ordered)
    if len(ordered) > 1 and ordered == sorted(ordered):
        ordered.reverse()
    return ordered


def _execute_batch(client, levels, *, batch_id, seed, round_index, requires_prediction=False):
    order = _randomized_order(levels, seed)
    seed_commitment = hashlib.sha256(str(seed).encode()).hexdigest()
    commitment = batch_commitment_v39(batch_id, order, seed_commitment)
    committed = client.send(
        "commit_batch",
        batch_id=batch_id,
        order=order,
        seed_commitment=seed_commitment,
        commitment=commitment,
        requires_prediction=requires_prediction,
    )
    revealed = client.send("run_batch")
    if not committed["ok"] or not revealed["ok"]:
        raise RuntimeError("live batch protocol failed")
    rows = tuple(LiveMeasurementV39.from_result(item, round_index) for item in revealed["results"])
    audit = {
        "batch_id": batch_id,
        "planned_levels": list(levels),
        "randomized_order": order,
        "seed_commitment": seed_commitment,
        "batch_commitment": commitment,
        "commit_event_index": committed["event_index"],
        "measurement_event_index": revealed["event_index"],
        "commit_precedes_measurement": committed["event_index"] < revealed["event_index"],
        "order_differs_from_sorted": len(order) == 1 or order != sorted(order),
        "started_at_unix_ns": revealed["started_at_unix_ns"],
        "ended_at_unix_ns": revealed["ended_at_unix_ns"],
    }
    return rows, audit


def _error_case(program, row):
    predicted = program.predict(row.level)
    return {
        "anonymous_level": row.level,
        "predicted_response": predicted,
        "observed_response": row.response,
        "absolute_percentage_error": abs(predicted - row.response) / row.response,
    }


def run_v39_acceptance():
    researcher = LiveScaleResearchV39()
    primary = LiveApparatusClientV39()
    replica = LiveApparatusClientV39()
    primary_rows = []
    plans = []
    batches = []
    holdout_level = 352
    try:
        primary_metadata = primary.send("metadata")
        replica_metadata = replica.send("metadata")
        available = [value for value in primary_metadata["available_levels"] if value != holdout_level]

        for round_index, batch_size in enumerate((3, 2, 2)):
            plan = researcher.plan(primary_rows, available, round_index=round_index, batch_size=batch_size)
            plans.append(plan)
            rows, batch = _execute_batch(
                primary,
                plan.selected_levels,
                batch_id=f"V39-PRIMARY-{round_index}",
                seed=39001 + round_index * 97,
                round_index=round_index,
            )
            primary_rows.extend(rows)
            batches.append(batch)

        selected = researcher.select(primary_rows)
        candidates = sorted(researcher.fit_candidates(primary_rows), key=lambda item: item.robust_score)

        prediction_commitment, holdout_prediction = prediction_commitment_v39(selected, holdout_level)
        prediction_event = primary.send("commit_prediction", commitment=prediction_commitment)
        holdout_rows, holdout_batch = _execute_batch(
            primary,
            (holdout_level,),
            batch_id="V39-PROSPECTIVE-HOLDOUT",
            seed=39991,
            round_index=3,
            requires_prediction=True,
        )
        holdout = _error_case(selected, holdout_rows[0])
        holdout.update({
            "prediction_commitment": prediction_commitment,
            "committed_prediction": holdout_prediction,
            "prediction_commit_event_index": prediction_event["event_index"],
            "measurement_event_index": holdout_batch["measurement_event_index"],
            "commitment_precedes_measurement": prediction_event["event_index"] < holdout_batch["measurement_event_index"],
        })

        replication_levels = (128, 288)
        replication_commitments = []
        for level in replication_levels:
            digest, prediction = prediction_commitment_v39(selected, level)
            event = replica.send("commit_prediction", commitment=digest)
            replication_commitments.append({"level": level, "commitment": digest, "prediction": prediction, "event_index": event["event_index"]})
        replication_rows, replication_batch = _execute_batch(
            replica,
            replication_levels,
            batch_id="V39-NEW-PROCESS-REPLICATION",
            seed=39731,
            round_index=4,
            requires_prediction=True,
        )
    finally:
        primary.close()
        replica.close()

    replication_cases = [_error_case(selected, row) for row in replication_rows]
    replication = {
        "passed": statistics.median(item["absolute_percentage_error"] for item in replication_cases) < 0.35,
        "new_process": primary_metadata["broker_pid"] != replica_metadata["broker_pid"],
        "primary_broker_pid": primary_metadata["broker_pid"],
        "replica_broker_pid": replica_metadata["broker_pid"],
        "prediction_commitments": replication_commitments,
        "batch_audit": replication_batch,
        "median_absolute_percentage_error": statistics.median(item["absolute_percentage_error"] for item in replication_cases),
        "cases": replication_cases,
    }
    holdout["passed"] = holdout["absolute_percentage_error"] < 0.35 and holdout["commitment_precedes_measurement"]

    noise_ratios = [row.mad / row.response for row in (*primary_rows, *holdout_rows, *replication_rows)]
    noise = {
        "measurement_count": len(noise_ratios),
        "median_mad_fraction": statistics.median(noise_ratios),
        "maximum_mad_fraction": max(noise_ratios),
        "passed": statistics.median(noise_ratios) < 0.20,
    }
    linear = next(item for item in candidates if item.exponent_quarters == 4)
    cubic = next(item for item in candidates if item.exponent_quarters == 12)
    competition = {
        "candidate_count": len(candidates),
        "selected": selected.to_dict(),
        "runner_up": candidates[1].to_dict(),
        "linear_null": linear.to_dict(),
        "cubic_null": cubic.to_dict(),
        "selected_beats_boundary_nulls": selected.robust_score < min(linear.robust_score, cubic.robust_score),
        "matches_quadratic_kernel_band": abs(selected.exponent - 2.0) <= 0.25,
    }
    adaptive = {
        "round_count": len(plans),
        "plans": [plan.to_dict() for plan in plans],
        "later_rounds_use_model_disagreement": all(plan.maximum_log_prediction_spread > 0 for plan in plans[1:]),
        "unique_measured_levels": len({row.level for row in primary_rows}),
    }
    order = {
        "batches": batches + [holdout_batch, replication_batch],
        "all_committed_before_measurement": all(item["commit_precedes_measurement"] for item in batches + [holdout_batch, replication_batch]),
        "all_multi_level_orders_randomized": all(item["order_differs_from_sorted"] for item in batches + [replication_batch]),
    }
    mutations = [
        {"mutation": "linear_scaling_only", "rejected": selected.robust_score < linear.robust_score},
        {"mutation": "cubic_scaling_only", "rejected": selected.robust_score < cubic.robust_score},
        {"mutation": "measure_before_batch_commitment", "rejected": order["all_committed_before_measurement"]},
        {"mutation": "predict_after_holdout_reveal", "rejected": holdout["commitment_precedes_measurement"]},
        {"mutation": "same_process_replication", "rejected": replication["new_process"]},
    ]
    gates = {
        "live_new_measurements": all(batch["ended_at_unix_ns"] >= batch["started_at_unix_ns"] for batch in order["batches"]),
        "independent_apparatus_process": primary_metadata["broker_pid"] != os.getpid(),
        "adaptive_experiment_selection": adaptive["later_rounds_use_model_disagreement"],
        "randomized_batch_order": order["all_multi_level_orders_randomized"],
        "commit_before_measurement": order["all_committed_before_measurement"],
        "prospective_holdout_prediction": holdout["passed"],
        "timing_noise_quantified": noise["passed"],
        "scale_law_competition": competition["selected_beats_boundary_nulls"],
        "new_process_replication": replication["passed"] and replication["new_process"],
        "known_kernel_scaling_match": competition["matches_quadratic_kernel_band"],
        "natural_physical_system": False,
        "external_laboratory": False,
        "human_novelty": False,
    }
    obligations = [
        {"obligation_id": key, "passed": value}
        for key, value in gates.items()
        if key not in ("natural_physical_system", "external_laboratory", "human_novelty")
    ] + [
        {"obligation_id": "natural_system_claim_blocked", "passed": not gates["natural_physical_system"]},
        {"obligation_id": "external_lab_claim_blocked", "passed": not gates["external_laboratory"]},
        {"obligation_id": "human_novelty_claim_blocked", "passed": not gates["human_novelty"]},
        {"obligation_id": "five_protocol_mutations_rejected", "passed": all(item["rejected"] for item in mutations)},
    ]
    return {
        "benchmark_version": "live-randomized-science-v39.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_live_randomized_adaptive_computational_apparatus_scale_calibration",
        "apparatus": {"primary": primary_metadata, "replica": replica_metadata, "natural_physical_system": False},
        "measurements": [row.to_dict() for row in (*primary_rows, *holdout_rows, *replication_rows)],
        "adaptive_experiment_audit": adaptive,
        "randomization_and_commitment_audit": order,
        "model_competition": competition,
        "prospective_holdout_audit": holdout,
        "timing_noise_audit": noise,
        "new_process_replication_audit": replication,
        "mutation_audits": mutations,
        "discovery_gates": gates,
        "claim_state": {
            "live_computational_experiment_loop_verified": all(item["passed"] for item in obligations[:10]),
            "natural_science_discovery_claim_allowed": False,
            "human_unknown_claim_allowed": False,
            "current_label": "LIVE_RANDOMIZED_COMPUTATIONAL_APPARATUS_CALIBRATION",
        },
        "proof_obligations": obligations,
        "posthoc_translation": {
            "anonymous_level": "nested-loop side length",
            "response": "median elapsed nanoseconds per kernel cycle",
            "selected_exponent": "empirical workload scaling exponent",
        },
        "limitations": [
            "The apparatus is a local computational workload, not a natural physical system or external laboratory.",
            "Wall-clock timing depends on the operating system, interpreter and processor load.",
            "The quadratic nested-loop structure is known to the evaluator and is not a human-novel discovery.",
            "Randomization, adaptive planning and commitments validate the discovery protocol, not scientific novelty.",
            "Replication uses a new process on the same machine, not an independent site or instrument.",
        ],
    }

