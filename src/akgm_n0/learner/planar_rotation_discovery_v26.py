"""Discover an oriented planar bilinear operation and a weighted rotation balance."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Sequence

from .anonymous_physics_discovery_v22 import DirectedPhysicsRuntimeV22
from .directed_rational_construction_v21 import DirectedValueV21


VectorV26 = tuple[DirectedValueV21, DirectedValueV21]


@dataclass(frozen=True, slots=True)
class PlanarActionObservationV26:
    experiment_id: str
    before: tuple[DirectedValueV21, ...]
    after: tuple[DirectedValueV21, ...]
    central_family: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "before": [item.to_dict() for item in self.before],
            "after": [item.to_dict() for item in self.after],
            "anonymous_family_tag": "F0" if self.central_family else "F1",
            "human_channel_names": None,
            "human_force_type": None,
            "human_rotation_formula": None,
        }


@dataclass(frozen=True, slots=True)
class OrientedBilinearPolicyV26:
    atom_routes: tuple[str, str, str, str]

    @property
    def program_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "ORB-" + hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "oriented_four_atom_bilinear_router_v26",
            "atom_routes": list(self.atom_routes),
            "human_operation_name": None,
        }

    def render(self) -> str:
        return "ORB<" + ",".join(self.atom_routes) + ">"


@dataclass(frozen=True, slots=True)
class RotationQuantityV26:
    weight_route: str
    bilinear_policy: OrientedBilinearPolicyV26
    training_cases: int

    @property
    def program_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "ROT-" + hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "weight_route": self.weight_route,
            "bilinear_program_id": self.bilinear_policy.program_id,
            "opaque_program": f"ROT<{self.weight_route},{self.bilinear_policy.render()}>",
            "training_cases": self.training_cases,
            "human_quantity_name": None,
        }


@dataclass(frozen=True, slots=True)
class PlanarRotationDiscoveryV26:
    bilinear_candidates_generated: int
    selected_bilinear: OrientedBilinearPolicyV26
    weight_candidates_generated: int
    selected_rotation_quantity: RotationQuantityV26
    central_training_cases: int
    general_training_cases: int
    dimension_constraints: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "bilinear_candidates_generated": self.bilinear_candidates_generated,
            "selected_bilinear": {
                "program_id": self.selected_bilinear.program_id,
                "policy": self.selected_bilinear.to_dict(),
                "opaque_program": self.selected_bilinear.render(),
            },
            "weight_candidates_generated": self.weight_candidates_generated,
            "selected_rotation_quantity": {"program_id": self.selected_rotation_quantity.program_id, **self.selected_rotation_quantity.to_dict()},
            "central_training_cases": self.central_training_cases,
            "general_training_cases": self.general_training_cases,
            "dimension_constraints": list(self.dimension_constraints),
        }


class PlanarRotationRuntimeV26:
    ROUTES = ("ZERO", "KEEP", "TURN")
    WEIGHTS = ("ONE", "Q0", "SEM<Q0,Q0>")

    def __init__(self, physics: DirectedPhysicsRuntimeV22) -> None:
        self.physics = physics

    def bilinear(self, policy: OrientedBilinearPolicyV26, left: VectorV26, right: VectorV26) -> DirectedValueV21:
        atoms = (
            self._interact(left[0], right[0]), self._interact(left[0], right[1]),
            self._interact(left[1], right[0]), self._interact(left[1], right[1]),
        )
        result = self.physics.zero
        for route, atom in zip(policy.atom_routes, atoms, strict=True):
            if route == "ZERO":
                term = self.physics.zero
            elif route == "KEEP":
                term = atom
            elif route == "TURN":
                term = self._inverse(atom)
            else:
                raise ValueError("unknown planar atom route")
            result = self._combine(result, term)
        return result

    def rotation_quantity(
        self,
        quantity: RotationQuantityV26,
        mass: DirectedValueV21,
        position: VectorV26,
        state: VectorV26,
    ) -> DirectedValueV21:
        oriented = self.bilinear(quantity.bilinear_policy, position, state)
        if quantity.weight_route == "ONE":
            return oriented
        if quantity.weight_route == "Q0":
            return self._interact(mass, oriented)
        if quantity.weight_route == "SEM<Q0,Q0>":
            return self._interact(self._interact(mass, mass), oriented)
        raise ValueError("unknown rotation weight route")

    def _combine(self, left: DirectedValueV21, right: DirectedValueV21) -> DirectedValueV21:
        return self.physics.normalize(self.physics.directed.execute_binary(self.physics.combine, left, right))

    def _interact(self, left: DirectedValueV21, right: DirectedValueV21) -> DirectedValueV21:
        return self.physics.normalize(self.physics.directed.execute_binary(self.physics.interact, left, right))

    def _inverse(self, value: DirectedValueV21) -> DirectedValueV21:
        return self.physics.normalize(self.physics.directed.execute_unary(self.physics.inverse, value))

    def difference(self, after: DirectedValueV21, before: DirectedValueV21) -> DirectedValueV21:
        return self._combine(after, self._inverse(before))


class PlanarRotationResearchV26:
    def discover(
        self,
        central_rows: Sequence[PlanarActionObservationV26],
        general_rows: Sequence[PlanarActionObservationV26],
        runtime: PlanarRotationRuntimeV26,
    ) -> PlanarRotationDiscoveryV26:
        if not central_rows or not general_rows:
            raise ValueError("central and general planar experiment families are required")
        policies = tuple(OrientedBilinearPolicyV26(tuple(routes)) for routes in itertools.product(runtime.ROUTES, repeat=4))
        selected = [policy for policy in policies if self._operator_laws(policy, runtime)]
        if len(selected) != 1:
            raise RuntimeError(f"expected one oriented bilinear operation, found {len(selected)}")
        policy = selected[0]

        quantities = tuple(RotationQuantityV26(weight, policy, len(general_rows)) for weight in runtime.WEIGHTS)
        balanced = [item for item in quantities if self._balance_holds(item, general_rows, runtime)]
        if len(balanced) != 1:
            raise RuntimeError(f"expected one weighted rotation quantity, found {len(balanced)}")
        quantity = balanced[0]
        if not all(self._central_conserved(quantity, row, runtime) for row in central_rows):
            raise RuntimeError("selected rotation quantity is not conserved for F0 experiments")
        return PlanarRotationDiscoveryV26(
            bilinear_candidates_generated=len(policies),
            selected_bilinear=policy,
            weight_candidates_generated=len(quantities),
            selected_rotation_quantity=quantity,
            central_training_cases=len(central_rows),
            general_training_cases=len(general_rows),
            dimension_constraints=("D_ROT=(D0+D_POS+D_STATE)", "D_ANGULAR_ACTION=(D_POS+D_ACTION)"),
        )

    @staticmethod
    def _operator_laws(policy: OrientedBilinearPolicyV26, runtime: PlanarRotationRuntimeV26) -> bool:
        zero = runtime.physics.zero
        one = runtime.physics.one
        minus_one = runtime._inverse(one)
        vectors: tuple[VectorV26, ...] = (
            (one, zero), (zero, one),
            (runtime._combine(one, one), one),
            (minus_one, one),
        )
        alternating = all(runtime.physics.equivalent(runtime.bilinear(policy, item, item), zero) for item in vectors)
        antisymmetric = all(runtime.physics.equivalent(
            runtime.bilinear(policy, left, right), runtime._inverse(runtime.bilinear(policy, right, left))
        ) for left, right in itertools.product(vectors, repeat=2))
        oriented_basis = runtime.physics.equivalent(runtime.bilinear(policy, vectors[0], vectors[1]), one)
        return alternating and antisymmetric and oriented_basis

    @staticmethod
    def _channels(row: PlanarActionObservationV26):
        mass = row.before[0]
        position = (row.before[1], row.before[2])
        before_state = (row.before[3], row.before[4])
        action = (row.before[5], row.before[6])
        after_state = (row.after[3], row.after[4])
        return mass, position, before_state, action, after_state

    @classmethod
    def _balance_holds(
        cls,
        quantity: RotationQuantityV26,
        rows: Sequence[PlanarActionObservationV26],
        runtime: PlanarRotationRuntimeV26,
    ) -> bool:
        for row in rows:
            mass, position, before_state, action, after_state = cls._channels(row)
            before = runtime.rotation_quantity(quantity, mass, position, before_state)
            after = runtime.rotation_quantity(quantity, mass, position, after_state)
            change = runtime.difference(after, before)
            angular_action = runtime.bilinear(quantity.bilinear_policy, position, action)
            if not runtime.physics.equivalent(change, angular_action):
                return False
        return True

    @classmethod
    def _central_conserved(
        cls,
        quantity: RotationQuantityV26,
        row: PlanarActionObservationV26,
        runtime: PlanarRotationRuntimeV26,
    ) -> bool:
        mass, position, before_state, action, after_state = cls._channels(row)
        angular_action = runtime.bilinear(quantity.bilinear_policy, position, action)
        before = runtime.rotation_quantity(quantity, mass, position, before_state)
        after = runtime.rotation_quantity(quantity, mass, position, after_state)
        return runtime.physics.equivalent(angular_action, runtime.physics.zero) and runtime.physics.equivalent(before, after)
