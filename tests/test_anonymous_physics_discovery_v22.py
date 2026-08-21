import unittest

from akgm_n0.evaluator.anonymous_physics_discovery_v22 import replay_v22_report, run_v22_acceptance


class AnonymousPhysicsDiscoveryV22Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v22_acceptance()

    def test_learner_receives_opaque_channels_and_no_named_law(self):
        self.assertFalse(self.acceptance["training"]["channel_names_supplied"])
        self.assertFalse(self.acceptance["training"]["law_formulas_supplied"])
        self.assertTrue(all(item["human_law_name"] is None for item in self.acceptance["discovery"]["channel_programs"]))

    def test_four_transition_programs_are_discovered(self):
        programs = self.acceptance["discovery"]["channel_programs"]
        self.assertEqual(len(programs), 4)
        self.assertIn("SEM", programs[0]["opaque_program"])
        self.assertIn("MERGE", programs[1]["opaque_program"])
        self.assertEqual(programs[2]["opaque_program"], "q2")
        self.assertEqual(programs[3]["opaque_program"], "q3")

    def test_sealed_multistep_kinematics_replays(self):
        proof = self.acceptance["proofs"]["kinematics"]
        self.assertTrue(proof["passed"])
        self.assertEqual(len(proof["hidden_replay"]), 12)
        self.assertTrue(all(item["passed"] for item in proof["hidden_replay"]))

    def test_dimension_chain_is_inferred_from_programs(self):
        proof = self.acceptance["proofs"]["dimensions"]
        self.assertTrue(proof["passed"])
        self.assertEqual(proof["derived_relation"], "D0=(D2+D3+D3)")
        self.assertFalse(proof["human_basis_given_to_learner"])

    def test_nontrivial_exchange_conservation_is_proven(self):
        invariant = self.acceptance["discovery"]["conservation"]
        self.assertEqual(invariant["opaque_program"], "MERGE<q0,q1>")
        self.assertEqual(invariant["changed_channels"], [0, 1])
        self.assertTrue(self.acceptance["proofs"]["conservation"]["passed"])

    def test_normalization_preserves_and_reduces_directed_values(self):
        proof = self.acceptance["proofs"]["normalization"]
        self.assertTrue(proof["passed"])
        self.assertTrue(all(item["passed"] for item in proof["hidden_replay"]))

    def test_wrong_physics_claims_are_counterexample_rejected(self):
        self.assertEqual(len(self.acceptance["mutation_audits"]), 4)
        self.assertTrue(all(item["rejected"] and item["counterexample"] for item in self.acceptance["mutation_audits"]))

    def test_full_acceptance_and_replay(self):
        self.assertTrue(self.acceptance["passed"])
        report = {"observed_values": self.acceptance["observed_values"], "discovery": self.acceptance["discovery"]}
        self.assertTrue(replay_v22_report(report)["passed"])


if __name__ == "__main__":
    unittest.main()
