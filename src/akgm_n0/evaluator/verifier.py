"""Independent executable verification and numeric counterexample capture."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from statistics import fmean
from typing import Any, Literal, Mapping, Sequence

from akgm_n0.learner.dsl import (
    ExecutionContext,
    NumericExecutionError,
    ProgramExecutor,
    ProgramNode,
)
from akgm_n0.learner.observation import NumericObservation
from akgm_n0.learner.search import iter_read_offsets, program_id


VerificationScope = Literal[
    "source_holdout", "registered_ood", "adversarial_challenge"
]
VerificationStatus = Literal["verified", "bounded", "rejected"]


@dataclass(frozen=True, slots=True)
class VerificationCase:
    case_id: str
    scope: VerificationScope
    observation: NumericObservation
    refit_prefix_length: int
    absolute_tolerance: float
    required_for_validity: bool

    @classmethod
    def create(
        cls,
        *,
        scope: VerificationScope,
        observation: NumericObservation,
        refit_prefix_length: int,
        absolute_tolerance: float = 1e-9,
        required_for_validity: bool,
    ) -> "VerificationCase":
        if refit_prefix_length < 3:
            raise ValueError("refit_prefix_length must provide at least two transitions")
        if refit_prefix_length >= len(observation.sequence_values):
            raise ValueError("verification case must retain unseen suffix values")
        if absolute_tolerance < 0 or not math.isfinite(absolute_tolerance):
            raise ValueError("absolute_tolerance must be finite and non-negative")
        identifier_payload = json.dumps(
            {
                "scope": scope,
                "observation": observation.opaque_session_id,
                "receipt": observation.action_receipt,
                "prefix": refit_prefix_length,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        case_id = "CASE-" + hashlib.sha256(identifier_payload.encode("utf-8")).hexdigest()[:16]
        return cls(
            case_id=case_id,
            scope=scope,
            observation=observation,
            refit_prefix_length=refit_prefix_length,
            absolute_tolerance=absolute_tolerance,
            required_for_validity=required_for_validity,
        )


@dataclass(frozen=True, slots=True)
class NumericCounterexample:
    case_id: str
    index: int
    readable_values: tuple[float, float]
    predicted_value: float
    observed_value: float
    absolute_error: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "index": self.index,
            "readable_values": list(self.readable_values),
            "predicted_value": self.predicted_value,
            "observed_value": self.observed_value,
            "absolute_error": self.absolute_error,
        }


@dataclass(frozen=True, slots=True)
class VerificationCaseResult:
    case_id: str
    scope: VerificationScope
    required_for_validity: bool
    passed: bool
    fitted_parameters: Mapping[int, float]
    validation_count: int
    mse: float
    normalized_mse: float
    maximum_absolute_error: float
    counterexamples: tuple[NumericCounterexample, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "scope": self.scope,
            "required_for_validity": self.required_for_validity,
            "passed": self.passed,
            "fitted_parameters": {
                str(key): value for key, value in self.fitted_parameters.items()
            },
            "validation_count": self.validation_count,
            "mse": self.mse,
            "normalized_mse": self.normalized_mse,
            "maximum_absolute_error": self.maximum_absolute_error,
            "counterexamples": [item.to_dict() for item in self.counterexamples],
        }


@dataclass(frozen=True, slots=True)
class VerificationReport:
    verifier_version: str
    candidate_id: str
    status: VerificationStatus
    case_results: tuple[VerificationCaseResult, ...]

    @property
    def counterexamples(self) -> tuple[NumericCounterexample, ...]:
        return tuple(
            counterexample
            for result in self.case_results
            for counterexample in result.counterexamples
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "verifier_version": self.verifier_version,
            "candidate_id": self.candidate_id,
            "status": self.status,
            "summary": {
                "case_count": len(self.case_results),
                "passed_case_count": sum(result.passed for result in self.case_results),
                "failed_case_count": sum(not result.passed for result in self.case_results),
                "counterexample_count": len(self.counterexamples),
            },
            "case_results": [result.to_dict() for result in self.case_results],
        }


class IndependentVerifier:
    """Refit and test candidates without using generator confidence scores."""

    VERSION = "independent-verifier-v0.1"

    def __init__(
        self,
        executor: ProgramExecutor | None = None,
        *,
        concept_library: Mapping[str, ProgramNode] | None = None,
    ) -> None:
        self.concept_library = dict(concept_library or {})
        self.executor = executor or ProgramExecutor(library=self.concept_library)

    def verify(
        self, program: ProgramNode, cases: Sequence[VerificationCase]
    ) -> VerificationReport:
        if not cases:
            raise ValueError("at least one verification case is required")
        if not set(iter_read_offsets(program, self.concept_library)).issubset({-1, 0}):
            raise ValueError("verification rejects candidates that can read the target")
        results = tuple(self._verify_case(program, case) for case in cases)
        if any(not result.passed for result in results if result.required_for_validity):
            status: VerificationStatus = "rejected"
        elif any(not result.passed for result in results):
            status = "bounded"
        else:
            status = "verified"
        return VerificationReport(
            verifier_version=self.VERSION,
            candidate_id=f"CAND-{program_id(program)}",
            status=status,
            case_results=results,
        )

    def _verify_case(
        self, program: ProgramNode, case: VerificationCase
    ) -> VerificationCaseResult:
        training_indices = tuple(range(1, case.refit_prefix_length - 1))
        validation_indices = tuple(
            range(case.refit_prefix_length - 1, len(case.observation.sequence_values) - 1)
        )
        training_indices = self._valid_indices(case.observation, training_indices)
        validation_indices = self._valid_indices(case.observation, validation_indices)
        if not training_indices or not validation_indices:
            raise ValueError("verification case has insufficient valid examples")

        parameters = self._fit_parameter_independently(
            program, case.observation, training_indices
        )
        errors: list[tuple[int, float, float, float]] = []
        for index in validation_indices:
            predicted = self._evaluate(program, case.observation, index, parameters)
            observed = case.observation.sequence_values[index + 1]
            errors.append((index, predicted, observed, abs(predicted - observed)))

        mse = fmean((predicted - observed) ** 2 for _, predicted, observed, _ in errors)
        observed_values = [observed for _, _, observed, _ in errors]
        observed_mean = fmean(observed_values)
        observed_variance = fmean(
            (observed - observed_mean) ** 2 for observed in observed_values
        )
        normalized_mse = mse / max(observed_variance, 1e-12)
        maximum_error = max(error for _, _, _, error in errors)
        counterexamples = tuple(
            NumericCounterexample(
                case_id=case.case_id,
                index=index,
                readable_values=(
                    case.observation.sequence_values[index - 1],
                    case.observation.sequence_values[index],
                ),
                predicted_value=predicted,
                observed_value=observed,
                absolute_error=error,
            )
            for index, predicted, observed, error in errors
            if error > case.absolute_tolerance
        )
        return VerificationCaseResult(
            case_id=case.case_id,
            scope=case.scope,
            required_for_validity=case.required_for_validity,
            passed=not counterexamples,
            fitted_parameters=parameters,
            validation_count=len(validation_indices),
            mse=mse,
            normalized_mse=normalized_mse,
            maximum_absolute_error=maximum_error,
            counterexamples=counterexamples,
        )

    @staticmethod
    def _valid_indices(
        observation: NumericObservation, indices: Sequence[int]
    ) -> tuple[int, ...]:
        return tuple(
            index
            for index in indices
            if all(
                observation.validity_mask[position]
                for position in (index - 1, index, index + 1)
            )
        )

    def _fit_parameter_independently(
        self,
        program: ProgramNode,
        observation: NumericObservation,
        indices: Sequence[int],
    ) -> dict[int, float]:
        slots = _parameter_slots(program)
        if not slots:
            return {}
        if slots != {0}:
            raise NumericExecutionError("verifier supports exactly parameter slot zero")

        design: list[float] = []
        residual_targets: list[float] = []
        for index in indices:
            at_zero = self._evaluate(program, observation, index, {0: 0.0})
            at_two = self._evaluate(program, observation, index, {0: 2.0})
            coefficient = (at_two - at_zero) / 2.0
            design.append(coefficient)
            residual_targets.append(observation.sequence_values[index + 1] - at_zero)
        denominator = sum(value * value for value in design)
        if denominator <= 1e-15:
            return {0: 0.0}
        fitted = sum(
            coefficient * target
            for coefficient, target in zip(design, residual_targets, strict=True)
        ) / denominator
        if not math.isfinite(fitted):
            raise NumericExecutionError("verifier parameter fit is non-finite")
        return {0: fitted}

    def _evaluate(
        self,
        program: ProgramNode,
        observation: NumericObservation,
        index: int,
        parameters: Mapping[int, float],
    ) -> float:
        return self.executor.evaluate(
            program,
            ExecutionContext.create(
                observation.sequence_values,
                index=index,
                parameters=parameters,
                validity_mask=observation.validity_mask,
            ),
        )


def _parameter_slots(program: ProgramNode) -> set[int]:
    slots: set[int] = set()
    stack = [program]
    while stack:
        node = stack.pop()
        if node.op == "p_scalar_parameter" and node.parameter_slot is not None:
            slots.add(node.parameter_slot)
        stack.extend(node.args)
    return slots
