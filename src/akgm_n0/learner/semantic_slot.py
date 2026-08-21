"""Synthesize executable semantics for an initially unbound glyph."""

from __future__ import annotations

import hashlib
import json
import math
import string
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .observation import NumericTableObservation


MICRO_VALUE_OPERATIONS = frozenset(
    {"m_input", "m_register", "m_constant", "m_add", "m_subtract"}
)
KEYBOARD_PUNCTUATION_GLYPHS = tuple(string.punctuation)


class InvalidMicroProgram(ValueError):
    """Raised when a synthesized micro-state program is unsafe or malformed."""


class UnboundSemanticError(ValueError):
    """Raised when an unverified glyph is called as though it had semantics."""


@dataclass(frozen=True, slots=True)
class MicroValueNode:
    op: str
    args: tuple["MicroValueNode", ...] = ()
    index: int | None = None
    constant: float | None = None

    @property
    def node_count(self) -> int:
        return 1 + sum(child.node_count for child in self.args)

    @property
    def uses_register(self) -> bool:
        return self.op == "m_register" or any(
            child.uses_register for child in self.args
        )

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"op": self.op}
        if self.args:
            value["args"] = [child.to_dict() for child in self.args]
        if self.index is not None:
            value["index"] = self.index
        if self.constant is not None:
            value["constant"] = self.constant
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MicroValueNode":
        """Load a persisted node without trusting its serialized shape."""

        if not isinstance(value, Mapping):
            raise InvalidMicroProgram("micro node must be a mapping")
        allowed = {"op", "args", "index", "constant"}
        if set(value) - allowed:
            raise InvalidMicroProgram("micro node contains unknown fields")
        op = value.get("op")
        if not isinstance(op, str) or op not in MICRO_VALUE_OPERATIONS:
            raise InvalidMicroProgram("micro node operation is not registered")
        raw_args = value.get("args", ())
        if not isinstance(raw_args, (list, tuple)):
            raise InvalidMicroProgram("micro node args must be a sequence")
        args = tuple(cls.from_dict(child) for child in raw_args)
        raw_index = value.get("index")
        if raw_index is not None and (
            isinstance(raw_index, bool) or not isinstance(raw_index, int)
        ):
            raise InvalidMicroProgram("micro node index must be an integer")
        raw_constant = value.get("constant")
        if raw_constant is not None and (
            isinstance(raw_constant, bool)
            or not isinstance(raw_constant, (int, float))
            or not math.isfinite(float(raw_constant))
        ):
            raise InvalidMicroProgram("micro node constant must be finite")
        return cls(
            op=op,
            args=args,
            index=raw_index,
            # Preserve JSON's numeric representation so persisted operation IDs
            # remain stable; execution still normalizes values to float.
            constant=raw_constant,
        )


@dataclass(frozen=True, slots=True)
class MicroHaltCondition:
    register_index: int
    constant: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "op": "m_equal",
            "left": {"op": "m_register", "index": self.register_index},
            "right": {"op": "m_constant", "constant": self.constant},
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MicroHaltCondition":
        if not isinstance(value, Mapping) or set(value) != {"op", "left", "right"}:
            raise InvalidMicroProgram("halt condition shape is invalid")
        if value.get("op") != "m_equal":
            raise InvalidMicroProgram("halt condition operation is invalid")
        left = MicroValueNode.from_dict(value["left"])
        right = MicroValueNode.from_dict(value["right"])
        if left.op != "m_register" or right.op != "m_constant":
            raise InvalidMicroProgram("halt condition operands are invalid")
        assert left.index is not None and right.constant is not None
        return cls(left.index, right.constant)


@dataclass(frozen=True, slots=True)
class MicroProgram:
    initial_registers: tuple[MicroValueNode, MicroValueNode]
    halt_condition: MicroHaltCondition
    updates: tuple[MicroValueNode, MicroValueNode]
    output_register: int

    @property
    def node_count(self) -> int:
        return (
            sum(node.node_count for node in self.initial_registers)
            + sum(node.node_count for node in self.updates)
            + 3
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "anonymous_microstate_v0.1",
            "initial_registers": [node.to_dict() for node in self.initial_registers],
            "halt_condition": self.halt_condition.to_dict(),
            "simultaneous_updates": [node.to_dict() for node in self.updates],
            "output_register": self.output_register,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MicroProgram":
        """Safely restore an independently verified success-room program."""

        required = {
            "substrate",
            "initial_registers",
            "halt_condition",
            "simultaneous_updates",
            "output_register",
        }
        if not isinstance(value, Mapping) or set(value) != required:
            raise InvalidMicroProgram("micro program shape is invalid")
        if value.get("substrate") != "anonymous_microstate_v0.1":
            raise InvalidMicroProgram("micro program substrate is not registered")
        raw_initial = value["initial_registers"]
        raw_updates = value["simultaneous_updates"]
        if not isinstance(raw_initial, (list, tuple)) or not isinstance(
            raw_updates, (list, tuple)
        ):
            raise InvalidMicroProgram("micro program registers must be sequences")
        output_register = value["output_register"]
        if isinstance(output_register, bool) or not isinstance(output_register, int):
            raise InvalidMicroProgram("output register must be an integer")
        program = cls(
            initial_registers=tuple(
                MicroValueNode.from_dict(node) for node in raw_initial
            ),
            halt_condition=MicroHaltCondition.from_dict(value["halt_condition"]),
            updates=tuple(MicroValueNode.from_dict(node) for node in raw_updates),
            output_register=output_register,
        )
        MicroProgramExecutor().validate(program, 2)
        return program


@dataclass(frozen=True, slots=True)
class MicroExecution:
    output_value: float
    step_count: int
    final_registers: tuple[float, float]


class MicroProgramExecutor:
    """Apply a candidate-defined state update until its candidate-defined halt."""

    def __init__(
        self,
        *,
        maximum_steps: int = 64,
        maximum_expression_nodes: int = 3,
        magnitude_limit: float = 1e100,
    ) -> None:
        if maximum_steps < 1 or maximum_expression_nodes < 1:
            raise ValueError("micro execution limits must be positive")
        if not math.isfinite(magnitude_limit) or magnitude_limit <= 0:
            raise ValueError("magnitude_limit must be finite and positive")
        self.maximum_steps = maximum_steps
        self.maximum_expression_nodes = maximum_expression_nodes
        self.magnitude_limit = magnitude_limit

    def execute(self, program: MicroProgram, inputs: Sequence[float]) -> MicroExecution:
        numeric_inputs = tuple(float(value) for value in inputs)
        if not numeric_inputs or not all(math.isfinite(value) for value in numeric_inputs):
            raise InvalidMicroProgram("inputs must be finite and nonempty")
        self.validate(program, len(numeric_inputs))
        registers = tuple(
            self._evaluate(node, numeric_inputs, None)
            for node in program.initial_registers
        )
        for step in range(self.maximum_steps + 1):
            if (
                registers[program.halt_condition.register_index]
                == program.halt_condition.constant
            ):
                return MicroExecution(
                    output_value=registers[program.output_register],
                    step_count=step,
                    final_registers=registers,
                )
            if step == self.maximum_steps:
                break
            registers = tuple(
                self._evaluate(node, numeric_inputs, registers)
                for node in program.updates
            )
        raise InvalidMicroProgram("candidate did not halt within the registered bound")

    def validate(self, program: MicroProgram, input_width: int) -> None:
        if len(program.initial_registers) != 2 or len(program.updates) != 2:
            raise InvalidMicroProgram("the frozen substrate has exactly two registers")
        if program.output_register not in {0, 1}:
            raise InvalidMicroProgram("output register is outside the substrate")
        if program.halt_condition.register_index not in {0, 1}:
            raise InvalidMicroProgram("halt register is outside the substrate")
        if not math.isfinite(program.halt_condition.constant):
            raise InvalidMicroProgram("halt constant must be finite")
        for node in program.initial_registers:
            self._validate_node(node, input_width, allow_register=False)
        for node in program.updates:
            self._validate_node(node, input_width, allow_register=True)
            if not node.uses_register:
                raise InvalidMicroProgram("each state update must depend on state")

    def _validate_node(
        self, node: MicroValueNode, input_width: int, *, allow_register: bool
    ) -> None:
        if node.op not in MICRO_VALUE_OPERATIONS:
            raise InvalidMicroProgram(f"unregistered micro operation: {node.op}")
        if node.node_count > self.maximum_expression_nodes:
            raise InvalidMicroProgram("micro expression exceeds node bound")
        if node.op == "m_input":
            if node.args or node.index is None or node.constant is not None:
                raise InvalidMicroProgram("m_input shape is invalid")
            if node.index < 0 or node.index >= input_width:
                raise InvalidMicroProgram("input index is outside the row")
            return
        if node.op == "m_register":
            if (
                not allow_register
                or node.args
                or node.index not in {0, 1}
                or node.constant is not None
            ):
                raise InvalidMicroProgram("m_register shape is invalid")
            return
        if node.op == "m_constant":
            if node.args or node.index is not None or node.constant is None:
                raise InvalidMicroProgram("m_constant shape is invalid")
            if not math.isfinite(node.constant):
                raise InvalidMicroProgram("constant must be finite")
            return
        if len(node.args) != 2 or node.index is not None or node.constant is not None:
            raise InvalidMicroProgram("binary micro expression shape is invalid")
        for child in node.args:
            self._validate_node(child, input_width, allow_register=allow_register)

    def _evaluate(
        self,
        node: MicroValueNode,
        inputs: tuple[float, ...],
        registers: tuple[float, float] | None,
    ) -> float:
        if node.op == "m_input":
            assert node.index is not None
            return self._checked(inputs[node.index])
        if node.op == "m_register":
            if registers is None or node.index is None:
                raise InvalidMicroProgram("register is unavailable")
            return self._checked(registers[node.index])
        if node.op == "m_constant":
            assert node.constant is not None
            return self._checked(node.constant)
        left = self._evaluate(node.args[0], inputs, registers)
        right = self._evaluate(node.args[1], inputs, registers)
        result = left + right if node.op == "m_add" else left - right
        return self._checked(result)

    def _checked(self, value: float) -> float:
        numeric = float(value)
        if not math.isfinite(numeric) or abs(numeric) > self.magnitude_limit:
            raise InvalidMicroProgram("micro program produced unsafe magnitude")
        return numeric


@dataclass(frozen=True, slots=True)
class MicroCandidate:
    candidate_id: str
    program: MicroProgram
    fit_error: float
    maximum_steps_used: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "program": self.program.to_dict(),
            "fit_error": self.fit_error,
            "maximum_steps_used": self.maximum_steps_used,
            "program_nodes": self.program.node_count,
        }


@dataclass(frozen=True, slots=True)
class MicroSearchReport:
    programs_generated: int
    programs_executed: int
    nonhalting_programs: int
    valid_row_count: int
    evidence_constants: tuple[dict[str, Any], ...]
    top_candidates: tuple[MicroCandidate, ...]
    programs_filtered: int = 0


class MicroProgramSearch:
    """Enumerate memory, update, halt, and output choices without an iterate node."""

    def __init__(
        self,
        *,
        top_k: int = 20,
        maximum_evidence_constants: int = 3,
        candidate_gate: Callable[[MicroProgram], bool] | None = None,
        executor: MicroProgramExecutor | None = None,
    ) -> None:
        if top_k < 1 or maximum_evidence_constants < 1:
            raise ValueError("search limits must be positive")
        self.top_k = top_k
        self.maximum_evidence_constants = maximum_evidence_constants
        self.candidate_gate = candidate_gate or (lambda _program: True)
        self.executor = executor or MicroProgramExecutor()

    def search(self, observation: NumericTableObservation) -> MicroSearchReport:
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
            raise ValueError("micro search requires valid numeric rows")
        width = len(valid[0][0])
        evidence_constants = self._derive_constants(valid)
        constants = tuple(item["value"] for item in evidence_constants)
        inputs = tuple(MicroValueNode("m_input", index=index) for index in range(width))
        constant_nodes = tuple(
            MicroValueNode("m_constant", constant=value) for value in constants
        )
        initial_nodes = inputs + constant_nodes
        registers = tuple(MicroValueNode("m_register", index=index) for index in range(2))
        update_sources = inputs + constant_nodes
        update_nodes: list[MicroValueNode] = list(registers)
        for register in registers:
            for source in update_sources:
                update_nodes.append(MicroValueNode("m_add", (register, source)))
                update_nodes.append(MicroValueNode("m_subtract", (register, source)))
        update_nodes = list(self._unique_nodes(update_nodes))
        halt_conditions = tuple(
            MicroHaltCondition(register_index, constant)
            for register_index in range(2)
            for constant in constants
        )

        generated = 0
        executed = 0
        nonhalting = 0
        filtered = 0
        candidates: list[MicroCandidate] = []
        for initial_0 in initial_nodes:
            for initial_1 in initial_nodes:
                for halt in halt_conditions:
                    for update_0 in update_nodes:
                        for update_1 in update_nodes:
                            for output_register in range(2):
                                generated += 1
                                program = MicroProgram(
                                    (initial_0, initial_1),
                                    halt,
                                    (update_0, update_1),
                                    output_register,
                                )
                                if not self.candidate_gate(program):
                                    filtered += 1
                                    continue
                                errors = []
                                maximum_steps = 0
                                try:
                                    for row, expected in valid:
                                        result = self.executor.execute(program, row)
                                        errors.append(result.output_value - expected)
                                        maximum_steps = max(maximum_steps, result.step_count)
                                except InvalidMicroProgram:
                                    nonhalting += 1
                                    continue
                                executed += 1
                                fit_error = sum(error * error for error in errors) / len(errors)
                                key = micro_program_key(program)
                                candidate_id = "MC-" + hashlib.sha256(
                                    key.encode("utf-8")
                                ).hexdigest()[:16]
                                candidates.append(
                                    MicroCandidate(
                                        candidate_id,
                                        program,
                                        fit_error,
                                        maximum_steps,
                                    )
                                )
        candidates.sort(
            key=lambda item: (
                item.fit_error,
                item.program.node_count,
                item.maximum_steps_used,
                item.candidate_id,
            )
        )
        return MicroSearchReport(
            programs_generated=generated,
            programs_executed=executed,
            nonhalting_programs=nonhalting,
            valid_row_count=len(valid),
            evidence_constants=evidence_constants,
            top_candidates=tuple(candidates[: self.top_k]),
            programs_filtered=filtered,
        )

    def _derive_constants(
        self, valid: tuple[tuple[tuple[float, ...], float], ...]
    ) -> tuple[dict[str, Any], ...]:
        observed = sorted(
            {
                float(value)
                for row, output in valid
                for value in (*row, output)
            }
        )
        derived: dict[float, dict[str, Any]] = {}
        for left in observed:
            for right in observed:
                value = float(left - right)
                derived.setdefault(
                    value,
                    {
                        "value": value,
                        "provenance": {
                            "op": "subtract_observed_numeric_atoms",
                            "left": left,
                            "right": right,
                        },
                    },
                )
        ordered = sorted(
            derived.values(), key=lambda item: (abs(item["value"]), item["value"])
        )
        return tuple(ordered[: self.maximum_evidence_constants])

    @staticmethod
    def _unique_nodes(nodes: Sequence[MicroValueNode]) -> tuple[MicroValueNode, ...]:
        unique = {micro_node_key(node): node for node in nodes}
        return tuple(unique[key] for key in sorted(unique))


@dataclass(frozen=True, slots=True)
class SemanticBinding:
    operation_id: str
    definition: MicroProgram
    verification_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "definition": self.definition.to_dict(),
            "verification_status": self.verification_status,
            "human_interpretation": None,
        }


class UnboundSemanticSlot:
    """A display glyph that has no behavior until a verified program is bound."""

    ACCEPTED_STATUSES = frozenset({"verified", "bounded", "admitted"})

    def __init__(
        self, glyph: str, *, executor: MicroProgramExecutor | None = None
    ) -> None:
        if not glyph:
            raise ValueError("glyph cannot be empty")
        self.glyph = glyph
        self.executor = executor or MicroProgramExecutor()
        self._binding: SemanticBinding | None = None

    @property
    def binding(self) -> SemanticBinding | None:
        return self._binding

    def bind(self, program: MicroProgram, *, verification_status: str) -> SemanticBinding:
        if verification_status not in self.ACCEPTED_STATUSES:
            raise UnboundSemanticError("an unverified program cannot bind the glyph")
        self.executor.validate(program, 2)
        operation_id = "SEM-" + hashlib.sha256(
            micro_program_key(program).encode("utf-8")
        ).hexdigest()[:16]
        binding = SemanticBinding(operation_id, program, verification_status)
        if self._binding is not None and self._binding.operation_id != operation_id:
            raise UnboundSemanticError("glyph is already bound to different semantics")
        self._binding = binding
        return binding

    def execute(self, inputs: Sequence[float]) -> MicroExecution:
        if self._binding is None:
            raise UnboundSemanticError("glyph has no executable semantics")
        return self.executor.execute(self._binding.definition, inputs)


@dataclass(frozen=True, slots=True)
class MicroReductionScore:
    verified: bool
    case_count: int
    passed_case_count: int
    original_node_count: int
    reduced_node_count: int
    reduction_gain: int
    unique_node_count: int
    constant_leaf_count: int
    mean_execution_steps: float | None
    description_cost: float
    reward: float
    reduced_program: MicroProgram

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "case_count": self.case_count,
            "passed_case_count": self.passed_case_count,
            "original_node_count": self.original_node_count,
            "reduced_node_count": self.reduced_node_count,
            "reduction_gain": self.reduction_gain,
            "unique_node_count": self.unique_node_count,
            "constant_leaf_count": self.constant_leaf_count,
            "mean_execution_steps": self.mean_execution_steps,
            "description_cost": self.description_cost,
            "reward": self.reward,
            "reduced_program": self.reduced_program.to_dict(),
        }


class MicroProgramReductionScorer:
    """Reward verified semantics by structural and execution description cost."""

    VERIFIED_REWARD_FLOOR = 1_000_000.0

    def __init__(self, executor: MicroProgramExecutor | None = None) -> None:
        self.executor = executor or MicroProgramExecutor()

    def score(
        self,
        program: MicroProgram,
        cases: Sequence[tuple[Sequence[float], float]],
    ) -> MicroReductionScore:
        if not cases:
            raise ValueError("reduction scoring requires verification cases")
        reduced = reduce_micro_program(program)
        passed = 0
        steps: list[int] = []
        for row, expected in cases:
            try:
                execution = self.executor.execute(reduced, row)
                if execution.output_value == float(expected):
                    passed += 1
                steps.append(execution.step_count)
            except InvalidMicroProgram:
                steps = []
                break
        verified = passed == len(cases)
        nodes = _walk_micro_program_nodes(reduced)
        unique_node_count = len({micro_node_key(node) for node in nodes})
        constant_leaf_count = sum(node.op == "m_constant" for node in nodes)
        mean_steps = sum(steps) / len(steps) if len(steps) == len(cases) else None
        execution_cost = mean_steps if mean_steps is not None else self.executor.maximum_steps
        description_cost = (
            reduced.node_count
            + 0.5 * unique_node_count
            + 0.75 * constant_leaf_count
            + 0.02 * execution_cost
            + 0.1 * program.node_count
        )
        reward = (
            self.VERIFIED_REWARD_FLOOR - description_cost
            if verified
            else -description_cost
        )
        return MicroReductionScore(
            verified=verified,
            case_count=len(cases),
            passed_case_count=passed,
            original_node_count=program.node_count,
            reduced_node_count=reduced.node_count,
            reduction_gain=program.node_count - reduced.node_count,
            unique_node_count=unique_node_count,
            constant_leaf_count=constant_leaf_count,
            mean_execution_steps=mean_steps,
            description_cost=description_cost,
            reward=reward,
            reduced_program=reduced,
        )


class KeyboardSymbolArena:
    """Expose every printable punctuation key as an equally meaningless slot."""

    def __init__(
        self,
        *,
        glyphs: Sequence[str] = KEYBOARD_PUNCTUATION_GLYPHS,
        executor: MicroProgramExecutor | None = None,
    ) -> None:
        unique = tuple(dict.fromkeys(glyphs))
        if not unique or any(len(glyph) != 1 for glyph in unique):
            raise ValueError("keyboard glyphs must be distinct single characters")
        self.executor = executor or MicroProgramExecutor()
        self._slots = {
            glyph: UnboundSemanticSlot(glyph, executor=self.executor)
            for glyph in unique
        }
        self._operation_glyphs: dict[str, str] = {}

    @property
    def glyphs(self) -> tuple[str, ...]:
        return tuple(self._slots)

    @property
    def unbound_glyphs(self) -> tuple[str, ...]:
        return tuple(
            glyph for glyph, slot in self._slots.items() if slot.binding is None
        )

    @property
    def bindings(self) -> dict[str, SemanticBinding]:
        return {
            glyph: slot.binding
            for glyph, slot in self._slots.items()
            if slot.binding is not None
        }

    def bind_reward_winner(
        self, program: MicroProgram, *, verification_status: str
    ) -> tuple[str, SemanticBinding]:
        operation_id = "SEM-" + hashlib.sha256(
            micro_program_key(program).encode("utf-8")
        ).hexdigest()[:16]
        if operation_id in self._operation_glyphs:
            glyph = self._operation_glyphs[operation_id]
            binding = self._slots[glyph].binding
            assert binding is not None
            return glyph, binding
        available = self.unbound_glyphs
        if not available:
            raise UnboundSemanticError("keyboard semantic arena is full")
        digest = hashlib.sha256(operation_id.encode("utf-8")).digest()
        glyph = available[int.from_bytes(digest[:8], "big") % len(available)]
        binding = self._slots[glyph].bind(
            program, verification_status=verification_status
        )
        self._operation_glyphs[operation_id] = glyph
        return glyph, binding

    def execute(self, glyph: str, inputs: Sequence[float]) -> MicroExecution:
        try:
            slot = self._slots[glyph]
        except KeyError as exc:
            raise UnboundSemanticError("glyph is outside the keyboard arena") from exc
        return slot.execute(inputs)


def reduce_micro_node(node: MicroValueNode) -> MicroValueNode:
    if not node.args:
        return node
    left = reduce_micro_node(node.args[0])
    right = reduce_micro_node(node.args[1])
    if left.op == "m_constant" and right.op == "m_constant":
        assert left.constant is not None and right.constant is not None
        value = (
            left.constant + right.constant
            if node.op == "m_add"
            else left.constant - right.constant
        )
        return MicroValueNode("m_constant", constant=float(value))
    if right.op == "m_constant" and right.constant == 0.0:
        return left
    if node.op == "m_add" and left.op == "m_constant" and left.constant == 0.0:
        return right
    if node.op == "m_subtract" and micro_node_key(left) == micro_node_key(right):
        return MicroValueNode("m_constant", constant=0.0)
    return MicroValueNode(node.op, (left, right))


def reduce_micro_program(program: MicroProgram) -> MicroProgram:
    return MicroProgram(
        initial_registers=tuple(
            reduce_micro_node(node) for node in program.initial_registers
        ),
        halt_condition=program.halt_condition,
        updates=tuple(reduce_micro_node(node) for node in program.updates),
        output_register=program.output_register,
    )


def _walk_micro_program_nodes(program: MicroProgram) -> tuple[MicroValueNode, ...]:
    result: list[MicroValueNode] = []
    pending = list(program.initial_registers) + list(program.updates)
    while pending:
        node = pending.pop()
        result.append(node)
        pending.extend(node.args)
    result.append(
        MicroValueNode(
            "m_register", index=program.halt_condition.register_index
        )
    )
    result.append(
        MicroValueNode(
            "m_constant", constant=program.halt_condition.constant
        )
    )
    return tuple(result)


def micro_node_key(node: MicroValueNode) -> str:
    return json.dumps(node.to_dict(), sort_keys=True, separators=(",", ":"))


def micro_program_key(program: MicroProgram) -> str:
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))
