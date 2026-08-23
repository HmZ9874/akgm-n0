import unittest

from akgm_n0.evaluator.self_bootstrap_efficiency_v54 import run_v54_acceptance
from akgm_n0.learner.self_bootstrap_efficiency_v54 import EfficiencyPolicyV54


class SelfBootstrapEfficiencyV54Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v54_acceptance()

    def test_frozen_acceptance_passes(self):
        self.assertTrue(self.acceptance["passed"])
        self.assertTrue(all(item["passed"] for item in self.acceptance["proof_obligations"]))

    def test_cache_reduces_real_semantic_computations(self):
        aggregate = self.acceptance["aggregate"]
        self.assertGreaterEqual(aggregate["behavior_execution_reduction"], 0.75)
        self.assertGreaterEqual(aggregate["window_normalization_reduction"], 0.75)
        self.assertGreaterEqual(aggregate["verified_operator_per_window_execution_gain"], 4.0)

    def test_discovery_coverage_is_not_traded_away(self):
        aggregate = self.acceptance["aggregate"]
        self.assertGreaterEqual(aggregate["operator_retention_ratio"], 0.9)
        self.assertLessEqual(aggregate["candidate_world_count"], aggregate["baseline_world_count"])
        self.assertTrue(all(record["candidate"]["verification"]["passed"] for record in self.acceptance["records"]))

    def test_curriculum_budget_is_driven_by_previous_yield(self):
        policy = EfficiencyPolicyV54()
        self.assertEqual(policy.workload_budget(None), (48, "full_evidence_default"))
        self.assertEqual(policy.workload_budget(8), (36, "full_promotion_budget_previous_round"))
        self.assertEqual(policy.workload_budget(7), (48, "full_evidence_default"))

    def test_mutations_and_named_targets_are_rejected(self):
        self.assertTrue(all(item["rejected"] and item["counterexample"] for item in self.acceptance["mutation_audits"]))
        self.assertTrue(all(record["candidate"]["policy"]["named_target_count"] == 0 for record in self.acceptance["records"]))


if __name__ == "__main__":
    unittest.main()
