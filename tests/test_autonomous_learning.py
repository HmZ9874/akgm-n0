from __future__ import annotations

import json
import unittest
from pathlib import Path

from akgm_n0.evaluator import UniversalFormulaRoom
from akgm_n0.learner import (
    AutonomousExperimentLoop,
    DisagreementExperimentPlanner,
    LearnedSearchPolicy,
    MotifExtractor,
    MotifGrowthSearch,
    PermutationInvariantSearch,
    ReflectiveExecutor,
    ReflectiveProgram,
    SearchPolicyTrainer,
)


ROOT = Path(__file__).resolve().parents[1]


def hidden_from_shuffled(row):
    q, n, a, p, b = (int(value) for value in row)
    for _ in range(n):
        a, b = b, p * b + q * a
    return float(a)


class AutonomousLearningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        room = UniversalFormulaRoom(
            ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl"
        )
        cls.success_values = [dict(record.program) for record in room.records]
        cls.reflective_sources = tuple(
            (record.room_record_id, ReflectiveProgram.from_dict(dict(record.program)))
            for record in room.records
            if record.program.get("substrate") == "anonymous_unified_word_machine_v0.1"
        )
        cls.failure_values = [
            json.loads(line)["program"]
            for line in (ROOT / "artifacts/mistakes/adaptive_mistakes.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]

    def test_success_and_mistake_rooms_train_reloadable_policy(self) -> None:
        policy = SearchPolicyTrainer().train(self.success_values, self.failure_values)
        replay = LearnedSearchPolicy.from_dict(policy.to_dict())
        success = ReflectiveProgram.from_dict(self.success_values[0])
        failure_value = next(
            item
            for item in self.failure_values
            if item.get("substrate") == "anonymous_unified_word_machine_v0.1"
        )
        failure = ReflectiveProgram.from_dict(failure_value)
        self.assertEqual(policy.policy_id, replay.policy_id)
        self.assertGreater(replay.score(success), replay.score(failure))
        self.assertEqual(replay.success_example_count, len(self.success_values))
        self.assertEqual(replay.failure_example_count, len(self.failure_values))

    def test_shuffled_columns_are_recovered_by_self_selected_experiments(self) -> None:
        motifs = MotifExtractor().extract(self.reflective_sources)
        executor = ReflectiveExecutor(maximum_steps=200_000)
        base = MotifGrowthSearch(motifs, top_k=300, executor=executor)
        search = PermutationInvariantSearch(
            base, maximum_width=5, top_k=5000, candidates_per_permutation=300
        )
        initial_rows = (
            (1, 0, 1, 1, 2),
            (1, 0, 3, 2, 4),
        )
        report = AutonomousExperimentLoop(
            search,
            planner=DisagreementExperimentPlanner(maximum_candidates=80),
            maximum_rounds=10,
        ).run(
            opaque_task_id="shuffled-five-column-active-learning",
            initial_rows=initial_rows,
            initial_outputs=tuple(hidden_from_shuffled(row) for row in initial_rows),
            oracle=hidden_from_shuffled,
            value_pool=(0, 1, 2, 3),
        )
        self.assertTrue(report.converged)
        self.assertGreater(len(report.input_rows), len(initial_rows))
        self.assertTrue(
            all(
                item.proposed_experiment is None
                or item.proposed_experiment.disagreeing_candidate_pairs >= 0
                for item in report.rounds
            )
        )
        sealed = (
            (2, 3, 6, 4, 9),
            (4, 4, 2, 3, 5),
            (1, 2, 8, 5, 1),
            (5, 3, 9, 2, 7),
        )
        for row in sealed:
            self.assertEqual(
                executor.execute(report.final_candidate.program, row).output_value,
                hidden_from_shuffled(row),
            )

    def test_latest_optimization_report_and_updated_policy_replay(self) -> None:
        report = json.loads(
            (ROOT / "reports/data/autonomous_learning_optimization_latest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(all(gate["passed"] for gate in report["gates"]))
        self.assertNotEqual(
            report["policy"]["initial_policy_id"],
            report["policy"]["updated_policy_id"],
        )
        self.assertEqual(report["blind_task"]["self_selected_experiment_count"], 2)
        self.assertEqual(sum(item["passed"] for item in report["sealed_results"]), 5)
        self.assertEqual(
            sum(item["passed"] for item in report["baseline"]["sealed_results"]), 1
        )
        policy = LearnedSearchPolicy.from_dict(
            json.loads(
                (ROOT / "artifacts/policies/learned_search_policy.json").read_text(
                    encoding="utf-8"
                )
            )
        )
        self.assertEqual(policy.policy_id, report["policy"]["updated_policy_id"])


if __name__ == "__main__":
    unittest.main()
