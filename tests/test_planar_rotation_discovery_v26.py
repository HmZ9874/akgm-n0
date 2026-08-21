import unittest

from akgm_n0.evaluator.planar_rotation_discovery_v26 import replay_v26_report, run_v26_acceptance


class PlanarRotationDiscoveryV26Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v26_acceptance()

    def test_planar_rows_are_anonymous(self):
        self.assertFalse(self.acceptance["training"]["physics_names_supplied"])
        self.assertFalse(self.acceptance["training"]["rotation_formula_supplied"])

    def test_oriented_bilinear_operation_is_unique(self):
        discovery = self.acceptance["discovery"]
        self.assertEqual(discovery["bilinear_candidates_generated"], 81)
        self.assertEqual(discovery["selected_bilinear"]["opaque_program"], "ORB<ZERO,KEEP,TURN,ZERO>")
        self.assertTrue(self.acceptance["proofs"]["oriented_operation"]["passed"])

    def test_mass_weighted_rotation_quantity_is_selected(self):
        quantity = self.acceptance["discovery"]["selected_rotation_quantity"]
        self.assertEqual(quantity["weight_route"], "Q0")
        self.assertEqual(self.acceptance["discovery"]["weight_candidates_generated"], 3)

    def test_central_and_general_hidden_cases_transfer(self):
        proof = self.acceptance["proofs"]["rotation_balance"]
        self.assertTrue(proof["passed"])
        self.assertEqual(len(proof["central_hidden_replay"]), 3)
        self.assertEqual(len(proof["general_hidden_replay"]), 3)
        self.assertTrue(all(item["passed"] for item in proof["central_hidden_replay"] + proof["general_hidden_replay"]))

    def test_mutations_are_rejected(self):
        mutations = self.acceptance["mutation_audits"]
        self.assertEqual(len(mutations), 4)
        self.assertTrue(all(item["rejected"] and item["counterexample"] for item in mutations))

    def test_research_names_are_post_proof(self):
        registry = self.acceptance["research_registry"]
        self.assertFalse(registry["supplied_to_learner"])
        self.assertEqual([item["research_symbol"] for item in registry["relations"]], ["ORB_2", "L_R", "A_J"])

    def test_full_acceptance_and_replay(self):
        self.assertTrue(self.acceptance["passed"])
        report = {"observed_values": self.acceptance["observed_values"], "discovery": self.acceptance["discovery"]}
        self.assertTrue(replay_v26_report(report)["passed"])


if __name__ == "__main__":
    unittest.main()
