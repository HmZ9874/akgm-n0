import unittest

from akgm_n0.evaluator.counterexample_transfer_v42 import run_v42_acceptance


class CounterexampleTransferV42Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_v42_acceptance()

    def test_acceptance_passes(self):
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["final_status"], "verified")

    def test_counterexample_is_consumed(self):
        feedback = self.report["counterexample_feedback"]
        self.assertEqual(
            feedback["consumed_failure_id"],
            "V41-CHALLENGE-LATE-LIFE-EXTRAPOLATION",
        )
        self.assertTrue(feedback["resolved_on_reused_archive"])

    def test_labels_are_hidden_from_learner(self):
        protocol = self.report["protocol"]
        self.assertFalse(protocol["human_quantity_names_exposed_to_learner"])
        self.assertFalse(protocol["source_identity_exposed_to_learner"])
        self.assertFalse(protocol["life_stage_exposed_to_learner"])

    def test_created_semantic_wins_validation(self):
        discovery = self.report["discovery"]
        self.assertEqual(discovery["selected"]["kind"], "interaction_fold")
        self.assertLess(
            discovery["selected"]["validation_rmse"],
            discovery["candidate_validation"]["state_fold"]["validation_rmse"],
        )

    def test_commitment_precedes_transfer_reveal(self):
        audit = self.report["preregistration"]
        self.assertTrue(audit["commitment_precedes_programmatic_reveal"])
        self.assertLess(audit["commit_event_index"], audit["transfer_reveal_event_index"])

    def test_all_transfer_stages_are_below_threshold(self):
        audit = self.report["transfer_audit"]
        self.assertTrue(all(audit["stage_passes"].values()))
        for stage in ("early", "middle", "late"):
            self.assertLess(audit["by_life_stage"][stage]["rmse"], 0.10)

    def test_late_transfer_improves_v41(self):
        audit = self.report["transfer_audit"]
        self.assertLess(
            audit["by_life_stage"]["late"]["rmse"],
            audit["frozen_v41_late"]["rmse"],
        )

    def test_claim_boundary_is_enforced(self):
        claim = self.report["claim_state"]
        self.assertTrue(claim["reused_archive_cross_object_transfer_allowed"])
        self.assertFalse(claim["fresh_external_replication_claim_allowed"])
        self.assertFalse(claim["universal_all_life_model_allowed"])
        self.assertFalse(claim["human_unknown_claim_allowed"])


if __name__ == "__main__":
    unittest.main()
