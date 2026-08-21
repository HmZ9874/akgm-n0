"""Unified primitive counter VM, learned proposal policy, CEGIS, and macro mining.

V15 intentionally separates two claims:

* the execution/search substrate is shared by every task and contains no named
  arithmetic opcode;
* the initial successful programs are migrated training memories from the
  already audited V10-V12 rooms, not cold-start discoveries.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from typing import Any, Iterable, Sequence


VM_OPS = frozenset({"u_zero", "u_unit", "u_inc", "u_dec", "u_jz", "u_jump", "u_emit", "u_halt"})
REGISTER_OPS = frozenset({"u_zero", "u_unit", "u_inc", "u_dec", "u_jz", "u_emit"})
FORBIDDEN_PROGRAM_TERMS = ("multiply", "multiplication", "divide", "division", "quotient", "remainder", "power", "exponent", "modulo")


class UnifiedVMError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class UInstruction:
    op: str
    register: int | None = None
    target: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"op": self.op}
        if self.register is not None:
            result["register"] = self.register
        if self.target is not None:
            result["target"] = self.target
        return result


@dataclass(frozen=True, slots=True)
class UnifiedProgram:
    program_id: str
    register_count: int
    input_registers: tuple[int, ...]
    instructions: tuple[UInstruction, ...]
    provenance: str = "migrated_verified_memory"

    @property
    def primitive_token_cost(self) -> int:
        return sum(1 + (item.register is not None) + (item.target is not None) for item in self.instructions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "unified_primitive_counter_vm_v15",
            "program_id": self.program_id,
            "register_count": self.register_count,
            "input_registers": list(self.input_registers),
            "instructions": [item.to_dict() for item in self.instructions],
            "provenance": self.provenance,
        }


@dataclass(frozen=True, slots=True)
class UnifiedExecution:
    outputs: tuple[int, ...]
    final_registers: tuple[int, ...]
    steps: int
    trace: tuple[tuple[int, str, tuple[int, ...]], ...]


class UnifiedCounterVM:
    def __init__(self, *, maximum_steps: int = 2_000_000, maximum_registers: int = 16, trace_limit: int = 256) -> None:
        self.maximum_steps = maximum_steps
        self.maximum_registers = maximum_registers
        self.trace_limit = trace_limit

    def validate(self, program: UnifiedProgram) -> None:
        if not 1 <= program.register_count <= self.maximum_registers:
            raise UnifiedVMError("register boundary is invalid")
        if not program.instructions or len(program.instructions) > 512:
            raise UnifiedVMError("instruction boundary is invalid")
        if len(set(program.input_registers)) != len(program.input_registers):
            raise UnifiedVMError("input registers must be distinct")
        if any(index < 0 or index >= program.register_count for index in program.input_registers):
            raise UnifiedVMError("input register is unavailable")
        for item in program.instructions:
            if item.op not in VM_OPS:
                raise UnifiedVMError("unregistered primitive opcode")
            if item.op in REGISTER_OPS:
                if item.register is None or not 0 <= item.register < program.register_count:
                    raise UnifiedVMError("instruction register is unavailable")
            elif item.register is not None:
                raise UnifiedVMError("non-register opcode carries a register")
            if item.op in {"u_jz", "u_jump"}:
                if item.target is None or not 0 <= item.target < len(program.instructions):
                    raise UnifiedVMError("jump target is unavailable")
            elif item.target is not None:
                raise UnifiedVMError("non-jump opcode carries a target")
        if program.instructions[-1].op != "u_halt":
            raise UnifiedVMError("program must end in halt")

    def execute(self, program: UnifiedProgram, inputs: Sequence[int]) -> UnifiedExecution:
        self.validate(program)
        if len(inputs) != len(program.input_registers):
            raise UnifiedVMError("input arity differs")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in inputs):
            raise UnifiedVMError("VM inputs must be natural counters")
        registers = [0] * program.register_count
        for register, value in zip(program.input_registers, inputs, strict=True):
            registers[register] = value
        outputs: list[int] = []
        trace: list[tuple[int, str, tuple[int, ...]]] = []
        pc = 0
        for step in range(self.maximum_steps + 1):
            if not 0 <= pc < len(program.instructions):
                raise UnifiedVMError("instruction pointer escaped")
            item = program.instructions[pc]
            if len(trace) < self.trace_limit:
                trace.append((pc, item.op, tuple(registers)))
            next_pc = pc + 1
            if item.op == "u_halt":
                if not outputs:
                    raise UnifiedVMError("program halted without output")
                return UnifiedExecution(tuple(outputs), tuple(registers), step, tuple(trace))
            if step == self.maximum_steps:
                break
            if item.op == "u_zero":
                registers[item.register] = 0  # type: ignore[index]
            elif item.op == "u_unit":
                registers[item.register] = 1  # type: ignore[index]
            elif item.op == "u_inc":
                registers[item.register] += 1  # type: ignore[index]
            elif item.op == "u_dec":
                assert item.register is not None
                if registers[item.register] == 0:
                    raise UnifiedVMError("cannot decrement an empty counter")
                registers[item.register] -= 1
            elif item.op == "u_jz":
                assert item.register is not None
                if registers[item.register] == 0:
                    next_pc = item.target  # type: ignore[assignment]
            elif item.op == "u_jump":
                next_pc = item.target  # type: ignore[assignment]
            elif item.op == "u_emit":
                outputs.append(registers[item.register])  # type: ignore[index]
            pc = next_pc
        raise UnifiedVMError("program did not halt inside the step boundary")


class Node:
    pass


@dataclass(frozen=True, slots=True)
class Unit(Node):
    op: str
    register: int


@dataclass(frozen=True, slots=True)
class SequenceNode(Node):
    children: tuple[Node, ...]


@dataclass(frozen=True, slots=True)
class WhileNode(Node):
    register: int
    body: Node


@dataclass(frozen=True, slots=True)
class IfZeroNode(Node):
    register: int
    body: Node


@dataclass(frozen=True, slots=True)
class EmitNode(Node):
    register: int


class UnifiedCompiler:
    """Compile generic structured control into only the eight primitive opcodes."""

    def compile(self, root: Node, *, register_count: int, input_registers: tuple[int, ...], provenance: str) -> UnifiedProgram:
        instructions: list[UInstruction] = []

        def emit(node: Node) -> None:
            if isinstance(node, Unit):
                instructions.append(UInstruction(node.op, register=node.register))
            elif isinstance(node, EmitNode):
                instructions.append(UInstruction("u_emit", register=node.register))
            elif isinstance(node, SequenceNode):
                for child in node.children:
                    emit(child)
            elif isinstance(node, WhileNode):
                start = len(instructions)
                guard = len(instructions)
                instructions.append(UInstruction("u_jz", register=node.register, target=0))
                emit(node.body)
                instructions.append(UInstruction("u_jump", target=start))
                instructions[guard] = replace(instructions[guard], target=len(instructions))
            elif isinstance(node, IfZeroNode):
                guard = len(instructions)
                instructions.append(UInstruction("u_jz", register=node.register, target=0))
                skip = len(instructions)
                instructions.append(UInstruction("u_jump", target=0))
                instructions[guard] = replace(instructions[guard], target=len(instructions))
                emit(node.body)
                instructions[skip] = replace(instructions[skip], target=len(instructions))
            else:
                raise TypeError("unknown structured node")

        emit(root)
        instructions.append(UInstruction("u_halt"))
        payload = {
            "register_count": register_count,
            "input_registers": input_registers,
            "instructions": [item.to_dict() for item in instructions],
        }
        program_id = "UVM-" + hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
        program = UnifiedProgram(program_id, register_count, input_registers, tuple(instructions), provenance)
        UnifiedCounterVM().validate(program)
        return program


def seq(*nodes: Node) -> SequenceNode:
    return SequenceNode(tuple(nodes))


def drain(source: int, *destinations: int) -> WhileNode:
    return WhileNode(source, seq(Unit("u_dec", source), *(Unit("u_inc", item) for item in destinations)))


def preserve_copy(source: int, destination: int, scratch: int) -> SequenceNode:
    return seq(drain(source, destination, scratch), drain(scratch, source))


def migrated_training_programs() -> dict[str, UnifiedProgram]:
    """Compile the three audited memories into one primitive substrate.

    Opaque ids deliberately carry no mathematical names.  This function is a
    migration bridge and is never described as cold-start synthesis.
    """

    compiler = UnifiedCompiler()
    first = compiler.compile(
        seq(
            WhileNode(0, seq(Unit("u_dec", 0), drain(3, 1), drain(1, 2, 3))),
            EmitNode(2),
        ),
        register_count=4,
        input_registers=(0, 1),
        provenance="strict_room_v10_migration",
    )
    second = compiler.compile(
        seq(
            preserve_copy(1, 4, 5),
            WhileNode(
                0,
                seq(
                    Unit("u_dec", 0),
                    Unit("u_dec", 4),
                    Unit("u_inc", 3),
                    IfZeroNode(
                        4,
                        seq(Unit("u_inc", 2), drain(3), preserve_copy(1, 4, 5)),
                    ),
                ),
            ),
            EmitNode(2),
            EmitNode(3),
        ),
        register_count=6,
        input_registers=(0, 1),
        provenance="strict_room_v11_migration",
    )
    third = compiler.compile(
        seq(
            Unit("u_unit", 2),
            WhileNode(
                1,
                seq(
                    Unit("u_dec", 1),
                    Unit("u_zero", 3),
                    WhileNode(2, seq(Unit("u_dec", 2), preserve_copy(0, 3, 4))),
                    drain(3, 2),
                ),
            ),
            EmitNode(2),
        ),
        register_count=5,
        input_registers=(0, 1),
        provenance="strict_room_v12_migration",
    )
    return {"WORLD-7f3a": first, "WORLD-b184": second, "WORLD-43de": third}


def rename_registers(program: UnifiedProgram, permutation: Sequence[int]) -> UnifiedProgram:
    if sorted(permutation) != list(range(program.register_count)):
        raise ValueError("register permutation is invalid")
    instructions = tuple(
        replace(item, register=None if item.register is None else permutation[item.register])
        for item in program.instructions
    )
    input_registers = tuple(permutation[item] for item in program.input_registers)
    payload = {"instructions": [item.to_dict() for item in instructions], "input_registers": input_registers}
    return UnifiedProgram(
        "UVM-" + hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16],
        program.register_count,
        input_registers,
        instructions,
        "register_renamed_reconstruction",
    )


def program_mutations(program: UnifiedProgram, *, maximum: int = 160) -> tuple[UnifiedProgram, ...]:
    mutations: list[UnifiedProgram] = []
    for index, item in enumerate(program.instructions):
        replacements: list[UInstruction] = []
        if item.op == "u_inc":
            replacements.append(replace(item, op="u_dec"))
        elif item.op == "u_dec":
            replacements.append(replace(item, op="u_inc"))
        elif item.op == "u_unit":
            replacements.append(replace(item, op="u_zero"))
        elif item.op == "u_zero":
            replacements.append(replace(item, op="u_unit"))
        if item.register is not None:
            replacements.extend(replace(item, register=register) for register in range(program.register_count) if register != item.register)
        for replacement in replacements:
            instructions = list(program.instructions)
            instructions[index] = replacement
            payload = [value.to_dict() for value in instructions]
            mutations.append(UnifiedProgram(
                "UMUT-" + hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16],
                program.register_count,
                program.input_registers,
                tuple(instructions),
                "generic_single_instruction_mutation",
            ))
            if len(mutations) >= maximum:
                return tuple(mutations)
    return tuple(mutations)


@dataclass(frozen=True, slots=True)
class ProposalScore:
    program_id: str
    score: float
    positive_features: int
    negative_features: int


class RecurrentProposalPolicy:
    """A non-Transformer first-order recurrent policy over primitive opcodes."""

    def __init__(self) -> None:
        self.start_counts: Counter[str] = Counter()
        self.transition_counts: Counter[tuple[str, str]] = Counter()
        self.negative_transitions: Counter[tuple[str, str]] = Counter()

    def fit(self, successes: Sequence[UnifiedProgram], mistakes: Sequence[UnifiedProgram]) -> None:
        for program in successes:
            ops = tuple(item.op for item in program.instructions)
            self.start_counts[ops[0]] += 1
            self.transition_counts.update(zip(ops, ops[1:], strict=False))
        for program in mistakes:
            ops = tuple(item.op for item in program.instructions)
            self.negative_transitions.update(zip(ops, ops[1:], strict=False))

    def score(self, program: UnifiedProgram) -> ProposalScore:
        ops = tuple(item.op for item in program.instructions)
        positive = self.start_counts[ops[0]] + sum(self.transition_counts[pair] for pair in zip(ops, ops[1:], strict=False))
        negative = sum(self.negative_transitions[pair] for pair in zip(ops, ops[1:], strict=False))
        normalized = (positive + 1) / (len(ops) + 1) - 0.35 * negative / (len(ops) + 1) - 0.0001 * program.primitive_token_cost
        return ProposalScore(program.program_id, normalized, positive, negative)

    def rank(self, programs: Iterable[UnifiedProgram]) -> tuple[UnifiedProgram, ...]:
        return tuple(sorted(programs, key=lambda item: (-self.score(item).score, item.primitive_token_cost, item.program_id)))


@dataclass(frozen=True, slots=True)
class AnonymousTask:
    task_id: str
    cases: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]


@dataclass(frozen=True, slots=True)
class CegisRoundV15:
    round_index: int
    active_case_indices: tuple[int, ...]
    candidates_replayed: int
    selected_program_id: str
    counterexample_index: int | None


@dataclass(frozen=True, slots=True)
class CegisResultV15:
    converged: bool
    selected: UnifiedProgram
    rounds: tuple[CegisRoundV15, ...]
    case_evaluations: int
    exhaustive_case_evaluations: int

    @property
    def evaluation_reduction(self) -> float:
        return 1.0 - self.case_evaluations / self.exhaustive_case_evaluations


class CounterexampleGuidedControllerV15:
    def __init__(self, policy: RecurrentProposalPolicy, vm: UnifiedCounterVM | None = None) -> None:
        self.policy = policy
        self.vm = vm or UnifiedCounterVM()

    def synthesize(self, task: AnonymousTask, candidates: Sequence[UnifiedProgram], initial_cases: tuple[int, ...] = (0, 1)) -> CegisResultV15:
        active = list(initial_cases)
        ranked = self.policy.rank(candidates)
        rounds: list[CegisRoundV15] = []
        evaluations = 0
        exhaustive = max(1, len(candidates) * len(task.cases))
        for round_index in range(min(12, len(task.cases))):
            consistent: list[UnifiedProgram] = []
            replayed = 0
            for program in ranked:
                passed = True
                for index in active:
                    replayed += 1
                    evaluations += 1
                    inputs, expected = task.cases[index]
                    try:
                        actual = self.vm.execute(program, inputs).outputs
                    except UnifiedVMError:
                        passed = False
                        break
                    if actual != expected:
                        passed = False
                        break
                if passed:
                    consistent.append(program)
            if not consistent:
                raise RuntimeError("CEGIS eliminated every candidate")
            selected = consistent[0]
            counterexample = None
            for index, (inputs, expected) in enumerate(task.cases):
                evaluations += 1
                try:
                    actual = self.vm.execute(selected, inputs).outputs
                except UnifiedVMError:
                    actual = ()
                if actual != expected:
                    counterexample = index
                    break
            rounds.append(CegisRoundV15(round_index, tuple(active), replayed, selected.program_id, counterexample))
            if counterexample is None:
                return CegisResultV15(True, selected, tuple(rounds), evaluations, exhaustive)
            if counterexample not in active:
                active.append(counterexample)
        return CegisResultV15(False, selected, tuple(rounds), evaluations, exhaustive)


@dataclass(frozen=True, slots=True)
class LearnedMacroV15:
    macro_id: str
    normalized_ops: tuple[str, ...]
    task_support: int
    occurrence_support: int
    primitive_token_cost: int
    macro_token_cost: int = 1

    @property
    def savings_per_use(self) -> int:
        return self.primitive_token_cost - self.macro_token_cost

    def to_dict(self) -> dict[str, Any]:
        return {
            "macro_id": self.macro_id,
            "normalized_ops": list(self.normalized_ops),
            "task_support": self.task_support,
            "occurrence_support": self.occurrence_support,
            "primitive_token_cost": self.primitive_token_cost,
            "macro_token_cost": self.macro_token_cost,
            "savings_per_use": self.savings_per_use,
        }


class CrossTaskMacroMinerV15:
    def mine(self, programs: dict[str, UnifiedProgram], *, minimum_task_support: int = 3) -> tuple[LearnedMacroV15, ...]:
        occurrence: Counter[tuple[str, ...]] = Counter()
        tasks: dict[tuple[str, ...], set[str]] = defaultdict(set)
        for task_id, program in programs.items():
            ops = tuple(item.op for item in program.instructions)
            for size in range(2, min(7, len(ops) + 1)):
                for start in range(len(ops) - size + 1):
                    window = ops[start : start + size]
                    occurrence[window] += 1
                    tasks[window].add(task_id)
        macros = []
        for window, count in occurrence.items():
            if len(tasks[window]) < minimum_task_support:
                continue
            digest = hashlib.sha256(json.dumps(window).encode()).hexdigest()[:16]
            macros.append(LearnedMacroV15("UMAC-" + digest, window, len(tasks[window]), count, len(window)))
        return tuple(sorted(macros, key=lambda item: (-item.savings_per_use * item.occurrence_support, -len(item.normalized_ops), item.macro_id)))


def primitive_leakage_audit(programs: Iterable[UnifiedProgram]) -> dict[str, Any]:
    findings = []
    for program in programs:
        encoded = json.dumps(program.to_dict(), sort_keys=True).lower()
        for term in FORBIDDEN_PROGRAM_TERMS:
            if term in encoded:
                findings.append({"program_id": program.program_id, "term": term})
        if any(item.op not in VM_OPS for item in program.instructions):
            findings.append({"program_id": program.program_id, "term": "unregistered_opcode"})
    return {
        "passed": not findings,
        "forbidden_terms": list(FORBIDDEN_PROGRAM_TERMS),
        "registered_opcodes": sorted(VM_OPS),
        "findings": findings,
    }


def default_anonymous_tasks() -> dict[str, AnonymousTask]:
    first_cases = tuple(((left, right), (sum(right for _ in range(left)),)) for left in range(7) for right in range(7))
    second_cases = tuple(((stream, template), (stream // template, stream % template)) for stream in range(21) for template in range(1, 7))
    third_cases = tuple(((base, count), (_natural_fold_oracle(base, count),)) for base in range(6) for count in range(7))
    return {
        "WORLD-7f3a": AnonymousTask("WORLD-7f3a", first_cases),
        "WORLD-b184": AnonymousTask("WORLD-b184", second_cases),
        "WORLD-43de": AnonymousTask("WORLD-43de", third_cases),
    }


def _natural_fold_oracle(base: int, count: int) -> int:
    state = 1
    for _ in range(count):
        next_state = 0
        for _ in range(base):
            next_state += state
        state = next_state
    return state
