from __future__ import annotations

import copy
import os
import unittest

from akgm_n0.evaluator.autonomous_intervention_v45 import (
    run_v45_acceptance,
    verify_v45_acceptance,
)


class AutonomousInterventionV45Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_v45_acceptance()

    def test_acceptance_passes(self):
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["final_status"], "verified")

    def test_apparatus_is_a_separate_process(self):
        boundary = self.report["apparatus_boundary"]
        self.assertTrue(boundary["separate_process"])
        self.assertNotEqual(boundary["primary_pid"], os.getpid())
        self.assertNotEqual(boundary["primary_pid"], boundary["replica_pid"])

    def test_model_selects_initial_and_adaptive_interventions(self):
        design = self.report["autonomous_experiment_design"]
        self.assertFalse(design["host_selected"])
        self.assertEqual(design["plans"][0]["kind"], "geometry_without_prior_response")
        self.assertGreaterEqual(len(design["plans"]), 3)
        self.assertTrue(all(item["host_selected"] is False for item in design["plans"]))

    def test_safety_and_randomized_commitments(self):
        gates = self.report["discovery_gates"]
        self.assertTrue(gates["safe_action_broker_rejects_invalid_intervention"])
        self.assertTrue(gates["all_batches_committed_before_execution"])
        self.assertTrue(gates["multi_action_order_randomized"])

    def test_language_discovers_interaction_and_guard(self):
        growth = self.report["language_growth"]
        self.assertEqual(growth["initial_features"], ["ONE"])
        self.assertEqual(
            growth["selected_mutations"],
            [
                "admit_structural_feature:COUPLE(0,1,2)",
                "admit_structural_feature:GUARD(0,1,0)",
            ],
        )

    def test_autonomous_stop_requires_three_sterile_rounds(self):
        design = self.report["autonomous_experiment_design"]
        rounds = self.report["language_growth"]["rounds"]
        self.assertEqual(design["stop_reason"], "semantic_saturation")
        self.assertEqual(rounds[-1]["sterile_round_count"], 3)

    def test_program_is_committed_before_transfer(self):
        registration = self.report["preregistration"]
        self.assertTrue(registration["commitment_precedes_transfer"])
        self.assertLess(registration["commit_event_index"], registration["transfer_event_index"])

    def test_frozen_program_predicts_all_sealed_actions(self):
        audit = self.report["sealed_counterfactual_audit"]
        self.assertGreater(audit["case_count"], 10)
        self.assertLess(audit["rmse"], 1e-8)

    def test_each_assigned_control_has_a_causal_effect(self):
        controls = self.report["causal_effect_audit"]["essential_controls"]
        self.assertEqual(len(controls), 3)
        self.assertTrue(all(item["essential_effect_observed"] for item in controls))

    def test_mistake_room_retains_rejected_structures(self):
        self.assertTrue(self.report["mistake_room"]["rejected_structural_features"])

    def test_independent_replay_rejects_tampering(self):
        self.assertTrue(verify_v45_acceptance(self.report)["passed"])
        forged = copy.deepcopy(self.report)
        forged["language_growth"]["selected_program"]["coefficients"][0] += 1.0
        self.assertFalse(verify_v45_acceptance(forged)["passed"])

    def test_natural_and_full_autonomy_claims_remain_blocked(self):
        claims = self.report["claim_state"]
        self.assertTrue(claims["autonomous_intervention_design_allowed"])
        self.assertTrue(claims["autonomous_safe_execution_allowed"])
        self.assertFalse(claims["natural_physical_causal_law_allowed"])
        self.assertFalse(claims["external_laboratory_replication_allowed"])
        self.assertFalse(claims["human_unknown_law_allowed"])
        self.assertFalse(claims["fully_autonomous_scientist_allowed"])


if __name__ == "__main__":
    unittest.main()
