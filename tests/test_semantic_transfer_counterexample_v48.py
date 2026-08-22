from __future__ import annotations

import copy
import unittest

from akgm_n0.evaluator.semantic_transfer_counterexample_v48 import (
    run_v48_acceptance,
    verify_v48_acceptance,
)


class SemanticTransferCounterexampleV48Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v48_acceptance()

    def test_acceptance_passes(self):
        self.assertTrue(self.acceptance["passed"])
        self.assertTrue(all(item["passed"] for item in self.acceptance["proof_obligations"]))

    def test_v47_selected_this_task(self):
        task = self.acceptance["task_selection"]
        self.assertEqual(task["selected_task"], "semantic_transfer_counterexample_campaign")
        self.assertTrue(task["selected_by_v47"])
        self.assertFalse(task["host_selected"])

    def test_frozen_opx_fails_cross_domain_transfer(self):
        transfer = self.acceptance["frozen_opx_transfer"]
        self.assertEqual(transfer["world_count"], 3)
        self.assertEqual(transfer["passed_world_count"], 0)
        self.assertFalse(transfer["universal_transfer_claim_allowed"])
        self.assertTrue(all(item["frozen_without_refit"] for item in transfer["world_results"]))

    def test_counterexamples_enter_mistake_room(self):
        room = self.acceptance["mistake_room"]
        self.assertEqual(room["failed_world_count"], 3)
        self.assertTrue(room["mandatory_replay"])
        self.assertTrue(all(item["counterexamples"] for item in room["failures"]))

    def test_replacement_is_bounded_not_universal(self):
        search = self.acceptance["counterexample_driven_search"]
        self.assertEqual(search["selected"]["features"], ["PREV", "DELTA"])
        self.assertEqual(len(search["passed_worlds"]), 2)
        self.assertEqual(len(search["failed_worlds"]), 1)
        self.assertFalse(search["universal_formula_accepted"])

    def test_new_scope_semantic_is_verified(self):
        semantic = self.acceptance["new_semantic"]
        self.assertTrue(semantic["semantic_id"].startswith("SCOPESEM-"))
        self.assertEqual(semantic["source_decision"], "execute")
        self.assertTrue(semantic["cross_domain_decision"].startswith("abstain"))
        self.assertEqual(semantic["false_cross_domain_accept_count"], 0)

    def test_campaign_advances_to_new_world_search(self):
        research = self.acceptance["long_horizon_research"]
        self.assertEqual(research["campaign"]["cycle_index"], research["previous_campaign_cycle"] + 1)
        self.assertEqual(research["campaign"]["next_selected_task"], "new_world_semantic_search")

    def test_independent_verifier_rejects_tampering(self):
        self.assertTrue(verify_v48_acceptance(self.acceptance)["passed"])
        tampered = copy.deepcopy(self.acceptance)
        tampered["new_semantic"]["cross_domain_decision"] = "execute"
        self.assertFalse(verify_v48_acceptance(tampered)["passed"])


if __name__ == "__main__":
    unittest.main()
