import unittest

from akgm_n0.evaluator.official_dynamic_science_v41 import run_v41_acceptance


class OfficialDynamicScienceV41Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_v41_acceptance()

    def test_official_provenance(self):
        self.assertTrue(self.report["dataset"]["provenance_audit"]["passed"])
        self.assertEqual(self.report["dataset"]["provenance_audit"]["provider"], "NASA Ames Prognostics Center of Excellence")

    def test_trace_partitions(self):
        counts = self.report["dataset"]["provenance_audit"]["partition_counts"]
        self.assertEqual(counts, {"training": 40, "validation": 20, "future_holdout": 20, "cross_cell_replication": 20})

    def test_archive_seal(self):
        self.assertTrue(self.report["discovery_gates"]["separate_sealed_archive_process"])
        self.assertTrue(self.report["preregistration"]["commitment_precedes_reveal"])

    def test_domain_blind(self):
        self.assertTrue(self.report["discovery_gates"]["domain_blind_channels"])
        self.assertFalse(self.report["dataset"]["provenance_audit"]["learner_received_translation"])

    def test_history_counterexample(self):
        audit = self.report["history_dependence_audit"]
        self.assertTrue(audit["passed"])
        self.assertGreater(audit["response_difference"], 0.1)

    def test_state_fold_selected(self):
        selected = self.report["discovery"]["selected"]
        self.assertEqual(selected["created_operator"], "STATE_FOLD")
        self.assertFalse(selected["domain_formula_supplied"])

    def test_state_beats_no_memory(self):
        self.assertLess(self.report["discovery"]["stateful_to_stateless_rmse_ratio"], 0.6)

    def test_future_trajectory(self):
        audit = self.report["future_trajectory_audit"]
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["trace_count"], 20)

    def test_cross_cell_replication(self):
        audit = self.report["cross_cell_replication_audit"]
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["trace_count"], 20)

    def test_claim_boundary(self):
        claim = self.report["claim_state"]
        self.assertTrue(claim["official_dynamic_archive_discovery_verified"])
        self.assertFalse(claim["live_physical_experiment_claim_allowed"])
        self.assertFalse(claim["human_unknown_claim_allowed"])


if __name__ == "__main__":
    unittest.main()
