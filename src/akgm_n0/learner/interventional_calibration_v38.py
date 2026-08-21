"""Anonymous intervention-direction and polynomial mechanism discovery."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class InterventionRowV38:
    row_id: str
    q0: float
    target: float | None
    unseen_intervention_level: bool = False

    @classmethod
    def from_dict(cls, payload):
        return cls(payload["row_id"], float(payload["q0"]), None if payload.get("target") is None else float(payload["target"]), bool(payload.get("unseen_intervention_level", False)))


def _solve(matrix, vector):
    work = [list(row) + [value] for row, value in zip(matrix, vector, strict=True)]
    size = len(vector)
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(work[row][column]))
        if abs(work[pivot][column]) < 1e-15:
            raise ValueError("singular polynomial system")
        work[column], work[pivot] = work[pivot], work[column]
        scale = work[column][column]
        work[column] = [value / scale for value in work[column]]
        for row in range(size):
            if row == column:
                continue
            factor = work[row][column]
            work[row] = [left - factor * right for left, right in zip(work[row], work[column], strict=True)]
    return tuple(work[index][-1] for index in range(size))


@dataclass(frozen=True, slots=True)
class PolynomialMechanismV38:
    direction: str
    degree: int
    coefficients: tuple[float, ...]
    bic: float
    normalized_sse: float

    def predict_value(self, value):
        return sum(coefficient * value**power for power, coefficient in enumerate(self.coefficients))

    def predict(self, row: InterventionRowV38):
        return self.predict_value(row.q0)

    @property
    def program_id(self):
        payload = (self.direction, self.degree, tuple(round(value, 12) for value in self.coefficients))
        return "CAU-" + hashlib.sha256(json.dumps(payload).encode()).hexdigest()[:16]

    def render(self):
        terms = [f"C{power}<{coefficient:.9g}>*Q0^{power}" for power, coefficient in enumerate(self.coefficients)]
        return f"MECHANISM<{self.direction};" + ";".join(terms) + ">"

    def to_dict(self):
        return {
            "program_id": self.program_id,
            "direction": self.direction,
            "degree": self.degree,
            "coefficients": list(self.coefficients),
            "bic": self.bic,
            "normalized_sse": self.normalized_sse,
            "opaque_program": self.render(),
            "human_mechanism_name": None,
        }


@dataclass(frozen=True, slots=True)
class InterventionalDiscoveryV38:
    selected: PolynomialMechanismV38
    forward_candidates: tuple[PolynomialMechanismV38, ...]
    reverse_candidates: tuple[PolynomialMechanismV38, ...]
    controlled_slot: str
    response_slot: str

    def to_dict(self):
        ranked = sorted(self.forward_candidates, key=lambda item: item.bic)
        return {
            "graph_candidates": ["Q0_TO_Q1", "Q1_TO_Q0", "NO_LINK"],
            "polynomial_degrees_per_direction": len(self.forward_candidates),
            "candidate_count": len(self.forward_candidates) + len(self.reverse_candidates) + 1,
            "selected_mechanism": self.selected.to_dict(),
            "forward_runner_up": ranked[1].to_dict(),
            "bic_margin": ranked[1].bic - ranked[0].bic,
            "controlled_slot": self.controlled_slot,
            "response_slot": self.response_slot,
            "direction_selected_from_intervention_role": True,
            "formula_name_supplied": False,
        }


class InterventionalMechanismResearchV38:
    DEGREES = tuple(range(6))

    @staticmethod
    def _fit(x_values, y_values, direction, degree):
        size = degree + 1
        matrix = [[sum(x ** (row + column) for x in x_values) for column in range(size)] for row in range(size)]
        vector = [sum(y * x**power for x, y in zip(x_values, y_values, strict=True)) for power in range(size)]
        coefficients = _solve(matrix, vector)
        predictions = [sum(coefficient * x**power for power, coefficient in enumerate(coefficients)) for x in x_values]
        sse = sum((y - prediction) ** 2 for y, prediction in zip(y_values, predictions, strict=True))
        mean = sum(y_values) / len(y_values)
        tss = sum((y - mean) ** 2 for y in y_values)
        normalized = sse / tss if tss else float("inf")
        bic = len(y_values) * math.log(max(sse / len(y_values), 1e-30)) + size * math.log(len(y_values))
        return PolynomialMechanismV38(direction, degree, coefficients, bic, normalized)

    def discover(self, rows: Sequence[InterventionRowV38], *, controlled_slot: str, response_slot: str):
        if controlled_slot != "Q0" or response_slot != "Q1":
            raise ValueError("V38 accepts only anonymous Q0 intervention and Q1 response roles")
        x_values = [row.q0 for row in rows]
        y_values = [row.target for row in rows]
        if len(rows) < 8 or any(value is None for value in y_values):
            raise ValueError("at least eight labeled intervention rows are required")
        y_values = [float(value) for value in y_values]
        forward = tuple(self._fit(x_values, y_values, "Q0_TO_Q1", degree) for degree in self.DEGREES)
        reverse = tuple(self._fit(y_values, x_values, "Q1_TO_Q0", degree) for degree in self.DEGREES)
        selected = min(forward, key=lambda item: item.bic)
        return InterventionalDiscoveryV38(selected, forward, reverse, controlled_slot, response_slot)


def prediction_commitment_v38(program: PolynomialMechanismV38, rows: Sequence[InterventionRowV38]):
    predictions = {row.row_id: program.predict(row) for row in rows}
    payload = {"program_id": program.program_id, "predictions": predictions}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return digest, predictions
