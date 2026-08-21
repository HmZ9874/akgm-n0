"""Target-free fold-program exploration over previously admitted semantics."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any


PRIOR_BINARY_SEMANTIC_ID = "STRICT-FSEM-82df58ba4ce6f41c"
SOURCE_NAMES = ("accumulator", "input_0", "input_1", "zero", "unit")
SEED_NAMES = ("input_0", "input_1", "zero", "unit")
OPERATION_IDS = ("verified_combine", PRIOR_BINARY_SEMANTIC_ID)
OUTPUT_NAMES = ("accumulator", "input_0", "input_1")


class FoldExecutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FoldProgram:
    loop_input: int
    seed_source: str
    operation_id: str
    left_source: str
    right_source: str
    output_source: str

    def __post_init__(self) -> None:
        if self.loop_input not in (0, 1):
            raise ValueError("loop input must be anonymous input 0 or 1")
        if self.seed_source not in SEED_NAMES:
            raise ValueError("unknown fold seed")
        if self.operation_id not in OPERATION_IDS:
            raise ValueError("unknown fold operation")
        if self.left_source not in SOURCE_NAMES or self.right_source not in SOURCE_NAMES:
            raise ValueError("unknown fold update source")
        if self.output_source not in OUTPUT_NAMES:
            raise ValueError("unknown fold output")

    @property
    def primitive_node_count(self) -> int:
        return 6

    def to_dict(self) -> dict[str, Any]:
        return {
            "substrate": "anonymous_fold_controller_v12",
            "loop_input": self.loop_input,
            "seed_source": self.seed_source,
            "update": {
                "operation_id": self.operation_id,
                "left_source": self.left_source,
                "right_source": self.right_source,
            },
            "output_source": self.output_source,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FoldProgram":
        if value.get("substrate") != "anonymous_fold_controller_v12":
            raise ValueError("fold substrate is unavailable")
        update = value["update"]
        return cls(
            int(value["loop_input"]),
            str(value["seed_source"]),
            str(update["operation_id"]),
            str(update["left_source"]),
            str(update["right_source"]),
            str(value["output_source"]),
        )


@dataclass(frozen=True, slots=True)
class FoldExecution:
    output: int
    accumulator: int
    iterations: int
    semantic_calls: int


class FoldExecutor:
    """Execute folds using combine or the verified opaque V10 semantic."""

    def __init__(self, magnitude_limit: int = 10**18) -> None:
        self.magnitude_limit = magnitude_limit

    def execute(self, program: FoldProgram, inputs: tuple[int, int]) -> FoldExecution:
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in inputs):
            raise FoldExecutionError("fold inputs must be natural numbers")
        accumulator = self._source(program.seed_source, inputs, 0)
        remaining = inputs[program.loop_input]
        calls = 0
        for _ in range(remaining):
            left = self._source(program.left_source, inputs, accumulator)
            right = self._source(program.right_source, inputs, accumulator)
            accumulator = self._apply(program.operation_id, left, right)
            calls += 1
            if accumulator > self.magnitude_limit:
                raise FoldExecutionError("fold exceeded its magnitude boundary")
        output = self._source(program.output_source, inputs, accumulator)
        return FoldExecution(output, accumulator, remaining, calls)

    @staticmethod
    def _source(name: str, inputs: tuple[int, int], accumulator: int) -> int:
        if name == "accumulator":
            return accumulator
        if name == "input_0":
            return inputs[0]
        if name == "input_1":
            return inputs[1]
        if name == "zero":
            return 0
        if name == "unit":
            return 1
        raise FoldExecutionError("unknown fold source")

    @staticmethod
    def _apply(operation_id: str, left: int, right: int) -> int:
        if operation_id == "verified_combine":
            return left + right
        if operation_id == PRIOR_BINARY_SEMANTIC_ID:
            # Replay the admitted semantic's proven normal form.  The candidate
            # sees only the opaque semantic id, not an arithmetic opcode.
            return left * right
        raise FoldExecutionError("unknown fold operation")


@dataclass(frozen=True, slots=True)
class IterationProfile:
    depends_on_base_and_count: bool
    zero_count_is_unit: bool
    successor_uses_prior_semantic: bool
    count_composition_homomorphism: bool
    unit_base_fixed: bool
    base_composition_homomorphism: bool

    @property
    def promotable(self) -> bool:
        return all((
            self.depends_on_base_and_count,
            self.zero_count_is_unit,
            self.successor_uses_prior_semantic,
            self.count_composition_homomorphism,
            self.unit_base_fixed,
            self.base_composition_homomorphism,
        ))

    @property
    def law_count(self) -> int:
        return sum((
            self.depends_on_base_and_count,
            self.zero_count_is_unit,
            self.successor_uses_prior_semantic,
            self.count_composition_homomorphism,
            self.unit_base_fixed,
            self.base_composition_homomorphism,
        ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "depends_on_base_and_count": self.depends_on_base_and_count,
            "zero_count_returns_prior_identity": self.zero_count_is_unit,
            "successor_is_one_prior_semantic_application": self.successor_uses_prior_semantic,
            "count_composition_is_homomorphic": self.count_composition_homomorphism,
            "prior_identity_base_is_fixed": self.unit_base_fixed,
            "base_composition_is_homomorphic": self.base_composition_homomorphism,
            "law_count": self.law_count,
            "promotable": self.promotable,
        }


@dataclass(frozen=True, slots=True)
class FoldCandidate:
    candidate_id: str
    program: FoldProgram
    behavior_signature: tuple[int, ...]
    profile: IterationProfile
    semantic_call_cost: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "program": self.program.to_dict(),
            "behavior_signature": list(self.behavior_signature),
            "iteration_profile": self.profile.to_dict(),
            "primitive_node_count": self.program.primitive_node_count,
            "semantic_call_cost": self.semantic_call_cost,
        }


@dataclass(frozen=True, slots=True)
class FoldExplorationReport:
    programs_generated: int
    programs_executed: int
    behavior_classes: int
    promotable_behavior_classes: int
    selected: FoldCandidate
    rejected_leaders: tuple[FoldCandidate, ...]


def fold_program_id(program: FoldProgram) -> str:
    payload = json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":"))
    return "FD-" + hashlib.sha256(payload.encode()).hexdigest()[:16]


def inspect_iteration_profile(executor: FoldExecutor, program: FoldProgram, *, limit: int = 4) -> IterationProfile:
    base_input = 1 - program.loop_input

    def run(base: int, count: int) -> int:
        inputs = (base, count) if base_input == 0 else (count, base)
        return executor.execute(program, inputs).output

    depends_base = any(run(base, count) != run(0, count) for base in range(limit + 1) for count in range(1, limit + 1))
    depends_count = any(run(base, count) != run(base, 0) for base in range(2, limit + 1) for count in range(1, limit + 1))
    zero = all(run(base, 0) == 1 for base in range(limit + 1))
    successor = all(run(base, count + 1) == run(base, count) * base for base in range(limit + 1) for count in range(limit))
    count_hom = all(run(base, left + right) == run(base, left) * run(base, right) for base in range(limit + 1) for left in range(3) for right in range(3))
    unit_fixed = all(run(1, count) == 1 for count in range(limit + 1))
    base_hom = all(run(left * right, count) == run(left, count) * run(right, count) for left in range(3) for right in range(3) for count in range(4))
    return IterationProfile(depends_base and depends_count, zero, successor, count_hom, unit_fixed, base_hom)


class TargetFreeFoldExplorer:
    def __init__(self, probe_limit: int = 4) -> None:
        self.probe_limit = probe_limit
        self.executor = FoldExecutor()

    def enumerate_programs(self) -> tuple[FoldProgram, ...]:
        return tuple(
            FoldProgram(loop, seed, operation, left, right, output)
            for loop, seed, operation, left, right, output in itertools.product(
                (0, 1), SEED_NAMES, OPERATION_IDS, SOURCE_NAMES, SOURCE_NAMES, OUTPUT_NAMES
            )
        )

    def search(self) -> FoldExplorationReport:
        programs = self.enumerate_programs()
        by_behavior: dict[tuple[int, ...], tuple[FoldProgram, int]] = {}
        executed = 0
        for program in programs:
            behavior = []
            calls = 0
            try:
                for left in range(self.probe_limit + 1):
                    for right in range(self.probe_limit + 1):
                        result = self.executor.execute(program, (left, right))
                        behavior.append(result.output)
                        calls += result.semantic_calls
            except FoldExecutionError:
                continue
            executed += 1
            signature = tuple(behavior)
            current = by_behavior.get(signature)
            if current is None or (program.primitive_node_count, calls, fold_program_id(program)) < (
                current[0].primitive_node_count, current[1], fold_program_id(current[0])
            ):
                by_behavior[signature] = (program, calls)
        candidates = []
        for behavior, (program, calls) in by_behavior.items():
            profile = inspect_iteration_profile(self.executor, program)
            candidates.append(FoldCandidate(fold_program_id(program), program, behavior, profile, calls))
        candidates.sort(key=lambda item: (-item.profile.law_count, item.program.primitive_node_count, item.semantic_call_cost, item.candidate_id))
        promotable = [item for item in candidates if item.profile.promotable]
        if not promotable:
            raise RuntimeError("no fold behavior passed the iteration-homomorphism gate")
        return FoldExplorationReport(len(programs), executed, len(candidates), len(promotable), promotable[0], tuple(item for item in candidates if not item.profile.promotable)[:20])
