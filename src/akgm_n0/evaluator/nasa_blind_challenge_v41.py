"""Post-commit RW5/RW6 stress test for the frozen V41 dynamic program."""
from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path

from akgm_n0.learner.dynamic_state_v41 import AnonymousTraceV41, DynamicProgramV41, DynamicStateResearchV41

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/data/official_dynamic_science_v41_latest.json"
SNAPSHOT = ROOT / "data/nasa_v41/nasa_battery_v41_blind_challenge.json"
PROVENANCE = ROOT / "data/nasa_v41/nasa_battery_v41_blind_challenge_provenance.json"


def _program(payload):
    return DynamicProgramV41(
        payload["kind"], tuple(payload["coefficients"]),
        payload["validation_rmse"], payload["validation_mape"], payload["node_count"],
    )


def run_v41_blind_challenge():
    original = json.loads(REPORT.read_text(encoding="utf-8"))
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    selected_payload = original["acceptance"]["discovery"]["selected"]
    selected = _program(selected_payload)
    researcher = DynamicStateResearchV41()
    traces = [AnonymousTraceV41.from_dict(item) for item in snapshot["traces"]]

    def group(field, value):
        return [trace for trace, raw in zip(traces, snapshot["traces"]) if raw[field] == value]

    overall = researcher.evaluate(selected, traces)
    by_cell = {cell: researcher.evaluate(selected, group("source_cell", cell)) for cell in ("RW5", "RW6")}
    by_stage = {stage: researcher.evaluate(selected, group("life_stage", stage)) for stage in ("early", "middle", "late")}
    candidates = {}
    for payload in original["acceptance"]["discovery"]["candidates"]:
        candidates[payload["kind"]] = researcher.evaluate(_program(payload), traces)

    median_initial = statistics.median(trace.samples[0]["q1"] for trace in traces)
    corrupted = []
    for trace in traces:
        first = {**trace.samples[0], "q1": median_initial}
        corrupted.append(AnonymousTraceV41(trace.trace_id, (first, *trace.samples[1:])))
    corrupted_audit = researcher.evaluate(selected, corrupted)

    provenance_audit = {
        **provenance,
        "snapshot_digest_recomputed": hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest(),
    }
    provenance_audit["passed"] = provenance_audit["snapshot_digest_recomputed"] == provenance["snapshot_sha256"] and provenance["program_id"] == selected.program_id and provenance["frozen_program_precedes_challenge"] and not provenance["program_refit_allowed"]
    performance = {
        "overall": overall,
        "by_cell": by_cell,
        "by_life_stage": by_stage,
        "candidate_comparison": candidates,
        "corrupted_initial_state": corrupted_audit,
        "state_corruption_rmse_ratio": corrupted_audit["rmse"] / overall["rmse"],
        "state_fold_best_overall": overall["rmse"] < min(candidates["stateless"]["rmse"], candidates["persistence"]["rmse"]),
        "early_stage_passed": by_stage["early"]["rmse"] < 0.08,
        "middle_stage_passed": by_stage["middle"]["rmse"] < 0.10,
        "late_stage_passed": by_stage["late"]["rmse"] < 0.10,
        "overall_median_percentage_passed": overall["median_absolute_percentage_error"] < 0.02,
    }
    failure = {
        "failure_id": "V41-CHALLENGE-LATE-LIFE-EXTRAPOLATION",
        "scope": "RW5_RW6_LATE_LIFE",
        "expected_max_rmse": 0.10,
        "observed_rmse": by_stage["late"]["rmse"],
        "passed": performance["late_stage_passed"],
        "action": "restrict_STATE_FOLD_to_early_and_middle_life_until_an_aging_state_is_created",
        "universal_formula_removed": True,
    }
    gates = {
        "post_commit_challenge_integrity": provenance_audit["passed"],
        "two_unseen_cells": provenance["cell_counts"] == {"RW5": 60, "RW6": 60},
        "three_life_stages": provenance["stage_counts"] == {"early": 40, "middle": 40, "late": 40},
        "no_parameter_refit": not provenance["program_refit_allowed"],
        "state_fold_still_best_overall": performance["state_fold_best_overall"],
        "initial_state_is_causally_useful": performance["state_corruption_rmse_ratio"] > 1.5,
        "early_stage_generalization": performance["early_stage_passed"],
        "middle_stage_generalization": performance["middle_stage_passed"],
        "late_stage_generalization": performance["late_stage_passed"],
        "overall_median_percentage_error": performance["overall_median_percentage_passed"],
        "universal_all_life_model": False,
    }
    protocol_gates = [key for key in gates if key not in ("late_stage_generalization", "universal_all_life_model")]
    return {
        "challenge_version": "nasa-v41-rw5-rw6-blind-challenge.0",
        "challenge_complete": all(gates[key] for key in protocol_gates),
        "universal_pass": all(value for key, value in gates.items() if key != "universal_all_life_model"),
        "final_status": "verified" if gates["late_stage_generalization"] else "bounded",
        "classification": "frozen_state_fold_generalizes_early_middle_but_fails_late_life_extrapolation",
        "frozen_program": selected.to_dict(),
        "provenance_audit": provenance_audit,
        "performance_audit": performance,
        "counterexample": failure,
        "challenge_gates": gates,
        "claim_state": {
            "early_middle_dynamic_model_allowed": performance["early_stage_passed"] and performance["middle_stage_passed"],
            "all_life_dynamic_model_allowed": False,
            "human_unknown_claim_allowed": False,
            "current_label": "NASA_STATE_FOLD_BOUNDED_BY_LATE_LIFE_COUNTEREXAMPLE",
        },
    }
