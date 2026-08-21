from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from akgm_n0.evaluator.operator_catalog_v5 import (
    run_operator_catalog_v5,
    verify_operator_catalog_v5_report,
)
from akgm_n0.evaluator.operator_catalog_v5_room import VerifiedOperatorCatalogRoom


class OperatorCatalogV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_operator_catalog_v5()

    def test_exactly_fifty_distinct_verified_operators(self) -> None:
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["promoted_operator_count"], 50)
        self.assertEqual(self.report["unique_program_count"], 50)
        self.assertEqual(self.report["unique_behavior_signature_count"], 50)

    def test_every_name_was_hidden_during_search(self) -> None:
        self.assertFalse(self.report["learner_received_formula_names"])
        self.assertTrue(all(not item["name_visible_to_learner"] for item in self.report["operators"]))

    def test_generic_power_uses_invented_state_input_interaction(self) -> None:
        record = next(item for item in self.report["operators"] if item["operator_id"] == "OPV5-R06")
        self.assertIn("grow_input_interaction", record["mutations"])
        self.assertEqual(record["classification"], "new_state_input_interaction_operator")
        self.assertTrue(record["program"]["state_input_coefficients"])

    def test_all_symbolic_proofs_and_replay_pass(self) -> None:
        self.assertTrue(all(item["symbolic_verification"]["passed"] for item in self.report["operators"]))
        self.assertTrue(verify_operator_catalog_v5_report(self.report)["passed"])

    def test_tampering_is_rejected(self) -> None:
        forged = json.loads(json.dumps(self.report))
        target = next(item for item in forged["operators"] if item["operator_id"] == "OPV5-R06")
        target["program"]["state_input_coefficients"] = [[0, 0]]
        self.assertFalse(verify_operator_catalog_v5_report(forged)["passed"])

    def test_verified_room_contains_and_replays_fifty_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "operators.jsonl"
            room = VerifiedOperatorCatalogRoom(path)
            for record in self.report["operators"]:
                room.record(record)
            self.assertEqual(len(VerifiedOperatorCatalogRoom(path).records), 50)


if __name__ == "__main__":
    unittest.main()
