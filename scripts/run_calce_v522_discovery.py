from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from run_calce_v52_discovery import (
    baseline_commitments,
    common_effect,
    online_last_observed,
    predict_program,
    program_expression,
    rmse,
    search,
    sha256_file,
    training_scales,
)


ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_SNAPSHOT = ROOT / "data" / "calce_v522" / "all_nonsealed_anonymous.jsonl"
DEVELOPMENT_MANIFEST = ROOT / "data" / "calce_v522" / "all_nonsealed_manifest.json"
SEALED_SNAPSHOT = ROOT / "data" / "calce_v522" / "sealed_anonymous.jsonl"
SEALED_MANIFEST = ROOT / "data" / "calce_v522" / "sealed_manifest.json"
COMMITMENT = ROOT / "experiments" / "v522_calce_program_commitment.json"
SEALED_REPORT = ROOT / "artifacts" / "v522_calce_sealed_report.json"
GRAMMAR_SOURCE = ROOT / "scripts" / "run_calce_v52_discovery.py"


def read_snapshot(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not rows:
        raise ValueError(f"No observations in {path}")
    return rows


def claimed_controls(program: dict[str, Any]) -> list[str]:
    controls: set[str] = set()
    for term in program["terms"]:
        modifier = term["modifier"]
        for control in ("c0", "c1", "c2"):
            if control in modifier:
                controls.add(control)
    return sorted(controls)


def sensitivity_audit(
    rows: list[dict[str, Any]], program: dict[str, Any], scales: dict[str, float]
) -> dict[str, float]:
    reference = dict(rows[len(rows) // 2])
    result: dict[str, float] = {}
    for control in claimed_controls(program):
        key = f"control_{control[-1]}"
        low = dict(reference)
        high = dict(reference)
        low[key] = float(low[key]) - 0.01
        high[key] = float(high[key]) + 0.01
        change = float(predict_program([high], program, scales)[0] - predict_program([low], program, scales)[0])
        result[key] = change
        if abs(change) <= 1.0e-12:
            raise ValueError(f"Selected program is insensitive to claimed {key}")
    return result


def fit() -> None:
    rows = read_snapshot(DEVELOPMENT_SNAPSHOT)
    scales = training_scales(rows)
    selected = search(rows, scales)
    selected["expression"] = program_expression(selected)
    selected["semantic_name"] = "FORGED_V522_RESPONSE_OPERATOR"
    selected["counterfactual_sensitivity"] = sensitivity_audit(rows, selected, scales)
    commitment = {
        "schema": "v52.2-calce-program-commitment-v1",
        "status": "committed_before_sealed_archive_download",
        "development_observation_count": len(rows),
        "development_cell_count": len({row["cell_token"] for row in rows}),
        "development_group_count": len({row["group_token"] for row in rows}),
        "snapshot_sha256": sha256_file(DEVELOPMENT_SNAPSHOT),
        "manifest_sha256": sha256_file(DEVELOPMENT_MANIFEST),
        "discovery_script_sha256": sha256_file(Path(__file__)),
        "grammar_source_sha256": sha256_file(GRAMMAR_SOURCE),
        "scales": scales,
        "selected_program": selected,
        "registered_baselines": baseline_commitments(rows, scales),
        "sealed_archive_accessed": False,
        "domain_labels_visible_to_learner": False,
        "claims_blocked": [
            "electrochemical mediation",
            "rate effect separated from internal heating",
            "cross-chemistry universality",
            "human-unknown scientific law",
        ],
    }
    COMMITMENT.write_text(json.dumps(commitment, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"commitment={COMMITMENT.relative_to(ROOT).as_posix()}")
    print(f"candidates={selected['candidate_count']} atoms={selected['atom_count']}")
    print(f"leave_group_out_rmse={selected['leave_group_out_rmse']:.12g}")
    print(selected["expression"])


def logger_observations(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    lookup = {
        (item["cell_token"], int(item["diagnostic_index"])): item["logger_normalized_response"]
        for item in manifest["capacity_crosschecks"]
    }
    result: list[dict[str, Any]] = []
    for row in rows:
        value = lookup[(row["cell_token"], int(row["diagnostic_index"]))]
        if value is None or not np.isfinite(value) or value <= 0:
            raise ValueError("Invalid logger crosscheck response")
        copied = dict(row)
        copied["response"] = float(value)
        result.append(copied)
    return result


def metric_bundle(
    rows: list[dict[str, Any]], commitment: dict[str, Any]
) -> tuple[dict[str, float], str, float]:
    scored = [row for row in rows if int(row["diagnostic_index"]) > 0]
    observed = np.asarray([row["response"] for row in scored], dtype=float)
    metrics = {
        "forged_program": rmse(
            observed,
            predict_program(scored, commitment["selected_program"], commitment["scales"]),
        )
    }
    for name, baseline in commitment["registered_baselines"].items():
        if baseline.get("online"):
            online_observed, online_prediction = online_last_observed(rows)
            metrics[name] = rmse(online_observed, online_prediction)
        else:
            metrics[name] = rmse(
                observed, predict_program(scored, baseline, commitment["scales"])
            )
    best = min((name for name in metrics if name != "forged_program"), key=metrics.get)
    return metrics, best, metrics["forged_program"] / metrics[best]


def evaluate_sealed() -> None:
    commitment = json.loads(COMMITMENT.read_text(encoding="utf-8"))
    if commitment["snapshot_sha256"] != sha256_file(DEVELOPMENT_SNAPSHOT):
        raise ValueError("Development snapshot changed after commitment")
    if commitment["discovery_script_sha256"] != sha256_file(Path(__file__)):
        raise ValueError("Discovery script changed after commitment")
    rows = read_snapshot(SEALED_SNAPSHOT)
    manifest = json.loads(SEALED_MANIFEST.read_text(encoding="utf-8"))
    logger_rows = logger_observations(rows, manifest)
    metrics, best, ratio = metric_bundle(rows, commitment)
    logger_metrics, logger_best, logger_ratio = metric_bundle(logger_rows, commitment)
    nonsealed = read_snapshot(DEVELOPMENT_SNAPSHOT)
    matched = [
        row
        for row in nonsealed + rows
        if float(row["control_0"]) == 0.5 and float(row["control_1"]) == 0.6
    ]
    rate_effect = common_effect(matched, 0.5, 2.0)
    passed = ratio < 0.80 and logger_ratio < 0.80
    report = {
        "schema": "v52.2-calce-sealed-report-v1",
        "status": "success" if passed else "registered_sealed_failure",
        "sealed_observation_count": len(rows),
        "integrated_capacity_metrics": metrics,
        "integrated_best_baseline": best,
        "integrated_prediction_error_ratio": ratio,
        "logger_capacity_metrics": logger_metrics,
        "logger_best_baseline": logger_best,
        "logger_prediction_error_ratio": logger_ratio,
        "registered_threshold": 0.80,
        "parser_crosscheck_preserves_conclusion": (ratio < 0.80) == (logger_ratio < 0.80),
        "matched_assigned_rate_effect": rate_effect,
        "commitment_sha256": sha256_file(COMMITMENT),
        "sealed_snapshot_sha256": sha256_file(SEALED_SNAPSHOT),
        "sealed_manifest_sha256": sha256_file(SEALED_MANIFEST),
    }
    SEALED_REPORT.parent.mkdir(parents=True, exist_ok=True)
    SEALED_REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"report={SEALED_REPORT.relative_to(ROOT).as_posix()}")
    print(f"integrated_ratio={ratio:.12g} logger_ratio={logger_ratio:.12g}")
    print(f"status={report['status']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run V52.2 discovery and sealed evaluation.")
    parser.add_argument("mode", choices=("fit", "evaluate-sealed"))
    args = parser.parse_args()
    if args.mode == "fit":
        fit()
    else:
        evaluate_sealed()


if __name__ == "__main__":
    main()
