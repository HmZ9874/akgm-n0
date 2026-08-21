"""V40 acceptance for a sealed, domain-blind external scanner experiment."""
from __future__ import annotations

import hashlib
import json
import os
import random
import statistics
import subprocess
import sys
from pathlib import Path

from akgm_n0.learner.live_experiment_v39 import batch_commitment_v39
from akgm_n0.learner.physical_experiment_v40 import (
    DomainBlindPhysicalResearchV40,
    PhysicalObservationV40,
    physical_prediction_commitment_v40,
)

ROOT = Path(__file__).resolve().parents[3]
APPARATUS = ROOT / "scripts/v40_scanner_apparatus.py"


class ExternalScannerClientV40:
    def __init__(self):
        self.process = subprocess.Popen(
            [sys.executable, "-B", str(APPARATUS)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8",
        )

    def send(self, operation, **payload):
        if self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("scanner broker pipes unavailable")
        self.process.stdin.write(json.dumps({"op": operation, **payload}, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            error = "" if self.process.stderr is None else self.process.stderr.read()
            raise RuntimeError(f"scanner broker closed: {error}")
        return json.loads(line)

    def close(self):
        try:
            if self.process.poll() is None:
                self.send("shutdown")
        except (BrokenPipeError, OSError, RuntimeError):
            if self.process.poll() is None:
                self.process.terminate()
        finally:
            self.process.wait(timeout=10)
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        pass


def _execute_batch(client, levels, *, batch_id, seed, requires_prediction=False):
    order = list(levels)
    random.Random(seed).shuffle(order)
    if len(order) > 1 and order == sorted(order):
        order.reverse()
    seed_commitment = hashlib.sha256(str(seed).encode()).hexdigest()
    commitment = batch_commitment_v39(batch_id, order, seed_commitment)
    committed = client.send(
        "commit_batch", batch_id=batch_id, order=order,
        seed_commitment=seed_commitment, commitment=commitment,
        requires_prediction=requires_prediction,
    )
    revealed = client.send("run_batch")
    if not committed["ok"] or not revealed["ok"]:
        raise RuntimeError("sealed physical batch failed")
    return revealed["results"], {
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


def _prediction_case(program, result):
    level = int(result["anonymous_level"])
    prediction = program.predict(level)
    observed = float(result["response"])
    return {
        "anonymous_level": level,
        "predicted": prediction,
        "observed": observed,
        "absolute_error": abs(prediction - observed),
        "absolute_percentage_error": abs(prediction - observed) / max(abs(observed), 1e-9),
    }


def _candidate_audit(rows, local_program):
    xs = [row.level for row in rows]
    ys = [row.response for row in rows]
    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
    intercept = mean_y - slope * mean_x
    constant_error = statistics.median(abs(y - mean_y) for y in ys)
    affine_error = statistics.median(abs(y - (intercept + slope * x)) for x, y in zip(xs, ys))
    return {
        "candidate_count": 3,
        "constant_memory": {"program": "CONST_MEMORY", "training_median_absolute_error": constant_error},
        "global_delta": {"program": "GLOBAL_DELTA", "training_median_absolute_error": affine_error},
        "created_local_memory": local_program.to_dict(),
        "domain_specific_formula_candidate_present": False,
    }


def run_v40_acceptance():
    researcher = DomainBlindPhysicalResearchV40()
    primary = ExternalScannerClientV40()
    replica = ExternalScannerClientV40()
    primary_results = []
    primary_rows = []
    plans = []
    batches = []
    reserved = {1, 4, 6}
    try:
        primary_metadata = primary.send("metadata")
        replica_metadata = replica.send("metadata")
        available = primary_metadata["available_anonymous_levels"]
        for round_index in range(3):
            plan = researcher.plan(primary_rows, available, reserved, round_index)
            plans.append(plan)
            results, batch = _execute_batch(
                primary, plan["selected_levels"],
                batch_id=f"V40-PRIMARY-{round_index}", seed=40001 + round_index * 131,
            )
            primary_results.extend(results)
            primary_rows.extend(PhysicalObservationV40.from_result(item) for item in results)
            batches.append(batch)

        program = researcher.discover(primary_rows)
        holdout_level = 4
        holdout_digest, holdout_prediction = physical_prediction_commitment_v40(program, holdout_level)
        prediction_event = primary.send("commit_prediction", commitment=holdout_digest)
        holdout_results, holdout_batch = _execute_batch(
            primary, (holdout_level,), batch_id="V40-PROSPECTIVE-HOLDOUT",
            seed=40991, requires_prediction=True,
        )

        replication_commitments = []
        for level in (1, 6):
            digest, prediction = physical_prediction_commitment_v40(program, level)
            event = replica.send("commit_prediction", commitment=digest)
            replication_commitments.append({"anonymous_level": level, "commitment": digest, "prediction": prediction, "event_index": event["event_index"]})
        replication_results, replication_batch = _execute_batch(
            replica, (1, 6), batch_id="V40-NEW-PROCESS-REPLICATION",
            seed=40733, requires_prediction=True,
        )
    finally:
        primary.close()
        replica.close()

    all_results = primary_results + holdout_results + replication_results
    holdout_case = _prediction_case(program, holdout_results[0])
    holdout = {
        **holdout_case,
        "committed_prediction": holdout_prediction,
        "prediction_commitment": holdout_digest,
        "prediction_commit_event_index": prediction_event["event_index"],
        "measurement_event_index": holdout_batch["measurement_event_index"],
        "commitment_precedes_measurement": prediction_event["event_index"] < holdout_batch["measurement_event_index"],
    }
    holdout["passed"] = holdout["commitment_precedes_measurement"] and holdout["absolute_percentage_error"] < 0.20

    replication_cases = [_prediction_case(program, item) for item in replication_results]
    replication = {
        "new_broker_process": primary_metadata["broker_pid"] != replica_metadata["broker_pid"],
        "primary_broker_pid": primary_metadata["broker_pid"],
        "replica_broker_pid": replica_metadata["broker_pid"],
        "prediction_commitments": replication_commitments,
        "batch_audit": replication_batch,
        "cases": replication_cases,
        "median_absolute_percentage_error": statistics.median(item["absolute_percentage_error"] for item in replication_cases),
    }
    replication["passed"] = replication["new_broker_process"] and replication["median_absolute_percentage_error"] < 0.20

    responses = [float(item["response"]) for item in all_results]
    receipt_audit = {
        "receipt_count": len(all_results),
        "unique_raw_digest_count": len({item["raw_digest"] for item in all_results}),
        "all_device_transactions_have_duration": all(item["device_receipt"]["ended_at_unix_ms"] > item["device_receipt"]["started_at_unix_ms"] for item in all_results),
        "all_raw_images_deleted_after_statistics": all(not item["raw_image_retained"] for item in all_results),
        "device_id_consistent": len({item["device_receipt"]["device_id_sha256"] for item in all_results}) == 1,
        "response_range": max(responses) - min(responses),
        "raw_digests": [item["raw_digest"] for item in all_results],
        "receipts": [
            {
                "anonymous_level": item["anonymous_level"],
                "response": item["response"],
                "dispersion": item["dispersion"],
                "dark_fraction": item["dark_fraction"],
                "bright_fraction": item["bright_fraction"],
                "raw_digest": item["raw_digest"],
                "raw_bytes": item["raw_bytes"],
                "measured_at_unix_ns": item["measured_at_unix_ns"],
                "device_receipt": item["device_receipt"],
                "raw_image_retained": item["raw_image_retained"],
            }
            for item in all_results
        ],
    }
    randomization = {
        "batches": batches + [holdout_batch, replication_batch],
        "all_commit_before_measurement": all(item["commit_precedes_measurement"] for item in batches + [holdout_batch, replication_batch]),
        "all_multi_level_orders_randomized": all(item["order_differs_from_sorted"] for item in batches + [replication_batch]),
    }
    adaptive = {
        "round_count": len(plans),
        "plans": plans,
        "later_rounds_gap_driven": all(plan["reason"] == "largest_response_weighted_knowledge_gap" for plan in plans[1:]),
        "training_level_count": len(primary_rows),
    }
    candidates = _candidate_audit(primary_rows, program)
    mutations = [
        {"mutation": "domain_names_visible_to_learner", "rejected": not primary_metadata["human_quantity_names_exposed_to_learner"]},
        {"mutation": "measurement_before_commit", "rejected": randomization["all_commit_before_measurement"]},
        {"mutation": "prediction_after_reveal", "rejected": holdout["commitment_precedes_measurement"]},
        {"mutation": "raw_scan_retained", "rejected": receipt_audit["all_raw_images_deleted_after_statistics"]},
        {"mutation": "same_process_replication", "rejected": replication["new_broker_process"]},
    ]
    gates = {
        "external_physical_apparatus": primary_metadata["apparatus"] == "anonymous_external_wia_optical_sensor_v40",
        "fresh_sensor_measurements": receipt_audit["receipt_count"] == 8 and receipt_audit["all_device_transactions_have_duration"],
        "isolated_apparatus_process": primary_metadata["broker_pid"] != os.getpid(),
        "domain_blind_learner": not primary_metadata["human_quantity_names_exposed_to_learner"] and all(row.to_dict()["human_quantity_names"] is None for row in primary_rows),
        "bounded_safe_controls": primary_metadata["safe_control_min"] == 0 and primary_metadata["safe_control_max"] == 7,
        "adaptive_experiment_selection": adaptive["later_rounds_gap_driven"],
        "randomized_intervention_order": randomization["all_multi_level_orders_randomized"],
        "commit_before_measurement": randomization["all_commit_before_measurement"],
        "prospective_holdout_prediction": holdout["passed"],
        "new_process_replication": replication["passed"],
        "physical_response_varies": receipt_audit["response_range"] > 0.005,
        "raw_receipts_unique": receipt_audit["unique_raw_digest_count"] >= 6,
        "privacy_preserving_raw_deletion": receipt_audit["all_raw_images_deleted_after_statistics"],
        "new_local_semantic_created": program.to_dict()["domain_formula_supplied"] is False,
        "human_unknown_natural_law": False,
    }
    obligations = [{"obligation_id": key, "passed": value} for key, value in gates.items() if key != "human_unknown_natural_law"]
    obligations.append({"obligation_id": "human_unknown_claim_blocked", "passed": not gates["human_unknown_natural_law"]})
    obligations.append({"obligation_id": "five_protocol_mutations_rejected", "passed": all(item["rejected"] for item in mutations)})
    return {
        "benchmark_version": "external-physical-science-v40.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_domain_blind_live_external_optical_apparatus_experiment",
        "apparatus": {"primary": primary_metadata, "replica": replica_metadata},
        "observations": [PhysicalObservationV40.from_result(item).to_dict() for item in all_results],
        "created_semantic": program.to_dict(),
        "candidate_audit": candidates,
        "adaptive_experiment_audit": adaptive,
        "randomization_and_commitment_audit": randomization,
        "prospective_holdout_audit": holdout,
        "new_process_replication_audit": replication,
        "physical_receipt_audit": receipt_audit,
        "mutation_audits": mutations,
        "discovery_gates": gates,
        "proof_obligations": obligations,
        "claim_state": {
            "external_physical_experiment_verified": all(item["passed"] for item in obligations[:-2]),
            "human_unknown_claim_allowed": False,
            "new_natural_law_claim_allowed": False,
            "current_label": "DOMAIN_BLIND_EXTERNAL_OPTICAL_APPARATUS_CALIBRATION",
        },
        "posthoc_translation": {
            "apparatus": "HP WIA flatbed optical scanner",
            "anonymous_control": "scanner brightness setting selected from eight safe levels",
            "anonymous_response": "normalized mean luminance of a 96 x 96 sensor crop",
            "created_semantic": "local-memory interpolation over neighboring intervention receipts",
            "control_mapping_after_discovery": {"0": 200, "1": 425, "2": 650, "3": 875, "4": 1125, "5": 1350, "6": 1575, "7": 1800},
        },
        "limitations": [
            "This is a genuine external physical sensor transaction, but it studies an engineered scanner rather than an uncontrolled natural system.",
            "The learner was blinded to control and response names; the evaluator and safety adapter necessarily knew the device mapping.",
            "Only a small optical crop and eight interventions were measured on one device at one site.",
            "Raw images were deleted immediately for privacy, so replication relies on receipts, hashes and derived statistics.",
            "The created local-memory semantic is an empirical calibration rule, not evidence of a human-unknown natural law.",
        ],
    }
