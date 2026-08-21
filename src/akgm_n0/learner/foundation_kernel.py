"""Zero-arithmetic token machine and anonymous program search.

The learner-facing instruction set contains no numeric arithmetic operation.
Quantities are represented only by finite collections of opaque symbols.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Sequence


OP_TEST_EMPTY = 0
OP_DISCARD_SYMBOL = 1
OP_EMIT_MARK = 2
OP_JUMP = 3
OP_HALT = 4
FOUNDATION_OPCODES = frozenset(
    {OP_TEST_EMPTY, OP_DISCARD_SYMBOL, OP_EMIT_MARK, OP_JUMP, OP_HALT}
)
OUTPUT_MARK = "●"


@dataclass(frozen=True, slots=True)
class FoundationInstruction:
    opcode: int
    operand: int | None = None
    target: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"opcode": self.opcode}
        if self.operand is not None:
            result["operand"] = self.operand
        if self.target is not None:
            result["target"] = self.target
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FoundationInstruction":
        return cls(
            int(value["opcode"]),
            None if "operand" not in value else int(value["operand"]),
            None if "target" not in value else int(value["target"]),
        )


@dataclass(frozen=True, slots=True)
class FoundationProgram:
    program_id: str
    source_plan: tuple[int, ...]
    instructions: tuple[FoundationInstruction, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "source_plan": list(self.source_plan),
            "instructions": [item.to_dict() for item in self.instructions],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FoundationProgram":
        return cls(
            str(value["program_id"]),
            tuple(int(item) for item in value["source_plan"]),
            tuple(FoundationInstruction.from_dict(item) for item in value["instructions"]),
        )


@dataclass(frozen=True, slots=True)
class TokenExample:
    sources: tuple[tuple[str, ...], ...]
    expected_output: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AnonymousTokenTask:
    task_id: str
    source_count: int
    examples: tuple[TokenExample, ...]


@dataclass(frozen=True, slots=True)
class FoundationExecution:
    halted: bool
    output: tuple[str, ...]
    remaining_sources: tuple[tuple[str, ...], ...]
    steps: int


@dataclass(frozen=True, slots=True)
class FoundationCandidate:
    program: FoundationProgram
    exact: bool
    passed_example_count: int
    example_count: int
    execution_token_cost: int
    program_token_cost: int
    total_token_cost: int
    reward: int


@dataclass(frozen=True, slots=True)
class FoundationRewardPolicy:
    """Reward correctness first, then fewer honest primitive tokens.

    ``execution_token_cost`` counts expanded primitive instruction dispatches.
    A future macro therefore cannot hide work by charging only one invocation.
    """

    exact_completion_reward: int = 1_000_000
    partial_case_reward: int = 1_000

    def score(
        self,
        *,
        exact: bool,
        passed_example_count: int,
        execution_token_cost: int,
        program_token_cost: int,
    ) -> tuple[int, int]:
        total_token_cost = execution_token_cost + program_token_cost
        correctness_reward = (
            self.exact_completion_reward
            if exact
            else passed_example_count * self.partial_case_reward
        )
        return total_token_cost, correctness_reward - total_token_cost


@dataclass(frozen=True, slots=True)
class FoundationSearchReport:
    task_id: str
    candidates_evaluated: int
    selected: FoundationCandidate
    rejected: tuple[FoundationCandidate, ...]


@dataclass(frozen=True, slots=True)
class FoundationSemantic:
    semantic_id: str
    opcode: int
    source_slots: tuple[int, ...]
    program: FoundationProgram
    dependency_semantic_ids: tuple[str, ...]
    source_task_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id,
            "opcode": self.opcode,
            "source_slots": list(self.source_slots),
            "program": self.program.to_dict(),
            "dependency_semantic_ids": list(self.dependency_semantic_ids),
            "source_task_ids": list(self.source_task_ids),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FoundationSemantic":
        return cls(
            str(value["semantic_id"]),
            int(value["opcode"]),
            tuple(int(item) for item in value["source_slots"]),
            FoundationProgram.from_dict(dict(value["program"])),
            tuple(str(item) for item in value["dependency_semantic_ids"]),
            tuple(str(item) for item in value["source_task_ids"]),
        )


class ZeroArithmeticExecutor:
    """Execute only symbol/control instructions under a finite step budget."""

    def execute(
        self,
        program: FoundationProgram,
        sources: Sequence[Sequence[str]],
        *,
        maximum_steps: int = 100_000,
    ) -> FoundationExecution:
        memory = [list(source) for source in sources]
        output: list[str] = []
        pc = 0
        steps = 0
        while 0 <= pc < len(program.instructions) and steps < maximum_steps:
            instruction = program.instructions[pc]
            steps += 1
            if instruction.opcode == OP_TEST_EMPTY:
                if instruction.operand is None or instruction.target is None:
                    raise ValueError("empty-test instruction is incomplete")
                pc = instruction.target if not memory[instruction.operand] else pc + 1
            elif instruction.opcode == OP_DISCARD_SYMBOL:
                if instruction.operand is None or not memory[instruction.operand]:
                    raise ValueError("cannot discard from an empty source")
                memory[instruction.operand].pop(0)
                pc += 1
            elif instruction.opcode == OP_EMIT_MARK:
                output.append(OUTPUT_MARK)
                pc += 1
            elif instruction.opcode == OP_JUMP:
                if instruction.target is None:
                    raise ValueError("jump instruction is incomplete")
                pc = instruction.target
            elif instruction.opcode == OP_HALT:
                return FoundationExecution(
                    True,
                    tuple(output),
                    tuple(tuple(source) for source in memory),
                    steps,
                )
            else:
                raise ValueError(f"unknown foundation opcode: {instruction.opcode}")
        return FoundationExecution(
            False,
            tuple(output),
            tuple(tuple(source) for source in memory),
            steps,
        )


class FoundationProgramSearch:
    """Enumerate anonymous drain-loop programs without formula targets."""

    def enumerate_candidates(
        self, task: AnonymousTokenTask
    ) -> tuple[FoundationCandidate, ...]:
        candidates: list[FoundationCandidate] = []
        reward_policy = FoundationRewardPolicy()
        for loop_count in range(0, task.source_count + 2):
            for source_plan in itertools.product(range(task.source_count), repeat=loop_count):
                program = compile_source_plan(source_plan)
                passed = 0
                exact = True
                execution_token_cost = 0
                for example in task.examples:
                    execution = ZeroArithmeticExecutor().execute(program, example.sources)
                    execution_token_cost += execution.steps
                    case_passed = execution.halted and execution.output == example.expected_output
                    passed += case_passed
                    exact = exact and case_passed
                program_token_cost = encoded_program_token_cost(program)
                total_token_cost, reward = reward_policy.score(
                    exact=exact,
                    passed_example_count=passed,
                    execution_token_cost=execution_token_cost,
                    program_token_cost=program_token_cost,
                )
                candidates.append(
                    FoundationCandidate(
                        program,
                        exact,
                        passed,
                        len(task.examples),
                        execution_token_cost,
                        program_token_cost,
                        total_token_cost,
                        reward,
                    )
                )
        return tuple(candidates)

    def search(self, task: AnonymousTokenTask) -> FoundationSearchReport:
        candidates = list(self.enumerate_candidates(task))
        exact_candidates = [item for item in candidates if item.exact]
        if not exact_candidates:
            raise ValueError(f"no exact foundation program for {task.task_id}")
        exact_candidates.sort(
            key=lambda item: (-item.reward, item.program.source_plan)
        )
        selected = exact_candidates[0]
        rejected = tuple(
            item for item in candidates if item.program.program_id != selected.program.program_id
        )
        return FoundationSearchReport(task.task_id, len(candidates), selected, rejected)


class FoundationSemanticInducer:
    """Compress proven anonymous token-transfer programs into new operations."""

    def induce(
        self,
        report: FoundationSearchReport,
        *,
        opcode: int,
        dependencies: Sequence[FoundationSemantic] = (),
    ) -> FoundationSemantic:
        program = report.selected.program
        payload = {
            "opcode": opcode,
            "source_slots": list(program.source_plan),
            "program_id": program.program_id,
            "dependencies": [item.semantic_id for item in dependencies],
            "source_tasks": [report.task_id],
        }
        semantic_id = "FSEM-" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16]
        return FoundationSemantic(
            semantic_id,
            opcode,
            program.source_plan,
            program,
            tuple(item.semantic_id for item in dependencies),
            (report.task_id,),
        )


class FoundationSemanticExecutor:
    def execute(
        self, semantic: FoundationSemantic, sources: Sequence[Sequence[str]]
    ) -> tuple[str, ...]:
        execution = ZeroArithmeticExecutor().execute(semantic.program, sources)
        if not execution.halted:
            raise ValueError("foundation semantic did not halt")
        return execution.output


def compile_source_plan(source_plan: Sequence[int]) -> FoundationProgram:
    instructions: list[FoundationInstruction] = []
    for source in source_plan:
        loop_start = len(instructions)
        loop_exit = loop_start + 4
        instructions.extend(
            (
                FoundationInstruction(OP_TEST_EMPTY, operand=int(source), target=loop_exit),
                FoundationInstruction(OP_DISCARD_SYMBOL, operand=int(source)),
                FoundationInstruction(OP_EMIT_MARK),
                FoundationInstruction(OP_JUMP, target=loop_start),
            )
        )
    instructions.append(FoundationInstruction(OP_HALT))
    payload = {
        "source_plan": list(source_plan),
        "instructions": [item.to_dict() for item in instructions],
    }
    program_id = "FKP-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    return FoundationProgram(program_id, tuple(int(item) for item in source_plan), tuple(instructions))


def opaque_symbols(prefix: str, count: int) -> tuple[str, ...]:
    """Evaluator helper: create distinct opaque objects, not numeric inputs."""

    return tuple(f"{prefix}:{index}" for index in range(count))


def unary_marks(count: int) -> tuple[str, ...]:
    return tuple(OUTPUT_MARK for _ in range(count))


def encoded_program_token_cost(program: FoundationProgram) -> int:
    """Count opcode and explicit operand/target fields in the stored program."""

    return sum(
        1 + (instruction.operand is not None) + (instruction.target is not None)
        for instruction in program.instructions
    )
