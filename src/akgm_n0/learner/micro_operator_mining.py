"""Mine parameterized straight-line operators from proven anonymous word code."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .metamachine_gen2 import (
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


START_OPS = frozenset({OP_LOAD_CELL, OP_LOAD_INPUT, OP_SET})
MIDDLE_OPS = frozenset(
    {OP_ADD_CELL, OP_SUB_CELL, OP_ADD_INPUT, OP_SUB_INPUT, OP_ADD_IMMEDIATE, OP_SUB_IMMEDIATE}
)
CELL_OPS = frozenset({OP_LOAD_CELL, OP_ADD_CELL, OP_SUB_CELL, OP_STORE_CELL})
INPUT_OPS = frozenset({OP_LOAD_INPUT, OP_ADD_INPUT, OP_SUB_INPUT})
IMMEDIATE_OPS = frozenset({OP_SET, OP_ADD_IMMEDIATE, OP_SUB_IMMEDIATE})


@dataclass(frozen=True, slots=True)
class NormalizedMicroInstruction:
    opcode: int
    operand_token: str

    def to_dict(self) -> dict[str, Any]:
        return {"opcode": self.opcode, "operand_token": self.operand_token}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "NormalizedMicroInstruction":
        return cls(int(value["opcode"]), str(value["operand_token"]))


@dataclass(frozen=True, slots=True)
class InducedMicroOperator:
    operator_id: str
    opcode: int
    normalized_instructions: tuple[NormalizedMicroInstruction, ...]
    target_token: str
    effect_ast: Mapping[str, Any]
    effect_signature: str
    source_record_ids: tuple[str, ...]
    supporting_occurrence_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "opcode": self.opcode,
            "normalized_instructions": [item.to_dict() for item in self.normalized_instructions],
            "target_token": self.target_token,
            "effect_ast": dict(self.effect_ast),
            "effect_signature": self.effect_signature,
            "source_record_ids": list(self.source_record_ids),
            "supporting_occurrence_count": self.supporting_occurrence_count,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InducedMicroOperator":
        return cls(
            str(value["operator_id"]), int(value["opcode"]),
            tuple(NormalizedMicroInstruction.from_dict(item) for item in value["normalized_instructions"]),
            str(value["target_token"]), dict(value["effect_ast"]),
            str(value["effect_signature"]), tuple(str(item) for item in value["source_record_ids"]),
            int(value["supporting_occurrence_count"]),
        )


class MicroOperatorMiner:
    """Discover the most-supported distinct effects; no formula labels are read."""

    def discover(
        self,
        sources: Sequence[tuple[str, Sequence[int]]],
        *,
        requested_count: int = 10,
        first_opcode: int = 18,
        minimum_occurrences: int = 2,
    ) -> tuple[InducedMicroOperator, ...]:
        groups: dict[str, dict[str, Any]] = {}
        for record_id, words in sources:
            instructions = tuple(zip(words[::2], words[1::2]))
            # Grow the candidate window instead of relaxing the evidence gate.
            # Longer blocks let the learner compress multi-step effects while
            # every accepted effect still needs repeated, multi-program support.
            for length in range(2, 9):
                for start in range(len(instructions) - length + 1):
                    normalized = _normalize_block(instructions[start : start + length])
                    if normalized is None:
                        continue
                    normalized_instructions, target, effect = normalized
                    signature = _effect_signature(target, effect)
                    # Identity writes do not create a computational effect.
                    if effect == {"op": "token", "token": target}:
                        continue
                    item = groups.setdefault(
                        signature,
                        {
                            "variants": {},
                            "sources": set(),
                            "occurrences": 0,
                            "target": target,
                            "effect": effect,
                        },
                    )
                    key = json.dumps(
                        [instruction.to_dict() for instruction in normalized_instructions],
                        sort_keys=True, separators=(",", ":"),
                    )
                    variant = item["variants"].setdefault(
                        key, {"instructions": normalized_instructions, "count": 0}
                    )
                    variant["count"] += 1
                    item["sources"].add(record_id)
                    item["occurrences"] += 1

        eligible = [
            (signature, item)
            for signature, item in groups.items()
            if item["occurrences"] >= minimum_occurrences and len(item["sources"]) >= 2
        ]
        eligible.sort(
            key=lambda pair: (
                -pair[1]["occurrences"],
                -len(pair[1]["sources"]),
                _ast_size(pair[1]["effect"]),
                pair[0],
            )
        )
        if len(eligible) < requested_count:
            raise ValueError(
                f"only {len(eligible)} supported distinct effects; {requested_count} required"
            )
        result = []
        for index, (signature, item) in enumerate(eligible[:requested_count]):
            best_variant = sorted(
                item["variants"].values(),
                key=lambda variant: (-variant["count"], len(variant["instructions"]), repr(variant["instructions"])),
            )[0]
            payload = {
                "opcode": first_opcode + index,
                "instructions": [instruction.to_dict() for instruction in best_variant["instructions"]],
                "effect": item["effect"],
                "sources": sorted(item["sources"]),
                "occurrences": item["occurrences"],
            }
            encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            result.append(
                InducedMicroOperator(
                    "SEM-" + hashlib.sha256(encoded.encode()).hexdigest()[:16],
                    first_opcode + index,
                    tuple(best_variant["instructions"]),
                    item["target"],
                    item["effect"],
                    signature,
                    tuple(sorted(item["sources"])),
                    item["occurrences"],
                )
            )
        return tuple(result)


class MicroOperatorExecutor:
    """Execute the compiled symbolic effect rather than replaying its source block."""

    def execute(
        self,
        operator: InducedMicroOperator,
        *,
        cells: Sequence[float],
        inputs: Sequence[float],
        immediates: Sequence[float],
    ) -> tuple[float, ...]:
        memory = [float(value) for value in cells]
        target_index = _token_index(operator.target_token, "cell")
        if target_index >= len(memory):
            raise ValueError("operator target cell is unavailable")
        memory[target_index] = _evaluate_ast(
            operator.effect_ast, memory, inputs, immediates
        )
        return tuple(memory)


def _normalize_block(
    block: Sequence[tuple[int, int]],
) -> tuple[tuple[NormalizedMicroInstruction, ...], str, Mapping[str, Any]] | None:
    if len(block) < 2 or block[0][0] not in START_OPS or block[-1][0] != OP_STORE_CELL:
        return None
    if any(opcode not in MIDDLE_OPS for opcode, _ in block[1:-1]):
        return None
    token_maps: dict[str, dict[int, str]] = {"cell": {}, "input": {}, "immediate": {}}

    def token(kind: str, operand: int) -> str:
        mapping = token_maps[kind]
        if operand not in mapping:
            mapping[operand] = f"{kind}:{len(mapping)}"
        return mapping[operand]

    normalized = []
    accumulator: Mapping[str, Any] | None = None
    for opcode, operand in block:
        if opcode in CELL_OPS:
            operand_token = token("cell", operand)
        elif opcode in INPUT_OPS:
            operand_token = token("input", operand)
        elif opcode in IMMEDIATE_OPS:
            operand_token = token("immediate", operand)
        else:
            return None
        normalized.append(NormalizedMicroInstruction(opcode, operand_token))
        node = {"op": "token", "token": operand_token}
        if opcode in (OP_LOAD_CELL, OP_LOAD_INPUT, OP_SET):
            accumulator = node
        elif opcode in (OP_ADD_CELL, OP_ADD_INPUT, OP_ADD_IMMEDIATE):
            if accumulator is None:
                return None
            accumulator = {"op": "add", "args": [accumulator, node]}
        elif opcode in (OP_SUB_CELL, OP_SUB_INPUT, OP_SUB_IMMEDIATE):
            if accumulator is None:
                return None
            accumulator = {"op": "sub", "args": [accumulator, node]}
    if accumulator is None:
        return None
    target = normalized[-1].operand_token
    return tuple(normalized), target, accumulator


def _effect_signature(target: str, effect: Mapping[str, Any]) -> str:
    return target + "=" + json.dumps(effect, sort_keys=True, separators=(",", ":"))


def _ast_size(node: Mapping[str, Any]) -> int:
    return 1 + sum(_ast_size(item) for item in node.get("args", []))


def _token_index(token: str, expected_kind: str) -> int:
    kind, raw = token.split(":", 1)
    if kind != expected_kind:
        raise ValueError(f"expected {expected_kind} token, got {kind}")
    return int(raw)


def _evaluate_ast(
    node: Mapping[str, Any],
    cells: Sequence[float], inputs: Sequence[float], immediates: Sequence[float],
) -> float:
    op = node["op"]
    if op == "token":
        token = str(node["token"])
        kind, raw = token.split(":", 1)
        index = int(raw)
        values = {"cell": cells, "input": inputs, "immediate": immediates}[kind]
        if index >= len(values):
            raise ValueError(f"{kind} slot unavailable")
        return float(values[index])
    left, right = node["args"]
    left_value = _evaluate_ast(left, cells, inputs, immediates)
    right_value = _evaluate_ast(right, cells, inputs, immediates)
    return left_value + right_value if op == "add" else left_value - right_value
