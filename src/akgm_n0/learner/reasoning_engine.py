"""Proof-carrying, variable-depth reasoning over anonymous verified operations.

The reasoner receives operation identifiers, executable programs, arities, and
proof-record identifiers.  It does not receive operation names or a target
composition template.  Intermediate expressions are created from observed
behavior, retained as hypotheses, and compiled into a replayable composition
graph only after search.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .composition_frontier import (
    CompositionExecutor,
    CompositionGraphProgram,
    CompositionNode,
    composition_key,
)
from .metamachine_gen2 import InvalidReflectiveProgram, ReflectiveProgram
from .observation import NumericTableObservation


@dataclass(frozen=True, slots=True)
class ReasoningExpression:
    """An input leaf or an anonymous operation applied to prior expressions."""

    operation_id: str | None
    input_index: int | None = None
    arguments: tuple["ReasoningExpression", ...] = ()

    @classmethod
    def input(cls, index: int) -> "ReasoningExpression":
        return cls(None, index, ())

    @classmethod
    def apply(
        cls, operation_id: str, arguments: Sequence["ReasoningExpression"]
    ) -> "ReasoningExpression":
        return cls(operation_id, None, tuple(arguments))

    @property
    def depth(self) -> int:
        if self.operation_id is None:
            return 0
        return 1 + max(argument.depth for argument in self.arguments)

    @property
    def node_count(self) -> int:
        if self.operation_id is None:
            return 0
        return 1 + sum(argument.node_count for argument in self.arguments)

    def key(self) -> str:
        if self.operation_id is None:
            return f"i:{self.input_index}"
        return "(" + self.operation_id + " " + " ".join(
            argument.key() for argument in self.arguments
        ) + ")"

    def to_program(self) -> CompositionGraphProgram:
        nodes: list[CompositionNode] = []
        memo: dict[str, int] = {}

        def emit(expression: "ReasoningExpression") -> str:
            if expression.operation_id is None:
                assert expression.input_index is not None
                return f"input:{expression.input_index}"
            key = expression.key()
            if key in memo:
                return f"node:{memo[key]}"
            arguments = tuple(emit(argument) for argument in expression.arguments)
            index = len(nodes)
            nodes.append(CompositionNode(expression.operation_id, arguments))
            memo[key] = index
            return f"node:{index}"

        output_reference = emit(self)
        if not output_reference.startswith("node:"):
            raise ValueError("a reasoning result must contain an operation")
        return CompositionGraphProgram(tuple(nodes))


@dataclass(frozen=True, slots=True)
class ReasoningState:
    expression: ReasoningExpression
    outputs: tuple[float, ...]
    fit_error: float
    maximum_absolute_error: float

    @property
    def exact(self) -> bool:
        return self.maximum_absolute_error == 0.0


@dataclass(frozen=True, slots=True)
class ReasoningStep:
    node_index: int
    operation_id: str
    arguments: tuple[str, ...]
    component_proof_record_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_index": self.node_index,
            "operation_id": self.operation_id,
            "arguments": list(self.arguments),
            "component_proof_record_id": self.component_proof_record_id,
        }


@dataclass(frozen=True, slots=True)
class ReasoningCandidate:
    candidate_id: str
    program: CompositionGraphProgram
    fit_error: float
    maximum_absolute_error: float
    outputs: tuple[float, ...]
    behavior_signature: tuple[float, ...]
    reasoning_depth: int
    reasoning_steps: tuple[ReasoningStep, ...]

    @property
    def exact(self) -> bool:
        return self.maximum_absolute_error == 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "program": self.program.to_dict(),
            "fit_error": self.fit_error,
            "maximum_absolute_error": self.maximum_absolute_error,
            "outputs": list(self.outputs),
            "behavior_signature": list(self.behavior_signature),
            "reasoning_depth": self.reasoning_depth,
            "reasoning_steps": [step.to_dict() for step in self.reasoning_steps],
            "instruction_count": len(self.program.nodes),
            "exact": self.exact,
        }


@dataclass(frozen=True, slots=True)
class ReasoningLayerReport:
    depth: int
    programs_generated: int
    programs_executed: int
    programs_rejected: int
    retained_states: int
    exact_states: int

    def to_dict(self) -> dict[str, int]:
        return {
            "depth": self.depth,
            "programs_generated": self.programs_generated,
            "programs_executed": self.programs_executed,
            "programs_rejected": self.programs_rejected,
            "retained_states": self.retained_states,
            "exact_states": self.exact_states,
        }


@dataclass(frozen=True, slots=True)
class ReasoningSearchReport:
    programs_generated: int
    programs_executed: int
    programs_rejected: int
    behavior_classes: int
    top_candidates: tuple[ReasoningCandidate, ...]
    layers: tuple[ReasoningLayerReport, ...]


class ProofCarryingReasoner:
    """Grow a behavior-deduplicated reasoning graph to an unknown depth.

    Search is bounded but its graph shape is not supplied.  A small number of
    structurally distinct hypotheses is retained for each observed behavior so
    active experiments can later separate accidental agreements.
    """

    def __init__(
        self,
        library: Mapping[str, ReflectiveProgram],
        arities: Mapping[str, int],
        component_proof_records: Mapping[str, str],
        *,
        maximum_depth: int = 3,
        maximum_binary_depth: int | None = None,
        maximum_nodes: int = 6,
        maximum_argument_states: int = 140,
        beam_per_depth: int = 2500,
        hypotheses_per_behavior: int = 4,
        top_k: int = 1000,
        maximum_absolute_value: float = 1_000_000_000_000.0,
    ) -> None:
        self.library = dict(library)
        self.arities = dict(arities)
        self.component_proof_records = dict(component_proof_records)
        if set(self.library) != set(self.arities):
            raise ValueError("every reasoning operation requires an arity")
        if not set(self.library).issubset(self.component_proof_records):
            raise ValueError("every reasoning operation requires a proof record")
        if any(arity not in (1, 2) for arity in self.arities.values()):
            raise ValueError("this reasoning substrate supports unary and binary operations")
        self.maximum_depth = maximum_depth
        self.maximum_binary_depth = (
            maximum_depth if maximum_binary_depth is None else maximum_binary_depth
        )
        self.maximum_nodes = maximum_nodes
        self.maximum_argument_states = maximum_argument_states
        self.beam_per_depth = beam_per_depth
        self.hypotheses_per_behavior = hypotheses_per_behavior
        self.top_k = top_k
        self.maximum_absolute_value = maximum_absolute_value
        self.executor = CompositionExecutor(self.library)
        # Persistent across active-learning rounds: a proven component is a
        # deterministic function, so replaying the same scalar call adds no
        # evidence and should not consume another VM execution.
        self._scalar_call_cache: dict[tuple[str, tuple[float, ...]], float | None] = {}

    def search(self, observation: NumericTableObservation) -> ReasoningSearchReport:
        valid = tuple(
            (tuple(float(value) for value in row), float(output))
            for row, output, include in zip(
                observation.input_rows,
                observation.output_values,
                observation.validity_mask,
                strict=True,
            )
            if include
        )
        if not valid:
            raise ValueError("reasoning requires at least one valid observation")
        width = len(valid[0][0])
        if any(len(row) != width for row, _ in valid):
            raise ValueError("reasoning input rows must have a stable width")
        targets = tuple(output for _, output in valid)
        input_states = tuple(
            self._state(
                ReasoningExpression.input(index),
                tuple(row[index] for row, _ in valid),
                targets,
            )
            for index in range(width)
        )
        retained: list[ReasoningState] = list(input_states)
        operation_states: list[ReasoningState] = []
        vector_cache: dict[tuple[str, tuple[tuple[float, ...], ...]], tuple[float, ...] | None] = {}
        layers: list[ReasoningLayerReport] = []
        total_generated = total_executed = total_rejected = 0

        for depth in range(1, self.maximum_depth + 1):
            argument_pool = self._argument_pool(retained, targets)
            generated = executed = rejected = 0
            new_states: list[ReasoningState] = []
            per_behavior: dict[tuple[float, ...], list[ReasoningState]] = {}
            for operation_id in sorted(self.library):
                arity = self.arities[operation_id]
                if arity == 2 and depth > self.maximum_binary_depth:
                    continue
                for arguments in itertools.product(argument_pool, repeat=arity):
                    if max(argument.expression.depth for argument in arguments) != depth - 1:
                        continue
                    expression = ReasoningExpression.apply(
                        operation_id, tuple(argument.expression for argument in arguments)
                    )
                    if expression.node_count > self.maximum_nodes:
                        continue
                    generated += 1
                    cache_key = (operation_id, tuple(argument.outputs for argument in arguments))
                    outputs = vector_cache.get(cache_key)
                    if cache_key not in vector_cache:
                        outputs = self._execute_vector(operation_id, arguments, len(valid))
                        vector_cache[cache_key] = outputs
                    if outputs is None:
                        rejected += 1
                        continue
                    executed += 1
                    state = self._state(expression, outputs, targets)
                    bucket = per_behavior.setdefault(outputs, [])
                    bucket.append(state)
                    bucket.sort(key=self._state_key)
                    del bucket[self.hypotheses_per_behavior :]
            for bucket in per_behavior.values():
                new_states.extend(bucket)
            new_states.sort(key=self._state_key)
            new_states = self._stratified_beam(new_states)
            operation_states.extend(new_states)
            retained.extend(new_states)
            total_generated += generated
            total_executed += executed
            total_rejected += rejected
            layers.append(
                ReasoningLayerReport(
                    depth,
                    generated,
                    executed,
                    rejected,
                    len(new_states),
                    sum(state.exact for state in new_states),
                )
            )

        candidates = [self._candidate(state) for state in operation_states]
        candidates.sort(
            key=lambda item: (
                item.fit_error,
                len(item.program.nodes),
                item.reasoning_depth,
                composition_key(item.program),
            )
        )
        return ReasoningSearchReport(
            total_generated,
            total_executed,
            total_rejected,
            len({state.outputs for state in operation_states}),
            tuple(candidates[: self.top_k]),
            tuple(layers),
        )

    def _argument_pool(
        self, states: Sequence[ReasoningState], targets: tuple[float, ...]
    ) -> tuple[ReasoningState, ...]:
        if len(states) <= self.maximum_argument_states:
            return tuple(states)
        ranked = sorted(states, key=self._state_key)
        relevance_count = max(1, self.maximum_argument_states * 3 // 4)
        selected = list(ranked[:relevance_count])
        selected_keys = {state.expression.key() for state in selected}
        # A deterministic novelty sample prevents a purely target-distance beam
        # from erasing useful intermediate conclusions.
        novelty = sorted(
            states,
            key=lambda state: hashlib.sha256(
                (state.expression.key() + repr(targets)).encode()
            ).hexdigest(),
        )
        for state in novelty:
            if state.expression.key() in selected_keys:
                continue
            selected.append(state)
            selected_keys.add(state.expression.key())
            if len(selected) >= self.maximum_argument_states:
                break
        return tuple(selected)

    def _stratified_beam(self, states: list[ReasoningState]) -> list[ReasoningState]:
        if len(states) <= self.beam_per_depth:
            return states
        relevance_count = self.beam_per_depth * 3 // 4
        selected = states[:relevance_count]
        selected_keys = {state.expression.key() for state in selected}
        for state in sorted(
            states,
            key=lambda item: hashlib.sha256(item.expression.key().encode()).hexdigest(),
        ):
            if state.expression.key() in selected_keys:
                continue
            selected.append(state)
            selected_keys.add(state.expression.key())
            if len(selected) >= self.beam_per_depth:
                break
        return selected

    def _execute_vector(
        self,
        operation_id: str,
        arguments: Sequence[ReasoningState],
        row_count: int,
    ) -> tuple[float, ...] | None:
        program = self.library[operation_id]
        outputs: list[float] = []
        for index in range(row_count):
            values = tuple(argument.outputs[index] for argument in arguments)
            cache_key = (operation_id, values)
            if cache_key in self._scalar_call_cache:
                output = self._scalar_call_cache[cache_key]
                if output is None:
                    return None
                outputs.append(output)
                continue
            try:
                output = float(self.executor.executor.execute(program, values).output_value)
                if not math.isfinite(output) or abs(output) > self.maximum_absolute_value:
                    self._scalar_call_cache[cache_key] = None
                    return None
                self._scalar_call_cache[cache_key] = output
                outputs.append(output)
            except (InvalidReflectiveProgram, IndexError, OverflowError):
                self._scalar_call_cache[cache_key] = None
                return None
        return tuple(outputs)

    @staticmethod
    def _state(
        expression: ReasoningExpression,
        outputs: tuple[float, ...],
        targets: tuple[float, ...],
    ) -> ReasoningState:
        errors = tuple(actual - target for actual, target in zip(outputs, targets, strict=True))
        return ReasoningState(
            expression,
            outputs,
            sum(error * error for error in errors) / len(errors),
            max(abs(error) for error in errors),
        )

    @staticmethod
    def _state_key(state: ReasoningState) -> tuple[float, int, int, str]:
        return (
            state.fit_error,
            state.expression.node_count,
            state.expression.depth,
            state.expression.key(),
        )

    def _candidate(self, state: ReasoningState) -> ReasoningCandidate:
        program = state.expression.to_program()
        key = composition_key(program)
        steps = tuple(
            ReasoningStep(
                index,
                node.operation_id,
                node.arguments,
                self.component_proof_records[node.operation_id],
            )
            for index, node in enumerate(program.nodes)
        )
        return ReasoningCandidate(
            "RSN-" + hashlib.sha256(key.encode()).hexdigest()[:16],
            program,
            state.fit_error,
            state.maximum_absolute_error,
            state.outputs,
            state.outputs,
            state.expression.depth,
            steps,
        )


class ReasoningTraceVerifier:
    """Independently replay a reasoning graph and its component proof lineage."""

    def __init__(
        self,
        library: Mapping[str, ReflectiveProgram],
        component_proof_records: Mapping[str, str],
    ) -> None:
        self.executor = CompositionExecutor(library)
        self.proofs = dict(component_proof_records)

    def verify(
        self,
        candidate: ReasoningCandidate,
        cases: Sequence[tuple[Sequence[float], float]],
    ) -> dict[str, Any]:
        structural = all(
            step.node_index == index
            and step.operation_id == candidate.program.nodes[index].operation_id
            and step.arguments == candidate.program.nodes[index].arguments
            and self.proofs.get(step.operation_id) == step.component_proof_record_id
            for index, step in enumerate(candidate.reasoning_steps)
        )
        results = []
        for inputs, expected in cases:
            try:
                actual = self.executor.execute(candidate.program, tuple(inputs)).output_value
                passed = actual == float(expected)
            except (InvalidReflectiveProgram, IndexError, OverflowError):
                actual = None
                passed = False
            results.append(
                {
                    "inputs": list(inputs),
                    "predicted": actual,
                    "observed": float(expected),
                    "passed": passed,
                }
            )
        obligations = (
            {
                "obligation_id": "trace_structure_matches_program",
                "passed": structural,
            },
            {
                "obligation_id": "all_components_have_proof_records",
                "passed": all(
                    step.component_proof_record_id.startswith("UF-")
                    for step in candidate.reasoning_steps
                ),
            },
            {
                "obligation_id": "all_replay_cases_exact",
                "passed": all(result["passed"] for result in results),
            },
        )
        return {
            "verifier_version": "reasoning-trace-verifier-v0.1",
            "passed": all(item["passed"] for item in obligations),
            "obligations": list(obligations),
            "case_results": results,
        }
