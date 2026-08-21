"""Discover parameter-dependent response and weighted conservation from opaque rows."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Sequence

from .anonymous_physics_discovery_v22 import DirectedPhysicsRuntimeV22, PhysicalExpressionV22
from .directed_rational_construction_v21 import DirectedValueV21


@dataclass(frozen=True, slots=True)
class ResponseObservationV24:
    experiment_id: str
    counter_parameter: int
    input_value: DirectedValueV21
    observed_value: DirectedValueV21

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "anonymous_inputs": [self.counter_parameter, self.input_value.to_dict()],
            "anonymous_output": self.observed_value.to_dict(),
            "human_channel_names": None,
            "human_formula": None,
        }


@dataclass(frozen=True, slots=True)
class ExchangeObservationV24:
    experiment_id: str
    before: tuple[DirectedValueV21, ...]
    after: tuple[DirectedValueV21, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "before": [item.to_dict() for item in self.before],
            "after": [item.to_dict() for item in self.after],
            "human_channel_names": None,
            "human_formula": None,
        }


@dataclass(frozen=True, slots=True)
class ResponsePolicyV24:
    swap_direction_channels: bool
    denominator_program: str

    @property
    def program_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "RSP-" + hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "direction_router_plus_counter_denominator_v24",
            "swap_direction_channels": self.swap_direction_channels,
            "denominator_program": self.denominator_program,
            "human_operation_name": None,
        }

    def render(self) -> str:
        direction = "SWAP" if self.swap_direction_channels else "KEEP"
        return f"RESP<{direction},DEN:{self.denominator_program}>"


@dataclass(frozen=True, slots=True)
class ResponseCandidateV24:
    policy: ResponsePolicyV24
    training_cases: int
    signature: tuple[tuple[int, int, int], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.policy.program_id,
            "policy": self.policy.to_dict(),
            "opaque_program": self.policy.render(),
            "training_cases": self.training_cases,
            "behavior_signature": [list(item) for item in self.signature],
        }


@dataclass(frozen=True, slots=True)
class WeightedInvariantV24:
    expression: PhysicalExpressionV22
    training_cases: int
    changed_channels: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "invariant_id": self.expression.expression_id,
            "expression": self.expression.to_dict(),
            "opaque_program": self.expression.render(),
            "training_cases": self.training_cases,
            "changed_channels": list(self.changed_channels),
            "human_quantity_name": None,
        }


@dataclass(frozen=True, slots=True)
class InertialDiscoveryV24:
    response_candidates_generated: int
    response_behavior_classes: int
    selected_response: ResponseCandidateV24
    invariant_candidates_generated: int
    selected_invariant: WeightedInvariantV24
    dimension_constraints: tuple[str, ...]
    response_training_cases: int
    exchange_training_cases: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_candidates_generated": self.response_candidates_generated,
            "response_behavior_classes": self.response_behavior_classes,
            "selected_response": self.selected_response.to_dict(),
            "invariant_candidates_generated": self.invariant_candidates_generated,
            "selected_invariant": self.selected_invariant.to_dict(),
            "dimension_constraints": list(self.dimension_constraints),
            "response_training_cases": self.response_training_cases,
            "exchange_training_cases": self.exchange_training_cases,
        }


class InertialResponseRuntimeV24:
    """Executes candidate structures using only the already-discovered counter substrate."""

    def __init__(self, physics: DirectedPhysicsRuntimeV22) -> None:
        self.physics = physics

    def execute_response(
        self,
        policy: ResponsePolicyV24,
        counter_parameter: int,
        value: DirectedValueV21,
    ) -> DirectedValueV21:
        positive, negative = value.positive, value.negative
        if policy.swap_direction_channels:
            positive, negative = negative, positive
        base = self.physics.directed.base
        if policy.denominator_program == "D":
            denominator = value.denominator
        elif policy.denominator_program == "P":
            denominator = counter_parameter
        elif policy.denominator_program == "SEM<D,P>":
            denominator = base.omega(value.denominator, counter_parameter)
        elif policy.denominator_program == "MERGE<D,P>":
            denominator = base.merge(value.denominator, counter_parameter)
        elif policy.denominator_program == "ONE":
            denominator = 1
        else:
            raise ValueError("unknown denominator program")
        return self.physics.normalize(DirectedValueV21(positive, negative, denominator))


class InertialResponseResearchV24:
    DENOMINATOR_PROGRAMS = ("D", "P", "SEM<D,P>", "MERGE<D,P>", "ONE")

    def discover(
        self,
        response_rows: Sequence[ResponseObservationV24],
        exchange_rows: Sequence[ExchangeObservationV24],
        runtime: InertialResponseRuntimeV24,
    ) -> InertialDiscoveryV24:
        if not response_rows or not exchange_rows:
            raise ValueError("both anonymous experiment families are required")
        policies = tuple(
            ResponsePolicyV24(swap, denominator)
            for swap in (False, True)
            for denominator in self.DENOMINATOR_PROGRAMS
        )
        by_signature: dict[tuple[tuple[int, int, int], ...], ResponseCandidateV24] = {}
        passing: list[ResponseCandidateV24] = []
        for policy in policies:
            outputs = tuple(
                runtime.execute_response(policy, row.counter_parameter, row.input_value)
                for row in response_rows
            )
            signature = tuple(item.to_tuple() for item in outputs)
            candidate = ResponseCandidateV24(policy, len(response_rows), signature)
            by_signature.setdefault(signature, candidate)
            if all(
                runtime.physics.equivalent(output, row.observed_value)
                for output, row in zip(outputs, response_rows, strict=True)
            ):
                passing.append(candidate)
        if len(passing) != 1:
            raise RuntimeError(f"expected one response program, found {len(passing)}")

        invariant_expressions = self._invariant_expressions()
        conserved = [
            expression for expression in invariant_expressions
            if all(
                runtime.physics.equivalent(
                    runtime.physics.evaluate(expression, row.before),
                    runtime.physics.evaluate(expression, row.after),
                )
                for row in exchange_rows
            )
        ]
        if len(conserved) != 1:
            raise RuntimeError(f"expected one weighted invariant, found {len(conserved)}")
        changed = tuple(
            channel for channel in range(4)
            if any(
                not runtime.physics.equivalent(row.before[channel], row.after[channel])
                for row in exchange_rows
            )
        )
        invariant = WeightedInvariantV24(conserved[0], len(exchange_rows), changed)
        return InertialDiscoveryV24(
            response_candidates_generated=len(policies),
            response_behavior_classes=len(by_signature),
            selected_response=passing[0],
            invariant_candidates_generated=len(invariant_expressions),
            selected_invariant=invariant,
            dimension_constraints=("D2=(D0+D1)", "D4=(D0+D3)"),
            response_training_cases=len(response_rows),
            exchange_training_cases=len(exchange_rows),
        )

    @staticmethod
    def _invariant_expressions() -> tuple[PhysicalExpressionV22, ...]:
        def read(channel: int) -> PhysicalExpressionV22:
            return PhysicalExpressionV22("read", channel=channel)

        def product(left: int, right: int) -> PhysicalExpressionV22:
            return PhysicalExpressionV22("interact", (read(left), read(right)))

        return tuple(
            PhysicalExpressionV22("combine", (product(a, b), product(c, d)))
            for (a, b), (c, d) in (
                ((0, 1), (2, 3)),
                ((0, 2), (1, 3)),
                ((0, 3), (1, 2)),
            )
        )
