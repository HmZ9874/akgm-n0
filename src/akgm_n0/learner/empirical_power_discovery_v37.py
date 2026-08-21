"""Anonymous robust power-law competition over measured rows."""
from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class EmpiricalRowV37:
    row_id: str
    q0: float
    q1: float
    target: float | None
    sigma_q0: float | None = None
    sigma_q1: float | None = None
    sigma_target: float | None = None

    @classmethod
    def from_dict(cls, payload):
        return cls(
            payload["row_id"], float(payload["q0"]), float(payload["q1"]),
            None if payload.get("target") is None else float(payload["target"]),
            payload.get("sigma_q0"), payload.get("sigma_q1"), payload.get("sigma_target"),
        )


@dataclass(frozen=True, slots=True)
class PowerProgramV37:
    alpha_twice: int
    beta_twice: int
    scale: float
    robust_score: float
    median_absolute_log_error: float

    @property
    def alpha(self):
        return self.alpha_twice / 2

    @property
    def beta(self):
        return self.beta_twice / 2

    @property
    def program_id(self):
        payload = (self.alpha_twice, self.beta_twice, round(self.scale, 12))
        return "EMP-" + hashlib.sha256(json.dumps(payload).encode()).hexdigest()[:16]

    def predict(self, row: EmpiricalRowV37):
        return self.scale * row.q0**self.alpha * row.q1**self.beta

    @staticmethod
    def _power(slot: str, twice: int):
        if twice == 0:
            return None
        sign = "TURN_EXP" if twice < 0 else "KEEP_EXP"
        numerator = abs(twice)
        exponent = str(numerator // 2) if numerator % 2 == 0 else f"{numerator}/2"
        return f"{sign}<{slot}^{exponent}>"

    def render(self):
        atoms = [f"SCALE<{self.scale:.8g}>", self._power("Q0", self.alpha_twice), self._power("Q1", self.beta_twice)]
        return "POWER<" + ";".join(atom for atom in atoms if atom is not None) + ">"

    def to_dict(self):
        return {
            "program_id": self.program_id,
            "opaque_program": self.render(),
            "alpha_twice": self.alpha_twice,
            "beta_twice": self.beta_twice,
            "fitted_scale": self.scale,
            "robust_score": self.robust_score,
            "median_absolute_log_error": self.median_absolute_log_error,
            "human_law_name": None,
        }


@dataclass(frozen=True, slots=True)
class EmpiricalDiscoveryV37:
    candidate_count: int
    selected: PowerProgramV37
    runner_up: PowerProgramV37
    bootstrap_selected_pairs: tuple[tuple[int, int], ...]
    missing_uncertainty_rows: int

    def to_dict(self):
        pair = (self.selected.alpha_twice, self.selected.beta_twice)
        return {
            "candidate_count": self.candidate_count,
            "selected_program": self.selected.to_dict(),
            "runner_up": self.runner_up.to_dict(),
            "score_margin": self.runner_up.robust_score - self.selected.robust_score,
            "bootstrap_runs": len(self.bootstrap_selected_pairs),
            "bootstrap_selection_rate": sum(item == pair for item in self.bootstrap_selected_pairs) / len(self.bootstrap_selected_pairs),
            "bootstrap_selected_pairs": [list(item) for item in self.bootstrap_selected_pairs],
            "missing_uncertainty_rows": self.missing_uncertainty_rows,
            "formula_name_supplied": False,
        }


class RobustPowerLawResearchV37:
    EXPONENTS_TWICE = tuple(range(-4, 5))

    @staticmethod
    def _fractional(value, sigma):
        return 0.0 if sigma is None or value == 0 else abs(float(sigma) / value)

    def _fit(self, rows: Sequence[EmpiricalRowV37], alpha_twice: int, beta_twice: int):
        alpha, beta = alpha_twice / 2, beta_twice / 2
        offsets = [math.log(row.target) - alpha * math.log(row.q0) - beta * math.log(row.q1) for row in rows if row.target is not None]
        log_scale = statistics.median(offsets)
        residuals, normalized = [], []
        for row in rows:
            if row.target is None:
                continue
            residual = abs(math.log(row.target) - (log_scale + alpha * math.log(row.q0) + beta * math.log(row.q1)))
            sigma = math.sqrt(
                self._fractional(row.target, row.sigma_target) ** 2
                + (alpha * self._fractional(row.q0, row.sigma_q0)) ** 2
                + (beta * self._fractional(row.q1, row.sigma_q1)) ** 2
                + 0.03**2
            )
            residuals.append(residual)
            normalized.append(residual / sigma)
        return PowerProgramV37(alpha_twice, beta_twice, math.exp(log_scale), statistics.median(normalized), statistics.median(residuals))

    def _rank(self, rows):
        candidates = [self._fit(rows, alpha, beta) for alpha in self.EXPONENTS_TWICE for beta in self.EXPONENTS_TWICE]
        return sorted(candidates, key=lambda item: (item.robust_score, abs(item.alpha_twice) + abs(item.beta_twice), item.alpha_twice, item.beta_twice))

    def discover(self, rows: Sequence[EmpiricalRowV37]):
        if len(rows) < 20 or any(row.target is None or min(row.q0, row.q1, row.target) <= 0 for row in rows):
            raise ValueError("at least twenty positive measured rows are required")
        ranked = self._rank(rows)
        bootstraps = []
        ordered = sorted(rows, key=lambda row: row.row_id)
        for offset in range(12):
            subset = tuple(row for index, row in enumerate(ordered) if (index + offset) % 4 != 0)
            winner = self._rank(subset)[0]
            bootstraps.append((winner.alpha_twice, winner.beta_twice))
        missing = sum(row.sigma_q0 is None or row.sigma_q1 is None or row.sigma_target is None for row in rows)
        return EmpiricalDiscoveryV37(81, ranked[0], ranked[1], tuple(bootstraps), missing)


def prediction_commitment(program: PowerProgramV37, rows: Sequence[EmpiricalRowV37]):
    predictions = {row.row_id: program.predict(row) for row in rows}
    payload = {"program_id": program.program_id, "predictions": predictions}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return digest, predictions
