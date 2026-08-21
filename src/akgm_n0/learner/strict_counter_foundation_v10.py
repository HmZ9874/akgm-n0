"""Target-free exploration of small counter programs.

The learner receives neither numeric target rows nor named arithmetic operations.
It enumerates two-level programs built from counter drain/transfer loops and lets
an evaluator inspect the resulting behavior tables after execution.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Callable


REGISTER_COUNT = 4


class CounterExecutionError(RuntimeError):
    """Raised when a candidate exceeds the registered execution boundary."""


@dataclass(frozen=True, slots=True)
class CounterMove:
    """Drain one register, emitting one increment to every destination."""

    source: int
    destinations: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.source not in range(REGISTER_COUNT):
            raise ValueError("counter source is unavailable")
        if not self.destinations or len(set(self.destinations)) != len(self.destinations):
            raise ValueError("counter destinations must be nonempty and distinct")
        if any(item not in range(REGISTER_COUNT) for item in self.destinations):
            raise ValueError("counter destination is unavailable")
        if self.source in self.destinations:
            raise ValueError("a drain loop cannot increment its own source")

    def to_dict(self) -> dict[str, Any]:
        return {
            "while_nonempty": self.source,
            "body": [
                {"op": "decrement_one", "register": self.source},
                *(
                    {"op": "increment_one", "register": destination}
                    for destination in self.destinations
                ),
            ],
        }


@dataclass(frozen=True, slots=True)
class CounterProgram:
    outer_source: int
    first_move: CounterMove
    second_move: CounterMove
    output_register: int

    def __post_init__(self) -> None:
        if self.outer_source not in (0, 1):
            raise ValueError("outer source must be one of the anonymous input registers")
        if self.output_register not in range(REGISTER_COUNT):
            raise ValueError("output register is unavailable")

    @property
    def primitive_node_count(self) -> int:
        return 4 + len(self.first_move.destinations) + len(self.second_move.destinations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "anonymous_counter_transfer_v10",
            "initial_registers": ["input_0", "input_1", 0, 0],
            "program": {
                "while_nonempty": self.outer_source,
                "body": [
                    {"op": "decrement_one", "register": self.outer_source},
                    self.first_move.to_dict(),
                    self.second_move.to_dict(),
                ],
            },
            "output_register": self.output_register,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CounterProgram":
        if value.get("substrate") != "anonymous_counter_transfer_v10":
            raise ValueError("counter program substrate is unavailable")
        body = value["program"]["body"]

        def parse_move(raw: dict[str, Any]) -> CounterMove:
            instructions = raw["body"]
            source = int(raw["while_nonempty"])
            if instructions[0] != {"op": "decrement_one", "register": source}:
                raise ValueError("counter move must begin with a unit decrement")
            destinations = tuple(
                int(item["register"])
                for item in instructions[1:]
                if item.get("op") == "increment_one"
            )
            if len(destinations) != len(instructions) - 1:
                raise ValueError("counter move contains an unknown primitive")
            return CounterMove(source, destinations)

        outer = int(value["program"]["while_nonempty"])
        if body[0] != {"op": "decrement_one", "register": outer}:
            raise ValueError("outer loop must begin with a unit decrement")
        return cls(outer, parse_move(body[1]), parse_move(body[2]), int(value["output_register"]))


@dataclass(frozen=True, slots=True)
class CounterExecution:
    output: int
    final_registers: tuple[int, ...]
    primitive_steps: int


class CounterExecutor:
    """Execute a candidate using only natural counters and unit transitions."""

    def __init__(self, maximum_steps: int = 200_000) -> None:
        self.maximum_steps = maximum_steps

    def execute(self, program: CounterProgram, inputs: tuple[int, int]) -> CounterExecution:
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in inputs):
            raise CounterExecutionError("counter inputs must be natural numbers")
        registers = [inputs[0], inputs[1], 0, 0]
        steps = 0
        while registers[program.outer_source] > 0:
            registers[program.outer_source] -= 1
            steps += 1
            steps = self._move(program.first_move, registers, steps)
            steps = self._move(program.second_move, registers, steps)
            if steps > self.maximum_steps:
                raise CounterExecutionError("candidate exceeded its primitive step budget")
        return CounterExecution(
            registers[program.output_register], tuple(registers), steps
        )

    def _move(self, move: CounterMove, registers: list[int], steps: int) -> int:
        while registers[move.source] > 0:
            registers[move.source] -= 1
            steps += 1
            for destination in move.destinations:
                registers[destination] += 1
                steps += 1
            if steps > self.maximum_steps:
                raise CounterExecutionError("candidate exceeded its primitive step budget")
        return steps


@dataclass(frozen=True, slots=True)
class AlgebraicProfile:
    depends_on_both_inputs: bool
    has_cross_input_interaction: bool
    commutative: bool
    associative: bool
    identity: int | None
    annihilator: int | None
    left_distributive_over_combine: bool
    right_distributive_over_combine: bool
    monotone: bool

    @property
    def promotable(self) -> bool:
        return all(
            (
                self.depends_on_both_inputs,
                self.has_cross_input_interaction,
                self.commutative,
                self.associative,
                self.identity is not None,
                self.annihilator is not None,
                self.left_distributive_over_combine,
                self.right_distributive_over_combine,
                self.monotone,
            )
        )

    @property
    def law_count(self) -> int:
        return sum(
            (
                self.depends_on_both_inputs,
                self.has_cross_input_interaction,
                self.commutative,
                self.associative,
                self.identity is not None,
                self.annihilator is not None,
                self.left_distributive_over_combine,
                self.right_distributive_over_combine,
                self.monotone,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "depends_on_both_inputs": self.depends_on_both_inputs,
            "has_cross_input_interaction": self.has_cross_input_interaction,
            "commutative": self.commutative,
            "associative": self.associative,
            "identity": self.identity,
            "annihilator": self.annihilator,
            "left_distributive_over_previously_verified_combine": self.left_distributive_over_combine,
            "right_distributive_over_previously_verified_combine": self.right_distributive_over_combine,
            "monotone": self.monotone,
            "law_count": self.law_count,
            "promotable": self.promotable,
        }


@dataclass(frozen=True, slots=True)
class CounterCandidate:
    candidate_id: str
    program: CounterProgram
    behavior_signature: tuple[int, ...]
    profile: AlgebraicProfile
    probe_step_cost: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "program": self.program.to_dict(),
            "behavior_signature": list(self.behavior_signature),
            "algebraic_profile": self.profile.to_dict(),
            "primitive_node_count": self.program.primitive_node_count,
            "probe_step_cost": self.probe_step_cost,
        }


@dataclass(frozen=True, slots=True)
class CounterExplorationReport:
    programs_generated: int
    programs_executed: int
    behavior_classes: int
    promotable_behavior_classes: int
    selected: CounterCandidate
    rejected_leaders: tuple[CounterCandidate, ...]


def program_key(program: CounterProgram) -> str:
    return json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))


def candidate_id(program: CounterProgram) -> str:
    return "CT-" + hashlib.sha256(program_key(program).encode()).hexdigest()[:16]


class TargetFreeCounterExplorer:
    """Enumerate programs first, then inspect unnamed behaviors for generic laws."""

    def __init__(self, probe_limit: int = 4, law_limit: int = 3) -> None:
        self.probe_limit = probe_limit
        self.law_limit = law_limit
        self.executor = CounterExecutor()

    def enumerate_programs(self) -> tuple[CounterProgram, ...]:
        destination_options = {
            source: tuple(
                destinations
                for size in (1, 2)
                for destinations in itertools.combinations(
                    (item for item in range(REGISTER_COUNT) if item != source), size
                )
            )
            for source in range(REGISTER_COUNT)
        }
        programs = []
        for outer_source in (0, 1):
            for first_source in range(REGISTER_COUNT):
                for first_destinations in destination_options[first_source]:
                    for second_source in range(REGISTER_COUNT):
                        for second_destinations in destination_options[second_source]:
                            for output_register in range(REGISTER_COUNT):
                                programs.append(
                                    CounterProgram(
                                        outer_source,
                                        CounterMove(first_source, first_destinations),
                                        CounterMove(second_source, second_destinations),
                                        output_register,
                                    )
                                )
        return tuple(programs)

    def search(self) -> CounterExplorationReport:
        programs = self.enumerate_programs()
        by_behavior: dict[tuple[int, ...], CounterCandidate] = {}
        executed = 0
        for program in programs:
            signature = []
            step_cost = 0
            try:
                for left in range(self.probe_limit + 1):
                    for right in range(self.probe_limit + 1):
                        result = self.executor.execute(program, (left, right))
                        signature.append(result.output)
                        step_cost += result.primitive_steps
            except CounterExecutionError:
                continue
            executed += 1
            behavior = tuple(signature)
            current = by_behavior.get(behavior)
            profile = inspect_algebraic_profile(
                lambda left, right, candidate=program: self.executor.execute(
                    candidate, (left, right)
                ).output,
                limit=self.law_limit,
            )
            item = CounterCandidate(
                candidate_id(program), program, behavior, profile, step_cost
            )
            if current is None or self._sort_key(item) < self._sort_key(current):
                by_behavior[behavior] = item
        candidates = sorted(by_behavior.values(), key=self._sort_key)
        promotable = [item for item in candidates if item.profile.promotable]
        if not promotable:
            raise RuntimeError("target-free counter exploration found no promotable behavior")
        return CounterExplorationReport(
            programs_generated=len(programs),
            programs_executed=executed,
            behavior_classes=len(candidates),
            promotable_behavior_classes=len(promotable),
            selected=promotable[0],
            rejected_leaders=tuple(item for item in candidates if not item.profile.promotable)[:20],
        )

    @staticmethod
    def _sort_key(item: CounterCandidate) -> tuple[Any, ...]:
        return (
            -item.profile.law_count,
            item.program.primitive_node_count,
            item.probe_step_cost,
            item.candidate_id,
        )


def inspect_algebraic_profile(
    operation: Callable[[int, int], int], *, limit: int
) -> AlgebraicProfile:
    values = range(limit + 1)
    table = {(left, right): operation(left, right) for left in values for right in values}
    depends_left = any(table[left, right] != table[0, right] for left in values for right in values)
    depends_right = any(table[left, right] != table[left, 0] for left in values for right in values)
    cross = table[1, 1] - table[1, 0] - table[0, 1] + table[0, 0] != 0
    commutative = all(table[left, right] == table[right, left] for left in values for right in values)
    identity = next(
        (
            item
            for item in values
            if all(operation(item, value) == value and operation(value, item) == value for value in values)
        ),
        None,
    )
    annihilator = next(
        (
            item
            for item in values
            if all(operation(item, value) == item and operation(value, item) == item for value in values)
        ),
        None,
    )
    associative = all(
        operation(operation(a, b), c) == operation(a, operation(b, c))
        for a in values
        for b in values
        for c in values
    )
    left_distributive = all(
        operation(a, b + c) == operation(a, b) + operation(a, c)
        for a in values
        for b in values
        for c in values
    )
    right_distributive = all(
        operation(a + b, c) == operation(a, c) + operation(b, c)
        for a in values
        for b in values
        for c in values
    )
    monotone = all(
        operation(a, b) <= operation(a + 1, b)
        and operation(a, b) <= operation(a, b + 1)
        for a in values
        for b in values
    )
    return AlgebraicProfile(
        depends_left and depends_right,
        cross,
        commutative,
        associative,
        identity,
        annihilator,
        left_distributive,
        right_distributive,
        monotone,
    )
