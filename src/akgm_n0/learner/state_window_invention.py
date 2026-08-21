"""Induce and execute a state-window shift semantic from proven copy chains."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .metamachine_gen2 import (
    CodeModification,
    InvalidReflectiveProgram,
    MemoryGrowth,
    OP_ADD_CELL,
    OP_ADD_IMMEDIATE,
    OP_ADD_INPUT,
    OP_EMIT,
    OP_GROW,
    OP_HALT,
    OP_JUMP,
    OP_JUMP_IF_NEGATIVE,
    OP_JUMP_IF_ZERO,
    OP_LOAD_CELL,
    OP_LOAD_INPUT,
    OP_SET,
    OP_STORE_CELL,
    OP_SUB_CELL,
    OP_SUB_IMMEDIATE,
    OP_SUB_INPUT,
    REGISTERED_OPCODES,
    ReflectiveCandidate,
    ReflectiveExecution,
    ReflectiveSearchReport,
)
from .observation import NumericTableObservation


@dataclass(frozen=True, slots=True)
class StateWindowSemantic:
    semantic_id: str
    opcode: int
    source_record_ids: tuple[str, ...]
    observed_widths: tuple[int, ...]
    supporting_occurrence_count: int
    effect_schema: str = "shift contiguous state window left and append source cell"

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id,
            "opcode": self.opcode,
            "source_record_ids": list(self.source_record_ids),
            "observed_widths": list(self.observed_widths),
            "supporting_occurrence_count": self.supporting_occurrence_count,
            "effect_schema": self.effect_schema,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StateWindowSemantic":
        required = {
            "semantic_id", "opcode", "source_record_ids", "observed_widths",
            "supporting_occurrence_count", "effect_schema",
        }
        if set(value) != required:
            raise InvalidReflectiveProgram("state-window semantic shape is invalid")
        semantic = cls(
            str(value["semantic_id"]),
            int(value["opcode"]),
            tuple(str(item) for item in value["source_record_ids"]),
            tuple(int(item) for item in value["observed_widths"]),
            int(value["supporting_occurrence_count"]),
            str(value["effect_schema"]),
        )
        if semantic.opcode in REGISTERED_OPCODES or semantic.opcode <= max(REGISTERED_OPCODES):
            raise InvalidReflectiveProgram("state-window opcode must occupy an unused slot")
        return semantic


class StateWindowOpcodeInducer:
    """Mine consecutive load/store chains without formula or theorem labels."""

    def induce(
        self,
        sources: Sequence[tuple[str, Sequence[int]]],
        *,
        occupied_opcodes: Sequence[int] = (16,),
    ) -> StateWindowSemantic:
        supporting_ids = []
        widths = []
        occurrences = 0
        for record_id, words in sources:
            found = _copy_chain_widths(words)
            if found:
                supporting_ids.append(record_id)
                widths.extend(found)
                occurrences += len(found)
        observed = tuple(sorted(set(widths)))
        if not {2, 3, 4}.issubset(observed):
            raise ValueError("proven code does not support state-window widths 2, 3, and 4")
        used = set(REGISTERED_OPCODES) | set(occupied_opcodes)
        opcode = min(value for value in range(max(used) + 2) if value not in used)
        payload = {
            "opcode": opcode,
            "sources": sorted(supporting_ids),
            "observed_widths": observed,
            "occurrences": occurrences,
            "micro_shape": [OP_LOAD_CELL, OP_STORE_CELL],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return StateWindowSemantic(
            "SEM-" + hashlib.sha256(encoded.encode()).hexdigest()[:16],
            opcode,
            tuple(sorted(supporting_ids)),
            observed,
            occurrences,
        )


def _copy_chain_widths(words: Sequence[int]) -> tuple[int, ...]:
    instructions = tuple(zip(words[::2], words[1::2]))
    widths = []
    index = 0
    while index + 1 < len(instructions):
        pairs = []
        cursor = index
        while (
            cursor + 1 < len(instructions)
            and instructions[cursor][0] == OP_LOAD_CELL
            and instructions[cursor + 1][0] == OP_STORE_CELL
        ):
            pairs.append((instructions[cursor][1], instructions[cursor + 1][1]))
            cursor += 2
        if len(pairs) >= 2 and all(
            pairs[position][0] == pairs[position + 1][1]
            for position in range(len(pairs) - 1)
        ):
            widths.append(len(pairs))
            index = cursor
        else:
            index += 1
    return tuple(widths)


@dataclass(frozen=True, slots=True)
class StateWindowProgram:
    words: tuple[int, ...]
    invented_semantic: StateWindowSemantic

    @property
    def instruction_count(self) -> int:
        return len(self.words) // 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "state_window_semantic_word_machine_v0.1",
            "word_width": 2,
            "invented_semantic": self.invented_semantic.to_dict(),
            "words": list(self.words),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StateWindowProgram":
        if set(value) != {"substrate", "word_width", "invented_semantic", "words"}:
            raise InvalidReflectiveProgram("state-window program shape is invalid")
        if value["substrate"] != "state_window_semantic_word_machine_v0.1" or value["word_width"] != 2:
            raise InvalidReflectiveProgram("state-window substrate is invalid")
        program = cls(
            tuple(int(item) for item in value["words"]),
            StateWindowSemantic.from_dict(value["invented_semantic"]),
        )
        StateWindowExecutor().validate(program)
        return program


class StateWindowExecutor:
    def __init__(
        self, *, maximum_instructions: int = 64, maximum_steps: int = 500_000,
        maximum_memory_cells: int = 512, magnitude_limit: float = 1e100,
    ) -> None:
        self.maximum_instructions = maximum_instructions
        self.maximum_steps = maximum_steps
        self.maximum_memory_cells = maximum_memory_cells
        self.magnitude_limit = magnitude_limit

    def validate(self, program: StateWindowProgram) -> None:
        if not program.words or len(program.words) % 2:
            raise InvalidReflectiveProgram("word code must contain complete instructions")
        if program.instruction_count > self.maximum_instructions:
            raise InvalidReflectiveProgram("word code exceeds instruction bound")
        allowed = set(REGISTERED_OPCODES) | {program.invented_semantic.opcode}
        if any(program.words[index] not in allowed for index in range(0, len(program.words), 2)):
            raise InvalidReflectiveProgram("program contains unavailable opcode")

    def execute(self, program: StateWindowProgram, inputs: Sequence[float]) -> ReflectiveExecution:
        self.validate(program)
        numeric_inputs = tuple(float(item) for item in inputs)
        if not all(math.isfinite(item) for item in numeric_inputs):
            raise InvalidReflectiveProgram("inputs must be finite")
        memory = [float(item) for item in program.words]
        original_size = len(memory)
        accumulator = 0.0
        pc = 0
        emitted = []
        modifications = []
        growth = []
        visited = []
        steps = 0
        while steps <= self.maximum_steps:
            cell = pc * 2
            if cell < 0 or cell + 1 >= len(memory):
                raise InvalidReflectiveProgram("instruction pointer left unified memory")
            opcode = _integer(memory[cell])
            operand = _integer(memory[cell + 1])
            visited.append(pc)
            steps += 1
            next_pc = pc + 1
            if opcode == OP_HALT:
                if not emitted:
                    raise InvalidReflectiveProgram("program halted without emitting")
                return ReflectiveExecution(
                    emitted[-1], tuple(emitted), steps, accumulator, tuple(memory),
                    tuple(modifications), tuple(growth), tuple(visited),
                )
            if opcode == OP_LOAD_INPUT:
                accumulator = self._input(numeric_inputs, operand)
            elif opcode == OP_LOAD_CELL:
                accumulator = self._cell(memory, operand)
            elif opcode == OP_STORE_CELL:
                self._address(memory, operand)
                previous = memory[operand]
                memory[operand] = self._checked(accumulator)
                if operand < original_size and previous != memory[operand]:
                    modifications.append(CodeModification(steps, operand, previous, memory[operand]))
            elif opcode == OP_SET:
                accumulator = self._checked(float(operand))
            elif opcode == OP_ADD_INPUT:
                accumulator = self._checked(accumulator + self._input(numeric_inputs, operand))
            elif opcode == OP_SUB_INPUT:
                accumulator = self._checked(accumulator - self._input(numeric_inputs, operand))
            elif opcode == OP_ADD_CELL:
                accumulator = self._checked(accumulator + self._cell(memory, operand))
            elif opcode == OP_SUB_CELL:
                accumulator = self._checked(accumulator - self._cell(memory, operand))
            elif opcode == OP_ADD_IMMEDIATE:
                accumulator = self._checked(accumulator + operand)
            elif opcode == OP_SUB_IMMEDIATE:
                accumulator = self._checked(accumulator - operand)
            elif opcode == OP_JUMP:
                next_pc = operand
            elif opcode == OP_JUMP_IF_ZERO:
                if accumulator == 0:
                    next_pc = operand
            elif opcode == OP_JUMP_IF_NEGATIVE:
                if accumulator < 0:
                    next_pc = operand
            elif opcode == OP_GROW:
                if operand < 1 or len(memory) + operand > self.maximum_memory_cells:
                    raise InvalidReflectiveProgram("memory growth outside bound")
                previous = len(memory)
                memory.extend(0.0 for _ in range(operand))
                growth.append(MemoryGrowth(steps, previous, len(memory)))
            elif opcode == OP_EMIT:
                emitted.append(self._checked(accumulator))
            elif opcode == program.invented_semantic.opcode:
                width, start, source = _decode_descriptor(operand)
                if width < 1 or start < 0 or start + width > len(memory):
                    raise InvalidReflectiveProgram("state window lies outside memory")
                self._address(memory, source)
                snapshot = tuple(memory[start : start + width])
                appended = memory[source]
                for offset in range(width - 1):
                    memory[start + offset] = snapshot[offset + 1]
                memory[start + width - 1] = appended
                accumulator = appended
                steps += width
                if steps > self.maximum_steps:
                    raise InvalidReflectiveProgram("state-window step bound exceeded")
            else:
                raise InvalidReflectiveProgram("runtime opcode unavailable")
            pc = next_pc
        raise InvalidReflectiveProgram("program did not halt within step bound")

    def _input(self, inputs: tuple[float, ...], index: int) -> float:
        if index < 0 or index >= len(inputs):
            raise InvalidReflectiveProgram("input index unavailable")
        return self._checked(inputs[index])

    def _cell(self, memory: list[float], address: int) -> float:
        self._address(memory, address)
        return self._checked(memory[address])

    @staticmethod
    def _address(memory: list[float], address: int) -> None:
        if address < 0 or address >= len(memory):
            raise InvalidReflectiveProgram("memory address unavailable")

    def _checked(self, value: float) -> float:
        value = float(value)
        if not math.isfinite(value) or abs(value) > self.magnitude_limit:
            raise InvalidReflectiveProgram("unsafe magnitude")
        return value


class StateWindowGrowthSearch:
    """Use the induced operator at an unseen width in an anonymous recurrence."""

    def __init__(
        self, semantic: StateWindowSemantic, *, top_k: int = 5000,
        executor: StateWindowExecutor | None = None,
    ) -> None:
        self.semantic = semantic
        self.top_k = top_k
        self.executor = executor or StateWindowExecutor()

    def search(self, observation: NumericTableObservation) -> ReflectiveSearchReport:
        valid = tuple(
            (row, float(output))
            for row, output, include in zip(
                observation.input_rows, observation.output_values,
                observation.validity_mask, strict=True,
            )
            if include
        )
        if not valid or len(valid[0][0]) != 6:
            raise ValueError("state-window growth requires anonymous six-column evidence")
        candidates = []
        rejected = generated = 0
        for roles in itertools.permutations(range(6)):
            seeds, counter = roles[:5], roles[5]
            for output in ("a", "b", "c", "d", "e"):
                generated += 1
                program = _five_state_program(self.semantic, seeds, counter, output)
                outputs = []
                try:
                    for row, _ in valid:
                        outputs.append(self.executor.execute(program, row).output_value)
                except InvalidReflectiveProgram:
                    rejected += 1
                    continue
                errors = tuple(
                    actual - target
                    for actual, (_, target) in zip(outputs, valid, strict=True)
                )
                key = state_window_program_key(program)
                candidates.append(
                    ReflectiveCandidate(
                        "SW-" + hashlib.sha256(key.encode()).hexdigest()[:16],
                        program,
                        sum(error * error for error in errors) / len(errors),
                        max(abs(error) for error in errors),
                        tuple(outputs), tuple(outputs),
                    )
                )
        candidates.sort(
            key=lambda item: (
                item.fit_error, item.program.instruction_count,
                item.maximum_absolute_error, item.candidate_id,
            )
        )
        return ReflectiveSearchReport(
            generated, len(candidates), rejected,
            len({item.outputs for item in candidates}), tuple(candidates[: self.top_k]),
        )


def state_window_program_key(program: StateWindowProgram) -> str:
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))


def state_window_probe_program(
    semantic: StateWindowSemantic, width: int
) -> tuple[StateWindowProgram, int]:
    """Build a one-shot executable used by an independent equivalence check."""
    if width < 1 or width > 20:
        raise ValueError("probe width is outside the verification bound")
    names = tuple(f"s{index}" for index in range(width))
    entries = [(OP_GROW, width + 1)]
    for index, name in enumerate(names):
        entries.extend(((OP_LOAD_INPUT, index), (OP_STORE_CELL, name)))
    entries.extend(
        (
            (OP_LOAD_INPUT, width), (OP_STORE_CELL, "source"),
            (semantic.opcode, (width, names[0], "source")),
            (OP_LOAD_CELL, names[0]), (OP_EMIT, 0), (OP_HALT, 0),
        )
    )
    program = _assemble(entries, names + ("source",), semantic)
    return program, 2 * program.instruction_count


def _encode_descriptor(width: int, start: int, source: int) -> int:
    if not (1 <= width < 100 and 0 <= start < 100 and 0 <= source < 100):
        raise ValueError("state-window descriptor field outside bound")
    return width * 10_000 + start * 100 + source


def _decode_descriptor(operand: int) -> tuple[int, int, int]:
    if operand < 0:
        raise InvalidReflectiveProgram("negative state-window descriptor")
    return operand // 10_000, (operand // 100) % 100, operand % 100


def _assemble(entries, data, semantic: StateWindowSemantic) -> StateWindowProgram:
    labels = {}
    instructions = []
    for entry in entries:
        if isinstance(entry, str):
            labels[entry] = len(instructions)
        else:
            instructions.append(entry)
    addresses = {name: 2 * len(instructions) + index for index, name in enumerate(data)}
    words = []
    for opcode, operand in instructions:
        if isinstance(operand, str):
            operand = labels[operand] if opcode in (OP_JUMP, OP_JUMP_IF_ZERO, OP_JUMP_IF_NEGATIVE) else addresses[operand]
        elif isinstance(operand, tuple):
            width, start, source = operand
            operand = _encode_descriptor(width, addresses[start], addresses[source])
        words.extend((opcode, operand))
    return StateWindowProgram(tuple(words), semantic)


def _five_state_program(
    semantic: StateWindowSemantic,
    seeds: Sequence[int],
    counter: int,
    output: str,
) -> StateWindowProgram:
    entries = [(OP_GROW, 7), (OP_LOAD_INPUT, counter), (OP_STORE_CELL, "counter")]
    for name, input_index in zip(("a", "b", "c", "d", "e"), seeds, strict=True):
        entries.extend(((OP_LOAD_INPUT, input_index), (OP_STORE_CELL, name)))
    entries.extend(
        (
            "outer", (OP_LOAD_CELL, "counter"), (OP_JUMP_IF_ZERO, "end"),
            (OP_LOAD_CELL, "a"), (OP_ADD_CELL, "b"), (OP_ADD_CELL, "c"),
            (OP_ADD_CELL, "d"), (OP_ADD_CELL, "e"), (OP_STORE_CELL, "next"),
            (semantic.opcode, (5, "a", "next")),
            (OP_LOAD_CELL, "counter"), (OP_SUB_IMMEDIATE, 1),
            (OP_STORE_CELL, "counter"), (OP_JUMP, "outer"),
            "end", (OP_LOAD_CELL, output), (OP_EMIT, 0), (OP_HALT, 0),
        )
    )
    return _assemble(entries, ("counter", "a", "b", "c", "d", "e", "next"), semantic)


def _integer(value: float) -> int:
    if not float(value).is_integer():
        raise InvalidReflectiveProgram("runtime word is not an integer")
    return int(value)
