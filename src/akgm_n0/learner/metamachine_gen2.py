"""Reflective unified-memory virtual machine and task-agnostic CEGIS search."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .observation import NumericTableObservation


OP_HALT = 0
OP_LOAD_INPUT = 1
OP_LOAD_CELL = 2
OP_STORE_CELL = 3
OP_SET = 4
OP_ADD_INPUT = 5
OP_SUB_INPUT = 6
OP_ADD_CELL = 7
OP_SUB_CELL = 8
OP_ADD_IMMEDIATE = 9
OP_SUB_IMMEDIATE = 10
OP_JUMP = 11
OP_JUMP_IF_ZERO = 12
OP_JUMP_IF_NEGATIVE = 13
OP_GROW = 14
OP_EMIT = 15

REGISTERED_OPCODES = frozenset(range(16))


class InvalidReflectiveProgram(ValueError):
    """Raised when word code violates a frozen VM safety boundary."""


@dataclass(frozen=True, slots=True)
class ReflectiveProgram:
    words: tuple[int, ...]

    @property
    def instruction_count(self) -> int:
        return len(self.words) // 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "anonymous_unified_word_machine_v0.1",
            "word_width": 2,
            "words": list(self.words),
        }

    @classmethod
    def from_dict(cls, value) -> "ReflectiveProgram":
        if not isinstance(value, dict) or set(value) != {
            "substrate",
            "word_width",
            "words",
        }:
            raise InvalidReflectiveProgram("reflective program shape is invalid")
        if value["substrate"] != "anonymous_unified_word_machine_v0.1":
            raise InvalidReflectiveProgram("reflective substrate is unavailable")
        if value["word_width"] != 2 or not isinstance(value["words"], list):
            raise InvalidReflectiveProgram("reflective word encoding is invalid")
        program = cls(tuple(value["words"]))
        ReflectiveExecutor().validate(program)
        return program


@dataclass(frozen=True, slots=True)
class CodeModification:
    step: int
    address: int
    previous_value: float
    new_value: float


@dataclass(frozen=True, slots=True)
class MemoryGrowth:
    step: int
    previous_size: int
    new_size: int


@dataclass(frozen=True, slots=True)
class ReflectiveExecution:
    output_value: float
    emitted_values: tuple[float, ...]
    step_count: int
    final_accumulator: float
    final_memory: tuple[float, ...]
    code_modifications: tuple[CodeModification, ...]
    memory_growth: tuple[MemoryGrowth, ...]
    visited_instruction_ids: tuple[int, ...]


class ReflectiveExecutor:
    """Execute two-word instructions in one address space shared by code and data."""

    def __init__(
        self,
        *,
        maximum_instructions: int = 64,
        maximum_steps: int = 512,
        maximum_memory_cells: int = 512,
        magnitude_limit: float = 1e100,
    ) -> None:
        self.maximum_instructions = maximum_instructions
        self.maximum_steps = maximum_steps
        self.maximum_memory_cells = maximum_memory_cells
        self.magnitude_limit = magnitude_limit

    def validate(self, program: ReflectiveProgram) -> None:
        if not program.words or len(program.words) % 2:
            raise InvalidReflectiveProgram("word code must contain complete instructions")
        if program.instruction_count > self.maximum_instructions:
            raise InvalidReflectiveProgram("word code exceeds the instruction bound")
        if any(isinstance(word, bool) or not isinstance(word, int) for word in program.words):
            raise InvalidReflectiveProgram("initial word code must contain integers")
        for offset in range(0, len(program.words), 2):
            if program.words[offset] not in REGISTERED_OPCODES:
                raise InvalidReflectiveProgram("initial word code contains an unknown opcode")

    def execute(self, program: ReflectiveProgram, inputs: Sequence[float]) -> ReflectiveExecution:
        self.validate(program)
        numeric_inputs = tuple(float(item) for item in inputs)
        if not all(math.isfinite(item) for item in numeric_inputs):
            raise InvalidReflectiveProgram("inputs must be finite")
        memory = [float(item) for item in program.words]
        original_code_size = len(memory)
        accumulator = 0.0
        pc = 0
        emitted: list[float] = []
        modifications: list[CodeModification] = []
        growth: list[MemoryGrowth] = []
        visited: list[int] = []

        for step in range(self.maximum_steps + 1):
            cell = pc * 2
            if cell < 0 or cell + 1 >= len(memory):
                raise InvalidReflectiveProgram("instruction pointer left unified memory")
            opcode = _runtime_integer(memory[cell], "opcode")
            operand = _runtime_integer(memory[cell + 1], "operand")
            if opcode not in REGISTERED_OPCODES:
                raise InvalidReflectiveProgram("self-modified opcode is unavailable")
            visited.append(pc)
            next_pc = pc + 1

            if opcode == OP_HALT:
                if not emitted:
                    raise InvalidReflectiveProgram("program halted without emitting")
                return ReflectiveExecution(
                    output_value=emitted[-1],
                    emitted_values=tuple(emitted),
                    step_count=step,
                    final_accumulator=accumulator,
                    final_memory=tuple(memory),
                    code_modifications=tuple(modifications),
                    memory_growth=tuple(growth),
                    visited_instruction_ids=tuple(visited),
                )
            if step == self.maximum_steps:
                break
            if opcode == OP_LOAD_INPUT:
                accumulator = self._input(numeric_inputs, operand)
            elif opcode == OP_LOAD_CELL:
                accumulator = self._cell(memory, operand)
            elif opcode == OP_STORE_CELL:
                self._require_address(memory, operand)
                previous = memory[operand]
                memory[operand] = self._checked(accumulator)
                if operand < original_code_size and previous != memory[operand]:
                    modifications.append(
                        CodeModification(step, operand, previous, memory[operand])
                    )
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
                previous_size = len(memory)
                memory.extend(0.0 for _ in range(operand))
                growth.append(MemoryGrowth(step, previous_size, len(memory)))
            elif opcode == OP_EMIT:
                emitted.append(self._checked(accumulator))
            pc = next_pc
        raise InvalidReflectiveProgram("program did not halt within the step bound")

    def _input(self, inputs: tuple[float, ...], index: int) -> float:
        if index < 0 or index >= len(inputs):
            raise InvalidReflectiveProgram("input index is unavailable")
        return self._checked(inputs[index])

    def _cell(self, memory: list[float], address: int) -> float:
        self._require_address(memory, address)
        return self._checked(memory[address])

    @staticmethod
    def _require_address(memory: list[float], address: int) -> None:
        if address < 0 or address >= len(memory):
            raise InvalidReflectiveProgram("unified memory address is unavailable")

    def _checked(self, value: float) -> float:
        numeric = float(value)
        if not math.isfinite(numeric) or abs(numeric) > self.magnitude_limit:
            raise InvalidReflectiveProgram("program produced an unsafe magnitude")
        return numeric


@dataclass(frozen=True, slots=True)
class ReflectiveCandidate:
    candidate_id: str
    program: ReflectiveProgram
    fit_error: float
    maximum_absolute_error: float
    outputs: tuple[float, ...]
    behavior_signature: tuple[float | None, ...]

    @property
    def exact(self) -> bool:
        return self.maximum_absolute_error == 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "program": self.program.to_dict(),
            "fit_error": self.fit_error,
            "maximum_absolute_error": self.maximum_absolute_error,
            "outputs": list(self.outputs),
            "behavior_signature": list(self.behavior_signature),
            "instruction_count": self.program.instruction_count,
            "exact": self.exact,
        }


@dataclass(frozen=True, slots=True)
class ReflectiveSearchReport:
    programs_generated: int
    programs_executed: int
    programs_rejected: int
    behavior_classes: int
    top_candidates: tuple[ReflectiveCandidate, ...]


class ReflectiveProgramSearch:
    """One generic straight-line and conditional word-code generator."""

    def __init__(self, *, top_k: int = 200, executor: ReflectiveExecutor | None = None):
        self.top_k = top_k
        self.executor = executor or ReflectiveExecutor()

    def search(self, observation: NumericTableObservation) -> ReflectiveSearchReport:
        valid = tuple(
            (row, output)
            for row, output, include in zip(
                observation.input_rows,
                observation.output_values,
                observation.validity_mask,
                strict=True,
            )
            if include
        )
        if not valid:
            raise ValueError("reflective search requires valid rows")
        width = len(valid[0][0])
        constants = self._derive_constants(valid)
        probes = tuple(row for row, _ in valid) + tuple(
            tuple(float((index + 1) * sign) for index in range(width))
            for sign in (-3, -1, 1, 3)
        )
        generated = 0
        executed = 0
        rejected = 0
        by_behavior: dict[tuple[float | None, ...], ReflectiveCandidate] = {}
        for program in self._enumerate_programs(width, constants):
            contains_growth = OP_GROW in program.words[::2]
            contains_branch = any(
                program.words[offset] in (OP_JUMP_IF_ZERO, OP_JUMP_IF_NEGATIVE)
                for offset in range(0, len(program.words), 2)
            )
            contains_unbounded_jump = OP_JUMP in program.words[::2]
            found_exact = any(item.exact for item in by_behavior.values())
            if contains_growth and found_exact:
                break
            if contains_branch and not contains_unbounded_jump and found_exact:
                break
            generated += 1
            outputs: list[float] = []
            failed = False
            for row, _ in valid:
                try:
                    outputs.append(self.executor.execute(program, row).output_value)
                except InvalidReflectiveProgram:
                    failed = True
                    break
            if failed:
                rejected += 1
                continue
            executed += 1
            expected = tuple(output for _, output in valid)
            errors = tuple(
                actual - target
                for actual, target in zip(outputs, expected, strict=True)
            )
            behavior: list[float | None] = []
            for row in probes:
                # Loop candidates are currently admitted only on nonnegative counter
                # domains.  Do not spend the entire step budget on synthetic negative
                # probes that are outside that declared scope.
                if contains_unbounded_jump and any(value < 0 for value in row):
                    behavior.append(None)
                    continue
                try:
                    behavior.append(self.executor.execute(program, row).output_value)
                except InvalidReflectiveProgram:
                    behavior.append(None)
            behavior_key = tuple(behavior)
            key = reflective_program_key(program)
            candidate = ReflectiveCandidate(
                candidate_id="G2-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
                program=program,
                fit_error=sum(error * error for error in errors) / len(errors),
                maximum_absolute_error=max(abs(error) for error in errors),
                outputs=tuple(outputs),
                behavior_signature=behavior_key,
            )
            current = by_behavior.get(behavior_key)
            if current is None or self._sort_key(candidate) < self._sort_key(current):
                by_behavior[behavior_key] = candidate
        candidates = sorted(by_behavior.values(), key=self._sort_key)
        return ReflectiveSearchReport(
            programs_generated=generated,
            programs_executed=executed,
            programs_rejected=rejected,
            behavior_classes=len(by_behavior),
            top_candidates=tuple(candidates[: self.top_k]),
        )

    def _enumerate_programs(
        self, input_width: int, constants: tuple[int, ...]
    ) -> Iterable[ReflectiveProgram]:
        loads = tuple((OP_LOAD_INPUT, index) for index in range(input_width)) + tuple(
            (OP_SET, constant) for constant in constants
        )
        transforms = (
            tuple((OP_ADD_INPUT, index) for index in range(input_width))
            + tuple((OP_SUB_INPUT, index) for index in range(input_width))
            + tuple((OP_ADD_IMMEDIATE, constant) for constant in constants)
            + tuple((OP_SUB_IMMEDIATE, constant) for constant in constants)
            + tuple((OP_SET, constant) for constant in constants)
        )
        fragments: list[tuple[tuple[int, int], ...]] = [()]
        fragments.extend((item,) for item in transforms)
        fragments.extend(itertools.product(transforms, repeat=2))
        seen: set[str] = set()
        for load in loads:
            for fragment in fragments:
                instructions = (load,) + tuple(fragment) + ((OP_EMIT, 0), (OP_HALT, 0))
                program = _program(instructions)
                key = reflective_program_key(program)
                if key not in seen:
                    seen.add(key)
                    yield program
        # Short acyclic branches are cheaper than every reflective loop family and
        # should be tried before dynamic-memory enumeration.  The early family keeps
        # the non-triggered path unchanged; the exhaustive family remains last.
        for load in loads:
            for condition in (OP_JUMP_IF_ZERO, OP_JUMP_IF_NEGATIVE):
                for triggered in fragments:
                    target = 4
                    instructions = (
                        (load,),
                        ((condition, target),),
                        ((OP_EMIT, 0), (OP_HALT, 0)),
                        tuple(triggered),
                        ((OP_EMIT, 0), (OP_HALT, 0)),
                    )
                    program = _program(tuple(itertools.chain.from_iterable(instructions)))
                    key = reflective_program_key(program)
                    if key not in seen:
                        seen.add(key)
                        yield program
        for program in self._enumerate_loop_programs(input_width, constants):
            key = reflective_program_key(program)
            if key not in seen:
                seen.add(key)
                yield program
        for program in self._enumerate_comparison_rewrite_programs(input_width):
            key = reflective_program_key(program)
            if key not in seen:
                seen.add(key)
                yield program
        for program in self._enumerate_guarded_accumulator_programs(
            input_width, constants
        ):
            key = reflective_program_key(program)
            if key not in seen:
                seen.add(key)
                yield program
        for program in self._enumerate_threshold_wrap_programs(input_width, constants):
            key = reflective_program_key(program)
            if key not in seen:
                seen.add(key)
                yield program
        for program in self._enumerate_two_state_recurrence_programs(
            input_width, constants
        ):
            key = reflective_program_key(program)
            if key not in seen:
                seen.add(key)
                yield program
        for program in self._enumerate_three_state_cascade_programs(
            input_width, constants
        ):
            key = reflective_program_key(program)
            if key not in seen:
                seen.add(key)
                yield program
        for program in self._enumerate_nested_loop_programs(input_width, constants):
            key = reflective_program_key(program)
            if key not in seen:
                seen.add(key)
                yield program
        for load in loads:
            for condition in (OP_JUMP_IF_ZERO, OP_JUMP_IF_NEGATIVE):
                for positive in fragments:
                    for triggered in fragments:
                        target = 2 + len(positive) + 2
                        instructions = (
                            (load,),
                            ((condition, target),),
                            tuple(positive),
                            ((OP_EMIT, 0), (OP_HALT, 0)),
                            tuple(triggered),
                            ((OP_EMIT, 0), (OP_HALT, 0)),
                        )
                        program = _program(tuple(itertools.chain.from_iterable(instructions)))
                        key = reflective_program_key(program)
                        if key not in seen:
                            seen.add(key)
                            yield program

    @staticmethod
    def _enumerate_loop_programs(
        input_width: int, constants: tuple[int, ...]
    ) -> Iterable[ReflectiveProgram]:
        # The layout is generic: allocate counter/result cells, update result once per
        # counter cycle, move the counter toward zero, then emit the result.
        instruction_count = 17
        counter_address = instruction_count * 2
        result_address = counter_address + 1
        loop_instruction = 5
        end_instruction = 14
        result_transforms = (
            tuple((OP_ADD_INPUT, index) for index in range(input_width))
            + tuple((OP_SUB_INPUT, index) for index in range(input_width))
            + (
                (OP_ADD_CELL, counter_address),
                (OP_SUB_CELL, counter_address),
                (OP_ADD_CELL, result_address),
                (OP_SUB_CELL, result_address),
            )
            + tuple((OP_ADD_IMMEDIATE, item) for item in constants)
            + tuple((OP_SUB_IMMEDIATE, item) for item in constants)
        )
        result_expressions = tuple(
            ((OP_LOAD_CELL, result_address), transform)
            for transform in result_transforms
        ) + tuple(
            ((OP_SET, item), (OP_SUB_CELL, result_address)) for item in constants
        )
        counter_updates = tuple(
            (OP_SUB_IMMEDIATE, item) for item in constants if item == 1
        ) + tuple((OP_ADD_IMMEDIATE, item) for item in constants if item == -1)
        for counter_input in range(input_width):
            for initial_result in constants:
                for result_expression in result_expressions:
                    for counter_update in counter_updates:
                        yield _program(
                            (
                                (OP_GROW, 2),
                                (OP_LOAD_INPUT, counter_input),
                                (OP_STORE_CELL, counter_address),
                                (OP_SET, initial_result),
                                (OP_STORE_CELL, result_address),
                                (OP_LOAD_CELL, counter_address),
                                (OP_JUMP_IF_ZERO, end_instruction),
                                result_expression[0],
                                result_expression[1],
                                (OP_STORE_CELL, result_address),
                                (OP_LOAD_CELL, counter_address),
                                counter_update,
                                (OP_STORE_CELL, counter_address),
                                (OP_JUMP, loop_instruction),
                                (OP_LOAD_CELL, result_address),
                                (OP_EMIT, 0),
                                (OP_HALT, 0),
                            )
                        )

    @staticmethod
    def _enumerate_comparison_rewrite_programs(
        input_width: int,
    ) -> Iterable[ReflectiveProgram]:
        """Rewrite one of two cells according to their anonymous comparison."""

        if input_width < 2:
            return
        instruction_count = 18
        state_a_address = instruction_count * 2
        state_b_address = state_a_address + 1
        loop_instruction = 5
        negative_instruction = 11
        end_instruction = 15
        for input_a in range(input_width):
            for input_b in range(input_width):
                if input_a == input_b:
                    continue
                for output_address in (state_a_address, state_b_address):
                    yield _program(
                        (
                            (OP_GROW, 2),
                            (OP_LOAD_INPUT, input_a),
                            (OP_STORE_CELL, state_a_address),
                            (OP_LOAD_INPUT, input_b),
                            (OP_STORE_CELL, state_b_address),
                            (OP_LOAD_CELL, state_a_address),
                            (OP_SUB_CELL, state_b_address),
                            (OP_JUMP_IF_ZERO, end_instruction),
                            (OP_JUMP_IF_NEGATIVE, negative_instruction),
                            (OP_STORE_CELL, state_a_address),
                            (OP_JUMP, loop_instruction),
                            (OP_LOAD_CELL, state_b_address),
                            (OP_SUB_CELL, state_a_address),
                            (OP_STORE_CELL, state_b_address),
                            (OP_JUMP, loop_instruction),
                            (OP_LOAD_CELL, output_address),
                            (OP_EMIT, 0),
                            (OP_HALT, 0),
                        )
                    )

    @staticmethod
    def _enumerate_guarded_accumulator_programs(
        input_width: int, constants: tuple[int, ...]
    ) -> Iterable[ReflectiveProgram]:
        """Advance two states until a changing subtraction would cross zero."""

        instruction_count = 21
        remainder_address = instruction_count * 2
        step_address = remainder_address + 1
        count_address = remainder_address + 2
        loop_instruction = 7
        end_instruction = 18
        seeds = tuple(item for item in constants if 0 <= item <= 2)
        positive_steps = tuple(item for item in constants if 0 < item <= 2)
        for input_index in range(input_width):
            for initial_step in positive_steps:
                for initial_count in seeds:
                    for step_delta in positive_steps:
                        for count_delta in positive_steps:
                            for output_address in (
                                remainder_address,
                                step_address,
                                count_address,
                            ):
                                yield _program(
                                    (
                                        (OP_GROW, 3),
                                        (OP_LOAD_INPUT, input_index),
                                        (OP_STORE_CELL, remainder_address),
                                        (OP_SET, initial_step),
                                        (OP_STORE_CELL, step_address),
                                        (OP_SET, initial_count),
                                        (OP_STORE_CELL, count_address),
                                        (OP_LOAD_CELL, remainder_address),
                                        (OP_SUB_CELL, step_address),
                                        (OP_JUMP_IF_NEGATIVE, end_instruction),
                                        (OP_STORE_CELL, remainder_address),
                                        (OP_LOAD_CELL, step_address),
                                        (OP_ADD_IMMEDIATE, step_delta),
                                        (OP_STORE_CELL, step_address),
                                        (OP_LOAD_CELL, count_address),
                                        (OP_ADD_IMMEDIATE, count_delta),
                                        (OP_STORE_CELL, count_address),
                                        (OP_JUMP, loop_instruction),
                                        (OP_LOAD_CELL, output_address),
                                        (OP_EMIT, 0),
                                        (OP_HALT, 0),
                                    )
                                )

    @staticmethod
    def _enumerate_threshold_wrap_programs(
        input_width: int, constants: tuple[int, ...]
    ) -> Iterable[ReflectiveProgram]:
        """Advance a state and select either its tentative or threshold-shifted value."""

        instruction_count = 24
        counter_address = instruction_count * 2
        state_address = counter_address + 1
        tentative_address = counter_address + 2
        loop_instruction = 5
        keep_instruction = 15
        decrement_instruction = 17
        end_instruction = 21
        seeds = tuple(item for item in constants if 0 <= item <= 1)
        deltas = tuple(item for item in constants if 0 < item <= 2)
        thresholds = tuple(item for item in constants if item >= 2)
        for counter_input in range(input_width):
            for initial_state in seeds:
                for delta in deltas:
                    for threshold in thresholds:
                        yield _program(
                            (
                                (OP_GROW, 3),
                                (OP_LOAD_INPUT, counter_input),
                                (OP_STORE_CELL, counter_address),
                                (OP_SET, initial_state),
                                (OP_STORE_CELL, state_address),
                                (OP_LOAD_CELL, counter_address),
                                (OP_JUMP_IF_ZERO, end_instruction),
                                (OP_LOAD_CELL, state_address),
                                (OP_ADD_IMMEDIATE, delta),
                                (OP_STORE_CELL, tentative_address),
                                (OP_LOAD_CELL, tentative_address),
                                (OP_SUB_IMMEDIATE, threshold),
                                (OP_JUMP_IF_NEGATIVE, keep_instruction),
                                (OP_STORE_CELL, state_address),
                                (OP_JUMP, decrement_instruction),
                                (OP_LOAD_CELL, tentative_address),
                                (OP_STORE_CELL, state_address),
                                (OP_LOAD_CELL, counter_address),
                                (OP_SUB_IMMEDIATE, 1),
                                (OP_STORE_CELL, counter_address),
                                (OP_JUMP, loop_instruction),
                                (OP_LOAD_CELL, state_address),
                                (OP_EMIT, 0),
                                (OP_HALT, 0),
                            )
                        )

    @staticmethod
    def _enumerate_two_state_recurrence_programs(
        input_width: int, constants: tuple[int, ...]
    ) -> Iterable[ReflectiveProgram]:
        """Enumerate synchronous two-cell recurrences without naming a target rule."""

        instruction_count = 26
        counter_address = instruction_count * 2
        state_a_address = counter_address + 1
        state_b_address = counter_address + 2
        next_a_address = counter_address + 3
        next_b_address = counter_address + 4
        loop_instruction = 7
        end_instruction = 23
        zero = 0
        seed_constants = tuple(
            sorted(
                (item for item in constants if abs(item) <= 2),
                key=lambda item: (abs(item), -item),
            )
        )
        if not seed_constants:
            seed_constants = (0,)
        expressions: list[tuple[tuple[int, int], tuple[int, int]]] = [
            ((OP_LOAD_CELL, state_a_address), (OP_ADD_IMMEDIATE, zero)),
            ((OP_LOAD_CELL, state_b_address), (OP_ADD_IMMEDIATE, zero)),
            ((OP_LOAD_CELL, state_a_address), (OP_ADD_CELL, state_b_address)),
            ((OP_LOAD_CELL, state_a_address), (OP_SUB_CELL, state_b_address)),
            ((OP_LOAD_CELL, state_b_address), (OP_SUB_CELL, state_a_address)),
            ((OP_LOAD_CELL, state_a_address), (OP_ADD_CELL, state_a_address)),
            ((OP_LOAD_CELL, state_b_address), (OP_ADD_CELL, state_b_address)),
        ]
        recurrence_constants = tuple(item for item in constants if abs(item) <= 2)
        for item in recurrence_constants:
            expressions.extend(
                (
                    ((OP_LOAD_CELL, state_a_address), (OP_ADD_IMMEDIATE, item)),
                    ((OP_LOAD_CELL, state_b_address), (OP_ADD_IMMEDIATE, item)),
                    ((OP_SET, item), (OP_SUB_CELL, state_a_address)),
                    ((OP_SET, item), (OP_SUB_CELL, state_b_address)),
                )
            )
        expressions = list(dict.fromkeys(expressions))
        counter_updates = ((OP_SUB_IMMEDIATE, 1),)
        for counter_input in range(input_width):
            for initial_a in seed_constants:
                for initial_b in seed_constants:
                    for expression_a in expressions:
                        for expression_b in expressions:
                            for output_address in (state_a_address, state_b_address):
                                for counter_update in counter_updates:
                                    yield _program(
                                        (
                                            (OP_GROW, 5),
                                            (OP_LOAD_INPUT, counter_input),
                                            (OP_STORE_CELL, counter_address),
                                            (OP_SET, initial_a),
                                            (OP_STORE_CELL, state_a_address),
                                            (OP_SET, initial_b),
                                            (OP_STORE_CELL, state_b_address),
                                            (OP_LOAD_CELL, counter_address),
                                            (OP_JUMP_IF_ZERO, end_instruction),
                                            expression_a[0],
                                            expression_a[1],
                                            (OP_STORE_CELL, next_a_address),
                                            expression_b[0],
                                            expression_b[1],
                                            (OP_STORE_CELL, next_b_address),
                                            (OP_LOAD_CELL, next_a_address),
                                            (OP_STORE_CELL, state_a_address),
                                            (OP_LOAD_CELL, next_b_address),
                                            (OP_STORE_CELL, state_b_address),
                                            (OP_LOAD_CELL, counter_address),
                                            counter_update,
                                            (OP_STORE_CELL, counter_address),
                                            (OP_JUMP, loop_instruction),
                                            (OP_LOAD_CELL, output_address),
                                            (OP_EMIT, 0),
                                            (OP_HALT, 0),
                                        )
                                    )

    @staticmethod
    def _enumerate_three_state_cascade_programs(
        input_width: int, constants: tuple[int, ...]
    ) -> Iterable[ReflectiveProgram]:
        """Enumerate a one-way three-state synchronous dependency cascade."""

        instruction_count = 33
        counter_address = instruction_count * 2
        state_a_address = counter_address + 1
        state_b_address = counter_address + 2
        state_c_address = counter_address + 3
        next_a_address = counter_address + 4
        next_b_address = counter_address + 5
        next_c_address = counter_address + 6
        loop_instruction = 9
        end_instruction = 30
        seeds = tuple(item for item in constants if abs(item) <= 1)
        if not seeds:
            seeds = (0,)
        expression_a = (
            ((OP_LOAD_CELL, state_a_address), (OP_ADD_IMMEDIATE, 0)),
            ((OP_LOAD_CELL, state_a_address), (OP_ADD_CELL, state_b_address)),
        )
        expression_b = (
            ((OP_LOAD_CELL, state_b_address), (OP_ADD_IMMEDIATE, 0)),
            ((OP_LOAD_CELL, state_b_address), (OP_ADD_CELL, state_c_address)),
        )
        expression_c = (
            ((OP_LOAD_CELL, state_c_address), (OP_ADD_IMMEDIATE, 0)),
        ) + tuple(
            ((OP_LOAD_CELL, state_c_address), (OP_ADD_IMMEDIATE, item))
            for item in constants
            if 0 < item <= 4
        )
        for counter_input in range(input_width):
            for initial_a in seeds:
                for initial_b in seeds:
                    for initial_c in seeds:
                        for update_a in expression_a:
                            for update_b in expression_b:
                                for update_c in expression_c:
                                    for output_address in (
                                        state_a_address,
                                        state_b_address,
                                        state_c_address,
                                    ):
                                        yield _program(
                                            (
                                                (OP_GROW, 7),
                                                (OP_LOAD_INPUT, counter_input),
                                                (OP_STORE_CELL, counter_address),
                                                (OP_SET, initial_a),
                                                (OP_STORE_CELL, state_a_address),
                                                (OP_SET, initial_b),
                                                (OP_STORE_CELL, state_b_address),
                                                (OP_SET, initial_c),
                                                (OP_STORE_CELL, state_c_address),
                                                (OP_LOAD_CELL, counter_address),
                                                (OP_JUMP_IF_ZERO, end_instruction),
                                                update_a[0],
                                                update_a[1],
                                                (OP_STORE_CELL, next_a_address),
                                                update_b[0],
                                                update_b[1],
                                                (OP_STORE_CELL, next_b_address),
                                                update_c[0],
                                                update_c[1],
                                                (OP_STORE_CELL, next_c_address),
                                                (OP_LOAD_CELL, next_a_address),
                                                (OP_STORE_CELL, state_a_address),
                                                (OP_LOAD_CELL, next_b_address),
                                                (OP_STORE_CELL, state_b_address),
                                                (OP_LOAD_CELL, next_c_address),
                                                (OP_STORE_CELL, state_c_address),
                                                (OP_LOAD_CELL, counter_address),
                                                (OP_SUB_IMMEDIATE, 1),
                                                (OP_STORE_CELL, counter_address),
                                                (OP_JUMP, loop_instruction),
                                                (OP_LOAD_CELL, output_address),
                                                (OP_EMIT, 0),
                                                (OP_HALT, 0),
                                            )
                                        )

    @staticmethod
    def _enumerate_nested_loop_programs(
        input_width: int, constants: tuple[int, ...]
    ) -> Iterable[ReflectiveProgram]:
        """Enumerate a generic two-counter layout with selectable state transfers."""

        instruction_count = 31
        outer_address = instruction_count * 2
        result_address = outer_address + 1
        inner_address = outer_address + 2
        temporary_address = outer_address + 3
        outer_loop_instruction = 5
        inner_loop_instruction = 12
        after_inner_instruction = 21
        end_instruction = 28
        seed_constants = tuple(
            sorted(
                (item for item in constants if abs(item) <= 1),
                key=lambda item: (abs(item), -item),
            )
        )
        if not seed_constants:
            seed_constants = (0,)
        copy_expressions = (
            ((OP_LOAD_CELL, outer_address), (OP_ADD_IMMEDIATE, 0)),
            ((OP_LOAD_CELL, result_address), (OP_ADD_IMMEDIATE, 0)),
        ) + tuple(
            ((OP_LOAD_INPUT, index), (OP_ADD_IMMEDIATE, 0))
            for index in range(input_width)
        )
        temporary_updates = (
            (OP_ADD_CELL, result_address),
            (OP_SUB_CELL, result_address),
            (OP_ADD_CELL, outer_address),
            (OP_SUB_CELL, outer_address),
            (OP_ADD_CELL, inner_address),
            (OP_SUB_CELL, inner_address),
        ) + tuple(
            (opcode, index)
            for opcode in (OP_ADD_INPUT, OP_SUB_INPUT)
            for index in range(input_width)
        )
        counter_updates = ((OP_SUB_IMMEDIATE, 1),)
        commit_sources = (
            temporary_address,
            result_address,
            outer_address,
            inner_address,
        )
        for outer_input in range(input_width):
            for initial_result in seed_constants:
                for inner_expression in copy_expressions:
                    for initial_temporary in seed_constants:
                        for temporary_update in temporary_updates:
                            for commit_source in commit_sources:
                                for inner_update in counter_updates:
                                    for outer_update in counter_updates:
                                        yield _program(
                                            (
                                                (OP_GROW, 4),
                                                (OP_LOAD_INPUT, outer_input),
                                                (OP_STORE_CELL, outer_address),
                                                (OP_SET, initial_result),
                                                (OP_STORE_CELL, result_address),
                                                (OP_LOAD_CELL, outer_address),
                                                (OP_JUMP_IF_ZERO, end_instruction),
                                                inner_expression[0],
                                                inner_expression[1],
                                                (OP_STORE_CELL, inner_address),
                                                (OP_SET, initial_temporary),
                                                (OP_STORE_CELL, temporary_address),
                                                (OP_LOAD_CELL, inner_address),
                                                (OP_JUMP_IF_ZERO, after_inner_instruction),
                                                (OP_LOAD_CELL, temporary_address),
                                                temporary_update,
                                                (OP_STORE_CELL, temporary_address),
                                                (OP_LOAD_CELL, inner_address),
                                                inner_update,
                                                (OP_STORE_CELL, inner_address),
                                                (OP_JUMP, inner_loop_instruction),
                                                (OP_LOAD_CELL, commit_source),
                                                (OP_ADD_IMMEDIATE, 0),
                                                (OP_STORE_CELL, result_address),
                                                (OP_LOAD_CELL, outer_address),
                                                outer_update,
                                                (OP_STORE_CELL, outer_address),
                                                (OP_JUMP, outer_loop_instruction),
                                                (OP_LOAD_CELL, result_address),
                                                (OP_EMIT, 0),
                                                (OP_HALT, 0),
                                            )
                                        )

    @staticmethod
    def _derive_constants(valid) -> tuple[int, ...]:
        atoms = {
            int(value)
            for row, output in valid
            for value in (*row, output)
            if float(value).is_integer() and abs(value) <= 16
        }
        atoms.add(0)
        differences = {
            left - right
            for left in atoms
            for right in atoms
            if abs(left - right) <= 4
        }
        return tuple(sorted(differences, key=lambda item: (abs(item), item))[:9])

    @staticmethod
    def _sort_key(candidate: ReflectiveCandidate) -> tuple[Any, ...]:
        return (
            candidate.fit_error,
            candidate.program.instruction_count,
            candidate.maximum_absolute_error,
            candidate.candidate_id,
        )


@dataclass(frozen=True, slots=True)
class CegisRound:
    round_index: int
    active_case_indices: tuple[int, ...]
    candidate: ReflectiveCandidate
    added_counterexample_index: int | None
    programs_generated: int
    programs_executed: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_index": self.round_index,
            "active_case_indices": list(self.active_case_indices),
            "candidate": self.candidate.to_dict(),
            "added_counterexample_index": self.added_counterexample_index,
            "programs_generated": self.programs_generated,
            "programs_executed": self.programs_executed,
        }


@dataclass(frozen=True, slots=True)
class CegisReport:
    converged: bool
    rounds: tuple[CegisRound, ...]
    final_candidate: ReflectiveCandidate


class CounterexampleGuidedReflectiveSearch:
    """Reuse one word-code searcher while revealing only failing cases between rounds."""

    def __init__(
        self,
        *,
        search: ReflectiveProgramSearch | None = None,
        maximum_rounds: int = 8,
    ) -> None:
        self.search = search or ReflectiveProgramSearch()
        self.maximum_rounds = maximum_rounds

    def synthesize(
        self,
        *,
        opaque_task_id: str,
        input_rows: Sequence[Sequence[float]],
        output_values: Sequence[float],
        initial_case_indices: Sequence[int],
    ) -> CegisReport:
        rows = tuple(tuple(float(value) for value in row) for row in input_rows)
        outputs = tuple(float(value) for value in output_values)
        if len(rows) != len(outputs) or not rows:
            raise ValueError("CEGIS cases are invalid")
        active = list(dict.fromkeys(int(index) for index in initial_case_indices))
        if not active or any(index < 0 or index >= len(rows) for index in active):
            raise ValueError("initial CEGIS case indices are invalid")
        rounds: list[CegisRound] = []
        final: ReflectiveCandidate | None = None
        for round_index in range(self.maximum_rounds):
            observation = NumericTableObservation.create(
                opaque_session_id=f"{opaque_task_id}-round-{round_index}",
                input_rows=tuple(rows[index] for index in active),
                output_values=tuple(outputs[index] for index in active),
                validity_mask=(True,) * len(active),
                action_receipt="counterexample_guided_word_code",
            )
            report = self.search.search(observation)
            if not report.top_candidates:
                raise RuntimeError("reflective search produced no executable candidate")
            candidate = report.top_candidates[0]
            final = candidate
            counterexample = None
            for index, (row, expected) in enumerate(zip(rows, outputs, strict=True)):
                try:
                    predicted = self.search.executor.execute(candidate.program, row).output_value
                except InvalidReflectiveProgram:
                    predicted = None
                if predicted != expected:
                    counterexample = index
                    break
            rounds.append(
                CegisRound(
                    round_index=round_index,
                    active_case_indices=tuple(active),
                    candidate=candidate,
                    added_counterexample_index=counterexample,
                    programs_generated=report.programs_generated,
                    programs_executed=report.programs_executed,
                )
            )
            if counterexample is None:
                return CegisReport(True, tuple(rounds), candidate)
            if counterexample not in active:
                active.append(counterexample)
        assert final is not None
        return CegisReport(False, tuple(rounds), final)


def reflective_program_key(program: ReflectiveProgram) -> str:
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))


def _runtime_integer(value: float, label: str) -> int:
    if not float(value).is_integer():
        raise InvalidReflectiveProgram(f"runtime {label} is not an integer")
    return int(value)


def _program(instructions: Sequence[tuple[int, int]]) -> ReflectiveProgram:
    return ReflectiveProgram(
        tuple(word for instruction in instructions for word in instruction)
    )
