"""Policy search for algebraic closures composed from strict V10-V13 semantics."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from .strict_foundation_expansion_v13 import (
    IntegerPartitionPolicy,
    SignedProductPolicy,
    StrictFoundationRuntime,
)


COMPONENT_PAIRS = (("a", "c"), ("a", "d"), ("b", "c"), ("b", "d"))


@dataclass(frozen=True, slots=True)
class RationalProductPolicy:
    numerator_pair: tuple[str, str]
    denominator_pair: tuple[str, str]

    def execute(
        self,
        runtime: StrictFoundationRuntime,
        signed_product: SignedProductPolicy,
        left: tuple[int, int],
        right: tuple[int, int],
    ) -> tuple[int, int]:
        a, b = left
        c, d = right
        if b <= 0 or d <= 0:
            raise ValueError("rational denominators must be positive")
        values = {"a": a, "b": b, "c": c, "d": d}
        numerator = signed_product.execute(runtime, values[self.numerator_pair[0]], values[self.numerator_pair[1]])
        denominator = signed_product.execute(runtime, values[self.denominator_pair[0]], values[self.denominator_pair[1]])
        if denominator <= 0:
            raise ValueError("candidate produced a nonpositive denominator")
        return numerator, denominator

    def to_dict(self) -> dict[str, Any]:
        return {"substrate": "component_pairing_over_signed_product_v14", "numerator_pair": list(self.numerator_pair), "denominator_pair": list(self.denominator_pair)}


@dataclass(frozen=True, slots=True)
class CongruencePolicy:
    output_slot: int

    def execute(
        self,
        runtime: StrictFoundationRuntime,
        partition: IntegerPartitionPolicy,
        value: int,
        modulus: int,
    ) -> int:
        return partition.execute(runtime, value, modulus)[self.output_slot]

    def to_dict(self) -> dict[str, Any]:
        return {"substrate": "output_projection_over_integer_partition_v14", "output_slot": self.output_slot}


@dataclass(frozen=True, slots=True)
class ModularProductPolicy:
    reduce_left: bool
    reduce_right: bool
    reduce_output: bool

    def execute(
        self,
        runtime: StrictFoundationRuntime,
        signed_product: SignedProductPolicy,
        partition: IntegerPartitionPolicy,
        congruence: CongruencePolicy,
        left: int,
        right: int,
        modulus: int,
    ) -> int:
        if modulus <= 0:
            raise ValueError("modulus must be positive")
        if self.reduce_left:
            left = congruence.execute(runtime, partition, left, modulus)
        if self.reduce_right:
            right = congruence.execute(runtime, partition, right, modulus)
        output = signed_product.execute(runtime, left, right)
        return congruence.execute(runtime, partition, output, modulus) if self.reduce_output else output

    def to_dict(self) -> dict[str, Any]:
        return {"substrate": "reduction_placement_over_strict_product_v14", "reduce_left": self.reduce_left, "reduce_right": self.reduce_right, "reduce_output": self.reduce_output}


@dataclass(frozen=True, slots=True)
class ModularFoldPolicy:
    seed: str
    operation: str
    reduce_each_step: bool
    reduce_final: bool

    def execute(
        self,
        runtime: StrictFoundationRuntime,
        signed_product: SignedProductPolicy,
        partition: IntegerPartitionPolicy,
        congruence: CongruencePolicy,
        modular_product: ModularProductPolicy,
        base: int,
        count: int,
        modulus: int,
    ) -> int:
        if count < 0 or modulus <= 0:
            raise ValueError("modular fold requires a natural count and positive modulus")
        state = {"zero": 0, "unit": 1, "base": base}[self.seed]
        for _ in range(count):
            if self.operation == "product":
                if self.reduce_each_step:
                    state = modular_product.execute(runtime, signed_product, partition, congruence, state, base, modulus)
                else:
                    state = signed_product.execute(runtime, state, base)
            else:
                state += base
                if self.reduce_each_step:
                    state = congruence.execute(runtime, partition, state, modulus)
        return congruence.execute(runtime, partition, state, modulus) if self.reduce_final else state

    def to_dict(self) -> dict[str, Any]:
        return {"substrate": "fold_over_modular_environment_v14", "seed": self.seed, "operation": self.operation, "reduce_each_step": self.reduce_each_step, "reduce_final": self.reduce_final}


@dataclass(frozen=True, slots=True)
class ClosureCandidate:
    candidate_id: str
    family: str
    policy: Any
    laws: dict[str, bool]
    behavior: tuple[Any, ...]

    @property
    def passed(self) -> bool:
        return all(self.laws.values())

    def to_dict(self) -> dict[str, Any]:
        return {"candidate_id": self.candidate_id, "family": self.family, "policy": self.policy.to_dict(), "laws": self.laws, "passed": self.passed}


@dataclass(frozen=True, slots=True)
class ClosureSearchReport:
    generated: int
    behavior_classes: int
    passing_behavior_classes: int
    selected: ClosureCandidate


def _id(family: str, policy: Any) -> str:
    payload = json.dumps(policy.to_dict(), sort_keys=True, separators=(",", ":"))
    return family + "-" + hashlib.sha256(payload.encode()).hexdigest()[:16]


class StrictAlgebraicClosureSearch:
    def __init__(
        self,
        runtime: StrictFoundationRuntime,
        signed_product: SignedProductPolicy,
        partition: IntegerPartitionPolicy,
    ) -> None:
        self.runtime = runtime
        self.signed_product = signed_product
        self.partition = partition

    def search_rational_product(self) -> ClosureSearchReport:
        samples = tuple((Fraction(a, b), Fraction(c, d)) for a, b, c, d in ((-2, 3, 4, 5), (3, 2, -5, 7), (0, 1, 9, 4), (7, 3, 2, 9)))
        candidates = []
        for numerator_pair, denominator_pair in itertools.product(COMPONENT_PAIRS, repeat=2):
            policy = RationalProductPolicy(numerator_pair, denominator_pair)
            try:
                behavior = tuple(policy.execute(self.runtime, self.signed_product, (left.numerator, left.denominator), (right.numerator, right.denominator)) for left, right in samples)
            except ValueError:
                continue
            def run(left: Fraction, right: Fraction) -> Fraction:
                n, d = policy.execute(self.runtime, self.signed_product, (left.numerator, left.denominator), (right.numerator, right.denominator))
                return Fraction(n, d)
            values = (Fraction(-2, 3), Fraction(0), Fraction(1), Fraction(3, 2), Fraction(5, 4))
            laws = {
                "representation_independent": all(run(Fraction(v.numerator * k, v.denominator * k), Fraction(2, 3)) == run(v, Fraction(2, 3)) for v in values for k in (1, 2, 3)),
                "commutative": all(run(a, b) == run(b, a) for a in values for b in values),
                "associative": all(run(run(a, b), c) == run(a, run(b, c)) for a in values for b in values for c in values),
                "identity": all(run(a, Fraction(1)) == a for a in values),
            }
            candidates.append(ClosureCandidate(_id("QR", policy), "rational_product", policy, laws, behavior))
        return self._finish(candidates)

    def search_congruence(self) -> ClosureSearchReport:
        candidates = []
        for slot in (0, 1):
            policy = CongruencePolicy(slot)
            cases = tuple((value, modulus) for value in range(-8, 9) for modulus in range(1, 6))
            behavior = tuple(policy.execute(self.runtime, self.partition, value, modulus) for value, modulus in cases)
            laws = {
                "canonical_range": all(0 <= policy.execute(self.runtime, self.partition, value, modulus) < modulus for value, modulus in cases),
                "representative_invariance": all(policy.execute(self.runtime, self.partition, value + shift * modulus, modulus) == policy.execute(self.runtime, self.partition, value, modulus) for value, modulus in cases for shift in range(-3, 4)),
                "idempotent": all(policy.execute(self.runtime, self.partition, policy.execute(self.runtime, self.partition, value, modulus), modulus) == policy.execute(self.runtime, self.partition, value, modulus) for value, modulus in cases),
            }
            candidates.append(ClosureCandidate(_id("CG", policy), "congruence_canonicalizer", policy, laws, behavior))
        return self._finish(candidates)

    def search_modular_product(self, congruence: CongruencePolicy) -> ClosureSearchReport:
        candidates = []
        cases = tuple((a, b, m) for a in range(-3, 4) for b in range(-3, 4) for m in range(2, 6))
        for bits in itertools.product((False, True), repeat=3):
            policy = ModularProductPolicy(*bits)
            behavior = tuple(policy.execute(self.runtime, self.signed_product, self.partition, congruence, *case) for case in cases)
            run = lambda a, b, m: policy.execute(self.runtime, self.signed_product, self.partition, congruence, a, b, m)
            laws = {
                "canonical_output": all(0 <= run(a, b, m) < m for a, b, m in cases),
                "representative_independence": all(run(a + i * m, b + j * m, m) == run(a, b, m) for a, b, m in cases for i in (-1, 1) for j in (-1, 1)),
                "commutative": all(run(a, b, m) == run(b, a, m) for a, b, m in cases),
                "associative": all(run(run(a, b, m), c, m) == run(a, run(b, c, m), m) for a in range(-2, 3) for b in range(-2, 3) for c in range(-2, 3) for m in range(2, 6)),
                "distributive": all(run(a, b + c, m) == congruence.execute(self.runtime, self.partition, run(a, b, m) + run(a, c, m), m) for a in range(-2, 3) for b in range(-2, 3) for c in range(-2, 3) for m in range(2, 6)),
            }
            candidates.append(ClosureCandidate(_id("MP", policy), "modular_product", policy, laws, behavior))
        return self._finish(candidates)

    def search_modular_fold(self, congruence: CongruencePolicy, modular_product: ModularProductPolicy) -> ClosureSearchReport:
        candidates = []
        cases = tuple((base, count, modulus) for base in range(-3, 5) for count in range(6) for modulus in range(2, 7))
        for seed, operation, reduce_each, reduce_final in itertools.product(("zero", "unit", "base"), ("combine", "product"), (False, True), (False, True)):
            policy = ModularFoldPolicy(seed, operation, reduce_each, reduce_final)
            try:
                behavior = tuple(policy.execute(self.runtime, self.signed_product, self.partition, congruence, modular_product, *case) for case in cases)
                run = lambda b, n, m: policy.execute(self.runtime, self.signed_product, self.partition, congruence, modular_product, b, n, m)
                laws = {
                    "canonical_every_step_policy": policy.reduce_each_step,
                    "zero_count_identity": all(run(base, 0, modulus) == congruence.execute(self.runtime, self.partition, 1, modulus) for base in range(-3, 4) for modulus in range(2, 7)),
                    "successor_recurrence": all(run(base, count + 1, modulus) == modular_product.execute(self.runtime, self.signed_product, self.partition, congruence, run(base, count, modulus), base, modulus) for base in range(-3, 4) for count in range(5) for modulus in range(2, 7)),
                    "count_addition_homomorphism": all(run(base, left + right, modulus) == modular_product.execute(self.runtime, self.signed_product, self.partition, congruence, run(base, left, modulus), run(base, right, modulus), modulus) for base in range(-2, 3) for left in range(3) for right in range(3) for modulus in range(2, 7)),
                    "representative_independence": all(run(base + shift * modulus, count, modulus) == run(base, count, modulus) for base in range(-3, 4) for count in range(5) for modulus in range(2, 7) for shift in (-2, 2)),
                }
            except (ArithmeticError, ValueError, RuntimeError):
                continue
            candidates.append(ClosureCandidate(_id("MF", policy), "modular_fold", policy, laws, behavior))
        return self._finish(candidates)

    @staticmethod
    def _finish(candidates: list[ClosureCandidate]) -> ClosureSearchReport:
        def policy_cost(candidate: ClosureCandidate) -> int:
            return sum(value is True for value in candidate.policy.to_dict().values())

        by_behavior: dict[tuple[Any, ...], ClosureCandidate] = {}
        for candidate in candidates:
            current = by_behavior.get(candidate.behavior)
            if current is None or (-sum(candidate.laws.values()), policy_cost(candidate), candidate.candidate_id) < (-sum(current.laws.values()), policy_cost(current), current.candidate_id):
                by_behavior[candidate.behavior] = candidate
        behaviors = sorted(by_behavior.values(), key=lambda item: (-sum(item.laws.values()), policy_cost(item), item.candidate_id))
        passing = [item for item in behaviors if item.passed]
        if not passing:
            raise RuntimeError("no algebraic closure policy passed")
        return ClosureSearchReport(len(candidates), len(behaviors), len(passing), passing[0])
