"""V45 bounded autonomous intervention design over anonymous controls.

The learner receives control ranges, an experiment budget, and observations.
It is not given the apparatus implementation, physical names, a target formula,
or a named mechanism family.  It grows an executable structural feature
language and chooses interventions by model disagreement, leverage, geometric
novelty, and action cost.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from itertools import combinations, permutations
from typing import Sequence

import numpy as np


@dataclass(frozen=True, slots=True)
class InterventionActionV45:
    values: tuple[float, ...]

    @property
    def action_id(self):
        return "ACT-" + hashlib.sha256(
            json.dumps(self.values, separators=(",", ":")).encode()
        ).hexdigest()[:16]

    def to_dict(self):
        return {"action_id": self.action_id, "values": list(self.values)}


@dataclass(frozen=True, slots=True)
class InterventionMeasurementV45:
    action: InterventionActionV45
    response: float
    round_index: int
    measurement_id: str

    def to_dict(self):
        return {
            "measurement_id": self.measurement_id,
            "action": self.action.to_dict(),
            "response": self.response,
            "round_index": self.round_index,
        }


def structural_feature_pool_v45(control_count):
    if control_count < 2:
        raise ValueError("V45 requires at least two intervention controls")
    atoms = [f"X{index}" for index in range(control_count)]
    pairs = [f"COUPLE({left},{right})" for left, right in combinations(range(control_count), 2)]
    triples = [
        "COUPLE(" + ",".join(map(str, indexes)) + ")"
        for indexes in combinations(range(control_count), 3)
    ]
    self_reductions = [f"SELF({index})" for index in range(control_count)]
    guards = [
        f"GUARD({left},{right},{payload})"
        for left, right in permutations(range(control_count), 2)
        for payload in range(control_count)
    ]
    return tuple(["ONE", *atoms, *pairs, *triples, *self_reductions, *guards])


def _feature_value(name, values):
    if name == "ONE":
        return 1.0
    if name.startswith("X") and name[1:].isdigit():
        return values[int(name[1:])]
    if name.startswith("SELF("):
        index = int(name[5:-1])
        return values[index] * values[index]
    if name.startswith("COUPLE("):
        indexes = tuple(map(int, name[7:-1].split(",")))
        result = 1.0
        for index in indexes:
            result *= values[index]
        return result
    if name.startswith("GUARD("):
        left, right, payload = map(int, name[6:-1].split(","))
        return (1.0 if values[left] > values[right] else 0.0) * values[payload]
    raise ValueError(f"unknown V45 structural feature: {name}")


@dataclass(frozen=True, slots=True)
class InterventionProgramV45:
    features: tuple[str, ...]
    coefficients: tuple[float, ...]
    cross_validated_rmse: float
    score: float

    @property
    def program_id(self):
        payload = {
            "features": self.features,
            "coefficients": tuple(round(value, 12) for value in self.coefficients),
        }
        return "CAUSEM-" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16]

    def predict(self, action: InterventionActionV45):
        return sum(
            coefficient * _feature_value(feature, action.values)
            for coefficient, feature in zip(self.coefficients, self.features, strict=True)
        )

    def render(self):
        return "INTERVENTION_UPDATE<" + ";".join(
            f"W{index}*{feature}" for index, feature in enumerate(self.features)
        ) + ">"

    def to_dict(self):
        return {
            "program_id": self.program_id,
            "features": list(self.features),
            "coefficients": list(self.coefficients),
            "cross_validated_rmse": self.cross_validated_rmse,
            "score": self.score,
            "opaque_program": self.render(),
            "human_formula_name": None,
            "named_mechanism_family_supplied": False,
        }


@dataclass(frozen=True, slots=True)
class ExperimentProposalV45:
    action: InterventionActionV45
    utility: float
    normalized_disagreement: float
    normalized_leverage: float
    geometric_novelty: float
    normalized_cost: float
    competing_program_ids: tuple[str, ...]

    def to_dict(self):
        return {
            "action": self.action.to_dict(),
            "utility": self.utility,
            "normalized_disagreement": self.normalized_disagreement,
            "normalized_leverage": self.normalized_leverage,
            "geometric_novelty": self.geometric_novelty,
            "normalized_cost": self.normalized_cost,
            "competing_program_ids": list(self.competing_program_ids),
            "host_selected": False,
        }


class AutonomousInterventionResearcherV45:
    def __init__(self, *, complexity_penalty=1e-4, minimum_gain=1e-4):
        self.complexity_penalty = complexity_penalty
        self.minimum_gain = minimum_gain

    @staticmethod
    def _design(measurements, features):
        return np.asarray([
            [_feature_value(feature, row.action.values) for feature in features]
            for row in measurements
        ], dtype=float)

    def compile(self, measurements, features):
        if not measurements:
            raise ValueError("cannot compile without intervention evidence")
        design = self._design(measurements, features)
        target = np.asarray([row.response for row in measurements], dtype=float)
        coefficients, *_ = np.linalg.lstsq(design, target, rcond=None)
        errors = []
        if len(measurements) > len(features) + 1:
            for holdout in range(len(measurements)):
                mask = np.arange(len(measurements)) != holdout
                trial, *_ = np.linalg.lstsq(design[mask], target[mask], rcond=None)
                errors.append(float(design[holdout] @ trial - target[holdout]))
        else:
            errors = list(design @ coefficients - target)
        rmse = math.sqrt(sum(value * value for value in errors) / len(errors))
        scale = max(float(np.std(target)), 1.0)
        score = rmse / scale + self.complexity_penalty * len(features)
        return InterventionProgramV45(
            tuple(features), tuple(float(value) for value in coefficients), rmse, score,
        )

    def grow_language(self, measurements, current):
        control_count = len(measurements[0].action.values)
        pool = structural_feature_pool_v45(control_count)
        candidates = []
        for feature in pool:
            if feature in current.features:
                continue
            trial = self.compile(measurements, (*current.features, feature))
            candidates.append((feature, trial))
        if not candidates:
            return {"selected": current, "mutation": None, "gain": 0.0, "trials": ()}
        feature, selected = min(candidates, key=lambda item: (item[1].score, item[0]))
        gain = current.score - selected.score
        accepted = math.isfinite(selected.score) and gain > self.minimum_gain
        return {
            "selected": selected if accepted else current,
            "mutation": f"admit_structural_feature:{feature}" if accepted else None,
            "gain": max(0.0, gain),
            "trials": tuple({
                "feature": trial_feature,
                "program_id": trial.program_id,
                "score": trial.score,
                "accepted": accepted and trial_feature == feature,
            } for trial_feature, trial in candidates),
        }

    @staticmethod
    def _normalized_vector(action, ranges):
        return np.asarray([
            (value - lower) / max(upper - lower, 1e-12)
            for value, (lower, upper) in zip(action.values, ranges, strict=True)
        ])

    def initial_plan(self, actions, ranges, *, batch_size):
        remaining = list(actions)
        selected = []
        while remaining and len(selected) < batch_size:
            def score(action):
                vector = self._normalized_vector(action, ranges)
                if not selected:
                    novelty = float(np.linalg.norm(vector - 0.5))
                else:
                    novelty = min(float(np.linalg.norm(
                        vector - self._normalized_vector(other, ranges)
                    )) for other in selected)
                cost = sum(vector) / len(vector)
                return novelty - 0.02 * cost
            chosen = max(remaining, key=lambda action: (score(action), action.action_id))
            selected.append(chosen)
            remaining.remove(chosen)
        return tuple(selected)

    def propose(self, measurements, current, actions, ranges):
        observed = {row.action.action_id for row in measurements}
        available = [action for action in actions if action.action_id not in observed]
        if not available:
            raise ValueError("no safe unobserved interventions remain")
        pool = structural_feature_pool_v45(len(ranges))
        competitors = [current]
        for feature in pool:
            if feature not in current.features:
                competitors.append(self.compile(measurements, (*current.features, feature)))
        design = self._design(measurements, current.features)
        information = np.linalg.pinv(design.T @ design)
        response_scale = max(float(np.std([row.response for row in measurements])), 1.0)
        proposals = []
        for action in available:
            predictions = np.asarray([program.predict(action) for program in competitors])
            disagreement = min(5.0, float(np.std(predictions)) / response_scale) / 5.0
            vector = np.asarray([_feature_value(feature, action.values) for feature in current.features])
            leverage = min(5.0, float(vector @ information @ vector)) / 5.0
            normalized = self._normalized_vector(action, ranges)
            novelty = min(float(np.linalg.norm(
                normalized - self._normalized_vector(row.action, ranges)
            )) for row in measurements) / math.sqrt(len(ranges))
            cost = sum(normalized) / len(normalized)
            utility = 0.55 * disagreement + 0.25 * leverage + 0.20 * novelty - 0.03 * cost
            proposals.append(ExperimentProposalV45(
                action, utility, disagreement, leverage, novelty, cost,
                tuple(program.program_id for program in competitors),
            ))
        return max(proposals, key=lambda item: (item.utility, item.action.action_id)), tuple(sorted(
            proposals, key=lambda item: (-item.utility, item.action.action_id),
        ))


def intervention_program_commitment_v45(program):
    payload = {
        "program_id": program.program_id,
        "features": program.features,
        "coefficients": tuple(round(value, 15) for value in program.coefficients),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
