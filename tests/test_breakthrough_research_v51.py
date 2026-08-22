from __future__ import annotations

import copy
import unittest

from akgm_n0.evaluator.breakthrough_research_v51 import (
    run_v51_acceptance,
    verify_v51_acceptance,
)


class BreakthroughResearchV51Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v51_acceptance()

    def test_architecture_upgrade_replays(self):
        self.assertTrue(self.acceptance["passed"])
        self.assertTrue(verify_v51_acceptance(self.acceptance)["passed"])

    def test_mechanisms_compete_by_behavior(self):
        tournament = self.acceptance["mechanism_tournament"]
        self.assertGreaterEqual(tournament["programs_generated"], 100)
        self.assertLessEqual(tournament["behavior_classes"], tournament["programs_generated"])
        self.assertLess(tournament["sealed_audit"]["rmse"], 1e-8)
        self.assertIsNotNone(tournament["next_discriminating_intervention"])

    def test_representation_is_executable_and_compressive(self):
        representation = self.acceptance["representation_forge"]
        self.assertTrue(representation["behaviorally_equivalent_on_registered_domain"])
        self.assertGreater(representation["token_savings_per_call"], 0)
        self.assertLess(representation["sealed_macro_rmse"], 1e-8)
        self.assertEqual(len(representation["dependency_slots"]), 3)

    def test_ten_is_a_hard_evidence_contract(self):
        axes = {axis["axis_id"]: axis for axis in self.acceptance["ten_gate_standard"]["axes"]}
        self.assertEqual(axes["autonomous_representation_creation"]["target"], 10)
        self.assertFalse(axes["human_unknown_scientific_law"]["reached_ten"])
        self.assertFalse(self.acceptance["claim_state"]["breakthrough_claim_allowed"])

    def test_unknown_law_cannot_be_self_awarded(self):
        claim = self.acceptance["claim_state"]
        self.assertFalse(claim["human_unknown_law_discovered"])
        tampered = copy.deepcopy(self.acceptance)
        tampered["claim_state"]["human_unknown_law_discovered"] = True
        tampered["claim_state"]["breakthrough_claim_allowed"] = True
        self.assertFalse(verify_v51_acceptance(tampered)["passed"])


if __name__ == "__main__":
    unittest.main()
