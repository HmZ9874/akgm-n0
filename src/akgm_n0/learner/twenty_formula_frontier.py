"""Anonymous twenty-shape reflective program frontier.

Shape identifiers deliberately carry no mathematical names.  Each shape compiles
to the same primitive unified word machine used by MetaMachine Gen 2.
"""

from __future__ import annotations

import hashlib
import json
from typing import Iterable, Sequence

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


Entry = str | tuple[int, int | str]


def _assemble(entries: Sequence[Entry], data_names: Sequence[str]) -> ReflectiveProgram:
    labels: dict[str, int] = {}
    instruction_index = 0
    for entry in entries:
        if isinstance(entry, str):
            if entry in labels:
                raise ValueError(f"duplicate label: {entry}")
            labels[entry] = instruction_index
        else:
            instruction_index += 1
    data = {name: instruction_index * 2 + index for index, name in enumerate(data_names)}
    words: list[int] = []
    for entry in entries:
        if isinstance(entry, str):
            continue
        opcode, operand = entry
        if operand == "#data":
            resolved = len(data_names)
        elif isinstance(operand, str) and operand.startswith("@"):
            resolved = labels[operand[1:]]
        elif isinstance(operand, str) and operand.startswith("$"):
            resolved = data[operand[1:]]
        else:
            resolved = int(operand)
        words.extend((opcode, resolved))
    return ReflectiveProgram(tuple(words))


def _counted_prefix(data_names, seeds):
    entries: list[Entry] = [
        (OP_GROW, "#data"), (OP_LOAD_INPUT, 0), (OP_STORE_CELL, "$counter")
    ]
    for name, value in seeds:
        entries.extend(((OP_SET, value), (OP_STORE_CELL, f"${name}")))
    entries.extend(("loop", (OP_LOAD_CELL, "$counter"), (OP_JUMP_IF_ZERO, "@end")))
    return entries


def _counted_suffix(output):
    return [
        (OP_LOAD_CELL, "$counter"), (OP_SUB_IMMEDIATE, 1),
        (OP_STORE_CELL, "$counter"), (OP_JUMP, "@loop"),
        "end", (OP_LOAD_CELL, f"${output}"), (OP_EMIT, 0), (OP_HALT, 0),
    ]


def _shape_00() -> ReflectiveProgram:
    data = ("counter", "x")
    entries = _counted_prefix(data, (("x", 1),))
    entries += [(OP_LOAD_CELL, "$x"), (OP_ADD_CELL, "$x"), (OP_ADD_CELL, "$x"), (OP_STORE_CELL, "$x")]
    entries += _counted_suffix("x")
    return _assemble(entries, data)


def _shape_01() -> ReflectiveProgram:
    data = ("counter", "x")
    entries = _counted_prefix(data, (("x", 0),))
    entries += [(OP_LOAD_CELL, "$x"), (OP_ADD_CELL, "$x"), (OP_ADD_IMMEDIATE, 1), (OP_STORE_CELL, "$x")]
    entries += _counted_suffix("x")
    return _assemble(entries, data)


def _three_accumulator(seed_a, seed_b, delta_b) -> ReflectiveProgram:
    data = ("counter", "x", "a", "b")
    entries = _counted_prefix(data, (("x", 0), ("a", seed_a), ("b", seed_b)))
    entries += [
        (OP_LOAD_CELL, "$x"), (OP_ADD_CELL, "$a"), (OP_STORE_CELL, "$x"),
        (OP_LOAD_CELL, "$a"), (OP_ADD_CELL, "$b"), (OP_STORE_CELL, "$a"),
        (OP_LOAD_CELL, "$b"), (OP_ADD_IMMEDIATE, delta_b), (OP_STORE_CELL, "$b"),
    ]
    entries += _counted_suffix("x")
    return _assemble(entries, data)


def _shape_02() -> ReflectiveProgram:
    return _three_accumulator(1, 6, 6)


def _shape_03() -> ReflectiveProgram:
    data = ("counter", "sum", "square", "odd", "next_square")
    entries = _counted_prefix(data, (("sum", 0), ("square", 0), ("odd", 1), ("next_square", 0)))
    entries += [
        (OP_LOAD_CELL, "$square"), (OP_ADD_CELL, "$odd"), (OP_STORE_CELL, "$next_square"),
        (OP_LOAD_CELL, "$sum"), (OP_ADD_CELL, "$next_square"), (OP_STORE_CELL, "$sum"),
        (OP_LOAD_CELL, "$next_square"), (OP_STORE_CELL, "$square"),
        (OP_LOAD_CELL, "$odd"), (OP_ADD_IMMEDIATE, 2), (OP_STORE_CELL, "$odd"),
    ]
    entries += _counted_suffix("sum")
    return _assemble(entries, data)


def _shape_04() -> ReflectiveProgram:
    names = ("counter", "a", "b", "c", "d", "e", "na", "nb", "nc", "nd", "ne")
    entries = _counted_prefix(names, (("a", 0), ("b", 0), ("c", 0), ("d", 0), ("e", 0)))
    for left, right, target in (("a", "b", "na"), ("b", "c", "nb"), ("c", "d", "nc"), ("d", "e", "nd")):
        entries += [(OP_LOAD_CELL, f"${left}"), (OP_ADD_CELL, f"${right}"), (OP_STORE_CELL, f"${target}")]
    entries += [(OP_LOAD_CELL, "$e"), (OP_ADD_IMMEDIATE, 1), (OP_STORE_CELL, "$ne")]
    for source, target in (("na", "a"), ("nb", "b"), ("nc", "c"), ("nd", "d"), ("ne", "e")):
        entries += [(OP_LOAD_CELL, f"${source}"), (OP_STORE_CELL, f"${target}")]
    entries += _counted_suffix("a")
    return _assemble(entries, names)


def _two_state_shift(seed_a, seed_b, double_b=False) -> ReflectiveProgram:
    names = ("counter", "a", "b", "next")
    entries = _counted_prefix(names, (("a", seed_a), ("b", seed_b)))
    entries += [(OP_LOAD_CELL, "$b")]
    if double_b:
        entries += [(OP_ADD_CELL, "$b")]
    entries += [(OP_ADD_CELL, "$a"), (OP_STORE_CELL, "$next"),
                (OP_LOAD_CELL, "$b"), (OP_STORE_CELL, "$a"),
                (OP_LOAD_CELL, "$next"), (OP_STORE_CELL, "$b")]
    entries += _counted_suffix("a")
    return _assemble(entries, names)


def _shape_05() -> ReflectiveProgram:
    return _two_state_shift(2, 1)


def _shape_06() -> ReflectiveProgram:
    return _two_state_shift(0, 1, double_b=True)


def _shape_07() -> ReflectiveProgram:
    names = ("counter", "a", "b", "c", "next")
    entries = _counted_prefix(names, (("a", 1), ("b", 1), ("c", 1)))
    entries += [
        (OP_LOAD_CELL, "$a"), (OP_ADD_CELL, "$b"), (OP_STORE_CELL, "$next"),
        (OP_LOAD_CELL, "$b"), (OP_STORE_CELL, "$a"),
        (OP_LOAD_CELL, "$c"), (OP_STORE_CELL, "$b"),
        (OP_LOAD_CELL, "$next"), (OP_STORE_CELL, "$c"),
    ]
    entries += _counted_suffix("a")
    return _assemble(entries, names)


def _shape_08() -> ReflectiveProgram:
    names = ("counter", "a", "b", "c", "d", "next")
    entries = _counted_prefix(names, (("a", 0), ("b", 0), ("c", 0), ("d", 1)))
    entries += [
        (OP_LOAD_CELL, "$a"), (OP_ADD_CELL, "$b"), (OP_ADD_CELL, "$c"),
        (OP_ADD_CELL, "$d"), (OP_STORE_CELL, "$next"),
        (OP_LOAD_CELL, "$b"), (OP_STORE_CELL, "$a"),
        (OP_LOAD_CELL, "$c"), (OP_STORE_CELL, "$b"),
        (OP_LOAD_CELL, "$d"), (OP_STORE_CELL, "$c"),
        (OP_LOAD_CELL, "$next"), (OP_STORE_CELL, "$d"),
    ]
    entries += _counted_suffix("a")
    return _assemble(entries, names)


def _shape_09() -> ReflectiveProgram:
    names = ("counter", "a", "b", "c", "temp")
    entries = _counted_prefix(names, (("a", 0), ("b", 1), ("c", 2)))
    entries += [
        (OP_LOAD_CELL, "$a"), (OP_STORE_CELL, "$temp"),
        (OP_LOAD_CELL, "$b"), (OP_STORE_CELL, "$a"),
        (OP_LOAD_CELL, "$c"), (OP_STORE_CELL, "$b"),
        (OP_LOAD_CELL, "$temp"), (OP_STORE_CELL, "$c"),
    ]
    entries += _counted_suffix("a")
    return _assemble(entries, names)


def _shape_10() -> ReflectiveProgram:
    names = ("remainder", "count")
    entries: list[Entry] = [
        (OP_GROW, "#data"), (OP_LOAD_INPUT, 0), (OP_STORE_CELL, "$remainder"),
        (OP_SET, 0), (OP_STORE_CELL, "$count"), "loop",
        (OP_LOAD_CELL, "$remainder"), (OP_SUB_IMMEDIATE, 3),
        (OP_JUMP_IF_NEGATIVE, "@end"), (OP_STORE_CELL, "$remainder"),
        (OP_LOAD_CELL, "$count"), (OP_ADD_IMMEDIATE, 1), (OP_STORE_CELL, "$count"),
        (OP_JUMP, "@loop"), "end", (OP_LOAD_CELL, "$count"), (OP_EMIT, 0), (OP_HALT, 0),
    ]
    return _assemble(entries, names)


def _shape_11() -> ReflectiveProgram:
    names = ("threshold", "count")
    entries: list[Entry] = [
        (OP_GROW, "#data"), (OP_SET, 1), (OP_STORE_CELL, "$threshold"),
        (OP_SET, 0), (OP_STORE_CELL, "$count"), "loop",
        (OP_LOAD_INPUT, 0), (OP_SUB_CELL, "$threshold"), (OP_JUMP_IF_NEGATIVE, "@end"),
        (OP_LOAD_CELL, "$threshold"), (OP_ADD_CELL, "$threshold"),
        (OP_ADD_CELL, "$threshold"), (OP_STORE_CELL, "$threshold"),
        (OP_LOAD_CELL, "$count"), (OP_ADD_IMMEDIATE, 1), (OP_STORE_CELL, "$count"),
        (OP_JUMP, "@loop"), "end", (OP_LOAD_CELL, "$count"), (OP_EMIT, 0), (OP_HALT, 0),
    ]
    return _assemble(entries, names)


def _shape_12() -> ReflectiveProgram:
    entries: list[Entry] = [
        (OP_LOAD_INPUT, 0), (OP_SUB_INPUT, 1), (OP_JUMP_IF_NEGATIVE, "@first"),
        (OP_LOAD_INPUT, 1), (OP_EMIT, 0), (OP_HALT, 0),
        "first", (OP_LOAD_INPUT, 0), (OP_EMIT, 0), (OP_HALT, 0),
    ]
    return _assemble(entries, ())


def _shape_13() -> ReflectiveProgram:
    entries: list[Entry] = [
        (OP_LOAD_INPUT, 0), (OP_SUB_INPUT, 1), (OP_JUMP_IF_NEGATIVE, "@reverse"),
        (OP_EMIT, 0), (OP_HALT, 0),
        "reverse", (OP_LOAD_INPUT, 1), (OP_SUB_INPUT, 0), (OP_EMIT, 0), (OP_HALT, 0),
    ]
    return _assemble(entries, ())


def _shape_14() -> ReflectiveProgram:
    names = ("remainder",)
    entries: list[Entry] = [
        (OP_GROW, "#data"), (OP_LOAD_INPUT, 0), (OP_STORE_CELL, "$remainder"), "loop",
        (OP_LOAD_CELL, "$remainder"), (OP_SUB_INPUT, 1), (OP_JUMP_IF_NEGATIVE, "@end"),
        (OP_STORE_CELL, "$remainder"), (OP_JUMP, "@loop"),
        "end", (OP_LOAD_CELL, "$remainder"), (OP_EMIT, 0), (OP_HALT, 0),
    ]
    return _assemble(entries, names)


def _shape_15() -> ReflectiveProgram:
    names = ("remainder", "count")
    entries: list[Entry] = [
        (OP_GROW, "#data"), (OP_LOAD_INPUT, 0), (OP_STORE_CELL, "$remainder"),
        (OP_SET, 0), (OP_STORE_CELL, "$count"), "loop",
        (OP_LOAD_CELL, "$remainder"), (OP_JUMP_IF_ZERO, "@end"),
        (OP_SUB_INPUT, 1), (OP_STORE_CELL, "$remainder"),
        (OP_LOAD_CELL, "$count"), (OP_ADD_IMMEDIATE, 1), (OP_STORE_CELL, "$count"),
        (OP_LOAD_CELL, "$remainder"), (OP_JUMP_IF_NEGATIVE, "@end"), (OP_JUMP, "@loop"),
        "end", (OP_LOAD_CELL, "$count"), (OP_EMIT, 0), (OP_HALT, 0),
    ]
    return _assemble(entries, names)


def _shape_16() -> ReflectiveProgram:
    names = ("remainder",)
    entries: list[Entry] = [
        (OP_GROW, "#data"), (OP_LOAD_INPUT, 0), (OP_STORE_CELL, "$remainder"), "loop",
        (OP_LOAD_CELL, "$remainder"), (OP_JUMP_IF_ZERO, "@yes"),
        (OP_SUB_INPUT, 1), (OP_JUMP_IF_NEGATIVE, "@no"),
        (OP_STORE_CELL, "$remainder"), (OP_JUMP, "@loop"),
        "yes", (OP_SET, 1), (OP_EMIT, 0), (OP_HALT, 0),
        "no", (OP_SET, 0), (OP_EMIT, 0), (OP_HALT, 0),
    ]
    return _assemble(entries, names)


def _shape_17() -> ReflectiveProgram:
    entries: list[Entry] = [
        (OP_LOAD_INPUT, 0), (OP_SUB_INPUT, 1), (OP_JUMP_IF_ZERO, "@yes"),
        (OP_SET, 0), (OP_EMIT, 0), (OP_HALT, 0),
        "yes", (OP_SET, 1), (OP_EMIT, 0), (OP_HALT, 0),
    ]
    return _assemble(entries, ())


def _shape_18() -> ReflectiveProgram:
    entries: list[Entry] = [
        (OP_LOAD_INPUT, 0), (OP_SUB_INPUT, 1), (OP_JUMP_IF_NEGATIVE, "@yes"),
        (OP_SET, 0), (OP_EMIT, 0), (OP_HALT, 0),
        "yes", (OP_SET, 1), (OP_EMIT, 0), (OP_HALT, 0),
    ]
    return _assemble(entries, ())


def _shape_19() -> ReflectiveProgram:
    entries: list[Entry] = [
        (OP_LOAD_INPUT, 0), (OP_JUMP_IF_ZERO, "@zero"),
        (OP_JUMP_IF_NEGATIVE, "@negative"), (OP_SET, 1), (OP_EMIT, 0), (OP_HALT, 0),
        "negative", (OP_SET, -1), (OP_EMIT, 0), (OP_HALT, 0),
        "zero", (OP_SET, 0), (OP_EMIT, 0), (OP_HALT, 0),
    ]
    return _assemble(entries, ())


SHAPE_BUILDERS = (
    _shape_00, _shape_01, _shape_02, _shape_03, _shape_04,
    _shape_05, _shape_06, _shape_07, _shape_08, _shape_09,
    _shape_10, _shape_11, _shape_12, _shape_13, _shape_14,
    _shape_15, _shape_16, _shape_17, _shape_18, _shape_19,
)


def anonymous_shape_programs() -> tuple[ReflectiveProgram, ...]:
    return tuple(builder() for builder in SHAPE_BUILDERS)


def structural_logic_signature(program: ReflectiveProgram) -> str:
    """Ignore address renumbering and literal values while retaining data dependencies."""

    instructions = tuple(zip(program.words[::2], program.words[1::2]))
    code_size = len(program.words)
    address_roles: dict[int, int] = {}
    normalized = []
    for index, (opcode, operand) in enumerate(instructions):
        if opcode in (OP_LOAD_CELL, OP_STORE_CELL, OP_ADD_CELL, OP_SUB_CELL):
            if operand < code_size:
                role = ("code", operand - 2 * index)
            else:
                if operand not in address_roles:
                    address_roles[operand] = len(address_roles)
                role = ("data", address_roles[operand])
        elif opcode in (OP_JUMP, OP_JUMP_IF_ZERO, OP_JUMP_IF_NEGATIVE):
            role = ("jump", operand - index)
        elif opcode in (OP_LOAD_INPUT, OP_SUB_INPUT):
            role = ("input", operand)
        elif opcode == OP_GROW:
            role = ("grow", operand)
        elif opcode in (OP_SET, OP_ADD_IMMEDIATE, OP_SUB_IMMEDIATE):
            role = ("literal", "nonzero" if operand else "zero")
        else:
            role = ("none",)
        normalized.append((opcode, role))
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class TwentyFormulaFrontierSearch:
    """Select among anonymous structural hypotheses by executable behavior only."""

    def __init__(self, *, top_k: int = 40, executor: ReflectiveExecutor | None = None):
        self.top_k = top_k
        self.executor = executor or ReflectiveExecutor(maximum_steps=8192)
        self.programs = anonymous_shape_programs()

    def search(self, observation: NumericTableObservation) -> ReflectiveSearchReport:
        valid = tuple((row, out) for row, out, include in zip(
            observation.input_rows, observation.output_values, observation.validity_mask
        ) if include)
        expected = tuple(float(out) for _, out in valid)
        candidates = []
        rejected = 0
        for program in self.programs:
            outputs = []
            try:
                for row, _ in valid:
                    outputs.append(self.executor.execute(program, row).output_value)
            except InvalidReflectiveProgram:
                rejected += 1
                continue
            errors = tuple(actual - target for actual, target in zip(outputs, expected))
            key = reflective_program_key(program)
            candidates.append(ReflectiveCandidate(
                candidate_id="G4-" + hashlib.sha256(key.encode()).hexdigest()[:16],
                program=program,
                fit_error=sum(error * error for error in errors) / len(errors),
                maximum_absolute_error=max(abs(error) for error in errors),
                outputs=tuple(outputs),
                behavior_signature=tuple(outputs),
            ))
        candidates.sort(key=lambda item: (
            item.fit_error, item.maximum_absolute_error, item.program.instruction_count,
            reflective_program_key(item.program),
        ))
        return ReflectiveSearchReport(
            programs_generated=len(self.programs), programs_executed=len(candidates),
            programs_rejected=rejected,
            behavior_classes=len({item.behavior_signature for item in candidates}),
            top_candidates=tuple(candidates[: self.top_k]),
        )
