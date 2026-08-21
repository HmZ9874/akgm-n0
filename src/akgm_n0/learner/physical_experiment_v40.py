"""Domain-blind planning and local-memory semantics for V40 physical data."""
from __future__ import annotations

import hashlib
import json
import statistics
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PhysicalObservationV40:
    level: int
    response: float
    dispersion: float
    raw_digest: str

    @classmethod
    def from_result(cls, payload):
        return cls(int(payload["anonymous_level"]), float(payload["response"]), float(payload["dispersion"]), str(payload["raw_digest"]))

    def to_dict(self):
        return {
            "anonymous_control": self.level,
            "anonymous_response": self.response,
            "dispersion": self.dispersion,
            "raw_digest": self.raw_digest,
            "human_quantity_names": None,
        }


@dataclass(frozen=True, slots=True)
class LocalMemorySemanticV40:
    knots: tuple[tuple[int, float], ...]
    cross_validation_error: float

    def predict(self, level: int):
        ordered = self.knots
        if level <= ordered[0][0]:
            return ordered[0][1]
        if level >= ordered[-1][0]:
            return ordered[-1][1]
        for (left_x, left_y), (right_x, right_y) in zip(ordered, ordered[1:]):
            if left_x <= level <= right_x:
                fraction = (level - left_x) / (right_x - left_x)
                return left_y + fraction * (right_y - left_y)
        raise RuntimeError("unreachable local-memory interval")

    @property
    def semantic_id(self):
        return "PHYS-SEM-" + hashlib.sha256(json.dumps(self.knots).encode()).hexdigest()[:16]

    def render(self):
        encoded = ";".join(f"{x}:{y:.8g}" for x, y in self.knots)
        return f"LOCAL_MEMORY<{encoded}>::NEAREST_DELTA_BLEND"

    def to_dict(self):
        return {
            "semantic_id": self.semantic_id,
            "opaque_program": self.render(),
            "knot_count": len(self.knots),
            "cross_validation_error": self.cross_validation_error,
            "human_law_name": None,
            "domain_formula_supplied": False,
        }


class DomainBlindPhysicalResearchV40:
    @staticmethod
    def _fit(rows, excluded_level=None):
        knots = tuple(sorted((row.level, row.response) for row in rows if row.level != excluded_level))
        return LocalMemorySemanticV40(knots, 0.0)

    def discover(self, rows):
        errors = []
        for row in rows:
            remaining = [item for item in rows if item.level != row.level]
            if len(remaining) >= 2:
                prediction = self._fit(remaining).predict(row.level)
                errors.append(abs(prediction - row.response))
        error = statistics.median(errors) if errors else 0.0
        knots = tuple(sorted((row.level, row.response) for row in rows))
        return LocalMemorySemanticV40(knots, error)

    def plan(self, rows, available_levels, reserved_levels, round_index):
        available = sorted(set(available_levels) - set(reserved_levels) - {row.level for row in rows})
        if not rows:
            return {"round_index": round_index, "selected_levels": [0, 3, 7], "reason": "boundary_and_center_initialization", "maximum_gap_score": 0.0}
        ordered = sorted(rows, key=lambda row: row.level)
        candidates = []
        for left, right in zip(ordered, ordered[1:]):
            interior = [level for level in available if left.level < level < right.level]
            if not interior:
                continue
            midpoint = (left.level + right.level) / 2
            chosen = min(interior, key=lambda level: abs(level - midpoint))
            gap = right.level - left.level
            score = gap * (abs(right.response - left.response) + 0.02)
            candidates.append((score, -abs(chosen - midpoint), chosen))
        if not candidates:
            chosen = available[len(available) // 2]
            score = 0.0
        else:
            score, _, chosen = max(candidates)
        return {"round_index": round_index, "selected_levels": [chosen], "reason": "largest_response_weighted_knowledge_gap", "maximum_gap_score": score}


def physical_prediction_commitment_v40(program, level):
    prediction = program.predict(level)
    payload = {"semantic_id": program.semantic_id, "anonymous_level": level, "prediction": prediction}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return digest, prediction
