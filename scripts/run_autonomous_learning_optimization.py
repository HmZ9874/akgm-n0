from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import AdaptiveMistakeLibrary, UniversalFormulaRoom  # noqa: E402
from akgm_n0.learner import (  # noqa: E402
    AutonomousExperimentLoop,
    DisagreementExperimentPlanner,
    ExperienceGuidedSearch,
    LearnedSearchPolicy,
    MotifExtractor,
    MotifGrowthSearch,
    NumericTableObservation,
    PermutationInvariantSearch,
    ReflectiveExecutor,
    ReflectiveProgram,
    SearchPolicyTrainer,
)


INITIAL_ROWS = (
    (1, 0, 1, 1, 2),
    (1, 0, 3, 2, 4),
)
SEALED_ROWS = (
    (2, 3, 6, 4, 9),
    (4, 4, 2, 3, 5),
    (1, 2, 8, 5, 1),
    (5, 3, 9, 2, 7),
    (3, 5, 4, 2, 6),
)


def hidden_oracle(row):
    q, n, a, p, b = (int(value) for value in row)
    for _ in range(n):
        a, b = b, p * b + q * a
    return float(a)


def mistake_program_values():
    path = ROOT / "artifacts/mistakes/adaptive_mistakes.jsonl"
    return [
        json.loads(line)["program"]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def evaluate(program, rows, executor):
    result = []
    for row in rows:
        predicted = executor.execute(program, row).output_value
        observed = hidden_oracle(row)
        result.append(
            {"inputs": list(row), "predicted": predicted, "observed": observed,
             "passed": predicted == observed}
        )
    return result


def main() -> int:
    strict = UniversalFormulaRoom(
        ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl"
    )
    success_values = [dict(record.program) for record in strict.records]
    reflective_sources = tuple(
        (record.room_record_id, ReflectiveProgram.from_dict(dict(record.program)))
        for record in strict.records
        if record.program.get("substrate") == "anonymous_unified_word_machine_v0.1"
    )
    old_failures = mistake_program_values()
    trainer = SearchPolicyTrainer()
    initial_policy = trainer.train(success_values, old_failures)
    LearnedSearchPolicy.from_dict(initial_policy.to_dict())

    executor = ReflectiveExecutor(maximum_steps=200_000)
    motifs = MotifExtractor().extract(reflective_sources)
    fixed_order_search = MotifGrowthSearch(motifs, top_k=300, executor=executor)
    permutation_search = PermutationInvariantSearch(
        fixed_order_search,
        maximum_width=5,
        top_k=5000,
        candidates_per_permutation=300,
    )
    guided_search = ExperienceGuidedSearch(
        permutation_search, initial_policy, top_k=5000
    )
    active = AutonomousExperimentLoop(
        guided_search,
        planner=DisagreementExperimentPlanner(maximum_candidates=80),
        maximum_rounds=10,
    ).run(
        opaque_task_id="autonomous-learning-optimization",
        initial_rows=INITIAL_ROWS,
        initial_outputs=tuple(hidden_oracle(row) for row in INITIAL_ROWS),
        oracle=hidden_oracle,
        value_pool=(0, 1, 2, 3),
    )
    sealed = evaluate(active.final_candidate.program, SEALED_ROWS, executor)
    if not active.converged or not all(item["passed"] for item in sealed):
        raise RuntimeError("autonomous optimization benchmark did not generalize")

    final_observation = NumericTableObservation.create(
        opaque_session_id="autonomous-optimization-final",
        input_rows=active.input_rows,
        output_values=active.output_values,
        validity_mask=(True,) * len(active.input_rows),
        action_receipt="self_selected_experiment_history",
    )
    baseline = fixed_order_search.search(final_observation).top_candidates[0]
    baseline_sealed = evaluate(baseline.program, SEALED_ROWS, executor)

    mistake_room = AdaptiveMistakeLibrary(
        ROOT / "artifacts/mistakes/adaptive_mistakes.jsonl"
    )
    new_mistake_ids = []
    final_candidates = guided_search.search(final_observation).top_candidates
    for candidate in final_candidates:
        if candidate.candidate_id == active.final_candidate.candidate_id:
            continue
        failures = [
            item
            for item in evaluate(candidate.program, active.input_rows + SEALED_ROWS, executor)
            if not item["passed"]
        ]
        if not failures:
            continue
        record = mistake_room.record(
            candidate.program,
            failed_scope="autonomous_shuffled_input_learning",
            condition_key="five_anonymous_columns_no_stable_roles",
            counterexamples=failures[:5],
            source_candidate_id=candidate.candidate_id,
        )
        new_mistake_ids.append(record.mistake_id)
        if len(new_mistake_ids) == 10:
            break

    new_failures = mistake_program_values()
    updated_policy = trainer.train(success_values, new_failures)
    if updated_policy.policy_id == initial_policy.policy_id:
        raise RuntimeError("new counterexamples did not update learned policy")
    policy_path = ROOT / "artifacts/policies/learned_search_policy.json"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(
        json.dumps(updated_policy.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    reloaded = LearnedSearchPolicy.from_dict(
        json.loads(policy_path.read_text(encoding="utf-8"))
    )
    if reloaded.policy_id != updated_policy.policy_id:
        raise RuntimeError("persisted learned policy did not replay")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = "RUN-autonomous-learning-" + stamp
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    report = {
        "report_version": "autonomous-learning-optimization-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verdict": "experience_policy_active_experiments_and_permutation_transfer_passed",
        "policy": {
            "initial_policy_id": initial_policy.policy_id,
            "updated_policy_id": updated_policy.policy_id,
            "success_example_count": updated_policy.success_example_count,
            "failure_example_count_before": len(old_failures),
            "failure_example_count_after": len(new_failures),
            "feature_count": len(updated_policy.feature_weights),
            "new_mistake_ids": new_mistake_ids,
            "policy_path": str(policy_path.relative_to(ROOT)),
            "replay_passed": True,
        },
        "blind_task": {
            "input_width": 5,
            "input_permutations_searched": 120,
            "learner_received_role_names": False,
            "learner_received_column_mapping": False,
            "host_seed_observation_count": len(INITIAL_ROWS),
            "self_selected_experiment_count": len(active.input_rows) - len(INITIAL_ROWS),
            "total_observation_count": len(active.input_rows),
            "active_rounds": [item.to_dict() for item in active.rounds],
            "selected_rows": [list(row) for row in active.input_rows[len(INITIAL_ROWS):]],
            "posthoc_column_mapping": {
                "column_0": "q", "column_1": "n", "column_2": "a",
                "column_3": "p", "column_4": "b",
            },
        },
        "winner": active.final_candidate.to_dict(),
        "sealed_results": sealed,
        "gates": [
            {
                "gate_id": "self_selected_queries_exist",
                "passed": len(active.input_rows) > len(INITIAL_ROWS),
                "actual": len(active.input_rows) - len(INITIAL_ROWS),
                "threshold": 1,
            },
            {
                "gate_id": "shuffled_input_unseen_exact",
                "passed": all(item["passed"] for item in sealed),
                "actual": sum(item["passed"] for item in sealed),
                "threshold": len(sealed),
            },
            {
                "gate_id": "fixed_order_baseline_fails_transfer",
                "passed": not all(item["passed"] for item in baseline_sealed),
                "actual": sum(item["passed"] for item in baseline_sealed),
                "threshold": len(baseline_sealed),
            },
            {
                "gate_id": "new_mistakes_update_policy",
                "passed": updated_policy.policy_id != initial_policy.policy_id,
                "actual": updated_policy.policy_id,
                "threshold": "different_from_" + initial_policy.policy_id,
            },
        ],
        "baseline": {
            "kind": "same_motif_search_without_input_permutation_wrapper",
            "candidate_id": baseline.candidate_id,
            "sealed_results": baseline_sealed,
        },
        "limitations": [
            "The underlying candidate family remains the learned-motif recurrence generator.",
            "Full permutation enumeration is factorial and currently capped at six columns.",
            "The active learner queries a finite value pool; larger or continuous domains require a learned proposal distribution.",
            "Experience weights are transparent log-odds features, not yet a neural or differentiable search policy.",
        ],
    }
    if not all(gate["passed"] for gate in report["gates"]):
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    artifact = run_dir / "autonomous_learning_optimization_report.json"
    artifact.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for destination in (
        ROOT / "reports/data/autonomous_learning_optimization_latest.json",
        ROOT / "dashboard/data/autonomous_learning_optimization_latest.json",
    ):
        shutil.copyfile(artifact, destination)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "initial_policy": initial_policy.policy_id,
                "updated_policy": updated_policy.policy_id,
                "experience": f"{updated_policy.success_example_count} success / {updated_policy.failure_example_count} failure",
                "self_selected_experiments": len(active.input_rows) - len(INITIAL_ROWS),
                "total_observations": len(active.input_rows),
                "sealed": f"{sum(item['passed'] for item in sealed)}/{len(sealed)}",
                "baseline_sealed": f"{sum(item['passed'] for item in baseline_sealed)}/{len(baseline_sealed)}",
                "new_mistakes": len(new_mistake_ids),
                "artifact_path": str(artifact.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
