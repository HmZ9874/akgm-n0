from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.learner import (
    NumericExperimentPlanner,
    relation_add,
    relation_constant,
    relation_value,
)


class NumericExperimentPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        value = relation_value()
        self.hypotheses = (
            value,
            relation_add(value, value),
            relation_constant(1),
        )

    def test_selects_action_that_separates_all_competing_programs(self) -> None:
        plan = NumericExperimentPlanner().choose(
            self.hypotheses,
            action_candidates=(0, 1, 2),
        )

        self.assertEqual(plan.selected.action, 2.0)
        self.assertAlmostEqual(plan.selected.information_gain_bits, 1.5849625)
        self.assertEqual(len(plan.selected.prediction_groups), 3)

    def test_excludes_actions_that_have_already_been_observed(self) -> None:
        plan = NumericExperimentPlanner().choose(
            self.hypotheses,
            action_candidates=(0, 1, 2),
            observed_actions=(2,),
        )

        self.assertNotEqual(plan.selected.action, 2.0)
        self.assertEqual(plan.excluded_observed_actions, (2.0,))

    def test_numeric_feedback_rejects_inconsistent_hypotheses(self) -> None:
        planner = NumericExperimentPlanner()
        update = planner.update(
            self.hypotheses,
            action=2,
            observed_value=4,
        )

        self.assertEqual(len(update.retained_candidate_ids), 1)
        self.assertEqual(len(update.rejected_candidate_ids), 2)
        retained_prediction = [
            item for item in update.predictions if item[0] in update.retained_candidate_ids
        ]
        self.assertEqual(retained_prediction[0][1], 4.0)

    def test_invalid_action_cost_is_rejected(self) -> None:
        planner = NumericExperimentPlanner(action_cost=lambda _action: 0)

        with self.assertRaises(ValueError):
            planner.choose(self.hypotheses, action_candidates=(2,))


if __name__ == "__main__":
    unittest.main()
