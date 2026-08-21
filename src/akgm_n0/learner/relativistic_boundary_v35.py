"""Discover an anonymous finite-speed composition law and its classical limit."""
from __future__ import annotations

import hashlib
import itertools
from dataclasses import dataclass
from typing import Sequence

from .anonymous_physics_discovery_v22 import DirectedPhysicsRuntimeV22
from .directed_rational_construction_v21 import DirectedValueV21


@dataclass(frozen=True, slots=True)
class FrameObservationV35:
    experiment_id: str
    q0: DirectedValueV21
    q1: DirectedValueV21
    q2: DirectedValueV21
    target: DirectedValueV21

    def to_dict(self):
        return {
            "experiment_id": self.experiment_id,
            "anonymous_inputs": [self.q0.to_dict(), self.q1.to_dict(), self.q2.to_dict()],
            "anonymous_target": self.target.to_dict(),
            "human_names": None,
            "human_formula": None,
        }


@dataclass(frozen=True, slots=True)
class CompositionProgramV35:
    numerator_route: str
    denominator_route: str

    @property
    def program_id(self):
        return "FRM-" + hashlib.sha256(self.render().encode()).hexdigest()[:16]

    def render(self):
        numerators = {
            "ADD": "MERGE<Q1,Q2>",
            "SUB": "MERGE<Q1,TURN<Q2>>",
            "PRODUCT": "SEM<Q1,Q2>",
            "LEFT": "Q1",
            "RIGHT": "Q2",
        }
        denominators = {
            "ONE": "ONE",
            "PLUS_RATIO": "MERGE<ONE,SEM<Q1,Q2>/SEM<Q0,Q0>>",
            "MINUS_RATIO": "MERGE<ONE,TURN<SEM<Q1,Q2>/SEM<Q0,Q0>>>",
            "BOUND_SQUARED": "SEM<Q0,Q0>",
            "PLUS_LEFT_RATIO": "MERGE<ONE,Q1/Q0>",
        }
        return f"FRAME<{numerators[self.numerator_route]};DEN:{denominators[self.denominator_route]}>"

    def to_dict(self):
        return {
            "numerator_route": self.numerator_route,
            "denominator_route": self.denominator_route,
            "human_operation_name": None,
        }


@dataclass(frozen=True, slots=True)
class RelativisticBoundaryDiscoveryV35:
    candidate_count: int
    selected_program: CompositionProgramV35
    invariant_role_candidates: int
    selected_invariant_role: str

    def to_dict(self):
        return {
            "candidate_count": self.candidate_count,
            "selected_program": {
                "program_id": self.selected_program.program_id,
                "opaque_program": self.selected_program.render(),
                "policy": self.selected_program.to_dict(),
            },
            "invariant_role_candidates": self.invariant_role_candidates,
            "selected_invariant_role": self.selected_invariant_role,
            "human_interpretation_during_search": None,
        }


class FrameRuntimeV35:
    def __init__(self, physics: DirectedPhysicsRuntimeV22):
        self.physics = physics

    def add(self, a, b):
        return self.physics.normalize(self.physics.directed.execute_binary(self.physics.combine, a, b))

    def mul(self, a, b):
        return self.physics.normalize(self.physics.directed.execute_binary(self.physics.interact, a, b))

    def turn(self, value):
        return self.physics.normalize(self.physics.directed.execute_unary(self.physics.inverse, value))

    def divide(self, value, divisor):
        divisor = self.physics.normalize(divisor)
        if divisor.positive == divisor.negative:
            return None
        base = self.physics.directed.base
        if divisor.positive > divisor.negative:
            signed = DirectedValueV21(
                base.omega(value.positive, divisor.denominator),
                base.omega(value.negative, divisor.denominator),
                base.omega(value.denominator, divisor.positive - divisor.negative),
            )
        else:
            signed = DirectedValueV21(
                base.omega(value.negative, divisor.denominator),
                base.omega(value.positive, divisor.denominator),
                base.omega(value.denominator, divisor.negative - divisor.positive),
            )
        return self.physics.normalize(signed)

    def execute(self, program: CompositionProgramV35, row: FrameObservationV35):
        if program.numerator_route == "ADD":
            numerator = self.add(row.q1, row.q2)
        elif program.numerator_route == "SUB":
            numerator = self.add(row.q1, self.turn(row.q2))
        elif program.numerator_route == "PRODUCT":
            numerator = self.mul(row.q1, row.q2)
        elif program.numerator_route == "LEFT":
            numerator = row.q1
        else:
            numerator = row.q2

        if program.denominator_route == "ONE":
            denominator = self.physics.one
        elif program.denominator_route in ("PLUS_RATIO", "MINUS_RATIO"):
            ratio = self.divide(self.mul(row.q1, row.q2), self.mul(row.q0, row.q0))
            if ratio is None:
                return None
            if program.denominator_route == "MINUS_RATIO":
                ratio = self.turn(ratio)
            denominator = self.add(self.physics.one, ratio)
        elif program.denominator_route == "BOUND_SQUARED":
            denominator = self.mul(row.q0, row.q0)
        else:
            ratio = self.divide(row.q1, row.q0)
            if ratio is None:
                return None
            denominator = self.add(self.physics.one, ratio)
        return self.divide(numerator, denominator)


class RelativisticBoundaryResearchV35:
    def candidates(self):
        return tuple(
            CompositionProgramV35(n, d)
            for n, d in itertools.product(
                ("ADD", "SUB", "PRODUCT", "LEFT", "RIGHT"),
                ("ONE", "PLUS_RATIO", "MINUS_RATIO", "BOUND_SQUARED", "PLUS_LEFT_RATIO"),
            )
        )

    def discover(
        self,
        rows: Sequence[FrameObservationV35],
        boundary_rows: Sequence[FrameObservationV35],
        runtime: FrameRuntimeV35,
    ):
        candidates = self.candidates()
        survivors = [
            program
            for program in candidates
            if all(
                (output := runtime.execute(program, row)) is not None
                and runtime.physics.equivalent(output, row.target)
                for row in rows
            )
        ]
        if len(survivors) != 1:
            raise RuntimeError(f"composition survivors: {len(survivors)}")
        selected = survivors[0]
        roles = ("Q0", "TURN_Q0", "ZERO", "ONE")
        fixed = []
        for role in roles:
            passed = True
            for row in boundary_rows:
                expected = {
                    "Q0": row.q0,
                    "TURN_Q0": runtime.turn(row.q0),
                    "ZERO": runtime.physics.zero,
                    "ONE": runtime.physics.one,
                }[role]
                output = runtime.execute(selected, row)
                passed = passed and output is not None and runtime.physics.equivalent(output, expected)
            if passed:
                fixed.append(role)
        if fixed != ["Q0"]:
            raise RuntimeError(f"invariant role survivors: {fixed}")
        return RelativisticBoundaryDiscoveryV35(len(candidates), selected, len(roles), fixed[0])
