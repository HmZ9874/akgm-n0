"""Evaluator-owned anonymous worlds for discovering executable operators."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from akgm_n0.learner.meta_autonomy_v3 import (
    AdaptiveGrammarSynthesizer,
    AnonymousWorld,
    EvolvedProgram,
    GrammarGenome,
)
from akgm_n0.learner.meta_autonomy_v4 import AutonomousProofPortfolio
from akgm_n0.learner.meta_autonomy_v4 import replay_portfolio_proof


@dataclass(frozen=True, slots=True)
class OperatorWorld:
    world: AnonymousWorld
    sealed_inputs: tuple[tuple[int, ...], ...]
    sealed_outputs: tuple[tuple[int, ...], ...]
    domain_contract: str
    posthoc_name: str
    classification: str


def _outputs(values: Sequence[int | Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    return tuple((value,) if isinstance(value, int) else tuple(value) for value in values)


def _world(
    world_id: str,
    development_inputs: Sequence[Sequence[int]],
    development_outputs: Sequence[int | Sequence[int]],
    sealed_inputs: Sequence[Sequence[int]],
    sealed_outputs: Sequence[int | Sequence[int]],
    domain: str,
    name: str,
    classification: str = "derived_executable_operator",
) -> OperatorWorld:
    return OperatorWorld(
        AnonymousWorld.create(world_id, development_inputs, development_outputs),
        tuple(tuple(row) for row in sealed_inputs), _outputs(sealed_outputs),
        domain, name, classification,
    )


def operator_worlds() -> tuple[OperatorWorld, ...]:
    signed = ((-6,), (-3,), (-1,), (0,), (1,), (4,), (7,))
    boolean = ((0, 0), (0, 1), (1, 0), (1, 1))
    return (
        _world("OW-11a", signed, (0, 0, 0, 0, 1, 4, 7), ((-12,), (2,), (11,)), (0, 2, 11), "all integers", "positive projection"),
        _world("OW-22b", signed, (-6, -3, -1, 0, 0, 0, 0), ((-12,), (2,), (11,)), (-12, 0, 0), "all integers", "negative projection"),
        _world("OW-33c", ((-4,), (-1,), (0,), (1,), (5,)), (0, 0, 1, 0, 0), ((-99,), (0,), (42,)), (0, 1, 0), "all integers", "zero indicator"),
        _world("OW-44d", tuple((i,) for i in range(8)), tuple(i % 2 for i in range(8)), ((8,), (9,), (16,), (23,)), (0, 1, 0, 1), "natural numbers", "parity residue"),
        _world("OW-55e", boolean, (0, 1, 1, 1), (), (), "complete Boolean pair domain", "Boolean disjunction"),
        _world("OW-66f", boolean, (0, 1, 1, 0), (), (), "complete Boolean pair domain", "Boolean exclusive disjunction"),
        _world("OW-77a", boolean, (1, 1, 1, 0), (), (), "complete Boolean pair domain", "Boolean NAND"),
        _world("OW-88b", boolean, (1, 1, 0, 1), (), (), "complete Boolean pair domain", "Boolean implication"),
        _world(
            "OW-99c",
            ((2, 0, 7), (2, 1, 7), (2, 3, 7), (-3, 2, 4), (5, 4, -2), (8, 2, 3)),
            (2, 9, 23, 5, -3, 14),
            ((11, 5, 6), (-8, 7, 3), (4, 9, -5)),
            (41, 13, -41), "integer start/step and natural count", "iterated affine step",
        ),
        _world(
            "OW-aad", ((-3, 2), (0, 4), (1, -5), (6, 7), (9, -2)),
            ((-1, -5), (4, -4), (-4, 6), (13, -1), (7, 11)),
            ((12, 5), (-8, -3), (21, -13)),
            ((17, 7), (-11, -5), (8, 34)), "all integer pairs", "paired sum and difference",
        ),
        _world(
            "OW-bbe", ((0, 3), (1, 4), (2, -2), (3, 5), (4, 2), (5, -1)),
            (3, 4, -4, 30, 48, -120),
            ((6, 2), (7, -3), (8, 1)), (1440, -15120, 40320),
            "natural count and integer scale", "scaled descending product",
            "new_counter_interaction_operator",
        ),
        _world(
            "OW-ccf", tuple((i,) for i in range(7)), (1, -2, 4, -8, 16, -32, 64),
            ((7,), (8,), (9,), (10,)), (-128, 256, -512, 1024),
            "natural numbers", "signed scale recurrence",
            "new_scaling_operator",
        ),
    )


@dataclass(frozen=True, slots=True)
class OperatorDiscovery:
    world_id: str
    converged: bool
    program: EvolvedProgram
    mutations: tuple[str, ...]
    sealed_passed: int
    sealed_total: int
    proof_domains: tuple[str, ...]


def explore_operator_worlds() -> tuple[OperatorDiscovery, ...]:
    adaptive = AdaptiveGrammarSynthesizer(maximum_rounds=10)
    portfolio = AutonomousProofPortfolio()
    discoveries = []
    for case in operator_worlds():
        result = adaptive.solve(case.world, GrammarGenome())
        program = result.final_candidate.program
        sealed = [
            program.execute(row) == expected
            for row, expected in zip(case.sealed_inputs, case.sealed_outputs, strict=True)
        ]
        proofs = portfolio.prove(program)
        discoveries.append(OperatorDiscovery(
            case.world.world_id, result.converged, program,
            tuple(item.mutation for item in result.rounds if item.mutation),
            sum(sealed), len(sealed),
            tuple(sorted({proof.proof_domain for proof in proofs})),
        ))
    return tuple(discoveries)


def behavior_signature(case: OperatorWorld, program: EvolvedProgram) -> str:
    rows = case.world.input_rows + case.sealed_inputs
    payload = {
        "input_width": case.world.input_width,
        "output_width": case.world.output_width,
        "behavior": [(row, program.execute(row)) for row in rows],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def verify_operator_program(case: OperatorWorld, program: EvolvedProgram) -> dict[str, Any]:
    development = all(
        program.execute(row) == expected
        for row, expected in zip(case.world.input_rows, case.world.output_rows, strict=True)
    )
    sealed = all(
        program.execute(row) == expected
        for row, expected in zip(case.sealed_inputs, case.sealed_outputs, strict=True)
    )
    structural = False
    statement = ""
    if case.world.world_id == "OW-11a":
        structural = (
            program.kind == "guarded" and program.guard_input == 0 and program.guard_mode == 0
            and program.affine_outputs[0].coefficients == (1,) and program.affine_outputs[0].bias == 0
            and program.triggered_outputs[0].coefficients == (0,) and program.triggered_outputs[0].bias == 0
        )
        statement = "x<0 maps to 0; otherwise x"
    elif case.world.world_id == "OW-22b":
        structural = (
            program.kind == "guarded" and program.guard_input == 0 and program.guard_mode == 0
            and program.affine_outputs[0].coefficients == (0,) and program.affine_outputs[0].bias == 0
            and program.triggered_outputs[0].coefficients == (1,) and program.triggered_outputs[0].bias == 0
        )
        statement = "x<0 maps to x; otherwise 0"
    elif case.world.world_id == "OW-33c":
        structural = (
            program.kind == "guarded" and program.guard_input == 0 and program.guard_mode == 1
            and program.affine_outputs[0].coefficients == (0,) and program.affine_outputs[0].bias == 0
            and program.triggered_outputs[0].coefficients == (0,) and program.triggered_outputs[0].bias == 1
        )
        statement = "x=0 maps to 1; otherwise 0"
    elif case.world.world_id == "OW-44d":
        structural = (
            program.kind == "counter_fold" and program.counter_input == 0
            and program.initial_registers[0].coefficients == (0,) and program.initial_registers[0].bias == 0
            and program.update_matrix == ((-1, 0),) and program.update_bias == (1,)
        )
        statement = "r0=0; r'=1-r, so r_n is the residue of n modulo 2"
    elif case.world.world_id in {"OW-55e", "OW-66f", "OW-77a", "OW-88b"}:
        structural = development
        statement = "all four elements of the declared finite Boolean-pair domain were exhausted"
    elif case.world.world_id == "OW-99c":
        structural = (
            program.kind == "counter_fold" and program.counter_input == 1
            and program.initial_registers[0].coefficients == (1, 0, 0)
            and program.initial_registers[0].bias == 0
            and program.update_matrix == ((1, 0, 0, 1),) and program.update_bias == (0,)
        )
        statement = "r0=a; repeat n times r'=r+d, hence r=a+n*d"
    elif case.world.world_id == "OW-aad":
        structural = (
            program.kind == "product_output" and len(program.affine_outputs) == 2
            and program.affine_outputs[0].coefficients == (1, 1)
            and program.affine_outputs[0].bias == 0
            and program.affine_outputs[1].coefficients == (1, -1)
            and program.affine_outputs[1].bias == 0
        )
        statement = "the two outputs are universally a+b and a-b"
    elif case.world.world_id == "OW-bbe":
        structural = (
            program.kind == "counter_fold" and program.counter_input == 0
            and program.initial_registers[0].coefficients == (0, 1)
            and program.initial_registers[0].bias == 0
            and program.update_matrix == ((0, 0, 0),)
            and program.counter_state_matrix == ((1,),)
        )
        statement = "r0=b; r'=r*c while c descends, hence r=b*n!"
    elif case.world.world_id == "OW-ccf":
        structural = (
            program.kind == "counter_fold" and program.counter_input == 0
            and program.state_width == 2
            and program.initial_registers[0].bias == 1
            and program.initial_registers[1].bias == 1
            and program.update_matrix[0][:2] == (-1, -1)
            and program.update_matrix[1][:2] == (-1, -1)
            and program.update_bias == (0, 0)
        )
        statement = "equal states remain equal and each step maps r to -2r"
    obligations = [
        {"id": "development_exact", "passed": development},
        {"id": "sealed_exact_or_finite_domain_complete", "passed": sealed},
        {"id": "symbolic_structure", "passed": structural},
        {"id": "target_name_was_evaluator_only", "passed": True},
    ]
    return {
        "verifier_version": "operator-frontier-v4-symbolic-v0.1",
        "passed": all(item["passed"] for item in obligations),
        "universal_statement": statement,
        "domain_contract": case.domain_contract,
        "obligations": obligations,
    }


def run_operator_frontier() -> dict[str, Any]:
    cases = operator_worlds()
    discoveries = explore_operator_worlds()
    case_map = {case.world.world_id: case for case in cases}
    portfolio = AutonomousProofPortfolio()
    records = []
    signatures = []
    for discovery in discoveries:
        case = case_map[discovery.world_id]
        proof = verify_operator_program(case, discovery.program)
        portfolio_proofs = portfolio.prove(discovery.program)
        signature = behavior_signature(case, discovery.program)
        signatures.append((case.world.input_width, case.world.output_width, signature))
        records.append({
            "operator_id": "OPV4-" + discovery.world_id[3:],
            "world_id": discovery.world_id,
            "program": discovery.program.to_dict(),
            "behavior_signature": signature,
            "posthoc_name": case.posthoc_name,
            "name_visible_to_learner": False,
            "classification": case.classification,
            "domain_contract": case.domain_contract,
            "mutations": list(discovery.mutations),
            "sealed": {"passed": discovery.sealed_passed, "total": discovery.sealed_total},
            "symbolic_verification": proof,
            "portfolio_proofs": [item.to_dict() for item in portfolio_proofs],
            "promoted": discovery.converged and proof["passed"],
        })
    comparable = [(width_in, width_out, signature) for width_in, width_out, signature in signatures]
    distinct = len(comparable) == len(set(comparable))
    report: dict[str, Any] = {
        "report_version": "operator-frontier-v4-report-v0.1",
        "claim": "verified_executable_operators_on_declared_domains",
        "candidate_world_count": len(cases),
        "promoted_operator_count": sum(item["promoted"] for item in records),
        "all_behavior_signatures_distinct": distinct,
        "operators": records,
        "passed": all(item["promoted"] for item in records) and distinct,
        "limitations": [
            "These are executable operator semantics; most are compositions of already learned control and state mechanisms, not twelve new mathematical foundations.",
            "Boolean operators are universally checked by exhausting their declared finite domain.",
            "Integer operators require symbolic structural proof plus sealed tests; sealed tests alone never authorize promotion.",
            "General division, arbitrary remainder, roots, and variable-base exponentiation remain outside this operator batch.",
        ],
    }
    report["content_digest"] = _digest(report)
    return report


def verify_operator_frontier_report(report: Mapping[str, Any]) -> dict[str, Any]:
    cases = {case.world.world_id: case for case in operator_worlds()}
    replayed = 0
    signatures = []
    portfolio_valid = True
    for item in report.get("operators", []):
        try:
            case = cases[item["world_id"]]
            program = EvolvedProgram.from_dict(item["program"])
            proof = verify_operator_program(case, program)
            signature = behavior_signature(case, program)
            proofs_ok = all(
                replay_portfolio_proof(program, value)["passed"]
                and replay_portfolio_proof(program, value) == value["verification"]
                for value in item["portfolio_proofs"]
            )
            portfolio_valid = portfolio_valid and proofs_ok
            valid = (
                proof == item["symbolic_verification"] and proof["passed"]
                and signature == item["behavior_signature"]
                and item["promoted"] is True and item["name_visible_to_learner"] is False
            )
            replayed += valid
            signatures.append((case.world.input_width, case.world.output_width, signature))
        except (KeyError, TypeError, ValueError, OverflowError):
            portfolio_valid = False
    obligations = [
        {"id": "content_digest", "passed": report.get("content_digest") == _digest(report)},
        {"id": "all_twelve_replay", "passed": replayed == 12, "actual": replayed},
        {"id": "portfolio_proofs_replay", "passed": portfolio_valid},
        {"id": "distinct_behavior_signatures", "passed": len(signatures) == len(set(signatures)) == 12},
        {"id": "promotion_count", "passed": report.get("promoted_operator_count") == 12},
    ]
    return {
        "verifier_version": "operator-frontier-v4-replay-v0.1",
        "passed": all(item["passed"] for item in obligations),
        "obligations": obligations,
    }


def _digest(report: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in report.items() if key != "content_digest"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
