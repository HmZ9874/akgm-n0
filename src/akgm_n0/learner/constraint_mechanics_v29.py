"""Discover planar constraint metric, tangent generator, projection, and one-coordinate reconstruction."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Sequence

from .anonymous_physics_discovery_v22 import DirectedPhysicsRuntimeV22
from .directed_rational_construction_v21 import DirectedValueV21
from .planar_rotation_discovery_v26 import OrientedBilinearPolicyV26, PlanarRotationRuntimeV26

VectorV29 = tuple[DirectedValueV21, DirectedValueV21]


@dataclass(frozen=True, slots=True)
class ConstraintObservationV29:
    experiment_id: str
    position: VectorV29
    proposed_state: VectorV29
    observed_state: VectorV29

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "anonymous_position": [item.to_dict() for item in self.position],
            "anonymous_proposed_state": [item.to_dict() for item in self.proposed_state],
            "anonymous_observed_state": [item.to_dict() for item in self.observed_state],
            "human_constraint_name": None,
            "human_projection_formula": None,
            "human_coordinate_name": None,
        }


@dataclass(frozen=True, slots=True)
class MetricPolicyV29:
    atom_routes: tuple[str, str, str, str]

    @property
    def program_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "MET-" + hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {"substrate": "symmetric_four_atom_router_v29", "atom_routes": list(self.atom_routes), "human_operation_name": None}

    def render(self) -> str:
        return "MET<" + ",".join(self.atom_routes) + ">"


@dataclass(frozen=True, slots=True)
class TangentPolicyV29:
    output_0_source: int
    output_0_turn: bool
    output_1_source: int
    output_1_turn: bool

    @property
    def program_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "TAN-" + hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {"sources": [self.output_0_source, self.output_1_source], "turns": [self.output_0_turn, self.output_1_turn], "human_operation_name": None}

    def render(self) -> str:
        a = ("TURN<" if self.output_0_turn else "KEEP<") + f"q{self.output_0_source}>"
        b = ("TURN<" if self.output_1_turn else "KEEP<") + f"q{self.output_1_source}>"
        return f"TANGENT<{a},{b}>"


@dataclass(frozen=True, slots=True)
class ProjectionPolicyV29:
    turn_correction: bool
    denominator_route: str

    @property
    def program_id(self) -> str:
        return "PRJ-" + hashlib.sha256((str(self.turn_correction) + self.denominator_route).encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {"turn_correction": self.turn_correction, "denominator_route": self.denominator_route, "human_operation_name": None}

    def render(self) -> str:
        return f"PROJECT<{'TURN' if self.turn_correction else 'KEEP'};DEN:{self.denominator_route}>"


@dataclass(frozen=True, slots=True)
class ConstraintDiscoveryV29:
    metric_candidates_generated: int
    selected_metric: MetricPolicyV29
    tangent_candidates_generated: int
    selected_tangent: TangentPolicyV29
    projection_candidates_generated: int
    selected_projection: ProjectionPolicyV29
    training_cases: int

    @property
    def generalized_coordinate_count(self) -> int:
        return 1

    @property
    def ambient_state_coordinate_count(self) -> int:
        return 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_candidates_generated": self.metric_candidates_generated,
            "selected_metric": {"program_id": self.selected_metric.program_id, "opaque_program": self.selected_metric.render(), "policy": self.selected_metric.to_dict()},
            "tangent_candidates_generated": self.tangent_candidates_generated,
            "selected_tangent": {"program_id": self.selected_tangent.program_id, "opaque_program": self.selected_tangent.render(), "policy": self.selected_tangent.to_dict()},
            "projection_candidates_generated": self.projection_candidates_generated,
            "selected_projection": {"program_id": self.selected_projection.program_id, "opaque_program": self.selected_projection.render(), "policy": self.selected_projection.to_dict()},
            "training_cases": self.training_cases,
            "generalized_coordinate_count": 1,
            "ambient_state_coordinate_count": 2,
        }


class ConstraintRuntimeV29:
    ROUTES = ("ZERO", "KEEP", "TURN")

    def __init__(self, physics: DirectedPhysicsRuntimeV22, oriented_policy: OrientedBilinearPolicyV26) -> None:
        self.physics = physics
        self.oriented = PlanarRotationRuntimeV26(physics)
        self.oriented_policy = oriented_policy

    def metric(self, policy: MetricPolicyV29, left: VectorV29, right: VectorV29) -> DirectedValueV21:
        atoms = (self._interact(left[0], right[0]), self._interact(left[0], right[1]), self._interact(left[1], right[0]), self._interact(left[1], right[1]))
        result = self.physics.zero
        for route, atom in zip(policy.atom_routes, atoms, strict=True):
            term = self.physics.zero if route == "ZERO" else atom if route == "KEEP" else self._inverse(atom)
            result = self._combine(result, term)
        return result

    def tangent(self, policy: TangentPolicyV29, position: VectorV29) -> VectorV29:
        outputs = []
        for source, turn in ((policy.output_0_source, policy.output_0_turn), (policy.output_1_source, policy.output_1_turn)):
            value = position[source]
            outputs.append(self._inverse(value) if turn else value)
        return outputs[0], outputs[1]

    def project(self, policy: ProjectionPolicyV29, metric: MetricPolicyV29, position: VectorV29, proposed: VectorV29) -> VectorV29 | None:
        radial = self.metric(metric, position, proposed)
        divisor = self.physics.one if policy.denominator_route == "ONE" else self.metric(metric, position, position)
        scale = self.divide_positive(radial, divisor)
        if scale is None:
            return None
        correction = (self._interact(position[0], scale), self._interact(position[1], scale))
        if policy.turn_correction:
            correction = (self._inverse(correction[0]), self._inverse(correction[1]))
        return self._combine(proposed[0], correction[0]), self._combine(proposed[1], correction[1])

    def generalized_scalar(self, metric: MetricPolicyV29, tangent: VectorV29, state: VectorV29) -> DirectedValueV21 | None:
        return self.divide_positive(self.metric(metric, tangent, state), self.metric(metric, tangent, tangent))

    def reconstruct(self, tangent: VectorV29, scalar: DirectedValueV21) -> VectorV29:
        return self._interact(tangent[0], scalar), self._interact(tangent[1], scalar)

    def divide_positive(self, value: DirectedValueV21, divisor: DirectedValueV21) -> DirectedValueV21 | None:
        divisor = self.physics.normalize(divisor)
        if divisor.negative or divisor.positive <= 0:
            return None
        base = self.physics.directed.base
        return self.physics.normalize(DirectedValueV21(base.omega(value.positive, divisor.denominator), base.omega(value.negative, divisor.denominator), base.omega(value.denominator, divisor.positive)))

    def _combine(self, a: DirectedValueV21, b: DirectedValueV21) -> DirectedValueV21:
        return self.physics.normalize(self.physics.directed.execute_binary(self.physics.combine, a, b))

    def _interact(self, a: DirectedValueV21, b: DirectedValueV21) -> DirectedValueV21:
        return self.physics.normalize(self.physics.directed.execute_binary(self.physics.interact, a, b))

    def _inverse(self, value: DirectedValueV21) -> DirectedValueV21:
        return self.physics.normalize(self.physics.directed.execute_unary(self.physics.inverse, value))


class ConstraintMechanicsResearchV29:
    def discover(self, rows: Sequence[ConstraintObservationV29], runtime: ConstraintRuntimeV29) -> ConstraintDiscoveryV29:
        metrics = tuple(MetricPolicyV29(tuple(routes)) for routes in itertools.product(runtime.ROUTES, repeat=4))
        selected_metrics = [item for item in metrics if self._metric_laws(item, runtime)]
        if len(selected_metrics) != 1:
            raise RuntimeError(f"expected one metric, found {len(selected_metrics)}")
        metric = selected_metrics[0]
        tangents = tuple(TangentPolicyV29(a, ta, b, tb) for a, ta, b, tb in itertools.product((0, 1), (False, True), (0, 1), (False, True)))
        selected_tangents = [item for item in tangents if self._tangent_laws(item, metric, runtime)]
        if len(selected_tangents) != 1:
            raise RuntimeError(f"expected one oriented tangent, found {len(selected_tangents)}")
        tangent = selected_tangents[0]
        projections = tuple(ProjectionPolicyV29(turn, denominator) for turn, denominator in itertools.product((False, True), ("ONE", "MET<R,R>")))
        selected_projections = [item for item in projections if all(self._row_holds(item, metric, row, runtime) for row in rows)]
        if len(selected_projections) != 1:
            raise RuntimeError(f"expected one projection, found {len(selected_projections)}")
        return ConstraintDiscoveryV29(len(metrics), metric, len(tangents), tangent, len(projections), selected_projections[0], len(rows))

    @staticmethod
    def _metric_laws(policy: MetricPolicyV29, runtime: ConstraintRuntimeV29) -> bool:
        z, o = runtime.physics.zero, runtime.physics.one
        e0, e1 = (o, z), (z, o)
        return all((
            runtime.physics.equivalent(runtime.metric(policy, e0, e0), o),
            runtime.physics.equivalent(runtime.metric(policy, e1, e1), o),
            runtime.physics.equivalent(runtime.metric(policy, e0, e1), z),
            runtime.physics.equivalent(runtime.metric(policy, e1, e0), z),
        ))

    @staticmethod
    def _tangent_laws(policy: TangentPolicyV29, metric: MetricPolicyV29, runtime: ConstraintRuntimeV29) -> bool:
        z, o = runtime.physics.zero, runtime.physics.one
        samples = ((o, z), (z, o), (o, o), (runtime._inverse(o), o))
        for r in samples:
            t = runtime.tangent(policy, r)
            if not runtime.physics.equivalent(runtime.metric(metric, r, t), z):
                return False
            if not runtime.physics.equivalent(runtime.metric(metric, r, r), runtime.metric(metric, t, t)):
                return False
            if not runtime.physics.equivalent(runtime.oriented.bilinear(runtime.oriented_policy, r, t), runtime.metric(metric, r, r)):
                return False
        return True

    @staticmethod
    def _row_holds(policy: ProjectionPolicyV29, metric: MetricPolicyV29, row: ConstraintObservationV29, runtime: ConstraintRuntimeV29) -> bool:
        predicted = runtime.project(policy, metric, row.position, row.proposed_state)
        return predicted is not None and all(runtime.physics.equivalent(a, b) for a, b in zip(predicted, row.observed_state, strict=True))
