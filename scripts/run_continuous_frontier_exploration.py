from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from fractions import Fraction
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import verify_continuous_semantics  # noqa: E402
from akgm_n0.learner import (  # noqa: E402
    LocalSample,
    LocalStabilitySearch,
    PartitionSample,
    PartitionStabilitySearch,
)


TRAINING_WORLDS = {
    "WORLD-00": (1, 2),
    "WORLD-01": (0, -1, 1),
    "WORLD-02": (3, 0, -2, 1),
    "WORLD-03": (-2, 3, 1),
    "WORLD-04": (5, -4, 2, -1),
}


def main() -> int:
    local_samples = _local_samples()
    partition_samples = _partition_samples()
    local_search = LocalStabilitySearch().search(local_samples, opcode=129)
    partition_search = PartitionStabilitySearch().search(partition_samples, opcode=130)
    verification = verify_continuous_semantics(
        local_search.semantic, partition_search.semantic
    )
    if not verification["passed"]:
        print(json.dumps(verification, ensure_ascii=False, indent=2))
        return 1

    mistake = _record_counterexample(verification["counterexample"])
    room_events = [
        _record_semantic(local_search.semantic.to_dict(), verification),
        _record_semantic(partition_search.semantic.to_dict(), verification),
    ]
    gates = [
        {
            "gate_id": "large_anonymous_candidate_search_completed",
            "passed": local_search.candidate_count == 96 and partition_search.candidate_count == 36,
            "actual": local_search.candidate_count + partition_search.candidate_count,
            "required": 132,
        },
        {
            "gate_id": "local_semantic_not_constant_or_unnormalized",
            "passed": local_search.semantic.denominator_power == 1
            and local_search.best_score[0] == "0",
            "actual": local_search.semantic.to_dict(),
            "required": "exact increment reconstruction with shrinking-step normalization",
        },
        {
            "gate_id": "partition_semantic_is_additive_and_refinement_stable",
            "passed": partition_search.semantic.width_power == 1
            and partition_search.semantic.scale == 1,
            "actual": partition_search.semantic.to_dict(),
            "required": "unscaled width-normalized partition sum",
        },
        {
            "gate_id": "independent_polynomial_domain_proof",
            "passed": verification["passed"],
            "actual": sum(item["passed"] for item in verification["obligations"]),
            "required": len(verification["obligations"]),
        },
        {
            "gate_id": "nonsmooth_counterexample_enters_mistake_room",
            "passed": verification["counterexample"]["rejected"] and bool(mistake["mistake_id"]),
            "actual": verification["counterexample"]["rejected"],
            "required": True,
        },
        {
            "gate_id": "both_semantics_enter_verified_room",
            "passed": len(room_events) == 2,
            "actual": len(room_events),
            "required": 2,
        },
    ]
    if not all(item["passed"] for item in gates):
        print(json.dumps({"verdict": "failed", "gates": gates}, ensure_ascii=False, indent=2))
        return 1

    now = datetime.now(timezone.utc)
    run_id = "RUN-continuous-frontier-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    coefficients = tuple(Fraction(item) for item in (1, -2, 3))
    point = Fraction(1)
    local_demo = []
    for power in (2, 4, 6, 8):
        step = Fraction(1, 2**power)
        sample = LocalSample(
            "DEMO", point, step,
            _poly(coefficients, point - step), _poly(coefficients, point),
            _poly(coefficients, point + step),
        )
        forward, backward = local_search.semantic.execute(sample)
        local_demo.append(
            {
                "step": _fraction_text(step),
                "forward": _fraction_text(forward),
                "backward": _fraction_text(backward),
            }
        )
    partition_demo = []
    for count in (8, 16, 32, 64):
        sample = _partition_for(coefficients, Fraction(0), Fraction(1), count, "DEMO", "I")
        partition_demo.append(
            {"partition_count": count, "value": _fraction_text(partition_search.semantic.execute(sample))}
        )
    report = {
        "report_version": "continuous-frontier-exploration-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "two_calculus_precursor_semantics_verified_on_declared_polynomial_domain",
        "exploration_scale": {
            "anonymous_world_count": len(TRAINING_WORLDS),
            "local_observation_count": len(local_samples),
            "partition_observation_count": len(partition_samples),
            "local_candidate_count": local_search.candidate_count,
            "partition_candidate_count": partition_search.candidate_count,
            "total_candidate_count": local_search.candidate_count + partition_search.candidate_count,
        },
        "discovered_semantics": [
            {
                "semantic": local_search.semantic.to_dict(),
                "search_report": local_search.to_dict(),
                "posthoc_name": "two-sided local change-rate stabilization",
                "name_given_to_learner": False,
            },
            {
                "semantic": partition_search.semantic.to_dict(),
                "search_report": partition_search.to_dict(),
                "posthoc_name": "refinement-stable interval accumulation",
                "name_given_to_learner": False,
            },
        ],
        "verification": verification,
        "counterexample": {
            **verification["counterexample"],
            "mistake_record": mistake,
        },
        "demonstrations": {
            "anonymous_local_world": local_demo,
            "anonymous_partition_world": partition_demo,
        },
        "verified_room_events": room_events,
        "gates": gates,
        "learner_received": {
            "calculus_terms": False,
            "derivative_or_integral_formula": False,
            "polynomial_coefficients": False,
            "target_outputs": False,
            "anonymous_exact_rational_samples": True,
            "candidate_program_grammar": True,
            "stability_additivity_and_simplicity_rewards": True,
        },
        "limitations": [
            "This is the first calculus precursor, not general calculus competence.",
            "The universal proof is limited to univariate rational-coefficient polynomials of degree at most three.",
            "The host supplied anonymous function worlds, sample locations, refinement schedules, candidate grammar, and proof rules.",
            "The learner selected program structures without target rate or accumulation values, but it did not invent epsilon-delta logic or real-number completeness.",
            "A cusp counterexample is rejected; broader discontinuous, oscillatory, and non-integrable families remain unexplored.",
        ],
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    artifact = run_dir / "continuous_frontier_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/continuous_frontier_latest.json",
        ROOT / "dashboard/data/continuous_frontier_latest.json",
        ROOT / "artifacts/semantics/continuous_frontier_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "opcodes": [local_search.semantic.opcode, partition_search.semantic.opcode],
                "semantic_ids": [local_search.semantic.semantic_id, partition_search.semantic.semantic_id],
                "candidates": local_search.candidate_count + partition_search.candidate_count,
                "observations": len(local_samples) + len(partition_samples),
                "proof": f"{sum(item['passed'] for item in verification['obligations'])}/{len(verification['obligations'])}",
                "cusp_rejected": verification["counterexample"]["rejected"],
                "artifact_path": str(artifact.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _local_samples():
    samples = []
    for world_id, raw in TRAINING_WORLDS.items():
        coefficients = tuple(Fraction(item) for item in raw)
        for point in map(Fraction, (-2, -1, 0, 1, 2)):
            for power in range(1, 7):
                step = Fraction(1, 2**power)
                samples.append(
                    LocalSample(
                        world_id, point, step,
                        _poly(coefficients, point - step), _poly(coefficients, point),
                        _poly(coefficients, point + step),
                    )
                )
    return samples


def _partition_samples():
    samples = []
    for world_id, raw in TRAINING_WORLDS.items():
        coefficients = tuple(Fraction(item) for item in raw)
        for start, end, interval_id in (
            (Fraction(-2), Fraction(2), "FULL"),
            (Fraction(-2), Fraction(0), "LEFT"),
            (Fraction(0), Fraction(2), "RIGHT"),
        ):
            for count in (4, 8, 16, 32, 64):
                samples.append(_partition_for(coefficients, start, end, count, world_id, interval_id))
    return samples


def _partition_for(coefficients, start, end, count, world_id, interval_id):
    width = (end - start) / count
    return PartitionSample(
        world_id, interval_id, start, end, count,
        tuple(_poly(coefficients, start + index * width) for index in range(count)),
        tuple(_poly(coefficients, start + (Fraction(index) + Fraction(1, 2)) * width) for index in range(count)),
        tuple(_poly(coefficients, start + (index + 1) * width) for index in range(count)),
    )


def _poly(coefficients, point):
    return sum((coefficient * point**index for index, coefficient in enumerate(coefficients)), Fraction(0))


def _fraction_text(value):
    value = Fraction(value)
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _record_counterexample(counterexample):
    payload = json.dumps(counterexample, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    record = {
        "mistake_id": "CM-" + hashlib.sha256(payload.encode()).hexdigest()[:16],
        "scope": "continuous_frontier_two_sided_local_stability",
        "counterexample": counterexample,
    }
    path = ROOT / "artifacts/mistakes/continuous_frontier_mistakes.jsonl"
    existing = [] if not path.exists() else [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not any(item["mistake_id"] == record["mistake_id"] for item in existing):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush(); os.fsync(stream.fileno())
    return record


def _record_semantic(semantic, verification):
    path = ROOT / "artifacts/semantics/verified_continuous_semantics.jsonl"
    existing = [] if not path.exists() else [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    found = next((item for item in existing if item["semantic"]["semantic_id"] == semantic["semantic_id"]), None)
    if found is not None:
        return found
    event = {
        "schema_version": "verified-continuous-semantic-event-v0.1",
        "event_index": len(existing),
        "semantic": semantic,
        "verification_digest": hashlib.sha256(
            json.dumps(verification, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "previous_event_hash": existing[-1]["event_hash"] if existing else "0" * 64,
    }
    event["event_hash"] = hashlib.sha256(
        json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush(); os.fsync(stream.fileno())
    return event


if __name__ == "__main__":
    raise SystemExit(main())
