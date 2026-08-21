from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator.approximation_frontier_proof import verify_approximation_foundation_semantic  # noqa: E402
from akgm_n0.evaluator.formula_rejection_room import FormulaRejectionRoom  # noqa: E402
from akgm_n0.evaluator.high_school_benchmark_v6 import (  # noqa: E402
    high_school_specs,
    run_high_school_benchmark,
    verify_high_school_report,
)
from akgm_n0.evaluator.high_school_room_v6 import HighSchoolCapabilityRoom  # noqa: E402
from akgm_n0.evaluator.operator_catalog_v5 import verify_operator_catalog_v5_report  # noqa: E402
from akgm_n0.evaluator.ratio_frontier_proof import verify_ratio_foundation_semantic  # noqa: E402
from akgm_n0.evaluator.rational_algebra_proof import verify_rational_algebra_semantic  # noqa: E402
from akgm_n0.evaluator.root_frontier_proof import verify_root_foundation_semantic  # noqa: E402
from akgm_n0.learner.approximation_frontier import ApproximationFoundationSemantic  # noqa: E402
from akgm_n0.learner.high_school_reasoning import compile_high_school_program  # noqa: E402
from akgm_n0.learner.ratio_frontier import RatioFoundationSemantic  # noqa: E402
from akgm_n0.learner.rational_algebra_frontier import RationalAlgebraSemantic  # noqa: E402
from akgm_n0.learner.root_frontier import RootFoundationSemantic  # noqa: E402


def _load(name: str) -> dict:
    return json.loads((ROOT / "reports/data" / name).read_text(encoding="utf-8"))


def audit_prerequisites() -> dict:
    operator_report = _load("operator_catalog_v5_latest.json")["catalog"]
    nested = _load("nested_arithmetic_latest.json")
    strict = _load("strict_parametric_twenty_latest.json")
    ratio_report = _load("autonomous_ratio_latest.json")
    rational_report = _load("autonomous_rational_latest.json")
    root_report = _load("autonomous_exact_root_latest.json")
    interval_report = _load("autonomous_interval_memory_latest.json")
    checks = [
        {"id": "fifty_operator_catalog", "passed": verify_operator_catalog_v5_report(operator_report)["passed"]},
        {"id": "euclidean_quotient_remainder", "passed": all(item["passed"] for item in nested["gates"])},
        {"id": "strict_parametric_formula_room", "passed": all(item["passed"] for item in strict["gates"])},
        {"id": "normalized_ratio", "passed": verify_ratio_foundation_semantic(RatioFoundationSemantic.from_dict(ratio_report["discovery"]["semantic"]))["passed"]},
        {"id": "signed_rational_algebra", "passed": verify_rational_algebra_semantic(RationalAlgebraSemantic.from_dict(rational_report["discovery"]["semantic"]))["passed"]},
        {"id": "exact_rational_root", "passed": verify_root_foundation_semantic(RootFoundationSemantic.from_dict(root_report["discovery"]["semantic"]))["passed"]},
        {"id": "certified_irrational_root_interval", "passed": verify_approximation_foundation_semantic(ApproximationFoundationSemantic.from_dict(interval_report["discovery"]["semantic"]))["passed"]},
    ]
    return {"passed": all(item["passed"] for item in checks), "checks": checks}


def main() -> int:
    prerequisite = audit_prerequisites()
    benchmark = run_high_school_benchmark(prerequisite_audit=prerequisite)
    replay = verify_high_school_report(benchmark)
    if not benchmark["passed"] or not replay["passed"]:
        print(json.dumps({"benchmark": benchmark, "replay": replay}, ensure_ascii=False, indent=2))
        return 1

    success_room = HighSchoolCapabilityRoom(
        ROOT / "artifacts/high_school/v6/success/verified_competencies.jsonl"
    )
    events = [success_room.record(item) for item in benchmark["competencies"]]
    if len(success_room.records) != 20:
        raise ValueError("high-school success room must contain exactly twenty competencies")

    mistake_room = FormulaRejectionRoom(
        ROOT / "artifacts/high_school/v6/mistakes/rejected_compositions.jsonl"
    )
    for spec in high_school_specs():
        task = spec.anonymous_task()
        for mode in range(20):
            if mode == spec.target_mode:
                continue
            program = compile_high_school_program(mode)
            passed = 0
            for row, expected in zip(task.input_rows, task.output_rows, strict=True):
                try:
                    passed += program.execute(row) == expected
                except (ValueError, OverflowError):
                    pass
            mistake_room.record(
                reason="fails_anonymous_high_school_world",
                candidate={"program": program.to_dict(), "task_id": task.task_id},
                evidence={"passed_examples": passed, "example_count": len(task.input_rows), "not_promoted": True},
            )

    now = datetime.now(timezone.utc)
    run_id = "RUN-high-school-core-v6-" + now.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "run_id": run_id,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "verdict": benchmark["level_verdict"],
        "benchmark": benchmark,
        "verification": replay,
        "rooms": {
            "success_path": "artifacts/high_school/v6/success/verified_competencies.jsonl",
            "mistake_path": "artifacts/high_school/v6/mistakes/rejected_compositions.jsonl",
            "success_count": len(success_room.records),
            "mistake_count": len(mistake_room.records),
            "latest_success_hash": events[-1]["event_hash"],
        },
    }
    artifact = run_dir / "high_school_core_v6_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/high_school_core_v6_latest.json",
        ROOT / "dashboard/data/high_school_core_v6_latest.json",
        ROOT / "artifacts/high_school/v6/high_school_core_v6_latest.json",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id,
        "verdict": benchmark["level_verdict"],
        "competencies": f"{benchmark['passed_competency_count']}/{benchmark['competency_count']}",
        "categories": f"{benchmark['passed_category_count']}/{benchmark['category_count']}",
        "prerequisites": f"{sum(x['passed'] for x in prerequisite['checks'])}/{len(prerequisite['checks'])}",
        "success_room": len(success_room.records),
        "mistake_room": len(mistake_room.records),
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
