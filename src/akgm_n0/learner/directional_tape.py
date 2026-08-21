"""Learner-side search for an anonymous two-symbol directional representation."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Sequence

from .foundation_kernel import FoundationRewardPolicy, OUTPUT_MARK, TokenExample
from .reversible_tape import (
    OP_BRANCH_IF_BLANK,
    OP_HALT,
    OP_JUMP,
    OP_MOVE_RIGHT,
    OP_WRITE_ALT_MARK,
    OP_WRITE_BLANK,
    OP_WRITE_MARK,
    OUTPUT_ALT_MARK,
    MultiTapeExecutor,
    TapeInstruction,
)


EMIT_NONE = 0
EMIT_PRIMARY = 1
EMIT_ALTERNATE = 2


@dataclass(frozen=True, slots=True)
class DirectionalPhase:
    source_tapes: tuple[int, ...]
    emit_slot: int

    def to_dict(self) -> dict[str, Any]:
        return {"source_tapes": list(self.source_tapes), "emit_slot": self.emit_slot}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DirectionalPhase":
        return cls(
            tuple(int(item) for item in value["source_tapes"]),
            int(value["emit_slot"]),
        )


@dataclass(frozen=True, slots=True)
class DirectionalProgram:
    program_id: str
    input_tape_count: int
    phases: tuple[DirectionalPhase, ...]
    instructions: tuple[TapeInstruction, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "input_tape_count": self.input_tape_count,
            "phases": [item.to_dict() for item in self.phases],
            "instructions": [item.to_dict() for item in self.instructions],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DirectionalProgram":
        return cls(
            str(value["program_id"]),
            int(value["input_tape_count"]),
            tuple(DirectionalPhase.from_dict(item) for item in value["phases"]),
            tuple(TapeInstruction.from_dict(item) for item in value["instructions"]),
        )


@dataclass(frozen=True, slots=True)
class DirectionalCandidate:
    program: DirectionalProgram
    exact: bool
    passed_example_count: int
    example_count: int
    execution_token_cost: int
    program_token_cost: int
    total_token_cost: int
    reward: int


@dataclass(frozen=True, slots=True)
class DirectionalSearchReport:
    task_id: str
    candidates_evaluated: int
    selected: DirectionalCandidate
    candidates: tuple[DirectionalCandidate, ...]


@dataclass(frozen=True, slots=True)
class DirectionalFoundationSemantic:
    semantic_id: str
    opcode: int
    program: DirectionalProgram
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
    def from_dict(cls, value: dict[str, Any]) -> "DirectionalFoundationSemantic":
        return cls(
            str(value["semantic_id"]),
            int(value["opcode"]),
            DirectionalProgram.from_dict(dict(value["program"])),
            tuple(str(item) for item in value["dependency_semantic_ids"]),
            tuple(str(item) for item in value["source_task_ids"]),
        )


class DirectionalTapeSearch:
    def enumerate_candidates(
        self,
        task_id: str,
        examples: Sequence[TokenExample],
        *,
        maximum_phases: int = 3,
    ) -> tuple[DirectionalCandidate, ...]:
        phase_options = tuple(
            DirectionalPhase(tuple(source_tapes), emit_slot)
            for width in (1, 2)
            for source_tapes in itertools.combinations(range(2), width)
            for emit_slot in (EMIT_NONE, EMIT_PRIMARY, EMIT_ALTERNATE)
        )
        candidates: list[DirectionalCandidate] = []
        policy = FoundationRewardPolicy()
        for phase_count in range(maximum_phases + 1):
            for phases in itertools.product(phase_options, repeat=phase_count):
                program = compile_directional_program(phases)
                passed = 0
                execution_tokens = 0
                for example in examples:
                    execution = MultiTapeExecutor().execute(program, example.sources)
                    execution_tokens += execution.primitive_execution_tokens
                    passed += execution.halted and execution.output == example.expected_output
                exact = passed == len(examples)
                program_tokens = encoded_directional_program_tokens(program)
                total_tokens, reward = policy.score(
                    exact=exact,
                    passed_example_count=passed,
                    execution_token_cost=execution_tokens,
                    program_token_cost=program_tokens,
                )
                candidates.append(
                    DirectionalCandidate(
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
        examples: Sequence[TokenExample],
        *,
        maximum_phases: int = 3,
    ) -> DirectionalSearchReport:
        candidates = self.enumerate_candidates(
            task_id, examples, maximum_phases=maximum_phases
        )
        exact = [item for item in candidates if item.exact]
        if not exact:
            raise ValueError(f"no exact directional program for {task_id}")
        exact.sort(key=lambda item: (-item.reward, _phase_key(item.program.phases)))
        return DirectionalSearchReport(task_id, len(candidates), exact[0], candidates)


class DirectionalSemanticInducer:
    def induce(
        self,
        report: DirectionalSearchReport,
        *,
        opcode: int,
        dependency_semantic_ids: Sequence[str],
    ) -> DirectionalFoundationSemantic:
        payload = {
            "opcode": opcode,
            "program_id": report.selected.program.program_id,
            "dependencies": list(dependency_semantic_ids),
            "source_tasks": [report.task_id],
        }
        semantic_id = "DSEM-" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16]
        return DirectionalFoundationSemantic(
            semantic_id,
            opcode,
            report.selected.program,
            tuple(dependency_semantic_ids),
            (report.task_id,),
        )


def compile_directional_program(
    phases: Sequence[DirectionalPhase],
) -> DirectionalProgram:
    instructions: list[TapeInstruction] = []
    output_tape = 2
    for phase in phases:
        loop_start = len(instructions)
        branch_indices: list[int] = []
        for tape in phase.source_tapes:
            branch_indices.append(len(instructions))
            instructions.append(TapeInstruction(OP_BRANCH_IF_BLANK, tape=tape, target=-1))
        for tape in phase.source_tapes:
            instructions.append(TapeInstruction(OP_WRITE_BLANK, tape=tape))
            instructions.append(TapeInstruction(OP_MOVE_RIGHT, tape=tape))
        if phase.emit_slot != EMIT_NONE:
            opcode = OP_WRITE_MARK if phase.emit_slot == EMIT_PRIMARY else OP_WRITE_ALT_MARK
            instructions.append(TapeInstruction(opcode, tape=output_tape))
            instructions.append(TapeInstruction(OP_MOVE_RIGHT, tape=output_tape))
        instructions.append(TapeInstruction(OP_JUMP, target=loop_start))
        loop_exit = len(instructions)
        for index in branch_indices:
            old = instructions[index]
            instructions[index] = TapeInstruction(old.opcode, tape=old.tape, target=loop_exit)
    instructions.append(TapeInstruction(OP_HALT))
    payload = {
        "input_tape_count": 2,
        "phases": [item.to_dict() for item in phases],
        "instructions": [item.to_dict() for item in instructions],
    }
    program_id = "DTP-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    return DirectionalProgram(program_id, 2, tuple(phases), tuple(instructions))


def signed_unary_output(left: int, right: int) -> tuple[str, ...]:
    if left >= right:
        return tuple(OUTPUT_MARK for _ in range(left - right))
    return tuple(OUTPUT_ALT_MARK for _ in range(right - left))


def decode_signed_unary(output: Sequence[str]) -> int:
    primary = sum(item == OUTPUT_MARK for item in output)
    alternate = sum(item == OUTPUT_ALT_MARK for item in output)
    if primary and alternate:
        raise ValueError("directional output is not normalized")
    return primary if primary else -alternate


def encoded_directional_program_tokens(program: DirectionalProgram) -> int:
    return sum(
        1 + (item.tape is not None) + (item.target is not None)
        for item in program.instructions
    )


def _phase_key(phases: Sequence[DirectionalPhase]) -> str:
    return json.dumps(
        [item.to_dict() for item in phases], sort_keys=True, separators=(",", ":")
    )

