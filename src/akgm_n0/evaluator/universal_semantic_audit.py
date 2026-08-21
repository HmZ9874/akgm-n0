"""Fixed-point universal-domain audit for evolved additive semantics."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from akgm_n0.learner.metamachine_gen2 import (
    OP_ADD_CELL,
    OP_ADD_IMMEDIATE,
    OP_ADD_INPUT,
    OP_LOAD_CELL,
    OP_LOAD_INPUT,
    OP_SET,
    OP_STORE_CELL,
    OP_SUB_CELL,
    OP_SUB_IMMEDIATE,
    OP_SUB_INPUT,
)
from akgm_n0.learner.operator_evolution import EvolvedMicroOperator

from .evolved_operator_proof import verify_evolved_operator


@dataclass(frozen=True, slots=True)
class UniversalSemanticAudit:
    operator_id: str
    passed: bool
    universal_domain: str
    natural_number_safe: bool
    canonical_vector: tuple[int, ...]
    obligations: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "auditor_version": "free-abelian-normal-form-auditor-v0.1",
            "operator_id": self.operator_id,
            "passed": self.passed,
            "universal_domain": self.universal_domain,
            "natural_number_safe": self.natural_number_safe,
            "canonical_vector": list(self.canonical_vector),
            "obligations": [dict(item) for item in self.obligations],
        }


class UniversalSemanticAuditor:
    """Prove equality for every valuation in every commutative additive group."""

    DOMAIN = "all commutative additive groups (therefore Z, Q, R under exact addition, and Z/nZ)"

    def audit(self, operator: EvolvedMicroOperator) -> UniversalSemanticAudit:
        instruction_vector = _instruction_vector(operator)
        ast_vector = _ast_vector(operator.effect_ast, operator.operand_tokens)
        executable = verify_evolved_operator(operator)
        has_subtraction = any(
            item.opcode in (OP_SUB_CELL, OP_SUB_INPUT, OP_SUB_IMMEDIATE)
            for item in operator.normalized_instructions
        )
        natural_safe = (
            not has_subtraction
            and all(value >= 0 for value in operator.coefficient_vector)
        )
        obligations = (
            {
                "obligation_id": "declared_total_algebraic_domain",
                "passed": True,
                "evidence": self.DOMAIN,
            },
            {
                "obligation_id": "instruction_free_group_normal_form",
                "passed": instruction_vector == operator.coefficient_vector,
                "evidence": list(instruction_vector),
            },
            {
                "obligation_id": "compiled_effect_free_group_normal_form",
                "passed": ast_vector == operator.coefficient_vector,
                "evidence": list(ast_vector),
            },
            {
                "obligation_id": "universal_equality_by_unique_normal_form",
                "passed": instruction_vector == ast_vector == operator.coefficient_vector,
                "evidence": "equal coefficient vectors are identical in the free abelian group, hence under every group homomorphism",
            },
            {
                "obligation_id": "independent_executable_proof_still_passes",
                "passed": executable["passed"],
                "evidence": executable["verifier_version"],
            },
        )
        return UniversalSemanticAudit(
            operator.operator_id,
            all(item["passed"] for item in obligations),
            self.DOMAIN,
            natural_safe,
            tuple(operator.coefficient_vector),
            obligations,
        )


class UniversalSemanticAuditLoop:
    """Remove failures until the active semantic set reaches a proven fixed point."""

    def __init__(self, *, maximum_rounds: int = 10, stable_rounds_required: int = 2):
        self.maximum_rounds = maximum_rounds
        self.stable_rounds_required = stable_rounds_required
        self.auditor = UniversalSemanticAuditor()

    def run(self, operators: Sequence[EvolvedMicroOperator]) -> dict[str, Any]:
        active = list(operators)
        rejected: list[dict[str, Any]] = []
        rounds = []
        previous_digest: str | None = None
        stable_round_count = 0
        final_audits: list[UniversalSemanticAudit] = []
        for round_index in range(1, self.maximum_rounds + 1):
            audits = [self.auditor.audit(operator) for operator in active]
            survivors = [
                operator
                for operator, audit in zip(active, audits, strict=True)
                if audit.passed
            ]
            removed = [
                {"operator": operator.to_dict(), "audit": audit.to_dict()}
                for operator, audit in zip(active, audits, strict=True)
                if not audit.passed
            ]
            rejected.extend(removed)
            digest = _active_digest(survivors)
            if not removed and digest == previous_digest:
                stable_round_count += 1
            elif not removed:
                stable_round_count = 1
            else:
                stable_round_count = 0
            rounds.append(
                {
                    "round": round_index,
                    "input_count": len(active),
                    "removed_count": len(removed),
                    "survivor_count": len(survivors),
                    "active_digest": digest,
                    "stable_round_count": stable_round_count,
                }
            )
            active = survivors
            final_audits = [self.auditor.audit(operator) for operator in active]
            previous_digest = digest
            if stable_round_count >= self.stable_rounds_required:
                return {
                    "loop_version": "universal-semantic-fixed-point-loop-v0.1",
                    "converged": True,
                    "rounds": rounds,
                    "active_operators": [item.to_dict() for item in active],
                    "active_audits": [item.to_dict() for item in final_audits],
                    "rejected": rejected,
                    "active_digest": digest,
                }
        return {
            "loop_version": "universal-semantic-fixed-point-loop-v0.1",
            "converged": False,
            "rounds": rounds,
            "active_operators": [item.to_dict() for item in active],
            "active_audits": [item.to_dict() for item in final_audits],
            "rejected": rejected,
            "active_digest": _active_digest(active),
        }


def _instruction_vector(operator: EvolvedMicroOperator) -> tuple[int, ...]:
    coefficients = {token: 0 for token in operator.operand_tokens}
    started = False
    stored = False
    for index, instruction in enumerate(operator.normalized_instructions):
        opcode, token = instruction.opcode, instruction.operand_token
        if opcode in (OP_LOAD_CELL, OP_LOAD_INPUT, OP_SET):
            if index != 0 or token not in coefficients:
                return ()
            coefficients[token] = 1
            started = True
        elif opcode in (OP_ADD_CELL, OP_ADD_INPUT, OP_ADD_IMMEDIATE):
            if not started or token not in coefficients:
                return ()
            coefficients[token] += 1
        elif opcode in (OP_SUB_CELL, OP_SUB_INPUT, OP_SUB_IMMEDIATE):
            if not started or token not in coefficients:
                return ()
            coefficients[token] -= 1
        elif opcode == OP_STORE_CELL:
            if index != len(operator.normalized_instructions) - 1 or token != operator.target_token:
                return ()
            stored = True
        else:
            return ()
    if not stored:
        return ()
    return tuple(coefficients[token] for token in operator.operand_tokens)


def _ast_vector(node: Mapping[str, Any], tokens: Sequence[str]) -> tuple[int, ...]:
    coefficients = {token: 0 for token in tokens}

    def walk(current: Mapping[str, Any], sign: int) -> None:
        if current.get("op") == "token":
            token = str(current.get("token"))
            if token not in coefficients:
                raise ValueError("unknown token")
            coefficients[token] += sign
            return
        if current.get("op") not in ("add", "sub"):
            raise ValueError("unknown AST operation")
        left, right = current["args"]
        walk(left, sign)
        walk(right, sign if current["op"] == "add" else -sign)

    try:
        walk(node, 1)
    except (KeyError, TypeError, ValueError):
        return ()
    return tuple(coefficients[token] for token in tokens)


def _active_digest(operators: Sequence[EvolvedMicroOperator]) -> str:
    return hashlib.sha256(
        json.dumps(
            [item.operator_id for item in operators],
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()

