"""Breakthrough-grade representation and mechanism research primitives.

V51 does not award scientific novelty.  It strengthens two reusable learner
components: exhaustive competition between anonymous intervention mechanisms,
and behavioral macro creation from the winning executable mechanism.  Claims
are scored later by an evaluator-owned ten-gate evidence contract.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass

import numpy as np

from akgm_n0.learner.autonomous_intervention_v45 import (
    _feature_value,
    structural_feature_pool_v45,
)


def _digest(payload) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class MechanismCandidateV51:
    features: tuple[str, ...]
    coefficients: tuple[float, ...]
    loo_rmse: float
    score: float
    behavior_signature: tuple[float, ...]

    @property
    def mechanism_id(self) -> str:
        payload = {
            "features": self.features,
            "coefficients": tuple(round(value, 10) for value in self.coefficients),
        }
        return "MECH51-" + _digest(payload)[:16]

    def predict(self, values) -> float:
        return sum(
            coefficient * _feature_value(feature, values)
            for coefficient, feature in zip(self.coefficients, self.features, strict=True)
        )

    def to_dict(self):
        return {
            "mechanism_id": self.mechanism_id,
            "features": list(self.features),
            "coefficients": list(self.coefficients),
            "loo_rmse": self.loo_rmse,
            "score": self.score,
            "behavior_signature_digest": _digest(self.behavior_signature),
            "human_formula_name": None,
        }


def _fit(features, rows):
    design = np.asarray([
        [_feature_value(feature, row["values"]) for feature in features]
        for row in rows
    ], dtype=float)
    target = np.asarray([row["response"] for row in rows], dtype=float)
    coefficients, *_ = np.linalg.lstsq(design, target, rcond=None)
    return tuple(float(value) for value in coefficients)


def _loo_rmse(features, rows):
    errors = []
    for holdout in range(len(rows)):
        development = [row for index, row in enumerate(rows) if index != holdout]
        coefficients = _fit(features, development)
        prediction = sum(
            coefficient * _feature_value(feature, rows[holdout]["values"])
            for coefficient, feature in zip(coefficients, features, strict=True)
        )
        errors.append(prediction - rows[holdout]["response"])
    return math.sqrt(sum(error * error for error in errors) / len(errors))


def _integer_grid(safe_ranges):
    axes = []
    for lower, upper in safe_ranges:
        start, stop = int(math.ceil(lower)), int(math.floor(upper))
        axes.append(tuple(float(value) for value in range(start, stop + 1)))
    return tuple(itertools.product(*axes))


class MechanismTournamentV51:
    """Enumerate, deduplicate, falsify, and rank anonymous causal programs."""

    def __init__(self, *, maximum_features=3, complexity_penalty=1e-4):
        self.maximum_features = maximum_features
        self.complexity_penalty = complexity_penalty

    def search(self, measurements, safe_ranges):
        rows = tuple({
            "values": tuple(map(float, row["action"]["values"])),
            "response": float(row["response"]),
        } for row in measurements)
        pool = structural_feature_pool_v45(len(safe_ranges))
        nonconstant = tuple(feature for feature in pool if feature != "ONE")
        probes = _integer_grid(safe_ranges)
        generated = []
        for size in range(self.maximum_features):
            for chosen in itertools.combinations(nonconstant, size):
                features = ("ONE", *chosen)
                coefficients = _fit(features, rows)
                loo = _loo_rmse(features, rows)
                scale = max(float(np.std([row["response"] for row in rows])), 1.0)
                signature = tuple(round(sum(
                    coefficient * _feature_value(feature, probe)
                    for coefficient, feature in zip(coefficients, features, strict=True)
                ), 9) for probe in probes)
                generated.append(MechanismCandidateV51(
                    features,
                    coefficients,
                    loo,
                    loo / scale + self.complexity_penalty * len(features),
                    signature,
                ))
        by_behavior = {}
        for candidate in generated:
            current = by_behavior.get(candidate.behavior_signature)
            key = (candidate.score, len(candidate.features), candidate.features)
            if current is None or key < (current.score, len(current.features), current.features):
                by_behavior[candidate.behavior_signature] = candidate
        ranked = sorted(
            by_behavior.values(),
            key=lambda item: (item.score, len(item.features), item.features),
        )
        selected = ranked[0]
        return {
            "selected": selected,
            "ranked": tuple(ranked),
            "programs_generated": len(generated),
            "behavior_classes": len(by_behavior),
            "probe_count": len(probes),
            "host_selected": False,
            "domain_labels_received": False,
        }

    @staticmethod
    def propose_discriminating_intervention(ranked, safe_ranges, observed_actions, top_k=12):
        contenders = tuple(ranked[:top_k])
        observed = {tuple(map(float, values)) for values in observed_actions}
        choices = []
        for action in _integer_grid(safe_ranges):
            if action in observed:
                continue
            predictions = np.asarray([candidate.predict(action) for candidate in contenders])
            disagreement = float(np.std(predictions))
            choices.append((disagreement, action, tuple(float(value) for value in predictions)))
        if not choices:
            return None
        disagreement, action, predictions = max(choices, key=lambda item: (item[0], item[1]))
        return {
            "action": list(action),
            "prediction_disagreement": disagreement,
            "contender_predictions": list(predictions),
            "contender_ids": [candidate.mechanism_id for candidate in contenders],
            "selected_by": "maximum_competing_mechanism_disagreement",
            "host_selected": False,
        }


class BehavioralRepresentationForgeV51:
    """Compress a learned multi-feature behavior into a verified opcode."""

    @staticmethod
    def forge(candidate, safe_ranges):
        active = tuple(
            (feature, coefficient)
            for feature, coefficient in zip(candidate.features, candidate.coefficients, strict=True)
            if abs(coefficient) > 1e-10
        )
        expansion = {
            "terms": [
                {"feature": feature, "coefficient": coefficient}
                for feature, coefficient in active
            ]
        }
        representation_id = "REP51-" + _digest(expansion)[:16]
        probes = _integer_grid(safe_ranges)
        expansion_values = tuple(sum(
            coefficient * _feature_value(feature, values)
            for feature, coefficient in active
        ) for values in probes)
        macro_values = tuple(candidate.predict(values) for values in probes)
        maximum_error = max(abs(left - right) for left, right in zip(
            expansion_values, macro_values, strict=True,
        ))
        dependencies = sorted({
            int(token)
            for feature, _ in active
            for token in feature.replace("(", ",").replace(")", "").split(",")
            if token.isdigit()
        })
        primitive_tokens = 2 * len(active) + max(0, len(active) - 1)
        return {
            "representation_id": representation_id,
            "kind": "learned_behavioral_opcode",
            "arity": len(safe_ranges),
            "expansion": expansion,
            "source_mechanism_id": candidate.mechanism_id,
            "dependency_slots": dependencies,
            "probe_count": len(probes),
            "maximum_expansion_error": maximum_error,
            "behaviorally_equivalent_on_registered_domain": maximum_error < 1e-9,
            "primitive_token_cost": primitive_tokens,
            "macro_token_cost": 1,
            "token_savings_per_call": primitive_tokens - 1,
            "human_name_supplied": False,
            "native_code_generated": False,
            "sandboxed_expansion_only": True,
        }

    @staticmethod
    def execute(representation, values):
        return sum(
            float(term["coefficient"]) * _feature_value(term["feature"], values)
            for term in representation["expansion"]["terms"]
        )


def sealed_audit(candidate, cases):
    errors = []
    for case in cases:
        values = tuple(map(float, case["action"]["values"]))
        errors.append(candidate.predict(values) - float(case["observed"]))
    return {
        "case_count": len(errors),
        "rmse": math.sqrt(sum(error * error for error in errors) / len(errors)),
        "maximum_absolute_error": max(abs(error) for error in errors),
    }


def ablation_audit(candidate, measurements, cases):
    rows = tuple({
        "values": tuple(map(float, row["action"]["values"])),
        "response": float(row["response"]),
    } for row in measurements)
    audits = []
    for removed in candidate.features:
        if removed == "ONE":
            continue
        features = tuple(feature for feature in candidate.features if feature != removed)
        coefficients = _fit(features, rows)
        errors = []
        for case in cases:
            values = tuple(map(float, case["action"]["values"]))
            predicted = sum(
                coefficient * _feature_value(feature, values)
                for coefficient, feature in zip(coefficients, features, strict=True)
            )
            errors.append(predicted - float(case["observed"]))
        audits.append({
            "removed_feature": removed,
            "sealed_rmse": math.sqrt(sum(error * error for error in errors) / len(errors)),
        })
    return tuple(audits)
