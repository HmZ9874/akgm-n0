from __future__ import annotations

import copy
import unittest

from akgm_n0.evaluator.open_set_representation_v50 import (
    run_v50_acceptance,
    verify_v50_acceptance,
)


class OpenSetRepresentationV50Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v50_acceptance()

    def test_acceptance_passes(self):
        self.assertTrue(self.acceptance["passed"])
        self.assertTrue(all(item["passed"] for item in self.acceptance["proof_obligations"]))

    def test_v49_gap_selects_representation_invention(self):
        task = self.acceptance["task_selection"]
        self.assertEqual(task["selected_task"], "event_world_feature_invention")
        self.assertTrue(task["selected_from_v49_gap"])
        self.assertFalse(task["host_selected"])

    def test_grid_is_derived_without_physical_labels(self):
        world = self.acceptance["anonymous_set_world"]
        self.assertEqual(world["grid"]["derived_from"], "training_values_only")
        self.assertFalse(world["physical_labels_available_during_search"])
        self.assertGreaterEqual(len(world["grid"]["thresholds"]), 6)

    def test_nontrivial_ast_is_synthesized(self):
        discovery = self.acceptance["representation_discovery"]
        self.assertGreaterEqual(discovery["evaluated_candidate_count"], 4)
        self.assertEqual(
            discovery["selected"]["ast"],
            {"op": "SAFE_DIV", "args": [{"var": "B"}, {"var": "A"}]},
        )
        self.assertTrue(all(discovery["anti_triviality"].values()))
        self.assertFalse(discovery["human_law_name_received"])

    def test_relation_transfers_without_refit(self):
        selected = self.acceptance["representation_discovery"]["selected"]
        sealed = self.acceptance["sealed_transfer"]
        self.assertLess(selected["validation"]["prediction_rmse_ratio"], 0.2)
        self.assertLess(sealed["prediction_rmse_ratio"], 0.2)
        self.assertLess(sealed["constant_relative_shift"], 0.02)
        self.assertFalse(sealed["constant_refit_on_sealed"])

    def test_bounded_success_and_residual_rooms(self):
        self.assertTrue(self.acceptance["success_room"]["registered"])
        self.assertFalse(self.acceptance["success_room"]["universal"])
        self.assertTrue(self.acceptance["mistake_room"]["mandatory_replay"])
        self.assertGreaterEqual(len(self.acceptance["mistake_room"]["counterexamples"]), 5)

    def test_posthoc_mapping_is_known_not_novel(self):
        translation = self.acceptance["posthoc_translation"]
        self.assertTrue(translation["labels_revealed_after_sealed_audit"])
        self.assertEqual(
            translation["human_equivalent"]["known_human_family"],
            "Gutenberg-Richter frequency-magnitude relation",
        )
        self.assertFalse(self.acceptance["claim_state"]["human_unknown_law_allowed"])

    def test_next_task_is_independent_replication(self):
        campaign = self.acceptance["long_horizon_research"]["campaign"]
        self.assertEqual(campaign["next_selected_task"], "independent_distribution_law_replication")
        self.assertFalse(campaign["next_selection_host_selected"])

    def test_independent_verifier_rejects_tampering(self):
        self.assertTrue(verify_v50_acceptance(self.acceptance)["passed"])
        tampered = copy.deepcopy(self.acceptance)
        tampered["representation_discovery"]["selected"]["constant"] += 0.1
        self.assertFalse(verify_v50_acceptance(tampered)["passed"])


if __name__ == "__main__":
    unittest.main()
