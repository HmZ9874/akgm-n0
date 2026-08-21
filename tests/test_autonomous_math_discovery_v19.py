import unittest

from akgm_n0.evaluator.autonomous_math_discovery_v19 import (
    replay_v19_report,
    run_v19_acceptance,
)
from akgm_n0.learner.autonomous_math_discovery_v19 import TargetFreeMathematicalResearchV19


class AutonomousMathDiscoveryV19Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v19_acceptance()

    def test_target_free_search_and_anonymous_surface(self):
        discovery = self.acceptance["discovery"]
        self.assertEqual(discovery["programs_generated"], 4608)
        self.assertFalse(discovery["human_operation_name_given_during_search"])

    def test_surviving_conjectures_have_universal_proofs(self):
        proofs = self.acceptance["theorem_proofs"]
        self.assertGreaterEqual(len(proofs), 20)
        self.assertTrue(all(item["passed"] for item in proofs))
        self.assertTrue(all(not item["finite_probe_is_proof"] for item in proofs))

    def test_wrong_conjectures_are_counterexample_rejected(self):
        rejected = self.acceptance["rejected_conjectures"]
        self.assertGreaterEqual(len(rejected), 20)
        self.assertTrue(all(item["rejected"] and item["counterexample"] for item in rejected))

    def test_input_sequence_induces_factor_concept_without_next_term(self):
        concept = self.acceptance["induced_concept"]
        self.assertEqual(concept["source_partition"]["boundary"], [1])
        self.assertEqual(concept["source_partition"]["no_internal_witness"], [3, 5, 7, 11, 13, 17])
        self.assertIn(19, concept["generated_no_internal_witness"])

    def test_discovery_is_deterministic_and_replayable(self):
        rerun = TargetFreeMathematicalResearchV19().discover((1, 3, 5, 7, 11, 13, 17))
        report = {"observed_values": [1, 3, 5, 7, 11, 13, 17], "discovery": self.acceptance["discovery"]}
        self.assertEqual(rerun.programs_generated, report["discovery"]["programs_generated"])
        self.assertTrue(replay_v19_report(report)["passed"])

    def test_full_acceptance(self):
        self.assertTrue(self.acceptance["passed"])
        self.assertTrue(all(item["passed"] for item in self.acceptance["proof_obligations"]))


if __name__ == "__main__":
    unittest.main()
