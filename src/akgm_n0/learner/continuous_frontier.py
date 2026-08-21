"""Anonymous exact-rational search for local and partition-stable semantics."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class LocalSample:
    world_id: str
    point: Fraction
    step: Fraction
    left: Fraction
    center: Fraction
    right: Fraction


@dataclass(frozen=True, slots=True)
class LocalStabilitySemantic:
    semantic_id: str
    opcode: int
    forward_form: str
    backward_form: str
    denominator_power: int
    denominator_scale: int
    candidate_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id,
            "opcode": self.opcode,
            "forward_form": self.forward_form,
            "backward_form": self.backward_form,
            "denominator_power": self.denominator_power,
            "denominator_scale": self.denominator_scale,
            "candidate_count": self.candidate_count,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LocalStabilitySemantic":
        return cls(
            str(value["semantic_id"]), int(value["opcode"]),
            str(value["forward_form"]), str(value["backward_form"]),
            int(value["denominator_power"]), int(value["denominator_scale"]),
            int(value["candidate_count"]),
        )

    def execute(self, sample: LocalSample) -> tuple[Fraction, Fraction]:
        denominator = self.denominator_scale * sample.step ** self.denominator_power
        return (
            _local_numerator(self.forward_form, sample) / denominator,
            _local_numerator(self.backward_form, sample) / denominator,
        )


@dataclass(frozen=True, slots=True)
class LocalSearchReport:
    semantic: LocalStabilitySemantic
    candidate_count: int
    context_count: int
    best_score: tuple[str, ...]
    runner_up_scores: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic": self.semantic.to_dict(),
            "candidate_count": self.candidate_count,
            "context_count": self.context_count,
            "best_score": list(self.best_score),
            "runner_up_scores": [dict(item) for item in self.runner_up_scores],
        }


class LocalStabilitySearch:
    FORWARD_FORMS = ("right-center", "center-right", "right-left", "right+center")
    BACKWARD_FORMS = ("center-left", "left-center", "right-left", "center+left")

    def search(self, samples: Sequence[LocalSample], *, opcode: int = 129) -> LocalSearchReport:
        grouped: dict[tuple[str, Fraction], list[LocalSample]] = {}
        for sample in samples:
            grouped.setdefault((sample.world_id, sample.point), []).append(sample)
        candidates = []
        for forward, backward, power, scale in itertools.product(
            self.FORWARD_FORMS, self.BACKWARD_FORMS, (0, 1, 2), (1, 2)
        ):
            reconstruction = Fraction(0)
            convergence = Fraction(0)
            agreement = Fraction(0)
            variation = set()
            valid = True
            for contexts in grouped.values():
                ordered = sorted(contexts, key=lambda item: item.step, reverse=True)
                values = []
                for sample in ordered:
                    denominator = scale * sample.step ** power
                    if denominator == 0:
                        valid = False
                        break
                    front = _local_numerator(forward, sample) / denominator
                    back = _local_numerator(backward, sample) / denominator
                    reconstruction += abs(front * sample.step - (sample.right - sample.center))
                    reconstruction += abs(back * sample.step - (sample.center - sample.left))
                    values.append((front, back))
                if not valid:
                    break
                for previous, current in zip(values, values[1:]):
                    convergence += abs(current[0] - previous[0]) + abs(current[1] - previous[1])
                agreement += abs(values[-1][0] - values[-1][1])
                variation.add((values[-1][0] + values[-1][1]) / 2)
            if not valid or len(variation) < 3:
                continue
            score = (reconstruction, convergence + agreement, power + scale)
            candidates.append((score, forward, backward, power, scale))
        candidates.sort(key=lambda item: (item[0], item[1:]))
        if not candidates:
            raise ValueError("no nontrivial local-stability candidate")
        best = candidates[0]
        _, forward, backward, power, scale = best
        payload = {
            "opcode": opcode, "forward": forward, "backward": backward,
            "power": power, "scale": scale, "candidate_count": len(candidates),
        }
        semantic = LocalStabilitySemantic(
            "SEM-" + hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()[:16],
            opcode, forward, backward, power, scale, len(candidates),
        )
        runners = tuple(
            {
                "forward_form": item[1], "backward_form": item[2],
                "denominator_power": item[3], "denominator_scale": item[4],
                "score": [_fraction_text(value) for value in item[0]],
            }
            for item in candidates[1:6]
        )
        return LocalSearchReport(
            semantic, len(candidates), len(samples),
            tuple(_fraction_text(value) for value in best[0]), runners,
        )


@dataclass(frozen=True, slots=True)
class PartitionSample:
    world_id: str
    interval_id: str
    start: Fraction
    end: Fraction
    partition_count: int
    left_values: tuple[Fraction, ...]
    midpoint_values: tuple[Fraction, ...]
    right_values: tuple[Fraction, ...]

    @property
    def width(self) -> Fraction:
        return (self.end - self.start) / self.partition_count


@dataclass(frozen=True, slots=True)
class PartitionAccumulationSemantic:
    semantic_id: str
    opcode: int
    anchor: str
    aggregation: str
    width_power: int
    scale: int
    candidate_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id, "opcode": self.opcode,
            "anchor": self.anchor, "aggregation": self.aggregation,
            "width_power": self.width_power, "scale": self.scale,
            "candidate_count": self.candidate_count,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PartitionAccumulationSemantic":
        return cls(
            str(value["semantic_id"]), int(value["opcode"]), str(value["anchor"]),
            str(value["aggregation"]), int(value["width_power"]),
            int(value["scale"]), int(value["candidate_count"]),
        )

    def execute(self, sample: PartitionSample) -> Fraction:
        values = {
            "left": sample.left_values,
            "midpoint": sample.midpoint_values,
            "right": sample.right_values,
        }[self.anchor]
        total = sum(values, Fraction(0))
        if self.aggregation == "mean":
            total /= len(values)
        return total * sample.width ** self.width_power / self.scale


@dataclass(frozen=True, slots=True)
class PartitionSearchReport:
    semantic: PartitionAccumulationSemantic
    candidate_count: int
    sample_count: int
    best_score: tuple[str, ...]
    runner_up_scores: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic": self.semantic.to_dict(), "candidate_count": self.candidate_count,
            "sample_count": self.sample_count, "best_score": list(self.best_score),
            "runner_up_scores": [dict(item) for item in self.runner_up_scores],
        }


class PartitionStabilitySearch:
    def search(
        self, samples: Sequence[PartitionSample], *, opcode: int = 130
    ) -> PartitionSearchReport:
        grouped: dict[tuple[str, str], list[PartitionSample]] = {}
        by_interval: dict[tuple[str, Fraction, Fraction, int], PartitionSample] = {}
        for sample in samples:
            grouped.setdefault((sample.world_id, sample.interval_id), []).append(sample)
            by_interval[(sample.world_id, sample.start, sample.end, sample.partition_count)] = sample
        candidates = []
        for anchor, aggregation, power, scale in itertools.product(
            ("left", "midpoint", "right"), ("sum", "mean"), (0, 1, 2), (1, 2)
        ):
            semantic = PartitionAccumulationSemantic("", opcode, anchor, aggregation, power, scale, 0)
            refinement = Fraction(0)
            additivity = Fraction(0)
            ratios = Fraction(0)
            variation = set()
            for contexts in grouped.values():
                ordered = sorted(contexts, key=lambda item: item.partition_count)
                values = [semantic.execute(item) for item in ordered]
                for previous, current in zip(values, values[1:]):
                    refinement += abs(current - previous)
                    if previous != 0:
                        ratios += abs(current / previous - 1)
                variation.add(values[-1])
            for sample in samples:
                midpoint = (sample.start + sample.end) / 2
                if sample.partition_count % 2:
                    continue
                left = by_interval.get((sample.world_id, sample.start, midpoint, sample.partition_count // 2))
                right = by_interval.get((sample.world_id, midpoint, sample.end, sample.partition_count // 2))
                if left and right:
                    additivity += abs(semantic.execute(sample) - semantic.execute(left) - semantic.execute(right))
            if len(variation) < 3:
                continue
            # Complexity precedes absolute residual magnitude so multiplying an
            # otherwise identical candidate by an arbitrary 1/2 cannot win only
            # because all of its errors were scaled down.
            candidates.append(((additivity, ratios, power + scale, refinement), anchor, aggregation, power, scale))
        candidates.sort(key=lambda item: (item[0], item[1:]))
        if not candidates:
            raise ValueError("no nontrivial partition-stability candidate")
        best = candidates[0]
        _, anchor, aggregation, power, scale = best
        payload = {
            "opcode": opcode, "anchor": anchor, "aggregation": aggregation,
            "power": power, "scale": scale, "candidate_count": len(candidates),
        }
        semantic = PartitionAccumulationSemantic(
            "SEM-" + hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()[:16],
            opcode, anchor, aggregation, power, scale, len(candidates),
        )
        runners = tuple(
            {
                "anchor": item[1], "aggregation": item[2], "width_power": item[3],
                "scale": item[4], "score": [_fraction_text(value) for value in item[0]],
            }
            for item in candidates[1:6]
        )
        return PartitionSearchReport(
            semantic, len(candidates), len(samples),
            tuple(_fraction_text(value) for value in best[0]), runners,
        )


def _local_numerator(form: str, sample: LocalSample) -> Fraction:
    return {
        "right-center": sample.right - sample.center,
        "center-right": sample.center - sample.right,
        "right-left": sample.right - sample.left,
        "right+center": sample.right + sample.center,
        "center-left": sample.center - sample.left,
        "left-center": sample.left - sample.center,
        "center+left": sample.center + sample.left,
    }[form]


def _fraction_text(value: Fraction | int) -> str:
    fraction = Fraction(value)
    return str(fraction.numerator) if fraction.denominator == 1 else f"{fraction.numerator}/{fraction.denominator}"
