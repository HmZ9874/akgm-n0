"""V36 active, blind and preregistered scientific-discovery workflow.

The learner sees only anonymous integer inputs and outputs through a query
function.  It never receives the oracle implementation, human variable names,
or a target formula.  The polynomial basis is an explicit bounded inductive
bias and is reported as such by the evaluator.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence


PointV36 = tuple[int, int]
QueryV36 = Callable[[PointV36], int]


@dataclass(frozen=True, slots=True)
class BlindObservationV36:
    experiment_id: str
    inputs: PointV36
    output: int

    def to_dict(self):
        return {
            "experiment_id": self.experiment_id,
            "anonymous_inputs": list(self.inputs),
            "anonymous_output": self.output,
            "human_variable_names": None,
            "human_formula": None,
        }


@dataclass(frozen=True, slots=True)
class SparseProgramV36:
    """Six-coefficient executable program over an anonymous basis."""

    coefficients: tuple[int, int, int, int, int, int]

    def execute(self, point: PointV36) -> int:
        q0, q1 = point
        basis = (1, q0, q1, q0 * q1, q0 * q0, q1 * q1)
        return sum(coefficient * value for coefficient, value in zip(self.coefficients, basis, strict=True))

    @property
    def complexity(self):
        return sum(value != 0 for value in self.coefficients)

    @property
    def token_cost(self):
        return self.complexity + sum(abs(value) for value in self.coefficients)

    @property
    def program_id(self):
        return "SCI-" + hashlib.sha256(json.dumps(self.coefficients).encode()).hexdigest()[:16]

    def render(self):
        basis = ("ONE", "Q0", "Q1", "SEM<Q0,Q1>", "SEM<Q0,Q0>", "SEM<Q1,Q1>")
        atoms = []
        for coefficient, atom in zip(self.coefficients, basis, strict=True):
            if coefficient == 0:
                continue
            routed = atom
            if abs(coefficient) == 2:
                routed = f"DOUBLE<{routed}>"
            if coefficient < 0:
                routed = f"TURN<{routed}>"
            atoms.append(routed)
        if not atoms:
            return "ZERO"
        return atoms[0] if len(atoms) == 1 else "MERGE<" + ",".join(atoms) + ">"

    def to_dict(self):
        return {
            "program_id": self.program_id,
            "opaque_program": self.render(),
            "coefficients": list(self.coefficients),
            "complexity": self.complexity,
            "token_cost": self.token_cost,
            "human_formula_name": None,
        }


@dataclass(frozen=True, slots=True)
class ActiveExperimentV36:
    round_index: int
    point: PointV36
    candidate_count_before: int
    predicted_output_classes: int
    largest_prediction_class: int
    observed_output: int
    candidate_count_after: int

    def to_dict(self):
        return {
            "round_index": self.round_index,
            "anonymous_query": list(self.point),
            "candidate_count_before": self.candidate_count_before,
            "predicted_output_classes": self.predicted_output_classes,
            "largest_prediction_class": self.largest_prediction_class,
            "observed_output": self.observed_output,
            "candidate_count_after": self.candidate_count_after,
        }


@dataclass(frozen=True, slots=True)
class PreregisteredPredictionV36:
    commitment: str
    points: tuple[PointV36, ...]
    predictions: tuple[int, ...]
    revealed_outputs: tuple[int, ...]

    @property
    def passed(self):
        return self.predictions == self.revealed_outputs

    def to_dict(self):
        return {
            "commitment": self.commitment,
            "anonymous_points": [list(point) for point in self.points],
            "predictions_committed_before_reveal": list(self.predictions),
            "revealed_outputs": list(self.revealed_outputs),
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class ActiveDiscoveryV36:
    initial_candidate_count: int
    initial_observations: tuple[BlindObservationV36, ...]
    experiments: tuple[ActiveExperimentV36, ...]
    selected_program: SparseProgramV36
    final_candidate_count: int

    def to_dict(self):
        return {
            "initial_candidate_count": self.initial_candidate_count,
            "initial_observations": [item.to_dict() for item in self.initial_observations],
            "active_experiments": [item.to_dict() for item in self.experiments],
            "selected_program": self.selected_program.to_dict(),
            "final_candidate_count": self.final_candidate_count,
        }


class ActiveScientificResearcherV36:
    """Select experiments that maximally split the current hypothesis set."""

    def __init__(self, *, maximum_nonzero_terms: int = 4, coefficient_limit: int = 2):
        self.maximum_nonzero_terms = maximum_nonzero_terms
        self.coefficient_limit = coefficient_limit

    def programs(self) -> tuple[SparseProgramV36, ...]:
        values = tuple(range(-self.coefficient_limit, self.coefficient_limit + 1))
        programs = (
            SparseProgramV36(tuple(coefficients))
            for coefficients in itertools.product(values, repeat=6)
            if sum(value != 0 for value in coefficients) <= self.maximum_nonzero_terms
        )
        return tuple(sorted(programs, key=lambda item: (item.token_cost, item.coefficients)))

    @staticmethod
    def _filter(programs: Iterable[SparseProgramV36], observations: Sequence[BlindObservationV36]):
        return tuple(
            program
            for program in programs
            if all(program.execute(item.inputs) == item.output for item in observations)
        )

    @staticmethod
    def _choose_query(programs: Sequence[SparseProgramV36], available: Sequence[PointV36]):
        best = None
        best_score = None
        best_partition = None
        for point in available:
            partitions: dict[int, int] = defaultdict(int)
            for program in programs:
                partitions[program.execute(point)] += 1
            score = (len(partitions), -max(partitions.values()), -(abs(point[0]) + abs(point[1])), tuple(-x for x in point))
            if best_score is None or score > best_score:
                best, best_score, best_partition = point, score, partitions
        if best is None or best_partition is None:
            raise RuntimeError("no discriminating experiment remains")
        return best, len(best_partition), max(best_partition.values())

    def discover(
        self,
        query: QueryV36,
        *,
        seed_points: Sequence[PointV36],
        experiment_pool: Sequence[PointV36],
        maximum_rounds: int = 12,
    ) -> ActiveDiscoveryV36:
        all_programs = self.programs()
        observations = tuple(
            BlindObservationV36(f"SEED-{index}", point, query(point))
            for index, point in enumerate(seed_points)
        )
        survivors = self._filter(all_programs, observations)
        used = set(seed_points)
        experiments = []
        for round_index in range(maximum_rounds):
            if len(survivors) <= 1:
                break
            available = tuple(point for point in experiment_pool if point not in used)
            point, classes, largest = self._choose_query(survivors, available)
            output = query(point)
            before = len(survivors)
            survivors = tuple(program for program in survivors if program.execute(point) == output)
            experiments.append(ActiveExperimentV36(round_index, point, before, classes, largest, output, len(survivors)))
            used.add(point)
        if len(survivors) != 1:
            raise RuntimeError(f"active discovery ended with {len(survivors)} candidates")
        return ActiveDiscoveryV36(len(all_programs), observations, tuple(experiments), survivors[0], len(survivors))

    @staticmethod
    def preregister_and_reveal(
        program: SparseProgramV36,
        points: Sequence[PointV36],
        query: QueryV36,
        commitment_sink: Callable[[str], None] | None = None,
    ):
        points = tuple(points)
        predictions = tuple(program.execute(point) for point in points)
        payload = {"program_id": program.program_id, "points": points, "predictions": predictions}
        commitment = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if commitment_sink is not None:
            commitment_sink(commitment)
        # The oracle is called only after the immutable prediction commitment exists.
        revealed = tuple(query(point) for point in points)
        return PreregisteredPredictionV36(commitment, points, predictions, revealed)
