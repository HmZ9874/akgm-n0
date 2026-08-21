import unittest

from akgm_n0.evaluator.goal_driven_planner_v18 import run_v18_acceptance, sealed_goal_problems
from akgm_n0.learner.cold_start_semantics_v16 import SelfExtendingCounterVM
from akgm_n0.learner.goal_driven_planner_v18 import (
    AnonymousGoalProblemV18,
    GoalDrivenProgramPlannerV18,
)


class GoalDrivenPlannerV18Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v18_acceptance(independent_runs=3, problems_per_run=36)

    def test_sealed_problem_surface_contains_no_solution(self):
        problem = sealed_goal_problems(123, problem_count=1)[0]
        self.assertEqual(set(problem.to_dict()), {"problem_id", "initial_state", "goal_state", "maximum_counter", "family_id"})

    def test_primitive_planner_reaches_an_explicit_goal(self):
        problem = AnonymousGoalProblemV18("TEST", (0, 0), (2, 1), 4, "TEST-F")
        plan = GoalDrivenProgramPlannerV18().plan(problem, SelfExtendingCounterVM(), ())
        self.assertTrue(plan.solved)
        self.assertEqual(plan.final_state, problem.goal_state)

    def test_every_unseen_problem_is_solved_and_replayed(self):
        aggregate = self.acceptance["aggregate"]
        self.assertEqual(aggregate["problem_count"], 108)
        self.assertEqual(aggregate["solved_count"], 108)
        self.assertEqual(aggregate["verified_count"], 108)

    def test_invented_semantics_are_used_and_reduce_tokens(self):
        aggregate = self.acceptance["aggregate"]
        self.assertEqual(aggregate["dynamic_use_problem_count"], aggregate["problem_count"])
        self.assertGreaterEqual(aggregate["improved_problem_count"], 100)
        self.assertGreaterEqual(aggregate["token_reduction"], 0.20)
        self.assertLess(aggregate["learned_tokens"], aggregate["baseline_tokens"])

    def test_full_goal_planner_acceptance(self):
        self.assertTrue(self.acceptance["passed"])
        self.assertTrue(all(item["passed"] for item in self.acceptance["proof_obligations"]))
        self.assertEqual(self.acceptance["aggregate"]["wrong_plans_rejected"], 3)


if __name__ == "__main__":
    unittest.main()

