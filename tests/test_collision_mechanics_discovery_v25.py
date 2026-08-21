import unittest

from akgm_n0.evaluator.collision_mechanics_discovery_v25 import replay_v25_report, run_v25_acceptance


class CollisionMechanicsDiscoveryV25Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v25_acceptance()

    def test_collision_rows_are_anonymous(self):
        self.assertFalse(self.acceptance["training"]["formula_supplied"])
        self.assertFalse(self.acceptance["training"]["physics_names_supplied"])

    def test_two_unique_collision_programs_are_constructed(self):
        discovery = self.acceptance["discovery"]
        self.assertEqual(discovery["candidates_per_output"], 1280)
        self.assertEqual(len(discovery["selected_programs"]), 2)
        self.assertTrue(all(item["policy"]["human_operation_name"] is None for item in discovery["selected_programs"]))

    def test_linear_and_quadratic_invariants_hold(self):
        discovery = self.acceptance["discovery"]
        self.assertEqual(discovery["inherited_linear_invariant"]["opaque_program"], "MERGE<SEM<q0,q1>,SEM<q2,q3>>")
        self.assertEqual(discovery["selected_quadratic_invariant"]["opaque_program"], "MERGE<SEM<q0,SEM<q1,q1>>,SEM<q2,SEM<q3,q3>>>")
        self.assertTrue(self.acceptance["proofs"]["dual_conservation"]["passed"])

    def test_sealed_collisions_replay(self):
        hidden = self.acceptance["proofs"]["collision_programs"]["hidden_replay"]
        self.assertEqual(len(hidden), 4)
        self.assertTrue(all(item["passed"] for item in hidden))

    def test_inelastic_mutation_loses_quadratic_conservation(self):
        mutations = self.acceptance["mutation_audits"]
        self.assertEqual(len(mutations), 4)
        self.assertTrue(all(item["rejected"] and item["counterexample"] for item in mutations))

    def test_research_names_are_post_proof(self):
        registry = self.acceptance["research_registry"]
        self.assertFalse(registry["supplied_to_learner"])
        self.assertEqual([item["research_symbol"] for item in registry["relations"]], ["P_L", "E_Q", "C_E"])

    def test_full_acceptance_and_replay(self):
        self.assertTrue(self.acceptance["passed"])
        report = {"observed_values": self.acceptance["observed_values"], "discovery": self.acceptance["discovery"]}
        self.assertTrue(replay_v25_report(report)["passed"])


if __name__ == "__main__":
    unittest.main()
