"""Target-free event-controller exploration over natural counters."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any


class PartitionExecutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class EventCounterProgram:
    stream_input: int
    state_a: int
    state_b: int
    work: int
    scratch: int
    preserve_template: bool
    consume_work: bool
    increment_state_b: bool
    boundary_increment_state_a: bool
    boundary_clear_state_b: bool
    boundary_refill_work: bool

    @property
    def template_input(self) -> int:
        return 1 - self.stream_input

    @property
    def primitive_node_count(self) -> int:
        return 5 + sum(
            (
                self.preserve_template,
                self.consume_work,
                self.increment_state_b,
                self.boundary_increment_state_a,
                self.boundary_clear_state_b,
                self.boundary_refill_work,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "anonymous_event_counter_v11",
            "initial_registers": ["input_0", "input_1", 0, 0, 0, 0],
            "roles": {
                "stream_input": self.stream_input,
                "template_input": self.template_input,
                "state_a": self.state_a,
                "state_b": self.state_b,
                "work": self.work,
                "scratch": self.scratch,
            },
            "policy_bits": {
                "preserve_template": self.preserve_template,
                "consume_work": self.consume_work,
                "increment_state_b": self.increment_state_b,
                "boundary_increment_state_a": self.boundary_increment_state_a,
                "boundary_clear_state_b": self.boundary_clear_state_b,
                "boundary_refill_work": self.boundary_refill_work,
            },
            "outputs": [self.state_a, self.state_b],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EventCounterProgram":
        if value.get("substrate") != "anonymous_event_counter_v11":
            raise ValueError("event counter substrate is unavailable")
        roles = value["roles"]
        policy = value["policy_bits"]
        return cls(
            int(roles["stream_input"]),
            int(roles["state_a"]),
            int(roles["state_b"]),
            int(roles["work"]),
            int(roles["scratch"]),
            *(bool(policy[key]) for key in (
                "preserve_template",
                "consume_work",
                "increment_state_b",
                "boundary_increment_state_a",
                "boundary_clear_state_b",
                "boundary_refill_work",
            )),
        )


@dataclass(frozen=True, slots=True)
class EventExecution:
    outputs: tuple[int, int]
    final_registers: tuple[int, ...]
    primitive_steps: int


class EventCounterExecutor:
    def __init__(self, maximum_steps: int = 1_000_000) -> None:
        self.maximum_steps = maximum_steps

    def execute(self, program: EventCounterProgram, inputs: tuple[int, int]) -> EventExecution:
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in inputs):
            raise PartitionExecutionError("inputs must be natural counters")
        if inputs[program.template_input] == 0:
            raise PartitionExecutionError("template counter must be positive")
        registers = [inputs[0], inputs[1], 0, 0, 0, 0]
        steps = 0
        steps = self._copy_template(program, registers, steps, initial=True)
        while registers[program.stream_input] > 0:
            registers[program.stream_input] -= 1
            steps += 1
            if program.consume_work:
                if registers[program.work] == 0:
                    raise PartitionExecutionError("policy consumed an empty work counter")
                registers[program.work] -= 1
                steps += 1
            if program.increment_state_b:
                registers[program.state_b] += 1
                steps += 1
            if registers[program.work] == 0:
                if program.boundary_increment_state_a:
                    registers[program.state_a] += 1
                    steps += 1
                if program.boundary_clear_state_b:
                    steps += registers[program.state_b]
                    registers[program.state_b] = 0
                if program.boundary_refill_work:
                    steps = self._copy_template(program, registers, steps, initial=False)
            if steps > self.maximum_steps:
                raise PartitionExecutionError("event program exceeded its step budget")
        return EventExecution(
            (registers[program.state_a], registers[program.state_b]),
            tuple(registers),
            steps,
        )

    def _copy_template(
        self,
        program: EventCounterProgram,
        registers: list[int],
        steps: int,
        *,
        initial: bool,
    ) -> int:
        source = program.template_input
        while registers[source] > 0:
            registers[source] -= 1
            registers[program.work] += 1
            steps += 2
            if program.preserve_template:
                registers[program.scratch] += 1
                steps += 1
        if program.preserve_template:
            while registers[program.scratch] > 0:
                registers[program.scratch] -= 1
                registers[source] += 1
                steps += 2
        if not initial and registers[program.work] == 0:
            raise PartitionExecutionError("boundary refill produced an empty work counter")
        return steps


@dataclass(frozen=True, slots=True)
class ConservationProfile:
    reconstructs_stream: bool
    residual_bounded: bool
    exact_boundary_consistent: bool
    state_a_monotone: bool
    deterministic: bool

    @property
    def promotable(self) -> bool:
        return all((
            self.reconstructs_stream,
            self.residual_bounded,
            self.exact_boundary_consistent,
            self.state_a_monotone,
            self.deterministic,
        ))

    @property
    def law_count(self) -> int:
        return sum((
            self.reconstructs_stream,
            self.residual_bounded,
            self.exact_boundary_consistent,
            self.state_a_monotone,
            self.deterministic,
        ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "reconstructs_stream_with_prior_binary_semantic": self.reconstructs_stream,
            "residual_is_strictly_bounded": self.residual_bounded,
            "zero_residual_matches_exact_boundary": self.exact_boundary_consistent,
            "first_state_is_monotone_in_stream": self.state_a_monotone,
            "deterministic_replay": self.deterministic,
            "law_count": self.law_count,
            "promotable": self.promotable,
        }


@dataclass(frozen=True, slots=True)
class PartitionCandidate:
    candidate_id: str
    program: EventCounterProgram
    behavior_signature: tuple[tuple[int, int], ...]
    profile: ConservationProfile
    step_cost: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "program": self.program.to_dict(),
            "behavior_signature": [list(item) for item in self.behavior_signature],
            "conservation_profile": self.profile.to_dict(),
            "primitive_node_count": self.program.primitive_node_count,
            "probe_step_cost": self.step_cost,
        }


@dataclass(frozen=True, slots=True)
class PartitionExplorationReport:
    programs_generated: int
    programs_executed: int
    behavior_classes: int
    promotable_behavior_classes: int
    selected: PartitionCandidate
    rejected_leaders: tuple[PartitionCandidate, ...]


def event_program_id(program: EventCounterProgram) -> str:
    payload = json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))
    return "EV-" + hashlib.sha256(payload.encode()).hexdigest()[:16]


def inspect_conservation_profile(
    executor: EventCounterExecutor,
    program: EventCounterProgram,
    *,
    limit: int = 6,
) -> ConservationProfile:
    def run(stream: int, template: int) -> tuple[int, int]:
        inputs = (stream, template) if program.stream_input == 0 else (template, stream)
        return executor.execute(program, inputs).outputs

    rows = {
        (stream, template): run(stream, template)
        for stream in range(limit + 1)
        for template in range(1, limit + 1)
    }
    reconstructs = all(a * template + b == stream for (stream, template), (a, b) in rows.items())
    bounded = all(0 <= b < template for (_, template), (_, b) in rows.items())
    exact = all((b == 0) == (a * template == stream) for (stream, template), (a, b) in rows.items())
    monotone = all(
        rows[stream, template][0] <= rows[stream + 1, template][0]
        for stream in range(limit)
        for template in range(1, limit + 1)
    )
    deterministic = all(run(stream, template) == value for (stream, template), value in rows.items())
    return ConservationProfile(reconstructs, bounded, exact, monotone, deterministic)


class TargetFreePartitionExplorer:
    def __init__(self, probe_stream_limit: int = 6, probe_template_limit: int = 4) -> None:
        self.probe_stream_limit = probe_stream_limit
        self.probe_template_limit = probe_template_limit
        self.executor = EventCounterExecutor()

    def enumerate_programs(self) -> tuple[EventCounterProgram, ...]:
        programs = []
        for stream in (0, 1):
            for state_a, state_b, work, scratch in itertools.permutations(range(2, 6)):
                for bits in itertools.product((False, True), repeat=6):
                    programs.append(EventCounterProgram(stream, state_a, state_b, work, scratch, *bits))
        return tuple(programs)

    def search(self) -> PartitionExplorationReport:
        programs = self.enumerate_programs()
        by_behavior: dict[tuple[tuple[int, int], ...], tuple[EventCounterProgram, int]] = {}
        executed = 0
        for program in programs:
            behavior = []
            cost = 0
            try:
                for stream in range(self.probe_stream_limit + 1):
                    for template in range(1, self.probe_template_limit + 1):
                        inputs = (stream, template) if program.stream_input == 0 else (template, stream)
                        result = self.executor.execute(program, inputs)
                        behavior.append(result.outputs)
                        cost += result.primitive_steps
            except PartitionExecutionError:
                continue
            executed += 1
            signature = tuple(behavior)
            current = by_behavior.get(signature)
            if current is None or (program.primitive_node_count, cost, event_program_id(program)) < (
                current[0].primitive_node_count,
                current[1],
                event_program_id(current[0]),
            ):
                by_behavior[signature] = (program, cost)

        candidates = []
        for behavior, (program, cost) in by_behavior.items():
            profile = inspect_conservation_profile(self.executor, program)
            candidates.append(PartitionCandidate(event_program_id(program), program, behavior, profile, cost))
        candidates.sort(key=lambda item: (-item.profile.law_count, item.program.primitive_node_count, item.step_cost, item.candidate_id))
        promotable = [item for item in candidates if item.profile.promotable]
        if not promotable:
            raise RuntimeError("no event-controller behavior passed the conservation gate")
        return PartitionExplorationReport(
            len(programs), executed, len(candidates), len(promotable), promotable[0],
            tuple(item for item in candidates if not item.profile.promotable)[:20],
        )
