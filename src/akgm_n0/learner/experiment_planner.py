"""Choose numeric experiments that maximally separate executable hypotheses."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from .relations import RelationExecutor, RelationNode, relation_key


@dataclass(frozen=True, slots=True)
class ExperimentActionScore:
    action: float
    information_gain_bits: float
    action_cost: float
    utility: float
    prediction_groups: tuple[tuple[float, tuple[str, ...]], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "information_gain_bits": self.information_gain_bits,
            "action_cost": self.action_cost,
            "utility": self.utility,
            "prediction_groups": [
                {"predicted_value": value, "candidate_ids": list(candidate_ids)}
                for value, candidate_ids in self.prediction_groups
            ],
        }


@dataclass(frozen=True, slots=True)
class ExperimentPlan:
    selected: ExperimentActionScore
    ranked_actions: tuple[ExperimentActionScore, ...]
    hypothesis_count: int
    excluded_observed_actions: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected": self.selected.to_dict(),
            "ranked_actions": [item.to_dict() for item in self.ranked_actions],
            "hypothesis_count": self.hypothesis_count,
            "excluded_observed_actions": list(self.excluded_observed_actions),
        }


@dataclass(frozen=True, slots=True)
class HypothesisUpdate:
    action: float
    observed_value: float
    retained_candidate_ids: tuple[str, ...]
    rejected_candidate_ids: tuple[str, ...]
    predictions: tuple[tuple[str, float, float], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "observed_value": self.observed_value,
            "retained_candidate_ids": list(self.retained_candidate_ids),
            "rejected_candidate_ids": list(self.rejected_candidate_ids),
            "predictions": [
                {
                    "candidate_id": candidate_id,
                    "predicted_value": predicted,
                    "absolute_error": error,
                }
                for candidate_id, predicted, error in self.predictions
            ],
        }


class NumericExperimentPlanner:
    """Use deterministic prediction partitions as a finite information score."""

    def __init__(
        self,
        *,
        executor: RelationExecutor | None = None,
        prediction_tolerance: float = 1e-9,
        action_cost: Callable[[float], float] | None = None,
    ) -> None:
        if not math.isfinite(prediction_tolerance) or prediction_tolerance <= 0:
            raise ValueError("prediction_tolerance must be finite and positive")
        self.executor = executor or RelationExecutor()
        self.prediction_tolerance = prediction_tolerance
        self.action_cost = action_cost or (lambda _action: 1.0)

    @staticmethod
    def candidate_id(program: RelationNode) -> str:
        key = relation_key(program)
        return "H-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def choose(
        self,
        hypotheses: Sequence[RelationNode],
        action_candidates: Sequence[float],
        *,
        observed_actions: Sequence[float] = (),
    ) -> ExperimentPlan:
        unique_hypotheses = {
            relation_key(program): program for program in hypotheses
        }
        if len(unique_hypotheses) < 2:
            raise ValueError("planning requires at least two distinct hypotheses")
        observed = {float(value) for value in observed_actions}
        actions = sorted(
            {
                float(value)
                for value in action_candidates
                if math.isfinite(float(value)) and float(value) not in observed
            }
        )
        if not actions:
            raise ValueError("no unobserved finite experiment actions remain")
        programs = tuple(unique_hypotheses[key] for key in sorted(unique_hypotheses))
        scores = tuple(self._score_action(programs, action) for action in actions)
        ranked = tuple(
            sorted(
                scores,
                key=lambda item: (
                    -item.utility,
                    -item.information_gain_bits,
                    item.action_cost,
                    abs(item.action),
                    item.action,
                ),
            )
        )
        return ExperimentPlan(
            selected=ranked[0],
            ranked_actions=ranked,
            hypothesis_count=len(programs),
            excluded_observed_actions=tuple(sorted(observed)),
        )

    def update(
        self,
        hypotheses: Sequence[RelationNode],
        *,
        action: float,
        observed_value: float,
    ) -> HypothesisUpdate:
        numeric_action = float(action)
        numeric_observed = float(observed_value)
        if not math.isfinite(numeric_action) or not math.isfinite(numeric_observed):
            raise ValueError("experiment evidence must be finite")
        predictions = []
        retained = []
        rejected = []
        for program in sorted(hypotheses, key=relation_key):
            candidate_id = self.candidate_id(program)
            predicted = self.executor.evaluate(program, numeric_action)
            error = abs(predicted - numeric_observed)
            predictions.append((candidate_id, predicted, error))
            if error <= self.prediction_tolerance:
                retained.append(candidate_id)
            else:
                rejected.append(candidate_id)
        return HypothesisUpdate(
            action=numeric_action,
            observed_value=numeric_observed,
            retained_candidate_ids=tuple(retained),
            rejected_candidate_ids=tuple(rejected),
            predictions=tuple(predictions),
        )

    def _score_action(
        self, programs: tuple[RelationNode, ...], action: float
    ) -> ExperimentActionScore:
        grouped: dict[float, list[str]] = {}
        for program in programs:
            prediction = self.executor.evaluate(program, action)
            quantized = round(prediction / self.prediction_tolerance) * self.prediction_tolerance
            grouped.setdefault(quantized, []).append(self.candidate_id(program))
        count = len(programs)
        information = -sum(
            (len(candidate_ids) / count) * math.log2(len(candidate_ids) / count)
            for candidate_ids in grouped.values()
        )
        cost = float(self.action_cost(action))
        if not math.isfinite(cost) or cost <= 0:
            raise ValueError("action cost must be finite and positive")
        groups = tuple(
            (value, tuple(sorted(candidate_ids)))
            for value, candidate_ids in sorted(grouped.items())
        )
        return ExperimentActionScore(
            action=action,
            information_gain_bits=information,
            action_cost=cost,
            utility=information / cost,
            prediction_groups=groups,
        )
