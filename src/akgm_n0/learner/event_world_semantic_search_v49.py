"""V49 anonymous local semantic search for the failed V48 event world."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

import numpy as np


def _digest(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class EventRowV49:
    trace_id: str
    index: int
    x: tuple[float, ...]
    previous_x: tuple[float, ...]
    lag1: float
    lag2: float
    target: float


class AnonymousEventAdapterV49:
    @staticmethod
    def _rows(partition):
        for trace in partition:
            inputs = trace["inputs"]
            outputs = trace["outputs"]
            for index in range(2, min(len(inputs), len(outputs))):
                yield trace["trace_id"], index, tuple(map(float, inputs[index])), tuple(map(float, inputs[index - 1])), float(outputs[index - 1]), float(outputs[index - 2]), float(outputs[index])

    def adapt(self, world):
        training_raw = list(self._rows(world["partitions"]["training"]))
        channel_count = len(training_raw[0][2])
        x_matrix = np.asarray([item[2] for item in training_raw], dtype=float)
        y_values = np.asarray(
            [float(value) for trace in world["partitions"]["training"] for value in trace["outputs"]],
            dtype=float,
        )
        x_mean = x_matrix.mean(axis=0)
        x_scale = x_matrix.std(axis=0)
        x_scale[x_scale < 1e-12] = 1.0
        y_mean, y_scale = float(y_values.mean()), float(y_values.std())
        y_scale = y_scale if y_scale > 1e-12 else 1.0

        def convert(partition):
            rows = []
            for trace_id, index, x, previous_x, lag1, lag2, target in self._rows(partition):
                normalized_x = tuple(float(value) for value in ((np.asarray(x) - x_mean) / x_scale))
                normalized_previous = tuple(float(value) for value in ((np.asarray(previous_x) - x_mean) / x_scale))
                rows.append(EventRowV49(
                    trace_id,
                    index,
                    normalized_x,
                    normalized_previous,
                    (lag1 - y_mean) / y_scale,
                    (lag2 - y_mean) / y_scale,
                    (target - y_mean) / y_scale,
                ))
            return rows

        return {
            "world_id": world["world_id"],
            "anonymous_descriptor": world["anonymous_descriptor"],
            "normalization": {
                "channel_count": channel_count,
                "input_mean": [float(value) for value in x_mean],
                "input_scale": [float(value) for value in x_scale],
                "output_mean": y_mean,
                "output_scale": y_scale,
                "fit_partition": "training_only",
            },
            "training": convert(world["partitions"]["training"]),
            "validation": convert(world["partitions"]["validation"]),
            "sealed_transfer": convert(world["partitions"]["transfer"]),
        }


def feature_value(name, row):
    if name == "ONE":
        return 1.0
    if name == "MEM(1)":
        return row.lag1
    if name == "MEM(2)":
        return row.lag2
    if name.startswith("READ("):
        return row.x[int(name[5:-1])]
    if name.startswith("DELTA_READ("):
        slot = int(name[11:-1])
        return row.x[slot] - row.previous_x[slot]
    if name.startswith("SELF_COUPLE("):
        slot = int(name[12:-1])
        return row.x[slot] * row.x[slot]
    if name.startswith("PAIR("):
        left, right = map(int, name[5:-1].split(","))
        return row.x[left] * row.x[right]
    if name.startswith("GUARD_POS("):
        slot = int(name[10:-1])
        return row.x[slot] if row.x[slot] > 0 else 0.0
    raise ValueError(name)


def _fit(features, rows, ridge=1e-4):
    design = np.asarray([[feature_value(name, row) for name in features] for row in rows], dtype=float)
    target = np.asarray([row.target for row in rows], dtype=float)
    gram = design.T @ design + ridge * np.eye(design.shape[1])
    coefficients = np.linalg.solve(gram, design.T @ target)
    return tuple(float(value) for value in coefficients)


def _predict(features, coefficients, row):
    return sum(
        coefficient * feature_value(name, row)
        for name, coefficient in zip(features, coefficients, strict=True)
    )


def evaluate_program(features, coefficients, rows):
    predictions = np.asarray([_predict(features, coefficients, row) for row in rows])
    targets = np.asarray([row.target for row in rows])
    errors = predictions - targets
    rmse = float(np.sqrt(np.mean(errors * errors)))
    baseline = float(np.sqrt(np.mean(targets * targets)))
    trace_ratios = []
    for trace_id in sorted({row.trace_id for row in rows}):
        indices = [index for index, row in enumerate(rows) if row.trace_id == trace_id]
        trace_errors = errors[indices]
        trace_targets = targets[indices]
        trace_rmse = float(np.sqrt(np.mean(trace_errors * trace_errors)))
        trace_baseline = float(np.sqrt(np.mean(trace_targets * trace_targets)))
        trace_ratios.append(trace_rmse / max(trace_baseline, 1e-15))
    order = np.argsort(np.abs(errors))[::-1][:10]
    return {
        "point_count": len(rows),
        "trace_count": len(trace_ratios),
        "rmse": rmse,
        "zero_baseline_rmse": baseline,
        "rmse_ratio_to_zero_baseline": rmse / max(baseline, 1e-15),
        "median_trace_ratio": float(np.median(trace_ratios)),
        "worst_trace_ratio": max(trace_ratios),
        "counterexamples": [
            {
                "trace_id": rows[index].trace_id,
                "index": rows[index].index,
                "anonymous_inputs": list(rows[index].x),
                "predicted": float(predictions[index]),
                "observed": float(targets[index]),
                "absolute_error": float(abs(errors[index])),
            }
            for index in order
        ],
    }


class AutonomousLocalLanguageSearchV49:
    @staticmethod
    def resource_pool(channel_count):
        pool = ["MEM(1)", "MEM(2)"]
        pool.extend(f"READ({slot})" for slot in range(channel_count))
        pool.extend(f"DELTA_READ({slot})" for slot in range(channel_count))
        pool.extend(f"SELF_COUPLE({slot})" for slot in range(channel_count))
        pool.extend(
            f"PAIR({left},{right})"
            for left in range(channel_count)
            for right in range(left + 1, channel_count)
        )
        pool.extend(f"GUARD_POS({slot})" for slot in range(channel_count))
        return tuple(pool)

    @staticmethod
    def _score(metrics, feature_count):
        return (
            metrics["rmse_ratio_to_zero_baseline"]
            + 0.12 * metrics["median_trace_ratio"]
            + 0.0015 * feature_count
        )

    def search(self, adapted, max_rounds=12, sterile_limit=3):
        training = adapted["training"]
        validation = adapted["validation"]
        pool = self.resource_pool(adapted["normalization"]["channel_count"])
        selected_features = ["ONE"]
        coefficients = _fit(tuple(selected_features), training)
        current_metrics = evaluate_program(tuple(selected_features), coefficients, validation)
        current_score = self._score(current_metrics, len(selected_features))
        rounds = []
        sterile = 0
        evaluated = 1
        for round_index in range(1, max_rounds + 1):
            trials = []
            for resource in pool:
                if resource in selected_features:
                    continue
                features = tuple(selected_features + [resource])
                trial_coefficients = _fit(features, training)
                metrics = evaluate_program(features, trial_coefficients, validation)
                score = self._score(metrics, len(features))
                trials.append({
                    "added_resource": resource,
                    "features": list(features),
                    "coefficients": list(trial_coefficients),
                    "validation": metrics,
                    "score": score,
                })
                evaluated += 1
            trials.sort(key=lambda item: (item["score"], item["added_resource"]))
            best = trials[0] if trials else None
            accepted = best is not None and best["score"] < current_score - 1e-4
            before = current_score
            if accepted:
                selected_features = best["features"]
                coefficients = tuple(best["coefficients"])
                current_metrics = best["validation"]
                current_score = best["score"]
                sterile = 0
            else:
                sterile += 1
            rounds.append({
                "round_index": round_index,
                "score_before": before,
                "score_after": current_score,
                "selected_resource": best["added_resource"] if accepted else None,
                "information_gain": before - current_score,
                "sterile_round_count": sterile,
                "host_selected": False,
                "trials": trials,
            })
            if sterile >= sterile_limit or not trials:
                break
        program = {
            "features": list(selected_features),
            "coefficients": list(coefficients),
            "validation": current_metrics,
        }
        return {
            "program_id": "EVENTSEM-" + _digest(program)[:16],
            "opaque_program": " + ".join(
                f"({coefficient:.12g})*{feature}"
                for coefficient, feature in zip(coefficients, selected_features, strict=True)
            ),
            "features": list(selected_features),
            "coefficients": list(coefficients),
            "validation": current_metrics,
            "rounds": rounds,
            "candidate_programs_evaluated": evaluated,
            "stop_reason": "semantic_saturation" if sterile >= sterile_limit else "round_budget",
            "host_selected": False,
            "human_names_received": False,
        }


def commit_program_v49(program):
    return _digest({
        "program_id": program["program_id"],
        "features": program["features"],
        "coefficients": program["coefficients"],
    })
