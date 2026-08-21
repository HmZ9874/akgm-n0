"""Run the first multi-task anonymous concept formation experiment."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import HiddenSequenceEnvironment, KnowledgeLedger, SequenceWorldSpec
from akgm_n0.learner import CrossTaskConceptMiner, NextValueProgramSearch


SECRET = b"local-concept-experiment-v0.1"
EXACT_TOLERANCE = 1e-12


def make_observation(parameters: tuple[float, float, float], seed: int):
    spec = SequenceWorldSpec("polynomial2", parameters, 14)
    return HiddenSequenceEnvironment(spec, seed=seed, secret=SECRET).observe(14)


def select_exact(report):
    exact = [
        candidate
        for candidate in report.top_candidates
        if candidate.train_mse <= EXACT_TOLERANCE
        and candidate.validation_mse <= EXACT_TOLERANCE
    ]
    if not exact:
        return None
    return min(exact, key=lambda item: (item.program_nodes, item.candidate_id))


def main() -> int:
    development_worlds = [
        ((1.0, 0.0, 1.0), 104729),
        ((2.0, 3.0, -4.0), 130363),
        ((-1.0, 5.0, 8.0), 155921),
        ((3.0, -2.0, 6.0), 181081),
    ]
    task_programs = {}
    development_results = []
    for task_index, (parameters, seed) in enumerate(development_worlds):
        task_id = f"DEV-{task_index + 1:03d}"
        search_report = NextValueProgramSearch(
            maximum_nodes=7,
            top_k=30,
            complexity_weight=1e-6,
        ).search(make_observation(parameters, seed))
        exact = select_exact(search_report)
        if exact is None:
            raise RuntimeError(f"registered development task has no exact candidate: {task_id}")
        task_programs[task_id] = exact.program
        development_results.append(
            {
                "task_id": task_id,
                "private_evaluator_parameters": list(parameters),
                "programs_generated": search_report.programs_generated,
                "selected_candidate": exact.to_dict(),
            }
        )

    miner = CrossTaskConceptMiner(minimum_support_tasks=3)
    concept_candidates = miner.mine(task_programs)
    if not concept_candidates:
        raise RuntimeError("no concept met the frozen cross-task compression requirements")
    experimental_library = miner.promote(concept_candidates, maximum_entries=1)
    promoted = experimental_library.entries[0]

    held_out_parameters = (4.0, 7.0, -10.0)
    held_out = make_observation(held_out_parameters, 206369)
    deep_without_library = NextValueProgramSearch(
        maximum_nodes=7,
        top_k=30,
        complexity_weight=1e-6,
    ).search(held_out)
    shallow_without_library = NextValueProgramSearch(
        maximum_nodes=5,
        top_k=30,
        complexity_weight=1e-6,
    ).search(held_out)
    shallow_with_library = NextValueProgramSearch(
        maximum_nodes=5,
        top_k=30,
        complexity_weight=1e-6,
        concept_library=experimental_library.definitions(),
    ).search(held_out)

    baseline_exact = select_exact(deep_without_library)
    shallow_baseline_exact = select_exact(shallow_without_library)
    transfer_exact = select_exact(shallow_with_library)
    if baseline_exact is None or transfer_exact is None:
        raise RuntimeError("registered transfer comparison did not produce exact candidates")

    search_cost_reduction = (
        1
        - shallow_with_library.programs_generated
        / deep_without_library.programs_generated
    )
    program_size_reduction = 1 - transfer_exact.program_nodes / baseline_exact.program_nodes
    gates = [
        {
            "gate_id": "cross_task_support",
            "threshold": 3,
            "actual": len(promoted.support_task_ids),
            "passed": len(promoted.support_task_ids) >= 3,
        },
        {
            "gate_id": "positive_description_gain",
            "threshold": 1,
            "actual": promoted.description_gain,
            "passed": promoted.description_gain > 0,
        },
        {
            "gate_id": "minimum_search_cost_reduction",
            "threshold": 0.30,
            "actual": search_cost_reduction,
            "passed": search_cost_reduction >= 0.30,
        },
        {
            "gate_id": "held_out_exact_recovery_with_library",
            "threshold": True,
            "actual": transfer_exact is not None,
            "passed": transfer_exact is not None,
        },
        {
            "gate_id": "noise_stability",
            "threshold": True,
            "actual": None,
            "passed": None,
        },
        {
            "gate_id": "blind_registered_benchmark",
            "threshold": True,
            "actual": None,
            "passed": None,
        },
    ]
    completed_gates = [gate for gate in gates if gate["passed"] is not None]
    verdict = (
        "conditionally_passed"
        if all(gate["passed"] for gate in completed_gates)
        else "failed"
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-concept-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    knowledge_id = ledger.propose(
        promoted.definition,
        parent_ids=("p_read_offset", "p_subtract"),
        provenance={
            "run_id": run_id,
            "miner_version": "cross-task-mdl-v0.1",
            "concept_id": promoted.concept_id,
        },
        evidence={"concept_candidate": promoted.to_dict()},
    )
    ledger.transition(
        knowledge_id,
        "fit_passed",
        reason="cross_task_description_gain_positive",
        evidence={
            "support_task_count": len(promoted.support_task_ids),
            "description_gain": promoted.description_gain,
        },
    )
    ledger.transition(
        knowledge_id,
        "verified",
        reason="held_out_transfer_search_cost_reduced",
        evidence={
            "search_cost_reduction": search_cost_reduction,
            "held_out_validation_mse": transfer_exact.validation_mse,
        },
    )
    ledger.transition(
        knowledge_id,
        "bounded",
        reason="validated_only_within_registered_noiseless_curriculum",
        evidence={
            "pending_gates": [
                gate["gate_id"] for gate in gates if gate["passed"] is None
            ]
        },
    )

    report = {
        "report_version": "concept-experiment-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "Gen 0 匿名概念形成与迁移对照",
        "verdict": verdict,
        "claim_scope": "registered_noiseless_numeric_curriculum_only",
        "architecture": "enumerative_program_search_not_transformer",
        "learner_inputs": {
            "natural_language": False,
            "target_concept_name": False,
            "target_formula": False,
            "readable_offsets": [-1, 0],
            "base_operations": ["p_read_offset", "p_add", "p_subtract", "p_scalar_parameter"],
        },
        "development": {
            "task_count": len(development_results),
            "all_tasks_exactly_solved": True,
            "tasks": development_results,
        },
        "concept": {
            **promoted.to_dict(),
            "knowledge_id": knowledge_id,
            "ledger_status": ledger.get(knowledge_id).status,
        },
        "transfer": {
            "private_evaluator_parameters": list(held_out_parameters),
            "without_library_deep": {
                "maximum_nodes": 7,
                "programs_generated": deep_without_library.programs_generated,
                "exact_candidate": baseline_exact.to_dict(),
            },
            "without_library_shallow": {
                "maximum_nodes": 5,
                "programs_generated": shallow_without_library.programs_generated,
                "exact_candidate_found": shallow_baseline_exact is not None,
            },
            "with_library_shallow": {
                "maximum_nodes": 5,
                "programs_generated": shallow_with_library.programs_generated,
                "exact_candidate": transfer_exact.to_dict(),
            },
            "search_cost_reduction": search_cost_reduction,
            "program_size_reduction": program_size_reduction,
        },
        "gates": gates,
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "概念只在四个开发任务和一个持出任务中验证。",
            "当前任务均为无噪声、完整可观测的合成数字序列。",
            "尚未运行预注册盲评集、随机片段基线和噪声稳定性测试。",
            "匿名原语的人类解释保持为空，当前结果不构成人类新知识。"
        ],
    }
    artifact_path = run_directory / "concept_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

    latest_path = PROJECT_ROOT / "reports" / "data" / "latest.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact_path, latest_path)
    dashboard_data_path = PROJECT_ROOT / "dashboard" / "data" / "latest.json"
    if dashboard_data_path.parent.parent.exists():
        dashboard_data_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact_path, dashboard_data_path)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": verdict,
                "concept_id": promoted.concept_id,
                "knowledge_status": ledger.get(knowledge_id).status,
                "support_task_count": len(promoted.support_task_ids),
                "description_gain": promoted.description_gain,
                "search_cost_reduction": search_cost_reduction,
                "program_size_reduction": program_size_reduction,
                "artifact_path": artifact_path.relative_to(PROJECT_ROOT).as_posix(),
                "dashboard_data": latest_path.relative_to(PROJECT_ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
