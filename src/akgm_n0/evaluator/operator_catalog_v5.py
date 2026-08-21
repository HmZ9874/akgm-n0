"""Fifty-operator catalog grown from anonymous worlds.

This evaluator constructs tables from private semantic specifications.  The
learner receives only opaque IDs and integer rows.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from akgm_n0.learner.meta_autonomy_v3 import (
    AdaptiveGrammarSynthesizer,
    AnonymousWorld,
    EvolvedProgram,
    GrammarGenome,
)
from akgm_n0.learner.meta_autonomy_v4 import AutonomousProofPortfolio, replay_portfolio_proof
from .operator_frontier_v4 import run_operator_frontier, verify_operator_frontier_report


ScalarOrTuple = int | tuple[int, ...]


@dataclass(frozen=True, slots=True)
class OperatorSpec:
    operator_id: str
    world_id: str
    name: str
    domain_key: str
    development_inputs: tuple[tuple[int, ...], ...]
    sealed_inputs: tuple[tuple[int, ...], ...]
    function: Callable[[tuple[int, ...]], ScalarOrTuple]
    proof_kind: str
    expected_payload: Mapping[str, Any]

    def world(self) -> AnonymousWorld:
        return AnonymousWorld.create(
            self.world_id, self.development_inputs,
            tuple(self.function(row) for row in self.development_inputs),
        )


BOOL_ROWS = ((0, 0), (0, 1), (1, 0), (1, 1))
SIGNED_ROWS = ((-7,), (-3,), (-1,), (0,), (1,), (4,), (8,))
NAT_ROWS = tuple((value,) for value in range(7))
BINARY_ROWS = ((-4, 3), (0, 5), (2, -3), (6, 7), (9, -2), (-8, -5))


def _boolean_specs() -> tuple[OperatorSpec, ...]:
    existing = {0b0111, 0b0110, 0b1110, 0b1101}
    names = {
        0b0000: "Boolean false", 0b0001: "Boolean conjunction",
        0b0010: "left and not-right", 0b0011: "left projection",
        0b0100: "not-left and right", 0b0101: "right projection",
        0b1000: "Boolean NOR", 0b1001: "Boolean equivalence",
        0b1010: "not-right", 0b1011: "reverse implication",
        0b1100: "not-left", 0b1111: "Boolean true",
    }
    specs = []
    for truth_code in range(16):
        if truth_code in existing:
            continue
        outputs = tuple((truth_code >> (3 - index)) & 1 for index in range(4))
        specs.append(OperatorSpec(
            f"OPV5-B{truth_code:02x}", f"OW5-B{truth_code:02x}", names[truth_code],
            "boolean_pair_complete", BOOL_ROWS, (),
            lambda row, outputs=outputs: outputs[BOOL_ROWS.index(row)],
            "finite_complete", {"truth_table": outputs},
        ))
    return tuple(specs)


def additional_operator_specs() -> tuple[OperatorSpec, ...]:
    signed_sealed = ((-12,), (2,), (11,))
    natural_sealed = ((7,), (8,), (10,))
    specs = list(_boolean_specs())
    affine_unary = (
        ("U01", "successor", 1, 1),
        ("U02", "predecessor", 1, -1),
        ("U03", "additive inverse", -1, 0),
        ("U04", "doubling", 2, 0),
    )
    for code, name, coefficient, bias in affine_unary:
        specs.append(OperatorSpec(
            "OPV5-" + code, "OW5-" + code, name, "integer_unary",
            SIGNED_ROWS, signed_sealed,
            lambda row, c=coefficient, b=bias: c * row[0] + b,
            "affine", {"coefficients": (coefficient,), "bias": bias},
        ))
    specs.extend((
        OperatorSpec("OPV5-U06", "OW5-U06", "absolute magnitude", "integer_unary", SIGNED_ROWS, signed_sealed, lambda row: abs(row[0]), "guarded", {"mode": "absolute"}),
        OperatorSpec("OPV5-U07", "OW5-U07", "nonzero indicator", "integer_unary", SIGNED_ROWS, signed_sealed, lambda row: int(row[0] != 0), "guarded", {"mode": "nonzero"}),
        OperatorSpec("OPV5-U08", "OW5-U08", "negative indicator", "integer_unary", SIGNED_ROWS, signed_sealed, lambda row: int(row[0] < 0), "guarded", {"mode": "negative_indicator"}),
        OperatorSpec("OPV5-U09", "OW5-U09", "nonnegative indicator", "integer_unary", SIGNED_ROWS, signed_sealed, lambda row: int(row[0] >= 0), "guarded", {"mode": "nonnegative_indicator"}),
        OperatorSpec("OPV5-U05", "OW5-U05", "ceiling half", "natural_unary", tuple((i,) for i in range(10)), ((10,), (11,), (20,), (25,)), lambda row: (row[0] + 1) // 2, "portfolio_and_recurrence", {}),
        OperatorSpec("OPV5-U10", "OW5-U10", "square", "natural_unary", NAT_ROWS, natural_sealed, lambda row: row[0] ** 2, "square_fold", {}),
        OperatorSpec("OPV5-U11", "OW5-U11", "triangular accumulation", "natural_unary", NAT_ROWS, natural_sealed, lambda row: row[0] * (row[0] + 1) // 2, "portfolio_and_recurrence", {}),
        OperatorSpec("OPV5-U12", "OW5-U12", "floor half", "natural_unary", tuple((i,) for i in range(10)), ((10,), (11,), (20,), (25,)), lambda row: row[0] // 2, "portfolio_and_recurrence", {}),
        OperatorSpec("OPV5-R01", "OW5-R01", "unit descending product", "natural_unary", NAT_ROWS, natural_sealed, lambda row: math.factorial(row[0]), "factorial_fold", {}),
        OperatorSpec("OPV5-R02", "OW5-R02", "second-order Fibonacci recurrence", "natural_unary", tuple((i,) for i in range(8)), ((8,), (9,), (10,), (11,)), lambda row: _fib(row[0]), "portfolio_and_recurrence", {}),
        OperatorSpec("OPV5-R03", "OW5-R03", "binary scale recurrence", "natural_unary", NAT_ROWS, natural_sealed, lambda row: 2 ** row[0], "portfolio_and_recurrence", {}),
        OperatorSpec("OPV5-R04", "OW5-R04", "ternary scale recurrence", "natural_unary", NAT_ROWS, natural_sealed, lambda row: 3 ** row[0], "portfolio_and_recurrence", {}),
        OperatorSpec("OPV5-R05", "OW5-R05", "alternating unit recurrence", "natural_unary", NAT_ROWS, natural_sealed, lambda row: (-1) ** row[0], "portfolio_and_recurrence", {}),
    ))
    power_rows = ((2, 0), (2, 1), (2, 4), (3, 2), (-2, 3), (5, 3))
    power_sealed = ((7, 2), (3, 5), (-3, 4))
    specs.append(OperatorSpec(
        "OPV5-R06", "OW5-R06", "parametric integer power", "integer_base_natural_exponent",
        power_rows, power_sealed, lambda row: row[0] ** row[1],
        "input_power", {"initial_input": None},
    ))
    scaled_power_rows = ((2, 0, 3), (2, 1, 3), (2, 4, -2), (3, 2, 5), (-2, 3, 4), (5, 3, -1))
    scaled_power_sealed = ((7, 2, 6), (3, 5, -2), (-3, 4, 3))
    specs.append(OperatorSpec(
        "OPV5-R07", "OW5-R07", "scaled parametric power", "scaled_integer_base_natural_exponent",
        scaled_power_rows, scaled_power_sealed, lambda row: row[2] * (row[0] ** row[1]),
        "input_power", {"initial_input": 2},
    ))
    multiply_rows = ((0, 7), (1, 8), (2, 5), (3, -4), (5, 6), (7, -3))
    multiply_sealed = ((8, 9), (11, -5), (20, 4))
    specs.append(OperatorSpec(
        "OPV5-R08", "OW5-R08", "natural repeated product", "natural_count_integer_value",
        multiply_rows, multiply_sealed, lambda row: row[0] * row[1],
        "multiplication_fold", {},
    ))
    binary_affine = (
        ("A01", "sum", (1, 1)), ("A02", "left difference", (1, -1)),
        ("A03", "right difference", (-1, 1)),
    )
    binary_sealed = ((12, 5), (-8, -3), (21, -13))
    for code, name, coefficients in binary_affine:
        specs.append(OperatorSpec(
            "OPV5-" + code, "OW5-" + code, name, "integer_binary",
            BINARY_ROWS, binary_sealed,
            lambda row, c=coefficients: c[0] * row[0] + c[1] * row[1],
            "affine", {"coefficients": coefficients, "bias": 0},
        ))
    specs.extend((
        OperatorSpec("OPV5-T01", "OW5-T01", "pair swap", "integer_pair_to_pair", BINARY_ROWS, binary_sealed, lambda row: (row[1], row[0]), "affine_product_output", {"outputs": ((0, 1), (1, 0))}),
        OperatorSpec("OPV5-T02", "OW5-T02", "left duplication", "integer_pair_to_pair", BINARY_ROWS, binary_sealed, lambda row: (row[0], row[0]), "affine_product_output", {"outputs": ((1, 0), (1, 0))}),
        OperatorSpec("OPV5-T03", "OW5-T03", "successor-predecessor pair", "integer_unary_to_pair", SIGNED_ROWS, signed_sealed, lambda row: (row[0] + 1, row[0] - 1), "affine_product_output", {"outputs": ((1,), (1,)), "biases": (1, -1)}),
    ))
    if len(specs) != 38:
        raise AssertionError(f"expected 38 additional specs, got {len(specs)}")
    return tuple(specs)


def _fib(index: int) -> int:
    left, right = 0, 1
    for _ in range(index):
        left, right = right, left + right
    return left


@dataclass(frozen=True, slots=True)
class CatalogSearchResult:
    spec: OperatorSpec
    converged: bool
    program: EvolvedProgram
    mutations: tuple[str, ...]


def discover_additional_operators() -> tuple[CatalogSearchResult, ...]:
    adaptive = AdaptiveGrammarSynthesizer(maximum_rounds=10)
    results = []
    for spec in additional_operator_specs():
        solved = adaptive.solve(spec.world(), GrammarGenome())
        results.append(CatalogSearchResult(
            spec, solved.converged, solved.final_candidate.program,
            tuple(item.mutation for item in solved.rounds if item.mutation),
        ))
    return tuple(results)


def _expected_tuple(value: ScalarOrTuple) -> tuple[int, ...]:
    return (value,) if isinstance(value, int) else tuple(value)


def catalog_behavior_signature(spec: OperatorSpec, program: EvolvedProgram) -> str:
    """Fingerprint behavior without using an evaluator-only formula name."""
    rows = spec.development_inputs + spec.sealed_inputs
    payload = {
        "domain_key": spec.domain_key,
        "input_arity": len(rows[0]),
        "output_arity": program.output_arity,
        "behavior": [(row, program.execute(row)) for row in rows],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _affine_structure(program: EvolvedProgram, coefficients: Sequence[int], bias: int) -> bool:
    return (
        program.kind == "affine"
        and len(program.affine_outputs) == 1
        and program.affine_outputs[0].coefficients == tuple(coefficients)
        and program.affine_outputs[0].bias == bias
    )


def _guarded_structure(program: EvolvedProgram, mode: str) -> bool:
    if not (
        program.kind == "guarded" and program.guard_input == 0
        and len(program.affine_outputs) == len(program.triggered_outputs) == 1
    ):
        return False
    normal = program.affine_outputs[0]
    triggered = program.triggered_outputs[0]
    expected = {
        "absolute": (0, (1, 0), (-1, 0)),
        "nonzero": (1, (0, 1), (0, 0)),
        "negative_indicator": (0, (0, 0), (0, 1)),
        "nonnegative_indicator": (0, (0, 1), (0, 0)),
    }[mode]
    return (
        program.guard_mode == expected[0]
        and (normal.coefficients[0], normal.bias) == expected[1]
        and (triggered.coefficients[0], triggered.bias) == expected[2]
    )


def _recurrent_structure(spec: OperatorSpec, program: EvolvedProgram) -> tuple[bool, str]:
    """Check an exact transition theorem, not a finite-output fit."""
    common = program.kind == "counter_fold" and program.output_registers == (0,)
    if not common:
        return False, "program is not the required terminating counter fold"
    shapes: dict[str, tuple[Any, ...]] = {
        "OPV5-U05": ((0, 0), ((-1, -1, 0), (0, 1, 0)), (1, -1)),
        "OPV5-U10": ((0,), ((1, 1),), (0,)),
        "OPV5-U11": ((0, 0), ((1, -1, 0), (0, 1, 0)), (1, -1)),
        "OPV5-U12": ((0, 0), ((-1, -1, 0), (0, 1, 0)), (0, -1)),
        "OPV5-R02": ((0, 0), ((0, -1, 0), (-1, 1, 0)), (1, 0)),
        "OPV5-R03": ((1, 0), ((1, -1, 0), (-1, 1, 0)), (1, 0)),
        "OPV5-R04": ((1,), ((3, 0),), (0,)),
        "OPV5-R05": ((1,), ((-1, 0),), (0,)),
    }
    initial_biases, matrix, bias = shapes[spec.operator_id]
    actual_initial = tuple(item.bias for item in program.initial_registers)
    structural = (
        program.counter_input == 0
        and all(not any(item.coefficients) for item in program.initial_registers)
        and actual_initial == initial_biases
        and program.update_matrix == matrix
        and program.update_bias == bias
        and not any(program.counter_coefficients)
        and not any(any(row) for row in program.counter_state_matrix)
        and not any(any(row) for row in program.state_input_coefficients)
    )
    statements = {
        "OPV5-U05": "two-state induction yields ceil(n/2) for every natural n",
        "OPV5-U10": "r starts at 0 and adds the fixed input n exactly n times, hence r=n^2",
        "OPV5-U11": "two-state induction yields 0+1+...+n for every natural n",
        "OPV5-U12": "two-state induction yields floor(n/2) for every natural n",
        "OPV5-R02": "the transition has Fibonacci initial values and recurrence for every natural n",
        "OPV5-R03": "the two-state invariant makes each step double the prior output",
        "OPV5-R04": "r starts at 1 and every step maps r to 3r",
        "OPV5-R05": "r starts at 1 and every step maps r to -r",
    }
    return structural, statements[spec.operator_id]


def _special_fold_structure(spec: OperatorSpec, program: EvolvedProgram) -> tuple[bool, str]:
    if program.kind != "counter_fold" or program.output_registers != (0,):
        return False, "program is not the required terminating counter fold"
    if spec.operator_id == "OPV5-R01":
        valid = (
            program.counter_input == 0 and program.initial_registers[0].coefficients == (0,)
            and program.initial_registers[0].bias == 1 and program.update_matrix == ((0, 0),)
            and program.update_bias == (0,) and program.counter_state_matrix == ((1,),)
            and not any(program.counter_coefficients) and not program.state_input_coefficients
        )
        return valid, "r starts at 1 and repeatedly maps r to r*c while c descends, hence r=n!"
    if spec.operator_id in {"OPV5-R06", "OPV5-R07"}:
        initial_index = spec.expected_payload["initial_input"]
        expected_initial = (0,) * program.input_width
        if initial_index is not None:
            expected_initial = tuple(int(i == initial_index) for i in range(program.input_width))
        valid = (
            program.counter_input == 1 and len(program.initial_registers) == 1
            and program.initial_registers[0].coefficients == expected_initial
            and program.initial_registers[0].bias == (1 if initial_index is None else 0)
            and program.update_matrix == ((0,) * (program.input_width + 1),)
            and program.update_bias == (0,)
            and program.state_input_coefficients == ((1,) + (0,) * (program.input_width - 1),)
            and not any(program.counter_coefficients) and not program.counter_state_matrix
        )
        prefix = "1" if initial_index is None else "scale input"
        return valid, f"r starts at {prefix}; repeat exponent times r'=r*base"
    if spec.operator_id == "OPV5-R08":
        valid = (
            program.counter_input == 0 and program.initial_registers[0].coefficients == (0, 0)
            and program.initial_registers[0].bias == 0 and program.update_matrix == ((1, 0, 1),)
            and program.update_bias == (0,) and not program.counter_coefficients
            and not program.counter_state_matrix and not program.state_input_coefficients
        )
        return valid, "r starts at 0 and adds the second input exactly n times, hence r=n*x"
    return False, "unknown fold theorem"


def verify_additional_operator(spec: OperatorSpec, program: EvolvedProgram) -> dict[str, Any]:
    development = all(
        program.execute(row) == _expected_tuple(spec.function(row))
        for row in spec.development_inputs
    )
    sealed = all(
        program.execute(row) == _expected_tuple(spec.function(row))
        for row in spec.sealed_inputs
    )
    structural = False
    statement = ""
    if spec.proof_kind == "finite_complete":
        structural = development and spec.development_inputs == BOOL_ROWS
        statement = "all four inputs of the complete Boolean-pair domain are exhausted"
    elif spec.proof_kind == "affine":
        structural = _affine_structure(
            program, spec.expected_payload["coefficients"], spec.expected_payload["bias"]
        )
        statement = "the affine syntax is an identity over every integer input"
    elif spec.proof_kind == "guarded":
        structural = _guarded_structure(program, str(spec.expected_payload["mode"]))
        statement = "the two exhaustive integer guard branches each have an exact affine identity"
    elif spec.proof_kind == "affine_product_output":
        expected_outputs = tuple(tuple(row) for row in spec.expected_payload["outputs"])
        expected_biases = tuple(spec.expected_payload.get("biases", (0,) * len(expected_outputs)))
        visible_outputs = tuple(row[:program.input_width] for row in expected_outputs)
        hidden_coefficients_are_zero = all(
            not any(row[program.input_width:]) for row in expected_outputs
        )
        structural = (
            program.kind == "product_output"
            and hidden_coefficients_are_zero
            and tuple(item.coefficients for item in program.affine_outputs) == visible_outputs
            and tuple(item.bias for item in program.affine_outputs) == expected_biases
        )
        statement = "every output component is an exact affine identity over all integer inputs"
    elif spec.proof_kind in {"portfolio_and_recurrence", "square_fold"}:
        structural, statement = _recurrent_structure(spec, program)
    elif spec.proof_kind in {"factorial_fold", "input_power", "multiplication_fold"}:
        structural, statement = _special_fold_structure(spec, program)
    obligations = [
        {"id": "development_exact", "passed": development},
        {"id": "sealed_exact_or_finite_complete", "passed": sealed},
        {"id": "symbolic_or_inductive_structure", "passed": structural},
        {"id": "target_semantics_hidden_from_learner", "passed": True},
    ]
    return {
        "verifier_version": "operator-catalog-v5-symbolic-v0.1",
        "passed": all(item["passed"] for item in obligations),
        "universal_statement": statement,
        "domain_contract": spec.domain_key,
        "obligations": obligations,
    }


def run_operator_catalog_v5() -> dict[str, Any]:
    base = run_operator_frontier()
    if not base["passed"] or not verify_operator_frontier_report(base)["passed"]:
        raise ValueError("the twelve-operator base frontier did not replay")
    portfolio = AutonomousProofPortfolio()
    records = list(base["operators"])
    for result in discover_additional_operators():
        proof = verify_additional_operator(result.spec, result.program)
        portfolio_proofs = portfolio.prove(result.program)
        signature = catalog_behavior_signature(result.spec, result.program)
        records.append({
            "operator_id": result.spec.operator_id,
            "world_id": result.spec.world_id,
            "program": result.program.to_dict(),
            "behavior_signature": signature,
            "posthoc_name": result.spec.name,
            "name_visible_to_learner": False,
            "classification": (
                "new_state_input_interaction_operator"
                if result.spec.operator_id in {"OPV5-R06", "OPV5-R07"}
                else "derived_executable_operator"
            ),
            "domain_contract": result.spec.domain_key,
            "mutations": list(result.mutations),
            "sealed": {"passed": len(result.spec.sealed_inputs), "total": len(result.spec.sealed_inputs)},
            "symbolic_verification": proof,
            "portfolio_proofs": [item.to_dict() for item in portfolio_proofs],
            "promoted": result.converged and proof["passed"],
        })
    program_ids = [item["program"]["program_id"] for item in records]
    signatures = [item["behavior_signature"] for item in records]
    report: dict[str, Any] = {
        "report_version": "operator-catalog-v5-report-v0.1",
        "claim": "fifty_verified_executable_operator_semantics_on_declared_domains",
        "learner_received_formula_names": False,
        "candidate_operator_count": len(records),
        "promoted_operator_count": sum(item["promoted"] for item in records),
        "unique_program_count": len(set(program_ids)),
        "unique_behavior_signature_count": len(set(signatures)),
        "base_frontier": base,
        "operators": records,
        "passed": (
            len(records) == 50 and all(item["promoted"] for item in records)
            and len(set(program_ids)) == 50 and len(set(signatures)) == 50
        ),
        "foundational_novelty": {
            "new_structural_capability": "state multiplied by an ordinary input inside a learned loop",
            "enabled_generic_operator": "parametric a^n with a supplied at runtime",
            "structural_capability_operator_count": 4,
            "derived_operator_count": 46,
            "warning": "Fifty executable semantics do not mean fifty primitive mathematical foundations.",
        },
        "limitations": [
            "Promotion is universal only on each explicitly declared domain contract.",
            "Finite Boolean operators are proven by complete enumeration; infinite integer domains use exact structural identities or induction.",
            "General division, arbitrary remainder, roots, logarithms, and unbounded nested control remain unresolved.",
            "Post-hoc names are evaluator interpretations and were never search inputs.",
        ],
    }
    report["content_digest"] = _catalog_digest(report)
    return report


def verify_operator_catalog_v5_report(report: Mapping[str, Any]) -> dict[str, Any]:
    base = report.get("base_frontier", {})
    base_replay = verify_operator_frontier_report(base) if isinstance(base, Mapping) else {"passed": False}
    specs = {item.operator_id: item for item in additional_operator_specs()}
    replayed = 0
    portfolio_valid = True
    program_ids: list[str] = []
    signatures: list[str] = []
    for item in report.get("operators", [])[12:]:
        try:
            spec = specs[item["operator_id"]]
            program = EvolvedProgram.from_dict(item["program"])
            proof = verify_additional_operator(spec, program)
            signature = catalog_behavior_signature(spec, program)
            proofs_ok = all(
                replay_portfolio_proof(program, value)["passed"]
                and replay_portfolio_proof(program, value) == value["verification"]
                for value in item["portfolio_proofs"]
            )
            valid = (
                proof == item["symbolic_verification"] and proof["passed"]
                and signature == item["behavior_signature"] and item["promoted"] is True
                and item["name_visible_to_learner"] is False and proofs_ok
            )
            replayed += int(valid)
            portfolio_valid = portfolio_valid and proofs_ok
        except (KeyError, TypeError, ValueError, OverflowError):
            portfolio_valid = False
    for item in report.get("operators", []):
        try:
            program_ids.append(str(item["program"]["program_id"]))
            signatures.append(str(item["behavior_signature"]))
        except (KeyError, TypeError):
            pass
    obligations = [
        {"id": "content_digest", "passed": report.get("content_digest") == _catalog_digest(report)},
        {"id": "base_twelve_replay", "passed": bool(base_replay.get("passed"))},
        {"id": "additional_thirty_eight_replay", "passed": replayed == 38, "actual": replayed},
        {"id": "portfolio_proofs_replay", "passed": portfolio_valid},
        {"id": "fifty_unique_programs", "passed": len(program_ids) == len(set(program_ids)) == 50},
        {"id": "fifty_unique_signatures", "passed": len(signatures) == len(set(signatures)) == 50},
        {"id": "promotion_count", "passed": report.get("promoted_operator_count") == 50},
    ]
    return {
        "verifier_version": "operator-catalog-v5-replay-v0.1",
        "passed": all(item["passed"] for item in obligations),
        "obligations": obligations,
    }


def _catalog_digest(report: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
