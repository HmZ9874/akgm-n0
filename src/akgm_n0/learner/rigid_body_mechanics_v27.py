"""Discover fixed-axis rigid-body inertia and reuse collision search for rotation."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Sequence

from .anonymous_physics_discovery_v22 import DirectedPhysicsRuntimeV22
from .collision_mechanics_discovery_v25 import (
    CollisionMechanicsDiscoveryV25,
    CollisionMechanicsResearchV25,
    CollisionMechanicsRuntimeV25,
    CollisionObservationV25,
)
from .directed_rational_construction_v21 import DirectedValueV21


@dataclass(frozen=True, slots=True)
class RigidPointV27:
    q0: DirectedValueV21
    q1: DirectedValueV21
    q2: DirectedValueV21

    def to_dict(self) -> dict[str, Any]:
        return {"channels": [self.q0.to_dict(), self.q1.to_dict(), self.q2.to_dict()], "human_channel_names": None}


@dataclass(frozen=True, slots=True)
class RigidBodyObservationV27:
    experiment_id: str
    points: tuple[RigidPointV27, ...]
    before_state: DirectedValueV21
    action: DirectedValueV21
    after_state: DirectedValueV21

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "points": [item.to_dict() for item in self.points],
            "before_state": self.before_state.to_dict(),
            "action": self.action.to_dict(),
            "after_state": self.after_state.to_dict(),
            "human_formula": None,
            "human_quantity_names": None,
        }


@dataclass(frozen=True, slots=True)
class InertiaAggregatePolicyV27:
    q0_route: str
    q12_route: str

    @property
    def program_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "INA-" + hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "point_aggregate_router_v27",
            "q0_route": self.q0_route,
            "q12_route": self.q12_route,
            "human_quantity_name": None,
        }

    def render(self) -> str:
        return f"AGG<{self.q0_route},{self.q12_route}>"


@dataclass(frozen=True, slots=True)
class AngularQuantityV27:
    weight_route: str
    aggregate_policy: InertiaAggregatePolicyV27

    @property
    def program_id(self) -> str:
        return "ANQ-" + hashlib.sha256((self.weight_route + self.aggregate_policy.program_id).encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "weight_route": self.weight_route,
            "aggregate_program_id": self.aggregate_policy.program_id,
            "opaque_program": f"ANQ<{self.weight_route},{self.aggregate_policy.render()}>",
            "human_quantity_name": None,
        }


@dataclass(frozen=True, slots=True)
class RigidBodyDiscoveryV27:
    aggregate_candidates_generated: int
    selected_aggregate: InertiaAggregatePolicyV27
    angular_weight_candidates_generated: int
    selected_angular_quantity: AngularQuantityV27
    angular_collision: CollisionMechanicsDiscoveryV25
    body_training_cases: int
    angular_collision_training_cases: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "aggregate_candidates_generated": self.aggregate_candidates_generated,
            "selected_aggregate": {
                "program_id": self.selected_aggregate.program_id,
                "policy": self.selected_aggregate.to_dict(),
                "opaque_program": self.selected_aggregate.render(),
            },
            "angular_weight_candidates_generated": self.angular_weight_candidates_generated,
            "selected_angular_quantity": self.selected_angular_quantity.to_dict(),
            "angular_collision": self.angular_collision.to_dict(),
            "body_training_cases": self.body_training_cases,
            "angular_collision_training_cases": self.angular_collision_training_cases,
        }


class RigidBodyRuntimeV27:
    Q0_ROUTES = ("ONE", "Q0", "SEM<Q0,Q0>")
    Q12_ROUTES = ("SEM<Q1,Q1>", "SEM<Q2,Q2>", "MERGE<SEM<Q1,Q1>,SEM<Q2,Q2>>", "SEM<Q1,Q2>")
    ANGULAR_WEIGHTS = ("ONE", "AGG", "SEM<AGG,AGG>")

    def __init__(self, physics: DirectedPhysicsRuntimeV22) -> None:
        self.physics = physics

    def aggregate(self, policy: InertiaAggregatePolicyV27, points: Sequence[RigidPointV27]) -> DirectedValueV21:
        total = self.physics.zero
        for point in points:
            q0_factor = self._q0_factor(policy.q0_route, point)
            q12_factor = self._q12_factor(policy.q12_route, point)
            total = self._combine(total, self._interact(q0_factor, q12_factor))
        return total

    def response(self, aggregate: DirectedValueV21, action: DirectedValueV21) -> DirectedValueV21 | None:
        normalized = self.physics.normalize(aggregate)
        if normalized.negative or normalized.denominator != 1 or normalized.positive <= 0:
            return None
        denominator = self.physics.directed.base.omega(action.denominator, normalized.positive)
        return self.physics.normalize(DirectedValueV21(action.positive, action.negative, denominator))

    def angular_quantity(
        self,
        quantity: AngularQuantityV27,
        points: Sequence[RigidPointV27],
        state: DirectedValueV21,
    ) -> DirectedValueV21:
        aggregate = self.aggregate(quantity.aggregate_policy, points)
        if quantity.weight_route == "ONE":
            return state
        if quantity.weight_route == "AGG":
            return self._interact(aggregate, state)
        if quantity.weight_route == "SEM<AGG,AGG>":
            return self._interact(self._interact(aggregate, aggregate), state)
        raise ValueError("unknown angular weight route")

    def _q0_factor(self, route: str, point: RigidPointV27) -> DirectedValueV21:
        if route == "ONE":
            return self.physics.one
        if route == "Q0":
            return point.q0
        if route == "SEM<Q0,Q0>":
            return self._interact(point.q0, point.q0)
        raise ValueError("unknown q0 route")

    def _q12_factor(self, route: str, point: RigidPointV27) -> DirectedValueV21:
        q1_square = self._interact(point.q1, point.q1)
        q2_square = self._interact(point.q2, point.q2)
        if route == "SEM<Q1,Q1>":
            return q1_square
        if route == "SEM<Q2,Q2>":
            return q2_square
        if route == "MERGE<SEM<Q1,Q1>,SEM<Q2,Q2>>":
            return self._combine(q1_square, q2_square)
        if route == "SEM<Q1,Q2>":
            return self._interact(point.q1, point.q2)
        raise ValueError("unknown q12 route")

    def _combine(self, left: DirectedValueV21, right: DirectedValueV21) -> DirectedValueV21:
        return self.physics.normalize(self.physics.directed.execute_binary(self.physics.combine, left, right))

    def _interact(self, left: DirectedValueV21, right: DirectedValueV21) -> DirectedValueV21:
        return self.physics.normalize(self.physics.directed.execute_binary(self.physics.interact, left, right))

    def difference(self, after: DirectedValueV21, before: DirectedValueV21) -> DirectedValueV21:
        inverse = self.physics.normalize(self.physics.directed.execute_unary(self.physics.inverse, before))
        return self._combine(after, inverse)


class RigidBodyMechanicsResearchV27:
    def discover(
        self,
        body_rows: Sequence[RigidBodyObservationV27],
        angular_collision_rows: Sequence[CollisionObservationV25],
        runtime: RigidBodyRuntimeV27,
    ) -> RigidBodyDiscoveryV27:
        policies = tuple(
            InertiaAggregatePolicyV27(q0_route, q12_route)
            for q0_route, q12_route in itertools.product(runtime.Q0_ROUTES, runtime.Q12_ROUTES)
        )
        passing = [policy for policy in policies if self._response_rows_hold(policy, body_rows, runtime)]
        if len(passing) != 1:
            raise RuntimeError(f"expected one rigid aggregate, found {len(passing)}")
        selected = passing[0]
        quantities = tuple(AngularQuantityV27(weight, selected) for weight in runtime.ANGULAR_WEIGHTS)
        balanced = [item for item in quantities if self._angular_balance_holds(item, body_rows, runtime)]
        if len(balanced) != 1:
            raise RuntimeError(f"expected one angular quantity, found {len(balanced)}")
        collision_runtime = CollisionMechanicsRuntimeV25(runtime.physics)
        angular_collision = CollisionMechanicsResearchV25().discover(angular_collision_rows, collision_runtime)
        return RigidBodyDiscoveryV27(
            len(policies), selected, len(quantities), balanced[0], angular_collision,
            len(body_rows), len(angular_collision_rows),
        )

    @staticmethod
    def _response_rows_hold(
        policy: InertiaAggregatePolicyV27,
        rows: Sequence[RigidBodyObservationV27],
        runtime: RigidBodyRuntimeV27,
    ) -> bool:
        for row in rows:
            aggregate = runtime.aggregate(policy, row.points)
            response = runtime.response(aggregate, row.action)
            if response is None:
                return False
            predicted = runtime._combine(row.before_state, response)
            if not runtime.physics.equivalent(predicted, row.after_state):
                return False
        return True

    @staticmethod
    def _angular_balance_holds(
        quantity: AngularQuantityV27,
        rows: Sequence[RigidBodyObservationV27],
        runtime: RigidBodyRuntimeV27,
    ) -> bool:
        for row in rows:
            before = runtime.angular_quantity(quantity, row.points, row.before_state)
            after = runtime.angular_quantity(quantity, row.points, row.after_state)
            if not runtime.physics.equivalent(runtime.difference(after, before), row.action):
                return False
        return True
