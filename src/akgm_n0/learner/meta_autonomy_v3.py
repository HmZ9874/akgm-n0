"""Unified, non-neural meta-autonomy loop for anonymous integer worlds.

The learner sees tables and structural resource genes only.  It can grow input
channels, guarded paths, counter folds, state width, and product outputs.  No
mathematical target name is part of this module.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class AnonymousWorld:
    world_id: str
    input_rows: tuple[tuple[int, ...], ...]
    output_rows: tuple[tuple[int, ...], ...]

    @classmethod
    def create(
        cls,
        world_id: str,
        input_rows: Sequence[Sequence[int]],
        outputs: Sequence[int | Sequence[int]],
    ) -> "AnonymousWorld":
        rows = tuple(tuple(int(value) for value in row) for row in input_rows)
        normalized_outputs = tuple(
            (int(output),)
            if isinstance(output, int)
            else tuple(int(value) for value in output)
            for output in outputs
        )
        if not world_id or not rows or len(rows) != len(normalized_outputs):
            raise ValueError("anonymous world rows are invalid")
        width = len(rows[0])
        output_width = len(normalized_outputs[0])
        if width == 0 or output_width == 0:
            raise ValueError("anonymous worlds require nonempty rows")
        if any(len(row) != width for row in rows):
            raise ValueError("input width must be stable")
        if any(len(row) != output_width for row in normalized_outputs):
            raise ValueError("output width must be stable")
        return cls(world_id, rows, normalized_outputs)

    @property
    def input_width(self) -> int:
        return len(self.input_rows[0])

    @property
    def output_width(self) -> int:
        return len(self.output_rows[0])


@dataclass(frozen=True, slots=True)
class AffineExpression:
    coefficients: tuple[int, ...]
    bias: int

    def evaluate(self, values: Sequence[int]) -> int:
        if len(values) < len(self.coefficients):
            raise ValueError("affine expression input is too narrow")
        return self.bias + sum(
            coefficient * int(values[index])
            for index, coefficient in enumerate(self.coefficients)
        )

    def to_dict(self) -> dict[str, Any]:
        return {"coefficients": list(self.coefficients), "bias": self.bias}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AffineExpression":
        return cls(tuple(map(int, value["coefficients"])), int(value["bias"]))


@dataclass(frozen=True, slots=True)
class EvolvedProgram:
    program_id: str
    kind: str
    input_width: int
    output_arity: int
    affine_outputs: tuple[AffineExpression, ...] = ()
    guard_input: int = -1
    guard_mode: int = -1
    triggered_outputs: tuple[AffineExpression, ...] = ()
    counter_input: int = -1
    initial_registers: tuple[AffineExpression, ...] = ()
    update_matrix: tuple[tuple[int, ...], ...] = ()
    update_bias: tuple[int, ...] = ()
    output_registers: tuple[int, ...] = ()
    counter_coefficients: tuple[int, ...] = ()
    counter_state_matrix: tuple[tuple[int, ...], ...] = ()
    state_input_coefficients: tuple[tuple[int, ...], ...] = ()

    def execute(self, row: Sequence[int], *, trace: bool = False) -> tuple[int, ...] | tuple[tuple[int, ...], ...]:
        inputs = tuple(int(value) for value in row)
        if len(inputs) < self.input_width:
            raise ValueError("program input is too narrow")
        if self.kind in ("affine", "product_output"):
            result = tuple(expression.evaluate(inputs) for expression in self.affine_outputs)
            return (result,) if trace else result
        if self.kind == "guarded":
            probe = inputs[self.guard_input]
            triggered = probe < 0 if self.guard_mode == 0 else probe == 0
            expressions = self.triggered_outputs if triggered else self.affine_outputs
            result = tuple(expression.evaluate(inputs) for expression in expressions)
            return (result,) if trace else result
        if self.kind != "counter_fold":
            raise ValueError("unknown evolved program kind")
        counter = inputs[self.counter_input]
        if counter < 0:
            raise ValueError("counter fold requires a natural controller")
        registers = [expression.evaluate(inputs) for expression in self.initial_registers]
        states = [tuple(inputs) + (counter,) + tuple(registers)]
        while counter > 0:
            source = tuple(registers) + inputs
            next_registers = []
            for register_index, (row_coefficients, bias) in enumerate(
                zip(self.update_matrix, self.update_bias, strict=True)
            ):
                counter_coefficient = (
                    self.counter_coefficients[register_index]
                    if register_index < len(self.counter_coefficients) else 0
                )
                interaction_row = (
                    self.counter_state_matrix[register_index]
                    if register_index < len(self.counter_state_matrix)
                    else (0,) * len(registers)
                )
                value = bias + sum(
                    coefficient * source[index]
                    for index, coefficient in enumerate(row_coefficients)
                )
                value += counter_coefficient * counter
                value += sum(
                    coefficient * registers[index] * counter
                    for index, coefficient in enumerate(interaction_row)
                )
                input_interactions = (
                    self.state_input_coefficients[register_index]
                    if register_index < len(self.state_input_coefficients)
                    else (0,) * self.input_width
                )
                value += sum(
                    coefficient * registers[register_index] * inputs[index]
                    for index, coefficient in enumerate(input_interactions)
                )
                next_registers.append(value)
            registers = next_registers
            counter -= 1
            states.append(tuple(inputs) + (counter,) + tuple(registers))
        result = tuple(registers[index] for index in self.output_registers)
        return tuple(states) if trace else result

    @property
    def state_width(self) -> int:
        return len(self.initial_registers)

    @property
    def complexity(self) -> int:
        nonzero = sum(
            coefficient != 0
            for expression in self.affine_outputs + self.triggered_outputs + self.initial_registers
            for coefficient in expression.coefficients
        )
        nonzero += sum(coefficient != 0 for row in self.update_matrix for coefficient in row)
        nonzero += sum(coefficient != 0 for coefficient in self.counter_coefficients)
        nonzero += sum(coefficient != 0 for row in self.counter_state_matrix for coefficient in row)
        nonzero += sum(coefficient != 0 for row in self.state_input_coefficients for coefficient in row)
        return 2 + nonzero + self.output_arity + self.state_width + int(self.kind == "guarded") + int(self.kind == "counter_fold")

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "kind": self.kind,
            "input_width": self.input_width,
            "output_arity": self.output_arity,
            "affine_outputs": [item.to_dict() for item in self.affine_outputs],
            "guard_input": self.guard_input,
            "guard_mode": self.guard_mode,
            "triggered_outputs": [item.to_dict() for item in self.triggered_outputs],
            "counter_input": self.counter_input,
            "initial_registers": [item.to_dict() for item in self.initial_registers],
            "update_matrix": [list(row) for row in self.update_matrix],
            "update_bias": list(self.update_bias),
            "output_registers": list(self.output_registers),
            "counter_coefficients": list(self.counter_coefficients),
            "counter_state_matrix": [list(row) for row in self.counter_state_matrix],
            "state_input_coefficients": [list(row) for row in self.state_input_coefficients],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvolvedProgram":
        return cls(
            str(value["program_id"]), str(value["kind"]), int(value["input_width"]),
            int(value["output_arity"]),
            tuple(AffineExpression.from_dict(item) for item in value["affine_outputs"]),
            int(value["guard_input"]), int(value["guard_mode"]),
            tuple(AffineExpression.from_dict(item) for item in value["triggered_outputs"]),
            int(value["counter_input"]),
            tuple(AffineExpression.from_dict(item) for item in value["initial_registers"]),
            tuple(tuple(map(int, row)) for row in value["update_matrix"]),
            tuple(map(int, value["update_bias"])), tuple(map(int, value["output_registers"])),
            tuple(map(int, value.get("counter_coefficients", ()))),
            tuple(tuple(map(int, row)) for row in value.get("counter_state_matrix", ())),
            tuple(tuple(map(int, row)) for row in value.get("state_input_coefficients", ())),
        )


@dataclass(frozen=True, slots=True)
class GrammarGenome:
    input_channels: int = 1
    state_cells: int = 1
    loop_depth: int = 0
    branch_slots: int = 0
    output_arity: int = 1
    coefficient_radius: int = 1
    counter_interactions: int = 0
    input_interactions: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "input_channels": self.input_channels,
            "state_cells": self.state_cells,
            "loop_depth": self.loop_depth,
            "branch_slots": self.branch_slots,
            "output_arity": self.output_arity,
            "coefficient_radius": self.coefficient_radius,
            "counter_interactions": self.counter_interactions,
            "input_interactions": self.input_interactions,
        }

    @property
    def cost(self) -> int:
        return (
            self.input_channels + self.state_cells + 2 * self.loop_depth
            + 2 * self.branch_slots + self.output_arity + self.coefficient_radius
            + 3 * self.counter_interactions
            + 3 * self.input_interactions
        )

    def mutations(self, world: AnonymousWorld) -> tuple[tuple[str, "GrammarGenome"], ...]:
        candidates = []
        if self.input_channels < world.input_width:
            candidates.append(("grow_input_channel", replace(self, input_channels=self.input_channels + 1)))
        if self.state_cells < 2:
            candidates.append(("grow_state_cell", replace(self, state_cells=self.state_cells + 1)))
        if self.loop_depth < 1:
            candidates.append(("grow_counter_fold", replace(self, loop_depth=self.loop_depth + 1)))
        if self.branch_slots < 1:
            candidates.append(("grow_guarded_path", replace(self, branch_slots=self.branch_slots + 1)))
        if self.output_arity < world.output_width:
            candidates.append(("grow_product_output", replace(self, output_arity=self.output_arity + 1)))
        if self.loop_depth and self.coefficient_radius < 3:
            candidates.append((
                "expand_coefficient_palette",
                replace(self, coefficient_radius=self.coefficient_radius + 1),
            ))
        if self.loop_depth and self.counter_interactions < 1:
            candidates.append((
                "grow_counter_interaction",
                replace(self, counter_interactions=self.counter_interactions + 1),
            ))
        if self.loop_depth and self.input_interactions < 1 and world.input_width >= 2:
            candidates.append((
                "grow_input_interaction",
                replace(self, input_interactions=self.input_interactions + 1),
            ))
        return tuple(candidates)


def _active_inputs(program: EvolvedProgram) -> tuple[int, ...]:
    active: set[int] = set()
    expressions = program.affine_outputs + program.triggered_outputs + program.initial_registers
    for expression in expressions:
        active.update(index for index, coefficient in enumerate(expression.coefficients) if coefficient)
    if program.kind == "guarded":
        active.add(program.guard_input)
    if program.kind == "counter_fold":
        active.add(program.counter_input)
        width = program.state_width
        for row in program.update_matrix:
            active.update(index - width for index, coefficient in enumerate(row[width:], width) if coefficient)
    return tuple(sorted(active))


def structural_atoms(program: EvolvedProgram) -> frozenset[str]:
    atoms = {
            "kind:" + program.kind,
            "active_inputs:" + ",".join(map(str, _active_inputs(program))),
            f"state_width:{program.state_width}",
            f"output_arity:{program.output_arity}",
            f"has_guard:{int(program.kind == 'guarded')}",
            f"has_loop:{int(program.kind == 'counter_fold')}",
        }
    if any(program.counter_coefficients) or any(any(row) for row in program.counter_state_matrix):
        atoms.add("has_counter_interaction:1")
    if any(any(row) for row in program.state_input_coefficients):
        atoms.add("has_input_interaction:1")
    return frozenset(atoms)


@dataclass(frozen=True, slots=True)
class FailureClause:
    clause_id: str
    context_key: str
    required_atoms: frozenset[str]
    support: int
    counterexample_count: int

    def matches(self, program: EvolvedProgram) -> bool:
        return self.required_atoms <= structural_atoms(program)

    def to_dict(self) -> dict[str, Any]:
        return {
            "clause_id": self.clause_id,
            "context_key": self.context_key,
            "required_atoms": sorted(self.required_atoms),
            "support": self.support,
            "counterexample_count": self.counterexample_count,
        }


class GeneralizedMistakeMemory:
    """Anti-unify repeated failures into structural clauses, not exact IDs."""

    def __init__(self, *, minimum_support: int = 2) -> None:
        self.minimum_support = minimum_support
        self._families: dict[
            str, list[tuple[str, frozenset[str], Mapping[str, Any]]]
        ] = {}

    def observe(self, context_key: str, program: EvolvedProgram, counterexample: Mapping[str, Any]) -> FailureClause:
        if not context_key:
            raise ValueError("failure context cannot be empty")
        observations = self._families.setdefault(context_key, [])
        atoms = structural_atoms(program)
        if not any(item[0] == program.program_id for item in observations):
            observations.append((program.program_id, atoms, dict(counterexample)))
        common = set(observations[0][1])
        for _, observed_atoms, _ in observations[1:]:
            common &= set(observed_atoms)
        # Kind, control shape, arity, and active-input pattern are safe structural
        # generalizers.  Numeric constants and exact coefficients never enter atoms.
        required = frozenset(common)
        payload = {"context": context_key, "atoms": sorted(required)}
        clause_id = "FCL-" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16]
        return FailureClause(clause_id, context_key, required, len(observations), len(observations))

    def clause(self, context_key: str) -> FailureClause | None:
        observations = self._families.get(context_key, [])
        if len(observations) < self.minimum_support:
            return None
        common = set(observations[0][1])
        for _, atoms, _ in observations[1:]:
            common &= set(atoms)
        required = frozenset(common)
        payload = {"context": context_key, "atoms": sorted(required)}
        return FailureClause(
            "FCL-" + hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16],
            context_key, required, len(observations), len(observations),
        )

    def rejects(self, context_key: str, program: EvolvedProgram) -> bool:
        clause = self.clause(context_key)
        return bool(clause and clause.matches(program))


@dataclass(frozen=True, slots=True)
class SynthesisCandidate:
    program: EvolvedProgram
    passed_rows: int
    row_count: int

    @property
    def exact(self) -> bool:
        return self.passed_rows == self.row_count


@dataclass(frozen=True, slots=True)
class SynthesisReport:
    genome: GrammarGenome
    candidates_generated: int
    candidates_executed: int
    candidates_skipped_by_mistakes: int
    selected: SynthesisCandidate
    truncated: bool = False


def _program_id(payload: Mapping[str, Any]) -> str:
    return "M3P-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]


def _make_program(**kwargs: Any) -> EvolvedProgram:
    payload = {
        key: (
            [item.to_dict() for item in value]
            if value and isinstance(value, tuple) and isinstance(value[0], AffineExpression)
            else [list(item) for item in value]
            if value and isinstance(value, tuple) and isinstance(value[0], tuple)
            else list(value) if isinstance(value, tuple) else value
        )
        for key, value in kwargs.items()
    }
    return EvolvedProgram(program_id=_program_id(payload), **kwargs)


def compile_affine_program(
    coefficients: Sequence[int], bias: int = 0
) -> EvolvedProgram:
    """Compile an affine genome phenotype without attaching a math label."""

    expression = AffineExpression(tuple(map(int, coefficients)), int(bias))
    return _make_program(
        kind="affine",
        input_width=len(expression.coefficients),
        output_arity=1,
        affine_outputs=(expression,),
    )


def compile_fold_program(
    *,
    input_width: int,
    counter_input: int,
    initial_registers: Sequence[AffineExpression],
    update_matrix: Sequence[Sequence[int]],
    update_bias: Sequence[int],
    output_registers: Sequence[int] = (0,),
    counter_coefficients: Sequence[int] = (),
    counter_state_matrix: Sequence[Sequence[int]] = (),
    state_input_coefficients: Sequence[Sequence[int]] = (),
) -> EvolvedProgram:
    """Compile a generic counter-controlled state transition program."""

    registers = tuple(initial_registers)
    matrix = tuple(tuple(map(int, row)) for row in update_matrix)
    biases = tuple(map(int, update_bias))
    if input_width < 1 or not 0 <= counter_input < input_width:
        raise ValueError("counter input is outside the program input")
    if not registers or len(matrix) != len(registers) or len(biases) != len(registers):
        raise ValueError("fold register dimensions do not agree")
    expected_row_width = len(registers) + input_width
    if any(len(row) != expected_row_width for row in matrix):
        raise ValueError("fold transition rows have the wrong width")
    outputs = tuple(map(int, output_registers))
    if not outputs or any(index < 0 or index >= len(registers) for index in outputs):
        raise ValueError("fold output register is invalid")
    counter_terms = tuple(map(int, counter_coefficients))
    interaction = tuple(tuple(map(int, row)) for row in counter_state_matrix)
    input_interaction = tuple(tuple(map(int, row)) for row in state_input_coefficients)
    if counter_terms and len(counter_terms) != len(registers):
        raise ValueError("counter coefficients have the wrong width")
    if interaction and (
        len(interaction) != len(registers)
        or any(len(row) != len(registers) for row in interaction)
    ):
        raise ValueError("counter-state interaction matrix has the wrong shape")
    if input_interaction and (
        len(input_interaction) != len(registers)
        or any(len(row) != input_width for row in input_interaction)
    ):
        raise ValueError("state-input interaction matrix has the wrong shape")
    return _make_program(
        kind="counter_fold",
        input_width=input_width,
        output_arity=len(outputs),
        counter_input=counter_input,
        initial_registers=registers,
        update_matrix=matrix,
        update_bias=biases,
        output_registers=outputs,
        counter_coefficients=counter_terms,
        counter_state_matrix=interaction,
        state_input_coefficients=input_interaction,
    )


class GenericProgramSynthesizer:
    """Compile and search every program admitted by a structural genome."""

    def __init__(
        self, *, coefficient_values: Sequence[int] = (-1, 0, 1),
        affine_values: Sequence[int] = (-2, -1, 0, 1, 2),
        maximum_candidates: int = 100_000,
    ) -> None:
        self.coefficient_values = tuple(coefficient_values)
        self.affine_values = tuple(affine_values)
        self.maximum_candidates = maximum_candidates

    def search(
        self,
        world: AnonymousWorld,
        genome: GrammarGenome,
        *,
        mistake_memory: GeneralizedMistakeMemory | None = None,
        context_key: str | None = None,
    ) -> SynthesisReport:
        programs = self._programs(world, genome)
        best: SynthesisCandidate | None = None
        generated = executed = skipped = 0
        truncated = False
        for program in programs:
            if generated >= self.maximum_candidates:
                truncated = True
                break
            generated += 1
            if mistake_memory and context_key and mistake_memory.rejects(context_key, program):
                skipped += 1
                continue
            passed = 0
            for row, expected in zip(world.input_rows, world.output_rows, strict=True):
                try:
                    passed += program.execute(row) == expected
                except (ValueError, OverflowError):
                    pass
            executed += 1
            candidate = SynthesisCandidate(program, passed, len(world.input_rows))
            if best is None or self._candidate_key(candidate) < self._candidate_key(best):
                best = candidate
            if candidate.exact:
                break
        if best is None:
            fallback = _make_program(
                kind="affine", input_width=min(genome.input_channels, world.input_width),
                output_arity=1, affine_outputs=(AffineExpression((0,) * min(genome.input_channels, world.input_width), 0),),
            )
            best = SynthesisCandidate(fallback, 0, len(world.input_rows))
        return SynthesisReport(genome, generated, executed, skipped, best, truncated)

    @staticmethod
    def _candidate_key(candidate: SynthesisCandidate) -> tuple[int, int, str]:
        return (-candidate.passed_rows, candidate.program.complexity, candidate.program.program_id)

    def _programs(self, world: AnonymousWorld, genome: GrammarGenome) -> Iterable[EvolvedProgram]:
        visible = min(genome.input_channels, world.input_width)
        output_arity = min(genome.output_arity, world.output_width)
        affine_choices = tuple(self._affine_expressions(visible))
        best_per_output = [
            self._rank_expressions(affine_choices, world, output_index, visible)
            for output_index in range(output_arity)
        ]
        # Cross only the best few per component; each component was independently
        # evaluated on every row, so an exact product output remains reachable.
        for expressions in itertools.product(*(choices[:4] for choices in best_per_output)):
            kind = "product_output" if output_arity > 1 else "affine"
            yield _make_program(
                kind=kind, input_width=visible, output_arity=output_arity,
                affine_outputs=tuple(expressions),
            )
        if genome.branch_slots:
            for guard_input in range(visible):
                for guard_mode in (0, 1):
                    triggered_indices = tuple(
                        index for index, row in enumerate(world.input_rows)
                        if (row[guard_input] < 0 if guard_mode == 0 else row[guard_input] == 0)
                    )
                    other_indices = tuple(index for index in range(len(world.input_rows)) if index not in triggered_indices)
                    if not triggered_indices or not other_indices:
                        continue
                    normal = self._rank_expressions(affine_choices, world, 0, visible, other_indices)[:3]
                    triggered = self._rank_expressions(affine_choices, world, 0, visible, triggered_indices)[:3]
                    for left, right in itertools.product(normal, triggered):
                        yield _make_program(
                            kind="guarded", input_width=visible, output_arity=1,
                            affine_outputs=(left,), guard_input=guard_input, guard_mode=guard_mode,
                            triggered_outputs=(right,),
                        )
        if genome.loop_depth:
            yield from self._fold_programs(
                world, visible, 1, output_arity, genome.coefficient_radius,
            )
            if genome.counter_interactions:
                yield from self._interaction_fold_programs(
                    world, visible, genome.state_cells, output_arity,
                    genome.coefficient_radius,
                )
            if genome.input_interactions:
                yield from self._input_interaction_fold_programs(
                    world, visible, genome.state_cells, output_arity,
                    genome.coefficient_radius,
                )
            if genome.state_cells >= 2:
                yield from self._fold_programs(
                    world, visible, 2, output_arity, genome.coefficient_radius,
                )

    def _affine_expressions(self, width: int) -> Iterable[AffineExpression]:
        for coefficients in itertools.product(self.affine_values, repeat=width):
            for bias in self.affine_values:
                yield AffineExpression(tuple(coefficients), bias)

    @staticmethod
    def _rank_expressions(
        expressions: Sequence[AffineExpression], world: AnonymousWorld, output_index: int,
        visible: int, indices: Sequence[int] | None = None,
    ) -> tuple[AffineExpression, ...]:
        chosen = tuple(range(len(world.input_rows))) if indices is None else tuple(indices)
        return tuple(sorted(
            expressions,
            key=lambda expression: (
                sum(expression.evaluate(world.input_rows[index][:visible]) != world.output_rows[index][output_index] for index in chosen),
                sum(coefficient != 0 for coefficient in expression.coefficients) + int(expression.bias != 0),
                expression.coefficients, expression.bias,
            ),
        ))

    def _fold_programs(
        self, world: AnonymousWorld, visible: int, state_width: int,
        output_arity: int, coefficient_radius: int,
    ) -> Iterable[EvolvedProgram]:
        width = max(1, min(2, state_width))
        if output_arity > width:
            return
        effective_radius = coefficient_radius if width == 1 else 1
        initial_options = (
            AffineExpression((0,) * visible, 0),
            AffineExpression((0,) * visible, 1),
        ) + tuple(
            AffineExpression(tuple(int(index == source) for index in range(visible)), 0)
            for source in range(visible)
        )
        row_options = tuple(
            tuple(coefficients)
            for coefficients in itertools.product(
                range(-effective_radius, effective_radius + 1),
                repeat=width + visible + 1,
            )
        )
        for counter_input in range(visible):
            for initial in itertools.product(initial_options, repeat=width):
                for rows in itertools.product(row_options, repeat=width):
                    matrix = tuple(tuple(row[:-1]) for row in rows)
                    bias = tuple(row[-1] for row in rows)
                    output_registers = tuple(range(output_arity))
                    yield _make_program(
                        kind="counter_fold", input_width=visible, output_arity=output_arity,
                        counter_input=counter_input, initial_registers=tuple(initial),
                        update_matrix=matrix, update_bias=bias,
                        output_registers=output_registers,
                    )

    def _interaction_fold_programs(
        self, world: AnonymousWorld, visible: int, state_width: int,
        output_arity: int, coefficient_radius: int,
    ) -> Iterable[EvolvedProgram]:
        # Start with one state cell: it is the smallest arena in which a
        # state/counter interaction can be identified without a combinatorial
        # explosion. More cells can later be introduced as learned macros.
        if state_width < 1 or output_arity > 1:
            return
        initial_options = (
            AffineExpression((0,) * visible, 0),
            AffineExpression((0,) * visible, 1),
        ) + tuple(
            AffineExpression(tuple(int(index == source) for index in range(visible)), 0)
            for source in range(visible)
        )
        values = range(-coefficient_radius, coefficient_radius + 1)
        # [state linear | original inputs | bias | counter | state*counter]
        for counter_input in range(visible):
            for initial in initial_options:
                for coefficients in itertools.product(values, repeat=visible + 4):
                    state_linear = coefficients[0]
                    input_linear = coefficients[1:1 + visible]
                    bias = coefficients[1 + visible]
                    counter_linear = coefficients[2 + visible]
                    interaction = coefficients[3 + visible]
                    if interaction == 0:
                        continue
                    yield _make_program(
                        kind="counter_fold", input_width=visible, output_arity=1,
                        counter_input=counter_input, initial_registers=(initial,),
                        update_matrix=((state_linear,) + tuple(input_linear),),
                        update_bias=(bias,), output_registers=(0,),
                        counter_coefficients=(counter_linear,),
                        counter_state_matrix=((interaction,),),
                    )

    def _input_interaction_fold_programs(
        self, world: AnonymousWorld, visible: int, state_width: int,
        output_arity: int, coefficient_radius: int,
    ) -> Iterable[EvolvedProgram]:
        if state_width < 1 or output_arity > 1 or visible < 2:
            return
        initial_options = (
            AffineExpression((0,) * visible, 0),
            AffineExpression((0,) * visible, 1),
        ) + tuple(
            AffineExpression(tuple(int(index == source) for index in range(visible)), 0)
            for source in range(visible)
        )
        values = range(-coefficient_radius, coefficient_radius + 1)
        # One active state*input term is an invented interaction slot.  The
        # surrounding affine transition remains generic and searchable.
        for counter_input in range(visible):
            for interaction_input in range(visible):
                if interaction_input == counter_input:
                    continue
                for interaction in values:
                    if interaction == 0:
                        continue
                    for initial in initial_options:
                        for coefficients in itertools.product(values, repeat=visible + 2):
                            state_linear = coefficients[0]
                            input_linear = coefficients[1:1 + visible]
                            bias = coefficients[-1]
                            interaction_row = [0] * visible
                            interaction_row[interaction_input] = interaction
                            yield _make_program(
                                kind="counter_fold", input_width=visible, output_arity=1,
                                counter_input=counter_input, initial_registers=(initial,),
                                update_matrix=((state_linear,) + tuple(input_linear),),
                                update_bias=(bias,), output_registers=(0,),
                                state_input_coefficients=(tuple(interaction_row),),
                            )


@dataclass(frozen=True, slots=True)
class GrammarGrowthRound:
    round_index: int
    mutation: str | None
    genome: GrammarGenome
    passed_rows: int
    row_count: int
    candidates_executed: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_index": self.round_index, "mutation": self.mutation,
            "genome": self.genome.to_dict(), "passed_rows": self.passed_rows,
            "row_count": self.row_count, "candidates_executed": self.candidates_executed,
        }


@dataclass(frozen=True, slots=True)
class AdaptiveSolveReport:
    world_id: str
    converged: bool
    initial_genome: GrammarGenome
    final_genome: GrammarGenome
    rounds: tuple[GrammarGrowthRound, ...]
    final_candidate: SynthesisCandidate


class AdaptiveGrammarSynthesizer:
    """Use empirical fit to choose generic grammar mutations without target labels."""

    def __init__(self, synthesizer: GenericProgramSynthesizer | None = None, *, maximum_rounds: int = 6) -> None:
        self.synthesizer = synthesizer or GenericProgramSynthesizer()
        self.maximum_rounds = maximum_rounds

    def solve(
        self,
        world: AnonymousWorld,
        genome: GrammarGenome,
        *,
        mistake_memory: GeneralizedMistakeMemory | None = None,
    ) -> AdaptiveSolveReport:
        initial = genome
        current = self.synthesizer.search(world, genome, mistake_memory=mistake_memory, context_key=self._context(world))
        rounds = [GrammarGrowthRound(0, None, genome, current.selected.passed_rows, current.selected.row_count, current.candidates_executed)]
        for round_index in range(1, self.maximum_rounds + 1):
            if current.selected.exact:
                return AdaptiveSolveReport(world.world_id, True, initial, genome, tuple(rounds), current.selected)
            trials = []
            for mutation, mutated in genome.mutations(world):
                report = self.synthesizer.search(world, mutated, mistake_memory=mistake_memory, context_key=self._context(world))
                trials.append((mutation, mutated, report))
            if not trials:
                break
            mutation, genome, current = min(
                trials,
                key=lambda item: (
                    -item[2].selected.passed_rows,
                    int(not item[2].selected.exact),
                    item[1].cost,
                    item[2].selected.program.complexity,
                    item[0],
                ),
            )
            rounds.append(GrammarGrowthRound(
                round_index, mutation, genome, current.selected.passed_rows,
                current.selected.row_count, current.candidates_executed,
            ))
        return AdaptiveSolveReport(world.world_id, current.selected.exact, initial, genome, tuple(rounds), current.selected)

    @staticmethod
    def _context(world: AnonymousWorld) -> str:
        return f"shape:{world.input_width}>{world.output_width}"


@dataclass(frozen=True, slots=True)
class FrontierSelection:
    selection_index: int
    selected_world_id: str
    learner_score: int
    solved: bool
    grammar_before: GrammarGenome
    grammar_after: GrammarGenome
    mutations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CurriculumReport:
    selections: tuple[FrontierSelection, ...]
    solved_world_ids: tuple[str, ...]
    final_genome: GrammarGenome
    programs: Mapping[str, EvolvedProgram]


class AutonomousCurriculum:
    """Generate its own ordering over opaque worlds using novelty and fit deficit."""

    def __init__(self, adaptive: AdaptiveGrammarSynthesizer | None = None) -> None:
        self.adaptive = adaptive or AdaptiveGrammarSynthesizer()

    def run(self, worlds: Sequence[AnonymousWorld], initial_genome: GrammarGenome) -> CurriculumReport:
        remaining = list(worlds)
        genome = initial_genome
        selections = []
        solved_ids = []
        programs: dict[str, EvolvedProgram] = {}
        seen_shapes: set[tuple[int, int]] = set()
        while remaining:
            ranked = []
            for world in remaining:
                preview = self.adaptive.synthesizer.search(world, genome)
                deficit = preview.selected.row_count - preview.selected.passed_rows
                shape = (world.input_width, world.output_width)
                novelty = 5 if shape not in seen_shapes else 0
                mutation_options = len(genome.mutations(world))
                disagreement = len({row for row in world.output_rows})
                score = 13 * deficit + 7 * novelty + 3 * mutation_options + disagreement - genome.cost
                ranked.append((score, world.world_id, world))
            score, _, selected = max(ranked, key=lambda item: (item[0], item[1]))
            before = genome
            result = self.adaptive.solve(selected, genome)
            genome = result.final_genome
            mutations = tuple(round_.mutation for round_ in result.rounds if round_.mutation)
            selections.append(FrontierSelection(
                len(selections), selected.world_id, score, result.converged,
                before, genome, mutations,
            ))
            if result.converged:
                solved_ids.append(selected.world_id)
                programs[selected.world_id] = result.final_candidate.program
            seen_shapes.add((selected.input_width, selected.output_width))
            remaining.remove(selected)
        return CurriculumReport(tuple(selections), tuple(solved_ids), genome, programs)


# ---- Exact polynomial invariant synthesis ---------------------------------

Monomial = tuple[int, ...]
Polynomial = dict[Monomial, Fraction]


def _poly_clean(value: Polynomial) -> Polynomial:
    return {monomial: coefficient for monomial, coefficient in value.items() if coefficient}


def _poly_add(left: Polynomial, right: Polynomial) -> Polynomial:
    result = dict(left)
    for monomial, coefficient in right.items():
        result[monomial] = result.get(monomial, Fraction(0)) + coefficient
    return _poly_clean(result)


def _poly_scale(value: Polynomial, scalar: Fraction) -> Polynomial:
    return _poly_clean({monomial: coefficient * scalar for monomial, coefficient in value.items()})


def _poly_mul(left: Polynomial, right: Polynomial) -> Polynomial:
    if not left or not right:
        return {}
    width = len(next(iter(left)))
    result: Polynomial = {}
    for lm, lc in left.items():
        for rm, rc in right.items():
            monomial = tuple(lm[index] + rm[index] for index in range(width))
            result[monomial] = result.get(monomial, Fraction(0)) + lc * rc
    return _poly_clean(result)


def _constant(width: int, value: int | Fraction) -> Polynomial:
    return {} if value == 0 else {(0,) * width: Fraction(value)}


def _variable(width: int, index: int) -> Polynomial:
    monomial = [0] * width
    monomial[index] = 1
    return {tuple(monomial): Fraction(1)}


def _substitute_monomial(monomial: Monomial, substitutions: Sequence[Polynomial]) -> Polynomial:
    width = len(next(iter(substitutions[0]))) if substitutions[0] else len(monomial)
    result = _constant(width, 1)
    for index, exponent in enumerate(monomial):
        for _ in range(exponent):
            result = _poly_mul(result, substitutions[index])
    return result


def _monomial_basis(width: int, degree: int = 2) -> tuple[Monomial, ...]:
    result = [(0,) * width]
    for index in range(width):
        monomial = [0] * width; monomial[index] = 1; result.append(tuple(monomial))
    if degree >= 2:
        for left in range(width):
            for right in range(left, width):
                monomial = [0] * width; monomial[left] += 1; monomial[right] += 1; result.append(tuple(monomial))
    return tuple(result)


def _nullspace(matrix: Sequence[Sequence[Fraction]], column_count: int) -> tuple[tuple[Fraction, ...], ...]:
    rows = [list(map(Fraction, row)) for row in matrix if any(row)]
    pivot_columns = []
    pivot_row = 0
    for column in range(column_count):
        found = next((index for index in range(pivot_row, len(rows)) if rows[index][column]), None)
        if found is None:
            continue
        rows[pivot_row], rows[found] = rows[found], rows[pivot_row]
        scale = rows[pivot_row][column]
        rows[pivot_row] = [value / scale for value in rows[pivot_row]]
        for index in range(len(rows)):
            if index == pivot_row or not rows[index][column]:
                continue
            factor = rows[index][column]
            rows[index] = [rows[index][item] - factor * rows[pivot_row][item] for item in range(column_count)]
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == len(rows):
            break
    free = [column for column in range(column_count) if column not in pivot_columns]
    basis = []
    for free_column in free:
        vector = [Fraction(0)] * column_count
        vector[free_column] = Fraction(1)
        for row_index, pivot_column in reversed(list(enumerate(pivot_columns))):
            vector[pivot_column] = -sum(rows[row_index][column] * vector[column] for column in free)
        basis.append(tuple(vector))
    return tuple(basis)


@dataclass(frozen=True, slots=True)
class InvariantCertificate:
    certificate_id: str
    program_id: str
    variable_count: int
    degree: int
    coefficients: tuple[int, ...]
    monomials: tuple[Monomial, ...]
    ranking_variable: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id, "program_id": self.program_id,
            "variable_count": self.variable_count, "degree": self.degree,
            "coefficients": list(self.coefficients),
            "monomials": [list(item) for item in self.monomials],
            "ranking_variable": self.ranking_variable,
        }


class PolynomialInvariantKernel:
    """Small fixed kernel: exact initialization, preservation, and ranking checks."""

    def verify(self, program: EvolvedProgram, certificate: InvariantCertificate) -> dict[str, Any]:
        if program.kind != "counter_fold":
            return {"passed": False, "obligations": [{"id": "counter_fold", "passed": False}]}
        basis = certificate.monomials
        coefficients = tuple(Fraction(value) for value in certificate.coefficients)
        transition, initial = _program_substitutions(program)
        polynomial = _poly_clean({monomial: coefficient for monomial, coefficient in zip(basis, coefficients, strict=True) if coefficient})
        preserved: Polynomial = {}
        initialized: Polynomial = {}
        for monomial, coefficient in polynomial.items():
            preserved = _poly_add(preserved, _poly_scale(_substitute_monomial(monomial, transition), coefficient))
            preserved = _poly_add(preserved, _poly_scale({monomial: Fraction(1)}, -coefficient))
            initialized = _poly_add(initialized, _poly_scale(_substitute_monomial(monomial, initial), coefficient))
        counter_index = program.input_width
        counter_update = transition[counter_index]
        expected_counter = _poly_add(_variable(len(transition), counter_index), _constant(len(transition), -1))
        obligations = [
            {"id": "program_binding", "passed": certificate.program_id == program.program_id},
            {"id": "nonzero_polynomial", "passed": bool(polynomial)},
            {"id": "initialization_identity", "passed": not initialized},
            {"id": "transition_preservation_identity", "passed": not preserved},
            {"id": "natural_counter_ranking", "passed": certificate.ranking_variable == counter_index and counter_update == expected_counter},
        ]
        return {"passed": all(item["passed"] for item in obligations), "obligations": obligations}


class PolynomialInvariantMiner:
    """Solve exact symbolic constraints for degree<=2 invariants."""

    def __init__(self, *, maximum_degree: int = 2) -> None:
        self.maximum_degree = maximum_degree
        self.kernel = PolynomialInvariantKernel()

    def mine(self, program: EvolvedProgram) -> tuple[InvariantCertificate, ...]:
        if program.kind != "counter_fold":
            return ()
        transition, initial = _program_substitutions(program)
        width = len(transition)
        monomials = _monomial_basis(width, self.maximum_degree)
        transition_columns = []
        initial_columns = []
        for monomial in monomials:
            transition_columns.append(_poly_add(
                _substitute_monomial(monomial, transition),
                _poly_scale({monomial: Fraction(1)}, -1),
            ))
            initial_columns.append(_substitute_monomial(monomial, initial))
        transition_terms = sorted(set().union(*(column.keys() for column in transition_columns)))
        initial_terms = sorted(set().union(*(column.keys() for column in initial_columns)))
        matrix = [
            [column.get(term, Fraction(0)) for column in transition_columns]
            for term in transition_terms
        ] + [
            [column.get(term, Fraction(0)) for column in initial_columns]
            for term in initial_terms
        ]
        certificates = []
        state_start = program.input_width + 1
        for vector in _nullspace(matrix, len(monomials)):
            if not any(vector):
                continue
            if not any(
                coefficient and any(monomial[index] for index in range(state_start, width))
                for coefficient, monomial in zip(vector, monomials, strict=True)
            ):
                continue
            denominator = math.lcm(*(value.denominator for value in vector))
            integers = [int(value * denominator) for value in vector]
            common = math.gcd(*(abs(value) for value in integers if value))
            integers = [value // common for value in integers]
            first = next(value for value in integers if value)
            if first < 0:
                integers = [-value for value in integers]
            payload = {"program": program.program_id, "coefficients": integers, "monomials": monomials}
            certificate = InvariantCertificate(
                "INV-" + hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16],
                program.program_id, width, self.maximum_degree, tuple(integers), monomials,
                program.input_width,
            )
            if self.kernel.verify(program, certificate)["passed"]:
                certificates.append(certificate)
        return tuple(certificates)


def _program_substitutions(program: EvolvedProgram) -> tuple[tuple[Polynomial, ...], tuple[Polynomial, ...]]:
    input_width = program.input_width
    state_width = program.state_width
    total_width = input_width + 1 + state_width
    transition = [_variable(total_width, index) for index in range(input_width)]
    transition.append(_poly_add(_variable(total_width, input_width), _constant(total_width, -1)))
    for row, bias in zip(program.update_matrix, program.update_bias, strict=True):
        polynomial = _constant(total_width, bias)
        for register_index, coefficient in enumerate(row[:state_width]):
            polynomial = _poly_add(polynomial, _poly_scale(_variable(total_width, input_width + 1 + register_index), coefficient))
        for input_index, coefficient in enumerate(row[state_width:]):
            polynomial = _poly_add(polynomial, _poly_scale(_variable(total_width, input_index), coefficient))
        register_index = len(transition) - input_width - 1
        counter_coefficient = (
            program.counter_coefficients[register_index]
            if register_index < len(program.counter_coefficients) else 0
        )
        polynomial = _poly_add(
            polynomial,
            _poly_scale(_variable(total_width, input_width), counter_coefficient),
        )
        interaction_row = (
            program.counter_state_matrix[register_index]
            if register_index < len(program.counter_state_matrix)
            else (0,) * state_width
        )
        for state_index, coefficient in enumerate(interaction_row):
            product = _poly_mul(
                _variable(total_width, input_width),
                _variable(total_width, input_width + 1 + state_index),
            )
            polynomial = _poly_add(polynomial, _poly_scale(product, coefficient))
        input_interaction_row = (
            program.state_input_coefficients[register_index]
            if register_index < len(program.state_input_coefficients)
            else (0,) * input_width
        )
        for input_index, coefficient in enumerate(input_interaction_row):
            product = _poly_mul(
                _variable(total_width, input_width + 1 + register_index),
                _variable(total_width, input_index),
            )
            polynomial = _poly_add(polynomial, _poly_scale(product, coefficient))
        transition.append(polynomial)
    # Initial substitutions live in the same-width ring but contain input variables only.
    initial = [_variable(total_width, index) for index in range(input_width)]
    initial.append(_variable(total_width, program.counter_input))
    for expression in program.initial_registers:
        polynomial = _constant(total_width, expression.bias)
        for input_index, coefficient in enumerate(expression.coefficients):
            polynomial = _poly_add(polynomial, _poly_scale(_variable(total_width, input_index), coefficient))
        initial.append(polynomial)
    return tuple(transition), tuple(initial)
