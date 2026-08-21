"""Anonymous physical program search over V21 directed rational semantics."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Sequence

from .directed_rational_construction_v21 import (
    DirectedRationalConstructorV21,
    DirectedRuntimeV21,
    DirectedValueV21,
)
from .proof_driven_program_construction_v20 import AnonymousDerivedRuntimeV20


@dataclass(frozen=True, slots=True)
class TransitionObservationV22:
    world_id: str
    before: tuple[DirectedValueV21, ...]
    after: tuple[DirectedValueV21, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "before": [item.to_dict() for item in self.before],
            "after": [item.to_dict() for item in self.after],
            "human_channel_names": None,
        }


@dataclass(frozen=True, slots=True)
class PhysicalExpressionV22:
    op: str
    args: tuple["PhysicalExpressionV22", ...] = ()
    channel: int | None = None

    @property
    def node_count(self) -> int:
        return 1 + sum(item.node_count for item in self.args)

    @property
    def channels(self) -> frozenset[int]:
        result = {self.channel} if self.channel is not None else set()
        for item in self.args:
            result.update(item.channels)
        return frozenset(result)

    @property
    def expression_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "PHX-" + hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"op": self.op}
        if self.args:
            result["args"] = [item.to_dict() for item in self.args]
        if self.channel is not None:
            result["channel"] = self.channel
        return result

    def render(self) -> str:
        if self.op == "read":
            return f"q{self.channel}"
        if self.op in ("zero", "one"):
            return self.op.upper()
        if self.op == "inverse":
            return f"TURN<{self.args[0].render()}>"
        glyph = "MERGE" if self.op == "combine" else "SEM"
        return f"{glyph}<{self.args[0].render()},{self.args[1].render()}>"


@dataclass(frozen=True, slots=True)
class ChannelProgramV22:
    output_channel: int
    expression: PhysicalExpressionV22
    training_cases: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_channel": self.output_channel,
            "program_id": self.expression.expression_id,
            "expression": self.expression.to_dict(),
            "opaque_program": self.expression.render(),
            "training_cases": self.training_cases,
            "human_law_name": None,
        }


@dataclass(frozen=True, slots=True)
class ConservationCandidateV22:
    expression: PhysicalExpressionV22
    changed_channels: tuple[int, ...]
    case_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "invariant_id": self.expression.expression_id,
            "expression": self.expression.to_dict(),
            "opaque_program": self.expression.render(),
            "changed_channels": list(self.changed_channels),
            "case_count": self.case_count,
            "human_quantity_name": None,
        }


class DirectedPhysicsRuntimeV22:
    def __init__(self, directed_runtime: DirectedRuntimeV21, construction: Any) -> None:
        self.directed = directed_runtime
        self.combine = construction.selected_combine.policy
        self.inverse = construction.selected_inverse
        self.interact = construction.selected_interact.policy
        self.zero = DirectedValueV21(0, 0, 1)
        self.one = DirectedValueV21(1, 0, 1)

    def normalize(self, value: DirectedValueV21) -> DirectedValueV21:
        positive = value.positive
        negative = value.negative
        while positive > 0 and negative > 0:
            positive -= 1
            negative -= 1
        magnitude = self.directed.base.merge(positive, negative)
        if magnitude == 0:
            return self.zero
        left, right = magnitude, value.denominator
        while right > 0:
            _, residual = self.directed.base.decompose(left, right)
            left, right = right, residual
        divisor = left
        if divisor > 1:
            positive, positive_residual = self.directed.base.decompose(positive, divisor)
            negative, negative_residual = self.directed.base.decompose(negative, divisor)
            denominator, denominator_residual = self.directed.base.decompose(value.denominator, divisor)
            if any((positive_residual, negative_residual, denominator_residual)):
                raise RuntimeError("normalization divisor did not divide every channel")
            return DirectedValueV21(positive, negative, denominator)
        return DirectedValueV21(positive, negative, value.denominator)

    def evaluate(self, expression: PhysicalExpressionV22, state: Sequence[DirectedValueV21]) -> DirectedValueV21:
        if expression.op == "read":
            if expression.channel is None or expression.channel >= len(state):
                raise ValueError("physical channel is unavailable")
            return self.normalize(state[expression.channel])
        if expression.op == "zero":
            return self.zero
        if expression.op == "one":
            return self.one
        if expression.op == "inverse":
            return self.normalize(self.directed.execute_unary(self.inverse, self.evaluate(expression.args[0], state)))
        left = self.evaluate(expression.args[0], state)
        right = self.evaluate(expression.args[1], state)
        if expression.op == "combine":
            return self.normalize(self.directed.execute_binary(self.combine, left, right))
        if expression.op == "interact":
            return self.normalize(self.directed.execute_binary(self.interact, left, right))
        raise ValueError("unknown physical expression operation")

    def equivalent(self, left: DirectedValueV21, right: DirectedValueV21) -> bool:
        return self.directed.equivalent(left, right)


@dataclass(frozen=True, slots=True)
class PhysicsDiscoveryV22:
    expressions_generated: int
    channel_programs: tuple[ChannelProgramV22, ...]
    conservation: ConservationCandidateV22
    dimension_constraints: tuple[str, ...]
    kinematic_training_cases: int
    exchange_training_cases: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "expressions_generated": self.expressions_generated,
            "channel_programs": [item.to_dict() for item in self.channel_programs],
            "conservation": self.conservation.to_dict(),
            "dimension_constraints": list(self.dimension_constraints),
            "kinematic_training_cases": self.kinematic_training_cases,
            "exchange_training_cases": self.exchange_training_cases,
        }


def expression_key_v22(expression: PhysicalExpressionV22) -> str:
    if expression.op in ("combine", "interact"):
        children = sorted((expression_key_v22(expression.args[0]), expression_key_v22(expression.args[1])))
        return expression.op + "(" + ",".join(children) + ")"
    if expression.op == "inverse":
        return "inverse(" + expression_key_v22(expression.args[0]) + ")"
    if expression.op == "read":
        return f"read:{expression.channel}"
    return expression.op


class AnonymousPhysicsResearchV22:
    def __init__(self, channel_count: int = 4, maximum_nodes: int = 5) -> None:
        self.channel_count = channel_count
        self.maximum_nodes = maximum_nodes

    @staticmethod
    def build_runtime(observed_values: Sequence[int] = (1, 3, 5, 7, 11, 13, 17)) -> DirectedPhysicsRuntimeV22:
        construction = DirectedRationalConstructorV21().construct(observed_values)
        base = construction.base_construction
        directed = DirectedRuntimeV21(
            AnonymousDerivedRuntimeV20(base.operation_program, base.partition_report.selected.program)
        )
        return DirectedPhysicsRuntimeV22(directed, construction)

    def discover(
        self,
        kinematic_rows: Sequence[TransitionObservationV22],
        exchange_rows: Sequence[TransitionObservationV22],
        *,
        runtime: DirectedPhysicsRuntimeV22 | None = None,
    ) -> PhysicsDiscoveryV22:
        if not kinematic_rows or not exchange_rows:
            raise ValueError("both anonymous experiment families are required")
        runtime = runtime or self.build_runtime()
        expressions = self._enumerate_expressions()
        programs = tuple(
            self._search_channel(output, expressions, kinematic_rows, runtime)
            for output in range(self.channel_count)
        )
        conservation = self._search_conservation(exchange_rows, runtime)
        constraints = self._dimension_constraints(programs)
        return PhysicsDiscoveryV22(
            len(expressions), programs, conservation, constraints,
            len(kinematic_rows), len(exchange_rows),
        )

    def _enumerate_expressions(self) -> tuple[PhysicalExpressionV22, ...]:
        leaves = tuple(PhysicalExpressionV22("read", channel=index) for index in range(self.channel_count)) + (
            PhysicalExpressionV22("zero"), PhysicalExpressionV22("one"),
        )
        by_size: dict[int, dict[str, PhysicalExpressionV22]] = {
            1: {expression_key_v22(item): item for item in leaves}
        }
        for size in range(2, self.maximum_nodes + 1):
            current: dict[str, PhysicalExpressionV22] = {}
            for child in by_size.get(size - 1, {}).values():
                expression = PhysicalExpressionV22("inverse", (child,))
                current[expression_key_v22(expression)] = expression
            for left_size in range(1, size - 1):
                right_size = size - 1 - left_size
                for left in by_size.get(left_size, {}).values():
                    for right in by_size.get(right_size, {}).values():
                        for op in ("combine", "interact"):
                            expression = PhysicalExpressionV22(op, (left, right))
                            current[expression_key_v22(expression)] = expression
            by_size[size] = current
        return tuple(item for size in sorted(by_size) for item in by_size[size].values())

    @staticmethod
    def _search_channel(
        output: int,
        expressions: Sequence[PhysicalExpressionV22],
        rows: Sequence[TransitionObservationV22],
        runtime: DirectedPhysicsRuntimeV22,
    ) -> ChannelProgramV22:
        passing = []
        for expression in expressions:
            if all(runtime.equivalent(runtime.evaluate(expression, row.before), row.after[output]) for row in rows):
                passing.append(expression)
        if not passing:
            raise RuntimeError(f"no physical transition program found for channel {output}")
        passing.sort(key=lambda item: (item.node_count, -len(item.channels), item.expression_id))
        return ChannelProgramV22(output, passing[0], len(rows))

    @staticmethod
    def _search_conservation(
        rows: Sequence[TransitionObservationV22],
        runtime: DirectedPhysicsRuntimeV22,
    ) -> ConservationCandidateV22:
        channel_count = len(rows[0].before)
        changed = tuple(
            index for index in range(channel_count)
            if any(not runtime.equivalent(row.before[index], row.after[index]) for row in rows)
        )
        candidates = []
        for left in range(channel_count):
            for right in range(left + 1, channel_count):
                if left not in changed or right not in changed:
                    continue
                expression = PhysicalExpressionV22(
                    "combine",
                    (PhysicalExpressionV22("read", channel=left), PhysicalExpressionV22("read", channel=right)),
                )
                if all(runtime.equivalent(runtime.evaluate(expression, row.before), runtime.evaluate(expression, row.after)) for row in rows):
                    candidates.append(expression)
        if len(candidates) != 1:
            raise RuntimeError(f"expected one nontrivial two-channel invariant, found {len(candidates)}")
        return ConservationCandidateV22(candidates[0], changed, len(rows))

    @staticmethod
    def _dimension_constraints(programs: Sequence[ChannelProgramV22]) -> tuple[str, ...]:
        constraints = set()

        def dimension(expression: PhysicalExpressionV22) -> str:
            if expression.op == "read":
                return f"D{expression.channel}"
            if expression.op in ("zero", "one"):
                return "0"
            if expression.op == "inverse":
                return dimension(expression.args[0])
            if expression.op == "interact":
                return f"({dimension(expression.args[0])}+{dimension(expression.args[1])})"
            left = dimension(expression.args[0])
            right = dimension(expression.args[1])
            constraints.add(f"{left}={right}")
            return left

        for program in programs:
            result = dimension(program.expression)
            constraints.add(f"D{program.output_channel}={result}")
        constraints.discard("0=0")
        constraints = {item for item in constraints if item.split("=", 1)[0] != item.split("=", 1)[1]}
        return tuple(sorted(constraints))
