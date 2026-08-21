from __future__ import annotations

import hashlib
import itertools
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.learner import (  # noqa: E402
    CanonicalExecutor,
    CanonicalFoundationSemantic,
    FiniteMassSemantic,
    JointExecutor,
    JointFoundationSemantic,
    MassExecutor,
    PairedExecutor,
    PairedWeightedSemantic,
    RatioExecutor,
    RatioFoundationSemantic,
    RationalAlgebraSemantic,
    RationalExecutor,
    WeightedExecutor,
    WeightedFoundationSemantic,
    RootExecutor,
    RootFoundationSemantic,
    ApproximationExecutor,
    ApproximationFoundationSemantic,
    canonical_subset_observation,
    exact_rational_boundary,
)


def _load(name: str) -> dict:
    return json.loads((ROOT / "reports/data" / name).read_text(encoding="utf-8"))


def _stage(name: str) -> dict:
    return {"stage": name, "case_count": 0, "passed_count": 0, "counterexamples": []}


def _check(stage: dict, passed: bool, evidence: dict) -> None:
    stage["case_count"] += 1
    stage["passed_count"] += bool(passed)
    if not passed and len(stage["counterexamples"]) < 20:
        stage["counterexamples"].append(evidence)


def main() -> int:
    canonical_report = _load("autonomous_canonicalization_latest.json")
    ratio_report = _load("autonomous_ratio_latest.json")
    mass_report = _load("autonomous_finite_mass_latest.json")
    joint_report = _load("autonomous_joint_latest.json")
    weighted_report = _load("autonomous_weighted_latest.json")
    rational_report = _load("autonomous_rational_latest.json")
    paired_report = _load("autonomous_paired_latest.json")
    root_report = _load("autonomous_exact_root_latest.json")
    interval_report = _load("autonomous_interval_memory_latest.json")
    canonical = CanonicalFoundationSemantic.from_dict(canonical_report["discovery"]["semantic"])
    ratio = RatioFoundationSemantic.from_dict(ratio_report["discovery"]["semantic"])
    mass = FiniteMassSemantic.from_dict(mass_report["derived_discovery"]["semantic"])
    joint = JointFoundationSemantic.from_dict(joint_report["discovery"]["semantic"])
    weighted = WeightedFoundationSemantic.from_dict(weighted_report["discovery"]["semantic"])
    rational = RationalAlgebraSemantic.from_dict(rational_report["discovery"]["semantic"])
    paired = PairedWeightedSemantic.from_dict(paired_report["discovery"]["semantic"])
    root = RootFoundationSemantic.from_dict(root_report["discovery"]["semantic"])
    interval = ApproximationFoundationSemantic.from_dict(interval_report["discovery"]["semantic"])

    stages = []

    result = _stage("order_canonicalization")
    executor = CanonicalExecutor()
    for base_count in range(13):
        base = tuple(f"B{i}" for i in range(base_count))
        for selected_count in range(13):
            control = tuple(f"C{i}" for i in range(selected_count))
            execution = executor.execute(canonical.program, (base, control))
            expected = canonical_subset_observation(base, control)
            _check(
                result,
                execution.halted and execution.output == expected and len(execution.output) == math.comb(base_count, selected_count),
                {"base_count": base_count, "selected_count": selected_count, "output_count": len(execution.output), "expected_count": len(expected)},
            )
    stages.append(result)

    result = _stage("exact_rational_square_boundary")
    executor = RootExecutor()
    for numerator in range(-5, 181):
        for denominator in range(1, 121):
            value_pair = (numerator, denominator)
            expected = exact_rational_boundary(value_pair)
            execution = executor.execute(root.program, value_pair)
            passed = (
                (expected is None and not execution.halted)
                or (expected is not None and execution.halted and execution.output == expected)
            )
            _check(result, passed, {"input": value_pair, "actual_halted": execution.halted, "actual": execution.output, "expected": expected})
    stages.append(result)

    result = _stage("ordered_rational_interval_memory")
    executor = ApproximationExecutor()
    for numerator in range(51):
        for denominator in range(1, 31):
            value = Fraction(numerator, denominator)
            initial_upper = max(Fraction(1), value)
            for rounds in range(13):
                execution = executor.execute(interval.program, (numerator, denominator), rounds)
                lower = Fraction(*execution.lower) if execution.halted else Fraction(0)
                upper = Fraction(*execution.upper) if execution.halted else Fraction(0)
                expected_width = initial_upper / (2 ** rounds)
                passed = execution.halted and lower * lower <= value <= upper * upper and upper - lower == expected_width
                _check(result, passed, {"input": (numerator, denominator), "rounds": rounds, "lower": execution.lower, "upper": execution.upper, "expected_width": str(expected_width)})
    stages.append(result)

    result = _stage("normalized_ratio_representation")
    executor = RatioExecutor()
    for whole in range(1, 251):
        for part in range(251):
            sources = (("p",) * part, ("w",) * whole)
            execution = executor.execute(ratio.program, sources)
            divisor = math.gcd(part, whole)
            expected = (0, 1) if part == 0 else (part // divisor, whole // divisor)
            actual = (len(execution.output_part), len(execution.output_whole))
            _check(result, execution.halted and actual == expected, {"part": part, "whole": whole, "actual": actual, "expected": expected})
    stages.append(result)

    result = _stage("finite_uniform_mass")
    executor = MassExecutor()
    for whole in range(1, 401):
        for event in range(whole + 1):
            execution = executor.execute(mass.program, event, whole)
            expected_fraction = Fraction(event, whole)
            actual_fraction = Fraction(*execution.output_pair) if execution.halted else None
            _check(result, execution.halted and actual_fraction == expected_fraction, {"event": event, "whole": whole, "actual": execution.output_pair, "expected": str(expected_fraction)})
    stages.append(result)

    result = _stage("joint_event_intersection")
    executor = JointExecutor()
    universe = tuple(f"U{i}" for i in range(7))
    subsets = tuple(tuple(universe[index] for index in range(7) if mask & (1 << index)) for mask in range(1 << 7))
    for left in subsets:
        for right in subsets:
            execution = executor.execute(joint.program, universe, (left, right))
            common = set(left) & set(right)
            expected = tuple(item for item in universe if item in common)
            _check(result, execution.halted and execution.output == expected, {"left": left, "right": right, "actual": execution.output, "expected": expected})
    stages.append(result)

    result = _stage("weighted_sum_accumulator")
    executor = WeightedExecutor()
    atoms = tuple(itertools.product(range(13), range(1, 6)))
    records_to_check = [(atom,) for atom in atoms]
    records_to_check.extend((atoms[i % len(atoms)], atoms[(i * 17 + 11) % len(atoms)]) for i in range(len(atoms) * 4))
    records_to_check.extend((atoms[i % len(atoms)], atoms[(i * 7 + 3) % len(atoms)], atoms[(i * 19 + 5) % len(atoms)]) for i in range(len(atoms) * 4))
    for records in records_to_check:
        execution = executor.execute(weighted.program, records)
        expected = sum(value * weight for value, weight in records) / Fraction(sum(weight for _, weight in records))
        actual = Fraction(*execution.output_pair) if execution.halted else None
        _check(result, execution.halted and actual == expected, {"records": records, "actual": execution.output_pair, "expected": str(expected)})
    stages.append(result)

    result = _stage("signed_rational_difference_and_square")
    executor = RationalExecutor()
    rationals = tuple((numerator, denominator) for numerator in range(-12, 13) for denominator in range(1, 13))
    for index, left in enumerate(rationals):
        for right in rationals[index % 11::11]:
            left_value, right_value = Fraction(*left), Fraction(*right)
            difference = executor.execute(rational.difference_program, left, right)
            square = executor.execute(rational.square_program, left, right)
            passed = (
                difference.halted
                and square.halted
                and Fraction(*difference.output) == left_value - right_value
                and Fraction(*square.output) == (left_value - right_value) ** 2
            )
            _check(result, passed, {"left": left, "right": right, "difference": difference.output, "square": square.output})
    stages.append(result)

    result = _stage("paired_weighted_product_accumulator")
    executor = PairedExecutor()
    atoms = tuple(((left, ld), (right, rd), weight) for left in range(-3, 4) for right in range(-3, 4) for ld in range(1, 5) for rd in range(1, 5) for weight in range(1, 4))
    records_to_check = [(atom,) for atom in atoms]
    records_to_check.extend((atoms[i], atoms[(i * 37 + 19) % len(atoms)]) for i in range(0, len(atoms), 2))
    records_to_check.extend((atoms[i], atoms[(i * 17 + 7) % len(atoms)], atoms[(i * 41 + 13) % len(atoms)]) for i in range(0, len(atoms), 3))
    for records in records_to_check:
        execution = executor.execute(paired.program, records)
        expected = sum(Fraction(*left) * Fraction(*right) * weight for left, right, weight in records) / sum(weight for _, _, weight in records)
        actual = Fraction(*execution.output) if execution.halted else None
        _check(result, execution.halted and actual == expected, {"records": records, "actual": execution.output, "expected": str(expected)})
    stages.append(result)

    for stage in stages:
        stage["failed_count"] = stage["case_count"] - stage["passed_count"]
        stage["passed"] = stage["failed_count"] == 0
    total = sum(stage["case_count"] for stage in stages)
    passed = sum(stage["passed_count"] for stage in stages)
    source_runs = [
        canonical_report["run_id"], ratio_report["run_id"], mass_report["run_id"],
        joint_report["run_id"], weighted_report["run_id"], rational_report["run_id"],
        paired_report["run_id"], root_report["run_id"], interval_report["run_id"],
    ]
    now = datetime.now(timezone.utc)
    run_id = "RUN-deep-adversarial-audit-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    report = {
        "report_version": "deep-frontier-adversarial-audit-v0.1",
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": "bounded_exhaustive_domains_passed" if passed == total else "counterexample_found",
        "passed": passed == total,
        "source_runs": source_runs,
        "case_count": total,
        "passed_case_count": passed,
        "failed_case_count": total - passed,
        "stages": stages,
        "proof_scope": "bounded exhaustive and deterministic adversarial replay; supplements but does not replace symbolic obligations",
        "universal_claim": False,
        "audit_hash": hashlib.sha256(json.dumps(stages, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    artifact = run_dir / "deep_frontier_adversarial_audit.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/deep_frontier_adversarial_audit_latest.json",
        ROOT / "dashboard/data/deep_frontier_adversarial_audit_latest.json",
        ROOT / "artifacts/foundation/deep_frontier_adversarial_audit_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({"run_id": run_id, "verdict": report["verdict"], "cases": f"{passed}/{total}", "stages": [{"stage": stage["stage"], "cases": stage["case_count"], "failed": stage["failed_count"]} for stage in stages], "artifact_path": artifact.relative_to(ROOT).as_posix()}, ensure_ascii=True, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
