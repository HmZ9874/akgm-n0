from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "calce_v52" / "v52_development_validation_anonymous.jsonl"
MANIFEST = ROOT / "data" / "calce_v52" / "v52_development_validation_manifest.json"
COMMITMENT = ROOT / "experiments" / "v52_calce_program_commitment.json"
VALIDATION_REPORT = ROOT / "artifacts" / "v52_calce_validation_report.json"
RIDGE = 1.0e-8


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(partition: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with SNAPSHOT.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["partition"] == partition:
                rows.append(row)
    if not rows:
        raise ValueError(f"No {partition} observations")
    return rows


def training_scales(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "diagnostic_index": max(float(row["diagnostic_index"]) for row in rows),
        "throughput": max(float(row["throughput_coordinate"]) for row in rows),
        "control_0_center": float(np.mean([row["control_0"] for row in rows])),
        "control_1_center": float(np.mean([row["control_1"] for row in rows])),
        "control_2_center": float(np.mean([row["control_2"] for row in rows])),
    }


def progression(name: str, row: dict[str, Any], scales: dict[str, float]) -> float:
    index = float(row["diagnostic_index"]) / scales["diagnostic_index"]
    throughput = float(row["throughput_coordinate"]) / scales["throughput"]
    if name == "index":
        return index
    if name == "throughput":
        return throughput
    if name == "sqrt_throughput":
        return float(np.sqrt(max(throughput, 0.0)))
    if name == "log_throughput":
        return float(np.log1p(4.0 * max(throughput, 0.0)) / np.log(5.0))
    if name == "square_throughput":
        return throughput * throughput
    raise KeyError(name)


def modifier(name: str, row: dict[str, Any], scales: dict[str, float]) -> float:
    controls = {
        "c0": float(row["control_0"]) - scales["control_0_center"],
        "c1": float(row["control_1"]) - scales["control_1_center"],
        "c2": float(row["control_2"]) - scales["control_2_center"],
    }
    if name == "one":
        return 1.0
    if name in controls:
        return controls[name]
    left, right = name.split("_times_")
    return controls[left] * controls[right]


def term_value(term: dict[str, str], row: dict[str, Any], scales: dict[str, float]) -> float:
    return progression(term["progression"], row, scales) * modifier(term["modifier"], row, scales)


def design(rows: list[dict[str, Any]], terms: list[dict[str, str]], scales: dict[str, float]) -> np.ndarray:
    return np.asarray(
        [[term_value(term, row, scales) for term in terms] for row in rows], dtype=float
    )


def targets(rows: list[dict[str, Any]]) -> np.ndarray:
    return np.asarray([float(row["response"]) - 1.0 for row in rows], dtype=float)


def fit_coefficients(matrix: np.ndarray, target: np.ndarray) -> np.ndarray:
    gram = matrix.T @ matrix + RIDGE * np.eye(matrix.shape[1])
    return np.linalg.solve(gram, matrix.T @ target)


def rmse(observed: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(observed - predicted))))


def candidate_terms(rows: list[dict[str, Any]], scales: dict[str, float]) -> list[dict[str, str]]:
    progressions = ("index", "throughput", "sqrt_throughput", "log_throughput", "square_throughput")
    modifiers = ("one", "c0", "c1", "c2", "c0_times_c1", "c0_times_c2", "c1_times_c2")
    raw = [
        {"progression": progression_name, "modifier": modifier_name}
        for progression_name in progressions
        for modifier_name in modifiers
    ]
    unique: list[dict[str, str]] = []
    fingerprints: set[bytes] = set()
    for term in raw:
        values = design(rows, [term], scales).reshape(-1)
        if float(np.std(values)) < 1.0e-12:
            continue
        fingerprint = np.round(values, 12).tobytes()
        if fingerprint in fingerprints:
            continue
        fingerprints.add(fingerprint)
        unique.append(term)
    return unique


def term_nodes(term: dict[str, str]) -> int:
    progression_nodes = {
        "index": 1,
        "throughput": 1,
        "sqrt_throughput": 2,
        "log_throughput": 4,
        "square_throughput": 2,
    }[term["progression"]]
    modifier_nodes = 1 if term["modifier"] in {"one", "c0", "c1", "c2"} else 3
    return 1 + progression_nodes + modifier_nodes


def leave_group_out_score(
    rows: list[dict[str, Any]], terms: list[dict[str, str]], scales: dict[str, float]
) -> tuple[float, list[float]]:
    groups = sorted({row["group_token"] for row in rows})
    fold_scores: list[float] = []
    for held_group in groups:
        fit_rows = [row for row in rows if row["group_token"] != held_group]
        held_rows = [row for row in rows if row["group_token"] == held_group]
        coefficients = fit_coefficients(design(fit_rows, terms, scales), targets(fit_rows))
        predicted = 1.0 + design(held_rows, terms, scales) @ coefficients
        fold_scores.append(rmse(np.asarray([row["response"] for row in held_rows]), predicted))
    return float(np.mean(fold_scores)), fold_scores


def search(rows: list[dict[str, Any]], scales: dict[str, float]) -> dict[str, Any]:
    atoms = candidate_terms(rows, scales)
    best: dict[str, Any] | None = None
    candidate_count = 0
    behavior_fingerprints: set[bytes] = set()
    for size in (1, 2, 3):
        for term_tuple in itertools.combinations(atoms, size):
            terms = list(term_tuple)
            matrix = design(rows, terms, scales)
            if np.linalg.matrix_rank(matrix) < len(terms):
                continue
            coefficients = fit_coefficients(matrix, targets(rows))
            behavior = np.round(matrix @ coefficients, 10).tobytes()
            if behavior in behavior_fingerprints:
                continue
            behavior_fingerprints.add(behavior)
            candidate_count += 1
            cv_rmse, fold_scores = leave_group_out_score(rows, terms, scales)
            nodes = sum(term_nodes(term) for term in terms) + 2 * len(terms)
            score = cv_rmse + 1.0e-4 * nodes
            result = {
                "terms": terms,
                "coefficients": [float(value) for value in coefficients],
                "leave_group_out_rmse": cv_rmse,
                "fold_rmse": fold_scores,
                "program_nodes": nodes,
                "objective_score": score,
            }
            if best is None or (score, nodes) < (best["objective_score"], best["program_nodes"]):
                best = result
    if best is None:
        raise RuntimeError("No executable candidate survived search")
    best["candidate_count"] = candidate_count
    best["atom_count"] = len(atoms)
    return best


def baseline_commitments(rows: list[dict[str, Any]], scales: dict[str, float]) -> dict[str, Any]:
    definitions = {
        "linear_index": [{"progression": "index", "modifier": "one"}],
        "linear_throughput": [{"progression": "throughput", "modifier": "one"}],
        "quadratic_throughput": [
            {"progression": "throughput", "modifier": "one"},
            {"progression": "square_throughput", "modifier": "one"},
        ],
        "protocol_controls_without_rate_interaction": [
            {"progression": "throughput", "modifier": "one"},
            {"progression": "throughput", "modifier": "c0"},
            {"progression": "throughput", "modifier": "c1"},
        ],
    }
    result: dict[str, Any] = {"last_observed_normalized_capacity": {"online": True}}
    for name, terms in definitions.items():
        coefficients = fit_coefficients(design(rows, terms, scales), targets(rows))
        cv_score, _ = leave_group_out_score(rows, terms, scales)
        result[name] = {
            "terms": terms,
            "coefficients": [float(value) for value in coefficients],
            "development_leave_group_out_rmse": cv_score,
        }
    return result


def predict_program(
    rows: list[dict[str, Any]], program: dict[str, Any], scales: dict[str, float]
) -> np.ndarray:
    coefficients = np.asarray(program["coefficients"], dtype=float)
    return 1.0 + design(rows, program["terms"], scales) @ coefficients


def program_expression(program: dict[str, Any]) -> str:
    pieces = []
    for coefficient, term in zip(program["coefficients"], program["terms"], strict=True):
        pieces.append(
            f"({coefficient:.12g})*{term['progression']}*{term['modifier']}"
        )
    return "response_hat = 1 + " + " + ".join(pieces)


def fit() -> None:
    rows = read_rows("development")
    scales = training_scales(rows)
    selected = search(rows, scales)
    selected["expression"] = program_expression(selected)
    selected["semantic_name"] = "FORGED_V52_RESPONSE_OPERATOR"
    baselines = baseline_commitments(rows, scales)
    commitment = {
        "schema": "v52-calce-program-commitment-v1",
        "status": "committed_before_validation_evaluation_and_sealed_access",
        "learner_visible_labels": [
            "diagnostic_index",
            "throughput_coordinate",
            "control_0",
            "control_1",
            "control_2",
            "response",
        ],
        "domain_labels_visible_to_learner": False,
        "development_observation_count": len(rows),
        "development_group_count": len({row["group_token"] for row in rows}),
        "snapshot_sha256": sha256_file(SNAPSHOT),
        "manifest_sha256": sha256_file(MANIFEST),
        "discovery_script_sha256": sha256_file(Path(__file__)),
        "scales": scales,
        "selected_program": selected,
        "registered_baselines": baselines,
        "sealed_archive_accessed": False,
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
    print(f"development_leave_group_out_rmse={selected['leave_group_out_rmse']:.12g}")
    print(selected["expression"])


def online_last_observed(rows: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    observed: list[float] = []
    predicted: list[float] = []
    by_cell: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_cell.setdefault(row["cell_token"], []).append(row)
    for cell_rows in by_cell.values():
        ordered = sorted(cell_rows, key=lambda row: row["diagnostic_index"])
        for previous, current in zip(ordered, ordered[1:]):
            observed.append(float(current["response"]))
            predicted.append(float(previous["response"]))
    return np.asarray(observed), np.asarray(predicted)


def common_effect(rows: list[dict[str, Any]], low_rate: float, high_rate: float) -> dict[str, Any]:
    by_rate_cell: dict[float, dict[str, list[dict[str, Any]]]] = {}
    for row in rows:
        by_rate_cell.setdefault(float(row["control_2"]), {}).setdefault(row["cell_token"], []).append(row)
    if low_rate not in by_rate_cell or high_rate not in by_rate_cell:
        return {"status": "unavailable"}
    low_cells = by_rate_cell[low_rate]
    high_cells = by_rate_cell[high_rate]
    common_max = min(
        min(max(item["throughput_coordinate"] for item in values) for values in low_cells.values()),
        min(max(item["throughput_coordinate"] for item in values) for values in high_cells.values()),
    )
    reference = 0.8 * common_max

    def interpolate(cell_rows: list[dict[str, Any]]) -> float:
        ordered = sorted(cell_rows, key=lambda row: row["throughput_coordinate"])
        x = np.asarray([row["throughput_coordinate"] for row in ordered], dtype=float)
        y = np.asarray([row["response"] for row in ordered], dtype=float)
        return float(np.interp(reference, x, y))

    low_values = [interpolate(value) for value in low_cells.values()]
    high_values = [interpolate(value) for value in high_cells.values()]
    effect = float(np.mean(high_values) - np.mean(low_values))
    return {
        "status": "bounded",
        "reference_throughput": reference,
        "low_rate_cell_count": len(low_values),
        "high_rate_cell_count": len(high_values),
        "low_rate_mean_response": float(np.mean(low_values)),
        "high_rate_mean_response": float(np.mean(high_values)),
        "high_minus_low_response": effect,
        "direction": "higher_response_at_high_rate" if effect > 0 else "lower_response_at_high_rate",
        "bootstrap_interval_available": len(low_values) >= 2 and len(high_values) >= 2,
    }


def evaluate_validation() -> None:
    commitment = json.loads(COMMITMENT.read_text(encoding="utf-8"))
    if commitment["snapshot_sha256"] != sha256_file(SNAPSHOT):
        raise ValueError("Snapshot changed after program commitment")
    if commitment["discovery_script_sha256"] != sha256_file(Path(__file__)):
        raise ValueError("Discovery script changed after program commitment")
    rows = read_rows("validation")
    scored_rows = [row for row in rows if int(row["diagnostic_index"]) > 0]
    observed = np.asarray([row["response"] for row in scored_rows], dtype=float)
    program = commitment["selected_program"]
    program_prediction = predict_program(scored_rows, program, commitment["scales"])
    metrics: dict[str, float] = {"forged_program": rmse(observed, program_prediction)}
    for name, baseline in commitment["registered_baselines"].items():
        if baseline.get("online"):
            online_observed, online_prediction = online_last_observed(rows)
            metrics[name] = rmse(online_observed, online_prediction)
        else:
            prediction = predict_program(scored_rows, baseline, commitment["scales"])
            metrics[name] = rmse(observed, prediction)
    best_baseline_name = min(
        (name for name in metrics if name != "forged_program"), key=metrics.get
    )
    ratio = metrics["forged_program"] / metrics[best_baseline_name]
    controls = sorted({(row["control_0"], row["control_1"]) for row in rows})
    matched_effects = []
    for control_0, control_1 in controls:
        subset = [
            row for row in rows if row["control_0"] == control_0 and row["control_1"] == control_1
        ]
        rates = sorted({float(row["control_2"]) for row in subset})
        if len(rates) == 2:
            matched_effects.append(
                {
                    "anonymous_controls": {"control_0": control_0, "control_1": control_1},
                    **common_effect(subset, rates[0], rates[1]),
                }
            )
    report = {
        "schema": "v52-calce-validation-report-v1",
        "status": "success" if ratio < 0.80 else "registered_prediction_failure",
        "validation_observation_count": len(rows),
        "scored_observation_count": len(scored_rows),
        "rmse": metrics,
        "best_registered_baseline": best_baseline_name,
        "prediction_error_ratio": ratio,
        "registered_threshold": 0.80,
        "matched_rate_effects": matched_effects,
        "sealed_archive_accessed": False,
        "commitment_sha256": sha256_file(COMMITMENT),
    }
    VALIDATION_REPORT.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"report={VALIDATION_REPORT.relative_to(ROOT).as_posix()}")
    print(f"forged_rmse={metrics['forged_program']:.12g}")
    print(f"best_baseline={best_baseline_name} rmse={metrics[best_baseline_name]:.12g}")
    print(f"prediction_error_ratio={ratio:.12g} status={report['status']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the V52 anonymous discovery and validation stages.")
    parser.add_argument("mode", choices=("fit", "evaluate-validation"))
    args = parser.parse_args()
    if args.mode == "fit":
        fit()
    else:
        evaluate_validation()


if __name__ == "__main__":
    main()
