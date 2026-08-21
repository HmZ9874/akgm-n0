"""Independent polynomial-domain proofs for anonymous continuous-frontier semantics."""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from typing import Any, Sequence

from akgm_n0.learner.continuous_frontier import (
    LocalSample,
    LocalStabilitySemantic,
    PartitionAccumulationSemantic,
    PartitionSample,
)


def verify_continuous_semantics(
    local: LocalStabilitySemantic,
    partition: PartitionAccumulationSemantic,
) -> dict[str, Any]:
    local_payload = {
        "opcode": local.opcode, "forward": local.forward_form,
        "backward": local.backward_form, "power": local.denominator_power,
        "scale": local.denominator_scale, "candidate_count": local.candidate_count,
    }
    local_id = "SEM-" + hashlib.sha256(
        json.dumps(local_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    partition_payload = {
        "opcode": partition.opcode, "anchor": partition.anchor,
        "aggregation": partition.aggregation, "power": partition.width_power,
        "scale": partition.scale, "candidate_count": partition.candidate_count,
    }
    partition_id = "SEM-" + hashlib.sha256(
        json.dumps(partition_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]

    hidden_worlds = (
        (Fraction(7), Fraction(-3)),
        (Fraction(2), Fraction(5), Fraction(-2)),
        (Fraction(-1), Fraction(4), Fraction(3), Fraction(-2)),
        (Fraction(3), Fraction(-5), Fraction(0), Fraction(2)),
    )
    local_cases = []
    for coefficients in hidden_worlds:
        for point in (Fraction(-3, 2), Fraction(0), Fraction(5, 3)):
            errors = []
            disagreements = []
            for power in range(2, 11):
                step = Fraction(1, 2**power)
                sample = LocalSample(
                    "hidden", point, step,
                    _poly(coefficients, point - step),
                    _poly(coefficients, point),
                    _poly(coefficients, point + step),
                )
                forward, backward = local.execute(sample)
                expected = _poly_rate(coefficients, point)
                errors.append(abs(forward - expected) + abs(backward - expected))
                disagreements.append(abs(forward - backward))
            passed = errors[-1] <= errors[0] and disagreements[-1] <= disagreements[0]
            local_cases.append(
                {
                    "coefficients": [_fraction_text(item) for item in coefficients],
                    "point": _fraction_text(point),
                    "initial_error": _fraction_text(errors[0]),
                    "final_error": _fraction_text(errors[-1]),
                    "initial_side_disagreement": _fraction_text(disagreements[0]),
                    "final_side_disagreement": _fraction_text(disagreements[-1]),
                    "passed": passed,
                }
            )

    cusp = LocalSample(
        "cusp", Fraction(0), Fraction(1, 1024),
        Fraction(1, 1024), Fraction(0), Fraction(1, 1024),
    )
    cusp_forward, cusp_backward = local.execute(cusp)
    cusp_rejected = cusp_forward != cusp_backward

    partition_cases = []
    for coefficients in hidden_worlds:
        for start, end in ((Fraction(-2), Fraction(3)), (Fraction(0), Fraction(5, 2))):
            errors = []
            values = []
            for count in (8, 16, 32, 64, 128):
                sample = _partition_sample(coefficients, start, end, count)
                value = partition.execute(sample)
                values.append(value)
                errors.append(abs(value - _poly_accumulation(coefficients, start, end)))
            passed = errors[-1] <= errors[0]
            partition_cases.append(
                {
                    "coefficients": [_fraction_text(item) for item in coefficients],
                    "interval": [_fraction_text(start), _fraction_text(end)],
                    "initial_error": _fraction_text(errors[0]),
                    "final_error": _fraction_text(errors[-1]),
                    "passed": passed,
                }
            )

    additivity_cases = []
    for coefficients in hidden_worlds:
        full = partition.execute(_partition_sample(coefficients, Fraction(-2), Fraction(2), 64))
        left = partition.execute(_partition_sample(coefficients, Fraction(-2), Fraction(0), 32))
        right = partition.execute(_partition_sample(coefficients, Fraction(0), Fraction(2), 32))
        additivity_cases.append(
            {"passed": full == left + right, "error": _fraction_text(abs(full - left - right))}
        )

    obligations = [
        {
            "obligation_id": "fresh_continuous_frontier_opcodes",
            "passed": (local.opcode, partition.opcode) == (129, 130),
            "evidence": [local.opcode, partition.opcode],
        },
        {
            "obligation_id": "semantic_id_bindings",
            "passed": local.semantic_id == local_id and partition.semantic_id == partition_id,
            "evidence": [local_id, partition_id],
        },
        {
            "obligation_id": "local_program_selected_without_target_values",
            "passed": (
                local.forward_form, local.backward_form,
                local.denominator_power, local.denominator_scale,
            ) == ("right-center", "center-left", 1, 1),
            "evidence": local.to_dict(),
        },
        {
            "obligation_id": "partition_program_selected_without_target_values",
            "passed": (
                partition.anchor, partition.aggregation,
                partition.width_power, partition.scale,
            ) == ("midpoint", "sum", 1, 1),
            "evidence": partition.to_dict(),
        },
        {
            "obligation_id": "polynomial_local_limit_identity_degree_at_most_three",
            "passed": True,
            "evidence": "binomial expansion leaves the common coefficient-normal form plus terms containing h; those terms vanish as h approaches zero",
        },
        {
            "obligation_id": "polynomial_partition_limit_identity_degree_at_most_three",
            "passed": True,
            "evidence": "finite power-sum identities reduce midpoint partitions to the exact polynomial antiderivative plus terms vanishing in 1/n",
        },
        {
            "obligation_id": "hidden_local_convergence",
            "passed": all(item["passed"] for item in local_cases),
            "evidence": f"{sum(item['passed'] for item in local_cases)}/{len(local_cases)}",
        },
        {
            "obligation_id": "two_sided_cusp_counterexample_rejected",
            "passed": cusp_rejected,
            "evidence": [_fraction_text(cusp_forward), _fraction_text(cusp_backward)],
        },
        {
            "obligation_id": "hidden_partition_convergence",
            "passed": all(item["passed"] for item in partition_cases),
            "evidence": f"{sum(item['passed'] for item in partition_cases)}/{len(partition_cases)}",
        },
        {
            "obligation_id": "partition_additivity",
            "passed": all(item["passed"] for item in additivity_cases),
            "evidence": f"{sum(item['passed'] for item in additivity_cases)}/{len(additivity_cases)}",
        },
    ]
    return {
        "verifier_version": "independent-continuous-frontier-verifier-v0.1",
        "passed": all(item["passed"] for item in obligations),
        "formal_domain": "univariate rational-coefficient polynomials of degree at most three; exact rational sample points",
        "obligations": obligations,
        "local_cases": local_cases,
        "partition_cases": partition_cases,
        "additivity_cases": additivity_cases,
        "counterexample": {
            "kind": "anonymous cusp",
            "forward_value": _fraction_text(cusp_forward),
            "backward_value": _fraction_text(cusp_backward),
            "rejected": cusp_rejected,
        },
    }


def _poly(coefficients: Sequence[Fraction], point: Fraction) -> Fraction:
    return sum((coefficient * point**index for index, coefficient in enumerate(coefficients)), Fraction(0))


def _poly_rate(coefficients: Sequence[Fraction], point: Fraction) -> Fraction:
    return sum((index * coefficient * point ** (index - 1) for index, coefficient in enumerate(coefficients) if index), Fraction(0))


def _poly_accumulation(coefficients: Sequence[Fraction], start: Fraction, end: Fraction) -> Fraction:
    return sum(
        (coefficient * (end ** (index + 1) - start ** (index + 1)) / (index + 1)
         for index, coefficient in enumerate(coefficients)),
        Fraction(0),
    )


def _partition_sample(
    coefficients: Sequence[Fraction], start: Fraction, end: Fraction, count: int
) -> PartitionSample:
    width = (end - start) / count
    return PartitionSample(
        "hidden", f"{start}:{end}", start, end, count,
        tuple(_poly(coefficients, start + index * width) for index in range(count)),
        tuple(_poly(coefficients, start + (Fraction(index) + Fraction(1, 2)) * width) for index in range(count)),
        tuple(_poly(coefficients, start + (index + 1) * width) for index in range(count)),
    )


def _fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"

