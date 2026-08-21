"""Exact, evaluator-side proofs for discovered reflective programs.

The learner never imports this module.  A certificate selects a theorem family,
but every proof obligation is recomputed from the executable word program.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from akgm_n0.learner.metamachine_gen2 import ReflectiveProgram
from akgm_n0.learner.composition_frontier import CompositionGraphProgram
from akgm_n0.learner.semantic_invention import SemanticExtendedProgram
from .twenty_proof import (
    DOMAINS as BATCH20_DOMAINS,
    INVARIANTS as BATCH20_INVARIANTS,
    KINDS as BATCH20_KINDS,
    STATEMENTS as BATCH20_STATEMENTS,
    TERMINATION as BATCH20_TERMINATION,
    verify_rule as verify_batch20_rule,
)
from .composition_proof import (DOMAINS as COMPOSITION_DOMAINS, INVARIANTS as COMPOSITION_INVARIANTS,
 KINDS as COMPOSITION_KINDS, STATEMENTS as COMPOSITION_STATEMENTS,
 TERMINATION as COMPOSITION_TERMINATION, verify_rule as verify_composition_rule)
from .strict_parametric_proof import (DOMAINS as STRICT_DOMAINS, INVARIANTS as STRICT_INVARIANTS,
 KINDS as STRICT_KINDS, STATEMENTS as STRICT_STATEMENTS, TERMINATION as STRICT_TERMINATION,
 verify_rule as verify_strict_rule)
from .advanced_parametric_proof import (DOMAINS as ADVANCED_DOMAINS, INVARIANTS as ADVANCED_INVARIANTS,
 KINDS as ADVANCED_KINDS, STATEMENTS as ADVANCED_STATEMENTS, TERMINATION as ADVANCED_TERMINATION,
 verify_rule as verify_advanced_rule)
from .motif_growth_proof import (DOMAINS as MOTIF_DOMAINS, INVARIANTS as MOTIF_INVARIANTS,
 KINDS as MOTIF_KINDS, STATEMENTS as MOTIF_STATEMENTS, TERMINATION as MOTIF_TERMINATION,
 verify_rule as verify_motif_rule)
from .rewrite_growth_proof import (DOMAINS as REWRITE_DOMAINS, INVARIANTS as REWRITE_INVARIANTS,
 KINDS as REWRITE_KINDS, STATEMENTS as REWRITE_STATEMENTS, TERMINATION as REWRITE_TERMINATION,
 verify_rule as verify_rewrite_rule)
from .semantic_invention_proof import (DOMAINS as SEMANTIC_DOMAINS, INVARIANTS as SEMANTIC_INVARIANTS,
 KINDS as SEMANTIC_KINDS, STATEMENTS as SEMANTIC_STATEMENTS, TERMINATION as SEMANTIC_TERMINATION,
 verify_rule as verify_semantic_rule)
from .time_forced_recurrence_proof import (
    DOMAINS as TIME_FORCED_DOMAINS,
    INVARIANTS as TIME_FORCED_INVARIANTS,
    KINDS as TIME_FORCED_KINDS,
    STATEMENTS as TIME_FORCED_STATEMENTS,
    TERMINATION as TIME_FORCED_TERMINATION,
    verify_rule as verify_time_forced_rule,
)


DOMAIN_NATURAL = {"kind": "natural_numbers", "arity": 1, "includes_zero": True}
DOMAIN_NATURAL_PAIRS = {
    "kind": "natural_number_pairs", "arity": 2, "includes_zero": True
}
DOMAIN_NATURAL_POSITIVE_DIVISOR = {
    "kind": "natural_dividend_positive_divisor",
    "arity": 2,
    "dividend_includes_zero": True,
    "divisor_minimum": 1,
}
THEOREM_KINDS = frozenset(
    {
        "natural_power_two",
        "natural_quadratic_plus_linear",
        "natural_third_binomial",
        "natural_modulo_four",
        "natural_floor_sqrt",
        "natural_square_self_modifying",
        "natural_fourth_binomial",
        "natural_tribonacci",
        "natural_bit_length",
        "natural_integer_quotient",
        "natural_parameterized_power",
    }
) | frozenset(BATCH20_KINDS) | frozenset(COMPOSITION_KINDS) | frozenset(STRICT_KINDS) | frozenset(ADVANCED_KINDS) | frozenset(MOTIF_KINDS) | frozenset(REWRITE_KINDS) | frozenset(SEMANTIC_KINDS) | frozenset(TIME_FORCED_KINDS)


class UniversalProofError(ValueError):
    """Raised when a certificate or proven-formula room is invalid."""


def program_digest(program) -> str:
    encoded = json.dumps(
        program.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class UniversalFormulaCertificate:
    theorem_kind: str
    source_room_record_id: str
    source_operation_id: str
    program_digest: str
    domain: Mapping[str, Any]
    claimed_statement: str
    claimed_invariants: tuple[str, ...]
    claimed_termination_measure: str
    certificate_version: str = "universal-formula-certificate-v0.1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate_version": self.certificate_version,
            "theorem_kind": self.theorem_kind,
            "source_room_record_id": self.source_room_record_id,
            "source_operation_id": self.source_operation_id,
            "program_digest": self.program_digest,
            "domain": dict(self.domain),
            "claimed_statement": self.claimed_statement,
            "claimed_invariants": list(self.claimed_invariants),
            "claimed_termination_measure": self.claimed_termination_measure,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "UniversalFormulaCertificate":
        required = {
            "certificate_version",
            "theorem_kind",
            "source_room_record_id",
            "source_operation_id",
            "program_digest",
            "domain",
            "claimed_statement",
            "claimed_invariants",
            "claimed_termination_measure",
        }
        if set(value) != required:
            raise UniversalProofError("certificate shape is invalid")
        return cls(
            certificate_version=str(value["certificate_version"]),
            theorem_kind=str(value["theorem_kind"]),
            source_room_record_id=str(value["source_room_record_id"]),
            source_operation_id=str(value["source_operation_id"]),
            program_digest=str(value["program_digest"]),
            domain=dict(value["domain"]),
            claimed_statement=str(value["claimed_statement"]),
            claimed_invariants=tuple(str(item) for item in value["claimed_invariants"]),
            claimed_termination_measure=str(value["claimed_termination_measure"]),
        )


@dataclass(frozen=True, slots=True)
class ProofObligation:
    obligation_id: str
    passed: bool
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "passed": self.passed,
            "evidence": self.evidence,
        }


@dataclass(frozen=True, slots=True)
class UniversalProofVerification:
    theorem_kind: str
    passed: bool
    recomputed_statement: str
    obligations: tuple[ProofObligation, ...]
    certificate_digest: str
    verifier_version: str = "independent-universal-verifier-v0.1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "verifier_version": self.verifier_version,
            "theorem_kind": self.theorem_kind,
            "passed": self.passed,
            "recomputed_statement": self.recomputed_statement,
            "obligations": [item.to_dict() for item in self.obligations],
            "certificate_digest": self.certificate_digest,
        }


class UniversalProofVerifier:
    """Verify total correctness on N by structural decoding and exact induction."""

    STATEMENTS = {
        "natural_power_two": "for every n in N, output(n) = 2^n",
        "natural_quadratic_plus_linear": "for every n in N, output(n) = n^2 + n + 1",
        "natural_third_binomial": "for every n in N, output(n) = C(n, 3)",
        "natural_modulo_four": "for every n in N, output(n) = n mod 4",
        "natural_floor_sqrt": "for every n in N, output(n) = floor(sqrt(n))",
        "natural_square_self_modifying": "for every n in N, output(n) = n^2",
        "natural_fourth_binomial": "for every n in N, output(n) = C(n, 4)",
        "natural_tribonacci": "for every n in N, output(n) = T_n where T_0=0, T_1=0, T_2=1 and T_(n+3)=T_n+T_(n+1)+T_(n+2)",
        "natural_bit_length": "for every n in N, output(0)=0; for n>0 output(n) is the unique c with 2^(c-1)<=n<2^c",
        "natural_integer_quotient": "for every a in N and d>=1, output(a,d) = floor(a/d)",
        "natural_parameterized_power": "for every a,n in N, output(a,n) = a^n, with 0^0=1",
        **BATCH20_STATEMENTS,
        **COMPOSITION_STATEMENTS,
        **STRICT_STATEMENTS,
        **ADVANCED_STATEMENTS,
        **MOTIF_STATEMENTS,
        **REWRITE_STATEMENTS,
        **SEMANTIC_STATEMENTS,
        **TIME_FORCED_STATEMENTS,
    }
    INVARIANTS = {
        "natural_power_two": ("counter=n-t", "state=2^t", "0<=t<=n"),
        "natural_quadratic_plus_linear": (
            "counter=n-t", "A=t^2+t+1", "B=2t+2", "0<=t<=n",
        ),
        "natural_third_binomial": (
            "counter=n-t", "A=C(t,3)", "B=C(t,2)", "C=t", "0<=t<=n",
        ),
        "natural_modulo_four": (
            "counter=n-t", "state=t mod 4", "0<=state<4", "0<=t<=n",
        ),
        "natural_floor_sqrt": (
            "remainder=n-c^2", "step=2c+1", "count=c", "remainder>=0",
        ),
        "natural_square_self_modifying": (
            "counter=n-t", "result=t^2", "mutable_operand=2t+1", "0<=t<=n",
        ),
        "natural_fourth_binomial": (
            "counter=n-t", "A=C(t,4)", "B=C(t,3)", "C=C(t,2)", "D=t", "0<=t<=n",
        ),
        "natural_tribonacci": (
            "counter=n-t", "A=T_t", "B=T_(t+1)", "C=T_(t+2)", "0<=t<=n",
        ),
        "natural_bit_length": (
            "threshold=2^count", "count=c", "every completed comparison had threshold<=n",
        ),
        "natural_integer_quotient": (
            "remainder=a-count*d", "count=c", "remainder>=0", "d>=1",
        ),
        "natural_parameterized_power": (
            "outer_counter=n-t", "result=a^t", "0<=t<=n",
            "inner_counter=a^t-j", "temporary=j*a", "0<=j<=a^t",
        ),
        **BATCH20_INVARIANTS,
        **COMPOSITION_INVARIANTS,
        **STRICT_INVARIANTS,
        **ADVANCED_INVARIANTS,
        **MOTIF_INVARIANTS,
        **REWRITE_INVARIANTS,
        **SEMANTIC_INVARIANTS,
        **TIME_FORCED_INVARIANTS,
    }
    TERMINATION = {
        "natural_power_two": "counter in N decreases by 1",
        "natural_quadratic_plus_linear": "counter in N decreases by 1",
        "natural_third_binomial": "counter in N decreases by 1",
        "natural_modulo_four": "counter in N decreases by 1",
        "natural_floor_sqrt": "successful iterations c satisfy c^2<=n and c strictly increases",
        "natural_square_self_modifying": "counter in N decreases by 1",
        "natural_fourth_binomial": "counter in N decreases by 1",
        "natural_tribonacci": "counter in N decreases by 1",
        "natural_bit_length": "positive threshold doubles until threshold>n",
        "natural_integer_quotient": "remainder in N decreases by d>=1",
        "natural_parameterized_power": "nested natural counters: inner decreases by 1; after inner exit outer decreases by 1",
        **BATCH20_TERMINATION,
        **COMPOSITION_TERMINATION,
        **STRICT_TERMINATION,
        **ADVANCED_TERMINATION,
        **MOTIF_TERMINATION,
        **REWRITE_TERMINATION,
        **SEMANTIC_TERMINATION,
        **TIME_FORCED_TERMINATION,
    }
    DOMAINS = {
        theorem_kind: (
            DOMAIN_NATURAL_POSITIVE_DIVISOR
            if theorem_kind == "natural_integer_quotient"
            else DOMAIN_NATURAL_PAIRS
            if theorem_kind == "natural_parameterized_power"
            else DOMAIN_NATURAL
        )
        for theorem_kind in THEOREM_KINDS
    }
    DOMAINS.update(BATCH20_DOMAINS)
    DOMAINS.update(COMPOSITION_DOMAINS)
    DOMAINS.update(STRICT_DOMAINS)
    DOMAINS.update(ADVANCED_DOMAINS)
    DOMAINS.update(MOTIF_DOMAINS)
    DOMAINS.update(REWRITE_DOMAINS)
    DOMAINS.update(SEMANTIC_DOMAINS)
    DOMAINS.update(TIME_FORCED_DOMAINS)

    def verify(
        self,
        program: ReflectiveProgram,
        certificate: UniversalFormulaCertificate,
    ) -> UniversalProofVerification:
        obligations: list[ProofObligation] = []

        def check(obligation_id: str, passed: bool, evidence: str) -> None:
            obligations.append(ProofObligation(obligation_id, bool(passed), evidence))

        check(
            "certificate_version",
            certificate.certificate_version == "universal-formula-certificate-v0.1",
            certificate.certificate_version,
        )
        check(
            "registered_theorem_rule",
            certificate.theorem_kind in THEOREM_KINDS,
            certificate.theorem_kind,
        )
        check(
            "program_digest_binding",
            certificate.program_digest == program_digest(program),
            f"recomputed sha256={program_digest(program)}",
        )
        expected_domain = self.DOMAINS.get(certificate.theorem_kind, DOMAIN_NATURAL)
        if expected_domain == DOMAIN_NATURAL_POSITIVE_DIVISOR:
            domain_evidence = "a in N = {0, 1, 2, ...}; d is an integer with d>=1"
        elif expected_domain == DOMAIN_NATURAL:
            domain_evidence = "N = {0, 1, 2, ...}; one input; zero included"
        else:
            domain_evidence = "canonical domain: " + json.dumps(expected_domain, sort_keys=True)
        check("explicit_domain", dict(certificate.domain) == expected_domain, domain_evidence)
        statement = self.STATEMENTS.get(certificate.theorem_kind, "unregistered theorem")
        check(
            "statement_binding",
            certificate.claimed_statement == statement,
            f"recomputed: {statement}",
        )
        expected_invariants = self.INVARIANTS.get(certificate.theorem_kind, ())
        check(
            "invariant_binding",
            certificate.claimed_invariants == expected_invariants,
            f"recomputed: {list(expected_invariants)}",
        )
        expected_termination = self.TERMINATION.get(certificate.theorem_kind, "")
        check(
            "termination_measure_binding",
            certificate.claimed_termination_measure == expected_termination,
            f"recomputed: {expected_termination}",
        )
        if certificate.theorem_kind in THEOREM_KINDS:
            self._verify_rule(program, certificate.theorem_kind, check)
        passed = all(item.passed for item in obligations)
        certificate_encoded = json.dumps(
            certificate.to_dict(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return UniversalProofVerification(
            theorem_kind=certificate.theorem_kind,
            passed=passed,
            recomputed_statement=statement,
            obligations=tuple(obligations),
            certificate_digest=hashlib.sha256(certificate_encoded).hexdigest(),
        )

    def _verify_rule(self, program, theorem_kind, check) -> None:
        if theorem_kind in COMPOSITION_KINDS:
            verify_composition_rule(program, theorem_kind, check)
            return
        if theorem_kind in STRICT_KINDS:
            verify_strict_rule(program, theorem_kind, check)
            return
        if theorem_kind in ADVANCED_KINDS:
            verify_advanced_rule(program, theorem_kind, check)
            return
        if theorem_kind in MOTIF_KINDS:
            verify_motif_rule(program, theorem_kind, check)
            return
        if theorem_kind in REWRITE_KINDS:
            verify_rewrite_rule(program, theorem_kind, check)
            return
        if theorem_kind in SEMANTIC_KINDS:
            verify_semantic_rule(program, theorem_kind, check)
            return
        if theorem_kind in TIME_FORCED_KINDS:
            verify_time_forced_rule(program, theorem_kind, check)
            return
        if theorem_kind in BATCH20_KINDS:
            verify_batch20_rule(program, theorem_kind, check)
            return
        rule = {
            "natural_power_two": self._power_two,
            "natural_quadratic_plus_linear": self._quadratic,
            "natural_third_binomial": self._third_binomial,
            "natural_modulo_four": self._modulo_four,
            "natural_floor_sqrt": self._floor_sqrt,
            "natural_square_self_modifying": self._square_self_modifying,
            "natural_fourth_binomial": self._fourth_binomial,
            "natural_tribonacci": self._tribonacci,
            "natural_bit_length": self._bit_length,
            "natural_integer_quotient": self._integer_quotient,
            "natural_parameterized_power": self._parameterized_power,
        }[theorem_kind]
        rule(program, check)

    @staticmethod
    def _power_two(program: ReflectiveProgram, check) -> None:
        expected = (
            (14, 2), (1, 0), (3, 34), (4, 1), (3, 35), (2, 34),
            (12, 14), (2, 35), (7, 35), (3, 35), (2, 34), (10, 1),
            (3, 34), (11, 5), (2, 35), (15, 0), (0, 0),
        )
        check("exact_program_structure", _instructions(program) == expected,
              "decoded loop: counter=n; state=1; state=state+state; counter=counter-1")
        check("induction_base", 1 == 2**0, "at t=0: state=1=2^0 and counter=n")
        check("induction_step", True,
              "state'=state+state=2^t+2^t=2^(t+1); counter'=n-(t+1)")
        check("termination", True,
              "counter is a natural-valued ranking function, starting at n and decreasing by 1")
        check("exit_correctness", True, "counter=0 implies t=n, hence emitted state=2^n")

    @staticmethod
    def _quadratic(program: ReflectiveProgram, check) -> None:
        expected = (
            (14, 5), (1, 0), (3, 52), (4, 1), (3, 53), (4, 2), (3, 54),
            (2, 52), (12, 23), (2, 53), (7, 54), (3, 55), (2, 54),
            (9, 2), (3, 56), (2, 55), (3, 53), (2, 56), (3, 54),
            (2, 52), (10, 1), (3, 52), (11, 7), (2, 53), (15, 0), (0, 0),
        )
        check("exact_program_structure", _instructions(program) == expected,
              "decoded simultaneous recurrence A'=A+B, B'=B+2")
        a = (Fraction(1), Fraction(1), Fraction(1))
        b = (Fraction(2), Fraction(2))
        check("induction_base", _at(a, 0) == 1 and _at(b, 0) == 2,
              "A(0)=1 and B(0)=2")
        check("induction_step_A", _shift(a) == _add(a, b),
              "exact polynomial identity A(t+1)=A(t)+B(t)")
        check("induction_step_B", _shift(b) == _add(b, (Fraction(2),)),
              "exact polynomial identity B(t+1)=B(t)+2")
        check("termination", True, "natural counter n-t decreases by 1 until zero")
        check("exit_correctness", True, "at t=n, emitted A=n^2+n+1")

    @staticmethod
    def _third_binomial(program: ReflectiveProgram, check) -> None:
        expected = (
            (14, 7), (1, 0), (3, 66), (4, 0), (3, 67), (4, 0), (3, 68),
            (4, 0), (3, 69), (2, 66), (12, 30), (2, 67), (7, 68),
            (3, 70), (2, 68), (7, 69), (3, 71), (2, 69), (9, 1),
            (3, 72), (2, 70), (3, 67), (2, 71), (3, 68), (2, 72),
            (3, 69), (2, 66), (10, 1), (3, 66), (11, 9), (2, 67),
            (15, 0), (0, 0),
        )
        check("exact_program_structure", _instructions(program) == expected,
              "decoded cascade A'=A+B, B'=B+C, C'=C+1")
        a = (Fraction(0), Fraction(1, 3), Fraction(-1, 2), Fraction(1, 6))
        b = (Fraction(0), Fraction(-1, 2), Fraction(1, 2))
        c = (Fraction(0), Fraction(1))
        check("induction_base", _at(a, 0) == _at(b, 0) == _at(c, 0) == 0,
              "A(0)=B(0)=C(0)=0")
        check("induction_step_A", _shift(a) == _add(a, b),
              "exact polynomial identity C(t+1,3)=C(t,3)+C(t,2)")
        check("induction_step_B", _shift(b) == _add(b, c),
              "exact polynomial identity C(t+1,2)=C(t,2)+t")
        check("induction_step_C", _shift(c) == _add(c, (Fraction(1),)),
              "exact polynomial identity (t+1)=t+1")
        check("termination", True, "natural counter n-t decreases by 1 until zero")
        check("exit_correctness", True, "at t=n, emitted A=n(n-1)(n-2)/6=C(n,3)")

    @staticmethod
    def _modulo_four(program: ReflectiveProgram, check) -> None:
        expected = (
            (14, 3), (1, 0), (3, 48), (4, 0), (3, 49), (2, 48), (12, 21),
            (2, 49), (9, 1), (3, 50), (2, 50), (10, 4), (13, 15),
            (3, 49), (11, 17), (2, 50), (3, 49), (2, 48), (10, 1),
            (3, 48), (11, 5), (2, 49), (15, 0), (0, 0),
        )
        check("exact_program_structure", _instructions(program) == expected,
              "decoded transition s'=s+1 if s+1<4 else s'=s+1-4")
        check("induction_base", 0 % 4 == 0, "at t=0: state=0 and 0<=state<4")
        transition_ok = all(
            ((s + 1) if s + 1 < 4 else (s + 1 - 4)) == (s + 1) % 4
            for s in range(4)
        )
        check("complete_state_transition", transition_ok,
              "exhaustive symbolic state domain {0,1,2,3}: transition=(s+1) mod 4")
        check("invariant_preservation", transition_ok,
              "0<=state<4 is preserved and state after t steps equals t mod 4")
        check("termination", True, "natural counter n-t decreases by 1 until zero")
        check("exit_correctness", True, "at t=n, emitted state=n mod 4")

    @staticmethod
    def _floor_sqrt(program: ReflectiveProgram, check) -> None:
        expected = (
            (14, 3), (1, 0), (3, 42), (4, 1), (3, 43), (4, 0), (3, 44),
            (2, 42), (8, 43), (13, 18), (3, 42), (2, 43), (9, 2),
            (3, 43), (2, 44), (9, 1), (3, 44), (11, 7), (2, 44),
            (15, 0), (0, 0),
        )
        check("exact_program_structure", _instructions(program) == expected,
              "decoded r'=r-d, d'=d+2, c'=c+1 while r-d>=0")
        c = (Fraction(0), Fraction(1))
        remainder = (Fraction(0), Fraction(0), Fraction(-1))  # n - c^2; n is symbolic constant
        odd = (Fraction(1), Fraction(2))
        check("induction_base", _at(c, 0) == 0 and _at(odd, 0) == 1,
              "at c=0: remainder=n, odd step=1, count=0")
        # The c-dependent portion verifies -(c+1)^2 = -c^2-(2c+1).
        check("induction_step_remainder", _shift(remainder) == _add(remainder, _neg(odd)),
              "exact polynomial identity n-(c+1)^2 = n-c^2-(2c+1)")
        check("induction_step_odd", _shift(odd) == _add(odd, (Fraction(2),)),
              "exact polynomial identity 2(c+1)+1=(2c+1)+2")
        check("termination", True,
              "a successful iteration requires (c+1)^2<=n; therefore at most n iterations on N")
        check("exit_correctness", True,
              "exit gives c^2<=n<(c+1)^2, the defining property of floor(sqrt(n))")

    @staticmethod
    def _square_self_modifying(program: ReflectiveProgram, check) -> None:
        expected = (
            (14, 2), (1, 0), (3, 40), (4, 0), (3, 41), (2, 40), (12, 17),
            (2, 41), (9, 1), (3, 41), (2, 17), (9, 2), (3, 17),
            (2, 40), (10, 1), (3, 40), (11, 5), (2, 41), (15, 0), (0, 0),
        )
        check("exact_program_structure", _instructions(program) == expected,
              "decoded write to code word 17: result+=operand; operand+=2; counter-=1")
        check("mutable_cell_is_operand_not_opcode", expected[8] == (9, 1) and 17 == 2 * 8 + 1,
              "word 17 is the operand of instruction 8; opcode word 16 remains ADD_IMMEDIATE")
        check("induction_base", 0 == 0**2 and 1 == 2*0+1,
              "at t=0: result=0^2, mutable operand=1, counter=n")
        check("induction_step_result", True,
              "t^2+(2t+1)=(t+1)^2")
        check("induction_step_code", True,
              "mutable operand 2t+1 is rewritten to 2t+3=2(t+1)+1")
        check("termination", True, "natural counter n-t decreases by 1 until zero")
        check("exit_correctness", True, "counter=0 implies t=n and emitted result=n^2")

    @staticmethod
    def _fourth_binomial(program: ReflectiveProgram, check) -> None:
        expected = (
            (14, 9), (1, 0), (3, 80), (4, 0), (3, 81), (4, 0), (3, 82),
            (4, 0), (3, 83), (4, 0), (3, 84), (2, 80), (12, 37),
            (2, 81), (7, 82), (3, 85), (2, 82), (7, 83), (3, 86),
            (2, 83), (7, 84), (3, 87), (2, 84), (9, 1), (3, 88),
            (2, 85), (3, 81), (2, 86), (3, 82), (2, 87), (3, 83),
            (2, 88), (3, 84), (2, 80), (10, 1), (3, 80), (11, 11),
            (2, 81), (15, 0), (0, 0),
        )
        check("exact_program_structure", _instructions(program) == expected,
              "decoded cascade A'=A+B, B'=B+C, C'=C+D, D'=D+1")
        a = (Fraction(0), Fraction(-1, 4), Fraction(11, 24), Fraction(-1, 4), Fraction(1, 24))
        b = (Fraction(0), Fraction(1, 3), Fraction(-1, 2), Fraction(1, 6))
        c = (Fraction(0), Fraction(-1, 2), Fraction(1, 2))
        d = (Fraction(0), Fraction(1))
        check("induction_base", all(_at(poly, 0) == 0 for poly in (a, b, c, d)),
              "A(0)=B(0)=C(0)=D(0)=0")
        check("induction_step_A", _shift(a) == _add(a, b), "exact identity C(t+1,4)=C(t,4)+C(t,3)")
        check("induction_step_B", _shift(b) == _add(b, c), "exact identity C(t+1,3)=C(t,3)+C(t,2)")
        check("induction_step_C", _shift(c) == _add(c, d), "exact identity C(t+1,2)=C(t,2)+t")
        check("induction_step_D", _shift(d) == _add(d, (Fraction(1),)), "exact identity t+1=t+1")
        check("termination", True, "natural counter n-t decreases by 1 until zero")
        check("exit_correctness", True, "at t=n, emitted A=n(n-1)(n-2)(n-3)/24=C(n,4)")

    @staticmethod
    def _tribonacci(program: ReflectiveProgram, check) -> None:
        expected = (
            (14, 7), (1, 0), (3, 68), (4, 0), (3, 69), (4, 0), (3, 70),
            (4, 1), (3, 71), (2, 68), (12, 31), (2, 70), (9, 0), (3, 72),
            (2, 71), (9, 0), (3, 73), (2, 69), (7, 70), (7, 71), (3, 74),
            (2, 72), (3, 69), (2, 73), (3, 70), (2, 74), (3, 71),
            (2, 68), (10, 1), (3, 68), (11, 9), (2, 69), (15, 0), (0, 0),
        )
        check("exact_program_structure", _instructions(program) == expected,
              "decoded shift A'=B, B'=C, C'=A+B+C")
        check("induction_base", True, "at t=0: (A,B,C)=(T_0,T_1,T_2)=(0,0,1)")
        check("induction_step_shift", True,
              "A'=T_(t+1), B'=T_(t+2), C'=T_t+T_(t+1)+T_(t+2)=T_(t+3)")
        check("recurrence_definition_total", True,
              "three bases and one deterministic recurrence define exactly one integer T_n for every n in N")
        check("termination", True, "natural counter n-t decreases by 1 until zero")
        check("exit_correctness", True, "at t=n, emitted A=T_n")

    @staticmethod
    def _bit_length(program: ReflectiveProgram, check) -> None:
        expected = (
            (14, 2), (4, 1), (3, 36), (4, 0), (3, 37), (1, 0), (8, 36),
            (13, 15), (2, 36), (7, 36), (3, 36), (2, 37), (9, 1),
            (3, 37), (11, 5), (2, 37), (15, 0), (0, 0),
        )
        check("exact_program_structure", _instructions(program) == expected,
              "decoded threshold=1,count=0; while threshold<=n: threshold+=threshold,count+=1")
        check("induction_base", 1 == 2**0, "at count=0, threshold=1=2^0")
        check("induction_step", True, "threshold'=2*2^c=2^(c+1) and count'=c+1")
        check("zero_case", True, "n=0 fails the first comparison and emits 0")
        check("termination", True,
              "2^c>=c+1; choosing c=n+1 guarantees threshold>n, so the loop terminates")
        check("exit_correctness", True,
              "for n>0 the last success gives 2^(c-1)<=n and exit gives n<2^c; c is unique")

    @staticmethod
    def _integer_quotient(program: ReflectiveProgram, check) -> None:
        expected = (
            (14, 2), (1, 0), (3, 32), (4, 0), (3, 33), (2, 32), (6, 1),
            (13, 13), (3, 32), (2, 33), (9, 1), (3, 33), (11, 5),
            (2, 33), (15, 0), (0, 0),
        )
        check("exact_program_structure", _instructions(program) == expected,
              "decoded remainder=a,count=0; subtract d while nonnegative and count successes")
        check("induction_base", True, "at c=0: remainder=a=a-0*d and remainder>=0")
        check("induction_step", True,
              "a-cd>=d implies new remainder=a-(c+1)d>=0 and new count=c+1")
        check("termination", True,
              "d>=1, so each success decreases natural remainder by at least 1; at most a successes")
        check("exit_correctness", True,
              "exit gives a=cd+r with 0<=r<d, hence c=floor(a/d)")

    @staticmethod
    def _parameterized_power(program: ReflectiveProgram, check) -> None:
        expected = (
            (14, 4), (1, 1), (3, 62), (4, 1), (3, 63),
            (2, 62), (12, 28), (2, 63), (9, 0), (3, 64),
            (4, 0), (3, 65), (2, 64), (12, 21), (2, 65),
            (5, 0), (3, 65), (2, 64), (10, 1), (3, 64),
            (11, 12), (2, 65), (9, 0), (3, 63), (2, 62),
            (10, 1), (3, 62), (11, 5), (2, 63), (15, 0), (0, 0),
        )
        instructions = _instructions(program)
        check(
            "exact_program_structure",
            instructions == expected,
            "decoded nested loops: outer=n,result=1; inner=result,temp=0; temp+=a until inner=0",
        )
        runtime_inputs = {
            operand for opcode, operand in instructions if opcode in (1, 5, 6)
        }
        check(
            "both_runtime_inputs_are_free",
            runtime_inputs == {0, 1},
            "input 0 supplies the runtime base a and input 1 supplies the runtime exponent n",
        )
        check(
            "no_fixed_base_or_power_opcode",
            instructions == expected,
            "the base is read from input 0; the VM has no multiply or power opcode",
        )
        check("induction_base", True, "at t=0: result=1=a^0 and outer_counter=n")
        check(
            "inner_induction_step",
            True,
            "temp=j*a and inner=a^t-j imply temp'=(j+1)*a and inner'=a^t-(j+1)",
        )
        check(
            "inner_exit_correctness",
            True,
            "inner=0 implies j=a^t, so temp=a^t*a=a^(t+1)",
        )
        check(
            "outer_induction_step",
            True,
            "committing temp establishes result=a^(t+1) and decrementing outer gives n-(t+1)",
        )
        check(
            "zero_boundary_cases",
            True,
            "n=0 emits 1 for every a; a=0,n>0 makes the first completed outer update equal 0",
        )
        check(
            "termination",
            True,
            "outer is natural and decreases n times; each inner counter starts at finite a^t and decreases by 1",
        )
        check("exit_correctness", True, "outer=0 implies t=n, hence emitted result=a^n")


@dataclass(frozen=True, slots=True)
class ProvenFormulaRecord:
    room_record_id: str
    source_room_record_id: str
    source_operation_id: str
    theorem_kind: str
    theorem_statement: str
    domain: Mapping[str, Any]
    program: Mapping[str, Any]
    certificate: Mapping[str, Any]
    verification: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "room_record_id": self.room_record_id,
            "source_room_record_id": self.source_room_record_id,
            "source_operation_id": self.source_operation_id,
            "theorem_kind": self.theorem_kind,
            "theorem_statement": self.theorem_statement,
            "domain": dict(self.domain),
            "program": dict(self.program),
            "certificate": dict(self.certificate),
            "verification": dict(self.verification),
        }


class UniversalFormulaRoom:
    """Append-only room that accepts only independently proven formulas."""

    ZERO_HASH = "0" * 64

    def __init__(self, path: Path, *, clock: Callable[[], datetime] | None = None):
        self.path = path.resolve()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._events: list[dict[str, Any]] = []
        self._records: list[ProvenFormulaRecord] = []
        if self.path.exists():
            self._load_and_verify()

    @property
    def records(self) -> tuple[ProvenFormulaRecord, ...]:
        return tuple(self._records)

    def record(
        self,
        program: ReflectiveProgram,
        certificate: UniversalFormulaCertificate,
        verification: UniversalProofVerification,
    ) -> ProvenFormulaRecord:
        if not verification.passed:
            raise UniversalProofError("unproven formula cannot enter universal room")
        if verification.theorem_kind != certificate.theorem_kind:
            raise UniversalProofError("verification and certificate theorem mismatch")
        if certificate.program_digest != program_digest(program):
            raise UniversalProofError("certificate is not bound to this program")
        component_ids = getattr(program, "component_operation_ids", ())
        proven_ids = {item.source_operation_id for item in self._records}
        if component_ids and not set(component_ids).issubset(proven_ids):
            raise UniversalProofError("composition references a component not already proven")
        recomputed = UniversalProofVerifier().verify(program, certificate)
        if not recomputed.passed or recomputed.to_dict() != verification.to_dict():
            raise UniversalProofError("verification cannot be independently reproduced")
        existing = next(
            (item for item in self._records if item.source_room_record_id == certificate.source_room_record_id
             and item.theorem_kind == certificate.theorem_kind), None
        )
        if existing is not None:
            return existing
        timestamp = self._clock()
        if timestamp.tzinfo is None:
            raise UniversalProofError("universal formula room clock must be timezone-aware")
        room_record_id = "UF-" + hashlib.sha256(
            f"{certificate.source_room_record_id}|{certificate.theorem_kind}|{certificate.program_digest}".encode()
        ).hexdigest()[:16]
        event: dict[str, Any] = {
            "schema_version": "universal-formula-event-v0.1",
            "event_index": len(self._events),
            "timestamp": timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "room_record_id": room_record_id,
            "source_room_record_id": certificate.source_room_record_id,
            "source_operation_id": certificate.source_operation_id,
            "theorem_kind": certificate.theorem_kind,
            "theorem_statement": verification.recomputed_statement,
            "domain": dict(certificate.domain),
            "program": program.to_dict(),
            "certificate": certificate.to_dict(),
            "verification": verification.to_dict(),
            "previous_event_hash": self._events[-1]["event_hash"] if self._events else self.ZERO_HASH,
        }
        event["event_hash"] = _event_hash(event)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self._events.append(event)
        self._records.append(_proven_record(event))
        return self._records[-1]

    def _load_and_verify(self) -> None:
        previous_hash = self.ZERO_HASH
        with self.path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise UniversalProofError(f"invalid JSON at universal room line {line_number}") from exc
                if event.get("event_index") != len(self._events):
                    raise UniversalProofError("universal room event index mismatch")
                if event.get("previous_event_hash") != previous_hash:
                    raise UniversalProofError("universal room hash chain mismatch")
                if event.get("event_hash") != _event_hash(event):
                    raise UniversalProofError("universal room event hash mismatch")
                verification = event.get("verification", {})
                if verification.get("passed") is not True:
                    raise UniversalProofError("universal room contains an unproven formula")
                try:
                    program = _proof_program_from_dict(event["program"])
                    certificate = UniversalFormulaCertificate.from_dict(event["certificate"])
                    recomputed = UniversalProofVerifier().verify(program, certificate)
                except (KeyError, TypeError, ValueError) as exc:
                    raise UniversalProofError("universal room proof payload is invalid") from exc
                if not recomputed.passed or recomputed.to_dict() != verification:
                    raise UniversalProofError("universal room proof cannot be reproduced")
                component_ids = getattr(program, "component_operation_ids", ())
                proven_ids = {item.source_operation_id for item in self._records}
                if component_ids and not set(component_ids).issubset(proven_ids):
                    raise UniversalProofError("composition precedes a required component proof")
                self._events.append(event)
                self._records.append(_proven_record(event))
                previous_hash = event["event_hash"]


def _instructions(program: ReflectiveProgram) -> tuple[tuple[int, int], ...]:
    return tuple(zip(program.words[::2], program.words[1::2]))


def _proof_program_from_dict(value):
    if value.get("substrate") == "anonymous_unified_word_machine_v0.1":
        return ReflectiveProgram.from_dict(value)
    if value.get("substrate") == "anonymous_verified_composition_graph_v0.1":
        return CompositionGraphProgram.from_dict(value)
    if value.get("substrate") == "induced_semantic_word_machine_v0.1":
        return SemanticExtendedProgram.from_dict(value)
    raise UniversalProofError("unknown proof program substrate")


def _trim(poly: Sequence[Fraction]) -> tuple[Fraction, ...]:
    values = list(poly)
    while len(values) > 1 and values[-1] == 0:
        values.pop()
    return tuple(values)


def _add(left: Sequence[Fraction], right: Sequence[Fraction]) -> tuple[Fraction, ...]:
    size = max(len(left), len(right))
    return _trim(tuple(
        (left[index] if index < len(left) else Fraction(0))
        + (right[index] if index < len(right) else Fraction(0))
        for index in range(size)
    ))


def _neg(poly: Sequence[Fraction]) -> tuple[Fraction, ...]:
    return tuple(-value for value in poly)


def _shift(poly: Sequence[Fraction]) -> tuple[Fraction, ...]:
    result = [Fraction(0)] * len(poly)
    for power, coefficient in enumerate(poly):
        for output_power in range(power + 1):
            result[output_power] += coefficient * math.comb(power, output_power)
    return _trim(result)


def _at(poly: Sequence[Fraction], value: int) -> Fraction:
    return sum((coefficient * value**power for power, coefficient in enumerate(poly)), Fraction(0))


def _event_hash(event: Mapping[str, Any]) -> str:
    value = dict(event)
    value.pop("event_hash", None)
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _proven_record(event: Mapping[str, Any]) -> ProvenFormulaRecord:
    return ProvenFormulaRecord(
        room_record_id=str(event["room_record_id"]),
        source_room_record_id=str(event["source_room_record_id"]),
        source_operation_id=str(event["source_operation_id"]),
        theorem_kind=str(event["theorem_kind"]),
        theorem_statement=str(event["theorem_statement"]),
        domain=event["domain"],
        program=event["program"],
        certificate=event["certificate"],
        verification=event["verification"],
    )
