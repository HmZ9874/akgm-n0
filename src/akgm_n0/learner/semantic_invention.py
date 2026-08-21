"""Induce a compressed opcode from repeated proven microprograms.

The new opcode is not assigned a mathematical name.  Its behavior is defined by
an extracted word-code block and executed as bounded repeated accumulation.
"""

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
    ReflectiveProgram,
    ReflectiveSearchReport,
)
from .observation import NumericTableObservation


MICRO_SHAPE = (
    OP_LOAD_INPUT, OP_STORE_CELL, OP_LOAD_CELL, OP_JUMP_IF_ZERO,
    OP_LOAD_CELL, OP_ADD_CELL, OP_STORE_CELL, OP_LOAD_CELL,
    OP_SUB_IMMEDIATE, OP_STORE_CELL, OP_JUMP,
)


@dataclass(frozen=True, slots=True)
class InventedSemantic:
    semantic_id: str
    opcode: int
    source_record_ids: tuple[str, ...]
    normalized_micro_shape: tuple[int, ...]
    supporting_occurrence_count: int
    compression_saving_per_use: int
    effect_schema: str = "repeat source-cell accumulation into target-cell by runtime counter"

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id,
            "opcode": self.opcode,
            "source_record_ids": list(self.source_record_ids),
            "normalized_micro_shape": list(self.normalized_micro_shape),
            "supporting_occurrence_count": self.supporting_occurrence_count,
            "compression_saving_per_use": self.compression_saving_per_use,
            "effect_schema": self.effect_schema,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InventedSemantic":
        required = {
            "semantic_id", "opcode", "source_record_ids", "normalized_micro_shape",
            "supporting_occurrence_count", "compression_saving_per_use", "effect_schema",
        }
        if set(value) != required:
            raise InvalidReflectiveProgram("invented semantic shape is invalid")
        semantic = cls(
            semantic_id=str(value["semantic_id"]),
            opcode=int(value["opcode"]),
            source_record_ids=tuple(str(item) for item in value["source_record_ids"]),
            normalized_micro_shape=tuple(int(item) for item in value["normalized_micro_shape"]),
            supporting_occurrence_count=int(value["supporting_occurrence_count"]),
            compression_saving_per_use=int(value["compression_saving_per_use"]),
            effect_schema=str(value["effect_schema"]),
        )
        if semantic.opcode in REGISTERED_OPCODES or semantic.opcode < 0:
            raise InvalidReflectiveProgram("invented opcode must occupy an unused slot")
        if semantic.normalized_micro_shape != MICRO_SHAPE:
            raise InvalidReflectiveProgram("invented semantic micro-shape is unavailable")
        return semantic


class SemanticOpcodeInducer:
    """Allocate the lowest unused opcode to a repeated, verified micro-shape."""

    def induce(
        self, sources: Sequence[tuple[str, ReflectiveProgram]]
    ) -> InventedSemantic:
        supporting_ids: list[str] = []
        occurrence_count = 0
        for record_id, program in sources:
            instructions = tuple(zip(program.words[::2], program.words[1::2]))
            count = _micro_shape_occurrences(instructions)
            if count:
                supporting_ids.append(record_id)
                occurrence_count += count
        if occurrence_count < 3:
            raise ValueError("not enough proven microprogram repetition to invent a semantic")
        opcode = min(set(range(max(REGISTERED_OPCODES) + 2)) - set(REGISTERED_OPCODES))
        payload = {
            "opcode": opcode,
            "source_record_ids": sorted(supporting_ids),
            "micro_shape": MICRO_SHAPE,
            "occurrences": occurrence_count,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return InventedSemantic(
            semantic_id="SEM-" + hashlib.sha256(encoded.encode()).hexdigest()[:16],
            opcode=opcode,
            source_record_ids=tuple(sorted(supporting_ids)),
            normalized_micro_shape=MICRO_SHAPE,
            supporting_occurrence_count=occurrence_count,
            compression_saving_per_use=len(MICRO_SHAPE) - 1,
        )


@dataclass(frozen=True, slots=True)
class SemanticExtendedProgram:
    words: tuple[int, ...]
    invented_semantic: InventedSemantic

    @property
    def instruction_count(self) -> int:
        return len(self.words) // 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "induced_semantic_word_machine_v0.1",
            "word_width": 2,
            "invented_semantic": self.invented_semantic.to_dict(),
            "words": list(self.words),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SemanticExtendedProgram":
        if set(value) != {"substrate", "word_width", "invented_semantic", "words"}:
            raise InvalidReflectiveProgram("semantic-extended program shape is invalid")
        if value["substrate"] != "induced_semantic_word_machine_v0.1" or value["word_width"] != 2:
            raise InvalidReflectiveProgram("semantic-extended substrate is invalid")
        semantic = InventedSemantic.from_dict(value["invented_semantic"])
        program = cls(tuple(value["words"]), semantic)
        SemanticExtendedExecutor().validate(program)
        return program


class SemanticExtendedExecutor:
    def __init__(
        self, *, maximum_instructions: int = 64, maximum_steps: int = 500_000,
        maximum_memory_cells: int = 512, magnitude_limit: float = 1e100,
    ) -> None:
        self.maximum_instructions = maximum_instructions
        self.maximum_steps = maximum_steps
        self.maximum_memory_cells = maximum_memory_cells
        self.magnitude_limit = magnitude_limit

    def validate(self, program: SemanticExtendedProgram) -> None:
        if not program.words or len(program.words) % 2:
            raise InvalidReflectiveProgram("word code must contain complete instructions")
        if program.instruction_count > self.maximum_instructions:
            raise InvalidReflectiveProgram("word code exceeds the instruction bound")
        if any(isinstance(word, bool) or not isinstance(word, int) for word in program.words):
            raise InvalidReflectiveProgram("word code must contain integers")
        allowed = set(REGISTERED_OPCODES) | {program.invented_semantic.opcode}
        if any(program.words[index] not in allowed for index in range(0, len(program.words), 2)):
            raise InvalidReflectiveProgram("program contains unavailable opcode")

    def execute(self, program: SemanticExtendedProgram, inputs: Sequence[float]) -> ReflectiveExecution:
        self.validate(program)
        numeric_inputs = tuple(float(item) for item in inputs)
        if not all(math.isfinite(item) for item in numeric_inputs):
            raise InvalidReflectiveProgram("inputs must be finite")
        memory = [float(item) for item in program.words]
        original_size = len(memory)
        accumulator = 0.0
        pc = 0
        emitted: list[float] = []
        modifications: list[CodeModification] = []
        growth: list[MemoryGrowth] = []
        visited: list[int] = []
        steps = 0
        while steps <= self.maximum_steps:
            cell = pc * 2
            if cell < 0 or cell + 1 >= len(memory):
                raise InvalidReflectiveProgram("instruction pointer left unified memory")
            opcode = _integer(memory[cell], "opcode")
            operand = _integer(memory[cell + 1], "operand")
            visited.append(pc)
            steps += 1
            next_pc = pc + 1
            if opcode == OP_HALT:
                if not emitted:
                    raise InvalidReflectiveProgram("program halted without emitting")
                return ReflectiveExecution(
                    output_value=emitted[-1], emitted_values=tuple(emitted),
                    step_count=steps, final_accumulator=accumulator,
                    final_memory=tuple(memory), code_modifications=tuple(modifications),
                    memory_growth=tuple(growth), visited_instruction_ids=tuple(visited),
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
                    raise InvalidReflectiveProgram("requested memory growth is outside the bound")
                previous = len(memory)
                memory.extend(0.0 for _ in range(operand))
                growth.append(MemoryGrowth(steps, previous, len(memory)))
            elif opcode == OP_EMIT:
                emitted.append(self._checked(accumulator))
            elif opcode == program.invented_semantic.opcode:
                coefficient_input, source_address, target_address = _decode_descriptor(operand)
                count_value = self._input(numeric_inputs, coefficient_input)
                if not count_value.is_integer() or count_value < 0:
                    raise InvalidReflectiveProgram("invented semantic requires a natural counter")
                source = self._cell(memory, source_address)
                target = self._cell(memory, target_address)
                for _ in range(int(count_value)):
                    steps += 1
                    if steps > self.maximum_steps:
                        raise InvalidReflectiveProgram("program exceeded semantic step bound")
                    target = self._checked(target + source)
                memory[target_address] = target
                accumulator = target
            else:
                raise InvalidReflectiveProgram("runtime opcode is unavailable")
            pc = next_pc
        raise InvalidReflectiveProgram("program did not halt within the step bound")

    def _input(self, inputs: tuple[float, ...], index: int) -> float:
        if index < 0 or index >= len(inputs):
            raise InvalidReflectiveProgram("input index is unavailable")
        return self._checked(inputs[index])

    def _cell(self, memory: list[float], address: int) -> float:
        self._address(memory, address)
        return self._checked(memory[address])

    @staticmethod
    def _address(memory: list[float], address: int) -> None:
        if address < 0 or address >= len(memory):
            raise InvalidReflectiveProgram("memory address is unavailable")

    def _checked(self, value: float) -> float:
        numeric = float(value)
        if not math.isfinite(numeric) or abs(numeric) > self.magnitude_limit:
            raise InvalidReflectiveProgram("program produced an unsafe magnitude")
        return numeric


class SemanticInventionSearch:
    def __init__(
        self, semantic: InventedSemantic, *, top_k: int = 300,
        executor: SemanticExtendedExecutor | None = None,
    ) -> None:
        self.semantic = semantic
        self.top_k = top_k
        self.executor = executor or SemanticExtendedExecutor()

    def search(self, observation: NumericTableObservation) -> ReflectiveSearchReport:
        valid = tuple(
            (row, float(output))
            for row, output, include in zip(
                observation.input_rows, observation.output_values,
                observation.validity_mask, strict=True,
            )
            if include
        )
        if not valid or len(valid[0][0]) != 9:
            raise ValueError("semantic invention search requires anonymous nine-column evidence")
        route_variants = _route_variants(4)
        candidates = []
        rejected = 0
        generated = 0
        for seeds in route_variants:
            for coefficients_relative in route_variants:
                coefficients = tuple(index + 4 for index in coefficients_relative)
                for sources_relative in route_variants:
                    sources = tuple(("a", "b", "c", "d")[index] for index in sources_relative)
                    for output in ("a", "b", "c", "d"):
                        generated += 1
                        program = _grow_fourth_order_program(
                            self.semantic, seeds, coefficients, sources, output
                        )
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
                        key = json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))
                        candidates.append(
                            ReflectiveCandidate(
                                "SI-" + hashlib.sha256(key.encode()).hexdigest()[:16],
                                program, sum(error * error for error in errors) / len(errors),
                                max(abs(error) for error in errors), tuple(outputs), tuple(outputs),
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
            len({item.outputs for item in candidates}), tuple(candidates[: self.top_k])
        )


def _micro_shape_occurrences(instructions: Sequence[tuple[int, int]]) -> int:
    count = 0
    for index in range(len(instructions) - len(MICRO_SHAPE) + 1):
        block = instructions[index : index + len(MICRO_SHAPE)]
        if tuple(opcode for opcode, _ in block) != MICRO_SHAPE:
            continue
        operands = tuple(operand for _, operand in block)
        if (
            operands[1] == operands[2] == operands[7] == operands[9]
            and operands[4] == operands[6]
            and operands[8] == 1
            and operands[10] < index + 10
        ):
            count += 1
    return count


def _route_variants(width: int) -> tuple[tuple[int, ...], ...]:
    identity = tuple(range(width))
    candidates = {
        identity,
        tuple(reversed(identity)),
        *(identity[shift:] + identity[:shift] for shift in range(1, width)),
        *(identity[:index] + (identity[index + 1], identity[index]) + identity[index + 2 :]
          for index in range(width - 1)),
    }
    return tuple(sorted(candidates))


def _encode_descriptor(coefficient_input: int, source_address: int, target_address: int) -> int:
    if not (0 <= coefficient_input < 100 and 0 <= source_address < 100 and 0 <= target_address < 100):
        raise ValueError("semantic descriptor field is out of range")
    return coefficient_input * 10_000 + source_address * 100 + target_address


def _decode_descriptor(operand: int) -> tuple[int, int, int]:
    if operand < 0:
        raise InvalidReflectiveProgram("semantic descriptor cannot be negative")
    return operand // 10_000, (operand // 100) % 100, operand % 100


def _assemble(entries, data, semantic: InventedSemantic) -> SemanticExtendedProgram:
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
            operand = (
                labels[operand]
                if opcode in (OP_JUMP, OP_JUMP_IF_ZERO, OP_JUMP_IF_NEGATIVE)
                else addresses[operand]
            )
        elif isinstance(operand, tuple):
            coefficient, source, target = operand
            operand = _encode_descriptor(coefficient, addresses[source], addresses[target])
        words.extend((opcode, operand))
    return SemanticExtendedProgram(tuple(words), semantic)


def _grow_fourth_order_program(
    semantic: InventedSemantic, seeds: tuple[int, ...], coefficients: tuple[int, ...],
    sources: tuple[str, ...], output: str,
) -> SemanticExtendedProgram:
    entries = [
        (OP_GROW, 6),
        (OP_LOAD_INPUT, 8), (OP_STORE_CELL, "counter"),
        (OP_LOAD_INPUT, seeds[0]), (OP_STORE_CELL, "a"),
        (OP_LOAD_INPUT, seeds[1]), (OP_STORE_CELL, "b"),
        (OP_LOAD_INPUT, seeds[2]), (OP_STORE_CELL, "c"),
        (OP_LOAD_INPUT, seeds[3]), (OP_STORE_CELL, "d"),
        "outer", (OP_LOAD_CELL, "counter"), (OP_JUMP_IF_ZERO, "end"),
        (OP_SET, 0), (OP_STORE_CELL, "next"),
    ]
    entries.extend(
        (semantic.opcode, (coefficient, source, "next"))
        for coefficient, source in zip(coefficients, sources, strict=True)
    )
    entries.extend(
        (
            (OP_LOAD_CELL, "b"), (OP_STORE_CELL, "a"),
            (OP_LOAD_CELL, "c"), (OP_STORE_CELL, "b"),
            (OP_LOAD_CELL, "d"), (OP_STORE_CELL, "c"),
            (OP_LOAD_CELL, "next"), (OP_STORE_CELL, "d"),
            (OP_LOAD_CELL, "counter"), (OP_SUB_IMMEDIATE, 1),
            (OP_STORE_CELL, "counter"), (OP_JUMP, "outer"),
            "end", (OP_LOAD_CELL, output), (OP_EMIT, 0), (OP_HALT, 0),
        )
    )
    return _assemble(entries, ("counter", "a", "b", "c", "d", "next"), semantic)


def _integer(value: float, label: str) -> int:
    if not float(value).is_integer():
        raise InvalidReflectiveProgram(f"runtime {label} is not an integer")
    return int(value)
