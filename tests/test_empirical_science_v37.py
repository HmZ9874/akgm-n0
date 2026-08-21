import unittest

from akgm_n0.evaluator.empirical_science_v37 import replay_v37_report, run_v37_acceptance


class EmpiricalScienceV37Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_v37_acceptance()

    def test_real_snapshot(self):
        self.assertEqual(self.report["dataset"]["metadata"]["rows"], 53)
        self.assertTrue(self.report["dataset"]["provenance_audit"]["passed"])

    def test_subprocess_and_seal(self):
        audit = self.report["leakage_audit"]
        self.assertTrue(audit["broker_process_isolated"])
        self.assertTrue(audit["holdout_output_before_commit_rejected"])

    def test_expected_anonymous_program(self):
        selected = self.report["discovery"]["selected_program"]
        self.assertEqual((selected["alpha_twice"], selected["beta_twice"]), (3, -1))

    def test_stability(self):
        self.assertEqual(self.report["discovery"]["bootstrap_selection_rate"], 1.0)

    def test_holdout(self):
        self.assertLess(self.report["holdout_audit"]["median_absolute_percentage_error"], 0.15)
        self.assertGreaterEqual(self.report["holdout_audit"]["coverage"], 0.8)

    def test_nulls(self):
        self.assertTrue(self.report["null_audit"]["passed"])

    def test_known_not_novel(self):
        self.assertTrue(self.report["known_law_audit"]["matched"])
        self.assertFalse(self.report["claim_state"]["human_unknown_claim_allowed"])

    def test_derived_value_risk(self):
        self.assertFalse(self.report["discovery_gates"]["independent_measurement_of_all_variables"])

    def test_replay(self):
        self.assertTrue(replay_v37_report(self.report)["passed"])


if __name__ == "__main__":
    unittest.main()
