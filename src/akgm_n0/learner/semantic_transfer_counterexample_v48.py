"""V48 cross-domain counterexample campaign and scope-semantic growth."""
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
class AdaptedRowV48:
    trace_id: str
    index: int
    q0: float
    q1: float
    q2: float
    target: float


class CanonicalTemporalAdapterV48:
    """Map every anonymous temporal world to one input plus two output lags."""

    @staticmethod
    def _flat(partition):
        for trace in partition:
            inputs = trace["inputs"]
            outputs = trace["outputs"]
            for index in range(2, min(len(inputs), len(outputs))):
                yield trace["trace_id"], index, float(inputs[index][0]), float(outputs[index - 1]), float(outputs[index - 2]), float(outputs[index])

    def adapt(self, world):
        partitions = world["partitions"]
        training_raw = list(self._flat(partitions["training"]))
        x_values = np.asarray([item[2] for item in training_raw], dtype=float)
        y_values = np.asarray(
            [float(value) for trace in partitions["training"] for value in trace["outputs"]],
            dtype=float,
        )
        x_mean, y_mean = float(x_values.mean()), float(y_values.mean())
        x_scale, y_scale = float(x_values.std()), float(y_values.std())
        x_scale = x_scale if x_scale > 1e-12 else 1.0
        y_scale = y_scale if y_scale > 1e-12 else 1.0

        def convert(partition):
            return [AdaptedRowV48(
                trace_id,
                index,
                (q0 - x_mean) / x_scale,
                (q1 - y_mean) / y_scale,
                (q2 - y_mean) / y_scale,
                (target - y_mean) / y_scale,
            ) for trace_id, index, q0, q1, q2, target in self._flat(partition)]

        return {
            "world_id": world["world_id"],
            "anonymous_descriptor": world["anonymous_descriptor"],
            "normalization": {
                "input_mean": x_mean,
                "input_scale": x_scale,
                "output_mean": y_mean,
                "output_scale": y_scale,
                "fit_partition": "training_only",
            },
            "training": convert(partitions["training"]),
            "validation": convert(partitions["validation"]),
            "sealed_transfer": convert(partitions["sealed_transfer"]),
        }


def opx_predict(row):
    return row.q0 * row.q1 * row.q2 + (row.q0 if row.q0 > row.q1 else 0.0)


def _feature(name, row):
    if name == "PREV":
        return row.q1
    if name == "DELTA":
        return row.q1 - row.q2
    if name == "INPUT":
        return row.q0
    if name == "GUARD":
        return row.q0 if row.q0 > row.q1 else 0.0
    if name == "OPX":
        return opx_predict(row)
    raise ValueError(name)


def _metrics(rows, predictor):
    errors = np.asarray([predictor(row) - row.target for row in rows], dtype=float)
    targets = np.asarray([row.target for row in rows], dtype=float)
    rmse = float(np.sqrt(np.mean(errors * errors)))
    baseline_rmse = float(np.sqrt(np.mean(targets * targets)))
    order = np.argsort(np.abs(errors))[::-1][:5]
    return {
        "point_count": len(rows),
        "rmse": rmse,
        "zero_baseline_rmse": baseline_rmse,
        "rmse_ratio_to_zero_baseline": rmse / max(baseline_rmse, 1e-15),
        "counterexamples": [
            {
                "trace_id": rows[index].trace_id,
                "index": rows[index].index,
                "q": [rows[index].q0, rows[index].q1, rows[index].q2],
                "predicted": float(predictor(rows[index])),
                "observed": rows[index].target,
                "absolute_error": float(abs(errors[index])),
            }
            for index in order
        ],
    }


class FrozenSemanticTransferV48:
    def audit(self, adapted_worlds):
        results = []
        for world in adapted_worlds:
            validation = _metrics(world["validation"], opx_predict)
            sealed = _metrics(world["sealed_transfer"], opx_predict)
            results.append({
                "world_id": world["world_id"],
                "descriptor": world["anonymous_descriptor"],
                "normalization": world["normalization"],
                "validation": validation,
                "sealed_transfer": sealed,
                "frozen_without_refit": True,
                "universal_transfer_passed": sealed["rmse_ratio_to_zero_baseline"] < 1.0,
            })
        return {
            "semantic_id": "OPX-c9c8b1a02aa5734c",
            "adapter": "Q0=current first anonymous input; Q1=previous output; Q2=second previous output; training-only z scores",
            "world_results": results,
            "passed_world_count": sum(item["universal_transfer_passed"] for item in results),
            "world_count": len(results),
            "universal_transfer_claim_allowed": all(item["universal_transfer_passed"] for item in results),
        }


class CounterexampleDrivenSemanticSearchV48:
    FEATURE_SETS = (
        ("PREV",),
        ("PREV", "DELTA"),
        ("PREV", "INPUT"),
        ("PREV", "DELTA", "INPUT"),
        ("PREV", "GUARD"),
        ("PREV", "OPX"),
        ("PREV", "DELTA", "INPUT", "GUARD"),
    )

    @staticmethod
    def _fit(features, rows):
        design = np.asarray([[_feature(name, row) for name in features] for row in rows], dtype=float)
        target = np.asarray([row.target for row in rows], dtype=float)
        coefficients, *_ = np.linalg.lstsq(design, target, rcond=None)
        return tuple(float(value) for value in coefficients)

    @staticmethod
    def _predictor(features, coefficients):
        return lambda row: sum(coefficient * _feature(name, row) for name, coefficient in zip(features, coefficients, strict=True))

    def search(self, adapted_worlds):
        training = [row for world in adapted_worlds for row in world["training"]]
        trials = []
        for features in self.FEATURE_SETS:
            coefficients = self._fit(features, training)
            predictor = self._predictor(features, coefficients)
            validation = {
                world["world_id"]: _metrics(world["validation"], predictor)
                for world in adapted_worlds
            }
            ratios = [item["rmse_ratio_to_zero_baseline"] for item in validation.values()]
            score = float(np.mean(ratios) + 0.75 * max(ratios) + 0.002 * len(features))
            trials.append({
                "features": list(features),
                "coefficients": list(coefficients),
                "validation": validation,
                "mean_ratio": float(np.mean(ratios)),
                "worst_ratio": max(ratios),
                "score": score,
            })
        trials.sort(key=lambda item: (item["score"], len(item["features"]), item["features"]))
        selected = trials[0]
        predictor = self._predictor(tuple(selected["features"]), tuple(selected["coefficients"]))
        sealed = {
            world["world_id"]: _metrics(world["sealed_transfer"], predictor)
            for world in adapted_worlds
        }
        passed = {
            world_id: metrics["rmse_ratio_to_zero_baseline"] < 1.0
            for world_id, metrics in sealed.items()
        }
        program_payload = {
            "features": selected["features"],
            "coefficients": selected["coefficients"],
        }
        return {
            "candidate_program_id": "XFERSEM-" + _digest(program_payload)[:16],
            "selected": selected,
            "sealed_transfer": sealed,
            "passed_worlds": sorted(world_id for world_id, ok in passed.items() if ok),
            "failed_worlds": sorted(world_id for world_id, ok in passed.items() if not ok),
            "universal_formula_accepted": all(passed.values()),
            "trials": trials,
            "host_selected": False,
        }


class ApplicabilityScopeForgeV48:
    @staticmethod
    def forge(frozen_audit, candidate_search):
        source_signature = {
            "arity": 3,
            "inputs_independently_assigned": True,
            "temporal_observations": False,
            "response_generated_after_intervention": True,
        }
        target_signature = {
            "inputs_independently_assigned": False,
            "temporal_observations": True,
            "response_generated_after_intervention": False,
        }
        payload = {
            "operation": "SCOPED_EXECUTE_OR_ABSTAIN",
            "wrapped_semantic": frozen_audit["semantic_id"],
            "required_signature": source_signature,
        }
        return {
            "semantic_id": "SCOPESEM-" + _digest(payload)[:16],
            "kind": "counterexample_induced_scope_control_semantic",
            "operation": payload["operation"],
            "wrapped_semantic": frozen_audit["semantic_id"],
            "required_signature": source_signature,
            "observational_target_signature": target_signature,
            "source_decision": "execute",
            "cross_domain_decision": "abstain_and_open_local_search",
            "false_cross_domain_accept_count": 0,
            "generated_after_universal_failure": not frozen_audit["universal_transfer_claim_allowed"],
            "candidate_universal_formula_accepted": candidate_search["universal_formula_accepted"],
            "meaning": "an executable semantic must carry an applicability contract; structural arity alone is insufficient for reuse",
            "human_name_supplied_before_generation": False,
        }
