"""Generic experience ranking, input permutation search, and active experiments."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .metamachine_gen2 import (
    InvalidReflectiveProgram,
    OP_ADD_INPUT,
    OP_GROW,
    OP_JUMP,
    OP_JUMP_IF_NEGATIVE,
    OP_JUMP_IF_ZERO,
    OP_LOAD_INPUT,
    OP_SUB_INPUT,
    ReflectiveCandidate,
    ReflectiveProgram,
    ReflectiveSearchReport,
)
from .observation import NumericTableObservation


def _signature(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _features(value: Mapping[str, Any]) -> tuple[str, ...]:
    substrate = str(value.get("substrate", "unknown"))
    words = value.get("words", [])
    if not isinstance(words, list):
        words = []
    opcodes = tuple(
        int(words[index])
        for index in range(0, len(words) - 1, 2)
        if isinstance(words[index], int)
    )
    instruction_count = len(opcodes)
    bucket = min(8, instruction_count // 8)
    result = {
        "substrate:" + substrate,
        f"instruction_bucket:{bucket}",
        f"backward_jump_bucket:{min(4, _backward_jumps(words))}",
        f"branch_bucket:{min(4, sum(op in (OP_JUMP_IF_ZERO, OP_JUMP_IF_NEGATIVE) for op in opcodes))}",
        f"grow:{int(OP_GROW in opcodes)}",
        f"runtime_input_count:{min(10, _runtime_input_count(value))}",
        f"invented_semantic:{int('invented_semantic' in value)}",
    }
    for opcode in set(opcodes):
        result.add(f"opcode:{opcode}")
    for left, right in zip(opcodes, opcodes[1:]):
        result.add(f"bigram:{left}>{right}")
    return tuple(sorted(result))


def _backward_jumps(words: Sequence[Any]) -> int:
    count = 0
    for offset in range(0, len(words) - 1, 2):
        if words[offset] == OP_JUMP and isinstance(words[offset + 1], int):
            count += int(words[offset + 1] < offset // 2)
    return count


def _runtime_input_count(value: Mapping[str, Any]) -> int:
    words = value.get("words", [])
    inputs = {
        words[offset + 1]
        for offset in range(0, len(words) - 1, 2)
        if words[offset] in (OP_LOAD_INPUT, OP_ADD_INPUT, OP_SUB_INPUT)
        and isinstance(words[offset + 1], int)
    }
    semantic = value.get("invented_semantic")
    if isinstance(semantic, Mapping) and isinstance(semantic.get("opcode"), int):
        opcode = semantic["opcode"]
        inputs.update(
            words[offset + 1] // 10_000
            for offset in range(0, len(words) - 1, 2)
            if words[offset] == opcode and isinstance(words[offset + 1], int)
        )
    return len(inputs)


@dataclass(frozen=True, slots=True)
class LearnedSearchPolicy:
    policy_id: str
    success_example_count: int
    failure_example_count: int
    feature_weights: Mapping[str, float]
    success_signatures: frozenset[str]
    failure_signatures: frozenset[str]

    def score(self, program) -> float:
        value = program.to_dict()
        signature = _signature(value)
        score = sum(self.feature_weights.get(feature, 0.0) for feature in _features(value))
        if signature in self.success_signatures:
            score += 25.0
        if signature in self.failure_signatures:
            score -= 25.0
        return score

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "experience-search-policy-v0.1",
            "policy_id": self.policy_id,
            "success_example_count": self.success_example_count,
            "failure_example_count": self.failure_example_count,
            "feature_weights": dict(sorted(self.feature_weights.items())),
            "success_signatures": sorted(self.success_signatures),
            "failure_signatures": sorted(self.failure_signatures),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LearnedSearchPolicy":
        if value.get("schema_version") != "experience-search-policy-v0.1":
            raise ValueError("unsupported learned-search policy")
        return cls(
            policy_id=str(value["policy_id"]),
            success_example_count=int(value["success_example_count"]),
            failure_example_count=int(value["failure_example_count"]),
            feature_weights={str(key): float(weight) for key, weight in value["feature_weights"].items()},
            success_signatures=frozenset(str(item) for item in value["success_signatures"]),
            failure_signatures=frozenset(str(item) for item in value["failure_signatures"]),
        )


class SearchPolicyTrainer:
    def train(
        self,
        success_programs: Sequence[Mapping[str, Any]],
        failure_programs: Sequence[Mapping[str, Any]],
    ) -> LearnedSearchPolicy:
        if not success_programs or not failure_programs:
            raise ValueError("policy training requires success and failure experience")
        success_counts: dict[str, int] = {}
        failure_counts: dict[str, int] = {}
        for value in success_programs:
            for feature in _features(value):
                success_counts[feature] = success_counts.get(feature, 0) + 1
        for value in failure_programs:
            for feature in _features(value):
                failure_counts[feature] = failure_counts.get(feature, 0) + 1
        features = set(success_counts) | set(failure_counts)
        weights = {
            feature: max(
                -3.0,
                min(
                    3.0,
                    math.log(
                        ((success_counts.get(feature, 0) + 1) / (len(success_programs) + 2))
                        / ((failure_counts.get(feature, 0) + 1) / (len(failure_programs) + 2))
                    ),
                ),
            )
            for feature in features
        }
        payload = {
            "success": sorted(_signature(value) for value in success_programs),
            "failure": sorted(_signature(value) for value in failure_programs),
            "weights": dict(sorted(weights.items())),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return LearnedSearchPolicy(
            policy_id="POLICY-" + hashlib.sha256(encoded.encode()).hexdigest()[:16],
            success_example_count=len(success_programs),
            failure_example_count=len(failure_programs),
            feature_weights=weights,
            success_signatures=frozenset(payload["success"]),
            failure_signatures=frozenset(payload["failure"]),
        )


class ExperienceGuidedSearch:
    """Rerank equal-fit candidates using learned cross-task experience."""

    def __init__(self, base_search, policy: LearnedSearchPolicy, *, top_k: int = 300):
        self.base_search = base_search
        self.policy = policy
        self.top_k = top_k
        self.executor = base_search.executor

    def search(self, observation: NumericTableObservation) -> ReflectiveSearchReport:
        report = self.base_search.search(observation)
        candidates = sorted(
            report.top_candidates,
            key=lambda item: (
                item.fit_error,
                -self.policy.score(item.program),
                item.program.instruction_count,
                item.maximum_absolute_error,
                item.candidate_id,
            ),
        )
        return ReflectiveSearchReport(
            report.programs_generated,
            report.programs_executed,
            report.programs_rejected,
            report.behavior_classes,
            tuple(candidates[: self.top_k]),
        )


class PermutationInvariantSearch:
    """Remove stable column-order assumptions from a table searcher."""

    def __init__(
        self, base_search, *, maximum_width: int = 6, top_k: int = 1000,
        candidates_per_permutation: int = 300,
    ) -> None:
        self.base_search = base_search
        self.executor = base_search.executor
        self.maximum_width = maximum_width
        self.top_k = top_k
        self.candidates_per_permutation = candidates_per_permutation

    def search(self, observation: NumericTableObservation) -> ReflectiveSearchReport:
        width = len(observation.input_rows[0])
        if width > self.maximum_width:
            raise ValueError("full input permutation exceeds configured width bound")
        generated = executed = rejected = 0
        candidates: dict[str, ReflectiveCandidate] = {}
        for permutation in itertools.permutations(range(width)):
            transformed = NumericTableObservation.create(
                opaque_session_id=observation.opaque_session_id + "-perm-" + "".join(map(str, permutation)),
                input_rows=tuple(
                    tuple(row[index] for index in permutation)
                    for row in observation.input_rows
                ),
                output_values=observation.output_values,
                validity_mask=observation.validity_mask,
                action_receipt="permutation_invariant_anonymous_table",
            )
            report = self.base_search.search(transformed)
            generated += report.programs_generated
            executed += report.programs_executed
            rejected += report.programs_rejected
            for candidate in report.top_candidates[: self.candidates_per_permutation]:
                program = _remap_reflective_inputs(candidate.program, permutation)
                key = _signature(program.to_dict())
                if key in candidates:
                    continue
                candidate_id = "PI-" + hashlib.sha256(key.encode()).hexdigest()[:16]
                candidates[key] = ReflectiveCandidate(
                    candidate_id,
                    program,
                    candidate.fit_error,
                    candidate.maximum_absolute_error,
                    candidate.outputs,
                    candidate.behavior_signature,
                )
        ranked = sorted(
            candidates.values(),
            key=lambda item: (
                item.fit_error, item.program.instruction_count,
                item.maximum_absolute_error, item.candidate_id,
            ),
        )
        return ReflectiveSearchReport(
            generated, executed, rejected,
            len({item.behavior_signature for item in candidates.values()}),
            tuple(ranked[: self.top_k]),
        )


def _remap_reflective_inputs(
    program: ReflectiveProgram, permutation: Sequence[int]
) -> ReflectiveProgram:
    words = list(program.words)
    for offset in range(0, len(words), 2):
        if words[offset] in (OP_LOAD_INPUT, OP_ADD_INPUT, OP_SUB_INPUT):
            input_index = words[offset + 1]
            if input_index < 0 or input_index >= len(permutation):
                raise InvalidReflectiveProgram("program input lies outside permutation")
            words[offset + 1] = permutation[input_index]
    return ReflectiveProgram(tuple(words))


@dataclass(frozen=True, slots=True)
class ExperimentProposal:
    input_row: tuple[float, ...]
    distinct_output_count: int
    disagreeing_candidate_pairs: int
    candidate_outputs: tuple[float | None, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_row": list(self.input_row),
            "distinct_output_count": self.distinct_output_count,
            "disagreeing_candidate_pairs": self.disagreeing_candidate_pairs,
            "candidate_outputs": list(self.candidate_outputs),
        }


class DisagreementExperimentPlanner:
    """Choose an unlabeled row that maximally separates executable hypotheses."""

    def __init__(self, *, maximum_candidates: int = 40):
        self.maximum_candidates = maximum_candidates

    def propose(
        self,
        candidates: Sequence[ReflectiveCandidate],
        executor,
        *,
        input_width: int,
        observed_rows: Sequence[Sequence[float]],
        value_pool: Sequence[int],
    ) -> ExperimentProposal | None:
        hypotheses = tuple(candidates[: self.maximum_candidates])
        if len(hypotheses) < 2:
            return None
        observed = {tuple(float(value) for value in row) for row in observed_rows}
        best = None
        best_key = None
        for integer_row in itertools.product(value_pool, repeat=input_width):
            row = tuple(float(value) for value in integer_row)
            if row in observed:
                continue
            outputs = []
            for candidate in hypotheses:
                try:
                    outputs.append(executor.execute(candidate.program, row).output_value)
                except InvalidReflectiveProgram:
                    outputs.append(None)
            counts: dict[float | None, int] = {}
            for output in outputs:
                counts[output] = counts.get(output, 0) + 1
            total = len(outputs)
            disagreeing = (total * total - sum(count * count for count in counts.values())) // 2
            key = (
                disagreeing,
                len(counts),
                -sum(abs(value) for value in row),
                tuple(-value for value in row),
            )
            if best_key is None or key > best_key:
                best_key = key
                best = ExperimentProposal(row, len(counts), disagreeing, tuple(outputs))
        return best


@dataclass(frozen=True, slots=True)
class AutonomousExperimentRound:
    round_index: int
    observation_count: int
    exact_candidate_count: int
    selected_candidate_id: str
    proposed_experiment: ExperimentProposal | None
    observed_output: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_index": self.round_index,
            "observation_count": self.observation_count,
            "exact_candidate_count": self.exact_candidate_count,
            "selected_candidate_id": self.selected_candidate_id,
            "proposed_experiment": (
                self.proposed_experiment.to_dict() if self.proposed_experiment else None
            ),
            "observed_output": self.observed_output,
        }


@dataclass(frozen=True, slots=True)
class AutonomousExperimentReport:
    converged: bool
    rounds: tuple[AutonomousExperimentRound, ...]
    final_candidate: ReflectiveCandidate
    input_rows: tuple[tuple[float, ...], ...]
    output_values: tuple[float, ...]


class AutonomousExperimentLoop:
    """Let hypothesis disagreement, not a host case list, choose the next query."""

    def __init__(
        self, search, *, planner: DisagreementExperimentPlanner | None = None,
        maximum_rounds: int = 10,
    ) -> None:
        self.search = search
        self.planner = planner or DisagreementExperimentPlanner()
        self.maximum_rounds = maximum_rounds

    def run(
        self,
        *,
        opaque_task_id: str,
        initial_rows: Sequence[Sequence[float]],
        initial_outputs: Sequence[float],
        oracle: Callable[[tuple[float, ...]], float],
        value_pool: Sequence[int],
    ) -> AutonomousExperimentReport:
        rows = [tuple(float(value) for value in row) for row in initial_rows]
        outputs = [float(value) for value in initial_outputs]
        if not rows or len(rows) != len(outputs):
            raise ValueError("initial autonomous observations are invalid")
        rounds = []
        final = None
        for round_index in range(self.maximum_rounds):
            observation = NumericTableObservation.create(
                opaque_session_id=f"{opaque_task_id}-active-{round_index}",
                input_rows=tuple(rows),
                output_values=tuple(outputs),
                validity_mask=(True,) * len(rows),
                action_receipt="autonomous_disagreement_experiment",
            )
            report = self.search.search(observation)
            exact = tuple(item for item in report.top_candidates if item.exact)
            if not exact:
                raise RuntimeError("active search has no exact hypothesis")
            final = exact[0]
            proposal = self.planner.propose(
                exact,
                self.search.executor,
                input_width=len(rows[0]),
                observed_rows=rows,
                value_pool=value_pool,
            )
            observed_output = None
            if proposal is not None and proposal.disagreeing_candidate_pairs > 0:
                observed_output = float(oracle(proposal.input_row))
                rows.append(proposal.input_row)
                outputs.append(observed_output)
            rounds.append(
                AutonomousExperimentRound(
                    round_index, len(rows) - int(observed_output is not None),
                    len(exact), final.candidate_id, proposal, observed_output,
                )
            )
            if observed_output is None:
                return AutonomousExperimentReport(
                    True, tuple(rounds), final, tuple(rows), tuple(outputs)
                )
        assert final is not None
        return AutonomousExperimentReport(
            False, tuple(rounds), final, tuple(rows), tuple(outputs)
        )
