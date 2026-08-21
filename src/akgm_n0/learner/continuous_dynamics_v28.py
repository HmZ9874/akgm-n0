"""Discover refinement-stable first and second time operators from anonymous stencils."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Sequence

from .anonymous_physics_discovery_v22 import DirectedPhysicsRuntimeV22
from .directed_rational_construction_v21 import DirectedValueV21


@dataclass(frozen=True, slots=True)
class StencilObservationV28:
    experiment_id: str
    samples: tuple[DirectedValueV21, DirectedValueV21, DirectedValueV21]
    interval: DirectedValueV21
    target_0: DirectedValueV21
    target_1: DirectedValueV21

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "anonymous_samples": [item.to_dict() for item in self.samples],
            "anonymous_interval": self.interval.to_dict(),
            "anonymous_targets": [self.target_0.to_dict(), self.target_1.to_dict()],
            "human_operator_names": None,
            "human_formulas": None,
        }


@dataclass(frozen=True, slots=True)
class RefinementObservationV28:
    experiment_id: str
    coarse_error: DirectedValueV21
    refined_error: DirectedValueV21
    refinement_factor: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "coarse_error": self.coarse_error.to_dict(),
            "refined_error": self.refined_error.to_dict(),
            "refinement_factor": self.refinement_factor,
            "human_convergence_order": None,
        }


@dataclass(frozen=True, slots=True)
class StencilPolicyV28:
    sample_routes: tuple[str, str, str]
    interval_power: int
    divisor_scale: int

    @property
    def program_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "STN-" + hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "three_sample_interval_router_v28",
            "sample_routes": list(self.sample_routes),
            "interval_power": self.interval_power,
            "divisor_scale": self.divisor_scale,
            "human_operator_name": None,
        }

    def render(self) -> str:
        return f"STENCIL<{','.join(self.sample_routes)};H^{self.interval_power};S{self.divisor_scale}>"


@dataclass(frozen=True, slots=True)
class ContinuousDynamicsDiscoveryV28:
    candidates_per_target: int
    selected_target_0: StencilPolicyV28
    selected_target_1: StencilPolicyV28
    refinement_orders_tested: tuple[int, ...]
    selected_refinement_order: int
    training_cases: int
    refinement_cases: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidates_per_target": self.candidates_per_target,
            "selected_target_0": {"program_id": self.selected_target_0.program_id, "opaque_program": self.selected_target_0.render(), "policy": self.selected_target_0.to_dict()},
            "selected_target_1": {"program_id": self.selected_target_1.program_id, "opaque_program": self.selected_target_1.render(), "policy": self.selected_target_1.to_dict()},
            "refinement_orders_tested": list(self.refinement_orders_tested),
            "selected_refinement_order": self.selected_refinement_order,
            "training_cases": self.training_cases,
            "refinement_cases": self.refinement_cases,
        }


class StencilRuntimeV28:
    ROUTES = ("TURN_DOUBLE", "TURN", "ZERO", "KEEP", "DOUBLE")

    def __init__(self, physics: DirectedPhysicsRuntimeV22) -> None:
        self.physics = physics

    def execute(self, policy: StencilPolicyV28, row: StencilObservationV28) -> DirectedValueV21 | None:
        numerator = self.physics.zero
        for route, sample in zip(policy.sample_routes, row.samples, strict=True):
            numerator = self._combine(numerator, self._route(route, sample))
        divisor = DirectedValueV21(policy.divisor_scale, 0, 1)
        for _ in range(policy.interval_power):
            divisor = self._interact(divisor, row.interval)
        return self.divide_by_positive(numerator, divisor)

    def divide_by_positive(self, value: DirectedValueV21, divisor: DirectedValueV21) -> DirectedValueV21 | None:
        divisor = self.physics.normalize(divisor)
        if divisor.negative or divisor.positive <= 0:
            return None
        base = self.physics.directed.base
        return self.physics.normalize(DirectedValueV21(
            base.omega(value.positive, divisor.denominator),
            base.omega(value.negative, divisor.denominator),
            base.omega(value.denominator, divisor.positive),
        ))

    def scale_natural(self, value: DirectedValueV21, factor: int) -> DirectedValueV21:
        return self._interact(value, DirectedValueV21(factor, 0, 1))

    def _route(self, route: str, value: DirectedValueV21) -> DirectedValueV21:
        if route == "ZERO":
            return self.physics.zero
        if route == "KEEP":
            return value
        if route == "TURN":
            return self.physics.normalize(self.physics.directed.execute_unary(self.physics.inverse, value))
        if route == "DOUBLE":
            return self._combine(value, value)
        if route == "TURN_DOUBLE":
            doubled = self._combine(value, value)
            return self.physics.normalize(self.physics.directed.execute_unary(self.physics.inverse, doubled))
        raise ValueError("unknown stencil route")

    def _combine(self, left: DirectedValueV21, right: DirectedValueV21) -> DirectedValueV21:
        return self.physics.normalize(self.physics.directed.execute_binary(self.physics.combine, left, right))

    def _interact(self, left: DirectedValueV21, right: DirectedValueV21) -> DirectedValueV21:
        return self.physics.normalize(self.physics.directed.execute_binary(self.physics.interact, left, right))


class ContinuousDynamicsResearchV28:
    def discover(
        self,
        rows: Sequence[StencilObservationV28],
        refinement_rows: Sequence[RefinementObservationV28],
        runtime: StencilRuntimeV28,
    ) -> ContinuousDynamicsDiscoveryV28:
        policies = tuple(
            StencilPolicyV28(tuple(routes), power, scale)
            for routes in itertools.product(runtime.ROUTES, repeat=3)
            for power in (0, 1, 2)
            for scale in (1, 2)
        )
        selected = tuple(self._search_target(index, policies, rows, runtime) for index in (0, 1))
        orders = (1, 2, 3, 4)
        passing_orders = [order for order in orders if all(runtime.physics.equivalent(
            runtime.scale_natural(row.refined_error, row.refinement_factor ** order), row.coarse_error
        ) for row in refinement_rows)]
        if len(passing_orders) != 1:
            raise RuntimeError(f"expected one refinement order, found {len(passing_orders)}")
        return ContinuousDynamicsDiscoveryV28(
            len(policies), selected[0], selected[1], orders, passing_orders[0], len(rows), len(refinement_rows)
        )

    @staticmethod
    def _search_target(
        target_index: int,
        policies: Sequence[StencilPolicyV28],
        rows: Sequence[StencilObservationV28],
        runtime: StencilRuntimeV28,
    ) -> StencilPolicyV28:
        passing = []
        for policy in policies:
            valid = True
            for row in rows:
                predicted = runtime.execute(policy, row)
                target = row.target_0 if target_index == 0 else row.target_1
                if predicted is None or not runtime.physics.equivalent(predicted, target):
                    valid = False
                    break
            if valid:
                passing.append(policy)
        if len(passing) != 1:
            raise RuntimeError(f"expected one stencil for target {target_index}, found {len(passing)}")
        return passing[0]
