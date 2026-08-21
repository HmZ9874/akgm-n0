"""Adaptive scale-law planning for measurements created by a live apparatus."""
from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class LiveMeasurementV39:
    level: int
    response: float
    mad: float
    round_index: int

    @classmethod
    def from_result(cls, payload, round_index):
        return cls(int(payload["level"]), float(payload["response_ns_per_cycle"]), float(payload["mad_ns_per_cycle"]), round_index)

    def to_dict(self):
        return {"anonymous_level": self.level, "response": self.response, "mad": self.mad, "round_index": self.round_index, "human_quantity_names": None}


@dataclass(frozen=True, slots=True)
class ScaleProgramV39:
    exponent_quarters: int
    scale: float
    robust_score: float

    @property
    def exponent(self):
        return self.exponent_quarters / 4

    def predict(self, level):
        return self.scale * level**self.exponent

    @property
    def program_id(self):
        payload = (self.exponent_quarters, round(self.scale, 12))
        return "LIVE-" + hashlib.sha256(json.dumps(payload).encode()).hexdigest()[:16]

    def render(self):
        return f"LIVE_POWER<SCALE<{self.scale:.9g}>;Q0^{self.exponent_quarters}/4>"

    def to_dict(self):
        return {"program_id": self.program_id, "opaque_program": self.render(), "exponent_quarters": self.exponent_quarters, "fitted_scale": self.scale, "robust_score": self.robust_score, "human_law_name": None}


@dataclass(frozen=True, slots=True)
class AdaptivePlanV39:
    round_index: int
    selected_levels: tuple[int, ...]
    candidate_count: int
    maximum_log_prediction_spread: float

    def to_dict(self):
        return {"round_index": self.round_index, "selected_anonymous_levels": list(self.selected_levels), "candidate_count": self.candidate_count, "maximum_log_prediction_spread": self.maximum_log_prediction_spread}


class LiveScaleResearchV39:
    EXPONENT_QUARTERS = tuple(range(4, 13))

    @staticmethod
    def _fit_for_exponent(rows: Sequence[LiveMeasurementV39], exponent_quarters: int):
        exponent = exponent_quarters / 4
        offsets = [math.log(row.response) - exponent * math.log(row.level) for row in rows]
        log_scale = statistics.median(offsets)
        residuals = []
        for row in rows:
            residual = abs(math.log(row.response) - (log_scale + exponent * math.log(row.level)))
            noise = max(row.mad / row.response, 0.015)
            residuals.append(residual / noise)
        return ScaleProgramV39(exponent_quarters, math.exp(log_scale), statistics.median(residuals))

    def fit_candidates(self, rows: Sequence[LiveMeasurementV39]):
        if len(rows) < 2:
            return tuple(ScaleProgramV39(value, 1.0, float("inf")) for value in self.EXPONENT_QUARTERS)
        return tuple(self._fit_for_exponent(rows, value) for value in self.EXPONENT_QUARTERS)

    def select(self, rows: Sequence[LiveMeasurementV39]):
        return min(self.fit_candidates(rows), key=lambda item: (item.robust_score, abs(item.exponent_quarters - 8)))

    def plan(self, rows: Sequence[LiveMeasurementV39], available_levels: Sequence[int], *, round_index: int, batch_size: int):
        available = tuple(sorted(set(available_levels) - {row.level for row in rows}))
        if not rows:
            seeds = tuple(available[index] for index in (1, len(available) // 2, len(available) - 2))
            return AdaptivePlanV39(round_index, seeds[:batch_size], len(self.EXPONENT_QUARTERS), 0.0)
        candidates = self.fit_candidates(rows)
        scored = []
        for level in available:
            logs = [math.log(candidate.predict(level)) for candidate in candidates]
            spread = max(logs) - min(logs)
            scored.append((spread, -abs(level - statistics.median(available)), level))
        scored.sort(reverse=True)
        chosen = tuple(item[2] for item in scored[:batch_size])
        return AdaptivePlanV39(round_index, chosen, len(candidates), scored[0][0])


def batch_commitment_v39(batch_id, order, seed_commitment):
    payload = {"batch_id": batch_id, "order": list(order), "seed_commitment": seed_commitment}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def prediction_commitment_v39(program: ScaleProgramV39, level: int):
    prediction = program.predict(level)
    payload = {"program_id": program.program_id, "level": level, "prediction": prediction}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), prediction
