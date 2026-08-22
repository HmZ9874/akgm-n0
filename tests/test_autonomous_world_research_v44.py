from __future__ import annotations

import copy
import unittest

from akgm_n0.evaluator.autonomous_world_research_v44 import (
    run_v44_acceptance,
    verify_v44_acceptance,
)


class AutonomousWorldResearchV44Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_v44_acceptance()

    def test_acceptance_passes(self):
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["final_status"], "verified")

    def test_three_official_worlds_are_surveyed_anonymously(self):
        registry = self.report["official_registry"]
        self.assertEqual(registry["world_count"], 3)
        self.assertTrue(self.report["discovery_gates"]["world_and_domain_labels_hidden_during_selection"])

    def test_priority_not_host_selects_the_world(self):
        agenda = self.report["autonomous_agenda"]
        self.assertFalse(agenda["host_selected"])
        self.assertEqual(agenda["selected_world_id"], agenda["ranking"][0]["world_id"])
        self.assertTrue(all(item["host_selected"] is False for item in agenda["ranking"]))

    def test_cross_group_risk_prevents_repeating_first_failure(self):
        ranking = self.report["autonomous_agenda"]["ranking"]
        selected = ranking[0]
        tide = next(item for item in ranking if item["world_id"] == "WORLD-692abdb0cf477f47")
        self.assertGreater(tide["normalized_information_gain"], selected["normalized_information_gain"])
        self.assertLess(tide["cross_group_stability"], selected["cross_group_stability"])
        self.assertLess(tide["research_priority"], selected["research_priority"])

    def test_program_is_frozen_before_transfer_and_labels(self):
        registration = self.report["preregistration"]
        self.assertLess(registration["commit_event_index"], registration["transfer_reveal_event_index"])
        self.assertLess(registration["transfer_reveal_event_index"], registration["metadata_reveal_event_index"])

    def test_source_groups_are_disjoint(self):
        audit = self.report["sealed_transfer_audit"]
        training = set(audit["training_groups"])
        validation = set(audit["validation_groups"])
        transfer = set(audit["transfer_groups"])
        self.assertFalse(training & validation)
        self.assertFalse(training & transfer)
        self.assertFalse(validation & transfer)

    def test_sealed_transfer_is_below_development_scale(self):
        self.assertLess(self.report["sealed_transfer_audit"]["normalized_rmse"], 1.0)

    def test_failures_and_next_worlds_remain_recorded(self):
        mistakes = self.report["mistake_room"]
        self.assertEqual(len(mistakes["nonselected_worlds"]), 2)
        self.assertTrue(mistakes["rejected_language_mutations"])
        self.assertEqual(len(self.report["autonomous_agenda"]["next_research_queue"]), 2)

    def test_independent_replay_rejects_tampering(self):
        self.assertTrue(verify_v44_acceptance(self.report)["passed"])
        forged = copy.deepcopy(self.report)
        forged["discovery"]["selected_program"]["coefficients"][0] += 1.0
        self.assertFalse(verify_v44_acceptance(forged)["passed"])

    def test_unachieved_scientist_claims_remain_blocked(self):
        claims = self.report["claim_state"]
        self.assertTrue(claims["autonomous_official_world_selection_allowed"])
        self.assertFalse(claims["fully_autonomous_scientist_claim_allowed"])
        self.assertFalse(claims["causal_law_claim_allowed"])
        self.assertFalse(claims["independent_laboratory_replication_allowed"])
        self.assertFalse(claims["human_unknown_law_claim_allowed"])


if __name__ == "__main__":
    unittest.main()
