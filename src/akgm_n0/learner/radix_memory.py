"""Search anonymous multi-stage residual memory without product or quotient nodes."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .adaptive_control import InvalidAdaptiveProgram
from .observation import NumericTableObservation
from .trace_memory import TraceMemoryExecutor, TraceMemoryProgram


def _decimal(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InvalidAdaptiveProgram("anonymous stage weight is invalid") from exc
    if not result.is_finite():
        raise InvalidAdaptiveProgram("anonymous stage weight must be finite")
    return result


def _repeat_add(value: Decimal, count: int) -> Decimal:
    result = Decimal(0)
    for _ in range(count):
        result += value
    return result


@dataclass(frozen=True, slots=True)
class RadixMemoryProgram:
    parent_operation_id: str
    parent_program: TraceMemoryProgram
    cycle_width: int
    stage_weights: tuple[str, ...]

    @property
    def node_count(self) -> int:
        return self.parent_program.node_count + self.cycle_width + len(self.stage_weights)

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "anonymous_multistage_residual_memory_v0.1",
            "parent_operation_id": self.parent_operation_id,
            "parent_program": self.parent_program.to_dict(),
            "cycle": {
                "width": self.cycle_width,
                "stage_weights": list(self.stage_weights),
                "residual_update": "bounded_repeated_addition_then_parent_call",
                "output_update": "bounded_repeated_addition_of_stage_weight",
            },
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RadixMemoryProgram":
        required = {"substrate", "parent_operation_id", "parent_program", "cycle"}
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidAdaptiveProgram("multistage residual program shape is invalid")
        if value["substrate"] != "anonymous_multistage_residual_memory_v0.1":
            raise InvalidAdaptiveProgram("multistage residual substrate is unavailable")
        cycle = value["cycle"]
        if not isinstance(cycle, Mapping) or set(cycle) != {
            "width",
            "stage_weights",
            "residual_update",
            "output_update",
        }:
            raise InvalidAdaptiveProgram("multistage cycle definition is invalid")
        if cycle["residual_update"] != "bounded_repeated_addition_then_parent_call":
            raise InvalidAdaptiveProgram("residual update is unavailable")
        if cycle["output_update"] != "bounded_repeated_addition_of_stage_weight":
            raise InvalidAdaptiveProgram("output update is unavailable")
        raw_weights = cycle["stage_weights"]
        if not isinstance(raw_weights, (list, tuple)):
            raise InvalidAdaptiveProgram("stage weights must be a sequence")
        program = cls(
            parent_operation_id=str(value["parent_operation_id"]),
            parent_program=TraceMemoryProgram.from_dict(value["parent_program"]),
            cycle_width=cycle["width"],
            stage_weights=tuple(str(item) for item in raw_weights),
        )
        RadixMemoryExecutor().validate(program)
        return program


@dataclass(frozen=True, slots=True)
class RadixStageExecution:
    stage_index: int
    input_residual: Decimal
    scaled_residual: Decimal
    emitted_count: int
    next_residual: Decimal
    stage_weight: Decimal

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_index": self.stage_index,
            "input_residual": str(self.input_residual),
            "scaled_residual": str(self.scaled_residual),
            "emitted_count": self.emitted_count,
            "next_residual": str(self.next_residual),
            "stage_weight": str(self.stage_weight),
        }


@dataclass(frozen=True, slots=True)
class RadixMemoryExecution:
    output_decimal: Decimal
    integer_memory: int
    initial_residual: Decimal
    adapted_inputs: tuple[float, float]
    stages: tuple[RadixStageExecution, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "output": str(self.output_decimal),
            "integer_memory": self.integer_memory,
            "initial_residual": str(self.initial_residual),
            "adapted_inputs": list(self.adapted_inputs),
            "stages": [item.to_dict() for item in self.stages],
        }


class RadixMemoryExecutor:
    def __init__(self, *, maximum_steps: int = 256) -> None:
        self.parent_executor = TraceMemoryExecutor(maximum_steps=maximum_steps)

    def validate(self, program: RadixMemoryProgram) -> None:
        if not program.parent_operation_id:
            raise InvalidAdaptiveProgram("multistage residual program requires a parent")
        self.parent_executor.validate(program.parent_program)
        if (
            isinstance(program.cycle_width, bool)
            or not isinstance(program.cycle_width, int)
            or not 2 <= program.cycle_width <= 32
        ):
            raise InvalidAdaptiveProgram("cycle width is outside the registered bound")
        if not 1 <= len(program.stage_weights) <= 4:
            raise InvalidAdaptiveProgram("stage count is outside the registered bound")
        weights = tuple(_decimal(item) for item in program.stage_weights)
        if any(item <= 0 or item > 1 for item in weights):
            raise InvalidAdaptiveProgram("stage weights must be positive bounded values")

    def execute(self, program: RadixMemoryProgram, inputs) -> RadixMemoryExecution:
        self.validate(program)
        numeric_inputs = tuple(float(value) for value in inputs)
        if len(numeric_inputs) != 2 or any(not value.is_integer() for value in numeric_inputs):
            raise InvalidAdaptiveProgram("multistage residual input must contain two integers")
        weights = tuple(_decimal(item) for item in program.stage_weights)
        parent_result = self.parent_executor.execute(program.parent_program, numeric_inputs)
        integer_memory = _integer(parent_result.output_value, "parent integer memory")
        residual = _decimal(parent_result.parent_output_value)
        divisor = _decimal(parent_result.adapted_inputs[1])
        if divisor <= 0 or divisor != divisor.to_integral_value():
            raise InvalidAdaptiveProgram("adapted second input must be a positive integer")
        output = Decimal(integer_memory)
        stages: list[RadixStageExecution] = []
        initial_residual = residual
        for stage_index, weight in enumerate(weights):
            scaled = _repeat_add(residual, program.cycle_width)
            stage_parent = self.parent_executor.execute(
                program.parent_program, (float(scaled), float(divisor))
            )
            emitted = _integer(stage_parent.output_value, "stage emission")
            if emitted < 0 or emitted >= program.cycle_width:
                raise InvalidAdaptiveProgram("stage emission is outside the cycle width")
            next_residual = _decimal(stage_parent.parent_output_value)
            output += _repeat_add(weight, emitted)
            stages.append(
                RadixStageExecution(
                    stage_index=stage_index,
                    input_residual=residual,
                    scaled_residual=scaled,
                    emitted_count=emitted,
                    next_residual=next_residual,
                    stage_weight=weight,
                )
            )
            residual = next_residual
        return RadixMemoryExecution(
            output_decimal=output,
            integer_memory=integer_memory,
            initial_residual=initial_residual,
            adapted_inputs=parent_result.adapted_inputs,
            stages=tuple(stages),
        )


@dataclass(frozen=True, slots=True)
class RadixMemoryCandidate:
    candidate_id: str
    program: RadixMemoryProgram
    fit_mse: float
    maximum_absolute_error: float
    coherence_error: float
    training_outputs: tuple[str, ...]
    behavior_signature: tuple[str | None, ...]
    logic_signature: str

    @property
    def exact(self) -> bool:
        return self.maximum_absolute_error == 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "program": self.program.to_dict(),
            "fit_mse": self.fit_mse,
            "maximum_absolute_error": self.maximum_absolute_error,
            "coherence_error": self.coherence_error,
            "training_outputs": list(self.training_outputs),
            "behavior_signature": list(self.behavior_signature),
            "logic_signature": self.logic_signature,
            "program_nodes": self.program.node_count,
            "exact": self.exact,
        }


@dataclass(frozen=True, slots=True)
class RadixMemorySearchReport:
    programs_generated: int
    programs_executed: int
    programs_rejected: int
    behavior_classes: int
    evidence_weights: tuple[dict[str, Any], ...]
    cycle_width_candidates: tuple[int, ...]
    top_candidates: tuple[RadixMemoryCandidate, ...]


@dataclass(frozen=True, slots=True)
class _AnonymousTrace:
    integer_memory: int
    stage_emissions: tuple[int, ...]


class RadixMemorySearch:
    def __init__(
        self,
        parent_program: TraceMemoryProgram,
        *,
        parent_operation_id: str,
        cycle_width_candidates=range(2, 13),
        maximum_stages: int = 3,
        maximum_weight_candidates: int = 12,
        top_k: int = 500,
        executor: RadixMemoryExecutor | None = None,
    ) -> None:
        self.parent_program = parent_program
        self.parent_operation_id = parent_operation_id
        self.cycle_width_candidates = tuple(int(item) for item in cycle_width_candidates)
        self.maximum_stages = maximum_stages
        self.maximum_weight_candidates = maximum_weight_candidates
        self.top_k = top_k
        self.executor = executor or RadixMemoryExecutor()

    def search(self, observation: NumericTableObservation) -> RadixMemorySearchReport:
        valid = tuple(
            (tuple(row), _decimal(output))
            for row, output, include in zip(
                observation.input_rows,
                observation.output_values,
                observation.validity_mask,
                strict=True,
            )
            if include
        )
        if not valid:
            raise ValueError("multistage residual search requires valid rows")
        evidence_weights = self._derive_weights(valid)
        weight_values = tuple(_decimal(item["value"]) for item in evidence_weights)
        probe_rows = tuple(row for row, _ in valid) + (
            (17.0, 8.0),
            (-17.0, -8.0),
            (999.0, 1000.0),
            (-999.0, 1000.0),
        )
        trace_cache: dict[tuple[int, tuple[float, ...]], _AnonymousTrace | None] = {}
        for width in self.cycle_width_candidates:
            for row in probe_rows:
                try:
                    trace_cache[(width, row)] = self._trace(width, row)
                except InvalidAdaptiveProgram:
                    trace_cache[(width, row)] = None

        generated = 0
        executed = 0
        rejected = 0
        behavior_keys: set[tuple[str | None, ...]] = set()
        by_logic_behavior: dict[
            tuple[tuple[str | None, ...], str], RadixMemoryCandidate
        ] = {}
        for width in self.cycle_width_candidates:
            for stage_count in range(1, self.maximum_stages + 1):
                for weights in itertools.product(weight_values, repeat=stage_count):
                    generated += 1
                    program = RadixMemoryProgram(
                        parent_operation_id=self.parent_operation_id,
                        parent_program=self.parent_program,
                        cycle_width=width,
                        stage_weights=tuple(str(item) for item in weights),
                    )
                    outputs: list[Decimal] = []
                    failed = False
                    for row, _ in valid:
                        trace = trace_cache[(width, row)]
                        if trace is None:
                            failed = True
                            break
                        outputs.append(self._output(trace, weights))
                    if failed:
                        rejected += 1
                        continue
                    executed += 1
                    errors = tuple(
                        actual - expected
                        for actual, (_, expected) in zip(outputs, valid, strict=True)
                    )
                    behavior: list[str | None] = []
                    for row in probe_rows:
                        trace = trace_cache[(width, row)]
                        behavior.append(
                            None if trace is None else str(self._output(trace, weights))
                        )
                    behavior_key = tuple(behavior)
                    coherence = self._coherence_error(width, weights)
                    key = radix_memory_program_key(program)
                    logic_signature = radix_memory_logic_signature(program)
                    candidate = RadixMemoryCandidate(
                        candidate_id="RM-"
                        + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
                        program=program,
                        fit_mse=sum(float(error * error) for error in errors) / len(errors),
                        maximum_absolute_error=float(max(abs(error) for error in errors)),
                        coherence_error=float(coherence),
                        training_outputs=tuple(str(item) for item in outputs),
                        behavior_signature=behavior_key,
                        logic_signature=logic_signature,
                    )
                    behavior_keys.add(behavior_key)
                    dedupe_key = (behavior_key, logic_signature)
                    current = by_logic_behavior.get(dedupe_key)
                    if current is None or self._sort_key(candidate) < self._sort_key(current):
                        by_logic_behavior[dedupe_key] = candidate
        candidates = sorted(by_logic_behavior.values(), key=self._sort_key)
        return RadixMemorySearchReport(
            programs_generated=generated,
            programs_executed=executed,
            programs_rejected=rejected,
            behavior_classes=len(behavior_keys),
            evidence_weights=evidence_weights,
            cycle_width_candidates=self.cycle_width_candidates,
            top_candidates=tuple(candidates[: self.top_k]),
        )

    def _trace(self, width: int, row: tuple[float, ...]) -> _AnonymousTrace:
        parent = self.executor.parent_executor.execute(self.parent_program, row)
        integer_memory = _integer(parent.output_value, "parent integer memory")
        residual = _decimal(parent.parent_output_value)
        divisor = _decimal(parent.adapted_inputs[1])
        emissions: list[int] = []
        for _ in range(self.maximum_stages):
            scaled = _repeat_add(residual, width)
            stage = self.executor.parent_executor.execute(
                self.parent_program, (float(scaled), float(divisor))
            )
            emitted = _integer(stage.output_value, "stage emission")
            if emitted < 0 or emitted >= width:
                raise InvalidAdaptiveProgram("stage emission is outside the cycle width")
            emissions.append(emitted)
            residual = _decimal(stage.parent_output_value)
        return _AnonymousTrace(integer_memory, tuple(emissions))

    @staticmethod
    def _output(trace: _AnonymousTrace, weights: tuple[Decimal, ...]) -> Decimal:
        result = Decimal(trace.integer_memory)
        for emitted, weight in zip(trace.stage_emissions, weights, strict=False):
            result += _repeat_add(weight, emitted)
        return result

    @staticmethod
    def _coherence_error(width: int, weights: tuple[Decimal, ...]) -> Decimal:
        return sum(
            (
                abs(_repeat_add(weights[index + 1], width) - weights[index])
                for index in range(len(weights) - 1)
            ),
            Decimal(0),
        )

    @staticmethod
    def _sort_key(candidate: RadixMemoryCandidate) -> tuple[Any, ...]:
        return (
            candidate.fit_mse,
            candidate.maximum_absolute_error,
            candidate.coherence_error,
            len(candidate.program.stage_weights),
            candidate.program.node_count,
            candidate.candidate_id,
        )

    def _derive_weights(self, valid) -> tuple[dict[str, Any], ...]:
        values: dict[Decimal, dict[str, Any]] = {}
        for _, output in valid:
            magnitude = abs(output)
            if Decimal(0) < magnitude <= Decimal(1):
                values.setdefault(
                    magnitude,
                    {
                        "value": str(magnitude),
                        "provenance": {
                            "op": "observed_output_atom_magnitude",
                            "observed": str(output),
                        },
                    },
                )
        ordered = sorted(values.values(), key=lambda item: _decimal(item["value"]))
        return tuple(ordered[: self.maximum_weight_candidates])


def _integer(value: float, label: str) -> int:
    numeric = float(value)
    if not numeric.is_integer():
        raise InvalidAdaptiveProgram(f"{label} must be integral")
    return int(numeric)


def radix_memory_program_key(program: RadixMemoryProgram) -> str:
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))


def radix_memory_logic_signature(program: RadixMemoryProgram) -> str:
    value = {
        "parent": program.parent_operation_id,
        "cycle_width": program.cycle_width,
        "stage_weights": list(program.stage_weights),
        "stage_count": len(program.stage_weights),
    }
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return "RMLOGIC-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
