"""Anonymous nonzero-unary and three-input program search over V21 values."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Sequence

from .directed_rational_construction_v21 import (
    DirectedRationalConstructorV21,
    DirectedRuntimeV21,
    DirectedValueV21,
    DirectionPolicyV21,
    UnaryDirectionPolicyV21,
)
from .proof_driven_program_construction_v20 import AnonymousDerivedRuntimeV20


class NonzeroUnaryDomainErrorV53(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class NonzeroUnaryPolicyV53:
    numerator_source: str
    denominator_source: str
    positive_branch_to_positive: bool
    negative_branch_to_positive: bool

    @property
    def program_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "NZU-" + hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "cancelled_direction_source_router_v53",
            "numerator_source": self.numerator_source,
            "denominator_source": self.denominator_source,
            "positive_branch_to_positive": self.positive_branch_to_positive,
            "negative_branch_to_positive": self.negative_branch_to_positive,
            "human_operation_name": None,
        }


@dataclass(frozen=True, slots=True)
class NonzeroUnaryProfileV53:
    nonzero_closed: bool
    representation_invariant: bool
    interaction_identity: bool
    involutive: bool

    @property
    def promotable(self) -> bool:
        return all((
            self.nonzero_closed,
            self.representation_invariant,
            self.interaction_identity,
            self.involutive,
        ))

    def to_dict(self) -> dict[str, bool]:
        return {
            "nonzero_closed": self.nonzero_closed,
            "representation_invariant": self.representation_invariant,
            "interaction_identity": self.interaction_identity,
            "involutive": self.involutive,
            "promotable": self.promotable,
        }


@dataclass(frozen=True, slots=True)
class NonzeroUnaryCandidateV53:
    policy: NonzeroUnaryPolicyV53
    profile: NonzeroUnaryProfileV53
    signature: tuple[tuple[int, int, int], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.policy.program_id,
            "policy": self.policy.to_dict(),
            "profile": self.profile.to_dict(),
            "behavior_signature": [list(item) for item in self.signature],
        }


@dataclass(frozen=True, slots=True)
class ThreeInputPolicyV53:
    leaf_order: tuple[str, str, str]
    unary_routes: tuple[str, str, str]
    binary_routes: tuple[str, str]
    bracketing: str

    @property
    def program_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "TRI-" + hashlib.sha256(payload.encode()).hexdigest()[:16]

    @property
    def operation_cost(self) -> int:
        return 2 + sum(route != "identity" for route in self.unary_routes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "anonymous_three_leaf_expression_router_v53",
            "leaf_order": list(self.leaf_order),
            "unary_routes": list(self.unary_routes),
            "binary_routes": list(self.binary_routes),
            "bracketing": self.bracketing,
            "operation_cost": self.operation_cost,
            "target_expression_given": False,
            "human_operation_name": None,
        }


@dataclass(frozen=True, slots=True)
class AnonymousFieldConstructionV53:
    dependency: Any
    unary_programs_generated: int
    unary_behavior_classes: int
    selected_nonzero_unary: NonzeroUnaryCandidateV53
    three_input_programs_generated: int
    three_input_passing_programs: int
    three_input_passing_behavior_classes: int
    selected_three_input: ThreeInputPolicyV53
    equation_examples: tuple[dict[str, Any], ...]


class AnonymousFieldRuntimeV53:
    SOURCES = ("magnitude", "source_denominator", "one", "zero")

    def __init__(
        self,
        directed: DirectedRuntimeV21,
        combine: DirectionPolicyV21,
        additive_unary: UnaryDirectionPolicyV21,
        interact: DirectionPolicyV21,
    ) -> None:
        self.directed = directed
        self.combine = combine
        self.additive_unary = additive_unary
        self.interact = interact

    @staticmethod
    def cancel_channels(value: DirectedValueV21) -> tuple[int, int]:
        positive = value.positive
        negative = value.negative
        while positive > 0 and negative > 0:
            positive -= 1
            negative -= 1
        return positive, negative

    @staticmethod
    def _source(name: str, magnitude: int, denominator: int) -> int:
        if name == "magnitude":
            return magnitude
        if name == "source_denominator":
            return denominator
        if name == "one":
            return 1
        if name == "zero":
            return 0
        raise ValueError(f"unknown counter source {name}")

    def execute_nonzero_unary(
        self, policy: NonzeroUnaryPolicyV53, value: DirectedValueV21
    ) -> DirectedValueV21:
        positive, negative = self.cancel_channels(value)
        if positive == 0 and negative == 0:
            raise NonzeroUnaryDomainErrorV53("anonymous unary program is undefined on the zero class")
        positive_branch = positive > 0
        magnitude = positive if positive_branch else negative
        numerator = self._source(policy.numerator_source, magnitude, value.denominator)
        denominator = self._source(policy.denominator_source, magnitude, value.denominator)
        if denominator <= 0:
            raise NonzeroUnaryDomainErrorV53("candidate produced a nonpositive denominator")
        route_positive = (
            policy.positive_branch_to_positive
            if positive_branch
            else policy.negative_branch_to_positive
        )
        return DirectedValueV21(
            numerator if route_positive else 0,
            0 if route_positive else numerator,
            denominator,
        )

    def execute_three_input(
        self,
        policy: ThreeInputPolicyV53,
        nonzero_unary: NonzeroUnaryPolicyV53,
        environment: dict[str, DirectedValueV21],
    ) -> DirectedValueV21:
        values = [
            self._execute_leaf_unary(route, nonzero_unary, environment[name])
            for name, route in zip(policy.leaf_order, policy.unary_routes, strict=True)
        ]
        if policy.bracketing == "left":
            return self._execute_binary(
                policy.binary_routes[1],
                self._execute_binary(policy.binary_routes[0], values[0], values[1]),
                values[2],
            )
        if policy.bracketing == "right":
            return self._execute_binary(
                policy.binary_routes[0],
                values[0],
                self._execute_binary(policy.binary_routes[1], values[1], values[2]),
            )
        raise ValueError("unknown bracketing")

    def _execute_leaf_unary(
        self,
        route: str,
        nonzero_unary: NonzeroUnaryPolicyV53,
        value: DirectedValueV21,
    ) -> DirectedValueV21:
        if route == "identity":
            return value
        if route == "unary_0":
            return self.directed.execute_unary(self.additive_unary, value)
        if route == "unary_1":
            return self.execute_nonzero_unary(nonzero_unary, value)
        raise ValueError("unknown unary route")

    def _execute_binary(
        self, route: str, left: DirectedValueV21, right: DirectedValueV21
    ) -> DirectedValueV21:
        if route == "binary_0":
            return self.directed.execute_binary(self.combine, left, right)
        if route == "binary_1":
            return self.directed.execute_binary(self.interact, left, right)
        raise ValueError("unknown binary route")


class AnonymousFieldConstructorV53:
    NONZERO_VALUES = (
        DirectedValueV21(1, 0, 1),
        DirectedValueV21(0, 1, 1),
        DirectedValueV21(1, 0, 2),
        DirectedValueV21(0, 1, 2),
        DirectedValueV21(2, 0, 3),
        DirectedValueV21(0, 3, 2),
        DirectedValueV21(5, 2, 4),
        DirectedValueV21(2, 9, 5),
    )
    GENERAL_VALUES = (
        DirectedValueV21(0, 0, 1),
        DirectedValueV21(1, 0, 1),
        DirectedValueV21(0, 1, 1),
        DirectedValueV21(1, 0, 2),
        DirectedValueV21(0, 1, 2),
        DirectedValueV21(2, 0, 3),
        DirectedValueV21(0, 3, 2),
    )

    def construct(
        self, observed_values: Sequence[int] = (1, 3, 5, 7, 11, 13, 17)
    ) -> AnonymousFieldConstructionV53:
        dependency = DirectedRationalConstructorV21().construct(observed_values)
        base = dependency.base_construction
        directed = DirectedRuntimeV21(
            AnonymousDerivedRuntimeV20(
                base.operation_program, base.partition_report.selected.program
            )
        )
        runtime = AnonymousFieldRuntimeV53(
            directed,
            dependency.selected_combine.policy,
            dependency.selected_inverse,
            dependency.selected_interact.policy,
        )
        unary_candidates = self._search_nonzero_unary(runtime)
        passing_unary = [item for item in unary_candidates if item.profile.promotable]
        passing_behaviors = self._behavior_classes(runtime, passing_unary)
        if len(passing_behaviors) != 1:
            raise RuntimeError(
                f"expected one promotable nonzero-unary behavior, found {len(passing_behaviors)}"
            )
        selected_unary = min(
            passing_behaviors[0], key=lambda item: item.policy.program_id
        )
        policies, passing = self._search_three_input(runtime, selected_unary.policy)
        passing_three_behaviors = self._three_input_behavior_classes(
            runtime, selected_unary.policy, passing
        )
        if len(passing_three_behaviors) != 1:
            raise RuntimeError(
                f"expected one passing three-input behavior, found {len(passing_three_behaviors)}"
            )
        selected_three = min(
            passing_three_behaviors[0],
            key=lambda item: (item.operation_cost, item.program_id),
        )
        examples = tuple(
            self._equation_example(runtime, selected_unary.policy, selected_three, a, b, c)
            for a, b, c in (
                (
                    DirectedValueV21(2, 0, 3),
                    DirectedValueV21(1, 0, 2),
                    DirectedValueV21(7, 0, 6),
                ),
                (
                    DirectedValueV21(0, 5, 4),
                    DirectedValueV21(2, 0, 3),
                    DirectedValueV21(0, 7, 6),
                ),
                (
                    DirectedValueV21(5, 2, 7),
                    DirectedValueV21(0, 4, 5),
                    DirectedValueV21(3, 1, 2),
                ),
            )
        )
        return AnonymousFieldConstructionV53(
            dependency,
            64,
            len(unary_candidates),
            selected_unary,
            len(policies),
            len(passing),
            len(passing_three_behaviors),
            selected_three,
            examples,
        )

    def _search_nonzero_unary(
        self, runtime: AnonymousFieldRuntimeV53
    ) -> tuple[NonzeroUnaryCandidateV53, ...]:
        one = DirectedValueV21(1, 0, 1)
        by_signature: dict[tuple[tuple[int, int, int], ...], NonzeroUnaryCandidateV53] = {}
        for numerator_source, denominator_source in itertools.product(
            runtime.SOURCES, repeat=2
        ):
            for positive_route, negative_route in itertools.product((False, True), repeat=2):
                policy = NonzeroUnaryPolicyV53(
                    numerator_source,
                    denominator_source,
                    positive_route,
                    negative_route,
                )
                try:
                    outputs = tuple(
                        runtime.execute_nonzero_unary(policy, value)
                        for value in self.NONZERO_VALUES
                    )
                    nonzero_closed = all(
                        not runtime.directed.equivalent(output, DirectedValueV21(0, 0, 1))
                        for output in outputs
                    )
                    invariant = all(
                        runtime.directed.equivalent(
                            runtime.execute_nonzero_unary(policy, variant), output
                        )
                        for value, output in zip(self.NONZERO_VALUES, outputs, strict=True)
                        for variant in runtime.directed.alternate_representations(value)
                    )
                    identity = all(
                        runtime.directed.equivalent(
                            runtime.directed.execute_binary(runtime.interact, value, output), one
                        )
                        for value, output in zip(self.NONZERO_VALUES, outputs, strict=True)
                    )
                    involutive = all(
                        runtime.directed.equivalent(
                            runtime.execute_nonzero_unary(policy, output), value
                        )
                        for value, output in zip(self.NONZERO_VALUES, outputs, strict=True)
                    )
                except NonzeroUnaryDomainErrorV53:
                    outputs = ()
                    nonzero_closed = invariant = identity = involutive = False
                signature = tuple(item.to_tuple() for item in outputs)
                candidate = NonzeroUnaryCandidateV53(
                    policy,
                    NonzeroUnaryProfileV53(
                        nonzero_closed, invariant, identity, involutive
                    ),
                    signature,
                )
                by_signature.setdefault(signature, candidate)
        return tuple(by_signature.values())

    def _behavior_classes(
        self,
        runtime: AnonymousFieldRuntimeV53,
        candidates: Sequence[NonzeroUnaryCandidateV53],
    ) -> list[list[NonzeroUnaryCandidateV53]]:
        groups: list[list[NonzeroUnaryCandidateV53]] = []
        for candidate in candidates:
            outputs = [
                runtime.execute_nonzero_unary(candidate.policy, value)
                for value in self.NONZERO_VALUES
            ]
            for group in groups:
                representative = [
                    runtime.execute_nonzero_unary(group[0].policy, value)
                    for value in self.NONZERO_VALUES
                ]
                if all(
                    runtime.directed.equivalent(left, right)
                    for left, right in zip(outputs, representative, strict=True)
                ):
                    group.append(candidate)
                    break
            else:
                groups.append([candidate])
        return groups

    def _search_three_input(
        self,
        runtime: AnonymousFieldRuntimeV53,
        unary: NonzeroUnaryPolicyV53,
    ) -> tuple[tuple[ThreeInputPolicyV53, ...], tuple[ThreeInputPolicyV53, ...]]:
        policies: list[ThreeInputPolicyV53] = []
        passing: list[ThreeInputPolicyV53] = []
        environments = tuple(
            {"a": a, "b": b, "c": c}
            for a, b, c in itertools.product(
                self.NONZERO_VALUES[:6], self.GENERAL_VALUES[:5], self.GENERAL_VALUES[:5]
            )
        )
        for order in itertools.permutations(("a", "b", "c")):
            for unary_routes in itertools.product(
                ("identity", "unary_0", "unary_1"), repeat=3
            ):
                for binary_routes in itertools.product(("binary_0", "binary_1"), repeat=2):
                    for bracketing in ("left", "right"):
                        policy = ThreeInputPolicyV53(
                            tuple(order), tuple(unary_routes), tuple(binary_routes), bracketing
                        )
                        policies.append(policy)
                        solved = True
                        for environment in environments:
                            try:
                                candidate = runtime.execute_three_input(policy, unary, environment)
                            except NonzeroUnaryDomainErrorV53:
                                solved = False
                                break
                            replay = runtime.directed.execute_binary(
                                runtime.combine,
                                runtime.directed.execute_binary(
                                    runtime.interact, environment["a"], candidate
                                ),
                                environment["b"],
                            )
                            if not runtime.directed.equivalent(replay, environment["c"]):
                                solved = False
                                break
                        if solved:
                            passing.append(policy)
        return tuple(policies), tuple(passing)

    def _three_input_behavior_classes(
        self,
        runtime: AnonymousFieldRuntimeV53,
        unary: NonzeroUnaryPolicyV53,
        candidates: Sequence[ThreeInputPolicyV53],
    ) -> list[list[ThreeInputPolicyV53]]:
        probes = tuple(
            {"a": a, "b": b, "c": c}
            for a, b, c in itertools.product(
                self.NONZERO_VALUES[:3], self.GENERAL_VALUES[:3], self.GENERAL_VALUES[:3]
            )
        )
        groups: list[list[ThreeInputPolicyV53]] = []
        for candidate in candidates:
            outputs = [runtime.execute_three_input(candidate, unary, row) for row in probes]
            for group in groups:
                representative = [
                    runtime.execute_three_input(group[0], unary, row) for row in probes
                ]
                if all(
                    runtime.directed.equivalent(left, right)
                    for left, right in zip(outputs, representative, strict=True)
                ):
                    group.append(candidate)
                    break
            else:
                groups.append([candidate])
        return groups

    @staticmethod
    def _equation_example(
        runtime: AnonymousFieldRuntimeV53,
        unary: NonzeroUnaryPolicyV53,
        policy: ThreeInputPolicyV53,
        a: DirectedValueV21,
        b: DirectedValueV21,
        c: DirectedValueV21,
    ) -> dict[str, Any]:
        solution = runtime.execute_three_input(policy, unary, {"a": a, "b": b, "c": c})
        replay = runtime.directed.execute_binary(
            runtime.combine,
            runtime.directed.execute_binary(runtime.interact, a, solution),
            b,
        )
        return {
            "inputs": {"a": a.to_dict(), "b": b.to_dict(), "c": c.to_dict()},
            "output": solution.to_dict(),
            "replay": replay.to_dict(),
            "passed": runtime.directed.equivalent(replay, c),
        }
