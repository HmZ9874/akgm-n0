"""Search anonymous two-entity collision programs and conserved expressions."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Sequence

from .anonymous_physics_discovery_v22 import DirectedPhysicsRuntimeV22, PhysicalExpressionV22
from .directed_rational_construction_v21 import DirectedValueV21


@dataclass(frozen=True, slots=True)
class CollisionObservationV25:
    experiment_id: str
    before: tuple[DirectedValueV21, ...]
    after: tuple[DirectedValueV21, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "before": [item.to_dict() for item in self.before],
            "after": [item.to_dict() for item in self.after],
            "human_channel_names": None,
            "human_collision_formula": None,
            "human_conservation_names": None,
        }


@dataclass(frozen=True, slots=True)
class CollisionPolicyV25:
    atom_routes: tuple[str, str, str, str]
    denominator_route: str

    @property
    def program_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "COL-" + hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "four_weighted_atoms_plus_denominator_router_v25",
            "atom_routes": list(self.atom_routes),
            "denominator_route": self.denominator_route,
            "human_operation_name": None,
        }

    def render(self) -> str:
        return "COL<" + ",".join(self.atom_routes) + f";DEN:{self.denominator_route}>"


@dataclass(frozen=True, slots=True)
class CollisionProgramV25:
    output_channel: int
    policy: CollisionPolicyV25
    training_cases: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_channel": self.output_channel,
            "program_id": self.policy.program_id,
            "policy": self.policy.to_dict(),
            "opaque_program": self.policy.render(),
            "training_cases": self.training_cases,
            "human_collision_law": None,
        }


@dataclass(frozen=True, slots=True)
class CollisionInvariantV25:
    expression: PhysicalExpressionV22
    invariant_family: str
    training_cases: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "invariant_id": self.expression.expression_id,
            "invariant_family": self.invariant_family,
            "expression": self.expression.to_dict(),
            "opaque_program": self.expression.render(),
            "training_cases": self.training_cases,
            "human_quantity_name": None,
        }


@dataclass(frozen=True, slots=True)
class CollisionMechanicsDiscoveryV25:
    candidates_per_output: int
    selected_programs: tuple[CollisionProgramV25, CollisionProgramV25]
    quadratic_invariant_candidates: int
    selected_quadratic_invariant: CollisionInvariantV25
    inherited_linear_invariant: CollisionInvariantV25
    collision_training_cases: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidates_per_output": self.candidates_per_output,
            "selected_programs": [item.to_dict() for item in self.selected_programs],
            "quadratic_invariant_candidates": self.quadratic_invariant_candidates,
            "selected_quadratic_invariant": self.selected_quadratic_invariant.to_dict(),
            "inherited_linear_invariant": self.inherited_linear_invariant.to_dict(),
            "collision_training_cases": self.collision_training_cases,
        }


class CollisionMechanicsRuntimeV25:
    ROUTES = ("ZERO", "KEEP", "TURN", "DOUBLE")
    DENOMINATORS = ("ONE", "Q0", "Q2", "MERGE<Q0,Q2>", "SEM<Q0,Q2>")

    def __init__(self, physics: DirectedPhysicsRuntimeV22) -> None:
        self.physics = physics

    def execute(self, policy: CollisionPolicyV25, state: Sequence[DirectedValueV21]) -> DirectedValueV21:
        if len(state) != 4:
            raise ValueError("V25 collision state requires four anonymous channels")
        q0, q1, q2, q3 = state
        atoms = (
            self._interact(q0, q1), self._interact(q2, q1),
            self._interact(q0, q3), self._interact(q2, q3),
        )
        numerator = self.physics.zero
        for route, atom in zip(policy.atom_routes, atoms, strict=True):
            numerator = self._combine(numerator, self._route(route, atom))
        base = self.physics.directed.base
        if policy.denominator_route == "ONE":
            denominator = 1
        elif policy.denominator_route == "Q0":
            denominator = q0.positive
        elif policy.denominator_route == "Q2":
            denominator = q2.positive
        elif policy.denominator_route == "MERGE<Q0,Q2>":
            denominator = base.merge(q0.positive, q2.positive)
        elif policy.denominator_route == "SEM<Q0,Q2>":
            denominator = base.omega(q0.positive, q2.positive)
        else:
            raise ValueError("unknown collision denominator route")
        expanded = DirectedValueV21(
            numerator.positive,
            numerator.negative,
            base.omega(numerator.denominator, denominator),
        )
        return self.physics.normalize(expanded)

    def _route(self, route: str, atom: DirectedValueV21) -> DirectedValueV21:
        if route == "ZERO":
            return self.physics.zero
        if route == "KEEP":
            return atom
        if route == "TURN":
            return self.physics.normalize(self.physics.directed.execute_unary(self.physics.inverse, atom))
        if route == "DOUBLE":
            return self._combine(atom, atom)
        raise ValueError("unknown atom route")

    def _combine(self, left: DirectedValueV21, right: DirectedValueV21) -> DirectedValueV21:
        return self.physics.normalize(self.physics.directed.execute_binary(self.physics.combine, left, right))

    def _interact(self, left: DirectedValueV21, right: DirectedValueV21) -> DirectedValueV21:
        return self.physics.normalize(self.physics.directed.execute_binary(self.physics.interact, left, right))


class CollisionMechanicsResearchV25:
    def discover(
        self,
        rows: Sequence[CollisionObservationV25],
        runtime: CollisionMechanicsRuntimeV25,
    ) -> CollisionMechanicsDiscoveryV25:
        if not rows:
            raise ValueError("anonymous collision experiments are required")
        policies = tuple(
            CollisionPolicyV25(tuple(routes), denominator)
            for routes in itertools.product(runtime.ROUTES, repeat=4)
            for denominator in runtime.DENOMINATORS
        )
        selected = tuple(self._search_output(output, policies, rows, runtime) for output in (1, 3))
        quadratic = self._quadratic_candidates()
        conserved = [item for item in quadratic if self._conserved(item, rows, runtime.physics)]
        if len(conserved) != 1:
            raise RuntimeError(f"expected one quadratic invariant, found {len(conserved)}")
        linear = PhysicalExpressionV22("combine", (
            PhysicalExpressionV22("interact", (self._read(0), self._read(1))),
            PhysicalExpressionV22("interact", (self._read(2), self._read(3))),
        ))
        if not self._conserved(linear, rows, runtime.physics):
            raise RuntimeError("V24 weighted linear invariant did not transfer to collisions")
        return CollisionMechanicsDiscoveryV25(
            candidates_per_output=len(policies),
            selected_programs=(selected[0], selected[1]),
            quadratic_invariant_candidates=len(quadratic),
            selected_quadratic_invariant=CollisionInvariantV25(conserved[0], "QF1", len(rows)),
            inherited_linear_invariant=CollisionInvariantV25(linear, "LF0", len(rows)),
            collision_training_cases=len(rows),
        )

    @staticmethod
    def _search_output(
        output: int,
        policies: Sequence[CollisionPolicyV25],
        rows: Sequence[CollisionObservationV25],
        runtime: CollisionMechanicsRuntimeV25,
    ) -> CollisionProgramV25:
        passing = []
        for policy in policies:
            if all(runtime.physics.equivalent(runtime.execute(policy, row.before), row.after[output]) for row in rows):
                passing.append(policy)
        if len(passing) != 1:
            raise RuntimeError(f"expected one collision program for q{output}, found {len(passing)}")
        return CollisionProgramV25(output, passing[0], len(rows))

    @staticmethod
    def _read(channel: int) -> PhysicalExpressionV22:
        return PhysicalExpressionV22("read", channel=channel)

    @classmethod
    def _quadratic_candidates(cls) -> tuple[PhysicalExpressionV22, ...]:
        atoms = []
        for parameter in (0, 2):
            for state in (1, 3):
                square = PhysicalExpressionV22("interact", (cls._read(state), cls._read(state)))
                atoms.append(PhysicalExpressionV22("interact", (cls._read(parameter), square)))
        return tuple(
            PhysicalExpressionV22("combine", (atoms[left], atoms[right]))
            for left in range(len(atoms)) for right in range(left + 1, len(atoms))
        )

    @staticmethod
    def _conserved(
        expression: PhysicalExpressionV22,
        rows: Sequence[CollisionObservationV25],
        physics: DirectedPhysicsRuntimeV22,
    ) -> bool:
        return all(physics.equivalent(
            physics.evaluate(expression, row.before), physics.evaluate(expression, row.after)
        ) for row in rows)
