"""Evaluator-owned numeric worlds whose generation rules stay sealed."""

from __future__ import annotations

import hashlib
import hmac
import math
import random
from dataclasses import dataclass
from typing import Literal

from akgm_n0.learner.observation import (
    NumericObservation,
    NumericTableObservation,
    SymbolTraceObservation,
)


WorldKind = Literal["affine", "polynomial2", "alternating_increment"]


@dataclass(frozen=True, slots=True)
class SequenceWorldSpec:
    """Private evaluator input. Never serialize this object to a learner."""

    kind: WorldKind
    parameters: tuple[float, ...]
    length: int
    noise_std: float = 0.0

    def __post_init__(self) -> None:
        expected_parameter_counts = {
            "affine": 2,
            "polynomial2": 3,
            "alternating_increment": 3,
        }
        if self.kind not in expected_parameter_counts:
            raise ValueError(f"unsupported private world kind: {self.kind}")
        if len(self.parameters) != expected_parameter_counts[self.kind]:
            raise ValueError("private world parameter count does not match its kind")
        if self.length < 2:
            raise ValueError("private world length must be at least two")
        if self.noise_std < 0 or not math.isfinite(self.noise_std):
            raise ValueError("noise_std must be finite and non-negative")
        if not all(math.isfinite(value) for value in self.parameters):
            raise ValueError("private world parameters must be finite")


class HiddenSequenceEnvironment:
    """Execute a sealed sequence world and return only public observations."""

    def __init__(self, spec: SequenceWorldSpec, *, seed: int, secret: bytes) -> None:
        if not secret:
            raise ValueError("an evaluator secret is required")
        self._spec = spec
        self._seed = int(seed)
        self._secret = bytes(secret)
        self._values = self._generate_values()
        self._session_id = self._opaque_token("session", spec.kind, spec.parameters)
        self._action_counter = 0

    def observe(self, requested_length: int) -> NumericObservation:
        if isinstance(requested_length, bool) or not isinstance(requested_length, int):
            raise TypeError("requested_length must be an integer")
        if requested_length < 1 or requested_length > len(self._values):
            raise ValueError("requested_length is outside the world bounds")
        self._action_counter += 1
        receipt = self._opaque_token(
            "action", self._session_id, self._action_counter, requested_length
        )
        visible = self._values[:requested_length]
        return NumericObservation.create(
            opaque_session_id=self._session_id,
            sequence_values=visible,
            validity_mask=[True] * len(visible),
            action_receipt=receipt,
        )

    def _generate_values(self) -> tuple[float, ...]:
        random_source = random.Random(self._seed)
        values: list[float] = []
        if self._spec.kind == "affine":
            intercept, slope = self._spec.parameters
            values = [intercept + slope * index for index in range(self._spec.length)]
        elif self._spec.kind == "polynomial2":
            coefficient_2, coefficient_1, coefficient_0 = self._spec.parameters
            values = [
                coefficient_2 * index * index + coefficient_1 * index + coefficient_0
                for index in range(self._spec.length)
            ]
        elif self._spec.kind == "alternating_increment":
            start, increment_a, increment_b = self._spec.parameters
            current = start
            values.append(current)
            for index in range(1, self._spec.length):
                current += increment_a if index % 2 else increment_b
                values.append(current)
        else:
            raise AssertionError("validated world kind became unreachable")

        if self._spec.noise_std:
            values = [
                value + random_source.gauss(0.0, self._spec.noise_std)
                for value in values
            ]
        if not all(math.isfinite(value) for value in values):
            raise ArithmeticError("sealed world produced non-finite data")
        return tuple(float(value) for value in values)

    def _opaque_token(self, *parts: object) -> str:
        payload = "|".join(repr(part) for part in (self._seed, *parts)).encode("utf-8")
        return hmac.new(self._secret, payload, hashlib.sha256).hexdigest()[:24]


class HiddenIntegerGridEnvironment:
    """Evaluator-owned two-column world used for the operation-growth trial."""

    def __init__(
        self,
        rows: tuple[tuple[int, int], ...],
        *,
        seed: int,
        secret: bytes,
    ) -> None:
        if not rows:
            raise ValueError("the private row set cannot be empty")
        if not secret:
            raise ValueError("an evaluator secret is required")
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for row in rows
            for value in row
        ):
            raise TypeError("private rows must contain integers")
        if any(right < 0 or right > 64 for _, right in rows):
            raise ValueError("the registered control column is outside its bounds")
        self._rows = rows
        self._seed = int(seed)
        self._secret = bytes(secret)
        self._session_id = self._opaque_token("table-session", len(rows))

    def observe(self) -> NumericTableObservation:
        outputs = tuple(float(left * right) for left, right in self._rows)
        return NumericTableObservation.create(
            opaque_session_id=self._session_id,
            input_rows=self._rows,
            output_values=outputs,
            validity_mask=[True] * len(self._rows),
            action_receipt=self._opaque_token("table-action", self._session_id),
        )

    def _opaque_token(self, *parts: object) -> str:
        payload = "|".join(repr(part) for part in (self._seed, *parts)).encode("utf-8")
        return hmac.new(self._secret, payload, hashlib.sha256).hexdigest()[:24]


class HiddenSymbolTraceEnvironment:
    """Evaluator-owned discrete trace world for MetaMachine Gen 1."""

    def __init__(
        self,
        traces: tuple[tuple[int, ...], ...],
        *,
        seed: int,
        secret: bytes,
        symbol_permutation: tuple[int, int],
    ) -> None:
        if not traces:
            raise ValueError("the private trace set cannot be empty")
        if not secret:
            raise ValueError("an evaluator secret is required")
        if sorted(symbol_permutation) != [0, 1]:
            raise ValueError("symbol_permutation must be a permutation of two ids")
        if any(len(trace) > 64 for trace in traces):
            raise ValueError("a private trace exceeds the registered step bound")
        if any(symbol not in {0, 1} for trace in traces for symbol in trace):
            raise ValueError("private traces must use the registered symbol cardinality")
        self._traces = traces
        self._seed = int(seed)
        self._secret = bytes(secret)
        self._symbol_permutation = symbol_permutation
        self._session_id = self._opaque_token("trace-session", len(traces))

    def observe(self) -> SymbolTraceObservation:
        visible = tuple(
            tuple(self._symbol_permutation[symbol] for symbol in trace)
            for trace in self._traces
        )
        outputs = tuple(sum(trace) % 2 for trace in self._traces)
        return SymbolTraceObservation.create(
            opaque_session_id=self._session_id,
            symbol_traces=visible,
            output_values=outputs,
            validity_mask=[True] * len(visible),
            action_receipt=self._opaque_token("trace-action", self._session_id),
        )

    def _opaque_token(self, *parts: object) -> str:
        payload = "|".join(repr(part) for part in (self._seed, *parts)).encode("utf-8")
        return hmac.new(self._secret, payload, hashlib.sha256).hexdigest()[:24]
