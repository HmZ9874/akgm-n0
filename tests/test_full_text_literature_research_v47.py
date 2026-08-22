from __future__ import annotations

import copy
import unittest

from akgm_n0.evaluator.full_text_literature_research_v47 import (
    run_v47_acceptance,
    verify_v47_acceptance,
)


class FullTextLiteratureResearchV47Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v47_acceptance()

    def test_acceptance_passes(self):
        self.assertTrue(self.acceptance["passed"])
        self.assertTrue(all(item["passed"] for item in self.acceptance["proof_obligations"]))

    def test_discovery_was_frozen_before_search(self):
        frozen = self.acceptance["frozen_discovery"]
        self.assertTrue(frozen["semantic_id"].startswith("OPX-"))
        self.assertEqual(len(frozen["commitment"]), 64)
        self.assertFalse(self.acceptance["prior_art_audit"]["discovery_was_modified_by_literature"])

    def test_full_text_is_open_and_not_copied(self):
        evidence = self.acceptance["open_full_text_evidence"]
        self.assertGreaterEqual(len(evidence["documents"]), 4)
        self.assertFalse(evidence["full_text_retained"])
        for document in evidence["documents"]:
            self.assertTrue(document["open_licence_detected"])
            self.assertGreaterEqual(document["body_word_count"], 1000)
            self.assertFalse(document["full_text_stored_in_repository"])
            self.assertEqual(document["receipt"]["status"], 200)

    def test_known_family_and_components_detected(self):
        audit = self.acceptance["prior_art_audit"]
        self.assertTrue(audit["foundational_prior_art_detected"])
        self.assertTrue(audit["known_components_detected"])
        self.assertFalse(audit["exact_formula_identity_established"])

    def test_claims_remain_conservative(self):
        claims = self.acceptance["claim_state"]
        self.assertTrue(claims["autonomous_full_text_audit_allowed"])
        self.assertFalse(claims["human_unknown_law_allowed"])
        self.assertFalse(claims["exhaustive_global_novelty_review_allowed"])
        self.assertFalse(claims["fully_autonomous_scientist_allowed"])

    def test_campaign_advances_and_selects_counterexamples(self):
        research = self.acceptance["long_horizon_research"]
        self.assertEqual(research["campaign"]["cycle_index"], research["previous_campaign_cycle"] + 1)
        self.assertEqual(research["campaign"]["completed_task"], "full_text_literature_review")
        self.assertEqual(research["campaign"]["next_selected_task"], "semantic_transfer_counterexample_campaign")
        self.assertFalse(research["campaign"]["next_selection_host_selected"])

    def test_independent_verifier_rejects_receipt_tampering(self):
        self.assertTrue(verify_v47_acceptance(self.acceptance)["passed"])
        tampered = copy.deepcopy(self.acceptance)
        tampered["open_full_text_evidence"]["documents"][0]["receipt"]["sha256"] = "0" * 64
        self.assertFalse(verify_v47_acceptance(tampered)["passed"])


if __name__ == "__main__":
    unittest.main()
