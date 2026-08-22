"""Independent acceptance and replay for V44 autonomous world research."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from akgm_n0.learner.autonomous_scientist_v43 import (
    AnonymousNumericTraceV43,
    AutonomousScientistKernelV43,
    scientific_program_commitment_v43,
)
from akgm_n0.learner.autonomous_world_research_v44 import (
    AnonymousWorldV44,
    AutonomousWorldResearchDirectorV44,
    program_from_report_v44,
    research_agenda_commitment_v44,
)


ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / "data/official_worlds_v44/official_worlds_v44_snapshot.json"
COUNTEREXAMPLE_HISTORY = ROOT / "data/official_worlds_v44/v44_counterexample_history.json"


def _trace(payload):
    return AnonymousNumericTraceV43(
        str(payload["trace_id"]),
        tuple(tuple(map(float, row)) for row in payload["inputs"]),
        tuple(map(float, payload["outputs"])),
    )


def _snapshot_digest(payload):
    body = {name: value for name, value in payload.items() if name != "snapshot_sha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _partition_groups(items):
    return sorted({str(item["trace_id"]).split("-", 1)[0] for item in items})


class OfficialWorldArchiveV44:
    def __init__(self, payload):
        self._payload = payload
        self._event_index = 0
        self._commitment = None
        self._transfer_revealed = False

    def development_registry(self):
        if self._commitment is not None:
            raise RuntimeError("development registry cannot reopen after commitment")
        self._event_index += 1
        worlds = []
        for item in self._payload["worlds"]:
            worlds.append(AnonymousWorldV44(
                item["world_id"],
                dict(item["anonymous_descriptor"]),
                tuple(_trace(trace) for trace in item["partitions"]["training"]),
                tuple(_trace(trace) for trace in item["partitions"]["validation"]),
                len(item["partitions"]["transfer"]),
                len(item["source_receipts"]),
            ))
        return {
            "worlds": tuple(worlds),
            "event_index": self._event_index,
            "domain_labels_exposed": False,
            "institution_names_exposed": False,
            "transfer_outputs_exposed": False,
        }

    def commit(self, world_id, program_commitment, agenda_commitment):
        if self._commitment is not None:
            raise RuntimeError("only one V44 world commitment is allowed")
        if world_id not in {item["world_id"] for item in self._payload["worlds"]}:
            raise ValueError("unknown anonymous world")
        self._commitment = {
            "world_id": str(world_id),
            "program_commitment": str(program_commitment),
            "agenda_commitment": str(agenda_commitment),
        }
        self._event_index += 1
        return {**self._commitment, "event_index": self._event_index}

    def reveal_transfer(self, commitment):
        if self._commitment is None or commitment != self._commitment:
            raise RuntimeError("official transfer measurements are sealed")
        world = next(
            item for item in self._payload["worlds"]
            if item["world_id"] == commitment["world_id"]
        )
        self._event_index += 1
        self._transfer_revealed = True
        return {
            "traces": tuple(_trace(item) for item in world["partitions"]["transfer"]),
            "event_index": self._event_index,
            "domain_labels_exposed_to_program": False,
            "physical_channel_names_exposed_to_program": False,
        }

    def reveal_metadata_after_audit(self, world_id):
        if not self._transfer_revealed or self._commitment["world_id"] != world_id:
            raise RuntimeError("post-hoc metadata is still sealed")
        world = next(item for item in self._payload["worlds"] if item["world_id"] == world_id)
        self._event_index += 1
        return {"metadata": dict(world["sealed_metadata"]), "event_index": self._event_index}


def _formula(program):
    return " + ".join(
        f"({weight:.12g})*{feature}"
        for weight, feature in zip(program.coefficients, program.features, strict=True)
    )


def run_v44_acceptance():
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    counterexample_history = json.loads(COUNTEREXAMPLE_HISTORY.read_text(encoding="utf-8"))
    archive = OfficialWorldArchiveV44(snapshot)
    development = archive.development_registry()
    director = AutonomousWorldResearchDirectorV44()
    agenda = director.choose_next_world(development["worlds"])
    selected = agenda["selected"]
    program_commitment = scientific_program_commitment_v43(selected.program)
    agenda_commitment = research_agenda_commitment_v44(selected)
    committed = archive.commit(selected.world_id, program_commitment, agenda_commitment)
    commitment_payload = {
        "world_id": committed["world_id"],
        "program_commitment": committed["program_commitment"],
        "agenda_commitment": committed["agenda_commitment"],
    }
    transfer = archive.reveal_transfer(commitment_payload)
    transfer_audit = director.kernel.evaluate(selected.program, transfer["traces"])
    transfer_normalized_rmse = transfer_audit["rmse"] / selected.output_scale
    metadata = archive.reveal_metadata_after_audit(selected.world_id)

    world_payload = next(item for item in snapshot["worlds"] if item["world_id"] == selected.world_id)
    training_groups = _partition_groups(world_payload["partitions"]["training"])
    validation_groups = _partition_groups(world_payload["partitions"]["validation"])
    transfer_groups = _partition_groups(world_payload["partitions"]["transfer"])
    group_isolation = not (
        set(training_groups) & set(validation_groups)
        or set(training_groups) & set(transfer_groups)
        or set(validation_groups) & set(transfer_groups)
    )
    ranking = [item.summary() for item in agenda["ranked"]]
    selected_rounds = selected.discovery["rounds"]
    rejected_mutations = []
    for research_round in selected_rounds:
        for trial in research_round.trials:
            if trial.mutation != research_round.selected_mutation:
                rejected_mutations.append({
                    "round_index": research_round.round_index,
                    "mutation": trial.mutation,
                    "validation_rmse": trial.validation_rmse,
                    "reason": "did_not_maximize_information_gain_after_complexity_cost",
                })
    mistake_room = {
        "mandatory_replay_history": counterexample_history["events"],
        "nonselected_worlds": [
            {**item, "reason": "lower_autonomous_research_priority"}
            for item in ranking[1:]
        ],
        "rejected_language_mutations": rejected_mutations,
        "sealed_transfer_counterexamples": transfer_audit["counterexamples"],
        "replay_policy": "reconsider only when new measurements or language resources change the evidence",
    }

    gates = {
        "three_official_worlds_available": snapshot["world_count"] == 3,
        "official_snapshot_digest_valid": _snapshot_digest(snapshot) == snapshot["snapshot_sha256"],
        "world_and_domain_labels_hidden_during_selection": (
            not development["domain_labels_exposed"]
            and not development["institution_names_exposed"]
        ),
        "world_selected_by_research_priority": selected.world_id == ranking[0]["world_id"],
        "host_did_not_select_world": not agenda["host_selected"],
        "positive_development_information_gain": selected.normalized_information_gain > 0.01,
        "program_committed_before_transfer_reveal": committed["event_index"] < transfer["event_index"],
        "metadata_revealed_only_after_transfer_audit": transfer["event_index"] < metadata["event_index"],
        "frozen_program_without_transfer_refit": program_commitment == scientific_program_commitment_v43(selected.program),
        "source_group_partitions_are_disjoint": group_isolation,
        "sealed_transfer_beats_scale_baseline": transfer_normalized_rmse < 1.0,
        "mistake_room_records_failures": bool(mistake_room["mandatory_replay_history"] and mistake_room["nonselected_worlds"] and rejected_mutations),
        "independent_lab_claim_blocked": True,
        "causal_discovery_claim_blocked": True,
        "fully_autonomous_scientist_claim_blocked": True,
    }
    proof_obligations = [
        {"obligation_id": name, "passed": bool(value)} for name, value in gates.items()
    ]
    passed = all(item["passed"] for item in proof_obligations)
    next_queue = [
        {
            "rank": index + 2,
            "world_id": item["world_id"],
            "knowledge_gap": item["final_normalized_error"],
            "expected_information_gain": item["normalized_information_gain"],
            "status": "sealed_and_queued",
        }
        for index, item in enumerate(ranking[1:])
    ]
    return {
        "benchmark_version": "autonomous-world-research-v44.0",
        "passed": passed,
        "final_status": "verified" if passed else "bounded",
        "classification": "bounded_autonomous_external_world_selection",
        "official_registry": {
            "snapshot_version": snapshot["snapshot_version"],
            "snapshot_sha256": snapshot["snapshot_sha256"],
            "snapshot_created_at": snapshot["created_at"],
            "world_count": snapshot["world_count"],
            "anonymous_worlds": [
                {
                    "world_id": world.world_id,
                    "descriptor": world.descriptor,
                    "training_trace_count": len(world.training),
                    "validation_trace_count": len(world.validation),
                    "sealed_transfer_trace_count": world.sealed_transfer_trace_count,
                }
                for world in development["worlds"]
            ],
        },
        "autonomous_agenda": {
            "ranking": ranking,
            "selected_world_id": selected.world_id,
            "selection_rule": "information gain + predictability + structural novelty + verification readiness - program cost",
            "next_research_queue": next_queue,
            "host_selected": False,
        },
        "discovery": {
            "selected_program": selected.program.to_dict(),
            "selected_mutations": ranking[0]["selected_mutations"],
            "initial_normalized_error": selected.initial_normalized_error,
            "validation_normalized_error": selected.final_normalized_error,
            "normalized_information_gain": selected.normalized_information_gain,
            "research_priority": selected.research_priority,
            "rounds": [item.to_dict() for item in selected_rounds],
            "candidate_programs_evaluated": selected.discovery["candidate_programs_evaluated"],
            "stop_reason": selected.discovery["stop_reason"],
        },
        "preregistration": {
            "program_commitment": program_commitment,
            "agenda_commitment": agenda_commitment,
            "development_event_index": development["event_index"],
            "commit_event_index": committed["event_index"],
            "transfer_reveal_event_index": transfer["event_index"],
            "metadata_reveal_event_index": metadata["event_index"],
        },
        "sealed_transfer_audit": {
            **transfer_audit,
            "output_scale_from_development_only": selected.output_scale,
            "normalized_rmse": transfer_normalized_rmse,
            "training_groups": training_groups,
            "validation_groups": validation_groups,
            "transfer_groups": transfer_groups,
        },
        "posthoc_translation": {
            **metadata["metadata"],
            "internal_program": selected.program.render(),
            "internal_formula": _formula(selected.program),
            "labels_revealed_after_audit": True,
        },
        "mistake_room": mistake_room,
        "next_experiment": {
            "generated_by_system": True,
            "target": transfer_audit["counterexamples"][0] if transfer_audit["counterexamples"] else None,
            "proposal": "Acquire a new independent source group at the largest residual regime, hold it sealed, and test whether a new state or interaction resource produces preregistered information gain.",
            "execution_status": "not_executed_no_independent_apparatus_or_laboratory",
        },
        "discovery_gates": gates,
        "proof_obligations": proof_obligations,
        "claim_state": {
            "autonomous_official_world_selection_allowed": passed,
            "fresh_official_snapshot_allowed": passed,
            "independent_laboratory_replication_allowed": False,
            "causal_law_claim_allowed": False,
            "human_unknown_law_claim_allowed": False,
            "fully_autonomous_scientist_claim_allowed": False,
            "current_label": "V44_BOUNDED_AUTONOMOUS_WORLD_SELECTION_CAUSAL_APPARATUS_REQUIRED",
        },
        "capability_progress": {
            "autonomous_world_selection": "implemented_and_verified",
            "knowledge_gap_ranking": "implemented_and_verified",
            "anonymous_variable_and_memory_growth": "implemented_via_v43_kernel",
            "question_generation": "implemented_as_ranked_research_agenda",
            "experiment_preregistration": "implemented_and_verified",
            "failure_memory": "implemented_and_replayable",
            "official_external_data_loop": "implemented_for_archival_observations",
            "causal_intervention": "protocol_generated_but_not_executed",
            "live_apparatus_control": "not_available",
            "unrestricted_language_invention": "not_achieved",
            "literature_novelty_adjudication": "not_achieved",
            "independent_lab_replication": "not_achieved",
        },
        "limitations": [
            "The host still curated a finite registry of three official worlds and supplied resource/safety limits.",
            "The research language still inherits floating-point arithmetic, least squares, and bounded V43 mutations.",
            "Official historical data are external evidence but not a new independent laboratory replication.",
            "Observational transfer cannot establish causation without intervention.",
            "The system proposed but did not execute a physical experiment.",
            "No claim of a human-unknown law or fully autonomous scientist is allowed.",
        ],
    }


def verify_v44_acceptance(acceptance):
    obligations = []

    def check(name, passed, actual):
        obligations.append({"obligation_id": name, "passed": bool(passed), "actual": actual})

    try:
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        counterexample_history = json.loads(COUNTEREXAMPLE_HISTORY.read_text(encoding="utf-8"))
        check("snapshot_digest_replay", _snapshot_digest(snapshot) == snapshot["snapshot_sha256"], snapshot["snapshot_sha256"])
        check("mistake_history_replay", acceptance["mistake_room"]["mandatory_replay_history"] == counterexample_history["events"], len(counterexample_history["events"]))
        program_payload = acceptance["discovery"]["selected_program"]
        program = program_from_report_v44(program_payload)
        check("program_id_replay", program.program_id == program_payload["program_id"], program.program_id)
        program_commitment = scientific_program_commitment_v43(program)
        check("program_commitment_replay", program_commitment == acceptance["preregistration"]["program_commitment"], program_commitment)
        agenda_payload = {
            "world_id": acceptance["autonomous_agenda"]["selected_world_id"],
            "program_commitment": program_commitment,
            "research_priority": round(float(acceptance["discovery"]["research_priority"]), 15),
            "normalized_information_gain": round(float(acceptance["discovery"]["normalized_information_gain"]), 15),
        }
        agenda_commitment = hashlib.sha256(json.dumps(agenda_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        check("agenda_commitment_replay", agenda_commitment == acceptance["preregistration"]["agenda_commitment"], agenda_commitment)
        ranking = acceptance["autonomous_agenda"]["ranking"]
        selected = acceptance["autonomous_agenda"]["selected_world_id"]
        expected_selected = max(ranking, key=lambda item: item["research_priority"])["world_id"]
        check("agenda_ranking_replay", selected == expected_selected, expected_selected)
        world = next(item for item in snapshot["worlds"] if item["world_id"] == selected)
        traces = tuple(_trace(item) for item in world["partitions"]["transfer"])
        replay = AutonomousScientistKernelV43().evaluate(program, traces)
        expected_rmse = acceptance["sealed_transfer_audit"]["rmse"]
        check("sealed_transfer_metric_replay", math.isclose(replay["rmse"], expected_rmse, rel_tol=0, abs_tol=1e-12), replay["rmse"])
        check("commit_before_reveal_replay", acceptance["preregistration"]["commit_event_index"] < acceptance["preregistration"]["transfer_reveal_event_index"], acceptance["preregistration"])
        claim = acceptance["claim_state"]
        check("overclaim_blocks_replay", not claim["fully_autonomous_scientist_claim_allowed"] and not claim["human_unknown_law_claim_allowed"] and not claim["causal_law_claim_allowed"], claim)
        check("proof_gate_replay", all(item["passed"] for item in acceptance["proof_obligations"]), len(acceptance["proof_obligations"]))
    except (KeyError, StopIteration, TypeError, ValueError, OverflowError) as error:
        check("report_structure", False, str(error))
    return {
        "verifier_version": "autonomous-world-research-v44-independent-replay-v0.1",
        "passed": all(item["passed"] for item in obligations),
        "obligations": obligations,
    }
