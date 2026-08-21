import unittest

from akgm_n0.evaluator.nasa_blind_challenge_v41 import run_v41_blind_challenge


class NasaBlindChallengeV41Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_v41_blind_challenge()

    def test_protocol_completed(self):
        self.assertTrue(self.report["challenge_complete"])
        self.assertEqual(self.report["final_status"], "bounded")

    def test_frozen_before_challenge(self):
        audit = self.report["provenance_audit"]
        self.assertTrue(audit["passed"])
        self.assertTrue(audit["frozen_program_precedes_challenge"])
        self.assertFalse(audit["program_refit_allowed"])

    def test_unseen_cells_and_stages(self):
        audit = self.report["provenance_audit"]
        self.assertEqual(audit["trace_count"], 120)
        self.assertEqual(audit["cell_counts"], {"RW5": 60, "RW6": 60})
        self.assertEqual(audit["stage_counts"], {"early": 40, "middle": 40, "late": 40})

    def test_state_fold_remains_best(self):
        self.assertTrue(self.report["performance_audit"]["state_fold_best_overall"])

    def test_initial_state_matters(self):
        self.assertGreater(self.report["performance_audit"]["state_corruption_rmse_ratio"], 1.5)

    def test_early_and_middle_generalize(self):
        audit = self.report["performance_audit"]
        self.assertTrue(audit["early_stage_passed"])
        self.assertTrue(audit["middle_stage_passed"])

    def test_late_life_fails(self):
        audit = self.report["performance_audit"]
        self.assertFalse(audit["late_stage_passed"])
        self.assertFalse(self.report["universal_pass"])

    def test_counterexample_restricts_scope(self):
        failure = self.report["counterexample"]
        self.assertTrue(failure["universal_formula_removed"])
        self.assertGreater(failure["observed_rmse"], failure["expected_max_rmse"])

    def test_claim_boundary(self):
        claim = self.report["claim_state"]
        self.assertTrue(claim["early_middle_dynamic_model_allowed"])
        self.assertFalse(claim["all_life_dynamic_model_allowed"])
        self.assertFalse(claim["human_unknown_claim_allowed"])


if __name__ == "__main__":
    unittest.main()
