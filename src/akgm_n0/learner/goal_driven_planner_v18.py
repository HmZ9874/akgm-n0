"""Goal-driven planning over primitive and autonomously installed semantics."""

from __future__ import annotations

import hashlib
import heapq
import itertools
import json
from dataclasses import dataclass
from typing import Any, Sequence

from .cold_start_semantics_v16 import (
    DATA_OPS,
    OperatorDefinitionV16,
    RuntimeInstruction,
    SelfExtendingCounterVM,
    SemanticRuntimeError,
)


class GoalPlanningError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AnonymousGoalProblemV18:
    problem_id: str
    initial_state: tuple[int, ...]
    goal_state: tuple[int, ...]
    maximum_counter: int
    family_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "problem_id": self.problem_id,
            "initial_state": list(self.initial_state),
            "goal_state": list(self.goal_state),
            "maximum_counter": self.maximum_counter,
            "family_id": self.family_id,
        }


@dataclass(frozen=True, slots=True)
class PlanStepV18:
    index: int
    instruction: RuntimeInstruction
    state_before: tuple[int, ...]
    state_after: tuple[int, ...]
    dynamic_operator: bool
    primitive_span: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "instruction": self.instruction.to_dict(),
            "state_before": list(self.state_before),
            "state_after": list(self.state_after),
            "dynamic_operator": self.dynamic_operator,
            "primitive_span": self.primitive_span,
        }


@dataclass(frozen=True, slots=True)
class GoalPlanV18:
    problem_id: str
    solved: bool
    steps: tuple[PlanStepV18, ...]
    explored_states: int
    runtime_token_cost: int
    expanded_primitive_cost: int
    dynamic_operator_uses: int
    final_state: tuple[int, ...] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "problem_id": self.problem_id,
            "solved": self.solved,
            "steps": [item.to_dict() for item in self.steps],
            "explored_states": self.explored_states,
            "runtime_token_cost": self.runtime_token_cost,
            "expanded_primitive_cost": self.expanded_primitive_cost,
            "dynamic_operator_uses": self.dynamic_operator_uses,
            "final_state": None if self.final_state is None else list(self.final_state),
        }


class GoalDrivenProgramPlannerV18:
    """Uniform-cost search in the bounded state graph exposed by the VM."""

    def __init__(self, *, maximum_explored_states: int = 100_000) -> None:
        self.maximum_explored_states = maximum_explored_states

    def plan(
        self,
        problem: AnonymousGoalProblemV18,
        vm: SelfExtendingCounterVM,
        definitions: Sequence[OperatorDefinitionV16] = (),
    ) -> GoalPlanV18:
        self._validate_problem(problem)
        actions = self._actions(len(problem.initial_state), definitions)
        start = problem.initial_state
        target = problem.goal_state
        if start == target:
            return GoalPlanV18(problem.problem_id, True, (), 1, 0, 0, 0, start)
        frontier: list[tuple[int, int, tuple[int, ...]]] = [(0, 0, start)]
        best = {start: 0}
        predecessor: dict[tuple[int, ...], tuple[tuple[int, ...], RuntimeInstruction, int, bool]] = {}
        serial = 0
        explored = 0
        while frontier:
            cost, _, state = heapq.heappop(frontier)
            if cost != best[state]:
                continue
            explored += 1
            if explored > self.maximum_explored_states:
                break
            if state == target:
                steps = self._reconstruct(start, target, predecessor)
                return GoalPlanV18(
                    problem.problem_id,
                    True,
                    steps,
                    explored,
                    len(steps),
                    sum(item.primitive_span for item in steps),
                    sum(item.dynamic_operator for item in steps),
                    target,
                )
            successor_choices: dict[tuple[int, ...], tuple[RuntimeInstruction, int, bool]] = {}
            for action, primitive_span, dynamic in actions:
                try:
                    successor, _, _ = vm.apply_sequence((action,), state)
                except SemanticRuntimeError:
                    continue
                if any(value < 0 or value > problem.maximum_counter for value in successor):
                    continue
                existing = successor_choices.get(successor)
                preference = (not dynamic, primitive_span, action.op, action.operands)
                if existing is None:
                    successor_choices[successor] = action, primitive_span, dynamic
                else:
                    old_action, old_span, old_dynamic = existing
                    old_preference = (not old_dynamic, old_span, old_action.op, old_action.operands)
                    if preference < old_preference:
                        successor_choices[successor] = action, primitive_span, dynamic
            for successor, (action, primitive_span, dynamic) in successor_choices.items():
                next_cost = cost + 1
                if next_cost >= best.get(successor, 10**18):
                    continue
                best[successor] = next_cost
                predecessor[successor] = state, action, primitive_span, dynamic
                serial += 1
                heapq.heappush(frontier, (next_cost, serial, successor))
        return GoalPlanV18(problem.problem_id, False, (), explored, 0, 0, 0, None)

    @staticmethod
    def _validate_problem(problem: AnonymousGoalProblemV18) -> None:
        if not problem.initial_state or len(problem.initial_state) != len(problem.goal_state):
            raise GoalPlanningError("problem state arity differs")
        if len(problem.initial_state) > 4:
            raise GoalPlanningError("problem state exceeds the planning boundary")
        if problem.maximum_counter < 1:
            raise GoalPlanningError("problem counter boundary is empty")
        if any(value < 0 or value > problem.maximum_counter for value in problem.initial_state + problem.goal_state):
            raise GoalPlanningError("problem state is outside the counter boundary")

    @staticmethod
    def _actions(
        register_count: int,
        definitions: Sequence[OperatorDefinitionV16],
    ) -> tuple[tuple[RuntimeInstruction, int, bool], ...]:
        actions: list[tuple[RuntimeInstruction, int, bool]] = []
        for op in sorted(DATA_OPS):
            for register in range(register_count):
                actions.append((RuntimeInstruction(op, (register,)), 1, False))
        for definition in definitions:
            if definition.arity > register_count:
                continue
            for operands in itertools.permutations(range(register_count), definition.arity):
                actions.append((
                    RuntimeInstruction(definition.operator_id, tuple(operands)),
                    definition.primitive_span,
                    True,
                ))
        return tuple(actions)

    @staticmethod
    def _reconstruct(
        start: tuple[int, ...],
        target: tuple[int, ...],
        predecessor: dict[tuple[int, ...], tuple[tuple[int, ...], RuntimeInstruction, int, bool]],
    ) -> tuple[PlanStepV18, ...]:
        reverse = []
        state = target
        while state != start:
            before, instruction, primitive_span, dynamic = predecessor[state]
            reverse.append((instruction, before, state, primitive_span, dynamic))
            state = before
        reverse.reverse()
        return tuple(
            PlanStepV18(index, instruction, before, after, dynamic, primitive_span)
            for index, (instruction, before, after, primitive_span, dynamic) in enumerate(reverse)
        )


def goal_problem_id(
    initial_state: Sequence[int],
    goal_state: Sequence[int],
    maximum_counter: int,
    family_id: str,
) -> str:
    payload = {
        "initial": list(initial_state),
        "goal": list(goal_state),
        "maximum": maximum_counter,
        "family": family_id,
    }
    return "GOAL-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]

