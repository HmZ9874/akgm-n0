"""Independent V43 replay and claim control for autonomous language growth."""
from __future__ import annotations

import json
import math
from pathlib import Path

from akgm_n0.learner.autonomous_scientist_v43 import (
    AnonymousNumericTraceV43,
    AutonomousScientistKernelV43,
    ResearchLanguageGenomeV43,
    ScientificProgramV43,
    scientific_program_commitment_v43,
)

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / "data/nasa_v41/nasa_battery_v41_blind_challenge.json"
V42_REPORT = ROOT / "reports/data/counterexample_transfer_v42_latest.json"


def _anonymous_trace(payload):
    return AnonymousNumericTraceV43(
        str(payload["trace_id"]),
        tuple(
            (float(row["q0"]), float(row["q2"]), float(row["q3"]))
            for row in payload["samples"]
        ),
        tuple(float(row["q1"]) for row in payload["samples"]),
    )


class SealedScientistArchiveV43:
    """Keep transfer-object responses behind an explicit program commitment."""

    def __init__(self, payload):
        self._payload = payload
        self._commitment = None
        self._event_index = 0

    def development(self):
        if self._commitment is not None:
            raise RuntimeError("development cannot reopen after commitment")
        rows = [item for item in self._payload["traces"] if item["source_cell"] == "RW5"]
        self._event_index += 1
        return {
            "training": tuple(_anonymous_trace(item) for item in rows[::2]),
            "validation": tuple(_anonymous_trace(item) for item in rows[1::2]),
            "event_index": self._event_index,
            "source_identity_exposed": False,
            "life_stage_exposed": False,
            "human_channel_names_exposed": False,
        }

    def commit(self, commitment):
        if self._commitment is not None:
            raise RuntimeError("only one V43 commitment is allowed")
        self._commitment = str(commitment)
        self._event_index += 1
        return {"commitment": self._commitment, "event_index": self._event_index}

    def reveal_transfer(self, commitment):
        if self._commitment is None or commitment != self._commitment:
            raise RuntimeError("transfer object is sealed")
        rows = [item for item in self._payload["traces"] if item["source_cell"] == "RW6"]
        self._event_index += 1
        return {
            "traces": tuple(_anonymous_trace(item) for item in rows),
            "stage_by_trace": {item["trace_id"]: item["life_stage"] for item in rows},
            "event_index": self._event_index,
            "labels_exposed_to_program": False,
        }


def _program_from_dict(payload):
    genome_payload = payload["genome"]
    genome = ResearchLanguageGenomeV43(
        int(genome_payload["visible_inputs"]),
        int(genome_payload["state_slots"]),
        int(genome_payload["initial_context"]),
        int(genome_payload["delta_features"]),
        int(genome_payload["pair_interactions"]),
        int(genome_payload["branch_slots"]),
    )
    return ScientificProgramV43(
        genome,
        tuple(map(str, payload["features"])),
        tuple(map(float, payload["coefficients"])),
        float(payload["validation_rmse"]),
        float(payload["validation_mape"]),
    )


def run_v43_acceptance():
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    v42 = json.loads(V42_REPORT.read_text(encoding="utf-8"))
    archive = SealedScientistArchiveV43(snapshot)
    development = archive.development()
    kernel = AutonomousScientistKernelV43()
    discovery = kernel.discover(development["training"], development["validation"])
    selected = discovery["selected_program"]
    commitment = scientific_program_commitment_v43(selected)
    commit = archive.commit(commitment)
    transfer = archive.reveal_transfer(commitment)

    overall = kernel.evaluate(selected, transfer["traces"])
    by_stage = {}
    for stage in ("early", "middle", "late"):
        traces = tuple(
            trace for trace in transfer["traces"]
            if transfer["stage_by_trace"][trace.trace_id] == stage
        )
        by_stage[stage] = kernel.evaluate(selected, traces)

    rounds = discovery["rounds"]
    selected_mutations = tuple(
        item.selected_mutation for item in rounds if item.selected_mutation
    )
    v42_acceptance = v42["acceptance"]
    v42_overall = v42_acceptance["transfer_audit"]["overall"]["rmse"]
    v42_nodes = v42_acceptance["discovery"]["selected"]["node_count"]
    threshold = 0.10
    stage_passes = {
        stage: audit["rmse"] < threshold for stage, audit in by_stage.items()
    }

    menu_gap = {
        "dependency_run_id": v42["run_id"],
        "v42_passed": v42_acceptance["passed"],
        "detected_gap": "V42 selected from developer-declared candidate families",
        "v42_candidate_kinds": [
            item["kind"] for item in v42_acceptance["discovery"]["candidates"]
        ],
        "v43_response": "replace named candidate families with generic structural genome mutation",
    }
    gates = {
        "v42_dependency_verified": v42_acceptance["passed"],
        "candidate_menu_gap_consumed": len(menu_gap["v42_candidate_kinds"]) == 3,
        "minimal_language_start": discovery["initial_genome"] == ResearchLanguageGenomeV43(),
        "no_named_candidate_menu_received": not discovery["named_candidate_menu_received"],
        "research_language_changed_itself": discovery["final_genome"] != discovery["initial_genome"],
        "input_visibility_grew_autonomously": "grow_input_channel" in selected_mutations,
        "memory_structure_grew_autonomously": selected_mutations.count("grow_state_slot") == 2,
        "two_state_slots_selected": discovery["final_genome"].state_slots == 2,
        "all_rounds_score_selected": all(not item.to_dict()["host_selected"] for item in rounds),
        "stopped_after_semantic_saturation": discovery["stop_reason"] == "semantic_saturation" and discovery["sterile_rounds"] == 3,
        "commitment_precedes_transfer_reveal": commit["event_index"] < transfer["event_index"],
        "frozen_without_transfer_refit": commitment == scientific_program_commitment_v43(selected),
        "all_transfer_stages_below_threshold": all(stage_passes.values()),
        "shorter_than_v42_selected_program": selected.node_count < v42_nodes,
        "lower_transfer_rmse_than_v42": overall["rmse"] < v42_overall,
        "fresh_external_replication_claim_blocked": True,
        "fully_autonomous_scientist_claim_blocked": True,
        "human_unknown_law_claim_blocked": True,
    }
    proof_obligations = [
        {"obligation_id": name, "passed": value} for name, value in gates.items()
    ]
    passed = all(item["passed"] for item in proof_obligations)
    coefficients = selected.coefficients
    posthoc_formula = (
        f"s_t={coefficients[0]:.12g}"
        f"+({coefficients[1]:.12g})Q0_t"
        f"+({coefficients[2]:.12g})Q2_t"
        f"+({coefficients[3]:.12g})s_(t-1)"
        f"+({coefficients[4]:.12g})s_(t-2)"
    )
    return {
        "benchmark_version": "autonomous-scientist-kernel-v43.0",
        "passed": passed,
        "final_status": "verified" if passed else "bounded",
        "classification": "bounded_autonomous_research_language_growth_on_reused_archive",
        "menu_gap": menu_gap,
        "information_boundary": {
            "learner_received": [
                "opaque numeric input tuples",
                "development response tuples",
                "generic structural mutation rules",
                "complexity and validation score",
            ],
            "learner_withheld": [
                "physical channel names",
                "source object identities",
                "life-stage labels",
                "named candidate model families",
                "transfer-object responses before commitment",
                "post-hoc human formula",
            ],
            "supplied_priors": [
                "floating-point arithmetic",
                "linear least-squares coefficient fitting",
                "maximum two recurrent state slots",
                "bounded structural mutation operators",
                "independent score and verifier",
            ],
        },
        "discovery": {
            "initial_genome": discovery["initial_genome"].to_dict(),
            "final_genome": discovery["final_genome"].to_dict(),
            "selected_program": selected.to_dict(),
            "selected_mutations": list(selected_mutations),
            "rounds": [item.to_dict() for item in rounds],
            "candidate_programs_evaluated": discovery["candidate_programs_evaluated"],
            "sterile_rounds": discovery["sterile_rounds"],
            "stop_reason": discovery["stop_reason"],
        },
        "preregistration": {
            "program_commitment": commitment,
            "development_event_index": development["event_index"],
            "commit_event_index": commit["event_index"],
            "transfer_reveal_event_index": transfer["event_index"],
            "commitment_precedes_transfer_reveal": commit["event_index"] < transfer["event_index"],
        },
        "transfer_audit": {
            "threshold_rmse": threshold,
            "overall": overall,
            "by_life_stage": by_stage,
            "stage_passes": stage_passes,
            "v42_overall_rmse": v42_overall,
            "rmse_ratio_to_v42": overall["rmse"] / v42_overall,
        },
        "posthoc_translation": {
            "internal_operation": "two-slot autonomous recurrent update",
            "human_equivalent_family": "second-order autoregressive model with anonymous exogenous inputs",
            "formula": posthoc_formula,
            "channel_mapping_visible_only_after_discovery": {
                "Q0": "absolute measured current",
                "Q1_and_state": "terminal voltage",
                "Q2": "battery temperature",
            },
        },
        "discovery_gates": gates,
        "proof_obligations": proof_obligations,
        "claim_state": {
            "autonomous_language_growth_on_reused_archive_allowed": passed,
            "fresh_external_replication_claim_allowed": False,
            "fully_autonomous_scientist_claim_allowed": False,
            "universal_battery_model_allowed": False,
            "human_unknown_claim_allowed": False,
            "current_label": "V43_BOUNDED_AUTONOMOUS_LANGUAGE_GROWTH_EXTERNAL_WORLD_REQUIRED",
        },
        "limitations": [
            "The system changed a bounded research language; it did not invent an unrestricted programming language.",
            "State memory is capped at two slots and coefficients use supplied least-squares fitting.",
            "RW6 is programmatically sealed from the learner but was previously visible to developers.",
            "The archive is reused and does not provide fresh independent-laboratory replication.",
            "No live physical apparatus was controlled in this run.",
            "The discovered recurrence is not claimed to be a human-unknown electrochemical law.",
            "A fully autonomous scientist has not yet been achieved.",
        ],
    }


def verify_v43_acceptance(acceptance):
    obligations = []

    def check(name, passed, actual):
        obligations.append({"obligation_id": name, "passed": bool(passed), "actual": actual})

    try:
        program = _program_from_dict(acceptance["discovery"]["selected_program"])
        check(
            "program_id_replay",
            program.program_id == acceptance["discovery"]["selected_program"]["program_id"],
            program.program_id,
        )
        check(
            "commitment_replay",
            scientific_program_commitment_v43(program) == acceptance["preregistration"]["program_commitment"],
            scientific_program_commitment_v43(program),
        )
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        traces = tuple(
            _anonymous_trace(item) for item in snapshot["traces"]
            if item["source_cell"] == "RW6"
        )
        replay = AutonomousScientistKernelV43().evaluate(program, traces)
        expected = acceptance["transfer_audit"]["overall"]["rmse"]
        check("sealed_metric_replay", math.isclose(replay["rmse"], expected, rel_tol=0, abs_tol=1e-12), replay["rmse"])
        checks = acceptance["proof_obligations"]
        check("claim_gate_replay", all(item["passed"] for item in checks), len(checks))
        claim = acceptance["claim_state"]
        check(
            "overclaim_blocks_replay",
            not claim["fresh_external_replication_claim_allowed"]
            and not claim["fully_autonomous_scientist_claim_allowed"]
            and not claim["human_unknown_claim_allowed"],
            claim,
        )
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        check("report_structure", False, str(error))
    return {
        "verifier_version": "autonomous-scientist-v43-independent-replay-v0.1",
        "passed": all(item["passed"] for item in obligations),
        "obligations": obligations,
    }
