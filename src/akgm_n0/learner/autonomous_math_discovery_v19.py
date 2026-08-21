"""Target-free conjecture generation over an anonymously discovered operation."""

from __future__ import annotations

import hashlib
import itertools
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Sequence

from .strict_counter_foundation_v10 import (
    CounterExecutor,
    CounterProgram,
    TargetFreeCounterExplorer,
)


@dataclass(frozen=True, slots=True)
class MathExprV19:
    op: str
    args: tuple["MathExprV19", ...] = ()
    variable: str | None = None
    constant: int | None = None

    @property
    def node_count(self) -> int:
        return 1 + sum(item.node_count for item in self.args)

    @property
    def variables(self) -> frozenset[str]:
        result = {self.variable} if self.variable is not None else set()
        for item in self.args:
            result.update(item.variables)
        return frozenset(result)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"op": self.op}
        if self.args:
            result["args"] = [item.to_dict() for item in self.args]
        if self.variable is not None:
            result["variable"] = self.variable
        if self.constant is not None:
            result["constant"] = self.constant
        return result


@dataclass(frozen=True, slots=True)
class ConjectureV19:
    conjecture_id: str
    left: MathExprV19
    right: MathExprV19
    probe_signature: tuple[int, ...]
    variable_set: tuple[str, ...]
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "conjecture_id": self.conjecture_id,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "probe_signature": list(self.probe_signature),
            "variable_set": list(self.variable_set),
            "source": self.source,
            "human_name_given_to_learner": False,
        }


@dataclass(frozen=True, slots=True)
class FactorObservationV19:
    value: int
    classification: str
    witness: tuple[int, int] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "classification": self.classification,
            "witness": None if self.witness is None else list(self.witness),
        }


@dataclass(frozen=True, slots=True)
class AutonomousMathDiscoveryV19:
    operation_program: CounterProgram
    programs_generated: int
    behavior_classes: int
    conjectures: tuple[ConjectureV19, ...]
    falsification_candidates: tuple[ConjectureV19, ...]
    input_factor_observations: tuple[FactorObservationV19, ...]
    generated_factor_observations: tuple[FactorObservationV19, ...]
    expressions_enumerated: int


def expression_key(expression: MathExprV19) -> str:
    return json.dumps(expression.to_dict(), sort_keys=True, separators=(",", ":"))


class OpaqueExpressionExecutorV19:
    def __init__(self, program: CounterProgram) -> None:
        self.program = program
        self.executor = CounterExecutor(maximum_steps=1_000_000)

    def evaluate(self, expression: MathExprV19, environment: dict[str, int]) -> int:
        if expression.op == "v":
            if expression.variable not in environment:
                raise ValueError("expression variable is unavailable")
            return environment[expression.variable]
        if expression.op == "c":
            if expression.constant is None:
                raise ValueError("expression constant is unavailable")
            return expression.constant
        if expression.op != "omega" or len(expression.args) != 2:
            raise ValueError("expression operation is unavailable")
        left = self.evaluate(expression.args[0], environment)
        right = self.evaluate(expression.args[1], environment)
        return self.executor.execute(self.program, (left, right)).output


class TargetFreeMathematicalResearchV19:
    """Discover one operation, conjecture its laws, and induce factor concepts."""

    VARIABLES = ("v0", "v1", "v2")

    def __init__(self, *, probe_limit: int = 3, maximum_expression_nodes: int = 5) -> None:
        self.probe_limit = probe_limit
        self.maximum_expression_nodes = maximum_expression_nodes

    def discover(self, observed_values: Sequence[int]) -> AutonomousMathDiscoveryV19:
        if not observed_values or any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in observed_values):
            raise ValueError("mathematical observations must be natural integers")
        exploration = TargetFreeCounterExplorer().search()
        program = exploration.selected.program
        executor = OpaqueExpressionExecutorV19(program)
        expressions = self._enumerate_expressions()
        probe_rows = tuple(itertools.product(range(self.probe_limit + 1), repeat=len(self.VARIABLES)))
        by_signature: dict[tuple[int, ...], list[MathExprV19]] = defaultdict(list)
        for expression in expressions:
            signature = tuple(
                executor.evaluate(expression, dict(zip(self.VARIABLES, row, strict=True)))
                for row in probe_rows
            )
            by_signature[signature].append(expression)
        conjectures = self._equivalent_conjectures(by_signature)
        false_candidates = self._falsification_candidates(expressions, executor, probe_rows, conjectures)
        observed = tuple(self._factor_observation(value, executor) for value in observed_values)
        generated = tuple(self._factor_observation(value, executor) for value in range(1, 41))
        return AutonomousMathDiscoveryV19(
            program,
            exploration.programs_generated,
            exploration.behavior_classes,
            conjectures,
            false_candidates,
            observed,
            generated,
            len(expressions),
        )

    def _enumerate_expressions(self) -> tuple[MathExprV19, ...]:
        leaves = tuple(MathExprV19("v", variable=name) for name in self.VARIABLES) + (
            MathExprV19("c", constant=0),
            MathExprV19("c", constant=1),
        )
        by_size: dict[int, dict[str, MathExprV19]] = {1: {expression_key(item): item for item in leaves}}
        for size in range(3, self.maximum_expression_nodes + 1, 2):
            current: dict[str, MathExprV19] = {}
            for left_size in range(1, size - 1, 2):
                right_size = size - 1 - left_size
                for left in by_size[left_size].values():
                    for right in by_size[right_size].values():
                        expression = MathExprV19("omega", (left, right))
                        current[expression_key(expression)] = expression
            by_size[size] = current
        return tuple(item for size in sorted(by_size) for item in by_size[size].values())

    def _equivalent_conjectures(
        self,
        by_signature: dict[tuple[int, ...], list[MathExprV19]],
    ) -> tuple[ConjectureV19, ...]:
        candidates = []
        seen = set()
        for signature, group in by_signature.items():
            ordered = sorted(group, key=lambda item: (item.node_count, expression_key(item)))
            for left_index, left in enumerate(ordered):
                for right in ordered[left_index + 1:]:
                    variables = left.variables | right.variables
                    if not variables:
                        continue
                    if "omega" not in {left.op, right.op} and left.node_count == right.node_count == 1:
                        continue
                    pair_key = expression_key(left) + "=" + expression_key(right)
                    digest = hashlib.sha256(pair_key.encode()).hexdigest()
                    topology = (
                        tuple(sorted(variables)),
                        left.node_count,
                        right.node_count,
                        self._shape(left),
                        self._shape(right),
                    )
                    if topology in seen:
                        continue
                    seen.add(topology)
                    candidates.append(ConjectureV19(
                        "MC-" + digest[:16], left, right, signature,
                        tuple(sorted(variables)), "behavioral_equivalence_without_named_law",
                    ))
        candidates.sort(key=lambda item: (
            item.left.node_count + item.right.node_count,
            -len(item.variable_set),
            item.conjecture_id,
        ))
        # Retain breadth without supplying any named law template.  Each
        # variable-coverage stratum gets a quota before remaining low-complexity
        # identities fill the room. Within a stratum, round-robin over distinct
        # observed behaviors so a degenerate constant behavior cannot crowd out
        # richer behaviors.
        selected: list[ConjectureV19] = []
        selected_ids: set[str] = set()
        for variable_count, quota in ((3, 20), (2, 30), (1, 30)):
            behavior_groups: dict[tuple[int, ...], list[ConjectureV19]] = defaultdict(list)
            for item in candidates:
                if len(item.variable_set) == variable_count:
                    behavior_groups[item.probe_signature].append(item)
            groups = sorted(
                behavior_groups.values(),
                key=lambda group: (
                    group[0].left.node_count + group[0].right.node_count,
                    -len(set(group[0].probe_signature)),
                    group[0].conjecture_id,
                ),
            )
            while groups and sum(len(entry.variable_set) == variable_count for entry in selected) < quota:
                next_groups = []
                for group in groups:
                    item = group.pop(0)
                    selected.append(item)
                    selected_ids.add(item.conjecture_id)
                    if group:
                        next_groups.append(group)
                    if sum(len(entry.variable_set) == variable_count for entry in selected) == quota:
                        break
                groups = next_groups
        for item in candidates:
            if len(selected) == 80:
                break
            if item.conjecture_id not in selected_ids:
                selected.append(item)
                selected_ids.add(item.conjecture_id)
        return tuple(selected)

    def _falsification_candidates(
        self,
        expressions: Sequence[MathExprV19],
        executor: OpaqueExpressionExecutorV19,
        rows: Sequence[tuple[int, ...]],
        accepted: Sequence[ConjectureV19],
    ) -> tuple[ConjectureV19, ...]:
        accepted_pairs = {
            frozenset((expression_key(item.left), expression_key(item.right))) for item in accepted
        }
        compact = [item for item in expressions if item.node_count <= 3 and item.variables]
        result = []
        for left, right in itertools.combinations(compact, 2):
            if left.variables != right.variables:
                continue
            pair = frozenset((expression_key(left), expression_key(right)))
            if pair in accepted_pairs:
                continue
            left_signature = tuple(executor.evaluate(left, dict(zip(self.VARIABLES, row, strict=True))) for row in rows)
            right_signature = tuple(executor.evaluate(right, dict(zip(self.VARIABLES, row, strict=True))) for row in rows)
            if left_signature == right_signature:
                continue
            digest = hashlib.sha256((expression_key(left) + "!=" + expression_key(right)).encode()).hexdigest()
            result.append(ConjectureV19(
                "MF-" + digest[:16], left, right, left_signature,
                tuple(sorted(left.variables)), "generic_nearby_expression_pair",
            ))
            if len(result) == 40:
                break
        return tuple(result)

    @staticmethod
    def _shape(expression: MathExprV19) -> str:
        if expression.op == "v":
            return "v"
        if expression.op == "c":
            return "c"
        return "o(" + ",".join(TargetFreeMathematicalResearchV19._shape(item) for item in expression.args) + ")"

    @staticmethod
    def _factor_observation(value: int, executor: OpaqueExpressionExecutorV19) -> FactorObservationV19:
        if value <= 1:
            return FactorObservationV19(value, "boundary", None)
        for left in range(2, value):
            for right in range(2, value):
                expression = MathExprV19("omega", (MathExprV19("c", constant=left), MathExprV19("c", constant=right)))
                if executor.evaluate(expression, {}) == value:
                    return FactorObservationV19(value, "has_internal_witness", (left, right))
        return FactorObservationV19(value, "no_internal_witness", None)
