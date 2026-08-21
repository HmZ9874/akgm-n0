import os
import unittest

from akgm_n0.evaluator.live_randomized_science_v39 import run_v39_acceptance


class LiveRandomizedScienceV39Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_v39_acceptance()

    def test_live_independent_apparatus(self):
        self.assertTrue(self.report["discovery_gates"]["live_new_measurements"])
        self.assertNotEqual(self.report["apparatus"]["primary"]["broker_pid"], os.getpid())

    def test_adaptive_plans(self):
        audit = self.report["adaptive_experiment_audit"]
        self.assertEqual(audit["round_count"], 3)
        self.assertTrue(audit["later_rounds_use_model_disagreement"])

    def test_randomized_commitments(self):
        audit = self.report["randomization_and_commitment_audit"]
        self.assertTrue(audit["all_committed_before_measurement"])
        self.assertTrue(audit["all_multi_level_orders_randomized"])

    def test_scale_law_competition(self):
        competition = self.report["model_competition"]
        self.assertEqual(competition["candidate_count"], 9)
        self.assertTrue(competition["selected_beats_boundary_nulls"])
        self.assertLessEqual(abs(competition["selected"]["exponent_quarters"] / 4 - 2), 0.25)

    def test_prospective_holdout(self):
        holdout = self.report["prospective_holdout_audit"]
        self.assertTrue(holdout["commitment_precedes_measurement"])
        self.assertTrue(holdout["passed"])

    def test_new_process_replication(self):
        replication = self.report["new_process_replication_audit"]
        self.assertTrue(replication["new_process"])
        self.assertTrue(replication["passed"])

    def test_timing_noise(self):
        noise = self.report["timing_noise_audit"]
        self.assertEqual(noise["measurement_count"], 10)
        self.assertTrue(noise["passed"])

    def test_protocol_mutations(self):
        self.assertEqual(len(self.report["mutation_audits"]), 5)
        self.assertTrue(all(item["rejected"] for item in self.report["mutation_audits"]))

    def test_claim_boundary(self):
        self.assertTrue(self.report["passed"])
        self.assertFalse(self.report["claim_state"]["natural_science_discovery_claim_allowed"])
        self.assertFalse(self.report["claim_state"]["human_unknown_claim_allowed"])


if __name__ == "__main__":
    unittest.main()
