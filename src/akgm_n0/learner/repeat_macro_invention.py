"""Induce a higher-order repeat macro from proven counter-loop skeletons."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .metamachine_gen2 import (
    OP_JUMP,
    OP_JUMP_IF_ZERO,
    OP_LOAD_CELL,
    OP_STORE_CELL,
    OP_SUB_IMMEDIATE,
    REGISTERED_OPCODES,
)


@dataclass(frozen=True, slots=True)
class RepeatLoopOccurrence:
    source_record_id: str
    start_instruction: int
    counter_cell: int
    body_opcode_shape: tuple[int, ...]
    body_instruction_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_record_id": self.source_record_id,
            "start_instruction": self.start_instruction,
            "counter_cell": self.counter_cell,
            "body_opcode_shape": list(self.body_opcode_shape),
            "body_instruction_count": self.body_instruction_count,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RepeatLoopOccurrence":
        return cls(
            str(value["source_record_id"]), int(value["start_instruction"]),
            int(value["counter_cell"]),
            tuple(int(item) for item in value["body_opcode_shape"]),
            int(value["body_instruction_count"]),
        )


@dataclass(frozen=True, slots=True)
class RepeatMacroSemantic:
    semantic_id: str
    opcode: int
    occurrences: tuple[RepeatLoopOccurrence, ...]
    observed_body_shapes: tuple[tuple[int, ...], ...]
    counter_update_shape: tuple[int, ...] = (
        OP_LOAD_CELL, OP_SUB_IMMEDIATE, OP_STORE_CELL, OP_JUMP
    )

    @property
    def source_record_ids(self) -> tuple[str, ...]:
        return tuple(sorted({item.source_record_id for item in self.occurrences}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id,
            "opcode": self.opcode,
            "occurrences": [item.to_dict() for item in self.occurrences],
            "observed_body_shapes": [list(item) for item in self.observed_body_shapes],
            "counter_update_shape": list(self.counter_update_shape),
            "source_record_ids": list(self.source_record_ids),
            "supporting_occurrence_count": len(self.occurrences),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RepeatMacroSemantic":
        return cls(
            str(value["semantic_id"]), int(value["opcode"]),
            tuple(RepeatLoopOccurrence.from_dict(item) for item in value["occurrences"]),
            tuple(tuple(int(opcode) for opcode in item) for item in value["observed_body_shapes"]),
            tuple(int(item) for item in value["counter_update_shape"]),
        )


@dataclass(frozen=True, slots=True)
class RepeatMacroExecution:
    final_state: tuple[Any, ...]
    iteration_count: int
    remaining_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_state": list(self.final_state),
            "iteration_count": self.iteration_count,
            "remaining_count": self.remaining_count,
        }


class RepeatMacroInducer:
    def induce(
        self,
        sources: Sequence[tuple[str, Sequence[int]]],
        *,
        occupied_opcodes: Sequence[int],
    ) -> RepeatMacroSemantic:
        occurrences = []
        for record_id, words in sources:
            occurrences.extend(_scan(record_id, words))
        body_shapes = tuple(sorted({item.body_opcode_shape for item in occurrences}))
        source_ids = {item.source_record_id for item in occurrences}
        if len(source_ids) < 5 or len(body_shapes) < 2:
            raise ValueError("repeat macro requires five sources and two distinct body shapes")
        used = set(REGISTERED_OPCODES) | set(occupied_opcodes)
        opcode = min(value for value in range(max(used) + 2) if value not in used)
        payload = {
            "opcode": opcode,
            "occurrences": [item.to_dict() for item in occurrences],
            "body_shapes": [list(item) for item in body_shapes],
            "counter_tail": [OP_LOAD_CELL, OP_SUB_IMMEDIATE, OP_STORE_CELL, OP_JUMP],
        }
        semantic_id = "SEM-" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16]
        return RepeatMacroSemantic(
            semantic_id, opcode, tuple(occurrences), body_shapes
        )


class RepeatMacroExecutor:
    """Execute one registered transition repeatedly through a single macro call."""

    def __init__(self, *, maximum_repetitions: int = 1_000_000):
        self.maximum_repetitions = maximum_repetitions

    def execute(
        self,
        initial_state: Sequence[Any],
        repeat_count: int,
        transition: Callable[[tuple[Any, ...]], Sequence[Any]],
    ) -> RepeatMacroExecution:
        if isinstance(repeat_count, bool) or not isinstance(repeat_count, int) or repeat_count < 0:
            raise ValueError("repeat count must be a natural number")
        if repeat_count > self.maximum_repetitions:
            raise ValueError("repeat count exceeds safety bound")
        state = tuple(initial_state)
        remaining = repeat_count
        iterations = 0
        while remaining:
            state = tuple(transition(state))
            remaining -= 1
            iterations += 1
        return RepeatMacroExecution(state, iterations, remaining)


def _scan(record_id: str, words: Sequence[int]) -> tuple[RepeatLoopOccurrence, ...]:
    instructions = tuple(zip(words[::2], words[1::2]))
    found = []
    for end, (opcode, target) in enumerate(instructions):
        if opcode != OP_JUMP or target >= end:
            continue
        start = target
        block = instructions[start : end + 1]
        if len(block) < 7:
            continue
        counter = block[0][1]
        if (
            block[0][0] != OP_LOAD_CELL
            or block[1] != (OP_JUMP_IF_ZERO, end + 1)
            or tuple(item[0] for item in block[-4:])
            != (OP_LOAD_CELL, OP_SUB_IMMEDIATE, OP_STORE_CELL, OP_JUMP)
            or block[-4][1] != counter
            or block[-3][1] != 1
            or block[-2][1] != counter
            or block[-1][1] != start
        ):
            continue
        body = block[2:-4]
        if not body or any(item[0] in (OP_JUMP, OP_JUMP_IF_ZERO) for item in body):
            continue
        found.append(
            RepeatLoopOccurrence(
                record_id, start, counter,
                tuple(item[0] for item in body), len(body),
            )
        )
    return tuple(found)

