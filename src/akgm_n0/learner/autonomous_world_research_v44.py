"""V44 autonomous world selection over sealed official numeric archives.

The host supplies a finite registry and safety/resource ceilings.  The research
director receives anonymous development traces, grows a V43 research language
inside every world, estimates expected information gain, and commits to one
world and one executable program before transfer measurements or domain labels
are revealed.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from akgm_n0.learner.autonomous_scientist_v43 import (
    AnonymousNumericTraceV43,
    AutonomousScientistKernelV43,
    ScientificProgramV43,
    scientific_program_commitment_v43,
)


@dataclass(frozen=True, slots=True)
class AnonymousWorldV44:
    world_id: str
    descriptor: dict[str, Any]
    training: tuple[AnonymousNumericTraceV43, ...]
    validation: tuple[AnonymousNumericTraceV43, ...]
    sealed_transfer_trace_count: int
    source_receipt_count: int


@dataclass(frozen=True, slots=True)
class WorldSurveyV44:
    world_id: str
    program: ScientificProgramV43
    discovery: dict[str, Any]
    output_scale: float
    initial_normalized_error: float
    final_normalized_error: float
    normalized_information_gain: float
    structural_novelty: float
    verification_readiness: float
    worst_development_group_error: float
    cross_group_stability: float
    research_priority: float

    def summary(self):
        return {
            "world_id": self.world_id,
            "program_id": self.program.program_id,
            "output_scale": self.output_scale,
            "initial_normalized_error": self.initial_normalized_error,
            "final_normalized_error": self.final_normalized_error,
            "normalized_information_gain": self.normalized_information_gain,
            "structural_novelty": self.structural_novelty,
            "verification_readiness": self.verification_readiness,
            "worst_development_group_error": self.worst_development_group_error,
            "cross_group_stability": self.cross_group_stability,
            "research_priority": self.research_priority,
            "selected_mutations": [
                item.selected_mutation for item in self.discovery["rounds"]
                if item.selected_mutation is not None
            ],
            "candidate_programs_evaluated": self.discovery["candidate_programs_evaluated"],
            "stop_reason": self.discovery["stop_reason"],
            "host_selected": False,
            "domain_label_received": False,
            "transfer_outputs_received": False,
        }


def _scale(traces):
    values = np.asarray([value for trace in traces for value in trace.outputs], dtype=float)
    if not len(values):
        return 1.0
    q10, q90 = np.quantile(values, (0.10, 0.90))
    robust = float(q90 - q10)
    standard = float(np.std(values))
    return max(robust, standard, 1e-9)


class AutonomousWorldResearchDirectorV44:
    """Choose a research world by evidence value rather than a host label."""

    def __init__(self, kernel: AutonomousScientistKernelV43 | None = None):
        self.kernel = kernel or AutonomousScientistKernelV43()

    def survey(self, world: AnonymousWorldV44):
        discovery = self.kernel.discover(world.training, world.validation)
        program = discovery["selected_program"]
        rounds = discovery["rounds"]
        output_scale = _scale(world.validation)
        initial_score = rounds[0].score_before if rounds else program.validation_rmse
        initial_error = initial_score / output_scale
        final_error = program.validation_rmse / output_scale
        gain = max(0.0, initial_error - final_error)
        accepted_mutations = sum(item.selected_mutation is not None for item in rounds)
        novelty = min(1.0, accepted_mutations / 4.0)
        source_diversity = min(1.0, world.source_receipt_count / 3.0)
        readiness = min(1.0, world.sealed_transfer_trace_count / 10.0) * source_diversity
        predictability = 1.0 / (1.0 + final_error)
        groups = {}
        for trace in world.training + world.validation:
            groups.setdefault(trace.trace_id.split("-", 1)[0], []).append(trace)
        group_errors = [
            self.kernel.evaluate(program, tuple(traces))["rmse"] / output_scale
            for traces in groups.values()
        ]
        worst_group_error = max(group_errors) if group_errors else math.inf
        cross_group_stability = (
            1.0 / (1.0 + worst_group_error) if len(groups) >= 2 else 0.25
        )
        evidence_value = (
            0.45 * min(1.0, gain)
            + 0.30 * predictability
            + 0.15 * novelty
            + 0.10 * readiness
            - 0.002 * program.node_count
        )
        priority = evidence_value * cross_group_stability
        return WorldSurveyV44(
            world.world_id,
            program,
            discovery,
            output_scale,
            initial_error,
            final_error,
            gain,
            novelty,
            readiness,
            worst_group_error,
            cross_group_stability,
            priority,
        )

    def choose_next_world(self, worlds):
        surveys = tuple(self.survey(world) for world in worlds)
        if not surveys:
            raise ValueError("V44 requires at least one anonymous world")
        ranked = tuple(sorted(
            surveys,
            key=lambda item: (-item.research_priority, item.world_id),
        ))
        return {"selected": ranked[0], "ranked": ranked, "host_selected": False}


def research_agenda_commitment_v44(survey: WorldSurveyV44):
    payload = {
        "world_id": survey.world_id,
        "program_commitment": scientific_program_commitment_v43(survey.program),
        "research_priority": round(survey.research_priority, 15),
        "normalized_information_gain": round(survey.normalized_information_gain, 15),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def program_from_report_v44(payload):
    from akgm_n0.learner.autonomous_scientist_v43 import ResearchLanguageGenomeV43

    genome = ResearchLanguageGenomeV43(**{
        name: int(value) for name, value in payload["genome"].items()
    })
    return ScientificProgramV43(
        genome,
        tuple(map(str, payload["features"])),
        tuple(map(float, payload["coefficients"])),
        float(payload["validation_rmse"]),
        float(payload["validation_mape"]),
    )
