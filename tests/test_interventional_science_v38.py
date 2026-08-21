import unittest

from akgm_n0.evaluator.interventional_science_v38 import replay_v38_report, run_v38_acceptance


class InterventionalScienceV38Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_v38_acceptance()

    def test_nist_snapshot(self):
        self.assertEqual(self.report["dataset"]["metadata"]["rows"], 40)
        self.assertTrue(self.report["dataset"]["provenance_audit"]["passed"])

    def test_separate_sealed_broker(self):
        self.assertTrue(self.report["discovery_gates"]["separate_data_process"])
        self.assertTrue(self.report["discovery_gates"]["commit_before_second_batch"])

    def test_direction(self):
        self.assertEqual(self.report["direction_audit"]["selected_graph"], "Q0_TO_Q1")
        self.assertFalse(self.report["direction_audit"]["observational_fit_alone_determines_direction"])

    def test_quadratic_mechanism(self):
        self.assertEqual(self.report["discovery"]["selected_mechanism"]["degree"], 2)
        self.assertGreater(self.report["discovery"]["bic_margin"], 0)

    def test_unseen_interventions(self):
        future = self.report["future_batch_audit"]
        self.assertEqual(future["unseen_intervention_count"], 10)
        self.assertTrue(future["passed"])

    def test_repeatability_and_shape(self):
        self.assertEqual(self.report["repeatability_audit"]["paired_levels"], 20)
        self.assertTrue(self.report["shape_certificate"]["passed"])

    def test_mutations(self):
        self.assertTrue(all(item["rejected"] for item in self.report["mutation_audits"]))

    def test_drift_gate(self):
        self.assertFalse(self.report["discovery_gates"]["randomized_intervention_order"])
        self.assertFalse(self.report["claim_state"]["clean_causal_effect_claim_allowed"])

    def test_replay(self):
        self.assertTrue(replay_v38_report(self.report)["passed"])


if __name__ == "__main__":
    unittest.main()
