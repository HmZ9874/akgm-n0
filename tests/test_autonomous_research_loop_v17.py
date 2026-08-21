import unittest

from akgm_n0.evaluator.autonomous_research_loop_v17 import run_v17_acceptance
from akgm_n0.learner.autonomous_research_loop_v17 import (
    AutonomousResearchLoopV17,
    AutonomousWorldFactoryV17,
    KnowledgeGapAnalyzerV17,
)


class AutonomousResearchLoopV17Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v17_acceptance(independent_runs=5)

    def test_empty_registry_generates_its_own_first_gap_and_world(self):
        gap = KnowledgeGapAnalyzerV17().inspect(())
        factory = AutonomousWorldFactoryV17()
        plan = factory.plan(gap, round_index=0, seed=123)
        worlds = factory.generate(plan, seed=123)
        self.assertTrue(worlds)
        self.assertEqual(plan.gap_id, gap.gap_id)
        self.assertEqual(plan.focus_transition, gap.focus_transition)
        self.assertEqual(plan.target_arity, gap.target_arity)

    def test_research_direction_changes_after_learning(self):
        for run in self.acceptance["runs"]:
            self.assertGreaterEqual(run["distinct_gap_count"], 4)
            self.assertTrue(run["causality_audit"]["passed"])

    def test_loop_stops_from_saturation_not_safety_cap(self):
        for run in self.acceptance["runs"]:
            self.assertEqual(run["stop_reason"], "semantic_saturation")
            self.assertLess(run["round_count"], run["maximum_rounds"])
            self.assertTrue(all(item["new_operator_count"] == 0 for item in run["rounds"][-run["patience"]:]))

    def test_all_discovered_semantics_are_independently_verified(self):
        self.assertTrue(all(run["operator_verification"]["passed"] for run in self.acceptance["runs"]))
        self.assertGreaterEqual(self.acceptance["aggregate"]["certificate_cases"], 10_000)
        self.assertEqual(self.acceptance["aggregate"]["mutations_rejected"], 5)

    def test_full_autonomous_research_acceptance(self):
        self.assertTrue(self.acceptance["passed"])
        self.assertTrue(all(item["passed"] for item in self.acceptance["proof_obligations"]))
        self.assertEqual(self.acceptance["aggregate"]["saturation_stops"], 5)
        self.assertGreaterEqual(self.acceptance["aggregate"]["minimum_operators_per_run"], 30)


if __name__ == "__main__":
    unittest.main()

