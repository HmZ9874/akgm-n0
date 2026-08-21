"""Induce a data-dependent guarded reduction loop from proven anonymous code."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .metamachine_gen2 import (
    OP_ADD_IMMEDIATE,
    OP_JUMP,
    OP_JUMP_IF_NEGATIVE,
    OP_LOAD_CELL,
    OP_STORE_CELL,
    OP_SUB_INPUT,
    REGISTERED_OPCODES,
)


LOOP_SHAPE = (
    OP_LOAD_CELL,
    OP_SUB_INPUT,
    OP_JUMP_IF_NEGATIVE,
    OP_STORE_CELL,
    OP_LOAD_CELL,
    OP_ADD_IMMEDIATE,
    OP_STORE_CELL,
    OP_JUMP,
)


@dataclass(frozen=True, slots=True)
class GuardedReductionOccurrence:
    source_record_id: str
    start_instruction: int
    remainder_cell: int
    count_cell: int
    divisor_input: int
    increment: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_record_id": self.source_record_id,
            "start_instruction": self.start_instruction,
            "remainder_cell": self.remainder_cell,
            "count_cell": self.count_cell,
            "divisor_input": self.divisor_input,
            "increment": self.increment,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GuardedReductionOccurrence":
        return cls(
            str(value["source_record_id"]),
            int(value["start_instruction"]),
            int(value["remainder_cell"]),
            int(value["count_cell"]),
            int(value["divisor_input"]),
            int(value["increment"]),
        )


@dataclass(frozen=True, slots=True)
class GuardedReductionSemantic:
    semantic_id: str
    opcode: int
    occurrences: tuple[GuardedReductionOccurrence, ...]
    normalized_opcode_shape: tuple[int, ...] = LOOP_SHAPE

    @property
    def source_record_ids(self) -> tuple[str, ...]:
        return tuple(sorted({item.source_record_id for item in self.occurrences}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id,
            "opcode": self.opcode,
            "occurrences": [item.to_dict() for item in self.occurrences],
            "source_record_ids": list(self.source_record_ids),
            "supporting_occurrence_count": len(self.occurrences),
            "normalized_opcode_shape": list(self.normalized_opcode_shape),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GuardedReductionSemantic":
        return cls(
            str(value["semantic_id"]),
            int(value["opcode"]),
            tuple(GuardedReductionOccurrence.from_dict(item) for item in value["occurrences"]),
            tuple(int(item) for item in value["normalized_opcode_shape"]),
        )


@dataclass(frozen=True, slots=True)
class GuardedReductionExecution:
    final_remainder: int
    final_count: int
    iteration_count: int

    def to_dict(self) -> dict[str, int]:
        return {
            "final_remainder": self.final_remainder,
            "final_count": self.final_count,
            "iteration_count": self.iteration_count,
        }


class GuardedReductionOpcodeInducer:
    def induce(
        self,
        sources: Sequence[tuple[str, Sequence[int]]],
        *,
        occupied_opcodes: Sequence[int],
    ) -> GuardedReductionSemantic:
        occurrences = []
        for record_id, words in sources:
            occurrences.extend(_scan(record_id, words))
        source_ids = {item.source_record_id for item in occurrences}
        if len(occurrences) < 3 or len(source_ids) < 3:
            raise ValueError("guarded reduction requires three proven source programs")
        used = set(REGISTERED_OPCODES) | set(occupied_opcodes)
        opcode = min(value for value in range(max(used) + 2) if value not in used)
        payload = {
            "opcode": opcode,
            "shape": list(LOOP_SHAPE),
            "occurrences": [item.to_dict() for item in occurrences],
        }
        semantic_id = "SEM-" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16]
        return GuardedReductionSemantic(semantic_id, opcode, tuple(occurrences))


class GuardedReductionExecutor:
    def execute(self, remainder: int, count: int, divisor: int) -> GuardedReductionExecution:
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (remainder, count, divisor)):
            raise ValueError("guarded reduction accepts integers")
        if remainder < 0 or count < 0 or divisor < 1:
            raise ValueError("domain requires remainder,count>=0 and divisor>=1")
        original_remainder = remainder
        iterations = 0
        while True:
            trial = remainder - divisor
            if trial < 0:
                break
            remainder = trial
            count += 1
            iterations += 1
            if iterations > original_remainder + 1:
                raise RuntimeError("termination measure failed")
        return GuardedReductionExecution(remainder, count, iterations)


def _scan(record_id: str, words: Sequence[int]) -> tuple[GuardedReductionOccurrence, ...]:
    instructions = tuple(zip(words[::2], words[1::2]))
    found = []
    for start in range(len(instructions) - len(LOOP_SHAPE) + 1):
        block = instructions[start : start + len(LOOP_SHAPE)]
        if tuple(opcode for opcode, _ in block) != LOOP_SHAPE:
            continue
        remainder = block[0][1]
        count = block[4][1]
        if (
            block[3][1] != remainder
            or block[6][1] != count
            or remainder == count
            or block[2][1] != start + len(LOOP_SHAPE)
            or block[7][1] != start
            or block[5][1] != 1
        ):
            continue
        found.append(
            GuardedReductionOccurrence(
                record_id, start, remainder, count, block[1][1], block[5][1]
            )
        )
    return tuple(found)

