from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from akgm_n0.evaluator.operator_frontier_v4 import (
    run_operator_frontier,
    verify_operator_frontier_report,
)
from akgm_n0.evaluator.operator_frontier_v4_room import VerifiedOperatorRoom


class OperatorFrontierV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_operator_frontier()

    def test_twelve_distinct_operators_are_promoted(self) -> None:
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["promoted_operator_count"], 12)
        self.assertTrue(self.report["all_behavior_signatures_distinct"])
        self.assertTrue(all(item["promoted"] for item in self.report["operators"]))

    def test_names_were_added_only_after_search(self) -> None:
        self.assertTrue(all(not item["name_visible_to_learner"] for item in self.report["operators"]))

    def test_every_operator_has_symbolic_or_complete_finite_proof(self) -> None:
        self.assertTrue(all(item["symbolic_verification"]["passed"] for item in self.report["operators"]))

    def test_scaled_product_receives_generalized_induction_certificate(self) -> None:
        record = next(item for item in self.report["operators"] if item["world_id"] == "OW-bbe")
        self.assertIn("scaled_counter_product_induction", {item["proof_domain"] for item in record["portfolio_proofs"]})

    def test_tampering_is_rejected(self) -> None:
        self.assertTrue(verify_operator_frontier_report(self.report)["passed"])
        forged = json.loads(json.dumps(self.report))
        forged["operators"][0]["program"]["guard_mode"] = 1
        self.assertFalse(verify_operator_frontier_report(forged)["passed"])

    def test_verified_room_replays_all_operators(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "operators.jsonl"
            room = VerifiedOperatorRoom(path)
            for record in self.report["operators"]:
                room.record(record)
            self.assertEqual(len(VerifiedOperatorRoom(path).records), 12)


if __name__ == "__main__":
    unittest.main()
