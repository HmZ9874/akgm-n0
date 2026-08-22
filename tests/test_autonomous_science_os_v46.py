from __future__ import annotations

import copy
import unittest

from akgm_n0.evaluator.autonomous_science_os_v46 import (
    run_v46_acceptance,
    verify_v46_acceptance,
)
from akgm_n0.learner.autonomous_science_os_v46 import LongHorizonResearchManagerV46


class AutonomousScienceOSV46Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_v46_acceptance()

    def test_acceptance_and_dependencies_pass(self):
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["final_status"], "verified")
        self.assertTrue(all(item["passed"] for item in self.report["dependency_chain"].values()))

    def test_network_source_is_selected_by_gap_not_host(self):
        agenda = self.report["network_reality"]["agenda"]
        self.assertFalse(agenda["host_selected"])
        self.assertEqual(agenda["selected"]["source_id"], agenda["ranking"][0]["source_id"])
        self.assertFalse(agenda["selected"]["domain_name_received"])

    def test_network_collection_has_receipt_and_commitment_order(self):
        reality = self.report["network_reality"]
        registration = reality["preregistration"]
        collection = reality["collection"]
        self.assertGreaterEqual(collection["record_count"], 100)
        self.assertEqual(collection["receipt"]["status"], 200)
        self.assertEqual(len(collection["receipt"]["sha256"]), 64)
        self.assertLess(registration["commit_event_index"], registration["collection_event_index"])
        self.assertLess(registration["collection_event_index"], registration["metadata_reveal_event_index"])

    def test_arbitrary_network_access_is_not_granted(self):
        self.assertFalse(self.report["network_reality"]["policy"]["arbitrary_urls_allowed"])

    def test_new_composite_opcode_is_created_and_verified(self):
        language = self.report["open_language_creation"]
        semantic = language["invented_semantic"]
        self.assertTrue(semantic["semantic_id"].startswith("OPX-"))
        self.assertGreater(semantic["token_savings_per_use"], 0)
        self.assertTrue(language["independent_expansion_verification"]["passed"])
        self.assertTrue(semantic["sandbox_required"])

    def test_causal_mechanisms_survive_ablation(self):
        causal = self.report["causal_and_mechanism_reasoning"]
        self.assertTrue(causal["assigned_interventions"])
        self.assertTrue(causal["all_selected_mechanisms_essential"])
        self.assertEqual(len(causal["mechanism_ablation"]), 2)
        self.assertTrue(all(item["mechanistically_essential"] for item in causal["mechanism_ablation"]))

    def test_unique_universal_graph_claim_is_blocked(self):
        causal = self.report["causal_and_mechanism_reasoning"]
        self.assertFalse(causal["unique_universal_causal_graph_claim_allowed"])
        self.assertIn("not proved", causal["confounding_assessment"])

    def test_instrument_blueprint_has_all_safety_interlocks(self):
        instrument = self.report["instrument_architecture"]
        self.assertTrue(instrument["verification"]["passed"])
        self.assertEqual(
            instrument["verification"]["required_interlock_count"],
            instrument["verification"]["present_interlock_count"],
        )
        self.assertFalse(instrument["blueprint"]["fabrication_executed"])
        self.assertTrue(instrument["blueprint"]["manufacturing_authority_required"])

    def test_long_horizon_campaign_records_budget_and_next_task(self):
        campaign = self.report["long_horizon_research"]["campaign"]
        self.assertEqual(campaign["cycle_index"], 1)
        self.assertGreater(campaign["budgets"]["compute_units_remaining"], 0)
        self.assertIsNotNone(campaign["next_selected_task"])
        self.assertFalse(campaign["next_selection_host_selected"])

    def test_long_horizon_manager_resumes_prior_state(self):
        campaign = self.report["long_horizon_research"]["campaign"]
        resumed = LongHorizonResearchManagerV46().advance(campaign, {
            "compute_cost": 1.0,
            "network_cost": 1.0,
            "network_collected": True,
            "semantic_verified": True,
            "causal_verified": True,
        })
        self.assertTrue(resumed["resumed_from_prior_state"])
        self.assertEqual(resumed["cycle_index"], campaign["cycle_index"] + 1)
        self.assertLess(resumed["budgets"]["compute_units_remaining"], campaign["budgets"]["compute_units_remaining"])

    def test_literature_audit_is_conservative(self):
        audit = self.report["literature_and_human_knowledge_audit"]
        self.assertEqual(audit["provider"], "Crossref REST API")
        self.assertGreaterEqual(audit["record_count"], 5)
        self.assertFalse(audit["full_text_reviewed"])
        self.assertFalse(audit["human_unknown_claim_allowed"])

    def test_independent_replay_rejects_semantic_tampering(self):
        self.assertTrue(verify_v46_acceptance(self.report)["passed"])
        forged = copy.deepcopy(self.report)
        forged["open_language_creation"]["invented_semantic"]["expansion_coefficients"][0] += 1.0
        self.assertFalse(verify_v46_acceptance(forged)["passed"])

    def test_partial_capabilities_are_not_reported_as_execution(self):
        status = self.report["capability_status"]
        self.assertIn("not executed", status["instrument_manufacture_or_modification"])
        self.assertIn("no new natural-system intervention", status["causal_experiment"])

    def test_full_scientist_and_novelty_claims_remain_blocked(self):
        claims = self.report["claim_state"]
        self.assertTrue(claims["autonomous_network_collection_allowed"])
        self.assertTrue(claims["sandboxed_open_language_creation_allowed"])
        self.assertFalse(claims["physical_instrument_manufactured_allowed"])
        self.assertFalse(claims["v46_new_natural_physical_causal_experiment_allowed"])
        self.assertFalse(claims["human_unknown_law_allowed"])
        self.assertFalse(claims["fully_autonomous_scientist_allowed"])


if __name__ == "__main__":
    unittest.main()
