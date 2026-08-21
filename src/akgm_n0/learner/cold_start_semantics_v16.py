"""Cold-start runtime semantic invention from recurring primitive programs.

The learner starts with an empty operator registry.  It receives anonymous
workloads containing only the eight substrate opcodes, mines recurring local
programs, and installs useful abstractions as parameterized runtime opcodes.
No migrated program, mathematical formula, or task-specific target is loaded.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from typing import Any, Iterable, Sequence


BASE_OPS = frozenset({"u_zero", "u_unit", "u_inc", "u_dec", "u_jz", "u_jump", "u_emit", "u_halt"})
DATA_OPS = frozenset({"u_zero", "u_unit", "u_inc", "u_dec"})
CONTROL_OPS = BASE_OPS - DATA_OPS


class SemanticRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RuntimeInstruction:
    op: str
    operands: tuple[int, ...] = ()
    target: int | None = None

    @property
    def encoded_tokens(self) -> int:
        return 1 + len(self.operands) + (self.target is not None)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"op": self.op}
        if self.operands:
            result["operands"] = list(self.operands)
        if self.target is not None:
            result["target"] = self.target
        return result


@dataclass(frozen=True, slots=True)
class RuntimeProgram:
    program_id: str
    register_count: int
    input_registers: tuple[int, ...]
    instructions: tuple[RuntimeInstruction, ...]


@dataclass(frozen=True, slots=True)
class PrimitiveWorkload:
    family_id: str
    workload_id: str
    register_count: int
    initial_state: tuple[int, ...]
    instructions: tuple[RuntimeInstruction, ...]

    @property
    def encoded_tokens(self) -> int:
        return sum(item.encoded_tokens for item in self.instructions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "workload_id": self.workload_id,
            "register_count": self.register_count,
            "initial_state": list(self.initial_state),
            "instructions": [item.to_dict() for item in self.instructions],
        }


@dataclass(frozen=True, slots=True)
class OperatorDefinitionV16:
    operator_id: str
    generation: int
    arity: int
    body: tuple[RuntimeInstruction, ...]
    primitive_body: tuple[RuntimeInstruction, ...]
    parent_operators: tuple[str, ...]
    train_family_support: int
    train_occurrences: int
    primitive_span: int
    token_gain_per_use: int
    net_training_reward: int
    behavior_signature: str
    certificate_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "generation": self.generation,
            "arity": self.arity,
            "body": [item.to_dict() for item in self.body],
            "primitive_body": [item.to_dict() for item in self.primitive_body],
            "parent_operators": list(self.parent_operators),
            "train_family_support": self.train_family_support,
            "train_occurrences": self.train_occurrences,
            "primitive_span": self.primitive_span,
            "token_gain_per_use": self.token_gain_per_use,
            "net_training_reward": self.net_training_reward,
            "behavior_signature": self.behavior_signature,
            "certificate_digest": self.certificate_digest,
        }


@dataclass(frozen=True, slots=True)
class RuntimeExecutionV16:
    outputs: tuple[int, ...]
    final_registers: tuple[int, ...]
    runtime_instructions: int
    dynamic_dispatches: int
    primitive_effects: int


class SelfExtendingCounterVM:
    """Eight fixed opcodes plus a runtime-installed, acyclic operator table."""

    def __init__(self, *, maximum_steps: int = 2_000_000) -> None:
        self.maximum_steps = maximum_steps
        self._operators: dict[str, OperatorDefinitionV16] = {}

    @property
    def operators(self) -> tuple[OperatorDefinitionV16, ...]:
        return tuple(self._operators.values())

    @property
    def operator_ids(self) -> frozenset[str]:
        return frozenset(self._operators)

    def install_operator(self, definition: OperatorDefinitionV16) -> None:
        if definition.operator_id in BASE_OPS or definition.operator_id in self._operators:
            raise SemanticRuntimeError("operator id is already registered")
        if definition.arity < 1 or definition.arity > 4:
            raise SemanticRuntimeError("operator arity is outside the runtime boundary")
        if not definition.body:
            raise SemanticRuntimeError("operator body is empty")
        available = DATA_OPS | self.operator_ids
        for item in definition.body:
            if item.op not in available or item.target is not None:
                raise SemanticRuntimeError("operator body contains unavailable control")
            expected = 1 if item.op in DATA_OPS else self._operators[item.op].arity
            if len(item.operands) != expected:
                raise SemanticRuntimeError("operator body operand arity differs")
            if any(role < 0 or role >= definition.arity for role in item.operands):
                raise SemanticRuntimeError("operator body references an unavailable role")
        self._operators[definition.operator_id] = definition

    def primitive_span(self, op: str) -> int:
        if op in DATA_OPS:
            return 1
        return len(self.flatten_operator(op))

    def flatten_body(self, body: Sequence[RuntimeInstruction]) -> tuple[RuntimeInstruction, ...]:
        result: list[RuntimeInstruction] = []
        for item in body:
            if item.op in DATA_OPS:
                result.append(item)
                continue
            definition = self._operators.get(item.op)
            if definition is None:
                raise SemanticRuntimeError("cannot flatten an unregistered operator")
            for primitive in definition.primitive_body:
                result.append(RuntimeInstruction(primitive.op, tuple(item.operands[role] for role in primitive.operands)))
        return tuple(result)

    def flatten_operator(self, operator_id: str) -> tuple[RuntimeInstruction, ...]:
        try:
            return self._operators[operator_id].primitive_body
        except KeyError as error:
            raise SemanticRuntimeError("unknown installed operator") from error

    def apply_sequence(
        self,
        instructions: Sequence[RuntimeInstruction],
        state: Sequence[int],
    ) -> tuple[tuple[int, ...], int, int]:
        registers = list(state)
        counters = {"dispatches": 0, "primitive_effects": 0}
        for item in instructions:
            self._apply_data(item, registers, counters, depth=0)
        return tuple(registers), counters["dispatches"], counters["primitive_effects"]

    def _apply_data(
        self,
        item: RuntimeInstruction,
        registers: list[int],
        counters: dict[str, int],
        *,
        depth: int,
    ) -> None:
        if depth > 64:
            raise SemanticRuntimeError("dynamic operator recursion boundary exceeded")
        if item.target is not None:
            raise SemanticRuntimeError("data dispatch cannot carry a jump target")
        if item.op in DATA_OPS:
            if len(item.operands) != 1:
                raise SemanticRuntimeError("primitive data operand arity differs")
            register = item.operands[0]
            if register < 0 or register >= len(registers):
                raise SemanticRuntimeError("register is unavailable")
            counters["primitive_effects"] += 1
            if item.op == "u_zero":
                registers[register] = 0
            elif item.op == "u_unit":
                registers[register] = 1
            elif item.op == "u_inc":
                registers[register] += 1
            elif item.op == "u_dec":
                if registers[register] == 0:
                    raise SemanticRuntimeError("cannot decrement an empty counter")
                registers[register] -= 1
            return
        definition = self._operators.get(item.op)
        if definition is None:
            raise SemanticRuntimeError("runtime operator is not installed")
        if len(item.operands) != definition.arity:
            raise SemanticRuntimeError("runtime operator operand arity differs")
        counters["dispatches"] += 1
        for child in definition.body:
            mapped = RuntimeInstruction(child.op, tuple(item.operands[role] for role in child.operands))
            self._apply_data(mapped, registers, counters, depth=depth + 1)

    def execute(self, program: RuntimeProgram, inputs: Sequence[int]) -> RuntimeExecutionV16:
        if len(inputs) != len(program.input_registers):
            raise SemanticRuntimeError("program input arity differs")
        if any(value < 0 for value in inputs):
            raise SemanticRuntimeError("counter inputs must be natural values")
        registers = [0] * program.register_count
        for register, value in zip(program.input_registers, inputs, strict=True):
            registers[register] = value
        outputs: list[int] = []
        counters = {"dispatches": 0, "primitive_effects": 0}
        pc = 0
        runtime_instructions = 0
        while runtime_instructions <= self.maximum_steps:
            if pc < 0 or pc >= len(program.instructions):
                raise SemanticRuntimeError("instruction pointer escaped")
            item = program.instructions[pc]
            runtime_instructions += 1
            next_pc = pc + 1
            if item.op in DATA_OPS or item.op in self._operators:
                self._apply_data(item, registers, counters, depth=0)
            elif item.op == "u_jz":
                if len(item.operands) != 1 or item.target is None:
                    raise SemanticRuntimeError("conditional jump is malformed")
                if registers[item.operands[0]] == 0:
                    next_pc = item.target
            elif item.op == "u_jump":
                if item.operands or item.target is None:
                    raise SemanticRuntimeError("jump is malformed")
                next_pc = item.target
            elif item.op == "u_emit":
                if len(item.operands) != 1 or item.target is not None:
                    raise SemanticRuntimeError("emit is malformed")
                outputs.append(registers[item.operands[0]])
            elif item.op == "u_halt":
                if item.operands or item.target is not None:
                    raise SemanticRuntimeError("halt is malformed")
                return RuntimeExecutionV16(
                    tuple(outputs), tuple(registers), runtime_instructions,
                    counters["dispatches"], counters["primitive_effects"],
                )
            else:
                raise SemanticRuntimeError("unregistered opcode")
            pc = next_pc
        raise SemanticRuntimeError("program did not halt inside the step boundary")


@dataclass(frozen=True, slots=True)
class SemanticCandidateV16:
    body: tuple[RuntimeInstruction, ...]
    arity: int
    family_support: int
    occurrences: int
    primitive_span: int
    token_gain_per_use: int
    net_reward: int
    parent_operators: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RejectedSemanticV16:
    candidate_digest: str
    reason: str
    family_support: int
    occurrences: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_digest": self.candidate_digest,
            "reason": self.reason,
            "family_support": self.family_support,
            "occurrences": self.occurrences,
        }


@dataclass(frozen=True, slots=True)
class ColdStartDiscoveryV16:
    manifest: dict[str, Any]
    operators: tuple[OperatorDefinitionV16, ...]
    rejected: tuple[RejectedSemanticV16, ...]
    training_tokens_before: int
    training_tokens_after: int
    compressed_streams: dict[str, tuple[RuntimeInstruction, ...]]

    @property
    def training_reduction(self) -> float:
        return 1.0 - self.training_tokens_after / self.training_tokens_before


def _body_payload(body: Sequence[RuntimeInstruction]) -> str:
    return json.dumps([item.to_dict() for item in body], sort_keys=True, separators=(",", ":"))


def _normalize_window(window: Sequence[RuntimeInstruction]) -> tuple[tuple[RuntimeInstruction, ...], int]:
    registers: dict[int, int] = {}
    normalized: list[RuntimeInstruction] = []
    for item in window:
        roles = []
        for register in item.operands:
            if register not in registers:
                registers[register] = len(registers)
            roles.append(registers[register])
        normalized.append(RuntimeInstruction(item.op, tuple(roles)))
    return tuple(normalized), len(registers)


def match_body(
    body: Sequence[RuntimeInstruction],
    stream: Sequence[RuntimeInstruction],
    start: int,
) -> tuple[int, ...] | None:
    if start + len(body) > len(stream):
        return None
    role_values: dict[int, int] = {}
    reverse: dict[int, int] = {}
    for pattern, actual in zip(body, stream[start:start + len(body)], strict=True):
        if pattern.op != actual.op or len(pattern.operands) != len(actual.operands):
            return None
        for role, register in zip(pattern.operands, actual.operands, strict=True):
            existing = role_values.get(role)
            if existing is not None and existing != register:
                return None
            claimed_role = reverse.get(register)
            if claimed_role is not None and claimed_role != role:
                return None
            role_values[role] = register
            reverse[register] = role
    if sorted(role_values) != list(range(len(role_values))):
        return None
    return tuple(role_values[index] for index in range(len(role_values)))


def compress_with_operator(
    stream: Sequence[RuntimeInstruction],
    definition: OperatorDefinitionV16,
) -> tuple[tuple[RuntimeInstruction, ...], int]:
    compressed: list[RuntimeInstruction] = []
    uses = 0
    index = 0
    while index < len(stream):
        operands = match_body(definition.body, stream, index)
        if operands is None:
            compressed.append(stream[index])
            index += 1
            continue
        compressed.append(RuntimeInstruction(definition.operator_id, operands))
        uses += 1
        index += len(definition.body)
    return tuple(compressed), uses


def behavior_signature(
    vm: SelfExtendingCounterVM,
    body: Sequence[RuntimeInstruction],
    arity: int,
    *,
    value_limit: int = 3,
) -> str:
    outcomes = []
    register_count = max(2, arity)
    for binding in itertools.product(range(register_count), repeat=arity):
        for state in itertools.product(range(value_limit + 1), repeat=register_count):
            mapped = tuple(
                RuntimeInstruction(item.op, tuple(binding[role] for role in item.operands))
                for item in body
            )
            try:
                final, _, _ = vm.apply_sequence(mapped, state)
                outcome: Any = ["ok", list(final)]
            except SemanticRuntimeError as error:
                outcome = ["error", str(error)]
            outcomes.append([list(binding), list(state), outcome])
    return hashlib.sha256(json.dumps(outcomes, separators=(",", ":")).encode()).hexdigest()


class ColdStartSemanticResearcherV16:
    """MDL-driven semantic abstraction with no successful program seed."""

    def __init__(self) -> None:
        self.vm = SelfExtendingCounterVM()
        self.rejections: list[RejectedSemanticV16] = []

    def discover(
        self,
        workloads: Sequence[PrimitiveWorkload],
        *,
        minimum_operators: int = 5,
        maximum_operators: int = 24,
    ) -> ColdStartDiscoveryV16:
        if self.vm.operators:
            raise SemanticRuntimeError("cold-start registry was not empty")
        if not workloads:
            raise ValueError("cold-start workload corpus is empty")
        if any(item.op not in DATA_OPS for workload in workloads for item in workload.instructions):
            raise ValueError("training corpus contains a non-primitive data operation")
        streams = {item.workload_id: item.instructions for item in workloads}
        families = {item.workload_id: item.family_id for item in workloads}
        before = sum(sum(item.encoded_tokens for item in stream) for stream in streams.values())
        known_signatures = self._initial_signatures()

        while len(self.vm.operators) < maximum_operators:
            candidates = self._mine(streams, families)
            if len(self.vm.operators) < minimum_operators:
                candidates = tuple(item for item in candidates if not item.parent_operators)
            else:
                recursive = tuple(item for item in candidates if item.parent_operators)
                if recursive:
                    candidates = recursive
            selected: tuple[SemanticCandidateV16, str] | None = None
            for candidate in candidates:
                digest = hashlib.sha256(_body_payload(candidate.body).encode()).hexdigest()[:16]
                signature = behavior_signature(self.vm, candidate.body, candidate.arity)
                if signature in known_signatures[candidate.arity]:
                    self.rejections.append(RejectedSemanticV16(digest, "behavior_already_available", candidate.family_support, candidate.occurrences))
                    continue
                if self._is_identity(candidate.body, candidate.arity):
                    self.rejections.append(RejectedSemanticV16(digest, "identity_has_no_state_effect", candidate.family_support, candidate.occurrences))
                    continue
                selected = candidate, signature
                break
            if selected is None:
                break
            candidate, signature = selected
            definition = self._definition(candidate, signature)
            self.vm.install_operator(definition)
            known_signatures[definition.arity].add(signature)
            for workload_id, stream in tuple(streams.items()):
                streams[workload_id] = compress_with_operator(stream, definition)[0]

        after = sum(sum(item.encoded_tokens for item in stream) for stream in streams.values())
        manifest = {
            "initial_success_program_count": 0,
            "initial_dynamic_operator_count": 0,
            "imported_program_count": 0,
            "prior_artifact_reads": 0,
            "target_formula_count": 0,
            "target_operator_name_count": 0,
            "base_opcodes": sorted(BASE_OPS),
            "selection_objective": "cross_family_minimum_description_length_reward",
            "workload_digest": hashlib.sha256(
                json.dumps([item.to_dict() for item in workloads], sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }
        return ColdStartDiscoveryV16(
            manifest, self.vm.operators, tuple(self.rejections), before, after, streams,
        )

    def extend(
        self,
        workloads: Sequence[PrimitiveWorkload],
        *,
        maximum_new_operators: int = 8,
        maximum_primitive_span: int = 3,
        maximum_arity: int = 2,
        maximum_generation: int = 3,
    ) -> ColdStartDiscoveryV16:
        """Continue an existing registry inside an explicit finite charter.

        V16's strict ``discover`` entry point remains empty-registry only.  This
        method is for later autonomous curricula that must reuse prior runtime
        semantics while retaining a finite, auditable saturation boundary.
        """

        if not workloads:
            raise ValueError("continuation workload corpus is empty")
        if maximum_new_operators < 1:
            raise ValueError("continuation operator budget is empty")
        if any(item.op not in DATA_OPS for workload in workloads for item in workload.instructions):
            raise ValueError("continuation corpus contains a non-primitive data operation")
        starting = len(self.vm.operators)
        rejection_start = len(self.rejections)
        streams = {item.workload_id: item.instructions for item in workloads}
        families = {item.workload_id: item.family_id for item in workloads}
        before = sum(sum(item.encoded_tokens for item in stream) for stream in streams.values())
        for definition in self.vm.operators:
            for workload_id, stream in tuple(streams.items()):
                streams[workload_id] = compress_with_operator(stream, definition)[0]
        known_signatures = self._initial_signatures()
        for definition in self.vm.operators:
            known_signatures[definition.arity].add(definition.behavior_signature)

        while len(self.vm.operators) < starting + maximum_new_operators:
            candidates = tuple(
                candidate for candidate in self._mine(streams, families)
                if candidate.arity <= maximum_arity
                and candidate.primitive_span <= maximum_primitive_span
                and 1 + max(
                    (self.vm._operators[parent].generation for parent in candidate.parent_operators),
                    default=0,
                ) <= maximum_generation
            )
            selected: tuple[SemanticCandidateV16, str] | None = None
            for candidate in candidates:
                digest = hashlib.sha256(_body_payload(candidate.body).encode()).hexdigest()[:16]
                signature = behavior_signature(self.vm, candidate.body, candidate.arity)
                if signature in known_signatures[candidate.arity]:
                    self.rejections.append(RejectedSemanticV16(
                        digest, "behavior_already_available", candidate.family_support, candidate.occurrences,
                    ))
                    continue
                if self._is_identity(candidate.body, candidate.arity):
                    self.rejections.append(RejectedSemanticV16(
                        digest, "identity_has_no_state_effect", candidate.family_support, candidate.occurrences,
                    ))
                    continue
                selected = candidate, signature
                break
            if selected is None:
                break
            candidate, signature = selected
            definition = self._definition(candidate, signature)
            self.vm.install_operator(definition)
            known_signatures[definition.arity].add(signature)
            for workload_id, stream in tuple(streams.items()):
                streams[workload_id] = compress_with_operator(stream, definition)[0]

        new_definitions = self.vm.operators[starting:]
        after = sum(sum(item.encoded_tokens for item in stream) for stream in streams.values())
        manifest = {
            "initial_success_program_count": 0,
            "initial_dynamic_operator_count": starting,
            "imported_program_count": 0,
            "prior_artifact_reads": 0,
            "target_formula_count": 0,
            "target_operator_name_count": 0,
            "base_opcodes": sorted(BASE_OPS),
            "selection_objective": "bounded_cross_family_minimum_description_length_reward",
            "research_charter": {
                "maximum_primitive_span": maximum_primitive_span,
                "maximum_arity": maximum_arity,
                "maximum_generation": maximum_generation,
            },
            "workload_digest": hashlib.sha256(
                json.dumps([item.to_dict() for item in workloads], sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }
        return ColdStartDiscoveryV16(
            manifest,
            new_definitions,
            tuple(self.rejections[rejection_start:]),
            before,
            after,
            streams,
        )

    def _initial_signatures(self) -> dict[int, set[str]]:
        signatures: dict[int, set[str]] = defaultdict(set)
        for op in sorted(DATA_OPS):
            signatures[1].add(behavior_signature(self.vm, (RuntimeInstruction(op, (0,)),), 1))
        return signatures

    def _is_identity(self, body: Sequence[RuntimeInstruction], arity: int) -> bool:
        register_count = max(2, arity)
        for state in itertools.product(range(4), repeat=register_count):
            try:
                final, _, _ = self.vm.apply_sequence(body, state)
            except SemanticRuntimeError:
                return False
            if final != state:
                return False
        return True

    def _mine(
        self,
        streams: dict[str, tuple[RuntimeInstruction, ...]],
        families: dict[str, str],
    ) -> tuple[SemanticCandidateV16, ...]:
        occurrences: Counter[str] = Counter()
        family_occurrences: dict[str, Counter[str]] = defaultdict(Counter)
        bodies: dict[str, tuple[tuple[RuntimeInstruction, ...], int]] = {}
        for workload_id, stream in streams.items():
            for width in range(2, min(5, len(stream) + 1)):
                for index in range(len(stream) - width + 1):
                    body, arity = _normalize_window(stream[index:index + width])
                    if arity < 1 or arity > 4:
                        continue
                    key = _body_payload(body)
                    bodies[key] = body, arity
                    occurrences[key] += 1
                    family_occurrences[key][families[workload_id]] += 1
        candidates = []
        for key, count in occurrences.items():
            body, arity = bodies[key]
            support = sum(count >= 5 for count in family_occurrences[key].values())
            if support < 3:
                continue
            body_tokens = sum(item.encoded_tokens for item in body)
            call_tokens = 1 + arity
            gain = body_tokens - call_tokens
            net = count * gain - body_tokens
            if gain <= 0 or net <= 0:
                continue
            parents = tuple(sorted({item.op for item in body if item.op not in DATA_OPS}))
            primitive_span = sum(self.vm.primitive_span(item.op) for item in body)
            candidates.append(SemanticCandidateV16(body, arity, support, count, primitive_span, gain, net, parents))
        return tuple(sorted(
            candidates,
            key=lambda item: (
                -item.net_reward,
                -item.family_support,
                -item.primitive_span,
                item.arity,
                _body_payload(item.body),
            ),
        ))

    def _definition(self, candidate: SemanticCandidateV16, signature: str) -> OperatorDefinitionV16:
        primitive_body = self.vm.flatten_body(candidate.body)
        generation = 1 + max(
            (self.vm._operators[parent].generation for parent in candidate.parent_operators),
            default=0,
        )
        payload = {
            "body": [item.to_dict() for item in candidate.body],
            "generation": generation,
            "arity": candidate.arity,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        certificate_digest = hashlib.sha256(_body_payload(primitive_body).encode()).hexdigest()
        return OperatorDefinitionV16(
            "nu_" + digest[:12], generation, candidate.arity, candidate.body,
            primitive_body, candidate.parent_operators, candidate.family_support,
            candidate.occurrences, candidate.primitive_span,
            candidate.token_gain_per_use, candidate.net_reward, signature,
            certificate_digest,
        )


def operator_surface_audit(definitions: Iterable[OperatorDefinitionV16]) -> dict[str, Any]:
    forbidden = ("add", "subtract", "multiply", "divide", "power", "root", "log", "formula", "target")
    opcodes = [
        instruction.op.lower()
        for definition in definitions
        for body in (definition.body, definition.primitive_body)
        for instruction in body
    ]
    readable = [opcode for opcode in opcodes if opcode not in BASE_OPS and re.fullmatch(r"nu_[0-9a-f]{12}", opcode) is None]
    hits = sorted({term for term in forbidden for opcode in readable if term in opcode})
    return {"passed": not hits and not readable, "forbidden_hits": hits, "non_opaque_dynamic_opcodes": readable}
