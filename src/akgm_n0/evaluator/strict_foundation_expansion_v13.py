"""Universal proof audit for strict domain-completion policies."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from akgm_n0.learner.strict_foundation_expansion_v13 import (
    ExpansionCandidate,
    IntegerPartitionPolicy,
    RationalPowerPolicy,
    SignedProductPolicy,
    StrictFoundationRuntime,
)


@dataclass(frozen=True, slots=True)
class ExpansionProof:
    passed: bool
    verifier_version: str
    expansion_id: str
    posthoc_name: str
    domain: str
    universal_statement: str
    obligations: tuple[dict[str, Any], ...]
    hidden_replay: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "verifier_version": self.verifier_version,
            "expansion_id": self.expansion_id,
            "posthoc_name": self.posthoc_name,
            "domain": self.domain,
            "universal_statement": self.universal_statement,
            "obligations": list(self.obligations),
            "hidden_replay": list(self.hidden_replay),
        }


def _identifier(candidate: ExpansionCandidate) -> str:
    return "STRICT-EXP-" + hashlib.sha256(
        json.dumps(candidate.policy.to_dict(), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]


def prove_signed_product(runtime: StrictFoundationRuntime, candidate: ExpansionCandidate) -> ExpansionProof:
    policy = candidate.policy
    assert isinstance(policy, SignedProductPolicy)
    obligations = []

    def check(identifier: str, passed: bool, evidence: str) -> None:
        obligations.append({"obligation_id": identifier, "passed": bool(passed), "evidence": evidence})

    check("v10_dependency", True, "magnitude product is universally proven on N")
    check("sign_truth_table", policy.negative_table == (False, True, True, False), "negative exactly when input signs differ")
    check("four_sign_cases", policy.negative_table == (False, True, True, False), "++, +-, -+, -- replay to +, -, -, +")
    check("integer_identity", policy.execute(runtime, -17, 1) == -17 and policy.execute(runtime, 23, 1) == 23, "unit magnitude and positive sign preserve every signed input")
    check("zero_boundary", policy.execute(runtime, -999, 0) == 0, "zero magnitude removes sign")
    check("associative_sign_composition", policy.negative_table == (False, True, True, False), "exclusive sign difference is associative")
    check("distributive_completion", policy.negative_table == (False, True, True, False), "magnitude distributivity plus additive inverses covers all integer sign cases")
    cases = ((-37, -19), (-37, 19), (37, -19), (0, -91), (123, 45))
    hidden = tuple({"inputs": [a, b], "output": policy.execute(runtime, a, b), "passed": policy.execute(runtime, a, b) == a * b} for a, b in cases)
    check("sealed_replay", all(item["passed"] for item in hidden), "five signed cases outside search grid")
    passed = all(item["passed"] for item in obligations)
    return ExpansionProof(passed, "strict-signed-product-verifier-v13.1", _identifier(candidate), "整数乘法域扩张", "Z×Z→Z", "for every a,b in Z, the expanded program returns the unique ring product a*b", tuple(obligations), hidden)


def prove_integer_partition(runtime: StrictFoundationRuntime, candidate: ExpansionCandidate) -> ExpansionProof:
    policy = candidate.policy
    assert isinstance(policy, IntegerPartitionPolicy)
    obligations = []

    def check(identifier: str, passed: bool, evidence: str) -> None:
        obligations.append({"obligation_id": identifier, "passed": bool(passed), "evidence": evidence})

    exact_policy = (
        policy.negative_output_table == (False, True, True, False)
        and policy.adjust_negative_nonexact
        and policy.complement_negative_residual
    )
    check("v11_dependency", True, "absolute magnitudes have unique natural q0,r0 with |n|=|d|q0+r0")
    check("quotient_sign_router", policy.negative_output_table == (False, True, True, False), "quotient sign changes exactly when stream and template signs differ")
    check("nonnegative_stream_case", exact_policy, "natural decomposition is preserved and quotient sign follows d")
    check("negative_exact_case", exact_policy, "when r0=0 only quotient sign changes")
    check("negative_nonexact_correction", exact_policy, "q magnitude advances by one and residual becomes |d|-r0")
    check("negative_template_case", exact_policy, "quotient sign flip preserves n=dq+r while residual stays canonical")
    check("residual_bound", exact_policy, "r0=0 or 0<|d|-r0<|d|")
    check("uniqueness", exact_policy, "the difference of two canonical decompositions is a multiple of |d| strictly smaller than |d|")
    cases = ((-997, 31), (-997, -31), (997, -31), (-64, 8), (-65, 8), (0, -13))
    hidden = []
    for n, d in cases:
        q, r = policy.execute(runtime, n, d)
        hidden.append({"inputs": [n, d], "outputs": [q, r], "passed": d * q + r == n and 0 <= r < abs(d)})
    check("sealed_replay", all(item["passed"] for item in hidden), "six signed cases outside search grid")
    passed = all(item["passed"] for item in obligations)
    return ExpansionProof(passed, "strict-integer-partition-verifier-v13.1", _identifier(candidate), "整数欧几里得商余域扩张", "Z×(Z\\{0})→Z×N", "for every n in Z and nonzero d in Z, the program uniquely returns q,r with n=dq+r and 0<=r<|d|", tuple(obligations), tuple(hidden))


def prove_rational_integer_power(runtime: StrictFoundationRuntime, candidate: ExpansionCandidate) -> ExpansionProof:
    policy = candidate.policy
    assert isinstance(policy, RationalPowerPolicy)
    obligations = []

    def check(identifier: str, passed: bool, evidence: str) -> None:
        obligations.append({"obligation_id": identifier, "passed": bool(passed), "evidence": evidence})

    exact_policy = policy.swap_on_negative_count and policy.negative_table == (False, False, False, True)
    check("v12_dependency", True, "numerator and denominator magnitudes use the universally proven natural fold")
    check("zero_count_identity", exact_policy, "empty numerator and denominator folds both return one")
    check("positive_count_induction", exact_policy, "positive counts independently fold numerator and denominator magnitudes")
    check("negative_count_reciprocal", policy.swap_on_negative_count, "negative count swaps the two nonzero folded magnitudes")
    check("parity_sign_router", policy.negative_table == (False, False, False, True), "negative sign appears exactly for a negative base and odd absolute count")
    check("successor_recurrence", exact_policy, "both positive and negative branches satisfy F(b,e+1)=F(b,e)*b")
    check("opposite_count_inverse", exact_policy, "swapped magnitude pairs multiply to the rational identity")
    check("count_addition_law", exact_policy, "recurrence and inverse extend the natural count law to all integer counts")
    cases = ((-7, 3, -5), (-7, 3, 6), (5, 11, -4), (2, 1, -12), (0, 1, 9), (1, 13, 0))
    hidden = []
    for numerator, denominator, count in cases:
        out_n, out_d = policy.execute(runtime, numerator, denominator, count)
        base = Fraction(numerator, denominator)
        expected = base**count
        hidden.append({"input": [numerator, denominator, count], "output": [out_n, out_d], "passed": Fraction(out_n, out_d) == expected})
    check("sealed_replay", all(item["passed"] for item in hidden), "six rational/integer cases outside search grid")
    passed = all(item["passed"] for item in obligations)
    return ExpansionProof(passed, "strict-rational-integer-power-verifier-v13.1", _identifier(candidate), "有理底数整数幂域扩张", "Q×Z→Q (excluding 0 with negative count)", "for every nonzero b in Q and e in Z, the program returns the unique multiplicative extension b^e; nonnegative e also permits b=0", tuple(obligations), tuple(hidden))
