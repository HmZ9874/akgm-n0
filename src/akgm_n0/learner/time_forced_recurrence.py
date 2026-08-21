"""Anonymous growth of a clock-coupled recurrence using an induced semantic."""

from __future__ import annotations

import hashlib
import itertools
import json
from typing import Sequence

from .metamachine_gen2 import (
    InvalidReflectiveProgram,
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
    OP_SUB_IMMEDIATE,
    ReflectiveCandidate,
    ReflectiveSearchReport,
)
from .observation import NumericTableObservation
from .semantic_invention import (
    InventedSemantic,
    SemanticExtendedExecutor,
    SemanticExtendedProgram,
)


class TimeForcedRecurrenceSearch:
    """Route five anonymous columns into a state-plus-clock program family.

    The family shape comes from the previously induced accumulation semantic.
    Input roles, semantic sources, and emitted state are selected only through
    numeric evidence.
    """

    def __init__(
        self,
        semantic: InventedSemantic,
        *,
        top_k: int = 1200,
        executor: SemanticExtendedExecutor | None = None,
    ) -> None:
        self.semantic = semantic
        self.top_k = top_k
        self.executor = executor or SemanticExtendedExecutor(maximum_steps=500_000)

    def search(self, observation: NumericTableObservation) -> ReflectiveSearchReport:
        valid = tuple(
            (row, float(output))
            for row, output, include in zip(
                observation.input_rows,
                observation.output_values,
                observation.validity_mask,
                strict=True,
            )
            if include
        )
        if not valid or len(valid[0][0]) != 5:
            raise ValueError("time-forced recurrence requires anonymous five-column evidence")
        candidates = []
        rejected = generated = 0
        for roles in itertools.permutations(range(5)):
            seed, coefficient_left, coefficient_right, bias, counter = roles
            for left_source, right_source in itertools.product(
                ("state", "clock"), repeat=2
            ):
                for output in ("state", "clock"):
                    generated += 1
                    program = _build_program(
                        self.semantic,
                        seed=seed,
                        coefficient_left=coefficient_left,
                        coefficient_right=coefficient_right,
                        bias=bias,
                        counter=counter,
                        left_source=left_source,
                        right_source=right_source,
                        output=output,
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
                    key = time_forced_program_key(program)
                    candidates.append(
                        ReflectiveCandidate(
                            "TF-" + hashlib.sha256(key.encode()).hexdigest()[:16],
                            program,
                            sum(error * error for error in errors) / len(errors),
                            max(abs(error) for error in errors),
                            tuple(outputs),
                            tuple(outputs),
                        )
                    )
        candidates.sort(
            key=lambda item: (
                item.fit_error,
                item.program.instruction_count,
                item.maximum_absolute_error,
                item.candidate_id,
            )
        )
        return ReflectiveSearchReport(
            generated,
            len(candidates),
            rejected,
            len({item.outputs for item in candidates}),
            tuple(candidates[: self.top_k]),
        )


def time_forced_program_key(program: SemanticExtendedProgram) -> str:
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))


def _descriptor(coefficient_input: int, source_address: int, target_address: int) -> int:
    if not all(0 <= value < 100 for value in (coefficient_input, source_address, target_address)):
        raise ValueError("semantic descriptor field is out of range")
    return coefficient_input * 10_000 + source_address * 100 + target_address


def _assemble(
    entries: Sequence[str | tuple[int, int | str | tuple[int, str, str]]],
    data: Sequence[str],
    semantic: InventedSemantic,
) -> SemanticExtendedProgram:
    labels: dict[str, int] = {}
    instructions: list[tuple[int, int | str | tuple[int, str, str]]] = []
    for entry in entries:
        if isinstance(entry, str):
            labels[entry] = len(instructions)
        else:
            instructions.append(entry)
    addresses = {name: 2 * len(instructions) + index for index, name in enumerate(data)}
    words: list[int] = []
    for opcode, operand in instructions:
        if isinstance(operand, str):
            operand = (
                labels[operand]
                if opcode in (OP_JUMP, OP_JUMP_IF_ZERO, OP_JUMP_IF_NEGATIVE)
                else addresses[operand]
            )
        elif isinstance(operand, tuple):
            coefficient, source, target = operand
            operand = _descriptor(coefficient, addresses[source], addresses[target])
        words.extend((opcode, operand))
    return SemanticExtendedProgram(tuple(words), semantic)


def _build_program(
    semantic: InventedSemantic,
    *,
    seed: int,
    coefficient_left: int,
    coefficient_right: int,
    bias: int,
    counter: int,
    left_source: str,
    right_source: str,
    output: str,
) -> SemanticExtendedProgram:
    return _assemble(
        (
            (OP_GROW, 4),
            (OP_LOAD_INPUT, counter),
            (OP_STORE_CELL, "counter"),
            (OP_LOAD_INPUT, seed),
            (OP_STORE_CELL, "state"),
            (OP_SET, 0),
            (OP_STORE_CELL, "clock"),
            "outer",
            (OP_LOAD_CELL, "counter"),
            (OP_JUMP_IF_ZERO, "end"),
            (OP_SET, 0),
            (OP_STORE_CELL, "next"),
            (semantic.opcode, (coefficient_left, left_source, "next")),
            (semantic.opcode, (coefficient_right, right_source, "next")),
            (OP_LOAD_CELL, "next"),
            (OP_ADD_INPUT, bias),
            (OP_STORE_CELL, "next"),
            (OP_LOAD_CELL, "next"),
            (OP_STORE_CELL, "state"),
            (OP_LOAD_CELL, "clock"),
            (OP_ADD_IMMEDIATE, 1),
            (OP_STORE_CELL, "clock"),
            (OP_LOAD_CELL, "counter"),
            (OP_SUB_IMMEDIATE, 1),
            (OP_STORE_CELL, "counter"),
            (OP_JUMP, "outer"),
            "end",
            (OP_LOAD_CELL, output),
            (OP_EMIT, 0),
            (OP_HALT, 0),
        ),
        ("counter", "state", "clock", "next"),
        semantic,
    )
