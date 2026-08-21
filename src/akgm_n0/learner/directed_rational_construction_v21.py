"""Discover directed rational programs without a signed-number primitive."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Sequence

from .proof_driven_program_construction_v20 import (
    AnonymousDerivedRuntimeV20,
    ProofDrivenProgramConstructorV20,
)


@dataclass(frozen=True, slots=True)
class DirectedValueV21:
    positive: int
    negative: int
    denominator: int

    def __post_init__(self) -> None:
        if self.positive < 0 or self.negative < 0 or self.denominator <= 0:
            raise ValueError("directed values require two natural counters and one positive counter")

    def to_tuple(self) -> tuple[int, int, int]:
        return self.positive, self.negative, self.denominator

    def to_dict(self) -> dict[str, int]:
        return {"positive": self.positive, "negative": self.negative, "denominator": self.denominator}


@dataclass(frozen=True, slots=True)
class DirectionPolicyV21:
    family: str
    positive_mask: tuple[bool, bool, bool, bool]

    @property
    def program_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "DIR-" + hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "four_term_direction_router_v21",
            "family": self.family,
            "positive_mask": list(self.positive_mask),
            "human_operation_name": None,
        }


@dataclass(frozen=True, slots=True)
class UnaryDirectionPolicyV21:
    swap_counters: bool

    @property
    def program_id(self) -> str:
        return "UDIR-" + hashlib.sha256(str(self.swap_counters).encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "unary_direction_router_v21",
            "swap_counters": self.swap_counters,
            "human_operation_name": None,
        }


@dataclass(frozen=True, slots=True)
class DirectedLawProfileV21:
    representation_invariant: bool
    closed: bool
    commutative: bool
    associative: bool
    identity: bool
    zero_annihilator: bool
    distributive: bool

    def to_dict(self) -> dict[str, bool]:
        return {
            "representation_invariant": self.representation_invariant,
            "closed": self.closed,
            "commutative": self.commutative,
            "associative": self.associative,
            "identity": self.identity,
            "zero_annihilator": self.zero_annihilator,
            "distributive": self.distributive,
        }


@dataclass(frozen=True, slots=True)
class DirectedCandidateV21:
    policy: DirectionPolicyV21
    profile: DirectedLawProfileV21
    signature: tuple[tuple[int, int, int], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.policy.program_id,
            "policy": self.policy.to_dict(),
            "law_profile": self.profile.to_dict(),
            "behavior_signature": [list(item) for item in self.signature],
        }


class DirectedRuntimeV21:
    def __init__(self, base: AnonymousDerivedRuntimeV20) -> None:
        self.base = base

    def equivalent(self, left: DirectedValueV21, right: DirectedValueV21) -> bool:
        left_cross = self.base.merge(
            self.base.omega(left.positive, right.denominator),
            self.base.omega(right.negative, left.denominator),
        )
        right_cross = self.base.merge(
            self.base.omega(right.positive, left.denominator),
            self.base.omega(left.negative, right.denominator),
        )
        return left_cross == right_cross

    def execute_binary(
        self,
        policy: DirectionPolicyV21,
        left: DirectedValueV21,
        right: DirectedValueV21,
    ) -> DirectedValueV21:
        if policy.family == "combine":
            terms = (
                self.base.omega(left.positive, right.denominator),
                self.base.omega(left.negative, right.denominator),
                self.base.omega(right.positive, left.denominator),
                self.base.omega(right.negative, left.denominator),
            )
        elif policy.family == "interact":
            terms = (
                self.base.omega(left.positive, right.positive),
                self.base.omega(left.positive, right.negative),
                self.base.omega(left.negative, right.positive),
                self.base.omega(left.negative, right.negative),
            )
        else:
            raise ValueError("unknown direction-policy family")
        positive = 0
        negative = 0
        for term, routed_positive in zip(terms, policy.positive_mask, strict=True):
            if routed_positive:
                positive = self.base.merge(positive, term)
            else:
                negative = self.base.merge(negative, term)
        denominator = self.base.omega(left.denominator, right.denominator)
        return DirectedValueV21(positive, negative, denominator)

    @staticmethod
    def execute_unary(policy: UnaryDirectionPolicyV21, value: DirectedValueV21) -> DirectedValueV21:
        if policy.swap_counters:
            return DirectedValueV21(value.negative, value.positive, value.denominator)
        return value

    def alternate_representations(self, value: DirectedValueV21) -> tuple[DirectedValueV21, ...]:
        scaled = DirectedValueV21(
            self.base.omega(value.positive, 2),
            self.base.omega(value.negative, 2),
            self.base.omega(value.denominator, 2),
        )
        offset = DirectedValueV21(
            self.base.merge(value.positive, 2),
            self.base.merge(value.negative, 2),
            value.denominator,
        )
        return scaled, offset


@dataclass(frozen=True, slots=True)
class DirectedConstructionV21:
    base_construction: Any
    policies_generated: int
    combine_behavior_classes: int
    interact_behavior_classes: int
    selected_combine: DirectedCandidateV21
    selected_inverse: UnaryDirectionPolicyV21
    selected_interact: DirectedCandidateV21
    equation_examples: tuple[dict[str, Any], ...]


class DirectedRationalConstructorV21:
    VALUES = (
        DirectedValueV21(0, 0, 1),
        DirectedValueV21(1, 0, 1),
        DirectedValueV21(0, 1, 1),
        DirectedValueV21(1, 0, 2),
        DirectedValueV21(0, 1, 2),
        DirectedValueV21(2, 0, 3),
        DirectedValueV21(0, 3, 2),
    )

    def construct(self, observed_values: Sequence[int] = (1, 3, 5, 7, 11, 13, 17)) -> DirectedConstructionV21:
        base = ProofDrivenProgramConstructorV20().construct(observed_values)
        runtime = DirectedRuntimeV21(
            AnonymousDerivedRuntimeV20(base.operation_program, base.partition_report.selected.program)
        )
        combine_candidates = self._search_family("combine", runtime, None)
        selected_combine = self._select_combine(combine_candidates)
        inverse = self._search_inverse(runtime, selected_combine.policy)
        interact_candidates = self._search_family("interact", runtime, selected_combine.policy)
        selected_interact = self._select_interact(interact_candidates)
        equations = tuple(
            self._solve_translation(runtime, selected_combine.policy, inverse, bias, target)
            for bias, target in (
                (DirectedValueV21(3, 0, 2), DirectedValueV21(7, 0, 2)),
                (DirectedValueV21(0, 5, 3), DirectedValueV21(2, 0, 3)),
                (DirectedValueV21(4, 1, 5), DirectedValueV21(1, 6, 5)),
            )
        )
        return DirectedConstructionV21(
            base,
            34,
            len(combine_candidates),
            len(interact_candidates),
            selected_combine,
            inverse,
            selected_interact,
            equations,
        )

    def _search_family(
        self,
        family: str,
        runtime: DirectedRuntimeV21,
        combine_policy: DirectionPolicyV21 | None,
    ) -> tuple[DirectedCandidateV21, ...]:
        by_behavior: dict[tuple[tuple[int, int, int], ...], DirectedCandidateV21] = {}
        for mask in itertools.product((False, True), repeat=4):
            policy = DirectionPolicyV21(family, tuple(mask))
            signature = tuple(
                runtime.execute_binary(policy, left, right).to_tuple()
                for left, right in itertools.product(self.VALUES, repeat=2)
            )
            candidate = DirectedCandidateV21(
                policy,
                self._profile(policy, runtime, combine_policy),
                signature,
            )
            by_behavior.setdefault(signature, candidate)
        return tuple(by_behavior.values())

    def _profile(
        self,
        policy: DirectionPolicyV21,
        runtime: DirectedRuntimeV21,
        combine_policy: DirectionPolicyV21 | None,
    ) -> DirectedLawProfileV21:
        values = self.VALUES
        apply = lambda left, right: runtime.execute_binary(policy, left, right)
        invariant = all(
            runtime.equivalent(apply(variant, right), apply(left, right))
            and runtime.equivalent(apply(left, variant_right), apply(left, right))
            for left, right in itertools.product(values, repeat=2)
            for variant in runtime.alternate_representations(left)
            for variant_right in runtime.alternate_representations(right)
        )
        commutative = all(runtime.equivalent(apply(a, b), apply(b, a)) for a, b in itertools.product(values, repeat=2))
        small = values[:5]
        associative = all(
            runtime.equivalent(apply(apply(a, b), c), apply(a, apply(b, c)))
            for a, b, c in itertools.product(small, repeat=3)
        )
        identity_value = DirectedValueV21(0, 0, 1) if policy.family == "combine" else DirectedValueV21(1, 0, 1)
        identity = all(runtime.equivalent(apply(identity_value, item), item) and runtime.equivalent(apply(item, identity_value), item) for item in values)
        zero = DirectedValueV21(0, 0, 1)
        annihilator = all(runtime.equivalent(apply(zero, item), zero) and runtime.equivalent(apply(item, zero), zero) for item in values)
        distributive = False
        if combine_policy is not None:
            combine = lambda left, right: runtime.execute_binary(combine_policy, left, right)
            distributive = all(
                runtime.equivalent(apply(a, combine(b, c)), combine(apply(a, b), apply(a, c)))
                for a, b, c in itertools.product(small, repeat=3)
            )
        return DirectedLawProfileV21(invariant, True, commutative, associative, identity, annihilator, distributive)

    @staticmethod
    def _select_combine(candidates: Sequence[DirectedCandidateV21]) -> DirectedCandidateV21:
        passing = [item for item in candidates if all((
            item.profile.representation_invariant,
            item.profile.commutative,
            item.profile.associative,
            item.profile.identity,
        ))]
        if len(passing) != 1:
            raise RuntimeError(f"expected one directed combine behavior, found {len(passing)}")
        return passing[0]

    def _search_inverse(
        self,
        runtime: DirectedRuntimeV21,
        combine: DirectionPolicyV21,
    ) -> UnaryDirectionPolicyV21:
        zero = DirectedValueV21(0, 0, 1)
        passing = []
        for swap in (False, True):
            policy = UnaryDirectionPolicyV21(swap)
            if all(
                runtime.equivalent(
                    runtime.execute_binary(combine, value, runtime.execute_unary(policy, value)), zero
                )
                and runtime.equivalent(runtime.execute_unary(policy, runtime.execute_unary(policy, value)), value)
                for value in self.VALUES
            ):
                passing.append(policy)
        if len(passing) != 1:
            raise RuntimeError(f"expected one inverse router, found {len(passing)}")
        return passing[0]

    @staticmethod
    def _select_interact(candidates: Sequence[DirectedCandidateV21]) -> DirectedCandidateV21:
        passing = [item for item in candidates if all((
            item.profile.representation_invariant,
            item.profile.commutative,
            item.profile.associative,
            item.profile.identity,
            item.profile.zero_annihilator,
            item.profile.distributive,
        ))]
        if len(passing) != 1:
            raise RuntimeError(f"expected one directed interaction behavior, found {len(passing)}")
        return passing[0]

    @staticmethod
    def _solve_translation(
        runtime: DirectedRuntimeV21,
        combine: DirectionPolicyV21,
        inverse: UnaryDirectionPolicyV21,
        bias: DirectedValueV21,
        target: DirectedValueV21,
    ) -> dict[str, Any]:
        solution = runtime.execute_binary(combine, target, runtime.execute_unary(inverse, bias))
        replay = runtime.execute_binary(combine, solution, bias)
        return {
            "bias": bias.to_dict(),
            "target": target.to_dict(),
            "solution": solution.to_dict(),
            "replay": replay.to_dict(),
            "passed": runtime.equivalent(replay, target),
        }
