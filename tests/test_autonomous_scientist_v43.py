from __future__ import annotations

import copy
import unittest

from akgm_n0.evaluator.autonomous_scientist_v43 import (
    run_v43_acceptance,
    verify_v43_acceptance,
)


class AutonomousScientistV43Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_v43_acceptance()

    def test_acceptance_passes(self):
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["final_status"], "verified")

    def test_named_candidate_menu_is_removed(self):
        discovery = self.report["discovery"]
        self.assertTrue(self.report["discovery_gates"]["no_named_candidate_menu_received"])
        self.assertFalse(discovery["selected_program"]["named_candidate_family_supplied"])

    def test_language_grows_from_minimal_genome(self):
        discovery = self.report["discovery"]
        self.assertEqual(discovery["initial_genome"]["state_slots"], 0)
        self.assertEqual(discovery["initial_genome"]["visible_inputs"], 1)
        self.assertEqual(discovery["final_genome"]["state_slots"], 2)
        self.assertEqual(discovery["final_genome"]["visible_inputs"], 2)
        self.assertEqual(
            discovery["selected_mutations"],
            ["grow_state_slot", "grow_input_channel", "grow_state_slot"],
        )

    def test_every_round_is_score_selected(self):
        self.assertTrue(all(
            item["host_selected"] is False for item in self.report["discovery"]["rounds"]
        ))

    def test_loop_stops_only_after_three_sterile_rounds(self):
        discovery = self.report["discovery"]
        self.assertEqual(discovery["stop_reason"], "semantic_saturation")
        self.assertEqual(discovery["sterile_rounds"], 3)

    def test_program_is_committed_before_transfer(self):
        registration = self.report["preregistration"]
        self.assertTrue(registration["commitment_precedes_transfer_reveal"])
        self.assertLess(
            registration["commit_event_index"], registration["transfer_reveal_event_index"],
        )

    def test_every_transfer_stage_passes(self):
        audit = self.report["transfer_audit"]
        self.assertTrue(all(audit["stage_passes"].values()))
        self.assertTrue(all(
            audit["by_life_stage"][stage]["rmse"] < 0.10
            for stage in ("early", "middle", "late")
        ))

    def test_v43_is_shorter_and_more_accurate_than_v42(self):
        gates = self.report["discovery_gates"]
        self.assertTrue(gates["shorter_than_v42_selected_program"])
        self.assertTrue(gates["lower_transfer_rmse_than_v42"])

    def test_independent_replay_passes_and_rejects_tampering(self):
        self.assertTrue(verify_v43_acceptance(self.report)["passed"])
        forged = copy.deepcopy(self.report)
        forged["discovery"]["selected_program"]["coefficients"][0] += 1.0
        self.assertFalse(verify_v43_acceptance(forged)["passed"])

    def test_full_autonomy_and_novel_law_claims_remain_blocked(self):
        claim = self.report["claim_state"]
        self.assertTrue(claim["autonomous_language_growth_on_reused_archive_allowed"])
        self.assertFalse(claim["fully_autonomous_scientist_claim_allowed"])
        self.assertFalse(claim["fresh_external_replication_claim_allowed"])
        self.assertFalse(claim["human_unknown_claim_allowed"])


if __name__ == "__main__":
    unittest.main()
