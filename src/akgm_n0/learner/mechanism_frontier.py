"""Small task-agnostic frontier of reflective mechanism grammars.

The generator receives only anonymous numeric tables.  It enumerates parameterized
word-machine mechanisms and ranks their observed behavior; it contains no formula
names or theorem labels.
"""

from __future__ import annotations

import hashlib
import itertools
from typing import Iterable

from .metamachine_gen2 import (
    InvalidReflectiveProgram,
    ReflectiveCandidate,
    ReflectiveExecutor,
    ReflectiveProgram,
    ReflectiveSearchReport,
    OP_ADD_CELL,
    OP_ADD_IMMEDIATE,
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
    reflective_program_key,
)
from .observation import NumericTableObservation


class MechanismFrontierSearch:
    """Rank programs from five generic memory/control mechanism families."""

    def __init__(self, *, top_k: int = 200, executor: ReflectiveExecutor | None = None):
        self.top_k = top_k
        self.executor = executor or ReflectiveExecutor(maximum_steps=4096)

    def search(self, observation: NumericTableObservation) -> ReflectiveSearchReport:
        valid = tuple(
            (row, output)
            for row, output, include in zip(
                observation.input_rows,
                observation.output_values,
                observation.validity_mask,
            )
            if include
        )
        if not valid:
            raise ValueError("mechanism frontier requires valid numeric rows")
        width = len(valid[0][0])
        expected = tuple(float(output) for _, output in valid)
        probes = tuple(row for row, _ in valid)
        generated = executed = rejected = 0
        by_behavior: dict[tuple[float | None, ...], ReflectiveCandidate] = {}
        for program in self._enumerate_programs(width):
            generated += 1
            outputs: list[float] = []
            try:
                for row, _ in valid:
                    outputs.append(self.executor.execute(program, row).output_value)
            except InvalidReflectiveProgram:
                rejected += 1
                continue
            executed += 1
            errors = tuple(actual - target for actual, target in zip(outputs, expected))
            behavior: list[float | None] = []
            for row in probes:
                try:
                    behavior.append(self.executor.execute(program, row).output_value)
                except InvalidReflectiveProgram:
                    behavior.append(None)
            behavior_key = tuple(behavior)
            key = reflective_program_key(program)
            candidate = ReflectiveCandidate(
                candidate_id="G3-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
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

    @staticmethod
    def _sort_key(candidate: ReflectiveCandidate):
        return (
            candidate.fit_error,
            candidate.maximum_absolute_error,
            candidate.program.instruction_count,
            reflective_program_key(candidate.program),
        )

    def _enumerate_programs(self, input_width: int) -> Iterable[ReflectiveProgram]:
        yield from self._self_modifying_accumulators(input_width)
        yield from self._four_state_cascades(input_width)
        yield from self._three_state_shift_feedback(input_width)
        yield from self._growing_threshold_counters(input_width)
        yield from self._variable_subtraction_counters(input_width)

    @staticmethod
    def _self_modifying_accumulators(input_width: int) -> Iterable[ReflectiveProgram]:
        """Mutate the operand word of the program's own accumulation instruction."""

        if input_width < 1:
            return
        instruction_count = 20
        counter = instruction_count * 2
        result = counter + 1
        mutable_operand_address = 17
        for input_index in range(input_width):
            for initial_result, initial_operand, operand_delta in itertools.product(
                (-1, 0, 1), (0, 1, 2), (1, 2, 3)
            ):
                yield _program(
                    (
                        (OP_GROW, 2),
                        (OP_LOAD_INPUT, input_index),
                        (OP_STORE_CELL, counter),
                        (OP_SET, initial_result),
                        (OP_STORE_CELL, result),
                        (OP_LOAD_CELL, counter),
                        (OP_JUMP_IF_ZERO, 17),
                        (OP_LOAD_CELL, result),
                        (OP_ADD_IMMEDIATE, initial_operand),
                        (OP_STORE_CELL, result),
                        (OP_LOAD_CELL, mutable_operand_address),
                        (OP_ADD_IMMEDIATE, operand_delta),
                        (OP_STORE_CELL, mutable_operand_address),
                        (OP_LOAD_CELL, counter),
                        (OP_SUB_IMMEDIATE, 1),
                        (OP_STORE_CELL, counter),
                        (OP_JUMP, 5),
                        (OP_LOAD_CELL, result),
                        (OP_EMIT, 0),
                        (OP_HALT, 0),
                    )
                )

    @staticmethod
    def _four_state_cascades(input_width: int) -> Iterable[ReflectiveProgram]:
        """Synchronous one-way cascade with four persistent and four next-state cells."""

        instruction_count = 40
        counter, a, b, c, d, next_a, next_b, next_c, next_d = range(80, 89)
        for input_index in range(input_width):
            for seeds in itertools.product((0, 1), repeat=4):
                for source_delta in (1, 2):
                    for output in (a, b, c, d):
                        yield _program(
                            (
                                (OP_GROW, 9), (OP_LOAD_INPUT, input_index), (OP_STORE_CELL, counter),
                                (OP_SET, seeds[0]), (OP_STORE_CELL, a),
                                (OP_SET, seeds[1]), (OP_STORE_CELL, b),
                                (OP_SET, seeds[2]), (OP_STORE_CELL, c),
                                (OP_SET, seeds[3]), (OP_STORE_CELL, d),
                                (OP_LOAD_CELL, counter), (OP_JUMP_IF_ZERO, 37),
                                (OP_LOAD_CELL, a), (OP_ADD_CELL, b), (OP_STORE_CELL, next_a),
                                (OP_LOAD_CELL, b), (OP_ADD_CELL, c), (OP_STORE_CELL, next_b),
                                (OP_LOAD_CELL, c), (OP_ADD_CELL, d), (OP_STORE_CELL, next_c),
                                (OP_LOAD_CELL, d), (OP_ADD_IMMEDIATE, source_delta), (OP_STORE_CELL, next_d),
                                (OP_LOAD_CELL, next_a), (OP_STORE_CELL, a),
                                (OP_LOAD_CELL, next_b), (OP_STORE_CELL, b),
                                (OP_LOAD_CELL, next_c), (OP_STORE_CELL, c),
                                (OP_LOAD_CELL, next_d), (OP_STORE_CELL, d),
                                (OP_LOAD_CELL, counter), (OP_SUB_IMMEDIATE, 1), (OP_STORE_CELL, counter),
                                (OP_JUMP, 11), (OP_LOAD_CELL, output), (OP_EMIT, 0), (OP_HALT, 0),
                            )
                        )

    @staticmethod
    def _three_state_shift_feedback(input_width: int) -> Iterable[ReflectiveProgram]:
        """Shift two states and feed a selected sum into the third state."""

        instruction_count = 34
        counter, a, b, c, next_a, next_b, next_c = range(68, 75)
        feedbacks = ((a, b), (a, c), (b, c), (a, b, c))
        for input_index in range(input_width):
            for seeds in itertools.product((0, 1), repeat=3):
                for feedback in feedbacks:
                    for output in (a, b, c):
                        feedback_instructions = [(OP_LOAD_CELL, feedback[0])]
                        feedback_instructions.extend((OP_ADD_CELL, address) for address in feedback[1:])
                        while len(feedback_instructions) < 3:
                            feedback_instructions.append((OP_ADD_IMMEDIATE, 0))
                        yield _program(
                            (
                                (OP_GROW, 7), (OP_LOAD_INPUT, input_index), (OP_STORE_CELL, counter),
                                (OP_SET, seeds[0]), (OP_STORE_CELL, a),
                                (OP_SET, seeds[1]), (OP_STORE_CELL, b),
                                (OP_SET, seeds[2]), (OP_STORE_CELL, c),
                                (OP_LOAD_CELL, counter), (OP_JUMP_IF_ZERO, 31),
                                (OP_LOAD_CELL, b), (OP_ADD_IMMEDIATE, 0), (OP_STORE_CELL, next_a),
                                (OP_LOAD_CELL, c), (OP_ADD_IMMEDIATE, 0), (OP_STORE_CELL, next_b),
                                feedback_instructions[0], feedback_instructions[1], feedback_instructions[2],
                                (OP_STORE_CELL, next_c),
                                (OP_LOAD_CELL, next_a), (OP_STORE_CELL, a),
                                (OP_LOAD_CELL, next_b), (OP_STORE_CELL, b),
                                (OP_LOAD_CELL, next_c), (OP_STORE_CELL, c),
                                (OP_LOAD_CELL, counter), (OP_SUB_IMMEDIATE, 1), (OP_STORE_CELL, counter),
                                (OP_JUMP, 9), (OP_LOAD_CELL, output), (OP_EMIT, 0), (OP_HALT, 0),
                            )
                        )

    @staticmethod
    def _growing_threshold_counters(input_width: int) -> Iterable[ReflectiveProgram]:
        """Grow a threshold until it crosses an anonymous input boundary."""

        instruction_count = 18
        threshold, count = 36, 37
        for input_index in range(input_width):
            for initial_threshold, initial_count, growth_kind, count_delta, output in itertools.product(
                (1, 2), (0, 1), ("self", "one", "two"), (1, 2), (threshold, count)
            ):
                growth = {
                    "self": (OP_ADD_CELL, threshold),
                    "one": (OP_ADD_IMMEDIATE, 1),
                    "two": (OP_ADD_IMMEDIATE, 2),
                }[growth_kind]
                yield _program(
                    (
                        (OP_GROW, 2), (OP_SET, initial_threshold), (OP_STORE_CELL, threshold),
                        (OP_SET, initial_count), (OP_STORE_CELL, count),
                        (OP_LOAD_INPUT, input_index), (OP_SUB_CELL, threshold),
                        (OP_JUMP_IF_NEGATIVE, 15),
                        (OP_LOAD_CELL, threshold), growth, (OP_STORE_CELL, threshold),
                        (OP_LOAD_CELL, count), (OP_ADD_IMMEDIATE, count_delta),
                        (OP_STORE_CELL, count), (OP_JUMP, 5),
                        (OP_LOAD_CELL, output), (OP_EMIT, 0), (OP_HALT, 0),
                    )
                )

    @staticmethod
    def _variable_subtraction_counters(input_width: int) -> Iterable[ReflectiveProgram]:
        """Count how often one anonymous input can be subtracted from another."""

        if input_width < 2:
            return
        instruction_count = 16
        remainder, count = 32, 33
        for dividend, divisor in itertools.permutations(range(input_width), 2):
            for initial_count, count_delta, output in itertools.product((0, 1), (1, 2), (remainder, count)):
                yield _program(
                    (
                        (OP_GROW, 2), (OP_LOAD_INPUT, dividend), (OP_STORE_CELL, remainder),
                        (OP_SET, initial_count), (OP_STORE_CELL, count),
                        (OP_LOAD_CELL, remainder), (OP_SUB_INPUT, divisor),
                        (OP_JUMP_IF_NEGATIVE, 13), (OP_STORE_CELL, remainder),
                        (OP_LOAD_CELL, count), (OP_ADD_IMMEDIATE, count_delta),
                        (OP_STORE_CELL, count), (OP_JUMP, 5),
                        (OP_LOAD_CELL, output), (OP_EMIT, 0), (OP_HALT, 0),
                    )
                )


def _program(instructions: Iterable[tuple[int, int]]) -> ReflectiveProgram:
    return ReflectiveProgram(tuple(value for instruction in instructions for value in instruction))
