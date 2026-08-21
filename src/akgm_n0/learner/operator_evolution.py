"""Second-generation operator synthesis by verified semantic composition."""

from __future__ import annotations

import hashlib
import itertools
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
from .micro_operator_mining import InducedMicroOperator, NormalizedMicroInstruction


@dataclass(frozen=True, slots=True)
class EvolvedMicroOperator:
    operator_id: str
    opcode: int
    normalized_instructions: tuple[NormalizedMicroInstruction, ...]
    target_token: str
    operand_tokens: tuple[str, ...]
    coefficient_vector: tuple[int, ...]
    effect_ast: Mapping[str, Any]
    effect_signature: str
    seed_library_digest: str
    generation: int = 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "opcode": self.opcode,
            "normalized_instructions": [item.to_dict() for item in self.normalized_instructions],
            "target_token": self.target_token,
            "operand_tokens": list(self.operand_tokens),
            "coefficient_vector": list(self.coefficient_vector),
            "effect_ast": dict(self.effect_ast),
            "effect_signature": self.effect_signature,
            "seed_library_digest": self.seed_library_digest,
            "generation": self.generation,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvolvedMicroOperator":
        return cls(
            str(value["operator_id"]),
            int(value["opcode"]),
            tuple(
                NormalizedMicroInstruction.from_dict(item)
                for item in value["normalized_instructions"]
            ),
            str(value["target_token"]),
            tuple(str(item) for item in value["operand_tokens"]),
            tuple(int(item) for item in value["coefficient_vector"]),
            dict(value["effect_ast"]),
            str(value["effect_signature"]),
            str(value["seed_library_digest"]),
            int(value.get("generation", 2)),
        )


class OperatorEvolutionSearch:
    """Enumerate minimal additive programs and retain unique algebraic effects."""

    def discover(
        self,
        seeds: Sequence[InducedMicroOperator],
        *,
        requested_count: int = 100,
        first_opcode: int = 28,
        excluded_coefficient_vectors: Sequence[Sequence[int]] = (),
        generation: int = 2,
    ) -> tuple[EvolvedMicroOperator, ...]:
        if not seeds:
            raise ValueError("operator evolution requires a verified seed library")
        operand_tokens = tuple(sorted(_effect_tokens(seeds)))
        if len(operand_tokens) < 2:
            raise ValueError("seed library exposes too few operand roles")
        target_token = _most_common_target(seeds)
        seed_digest = hashlib.sha256(
            "|".join(sorted(item.operator_id for item in seeds)).encode()
        ).hexdigest()
        excluded = {
            _coefficient_vector(item.effect_ast, operand_tokens) for item in seeds
        }
        excluded.update(tuple(int(value) for value in item) for item in excluded_coefficient_vectors)
        seen = set(excluded)
        results: list[EvolvedMicroOperator] = []
        step_options = tuple(
            (sign, token) for sign in (1, -1) for token in operand_tokens
        )

        # Increasing program length is the reduction reward: the first program
        # retained for an algebraic effect is its shortest discovered expansion.
        for middle_count in range(1, 8):
            for start_token in operand_tokens:
                for steps in itertools.product(step_options, repeat=middle_count):
                    vector = [0] * len(operand_tokens)
                    vector[operand_tokens.index(start_token)] += 1
                    for sign, token in steps:
                        vector[operand_tokens.index(token)] += sign
                    coefficient_vector = tuple(vector)
                    if sum(value != 0 for value in coefficient_vector) < 2:
                        continue
                    if coefficient_vector in seen:
                        continue
                    seen.add(coefficient_vector)
                    effect_ast = _effect_ast(start_token, steps)
                    signature = _effect_signature(
                        target_token, operand_tokens, coefficient_vector
                    )
                    instructions = (
                        NormalizedMicroInstruction(_load_opcode(start_token), start_token),
                        *(
                            NormalizedMicroInstruction(
                                _middle_opcode(sign, token), token
                            )
                            for sign, token in steps
                        ),
                        NormalizedMicroInstruction(OP_STORE_CELL, target_token),
                    )
                    opcode = first_opcode + len(results)
                    payload = {
                        "opcode": opcode,
                        "instructions": [item.to_dict() for item in instructions],
                        "target": target_token,
                        "operands": list(operand_tokens),
                        "coefficients": list(coefficient_vector),
                        "seed_library_digest": seed_digest,
                        "generation": generation,
                    }
                    operator_id = "ESEM-" + hashlib.sha256(
                        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
                    ).hexdigest()[:16]
                    results.append(
                        EvolvedMicroOperator(
                            operator_id,
                            opcode,
                            tuple(instructions),
                            target_token,
                            operand_tokens,
                            coefficient_vector,
                            effect_ast,
                            signature,
                            seed_digest,
                            generation,
                        )
                    )
                    if len(results) == requested_count:
                        return tuple(results)
        raise ValueError(
            f"only {len(results)} distinct evolved effects; {requested_count} required"
        )


class EvolvedMicroOperatorExecutor:
    def execute(
        self,
        operator: EvolvedMicroOperator,
        *,
        cells: Sequence[float],
        inputs: Sequence[float],
        immediates: Sequence[float],
    ) -> tuple[float, ...]:
        memory = [float(value) for value in cells]
        target_kind, target_raw = operator.target_token.split(":", 1)
        if target_kind != "cell":
            raise ValueError("operator target must be a cell")
        memory[int(target_raw)] = _evaluate(
            operator.effect_ast, memory, inputs, immediates
        )
        return tuple(memory)


def _effect_tokens(seeds: Sequence[InducedMicroOperator]) -> set[str]:
    tokens: set[str] = set()
    for seed in seeds:
        _collect_tokens(seed.effect_ast, tokens)
    return tokens


def _collect_tokens(node: Mapping[str, Any], output: set[str]) -> None:
    if node["op"] == "token":
        output.add(str(node["token"]))
        return
    for child in node["args"]:
        _collect_tokens(child, output)


def _most_common_target(seeds: Sequence[InducedMicroOperator]) -> str:
    counts: dict[str, int] = {}
    for seed in seeds:
        counts[seed.target_token] = counts.get(seed.target_token, 0) + 1
    return sorted(counts, key=lambda token: (-counts[token], token))[0]


def _coefficient_vector(
    node: Mapping[str, Any], operand_tokens: Sequence[str]
) -> tuple[int, ...]:
    coefficients = {token: 0 for token in operand_tokens}

    def walk(current: Mapping[str, Any], sign: int = 1) -> None:
        if current["op"] == "token":
            coefficients[str(current["token"])] += sign
            return
        left, right = current["args"]
        walk(left, sign)
        walk(right, sign if current["op"] == "add" else -sign)

    walk(node)
    return tuple(coefficients[token] for token in operand_tokens)


def _effect_ast(
    start_token: str, steps: Sequence[tuple[int, str]]
) -> Mapping[str, Any]:
    node: Mapping[str, Any] = {"op": "token", "token": start_token}
    for sign, token in steps:
        node = {
            "op": "add" if sign == 1 else "sub",
            "args": [node, {"op": "token", "token": token}],
        }
    return node


def _effect_signature(
    target: str, tokens: Sequence[str], coefficients: Sequence[int]
) -> str:
    return target + "=" + ",".join(
        f"{token}:{coefficient}" for token, coefficient in zip(tokens, coefficients, strict=True)
    )


def _load_opcode(token: str) -> int:
    kind = token.split(":", 1)[0]
    return {"cell": OP_LOAD_CELL, "input": OP_LOAD_INPUT, "immediate": OP_SET}[kind]


def _middle_opcode(sign: int, token: str) -> int:
    kind = token.split(":", 1)[0]
    if sign == 1:
        return {"cell": OP_ADD_CELL, "input": OP_ADD_INPUT, "immediate": OP_ADD_IMMEDIATE}[kind]
    return {"cell": OP_SUB_CELL, "input": OP_SUB_INPUT, "immediate": OP_SUB_IMMEDIATE}[kind]


def _evaluate(
    node: Mapping[str, Any],
    cells: Sequence[float],
    inputs: Sequence[float],
    immediates: Sequence[float],
) -> float:
    if node["op"] == "token":
        kind, raw = str(node["token"]).split(":", 1)
        values = {"cell": cells, "input": inputs, "immediate": immediates}[kind]
        return float(values[int(raw)])
    left, right = node["args"]
    left_value = _evaluate(left, cells, inputs, immediates)
    right_value = _evaluate(right, cells, inputs, immediates)
    return left_value + right_value if node["op"] == "add" else left_value - right_value
