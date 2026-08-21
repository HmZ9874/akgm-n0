import unittest

from akgm_n0.evaluator.inertial_response_discovery_v24 import replay_v24_report, run_v24_acceptance


class InertialResponseDiscoveryV24Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v24_acceptance()

    def test_rows_are_opaque(self):
        training = self.acceptance["training"]
        self.assertFalse(training["channel_names_supplied"])
        self.assertFalse(training["formula_supplied"])

    def test_response_program_is_unique_and_anonymous(self):
        discovery = self.acceptance["discovery"]
        self.assertEqual(discovery["response_candidates_generated"], 10)
        selected = discovery["selected_response"]
        self.assertEqual(selected["opaque_program"], "RESP<KEEP,DEN:SEM<D,P>>")
        self.assertIsNone(selected["policy"]["human_operation_name"])

    def test_response_has_universal_proof_and_sealed_transfer(self):
        proof = self.acceptance["proofs"]["response"]
        self.assertTrue(proof["passed"])
        self.assertEqual(len(proof["hidden_replay"]), 5)
        self.assertTrue(all(item["passed"] for item in proof["hidden_replay"]))

    def test_weighted_invariant_is_discovered(self):
        invariant = self.acceptance["discovery"]["selected_invariant"]
        self.assertEqual(invariant["opaque_program"], "MERGE<SEM<q0,q1>,SEM<q2,q3>>")
        self.assertEqual(invariant["changed_channels"], [1, 3])
        self.assertTrue(self.acceptance["proofs"]["weighted_conservation"]["passed"])

    def test_mutations_are_counterexample_rejected(self):
        mutations = self.acceptance["mutation_audits"]
        self.assertEqual(len(mutations), 4)
        self.assertTrue(all(item["rejected"] and item["counterexample"] for item in mutations))

    def test_posthoc_translation_is_honest(self):
        self.assertEqual(self.acceptance["posthoc_translation"]["selected_response"], "a = F/m, equivalently F = m*a")
        self.assertIn("finite structural grammar", " ".join(self.acceptance["limitations"]))

    def test_research_names_are_post_proof_and_scoped(self):
        registry = self.acceptance["research_registry"]
        self.assertFalse(registry["supplied_to_learner"])
        self.assertEqual([item["posthoc_physics_alias"] for item in registry["quantities"]], ["m", "F", "a", "p_total"])
        constant = registry["constant_candidates"][0]
        self.assertEqual(constant["display_symbol"], "κ_IR")
        self.assertEqual(constant["status"], "unit_normalized_constant_candidate")
        self.assertFalse(constant["universal_nature_constant_claimed"])

    def test_full_acceptance_and_replay(self):
        self.assertTrue(self.acceptance["passed"])
        report = {"observed_values": self.acceptance["observed_values"], "discovery": self.acceptance["discovery"]}
        self.assertTrue(replay_v24_report(report)["passed"])


if __name__ == "__main__":
    unittest.main()
