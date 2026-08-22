from __future__ import annotations

import copy
import unittest

from akgm_n0.evaluator.event_world_semantic_search_v49 import (
    run_v49_acceptance,
    verify_v49_acceptance,
)


class EventWorldSemanticSearchV49Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v49_acceptance()

    def test_acceptance_passes(self):
        self.assertTrue(self.acceptance["passed"])
        self.assertTrue(all(item["passed"] for item in self.acceptance["proof_obligations"]))

    def test_failed_world_is_selected_from_v48(self):
        task = self.acceptance["task_selection"]
        self.assertTrue(task["selected_from_v48_failure"])
        self.assertFalse(task["host_selected"])

    def test_anonymous_search_exhausts_finite_resources(self):
        program = self.acceptance["autonomous_language_search"]
        self.assertGreaterEqual(program["candidate_programs_evaluated"], 70)
        self.assertEqual(program["stop_reason"], "semantic_saturation")
        self.assertFalse(program["human_names_received"])

    def test_no_formula_is_forced(self):
        program = self.acceptance["autonomous_language_search"]
        self.assertEqual(program["features"], ["ONE"])
        self.assertGreaterEqual(program["validation"]["rmse_ratio_to_zero_baseline"], 0.98)
        self.assertGreaterEqual(self.acceptance["sealed_transfer"]["rmse_ratio_to_zero_baseline"], 0.98)
        self.assertFalse(self.acceptance["local_formula_accepted"])

    def test_counterexamples_are_retained(self):
        room = self.acceptance["mistake_room"]
        self.assertEqual(room["program_status"], "rejected")
        self.assertTrue(room["mandatory_replay"])
        self.assertGreaterEqual(len(room["counterexamples"]), 10)

    def test_next_task_invents_features(self):
        campaign = self.acceptance["long_horizon_research"]["campaign"]
        self.assertEqual(campaign["next_selected_task"], "event_world_feature_invention")
        self.assertFalse(campaign["next_selection_host_selected"])

    def test_independent_verifier_rejects_tampering(self):
        self.assertTrue(verify_v49_acceptance(self.acceptance)["passed"])
        tampered = copy.deepcopy(self.acceptance)
        tampered["autonomous_language_search"]["coefficients"][0] += 1.0
        self.assertFalse(verify_v49_acceptance(tampered)["passed"])


if __name__ == "__main__":
    unittest.main()
