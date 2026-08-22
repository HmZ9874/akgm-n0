"""Counterexample-guided, domain-blind transfer semantics for V42."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

import numpy as np

from akgm_n0.learner.dynamic_state_v41 import AnonymousTraceV41


@dataclass(frozen=True, slots=True)
class TransferProgramV42:
    """A frozen recurrent program assembled from anonymous numeric features."""

    kind: str
    coefficients: tuple[float, ...]
    validation_rmse: float
    validation_mape: float
    node_count: int

    @property
    def program_id(self):
        payload = (self.kind, tuple(round(value, 12) for value in self.coefficients))
        return "XFER-" + hashlib.sha256(json.dumps(payload).encode()).hexdigest()[:16]

    @staticmethod
    def feature_names(kind):
        base = ("ONE", "STATE", "Q0", "Q2", "DELTA_Q3", "Q3")
        context = ("INITIAL_Q1", "INITIAL_Q0", "INITIAL_Q2")
        if kind == "state_fold":
            return base
        if kind == "context_fold":
            return base + context
        if kind == "interaction_fold":
            return base + context + (
                "Q0@Q3", "Q0@Q0", "Q2@Q3", "STATE@Q0", "STATE@Q2",
            )
        raise ValueError(kind)

    def _features(self, state, sample, previous_time, initial_context):
        q0 = sample["q0"]
        q2 = sample["q2"]
        q3 = sample["q3"]
        values = [1.0, state, q0, q2, q3 - previous_time, q3]
        if self.kind in ("context_fold", "interaction_fold"):
            values.extend(initial_context)
        if self.kind == "interaction_fold":
            values.extend((q0 * q3, q0 * q0, q2 * q3, state * q0, state * q2))
        return np.asarray(values)

    def rollout(self, trace: AnonymousTraceV41):
        first = trace.samples[0]
        state = first["q1"]
        initial_context = (first["q1"], first["q0"], first["q2"])
        predictions = [state]
        previous_time = first["q3"]
        for sample in trace.samples[1:]:
            features = self._features(state, sample, previous_time, initial_context)
            state = float(features @ np.asarray(self.coefficients))
            predictions.append(state)
            previous_time = sample["q3"]
        return predictions

    def render(self):
        features = ";".join(self.feature_names(self.kind))
        weights = ";".join(f"W{i}={value:.9g}" for i, value in enumerate(self.coefficients))
        return f"{self.kind.upper()}<S0=Q1;FEATURES={features};STEP={weights}>"

    def to_dict(self):
        return {
            "program_id": self.program_id,
            "kind": self.kind,
            "opaque_program": self.render(),
            "feature_names": list(self.feature_names(self.kind)),
            "coefficients": list(self.coefficients),
            "validation_rmse": self.validation_rmse,
            "validation_mape": self.validation_mape,
            "node_count": self.node_count,
            "created_operator": self.kind.upper(),
            "human_law_name": None,
            "domain_formula_supplied": False,
        }


class CounterexampleTransferResearchV42:
    """Search a small semantic grammar without receiving domain or stage labels."""

    @staticmethod
    def _design_row(kind, previous, sample, initial_context):
        draft = TransferProgramV42(kind, (), math.inf, math.inf, 0)
        return draft._features(previous["q1"], sample, previous["q3"], initial_context)

    def _fit(self, traces, kind):
        features = []
        targets = []
        for trace in traces:
            first = trace.samples[0]
            initial_context = (first["q1"], first["q0"], first["q2"])
            for previous, sample in zip(trace.samples, trace.samples[1:]):
                features.append(self._design_row(kind, previous, sample, initial_context))
                targets.append(sample["q1"])
        coefficients, *_ = np.linalg.lstsq(
            np.asarray(features), np.asarray(targets), rcond=None,
        )
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
                "trajectory_rmse": math.sqrt(
                    sum(value * value for value in trace_errors) / len(trace_errors)
                ),
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
        for kind, node_count in (
            ("state_fold", 11),
            ("context_fold", 17),
            ("interaction_fold", 27),
        ):
            coefficients = self._fit(training, kind)
            draft = TransferProgramV42(kind, coefficients, math.inf, math.inf, node_count)
            audit = self.evaluate(draft, validation)
            candidates.append(TransferProgramV42(
                kind,
                coefficients,
                audit["rmse"],
                audit["median_absolute_percentage_error"],
                node_count,
            ))
        selected = min(
            candidates,
            key=lambda item: item.validation_rmse + item.node_count * 1e-5,
        )
        return selected, tuple(candidates)


def transfer_program_commitment_v42(program: TransferProgramV42):
    payload = {
        "program_id": program.program_id,
        "opaque_program": program.render(),
        "coefficients": list(program.coefficients),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
