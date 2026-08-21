"""Search minimal domain-completion policies for strict V10-V12 semantics."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from .strict_counter_foundation_v10 import CounterExecutor, CounterProgram
from .strict_fold_foundation_v12 import FoldExecutor, FoldProgram
from .strict_partition_foundation_v11 import EventCounterExecutor, EventCounterProgram


class ExpansionDomainError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StrictFoundationRuntime:
    product_program: CounterProgram
    partition_program: EventCounterProgram
    fold_program: FoldProgram

    def natural_product(self, left: int, right: int) -> int:
        return CounterExecutor(maximum_steps=5_000_000).execute(
            self.product_program, (left, right)
        ).output

    def natural_partition(self, stream: int, template: int) -> tuple[int, int]:
        program = self.partition_program
        inputs = (stream, template) if program.stream_input == 0 else (template, stream)
        return EventCounterExecutor(maximum_steps=5_000_000).execute(program, inputs).outputs

    def natural_fold(self, base: int, count: int) -> int:
        program = self.fold_program
        base_input = 1 - program.loop_input
        inputs = (base, count) if base_input == 0 else (count, base)
        return FoldExecutor(magnitude_limit=10**200).execute(program, inputs).output


@dataclass(frozen=True, slots=True)
class SignedProductPolicy:
    negative_table: tuple[bool, bool, bool, bool]

    def execute(self, runtime: StrictFoundationRuntime, left: int, right: int) -> int:
        magnitude = runtime.natural_product(abs(left), abs(right))
        index = 2 * (left < 0) + (right < 0)
        return -magnitude if self.negative_table[index] and magnitude else magnitude

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "sign_router_over_strict_v10",
            "negative_table": list(self.negative_table),
            "magnitude_semantic": "STRICT-FSEM-82df58ba4ce6f41c",
        }


@dataclass(frozen=True, slots=True)
class IntegerPartitionPolicy:
    negative_output_table: tuple[bool, bool, bool, bool]
    adjust_negative_nonexact: bool
    complement_negative_residual: bool

    def execute(
        self, runtime: StrictFoundationRuntime, stream: int, template: int
    ) -> tuple[int, int]:
        if template == 0:
            raise ExpansionDomainError("integer partition template cannot be zero")
        first, residual = runtime.natural_partition(abs(stream), abs(template))
        nonexact_negative = stream < 0 and residual > 0
        magnitude = first + int(self.adjust_negative_nonexact and nonexact_negative)
        if self.complement_negative_residual and nonexact_negative:
            residual = abs(template) - residual
        index = 2 * (stream < 0) + (template < 0)
        first = -magnitude if self.negative_output_table[index] and magnitude else magnitude
        return first, residual

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "signed_correction_over_strict_v11",
            "negative_output_table": list(self.negative_output_table),
            "adjust_negative_nonexact": self.adjust_negative_nonexact,
            "complement_negative_residual": self.complement_negative_residual,
            "partition_semantic": "strict_v11_two_output",
        }


@dataclass(frozen=True, slots=True)
class RationalPowerPolicy:
    swap_on_negative_count: bool
    negative_table: tuple[bool, bool, bool, bool]

    def execute(
        self,
        runtime: StrictFoundationRuntime,
        numerator: int,
        denominator: int,
        count: int,
    ) -> tuple[int, int]:
        if denominator <= 0:
            raise ExpansionDomainError("rational denominator must be positive")
        if numerator == 0 and count < 0:
            raise ExpansionDomainError("zero has no negative-count extension")
        magnitude_numerator = runtime.natural_fold(abs(numerator), abs(count))
        magnitude_denominator = runtime.natural_fold(denominator, abs(count))
        if count < 0 and self.swap_on_negative_count:
            magnitude_numerator, magnitude_denominator = magnitude_denominator, magnitude_numerator
        index = 2 * (numerator < 0) + (abs(count) % 2 == 1)
        if self.negative_table[index] and magnitude_numerator:
            magnitude_numerator = -magnitude_numerator
        return magnitude_numerator, magnitude_denominator

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "reciprocal_sign_router_over_strict_v12",
            "swap_on_negative_count": self.swap_on_negative_count,
            "negative_table": list(self.negative_table),
            "fold_semantic": "strict_v12_fold",
        }


@dataclass(frozen=True, slots=True)
class ExpansionCandidate:
    candidate_id: str
    family: str
    policy: Any
    law_profile: dict[str, bool]
    behavior_signature: tuple[Any, ...]

    @property
    def passed(self) -> bool:
        return all(self.law_profile.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "family": self.family,
            "policy": self.policy.to_dict(),
            "law_profile": self.law_profile,
            "behavior_signature": [list(item) if isinstance(item, tuple) else item for item in self.behavior_signature],
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class ExpansionSearchReport:
    generated: int
    behavior_classes: int
    passing_behavior_classes: int
    selected: ExpansionCandidate


def _candidate_id(family: str, policy: Any) -> str:
    payload = json.dumps(policy.to_dict(), sort_keys=True, separators=(",", ":"))
    return family + "-" + hashlib.sha256(payload.encode()).hexdigest()[:16]


class StrictFoundationExpander:
    def __init__(self, runtime: StrictFoundationRuntime) -> None:
        self.runtime = runtime

    def search_signed_product(self) -> ExpansionSearchReport:
        candidates = []
        for table in itertools.product((False, True), repeat=4):
            policy = SignedProductPolicy(table)
            values = range(-4, 5)
            signature = tuple(policy.execute(self.runtime, a, b) for a in values for b in values)
            law_profile = {
                "commutative": all(policy.execute(self.runtime, a, b) == policy.execute(self.runtime, b, a) for a in values for b in values),
                "associative": all(policy.execute(self.runtime, policy.execute(self.runtime, a, b), c) == policy.execute(self.runtime, a, policy.execute(self.runtime, b, c)) for a in range(-2, 3) for b in range(-2, 3) for c in range(-2, 3)),
                "integer_identity": all(policy.execute(self.runtime, a, 1) == a == policy.execute(self.runtime, 1, a) for a in values),
                "zero_annihilator": all(policy.execute(self.runtime, a, 0) == 0 == policy.execute(self.runtime, 0, a) for a in values),
                "distributive_over_integer_combine": all(policy.execute(self.runtime, a, b + c) == policy.execute(self.runtime, a, b) + policy.execute(self.runtime, a, c) for a in range(-2, 3) for b in range(-2, 3) for c in range(-2, 3)),
            }
            candidates.append(ExpansionCandidate(_candidate_id("SP", policy), "signed_product", policy, law_profile, signature))
        return self._finish(candidates)

    def search_integer_partition(self) -> ExpansionSearchReport:
        candidates = []
        for table, adjust, complement in itertools.product(
            itertools.product((False, True), repeat=4), (False, True), (False, True)
        ):
            policy = IntegerPartitionPolicy(tuple(table), adjust, complement)
            cases = tuple((n, d) for n in range(-9, 10) for d in range(-5, 6) if d)
            signature = tuple(policy.execute(self.runtime, n, d) for n, d in cases)
            law_profile = {
                "integer_reconstruction": all(d * q + r == n for (n, d), (q, r) in zip(cases, signature, strict=True)),
                "canonical_nonnegative_residual": all(0 <= r < abs(d) for (_, d), (_, r) in zip(cases, signature, strict=True)),
                "exact_cases_preserved": all((r == 0) == (d * q == n) for (n, d), (q, r) in zip(cases, signature, strict=True)),
                "unique_canonical_pair": all(not any(d * other_q + other_r == n and 0 <= other_r < abs(d) for other_q in range(q - 3, q + 4) for other_r in range(abs(d)) if (other_q, other_r) != (q, r)) for (n, d), (q, r) in zip(cases, signature, strict=True)),
            }
            candidates.append(ExpansionCandidate(_candidate_id("IP", policy), "integer_partition", policy, law_profile, signature))
        return self._finish(candidates)

    def search_rational_integer_power(self) -> ExpansionSearchReport:
        candidates = []
        bases = tuple(Fraction(n, d) for n, d in ((-3, 2), (-2, 1), (-1, 2), (1, 2), (1, 1), (3, 2), (2, 1)))
        counts = range(-3, 4)
        for swap, table in itertools.product((False, True), itertools.product((False, True), repeat=4)):
            policy = RationalPowerPolicy(swap, tuple(table))

            def run(base: Fraction, count: int) -> Fraction:
                numerator, denominator = policy.execute(self.runtime, base.numerator, base.denominator, count)
                return Fraction(numerator, denominator)

            signature = tuple((run(base, count).numerator, run(base, count).denominator) for base in bases for count in counts)
            law_profile = {
                "zero_count_identity": all(run(base, 0) == 1 for base in bases),
                "integer_successor_recurrence": all(run(base, count + 1) == run(base, count) * base for base in bases for count in range(-3, 3)),
                "opposite_counts_are_inverses": all(run(base, count) * run(base, -count) == 1 for base in bases for count in range(1, 4)),
                "count_addition_homomorphism": all(run(base, left + right) == run(base, left) * run(base, right) for base in bases for left in range(-1, 2) for right in range(-1, 2)),
            }
            candidates.append(ExpansionCandidate(_candidate_id("RP", policy), "rational_integer_power", policy, law_profile, signature))
        return self._finish(candidates)

    @staticmethod
    def _finish(candidates: list[ExpansionCandidate]) -> ExpansionSearchReport:
        by_behavior: dict[tuple[Any, ...], ExpansionCandidate] = {}
        for candidate in candidates:
            current = by_behavior.get(candidate.behavior_signature)
            if current is None or (-sum(candidate.law_profile.values()), candidate.candidate_id) < (-sum(current.law_profile.values()), current.candidate_id):
                by_behavior[candidate.behavior_signature] = candidate
        behaviors = sorted(by_behavior.values(), key=lambda item: (-sum(item.law_profile.values()), item.candidate_id))
        passing = [item for item in behaviors if item.passed]
        if not passing:
            raise RuntimeError("domain expansion produced no universally lawful behavior")
        return ExpansionSearchReport(len(candidates), len(behaviors), len(passing), passing[0])
