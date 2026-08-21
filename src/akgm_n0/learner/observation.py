"""The complete public observation surface available to a learner."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence


PUBLIC_OBSERVATION_FIELDS = frozenset(
    {
        "opaque_session_id",
        "sequence_values",
        "validity_mask",
        "action_receipt",
    }
)

PUBLIC_TABLE_OBSERVATION_FIELDS = frozenset(
    {
        "opaque_session_id",
        "input_rows",
        "output_values",
        "validity_mask",
        "action_receipt",
    }
)

PUBLIC_TRACE_OBSERVATION_FIELDS = frozenset(
    {
        "opaque_session_id",
        "symbol_traces",
        "output_values",
        "validity_mask",
        "action_receipt",
    }
)

PUBLIC_COLLECTION_OBSERVATION_FIELDS = frozenset(
    {
        "opaque_session_id",
        "numeric_values",
        "validity_mask",
        "action_receipt",
    }
)


@dataclass(frozen=True, slots=True)
class NumericObservation:
    """Anonymous numeric data returned by an environment runner."""

    opaque_session_id: str
    sequence_values: tuple[float, ...]
    validity_mask: tuple[bool, ...]
    action_receipt: str

    def __post_init__(self) -> None:
        if not self.opaque_session_id:
            raise ValueError("opaque_session_id cannot be empty")
        if len(self.sequence_values) != len(self.validity_mask):
            raise ValueError("sequence_values and validity_mask lengths differ")
        if not self.sequence_values:
            raise ValueError("an observation must contain at least one value")
        for index, (value, valid) in enumerate(
            zip(self.sequence_values, self.validity_mask, strict=True)
        ):
            if valid and not math.isfinite(value):
                raise ValueError(f"valid observation value at index {index} is not finite")

    @classmethod
    def create(
        cls,
        *,
        opaque_session_id: str,
        sequence_values: Sequence[float],
        validity_mask: Sequence[bool],
        action_receipt: str,
    ) -> "NumericObservation":
        return cls(
            opaque_session_id=opaque_session_id,
            sequence_values=tuple(float(value) for value in sequence_values),
            validity_mask=tuple(bool(value) for value in validity_mask),
            action_receipt=action_receipt,
        )

    def to_public_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "opaque_session_id": self.opaque_session_id,
            "sequence_values": list(self.sequence_values),
            "validity_mask": list(self.validity_mask),
            "action_receipt": self.action_receipt,
        }
        if set(result) != PUBLIC_OBSERVATION_FIELDS:
            raise AssertionError("public observation surface changed without a contract update")
        return result


@dataclass(frozen=True, slots=True)
class NumericTableObservation:
    """Anonymous fixed-width numeric rows paired with anonymous scalar outputs."""

    opaque_session_id: str
    input_rows: tuple[tuple[float, ...], ...]
    output_values: tuple[float, ...]
    validity_mask: tuple[bool, ...]
    action_receipt: str

    def __post_init__(self) -> None:
        if not self.opaque_session_id:
            raise ValueError("opaque_session_id cannot be empty")
        row_count = len(self.input_rows)
        if row_count == 0:
            raise ValueError("an observation must contain at least one row")
        if row_count != len(self.output_values) or row_count != len(self.validity_mask):
            raise ValueError("table observation lengths differ")
        width = len(self.input_rows[0])
        if width == 0 or any(len(row) != width for row in self.input_rows):
            raise ValueError("input rows must have one fixed, non-zero width")
        for row_index, (row, output, valid) in enumerate(
            zip(self.input_rows, self.output_values, self.validity_mask, strict=True)
        ):
            if valid and (
                not all(math.isfinite(value) for value in row)
                or not math.isfinite(output)
            ):
                raise ValueError(
                    f"valid table value at row {row_index} is not finite"
                )

    @classmethod
    def create(
        cls,
        *,
        opaque_session_id: str,
        input_rows: Sequence[Sequence[float]],
        output_values: Sequence[float],
        validity_mask: Sequence[bool],
        action_receipt: str,
    ) -> "NumericTableObservation":
        return cls(
            opaque_session_id=opaque_session_id,
            input_rows=tuple(tuple(float(value) for value in row) for row in input_rows),
            output_values=tuple(float(value) for value in output_values),
            validity_mask=tuple(bool(value) for value in validity_mask),
            action_receipt=action_receipt,
        )

    def to_public_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "opaque_session_id": self.opaque_session_id,
            "input_rows": [list(row) for row in self.input_rows],
            "output_values": list(self.output_values),
            "validity_mask": list(self.validity_mask),
            "action_receipt": self.action_receipt,
        }
        if set(result) != PUBLIC_TABLE_OBSERVATION_FIELDS:
            raise AssertionError("public table surface changed without a contract update")
        return result


@dataclass(frozen=True, slots=True)
class SymbolTraceObservation:
    """Anonymous finite symbol traces paired with anonymous discrete outputs."""

    opaque_session_id: str
    symbol_traces: tuple[tuple[int, ...], ...]
    output_values: tuple[int, ...]
    validity_mask: tuple[bool, ...]
    action_receipt: str

    def __post_init__(self) -> None:
        if not self.opaque_session_id:
            raise ValueError("opaque_session_id cannot be empty")
        trace_count = len(self.symbol_traces)
        if trace_count == 0:
            raise ValueError("an observation must contain at least one trace")
        if trace_count != len(self.output_values) or trace_count != len(self.validity_mask):
            raise ValueError("trace observation lengths differ")
        for trace_index, (trace, output, valid) in enumerate(
            zip(self.symbol_traces, self.output_values, self.validity_mask, strict=True)
        ):
            if valid and (
                any(isinstance(symbol, bool) or not isinstance(symbol, int) for symbol in trace)
                or isinstance(output, bool)
                or not isinstance(output, int)
            ):
                raise ValueError(
                    f"valid trace at index {trace_index} contains a non-integer"
                )

    @classmethod
    def create(
        cls,
        *,
        opaque_session_id: str,
        symbol_traces: Sequence[Sequence[int]],
        output_values: Sequence[int],
        validity_mask: Sequence[bool],
        action_receipt: str,
    ) -> "SymbolTraceObservation":
        return cls(
            opaque_session_id=opaque_session_id,
            symbol_traces=tuple(tuple(int(symbol) for symbol in trace) for trace in symbol_traces),
            output_values=tuple(int(value) for value in output_values),
            validity_mask=tuple(bool(value) for value in validity_mask),
            action_receipt=action_receipt,
        )

    def to_public_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "opaque_session_id": self.opaque_session_id,
            "symbol_traces": [list(trace) for trace in self.symbol_traces],
            "output_values": list(self.output_values),
            "validity_mask": list(self.validity_mask),
            "action_receipt": self.action_receipt,
        }
        if set(result) != PUBLIC_TRACE_OBSERVATION_FIELDS:
            raise AssertionError("public trace surface changed without a contract update")
        return result


@dataclass(frozen=True, slots=True)
class NumericCollectionObservation:
    """Anonymous numeric members with no positional or ordering semantics."""

    opaque_session_id: str
    numeric_values: tuple[float, ...]
    validity_mask: tuple[bool, ...]
    action_receipt: str

    def __post_init__(self) -> None:
        if not self.opaque_session_id:
            raise ValueError("opaque_session_id cannot be empty")
        if not self.numeric_values:
            raise ValueError("a collection must contain at least one value")
        if len(self.numeric_values) != len(self.validity_mask):
            raise ValueError("numeric_values and validity_mask lengths differ")
        if len(set(self.numeric_values)) != len(self.numeric_values):
            raise ValueError("the registered relation probe requires unique values")
        for index, (value, valid) in enumerate(
            zip(self.numeric_values, self.validity_mask, strict=True)
        ):
            if valid and not math.isfinite(value):
                raise ValueError(f"valid collection value at index {index} is not finite")

    @classmethod
    def create(
        cls,
        *,
        opaque_session_id: str,
        numeric_values: Sequence[float],
        validity_mask: Sequence[bool],
        action_receipt: str,
    ) -> "NumericCollectionObservation":
        return cls(
            opaque_session_id=opaque_session_id,
            numeric_values=tuple(float(value) for value in numeric_values),
            validity_mask=tuple(bool(value) for value in validity_mask),
            action_receipt=action_receipt,
        )

    def to_public_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "opaque_session_id": self.opaque_session_id,
            "numeric_values": list(self.numeric_values),
            "validity_mask": list(self.validity_mask),
            "action_receipt": self.action_receipt,
        }
        if set(result) != PUBLIC_COLLECTION_OBSERVATION_FIELDS:
            raise AssertionError("public collection surface changed without a contract update")
        return result
