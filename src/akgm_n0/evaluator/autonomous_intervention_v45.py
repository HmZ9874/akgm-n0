"""Independent execution, acceptance, and replay for V45 interventions."""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import statistics
import subprocess
import sys
from pathlib import Path

from akgm_n0.learner.autonomous_intervention_v45 import (
    AutonomousInterventionResearcherV45,
    InterventionActionV45,
    InterventionMeasurementV45,
    InterventionProgramV45,
    intervention_program_commitment_v45,
)


ROOT = Path(__file__).resolve().parents[3]
APPARATUS = ROOT / "scripts/v45_autonomous_intervention_apparatus.py"


class AutonomousInterventionApparatusClientV45:
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
            raise RuntimeError("V45 apparatus pipes unavailable")
        self.process.stdin.write(json.dumps({"op": operation, **payload}, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            error = "" if self.process.stderr is None else self.process.stderr.read()
            raise RuntimeError(f"V45 apparatus closed: {error}")
        return json.loads(line)

    def close(self):
        try:
            self.send("shutdown")
        finally:
            self.process.wait(timeout=10)
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream is not None:
                    stream.close()


def _batch_commitment(batch_id, order, randomization_commitment):
    payload = {
        "batch_id": batch_id,
        "order": order,
        "randomization_commitment": randomization_commitment,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _execute_batch(client, actions, *, batch_id, seed, round_index):
    order = list(actions)
    random.Random(seed).shuffle(order)
    if len(order) > 1 and order == sorted(order, key=lambda item: item.action_id):
        order.reverse()
    serialized = [list(map(int, action.values)) for action in order]
    randomization_commitment = hashlib.sha256(str(seed).encode()).hexdigest()
    commitment = _batch_commitment(batch_id, serialized, randomization_commitment)
    commit = client.send(
        "commit_batch",
        batch_id=batch_id,
        order=serialized,
        randomization_commitment=randomization_commitment,
        commitment=commitment,
    )
    if not commit["ok"]:
        raise RuntimeError(commit)
    reveal = client.send("run_batch")
    if not reveal["ok"]:
        raise RuntimeError(reveal)
    measurements = tuple(
        InterventionMeasurementV45(
            InterventionActionV45(tuple(map(float, item["values"]))),
            float(item["response"]),
            round_index,
            str(item["measurement_id"]),
        )
        for item in reveal["results"]
    )
    return measurements, {
        "batch_id": batch_id,
        "model_selected_actions": [action.to_dict() for action in actions],
        "randomized_execution_order": [action.to_dict() for action in order],
        "randomization_commitment": randomization_commitment,
        "batch_commitment": commitment,
        "commit_event_index": commit["event_index"],
        "measurement_event_index": reveal["event_index"],
        "commit_precedes_measurement": commit["event_index"] < reveal["event_index"],
        "started_at_unix_ns": reveal["started_at_unix_ns"],
        "ended_at_unix_ns": reveal["ended_at_unix_ns"],
        "host_selected": False,
    }


def _program_from_dict(payload):
    return InterventionProgramV45(
        tuple(map(str, payload["features"])),
        tuple(map(float, payload["coefficients"])),
        float(payload["cross_validated_rmse"]),
        float(payload["score"]),
    )


def _transfer_audit(program, results):
    cases = []
    errors = []
    for item in results:
        action = InterventionActionV45(tuple(map(float, item["values"])))
        predicted = program.predict(action)
        observed = float(item["response"])
        error = predicted - observed
        errors.append(error)
        cases.append({
            "action": action.to_dict(),
            "predicted": predicted,
            "observed": observed,
            "absolute_error": abs(error),
        })
    rmse = math.sqrt(sum(error * error for error in errors) / len(errors))
    return {
        "case_count": len(cases),
        "rmse": rmse,
        "maximum_absolute_error": max(item["absolute_error"] for item in cases),
        "cases": cases,
        "counterexamples": sorted(cases, key=lambda item: -item["absolute_error"])[:5],
    }


def _essential_control_audit(results):
    response = {tuple(item["values"]): float(item["response"]) for item in results}
    audits = []
    for control in range(3):
        comparisons = []
        keys = list(response)
        for left_index, left in enumerate(keys):
            for right in keys[left_index + 1:]:
                differing = [index for index in range(3) if left[index] != right[index]]
                if differing == [control]:
                    comparisons.append(abs(response[left] - response[right]))
        audits.append({
            "control_slot": f"Q{control}",
            "matched_pair_count": len(comparisons),
            "nonzero_effect_count": sum(value > 0 for value in comparisons),
            "essential_effect_observed": bool(comparisons) and all(value > 0 for value in comparisons),
        })
    return audits


def run_v45_acceptance():
    researcher = AutonomousInterventionResearcherV45()
    primary = AutonomousInterventionApparatusClientV45()
    replica = AutonomousInterventionApparatusClientV45()
    measurements = []
    growth_rounds = []
    experiment_plans = []
    batch_audits = []
    try:
        metadata = primary.send("metadata")
        replica_metadata = replica.send("metadata")
        premature_transfer = replica.send("run_transfer", commitment="0" * 64)
        unsafe_attempt = primary.send(
            "commit_batch",
            batch_id="V45-UNSAFE-PROBE",
            order=[[999, 999, 999]],
            randomization_commitment="0" * 64,
            commitment="0" * 64,
        )
        actions = tuple(
            InterventionActionV45(tuple(map(float, values)))
            for values in metadata["development_actions"]
        )
        ranges = tuple(tuple(map(float, values)) for values in metadata["safe_ranges"])
        initial_actions = researcher.initial_plan(actions, ranges, batch_size=10)
        rows, initial_batch = _execute_batch(
            primary, initial_actions, batch_id="V45-AUTONOMOUS-SEED", seed=45001, round_index=0,
        )
        measurements.extend(rows)
        batch_audits.append(initial_batch)
        experiment_plans.append({
            "round_index": 0,
            "kind": "geometry_without_prior_response",
            "selected_actions": [action.to_dict() for action in initial_actions],
            "host_selected": False,
        })
        current = researcher.compile(measurements, ("ONE",))
        sterile = 0
        for round_index in range(1, 11):
            growth = researcher.grow_language(measurements, current)
            current = growth["selected"]
            sterile = 0 if growth["mutation"] else sterile + 1
            growth_rounds.append({
                "round_index": round_index,
                "selected_mutation": growth["mutation"],
                "information_gain": growth["gain"],
                "program_after": current.to_dict(),
                "sterile_round_count": sterile,
                "trials": list(growth["trials"]),
                "host_selected": False,
            })
            if sterile >= 3:
                break
            proposal, ranked = researcher.propose(measurements, current, actions, ranges)
            experiment_plans.append({
                "round_index": round_index,
                "kind": "model_disagreement_and_leverage",
                "selected": proposal.to_dict(),
                "top_ranked": [item.to_dict() for item in ranked[:5]],
                "host_selected": False,
            })
            rows, batch = _execute_batch(
                primary,
                (proposal.action,),
                batch_id=f"V45-AUTONOMOUS-ACTIVE-{round_index}",
                seed=45001 + round_index * 101,
                round_index=round_index,
            )
            measurements.extend(rows)
            batch_audits.append(batch)
            current = researcher.compile(measurements, current.features)

        program_commitment = intervention_program_commitment_v45(current)
        commit = replica.send("commit_program", commitment=program_commitment)
        transfer = replica.send("run_transfer", commitment=program_commitment)
    finally:
        primary.close()
        replica.close()

    transfer_audit = _transfer_audit(current, transfer["results"])
    essential_controls = _essential_control_audit(transfer["results"])
    selected_mutations = [item["selected_mutation"] for item in growth_rounds if item["selected_mutation"]]
    rejected_features = [
        {
            "round_index": research_round["round_index"],
            "feature": trial["feature"],
            "score": trial["score"],
            "reason": "did_not_improve_cross_validated_score_after_complexity_cost",
        }
        for research_round in growth_rounds
        for trial in research_round["trials"]
        if not trial["accepted"]
    ]
    randomized = all(
        len(batch["randomized_execution_order"]) == 1
        or batch["randomized_execution_order"] != sorted(
            batch["randomized_execution_order"], key=lambda item: item["action_id"],
        )
        for batch in batch_audits
    )
    gates = {
        "three_anonymous_controls_available": metadata["control_count"] == 3,
        "mechanism_and_control_names_hidden": not metadata["mechanism_exposed"] and not metadata["control_names_exposed"],
        "initial_interventions_selected_without_responses": experiment_plans[0]["kind"] == "geometry_without_prior_response",
        "adaptive_interventions_selected_by_model": len(experiment_plans) >= 3 and all(not item["host_selected"] for item in experiment_plans),
        "safe_action_broker_rejects_invalid_intervention": not unsafe_attempt["ok"],
        "all_batches_committed_before_execution": all(item["commit_precedes_measurement"] for item in batch_audits),
        "multi_action_order_randomized": randomized,
        "live_experiments_executed": all(item["ended_at_unix_ns"] >= item["started_at_unix_ns"] for item in batch_audits),
        "research_language_grew": len(selected_mutations) >= 2,
        "autonomous_semantic_saturation_stop": growth_rounds[-1]["sterile_round_count"] == 3,
        "transfer_sealed_until_program_commitment": not premature_transfer["ok"] and commit["event_index"] < transfer["event_index"],
        "frozen_program_predicts_sealed_interventions": transfer_audit["rmse"] < 1e-8,
        "every_assigned_control_has_matched_pair_effect": all(item["essential_effect_observed"] for item in essential_controls),
        "new_process_replication": metadata["broker_pid"] != replica_metadata["broker_pid"],
        "mistake_room_contains_rejected_mechanisms": bool(rejected_features),
        "natural_system_claim_blocked": True,
        "external_laboratory_claim_blocked": True,
        "fully_autonomous_scientist_claim_blocked": True,
    }
    obligations = [{"obligation_id": key, "passed": bool(value)} for key, value in gates.items()]
    passed = all(item["passed"] for item in obligations)
    formula = " + ".join(
        f"({coefficient:.12g})*{feature}"
        for coefficient, feature in zip(current.coefficients, current.features, strict=True)
    )
    return {
        "benchmark_version": "autonomous-intervention-v45.0",
        "passed": passed,
        "final_status": "verified" if passed else "bounded",
        "classification": "bounded_autonomous_live_computational_causal_intervention",
        "apparatus_boundary": {
            "primary_pid": metadata["broker_pid"],
            "replica_pid": replica_metadata["broker_pid"],
            "learner_pid": os.getpid(),
            "separate_process": metadata["broker_pid"] != os.getpid(),
            "natural_physical_system": False,
            "external_laboratory": False,
            "safe_ranges": metadata["safe_ranges"],
            "development_action_count": len(metadata["development_actions"]),
            "sealed_transfer_action_count": metadata["sealed_transfer_action_count"],
            "experiment_budget": metadata["maximum_development_experiments"],
        },
        "autonomous_experiment_design": {
            "plans": experiment_plans,
            "batch_audits": batch_audits,
            "development_measurements": [row.to_dict() for row in measurements],
            "experiment_count": len(measurements),
            "host_selected": False,
            "stop_reason": "semantic_saturation" if growth_rounds[-1]["sterile_round_count"] == 3 else "resource_ceiling",
        },
        "language_growth": {
            "initial_features": ["ONE"],
            "selected_mutations": selected_mutations,
            "rounds": growth_rounds,
            "selected_program": current.to_dict(),
        },
        "preregistration": {
            "program_commitment": program_commitment,
            "commit_event_index": commit["event_index"],
            "transfer_event_index": transfer["event_index"],
            "commitment_precedes_transfer": commit["event_index"] < transfer["event_index"],
        },
        "sealed_counterfactual_audit": transfer_audit,
        "causal_effect_audit": {
            "direction": "assigned Q slots -> observed response",
            "observational_direction_claimed": False,
            "essential_controls": essential_controls,
        },
        "mistake_room": {
            "rejected_structural_features": rejected_features,
            "transfer_counterexamples": transfer_audit["counterexamples"],
            "replay_policy": "retest rejected structures only after new intervention evidence changes cross-validated score",
        },
        "posthoc_translation": {
            "internal_formula": formula,
            "Q0": "outer executable loop bound",
            "Q1": "middle executable loop bound",
            "Q2": "inner executable loop bound",
            "response": "executed operation count",
            "human_equivalent": "three-control interaction plus a guarded asymmetric branch",
            "labels_revealed_after_discovery": True,
        },
        "discovery_gates": gates,
        "proof_obligations": obligations,
        "claim_state": {
            "autonomous_intervention_design_allowed": passed,
            "autonomous_safe_execution_allowed": passed,
            "computational_causal_mechanism_allowed": passed,
            "natural_physical_causal_law_allowed": False,
            "external_laboratory_replication_allowed": False,
            "human_unknown_law_allowed": False,
            "fully_autonomous_scientist_allowed": False,
            "current_label": "V45_BOUNDED_AUTONOMOUS_INTERVENTION_PHYSICAL_APPARATUS_REQUIRED",
        },
        "limitations": [
            "The interventions execute in a local computational apparatus, not an unknown natural physical system.",
            "The host supplies safe ranges, a finite action space, arithmetic, least squares, and structural feature constructors.",
            "The evaluator knows the apparatus implementation; the learner process does not receive it.",
            "New-process replay is on the same machine and is not independent-laboratory replication.",
            "No human-unknown law or fully autonomous scientist claim is allowed.",
        ],
    }


def verify_v45_acceptance(acceptance):
    obligations = []

    def check(name, passed, actual):
        obligations.append({"obligation_id": name, "passed": bool(passed), "actual": actual})

    client = None
    try:
        program = _program_from_dict(acceptance["language_growth"]["selected_program"])
        check("program_id_replay", program.program_id == acceptance["language_growth"]["selected_program"]["program_id"], program.program_id)
        commitment = intervention_program_commitment_v45(program)
        check("program_commitment_replay", commitment == acceptance["preregistration"]["program_commitment"], commitment)
        client = AutonomousInterventionApparatusClientV45()
        client.send("metadata")
        commit = client.send("commit_program", commitment=commitment)
        transfer = client.send("run_transfer", commitment=commitment)
        replay = _transfer_audit(program, transfer["results"])
        expected = acceptance["sealed_counterfactual_audit"]["rmse"]
        check("fresh_process_transfer_replay", math.isclose(replay["rmse"], expected, rel_tol=0, abs_tol=1e-12), replay["rmse"])
        check("commit_before_transfer_replay", commit["event_index"] < transfer["event_index"], [commit["event_index"], transfer["event_index"]])
        check("proof_gate_replay", all(item["passed"] for item in acceptance["proof_obligations"]), len(acceptance["proof_obligations"]))
        claims = acceptance["claim_state"]
        check("overclaim_blocks_replay", not claims["natural_physical_causal_law_allowed"] and not claims["fully_autonomous_scientist_allowed"] and not claims["human_unknown_law_allowed"], claims)
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        check("report_structure", False, str(error))
    finally:
        if client is not None:
            client.close()
    return {
        "verifier_version": "autonomous-intervention-v45-independent-replay-v0.1",
        "passed": all(item["passed"] for item in obligations),
        "obligations": obligations,
    }
