"""V43 autonomous research-language growth over anonymous numeric traces.

The learner receives no named candidate model family.  It starts from one
visible channel and no recurrent state, mutates generic language resources,
fits every resulting executable program, and keeps only score-improving
mutations.  Arithmetic, least-squares fitting, and the bounded mutation rules
remain supplied substrate priors.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, replace
from typing import Any, Sequence

import numpy as np


@dataclass(frozen=True, slots=True)
class AnonymousNumericTraceV43:
    trace_id: str
    inputs: tuple[tuple[float, ...], ...]
    outputs: tuple[float, ...]

    def __post_init__(self):
        if len(self.inputs) < 3 or len(self.inputs) != len(self.outputs):
            raise ValueError("anonymous trace length is invalid")
        width = len(self.inputs[0])
        if width < 1 or any(len(row) != width for row in self.inputs):
            raise ValueError("anonymous input width is invalid")

    @property
    def input_width(self):
        return len(self.inputs[0])


@dataclass(frozen=True, slots=True)
class ResearchLanguageGenomeV43:
    visible_inputs: int = 1
    state_slots: int = 0
    initial_context: int = 0
    delta_features: int = 0
    pair_interactions: int = 0
    branch_slots: int = 0

    @property
    def cost(self):
        return (
            self.visible_inputs + 2 * self.state_slots + 2 * self.initial_context
            + 2 * self.delta_features + 3 * self.pair_interactions
            + 3 * self.branch_slots
        )

    def to_dict(self):
        return {
            "visible_inputs": self.visible_inputs,
            "state_slots": self.state_slots,
            "initial_context": self.initial_context,
            "delta_features": self.delta_features,
            "pair_interactions": self.pair_interactions,
            "branch_slots": self.branch_slots,
        }

    def mutations(self, input_width):
        candidates = []
        if self.visible_inputs < input_width:
            candidates.append((
                "grow_input_channel",
                replace(self, visible_inputs=self.visible_inputs + 1),
            ))
        if self.state_slots < 2:
            candidates.append((
                "grow_state_slot",
                replace(self, state_slots=self.state_slots + 1),
            ))
        if not self.initial_context:
            candidates.append((
                "grow_initial_context",
                replace(self, initial_context=1),
            ))
        if not self.delta_features and self.visible_inputs == input_width:
            candidates.append((
                "grow_delta_features",
                replace(self, delta_features=1),
            ))
        if not self.pair_interactions:
            candidates.append((
                "grow_pair_interactions",
                replace(self, pair_interactions=1),
            ))
        if self.state_slots and self.initial_context and not self.branch_slots:
            candidates.append((
                "grow_guarded_path",
                replace(self, branch_slots=1),
            ))
        return tuple(candidates)


def feature_language_v43(genome: ResearchLanguageGenomeV43):
    features = ["ONE"]
    features.extend(f"X{index}" for index in range(genome.visible_inputs))
    features.extend(f"LAG{index}" for index in range(1, genome.state_slots + 1))
    if genome.initial_context:
        features.append("INITIAL_Y")
        features.extend(f"INITIAL_X{index}" for index in range(genome.visible_inputs))
    if genome.delta_features:
        features.extend(f"DELTA_X{index}" for index in range(genome.visible_inputs))
    if genome.branch_slots:
        features.append("GUARD_X0_INITIAL_X0_LAG1")
    if genome.pair_interactions:
        atoms = tuple(features[1:])
        features.extend(
            f"MUL({left},{right})"
            for left_index, left in enumerate(atoms)
            for right in atoms[left_index:]
        )
    return tuple(features)


def _feature_value(name, current, previous, history, initial_input, initial_output):
    if name == "ONE":
        return 1.0
    if name.startswith("X") and name[1:].isdigit():
        return current[int(name[1:])]
    if name.startswith("LAG"):
        lag = int(name[3:])
        return history[-lag] if len(history) >= lag else history[0]
    if name == "INITIAL_Y":
        return initial_output
    if name.startswith("INITIAL_X"):
        return initial_input[int(name[9:])]
    if name.startswith("DELTA_X"):
        index = int(name[7:])
        return current[index] - previous[index]
    if name == "GUARD_X0_INITIAL_X0_LAG1":
        return (1.0 if current[0] >= initial_input[0] else 0.0) * history[-1]
    if name.startswith("MUL(") and name.endswith(")"):
        left, right = name[4:-1].split(",", 1)
        return _feature_value(
            left, current, previous, history, initial_input, initial_output,
        ) * _feature_value(
            right, current, previous, history, initial_input, initial_output,
        )
    raise ValueError(f"unknown feature semantic: {name}")


@dataclass(frozen=True, slots=True)
class ScientificProgramV43:
    genome: ResearchLanguageGenomeV43
    features: tuple[str, ...]
    coefficients: tuple[float, ...]
    validation_rmse: float
    validation_mape: float

    @property
    def program_id(self):
        payload = {
            "genome": self.genome.to_dict(),
            "features": self.features,
            "coefficients": tuple(round(value, 12) for value in self.coefficients),
        }
        return "AUTOSEM-" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16]

    @property
    def node_count(self):
        return len(self.features) + sum(name.startswith("MUL(") for name in self.features)

    def rollout(self, trace: AnonymousNumericTraceV43):
        history = [trace.outputs[0]]
        initial_input = trace.inputs[0]
        initial_output = trace.outputs[0]
        weights = np.asarray(self.coefficients)
        for index in range(1, len(trace.inputs)):
            values = np.asarray([
                _feature_value(
                    name,
                    trace.inputs[index],
                    trace.inputs[index - 1],
                    history,
                    initial_input,
                    initial_output,
                )
                for name in self.features
            ])
            with np.errstate(over="ignore", invalid="ignore"):
                predicted = float(values @ weights)
            history.append(predicted)
        return tuple(history)

    def render(self):
        terms = ";".join(
            f"W{index}*{name}" for index, name in enumerate(self.features)
        )
        return f"AUTONOMOUS_UPDATE<SLOTS={self.genome.state_slots};{terms}>"

    def to_dict(self):
        return {
            "program_id": self.program_id,
            "opaque_program": self.render(),
            "genome": self.genome.to_dict(),
            "features": list(self.features),
            "coefficients": list(self.coefficients),
            "validation_rmse": self.validation_rmse,
            "validation_mape": self.validation_mape,
            "node_count": self.node_count,
            "human_law_name": None,
            "named_candidate_family_supplied": False,
        }


@dataclass(frozen=True, slots=True)
class GenomeTrialV43:
    mutation: str
    genome: ResearchLanguageGenomeV43
    score: float
    validation_rmse: float
    feature_count: int

    def to_dict(self):
        return {
            "mutation": self.mutation,
            "genome": self.genome.to_dict(),
            "score": self.score,
            "validation_rmse": self.validation_rmse,
            "feature_count": self.feature_count,
        }


@dataclass(frozen=True, slots=True)
class ResearchRoundV43:
    round_index: int
    genome_before: ResearchLanguageGenomeV43
    selected_mutation: str | None
    genome_after: ResearchLanguageGenomeV43
    score_before: float
    score_after: float
    information_gain: float
    sterile_round_count: int
    trials: tuple[GenomeTrialV43, ...]

    def to_dict(self):
        return {
            "round_index": self.round_index,
            "genome_before": self.genome_before.to_dict(),
            "selected_mutation": self.selected_mutation,
            "genome_after": self.genome_after.to_dict(),
            "score_before": self.score_before,
            "score_after": self.score_after,
            "information_gain": self.information_gain,
            "sterile_round_count": self.sterile_round_count,
            "host_selected": False,
            "trials": [item.to_dict() for item in self.trials],
        }


class AutonomousScientistKernelV43:
    def __init__(
        self,
        *,
        complexity_penalty: float = 1e-5,
        minimum_information_gain: float = 1e-5,
        sterile_round_limit: int = 3,
        maximum_rounds: int = 16,
    ):
        self.complexity_penalty = complexity_penalty
        self.minimum_information_gain = minimum_information_gain
        self.sterile_round_limit = sterile_round_limit
        self.maximum_rounds = maximum_rounds

    @staticmethod
    def _fit_coefficients(traces, features):
        design = []
        targets = []
        for trace in traces:
            teacher_history = list(trace.outputs)
            for index in range(1, len(trace.inputs)):
                design.append([
                    _feature_value(
                        name,
                        trace.inputs[index],
                        trace.inputs[index - 1],
                        teacher_history[:index],
                        trace.inputs[0],
                        trace.outputs[0],
                    )
                    for name in features
                ])
                targets.append(trace.outputs[index])
        coefficients, *_ = np.linalg.lstsq(
            np.asarray(design), np.asarray(targets), rcond=None,
        )
        return tuple(float(value) for value in coefficients)

    @staticmethod
    def evaluate(program, traces, *, counterexample_limit=5):
        errors = []
        percentages = []
        cases = []
        for trace in traces:
            predictions = program.rollout(trace)
            trace_errors = [
                predicted - observed
                for predicted, observed in zip(
                    predictions[1:], trace.outputs[1:], strict=True,
                )
            ]
            errors.extend(trace_errors)
            percentages.extend(
                abs(error) / max(abs(observed), 1e-9)
                for error, observed in zip(
                    trace_errors, trace.outputs[1:], strict=True,
                )
            )
            trace_rmse = math.sqrt(
                sum(value * value for value in trace_errors) / len(trace_errors)
            ) if all(math.isfinite(value) for value in trace_errors) else math.inf
            cases.append({
                "trace_id": trace.trace_id,
                "rmse": trace_rmse,
                "final_predicted": predictions[-1],
                "final_observed": trace.outputs[-1],
            })
        finite = bool(errors) and all(math.isfinite(value) for value in errors)
        rmse = math.sqrt(sum(value * value for value in errors) / len(errors)) if finite else math.inf
        mape = float(np.median(percentages)) if finite else math.inf
        worst = sorted(cases, key=lambda item: (-item["rmse"], item["trace_id"]))
        return {
            "trace_count": len(traces),
            "point_count": len(errors),
            "rmse": rmse,
            "median_absolute_percentage_error": mape,
            "worst_trace_rmse": worst[0]["rmse"] if worst else math.inf,
            "counterexamples": worst[:counterexample_limit],
        }

    def _compile(self, genome, training, validation):
        features = feature_language_v43(genome)
        coefficients = self._fit_coefficients(training, features)
        draft = ScientificProgramV43(genome, features, coefficients, math.inf, math.inf)
        audit = self.evaluate(draft, validation)
        return ScientificProgramV43(
            genome,
            features,
            coefficients,
            audit["rmse"],
            audit["median_absolute_percentage_error"],
        )

    def _score(self, program):
        if not math.isfinite(program.validation_rmse):
            return math.inf
        return program.validation_rmse + self.complexity_penalty * program.node_count

    def discover(self, training, validation):
        if not training or not validation:
            raise ValueError("V43 requires separate development partitions")
        input_width = training[0].input_width
        if any(trace.input_width != input_width for trace in training + validation):
            raise ValueError("anonymous input widths differ")
        initial = ResearchLanguageGenomeV43()
        genome = initial
        current = self._compile(genome, training, validation)
        current_score = self._score(current)
        rounds = []
        sterile = 0
        evaluated = 1
        for round_index in range(1, self.maximum_rounds + 1):
            compiled_trials = []
            for mutation, candidate_genome in genome.mutations(input_width):
                candidate = self._compile(candidate_genome, training, validation)
                score = self._score(candidate)
                evaluated += 1
                compiled_trials.append((mutation, candidate_genome, candidate, score))
            if not compiled_trials:
                break
            mutation, candidate_genome, candidate, score = min(
                compiled_trials,
                key=lambda item: (item[3], item[1].cost, item[0]),
            )
            gain = current_score - score
            accepted = math.isfinite(score) and gain > self.minimum_information_gain
            before = genome
            before_score = current_score
            if accepted:
                genome = candidate_genome
                current = candidate
                current_score = score
                sterile = 0
            else:
                mutation = None
                gain = max(0.0, gain) if math.isfinite(gain) else 0.0
                sterile += 1
            trials = tuple(
                GenomeTrialV43(
                    trial_mutation,
                    trial_genome,
                    trial_score,
                    trial_program.validation_rmse,
                    len(trial_program.features),
                )
                for trial_mutation, trial_genome, trial_program, trial_score
                in compiled_trials
                if math.isfinite(trial_score)
            )
            rounds.append(ResearchRoundV43(
                round_index,
                before,
                mutation,
                genome,
                before_score,
                current_score,
                gain,
                sterile,
                trials,
            ))
            if sterile >= self.sterile_round_limit:
                break
        stop_reason = (
            "semantic_saturation"
            if sterile >= self.sterile_round_limit
            else "bounded_round_limit_or_exhausted_mutations"
        )
        return {
            "initial_genome": initial,
            "final_genome": genome,
            "selected_program": current,
            "rounds": tuple(rounds),
            "candidate_programs_evaluated": evaluated,
            "sterile_rounds": sterile,
            "stop_reason": stop_reason,
            "named_candidate_menu_received": False,
        }


def scientific_program_commitment_v43(program: ScientificProgramV43):
    payload = {
        "program_id": program.program_id,
        "features": program.features,
        "coefficients": tuple(round(value, 15) for value in program.coefficients),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
