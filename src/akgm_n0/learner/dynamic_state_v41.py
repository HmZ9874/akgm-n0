"""Domain-blind recurrent semantic synthesis for anonymous physical trajectories."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class AnonymousTraceV41:
    trace_id: str
    samples: tuple[dict[str, float], ...]

    @classmethod
    def from_dict(cls, payload):
        return cls(str(payload["trace_id"]), tuple({key: float(value) if key != "sequence_index" else int(value) for key, value in row.items()} for row in payload["samples"]))


@dataclass(frozen=True, slots=True)
class DynamicProgramV41:
    kind: str
    coefficients: tuple[float, ...]
    validation_rmse: float
    validation_mape: float
    node_count: int

    @property
    def program_id(self):
        payload = (self.kind, tuple(round(value, 12) for value in self.coefficients))
        return "DYN-" + hashlib.sha256(json.dumps(payload).encode()).hexdigest()[:16]

    def step(self, state, sample, previous_time):
        if self.kind == "persistence":
            return state
        if self.kind == "stateless":
            features = np.array([1.0, sample["q0"], sample["q2"], sample["q3"]])
        elif self.kind == "state_fold":
            dt = sample["q3"] - previous_time
            features = np.array([1.0, state, sample["q0"], sample["q2"], dt, sample["q3"]])
        else:
            raise ValueError(self.kind)
        return float(features @ np.asarray(self.coefficients))

    def rollout(self, trace: AnonymousTraceV41):
        state = trace.samples[0]["q1"]
        predictions = [state]
        previous_time = trace.samples[0]["q3"]
        for sample in trace.samples[1:]:
            state = self.step(state, sample, previous_time)
            predictions.append(state)
            previous_time = sample["q3"]
        return predictions

    def render(self):
        if self.kind == "state_fold":
            weights = ";".join(f"W{i}={value:.9g}" for i, value in enumerate(self.coefficients))
            return f"STATE_FOLD<S0=Q1;STEP<{weights}>;MEMORY=PREVIOUS_STATE>"
        return f"{self.kind.upper()}<{','.join(f'{value:.9g}' for value in self.coefficients)}>"

    def to_dict(self):
        return {
            "program_id": self.program_id,
            "kind": self.kind,
            "opaque_program": self.render(),
            "coefficients": list(self.coefficients),
            "validation_rmse": self.validation_rmse,
            "validation_mape": self.validation_mape,
            "node_count": self.node_count,
            "created_operator": "STATE_FOLD" if self.kind == "state_fold" else None,
            "human_law_name": None,
            "domain_formula_supplied": False,
        }


class DynamicStateResearchV41:
    @staticmethod
    def _fit_coefficients(traces, kind):
        features = []
        targets = []
        for trace in traces:
            for previous, sample in zip(trace.samples, trace.samples[1:]):
                if kind == "stateless":
                    features.append([1.0, sample["q0"], sample["q2"], sample["q3"]])
                else:
                    dt = sample["q3"] - previous["q3"]
                    features.append([1.0, previous["q1"], sample["q0"], sample["q2"], dt, sample["q3"]])
                targets.append(sample["q1"])
        coefficients, *_ = np.linalg.lstsq(np.asarray(features), np.asarray(targets), rcond=None)
        return tuple(float(value) for value in coefficients)

    @staticmethod
    def evaluate(program, traces):
        errors = []
        percentages = []
        cases = []
        for trace in traces:
            predictions = program.rollout(trace)
            trace_errors = []
            for sample, predicted in zip(trace.samples[1:], predictions[1:]):
                error = predicted - sample["q1"]
                errors.append(error)
                trace_errors.append(error)
                percentages.append(abs(error) / max(abs(sample["q1"]), 1e-9))
            cases.append({
                "trace_id": trace.trace_id,
                "point_count": len(trace.samples) - 1,
                "trajectory_rmse": math.sqrt(sum(value * value for value in trace_errors) / len(trace_errors)),
                "final_predicted": predictions[-1],
                "final_observed": trace.samples[-1]["q1"],
            })
        return {
            "trace_count": len(traces),
            "point_count": len(errors),
            "rmse": math.sqrt(sum(value * value for value in errors) / len(errors)),
            "median_absolute_percentage_error": float(np.median(percentages)),
            "cases": cases,
        }

    def discover(self, training, validation):
        candidates = []
        for kind, node_count in (("persistence", 1), ("stateless", 7), ("state_fold", 11)):
            coefficients = () if kind == "persistence" else self._fit_coefficients(training, kind)
            draft = DynamicProgramV41(kind, coefficients, float("inf"), float("inf"), node_count)
            audit = self.evaluate(draft, validation)
            candidates.append(DynamicProgramV41(kind, coefficients, audit["rmse"], audit["median_absolute_percentage_error"], node_count))
        selected = min(candidates, key=lambda item: item.validation_rmse + item.node_count * 1e-5)
        return selected, tuple(candidates)


def dynamic_program_commitment_v41(program: DynamicProgramV41):
    payload = {"program_id": program.program_id, "opaque_program": program.render(), "coefficients": list(program.coefficients)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
