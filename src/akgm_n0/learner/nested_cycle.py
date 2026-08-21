"""Anonymous nested-cycle and repeated-group program discovery.

The learner manipulates finite collections, cursor positions, registers, and a
small buffer.  Arithmetic names and arithmetic opcodes do not occur in this
module.  Mathematical interpretations are attached only by independent
evaluators after a structural program has been induced.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Sequence

from .foundation_kernel import FoundationRewardPolicy, OUTPUT_MARK


OP_TEST_EMPTY = 0
OP_ADVANCE = 1
OP_REWIND = 2
OP_EMIT = 3
OP_BUFFER = 4
OP_JUMP = 5
OP_HALT = 6
OP_CLEAR_BUFFER = 7
OP_EMIT_BUFFER = 8
CYCLE_OPCODES = frozenset(
    {OP_TEST_EMPTY, OP_ADVANCE, OP_REWIND, OP_EMIT, OP_BUFFER, OP_JUMP,
     OP_HALT, OP_CLEAR_BUFFER, OP_EMIT_BUFFER}
)

EMIT_NONE = 0
EMIT_PAIR = 1
EMIT_OUTER = 2
EMIT_INNER = 3
EMIT_PRIMARY = 4

GROUP_EMIT_NONE = 0
GROUP_EMIT_COMPLETE = 1
GROUP_EMIT_ITEM = 2


@dataclass(frozen=True, slots=True)
class CycleInstruction:
    opcode: int
    slot: int | None = None
    target: int | None = None
    mode: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"opcode": self.opcode}
        if self.slot is not None:
            result["slot"] = self.slot
        if self.target is not None:
            result["target"] = self.target
        if self.mode is not None:
            result["mode"] = self.mode
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CycleInstruction":
        return cls(
            int(value["opcode"]),
            None if "slot" not in value else int(value["slot"]),
            None if "target" not in value else int(value["target"]),
            None if "mode" not in value else int(value["mode"]),
        )


@dataclass(frozen=True, slots=True)
class NestedCycleProgram:
    program_id: str
    outer_slot: int
    inner_slot: int
    rewind_inner: bool
    emit_mode: int
    instructions: tuple[CycleInstruction, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "outer_slot": self.outer_slot,
            "inner_slot": self.inner_slot,
            "rewind_inner": self.rewind_inner,
            "emit_mode": self.emit_mode,
            "instructions": [item.to_dict() for item in self.instructions],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "NestedCycleProgram":
        return cls(
            str(value["program_id"]),
            int(value["outer_slot"]),
            int(value["inner_slot"]),
            bool(value["rewind_inner"]),
            int(value["emit_mode"]),
            tuple(CycleInstruction.from_dict(item) for item in value["instructions"]),
        )


@dataclass(frozen=True, slots=True)
class GroupCycleProgram:
    program_id: str
    source_slot: int
    stencil_slot: int
    restart_stencil: bool
    emit_mode: int
    preserve_incomplete: bool
    instructions: tuple[CycleInstruction, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "source_slot": self.source_slot,
            "stencil_slot": self.stencil_slot,
            "restart_stencil": self.restart_stencil,
            "emit_mode": self.emit_mode,
            "preserve_incomplete": self.preserve_incomplete,
            "instructions": [item.to_dict() for item in self.instructions],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "GroupCycleProgram":
        return cls(
            str(value["program_id"]),
            int(value["source_slot"]),
            int(value["stencil_slot"]),
            bool(value["restart_stencil"]),
            int(value["emit_mode"]),
            bool(value["preserve_incomplete"]),
            tuple(CycleInstruction.from_dict(item) for item in value["instructions"]),
        )


@dataclass(frozen=True, slots=True)
class NestedExample:
    sources: tuple[tuple[str, ...], tuple[str, ...]]
    expected_output: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GroupExample:
    sources: tuple[tuple[str, ...], tuple[str, ...]]
    expected_completed: tuple[str, ...]
    expected_residue: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CycleExecution:
    halted: bool
    output: tuple[str, ...]
    residue: tuple[str, ...]
    heads: tuple[int, int]
    primitive_execution_tokens: int


@dataclass(frozen=True, slots=True)
class CycleCandidate:
    program: NestedCycleProgram | GroupCycleProgram
    exact: bool
    passed_example_count: int
    example_count: int
    execution_token_cost: int
    program_token_cost: int
    total_token_cost: int
    reward: int


@dataclass(frozen=True, slots=True)
class CycleSearchReport:
    task_id: str
    candidates_evaluated: int
    selected: CycleCandidate
    candidates: tuple[CycleCandidate, ...]


@dataclass(frozen=True, slots=True)
class NestedFoundationSemantic:
    semantic_id: str
    opcode: int
    program: NestedCycleProgram
    dependency_semantic_ids: tuple[str, ...]
    source_task_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id,
            "opcode": self.opcode,
            "program": self.program.to_dict(),
            "dependency_semantic_ids": list(self.dependency_semantic_ids),
            "source_task_ids": list(self.source_task_ids),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "NestedFoundationSemantic":
        return cls(
            str(value["semantic_id"]),
            int(value["opcode"]),
            NestedCycleProgram.from_dict(dict(value["program"])),
            tuple(str(item) for item in value["dependency_semantic_ids"]),
            tuple(str(item) for item in value["source_task_ids"]),
        )


@dataclass(frozen=True, slots=True)
class PartitionFoundationSemantic:
    semantic_id: str
    opcode: int
    program: GroupCycleProgram
    dependency_semantic_ids: tuple[str, ...]
    source_task_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id,
            "opcode": self.opcode,
            "program": self.program.to_dict(),
            "dependency_semantic_ids": list(self.dependency_semantic_ids),
            "source_task_ids": list(self.source_task_ids),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PartitionFoundationSemantic":
        return cls(
            str(value["semantic_id"]),
            int(value["opcode"]),
            GroupCycleProgram.from_dict(dict(value["program"])),
            tuple(str(item) for item in value["dependency_semantic_ids"]),
            tuple(str(item) for item in value["source_task_ids"]),
        )


class AnonymousCycleExecutor:
    """Interpret generic cursor, loop, register, and buffer instructions."""

    def execute_nested(
        self,
        program: NestedCycleProgram,
        sources: Sequence[Sequence[str]],
        *,
        maximum_steps: int = 100_000,
    ) -> CycleExecution:
        return self._execute(program.instructions, sources, maximum_steps=maximum_steps)

    def execute_group(
        self,
        program: GroupCycleProgram,
        sources: Sequence[Sequence[str]],
        *,
        maximum_steps: int = 100_000,
    ) -> CycleExecution:
        if not sources[program.stencil_slot]:
            return CycleExecution(False, (), (), (0, 0), 0)
        return self._execute(program.instructions, sources, maximum_steps=maximum_steps)

    def _execute(
        self,
        instructions: Sequence[CycleInstruction],
        sources: Sequence[Sequence[str]],
        *,
        maximum_steps: int,
    ) -> CycleExecution:
        if len(sources) != 2:
            raise ValueError("cycle programs require exactly two source collections")
        memory = (tuple(sources[0]), tuple(sources[1]))
        heads = [0, 0]
        registers: list[str | None] = [None, None]
        buffer: list[str] = []
        output: list[str] = []
        residue: list[str] = []
        pc = 0
        steps = 0
        while 0 <= pc < len(instructions) and steps < maximum_steps:
            instruction = instructions[pc]
            steps += 1
            if instruction.opcode == OP_TEST_EMPTY:
                if instruction.slot is None or instruction.target is None:
                    raise ValueError("empty test is incomplete")
                pc = instruction.target if heads[instruction.slot] >= len(memory[instruction.slot]) else pc + 1
            elif instruction.opcode == OP_ADVANCE:
                if instruction.slot is None or heads[instruction.slot] >= len(memory[instruction.slot]):
                    raise ValueError("cannot advance an empty cursor")
                registers[instruction.slot] = memory[instruction.slot][heads[instruction.slot]]
                heads[instruction.slot] += 1
                pc += 1
            elif instruction.opcode == OP_REWIND:
                if instruction.slot is None:
                    raise ValueError("rewind is incomplete")
                heads[instruction.slot] = 0
                pc += 1
            elif instruction.opcode == OP_EMIT:
                if instruction.mode == EMIT_PAIR:
                    if registers[0] is None or registers[1] is None:
                        raise ValueError("pair registers are incomplete")
                    output.append(paired_token(registers[0], registers[1]))
                elif instruction.mode == EMIT_OUTER:
                    slot = instruction.slot
                    if slot is None or registers[slot] is None:
                        raise ValueError("outer register is incomplete")
                    output.append(str(registers[slot]))
                elif instruction.mode == EMIT_INNER:
                    slot = instruction.slot
                    if slot is None or registers[slot] is None:
                        raise ValueError("inner register is incomplete")
                    output.append(str(registers[slot]))
                elif instruction.mode == EMIT_PRIMARY:
                    output.append(OUTPUT_MARK)
                else:
                    raise ValueError("unknown emit mode")
                pc += 1
            elif instruction.opcode == OP_BUFFER:
                if instruction.slot is None or registers[instruction.slot] is None:
                    raise ValueError("buffer source register is incomplete")
                buffer.append(str(registers[instruction.slot]))
                pc += 1
            elif instruction.opcode == OP_CLEAR_BUFFER:
                buffer.clear()
                pc += 1
            elif instruction.opcode == OP_EMIT_BUFFER:
                residue.extend(buffer)
                pc += 1
            elif instruction.opcode == OP_JUMP:
                if instruction.target is None:
                    raise ValueError("jump is incomplete")
                pc = instruction.target
            elif instruction.opcode == OP_HALT:
                return CycleExecution(True, tuple(output), tuple(residue), tuple(heads), steps)
            else:
                raise ValueError(f"unknown cycle opcode: {instruction.opcode}")
        return CycleExecution(False, tuple(output), tuple(residue), tuple(heads), steps)


class NestedCycleSearch:
    def search(self, task_id: str, examples: Sequence[NestedExample]) -> CycleSearchReport:
        candidates: list[CycleCandidate] = []
        for outer_slot, rewind_inner, emit_mode in itertools.product(
            (0, 1), (False, True), (EMIT_NONE, EMIT_PAIR, EMIT_OUTER, EMIT_INNER, EMIT_PRIMARY)
        ):
            program = compile_nested_program(outer_slot, 1 - outer_slot, rewind_inner, emit_mode)
            candidates.append(_score_nested(program, examples))
        return _select(task_id, candidates)


class GroupCycleSearch:
    def search(self, task_id: str, examples: Sequence[GroupExample]) -> CycleSearchReport:
        candidates: list[CycleCandidate] = []
        for source_slot, restart, emit_mode, preserve in itertools.product(
            (0, 1), (False, True),
            (GROUP_EMIT_NONE, GROUP_EMIT_COMPLETE, GROUP_EMIT_ITEM),
            (False, True),
        ):
            program = compile_group_program(source_slot, 1 - source_slot, restart, emit_mode, preserve)
            candidates.append(_score_group(program, examples))
        return _select(task_id, candidates)


class NestedSemanticInducer:
    def induce(self, report: CycleSearchReport, *, opcode: int, dependency_semantic_ids: Sequence[str]) -> NestedFoundationSemantic:
        if not isinstance(report.selected.program, NestedCycleProgram):
            raise TypeError("nested inducer requires a nested-cycle program")
        semantic_id = _semantic_id("NSEM", opcode, report.selected.program.program_id, dependency_semantic_ids, report.task_id)
        return NestedFoundationSemantic(semantic_id, opcode, report.selected.program, tuple(dependency_semantic_ids), (report.task_id,))


class PartitionSemanticInducer:
    def induce(self, report: CycleSearchReport, *, opcode: int, dependency_semantic_ids: Sequence[str]) -> PartitionFoundationSemantic:
        if not isinstance(report.selected.program, GroupCycleProgram):
            raise TypeError("partition inducer requires a group-cycle program")
        semantic_id = _semantic_id("PSEM", opcode, report.selected.program.program_id, dependency_semantic_ids, report.task_id)
        return PartitionFoundationSemantic(semantic_id, opcode, report.selected.program, tuple(dependency_semantic_ids), (report.task_id,))


def compile_nested_program(outer_slot: int, inner_slot: int, rewind_inner: bool, emit_mode: int) -> NestedCycleProgram:
    instructions: list[CycleInstruction] = []
    outer_test = len(instructions)
    instructions.append(CycleInstruction(OP_TEST_EMPTY, slot=outer_slot, target=-1))
    instructions.append(CycleInstruction(OP_ADVANCE, slot=outer_slot))
    if rewind_inner:
        instructions.append(CycleInstruction(OP_REWIND, slot=inner_slot))
    inner_test = len(instructions)
    instructions.append(CycleInstruction(OP_TEST_EMPTY, slot=inner_slot, target=-1))
    instructions.append(CycleInstruction(OP_ADVANCE, slot=inner_slot))
    if emit_mode != EMIT_NONE:
        emit_slot = outer_slot if emit_mode == EMIT_OUTER else inner_slot if emit_mode == EMIT_INNER else None
        instructions.append(CycleInstruction(OP_EMIT, slot=emit_slot, mode=emit_mode))
    instructions.append(CycleInstruction(OP_JUMP, target=inner_test))
    return_outer = len(instructions)
    instructions.append(CycleInstruction(OP_JUMP, target=outer_test))
    halt = len(instructions)
    instructions.append(CycleInstruction(OP_HALT))
    instructions[outer_test] = CycleInstruction(OP_TEST_EMPTY, slot=outer_slot, target=halt)
    instructions[inner_test] = CycleInstruction(OP_TEST_EMPTY, slot=inner_slot, target=return_outer)
    payload = {
        "outer_slot": outer_slot, "inner_slot": inner_slot,
        "rewind_inner": rewind_inner, "emit_mode": emit_mode,
        "instructions": [item.to_dict() for item in instructions],
    }
    program_id = "NCP-" + _digest(payload)
    return NestedCycleProgram(program_id, outer_slot, inner_slot, rewind_inner, emit_mode, tuple(instructions))


def compile_group_program(source_slot: int, stencil_slot: int, restart_stencil: bool, emit_mode: int, preserve_incomplete: bool) -> GroupCycleProgram:
    instructions: list[CycleInstruction] = []
    group_start = len(instructions)
    instructions.append(CycleInstruction(OP_CLEAR_BUFFER))
    instructions.append(CycleInstruction(OP_TEST_EMPTY, slot=source_slot, target=-1))
    if restart_stencil:
        instructions.append(CycleInstruction(OP_REWIND, slot=stencil_slot))
    stencil_test = len(instructions)
    instructions.append(CycleInstruction(OP_TEST_EMPTY, slot=stencil_slot, target=-1))
    instructions.append(CycleInstruction(OP_TEST_EMPTY, slot=source_slot, target=-1))
    instructions.append(CycleInstruction(OP_ADVANCE, slot=source_slot))
    instructions.append(CycleInstruction(OP_BUFFER, slot=source_slot))
    instructions.append(CycleInstruction(OP_ADVANCE, slot=stencil_slot))
    if emit_mode == GROUP_EMIT_ITEM:
        instructions.append(CycleInstruction(OP_EMIT, mode=EMIT_PRIMARY))
    instructions.append(CycleInstruction(OP_JUMP, target=stencil_test))
    complete = len(instructions)
    if emit_mode == GROUP_EMIT_COMPLETE:
        instructions.append(CycleInstruction(OP_EMIT, mode=EMIT_PRIMARY))
    instructions.append(CycleInstruction(OP_JUMP, target=group_start))
    incomplete = len(instructions)
    if preserve_incomplete:
        instructions.append(CycleInstruction(OP_EMIT_BUFFER))
    instructions.append(CycleInstruction(OP_HALT))
    halt = len(instructions)
    instructions.append(CycleInstruction(OP_HALT))
    instructions[group_start + 1] = CycleInstruction(OP_TEST_EMPTY, slot=source_slot, target=halt)
    instructions[stencil_test] = CycleInstruction(OP_TEST_EMPTY, slot=stencil_slot, target=complete)
    instructions[stencil_test + 1] = CycleInstruction(OP_TEST_EMPTY, slot=source_slot, target=incomplete)
    payload = {
        "source_slot": source_slot, "stencil_slot": stencil_slot,
        "restart_stencil": restart_stencil, "emit_mode": emit_mode,
        "preserve_incomplete": preserve_incomplete,
        "instructions": [item.to_dict() for item in instructions],
    }
    program_id = "GCP-" + _digest(payload)
    return GroupCycleProgram(program_id, source_slot, stencil_slot, restart_stencil, emit_mode, preserve_incomplete, tuple(instructions))


def paired_token(left: str, right: str) -> str:
    return "PAIR:" + json.dumps([left, right], ensure_ascii=False, separators=(",", ":"))


def cartesian_observation(left: Sequence[str], right: Sequence[str]) -> tuple[str, ...]:
    return tuple(paired_token(x, y) for x in left for y in right)


def grouping_observation(source: Sequence[str], stencil: Sequence[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not stencil:
        raise ValueError("anonymous stencil must be non-empty")
    completed: list[str] = []
    residue: tuple[str, ...] = ()
    cursor = 0
    while cursor < len(source):
        end = cursor + len(stencil)
        if end > len(source):
            residue = tuple(source[cursor:])
            break
        completed.append(OUTPUT_MARK)
        cursor = end
    return tuple(completed), residue


def encoded_cycle_program_tokens(program: NestedCycleProgram | GroupCycleProgram) -> int:
    return sum(1 + (item.slot is not None) + (item.target is not None) + (item.mode is not None) for item in program.instructions)


def _score_nested(program: NestedCycleProgram, examples: Sequence[NestedExample]) -> CycleCandidate:
    passed = 0
    execution_tokens = 0
    executor = AnonymousCycleExecutor()
    for example in examples:
        result = executor.execute_nested(program, example.sources)
        execution_tokens += result.primitive_execution_tokens
        passed += result.halted and result.output == example.expected_output
    return _candidate(program, passed, len(examples), execution_tokens)


def _score_group(program: GroupCycleProgram, examples: Sequence[GroupExample]) -> CycleCandidate:
    passed = 0
    execution_tokens = 0
    executor = AnonymousCycleExecutor()
    for example in examples:
        result = executor.execute_group(program, example.sources, maximum_steps=5_000)
        execution_tokens += result.primitive_execution_tokens
        passed += result.halted and result.output == example.expected_completed and result.residue == example.expected_residue
    return _candidate(program, passed, len(examples), execution_tokens)


def _candidate(program: NestedCycleProgram | GroupCycleProgram, passed: int, example_count: int, execution_tokens: int) -> CycleCandidate:
    exact = passed == example_count
    program_tokens = encoded_cycle_program_tokens(program)
    total, reward = FoundationRewardPolicy().score(
        exact=exact, passed_example_count=passed,
        execution_token_cost=execution_tokens, program_token_cost=program_tokens,
    )
    return CycleCandidate(program, exact, passed, example_count, execution_tokens, program_tokens, total, reward)


def _select(task_id: str, candidates: Sequence[CycleCandidate]) -> CycleSearchReport:
    exact = [item for item in candidates if item.exact]
    if not exact:
        raise ValueError(f"no exact anonymous cycle program for {task_id}")
    exact.sort(key=lambda item: (-item.reward, item.program.program_id))
    return CycleSearchReport(task_id, len(candidates), exact[0], tuple(candidates))


def _semantic_id(prefix: str, opcode: int, program_id: str, dependencies: Sequence[str], task_id: str) -> str:
    return prefix + "-" + _digest({
        "opcode": opcode, "program_id": program_id,
        "dependencies": list(dependencies), "source_tasks": [task_id],
    })


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
