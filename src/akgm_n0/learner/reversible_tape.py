"""Anonymous multi-tape symbol machine for post-counting foundation growth."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Sequence

from .foundation_kernel import FoundationRewardPolicy, OUTPUT_MARK, TokenExample


OP_BRANCH_IF_BLANK = 0
OP_WRITE_BLANK = 1
OP_WRITE_MARK = 2
OP_MOVE_RIGHT = 3
OP_JUMP = 4
OP_HALT = 5
OP_WRITE_ALT_MARK = 6
REVERSIBLE_TAPE_OPCODES = frozenset(
    {OP_BRANCH_IF_BLANK, OP_WRITE_BLANK, OP_WRITE_MARK, OP_MOVE_RIGHT, OP_JUMP, OP_HALT, OP_WRITE_ALT_MARK}
)
BLANK = ""
OUTPUT_ALT_MARK = "○"


@dataclass(frozen=True, slots=True)
class TapeInstruction:
    opcode: int
    tape: int | None = None
    target: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"opcode": self.opcode}
        if self.tape is not None:
            result["tape"] = self.tape
        if self.target is not None:
            result["target"] = self.target
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TapeInstruction":
        return cls(
            int(value["opcode"]),
            None if "tape" not in value else int(value["tape"]),
            None if "target" not in value else int(value["target"]),
        )


@dataclass(frozen=True, slots=True)
class TapePhase:
    source_tapes: tuple[int, ...]
    emit_mark: bool

    def to_dict(self) -> dict[str, Any]:
        return {"source_tapes": list(self.source_tapes), "emit_mark": self.emit_mark}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TapePhase":
        return cls(
            tuple(int(item) for item in value["source_tapes"]),
            bool(value["emit_mark"]),
        )


@dataclass(frozen=True, slots=True)
class TapeProgram:
    program_id: str
    input_tape_count: int
    phases: tuple[TapePhase, ...]
    instructions: tuple[TapeInstruction, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "input_tape_count": self.input_tape_count,
            "phases": [item.to_dict() for item in self.phases],
            "instructions": [item.to_dict() for item in self.instructions],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TapeProgram":
        return cls(
            str(value["program_id"]),
            int(value["input_tape_count"]),
            tuple(TapePhase.from_dict(item) for item in value["phases"]),
            tuple(TapeInstruction.from_dict(item) for item in value["instructions"]),
        )


@dataclass(frozen=True, slots=True)
class TapeExecution:
    halted: bool
    output: tuple[str, ...]
    remaining_input_counts: tuple[int, ...]
    heads: tuple[int, ...]
    primitive_execution_tokens: int


@dataclass(frozen=True, slots=True)
class TapeCandidate:
    program: TapeProgram
    exact: bool
    passed_example_count: int
    example_count: int
    execution_token_cost: int
    program_token_cost: int
    total_token_cost: int
    reward: int


@dataclass(frozen=True, slots=True)
class TapeSearchReport:
    task_id: str
    candidates_evaluated: int
    selected: TapeCandidate
    candidates: tuple[TapeCandidate, ...]


@dataclass(frozen=True, slots=True)
class ReversibleFoundationSemantic:
    semantic_id: str
    opcode: int
    program: TapeProgram
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
    def from_dict(cls, value: dict[str, Any]) -> "ReversibleFoundationSemantic":
        return cls(
            str(value["semantic_id"]),
            int(value["opcode"]),
            TapeProgram.from_dict(dict(value["program"])),
            tuple(str(item) for item in value["dependency_semantic_ids"]),
            tuple(str(item) for item in value["source_task_ids"]),
        )


class MultiTapeExecutor:
    """Run generic read/write/move/control opcodes over finite symbol tapes."""

    def execute(
        self,
        program: TapeProgram,
        sources: Sequence[Sequence[str]],
        *,
        maximum_steps: int = 1_000_000,
    ) -> TapeExecution:
        if len(sources) != program.input_tape_count:
            raise ValueError("source count does not match tape program")
        tapes: list[dict[int, str]] = [
            {index: value for index, value in enumerate(source)} for source in sources
        ]
        tapes.append({})
        heads = [0 for _ in tapes]
        pc = 0
        tokens = 0
        halted = False
        while 0 <= pc < len(program.instructions) and tokens < maximum_steps:
            instruction = program.instructions[pc]
            tokens += 1
            if instruction.opcode == OP_BRANCH_IF_BLANK:
                if instruction.tape is None or instruction.target is None:
                    raise ValueError("blank branch is incomplete")
                value = tapes[instruction.tape].get(heads[instruction.tape], BLANK)
                pc = instruction.target if value == BLANK else pc + 1
            elif instruction.opcode == OP_WRITE_BLANK:
                if instruction.tape is None:
                    raise ValueError("blank write is incomplete")
                tapes[instruction.tape].pop(heads[instruction.tape], None)
                pc += 1
            elif instruction.opcode == OP_WRITE_MARK:
                if instruction.tape is None:
                    raise ValueError("mark write is incomplete")
                tapes[instruction.tape][heads[instruction.tape]] = OUTPUT_MARK
                pc += 1
            elif instruction.opcode == OP_WRITE_ALT_MARK:
                if instruction.tape is None:
                    raise ValueError("alternate mark write is incomplete")
                tapes[instruction.tape][heads[instruction.tape]] = OUTPUT_ALT_MARK
                pc += 1
            elif instruction.opcode == OP_MOVE_RIGHT:
                if instruction.tape is None:
                    raise ValueError("move is incomplete")
                heads[instruction.tape] += 1
                pc += 1
            elif instruction.opcode == OP_JUMP:
                if instruction.target is None:
                    raise ValueError("jump is incomplete")
                pc = instruction.target
            elif instruction.opcode == OP_HALT:
                halted = True
                break
            else:
                raise ValueError(f"unknown tape opcode: {instruction.opcode}")
        output_tape = tapes[program.input_tape_count]
        output = tuple(output_tape[index] for index in sorted(output_tape))
        remaining = tuple(len(tapes[index]) for index in range(program.input_tape_count))
        return TapeExecution(halted, output, remaining, tuple(heads), tokens)


class ReversibleTapeSearch:
    """Enumerate anonymous synchronized and single-tape traversal phases."""

    def enumerate_candidates(
        self,
        task_id: str,
        input_tape_count: int,
        examples: Sequence[TokenExample],
        *,
        maximum_phases: int = 2,
    ) -> tuple[TapeCandidate, ...]:
        phase_options = tuple(
            TapePhase(tuple(subset), emit)
            for width in range(1, min(2, input_tape_count) + 1)
            for subset in itertools.combinations(range(input_tape_count), width)
            for emit in (False, True)
        )
        candidates: list[TapeCandidate] = []
        policy = FoundationRewardPolicy()
        for phase_count in range(maximum_phases + 1):
            for phases in itertools.product(phase_options, repeat=phase_count):
                program = compile_tape_program(input_tape_count, phases)
                passed = 0
                execution_tokens = 0
                for example in examples:
                    execution = MultiTapeExecutor().execute(program, example.sources)
                    execution_tokens += execution.primitive_execution_tokens
                    passed += execution.halted and execution.output == example.expected_output
                exact = passed == len(examples)
                program_tokens = encoded_tape_program_tokens(program)
                total_tokens, reward = policy.score(
                    exact=exact,
                    passed_example_count=passed,
                    execution_token_cost=execution_tokens,
                    program_token_cost=program_tokens,
                )
                candidates.append(
                    TapeCandidate(
                        program,
                        exact,
                        passed,
                        len(examples),
                        execution_tokens,
                        program_tokens,
                        total_tokens,
                        reward,
                    )
                )
        return tuple(candidates)

    def search(
        self,
        task_id: str,
        input_tape_count: int,
        examples: Sequence[TokenExample],
        *,
        maximum_phases: int = 2,
    ) -> TapeSearchReport:
        candidates = self.enumerate_candidates(
            task_id, input_tape_count, examples, maximum_phases=maximum_phases
        )
        exact = [item for item in candidates if item.exact]
        if not exact:
            raise ValueError(f"no exact reversible tape program for {task_id}")
        exact.sort(key=lambda item: (-item.reward, _phase_key(item.program.phases)))
        return TapeSearchReport(task_id, len(candidates), exact[0], candidates)


class ReversibleSemanticInducer:
    def induce(
        self,
        report: TapeSearchReport,
        *,
        opcode: int,
        dependency_semantic_ids: Sequence[str],
    ) -> ReversibleFoundationSemantic:
        payload = {
            "opcode": opcode,
            "program_id": report.selected.program.program_id,
            "dependencies": list(dependency_semantic_ids),
            "source_tasks": [report.task_id],
        }
        semantic_id = "RSEM-" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16]
        return ReversibleFoundationSemantic(
            semantic_id,
            opcode,
            report.selected.program,
            tuple(dependency_semantic_ids),
            (report.task_id,),
        )


def compile_tape_program(
    input_tape_count: int, phases: Sequence[TapePhase]
) -> TapeProgram:
    instructions: list[TapeInstruction] = []
    for phase in phases:
        loop_start = len(instructions)
        branch_indices: list[int] = []
        for tape in phase.source_tapes:
            branch_indices.append(len(instructions))
            instructions.append(TapeInstruction(OP_BRANCH_IF_BLANK, tape=tape, target=-1))
        for tape in phase.source_tapes:
            instructions.append(TapeInstruction(OP_WRITE_BLANK, tape=tape))
            instructions.append(TapeInstruction(OP_MOVE_RIGHT, tape=tape))
        if phase.emit_mark:
            instructions.append(TapeInstruction(OP_WRITE_MARK, tape=input_tape_count))
            instructions.append(TapeInstruction(OP_MOVE_RIGHT, tape=input_tape_count))
        instructions.append(TapeInstruction(OP_JUMP, target=loop_start))
        loop_exit = len(instructions)
        for index in branch_indices:
            old = instructions[index]
            instructions[index] = TapeInstruction(old.opcode, tape=old.tape, target=loop_exit)
    instructions.append(TapeInstruction(OP_HALT))
    payload = {
        "input_tape_count": input_tape_count,
        "phases": [item.to_dict() for item in phases],
        "instructions": [item.to_dict() for item in instructions],
    }
    program_id = "RTP-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    return TapeProgram(program_id, input_tape_count, tuple(phases), tuple(instructions))


def encoded_tape_program_tokens(program: TapeProgram) -> int:
    return sum(
        1 + (item.tape is not None) + (item.target is not None)
        for item in program.instructions
    )


def _phase_key(phases: Sequence[TapePhase]) -> str:
    return json.dumps(
        [item.to_dict() for item in phases], sort_keys=True, separators=(",", ":")
    )
