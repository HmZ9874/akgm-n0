"""Construct new executable mathematics from V19's anonymous operation."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Sequence

from .autonomous_math_discovery_v19 import OpaqueExpressionExecutorV19, TargetFreeMathematicalResearchV19
from .strict_counter_foundation_v10 import CounterProgram
from .strict_partition_foundation_v11 import (
    EventCounterExecutor,
    EventCounterProgram,
    PartitionExplorationReport,
    TargetFreePartitionExplorer,
)


class ConstructedMathErrorV20(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PairExpressionV20:
    op: str
    args: tuple["PairExpressionV20", ...] = ()
    atom: str | None = None

    @property
    def node_count(self) -> int:
        return 1 + sum(item.node_count for item in self.args)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"op": self.op}
        if self.args:
            result["args"] = [item.to_dict() for item in self.args]
        if self.atom is not None:
            result["atom"] = self.atom
        return result

    def render(self) -> str:
        if self.op == "atom":
            return str(self.atom)
        glyph = "SEM" if self.op == "omega" else "MERGE"
        return f"{glyph}<{self.args[0].render()},{self.args[1].render()}>"


@dataclass(frozen=True, slots=True)
class PairProgramV20:
    numerator: PairExpressionV20
    denominator: PairExpressionV20

    @property
    def node_count(self) -> int:
        return self.numerator.node_count + self.denominator.node_count

    @property
    def program_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "PAIR-" + hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "anonymous_positive_pair_program_v20",
            "numerator": self.numerator.to_dict(),
            "denominator": self.denominator.to_dict(),
            "human_operation_name": None,
        }


@dataclass(frozen=True, slots=True)
class PairLawProfileV20:
    closed: bool
    representation_invariant: bool
    commutative: bool
    associative: bool
    identity_pair: tuple[int, int] | None
    zero_pair_annihilator: bool
    depends_on_both_inputs: bool

    @property
    def promotable(self) -> bool:
        return all((
            self.closed,
            self.representation_invariant,
            self.commutative,
            self.associative,
            self.identity_pair is not None,
            self.depends_on_both_inputs,
        ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "closed_positive_pair": self.closed,
            "representation_invariant": self.representation_invariant,
            "commutative": self.commutative,
            "associative": self.associative,
            "identity_pair": None if self.identity_pair is None else list(self.identity_pair),
            "zero_pair_annihilator": self.zero_pair_annihilator,
            "depends_on_both_inputs": self.depends_on_both_inputs,
            "promotable": self.promotable,
        }


@dataclass(frozen=True, slots=True)
class PairCandidateV20:
    program: PairProgramV20
    profile: PairLawProfileV20
    behavior_signature: tuple[tuple[int, int], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.program.program_id,
            "program": self.program.to_dict(),
            "law_profile": self.profile.to_dict(),
            "behavior_signature": [list(item) for item in self.behavior_signature],
            "program_nodes": self.program.node_count,
        }


@dataclass(frozen=True, slots=True)
class EquationResultV20:
    coefficient: int
    target: int
    candidate: int
    residual: int
    solved: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "coefficient": self.coefficient,
            "target": self.target,
            "candidate": self.candidate,
            "residual": self.residual,
            "solved": self.solved,
        }


class AnonymousDerivedRuntimeV20:
    def __init__(self, operation_program: CounterProgram, partition_program: EventCounterProgram) -> None:
        self.operation_program = operation_program
        self.partition_program = partition_program
        self._omega_executor = OpaqueExpressionExecutorV19(operation_program).executor
        self._partition_executor = EventCounterExecutor(maximum_steps=5_000_000)
        self._omega_cache: dict[tuple[int, int], int] = {}

    def omega(self, left: int, right: int) -> int:
        key = (left, right)
        if key not in self._omega_cache:
            self._omega_cache[key] = self._omega_executor.execute(
                self.operation_program, key
            ).output
        return self._omega_cache[key]

    @staticmethod
    def merge(left: int, right: int) -> int:
        # Physical union of two counter collections; no multiplication or
        # quotient opcode is available here.
        return left + right

    def decompose(self, stream: int, template: int) -> tuple[int, int]:
        program = self.partition_program
        inputs = (stream, template) if program.stream_input == 0 else (template, stream)
        return self._partition_executor.execute(program, inputs).outputs

    def solve_right(self, coefficient: int, target: int) -> EquationResultV20:
        if coefficient <= 0 or target < 0:
            raise ConstructedMathErrorV20("equation domain requires coefficient>0 and target>=0")
        candidate, residual = self.decompose(target, coefficient)
        return EquationResultV20(coefficient, target, candidate, residual, residual == 0)

    def equivalent(self, left: tuple[int, int], right: tuple[int, int]) -> bool:
        self._validate_pair(left)
        self._validate_pair(right)
        return self.omega(left[0], right[1]) == self.omega(right[0], left[1])

    def execute_pair_program(
        self,
        program: PairProgramV20,
        left: tuple[int, int],
        right: tuple[int, int],
    ) -> tuple[int, int]:
        self._validate_pair(left)
        self._validate_pair(right)
        environment = {
            "a": left[0], "b": left[1], "c": right[0], "d": right[1], "0": 0, "1": 1,
        }
        numerator = self._evaluate_pair_expression(program.numerator, environment)
        denominator = self._evaluate_pair_expression(program.denominator, environment)
        if denominator <= 0:
            raise ConstructedMathErrorV20("constructed pair left the positive-denominator domain")
        return numerator, denominator

    def _evaluate_pair_expression(self, expression: PairExpressionV20, environment: dict[str, int]) -> int:
        if expression.op == "atom":
            if expression.atom not in environment:
                raise ConstructedMathErrorV20("unknown pair atom")
            return environment[expression.atom]
        left = self._evaluate_pair_expression(expression.args[0], environment)
        right = self._evaluate_pair_expression(expression.args[1], environment)
        if expression.op == "omega":
            return self.omega(left, right)
        if expression.op == "merge":
            return self.merge(left, right)
        raise ConstructedMathErrorV20("unknown pair expression operation")

    @staticmethod
    def _validate_pair(value: tuple[int, int]) -> None:
        if len(value) != 2 or value[0] < 0 or value[1] <= 0:
            raise ConstructedMathErrorV20("pair domain is N x N+")


@dataclass(frozen=True, slots=True)
class ConstructedMathematicsV20:
    operation_program: CounterProgram
    partition_report: PartitionExplorationReport
    pair_programs_generated: int
    pair_behavior_classes: int
    promoted_pair_operations: tuple[PairCandidateV20, ...]
    equation_examples: tuple[EquationResultV20, ...]


def _expression_key(expression: PairExpressionV20) -> str:
    return json.dumps(expression.to_dict(), sort_keys=True, separators=(",", ":"))


class ProofDrivenProgramConstructorV20:
    """Grow executable concepts from proven semantics, without named targets."""

    PAIRS = ((0, 1), (1, 1), (1, 2), (2, 1), (2, 3), (3, 2))

    def construct(self, observed_values: Sequence[int] = (1, 3, 5, 7, 11, 13, 17)) -> ConstructedMathematicsV20:
        operation = TargetFreeMathematicalResearchV19().discover(observed_values).operation_program
        partition = TargetFreePartitionExplorer().search()
        runtime = AnonymousDerivedRuntimeV20(operation, partition.selected.program)
        candidates, generated = self._search_pair_programs(runtime)
        equation_examples = tuple(
            runtime.solve_right(coefficient, target)
            for coefficient, target in ((3, 21), (4, 18), (5, 0), (7, 49), (8, 65), (11, 121))
        )
        return ConstructedMathematicsV20(
            operation,
            partition,
            generated,
            len(candidates),
            self._select_distinct_pair_operations(candidates),
            equation_examples,
        )

    def _search_pair_programs(
        self, runtime: AnonymousDerivedRuntimeV20
    ) -> tuple[tuple[PairCandidateV20, ...], int]:
        atoms = tuple(PairExpressionV20("atom", atom=name) for name in ("a", "b", "c", "d", "0", "1"))
        products = tuple(PairExpressionV20("omega", (left, right)) for left in atoms for right in atoms)
        merged_products = tuple(
            PairExpressionV20("merge", (left, right))
            for index, left in enumerate(products)
            for right in products[index:]
        )
        numerators = atoms + products + merged_products
        denominators = products

        # Collapse expression behavior before crossing numerator and denominator.
        probe_environments = tuple(
            {"a": a, "b": b, "c": c, "d": d, "0": 0, "1": 1}
            for (a, b), (c, d) in itertools.product(self.PAIRS, repeat=2)
        )
        numerator_leaders = self._behavior_leaders(numerators, probe_environments, runtime)
        denominator_leaders = self._behavior_leaders(denominators, probe_environments, runtime)
        programs = tuple(
            PairProgramV20(numerator, denominator)
            for numerator in numerator_leaders
            for denominator in denominator_leaders
        )
        by_behavior: dict[tuple[tuple[int, int], ...], PairCandidateV20] = {}
        for program in programs:
            try:
                signature = tuple(
                    runtime.execute_pair_program(program, left, right)
                    for left, right in itertools.product(self.PAIRS, repeat=2)
                )
                profile = self._profile(program, runtime, signature)
            except ConstructedMathErrorV20:
                continue
            candidate = PairCandidateV20(program, profile, signature)
            current = by_behavior.get(signature)
            if current is None or (program.node_count, program.program_id) < (
                current.program.node_count, current.program.program_id
            ):
                by_behavior[signature] = candidate
        return tuple(by_behavior.values()), len(programs)

    @staticmethod
    def _behavior_leaders(
        expressions: Sequence[PairExpressionV20],
        environments: Sequence[dict[str, int]],
        runtime: AnonymousDerivedRuntimeV20,
    ) -> tuple[PairExpressionV20, ...]:
        leaders: dict[tuple[int, ...], PairExpressionV20] = {}
        for expression in expressions:
            signature = tuple(runtime._evaluate_pair_expression(expression, env) for env in environments)
            current = leaders.get(signature)
            if current is None or (expression.node_count, _expression_key(expression)) < (
                current.node_count, _expression_key(current)
            ):
                leaders[signature] = expression
        return tuple(leaders.values())

    def _profile(
        self,
        program: PairProgramV20,
        runtime: AnonymousDerivedRuntimeV20,
        signature: tuple[tuple[int, int], ...],
    ) -> PairLawProfileV20:
        pairs = self.PAIRS

        def apply(left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
            return runtime.execute_pair_program(program, left, right)

        closed = all(item[1] > 0 for item in signature)
        representation_invariant = all(
            runtime.equivalent(apply((left[0] * scale, left[1] * scale), right), apply(left, right))
            and runtime.equivalent(apply(left, (right[0] * scale, right[1] * scale)), apply(left, right))
            for left, right in itertools.product(pairs, repeat=2)
            for scale in (2, 3)
        )
        commutative = all(runtime.equivalent(apply(left, right), apply(right, left)) for left, right in itertools.product(pairs, repeat=2))
        small = pairs[:5]
        associative = all(
            runtime.equivalent(apply(apply(left, middle), right), apply(left, apply(middle, right)))
            for left, middle, right in itertools.product(small, repeat=3)
        )
        identity = next(
            (
                candidate for candidate in ((0, 1), (1, 1))
                if all(runtime.equivalent(apply(candidate, value), value) and runtime.equivalent(apply(value, candidate), value) for value in pairs)
            ),
            None,
        )
        zero = (0, 1)
        annihilator = all(runtime.equivalent(apply(zero, value), zero) and runtime.equivalent(apply(value, zero), zero) for value in pairs)
        left_variation = len({apply(pairs[1], item) for item in pairs}) > 1
        right_variation = len({apply(item, pairs[1]) for item in pairs}) > 1
        return PairLawProfileV20(closed, representation_invariant, commutative, associative, identity, annihilator, left_variation and right_variation)

    @staticmethod
    def _select_distinct_pair_operations(
        candidates: Sequence[PairCandidateV20],
    ) -> tuple[PairCandidateV20, ...]:
        promotable = [item for item in candidates if item.profile.promotable]
        by_role: dict[tuple[tuple[int, int], bool], PairCandidateV20] = {}
        for item in promotable:
            role = (item.profile.identity_pair or (-1, -1), item.profile.zero_pair_annihilator)
            current = by_role.get(role)
            if current is None or (item.program.node_count, item.program.program_id) < (
                current.program.node_count, current.program.program_id
            ):
                by_role[role] = item
        selected = sorted(by_role.values(), key=lambda item: (item.profile.identity_pair or (-1, -1), item.program.program_id))
        return tuple(selected)
